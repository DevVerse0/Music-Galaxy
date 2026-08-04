# Copyright (c) 2025 Delete_ee
# Licensed under the MIT License.
# This file is part of Delete_ee

import os
import aiohttp
import asyncio
from typing import List, Union
from py_yt import VideosSearch, Playlist

from devverse import config, logger
from devverse.helpers import Media, Track, utils


class YouTube:
    def __init__(self):
        self._session = None

    async def _get_api(self):
        from devverse import db
        return await db.get_api()

    async def _get_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    def valid(self, url: str) -> bool:
        """Check if a URL is a valid YouTube URL."""
        if not url:
            return False
        return "youtube.com" in url or "youtu.be" in url

    def invalid(self, url: str) -> bool:
        """Check if a URL is NOT a valid YouTube URL."""
        return not self.valid(url)

    async def search(self, query: str, msg_id: int = 0, video: bool = False) -> Track | None:
        """Search for a video on YouTube."""
        try:
            search = VideosSearch(query, limit=12)
            results = (await search.next()).get("result", [])
            if not results:
                return None
            
            # Logic: Try to find a video that is likely a song (less than 12 mins)
            # If not found, fall back to any video within the global duration limit.
            video_data = None
            for res in results:
                duration_str = res.get("duration")
                if not duration_str:
                    continue
                d_sec = utils.to_seconds(duration_str)
                if 10 < d_sec <= 720: # 12 minutes
                    video_data = res
                    break
            
            if not video_data:
                for res in results:
                    d_sec = utils.to_seconds(res.get("duration", "0:00"))
                    if 0 < d_sec <= config.DURATION_LIMIT:
                        video_data = res
                        break
            
            if not video_data:
                video_data = results[0]

            return Track(
                id=video_data.get("id"),
                title=video_data.get("title"),
                duration=video_data.get("duration"),
                duration_sec=utils.to_seconds(video_data.get("duration")),
                url=video_data.get("link"),
                thumbnail=video_data.get("thumbnails", [{}])[0].get("url"),
                channel_name=video_data.get("channel", {}).get("name"),
                view_count=video_data.get("viewCount", {}).get("short"),
                video=video,
            )
        except Exception as e:
            logger.error(f"YouTube Search Error: {e}")
            return None

    async def playlist(self, limit: int, mention: str, url: str, video: bool = False) -> List[Track]:
        """Fetch tracks from a YouTube playlist."""
        tracks = []
        try:
            playlist = Playlist(url)
            while playlist.hasMoreVideos and len(tracks) < limit:
                await playlist.getNextVideos()
            
            for video_data in playlist.videos[:limit]:
                tracks.append(Track(
                    id=video_data.get("id"),
                    title=video_data.get("title"),
                    duration=video_data.get("duration"),
                    duration_sec=utils.to_seconds(video_data.get("duration")),
                    url=video_data.get("link"),
                    thumbnail=video_data.get("thumbnails", [{}])[0].get("url"),
                    channel_name=video_data.get("channel", {}).get("name"),
                    video=video,
                    user=mention,
                ))
        except Exception as e:
            logger.error(f"YouTube Playlist Error: {e}")
        return tracks

    async def download(self, song_id: str, video: bool = False) -> str | None:
        import glob
        import yt_dlp
        url = f"https://www.youtube.com/watch?v={song_id}"
        out_template = f"downloads/{song_id}"

        try:
            ydl_opts = {
                "format": "bestvideo[height<=720]+bestaudio/best[height<=720]" if video else "bestaudio[abr<=128]/bestaudio",
                "outtmpl": f"{out_template}.%(ext)s",
                "concurrent_fragments": 5,
                "no_check_certificate": True,
                "extractor_retries": 3,
                "ignoreerrors": True,
                "no_warnings": True,
                "quiet": True,
                "no_playlist": True,
                "fixup": "detect_or_warn",
            }

            if video:
                ydl_opts["merge_output_format"] = "mp4"
            else:
                # Modern yt-dlp API: legacy extract_audio/audio_format params are gone
                ydl_opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "128",
                }]

            if os.path.exists(config.COOKIES_FILE):
                ydl_opts["cookiefile"] = config.COOKIES_FILE

            loop = asyncio.get_event_loop()
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                await loop.run_in_executor(None, ydl.download, [url])

            result = sorted(
                (
                    f
                    for f in glob.glob(f"{out_template}.*")
                    if not utils.is_download_fragment(f)
                ),
                key=os.path.getmtime,
                reverse=True,
            )
            if result:
                from devverse import db
                await db.register_file(
                    song_id=song_id,
                    storage_path=result[0],
                    public_url="local",
                    song_name=song_id
                )
                return result[0]
        except Exception as e:
            logger.error(f"YouTube Download Error: {e}")

        return None

