import sys
import os
import glob
import importlib
from pathlib import Path
import asyncio
import time
import logging
import logging.config
from datetime import date, datetime
import pytz

from aiohttp import web
from pyrogram import idle, __version__
from pyrogram.raw.all import layer

from database.ia_filterdb import Media, Media2, choose_mediaDB, tempDict, db as clientDB
from database.users_chats_db import db
from info import *
from utils import temp
from Script import script
from plugins import web_server, check_expired_premium
from LucyBot.Bot import Codeflix
from LucyBot.util.keepalive import ping_server
from LucyBot.Bot.clients import initialize_clients

# ---------------- LOGGING ---------------- #
logging.config.fileConfig("logging.conf")
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("aiohttp").setLevel(logging.ERROR)

botStartTime = time.time()
files = glob.glob("plugins/*.py")

# ---------------- WEB SERVER (Render) ---------------- #
async def start_render_web():
    async def home(request):
        return web.Response(text="OK")

    app = web.Application()
    app.router.add_get("/", home)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    logging.info(f"🌐 Web server started on port {port}")
    return runner


# ---------------- MAIN BOT START ---------------- #
async def Lucy_start():
    print("\nInitializing Lucy")

    # ✅ REQUIRED FOR RENDER
    render_runner = await start_render_web()

    await Codeflix.start()
    bot_info = await Codeflix.get_me()
    Codeflix.username = bot_info.username

    await initialize_clients()

    for name in files:
        patt = Path(name)
        plugin_name = patt.stem
        import_path = f"plugins.{plugin_name}"
        spec = importlib.util.spec_from_file_location(import_path, patt)
        load = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(load)
        sys.modules[import_path] = load
        print("Lucy Bot Imported =>", plugin_name)

    if ON_HEROKU:
        asyncio.create_task(ping_server())

    b_users, b_chats = await db.get_banned()
    temp.BANNED_USERS = b_users
    temp.BANNED_CHATS = b_chats

    await Media.ensure_indexes()
    await Media2.ensure_indexes()

    stats = await clientDB.command("dbStats")
    free_dbSize = round(
        512 - ((stats["dataSize"] / (1024 * 1024)) + (stats["indexSize"] / (1024 * 1024))), 2
    )

    if DATABASE_URI2 and free_dbSize < 62:
        tempDict["indexDB"] = DATABASE_URI2
        logging.info(f"Secondary DB enabled ({free_dbSize} MB left)")
    elif DATABASE_URI2 is None:
        logging.error("SECONDDB_URI missing")
        sys.exit(1)

    await choose_mediaDB()

    me = await Codeflix.get_me()
    temp.ME = me.id
    temp.U_NAME = me.username
    temp.B_NAME = me.first_name
    temp.B_LINK = me.mention
    Codeflix.username = f"@{me.username}"

    Codeflix.loop.create_task(check_expired_premium(Codeflix))

    logging.info(
        f"{me.first_name} | Pyrogram v{__version__} (Layer {layer}) started"
    )
    logging.info(LOG_STR)
    logging.info(script.LOGO)

    tz = pytz.timezone("Asia/Kolkata")
    today = date.today()
    now = datetime.now(tz).strftime("%H:%M:%S %p")

    await Codeflix.send_message(
        LOG_CHANNEL,
        script.RESTART_TXT.format(temp.B_LINK, today, now),
    )

    # ❌ REMOVE extra web_server() — already running
    await idle()


# ---------------- ENTRY ---------------- #
if __name__ == "__main__":
    try:
        asyncio.run(Lucy_start())
    except KeyboardInterrupt:
        logging.info("Service stopped 👋")
