"""YouTube client module using yt-dlp Python SDK.

This module provides a clean Python API for YouTube video operations,
replacing the previous subprocess-based CLI invocations.
"""

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Optional

import yt_dlp

from api.constants import (
    DEFAULT_YOUTUBE_INFO_TIMEOUT,
    DEFAULT_YOUTUBE_DOWNLOAD_TIMEOUT,
    SUBTITLE_DOWNLOAD_TIMEOUT,
    SUBTITLE_LANG_PRIORITY,
)


@dataclass
class VideoInfo:
    """YouTube video information."""

    id: str
    title: str
    duration: Optional[int] = None
    thumbnail: Optional[str] = None
    uploader: Optional[str] = None
    description: Optional[str] = None

    @property
    def duration_formatted(self) -> str:
        """Format duration as HH:MM:SS."""
        if self.duration is None:
            return "Unknown"
        return str(timedelta(seconds=self.duration))


@dataclass
class SubtitleTrack:
    """Subtitle track information."""

    lang: str
    name: str
    is_auto: bool = False

    def __str__(self) -> str:
        suffix = " (auto)" if self.is_auto else ""
        return f"{self.lang} - {self.name}{suffix}"


@dataclass
class SubtitleInfo:
    """Available subtitle information."""

    manual: list[SubtitleTrack] = field(default_factory=list)
    auto: list[SubtitleTrack] = field(default_factory=list)

    @property
    def has_subtitles(self) -> bool:
        """Check if any subtitles are available."""
        return bool(self.manual or self.auto)

    @property
    def available_langs(self) -> set[str]:
        """Get all available language codes."""
        return {t.lang for t in self.manual + self.auto}

    def get_best_track(self, preferred_langs: list[str]) -> Optional[SubtitleTrack]:
        """Get the best subtitle track based on language priority.

        Args:
            preferred_langs: List of preferred language codes in priority order

        Returns:
            Best matching subtitle track or None
        """
        for lang in preferred_langs:
            for track in self.manual:
                if track.lang == lang:
                    return track
        for lang in preferred_langs:
            for track in self.auto:
                if track.lang == lang:
                    return track
        return None


class YouTubeClientError(Exception):
    """Base exception for YouTube client errors."""
    pass


class VideoNotFoundError(YouTubeClientError):
    """Video not found or not accessible."""
    pass


class SubtitleNotAvailableError(YouTubeClientError):
    """Requested subtitle not available."""
    pass


class DownloadError(YouTubeClientError):
    """Download failed."""
    pass


class InfoExtractionError(YouTubeClientError):
    """Failed to extract video information."""
    pass


class YouTubeClient:
    """yt-dlp Python SDK wrapper.

    Provides a clean interface for YouTube video operations including
    video info extraction, audio download, and subtitle handling.
    """

    def __init__(
        self,
        *,
        timeout: int = DEFAULT_YOUTUBE_INFO_TIMEOUT,
        download_timeout: int = DEFAULT_YOUTUBE_DOWNLOAD_TIMEOUT,
        subtitle_timeout: int = SUBTITLE_DOWNLOAD_TIMEOUT,
        proxy: Optional[str] = None,
        cookies_file: Optional[str] = None,
    ):
        self.timeout = timeout
        self.download_timeout = download_timeout
        self.subtitle_timeout = subtitle_timeout
        self.proxy = proxy
        self.cookies_file = cookies_file

    def _get_base_opts(self) -> dict:
        """Get base yt-dlp configuration options."""
        opts = {
            "quiet": True,
            "nocheckcertificate": True,
            "noplaylist": True,
        }
        if self.proxy:
            opts["proxy"] = self.proxy
        if self.cookies_file:
            opts["cookiefile"] = self.cookies_file
        return opts

    def get_video_info(self, url: str) -> VideoInfo:
        """Get detailed video information.

        Args:
            url: YouTube video URL

        Returns:
            VideoInfo object with video details

        Raises:
            VideoNotFoundError: Video not found or not accessible
            InfoExtractionError: Failed to extract video information
        """
        opts = self._get_base_opts()
        opts["extract_flat"] = False

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)

                if info is None:
                    raise VideoNotFoundError(f"Video not found: {url}")

                return VideoInfo(
                    id=info.get("id", "unknown"),
                    title=info.get("title", "Unknown"),
                    duration=info.get("duration"),
                    thumbnail=info.get("thumbnail"),
                    uploader=info.get("uploader"),
                    description=info.get("description"),
                )
        except yt_dlp.utils.DownloadError as e:
            raise VideoNotFoundError(f"Video not accessible: {url}") from e
        except YouTubeClientError:
            raise
        except Exception as e:
            raise InfoExtractionError(f"Failed to extract info: {e}") from e

    def download_audio(
        self,
        url: str,
        output_dir: str = "/tmp",
        audio_quality: str = "128K",
    ) -> tuple[str, str]:
        """Download YouTube video audio.

        Args:
            url: YouTube video URL
            output_dir: Output directory for downloaded file
            audio_quality: Audio quality (e.g., "128K", "192K")

        Returns:
            Tuple of (audio file path, video title)

        Raises:
            VideoNotFoundError: Video not found
            DownloadError: Download failed
        """
        info = self.get_video_info(url)
        output_path = f"{output_dir}/{info.id}.mp3"

        opts = self._get_base_opts()
        opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": audio_quality,
            }],
            "outtmpl": f"{output_dir}/{info.id}.%(ext)s",
        })

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            return output_path, info.title
        except yt_dlp.utils.DownloadError as e:
            raise DownloadError(f"Failed to download audio: {e}") from e
        except Exception as e:
            raise DownloadError(f"Download failed: {e}") from e

    def list_subtitles(self, url: str) -> SubtitleInfo:
        """List available subtitles for a video.

        Args:
            url: YouTube video URL

        Returns:
            SubtitleInfo object with available subtitles
        """
        opts = self._get_base_opts()
        opts["listsubtitles"] = True
        opts["skip_download"] = True

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)

                subtitle_info = SubtitleInfo()

                if info and info.get("subtitles"):
                    for lang, tracks in info["subtitles"].items():
                        name = tracks[0].get("name", lang) if tracks else lang
                        subtitle_info.manual.append(SubtitleTrack(
                            lang=lang,
                            name=name,
                            is_auto=False,
                        ))

                if info and info.get("automatic_captions"):
                    for lang, tracks in info["automatic_captions"].items():
                        name = tracks[0].get("name", lang) if tracks else lang
                        subtitle_info.auto.append(SubtitleTrack(
                            lang=lang,
                            name=name,
                            is_auto=True,
                        ))

                return subtitle_info

        except Exception:
            return SubtitleInfo()

    def download_subtitles(
        self,
        url: str,
        lang: str,
        output_dir: str = "/tmp",
    ) -> Optional[str]:
        """Download subtitles for a specific language.

        Args:
            url: YouTube video URL
            lang: Language code (e.g., "zh-Hant", "en")
            output_dir: Output directory

        Returns:
            Path to downloaded VTT file or None if failed
        """
        output_template = f"{output_dir}/%(id)s.%(ext)s"

        opts = self._get_base_opts()
        opts.update({
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": [lang],
            "subtitlesformat": "vtt/best",
            "outtmpl": output_template,
        })

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)

                if info is None:
                    return None

                video_id = info.get("id")
                expected_file = f"{output_dir}/{video_id}.{lang}.vtt"

                import os
                if os.path.exists(expected_file):
                    return expected_file

                for file in os.listdir(output_dir):
                    if file.startswith(video_id) and file.endswith(".vtt"):
                        return f"{output_dir}/{file}"

                return None

        except Exception:
            return None

    def get_best_subtitles(
        self,
        url: str,
        preferred_langs: Optional[list[str]] = None,
        output_dir: str = "/tmp",
    ) -> Optional[str]:
        """Download best available subtitles based on language priority.

        Args:
            url: YouTube video URL
            preferred_langs: Language priority list (uses SUBTITLE_LANG_PRIORITY if None)
            output_dir: Output directory

        Returns:
            Path to downloaded VTT file or None if failed
        """
        if preferred_langs is None:
            preferred_langs = list(SUBTITLE_LANG_PRIORITY)

        subtitle_info = self.list_subtitles(url)

        if not subtitle_info.has_subtitles:
            return None

        best_track = subtitle_info.get_best_track(preferred_langs)

        if best_track is None:
            all_langs = list(subtitle_info.available_langs)
            if all_langs:
                best_track = SubtitleTrack(lang=all_langs[0], name=all_langs[0])
            else:
                return None

        return self.download_subtitles(
            url=url,
            lang=best_track.lang,
            output_dir=output_dir,
        )