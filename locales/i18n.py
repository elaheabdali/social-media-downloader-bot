"""Bilingual (English & Persian) message catalog and translation helpers."""

from __future__ import annotations

from typing import Any

# Persistent ReplyKeyboard button labels (bilingual so users can always tap them)
BTN_TRENDING = "🔥 Trending GIFs / گیف‌های ترند"
BTN_YOUTUBE = "📺 YouTube Channel / کانال یوتیوب"
BTN_LANGUAGE = "🌐 Language / تغییر زبان"
BTN_HELP = "ℹ️ Help / راهنما"

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "welcome": (
            "👋 Hello <b>{name}</b>!\n\n"
            "I am your all-in-one media downloader for <b>X (Twitter)</b>, <b>Instagram</b>, and <b>YouTube</b>:\n"
            "• <b>YouTube:</b> Videos (multi-quality), Shorts, MP3 Audio & Channel Latest Videos\n"
            "• <b>X / Twitter:</b> GIFs & Videos (original quality or convert to GIF)\n"
            "• <b>Instagram:</b> Reels, Video/Photo Posts, Carousels & Profile Pictures\n"
            "• <b>Trending GIFs:</b> Persian & English Twitter trends, Romantic & Meme GIFs\n\n"
            "Paste any link, search a YouTube channel, or browse Trending GIFs:"
        ),
        "choose_language": "🌐 Please choose your preferred language:",
        "language_updated": "✅ Language set to <b>English</b>.\nSend any X, Instagram, or YouTube link to start!",
        "help": (
            "📖 <b>How to use this bot</b>\n\n"
            "1. <b>Download Media:</b> Paste any link from <b>YouTube</b>, <b>X (Twitter)</b>, or <b>Instagram</b>.\n"
            "2. <b>Quality & Audio:</b> For videos, choose your preferred resolution, extract <b>MP3 Audio</b>, "
            "or convert X videos to <b>GIF</b>.\n"
            "3. <b>YouTube Channels:</b> Tap <b>📺 YouTube Channel</b> (or /youtube) and type a channel name "
            "(e.g., <code>MKBHD</code>) or paste a channel link to view and download its latest videos.\n"
            "4. <b>Trending GIFs:</b> Tap <b>🔥 Trending GIFs</b> (or /trending) for curated trending GIFs.\n\n"
            "Use /language anytime to switch between English and Persian."
        ),
        "trending_menu_title": (
            "🔥 <b>Trending GIFs</b>\n\n"
            "Choose a category to receive fresh & trending GIFs:"
        ),
        "cat_fa_twitter": "🇮🇷 ترند توییتر فارسی (Persian X)",
        "cat_en_twitter": "🌍 English Twitter Trending",
        "cat_romantic": "❤️ Romantic & Love GIFs",
        "cat_memes": "😂 Memes, Jokes & Funny",
        "fetching_trending": "🔍 Finding a fresh trending GIF...",
        "btn_next_gif": "🔄 Next GIF",
        "btn_change_category": "📂 Categories",
        "trending_caption": "🔥 <b>{category}</b>\n✅ @{bot_username}",
        "err_trending_empty": "😕 Could not fetch a trending GIF right now. Please try again in a moment.",
        "yt_channel_prompt": (
            "📺 <b>YouTube Channel Search</b>\n\n"
            "Enter the name or <code>@handle</code> of a YouTube channel (or paste its link):\n"
            "<i>Example:</i> <code>Kurzgesagt</code> or <code>@MKBHD</code>"
        ),
        "yt_searching_channel": "🔍 Searching YouTube channels...",
        "yt_fetching_videos": "📡 Fetching latest videos from channel...",
        "yt_select_channel": "📺 <b>Matching channels found:</b>\nSelect a channel to view its latest videos:",
        "yt_latest_videos": (
            "📺 <b>{channel}</b>\n"
            "Latest uploaded videos — tap any video to download:"
        ),
        "yt_channel_not_found": "😕 No YouTube channel matched your search. Please try another name or paste the channel URL.",
        "yt_no_videos": "😕 Could not load recent videos for this channel right now.",
        "invalid_link": (
            "🔗 Please send a valid <b>YouTube</b>, <b>X (Twitter)</b>, or <b>Instagram</b> link, "
            "or use the menu buttons below.\n"
            "Examples:\n"
            "• <code>https://youtu.be/dQw4w9WgXcQ</code>\n"
            "• <code>https://x.com/username/status/123456789</code>\n"
            "• <code>https://www.instagram.com/reel/ABC123xyz/</code>"
        ),
        "inspecting": "🔍 Inspecting media...",
        "downloading_gif": "⬇️ Downloading GIF...",
        "converting_to_gif": "🎞 Downloading and converting video to GIF...",
        "uploading_gif": "📤 Uploading GIF to Telegram...",
        "downloading_photo": "⬇️ Downloading photo...",
        "uploading_photo": "📤 Uploading photo to Telegram...",
        "downloading_video": "⬇️ Downloading video ({quality})...",
        "uploading_video": "📤 Uploading video to Telegram...",
        "downloading_audio": "🎵 Extracting MP3 audio...",
        "uploading_audio": "📤 Uploading audio to Telegram...",
        "btn_convert_gif": "🎞 Convert to GIF",
        "btn_audio_mp3": "🎵 Audio (MP3)",
        "select_quality": (
            "🎬 <b>Video found!</b>\n"
            "Title: <i>{title}</i>\n\n"
            "Choose a video quality or format below:"
        ),
        "select_quality_limit_note": (
            "\n\n⚠️ <i>Note: Options marked with ⚠️ exceed Telegram's 50 MB Bot API limit. "
            "Please pick a lower resolution or download as MP3 Audio.</i>"
        ),
        "quality_btn": "{label}{size_part}",
        "quality_btn_over_limit": "⚠️ {label}{size_part} (>50 MB)",
        "file_too_large": (
            "❌ This file ({size_mb:.1f} MB) exceeds Telegram's 50 MB upload limit for bots.\n"
            "Please choose a lower resolution or download the MP3 audio."
        ),
        "session_expired": "⏳ This download menu has expired. Please send the link again.",
        "already_processing": "⏳ Please wait, your previous request is still being processed.",
        "multi_media_notice": "📦 Found {count} media items in this post. Processing...",
        "done_caption": "✅ Downloaded via @{bot_username}",
        "err_no_media": (
            "😕 No downloadable media was found in this link.\n"
            "(Text-only posts or Instagram Stories are not supported.)"
        ),
        "err_private_or_deleted": (
            "🔒 Could not access this content. It may be private, deleted, or unavailable."
        ),
        "err_age_restricted": (
            "🔞 This content is age-restricted or requires login verification to view."
        ),
        "err_rate_limit": "🚦 Rate limit reached. Please try again in a minute.",
        "err_gif_convert_failed": (
            "❌ Failed to convert the video to GIF. Please try downloading one of the video qualities instead."
        ),
        "err_audio_failed": "❌ Failed to extract audio from this video. Please try again.",
        "err_generic": "❌ Something went wrong while processing this link. Please try again later.",
        "err_upload_failed": "❌ Failed to upload the media to Telegram. Please try again.",
    },
    "fa": {
        "welcome": (
            "👋 سلام <b>{name}</b> عزیز!\n\n"
            "من ربات جامع دانلود از <b>یوتیوب (YouTube)</b>، <b>X (توییتر)</b> و <b>اینستاگرام</b> هستم:\n"
            "• <b>یوتیوب:</b> دانلود ویدیو با کیفیت‌های مختلف، شورتس، فایل صوتی MP3 و آخرین ویدیوهای کانال‌ها\n"
            "• <b>X / توییتر:</b> گیف‌ها و ویدیوها (دانلود کیفیت اصلی یا تبدیل ویدیو به GIF)\n"
            "• <b>اینستاگرام:</b> ریلز، پست‌های ویدیویی و عکسی، اسلایدها و عکس پروفایل\n"
            "• <b>گیف‌های ترند:</b> ترندهای توییتر فارسی و انگلیسی، عاشقانه و میم و فان\n\n"
            "لینک بفرستید یا از دکمه‌های منوی پایین استفاده کنید:"
        ),
        "choose_language": "🌐 لطفاً زبان مورد نظر خود را انتخاب کنید:",
        "language_updated": "✅ زبان ربات به <b>فارسی</b> تغییر یافت.\nمی‌توانید لینک یوتیوب، توییتر یا اینستاگرام بفرستید!",
        "help": (
            "📖 <b>راهنمای استفاده از ربات</b>\n\n"
            "۱. <b>دانلود مستقیم:</b> لینک پست یا ویدیو را از <b>یوتیوب</b>، <b>X (توییتر)</b> یا <b>اینستاگرام</b> بفرستید.\n"
            "۲. <b>انتخاب کیفیت و فرمت:</b> برای ویدیوها کیفیت دلخواه یا <b>دانلود صوتی (MP3)</b> را انتخاب کنید (ویدیوهای X را می‌توانید به <b>GIF</b> هم تبدیل کنید).\n"
            "۳. <b>جستجوی کانال یوتیوب:</b> دکمه <b>📺 کانال یوتیوب</b> (یا دستور /youtube) را بزنید و نام کانال (مثلاً <code>MKBHD</code> یا نام کانال فارسی) را بنویسید تا آخرین ویدیوهای آن نمایش داده شوند.\n"
            "۴. <b>گیف‌های ترند:</b> دکمه <b>🔥 گیف‌های ترند</b> (یا دستور /trending) را بزنید.\n\n"
            "برای تغییر زبان در هر زمان از دستور /language استفاده کنید."
        ),
        "trending_menu_title": (
            "🔥 <b>گیف‌های ترند و جدید</b>\n\n"
            "دسته‌بندی مورد نظر خود را انتخاب کنید تا گیف برایتان ارسال شود:"
        ),
        "cat_fa_twitter": "🇮🇷 ترند توییتر فارسی",
        "cat_en_twitter": "🌍 ترند توییتر انگلیسی",
        "cat_romantic": "❤️ عاشقانه و رمانتیک",
        "cat_memes": "😂 میم، جوک و فان",
        "fetching_trending": "🔍 در حال پیدا کردن گیف ترند جدید...",
        "btn_next_gif": "🔄 گیف بعدی",
        "btn_change_category": "📂 دسته‌بندی‌ها",
        "trending_caption": "🔥 <b>{category}</b>\n✅ @{bot_username}",
        "err_trending_empty": "😕 در حال حاضر دریافت گیف ترند با خطا مواجه شد. لطفاً چند لحظه دیگر دوباره تلاش کنید.",
        "yt_channel_prompt": (
            "📺 <b>جستجوی کانال یوتیوب</b>\n\n"
            "نام کانال یا آیدی (<code>@handle</code>) یوتیوب مورد نظر را بنویسید (یا لینک کانال را بفرستید):\n"
            "<i>مثال:</i> <code>Kurzgesagt</code> یا <code>@MKBHD</code>"
        ),
        "yt_searching_channel": "🔍 در حال جستجوی کانال در یوتیوب...",
        "yt_fetching_videos": "📡 در حال دریافت آخرین ویدیوهای کانال...",
        "yt_select_channel": "📺 <b>کانال‌های پیدا شده:</b>\nروی کانال مورد نظر بزنید تا آخرین ویدیوهایش نمایش داده شوند:",
        "yt_latest_videos": (
            "📺 <b>{channel}</b>\n"
            "آخرین ویدیوهای منتشر شده — برای دانلود روی هر ویدیو بزنید:"
        ),
        "yt_channel_not_found": "😕 کانالی با این نام در یوتیوب پیدا نشد. لطفاً نام دیگری بنویسید یا لینک مستقیم کانال را بفرستید.",
        "yt_no_videos": "😕 دریافت لیست ویدیوهای این کانال در حال حاضر ناموفق بود.",
        "invalid_link": (
            "🔗 لطفاً یک لینک معتبر از <b>یوتیوب</b>، <b>X (توییتر)</b> یا <b>اینستاگرام</b> ارسال کنید "
            "یا از دکمه‌های منوی پایین استفاده کنید.\n"
            "مثال‌ها:\n"
            "• <code>https://youtu.be/dQw4w9WgXcQ</code>\n"
            "• <code>https://x.com/username/status/123456789</code>\n"
            "• <code>https://www.instagram.com/reel/ABC123xyz/</code>"
        ),
        "inspecting": "🔍 در حال بررسی اطلاعات لینک...",
        "downloading_gif": "⬇️ در حال دانلود گیف...",
        "converting_to_gif": "🎞 در حال دانلود و تبدیل ویدیو به GIF...",
        "uploading_gif": "📤 در حال ارسال گیف به تلگرام...",
        "downloading_photo": "⬇️ در حال دانلود عکس...",
        "uploading_photo": "📤 در حال ارسال عکس به تلگرام...",
        "downloading_video": "⬇️ در حال دانلود ویدیو ({quality})...",
        "uploading_video": "📤 در حال ارسال ویدیو به تلگرام...",
        "downloading_audio": "🎵 در حال استخراج فایل صوتی MP3...",
        "uploading_audio": "📤 در حال ارسال فایل صوتی به تلگرام...",
        "btn_convert_gif": "🎞 تبدیل به GIF",
        "btn_audio_mp3": "🎵 دانلود صوتی (MP3)",
        "select_quality": (
            "🎬 <b>ویدیو پیدا شد!</b>\n"
            "عنوان: <i>{title}</i>\n\n"
            "کیفیت دلخواه ویدیو یا فرمت مورد نظر را انتخاب کنید:"
        ),
        "select_quality_limit_note": (
            "\n\n⚠️ <i>توجه: گزینه‌های دارای علامت ⚠️ بیشتر از محدودیت ۵۰ مگابایتی تلگرام هستند. "
            "لطفاً کیفیت پایین‌تر یا گزینه فایل صوتی MP3 را انتخاب کنید.</i>"
        ),
        "quality_btn": "{label}{size_part}",
        "quality_btn_over_limit": "⚠️ {label}{size_part} (بیش از ۵۰ مگابایت)",
        "file_too_large": (
            "❌ حجم این فایل ({size_mb:.1f} مگابایت) از محدودیت ۵۰ مگابایتی ربات‌های تلگرام بیشتر است.\n"
            "لطفاً کیفیت پایین‌تر یا فایل صوتی MP3 را انتخاب کنید."
        ),
        "session_expired": "⏳ اعتبار این منوی دانلود به پایان رسیده است. لطفاً لینک را دوباره بفرستید.",
        "already_processing": "⏳ لطفاً کمی صبر کنید؛ درخواست قبلی شما هنوز در حال پردازش است.",
        "multi_media_notice": "📦 {count} رسانه در این پست پیدا شد. در حال پردازش...",
        "done_caption": "✅ دانلود شده توسط @{bot_username}",
        "err_no_media": (
            "😕 هیچ رسانه قابل دانلودی در این لینک پیدا نشد.\n"
            "(پست‌های فقط متنی یا استوری‌های اینستاگرام پشتیبانی نمی‌شوند.)"
        ),
        "err_private_or_deleted": (
            "🔒 امکان دسترسی به این محتوا وجود ندارد. ممکن است محتوا خصوصی یا حذف شده باشد."
        ),
        "err_age_restricted": (
            "🔞 این محتوا دارای محدودیت سنی است یا برای مشاهده آن نیاز به احراز هویت دارد."
        ),
        "err_rate_limit": "🚦 در حال حاضر محدودیت موقت درخواست اعمال شده است. لطفاً یک دقیقه دیگر دوباره تلاش کنید.",
        "err_gif_convert_failed": (
            "❌ تبدیل ویدیو به GIF ناموفق بود. لطفاً یکی از کیفیت‌های اصلی ویدیو را دانلود کنید."
        ),
        "err_audio_failed": "❌ استخراج فایل صوتی از این ویدیو ناموفق بود. لطفاً دوباره تلاش کنید.",
        "err_generic": "❌ هنگام پردازش این لینک خطایی رخ داد. لطفاً کمی بعد دوباره امتحان کنید.",
        "err_upload_failed": "❌ ارسال فایل به تلگرام ناموفق بود. لطفاً دوباره تلاش کنید.",
    },
}


def get_text(lang: str, key: str, **kwargs: Any) -> str:
    """Fetch a localized string and safely format placeholders."""
    catalog = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    template = catalog.get(key) or TRANSLATIONS["en"].get(key, key)
    if kwargs:
        return template.format(**kwargs)
    return template