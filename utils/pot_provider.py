# -*- coding: utf-8 -*-
"""
Démarrage automatique du provider PO Token (bgutil-ytdlp-pot-provider),
requis par YouTube depuis 2025 pour contourner le blocage
"Sign in to confirm you're not a bot" (voir utils/downloader.py et
https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide).

Le plugin Python (déjà dans requirements.txt) parle en HTTP à un petit
serveur Node.js qui génère les tokens. Ce module clone/installe ce
serveur une seule fois au premier démarrage, puis le lance et le
surveille en arrière-plan pendant toute la vie du bot.

Si Node.js n'est pas disponible sur la plateforme d'hébergement, le
provider est simplement désactivé : yt-dlp continue de fonctionner
normalement, avec un peu moins de résistance face aux blocages anti-bot
YouTube (comportement identique à avant cette fonctionnalité).
"""
import asyncio
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

PROVIDER_VERSION = "1.2.2"
PROVIDER_REPO = "https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git"
PROVIDER_DIR = Path(__file__).resolve().parent.parent / "bgutil-ytdlp-pot-provider"
SERVER_DIR = PROVIDER_DIR / "server"
SERVER_ENTRYPOINT = SERVER_DIR / "build" / "main.js"
PROVIDER_PORT = 4416

_process: asyncio.subprocess.Process | None = None
_watchdog_task: asyncio.Task | None = None
_enabled = False


async def _run(cmd: list[str], cwd: Path | None = None) -> bool:
    """Exécute une commande, log stdout/stderr, retourne True si succès."""
    logger.info(f"🍪 POT provider: exécution de `{' '.join(cmd)}`" + (f" (dans {cwd})" if cwd else ""))
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, cwd=str(cwd) if cwd else None,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
        output, _ = await proc.communicate()
        if proc.returncode != 0:
            logger.warning(
                f"🍪 POT provider: `{cmd[0]}` a échoué (code {proc.returncode})\n"
                f"{output.decode(errors='replace')[-2000:]}"
            )
            return False
        return True
    except FileNotFoundError:
        logger.warning(f"🍪 POT provider: commande introuvable ({cmd[0]}) — ignoré.")
        return False


async def _ensure_installed() -> bool:
    """Clone et build le serveur si nécessaire. Idempotent."""
    if SERVER_ENTRYPOINT.exists():
        return True

    if not shutil.which("git"):
        logger.warning("🍪 POT provider: git introuvable, installation impossible.")
        return False
    if not shutil.which("node"):
        logger.warning(
            "🍪 POT provider: Node.js introuvable sur ce serveur. "
            "YouTube pourrait bloquer certains téléchargements ('Sign in to "
            "confirm you're not a bot') faute de PO Token. Installez Node.js "
            "18+ (voir render.yaml) pour activer cette protection."
        )
        return False

    logger.info(f"🍪 POT provider: première installation (clone {PROVIDER_VERSION})...")
    if PROVIDER_DIR.exists():
        shutil.rmtree(PROVIDER_DIR, ignore_errors=True)

    ok = await _run([
        "git", "clone", "--single-branch", "--branch", PROVIDER_VERSION,
        "--depth", "1", PROVIDER_REPO, str(PROVIDER_DIR),
    ])
    if not ok:
        return False

    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm:
        logger.warning("🍪 POT provider: npm introuvable, installation impossible.")
        return False

    if not await _run([npm, "install"], cwd=SERVER_DIR):
        return False
    if not await _run([npm, "exec", "--", "tsc"], cwd=SERVER_DIR):
        return False

    if not SERVER_ENTRYPOINT.exists():
        logger.warning("🍪 POT provider: build terminé mais main.js introuvable, abandon.")
        return False

    logger.info("✅ POT provider: installation terminée.")
    return True


async def _spawn_server() -> asyncio.subprocess.Process | None:
    node = shutil.which("node")
    if not node:
        return None
    try:
        return await asyncio.create_subprocess_exec(
            node, str(SERVER_ENTRYPOINT), "--port", str(PROVIDER_PORT),
            cwd=str(SERVER_DIR),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
    except Exception:
        logger.exception("🍪 POT provider: échec du démarrage du serveur.")
        return None


async def _watchdog():
    """Redémarre le serveur automatiquement s'il plante, avec backoff."""
    global _process
    backoff = 5
    while _enabled:
        if _process is None or _process.returncode is not None:
            _process = await _spawn_server()
            if _process:
                logger.info(f"🍪 POT provider: serveur démarré (PID {_process.pid}, port {PROVIDER_PORT}).")
                backoff = 5
            else:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 300)
                continue
        await asyncio.sleep(15)


async def start():
    """À appeler une fois au démarrage du bot (post_init)."""
    global _enabled, _watchdog_task
    installed = await _ensure_installed()
    if not installed:
        logger.info("🍪 POT provider: désactivé (yt-dlp fonctionnera sans PO Token).")
        return
    _enabled = True
    _watchdog_task = asyncio.create_task(_watchdog())


async def stop():
    """À appeler à l'arrêt du bot pour terminer proprement le serveur."""
    global _enabled, _process, _watchdog_task
    _enabled = False
    if _watchdog_task:
        _watchdog_task.cancel()
    if _process and _process.returncode is None:
        _process.terminate()
        try:
            await asyncio.wait_for(_process.wait(), timeout=10)
        except asyncio.TimeoutError:
            _process.kill()
    _process = None
