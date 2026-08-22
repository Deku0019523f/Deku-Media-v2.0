# -*- coding: utf-8 -*-
"""
English translations
"""

TRANSLATIONS = {
    # Welcome
    "welcome": """
👋 **Welcome to the Multi-Platform Download Bot!**

I can download videos from:
• YouTube (videos & shorts)
• TikTok
• Instagram (reels, posts, stories)
• Facebook (videos, reels)
• Pinterest
• Twitter/X
• And many more sites (Vimeo, Dailymotion, SoundCloud, Twitch, Reddit, etc.)!

📤 **Simply send a link** to get started!

👤 Owner: {owner}
🌟 Developed with ❤️
""",
    
    # Main menu
    "menu_support": "🛟 Support",
    "menu_invite": "👯 Invite a friend",
    "menu_premium": "⭐️ Subscription",
    "menu_language": "🌍 Change language",
    "menu_donate": "❤️ Donate",
    "menu_hide": "❌ Hide",
    "menu_stats": "📊 My stats",
    
    # Premium
    "premium_info": """
⭐️ **PREMIUM SUBSCRIPTION**

✨ Benefits:
• **Unlimited** downloads
• No waiting time
• Quality up to **4K**
• Priority support
• Duration: **2 months**

💳 To subscribe, click the button below: a secure payment link
(Mobile Money or card) will be generated for you.
Your Premium is activated **automatically** once payment is confirmed.
""",
    "premium_button": "💳 Subscribe Premium",
    "premium_confirm_button": "✅ Payment completed",
    "premium_pending": "⏳ Your subscription request has been sent to administrators. You will be notified upon validation.",
    "premium_active": "✨ You are already Premium until {date}!",
    "premium_activated": "🎉 Congratulations! Your Premium account is activated for 2 months.",
    "premium_pay_button": "💳 Pay now",
    "premium_check_button": "🔄 Check my payment",
    "premium_checkout_created": """
💳 **Your payment link is ready!**

1️⃣ Click **Pay now**
2️⃣ Pay by Mobile Money or card
3️⃣ Come back here: your Premium will be activated **automatically**

If nothing happens after payment, click **Check my payment**.
""",
    "premium_payment_error": "❌ Couldn't generate your payment link right now. Please try again shortly or contact support.",
    "premium_still_pending": "⏳ Payment not confirmed yet. Please try again shortly.",
    
    # Referral
    "referral_info": """
👯 **REFERRAL SYSTEM**

Invite your friends and earn points!

🎁 Rewards:
• Normal friend: **2 points**
• Premium friend: **5 points**

💎 Conversion:
• 10 points = **1 week Premium**
• 30 points = **1 month Premium**

📊 Your status:
• Points: **{points}**
• Invited: **{invited}**

🔗 Your referral link:
`{link}`
""",
    "referral_button": "🔗 Share my link",
    "referral_redeem": "💎 Redeem my points",
    "referral_not_enough": "❌ Insufficient points. You have {points} points.",
    "referral_success": "✅ {days} days Premium added! Remaining points: {points}",
    
    # Download
    "download_processing": "⏳ Analyzing video...",
    "download_preview": """
🎬 **{title}**

⏱ Duration: {duration}
👤 Author: {uploader}
📺 Platform: {platform}
👁 Views: {views}
""",
    "download_select_quality": "📊 Select quality:",
    "download_button_confirm": "▶️ Download",
    "download_button_cancel": "❌ Cancel",
    "download_cancelled": "❌ Download cancelled.",
    "download_starting": "⬇️ Downloading...",
    "download_success": "✅ Download completed! File will be deleted in 20 seconds.",
    "download_error": "❌ Download error: {error}",
    "download_too_large": "❌ File too large (limit: 2 GB).",
    
    # Errors
    "error_platform_not_supported": "❌ Unsupported platform or invalid link.",
    "error_platform_disabled": "❌ This platform is temporarily disabled.",
    "error_invalid_url": "❌ Invalid URL. Please send a valid link.",
    "error_banned": "🚫 You are banned from this bot.",
    
    # Donation
    "donate_info": """
❤️ **MAKE A DONATION**

Support bot development with Telegram Stars!

Choose an amount:
""",
    "donate_button_20": "⭐️ 20 Stars",
    "donate_button_50": "⭐️ 50 Stars",
    "donate_success": "🙏 Thank you for your generous donation of {amount} Stars!",
    
    # Statistics
    "stats_user": """
📊 **YOUR STATISTICS**

👤 ID: `{user_id}`
⭐️ Status: {status}
{premium_info}

📥 Downloads:
• YouTube today: {yt_today}/{yt_limit}
• Others today: {other_today}/{other_limit}
• Total: {total}

🎁 Referral:
• Points: {points}
• Invited: {invited}
""",
    
    # Admin
    "admin_menu": "🛡 **ADMIN PANEL**",
    "admin_users": "👥 User management",
    "admin_payments": "💳 Pending payments",
    "admin_stats": "📊 Global statistics",
    "admin_broadcast": "📢 Broadcast message",
    "admin_settings": "⚙️ Settings",
    
    # Language
    "language_select": "🌍 Choose your language:",
    "language_changed": "✅ Language changed to English.",
}

def get_text(key: str, **kwargs) -> str:
    """Get translation with variables"""
    text = TRANSLATIONS.get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text
