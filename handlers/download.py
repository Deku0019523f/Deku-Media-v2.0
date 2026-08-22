# -*- coding: utf-8 -*-
"""
Handler pour le téléchargement de vidéos - VERSION FINALE AVEC API TIKTOK
Support: YouTube, TikTok, Instagram, Facebook, Pinterest, Twitter/X
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from utils.platform_detector import platform_detector
from utils.user_manager import user_manager
from utils.downloader import downloader
from utils.limits import limit_checker
from utils.database import db
from config import DELETE_AFTER_SEND, SUPPORT_CHANNEL, ADMIN_IDS
import importlib
import asyncio
import os

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Traite les URLs envoyées par l'utilisateur"""
    user_id = update.effective_user.id
    url = update.message.text.strip()
    
    # Vérifier si banni
    if await db.is_banned(user_id):
        await update.message.reply_text("🚫 Vous êtes banni de ce bot.")
        return
    
    # Récupérer données utilisateur
    user_data = await user_manager.get_user(user_id)
    lang = user_data.get("lang", "fr")
    locale = importlib.import_module(f"locales.{lang}")
    
    # Détecter la plateforme
    is_supported, platform = platform_detector.is_supported(url)
    
    if not is_supported:
        await update.message.reply_text(
            locale.get_text("error_platform_not_supported")
        )
        return
    
    # Vérifier les limites
    is_youtube = platform == "youtube"
    can_download, error_msg = await limit_checker.check_limits(user_data, is_youtube)
    
    if not can_download:
        await update.message.reply_text(error_msg)
        return
    
    # Message de traitement
    processing_msg = await update.message.reply_text(
        locale.get_text("download_processing")
    )
    
    # Extraire les informations vidéo
    try:
        video_info = await downloader.get_video_info(url, platform)
    except Exception as e:
        error_text = locale.get_text("download_error", error=str(e)[:100])
        await processing_msg.edit_text(error_text)
        return
    
    if not video_info:
        await processing_msg.edit_text(
            locale.get_text("error_invalid_url")
        )
        return
    
    # Formater la durée (CORRIGÉ)
    duration = video_info.get("duration", 0)
    if duration:
        try:
            duration = int(float(duration))
            minutes = duration // 60
            seconds = duration % 60
            duration_str = f"{minutes}:{seconds:02d}"
        except (ValueError, TypeError):
            duration_str = "Inconnue"
    else:
        duration_str = "Inconnue"
    
    # Formater les vues (CORRIGÉ)
    views = video_info.get("view_count", 0)
    if views:
        try:
            views = int(views)
            if views >= 1_000_000:
                views_str = f"{views / 1_000_000:.1f}M"
            elif views >= 1_000:
                views_str = f"{views / 1_000:.1f}K"
            else:
                views_str = str(views)
        except (ValueError, TypeError):
            views_str = "Inconnues"
    else:
        views_str = "Inconnues"
    
    # Créer l'aperçu
    preview_text = locale.get_text(
        "download_preview",
        title=video_info['title'][:100],
        duration=duration_str,
        uploader=video_info['uploader'][:50],
        platform=platform.capitalize(),
        views=views_str
    )
    
    # Envoyer la thumbnail si disponible
    thumbnail_sent = False
    if video_info.get('thumbnail'):
        try:
            await update.message.reply_photo(
                photo=video_info['thumbnail'],
                caption=preview_text,
                parse_mode=ParseMode.MARKDOWN
            )
            await processing_msg.delete()
            thumbnail_sent = True
        except Exception as e:
            print(f"Erreur envoi thumbnail: {e}")
    
    if not thumbnail_sent:
        await processing_msg.edit_text(preview_text, parse_mode=ParseMode.MARKDOWN)
    
    # Sauvegarder le contexte pour le callback
    context.user_data['pending_download'] = {
        'url': url,
        'platform': platform,
        'video_info': video_info,
        'is_youtube': is_youtube
    }
    
    # Boutons de qualité pour YouTube
    if platform == "youtube":
        formats = video_info.get('formats', [])
        filtered_formats = limit_checker.filter_qualities(formats, user_data)
        
        if not filtered_formats:
            filtered_formats = [{'quality': 'best', 'label': 'Meilleure qualité'}]
        
        keyboard = []
        for fmt in filtered_formats:
            keyboard.append([
                InlineKeyboardButton(
                    fmt['label'],
                    callback_data=f"dl_quality_{fmt['quality']}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(
                locale.get_text("download_button_cancel"),
                callback_data="dl_cancel"
            )
        ])
        
        await update.message.reply_text(
            locale.get_text("download_select_quality"),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        # Autres plateformes: téléchargement direct avec confirmation
        keyboard = [
            [InlineKeyboardButton(
                locale.get_text("download_button_confirm"),
                callback_data="dl_quality_best"
            )],
            [InlineKeyboardButton(
                locale.get_text("download_button_cancel"),
                callback_data="dl_cancel"
            )]
        ]
        
        await update.message.reply_text(
            "✅ Prêt à télécharger !",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback pour les boutons de téléchargement"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    # Récupérer données utilisateur
    user_data = await user_manager.get_user(user_id)
    lang = user_data.get("lang", "fr")
    locale = importlib.import_module(f"locales.{lang}")
    
    # Annulation
    if data == "dl_cancel":
        await query.edit_message_text(locale.get_text("download_cancelled"))
        context.user_data.pop('pending_download', None)
        return
    
    # Téléchargement
    if data.startswith("dl_quality_"):
        quality = data.replace("dl_quality_", "")
        pending = context.user_data.get('pending_download')
        
        if not pending:
            await query.edit_message_text("❌ Session expirée. Renvoyez le lien.")
            return
        
        url = pending['url']
        platform = pending['platform']
        is_youtube = pending.get('is_youtube', False)
        
        # Vérifier à nouveau les limites
        can_download, error_msg = await limit_checker.check_limits(user_data, is_youtube)
        
        if not can_download:
            await query.edit_message_text(error_msg)
            context.user_data.pop('pending_download', None)
            return
        
        # Message de téléchargement
        await query.edit_message_text(locale.get_text("download_starting"))
        
        # Télécharger
        file_path = None
        try:
            file_path = await downloader.download_video(url, platform, quality, user_id)
            
            if not file_path or not file_path.exists():
                await query.edit_message_text(
                    locale.get_text("download_error", error="Fichier introuvable")
                )
                await db.log_download(user_id, platform, url, quality, False, "File not found")
                return
            
            # Vérifier la taille du fichier
            file_size_bytes = file_path.stat().st_size
            file_size_mb = file_size_bytes / (1024 * 1024)
            
            if file_size_mb > 2000:  # Limite Telegram: 2 Go
                await query.edit_message_text(locale.get_text("download_too_large"))
                file_path.unlink()
                await db.log_download(user_id, platform, url, quality, False, "File too large")
                context.user_data.pop('pending_download', None)
                return
            
            # Afficher la taille
            if file_size_mb >= 1:
                size_text = f"{file_size_mb:.1f} MB"
            else:
                size_text = f"{file_size_bytes / 1024:.1f} KB"
            
            # Déterminer le type d'envoi
            file_extension = file_path.suffix.lower()
            
            # Envoyer le fichier
            caption_text = (
                f"✅ {locale.get_text('download_success')}\n"
                f"📦 Taille: {size_text}\n"
                f"📺 Plateforme: {platform.capitalize()}"
            )
            
            # Envoyer comme vidéo ou document selon la taille et l'extension
            if file_size_mb <= 50 and file_extension in ['.mp4', '.mkv', '.avi', '.mov', '.webm']:
                try:
                    with open(file_path, 'rb') as video_file:
                        await context.bot.send_video(
                            chat_id=user_id,
                            video=video_file,
                            caption=caption_text,
                            supports_streaming=True,
                            read_timeout=300,
                            write_timeout=300,
                            connect_timeout=60
                        )
                except Exception as e:
                    print(f"Erreur envoi vidéo, fallback sur document: {e}")
                    with open(file_path, 'rb') as doc_file:
                        await context.bot.send_document(
                            chat_id=user_id,
                            document=doc_file,
                            caption=caption_text,
                            filename=file_path.name,
                            read_timeout=300,
                            write_timeout=300,
                            connect_timeout=60
                        )
            else:
                with open(file_path, 'rb') as doc_file:
                    await context.bot.send_document(
                        chat_id=user_id,
                        document=doc_file,
                        caption=caption_text,
                        filename=file_path.name,
                        read_timeout=300,
                        write_timeout=300,
                        connect_timeout=60
                    )
            
            # Incrémenter les compteurs
            await user_manager.increment_download(user_id, is_youtube)
            
            # Logger le téléchargement réussi
            await db.log_download(user_id, platform, url, quality, True)
            
            # Supprimer le message de progression
            try:
                await query.message.delete()
            except:
                pass
            
            # Planifier la suppression du fichier
            asyncio.create_task(downloader.cleanup_file(file_path, DELETE_AFTER_SEND))
            
        except Exception as e:
            error_message = str(e)
            print(f"Erreur téléchargement: {error_message}")
            
            # Message d'erreur personnalisé
            if "timeout" in error_message.lower():
                error_text = "⏱ Délai d'attente dépassé. Le fichier est peut-être trop volumineux."
            elif "network" in error_message.lower():
                error_text = "🌐 Erreur réseau. Vérifiez votre connexion."
            elif "not found" in error_message.lower():
                error_text = "❌ Vidéo introuvable ou indisponible."
            elif "private" in error_message.lower() or "unavailable" in error_message.lower():
                error_text = "🔒 Contenu privé ou indisponible."
            elif "sign in" in error_message.lower() or "login" in error_message.lower():
                error_text = "🔐 Connexion requise. Les cookies ne sont peut-être pas valides."
            else:
                error_text = locale.get_text("download_error", error=error_message[:100])
            
            await query.edit_message_text(error_text)
            
            # Logger l'erreur
            await db.log_download(user_id, platform, url, quality, False, error_message)
            
            # Nettoyer le fichier en cas d'erreur
            if file_path and file_path.exists():
                try:
                    file_path.unlink()
                except:
                    pass
        
        finally:
            # Nettoyer le contexte
            context.user_data.pop('pending_download', None)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Gère tous les messages texte (URLs ou boutons menu)
    """
    text = update.message.text
    user_id = update.effective_user.id
    
    # Vérifier si c'est une URL
    if text.startswith("http://") or text.startswith("https://") or "youtu.be" in text or "tiktok.com" in text:
        await handle_url(update, context)
        return
    
    # Sinon, c'est probablement un bouton du menu
    user_data = await user_manager.get_user(user_id)
    lang = user_data.get("lang", "fr")
    
    locale = importlib.import_module(f"locales.{lang}")
    
    # Gérer les boutons du menu
    if text == locale.get_text("menu_support") or text == "🛟 Soutien":
        await update.message.reply_text(
            f"🛟 **Besoin d'aide ?**\n\n"
            f"Rejoignez notre canal de support :\n{SUPPORT_CHANNEL}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif text == locale.get_text("menu_invite") or text == "👯 Inviter un ami":
        from handlers.referral import referral_command
        await referral_command(update, context)
    
    elif text == locale.get_text("menu_premium") or text == "⭐️ Abonnement":
        from handlers.premium import premium_command
        await premium_command(update, context)
    
    elif text == locale.get_text("menu_language") or text == "🌍 Changer de langue":
        from handlers.language import language_command
        await language_command(update, context)
    
    elif text == locale.get_text("menu_donate") or text == "❤️ Faire un don":
        from handlers.payment import donate_command
        await donate_command(update, context)
    
    elif text == locale.get_text("menu_stats") or text == "📊 Mes statistiques":
        from handlers.stats import stats_command
        await stats_command(update, context)
    
    elif text == locale.get_text("menu_hide") or text == "❌ Masquer":
        from handlers.start import hide_keyboard
        await hide_keyboard(update, context)
    
    elif text == "🛡 Admin" and user_id in ADMIN_IDS:
        from handlers.admin import admin_command
        await admin_command(update, context)
    
    else:
        # Message non reconnu
        if any(keyword in text.lower() for keyword in ['tiktok', 'youtube', 'facebook', 'instagram', 'twitter', 'pinterest']):
            await handle_url(update, context)
        else:
            await update.message.reply_text(
                "❓ Commande non reconnue.\n\n"
                "💡 Envoyez un lien pour télécharger une vidéo.\n"
                "📋 Utilisez /start pour voir le menu.",
                parse_mode=ParseMode.MARKDOWN
            )
