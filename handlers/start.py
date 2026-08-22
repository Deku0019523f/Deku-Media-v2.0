# -*- coding: utf-8 -*-
"""
Handler pour la commande /start et menu principal
"""
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from utils.user_manager import user_manager
from utils.database import db
from config import OWNER_USERNAME, ADMIN_IDS
import importlib

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /start avec gestion du parrainage"""
    user = update.effective_user
    user_id = user.id
    
    # Vérifier si banni
    if await db.is_banned(user_id):
        await update.message.reply_text("🚫 Vous êtes banni de ce bot.")
        return
    
    # Créer/récupérer l'utilisateur
    user_data = await user_manager.get_user(user_id)
    user_data["username"] = user.username
    await user_manager.save_user(user_id, user_data)
    
    # Ajouter dans la base SQLite
    await db.add_user(user_id, user.username, user.first_name, user.last_name)
    await db.update_user_activity(user_id)
    
    # Gestion du parrainage
    if context.args and context.args[0].startswith("ref_"):
        referrer_id = int(context.args[0].replace("ref_", ""))
        if referrer_id != user_id:
            # Enregistrer le parrainage
            if await user_manager.set_referrer(user_id, referrer_id):
                await db.add_referral(referrer_id, user_id)
                
                # Donner des points au parrain
                referrer_data = await user_manager.get_user(referrer_id)
                points = 5 if user_data.get("premium") else 2
                await user_manager.add_points(referrer_id, points)
                
                # Notifier le parrain
                try:
                    from config import REFERRAL_POINTS_PREMIUM, REFERRAL_POINTS_NORMAL
                    await context.bot.send_message(
                        referrer_id,
                        f"🎉 Nouveau filleul ! +{points} points"
                    )
                except:
                    pass
    
    # Charger les traductions
    lang = user_data.get("lang", "fr")
    locale = importlib.import_module(f"locales.{lang}")
    
    # Message de bienvenue
    welcome_text = locale.get_text("welcome", owner=OWNER_USERNAME)
    
    # Créer le menu principal
    keyboard = get_main_keyboard(locale, user_id in ADMIN_IDS)
    
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )

def get_main_keyboard(locale, is_admin: bool = False):
    """Génère le clavier principal"""
    keyboard = [
        [
            KeyboardButton(locale.get_text("menu_support")),
            KeyboardButton(locale.get_text("menu_invite"))
        ],
        [
            KeyboardButton(locale.get_text("menu_premium")),
            KeyboardButton(locale.get_text("menu_stats"))
        ],
        [
            KeyboardButton(locale.get_text("menu_language")),
            KeyboardButton(locale.get_text("menu_donate"))
        ]
    ]
    
    if is_admin:
        keyboard.append([KeyboardButton("🛡 Admin")])
    
    keyboard.append([KeyboardButton(locale.get_text("menu_hide"))])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def hide_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Masque le clavier"""
    from telegram import ReplyKeyboardRemove
    await update.message.reply_text(
        "✅ Clavier masqué. Utilisez /start pour le réafficher.",
        reply_markup=ReplyKeyboardRemove()
    )
