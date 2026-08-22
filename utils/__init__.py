# -*- coding: utf-8 -*-
"""
Package utils - Utilitaires et fonctions helpers

Ce package contient tous les utilitaires pour la gestion
des utilisateurs, téléchargements, base de données, etc.
"""

# Import avec gestion d'erreurs
try:
    from .user_manager import UserManager, user_manager
except ImportError as e:
    print(f"⚠️  Erreur import user_manager: {e}")
    UserManager = None
    user_manager = None

try:
    from .database import Database, db
except ImportError as e:
    print(f"⚠️  Erreur import database: {e}")
    Database = None
    db = None

try:
    from .downloader import Downloader, downloader
except ImportError as e:
    print(f"⚠️  Erreur import downloader: {e}")
    Downloader = None
    downloader = None

try:
    from .limits import LimitChecker, limit_checker
except ImportError as e:
    print(f"⚠️  Erreur import limits: {e}")
    LimitChecker = None
    limit_checker = None

try:
    from .platform_detector import PlatformDetector, platform_detector
except ImportError as e:
    print(f"⚠️  Erreur import platform_detector: {e}")
    PlatformDetector = None
    platform_detector = None

try:
    from .scheduler import BotScheduler, bot_scheduler
except ImportError as e:
    print(f"⚠️  Erreur import scheduler: {e}")
    BotScheduler = None
    bot_scheduler = None

__all__ = [
    # User Management
    'UserManager',
    'user_manager',
    
    # Database
    'Database',
    'db',
    
    # Downloader
    'Downloader',
    'downloader',
    
    # Limits
    'LimitChecker',
    'limit_checker',
    
    # Platform Detection
    'PlatformDetector',
    'platform_detector',
    
    # Scheduler
    'BotScheduler',
    'bot_scheduler',
]

__version__ = '1.0.0'
__author__ = '@Darkdeku225'
