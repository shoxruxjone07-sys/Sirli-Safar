"""Taymer: vaqt chegaralari bazadagi UTC `deadline_at` bo‘yicha tekshiriladi (sleep-taymer emas).
Server uxlab turib uyg‘onsa ham muddati o‘tgan topshiriqlar zudlik bilan hal qilinadi."""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

import aiohttp

from app.services.game_flow import GameFlow
from app.services.game_service import GameService
from app.utils.tg import fmt_limit, try_call

log = logging.getLogger(__name__)


class TimerService:
    def __init__(self, games: GameService, flow: GameFlow, *, interval: float = 2.0,
                 keepalive_url: Optional[str] = None, keepalive_every: float = 540.0):
        self.games = games
        self.flow = flow
        self.interval = interval
        self.keepalive_url = keepalive_url
        self.keepalive_every = keepalive_every
        self._task: Optional[asyncio.Task] = None
        self._last_keepalive = 0.0
        self._stop = asyncio.Event()

    def start(self) -> None:
        self._stop.clear()
        self._task = asyncio.create_task(self._loop(), name="sirli-timer")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass

    async def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("Taymer siklida xato")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.interval)
            except asyncio.TimeoutError:
                pass

    async def tick(self) -> None:
        # 1) muddati o‘tgan topshiriqlar
        for gt_id in await self.games.due_task_ids():
            try:
                res = await self.games.expire(gt_id)
                if res:
                    await self.flow.after_resolve(res)
            except Exception:
                log.exception("Topshiriq muddatini yopishda xato (%s)", gt_id)
        # 2) 10 soniya qolganda ogohlantirish
        for gt_id in await self.games.warn_candidates():
            gt = await self.games.get_task(gt_id)
            if gt and gt["status"] == "open":
                chat = gt["assigned_user_id"] if gt["kind"] == "individual" else gt["group_id"]
                await try_call(self.flow.bot.send_message, chat, "⏳ <b>10 soniya qoldi!</b>")
        # 3) e’lon qilinmay qolgan topshiriqlar
        for gt_id in await self.games.stale_pending_ids():
            await self.flow.announce(gt_id)
        # 4) faol topshirig‘i yo‘q (masalan, qayta ishga tushish) o‘yinlar
        for game_id in await self.games.idle_game_ids():
            await self.flow.next_task(game_id)
        # 5) lobbi xabarini yangilash
        for game_id in await self.games.dirty_lobby_ids():
            await self.flow.refresh_lobby(game_id)
        # 6) Render uxlab qolmasligi uchun faol o‘yin paytida o‘zini “uyg‘otish”
        await self._keepalive()

    async def _keepalive(self) -> None:
        if not self.keepalive_url:
            return
        loop = asyncio.get_running_loop()
        if loop.time() - self._last_keepalive < self.keepalive_every:
            return
        self._last_keepalive = loop.time()
        if not await self.games.has_active_games():
            return
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as s:
                async with s.get(self.keepalive_url) as r:
                    log.debug("keepalive: %s", r.status)
        except Exception as exc:  # tarmoq xatosi o‘yinga ta’sir qilmasin
            log.warning("keepalive xatosi: %s", exc)
