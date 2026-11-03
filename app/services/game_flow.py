"""O‘yinning Telegram qatlami: guruh va shaxsiy chatga xabarlar yuborish, natijalarni e’lon qilish."""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from aiogram.types import BufferedInputFile

from app.keyboards import game as kb
from app.services.game_service import GameService, Resolution
from app.services.gif_service import build_gif
from app.services.result_service import format_stats
from app.services.settings_service import SettingsService
from app.services.staircase_service import render_staircase, text_ladder
from app.services.story_service import StoryService
from app.utils.tg import esc, fmt_limit, mention, split_text, tg_call, try_call

log = logging.getLogger(__name__)
LETTERS = "ABCD"

KIND_LABEL = {
    "test": "Variantli test", "text": "Matnli savol", "individual": "Individual topshiriq",
    "creative": "Ijodiy topshiriq", "trap": "TUZOQ",
}


class GameFlow:
    def __init__(self, bot: Bot, games: GameService, stories: StoryService, settings: SettingsService):
        self.bot = bot
        self.games = games
        self.stories = stories
        self.settings = settings
        self.bot_username: str = ""

    async def init(self) -> None:
        me = await self.bot.get_me()
        self.bot_username = me.username or ""

    # ================================================================== lobbi
    async def lobby_text(self, game_id: int) -> str:
        game = await self.games.get_game(game_id)
        story = await self.stories.get_story(game["story_id"])
        roster = await self.games.roster(game_id)
        lines = [
            "🧭 <b>SIRLI SAFAR</b> — sarguzasht boshlanmoqda!",
            f"📖 Hikoya: <b>{esc(story['title'])}</b>",
            f"<i>{esc(story['synopsis'])}</i>",
            "",
            "Guruhdagi barcha ishtirokchilar bitta jamoa. Maqsad — <b>1-zinadan 10-zinaga</b> yetib borish: "
            "to‘g‘ri javob — bir zina yuqoriga, noto‘g‘ri javob yoki vaqt tugashi — bir zina pastga.",
            "",
            "❗ <b>Qatnashish uchun:</b> pastdagi tugmani bosing → bot ochilgach <b>«Start»</b> tugmasini bosing. "
            "Botga /start bosmagan talaba o‘yinda qatnasha olmaydi va unga shaxsiy topshiriq yuborilmaydi. "
            "O‘qituvchi o‘yinni boshlagach ro‘yxat yopiladi.",
            "",
            f"👥 Ro‘yxatga yozilganlar: <b>{len(roster)}</b>",
        ]
        for i, p in enumerate(roster[:40], start=1):
            lines.append(f"{i}. {esc(p['full_name'])}" + (f" (@{esc(p['username'])})" if p["username"] else ""))
        if len(roster) > 40:
            lines.append(f"… va yana {len(roster) - 40} kishi")
        return "\n".join(lines)

    async def post_lobby(self, game_id: int) -> int:
        game = await self.games.get_game(game_id)
        msg = await tg_call(self.bot.send_message, game["group_id"], await self.lobby_text(game_id),
                            reply_markup=kb.lobby_kb(self.bot_username, game_id))
        await self.games.db.execute(
            "UPDATE games SET lobby_message_id=$2, lobby_dirty=FALSE WHERE id=$1", game_id, msg.message_id)
        return msg.message_id

    async def refresh_lobby(self, game_id: int) -> None:
        game = await self.games.get_game(game_id)
        if not game or game["status"] != "lobby" or not game["lobby_message_id"]:
            return
        await self.games.db.execute("UPDATE games SET lobby_dirty=FALSE WHERE id=$1", game_id)
        try:
            await tg_call(self.bot.edit_message_text, await self.lobby_text(game_id), chat_id=game["group_id"],
                          message_id=game["lobby_message_id"],
                          reply_markup=kb.lobby_kb(self.bot_username, game_id))
        except TelegramBadRequest as exc:
            if "not modified" not in str(exc).lower():
                log.warning("Lobbi xabarini yangilab bo‘lmadi: %s", exc)
        except TelegramAPIError as exc:
            log.warning("Lobbi xabarini yangilab bo‘lmadi: %s", exc)

    # ============================================================== boshlanish
    async def begin(self, game_id: int) -> None:
        game = await self.games.get_game(game_id)
        story = await self.stories.get_story(game["story_id"])
        roster = await self.games.roster(game_id)
        await try_call(
            self.bot.send_message, game["group_id"],
            f"🚀 <b>SIRLI SAFAR boshlandi!</b>\n📖 «{esc(story['title'])}»\n"
            f"👥 Jamoa a’zolari: <b>{len(roster)}</b> kishi\n\n"
            "• To‘g‘ri javob — <b>+1 zina</b>, noto‘g‘ri javob yoki vaqt tugashi — <b>−1 zina</b>.\n"
            "• Variantli testda jamoadan <b>birinchi bosilgan</b> javob yakuniy hisoblanadi.\n"
            "• Matnli topshiriqda topshiriq xabariga <b>reply</b> qilib yozing — birinchi javob yakuniy.\n"
            "• Individual topshiriq tanlangan talabaga shaxsiy chatda yuboriladi.\n\n"
            "Omad! Jamoa — birdamlikda kuch! 💪")
        await self.send_stair(game, 1)
        await self.send_story_part(game, 1, up=True)
        await self.next_task(game_id)

    # ============================================================ hikoya / zina
    async def send_stair(self, game, stage_no: int) -> None:
        stage = await self.stories.get_stage(game["story_id"], stage_no)
        story = await self.stories.get_story(game["story_id"])
        png = await asyncio.to_thread(
            render_staircase, stage_no, story_title=story["title"],
            stage_title=stage["title"] if stage else "", theme=story["theme"])
        await try_call(
            self.bot.send_photo, game["group_id"], BufferedInputFile(png, filename=f"zina_{stage_no}.png"),
            caption=f"🪜 {text_ladder(stage_no)}\n<b>{stage_no}-zina</b>")

    async def send_story_part(self, game, stage_no: int, up: bool) -> None:
        stage = await self.stories.get_stage(game["story_id"], stage_no)
        if not stage:
            return
        chat = game["group_id"]
        if up:
            if stage["media_file_id"]:
                send = self.bot.send_animation if stage["media_type"] == "animation" else self.bot.send_photo
                kwargs = {"animation" if stage["media_type"] == "animation" else "photo": stage["media_file_id"]}
                await try_call(send, chat, caption=f"<b>{stage_no}-bosqich · {esc(stage['title'])}</b>", **kwargs)
            text = f"📖 <b>{stage_no}-bosqich · {esc(stage['title'])}</b>\n\n{esc(stage['body'])}"
            if stage["bridge"]:
                text += f"\n\n<i>{esc(stage['bridge'])}</i>"
        else:
            text = (f"🔙 <b>Jamoa {stage_no}-bosqichga qaytdi · {esc(stage['title'])}</b>\n"
                    + (f"<i>{esc(stage['bridge'])}</i>" if stage["bridge"] else ""))
        for part in split_text(text):
            await try_call(self.bot.send_message, chat, part)

    async def _send_gif(self, chat_id: int, kind: str, caption: str) -> None:
        custom = await self.settings.get_opt(f"gif_custom:{kind}")
        builtin = await self.settings.get_opt(f"gif_builtin:{kind}")
        file = custom or builtin
        try:
            if file:
                await tg_call(self.bot.send_animation, chat_id, file, caption=caption)
                return
            data = await asyncio.to_thread(build_gif, kind)
            msg = await tg_call(self.bot.send_animation, chat_id,
                                BufferedInputFile(data, filename=f"{kind}.gif"), caption=caption)
            if msg and msg.animation:
                await self.settings.set(f"gif_builtin:{kind}", msg.animation.file_id)
        except TelegramAPIError as exc:
            log.warning("GIF yuborilmadi (%s): %s", kind, exc)
            if custom:  # yaroqsiz file_id bo‘lsa, o‘chirib tashlaymiz
                await self.settings.delete(f"gif_custom:{kind}")
            if builtin and not custom:
                await self.settings.delete(f"gif_builtin:{kind}")
            await try_call(self.bot.send_message, chat_id, caption)

    # ================================================================ topshiriq
    async def next_task(self, game_id: int, exclude_kinds: tuple = ()) -> None:
        prepared = await self.games.prepare_next(game_id, exclude_kinds)
        game = await self.games.get_game(game_id)
        if prepared.reason == "no_tasks":
            await try_call(self.bot.send_message, game["group_id"],
                           "⏸ O‘yin vaqtincha to‘xtatildi — o‘qituvchi topshiriq qo‘shishi kerak.")
            await try_call(
                self.bot.send_message, game["admin_id"],
                f"⚠️ <b>{esc(game['group_title'])}</b>: {prepared.stage}-zina uchun faol topshiriq yo‘q, "
                "o‘yin pauzaga qo‘yildi.\nTopshiriq qo‘shing va o‘yinni «Faol o‘yinlar» orqali davom ettiring.")
            return
        if prepared.gt_id:
            await self.announce(prepared.gt_id)

    async def announce(self, gt_id: int) -> None:
        gt = await self.games.get_task(gt_id)
        if not gt or gt["status"] not in ("pending", "needs_input"):
            return
        game = await self.games.get_game(gt["game_id"])
        if not game or game["status"] != "running":
            return
        if gt["status"] == "needs_input":
            await self._ask_admin_trap(game, gt)
        elif gt["kind"] == "individual":
            await self._announce_individual(game, gt)
        else:
            await self._announce_group_task(game, gt)

    def _task_text(self, gt: dict) -> str:
        head = "🪤" if gt["kind"] == "trap" else "🧩"
        lines = [f"{head} <b>{gt['stage_no']}-zina · {KIND_LABEL[gt['kind']]}</b>", "", esc(gt["question"])]
        if gt["options"]:
            lines.append("")
            lines += [f"<b>{LETTERS[i]})</b> {esc(o)}" for i, o in enumerate(gt["options"])]
        lines.append("")
        lines.append(f"⏱ Vaqt: <b>{fmt_limit(gt['time_limit_sec'])}</b>")
        return "\n".join(lines)

    async def _announce_group_task(self, game, gt: dict) -> None:
        text = self._task_text(gt)
        markup = None
        if gt["kind"] == "test":
            text += "\n\n👇 Javobni tanlang. Jamoadan <b>birinchi bosilgan</b> javob yakuniy hisoblanadi."
            markup = kb.answer_kb(gt["id"], len(gt["options"]))
        elif gt["kind"] == "trap":
            text += ("\n\n✍️ Javobingizni shu xabarga <b>reply</b> qilib yozing yoki topshiriqni bajaring — "
                     "natijani o‘qituvchi baholaydi. Birdamlik bilan harakat qiling!")
        else:
            text += ("\n\n✍️ Javobni shu xabarga <b>reply</b> qilib yozing. Jamoa nomidan "
                     "<b>birinchi yuborilgan javob</b> yakuniy hisoblanadi — avval kelishib oling!")
        try:
            msg = await tg_call(self.bot.send_message, game["group_id"], text, reply_markup=markup)
        except TelegramAPIError as exc:
            log.error("Topshiriqni guruhga yuborib bo‘lmadi (game %s): %s", game["id"], exc)
            return  # pending holatda qoladi, taymer qayta urinadi
        dm_id = None
        if gt["kind"] == "trap":
            dm = await try_call(
                self.bot.send_message, game["admin_id"],
                f"🪤 <b>Tuzoq ochildi</b> — {esc(game['group_title'])}, {gt['stage_no']}-zina\n\n{esc(gt['question'])}\n\n"
                f"⏱ {fmt_limit(gt['time_limit_sec'])}. Talabalar javobi shu yerga yuboriladi. "
                "Natijani baholang:", reply_markup=kb.grade_kb(gt["id"]))
            dm_id = dm.message_id if dm else None
        await self.games.open_task(gt["id"], msg.message_id, dm_id)

    async def _announce_individual(self, game, gt: dict) -> None:
        user_id = gt["assigned_user_id"]
        for _ in range(8):  # shaxsiy xabar bormasa, boshqa talabaga o‘tamiz
            player = await self.games.db.fetchrow("SELECT * FROM players WHERE tg_id=$1", user_id)
            text = (self._task_text(gt) +
                    ("\n\n👇 Variantni tanlang. Javob bir marta qabul qilinadi." if gt["options"]
                     else "\n\n✍️ Javobingizni shu chatga <b>matn</b> ko‘rinishida yozing. Javob bir marta qabul qilinadi."))
            markup = kb.answer_kb(gt["id"], len(gt["options"])) if gt["options"] else None
            try:
                dm = await tg_call(self.bot.send_message, user_id, "🎯 <b>Sizga maxsus topshiriq!</b>\n\n" + text,
                                   reply_markup=markup)
            except (TelegramForbiddenError, TelegramBadRequest) as exc:
                log.info("Talabaga shaxsiy xabar yuborilmadi (%s): %s", user_id, exc)
                await try_call(
                    self.bot.send_message, game["group_id"],
                    f"⚠️ {mention(user_id, player['full_name'] if player else 'Talaba', player['username'] if player else None)} "
                    "botga shaxsiy /start bosmagan yoki botni bloklagan. Topshiriq boshqa talabaga o‘tkazilmoqda. "
                    "Barcha talabalar botga /start bosishi shart!")
                new = await self.games.reassign_individual(gt["id"], user_id)
                if not new:
                    await try_call(self.bot.send_message, game["group_id"],
                                   "Shaxsiy topshiriq berish uchun mos talaba topilmadi — keyingi topshiriqqa o‘tamiz.")
                    await self.next_task(game["id"], exclude_kinds=("individual",))
                    return
                user_id = new["tg_id"]
                gt = await self.games.get_task(gt["id"])
                continue
            except TelegramAPIError as exc:
                log.error("Individual topshiriq yuborishda xato: %s", exc)
                return
            await self.games.open_task(gt["id"], None, dm.message_id)
            await try_call(
                self.bot.send_message, game["group_id"],
                f"🎯 {mention(user_id, player['full_name'], player['username'])}, sizga maxsus topshiriq yuborildi!\n"
                f"Botning shaxsiy chatiga o‘ting va <b>{fmt_limit(gt['time_limit_sec'])}</b> ichida javob bering.",
                reply_markup=kb.open_bot_kb(self.bot_username))
            return

    async def _ask_admin_trap(self, game, gt: dict) -> None:
        await try_call(self.bot.send_message, game["group_id"],
                       "🪤 <b>Tuzoq!</b> O‘qituvchi tuzoq topshirig‘ini e’lon qilmoqda — tayyor turing!")
        await try_call(
            self.bot.send_message, game["admin_id"],
            f"🪤 <b>Tuzoq vaqti!</b> {esc(game['group_title'])} jamoasi {gt['stage_no']}-zinada tuzoqqa duch keldi.\n"
            "Tuzoq topshirig‘ini o‘zingiz yozing yoki kutubxonadan tanlang:",
            reply_markup=kb.trap_source_kb(gt["id"]))

    # ============================================================ javob natijalari
    async def send_review(self, gt: dict, answer_user: dict, text: str) -> None:
        game = await self.games.get_game(gt["game_id"])
        who = mention(answer_user["tg_id"], answer_user["full_name"], answer_user.get("username"))
        dm = await try_call(
            self.bot.send_message, game["admin_id"],
            f"📝 <b>Javobni tekshiring</b> — {esc(game['group_title'])}, {gt['stage_no']}-zina\n\n"
            f"<b>Topshiriq:</b> {esc(gt['question'])}\n\n<b>Javob</b> ({who}):\n{esc(text)}",
            reply_markup=kb.grade_kb(gt["id"]))
        if dm:
            await self.games.db.execute("UPDATE game_tasks SET dm_message_id=COALESCE(dm_message_id,$2) WHERE id=$1",
                                        gt["id"], dm.message_id)

    async def after_resolve(self, res: Resolution) -> None:
        game = await self.games.get_game(res.game_id)
        gt = res.task
        chat = game["group_id"]
        # topshiriq xabaridagi tugmalarni olib tashlash
        if gt.get("group_message_id"):
            await try_call(self.bot.edit_message_reply_markup, chat_id=chat,
                           message_id=gt["group_message_id"], reply_markup=None)
        answer = await self.games.db.fetchrow(
            "SELECT a.*, p.full_name, p.username FROM answers a JOIN players p ON p.tg_id=a.user_id "
            "WHERE a.game_task_id=$1", gt["id"])
        text = await self._result_text(res, gt, answer)
        kind = "correct" if res.outcome == "correct" else "wrong"
        if res.finished:
            await self._finish(game, res, text)
            return
        await self._send_gif(chat, kind, text)
        await self.send_stair(game, res.new_stage)
        if res.moved == "up":
            await self.send_story_part(game, res.new_stage, up=True)
        elif res.moved == "down":
            await self.send_story_part(game, res.new_stage, up=False)
        await self.next_task(res.game_id)

    async def _result_text(self, res: Resolution, gt: dict, answer) -> str:
        who = ""
        if answer:
            who = f"{mention(answer['user_id'], answer['full_name'], answer['username'])} — "
            if answer["choice_index"] is not None and gt.get("options"):
                letter = LETTERS[answer["choice_index"]]
                who += f"javob: <b>{letter}) {esc(gt['options'][answer['choice_index']])}</b>\n"
            else:
                who += "javob qabul qilindi\n"
        if gt["kind"] == "trap":
            if res.outcome == "correct":
                return f"🛡 <b>Tuzoqdan omon o‘tdingiz!</b> Jamoa birdamlik bilan sinovdan o‘tdi.\n{res.new_stage}-zinada qolasiz."
            head = "⏰ <b>Tuzoq vaqti tugadi!</b>" if res.outcome == "timeout" else "💥 <b>Tuzoq ishladi!</b>"
            return f"{head}\n{self._move_line(res)}"
        if res.outcome == "correct":
            return f"✅ <b>To‘g‘ri!</b>\n{who}{self._move_line(res)}"
        if res.outcome == "timeout":
            return f"⏰ <b>Vaqt tugadi!</b> Javob berilmadi — noto‘g‘ri hisoblanadi.\n{self._move_line(res)}"
        reveal = ""
        if (gt.get("correct_option") is not None and gt.get("options")
                and await self.settings.get_bool("reveal_correct")):
            reveal = f"To‘g‘ri javob: <b>{LETTERS[gt['correct_option']]}) {esc(gt['options'][gt['correct_option']])}</b>\n"
        return f"❌ <b>Noto‘g‘ri.</b>\n{who}{reveal}{self._move_line(res)}"

    @staticmethod
    def _move_line(res: Resolution) -> str:
        if res.moved == "up":
            return f"🔼 Jamoa <b>{res.old_stage}-zinadan {res.new_stage}-zinaga</b> ko‘tarildi!"
        if res.moved == "down":
            return f"🔽 Jamoa <b>{res.old_stage}-zinadan {res.new_stage}-zinaga</b> tushdi."
        if res.new_stage == 1 and res.outcome != "correct":
            return "Jamoa 1-zinada qoldi — pastga tushib bo‘lmaydi."
        return f"Jamoa {res.new_stage}-zinada qoldi."

    # =============================================================== yakunlash
    async def _finish(self, game, res: Resolution, result_text: str) -> None:
        chat = game["group_id"]
        stage = await self.stories.get_stage(game["story_id"], 10)
        await self._send_gif(chat, "victory", "🏆 <b>G‘ALABA!</b> Jamoa 10-zinaga yetdi!\n" + result_text)
        await self.send_stair(game, 10)
        if stage:
            if stage["media_file_id"]:
                send = self.bot.send_animation if stage["media_type"] == "animation" else self.bot.send_photo
                kwargs = {"animation" if stage["media_type"] == "animation" else "photo": stage["media_file_id"]}
                await try_call(send, chat, **kwargs)
            scene = f"🏁 <b>10-bosqich · {esc(stage['title'])}</b>\n\n{esc(stage['body'])}"
            if stage["final_scene"]:
                scene += f"\n\n{esc(stage['final_scene'])}"
            for part in split_text(scene):
                await try_call(self.bot.send_message, chat, part)
        stats = await self.games.stats(game["id"])
        summary = format_stats(stats, title="📊 Yakuniy natijalar")
        await try_call(self.bot.send_message, chat, summary)
        await try_call(self.bot.send_message, game["admin_id"],
                       f"🏆 <b>{esc(game['group_title'])}</b> jamoasi o‘yinni yakunladi!\n\n{summary}")

    async def announce_cancel(self, game_id: int) -> None:
        game = await self.games.get_game(game_id)
        stats = await self.games.stats(game_id)
        text = (f"🛑 O‘yin o‘qituvchi tomonidan bekor qilindi. Jamoa {stats['stage']}-zinada to‘xtadi.\n\n"
                + format_stats(stats, title="📊 Natijalar"))
        await try_call(self.bot.send_message, game["group_id"], text)

    async def announce_pause(self, game_id: int) -> None:
        game = await self.games.get_game(game_id)
        await try_call(self.bot.send_message, game["group_id"],
                       "⏸ <b>O‘yin pauzaga qo‘yildi.</b> Vaqt hisoblagichi to‘xtatildi.")

    async def announce_resume(self, game_id: int) -> None:
        game = await self.games.get_game(game_id)
        await try_call(self.bot.send_message, game["group_id"],
                       "▶️ <b>O‘yin davom etmoqda!</b> Vaqt hisoblagichi qayta ishga tushdi.")
        await self.recover_game(game_id)

    async def recover_game(self, game_id: int) -> None:
        """Pauza/qayta ishga tushishdan keyin to‘xtab qolgan bosqichlarni davom ettiradi."""
        for gt in await self.games.needs_input_tasks(game_id):
            await self._ask_admin_trap(await self.games.get_game(game_id), gt)
        for gt_id in await self.games.stale_pending_ids():
            gt = await self.games.get_task(gt_id)
            if gt and gt["game_id"] == game_id:
                await self.announce(gt_id)
        if game_id in await self.games.idle_game_ids():
            await self.next_task(game_id)
