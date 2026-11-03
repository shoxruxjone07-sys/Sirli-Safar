"""Barcha servislar bitta konteynerda; handlerlarga `deps` nomi bilan uzatiladi."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Coroutine, Optional

from aiogram import Bot

from app.config import Config
from app.database import Db
from app.services.game_flow import GameFlow
from app.services.game_service import GameService
from app.services.settings_service import SettingsService
from app.services.story_service import StoryService
from app.services.task_service import TaskService
from app.services.timer_service import TimerService
from app.utils.security import AdminAuth

log = logging.getLogger(__name__)


@dataclass
class Deps:
    config: Config
    db: Db
    bot: Bot
    auth: AdminAuth
    settings: SettingsService
    stories: StoryService
    tasks: TaskService
    games: GameService
    flow: GameFlow
    timer: Optional[TimerService] = None
    _spawned: set = field(default_factory=set)

    def spawn(self, coro: Coroutine[Any, Any, Any]) -> asyncio.Task:
        """Fon vazifasi: xatolar jurnalga yoziladi, jarayon yiqilmaydi."""
        task = asyncio.create_task(self._guard(coro))
        self._spawned.add(task)
        task.add_done_callback(self._spawned.discard)
        return task

    @staticmethod
    async def _guard(coro):
        try:
            return await coro
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Fon vazifasida xato")

    async def drain(self) -> None:
        while self._spawned:
            await asyncio.gather(*list(self._spawned), return_exceptions=True)


def build_deps(config: Config, db: Db, bot: Bot) -> Deps:
    settings = SettingsService(db)
    stories = StoryService(db)
    tasks = TaskService(db)
    games = GameService(db, settings)
    flow = GameFlow(bot, games, stories, settings)
    auth = AdminAuth(db, config)
    return Deps(config=config, db=db, bot=bot, auth=auth, settings=settings,
                stories=stories, tasks=tasks, games=games, flow=flow)
