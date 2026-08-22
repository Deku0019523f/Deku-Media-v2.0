# -*- coding: utf-8 -*-
"""
Handler pour la gestion des langues
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from utils.user_manager import user_manager
import importlib

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche le sélecteur de langue"""
    user_id = update.effective_user.id
    user_data = await user_manager.get_user(user_id)
    lang = user_data.get("lang", "fr")
    locale = importlib.import_module(f"locales.{lang}")
    
    keyboard = [
        [InlineKeyboardButton("🇫🇷 Français", callback_data="lang_fr")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
    ]
    
    await update.message.reply_text(
        locale.get_text("language_select"),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback pour changer la langue"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    new_lang = query.data.replace("lang_", "")
    
    await user_manager.set_language(user_id, new_lang)
    
    locale = importlib.import_module(f"locales.{new_lang}")
    
    await query.edit_message_text(
        locale.get_text("language_changed")
    )
