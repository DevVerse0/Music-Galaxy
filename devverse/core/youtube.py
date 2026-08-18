# Copyright (c) 2025 Delete_ee
# Licensed under the MIT License.
# This file is part of Delete_ee

import os
import shutil
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

    async def save_cookies(self, url) -> None:
        """Download cookies.txt from a URL (or list of URLs) for yt-dlp."""
        import os
        os.makedirs(os.path.dirname(config.COOKIES_FILE) or ".", exist_ok=True)
        session = await self._get_session()
        urls = url if isinstance(url, (list, tuple)) else [url]
        for u in urls:
            try:
                async with session.get(u, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        logger.error(f"Failed to download cookies: {resp.status}")
                        continue
                    data = await resp.text()
            except Exception as e:
                logger.error(f"Cookies fetch error: {e!r}")
                continue
            with open(config.COOKIES_FILE, "w", encoding="utf-8") as f:
                f.write(data)
            logger.info("Cookies saved to %s", config.COOKIES_FILE)
            return

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

    async def _download_via_api(self, song_id: str, video: bool = False) -> str | None:
        """Download a song using the configured external download API."""
        import os
        from devverse import config

        api_url = (config.DOWNLOAD_API_URL or "").strip()
        if not api_url:
            return None

        if "rapidapi.com" in api_url:
            return await self._download_via_rapidapi(song_id, video, api_url)

        video_url = f"https://www.youtube.com/watch?v={song_id}"
        ext = "mp4" if video else "mp3"
        out_path = f"downloads/{song_id}.{ext}"
        os.makedirs("downloads", exist_ok=True)

        params = {"url": video_url, "format": ext}
        headers = {}
        if config.DOWNLOAD_API_KEY:
            headers["X-API-Key"] = config.DOWNLOAD_API_KEY

        session = await self._get_session()
        timeout = aiohttp.ClientTimeout(total=60)
        try:
            async with session.get(
                api_url, params=params, headers=headers, timeout=timeout
            ) as resp:
                if resp.status != 200:
                    logger.error(
                        f"Download API error: {resp.status} {resp.reason}"
                    )
                    return None
                ctype = resp.headers.get("Content-Type", "")
                if "json" in ctype:
                    data = await resp.json()
                    file_url = (
                        data.get("download_url")
                        or data.get("url")
                        or data.get("link")
                        or data.get("downloadUrl")
                        or (data.get("data") or {}).get("url")
                    )
                    if not file_url:
                        logger.error(f"Download API JSON missing url: {data}")
                        return None
                    if data.get("ext") and not video:
                        ext = data["ext"].lstrip(".") or ext
                        out_path = f"downloads/{song_id}.{ext}"
                    await self._stream_to_file(session, file_url, out_path)
                else:
                    import os as _os
                    _os.makedirs("downloads", exist_ok=True)
                    with open(out_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(256 * 1024):
                            f.write(chunk)
        except Exception as e:
            logger.error(f"Download API Error: {e}")
            return None

        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            from devverse import db
            await db.register_file(
                song_id=song_id,
                storage_path=out_path,
                public_url="local",
                song_name=song_id,
            )
            return out_path
        return None

    async def _stream_to_file(self, session, file_url: str, out_path: str) -> None:
        """Download a file URL to disk with a browser UA and generous timeout."""
        import os
        stream_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
            )
        }
        stream_timeout = aiohttp.ClientTimeout(total=600)
        async with session.get(
            file_url, headers=stream_headers, timeout=stream_timeout
        ) as f_resp:
            if f_resp.status != 200:
                logger.error(f"Download API file error: {f_resp.status}")
                raise RuntimeError(f"file download returned {f_resp.status}")
            with open(out_path, "wb") as f:
                async for chunk in f_resp.content.iter_chunked(256 * 1024):
                    f.write(chunk)

    async def _download_via_rapidapi(self, song_id: str, video: bool, api_url: str) -> str | None:
        """Download via the RapidAPI 'youtube-media-downloader' API (with retries)."""
        for attempt in range(1, 4):
            try:
                path = await self._rapidapi_attempt(song_id, video, api_url)
                if path:
                    return path
            except Exception as e:
                logger.error(f"RapidAPI attempt {attempt}/3 error: {e!r}")
            logger.warning(f"RapidAPI attempt {attempt}/3 failed, retrying...")
        return None

    async def _rapidapi_attempt(self, song_id: str, video: bool, api_url: str) -> str | None:
        """Single RapidAPI fetch + download attempt."""
        import os
        from urllib.parse import urlparse
        from devverse import config

        os.makedirs("downloads", exist_ok=True)
        headers = {
            "Content-Type": "application/json",
            "x-rapidapi-host": urlparse(api_url).netloc,
            "x-rapidapi-key": config.DOWNLOAD_API_KEY or "",
        }
        params = {
            "videoId": song_id,
            "urlAccess": "normal",
            "videos": "auto",
            "audios": "auto",
        }

        session = await self._get_session()
        api_timeout = aiohttp.ClientTimeout(total=60)
        async with session.get(
            api_url, params=params, headers=headers, timeout=api_timeout
        ) as resp:
            if resp.status != 200:
                logger.error(f"RapidAPI error: {resp.status} {resp.reason}")
                return None
            data = await resp.json()

        audios = (data.get("audios") or {}).get("items") or []
        videos = (data.get("videos") or {}).get("items") or []

        if video:
            target = None
            for it in videos:
                mime = it.get("mimeType", "")
                if it.get("quality") == "720p" and "video/mp4" in mime and "mp4a" in mime:
                    target = it
                    break
            if not target:
                for it in videos:
                    mime = it.get("mimeType", "")
                    if "video/mp4" in mime and "mp4a" in mime:
                        target = it
                        break
            if not target:
                for it in videos:
                    if "video/mp4" in it.get("mimeType", ""):
                        target = it
                        break
            if not target and videos:
                target = videos[0]
            if not target:
                logger.error("RapidAPI: no video stream found")
                return None
            ext = "mp4"
        else:
            target = None
            for it in audios:
                if "audio/mp4" in it.get("mimeType", ""):
                    target = it
                    break
            if not target and audios:
                target = audios[0]
            if not target:
                logger.error("RapidAPI: no audio stream found")
                return None
            mime = target.get("mimeType", "")
            ext = "m4a" if "audio/mp4" in mime else "opus"

        file_url = target.get("url")
        if not file_url:
            logger.error("RapidAPI: stream has no url")
            return None

        out_path = f"downloads/{song_id}.{ext}"
        stream_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
            )
        }
        stream_timeout = aiohttp.ClientTimeout(total=600)
        async with session.get(
            file_url, headers=stream_headers, timeout=stream_timeout
        ) as f_resp:
            if f_resp.status != 200:
                logger.error(f"RapidAPI file error: {f_resp.status}")
                raise RuntimeError(f"file download returned {f_resp.status}")
            with open(out_path, "wb") as f:
                async for chunk in f_resp.content.iter_chunked(256 * 1024):
                    f.write(chunk)

        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            from devverse import db
            await db.register_file(
                song_id=song_id,
                storage_path=out_path,
                public_url="local",
                song_name=song_id,
            )
            return out_path
        return None

    async def download(self, song_id: str, video: bool = False) -> str | None:
        if config.DOWNLOAD_API:
            path = await self._download_via_api(song_id, video)
            if path:
                return path
            logger.warning("Download API failed, falling back to yt-dlp...")

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
                "no_warnings": True,
                "quiet": True,
                "no_playlist": True,
                "geo_bypass": True,
                "fixup": "detect_or_warn",
                "extractor_args": {
                    "youtube": {
                        "player_client": ["web", "mweb", "android"],
                        "player_skip": ["configs"],
                    }
                },
                "http_headers": {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                    ),
                    "Referer": "https://www.youtube.com/",
                    "Origin": "https://www.youtube.com",
                },
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

            js_runtimes = {}
            for runtime in ("node", "deno", "bun"):
                if shutil.which(runtime):
                    js_runtimes[runtime] = {}
            if js_runtimes:
                ydl_opts["js_runtimes"] = js_runtimes

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
            logger.error(f"YouTube Download produced no file for {song_id}")
        except Exception as e:
            logger.error(f"YouTube Download Error: {e!r}")

        return None

