from pyrogram import filters
from LucyBot.Bot import Codeflix

@Codeflix.on_message(filters.private & filters.command("alive"))
async def alive(_, message):
    await message.reply_text("✅ Bot is alive and receiving messages")
