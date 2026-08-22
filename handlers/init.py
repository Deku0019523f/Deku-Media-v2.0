# -*- coding: utf-8 -*-
"""
Package handlers - Gestionnaires d'événements Telegram

Ce package contient tous les handlers pour les commandes,
callbacks et interactions utilisateur du bot.
"""

from .start import start_command, hide_keyboard, get_main_keyboard
from .download import handle_url, download_callback
from .premium import (
    premium_command,
    premium_confirm_callback,
    admin_validate_payment,
    admin_reject_payment
)
from .referral import referral_command, redeem_callback
from .payment import (
    donate_command,
    donate_callback,
    precheckout_callback,
    successful_payment_callback
)
from .language import language_command, language_callback
from .stats import stats_command
from .admin import (
    admin_command,
    admin_stats_callback,
    admin_payments_callback,
    admin_users_callback,
    admin_settings_callback,
    admin_broadcast_callback,
    admin_receive_broadcast,
    admin_cancel,
    BROADCAST_MESSAGE
)

__all__ = [
    # Start
    'start_command',
    'hide_keyboard',
    'get_main_keyboard',
    
    # Download
    'handle_url',
    'download_callback',
    
    # Premium
    'premium_command',
    'premium_confirm_callback',
    'admin_validate_payment',
    'admin_reject_payment',
    
    # Referral
    'referral_command',
    'redeem_callback',
    
    # Payment
    'donate_command',
    'donate_callback',
    'precheckout_callback',
    'successful_payment_callback',
    
    # Language
    'language_command',
    'language_callback',
    
    # Stats
    'stats_command',
    
    # Admin
    'admin_command',
    'admin_stats_callback',
    'admin_payments_callback',
    'admin_users_callback',
    'admin_settings_callback',
    'admin_broadcast_callback',
    'admin_receive_broadcast',
    'admin_cancel',
    'BROADCAST_MESSAGE',
]

__version__ = '1.0.0'
__author__ = '@Darkdeku225'
