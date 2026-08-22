# -*- coding: utf-8 -*-
"""
Vérification des limites d'utilisation
"""
from datetime import datetime
from typing import Tuple
from config import (
    NORMAL_YOUTUBE_DAILY_LIMIT, NORMAL_OTHER_DAILY_LIMIT, NORMAL_COOLDOWN,
    NORMAL_MAX_QUALITY_YOUTUBE, PREMIUM_MAX_QUALITY
)

class LimitChecker:
    
    @staticmethod
    async def check_limits(user_data: dict, is_youtube: bool) -> Tuple[bool, str]:
        """
        Vérifie si l'utilisateur peut télécharger
        Retourne (peut_télécharger, message_erreur)
        """
        # Premium = pas de limite
        if user_data.get("premium"):
            return True, ""
        
        # Vérifier le cooldown
        last_download = user_data.get("last_download_time", 0)
        time_since_last = datetime.now().timestamp() - last_download
        
        if time_since_last < NORMAL_COOLDOWN:
            remaining = int(NORMAL_COOLDOWN - time_since_last)
            return False, f"⏳ Attendez {remaining} secondes avant le prochain téléchargement."
        
        # Vérifier les limites journalières
        if is_youtube:
            downloads_today = user_data.get("downloads_youtube_today", 0)
            limit = NORMAL_YOUTUBE_DAILY_LIMIT
            
            if downloads_today >= limit:
                return False, f"❌ Limite YouTube atteinte ({limit}/jour). Passez Premium pour téléchargements illimités !"
        else:
            downloads_today = user_data.get("downloads_other_today", 0)
            limit = NORMAL_OTHER_DAILY_LIMIT
            
            if downloads_today >= limit:
                return False, f"❌ Limite quotidienne atteinte ({limit}/jour). Passez Premium !"
        
        return True, ""
    
    @staticmethod
    def get_max_quality(user_data: dict) -> str:
        """Retourne la qualité maximale autorisée"""
        if user_data.get("premium"):
            return PREMIUM_MAX_QUALITY
        return NORMAL_MAX_QUALITY_YOUTUBE
    
    @staticmethod
    def filter_qualities(formats: list, user_data: dict) -> list:
        """Filtre les qualités selon le type d'utilisateur"""
        max_quality = LimitChecker.get_max_quality(user_data)
        
        if user_data.get("premium"):
            return formats
        
        # Filtrer pour utilisateurs normaux
        filtered = []
        for fmt in formats:
            if fmt['quality'] == 'audio':
                filtered.append(fmt)
            elif fmt['quality'].isdigit() and int(fmt['quality']) <= int(max_quality):
                filtered.append(fmt)
        
        return filtered

# Instance globale
limit_checker = LimitChecker()
