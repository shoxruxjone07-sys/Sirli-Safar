"""SIRLI SAFAR — kirish nuqtasi: aiohttp + aiogram webhook (Render Free Web Service)."""
from __future__ import annotations

import asyncio
import logging
import signal

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiohttp import web

from app.config import WEBHOOK_PATH, Config, load_config, load_dotenv
from app.database import Db, run_migrations
from app.deps import Deps, build_deps
from app.handlers import admin, answers, game, players, tasks
from app.middlewares.track import TrackUsers
from app.seed.seeds import seed_stories, validate_story_data
from app.services.timer_service import TimerService
from app.utils.fsm_storage import PgStorage
from app.utils.log import setup_logging

log = logging.getLogger("sirli")


def build_dispatcher(deps: Deps) -> Dispatcher:
    dp = Dispatcher(storage=PgStorage(deps.db), deps=deps)
    dp.message.outer_middleware(TrackUsers())
    dp.callback_query.outer_middleware(TrackUsers())
    # Tartib muhim: admin/FSM handlerlari umumiy javob handlerlaridan oldin
    routers = (admin.login_router, admin.router, tasks.router, players.router, game.router, answers.router)
    for r in routers:  # testlarda dispatcher qayta quriladi — routerni avvalgi dispatcherdan ajratamiz
        r._parent_router = None
    dp.include_routers(*routers)
    return dp


def build_app(deps: Deps, dp: Dispatcher) -> web.Application:
    app = web.Application()

    async def health(_: web.Request) -> web.Response:
        db_ok = True
        try:
            await asyncio.wait_for(deps.db.fetchval("SELECT 1"), timeout=4)
        except Exception:
            db_ok = False
        return web.json_response({"status": "ok", "db": db_ok})

    async def index(_: web.Request) -> web.Response:
        return web.Response(text="SIRLI SAFAR ishlayapti ✅")

    app.router.add_get("/health", health)
    app.router.add_get("/", index)
    SimpleRequestHandler(dispatcher=dp, bot=deps.bot, secret_token=deps.config.webhook_secret).register(app, path=WEBHOOK_PATH)
    return app


async def prepare_database(db: Db, deps: Deps) -> None:
    validate_story_data()
    applied = await run_migrations(db)
    if applied:
        log.info("Qo‘llangan migratsiyalar: %s", ", ".join(applied))
    added = await seed_stories(db)
    demo = await deps.tasks.seed_demo()
    log.info("Hikoyalar yuklandi: %s ta yangi; demo yozuvlar: %s", added, demo)


async def run() -> None:
    load_dotenv()  # lokal ishga tushirishda .env dan; Render’da muhit o‘zgaruvchilari ustuvor
    config: Config = load_config()
    setup_logging(config.log_level, [config.bot_token, config.webhook_secret])
    db = await Db.connect(config.database_url)
    bot = Bot(config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    deps = build_deps(config, db, bot)
    await prepare_database(db, deps)
    await deps.flow.init()
    dp = build_dispatcher(deps)
    deps.timer = TimerService(deps.games, deps.flow, keepalive_url=f"{config.webhook_url}/health")

    runner = web.AppRunner(build_app(deps, dp))
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", config.port).start()
    log.info("Server %s portda ishga tushdi", config.port)

    await bot.set_webhook(config.webhook_full_url, secret_token=config.webhook_secret,
                          allowed_updates=dp.resolve_used_update_types(), drop_pending_updates=False)
    log.info("Webhook o‘rnatildi: %s", config.webhook_full_url)
    deps.timer.start()  # qayta ishga tushganda o‘yin holati bazadan tiklanadi (timer.tick)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass
    await stop.wait()
    log.info("To‘xtatilmoqda…")
    await deps.timer.stop()
    await runner.cleanup()
    await bot.session.close()
    await db.close()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
