from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from sqlalchemy import select
import os

from keyboards.inline import main_menu, back_button
from database.db import async_session
from database.models import User
from database.requests import get_or_create_user
from config import config

router = Router()

LEVELS = {
    1: 0,
    2: 100,
    3: 250,
    4: 450,
    5: 700,
    6: 1000,
    7: 1350,
    8: 1750,
    9: 2200,
    10: 2700,
    11: 3250,
    12: 3850,
    13: 4500,
    14: 5200,
    15: 5950,
    16: 6750,
    17: 7600,
    18: 8500,
    19: 9450,
    20: 10450,
}

def get_level_info(exp: int) -> tuple:
    level = 1
    for lvl, required_exp in sorted(LEVELS.items()):
        if exp >= required_exp:
            level = lvl
        else:
            break
    
    current_level_exp = LEVELS.get(level, 0)
    next_level_exp = LEVELS.get(level + 1, LEVELS[level] + 999999)
    exp_needed = next_level_exp - exp
    total_needed = next_level_exp - current_level_exp
    progress = ((exp - current_level_exp) / total_needed) * 100 if total_needed > 0 else 100
    
    level_names = {
        1: "САЛАГА",
        2: "САЛАГА",
        3: "МАТРОС", 
        4: "МАТРОС",
        5: "МАТРОС",
        6: "МАТРОС", 
        7: "МАТРОС",
        8: "МАТРОС",
        9: "КАПИТАН",
        10: "КАПИТАН",
        11: "КАПИТАН",
        12: "КАПИТАН",
        13: "КАПИТАН", 
        14: "КАПИТАН",
        15: "КАПИТАН",
        16: "КАПИТАН",
        17: "КАПИТАН",
        18: "КАПИТАН",
        19: "КАПИТАН",
        20: "ЛЕГЕНДА"
    }
    
    rank_emojis = {
        "САЛАГА": "🐣",
        "МАТРОС": "⚓",
        "КАПИТАН": "🏴‍☠️",
        "ЛЕГЕНДА": "👑",
    }
    
    level_title = level_names.get(level, f"УРОВЕНЬ {level}")
    rank_emoji = rank_emojis.get(level_title.split()[0] if " " in level_title else level_title, "🎯")
    
    return level, exp_needed, progress, level_title, rank_emoji


def create_progress_bar(progress: float, length: int = 10) -> str:
    filled = int((progress / 100) * length)
    empty = length - filled
    bar = "🟩" * filled + "⬛" * empty
    return bar


@router.message(F.chat.type == "private", Command("start"))
async def cmd_start(message: Message):
    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
    level, exp_needed, progress, level_title, rank_emoji = get_level_info(user.exp)
    progress_bar = create_progress_bar(progress)
    
    text = (
        f"🏴‍☠️ <b>ДОБРО ПОЖАЛОВАТЬ, КАПИТАН!</b>\n\n"
        f"Ты — капитан пиратского судна.\n"
        f"Отправляйся в плавание, ищи сокровища,\n"
        f"Улучшай корабль и стань легендой морей!\n\n"
        f"{rank_emoji} <b>РАНГ:</b> {level_title}\n"
        f"{progress_bar} <code>{progress:.1f}%</code>\n\n"
        f"┠ До следующего ранга: <code>{exp_needed}</code> опыта\n\n"
        f"┠ <b>МОНЕТ:</b> <code>{user.current_money}</code> ⚜️"
    )
    image_path = os.path.join(config.BASE_DIR, 'static', 'main.png')
    
    try:
        photo = FSInputFile(image_path)
        await message.answer_photo(
            photo=photo,
            caption=text,
            reply_markup=main_menu()
        )
    except Exception as e:
        print(f"Ошибка загрузки фото: {e}")
        await message.answer(text, reply_markup=main_menu())


@router.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Ошибка загрузки данных", show_alert=True)
            return
        
        level, exp_needed, progress, level_title, rank_emoji = get_level_info(user.exp)
        progress_bar = create_progress_bar(progress)
        
        text = (
            f"🏴‍☠️ <b>ГЛАВНОЕ МЕНЮ</b>\n\n"
            f"{rank_emoji} <b>РАНГ:</b> {level_title}\n"
            f"{progress_bar} <code>{progress:.1f}%</code>\n"
            f"┠ До следующего ранга: <code>{exp_needed}</code> опыта\n\n"
            f"┠ <b>МОНЕТ:</b> <code>{user.current_money}</code> ⚜️"
        )
    
    await callback.message.delete()

    image_path = os.path.join(config.BASE_DIR, 'static', 'main.png')
    
    try:
        photo = FSInputFile(image_path)
        await callback.message.answer_photo(
            photo=photo,
            caption=text,
            reply_markup=main_menu()
        )
    except Exception as e:
        print(f"Ошибка загрузки фото: {e}")
        await callback.message.answer(text, reply_markup=main_menu())
    
    await callback.answer()


@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Ошибка загрузки данных", show_alert=True)
            return
        
        level, exp_needed, progress, level_title, rank_emoji = get_level_info(user.exp)
        progress_bar = create_progress_bar(progress)
        
        text = (
            f"👤 <b>ПРОФИЛЬ КАПИТАНА</b>\n\n"
            f"<b>ИМЯ:</b> {callback.from_user.first_name}\n\n"
            f"{rank_emoji} <b>РАНГ:</b> {level_title}\n"
            f"{progress_bar} <code>{progress:.1f}%</code>\n"
            f"До {level+1} ур.: <code>{exp_needed}</code> опыта\n\n"
            f"<b>ФИНАНСЫ:</b>\n"
            f"┠   💰 Текущие: <code>{user.current_money}</code>\n"
            f"┠   📈 Всего: <code>{user.total_money}</code>\n\n"
            f"<b>СТАТИСТИКА:</b>\n"
            f"┠   ⚓ Рейдов: <code>{user.voyages_completed}</code>\n"
            f"┠   👑 Легендарных: <code>{user.legendary_finds}</code>\n\n"
            f"┠ <i>Продолжай бороздить моря, капитан!</i>"
        )
    
    await callback.message.delete()
    
    image_path = os.path.join(config.BASE_DIR, 'static', 'profile.png')
    
    try:
        photo = FSInputFile(image_path)
        await callback.message.answer_photo(
            photo=photo,
            caption=text,
            reply_markup=back_button("main_menu")
        )
    except Exception as e:
        print(f"Ошибка загрузки фото профиля: {e}")
        await callback.message.answer(text, reply_markup=back_button("main_menu"))
    
    await callback.answer()