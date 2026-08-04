import os
import shutil
from pathlib import Path

from devverse import logger


def ensure_dirs():
    """
    Ensure that the necessary directories exist.
    """
    if not shutil.which("ffmpeg"):
        # Common Windows paths from winget/choco/manual
        common_paths = [
            "C:\\ffmpeg\\bin\\ffmpeg.exe",
            os.path.expandvars("%LOCALAPPDATA%\\Microsoft\\WinGet\\Packages\\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\\ffmpeg-8.1-full_build\\bin\\ffmpeg.exe"),
            "tools\\ffmpeg.exe"
        ]
        found = False
        for path in common_paths:
            if os.path.exists(path):
                # Add it to runtime path so subprocesses can find it
                os.environ["PATH"] += os.pathsep + os.path.dirname(path)
                found = True
                break
        
        if not found:
            raise RuntimeError("FFmpeg must be installed and accessible in the system PATH.")



    for directory in ["cache", "downloads", "devverse/cookies"]:
        Path(directory).mkdir(parents=True, exist_ok=True)
    logger.info("Cache directories updated.")


async def auto_clean():
    return  # Auto-cleanup permanently disabled by user


