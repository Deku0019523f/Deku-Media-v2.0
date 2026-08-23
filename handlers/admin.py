# -*- coding: utf-8 -*-
"""
Handler pour le panneau administrateur - VERSION CORRIGÉE FINALE
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from utils.database import db
from utils.user_manager import user_manager
from config import ADMIN_IDS, PLATFORMS_ENABLED, COOKIES_MAP
from datetime import datetime, timedelta
import json
import asyncio
import logging

logger = logging.getLogger(__name__)


def escape_markdown(text) -> str:
    """Échappe les caractères spéciaux du Markdown (legacy) dans du texte non
    fiable (pseudos Telegram, raisons de ban...) avant de l'insérer dans un
    message parse_mode=MARKDOWN — un pseudo avec un simple "_" fait sinon
    échouer l'envoi du message entier."""
    if not text:
        return ""
    text = str(text)
    for char in ('_', '*', '`', '['):
        text = text.replace(char, f'\\{char}')
    return text

# États de conversation
BROADCAST_MESSAGE, BAN_REASON = range(2)

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu principal admin"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Accès refusé.")
        return
    
    keyboard = [
        [
            InlineKeyboardButton("👥 Utilisateurs", callback_data="admin_users"),
            InlineKeyboardButton("💳 Paiements", callback_data="admin_payments")
        ],
        [
            InlineKeyboardButton("📊 Statistiques", callback_data="admin_stats"),
            InlineKeyboardButton("🎁 Parrainages", callback_data="admin_referrals")
        ],
        [
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
            InlineKeyboardButton("⚙️ Paramètres", callback_data="admin_settings")
        ],
        [
            InlineKeyboardButton("📝 Logs", callback_data="admin_logs")
        ]
    ]
    
    await update.message.reply_text(
        "🛡 **PANNEAU ADMINISTRATEUR**\n\nChoisissez une option :",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Retour au menu admin"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in ADMIN_IDS:
        return
    
    keyboard = [
        [
            InlineKeyboardButton("👥 Utilisateurs", callback_data="admin_users"),
            InlineKeyboardButton("💳 Paiements", callback_data="admin_payments")
        ],
        [
            InlineKeyboardButton("📊 Statistiques", callback_data="admin_stats"),
            InlineKeyboardButton("🎁 Parrainages", callback_data="admin_referrals")
        ],
        [
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
            InlineKeyboardButton("⚙️ Paramètres", callback_data="admin_settings")
        ],
        [
            InlineKeyboardButton("📝 Logs", callback_data="admin_logs")
        ]
    ]
    
    await query.edit_message_text(
        "🛡 **PANNEAU ADMINISTRATEUR**\n\nChoisissez une option :",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche les statistiques globales"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in ADMIN_IDS:
        return
    
    stats = await db.get_global_stats()
    
    text = f"""📊 **STATISTIQUES GLOBALES**

👥 **Utilisateurs :**
• Total : {stats['total_users']}
• Premium : {stats['premium_users']}
• Ratio : {(stats['premium_users']/stats['total_users']*100) if stats['total_users'] > 0 else 0:.1f}%

📥 **Téléchargements :**
• Aujourd'hui : {stats['today_downloads']}
• Total : {stats['total_downloads']}
• Moyenne/user : {(stats['total_downloads']/stats['total_users']) if stats['total_users'] > 0 else 0:.1f}
"""
    
    keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data="admin_menu")]]
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_payments_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche les paiements en attente"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in ADMIN_IDS:
        return
    
    pending = await db.get_pending_payments()
    
    if not pending:
        text = "✅ Aucun paiement en attente."
        keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data="admin_menu")]]
    else:
        text = f"💳 **PAIEMENTS EN ATTENTE** ({len(pending)})\n\n"
        keyboard = []
        
        for payment in pending[:5]:
            user_id = payment['user_id']
            username = payment['username']
            payment_id = payment['id']
            created = payment['created_at']
            
            text += f"• @{escape_markdown(username)} (ID: `{user_id}`)\n"
            text += f"  Date: {created[:10]}\n\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"✅ #{payment_id}",
                    callback_data=f"admin_validate_{payment_id}_{user_id}"
                ),
                InlineKeyboardButton(
                    f"❌ #{payment_id}",
                    callback_data=f"admin_reject_{payment_id}_{user_id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Retour", callback_data="admin_menu")])
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu de gestion des utilisateurs"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in ADMIN_IDS:
        return
    
    keyboard = [
        [InlineKeyboardButton("⭐️ Donner Premium", callback_data="admin_give_premium")],
        [InlineKeyboardButton("🚫 Bannir user", callback_data="admin_ban_user")],
        [InlineKeyboardButton("✅ Débannir user", callback_data="admin_unban_user")],
        [InlineKeyboardButton("🔄 Reset limites", callback_data="admin_reset_limits")],
        [InlineKeyboardButton("🔙 Retour", callback_data="admin_menu")]
    ]
    
    await query.edit_message_text(
        "👥 **GESTION UTILISATEURS**\n\nChoisissez une action :",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Paramètres du bot"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in ADMIN_IDS:
        return
    
    text = "⚙️ **PARAMÈTRES DU BOT**\n\n📺 **Plateformes :**\n\n"
    keyboard = []
    
    for platform, enabled in PLATFORMS_ENABLED.items():
        status = "✅" if enabled else "❌"
        text += f"{status} {platform.capitalize()}\n"
        
        keyboard.append([
            InlineKeyboardButton(
                f"{'❌ Désactiver' if enabled else '✅ Activer'} {platform}",
                callback_data=f"admin_toggle_{platform}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Retour", callback_data="admin_menu")])
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_toggle_platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Active/Désactive une plateforme"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in ADMIN_IDS:
        return
    
    platform = query.data.replace("admin_toggle_", "")
    PLATFORMS_ENABLED[platform] = not PLATFORMS_ENABLED.get(platform, True)
    
    status = "✅ activée" if PLATFORMS_ENABLED[platform] else "❌ désactivée"
    await query.answer(f"{platform.capitalize()} {status}")
    
    await admin_settings_callback(update, context)

async def admin_referrals_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche les statistiques de parrainage"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in ADMIN_IDS:
        return
    
    from config import USERS_DIR
    
    total_referrals = 0
    top_referrers = []
    
    for user_file in USERS_DIR.glob("*.json"):
        try:
            with open(user_file, 'r', encoding='utf-8') as f:
                user_data = json.load(f)
            
            invited = len(user_data.get("invited_users", []))
            if invited > 0:
                total_referrals += invited
                top_referrers.append({
                    'id': user_data['id'],
                    'username': user_data.get('username', 'N/A'),
                    'invited': invited,
                    'points': user_data.get('points', 0)
                })
        except:
            pass
    
    top_referrers.sort(key=lambda x: x['invited'], reverse=True)
    
    text = f"🎁 **SYSTÈME DE PARRAINAGE**\n\n"
    text += f"📊 Total parrainages : {total_referrals}\n\n"
    text += "🏆 **Top 5 parrains :**\n\n"
    
    for i, referrer in enumerate(top_referrers[:5], 1):
        text += f"{i}. @{escape_markdown(referrer['username'])} (ID: `{referrer['id']}`)\n"
        text += f"   • Invités : {referrer['invited']}\n"
        text += f"   • Points : {referrer['points']}\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data="admin_menu")]]
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_logs_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche les derniers logs"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in ADMIN_IDS:
        return
    
    from config import LOG_FILE
    
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            last_lines = lines[-20:] if len(lines) > 20 else lines
        
        logs_text = "".join(last_lines[-10:])
        
        text = "📝 **DERNIERS LOGS**\n\n"
        text += f"``````"
        
    except Exception as e:
        text = f"❌ Erreur lecture logs : {e}"
    
    keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data="admin_menu")]]
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initie le broadcast"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    
    await query.edit_message_text(
        "📢 **BROADCAST**\n\n"
        "Envoyez le message à diffuser à tous les utilisateurs.\n\n"
        "Utilisez /cancel pour annuler.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return BROADCAST_MESSAGE

async def admin_receive_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reçoit et envoie le broadcast"""
    if update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    
    message = update.message.text
    
    await update.message.reply_text("📤 Envoi en cours...")
    
    from config import USERS_DIR
    
    success = 0
    failed = 0
    
    for user_file in USERS_DIR.glob("*.json"):
        user_id = int(user_file.stem)
        try:
            await context.bot.send_message(user_id, message, parse_mode=ParseMode.MARKDOWN)
            success += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            # Repli en texte brut si l'échec vient du Markdown (ex: un "_"
            # non échappé dans le message) — évite que TOUT le broadcast
            # échoue silencieusement pour une simple faute de frappe.
            if "parse entities" in str(e).lower() or "can't find end" in str(e).lower():
                try:
                    await context.bot.send_message(user_id, message)
                    success += 1
                    await asyncio.sleep(0.05)
                    continue
                except Exception:
                    pass
            failed += 1
    
    await update.message.reply_text(
        f"✅ **Broadcast terminé !**\n\n"
        f"✅ Envoyés : {success}\n"
        f"❌ Échecs : {failed}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ConversationHandler.END

async def admin_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Annule l'opération admin"""
    await update.message.reply_text("❌ Opération annulée.")
    return ConversationHandler.END

async def admin_give_premium_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Demande l'ID pour donner Premium"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in ADMIN_IDS:
        return
    
    await query.edit_message_text(
        "⭐️ **DONNER PREMIUM**\n\n"
        "Envoyez l'ID de l'utilisateur :\n"
        "`/setpremium USER_ID JOURS`\n\n"
        "Exemple : `/setpremium 123456789 60`",
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_ban_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Demande l'ID pour bannir"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in ADMIN_IDS:
        return
    
    await query.edit_message_text(
        "🚫 **BANNIR UTILISATEUR**\n\n"
        "Envoyez la commande :\n"
        "`/ban USER_ID RAISON`\n\n"
        "Exemple : `/ban 123456789 Spam`",
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_unban_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Demande l'ID pour débannir"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in ADMIN_IDS:
        return
    
    await query.edit_message_text(
        "✅ **DÉBANNIR UTILISATEUR**\n\n"
        "Envoyez la commande :\n"
        "`/unban USER_ID`\n\n"
        "Exemple : `/unban 123456789`",
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_reset_limits_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset les limites d'un utilisateur"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in ADMIN_IDS:
        return
    
    await query.edit_message_text(
        "🔄 **RESET LIMITES**\n\n"
        "Envoyez la commande :\n"
        "`/resetlimits USER_ID`\n\n"
        "Exemple : `/resetlimits 123456789`",
        parse_mode=ParseMode.MARKDOWN
    )

async def setpremium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Donne le Premium à un utilisateur (commande admin)"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if len(context.args) != 2:
        await update.message.reply_text(
            "❌ Usage : `/setpremium USER_ID JOURS`\n\nExemple : `/setpremium 123456789 60`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        target_id = int(context.args[0])
        days = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ USER_ID et JOURS doivent être des nombres entiers.")
        return
    
    if days <= 0:
        await update.message.reply_text("❌ Le nombre de jours doit être positif.")
        return
    
    expire_date = (datetime.now() + timedelta(days=days)).isoformat()
    await user_manager.set_premium(target_id, days)
    await db.set_premium(target_id, expire_date)
    
    await update.message.reply_text(
        f"✅ Premium accordé à `{target_id}` pour {days} jours.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    try:
        await context.bot.send_message(
            target_id,
            f"🎉 Un administrateur vous a offert le Premium pour {days} jours !",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception:
        pass

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bannit un utilisateur (commande admin)"""
    admin_id = update.effective_user.id
    if admin_id not in ADMIN_IDS:
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Usage : `/ban USER_ID RAISON`\n\nExemple : `/ban 123456789 Spam`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ USER_ID doit être un nombre entier.")
        return
    
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Non précisée"
    
    await db.ban_user(target_id, reason, admin_id)
    
    await update.message.reply_text(
        f"🚫 Utilisateur `{target_id}` banni.\nRaison : {escape_markdown(reason)}",
        parse_mode=ParseMode.MARKDOWN
    )

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Débannit un utilisateur (commande admin)"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if len(context.args) != 1:
        await update.message.reply_text(
            "❌ Usage : `/unban USER_ID`\n\nExemple : `/unban 123456789`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ USER_ID doit être un nombre entier.")
        return
    
    await db.unban_user(target_id)
    
    await update.message.reply_text(
        f"✅ Utilisateur `{target_id}` débanni.",
        parse_mode=ParseMode.MARKDOWN
    )

async def resetlimits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Réinitialise les limites de téléchargement d'un utilisateur (commande admin)"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if len(context.args) != 1:
        await update.message.reply_text(
            "❌ Usage : `/resetlimits USER_ID`\n\nExemple : `/resetlimits 123456789`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ USER_ID doit être un nombre entier.")
        return
    
    await user_manager.reset_daily_limits(target_id)
    
    await update.message.reply_text(
        f"🔄 Limites de téléchargement réinitialisées pour `{target_id}`.",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_cookie_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reçoit un fichier de cookies envoyé par un admin, demande la plateforme"""
    if update.effective_user.id not in ADMIN_IDS:
        return

    document = update.message.document
    if not document.file_name or not document.file_name.lower().endswith(".txt"):
        await update.message.reply_text(
            "❌ Envoie un fichier `.txt` au format Netscape (export de cookies de navigateur).",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    context.user_data["pending_cookie_file_id"] = document.file_id

    keyboard = [
        [
            InlineKeyboardButton("YouTube", callback_data="cookie_platform_youtube"),
            InlineKeyboardButton("Facebook", callback_data="cookie_platform_facebook"),
        ],
        [
            InlineKeyboardButton("Instagram", callback_data="cookie_platform_instagram"),
            InlineKeyboardButton("TikTok", callback_data="cookie_platform_tiktok"),
        ],
    ]
    await update.message.reply_text(
        "🍪 Pour quelle plateforme est ce fichier de cookies ?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_cookie_platform_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enregistre le fichier de cookies reçu pour la plateforme choisie"""
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in ADMIN_IDS:
        return

    platform = query.data.replace("cookie_platform_", "")
    file_id = context.user_data.get("pending_cookie_file_id")

    if not file_id:
        await query.edit_message_text("❌ Session expirée, renvoie le fichier de cookies.")
        return

    dest_path = COOKIES_MAP.get(platform)
    if not dest_path:
        await query.edit_message_text("❌ Plateforme inconnue.")
        return

    try:
        tg_file = await context.bot.get_file(file_id)
        await tg_file.download_to_drive(str(dest_path))
        context.user_data.pop("pending_cookie_file_id", None)
        await query.edit_message_text(
            f"✅ Cookies **{platform.capitalize()}** mis à jour (`{dest_path.name}`).\n\n"
            f"Utilisés immédiatement pour les prochains téléchargements (bot et site web).",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception:
        logger.exception(f"Échec sauvegarde cookies (plateforme={platform})")
        await query.edit_message_text("❌ Erreur lors de la sauvegarde du fichier. Réessaie.")

async def removecookies_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Supprime le fichier de cookies d'une plateforme (utile si les cookies sont invalides)"""
    if update.effective_user.id not in ADMIN_IDS:
        return

    if len(context.args) != 1 or context.args[0].lower() not in COOKIES_MAP:
        platforms = ", ".join(COOKIES_MAP.keys())
        await update.message.reply_text(
            f"❌ Usage : `/removecookies PLATEFORME`\n\nPlateformes : {platforms}",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    platform = context.args[0].lower()
    path = COOKIES_MAP[platform]

    if not path.exists():
        await update.message.reply_text(f"ℹ️ Aucun fichier de cookies pour {platform.capitalize()}.")
        return

    path.unlink()
    await update.message.reply_text(f"🗑 Cookies {platform.capitalize()} supprimés.")
