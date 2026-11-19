"""Bilingual (English & Persian) message catalog and translation helpers."""

from __future__ import annotations

from typing import Any

# Persistent ReplyKeyboard button labels (bilingual so users can always tap them)
BTN_TRENDING = "🔥 Trending GIFs / گیف‌های ترند"
BTN_LANGUAGE = "🌐 Language / تغییر زبان"
BTN_HELP = "ℹ️ Help / راهنما"

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "welcome": (
            "👋 Hello <b>{name}</b>!\n\n"
            "I can download media from <b>X (Twitter)</b> and <b>Instagram</b> links, "
            "and send you <b>Trending GIFs</b>:\n"
            "• <b>X / Twitter:</b> GIFs & Videos (original quality or convert to GIF)\n"
            "• <b>Instagram:</b> Reels, Video/Photo Posts, Carousels & Profile Pictures\n"
            "• <b>Trending GIFs:</b> Persian & English Twitter trends, Romantic & Meme GIFs\n\n"
            "Select a language below, tap <b>Trending GIFs</b> in the menu, or paste a link:"
        ),
        "choose_language": "🌐 Please choose your preferred language:",
        "language_updated": "✅ Language set to <b>English</b>.\nSend any X/Instagram link or tap <b>Trending GIFs</b>!",
        "help": (
            "📖 <b>How to use this bot</b>\n\n"
            "1. Paste any link from <b>X (Twitter)</b> or <b>Instagram</b> to download videos, GIFs, photos, or avatars.\n"
            "2. For X videos, choose a video quality or tap <b>Convert to GIF</b>.\n"
            "3. Tap <b>🔥 Trending GIFs</b> in the bottom menu (or /trending) to browse trending GIFs from "
            "Persian Twitter, English Twitter, Romantic, and Meme categories.\n\n"
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
        "invalid_link": (
            "🔗 Please send a valid <b>X (Twitter)</b> or <b>Instagram</b> link, "
            "or tap <b>🔥 Trending GIFs</b> in the menu.\n"
            "Examples:\n"
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
        "btn_convert_gif": "🎞 Convert to GIF",
        "select_quality": (
            "🎬 <b>Video found!</b>\n"
            "Title: <i>{title}</i>\n\n"
            "Choose a video quality or convert it to a <b>GIF</b>:"
        ),
        "select_quality_limit_note": (
            "\n\n⚠️ <i>Note: Options marked with ⚠️ exceed Telegram's 50 MB Bot API limit. "
            "Please pick a lower resolution if available.</i>"
        ),
        "quality_btn": "{label}{size_part}",
        "quality_btn_over_limit": "⚠️ {label}{size_part} (>50 MB)",
        "file_too_large": (
            "❌ This file ({size_mb:.1f} MB) exceeds Telegram's 50 MB upload limit for bots.\n"
            "Please choose a lower resolution."
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
            "🔒 Could not access this content. It may be from a private account, deleted, or unavailable."
        ),
        "err_age_restricted": (
            "🔞 This content is age-restricted or requires login to view."
        ),
        "err_rate_limit": "🚦 Rate limit reached. Please try again in a minute.",
        "err_gif_convert_failed": (
            "❌ Failed to convert the video to GIF. Please try downloading one of the video qualities instead."
        ),
        "err_generic": "❌ Something went wrong while processing this link. Please try again later.",
        "err_upload_failed": "❌ Failed to upload the media to Telegram. Please try again.",
    },
    "fa": {
        "welcome": (
            "👋 سلام <b>{name}</b> عزیز!\n\n"
            "من می‌توانم محتوای لینک‌های <b>X (توییتر)</b> و <b>اینستاگرام</b> را دانلود کنم "
            "و <b>گیف‌های ترند</b> برایتان بفرستم:\n"
            "• <b>X / توییتر:</b> گیف‌ها و ویدیوها (دانلود کیفیت اصلی یا تبدیل ویدیو به GIF)\n"
            "• <b>اینستاگرام:</b> ریلز، پست‌های ویدیویی و عکسی، اسلایدها و عکس پروفایل\n"
            "• <b>گیف‌های ترند:</b> ترندهای توییتر فارسی و انگلیسی، عاشقانه و میم و فان\n\n"
            "زبان خود را انتخاب کنید، دکمه <b>گیف‌های ترند</b> را بزنید یا مستقیم لینک بفرستید:"
        ),
        "choose_language": "🌐 لطفاً زبان مورد نظر خود را انتخاب کنید:",
        "language_updated": "✅ زبان ربات به <b>فارسی</b> تغییر یافت.\nمی‌توانید لینک بفرستید یا دکمه <b>گیف‌های ترند</b> را بزنید!",
        "help": (
            "📖 <b>راهنمای استفاده از ربات</b>\n\n"
            "۱. لینک پست یا پروفایل را از <b>X (توییتر)</b> یا <b>اینستاگرام</b> بفرستید تا دانلود شود.\n"
            "۲. برای ویدیوهای توییتر می‌توانید کیفیت دلخواه را بزنید یا گزینه <b>تبدیل به GIF</b> را انتخاب کنید.\n"
            "۳. با زدن دکمه <b>🔥 گیف‌های ترند</b> در منوی پایین صفحه (یا دستور /trending) می‌توانید گیف‌های ترند "
            "توییتر فارسی، توییتر انگلیسی، عاشقانه و میم/فان را دریافت کنید.\n\n"
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
        "invalid_link": (
            "🔗 لطفاً یک لینک معتبر از <b>X (توییتر)</b> یا <b>اینستاگرام</b> ارسال کنید "
            "یا از منوی پایین دکمه <b>🔥 گیف‌های ترند</b> را بزنید.\n"
            "مثال‌ها:\n"
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
        "btn_convert_gif": "🎞 تبدیل به GIF",
        "select_quality": (
            "🎬 <b>ویدیو پیدا شد!</b>\n"
            "عنوان: <i>{title}</i>\n\n"
            "کیفیت دلخواه ویدیو را انتخاب کنید یا آن را به <b>GIF</b> تبدیل کنید:"
        ),
        "select_quality_limit_note": (
            "\n\n⚠️ <i>توجه: گزینه‌های دارای علامت ⚠️ بیشتر از محدودیت ۵۰ مگابایتی تلگرام هستند. "
            "در صورت امکان کیفیت پایین‌تری را انتخاب کنید.</i>"
        ),
        "quality_btn": "{label}{size_part}",
        "quality_btn_over_limit": "⚠️ {label}{size_part} (بیش از ۵۰ مگابایت)",
        "file_too_large": (
            "❌ حجم این فایل ({size_mb:.1f} مگابایت) از محدودیت ۵۰ مگابایتی ربات‌های تلگرام بیشتر است.\n"
            "لطفاً کیفیت پایین‌تری را انتخاب کنید."
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
            "🔒 امکان دسترسی به این محتوا وجود ندارد. ممکن است پیج خصوصی باشد یا پست حذف شده باشد."
        ),
        "err_age_restricted": (
            "🔞 این محتوا دارای محدودیت سنی است یا برای مشاهده آن نیاز به ورود به حساب کاربری دارد."
        ),
        "err_rate_limit": "🚦 در حال حاضر محدودیت موقت درخواست اعمال شده است. لطفاً یک دقیقه دیگر دوباره تلاش کنید.",
        "err_gif_convert_failed": (
            "❌ تبدیل ویدیو به GIF ناموفق بود. لطفاً یکی از کیفیت‌های اصلی ویدیو را دانلود کنید."
        ),
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