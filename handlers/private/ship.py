from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import os

from keyboards.inline import back_button
from database.db import async_session
from database.models import User
from config import config

router = Router()


@router.callback_query(F.data == "ship_info")
async def ship_info(callback: CallbackQuery):
    await callback.answer()
    
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == callback.from_user.id)
            .options(selectinload(User.ship), selectinload(User.crew))
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.ship:
            await callback.message.answer("❌ Ошибка загрузки данных")
            return
        
        from game_logic.cooldown import calculate_cooldown, get_remaining_cooldown, format_cooldown
        
        ship = user.ship
        crew = user.crew
        
        base_cooldown = 15 * 60
        current_cooldown = calculate_cooldown(user)
        cooldown_reduction = base_cooldown - current_cooldown
        
        remaining = get_remaining_cooldown(user)
        cooldown_status = f"┠ ✅ <b>ГОТОВ К ПЛАВАНИЮ!</b>"
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
        
        text = (
            f"⚓ <b>КОРАБЛЬ И КОМАНДА</b>\n\n"
            f"┠ <b>ПРОЧНОСТЬ:</b> {ship.health}/{ship.max_health}\n"
            f"┠ <code>{health_bar}</code> {int((ship.health/ship.max_health)*100)}%\n\n"
            
            f"┠ <b>КОРАБЛЬ:</b>\n"
            f"┠ ⚙️ Паруса: <b>{ship.sails_level}</b> ур. ┠ +{loot_quantity_bonus} предмет, -{ship.sails_level*30} сек\n"
            f"┠ 🛡️ Корпус: <b>{ship.hull_level}</b> ур. ┠ -{damage_reduction}% урона, -{ship.hull_level*20} сек\n"
            f"┠ 🔫 Пушки: <b>{ship.cannons_level}</b> ур. ┠ +{combat_power_bonus}% силы\n"
            f"┠ 📦 Трюм: <b>{ship.hold_level}</b> ур. ┠ +{loot_value_bonus}% ценности\n"
            f"┠ 🧲 Обшивка: <b>{ship.copper_sheathing_level}</b> ур. ┠ +{rare_chance_bonus}% к редким, -{ship.copper_sheathing_level*15} сек\n"
            f"┠ 🔥 Двигатель: <b>{ship.steam_engine_level}/5</b> ур. ┠ -{ship.steam_engine_level*60} сек\n\n"
            
            f"┠ <b>КОМАНДА:</b>\n"
            f"┠ 👨‍✈️ Боцман: <b>{crew.boatswain_level}/1</b> ┠ -{event_damage_reduction}% урона от событий, -10% кд\n"
            f"┠ 👨‍🍳 Кок: <b>{crew.cook_level}/5</b> ┠ +{consumables_bonus}% ценности провизии\n"
            f"┠ 🔫 Канонир: <b>{crew.gunner_level}/5</b> ┠ +{combat_damage_bonus}% урона в бою\n"
            f"┠ 🧭 Штурман: <b>{crew.navigator_level}/5</b> ┠ +{rare_event_bonus}% к редким событиям\n"
            f"┠ 🦜 Попугай: <b>{crew.parrot_level}/3</b> ┠ +{casino_luck_bonus}% к дублям в казино\n\n"
            
            
            f"{cooldown_status}\n"
            f"┠ ⏱️ <b>Базовая перезарядка:</b> {format_cooldown(current_cooldown)}"
        )
    
    await callback.message.delete()
    
    image_path = os.path.join(config.BASE_DIR, 'static', 'ship.png')
    
    try:
        photo = FSInputFile(image_path)
        await callback.message.answer_photo(
            photo=photo,
            caption=text,
            reply_markup=back_button("main_menu")
        )
    except Exception as e:
        print(f"Ошибка загрузки фото: {e}")
        await callback.message.answer(text, reply_markup=back_button("main_menu"))