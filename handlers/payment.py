# -*- coding: utf-8 -*-
"""
Handler pour les paiements avec Telegram Stars
"""
from telegram import Update, LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from utils.user_manager import user_manager
from config import DONATION_STARS
import importlib

async def donate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche les options de don"""
    user_id = update.effective_user.id
    user_data = await user_manager.get_user(user_id)
    lang = user_data.get("lang", "fr")
    locale = importlib.import_module(f"locales.{lang}")
    
    keyboard = []
    for amount in DONATION_STARS:
        keyboard.append([
            InlineKeyboardButton(
                locale.get_text(f"donate_button_{amount}"),
                callback_data=f"donate_{amount}"
            )
        ])
    
    await update.message.reply_text(
        locale.get_text("donate_info"),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def donate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback pour initier un don"""
    query = update.callback_query
    await query.answer()
    
    # Extraire le montant
    amount = int(query.data.replace("donate_", ""))
    
    # Créer la facture Telegram Stars
    title = f"Don de {amount} Stars"
    description = "Merci de soutenir le développement du bot !"
    payload = f"donation_{amount}_{update.effective_user.id}"
    
    prices = [LabeledPrice(label=f"{amount} Stars", amount=amount)]
    
    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title=title,
        description=description,
        payload=payload,
        provider_token="",  # VIDE pour Telegram Stars
        currency="XTR",  # Currency pour Telegram Stars
        prices=prices
    )
    
    await query.message.delete()

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Valide avant le paiement"""
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère les paiements réussis"""
    payment = update.message.successful_payment
    amount = payment.total_amount
    
    user_id = update.effective_user.id
    user_data = await user_manager.get_user(user_id)
    lang = user_data.get("lang", "fr")
    locale = importlib.import_module(f"locales.{lang}")
    
    # Message de remerciement
    await update.message.reply_text(
        locale.get_text("donate_success", amount=amount),
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Logger le paiement
    from utils.database import db
    await db.execute(
        "INSERT INTO payments (user_id, amount, currency, payment_type) VALUES (?, ?, ?, ?)",
        (user_id, amount, "XTR", "donation")
    )
