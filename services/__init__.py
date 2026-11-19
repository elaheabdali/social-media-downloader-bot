"""Services package for X/Twitter, Instagram, YouTube, and trending GIFs."""

from services.downloader import (
    DownloaderError,
    MediaItem,
    PendingDownload,
    PendingDownloadStore,
    VideoQuality,
    download_audio_mp3,
    download_media,
    extract_x_url,
    inspect_url,
)
from services.trending import (
    CATEGORY_LABEL_KEYS,
    VALID_CATEGORIES,
    get_next_trending_gif,
)
from services.youtube import (
    YouTubeChannelResult,
    YouTubeVideoEntry,
    fetch_channel_latest_videos,
    is_youtube_channel_url,
    is_youtube_url,
    resolve_channel_id_from_url,
    search_youtube_channels,
)

__all__ = [
    "CATEGORY_LABEL_KEYS",
    "DownloaderError",
    "MediaItem",
    "PendingDownload",
    "PendingDownloadStore",
    "VALID_CATEGORIES",
    "VideoQuality",
    "YouTubeChannelResult",
    "YouTubeVideoEntry",
    "download_audio_mp3",
    "download_media",
    "extract_x_url",
    "fetch_channel_latest_videos",
    "get_next_trending_gif",
    "inspect_url",
    "is_youtube_channel_url",
    "is_youtube_url",
    "resolve_channel_id_from_url",
    "search_youtube_channels",
]