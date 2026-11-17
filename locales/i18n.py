"""Bilingual (English & Persian) message catalog and translation helpers."""

from __future__ import annotations

from typing import Any

# Persistent ReplyKeyboard button labels (bilingual so users can always tap them)
BTN_LANGUAGE = "🌐 Language / تغییر زبان"
BTN_HELP = "ℹ️ Help / راهنما"

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "welcome": (
            "👋 Hello <b>{name}</b>!\n\n"
            "I can download <b>GIFs</b> and <b>Videos</b> from X (Twitter) links.\n"
            "• <b>GIFs</b> are sent automatically as native Telegram animations.\n"
            "• <b>Videos</b> let you choose your preferred resolution.\n\n"
            "Please select your language below, or simply paste an X/Twitter link:"
        ),
        "choose_language": "🌐 Please choose your preferred language:",
        "language_updated": "✅ Language set to <b>English</b>.\nSend any X (Twitter) link to start!",
        "help": (
            "📖 <b>How to use this bot</b>\n\n"
            "1. Copy a link to any X/Twitter post containing a video or GIF.\n"
            "   (Supports <code>x.com</code>, <code>twitter.com</code>, <code>t.co</code>, "
            "<code>fxtwitter.com</code>, and <code>vxtwitter.com</code>)\n"
            "2. Paste and send the link here.\n"
            "3. GIFs download automatically; for videos, pick your desired quality.\n\n"
            "Use /language anytime to switch between English and Persian."
        ),
        "invalid_link": (
            "🔗 Please send a valid X (Twitter) link.\n"
            "Example: <code>https://x.com/username/status/123456789</code>"
        ),
        "inspecting": "🔍 Inspecting post media...",
        "downloading_gif": "⬇️ Downloading GIF...",
        "uploading_gif": "📤 Uploading GIF to Telegram...",
        "downloading_video": "⬇️ Downloading video ({quality})...",
        "uploading_video": "📤 Uploading video to Telegram...",
        "select_quality": (
            "🎬 <b>Video found!</b>\n"
            "Title: <i>{title}</i>\n\n"
            "Choose a quality to download:"
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
            "😕 No downloadable video or GIF was found in this post.\n"
            "(Image-only or text-only posts are not supported.)"
        ),
        "err_private_or_deleted": (
            "🔒 Could not access this post. It may be private, deleted, or from a suspended account."
        ),
        "err_age_restricted": (
            "🔞 This post appears to be age-restricted or requires an X login to view."
        ),
        "err_rate_limit": "🚦 X/Twitter is temporarily rate-limiting requests. Please try again in a minute.",
        "err_generic": "❌ Something went wrong while processing this link. Please try again later.",
        "err_upload_failed": "❌ Failed to upload the media to Telegram. Please try a lower quality.",
    },
    "fa": {
        "welcome": (
            "👋 سلام <b>{name}</b> عزیز!\n\n"
            "من می‌توانم <b>گیف‌ها (GIF)</b> و <b>ویدیوها</b> را از لینک‌های X (توییتر) برایتان دانلود کنم.\n"
            "• <b>گیف‌ها</b> به‌صورت خودکار و بدون نیاز به انتخاب کیفیت ارسال می‌شوند.\n"
            "• برای <b>ویدیوها</b> می‌توانید کیفیت دلخواه را انتخاب کنید.\n\n"
            "لطفاً زبان مورد نظر خود را انتخاب کنید یا مستقیم لینک پست را بفرستید:"
        ),
        "choose_language": "🌐 لطفاً زبان مورد نظر خود را انتخاب کنید:",
        "language_updated": "✅ زبان ربات به <b>فارسی</b> تغییر یافت.\nحالا می‌توانید لینک X (توییتر) را بفرستید!",
        "help": (
            "📖 <b>راهنمای استفاده از ربات</b>\n\n"
            "۱. لینک پست X یا توییتر حاوی ویدیو یا گیف را کپی کنید.\n"
            "   (پشتیبانی از دامنه‌های <code>x.com</code>، <code>twitter.com</code>، <code>t.co</code>، "
            "<code>fxtwitter.com</code> و <code>vxtwitter.com</code>)\n"
            "۲. لینک را در همین چت ارسال کنید.\n"
            "۳. گیف‌ها خودکار ارسال می‌شوند و برای ویدیوها می‌توانید کیفیت دلخواه را انتخاب کنید.\n\n"
            "برای تغییر زبان در هر زمان از دستور /language استفاده کنید."
        ),
        "invalid_link": (
            "🔗 لطفاً یک لینک معتبر از X (توییتر) ارسال کنید.\n"
            "مثال: <code>https://x.com/username/status/123456789</code>"
        ),
        "inspecting": "🔍 در حال بررسی اطلاعات پست...",
        "downloading_gif": "⬇️ در حال دانلود گیف...",
        "uploading_gif": "📤 در حال ارسال گیف به تلگرام...",
        "downloading_video": "⬇️ در حال دانلود ویدیو ({quality})...",
        "uploading_video": "📤 در حال ارسال ویدیو به تلگرام...",
        "select_quality": (
            "🎬 <b>ویدیو پیدا شد!</b>\n"
            "عنوان: <i>{title}</i>\n\n"
            "کیفیت مورد نظر برای دانلود را انتخاب کنید:"
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
            "😕 هیچ ویدیو یا گیف قابل دانلودی در این پست پیدا نشد.\n"
            "(پست‌های متنی یا فقط عکس پشتیبانی نمی‌شوند.)"
        ),
        "err_private_or_deleted": (
            "🔒 امکان دسترسی به این پست وجود ندارد. ممکن است پست خصوصی، حذف‌شده یا مربوط به اکانت مسدودشده باشد."
        ),
        "err_age_restricted": (
            "🔞 این پست دارای محدودیت سنی است یا برای مشاهده آن نیاز به ورود به حساب X دارد."
        ),
        "err_rate_limit": "🚦 در حال حاضر X/توییتر محدودیت موقت اعمال کرده است. لطفاً یک دقیقه دیگر دوباره تلاش کنید.",
        "err_generic": "❌ هنگام پردازش این لینک خطایی رخ داد. لطفاً کمی بعد دوباره امتحان کنید.",
        "err_upload_failed": "❌ ارسال فایل به تلگرام ناموفق بود. لطفاً کیفیت پایین‌تری را امتحان کنید.",
    },
}


def get_text(lang: str, key: str, **kwargs: Any) -> str:
    """Fetch a localized string and safely format placeholders."""
    catalog = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    template = catalog.get(key) or TRANSLATIONS["en"].get(key, key)
    if kwargs:
        return template.format(**kwargs)
    return template
