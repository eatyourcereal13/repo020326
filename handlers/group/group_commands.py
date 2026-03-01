from aiogram import Router, F
from aiogram.types import Message, ChatMemberUpdated
from aiogram.filters import Command, ChatMemberUpdatedFilter, IS_NOT_MEMBER, MEMBER
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.db import async_session
from database.models import User
from handlers.private.start import get_level_info, create_progress_bar, LEVELS
from config import config

router = Router()


async def check_allowed_group(message: Message) -> bool:
    if message.chat.id in config.ALLOWED_GROUPS:
        return True
    
    await message.reply("Пиши бота сам, бездарь")
    await message.bot.leave_chat(message.chat.id)
    return False


@router.my_chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> MEMBER))
async def bot_added_to_group(event: ChatMemberUpdated):
    chat_id = event.chat.id
    
    if chat_id not in config.ALLOWED_GROUPS:
        await event.bot.send_message(
            chat_id,
            "Пиши бота сам, бездарь"
        )
        await event.bot.leave_chat(chat_id)


def get_exp_for_level(level: int) -> int:
    return LEVELS.get(level, LEVELS[20] + 1000)


@router.message(F.chat.type.in_({"group", "supergroup"}), Command("profile"))
async def group_profile(message: Message):
    if not await check_allowed_group(message):
        return
    
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
    
    if not user:
        from database.requests import get_or_create_user
        user = await get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
    
    level, exp_needed, progress, level_title, rank_emoji = get_level_info(user.exp)
    progress_bar = create_progress_bar(progress)
    
    next_level = level + 1
    next_level_exp = LEVELS.get(next_level, LEVELS[level] + 1000)
    
    text = (
        f"👤 <b>ПРОФИЛЬ</b> {message.from_user.first_name}\n\n"
        f"┠ {rank_emoji} <b>РАНГ:</b> {level_title}\n"
        f"┠ {progress_bar} <code>{progress:.1f}%</code>\n"
        f"┠ <b>ОПЫТ:</b> <code>{user.exp} / {next_level_exp}</code>\n"
        f"┠ До {next_level} ур.: <code>{exp_needed}</code> опыта\n\n"
        f"┠ <b>ФИНАНСЫ:</b>\n"
        f"┠   💰 Текущие: <code>{user.current_money}</code> \n"
        f"┠   📈 Всего: <code>{user.total_money}</code> \n\n"
        f"┠ <b>СТАТИСТИКА:</b>\n"
        f"┠   ⚓ Рейдов: <code>{user.voyages_completed}</code>\n"
        f"┠   👑 Легендарных: <code>{user.legendary_finds}</code>"
    )
    
    await message.reply(text)


@router.message(F.chat.type.in_({"group", "supergroup"}), Command("ship"))
async def group_ship(message: Message):
    if not await check_allowed_group(message):
        return
    
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == message.from_user.id)
            .options(selectinload(User.ship), selectinload(User.crew))
        )
        user = result.scalar_one_or_none()
    
    if not user or not user.ship:
        await message.reply("❌ Сначала зарегистрируйся в игре")
        return
    
    from game_logic.cooldown import calculate_cooldown, get_remaining_cooldown, format_cooldown
    
    ship = user.ship
    crew = user.crew
    
    current_cooldown = calculate_cooldown(user)
    
    remaining = get_remaining_cooldown(user)
    cooldown_status = "┠ ✅ <b>ГОТОВ К ПЛАВАНИЮ!</b>"
    if remaining > 0:
        cooldown_status = f"┠ ⏳ <b>ПЕРЕЗАРЯДКА:</b> {format_cooldown(remaining)}"
    
    loot_quantity_bonus = ship.sails_level
    loot_value_bonus = ship.hold_level * 5
    rare_chance_bonus = ship.copper_sheathing_level * 3
    combat_power_bonus = ship.cannons_level * 8
    damage_reduction = ship.hull_level * 5
    
    event_damage_reduction = 15 if crew.boatswain_level > 0 else 0
    consumables_bonus = crew.cook_level * 10
    combat_damage_bonus = crew.gunner_level * 12
    rare_event_bonus = crew.navigator_level * 4
    casino_luck_bonus = crew.parrot_level * 2
    
    health_percent = int((ship.health / ship.max_health) * 10)
    health_bar = "█" * health_percent + "░" * (10 - health_percent)
    
    morale_percent = int(crew.morale / 10)
    morale_bar = "█" * morale_percent + "░" * (10 - morale_percent)
    
    text = (
        f"⚓ <b>КОРАБЛЬ</b> {message.from_user.first_name}\n\n"
        f"┠ <b>ПРОЧНОСТЬ:</b> {ship.health}/{ship.max_health}\n"
        f"┠ <code>{health_bar}</code> {int((ship.health/ship.max_health)*100)}%\n\n"
        f"┠ <b>КОРАБЛЬ:</b>\n"
        f"┠ ⚙️ Паруса: <b>{ship.sails_level}</b> ур. ┠ +{loot_quantity_bonus} предмет\n"
        f"┠ 🛡️ Корпус: <b>{ship.hull_level}</b> ур. ┠ -{damage_reduction}% урона\n"
        f"┠ 🔫 Пушки: <b>{ship.cannons_level}</b> ур. ┠ +{combat_power_bonus}% силы\n"
        f"┠ 📦 Трюм: <b>{ship.hold_level}</b> ур. ┠ +{loot_value_bonus}% ценности\n"
        f"┠ 🧲 Обшивка: <b>{ship.copper_sheathing_level}</b> ур. ┠ +{rare_chance_bonus}% к редким\n"
        f"┠ 🔥 Двигатель: <b>{ship.steam_engine_level}/5</b> ур.\n\n"
        f"┠ <b>КОМАНДА:</b>\n"
        f"┠ 👨‍✈️ Боцман: <b>{crew.boatswain_level}/1</b> ┠ -{event_damage_reduction}% урона от событий\n"
        f"┠ 👨‍🍳 Кок: <b>{crew.cook_level}/5</b> ┠ +{consumables_bonus}% ценности провизии\n"
        f"┠ 🔫 Канонир: <b>{crew.gunner_level}/5</b> ┠ +{combat_damage_bonus}% урона\n"
        f"┠ 🧭 Штурман: <b>{crew.navigator_level}/5</b> ┠ +{rare_event_bonus}% к событиям\n"
        f"┠ 🦜 Попугай: <b>{crew.parrot_level}/3</b> ┠ +{casino_luck_bonus}% к дублям\n\n"
        f"┠ <b>МОРАЛЬ:</b> {crew.morale}%\n"
        f"┠ <code>{morale_bar}</code>\n\n"
        f"{cooldown_status}\n"
        f"┠ ⏱️ <b>Базовая перезарядка:</b> {format_cooldown(current_cooldown)}"
    )
    
    await message.reply(text)


@router.message(F.chat.type.in_({"group", "supergroup"}), Command("top"))
async def group_top(message: Message):
    if not await check_allowed_group(message):
        return
    
    async with async_session() as session:
        top_level = await session.execute(
            select(User)
            .order_by(User.exp.desc())
            .limit(5)
        )
        top_level_users = top_level.scalars().all()
        
        top_money = await session.execute(
            select(User)
            .order_by(User.total_money.desc())
            .limit(5)
        )
        top_money_users = top_money.scalars().all()
        
        top_voyages = await session.execute(
            select(User)
            .order_by(User.voyages_completed.desc())
            .limit(5)
        )
        top_voyages_users = top_voyages.scalars().all()
    
    text = "🏆 <b>ТОП ПИРАТОВ</b>\n\n"
    
    text += "📊 <b>ПО УРОВНЮ:</b>\n"
    if top_level_users:
        for i, user in enumerate(top_level_users, 1):
            name = user.first_name or f"ID{user.telegram_id}"
            if len(name) > 15:
                name = name[:12] + "..."
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            
            level, _, _, _, _ = get_level_info(user.exp)
            
            text += f"┠ {medal} {name} — <b>Уровень {level}</b>\n"
    else:
        text += "┠ <i>Пока нет данных</i>\n"
    
    text += "\n"
    
    text += "💰 <b>САМЫЕ БОГАТЫЕ:</b>\n"
    if top_money_users:
        for i, user in enumerate(top_money_users, 1):
            name = user.first_name or f"ID{user.telegram_id}"
            if len(name) > 15:
                name = name[:12] + "..."
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            
            text += f"┠ {medal} {name} — <code>{user.total_money}</code>\n"
    else:
        text += "┠ <i>Пока нет данных</i>\n"
    
    text += "\n"
    
    text += "⚓ <b>САМЫЕ ОПЫТНЫЕ:</b>\n"
    if top_voyages_users:
        for i, user in enumerate(top_voyages_users, 1):
            name = user.first_name or f"ID{user.telegram_id}"
            if len(name) > 15:
                name = name[:12] + "..."
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            
            text += f"┠ {medal} {name} — <code>{user.voyages_completed}</code> рейдов\n"
    else:
        text += "┠ <i>Пока нет данных</i>\n"
    
    await message.reply(text)