# -*- coding: utf-8 -*-
"""
Détection automatique des plateformes à partir d'URLs

Deux niveaux :
1. Plateformes "vedettes" (YouTube, TikTok, Instagram, Facebook, Pinterest,
   Twitter/X) : détection par regex rapide, comportement/cookies dédiés dans
   utils/downloader.py.
2. Toutes les autres plateformes supportées par yt-dlp (voir la sortie de
   `yt-dlp --list-extractors`, ~1750 sites) : détectées en repli via le
   registre d'extracteurs de yt-dlp lui-même — donc toujours à jour avec
   la version de yt-dlp installée, sans liste à maintenir à la main.
   Contrôlable globalement via PLATFORMS_ENABLED["autres"].
"""
import re
from typing import Optional, Tuple
from config import PLATFORMS_ENABLED

class PlatformDetector:

    PATTERNS = {
        "youtube": [
            r'(?:https?://)?(?:www\.|m\.)?youtube\.com/watch\?v=[\w-]+',
            r'(?:https?://)?(?:www\.|m\.)?youtube\.com/shorts/[\w-]+',
            r'(?:https?://)?youtu\.be/[\w-]+',
            r'(?:https?://)?(?:www\.|m\.)?youtube\.com/live/[\w-]+',
        ],
        "tiktok": [
            r'(?:https?://)?(?:www\.|m\.|vm\.)?tiktok\.com/@[\w.-]+/video/\d+',
            r'(?:https?://)?(?:www\.|m\.|vm\.)?tiktok\.com/[\w-]+',
            r'(?:https?://)?vm\.tiktok\.com/[\w-]+',
            r'(?:https?://)?vt\.tiktok\.com/[\w-]+',
        ],
        "instagram": [
            r'(?:https?://)?(?:www\.|m\.)?instagram\.com/reel/[\w-]+',
            r'(?:https?://)?(?:www\.|m\.)?instagram\.com/p/[\w-]+',
            r'(?:https?://)?(?:www\.|m\.)?instagram\.com/stories/[\w.-]+/\d+',
            r'(?:https?://)?(?:www\.|m\.)?instagram\.com/tv/[\w-]+',
        ],
        "facebook": [
            # NOUVEAUX FORMATS (2024-2025)
            r'(?:https?://)?(?:www\.|m\.)?facebook\.com/share/v/[\w-]+',
            r'(?:https?://)?(?:www\.|m\.)?facebook\.com/share/r/[\w-]+',
            r'(?:https?://)?(?:www\.|m\.)?facebook\.com/reel/\d+',
            # ANCIENS FORMATS
            r'(?:https?://)?(?:www\.|m\.)?facebook\.com/[\w.-]+/videos/\d+',
            r'(?:https?://)?(?:www\.|m\.)?facebook\.com/watch/?\?v=\d+',
            r'(?:https?://)?fb\.watch/[\w-]+',
            r'(?:https?://)?(?:www\.|m\.)?facebook\.com/.*?/videos?/\d+',
        ],
        "pinterest": [
            r'(?:https?://)?(?:www\.|m\.)?pinterest\.com/pin/\d+',
            r'(?:https?://)?pin\.it/[\w-]+',
            r'(?:https?://)?(?:www\.|m\.)?pinterest\.[a-z]{2,}/pin/\d+',
        ],
        "twitter": [
            r'(?:https?://)?(?:www\.|m\.)?twitter\.com/[\w]+/status/\d+',
            r'(?:https?://)?(?:www\.|m\.)?x\.com/[\w]+/status/\d+',
            r'(?:https?://)?t\.co/[\w-]+',
        ],
    }

    # Registre des extracteurs yt-dlp, chargé une seule fois (paresseusement,
    # car construire cette liste a un léger coût et n'est pas nécessaire
    # tant qu'aucune URL "hors vedettes" n'a été envoyée).
    _extractor_classes = None

    @classmethod
    def _get_extractor_classes(cls):
        if cls._extractor_classes is None:
            import yt_dlp.extractor
            cls._extractor_classes = list(yt_dlp.extractor.gen_extractor_classes())
        return cls._extractor_classes

    @staticmethod
    def detect_platform(url: str) -> Optional[str]:
        """
        Détecte la plateforme à partir d'une URL.
        Retourne le nom de la plateforme ou None.
        """
        url = url.strip()

        # 1) Plateformes vedettes (regex rapide)
        for platform, patterns in PlatformDetector.PATTERNS.items():
            if not PLATFORMS_ENABLED.get(platform, True):
                continue

            for pattern in patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return platform

        # 2) Repli : n'importe quel extracteur yt-dlp (~1750 sites, y
        # compris l'extracteur "generic" en tout dernier recours pour les
        # pages web contenant une vidéo intégrée). Désactivable globalement
        # depuis le panneau admin (Paramètres → Autres).
        if not PLATFORMS_ENABLED.get("autres", True):
            return None

        if not re.match(r'^https?://', url, re.IGNORECASE):
            return None

        try:
            for ie in PlatformDetector._get_extractor_classes():
                ie_name = getattr(ie, "IE_NAME", "") or ""
                if not ie_name:
                    continue
                try:
                    if ie.suitable(url):
                        # yt-dlp utilise parfois "site:sous-type" (ex.
                        # "twitch:clips") — on garde la partie principale,
                        # plus lisible pour l'affichage et pour le fallback
                        # générique de downloader.py.
                        return ie_name.lower().split(':')[0]
                except Exception:
                    continue
        except Exception:
            pass

        return None
    
    @staticmethod
    def is_supported(url: str) -> Tuple[bool, Optional[str]]:
        """
        Vérifie si l'URL est supportée
        Retourne (est_supporté, plateforme)
        """
        platform = PlatformDetector.detect_platform(url)
        return (platform is not None, platform)
    
    @staticmethod
    def normalize_url(url: str, platform: str) -> str:
        """
        Normalise les URLs (convertit les URLs courtes en URLs complètes)
        """
        # Facebook share links vers format standard
        if platform == "facebook":
            if "/share/v/" in url or "/share/r/" in url:
                # Ces URLs sont déjà supportées par yt-dlp
                return url
        
        # TikTok vm.tiktok.com vers www.tiktok.com
        if platform == "tiktok":
            if "vm.tiktok.com" in url or "vt.tiktok.com" in url:
                # yt-dlp gère la redirection automatiquement
                return url
        
        return url

# Instance globale
platform_detector = PlatformDetector()
