import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from metaphor_bot.config import settings
from metaphor_bot.db import apply_all_migrations, connect
from metaphor_bot.flows import (
    CHECK_IN_STEPS,
    SITUATION_STEPS,
    check_in_intro,
    day_card_intro,
    onboarding_text,
    render_check_in_summary,
    render_patterns_summary,
    render_situation_summary,
    situation_intro,
)
from metaphor_bot.repository import (
    ActiveFlowState,
    clear_active_flow,
    complete_session,
    get_active_flow,
    log_safety_event,
    recent_insights,
    get_user_metrics,
    get_global_metrics,
    get_scenario_metrics,
    save_insight,
    save_message,
    set_active_flow,
    start_session,
    summarize_patterns,
    upsert_user,
)
from metaphor_bot.safety import detect_red_flag, safety_reply

logging.basicConfig(level=logging.INFO)


def _check_safety(conn, user_id: int, session_id: int, body: str) -> str | None:
    category = detect_red_flag(body)
    if not category:
        return None

    reply = safety_reply()
    log_safety_event(conn, user_id, session_id, body[:500], category)
    save_message(conn, session_id, "system", f"safety_trigger:{category}")
    save_message(conn, session_id, "bot", reply)
    complete_session(conn, session_id, "safety_interrupted")
    clear_active_flow(conn, user_id)
    return reply


def _restart_active_flow_if_any(conn, user_id: int) -> None:
    flow = get_active_flow(conn, user_id)
    if flow:
        clear_active_flow(conn, user_id)
        complete_session(conn, flow.session_id, "aborted")


def build_dispatcher(conn):
    dp = Dispatcher()

    @dp.message(Command("start"))
    async def handle_start(message: Message):
        user = message.from_user
        user_id = upsert_user(conn, user.id, user.username, user.first_name)
        session_id = start_session(conn, user_id, "onboarding")
        text = onboarding_text()
        save_message(conn, session_id, "bot", text)
        complete_session(conn, session_id)
        await message.answer(text)

    @dp.message(Command("cancel"))
    async def handle_cancel(message: Message):
        user = message.from_user
        user_id = upsert_user(conn, user.id, user.username, user.first_name)
        flow = get_active_flow(conn, user_id)
        if flow:
            clear_active_flow(conn, user_id)
            complete_session(conn, flow.session_id, "aborted")
            await message.answer("Текущая сессия остановлена. Когда будешь готов(а), выбери новый сценарий.")
            return
        await message.answer("Сейчас нет активной сессии. Доступно: /day_card, /check_in, /situation")

    @dp.message(Command("day_card"))
    async def handle_day_card(message: Message):
        user = message.from_user
        user_id = upsert_user(conn, user.id, user.username, user.first_name)
        _restart_active_flow_if_any(conn, user_id)
        session_id = start_session(conn, user_id, "day_card")
        text = day_card_intro()
        save_message(conn, session_id, "bot", text)
        complete_session(conn, session_id)
        await message.answer(text)

    @dp.message(Command("check_in"))
    async def handle_check_in(message: Message):
        user = message.from_user
        user_id = upsert_user(conn, user.id, user.username, user.first_name)
        _restart_active_flow_if_any(conn, user_id)
        session_id = start_session(conn, user_id, "check_in")
        text = check_in_intro()
        set_active_flow(conn, ActiveFlowState(scenario="check_in", user_id=user_id, session_id=session_id, step=0, answers=[]))
        save_message(conn, session_id, "bot", text)
        await message.answer(text)

    @dp.message(Command("situation"))
    async def handle_situation(message: Message):
        user = message.from_user
        user_id = upsert_user(conn, user.id, user.username, user.first_name)
        _restart_active_flow_if_any(conn, user_id)
        session_id = start_session(conn, user_id, "situation")
        text = situation_intro()
        set_active_flow(conn, ActiveFlowState(scenario="situation", user_id=user_id, session_id=session_id, step=0, answers=[]))
        save_message(conn, session_id, "bot", text)
        await message.answer(text)

    @dp.message(Command("save_insight"))
    async def handle_save_insight(message: Message, command: CommandObject):
        user = message.from_user
        user_id = upsert_user(conn, user.id, user.username, user.first_name)
        _restart_active_flow_if_any(conn, user_id)
        session_id = start_session(conn, user_id, "save_insight")

        if not command.args:
            reply = "Формат: /save_insight <инсайт> | <маленький шаг>. Шаг можно опустить."
            save_message(conn, session_id, "bot", reply)
            complete_session(conn, session_id, "aborted")
            await message.answer(reply)
            return

        if "|" in command.args:
            insight_text, next_step = [part.strip() for part in command.args.split("|", 1)]
        else:
            insight_text, next_step = command.args.strip(), None

        if not insight_text:
            reply = "Инсайт не должен быть пустым. Пример: /save_insight Я устал | лечь спать до 23:00"
            save_message(conn, session_id, "bot", reply)
            complete_session(conn, session_id, "aborted")
            await message.answer(reply)
            return

        save_insight(conn, session_id, user_id, insight_text, next_step)
        reply = "Сохранил в личную историю. Вернуться к записям: /history"
        save_message(conn, session_id, "bot", reply)
        complete_session(conn, session_id)
        await message.answer(reply)

    @dp.message(Command("history"))
    async def handle_history(message: Message):
        user = message.from_user
        user_id = upsert_user(conn, user.id, user.username, user.first_name)
        _restart_active_flow_if_any(conn, user_id)
        session_id = start_session(conn, user_id, "history")
        rows = recent_insights(conn, user_id, limit=5)
        if not rows:
            reply = "История пока пустая. Добавь первую запись через /save_insight"
        else:
            lines = ["Последние инсайты:"]
            for idx, row in enumerate(rows, start=1):
                step = f" | шаг: {row['next_step']}" if row["next_step"] else ""
                lines.append(f"{idx}. {row['insight_text']}{step}")
            reply = "\n".join(lines)

        save_message(conn, session_id, "bot", reply)
        complete_session(conn, session_id)
        await message.answer(reply)


    @dp.message(Command("metrics"))
    async def handle_metrics(message: Message):
        user = message.from_user
        user_id = upsert_user(conn, user.id, user.username, user.first_name)
        _restart_active_flow_if_any(conn, user_id)
        session_id = start_session(conn, user_id, "metrics")

        metrics = get_user_metrics(conn, user_id)
        completion_rate = 0
        if metrics.total_sessions > 0:
            completion_rate = round(metrics.completed_sessions * 100 / metrics.total_sessions)

        reply = (
            "Твои метрики на текущий момент:\n"
            f"- Сессий всего: {metrics.total_sessions}\n"
            f"- Завершено: {metrics.completed_sessions} ({completion_rate}%)\n"
            f"- Сохранено инсайтов: {metrics.insight_count}\n"
            f"- Safety-срабатываний: {metrics.safety_events}"
        )

        save_message(conn, session_id, "bot", reply)
        complete_session(conn, session_id)
        await message.answer(reply)


    @dp.message(Command("admin_metrics"))
    async def handle_admin_metrics(message: Message, command: CommandObject):
        user = message.from_user
        user_id = upsert_user(conn, user.id, user.username, user.first_name)
        _restart_active_flow_if_any(conn, user_id)
        session_id = start_session(conn, user_id, "admin_metrics")

        if user.id not in settings.admin_ids_set:
            reply = "Недостаточно прав для этой команды."
            save_message(conn, session_id, "bot", reply)
            complete_session(conn, session_id, "aborted")
            await message.answer(reply)
            return

        days: int | None = None
        if command.args:
            arg = command.args.strip()
            if not arg.isdigit():
                reply = "Формат: /admin_metrics или /admin_metrics <days>. Пример: /admin_metrics 7"
                save_message(conn, session_id, "bot", reply)
                complete_session(conn, session_id, "aborted")
                await message.answer(reply)
                return
            days = int(arg)
            if days <= 0:
                reply = "Количество дней должно быть положительным числом."
                save_message(conn, session_id, "bot", reply)
                complete_session(conn, session_id, "aborted")
                await message.answer(reply)
                return

        metrics = get_global_metrics(conn, days=days)
        by_scenario = get_scenario_metrics(conn, days=days)
        completion_rate = 0
        if metrics.total_sessions > 0:
            completion_rate = round(metrics.completed_sessions * 100 / metrics.total_sessions)

        period = f"за последние {days} дн." if days else "за всё время"
        lines = [
            f"Админ-метрики проекта ({period}):",
            f"- Пользователей: {metrics.total_users}",
            f"- Сессий всего: {metrics.total_sessions}",
            f"- Завершено: {metrics.completed_sessions} ({completion_rate}%)",
            f"- Инсайтов сохранено: {metrics.total_insights}",
            f"- Safety-событий: {metrics.total_safety_events}",
            "- По сценариям:",
        ]
        if by_scenario:
            for item in by_scenario:
                item_rate = round(item.completed_sessions * 100 / item.total_sessions) if item.total_sessions else 0
                lines.append(f"  • {item.scenario}: {item.completed_sessions}/{item.total_sessions} ({item_rate}%)")
        else:
            lines.append("  • данных пока нет")

        reply = "\n".join(lines)

        save_message(conn, session_id, "bot", reply)
        complete_session(conn, session_id)
        await message.answer(reply)

    @dp.message(Command("patterns"))
    async def handle_patterns(message: Message):
        user = message.from_user
        user_id = upsert_user(conn, user.id, user.username, user.first_name)
        _restart_active_flow_if_any(conn, user_id)
        session_id = start_session(conn, user_id, "patterns")
        patterns = summarize_patterns(conn, user_id)
        reply = render_patterns_summary(patterns)
        save_message(conn, session_id, "bot", reply)
        complete_session(conn, session_id)
        await message.answer(reply)

    @dp.message()
    async def handle_text(message: Message):
        body = message.text or ""
        user = message.from_user
        user_id = upsert_user(conn, user.id, user.username, user.first_name)

        flow = get_active_flow(conn, user_id)
        if flow:
            save_message(conn, flow.session_id, "user", body)
            safety = _check_safety(conn, flow.user_id, flow.session_id, body)
            if safety:
                await message.answer(safety)
                return

            answers = flow.answers + [body]
            step = flow.step + 1

            if flow.scenario == "check_in":
                if step < len(CHECK_IN_STEPS):
                    set_active_flow(conn, ActiveFlowState("check_in", flow.user_id, flow.session_id, step, answers))
                    reply = CHECK_IN_STEPS[step]
                    save_message(conn, flow.session_id, "bot", reply)
                    await message.answer(reply)
                    return

                insight_text, next_step = render_check_in_summary(answers)
                save_insight(conn, flow.session_id, flow.user_id, insight_text, next_step)
                reply = "Спасибо. Сформулировал и сохранил твой чек-ин в историю. Посмотреть: /history"
                save_message(conn, flow.session_id, "bot", reply)
                complete_session(conn, flow.session_id)
                clear_active_flow(conn, flow.user_id)
                await message.answer(reply)
                return

            if flow.scenario == "situation":
                if step < len(SITUATION_STEPS):
                    set_active_flow(conn, ActiveFlowState("situation", flow.user_id, flow.session_id, step, answers))
                    reply = SITUATION_STEPS[step]
                    save_message(conn, flow.session_id, "bot", reply)
                    await message.answer(reply)
                    return

                insight_text, next_step = render_situation_summary(answers)
                save_insight(conn, flow.session_id, flow.user_id, insight_text, next_step)
                reply = "Разбор завершён: вывод и шаг сохранены. Можешь открыть /history"
                save_message(conn, flow.session_id, "bot", reply)
                complete_session(conn, flow.session_id)
                clear_active_flow(conn, flow.user_id)
                await message.answer(reply)
                return

        session_id = start_session(conn, user_id, "free_text")
        save_message(conn, session_id, "user", body)

        safety = _check_safety(conn, user_id, session_id, body)
        if safety:
            await message.answer(safety)
            return

        reply = (
            "Я рядом. Используй /day_card, /check_in или /situation. "
            "Инсайт можно сохранить через /save_insight, повторяющиеся темы посмотреть через /patterns, а сводку активности через /metrics (для админа: /admin_metrics)"
        )
        save_message(conn, session_id, "bot", reply)
        complete_session(conn, session_id)
        await message.answer(reply)

    return dp


async def main() -> None:
    conn = connect(settings.database_path)
    apply_all_migrations(conn)

    bot = Bot(token=settings.bot_token)
    dp = build_dispatcher(conn)
    await dp.start_polling(bot)
