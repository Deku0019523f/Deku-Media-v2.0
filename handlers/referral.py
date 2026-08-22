# -*- coding: utf-8 -*-
"""
Handler pour le système de parrainage
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from utils.user_manager import user_manager
from config import POINTS_FOR_1_WEEK, POINTS_FOR_1_MONTH
import importlib

async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche les informations de parrainage"""
    user_id = update.effective_user.id
    user_data = await user_manager.get_user(user_id)
    lang = user_data.get("lang", "fr")
    locale = importlib.import_module(f"locales.{lang}")
    
    # Générer le lien de parrainage
    bot_username = (await context.bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    
    points = user_data.get("points", 0)
    invited = len(user_data.get("invited_users", []))
    
    # Créer les boutons
    keyboard = [
        [InlineKeyboardButton(
            locale.get_text("referral_button"),
            url=f"https://t.me/share/url?url={referral_link}&text=Rejoins-moi sur ce bot de téléchargement !"
        )]
    ]
    
    # Boutons d'échange de points
    if points >= POINTS_FOR_1_WEEK:
        keyboard.append([
            InlineKeyboardButton(
                f"💎 1 semaine ({POINTS_FOR_1_WEEK} pts)",
                callback_data="redeem_7"
            )
        ])
    
    if points >= POINTS_FOR_1_MONTH:
        keyboard.append([
            InlineKeyboardButton(
                f"💎 1 mois ({POINTS_FOR_1_MONTH} pts)",
                callback_data="redeem_30"
            )
        ])
    
    await update.message.reply_text(
        locale.get_text(
            "referral_info",
            points=points,
            invited=invited,
            link=referral_link
        ),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def redeem_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback pour échanger les points"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_data = await user_manager.get_user(user_id)
    lang = user_data.get("lang", "fr")
    locale = importlib.import_module(f"locales.{lang}")
    
    # Extraire les jours
    days = int(query.data.replace("redeem_", ""))
    points_needed = POINTS_FOR_1_WEEK if days == 7 else POINTS_FOR_1_MONTH
    
    current_points = user_data.get("points", 0)
    
    if current_points < points_needed:
        await query.edit_message_text(
            locale.get_text("referral_not_enough", points=current_points)
        )
        return
    
    # Échanger les points
    success = await user_manager.redeem_points(user_id, points_needed, days)
    
    if success:
        remaining_points = current_points - points_needed
        await query.edit_message_text(
            locale.get_text("referral_success", days=days, points=remaining_points),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await query.edit_message_text(
            locale.get_text("referral_not_enough", points=current_points)
        )
