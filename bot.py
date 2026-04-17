import asyncio
import logging
import os

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route
from telegram import Update
from telegram.ext import Application

from database import init_db
from handlers.user_handlers import get_user_handlers
from handlers.admin_handlers import get_admin_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

print("🚀 AgentBD Bot starting on Render...")
init_db()


async def root(request: Request) -> PlainTextResponse:
    return PlainTextResponse("AgentBD Bot is Live! 🟢")


async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("✅ AgentBD Bot is Live! 🟢")


async def telegram_webhook(request: Request) -> Response:
    try:
        bot_app = request.app.state.bot_app
        data = await request.json()
        update = Update.de_json(data, bot_app.bot)
        await bot_app.process_update(update)
    except Exception as e:
        logger.error(f"❌ Error processing webhook update: {e}")
    return Response(status_code=200)


async def main() -> None:
    TOKEN = os.environ.get("BOT_TOKEN", "")
    WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
    PORT = int(os.environ.get("PORT", 8000))

    if not TOKEN:
        logger.error("❌ BOT_TOKEN environment variable is not set. Exiting.")
        return

    if not WEBHOOK_URL:
        logger.error(
            "❌ RENDER_EXTERNAL_URL environment variable is not set. Exiting."
        )
        return

    bot_app = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    for handler in get_user_handlers():
        bot_app.add_handler(handler)

    for handler in get_admin_handlers():
        bot_app.add_handler(handler, group=1)

    await bot_app.initialize()
    await bot_app.start()

    webhook_path = f"/webhook/{TOKEN}"
    full_webhook_url = f"{WEBHOOK_URL}{webhook_path}"

    try:
        await bot_app.bot.set_webhook(full_webhook_url)
        logger.info(f"✅ Webhook set: {full_webhook_url}")
    except Exception as e:
        logger.error(f"❌ Failed to set webhook: {e}")

    routes = [
        Route("/", endpoint=root, methods=["GET"]),
        Route("/health", endpoint=health_check, methods=["GET"]),
        Route(webhook_path, endpoint=telegram_webhook, methods=["POST"]),
    ]

    starlette_app = Starlette(routes=routes)
    starlette_app.state.bot_app = bot_app

    config = uvicorn.Config(
        starlette_app,
        host="0.0.0.0",
        port=PORT,
        log_level="info",
    )
    server = uvicorn.Server(config)

    logger.info(f"🚀 Starting uvicorn server on 0.0.0.0:{PORT}")
    await server.serve()

    logger.info("🛑 Server stopped. Shutting down bot...")
    await bot_app.stop()
    await bot_app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
