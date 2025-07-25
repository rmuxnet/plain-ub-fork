import io
from urllib.parse import quote

import qrcode
from pyrogram import filters
from pyrogram.raw.types.messages import BotResults
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultPhoto,
    ReplyParameters,
)

from app import BOT, Message, bot


@bot.add_cmd(cmd="qr")
async def generate_qr(bot: BOT, message: Message):
    if not message.input:
        await message.reply_text(
            "**Usage:** `.qr <text/link>`\n**Example:** `.qr https://github.com`"
        )
        return

    # Inline QR if Dual Mode
    if bot.is_user and getattr(bot, "has_bot", False):
        query = f"qr_gen {message.input}"
        inline_result: BotResults = await bot.get_inline_bot_results(
            bot=bot.bot.me.username, query=query
        )
        if inline_result.results:
            await bot.send_inline_bot_result(
                chat_id=message.chat.id,
                result_id=inline_result.results[0].id,
                query_id=inline_result.query_id,
            )
        return

    # Generate QR code
    qr_image = generate_qr_code(message.input)
    
    await bot.send_photo(
        chat_id=message.chat.id,
        photo=qr_image,
        caption=f"**QR Code Generated**\n\n**Data:** `{message.input}`",
        reply_parameters=ReplyParameters(message_id=message.reply_id or message.id),
    )


_bot = getattr(bot, "bot", bot)
if _bot.is_bot:

    @_bot.on_inline_query(filters=filters.regex(r"^qr_gen (.+)"), group=2)
    async def return_inline_qr_results(client: BOT, inline_query: InlineQuery):
        query_text = inline_query.matches[0].group(1)
        
        # Generate QR code image URL (using a QR code API service)
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=500x500&data={quote(query_text)}"
        
        result = InlineQueryResultPhoto(
            photo_url=qr_url,
            title="Generate QR Code",
            description=f"QR Code for: {query_text[:50]}...",
            caption=f"**QR Code Generated**\n\n**Data:** `{query_text}`",
        )

        await inline_query.answer(results=[result], cache_time=300)


def generate_qr_code(data: str) -> io.BytesIO:
    """Generate QR code and return as BytesIO object"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert PIL image to BytesIO
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    bio.name = "qrcode.png"
    
    return bio
