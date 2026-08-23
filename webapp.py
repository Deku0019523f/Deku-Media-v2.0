# -*- coding: utf-8 -*-
"""
Page web de téléchargement — une seule page (pas d'écran de connexion séparé) :
- Non connecté : formulaire "ID Telegram" -> code à 6 chiffres -> session
- Connecté : formulaire de téléchargement avec aperçu (façon Telegram) avant
  de lancer le téléchargement

Routes montées sur le même serveur aiohttp que les webhooks de paiement
(voir webhook_server.py / bot.py) :

  GET  /                    page unique (login OU outil, selon la session)
  POST /auth/request-code   envoie le code de connexion via le bot
  POST /auth/verify-code    vérifie le code, ouvre la session
  POST /api/preview         aperçu (titre, miniature, durée...) sans télécharger
  POST /api/download        lance le téléchargement pour l'utilisateur connecté
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

GITHUB_REPO_URL = "https://github.com/Deku0019523f/Deku-Media-v2.0"

_COOKIE_SECURE = PUBLIC_BASE_URL.startswith("https://")

# Références gardées en vie pour les tâches de fond (asyncio.create_task ne
# garde pas de référence forte par lui-même)
_background_tasks = set()


def _get_logged_in_user_id(request: web.Request):
    token = request.cookies.get("session")
    if not token:
        return None
    return verify_session_token(token)


def _format_duration(seconds) -> str:
    try:
        seconds = int(seconds or 0)
    except (TypeError, ValueError):
        return "?"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


# ==================== GABARIT DE PAGE ====================

_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1">
<meta name="theme-color" content="#0f1115">
<title>Deku225-média — Téléchargement multiplateforme</title>
<link rel="icon" href="/static/favicon.png">
<style>
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: radial-gradient(circle at top, #1c2029 0%, #0a0b0f 70%);
    color: #eaeaea; margin: 0; min-height: 100vh;
    display: flex; flex-direction: column; align-items: center;
  }}
  .wrap {{ width: 100%; max-width: 460px; padding: 24px 18px 12px; flex: 1; }}
  header {{ text-align: center; margin-bottom: 20px; }}
  header img {{ width: 84px; height: 84px; border-radius: 20px; box-shadow: 0 6px 24px rgba(0,0,0,0.5); }}
  header h1 {{ font-size: 1.3rem; margin: 12px 0 2px; }}
  header p {{ color: #8b8f99; font-size: 0.85rem; margin: 0; }}

  .card {{
    background: #171a21; border: 1px solid #262a35; border-radius: 18px;
    padding: 26px 22px; box-shadow: 0 10px 34px rgba(0,0,0,0.35);
  }}
  .card + .card {{ margin-top: 16px; }}

  h2 {{ font-size: 1.05rem; margin: 0 0 6px; }}
  p.hint {{ color: #8b8f99; font-size: 0.85rem; line-height: 1.5; margin: 0 0 16px; }}

  input[type=text] {{
    width: 100%; padding: 13px 14px; border-radius: 12px; border: 1px solid #2c313d;
    background: #0e1015; color: #fff; font-size: 1rem; margin-bottom: 10px;
  }}
  input[type=text]:focus {{ outline: none; border-color: #3390ec; }}

  button {{
    width: 100%; padding: 13px; border-radius: 12px; border: none;
    background: #3390ec; color: #fff; font-size: 1rem; font-weight: 600;
    cursor: pointer; transition: opacity .15s; min-height: 46px;
  }}
  button:active {{ opacity: 0.8; }}
  button:disabled {{ opacity: 0.5; cursor: default; }}
  button.secondary {{ background: transparent; color: #8b8f99; font-weight: 500; text-decoration: underline; }}
  button.success {{ background: #2ea043; }}

  .status-line {{ margin-top: 12px; font-size: 0.88rem; text-align: center; min-height: 20px; color: #c7cad1; }}
  .status-line.err {{ color: #f2777a; }}
  .status-line.ok {{ color: #6bd68a; }}

  .spinner {{
    display: inline-block; width: 16px; height: 16px; border: 2px solid #3390ec44;
    border-top-color: #3390ec; border-radius: 50%; animation: spin .7s linear infinite;
    vertical-align: middle; margin-right: 6px;
  }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}

  .preview {{ display: flex; gap: 12px; margin-bottom: 16px; }}
  .preview img {{
    width: 96px; height: 96px; object-fit: cover; border-radius: 12px; flex-shrink: 0;
    background: #0e1015;
  }}
  .preview .meta {{ min-width: 0; }}
  .preview .meta .title {{
    font-size: 0.92rem; font-weight: 600; margin: 0 0 6px;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  }}
  .preview .meta .sub {{ color: #8b8f99; font-size: 0.8rem; margin: 2px 0; }}
  .badge {{
    display: inline-block; background: #24304a; color: #7fb1f8; font-size: 0.72rem;
    padding: 2px 9px; border-radius: 999px; font-weight: 600; text-transform: capitalize;
  }}

  select {{
    width: 100%; padding: 11px 14px; border-radius: 12px; border: 1px solid #2c313d;
    background: #0e1015; color: #fff; font-size: 0.95rem; margin-bottom: 12px;
  }}

  a.dl-link {{
    display: block; text-align: center; margin-top: 4px; background: #2ea043; color: #fff;
    padding: 13px; border-radius: 12px; text-decoration: none; font-weight: 600;
  }}

  .top-account {{ display: flex; justify-content: space-between; align-items: center; font-size: 0.82rem; color: #8b8f99; margin-bottom: 14px; }}
  .top-account b {{ color: #eaeaea; }}
  .top-account a {{ color: #6b7280; }}

  footer {{ text-align: center; padding: 24px 18px; color: #565a66; font-size: 0.78rem; }}
  footer a {{ color: #7fb1f8; text-decoration: none; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <img src="/static/logo.png" alt="Deku225-média">
    <h1>Deku225-média</h1>
    <p>Téléchargement multiplateforme — YouTube, TikTok, Instagram, Facebook, Pinterest, Twitter/X et ~1750 autres sites</p>
  </header>
  {content}
</div>
<footer>
  Développé par <a href="https://t.me/Darkdeku225">@Darkdeku225</a> · Code source sur <a href="{repo_url}">GitHub</a>
</footer>
</body>
</html>"""


def _render(content: str) -> str:
    return _PAGE_TEMPLATE.format(content=content, repo_url=GITHUB_REPO_URL)


# ==================== CONTENU : CONNEXION ====================

_LOGIN_CONTENT = f"""
<div class="card" id="card-login">
  <div id="step-id">
    <h2>🔑 Connexion</h2>
    <p class="hint">Entre ton ID Telegram pour recevoir un code de connexion par message privé du bot. Tu dois avoir déjà démarré <a href="https://t.me/{BOT_USERNAME}" style="color:#3390ec;">@{BOT_USERNAME}</a> (/start) pour pouvoir le recevoir.</p>
    <input type="text" id="tgid" inputmode="numeric" placeholder="Ton ID Telegram (ex: 1299831974)">
    <button id="send-code">Recevoir mon code</button>
  </div>
  <div id="step-code" style="display:none;">
    <h2>📩 Code reçu</h2>
    <p class="hint">Entre le code à 6 chiffres reçu sur Telegram.</p>
    <input type="text" id="code" inputmode="numeric" maxlength="6" placeholder="Code à 6 chiffres">
    <button id="verify-code">Valider</button>
    <button class="secondary" id="back-id" type="button">← Changer d'ID</button>
  </div>
  <div class="status-line" id="login-status"></div>
</div>

<script>
const stepId = document.getElementById('step-id');
const stepCode = document.getElementById('step-code');
const statusEl = document.getElementById('login-status');
let currentId = null;

function setStatus(msg, cls) {{
  statusEl.textContent = msg;
  statusEl.className = 'status-line' + (cls ? ' ' + cls : '');
}}

document.getElementById('send-code').addEventListener('click', async () => {{
  const tgid = document.getElementById('tgid').value.trim();
  if (!tgid) return;
  setStatus('⏳ Envoi du code...');
  try {{
    const res = await fetch('/auth/request-code', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{telegram_id: tgid}})
    }});
    const data = await res.json();
    if (!res.ok) {{ setStatus('❌ ' + (data.error || 'Erreur.'), 'err'); return; }}
    currentId = tgid;
    setStatus('✅ Code envoyé — vérifie tes messages Telegram.', 'ok');
    stepId.style.display = 'none';
    stepCode.style.display = 'block';
  }} catch (e) {{ setStatus('❌ Erreur réseau.', 'err'); }}
}});

document.getElementById('back-id').addEventListener('click', () => {{
  stepCode.style.display = 'none';
  stepId.style.display = 'block';
  setStatus('');
}});

document.getElementById('verify-code').addEventListener('click', async () => {{
  const code = document.getElementById('code').value.trim();
  if (!code || !currentId) return;
  setStatus('⏳ Vérification...');
  try {{
    const res = await fetch('/auth/verify-code', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{telegram_id: currentId, code}})
    }});
    const data = await res.json();
    if (!res.ok) {{ setStatus('❌ ' + (data.error || 'Code invalide.'), 'err'); return; }}
    window.location.href = '/';
  }} catch (e) {{ setStatus('❌ Erreur réseau.', 'err'); }}
}});
</script>
"""


async def handle_index(request: web.Request) -> web.Response:
    user_id = _get_logged_in_user_id(request)
    if not user_id:
        return web.Response(text=_render(_LOGIN_CONTENT), content_type="text/html")

    user_data = await user_manager.get_user(user_id)
    premium_badge = "✨ Premium" if user_data.get("premium") else "Compte standard"
    display_name = user_data.get("username") or user_id

    content = f"""
<div class="top-account">
  <span>{premium_badge} — <b>{display_name}</b></span>
  <a href="/logout">Se déconnecter</a>
</div>

<div class="card">
  <h2>📥 Télécharger une vidéo</h2>
  <p class="hint">Colle un lien (YouTube, TikTok, Instagram, Facebook, Pinterest, Twitter/X, ou l'un des ~1750 autres sites supportés).</p>
  <input type="text" id="url" placeholder="https://...">
  <button id="analyze">Analyser le lien</button>
  <div class="status-line" id="main-status"></div>
</div>

<div class="card" id="preview-card" style="display:none;"></div>

<script>
const urlInput = document.getElementById('url');
const analyzeBtn = document.getElementById('analyze');
const mainStatus = document.getElementById('main-status');
const previewCard = document.getElementById('preview-card');

function setMainStatus(msg, cls) {{
  mainStatus.textContent = msg;
  mainStatus.className = 'status-line' + (cls ? ' ' + cls : '');
}}

function fmtViews(n) {{
  if (!n) return null;
  if (n >= 1000000) return (n/1000000).toFixed(1) + 'M vues';
  if (n >= 1000) return (n/1000).toFixed(1) + 'k vues';
  return n + ' vues';
}}

analyzeBtn.addEventListener('click', async () => {{
  const url = urlInput.value.trim();
  if (!url) return;
  previewCard.style.display = 'none';
  analyzeBtn.disabled = true;
  setMainStatus('<span class="spinner"></span> Analyse du lien...');
  mainStatus.innerHTML = '<span class="spinner"></span> Analyse du lien...';
  mainStatus.className = 'status-line';

  try {{
    const res = await fetch('/api/preview', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{url}})
    }});
    const data = await res.json();
    analyzeBtn.disabled = false;
    if (!res.ok) {{ setMainStatus('❌ ' + (data.error || 'Erreur.'), 'err'); return; }}

    setMainStatus('');
    renderPreview(url, data);
  }} catch (e) {{
    analyzeBtn.disabled = false;
    setMainStatus('❌ Erreur réseau.', 'err');
  }}
}});

function renderPreview(url, info) {{
  const views = fmtViews(info.view_count);
  const formatOptions = (info.formats || [{{quality: 'best', label: 'Meilleure qualité'}}])
    .map(f => `<option value="${{f.quality}}">${{f.label}}</option>`).join('');

  previewCard.innerHTML = `
    <div class="preview">
      ${{info.thumbnail ? `<img src="${{info.thumbnail}}" alt="">` : '<div style="width:96px;height:96px;border-radius:12px;background:#0e1015;flex-shrink:0;"></div>'}}
      <div class="meta">
        <div class="title">${{info.title || 'Sans titre'}}</div>
        <div class="sub">⏱ ${{info.duration_text || '?'}} · 👤 ${{info.uploader || 'Inconnu'}}</div>
        ${{views ? `<div class="sub">👁 ${{views}}</div>` : ''}}
        <div class="sub"><span class="badge">${{info.platform}}</span></div>
      </div>
    </div>
    <select id="quality">${{formatOptions}}</select>
    <button id="confirm-download">⬇️ Télécharger</button>
    <div class="status-line" id="dl-status"></div>
  `;
  previewCard.style.display = 'block';

  document.getElementById('confirm-download').addEventListener('click', () => startDownload(url));
}}

async function startDownload(url) {{
  const btn = document.getElementById('confirm-download');
  const dlStatus = document.getElementById('dl-status');
  const quality = document.getElementById('quality').value;
  btn.disabled = true;
  dlStatus.innerHTML = '<span class="spinner"></span> Démarrage du téléchargement...';
  dlStatus.className = 'status-line';

  try {{
    const res = await fetch('/api/download', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{url, quality}})
    }});
    const data = await res.json();
    if (!res.ok) {{
      dlStatus.textContent = '❌ ' + (data.error || 'Erreur.');
      dlStatus.className = 'status-line err';
      btn.disabled = false;
      return;
    }}
    pollStatus(data.token, dlStatus, btn);
  }} catch (e) {{
    dlStatus.textContent = '❌ Erreur réseau.';
    dlStatus.className = 'status-line err';
    btn.disabled = false;
  }}
}}

async function pollStatus(token, dlStatus, btn) {{
  const res = await fetch('/api/status/' + token);
  const data = await res.json();
  if (data.status === 'ready') {{
    dlStatus.innerHTML = '';
    const a = document.createElement('a');
    a.href = data.download_url;
    a.className = 'dl-link';
    a.textContent = '✅ Télécharger le fichier';
    dlStatus.appendChild(a);
    btn.style.display = 'none';
  }} else if (data.status === 'error') {{
    dlStatus.textContent = '❌ ' + (data.error || 'Échec du téléchargement.');
    dlStatus.className = 'status-line err';
    btn.disabled = false;
  }} else {{
    dlStatus.innerHTML = '<span class="spinner"></span> Téléchargement en cours...';
    setTimeout(() => pollStatus(token, dlStatus, btn), 2000);
  }}
}}
</script>
"""
    return web.Response(text=_render(content), content_type="text/html")


async def handle_app(request: web.Request) -> web.Response:
    # Ancienne URL séparée conservée en redirection simple (page unique désormais)
    raise web.HTTPFound("/")


# ==================== AUTHENTIFICATION ====================

async def handle_request_code(request: web.Request) -> web.Response:
    try:
        body = await request.json()
        telegram_id = str(body.get("telegram_id", "")).strip()
    except Exception:
        return web.json_response({"error": "Requête invalide."}, status=400)

    if not telegram_id.isdigit():
        return web.json_response({"error": "ID Telegram invalide."}, status=400)

    user_id = int(telegram_id)

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


# ==================== TÉLÉCHARGEMENT ====================

async def handle_api_preview(request: web.Request) -> web.Response:
    user_id = _get_logged_in_user_id(request)
    if not user_id:
        return web.json_response({"error": "not_authenticated"}, status=401)

    try:
        body = await request.json()
        url = (body.get("url") or "").strip()
    except Exception:
        return web.json_response({"error": "Requête invalide."}, status=400)

    if not url:
        return web.json_response({"error": "Lien manquant."}, status=400)

    loop = asyncio.get_event_loop()
    is_supported, platform = await loop.run_in_executor(None, platform_detector.is_supported, url)
    if not is_supported:
        return web.json_response({"error": "Plateforme non supportée ou lien invalide."}, status=400)

    info = await downloader.get_video_info(url, platform)
    if not info:
        return web.json_response(
            {"error": "Impossible d'analyser ce lien (contenu privé, supprimé, ou site protégé)."},
            status=400
        )

    return web.json_response({
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "duration_text": _format_duration(info.get("duration")),
        "uploader": info.get("uploader"),
        "view_count": info.get("view_count"),
        "platform": platform,
        "formats": info.get("formats") or [{"quality": "best", "label": "Meilleure qualité"}],
    })


async def _process_web_download(token: str, url: str, platform: str, quality: str, user_id: int):
    """Tâche de fond : télécharge la vidéo puis met à jour le lien correspondant"""
    try:
        file_path = await downloader.download_video(url, platform, quality, user_id)

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
        await db.log_download(user_id, platform, url, quality, True)

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
        quality = (body.get("quality") or "best").strip()
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

    task = asyncio.create_task(_process_web_download(token, url, platform, quality, user_id))
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
            text=_render('<div class="card"><h2>🔗 Lien invalide ou expiré</h2><p class="hint">Redemande le téléchargement.</p></div>'),
            content_type="text/html",
            status=404,
        )

    path = Path(link["file_path"])
    if not path.exists():
        return web.Response(
            text=_render('<div class="card"><h2>🔗 Fichier introuvable</h2><p class="hint">Il a peut-être déjà expiré.</p></div>'),
            content_type="text/html",
            status=404,
        )

    return web.FileResponse(
        path,
        headers={"Content-Disposition": f'attachment; filename="{link.get("filename") or path.name}"'},
    )


def register_webapp_routes(app: web.Application):
    static_dir = Path(__file__).parent / "static"
    app.router.add_static("/static/", path=static_dir, name="static")

    app.router.add_get("/", handle_index)
    app.router.add_get("/app", handle_app)
    app.router.add_post("/auth/request-code", handle_request_code)
    app.router.add_post("/auth/verify-code", handle_verify_code)
    app.router.add_get("/logout", handle_logout)
    app.router.add_post("/api/preview", handle_api_preview)
    app.router.add_post("/api/download", handle_api_download)
    app.router.add_get("/api/status/{token}", handle_api_status)
    app.router.add_get("/dl/{token}", handle_download_file)
