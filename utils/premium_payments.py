# -*- coding: utf-8 -*-
"""
Logique partagée : vérifier un paiement Atelier et créditer le Premium.
Utilisée à la fois par le serveur webhook (webhook_server.py) et par le
bouton "Vérifier mon paiement" (handlers/premium.py).
"""
import importlib
import logging
from datetime import datetime, timedelta
from telegram.constants import ParseMode
from utils.database import db
from utils.user_manager import user_manager
from utils.atelier_client import atelier_client, AtelierAPIError
from config import PREMIUM_DURATION_DAYS, ADMIN_IDS

logger = logging.getLogger(__name__)


async def grant_premium_if_paid(reference: str, bot) -> str:
    """
    Revérifie le statut réel du paiement auprès de l'API Atelier (jamais via
    le seul contenu du webhook, cf. doc Atelier : "les webhooks ne sont pas
    encore signés") puis, si payé, active le Premium pour l'utilisateur.

    Idempotent : peut être appelée plusieurs fois pour la même référence
    (webhook reçu deux fois + clic manuel) sans créditer deux fois.

    Retourne l'un de : "paid", "already_processed", "pending", "failed", "not_found"
    """
    record = await db.get_atelier_payment(reference)
    if not record:
        return "not_found"

    if record["status"] == "paid":
        return "already_processed"

    try:
        status_data = await atelier_client.get_payment_status(reference)
    except AtelierAPIError:
        logger.exception(f"Vérification du paiement Atelier échouée (reference={reference})")
        return "pending"

    remote_status = status_data.get("status")
    if remote_status != "paid":
        return "pending" if remote_status == "pending" else "failed"

    user_id = record["user_id"]

    # Verrou d'idempotence : seul l'appel qui bascule réellement pending -> paid
    # a le droit de créditer le Premium.
    did_transition = await db.mark_atelier_payment_paid(reference)
    if not did_transition:
        return "already_processed"

    expire_date = (datetime.now() + timedelta(days=PREMIUM_DURATION_DAYS)).isoformat()
    await user_manager.set_premium(user_id, PREMIUM_DURATION_DAYS)
    await db.set_premium(user_id, expire_date)
    await db.add_payment_record(
        user_id, status_data.get("amount", 0), status_data.get("currency", "XOF"), "atelier_auto"
    )

    user_data = await user_manager.get_user(user_id)
    lang = user_data.get("lang", "fr")
    locale = importlib.import_module(f"locales.{lang}")

    try:
        await bot.send_message(user_id, locale.get_text("premium_activated"), parse_mode=ParseMode.MARKDOWN)
    except Exception:
        logger.warning(f"Impossible de notifier l'utilisateur {user_id} de son Premium")

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"✅ **Paiement Premium automatique confirmé**\n\n"
                f"👤 User ID: `{user_id}`\n"
                f"💰 Montant: {status_data.get('amount')} {status_data.get('currency', 'XOF')}\n"
                f"🆔 Référence: `{reference}`",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            pass

    return "paid"
