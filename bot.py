"""
ربات ارسال پیام با ایموجی‌های پرمیوم (Custom Emoji) به کانال تلگرام
--------------------------------------------------------------------
نحوه کارکرد کلی:
1. کاربر /start می‌زند.
2. ربات آیدی/یوزرنیم کانال را می‌پرسد.
3. ربات بررسی می‌کند که در آن کانال ادمین است (و ترجیحاً دسترسی post messages دارد).
4. ربات از کاربر یک پیام همراه با کد ایموجی پرمیوم می‌خواهد؛ کد می‌تواند به دو شکل باشد:
      سلام [6001099232784683975]
      سلام 6001099232784683975
5. ربات کد عددی را از متن استخراج می‌کند، آن را با یک ایموجی جایگزین (placeholder)
   جایگزین می‌کند و پیام را با MessageEntity از نوع custom_emoji به کانال ارسال می‌کند.

نکتهٔ مهم (حتماً بخوانید):
طبق مستندات رسمی تلگرام، ارسال «کاستوم ایموجی» توسط ربات فقط برای ربات‌هایی
امکان‌پذیر است که حداقل یک یوزرنیم اضافه (collectible username) از طریق
Fragment خریداری کرده باشند. اگر ربات چنین یوزرنیمی نداشته باشد، تلگرام
entity کاستوم‌ایموجی را نادیده می‌گیرد و فقط ایموجی معمولی جایگزین را نشان می‌دهد
(یعنی کد اررور نمی‌دهد ولی ایموجی پرمیوم هم نشان داده نمی‌شود).
منبع: https://core.telegram.org/bots/api#messageentity
"""

import os
import re
import logging

from telegram import Update, MessageEntity, Chat
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from telegram.error import TelegramError

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# تنظیمات از Environment Variables (در Render تنظیم می‌شوند)
# ---------------------------------------------------------------------------
BOT_TOKEN = os.environ["BOT_TOKEN"]                     # توکن ربات از @BotFather
WEBHOOK_URL = os.environ["WEBHOOK_URL"].rstrip("/")      # مثلا: https://your-app.onrender.com
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "tg-webhook-secret")
PORT = int(os.environ.get("PORT", 10000))
# ایموجی‌ای که به عنوان placeholder روی entity کاستوم‌ایموجی گذاشته می‌شود
PLACEHOLDER_EMOJI = os.environ.get("PLACEHOLDER_EMOJI", "⭐")

# مراحل مکالمه
ASK_CHANNEL, ASK_MESSAGE = range(2)

# الگوی تشخیص کد ایموجی: عدد ۱۰ تا ۲۰ رقمی، با یا بدون کروشه
CODE_PATTERN = re.compile(r"\[?\s*(\d{10,20})\s*\]?")


def utf16_len(s: str) -> int:
    """طول یک رشته بر حسب واحدهای UTF-16 (همان چیزی که تلگرام برای offset/length استفاده می‌کند)."""
    return len(s.encode("utf-16-le")) // 2


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "سلام 👋\n"
        "این ربات پیام شما را همراه با ایموجی پرمیوم به کانالتان ارسال می‌کند.\n\n"
        "لطفاً آیدی عددی کانال یا یوزرنیم آن را برایم بفرست (مثل @mychannel یا -1001234567890).\n\n"
        "⚠️ قبل از ادامه، ربات را در کانالت ادمین کن (با دسترسی ارسال پیام)."
    )
    return ASK_CHANNEL


# ---------------------------------------------------------------------------
# دریافت و اعتبارسنجی کانال
# ---------------------------------------------------------------------------
async def receive_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    channel_input = update.message.text.strip()

    try:
        chat: Chat = await context.bot.get_chat(channel_input)
    except TelegramError as e:
        await update.message.reply_text(
            f"❌ نتونستم این کانال رو پیدا کنم.\nخطا: {e.message}\n"
            "دوباره آیدی یا یوزرنیم کانال رو بفرست، یا /cancel برای لغو."
        )
        return ASK_CHANNEL

    if chat.type != Chat.CHANNEL:
        await update.message.reply_text(
            "❌ این چت یک کانال نیست. لطفاً آیدی/یوزرنیم یک کانال را بفرست."
        )
        return ASK_CHANNEL

    try:
        member = await context.bot.get_chat_member(chat.id, context.bot.id)
    except TelegramError as e:
        await update.message.reply_text(
            f"❌ نتونستم عضویت ربات در کانال رو بررسی کنم.\nخطا: {e.message}\n"
            "مطمئن شو ربات عضو/ادمین کانال هست و دوباره امتحان کن."
        )
        return ASK_CHANNEL

    if member.status != ChatMemberStatus.ADMINISTRATOR:
        await update.message.reply_text(
            "❌ ربات در این کانال ادمین نیست.\n"
            "لطفاً از تنظیمات کانال، ربات رو با دسترسی «ارسال پیام» ادمین کن و دوباره آیدی کانال رو بفرست."
        )
        return ASK_CHANNEL

    can_post = getattr(member, "can_post_messages", True)
    if can_post is False:
        await update.message.reply_text(
            "⚠️ ربات ادمینه ولی دسترسی «ارسال پیام» (Post Messages) رو نداره.\n"
            "این دسترسی رو فعال کن و دوباره آیدی کانال رو بفرست."
        )
        return ASK_CHANNEL

    context.user_data["channel_id"] = chat.id
    context.user_data["channel_title"] = chat.title

    await update.message.reply_text(
        f"✅ عالی! کانال «{chat.title}» تایید شد و ربات در آن ادمین است.\n\n"
        "حالا پیامی که می‌خوای ارسال بشه رو همراه با کد ایموجی پرمیوم بفرست.\n"
        "مثال:\n"
        "سلام [6001099232784683975]\n"
        "یا\n"
        "سلام 6001099232784683975\n\n"
        "اگه چند تا کد ایموجی داری، همه‌شون رو داخل متن قرار بده.\n"
        "برای عوض کردن کانال هر وقت خواستی /start رو دوباره بزن."
    )
    return ASK_MESSAGE


# ---------------------------------------------------------------------------
# دریافت پیام نهایی و ارسال به کانال
# ---------------------------------------------------------------------------
async def receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw_text = update.message.text

    matches = list(CODE_PATTERN.finditer(raw_text))
    if not matches:
        await update.message.reply_text(
            "❌ هیچ کد ایموجی‌ای توی پیامت پیدا نکردم.\n"
            "کد باید یک عدد طولانی (مثل شناسه کاستوم‌ایموجی) باشه، با یا بدون کروشه.\n"
            "دوباره پیامت رو بفرست یا /cancel برای لغو."
        )
        return ASK_MESSAGE

    # ساخت متن نهایی: هر کد پیدا شده با ایموجی جایگزین می‌شود
    new_text_parts = []
    entities = []
    last_end = 0
    utf16_offset = 0

    for m in matches:
        # بخش متن قبل از کد، بدون تغییر
        before = raw_text[last_end:m.start()]
        new_text_parts.append(before)
        utf16_offset += utf16_len(before)

        # ایموجی جایگزین + entity
        code = m.group(1)
        new_text_parts.append(PLACEHOLDER_EMOJI)
        entities.append(
            MessageEntity(
                type=MessageEntity.CUSTOM_EMOJI,
                offset=utf16_offset,
                length=utf16_len(PLACEHOLDER_EMOJI),
                custom_emoji_id=code,
            )
        )
        utf16_offset += utf16_len(PLACEHOLDER_EMOJI)
        last_end = m.end()

    tail = raw_text[last_end:]
    new_text_parts.append(tail)
    final_text = "".join(new_text_parts)

    channel_id = context.user_data.get("channel_id")
    if channel_id is None:
        await update.message.reply_text("ابتدا با /start کانال رو انتخاب کن.")
        return ConversationHandler.END

    try:
        await context.bot.send_message(
            chat_id=channel_id,
            text=final_text,
            entities=entities,
        )
    except TelegramError as e:
        await update.message.reply_text(
            f"❌ ارسال پیام به کانال ناموفق بود.\nخطا: {e.message}\n\n"
            "نکته: طبق مستندات تلگرام، کاستوم‌ایموجی برای کانال‌ها فقط توسط ربات‌هایی که "
            "یوزرنیم اضافه از Fragment خریده‌اند تضمین‌شده کار می‌کند. اگه مالک ربات پرمیومه ولی "
            "یوزرنیم Fragment نداره، ممکنه ارسال باز هم fail بشه یا بدون ایموجی پرمیوم بره."
        )
        return ASK_MESSAGE

    await update.message.reply_text(
        f"✅ پیام با {len(matches)} کد ایموجی به کانال «{context.user_data.get('channel_title')}» ارسال شد.\n"
        "اگه ربات یوزرنیم Fragment نداره ولی مالکش پرمیومه، حتماً چک کن که ایموجی واقعاً به‌صورت "
        "پرمیوم نمایش داده شده باشه (چون این حالت برای کانال رسماً تضمین نشده - به README مراجعه کن).\n"
        "می‌تونی پیام بعدی رو بفرستی، یا /start برای تغییر کانال."
    )
    return ASK_MESSAGE


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("لغو شد. برای شروع دوباره /start رو بزن.")
    return ConversationHandler.END


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)


def build_application() -> Application:
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_channel)],
            ASK_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_message)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
    )

    application.add_handler(conv_handler)
    application.add_error_handler(error_handler)
    return application


def main() -> None:
    application = build_application()

    # اجرا به صورت webhook (سریع‌تر از polling و مناسب Render)
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=WEBHOOK_SECRET,
        webhook_url=f"{WEBHOOK_URL}/{WEBHOOK_SECRET}",
        secret_token=WEBHOOK_SECRET,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
