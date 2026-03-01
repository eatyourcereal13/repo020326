import json
import os
from aiogram import Router, F
from sqlalchemy.orm import selectinload
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy import select, func
from datetime import datetime, timedelta
import asyncio

from database.db import async_session
from database.models import User, Ship, Crew
from config import config
from keyboards.admin import admin_keyboards

router = Router()

broadcast_data = {}
COOLDOWN_PRICE_FILE = os.path.join(config.BASE_DIR, 'data', 'cooldown_price.json')
ITEMS_PRICE_FILE = os.path.join(config.BASE_DIR, 'data', 'items_prices.json')

def get_cooldown_price():
    try:
        with open(COOLDOWN_PRICE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('price', 1)
    except:
        return 1

def save_cooldown_price(price: int):
    with open(COOLDOWN_PRICE_FILE, 'w', encoding='utf-8') as f:
        json.dump({'price': price}, f, ensure_ascii=False, indent=2)

def get_item_price(item_id: str) -> int:
    try:
        with open(ITEMS_PRICE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get(item_id, 2)
    except:
        return 2

def save_item_price(item_id: str, price: int):
    try:
        with open(ITEMS_PRICE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        data = {}
    
    data[item_id] = price
    
    with open(ITEMS_PRICE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


@router.message(Command("admin"))
async def admin_start(message: Message):
    if not is_admin(message.from_user.id):
        await message.delete()
        return
    
    await message.answer(
        "👑 АДМИН-ПАНЕЛЬ\n\n┠ Выбери действие:",
        reply_markup=admin_keyboards.admin_main_keyboard()
    )


@router.message(F.text == "🔙 Выход")
async def admin_exit(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(
        "👋 Вышел из админ-панели",
        reply_markup=admin_keyboards.admin_main_keyboard()
    )


@router.message(F.text == "🔙 Назад")
async def admin_back(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(
        "👑 АДМИН-ПАНЕЛЬ\n\n┠ Выбери действие:",
        reply_markup=admin_keyboards.admin_main_keyboard()
    )


@router.message(F.text == "📊 Статистика")
async def admin_stats(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    async with async_session() as session:
        total_users = await session.scalar(select(func.count(User.id)))
        
        today = datetime.utcnow().date()
        active_today = await session.scalar(
            select(func.count(User.id)).where(func.date(User.last_activity) == today)
        )
        
        week_ago = datetime.utcnow() - timedelta(days=7)
        active_week = await session.scalar(
            select(func.count(User.id)).where(User.last_activity >= week_ago)
        )
        
        new_today = await session.scalar(
            select(func.count(User.id)).where(func.date(User.registered_at) == today)
        )
        
        total_money = await session.scalar(select(func.sum(User.current_money))) or 0
        total_voyages = await session.scalar(select(func.sum(User.voyages_completed))) or 0
    
    text = (
        f"📊 <b>СТАТИСТИКА</b>\n\n"
        f"┠ 👥 Всего пользователей: <code>{total_users}</code>\n"
        f"┠ 🟢 Активных сегодня: <code>{active_today}</code>\n"
        f"┠ 📅 Активных за неделю: <code>{active_week}</code>\n"
        f"┠ 🆕 Новых сегодня: <code>{new_today}</code>\n\n"
        f"┠ 💰 Всего монет: <code>{total_money:,.0f}</code>\n"
        f"┠ ⚓ Всего рейдов: <code>{total_voyages}</code>"
    )
    
    await message.answer(text, reply_markup=admin_keyboards.admin_back_keyboard())


@router.message(F.text == "📈 Топ")
async def admin_top(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    async with async_session() as session:
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
    
    text = "🏆 <b>ТОП ИГРОКОВ</b>\n\n"
    
    text += "┠ <b>💰 ПО МОНЕТАМ:</b>\n"
    for i, user in enumerate(top_money_users, 1):
        name = user.first_name or f"ID{user.telegram_id}"
        text += f"┠ {i}. {name} — <code>{user.total_money}</code>💰 (ур.{user.level})\n"
    
    text += "\n┠ <b>⚓ ПО РЕЙДАМ:</b>\n"
    for i, user in enumerate(top_voyages_users, 1):
        name = user.first_name or f"ID{user.telegram_id}"
        text += f"┠ {i}. {name} — <code>{user.voyages_completed}</code> рейдов\n"
    
    await message.answer(text, reply_markup=admin_keyboards.admin_back_keyboard())


@router.message(F.text == "👥 Пользователи")
async def admin_users(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    async with async_session() as session:
        level_stats = await session.execute(
            select(User.level, func.count(User.id))
            .group_by(User.level)
            .order_by(User.level)
        )
        levels = level_stats.all()
        
        last_users = await session.execute(
            select(User)
            .order_by(User.registered_at.desc())
            .limit(5)
        )
        last_users = last_users.scalars().all()
    
    text = "👥 <b>ПОЛЬЗОВАТЕЛИ</b>\n\n"
    
    text += "┠ <b>УРОВНИ:</b>\n"
    for level, count in levels:
        text += f"┠ • {level} ур.: <code>{count}</code> чел.\n"
    
    text += "\n┠ <b>ПОСЛЕДНИЕ РЕГИСТРАЦИИ:</b>\n"
    for user in last_users:
        name = user.first_name or f"ID{user.telegram_id}"
        date = user.registered_at.strftime("%d.%m %H:%M")
        text += f"┠ • {name} — {date}\n"
    
    await message.answer(text, reply_markup=admin_keyboards.admin_back_keyboard())


@router.message(F.text == "⚙️ Настройки")
async def admin_settings(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    current_price = get_cooldown_price()
    
    text = (
        f"⚙️ <b>НАСТРОЙКИ</b>\n\n"
        f"┠ 💰 Текущая цена пропуска: <code>{current_price}</code> ⭐\n\n"
        f"┠ Выбери что хочешь изменить:"
    )
    
    await message.answer(text, reply_markup=admin_keyboards.admin_settings_keyboard())


@router.message(F.text == "💰 Цена пропуска")
async def admin_cooldown_price(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    current_price = get_cooldown_price()
    
    text = (
        f"💰 <b>ИЗМЕНЕНИЕ ЦЕНЫ ПРОПУСКА</b>\n\n"
        f"┠ Текущая цена: <code>{current_price}</code> ⭐\n\n"
        f"┠ Выбери новую цену:"
    )
    
    await message.answer(text, reply_markup=admin_keyboards.admin_price_keyboard())


@router.message(F.text.in_(["1 🌟", "2 🌟", "3 🌟", "5 🌟", "10 🌟", "15 🌟", "20 🌟"]))
async def admin_set_price(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    price = int(message.text.split()[0])
    save_cooldown_price(price)
    
    await message.answer(
        f"✅ <b>ЦЕНА ПРОПУСКА ИЗМЕНЕНА</b>\n\n┠ Новая цена пропуска: <code>{price}</code> ⭐",
        reply_markup=admin_keyboards.admin_settings_keyboard()
    )


@router.message(F.text == "🏪 Цены в магазине")
async def admin_shop_prices(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    ticket_price = get_item_price('death_island_ticket')
    map_price = get_item_price('treasure_map')
    amulet_price = get_item_price('luck_amulet')
    
    text = (
        f"🏪 <b>ЦЕНЫ В МАГАЗИНЕ</b>\n\n"
        f"┠ 🎫 Билет на Остров смерти: <code>{ticket_price}</code> ✨\n"
        f"┠ 🗺️ Карта сокровищ: <code>{map_price}</code> ✨\n"
        f"┠ 🍀 Амулет удачи: <code>{amulet_price}</code> ✨\n\n"
        f"┠ Выбери предмет для изменения цены:"
    )
    
    await message.answer(text, reply_markup=admin_keyboards.admin_shop_prices_keyboard())


@router.message(F.text == "Билет на Остров смерти")
async def admin_ticket_price(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    current_price = get_item_price('death_island_ticket')
    
    current_item[message.from_user.id] = 'death_island_ticket'
    
    text = (
        f"🎫 <b>ИЗМЕНЕНИЕ ЦЕНЫ БИЛЕТА</b>\n\n"
        f"┠ Текущая цена: <code>{current_price}</code> ✨\n\n"
        f"┠ Выбери новую цену:"
    )
    
    await message.answer(text, reply_markup=admin_keyboards.admin_item_price_keyboard())


@router.message(F.text == "Карта сокровищ")
async def admin_map_price(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    current_price = get_item_price('treasure_map')
    
    current_item[message.from_user.id] = 'treasure_map'
    
    text = (
        f"🗺️ <b>ИЗМЕНЕНИЕ ЦЕНЫ КАРТЫ</b>\n\n"
        f"┠ Текущая цена: <code>{current_price}</code> ✨\n\n"
        f"┠ Выбери новую цену:"
    )
    
    await message.answer(text, reply_markup=admin_keyboards.admin_item_price_keyboard())


@router.message(F.text == "Амулет удачи")
async def admin_amulet_price(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    current_price = get_item_price('luck_amulet')
    
    current_item[message.from_user.id] = 'luck_amulet'
    
    text = (
        f"🍀 <b>ИЗМЕНЕНИЕ ЦЕНЫ АМУЛЕТА</b>\n\n"
        f"┠ Текущая цена: <code>{current_price}</code> ✨\n\n"
        f"┠ Выбери новую цену:"
    )
    
    await message.answer(text, reply_markup=admin_keyboards.admin_item_price_keyboard())


item_price_map = {
    "Билет на Остров смерти": "death_island_ticket",
    "Карта сокровищ": "treasure_map",
    "Амулет удачи": "luck_amulet"
}

current_item = {}

@router.message(F.text.in_(["1 ✨", "2 ✨", "3 ✨", "5 ✨", "10 ✨", "15 ✨", "20 ✨"]))
async def admin_set_item_price(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    if message.from_user.id not in current_item:
        return
    
    price = int(message.text.split()[0])
    item_id = current_item[message.from_user.id]
    item_name = {
        "death_island_ticket": "Билет на Остров смерти",
        "treasure_map": "Карта сокровищ", 
        "luck_amulet": "Амулет удачи"
    }[item_id]
    
    save_item_price(item_id, price)
    del current_item[message.from_user.id]
    
    await message.answer(
        f"✅ <b>ЦЕНА ИЗМЕНЕНА</b>\n\n┠ {item_name}: <code>{price}</code> ✨",
        reply_markup=admin_keyboards.admin_shop_prices_keyboard()
    )


@router.message(F.text == "🔄 Ресет прогресса")
async def admin_reset_menu(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    text = (
        f"⚠️ <b>СБРОС ПРОГРЕССА</b>\n\n"
        f"┠ <b>ВНИМАНИЕ!</b> Это действие:\n"
        f"┠ • Удаляет все предметы из инвентаря\n"
        f"┠ • Сбрасывает монеты и опыт\n"
        f"┠ • Обнуляет статистику рейдов\n"
        f"┠ • Сбрасывает улучшения корабля\n"
        f"┠ • Удаляет активные эффекты\n\n"
        f"┠ <i>Это действие нельзя отменить!</i>\n\n"
        f"┠ Нажми <b>⚠️ ПОЛНЫЙ СБРОС</b> для подтверждения"
    )
    
    await message.answer(text, reply_markup=admin_keyboards.admin_reset_keyboard())


@router.message(F.text == "⚠️ ПОЛНЫЙ СБРОС")
async def admin_reset_confirm(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .options(
                selectinload(User.ship),
                selectinload(User.crew),
                selectinload(User.inventory),
                selectinload(User.active_effects),
                selectinload(User.voyage)
            )
        )
        users = result.scalars().all()
        
        reset_count = 0
        for user in users:
            try:
                if user.inventory:
                    for item in user.inventory:
                        await session.delete(item)
                
                if user.voyage:
                    await session.delete(user.voyage)
                
                if user.active_effects:
                    for effect in user.active_effects:
                        await session.delete(effect)
                
                user.current_money = 0
                user.total_money = 0
                user.exp = 0
                user.level = 1
                user.voyages_completed = 0
                user.legendary_finds = 0
                user.traders_attacked = 0
                user.kraken_defeated = 0
                user.last_voyage_time = None
                user.last_voyage_location = 'navirettnye_ostrova'
                
                if user.ship:
                    user.ship.sails_level = 0
                    user.ship.hull_level = 0
                    user.ship.cannons_level = 0
                    user.ship.hold_level = 0
                    user.ship.copper_sheathing_level = 0
                    user.ship.steam_engine_level = 0
                    user.ship.health = 100
                    user.ship.max_health = 100
                else:
                    ship = Ship(
                        user_id=user.id,
                        sails_level=0,
                        hull_level=0,
                        cannons_level=0,
                        hold_level=0,
                        copper_sheathing_level=0,
                        steam_engine_level=0,
                        health=100,
                        max_health=100
                    )
                    session.add(ship)
                
                if user.crew:
                    user.crew.boatswain_level = 0
                    user.crew.cook_level = 0
                    user.crew.gunner_level = 0
                    user.crew.navigator_level = 0
                    user.crew.parrot_level = 0
                    user.crew.morale = 100
                else:
                    crew = Crew(
                        user_id=user.id,
                        boatswain_level=0,
                        cook_level=0,
                        gunner_level=0,
                        navigator_level=0,
                        parrot_level=0,
                        morale=100
                    )
                    session.add(crew)
                
                reset_count += 1
                
            except Exception as e:
                print(f"Ошибка сброса пользователя {user.telegram_id}: {e}")
        
        await session.commit()
    
    text = (
        f"✅ <b>СБРОС ВЫПОЛНЕН</b>\n\n"
        f"┠ Сброшено прогрессов: <code>{reset_count}</code>\n"
        f"┠ Все пользователи возвращены к старту!"
    )
    
    await message.answer(text, reply_markup=admin_keyboards.admin_main_keyboard())


@router.message(F.text == "📨 Рассылка")
async def admin_broadcast_start(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    broadcast_data[message.from_user.id] = {'stage': 'waiting'}
    
    await message.answer(
        "📨 <b>РЕЖИМ РАССЫЛКИ</b>\n\n"
        "┠ Отправь мне сообщение для рассылки (можно с фото)\n"
        "┠ Или нажми 'Отмена'",
        reply_markup=admin_keyboards.admin_broadcast_keyboard()
    )


@router.message(F.text == "❌ Отмена")
async def admin_broadcast_cancel(message: Message):
    if message.from_user.id in broadcast_data:
        del broadcast_data[message.from_user.id]
        await message.answer(
            "❌ Рассылка отменена",
            reply_markup=admin_keyboards.admin_main_keyboard()
        )


@router.message(F.text == "✅ Отправить")
async def admin_broadcast_confirm(message: Message):
    if message.from_user.id not in broadcast_data:
        return
    
    data = broadcast_data[message.from_user.id]
    
    if 'content' not in data:
        await message.answer("❌ Сначала отправь сообщение для рассылки")
        return
    
    await message.answer("📨 Начинаю рассылку...")
    
    async with async_session() as session:
        result = await session.execute(select(User.telegram_id))
        user_ids = [row[0] for row in result.all()]
    
    sent = 0
    failed = 0
    
    for user_id in user_ids:
        try:
            if data['content'].get('photo'):
                await message.bot.send_photo(
                    chat_id=user_id,
                    photo=data['content']['photo'],
                    caption=data['content'].get('caption', '')
                )
            elif data['content'].get('text'):
                await message.bot.send_message(
                    chat_id=user_id,
                    text=data['content']['text']
                )
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            failed += 1
            print(f"Ошибка отправки {user_id}: {e}")
    
    del broadcast_data[message.from_user.id]
    
    await message.answer(
        f"📊 <b>РАССЫЛКА ЗАВЕРШЕНА</b>\n\n"
        f"┠ ✅ Отправлено: <code>{sent}</code>\n"
        f"┠ ❌ Ошибок: <code>{failed}</code>\n"
        f"┠ 👥 Всего: <code>{len(user_ids)}</code>",
        reply_markup=admin_keyboards.admin_main_keyboard()
    )


@router.message(F.text)
async def admin_broadcast_text(message: Message):
    if message.from_user.id not in broadcast_data:
        return
    
    if message.text in ["✅ Отправить", "❌ Отмена", "🔙 Назад", "🔙 Выход", 
                        "📊 Статистика", "📈 Топ", "👥 Пользователи", "📨 Рассылка", 
                        "🎲 Лотерея", "🔄 Ресет прогресса", "⚠️ ПОЛНЫЙ СБРОС",
                        "⚙️ Настройки", "💰 Цена пропуска", "1 ⭐", "2 ⭐", "3 ⭐",
                        "5 ⭐", "10 ⭐", "15 ⭐", "20 ⭐", "1 🌟", "2 🌟", "3 🌟", "5 🌟", "10 🌟", "15 🌟", "20 🌟",
                        "1 ✨", "2 ✨", "3 ✨", "5 ✨", "10 ✨", "15 ✨", "20 ✨"]:
        return
    
    data = broadcast_data[message.from_user.id]
    data['stage'] = 'content_received'
    data['content'] = {'text': message.text}
    
    await message.answer("✅ Текст получен. Нажми 'Отправить' для рассылки")


@router.message(F.photo)
async def admin_broadcast_photo(message: Message):
    if message.from_user.id not in broadcast_data:
        return
    
    data = broadcast_data[message.from_user.id]
    data['stage'] = 'content_received'
    data['content'] = {
        'photo': message.photo[-1].file_id,
        'caption': message.caption or ""
    }
    
    await message.answer("✅ Фото получено. Нажми 'Отправить' для рассылки")