# -*- coding: utf-8 -*-
"""
Page web de téléchargement — accès libre, sans connexion Telegram requise.

⚠️ Sans identité Telegram vérifiée, il n'y a pas de suivi Premium ni de
limites quotidiennes personnalisées côté web (contrairement au bot Telegram,
qui lui garde toutes ses règles habituelles, inchangées). Chaque visiteur
reçoit un identifiant anonyme (cookie) utilisé uniquement pour retrouver ses
propres téléchargements en cours — ce n'est pas un compte.

Routes montées sur le même serveur aiohttp que les webhooks de paiement
(voir webhook_server.py / bot.py) :

  GET  /                    page unique : outil de téléchargement
  POST /api/preview         aperçu (titre, miniature, durée...) sans télécharger
  POST /api/download        lance le téléchargement
  GET  /api/status/{token}  statut d'un téléchargement en cours
  GET  /dl/{token}          sert le fichier (lien à usage direct, aussi
                            utilisé pour l'envoi Telegram des fichiers >50 Mo)
"""
import asyncio
import logging
import secrets
from pathlib import Path
from aiohttp import web

from config import PUBLIC_BASE_URL, DOWNLOAD_LINK_EXPIRY, MAX_FILE_SIZE_MB
from utils.platform_detector import platform_detector
from utils.downloader import downloader, download_progress
from utils.database import db

logger = logging.getLogger(__name__)

GITHUB_REPO_URL = "https://github.com/Deku0019523f/Deku-Media-v2.0"

_COOKIE_SECURE = PUBLIC_BASE_URL.startswith("https://")

# Références gardées en vie pour les tâches de fond (asyncio.create_task ne
# garde pas de référence forte par lui-même)
_background_tasks = set()


def _get_or_create_visitor_id(request: web.Request):
    """
    Identifiant anonyme par visiteur (cookie), utilisé UNIQUEMENT pour
    retrouver ses propres téléchargements en cours — ce n'est pas un compte,
    pas de lien avec Telegram, pas de Premium/limites personnalisées.
    """
    visitor_id = request.cookies.get("visitor_id")
    is_new = not visitor_id
    if is_new:
        visitor_id = secrets.token_urlsafe(16)
    return visitor_id, is_new


def _set_visitor_cookie(response: web.Response, visitor_id: str):
    response.set_cookie(
        "visitor_id", visitor_id,
        max_age=365 * 86400,
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite="Lax",
    )


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

  .progress-box {{ text-align: left; padding: 4px 2px; }}
  .progress-label {{ font-size: 0.88rem; color: #d7d9de; margin-bottom: 8px; }}
  .progress-label b {{ color: #fff; }}
  .progress-track {{
    width: 100%; height: 10px; background: #0e1015; border-radius: 999px;
    overflow: hidden; border: 1px solid #262a35;
  }}
  .progress-fill {{
    height: 100%; background: linear-gradient(90deg, #3390ec, #5aa9f5);
    border-radius: 999px; transition: width .4s ease;
  }}
  .progress-meta {{
    display: flex; justify-content: space-between; margin-top: 8px;
    font-size: 0.76rem; color: #8b8f99;
  }}

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


# ==================== PAGE PRINCIPALE ====================

async def handle_index(request: web.Request) -> web.Response:
    visitor_id, is_new = _get_or_create_visitor_id(request)

    content = f"""
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
    dlStatus.innerHTML = '';
    dlStatus.textContent = '❌ ' + (data.error || 'Échec du téléchargement.');
    dlStatus.className = 'status-line err';
    btn.disabled = false;
  }} else {{
    renderProgress(dlStatus, data.progress || {{status: 'pending'}});
    setTimeout(() => pollStatus(token, dlStatus, btn), 1500);
  }}
}}

function renderProgress(container, p) {{
  container.className = 'status-line';

  if (p.status === 'processing') {{
    container.innerHTML = `
      <div class="progress-box">
        <div class="progress-label"><span class="spinner"></span> Finalisation (fusion audio/vidéo)...</div>
      </div>`;
    return;
  }}

  if (p.status !== 'downloading' || p.percent === null || p.percent === undefined) {{
    container.innerHTML = `
      <div class="progress-box">
        <div class="progress-label"><span class="spinner"></span> Préparation du téléchargement...</div>
      </div>`;
    return;
  }}

  const pct = Math.max(0, Math.min(100, p.percent));
  const sizeInfo = (p.downloaded_mb != null && p.total_mb)
    ? `${{p.downloaded_mb}} Mo / ${{p.total_mb}} Mo`
    : (p.downloaded_mb != null ? `${{p.downloaded_mb}} Mo` : '');

  container.innerHTML = `
    <div class="progress-box">
      <div class="progress-label">⬇️ Téléchargement... <b>${{pct}}%</b></div>
      <div class="progress-track"><div class="progress-fill" style="width:${{pct}}%"></div></div>
      <div class="progress-meta">
        <span>${{sizeInfo}}</span>
        <span>${{p.speed ? '🚀 ' + p.speed : ''}}</span>
        <span>${{p.eta ? '⏱ ' + p.eta : ''}}</span>
      </div>
    </div>`;
}}
}}
</script>
"""
    response = web.Response(text=_render(content), content_type="text/html")
    if is_new:
        _set_visitor_cookie(response, visitor_id)
    return response


async def handle_app(request: web.Request) -> web.Response:
    # Ancienne URL séparée conservée en redirection simple (page unique désormais)
    raise web.HTTPFound("/")


# ==================== TÉLÉCHARGEMENT ====================

async def handle_api_preview(request: web.Request) -> web.Response:
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


async def _process_web_download(token: str, url: str, platform: str, quality: str, visitor_id: str):
    """Tâche de fond : télécharge la vidéo puis met à jour le lien correspondant"""
    try:
        # Pas d'identité Telegram ici : on utilise un identifiant technique
        # neutre pour le nom de fichier temporaire (pas de compteurs/limites).
        file_path = await downloader.download_video(
            url, platform, quality, f"web_{token[:8]}", progress_key=token
        )

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
        await db.log_download(visitor_id, platform, url, quality, True)

    except Exception as e:
        logger.exception(f"Échec téléchargement web (token={token})")
        await db.update_download_link(token, status="error", error=str(e)[:200])
    finally:
        download_progress.pop(token, None)


async def handle_api_download(request: web.Request) -> web.Response:
    visitor_id, is_new = _get_or_create_visitor_id(request)

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

    token = secrets.token_urlsafe(24)
    await db.create_download_link(token, visitor_id, DOWNLOAD_LINK_EXPIRY, status="pending")

    task = asyncio.create_task(_process_web_download(token, url, platform, quality, visitor_id))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    response = web.json_response({"token": token}, status=202)
    if is_new:
        _set_visitor_cookie(response, visitor_id)
    return response


async def handle_api_status(request: web.Request) -> web.Response:
    visitor_id, _ = _get_or_create_visitor_id(request)

    token = request.match_info["token"]
    link = await db.get_download_link(token)

    if not link or link["user_id"] != visitor_id:
        return web.json_response({"error": "not_found"}, status=404)

    if link["status"] == "ready":
        return web.json_response({"status": "ready", "download_url": f"{PUBLIC_BASE_URL}/dl/{token}"})
    if link["status"] == "error":
        return web.json_response({"status": "error", "error": link.get("error")})

    progress = download_progress.get(token) or {"status": "pending"}
    return web.json_response({"status": "pending", "progress": progress})


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
    app.router.add_post("/api/preview", handle_api_preview)
    app.router.add_post("/api/download", handle_api_download)
    app.router.add_get("/api/status/{token}", handle_api_status)
    app.router.add_get("/dl/{token}", handle_download_file)
