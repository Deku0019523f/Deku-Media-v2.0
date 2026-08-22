# -*- coding: utf-8 -*-
"""
Handler pour les statistiques utilisateur
"""
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from utils.user_manager import user_manager
from utils.database import db
from config import NORMAL_YOUTUBE_DAILY_LIMIT, NORMAL_OTHER_DAILY_LIMIT
from datetime import datetime
import importlib

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche les statistiques de l'utilisateur"""
    user_id = update.effective_user.id
    user_data = await user_manager.get_user(user_id)
    lang = user_data.get("lang", "fr")
    locale = importlib.import_module(f"locales.{lang}")
    
    # Récupérer les stats de la base
    db_stats = await db.get_user_stats(user_id)
    
    # Statut Premium
    status = "⭐️ Premium" if user_data.get("premium") else "👤 Normal"
    
    premium_info = ""
    if user_data.get("premium"):
        expire_date = datetime.fromisoformat(user_data['premium_expire']).strftime("%d/%m/%Y")
        premium_info = f"📅 Expire le : {expire_date}\n"
    
    # Limites
    yt_today = user_data.get("downloads_youtube_today", 0)
    other_today = user_data.get("downloads_other_today", 0)
    
    yt_limit = "∞" if user_data.get("premium") else NORMAL_YOUTUBE_DAILY_LIMIT
    other_limit = "∞" if user_data.get("premium") else NORMAL_OTHER_DAILY_LIMIT
    
    # Points et invités
    points = user_data.get("points", 0)
    invited = len(user_data.get("invited_users", []))
    
    # Total téléchargements
    total_downloads = db_stats.get("total_downloads", 0)
    
    await update.message.reply_text(
        locale.get_text(
            "stats_user",
            user_id=user_id,
            status=status,
            premium_info=premium_info,
            yt_today=yt_today,
            yt_limit=yt_limit,
            other_today=other_today,
            other_limit=other_limit,
            total=total_downloads,
            points=points,
            invited=invited
        ),
        parse_mode=ParseMode.MARKDOWN
    )
