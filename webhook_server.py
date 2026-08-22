# -*- coding: utf-8 -*-
"""
Serveur HTTP (aiohttp) qui reçoit les webhooks de paiement de l'API Atelier
et déclenche l'activation automatique du Premium.

Tourne dans le même processus/event loop que le bot Telegram (voir bot.py).
À exposer publiquement en HTTPS via un reverse proxy (nginx/caddy) sur le
VPS, vers 127.0.0.1:WEBHOOK_SERVER_PORT — c'est cette URL publique qu'il
faut renseigner dans config.ATELIER_CALLBACK_URL.
"""
import logging
from aiohttp import web
from utils.premium_payments import grant_premium_if_paid

logger = logging.getLogger(__name__)


async def handle_atelier_webhook(request: web.Request) -> web.Response:
    try:
        payload = await request.json()
    except Exception:
        return web.json_response({"error": "invalid_json"}, status=400)

    reference = (payload.get("data") or {}).get("reference")
    if not reference:
        return web.json_response({"error": "missing_reference"}, status=400)

    bot = request.app["bot"]

    try:
        result = await grant_premium_if_paid(reference, bot)
    except Exception:
        logger.exception(f"Erreur en traitant le webhook Atelier (reference={reference})")
        return web.json_response({"error": "processing_error"}, status=500)

    logger.info(f"📩 Webhook Atelier traité — reference={reference} résultat={result}")
    return web.json_response({"ok": True, "result": result})


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


def create_webhook_app(bot) -> web.Application:
    app = web.Application()
    app["bot"] = bot
    app.router.add_post("/webhooks/atelier", handle_atelier_webhook)
    app.router.add_get("/health", handle_health)
    return app


async def run_webhook_server(bot, host: str, port: int) -> web.AppRunner:
    """Démarre le serveur webhook et retourne le runner (à fermer via runner.cleanup())"""
    app = create_webhook_app(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info(f"🌐 Serveur webhook de paiement démarré sur {host}:{port}")
    return runner
