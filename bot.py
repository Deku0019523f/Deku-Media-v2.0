#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOT TELEGRAM DE TÉLÉCHARGEMENT MULTIPLATEFORMES
Développé par @Darkdeku225

Version: 1.0.0
Python: 3.10+
"""

import asyncio
import logging
import sys
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
    ConversationHandler,
    filters
)

# Imports locaux
from config import BOT_TOKEN, ADMIN_IDS, LOG_LEVEL, LOG_FILE, WEBHOOK_SERVER_HOST, WEBHOOK_SERVER_PORT
from utils.database import db
from utils.scheduler import bot_scheduler
from webhook_server import run_webhook_server

# Handlers - Start
from handlers.start import start_command, hide_keyboard

# Handlers - Download
from handlers.download import handle_message, download_callback

# Handlers - Premium
from handlers.premium import (
    premium_command,
    premium_confirm_callback,
    premium_check_callback,
    admin_validate_payment,
    admin_reject_payment
)

# Handlers - Referral
from handlers.referral import referral_command, redeem_callback

# Handlers - Payment
from handlers.payment import (
    donate_command,
    donate_callback,
    precheckout_callback,
    successful_payment_callback
)

# Handlers - Language
from handlers.language import language_command, language_callback

# Handlers - Stats
from handlers.stats import stats_command

# Handlers - Admin
from handlers.admin import (
    admin_command,
    admin_menu_callback,
    admin_stats_callback,
    admin_payments_callback,
    admin_users_callback,
    admin_settings_callback,
    admin_broadcast_callback,
    admin_receive_broadcast,
    admin_cancel,
    admin_referrals_callback,
    admin_logs_callback,
    admin_give_premium_callback,
    admin_ban_user_callback,
    admin_unban_user_callback,
    admin_reset_limits_callback,
    admin_toggle_platform,
    setpremium_command,
    ban_command,
    unban_command,
    resetlimits_command,
    BROADCAST_MESSAGE
)

# Configuration du logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, LOG_LEVEL),
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def post_init(application: Application):
    """Fonction appelée après l'initialisation de l'application"""
    logger.info("🔧 Initialisation de la base de données...")
    await db.init_database()
    logger.info("✅ Base de données initialisée")

async def error_handler(update: Update, context):
    """Gère les erreurs globales"""
    logger.error(f"Exception lors de la mise à jour: {context.error}", exc_info=context.error)
    
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ Une erreur s'est produite. Veuillez réessayer plus tard.\n"
                "Si le problème persiste, contactez le support."
            )
        except Exception as e:
            logger.error(f"Impossible d'envoyer le message d'erreur: {e}")

def setup_handlers(application: Application):
    """Configure tous les handlers du bot"""
    
    # ==================== COMMANDES ====================
    logger.info("📝 Enregistrement des commandes...")
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("premium", premium_command))
    application.add_handler(CommandHandler("referral", referral_command))
    application.add_handler(CommandHandler("invite", referral_command))
    application.add_handler(CommandHandler("parrainage", referral_command))
    application.add_handler(CommandHandler("language", language_command))
    application.add_handler(CommandHandler("lang", language_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("statistiques", stats_command))
    application.add_handler(CommandHandler("donate", donate_command))
    application.add_handler(CommandHandler("don", donate_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("setpremium", setpremium_command))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(CommandHandler("resetlimits", resetlimits_command))
    application.add_handler(CommandHandler("help", start_command))
    application.add_handler(CommandHandler("aide", start_command))
    
    # ==================== CONVERSATION ADMIN BROADCAST ====================
    logger.info("📢 Configuration du système de broadcast...")
    
    broadcast_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_broadcast_callback, pattern="^admin_broadcast$")
        ],
        states={
            BROADCAST_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_receive_broadcast)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", admin_cancel),
            CommandHandler("annuler", admin_cancel)
        ]
    )
    application.add_handler(broadcast_handler)
    
    # ==================== CALLBACKS - TÉLÉCHARGEMENT ====================
    logger.info("⬇️ Configuration des callbacks de téléchargement...")
    
    application.add_handler(CallbackQueryHandler(download_callback, pattern="^dl_"))
    
    # ==================== CALLBACKS - PREMIUM ====================
    logger.info("⭐️ Configuration des callbacks Premium...")
    
    application.add_handler(
        CallbackQueryHandler(premium_confirm_callback, pattern="^premium_confirm$")
    )
    application.add_handler(
        CallbackQueryHandler(premium_check_callback, pattern="^premium_check_")
    )
    application.add_handler(
        CallbackQueryHandler(admin_validate_payment, pattern="^admin_validate_")
    )
    application.add_handler(
        CallbackQueryHandler(admin_reject_payment, pattern="^admin_reject_")
    )
    
    # ==================== CALLBACKS - PARRAINAGE ====================
    logger.info("🎁 Configuration des callbacks de parrainage...")
    
    application.add_handler(CallbackQueryHandler(redeem_callback, pattern="^redeem_"))
    
    # ==================== CALLBACKS - PAIEMENTS ====================
    logger.info("💳 Configuration des callbacks de paiements...")
    
    application.add_handler(CallbackQueryHandler(donate_callback, pattern="^donate_"))
    
    # ==================== CALLBACKS - LANGUE ====================
    logger.info("🌍 Configuration des callbacks de langue...")
    
    application.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
    
    # ==================== CALLBACKS - ADMIN ====================
    logger.info("🛡 Configuration des callbacks admin...")
    
    application.add_handler(
        CallbackQueryHandler(admin_stats_callback, pattern="^admin_stats$")
    )
    application.add_handler(
        CallbackQueryHandler(admin_payments_callback, pattern="^admin_payments$")
    )
    application.add_handler(
        CallbackQueryHandler(admin_users_callback, pattern="^admin_users$")
    )
    application.add_handler(
        CallbackQueryHandler(admin_settings_callback, pattern="^admin_settings$")
    )
    application.add_handler(
        CallbackQueryHandler(admin_menu_callback, pattern="^admin_menu$")
    )
    application.add_handler(
        CallbackQueryHandler(admin_referrals_callback, pattern="^admin_referrals$")
    )
    application.add_handler(
        CallbackQueryHandler(admin_logs_callback, pattern="^admin_logs$")
    )
    application.add_handler(
        CallbackQueryHandler(admin_give_premium_callback, pattern="^admin_give_premium$")
    )
    application.add_handler(
        CallbackQueryHandler(admin_ban_user_callback, pattern="^admin_ban_user$")
    )
    application.add_handler(
        CallbackQueryHandler(admin_unban_user_callback, pattern="^admin_unban_user$")
    )
    application.add_handler(
        CallbackQueryHandler(admin_reset_limits_callback, pattern="^admin_reset_limits$")
    )
    application.add_handler(
        CallbackQueryHandler(admin_toggle_platform, pattern="^admin_toggle_")
    )
    
    # ==================== PAIEMENTS TELEGRAM STARS ====================
    logger.info("⭐️ Configuration des paiements Telegram Stars...")
    
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(
        MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback)
    )
    
    # ==================== MESSAGES TEXTE ====================
    logger.info("💬 Configuration du handler de messages...")
    
    # Handler principal pour tous les messages texte (URLs et boutons menu)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    
    # ==================== GESTIONNAIRE D'ERREURS ====================
    logger.info("⚠️ Configuration du gestionnaire d'erreurs...")
    
    application.add_error_handler(error_handler)
    
    logger.info("✅ Tous les handlers sont enregistrés")

def print_startup_banner():
    """Affiche la bannière de démarrage"""
    banner = """
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║     🤖 BOT TELEGRAM DE TÉLÉCHARGEMENT MULTIPLATEFORME   ║
║                                                          ║
║     📺 YouTube | TikTok | Instagram | Facebook          ║
║     📌 Pinterest | Twitter/X                            ║
║                                                          ║
║     ⭐️ Premium | 🎁 Parrainage | 💳 Paiements           ║
║                                                          ║
║     Développé par @Darkdeku225                          ║
║     Version 1.0.0                                        ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """
    print(banner)

def check_config():
    """Vérifie que la configuration est valide"""
    errors = []
    
    if not BOT_TOKEN or BOT_TOKEN == "VOTRE_TOKEN_ICI":
        errors.append("❌ BOT_TOKEN non configuré dans config.py")
    
    if not ADMIN_IDS or ADMIN_IDS == [123456789]:
        errors.append("⚠️  ADMIN_IDS non configuré (utilise la valeur par défaut)")
    
    # Vérifier l'existence des dossiers
    from config import COOKIES_DIR, USERS_DIR, DOWNLOADS_DIR, DATABASE_PATH
    
    if not COOKIES_DIR.exists():
        errors.append(f"⚠️  Dossier cookies/ manquant: {COOKIES_DIR}")
    
    if not USERS_DIR.exists():
        errors.append(f"⚠️  Dossier users/ manquant: {USERS_DIR}")
    
    if not DOWNLOADS_DIR.exists():
        errors.append(f"⚠️  Dossier downloads/ manquant: {DOWNLOADS_DIR}")
    
    # Vérifier les fichiers cookies
    from config import COOKIES_MAP
    
    missing_cookies = []
    for platform, cookie_path in COOKIES_MAP.items():
        if not cookie_path.exists():
            missing_cookies.append(f"   • {platform}: {cookie_path.name}")
    
    if missing_cookies:
        errors.append("⚠️  Fichiers cookies manquants:")
        errors.extend(missing_cookies)
    
    return errors

async def run_bot(application: Application):
    """Démarre le polling Telegram ET le serveur webhook de paiement, en parallèle,
    dans la même boucle asyncio, puis reste actif jusqu'à l'arrêt du processus."""
    async with application:
        # `async with application` n'appelle QUE initialize() : contrairement à
        # run_polling()/run_webhook(), il n'exécute PAS post_init tout seul.
        # On le fait explicitement ici, sinon db.init_database() n'est jamais
        # appelé et des tables comme "bans" ou "atelier_payments" n'existent
        # jamais dans la base au démarrage.
        if application.post_init:
            await application.post_init(application)

        await application.start()
        await application.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )

        webhook_runner = await run_webhook_server(
            application.bot, WEBHOOK_SERVER_HOST, WEBHOOK_SERVER_PORT
        )

        # Démarré ici (et non dans main()) pour que l'AsyncIOScheduler se lie
        # à CETTE boucle asyncio, celle réellement exécutée par asyncio.run().
        bot_scheduler.start()
        logger.info("✅ Planificateur démarré")

        try:
            await asyncio.Event().wait()  # bloque jusqu'à Ctrl+C / arrêt du process
        finally:
            bot_scheduler.stop()
            await webhook_runner.cleanup()
            await application.updater.stop()
            await application.stop()

def main():
    """Point d'entrée principal du bot"""
    try:
        # Afficher la bannière
        print_startup_banner()
        
        # Vérifier la configuration
        logger.info("🔍 Vérification de la configuration...")
        config_errors = check_config()
        
        if config_errors:
            print("\n⚠️  AVERTISSEMENTS DE CONFIGURATION:\n")
            for error in config_errors:
                print(error)
            print("\n")
            
            # Arrêter si le token n'est pas configuré
            if any("BOT_TOKEN" in e for e in config_errors):
                logger.error("Token du bot non configuré. Arrêt.")
                sys.exit(1)
            
            # Continuer automatiquement avec un avertissement (les avertissements
            # restants sont non bloquants, ex: cookies manquants — le bot
            # fonctionne quand même pour le contenu public). Pas d'input()
            # ici : ça plante immédiatement sur un serveur non-interactif
            # (Render, Railway, Docker...) avec EOFError.
            logger.warning("Démarrage malgré les avertissements ci-dessus (non bloquants).")
        
        logger.info("✅ Configuration validée")
        
        # Créer l'application
        logger.info("🔧 Création de l'application Telegram...")
        application = (
            Application.builder()
            .token(BOT_TOKEN)
            .post_init(post_init)
            .read_timeout(30)
            .write_timeout(30)
            .connect_timeout(30)
            .build()
        )
        
        # Configurer les handlers
        setup_handlers(application)
        
        # Informations de démarrage
        print("\n" + "="*60)
        print(f"✅ Bot démarré avec succès!")
        print(f"🤖 Token: {BOT_TOKEN[:15]}..." + "*" * 20)
        print(f"👥 Administrateurs: {ADMIN_IDS}")
        print(f"📝 Logs: {LOG_FILE}")
        print(f"💳 Webhook paiement: http://{WEBHOOK_SERVER_HOST}:{WEBHOOK_SERVER_PORT}/webhooks/atelier")
        print("="*60)
        print("\n⏳ En attente de messages...\n")
        
        # Démarrer le bot + le serveur webhook de paiement
        logger.info("🚀 Démarrage du polling et du serveur de paiement...")
        asyncio.run(run_bot(application))
        
    except KeyboardInterrupt:
        print("\n\n🛑 Arrêt demandé par l'utilisateur...")
        logger.info("Arrêt du bot par l'utilisateur")
        
    except Exception as e:
        logger.error(f"Erreur fatale: {e}", exc_info=True)
        print(f"\n❌ ERREUR FATALE: {e}")
        print("Consultez bot.log pour plus de détails")
        sys.exit(1)
        
    finally:
        # Le planificateur est démarré/arrêté dans run_bot(), pas ici
        print("\n👋 Au revoir!\n")
        logger.info("Bot arrêté proprement")

if __name__ == "__main__":
    main()
