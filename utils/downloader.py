# -*- coding: utf-8 -*-
"""
Gestionnaire de téléchargement avec yt-dlp et API alternative TikTok
Support: YouTube, TikTok, Instagram, Facebook, Pinterest, Twitter/X
"""
import yt_dlp
import asyncio
import logging
import requests
from pathlib import Path
from typing import Dict, Optional, List
from config import (
    COOKIES_MAP, DOWNLOADS_DIR, YTDLP_BASE_OPTIONS,
    MAX_FILE_SIZE_MB, NORMAL_MAX_QUALITY_YOUTUBE, PREMIUM_MAX_QUALITY, FFMPEG_LOCATION
)

logger = logging.getLogger(__name__)

class TikTokAPI:
    """API alternative pour TikTok - TikWM.com (Gratuit)"""
    
    @staticmethod
    async def download(url: str, output_path: Path) -> bool:
        """Télécharge une vidéo TikTok via API TikWM"""
        try:
            print(f"🔄 API TikTok: {url}")
            
            # Requête à l'API TikWM
            loop = asyncio.get_event_loop()
            
            def fetch_api():
                response = requests.post(
                    "https://www.tikwm.com/api/",
                    data={'url': url, 'hd': 1},
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    timeout=30
                )
                return response.json()
            
            data = await loop.run_in_executor(None, fetch_api)
            
            if data.get('code') != 0:
                print(f"❌ API Error: {data.get('msg', 'Unknown error')}")
                return False
            
            # Récupérer l'URL de la vidéo (HD ou normale)
            video_url = data['data'].get('hdplay') or data['data'].get('play')
            
            if not video_url:
                print("❌ Aucune URL vidéo dans la réponse")
                return False
            
            print(f"✅ URL vidéo obtenue")
            
            # Télécharger la vidéo
            def download_video():
                video_response = requests.get(
                    video_url,
                    stream=True,
                    headers={'User-Agent': 'Mozilla/5.0'},
                    timeout=120
                )
                
                with open(output_path, 'wb') as f:
                    for chunk in video_response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            
            await loop.run_in_executor(None, download_video)
            
            if output_path.exists():
                size_mb = output_path.stat().st_size / 1024 / 1024
                print(f"✅ TikTok téléchargé via API: {size_mb:.2f} MB")
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Erreur API TikTok: {e}")
            return False

    @staticmethod
    async def get_info(url: str) -> Optional[Dict]:
        """
        Récupère les métadonnées TikTok via l'API TikWM, SANS télécharger.
        Plus fiable que yt-dlp pour TikTok (moins bloqué par la détection
        anti-bot) — utilisé en priorité pour les aperçus.
        """
        try:
            loop = asyncio.get_event_loop()

            def fetch_api():
                response = requests.post(
                    "https://www.tikwm.com/api/",
                    data={'url': url, 'hd': 1},
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    timeout=30
                )
                return response.json()

            data = await loop.run_in_executor(None, fetch_api)

            if data.get('code') != 0:
                return None

            d = data.get('data', {})
            return {
                'title': d.get('title') or 'Vidéo TikTok',
                'duration': d.get('duration', 0),
                'thumbnail': d.get('cover') or d.get('origin_cover'),
                'uploader': (d.get('author') or {}).get('nickname', 'Inconnu'),
                'view_count': d.get('play_count', 0),
            }
        except Exception:
            return None

class Downloader:
    
    def __init__(self):
        self.downloads_dir = DOWNLOADS_DIR
    
    def _get_cookie_file(self, platform: str) -> Optional[Path]:
        """Retourne le fichier cookie pour la plateforme"""
        cookie_path = COOKIES_MAP.get(platform)
        if cookie_path and cookie_path.exists():
            return cookie_path
        return None
    
    def _build_ytdlp_options(self, platform: str, quality: str, 
                            output_path: str) -> Dict:
        """Construit les options yt-dlp avec cookies et headers optimisés"""
        options = YTDLP_BASE_OPTIONS.copy()
        options['outtmpl'] = output_path
        if FFMPEG_LOCATION:
            options['ffmpeg_location'] = FFMPEG_LOCATION
        
        # Ajouter le fichier cookie si disponible
        cookie_file = self._get_cookie_file(platform)
        if cookie_file:
            options['cookiefile'] = str(cookie_file)
        
        # ============ TIKTOK ============
        if platform == "tiktok":
            options.update({
                'format': 'best/bestvideo+bestaudio',
                'merge_output_format': 'mp4',
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
                    'Referer': 'https://www.tiktok.com/',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                },
                'extractor_args': {
                    'tiktok': {
                        'api_hostname': 'api16-normal-c-useast1a.tiktokv.com',
                        'app_version': '34.1.2',
                        'manifest_app_version': '341'
                    }
                },
                'nocheckcertificate': True,
                'geo_bypass': True,
                'socket_timeout': 60,
                'retries': 3,
            })
        
        # ============ YOUTUBE ============
        elif platform == "youtube":
            if quality == "audio":
                options['format'] = 'bestaudio/best'
                options['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }]
            elif quality == "best":
                options['format'] = 'best'
            else:
                try:
                    quality_int = int(quality)
                    options['format'] = (
                        f'bestvideo[height<={quality_int}][ext=mp4]+bestaudio[ext=m4a]/'
                        f'bestvideo[height<={quality_int}]+bestaudio/'
                        f'best[height<={quality_int}]/'
                        'best'
                    )
                except ValueError:
                    options['format'] = 'best'
        
        # ============ FACEBOOK ============
        elif platform == "facebook":
            options.update({
                'format': 'best/bestvideo+bestaudio/bestaudio/best',
                'merge_output_format': 'mp4',
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Referer': 'https://www.facebook.com/',
                },
                'extractor_args': {
                    'facebook': {
                        'skip_dash_manifest': True
                    }
                }
            })
        
        # ============ INSTAGRAM ============
        elif platform == "instagram":
            options.update({
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
                    'Accept': '*/*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Referer': 'https://www.instagram.com/',
                },
                'format': 'best/bestvideo+bestaudio/bestaudio/best',
                'merge_output_format': 'mp4',
            })
        
        # ============ TWITTER/X ============
        elif platform == "twitter":
            options.update({
                'format': 'best/bestvideo+bestaudio/bestaudio/best',
                'merge_output_format': 'mp4',
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                }
            })
        
        # ============ PINTEREST ============
        elif platform == "pinterest":
            options.update({
                'format': 'best/bestvideo+bestaudio/bestaudio/best',
                'merge_output_format': 'mp4',
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                }
            })
        
        else:
            options['format'] = 'best/bestvideo+bestaudio/bestaudio/best'
            options['merge_output_format'] = 'mp4'
        
        # Limite de taille
        options['max_filesize'] = MAX_FILE_SIZE_MB * 1024 * 1024
        
        return options
    
    async def get_video_info(self, url: str, platform: str) -> Optional[Dict]:
        """
        Extrait les métadonnées vidéo sans télécharger
        """
        # TikTok : l'API TikWM est plus fiable que l'extracteur yt-dlp pour
        # les infos (même repli que download_video). Si elle échoue, on
        # retombe sur yt-dlp normalement.
        if platform == "tiktok":
            tiktok_info = await TikTokAPI.get_info(url)
            if tiktok_info:
                return {
                    **tiktok_info,
                    'platform': platform,
                    'formats': [{'quality': 'best', 'label': 'Meilleure qualité'}],
                }
            logger.warning(f"API TikTok (infos) échouée, repli sur yt-dlp pour {url}")

        try:
            options = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'skip_download': True,
                'no_check_certificate': True,
            }
            
            # Ajouter cookies
            cookie_file = self._get_cookie_file(platform)
            if cookie_file:
                options['cookiefile'] = str(cookie_file)
            
            # Headers par plateforme
            if platform == "tiktok":
                options.update({
                    'format': 'best',
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36',
                        'Referer': 'https://www.tiktok.com/',
                    },
                    'extractor_args': {
                        'tiktok': {
                            'api_hostname': 'api16-normal-c-useast1a.tiktokv.com',
                        }
                    },
                    'nocheckcertificate': True,
                })
            
            elif platform == "facebook":
                options['http_headers'] = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': 'https://www.facebook.com/',
                }
            
            elif platform == "instagram":
                options['http_headers'] = {
                    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15',
                }
            
            # Extraction asynchrone
            loop = asyncio.get_event_loop()
            def extract_info():
                with yt_dlp.YoutubeDL(options) as ydl:
                    return ydl.extract_info(url, download=False)
            
            info = await loop.run_in_executor(None, extract_info)
            
            if not info:
                return None
            
            # Formater les informations
            return {
                'title': info.get('title', 'Sans titre'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail'),
                'uploader': info.get('uploader', 'Inconnu'),
                'view_count': info.get('view_count', 0),
                'platform': platform,
                'formats': self._extract_formats(info, platform),
            }
        
        except Exception as e:
            logger.exception(f"Erreur extraction info (plateforme={platform}, url={url})")
            return None
    
    def _extract_formats(self, info: Dict, platform: str) -> List[Dict]:
        """Extrait les formats disponibles"""
        if platform != "youtube":
            return [{'quality': 'best', 'label': 'Meilleure qualité'}]
        
        formats = []
        seen_heights = set()
        
        for fmt in info.get('formats', []):
            height = fmt.get('height')
            if height and height not in seen_heights and fmt.get('vcodec') != 'none':
                seen_heights.add(height)
                formats.append({
                    'quality': str(height),
                    'label': f'{height}p',
                    'ext': fmt.get('ext', 'mp4')
                })
        
        if not formats:
            formats.append({
                'quality': 'best',
                'label': 'Meilleure qualité disponible'
            })
        else:
            formats.sort(key=lambda x: int(x['quality']) if x['quality'].isdigit() else 0, reverse=True)
        
        formats.append({
            'quality': 'audio',
            'label': 'Audio seulement (MP3)'
        })
        
        return formats
    
    async def download_video(self, url: str, platform: str, 
                           quality: str, user_id: int) -> Optional[Path]:
        """
        Télécharge une vidéo avec yt-dlp ou API alternative (TikTok)
        """
        # ✅ TIKTOK : Essayer l'API EN PREMIER
        if platform == "tiktok":
            print("🎵 TikTok détecté - Tentative API...")
            
            filename = f"{user_id}_{int(asyncio.get_event_loop().time())}.mp4"
            output_path = self.downloads_dir / filename
            
            try:
                success = await TikTokAPI.download(url, output_path)
                if success and output_path.exists():
                    return output_path
                else:
                    logger.warning(f"API TikTok échouée (user={user_id}), essai yt-dlp en repli...")
            except Exception as e:
                logger.warning(f"Erreur API TikTok: {e}, essai yt-dlp en repli...")
        
        # Fallback : yt-dlp pour toutes les plateformes
        try:
            filename = f"{user_id}_{int(asyncio.get_event_loop().time())}.%(ext)s"
            output_path = str(self.downloads_dir / filename)
            
            options = self._build_ytdlp_options(platform, quality, output_path)
            
            loop = asyncio.get_event_loop()
            def download():
                with yt_dlp.YoutubeDL(options) as ydl:
                    ydl.download([url])
            
            await loop.run_in_executor(None, download)
            
            downloaded_files = list(self.downloads_dir.glob(f"{user_id}_*"))
            if downloaded_files:
                return max(downloaded_files, key=lambda p: p.stat().st_mtime)
            
            # yt-dlp n'a levé aucune exception, mais aucun fichier ne correspond
            # au motif attendu : cas silencieux à surveiller explicitement
            # (ex: max_filesize dépassé, format introuvable, fichier écrit
            # ailleurs). Sans ce log, cette situation ne laissait AUCUNE trace.
            logger.warning(
                f"yt-dlp n'a levé aucune erreur mais aucun fichier '{user_id}_*' "
                f"trouvé dans {self.downloads_dir} (plateforme={platform}, url={url})"
            )
            return None
        
        except Exception as e:
            logger.exception(f"Erreur téléchargement (plateforme={platform}, url={url}, user={user_id})")
            return None
    
    async def cleanup_file(self, file_path: Path, delay: int = 20):
        """Supprime un fichier après un délai"""
        await asyncio.sleep(delay)
        try:
            if file_path.exists():
                file_path.unlink()
                print(f"✅ Fichier supprimé: {file_path.name}")
        except Exception as e:
            print(f"❌ Erreur suppression: {e}")

# Instance globale
downloader = Downloader()