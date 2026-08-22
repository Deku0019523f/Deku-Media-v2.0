# -*- coding: utf-8 -*-
"""
Handler pour l'abonnement Premium
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from utils.user_manager import user_manager
from utils.database import db
from utils.atelier_client import atelier_client, AtelierAPIError
from utils.premium_payments import grant_premium_if_paid
from config import ADMIN_IDS, PREMIUM_PRICE_XOF, PREMIUM_DURATION_DAYS
from datetime import datetime
import importlib
import logging

logger = logging.getLogger(__name__)

async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche les informations Premium"""
    user_id = update.effective_user.id
    user_data = await user_manager.get_user(user_id)
    lang = user_data.get("lang", "fr")
    locale = importlib.import_module(f"locales.{lang}")
    
    # Vérifier si déjà premium
    if user_data.get("premium"):
        expire_date = datetime.fromisoformat(user_data['premium_expire']).strftime("%d/%m/%Y")
        await update.message.reply_text(
            locale.get_text("premium_active", date=expire_date),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Afficher les informations Premium
    keyboard = [
        [InlineKeyboardButton(
            locale.get_text("premium_button"),
            callback_data="premium_confirm"
        )]
    ]
    
    await update.message.reply_text(
        locale.get_text("premium_info"),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def premium_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Génère un paiement automatique (Mobile Money / carte) via l'API Atelier"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    tg_user = update.effective_user
    
    user_data = await user_manager.get_user(user_id)
    lang = user_data.get("lang", "fr")
    locale = importlib.import_module(f"locales.{lang}")
    
    customer_name = tg_user.full_name or tg_user.username or str(user_id)
    
    try:
        payment = await atelier_client.create_payment(
            amount=PREMIUM_PRICE_XOF,
            description=f"Abonnement Premium ({PREMIUM_DURATION_DAYS} jours)",
            customer_name=customer_name,
            metadata={"telegram_user_id": str(user_id), "type": "premium_subscription"}
        )
    except AtelierAPIError as e:
        logger.error(
            f"Échec création paiement Atelier (user_id={user_id}) — "
            f"code={e.code} http_status={e.http_status} message={e}"
        )
        await query.edit_message_text(
            locale.get_text("premium_payment_error"),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    reference = payment["reference"]
    checkout_url = payment["checkout_url"]
    
    await db.create_atelier_payment(reference, user_id, PREMIUM_PRICE_XOF)
    
    keyboard = [
        [InlineKeyboardButton(locale.get_text("premium_pay_button"), url=checkout_url)],
        [InlineKeyboardButton(locale.get_text("premium_check_button"), callback_data=f"premium_check_{reference}")]
    ]
    
    await query.edit_message_text(
        locale.get_text("premium_checkout_created"),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def premium_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vérifie manuellement le statut d'un paiement (filet de sécurité si le webhook n'arrive pas)"""
    query = update.callback_query
    
    user_id = update.effective_user.id
    user_data = await user_manager.get_user(user_id)
    lang = user_data.get("lang", "fr")
    locale = importlib.import_module(f"locales.{lang}")
    
    reference = query.data[len("premium_check_"):]
    result = await grant_premium_if_paid(reference, context.bot)
    
    if result in ("paid", "already_processed"):
        await query.answer()
        await query.edit_message_text(
            locale.get_text("premium_activated"),
            parse_mode=ParseMode.MARKDOWN
        )
    elif result == "failed":
        await query.answer()
        await query.edit_message_text(
            locale.get_text("premium_payment_error"),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        # "pending" ou "not_found" : on laisse le message/boutons tels quels
        await query.answer(locale.get_text("premium_still_pending"), show_alert=True)

async def admin_validate_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Validation d'un paiement par l'admin"""
    query = update.callback_query
    await query.answer("✅ Paiement validé")
    
    admin_id = update.effective_user.id
    if admin_id not in ADMIN_IDS:
        return
    
    # Extraire les données
    parts = query.data.split("_")
    payment_id = int(parts[2])
    user_id = int(parts[3])
    
    # Activer le Premium
    from datetime import timedelta
    from config import PREMIUM_DURATION_DAYS
    
    expire_date = (datetime.now() + timedelta(days=PREMIUM_DURATION_DAYS)).isoformat()
    
    await user_manager.set_premium(user_id, PREMIUM_DURATION_DAYS)
    await db.set_premium(user_id, expire_date)
    await db.validate_payment(payment_id, admin_id, user_id)
    
    # Notifier l'utilisateur
    user_data = await user_manager.get_user(user_id)
    lang = user_data.get("lang", "fr")
    locale = importlib.import_module(f"locales.{lang}")
    
    try:
        await context.bot.send_message(
            user_id,
            locale.get_text("premium_activated"),
            parse_mode=ParseMode.MARKDOWN
        )
    except:
        pass
    
    await query.edit_message_text(
        f"✅ Paiement validé pour l'utilisateur {user_id}\n"
        f"Premium activé jusqu'au {datetime.fromisoformat(expire_date).strftime('%d/%m/%Y')}"
    )

async def admin_reject_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rejet d'un paiement par l'admin"""
    query = update.callback_query
    await query.answer("❌ Paiement rejeté")
    
    admin_id = update.effective_user.id
    if admin_id not in ADMIN_IDS:
        return
    
    # Extraire les données
    parts = query.data.split("_")
    payment_id = int(parts[2])
    user_id = int(parts[3])
    
    await db.reject_payment(payment_id)
    
    # Notifier l'utilisateur
    try:
        await context.bot.send_message(
            user_id,
            "❌ Votre demande de Premium a été rejetée. Veuillez contacter le support."
        )
    except:
        pass
    
    await query.edit_message_text(
        f"❌ Paiement rejeté pour l'utilisateur {user_id}"
    )
