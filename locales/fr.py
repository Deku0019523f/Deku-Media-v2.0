# -*- coding: utf-8 -*-
"""
Traductions françaises
"""

TRANSLATIONS = {
    # Bienvenue
    "welcome": """
👋 **Bienvenue sur le Bot de Téléchargement Multiplateforme !**

Je peux télécharger des vidéos depuis :
• YouTube (vidéos & shorts)
• TikTok
• Instagram (reels, posts, stories)
• Facebook (vidéos, reels)
• Pinterest
• Twitter/X
• Et bien d'autres sites (Vimeo, Dailymotion, SoundCloud, Twitch, Reddit, etc.) !

📤 **Envoyez simplement un lien** pour commencer !

👤 Propriétaire : {owner}
🌟 Développé avec ❤️
""",
    
    # Menu principal
    "menu_support": "🛟 Soutien",
    "menu_invite": "👯 Inviter un ami",
    "menu_premium": "⭐️ Abonnement",
    "menu_language": "🌍 Changer de langue",
    "menu_donate": "❤️ Faire un don",
    "menu_hide": "❌ Masquer",
    "menu_stats": "📊 Mes statistiques",
    
    # Premium
    "premium_info": """
⭐️ **ABONNEMENT PREMIUM**

✨ Avantages :
• Téléchargements **illimités**
• Aucun délai d'attente
• Qualité jusqu'à **4K**
• Support prioritaire
• Durée : **2 mois**

💳 Pour souscrire, cliquez sur le bouton ci-dessous : un lien de paiement
sécurisé (Mobile Money ou carte bancaire) sera généré pour vous.
Votre Premium est activé **automatiquement** dès le paiement confirmé.
""",
    "premium_button": "💳 Souscrire Premium",
    "premium_confirm_button": "✅ Paiement effectué",
    "premium_pending": "⏳ Votre demande d'abonnement a été envoyée aux administrateurs. Vous serez notifié dès validation.",
    "premium_active": "✨ Vous êtes déjà Premium jusqu'au {date} !",
    "premium_activated": "🎉 Félicitations ! Votre compte Premium est activé pour 2 mois.",
    "premium_pay_button": "💳 Payer maintenant",
    "premium_check_button": "🔄 Vérifier mon paiement",
    "premium_checkout_created": """
💳 **Votre lien de paiement est prêt !**

1️⃣ Cliquez sur **Payer maintenant**
2️⃣ Réglez par Mobile Money ou carte bancaire
3️⃣ Revenez ici : votre Premium sera activé **automatiquement**

Si rien ne se passe après paiement, cliquez sur **Vérifier mon paiement**.
""",
    "premium_payment_error": "❌ Impossible de générer votre lien de paiement pour le moment. Réessayez dans quelques instants ou contactez le support.",
    "premium_still_pending": "⏳ Paiement pas encore confirmé. Réessayez dans quelques instants.",
    
    # Parrainage
    "referral_info": """
👯 **SYSTÈME DE PARRAINAGE**

Invitez vos amis et gagnez des points !

🎁 Récompenses :
• Ami normal : **2 points**
• Ami premium : **5 points**

💎 Conversion :
• 10 points = **1 semaine Premium**
• 30 points = **1 mois Premium**

📊 Votre statut :
• Points : **{points}**
• Invités : **{invited}**

🔗 Votre lien de parrainage :
`{link}`
""",
    "referral_button": "🔗 Partager mon lien",
    "referral_redeem": "💎 Échanger mes points",
    "referral_not_enough": "❌ Points insuffisants. Vous avez {points} points.",
    "referral_success": "✅ {days} jours Premium ajoutés ! Points restants : {points}",
    
    # Téléchargement
    "download_processing": "⏳ Analyse de la vidéo en cours...",
    "download_preview": """
🎬 **{title}**

⏱ Durée : {duration}
👤 Auteur : {uploader}
📺 Plateforme : {platform}
👁 Vues : {views}
""",
    "download_select_quality": "📊 Sélectionnez la qualité :",
    "download_button_confirm": "▶️ Télécharger",
    "download_button_cancel": "❌ Annuler",
    "download_cancelled": "❌ Téléchargement annulé.",
    "download_starting": "⬇️ Téléchargement en cours...",
    "download_success": "✅ Téléchargement terminé ! Le fichier sera supprimé dans 20 secondes.",
    "download_error": "❌ Erreur lors du téléchargement : {error}",
    "download_too_large": "❌ Fichier trop volumineux (limite : 2 Go).",
    
    # Erreurs
    "error_platform_not_supported": "❌ Plateforme non supportée ou lien invalide.",
    "error_platform_disabled": "❌ Cette plateforme est temporairement désactivée.",
    "error_invalid_url": "❌ URL invalide. Veuillez envoyer un lien valide.",
    "error_banned": "🚫 Vous êtes banni de ce bot.",
    
    # Don
    "donate_info": """
❤️ **FAIRE UN DON**

Soutenez le développement du bot avec Telegram Stars !

Choisissez un montant :
""",
    "donate_button_20": "⭐️ 20 Stars",
    "donate_button_50": "⭐️ 50 Stars",
    "donate_success": "🙏 Merci pour votre généreux don de {amount} Stars !",
    
    # Statistiques
    "stats_user": """
📊 **VOS STATISTIQUES**

👤 ID : `{user_id}`
⭐️ Statut : {status}
{premium_info}

📥 Téléchargements :
• YouTube aujourd'hui : {yt_today}/{yt_limit}
• Autres aujourd'hui : {other_today}/{other_limit}
• Total : {total}

🎁 Parrainage :
• Points : {points}
• Invités : {invited}
""",
    
    # Admin
    "admin_menu": "🛡 **PANNEAU ADMINISTRATEUR**",
    "admin_users": "👥 Gestion utilisateurs",
    "admin_payments": "💳 Paiements en attente",
    "admin_stats": "📊 Statistiques globales",
    "admin_broadcast": "📢 Message groupé",
    "admin_settings": "⚙️ Paramètres",
    
    # Langue
    "language_select": "🌍 Choisissez votre langue :",
    "language_changed": "✅ Langue changée en Français.",
}

def get_text(key: str, **kwargs) -> str:
    """Récupère une traduction avec variables"""
    text = TRANSLATIONS.get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text
