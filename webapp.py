# -*- coding: utf-8 -*-
"""
Page web de téléchargement, liée à l'identité Telegram de l'utilisateur :
l'utilisateur saisit son ID Telegram, reçoit un code à 6 chiffres par
message privé du bot, et le recopie sur le site pour ouvrir sa session.

Routes montées sur le même serveur aiohttp que les webhooks de paiement
(voir webhook_server.py / bot.py) :

  GET  /                    page d'accueil (saisie de l'ID Telegram)
  POST /auth/request-code   envoie le code de connexion via le bot
  POST /auth/verify-code    vérifie le code, ouvre la session
  GET  /app                 page de téléchargement (nécessite une session)
  POST /api/download        lance un téléchargement pour l'utilisateur connecté
  GET  /api/status/{token}  statut d'un téléchargement en cours
  GET  /logout              efface la session
  GET  /dl/{token}          sert le fichier (sans connexion requise — lien à
                            usage direct, utilisé aussi pour l'envoi Telegram >50 Mo)

⚠️ Prérequis : l'utilisateur doit avoir déjà démarré une conversation avec
le bot (/start) — Telegram interdit à un bot d'écrire en premier à quelqu'un
qui ne lui a jamais parlé, donc l'envoi du code échouera sinon.
"""
import asyncio
import logging
import secrets
from pathlib import Path
from aiohttp import web
from telegram.error import TelegramError

from config import PUBLIC_BASE_URL, BOT_USERNAME, DOWNLOAD_LINK_EXPIRY, MAX_FILE_SIZE_MB
from utils.telegram_auth import (
    generate_login_code, create_session_token, verify_session_token,
    LOGIN_CODE_VALID_SECONDS, LOGIN_CODE_MAX_ATTEMPTS, LOGIN_CODE_REQUEST_COOLDOWN,
)
from utils.platform_detector import platform_detector
from utils.downloader import downloader
from utils.user_manager import user_manager
from utils.limits import limit_checker
from utils.database import db
from datetime import datetime

logger = logging.getLogger(__name__)

_COOKIE_SECURE = PUBLIC_BASE_URL.startswith("https://")

# Références gardées en vie pour les tâches de téléchargement en tâche de fond
# (asyncio.create_task ne garde pas de référence forte par lui-même)
_background_tasks = set()


def _get_logged_in_user_id(request: web.Request):
    token = request.cookies.get("session")
    if not token:
        return None
    return verify_session_token(token)


def _page(body: str, title: str = "Deku225-média") -> str:
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; background: #0f1115; color: #e8e8e8;
          margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 24px; box-sizing: border-box; }}
  .card {{ background: #1a1d24; border-radius: 16px; padding: 32px 28px; max-width: 420px; width: 100%;
           box-shadow: 0 8px 30px rgba(0,0,0,0.3); text-align: center; }}
  h1 {{ font-size: 1.4rem; margin-bottom: 8px; }}
  p {{ color: #a0a4ad; font-size: 0.95rem; line-height: 1.5; }}
  input[type=text] {{ width: 100%; padding: 12px 14px; border-radius: 10px; border: 1px solid #2c2f38;
                       background: #12141a; color: #fff; font-size: 1rem; box-sizing: border-box; margin: 16px 0 12px; }}
  button {{ width: 100%; padding: 12px; border-radius: 10px; border: none; background: #3390ec;
            color: #fff; font-size: 1rem; font-weight: 600; cursor: pointer; }}
  button:disabled {{ opacity: 0.6; cursor: default; }}
  #status {{ margin-top: 16px; font-size: 0.9rem; min-height: 24px; }}
  a.dl-link {{ display: inline-block; margin-top: 8px; background: #2ea043; color: #fff; padding: 10px 18px;
               border-radius: 10px; text-decoration: none; font-weight: 600; }}
  .muted {{ color: #6b7280; font-size: 0.8rem; margin-top: 24px; }}
</style>
</head>
<body>
<div class="card">
{body}
</div>
</body>
</html>"""


async def handle_index(request: web.Request) -> web.Response:
    if _get_logged_in_user_id(request):
        raise web.HTTPFound("/app")

    body = f"""
<h1>📥 Deku225-média</h1>
<p>Entre ton ID Telegram pour recevoir un code de connexion par message privé du bot.</p>
<p class="muted">Tu dois avoir déjà démarré <a href="https://t.me/{BOT_USERNAME}" style="color:#3390ec;">@{BOT_USERNAME}</a> (envoyé /start) pour pouvoir recevoir le code.</p>

<div id="step-id">
  <input type="text" id="tgid" inputmode="numeric" placeholder="Ton ID Telegram (ex: 1299831974)" />
  <button id="send-code">Recevoir mon code</button>
</div>

<div id="step-code" style="display:none;">
  <input type="text" id="code" inputmode="numeric" maxlength="6" placeholder="Code à 6 chiffres" />
  <button id="verify-code">Valider</button>
</div>

<div id="status"></div>

<script>
const stepId = document.getElementById('step-id');
const stepCode = document.getElementById('step-code');
const statusEl = document.getElementById('status');
let currentId = null;

document.getElementById('send-code').addEventListener('click', async () => {{
  const tgid = document.getElementById('tgid').value.trim();
  if (!tgid) return;
  statusEl.textContent = '⏳ Envoi du code...';
  try {{
    const res = await fetch('/auth/request-code', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{telegram_id: tgid}})
    }});
    const data = await res.json();
    if (!res.ok) {{
      statusEl.textContent = '❌ ' + (data.error || 'Erreur.');
      return;
    }}
    currentId = tgid;
    statusEl.textContent = '✅ Code envoyé sur Telegram — vérifie tes messages.';
    stepId.style.display = 'none';
    stepCode.style.display = 'block';
  }} catch (e) {{
    statusEl.textContent = '❌ Erreur réseau.';
  }}
}});

document.getElementById('verify-code').addEventListener('click', async () => {{
  const code = document.getElementById('code').value.trim();
  if (!code || !currentId) return;
  statusEl.textContent = '⏳ Vérification...';
  try {{
    const res = await fetch('/auth/verify-code', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{telegram_id: currentId, code}})
    }});
    const data = await res.json();
    if (!res.ok) {{
      statusEl.textContent = '❌ ' + (data.error || 'Code invalide.');
      return;
    }}
    window.location.href = '/app';
  }} catch (e) {{
    statusEl.textContent = '❌ Erreur réseau.';
  }}
}});
</script>
"""
    return web.Response(text=_page(body), content_type="text/html")


async def handle_request_code(request: web.Request) -> web.Response:
    try:
        body = await request.json()
        telegram_id = str(body.get("telegram_id", "")).strip()
    except Exception:
        return web.json_response({"error": "Requête invalide."}, status=400)

    if not telegram_id.isdigit():
        return web.json_response({"error": "ID Telegram invalide."}, status=400)

    user_id = int(telegram_id)

    # Anti-spam : pas plus d'une demande de code par minute pour le même ID
    # (évite qu'on puisse harceler quelqu'un de messages en boucle)
    existing = await db.get_login_code(user_id)
    if existing:
        created_at = datetime.fromisoformat(existing["created_at"])
        elapsed = (datetime.now() - created_at).total_seconds()
        if elapsed < LOGIN_CODE_REQUEST_COOLDOWN:
            wait = int(LOGIN_CODE_REQUEST_COOLDOWN - elapsed)
            return web.json_response({"error": f"Réessaie dans {wait}s."}, status=429)

    code = generate_login_code()
    await db.create_login_code(user_id, code, LOGIN_CODE_VALID_SECONDS)

    bot = request.app["bot"]
    try:
        await bot.send_message(
            user_id,
            f"🔑 Ton code de connexion au site : `{code}`\n\nValable 10 minutes.",
            parse_mode="Markdown"
        )
    except TelegramError:
        await db.delete_login_code(user_id)
        return web.json_response(
            {"error": f"Impossible de t'envoyer le code. As-tu bien démarré @{BOT_USERNAME} (/start) ?"},
            status=400
        )

    return web.json_response({"ok": True})


async def handle_verify_code(request: web.Request) -> web.Response:
    try:
        body = await request.json()
        telegram_id = str(body.get("telegram_id", "")).strip()
        code = str(body.get("code", "")).strip()
    except Exception:
        return web.json_response({"error": "Requête invalide."}, status=400)

    if not telegram_id.isdigit():
        return web.json_response({"error": "ID Telegram invalide."}, status=400)

    user_id = int(telegram_id)
    record = await db.get_login_code(user_id)

    if not record:
        return web.json_response({"error": "Aucun code en attente. Redemande-en un."}, status=400)

    if record["attempts"] >= LOGIN_CODE_MAX_ATTEMPTS:
        await db.delete_login_code(user_id)
        return web.json_response({"error": "Trop d'essais. Redemande un code."}, status=429)

    expires_at = datetime.fromisoformat(record["expires_at"])
    if datetime.now() > expires_at:
        await db.delete_login_code(user_id)
        return web.json_response({"error": "Code expiré. Redemande-en un."}, status=400)

    if code != record["code"]:
        await db.increment_login_code_attempts(user_id)
        remaining = LOGIN_CODE_MAX_ATTEMPTS - record["attempts"] - 1
        return web.json_response({"error": f"Code incorrect ({remaining} essai(s) restant(s))."}, status=400)

    await db.delete_login_code(user_id)
    await user_manager.get_user(user_id)  # crée le profil s'il n'existe pas encore

    token = create_session_token(user_id)
    response = web.json_response({"ok": True})
    response.set_cookie(
        "session", token,
        max_age=30 * 86400,
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite="Lax",
    )
    return response


async def handle_logout(request: web.Request) -> web.Response:
    response = web.HTTPFound("/")
    response.del_cookie("session")
    raise response


async def handle_app(request: web.Request) -> web.Response:
    user_id = _get_logged_in_user_id(request)
    if not user_id:
        raise web.HTTPFound("/")

    user_data = await user_manager.get_user(user_id)
    premium_badge = "✨ Premium actif" if user_data.get("premium") else "Compte standard"

    body = f"""
<h1>📥 Télécharger une vidéo</h1>
<p>{premium_badge} — connecté en tant que {user_data.get('username') or user_id}</p>
<input type="text" id="url" placeholder="Colle un lien (YouTube, TikTok, Vimeo, ...)" />
<button id="go">Télécharger</button>
<div id="status"></div>
<p class="muted"><a href="/logout" style="color:#6b7280;">Se déconnecter</a></p>
<script>
const btn = document.getElementById('go');
const statusEl = document.getElementById('status');
const urlInput = document.getElementById('url');

async function poll(token) {{
  const res = await fetch('/api/status/' + token);
  const data = await res.json();
  if (data.status === 'ready') {{
    statusEl.innerHTML = '✅ Prêt : <a class="dl-link" href="' + data.download_url + '">Télécharger le fichier</a>';
    btn.disabled = false;
  }} else if (data.status === 'error') {{
    statusEl.textContent = '❌ ' + (data.error || 'Échec du téléchargement.');
    btn.disabled = false;
  }} else {{
    statusEl.textContent = '⏳ Traitement en cours...';
    setTimeout(() => poll(token), 2000);
  }}
}}

btn.addEventListener('click', async () => {{
  const url = urlInput.value.trim();
  if (!url) return;
  btn.disabled = true;
  statusEl.textContent = '⏳ Démarrage...';
  try {{
    const res = await fetch('/api/download', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{url}})
    }});
    const data = await res.json();
    if (!res.ok) {{
      statusEl.textContent = '❌ ' + (data.error || 'Erreur.');
      btn.disabled = false;
      return;
    }}
    poll(data.token);
  }} catch (e) {{
    statusEl.textContent = '❌ Erreur réseau.';
    btn.disabled = false;
  }}
}});
</script>
"""
    return web.Response(text=_page(body), content_type="text/html")


async def _process_web_download(token: str, url: str, platform: str, user_id: int):
    """Tâche de fond : télécharge la vidéo puis met à jour le lien correspondant"""
    try:
        file_path = await downloader.download_video(url, platform, "best", user_id)

        if not file_path or not file_path.exists():
            await db.update_download_link(token, status="error", error="Fichier introuvable après téléchargement.")
            return

        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            file_path.unlink(missing_ok=True)
            await db.update_download_link(token, status="error", error="Fichier trop volumineux.")
            return

        await db.update_download_link(
            token, status="ready", file_path=str(file_path), filename=file_path.name
        )
        await user_manager.increment_download(user_id, platform == "youtube")
        await db.log_download(user_id, platform, url, "best", True)

    except Exception as e:
        logger.exception(f"Échec téléchargement web (token={token})")
        await db.update_download_link(token, status="error", error=str(e)[:200])


async def handle_api_download(request: web.Request) -> web.Response:
    user_id = _get_logged_in_user_id(request)
    if not user_id:
        return web.json_response({"error": "not_authenticated"}, status=401)

    try:
        body = await request.json()
        url = (body.get("url") or "").strip()
    except Exception:
        return web.json_response({"error": "invalid_request"}, status=400)

    if not url:
        return web.json_response({"error": "missing_url"}, status=400)

    loop = asyncio.get_event_loop()
    is_supported, platform = await loop.run_in_executor(None, platform_detector.is_supported, url)
    if not is_supported:
        return web.json_response({"error": "Plateforme non supportée ou lien invalide."}, status=400)

    user_data = await user_manager.get_user(user_id)
    is_youtube = platform == "youtube"
    can_download, error_msg = await limit_checker.check_limits(user_data, is_youtube)
    if not can_download:
        return web.json_response({"error": error_msg}, status=429)

    token = secrets.token_urlsafe(24)
    await db.create_download_link(token, user_id, DOWNLOAD_LINK_EXPIRY, status="pending")

    task = asyncio.create_task(_process_web_download(token, url, platform, user_id))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return web.json_response({"token": token}, status=202)


async def handle_api_status(request: web.Request) -> web.Response:
    user_id = _get_logged_in_user_id(request)
    if not user_id:
        return web.json_response({"error": "not_authenticated"}, status=401)

    token = request.match_info["token"]
    link = await db.get_download_link(token)

    if not link or link["user_id"] != user_id:
        return web.json_response({"error": "not_found"}, status=404)

    if link["status"] == "ready":
        return web.json_response({"status": "ready", "download_url": f"{PUBLIC_BASE_URL}/dl/{token}"})
    if link["status"] == "error":
        return web.json_response({"status": "error", "error": link.get("error")})
    return web.json_response({"status": "pending"})


async def handle_download_file(request: web.Request) -> web.Response:
    """Sert le fichier — pas de connexion requise (lien à usage direct,
    partagé ex. via un message Telegram pour les fichiers >50 Mo)."""
    token = request.match_info["token"]
    link = await db.get_download_link(token)

    if not link or link["status"] != "ready" or not link.get("file_path"):
        return web.Response(
            text=_page("<h1>🔗 Lien invalide ou expiré</h1><p>Redemande le téléchargement.</p>"),
            content_type="text/html",
            status=404,
        )

    path = Path(link["file_path"])
    if not path.exists():
        return web.Response(
            text=_page("<h1>🔗 Fichier introuvable</h1><p>Il a peut-être déjà expiré.</p>"),
            content_type="text/html",
            status=404,
        )

    return web.FileResponse(
        path,
        headers={"Content-Disposition": f'attachment; filename="{link.get("filename") or path.name}"'},
    )


def register_webapp_routes(app: web.Application):
    app.router.add_get("/", handle_index)
    app.router.add_post("/auth/request-code", handle_request_code)
    app.router.add_post("/auth/verify-code", handle_verify_code)
    app.router.add_get("/logout", handle_logout)
    app.router.add_get("/app", handle_app)
    app.router.add_post("/api/download", handle_api_download)
    app.router.add_get("/api/status/{token}", handle_api_status)
    app.router.add_get("/dl/{token}", handle_download_file)
