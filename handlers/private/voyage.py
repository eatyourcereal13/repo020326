import json
import os
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, PreCheckoutQuery, LabeledPrice, Message, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from database.requests import add_active_effect

from keyboards.inline import main_menu, back_button, event_choice_menu
from game_logic.loot_tables import generate_loot, calculate_loot_value, format_loot_message
from game_logic.events import get_random_event, process_event_choice
from game_logic.combat import calculate_combat_outcome, get_combat_description
from database.db import async_session
from database.models import User, Voyage, Inventory
from config import config
from datetime import datetime, timedelta

router = Router()

LOCATIONS_PATH = os.path.join(config.BASE_DIR, 'data', 'locations.json')
with open(LOCATIONS_PATH, 'r', encoding='utf-8') as f:
    LOCATIONS_DATA = json.load(f)


@router.callback_query(F.data == "voyage_start")
async def voyage_start(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == callback.from_user.id)
            .options(
                selectinload(User.ship), 
                selectinload(User.crew),
                selectinload(User.inventory),
                selectinload(User.active_effects)
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Ошибка загрузки данных", show_alert=True)
            return
    
    builder = InlineKeyboardBuilder()
    
    ticket_count = sum(1 for item in user.inventory if item.item_id == 'death_island_ticket')
    
    has_island_access = any(
        effect.effect_type == 'death_island_access' and effect.remaining_uses > 0
        for effect in user.active_effects
    )
    
    for loc_id, loc_data in LOCATIONS_DATA.items():
        available = True
        lock_reason = ""
        
        if user.level < loc_data.get('min_level', 1):
            available = False
            lock_reason = f"🔒 {loc_data['min_level']} ур."
        
        if loc_id == 'ostrov_smerti':
            if has_island_access:
                available = True
                lock_reason = ""
            elif ticket_count > 0:
                available = True
                lock_reason = "⚡"
            else:
                available = False
                lock_reason = "🔒 Нужен билет"
        if available:
            if lock_reason == "⚡":
                button_text = f"{lock_reason} {loc_data['name']}"
            else:
                button_text = f"{loc_data['name']}"
            callback_data = f"voyage_to_{loc_id}"
        else:
            button_text = f"{lock_reason} {loc_data['name']}"
            callback_data = f"voyage_locked_{loc_id}"
        
        builder.row(
            InlineKeyboardButton(
                text=button_text,
                callback_data=callback_data
            ),
            width=1
        )
    
    builder.row(
        InlineKeyboardButton(text="◄ НАЗАД", callback_data="main_menu"),
        width=1
    )
    
    effect_info = ""
    if has_island_access:
        remaining = next(
            (effect.remaining_uses for effect in user.active_effects 
             if effect.effect_type == 'death_island_access'), 0
        )
        effect_info = f"\n┠ ⚡ <b>Остров смерти:</b> доступен еще {remaining} рейд(ов)"
    
    text = (
        f"🏝️ <b>ВЫБОР ЛОКАЦИИ</b>\n\n"
        f"┠ <b>Твой уровень:</b> <code>{user.level}</code>\n"
        f"┠ <b>Билетов в инвентаре:</b> <code>{ticket_count}</code>{effect_info}\n\n"
        f"┠ <i>🟢 Доступно\n"
        f"┠ ⚡ Есть билет (активируй при входе)\n"
        f"┠ 🔒 Требуется уровень/билет</i>"
    )
    
    await callback.message.delete()
    
    image_path = os.path.join(config.BASE_DIR, 'static', 'voyage.png')
    
    try:
        photo = FSInputFile(image_path)
        await callback.message.answer_photo(
            photo=photo,
            caption=text,
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        print(f"Ошибка загрузки фото плавания: {e}")
        await callback.message.answer(
            text,
            reply_markup=builder.as_markup()
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("voyage_locked_"))
async def voyage_locked(callback: CallbackQuery):
    location_id = callback.data.replace("voyage_locked_", "")
    location_data = LOCATIONS_DATA.get(location_id, {})
    
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == callback.from_user.id)
            .options(selectinload(User.inventory))
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Ошибка загрузки данных", show_alert=True)
            return
        
        ticket_count = sum(1 for item in user.inventory if item.item_id == 'death_island_ticket')
        
        if user.level < location_data.get('min_level', 1):
            text = (
                f"🔒 <b>ЛОКАЦИЯ ЗАБЛОКИРОВАНА</b>\n\n"
                f"┠ Для посещения <b>{location_data.get('name', 'этой локации')}</b>\n"
                f"┠ нужен <code>{location_data['min_level']}</code> уровень.\n"
                f"┠ Твой уровень: <code>{user.level}</code>\n\n"
                f"┠ До {location_data['min_level']} уровня осталось:\n"
                f"┠ <code>{get_exp_needed(user.level, location_data['min_level'])}</code> опыта"
            )
        
        elif location_data.get('requires_item'):
            text = (
                f"🔒 <b>ЛОКАЦИЯ ЗАБЛОКИРОВАНА</b>\n\n"
                f"┠ Для посещения <b>{location_data.get('name', 'этой локации')}</b>\n"
                f"┠ нужен специальный билет.\n"
                f"┠ У тебя: <code>{ticket_count}</code> шт.\n\n"
                f"┠ 🎫 Билет можно найти в рейдах или купить в магазине!"
            )
        
        else:
            text = "🔒 <b>ЛОКАЦИЯ НЕДОСТУПНА</b>"
    
    await callback.answer(text, show_alert=True)


def get_exp_needed(current_level: int, target_level: int) -> int:
    from handlers.private.start import LEVELS
    current_exp = LEVELS.get(current_level, 0)
    target_exp = LEVELS.get(target_level, 0)
    return target_exp - current_exp


@router.callback_query(F.data.startswith("voyage_to_"))
async def voyage_to_location(callback: CallbackQuery):
    location_id = callback.data.replace("voyage_to_", "")
    location_data = LOCATIONS_DATA.get(location_id, LOCATIONS_DATA['navirettnye_ostrova'])
    
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == callback.from_user.id)
            .options(
                selectinload(User.ship),
                selectinload(User.crew),
                selectinload(User.active_effects),
                selectinload(User.voyage),
                selectinload(User.inventory)
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Ошибка загрузки данных", show_alert=True)
            return

        if user.level < location_data.get('min_level', 1):
            await callback.answer(
                f"❌ Нужен {location_data['min_level']} уровень!",
                show_alert=True
            )
            return
        
        from game_logic.cooldown import get_remaining_cooldown, format_cooldown
        
        remaining = get_remaining_cooldown(user)
        if remaining > 0:
            from handlers.admin.admin_panel import get_cooldown_price
            price = get_cooldown_price()
            
            builder = InlineKeyboardBuilder()
            
            builder.row(
                InlineKeyboardButton(
                    text=f"⭐ Пропустить за {price} звезд",
                    callback_data=f"skip_cooldown_{location_id}"
                ),
                width=1
            )
            
            builder.row(
                InlineKeyboardButton(
                    text="◄ Назад к выбору локаций",
                    callback_data="voyage_start"
                ),
                width=1
            )
            
            await callback.message.delete()
            await callback.message.answer(
                f"⏳ <b>ПЕРЕЗАРЯДКА</b>\n\n"
                f"┠ Корабль ещё не готов к плаванию!\n"
                f"┠ Осталось: <code>{format_cooldown(remaining)}</code>\n\n"
                f"┠ Пропустить ожидание за {price} ⭐ ?",
                reply_markup=builder.as_markup()
            )
            return
        
        if location_id == 'ostrov_smerti':
            has_access = any(
                effect.effect_type == 'death_island_access' and effect.remaining_uses > 0
                for effect in user.active_effects
            )
            
            has_ticket = any(
                item.item_id == 'death_island_ticket' 
                for item in user.inventory
            )
            
            if has_access:
                pass
            elif has_ticket:
                builder = InlineKeyboardBuilder()
                builder.row(
                    InlineKeyboardButton(text="✅ Активировать билет", callback_data="activate_ticket_now"),
                    InlineKeyboardButton(text="❌ Отмена", callback_data="voyage_start"),
                    width=2
                )
                
                await callback.message.delete()
                await callback.message.answer(
                    f"🎫 <b>БИЛЕТ НА ОСТРОВ СМЕРТИ</b>\n\n"
                    f"┠ У тебя есть билет!\n"
                    f"┠ Активировать сейчас?\n"
                    f"┠ (даст доступ на 3 рейда)",
                    reply_markup=builder.as_markup()
                )
                return
            else:
                await callback.answer(
                    "❌ Нужен билет на Остров смерти!\nКупи в магазине за 10 ⭐ и активируй!",
                    show_alert=True
                )
                return
        
        active_effects = []
        for effect in user.active_effects:
            if effect.remaining_uses > 0:
                active_effects.append({
                    'type': effect.effect_type,
                    'source': effect.source_item
                })
        
        if not user.voyage:
            voyage = Voyage(
                user_id=user.id,
                location=location_id
            )
            session.add(voyage)
            await session.flush()
            user.voyage = voyage
        
        storm_reduction = user.crew.parrot_level * 0.1
        event = get_random_event(
            user_level=user.level,
            location_multiplier=location_data.get('event_chance', 0.1),
            storm_reduction=storm_reduction
        )
        
        if event:
            user.voyage.current_event = json.dumps(event, ensure_ascii=False)
            user.voyage.event_resolved = False
            await session.commit()
            
            text = (
                f"🌊 <b>{event['name']}</b>\n\n"
                f"┠ {event['description']}\n\n"
                f"┠ <b>Что будешь делать?</b>"
            )
            
            await callback.message.delete()
            await callback.message.answer(
                text,
                reply_markup=event_choice_menu(event['id'], event['options'])
            )
        else:
            await complete_voyage(
                user.id, 
                location_id, 
                active_effects, 
                callback,
                use_ticket=False
            )
            return
    
    await callback.answer()


@router.callback_query(F.data == "activate_ticket_now")
async def activate_ticket_now(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == callback.from_user.id)
            .options(
                selectinload(User.inventory),
                selectinload(User.active_effects)
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Ошибка загрузки данных", show_alert=True)
            return
        
        ticket = None
        for item in user.inventory:
            if item.item_id == 'death_island_ticket':
                ticket = item
                break
        
        if not ticket:
            await callback.answer("❌ Билет не найден!", show_alert=True)
            return
        
        if ticket.quantity > 1:
            ticket.quantity -= 1
        else:
            await session.delete(ticket)
        
        await add_active_effect(
            user_id=user.id,
            effect_type='death_island_access',
            source_item='death_island_ticket',
            remaining_uses=3
        )
        
        await session.commit()
        
        result = await session.execute(
            select(User)
            .where(User.id == user.id)
            .options(
                selectinload(User.ship), 
                selectinload(User.crew),
                selectinload(User.inventory),
                selectinload(User.active_effects)
            )
        )
        user = result.scalar_one()
    
    builder = InlineKeyboardBuilder()
    
    user_item_ids = [item.item_id for item in user.inventory]
    ticket_count = user_item_ids.count('death_island_ticket')
    
    has_island_access = any(
        effect.effect_type == 'death_island_access' and effect.remaining_uses > 0
        for effect in user.active_effects
    )
    
    for loc_id, loc_data in LOCATIONS_DATA.items():
        available = True
        lock_reason = ""
        
        if user.level < loc_data.get('min_level', 1):
            available = False
            lock_reason = f"🔒 {loc_data['min_level']} ур."
        
        if loc_id == 'ostrov_smerti':
            if has_island_access:
                available = True
                lock_reason = ""
            elif ticket_count > 0:
                available = True
                lock_reason = "⚡"
            else:
                available = False
                lock_reason = "🔒 Нужен билет"
        
        if available:
            if lock_reason == "⚡":
                button_text = f"{lock_reason} {loc_data['name']}"
            else:
                button_text = f"{loc_data['name']}"
            callback_data = f"voyage_to_{loc_id}"
        else:
            button_text = f"{lock_reason} {loc_data['name']}"
            callback_data = f"voyage_locked_{loc_id}"
        
        builder.row(
            InlineKeyboardButton(text=button_text, callback_data=callback_data),
            width=1
        )
    
    builder.row(
        InlineKeyboardButton(text="◄ НАЗАД", callback_data="main_menu"),
        width=1
    )
    
    effect_info = ""
    if has_island_access:
        remaining = next(
            (effect.remaining_uses for effect in user.active_effects 
             if effect.effect_type == 'death_island_access'), 0
        )
        effect_info = f"\n┠ ⚡ <b>Остров смерти:</b> доступен еще {remaining} рейд(ов)"
    
    text = (
        f"🏝️ <b>ВЫБОР ЛОКАЦИИ</b>\n\n"
        f"┠ <b>Твой уровень:</b> <code>{user.level}</code>\n"
        f"┠ <b>Билетов в инвентаре:</b> <code>{ticket_count}</code>{effect_info}\n\n"
        f"┠ <i>🟢 Доступно\n"
        f"┠ ⚡ Есть билет (активируй при входе)\n"
        f"┠ 🔒 Требуется уровень/билет</i>"
    )
    
    await callback.message.delete()
    await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("event_"))
async def handle_event_choice(callback: CallbackQuery):
    parts = callback.data.split("_")
    event_id = parts[1]
    choice_callback = "_".join(parts[2:])
    
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == callback.from_user.id)
            .options(
                selectinload(User.ship),
                selectinload(User.crew),
                selectinload(User.active_effects),
                selectinload(User.voyage)
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Ошибка загрузки данных", show_alert=True)
            return
            
        if not user.voyage or not user.voyage.current_event:
            await callback.answer("❌ Событие не найдено", show_alert=True)
            return
        
        event = json.loads(user.voyage.current_event)
        
        result_text, modifiers = process_event_choice(event_id, choice_callback, {
            'ship': user.ship,
            'crew': user.crew,
            'level': user.level
        })
        
        active_effects = []
        for effect in user.active_effects:
            if effect.remaining_uses > 0:
                active_effects.append({
                    'type': effect.effect_type,
                    'source': effect.source_item
                })
        
        if modifiers.get('effect') == 'combat_merchant':
            victory, combat_mods = calculate_combat_outcome(
                attacker_level=user.level,
                defender_type='merchant',
                ship_stats={
                    'cannons_level': user.ship.cannons_level
                },
                crew_stats={
                    'gunner_level': user.crew.gunner_level
                }
            )
            
            combat_text = get_combat_description('merchant', victory)
            result_text += f"\n\n┠ {combat_text}"
            
            if victory:
                modifiers['loot_multiplier'] = modifiers.get('loot_multiplier', 1.0) * 2.0
                user.traders_attacked += 1
            else:
                modifiers['loot_multiplier'] = modifiers.get('loot_multiplier', 1.0) * 0.5
            
            modifiers['damage'] = combat_mods.get('damage', 0)
            user.exp += combat_mods.get('experience', 0)
            
        elif modifiers.get('effect') == 'combat_kraken':
            victory, combat_mods = calculate_combat_outcome(
                attacker_level=user.level,
                defender_type='kraken',
                ship_stats={
                    'cannons_level': user.ship.cannons_level,
                    'copper_sheathing_level': user.ship.copper_sheathing_level
                },
                crew_stats={
                    'gunner_level': user.crew.gunner_level
                }
            )
            
            combat_text = get_combat_description('kraken', victory)
            result_text += f"\n\n┠ {combat_text}"
            
            if victory:
                modifiers['loot_multiplier'] = modifiers.get('loot_multiplier', 1.0) * 3.0
                modifiers['guaranteed_loot'] = 'legendary'
                user.kraken_defeated += 1
            else:
                modifiers['loot_multiplier'] = modifiers.get('loot_multiplier', 1.0) * 0.3
            
            modifiers['damage'] = combat_mods.get('damage', 30)
            user.exp += combat_mods.get('experience', 10)
        
        if modifiers.get('damage', 0) > 0:
            user.ship.health = max(0, user.ship.health - modifiers['damage'])
            if user.ship.health <= 0:
                user.ship.health = 20
        
        if modifiers.get('money', 0) != 0:
            user.current_money += modifiers['money']
            if modifiers['money'] > 0:
                user.total_money += modifiers['money']
        
        await complete_voyage(
            user.id, 
            user.voyage.location, 
            active_effects, 
            callback, 
            event_text=result_text,
            loot_multiplier=modifiers.get('loot_multiplier', 1.0),
            guaranteed_chest=(modifiers.get('guaranteed_loot') == 'legendary'),
            use_ticket=modifiers.get('use_ticket', False) or (user.voyage.location == 'ostrov_smerti')
        )


async def complete_voyage(user_id: int, location_id: str, active_effects: list, callback=None, 
                          event_text=None, loot_multiplier=1.0, guaranteed_chest=False, use_ticket=False):
    
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.ship),
                selectinload(User.crew),
                selectinload(User.inventory),
                selectinload(User.active_effects),
                selectinload(User.voyage)
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            if callback:
                await callback.answer("❌ Ошибка загрузки данных", show_alert=True)
            return
        
        user.last_voyage_time = datetime.utcnow()
        
        location_data = LOCATIONS_DATA.get(location_id, LOCATIONS_DATA['navirettnye_ostrova'])
        
        loot_quantity_bonus = user.ship.sails_level
        loot_value_bonus = user.ship.hold_level * 5
        rare_chance_bonus = user.ship.copper_sheathing_level * 3
        

        luck_multiplier = 1.3 if any(e.get('type') == 'luck_boost' for e in active_effects) else 1.0
        is_death_island = (location_id == 'ostrov_smerti')
        

        loot = generate_loot(
            user_level=user.level,
            location_multiplier=location_data.get('loot_multiplier', 1.0) * loot_multiplier,
            luck_multiplier=luck_multiplier,
            guaranteed_chest=guaranteed_chest or any(e.get('type') == 'guaranteed_chest' for e in active_effects),
            loot_quantity_bonus=loot_quantity_bonus,
            loot_value_bonus=loot_value_bonus,
            rare_chance_bonus=rare_chance_bonus,
            is_death_island=is_death_island
        )
        
        total_value = calculate_loot_value(loot)
        exp_gained = 10 + len(loot) * 2
        

        user.voyages_completed += 1
        user.exp += exp_gained
        user.last_voyage_location = location_id
        

        from handlers.private.start import LEVELS
        old_level = user.level
        new_level = 1
        for lvl, required_exp in sorted(LEVELS.items()):
            if user.exp >= required_exp:
                new_level = lvl
        
        if new_level > old_level:
            user.level = new_level
            print(f"🆙 Повышение уровня! {old_level} -> {new_level}")
        
        for item in loot:
            item_id = item.get('id')
            if not item_id:
                continue
            
            inv_item = None
            for inv in user.inventory:
                if inv.item_id == item_id:
                    inv_item = inv
                    break
            
            if inv_item:
                inv_item.quantity += 1
            else:
                new_item = Inventory(
                    user_id=user.id,
                    item_id=item_id,
                    quantity=1
                )
                session.add(new_item)
        
        for effect in user.active_effects:
            if effect.remaining_uses > 0:
                effect.remaining_uses -= 1
        
        if user.voyage:
            user.voyage.current_event = None
            user.voyage.loot_json = json.dumps(loot, ensure_ascii=False)
            user.voyage.money_gained = 0
            user.voyage.experience_gained = exp_gained
            user.voyage.location = location_id
        
        await session.commit()
        
        loot_text = format_loot_message(loot)
        
        bonus_text = ""
        if loot_quantity_bonus > 0:
            bonus_text += f"\n┠ ⚓ Паруса: +{loot_quantity_bonus} предмет"
        if loot_value_bonus > 0:
            bonus_text += f"\n┠ 📦 Трюм: +{loot_value_bonus}% ценности"
        if rare_chance_bonus > 0:
            bonus_text += f"\n┠ 🧲 Обшивка: +{rare_chance_bonus}% к шансу редких"
        
        island_access = None
        for effect in user.active_effects:
            if effect.effect_type == 'death_island_access' and effect.remaining_uses > 0:
                island_access = effect.remaining_uses
                break
        
        ticket_info = ""
        if location_id == 'ostrov_smerti' and island_access:
            ticket_info = f"\n┠ 🎫 Осталось рейдов на Остров: {island_access}"
        elif location_id == 'ostrov_smerti' and not island_access:
            ticket_info = "\n┠ 🎫 Доступ к Острову закончился, нужен новый билет!"
        
        level_up_text = ""
        if new_level > old_level:
            level_up_text = f"\n\n┠ ⭐ <b>ПОВЫШЕНИЕ УРОВНЯ! {old_level} → {new_level}</b> ⭐"
        
        if event_text:
            full_text = (
                f"{event_text}\n\n"
                f"{loot_text}\n"
                f"{bonus_text}\n\n"
                f"┠ ✨ <b>Опыт:</b> +{exp_gained}{ticket_info}"
                f"{level_up_text}\n\n"
                f"┠ <i>Продай предметы в инвентаре!</i>"
            )
        else:
            full_text = (
                f"🏴‍☠️ <b>ПЛАВАНИЕ ЗАВЕРШЕНО</b>\n\n"
                f"┠ 📍 {location_data['name']}\n"
                f"{loot_text}\n"
                f"{bonus_text}\n\n"
                f"┠ ✨ <b>Опыт:</b> +{exp_gained}{ticket_info}"
                f"{level_up_text}\n\n"
                f"┠ <i>Продай предметы в инвентаре!</i>"
            )
        
        if callback:
            await callback.message.delete()
            await callback.message.answer(full_text, reply_markup=main_menu())
            await callback.answer()


@router.callback_query(F.data == "ratings")
async def ratings_menu(callback: CallbackQuery):
    async with async_session() as session:
        top_money = await session.execute(
            select(User)
            .order_by(User.total_money.desc())
            .limit(10)
        )
        top_money_users = top_money.scalars().all()
        
        top_voyages = await session.execute(
            select(User)
            .order_by(User.voyages_completed.desc())
            .limit(10)
        )
        top_voyages_users = top_voyages.scalars().all()
        
        top_legendary = await session.execute(
            select(User)
            .order_by(User.legendary_finds.desc())
            .limit(10)
        )
        top_legendary_users = top_legendary.scalars().all()
    
    text = "🏆 <b>РЕЙТИНГИ КАПИТАНОВ</b>\n\n"
    
    text += "💰 <b>САМЫЕ БОГАТЫЕ:</b>\n"
    if top_money_users:
        for i, user in enumerate(top_money_users, 1):
            name = user.first_name or f"ID{user.telegram_id}"
            if len(name) > 15:
                name = name[:12] + "..."
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"┠ {medal} {name} — <code>{user.total_money}</code> ⚜️\n"
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
    
    text += "\n"
    
    text += "👑 <b>ЛЕГЕНДАРНЫЕ КАПИТАНЫ:</b>\n"
    if top_legendary_users:
        for i, user in enumerate(top_legendary_users, 1):
            name = user.first_name or f"ID{user.telegram_id}"
            if len(name) > 15:
                name = name[:12] + "..."
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"┠ {medal} {name} — <code>{user.legendary_finds}</code> 🏆\n"
    else:
        text += "┠ <i>Пока нет данных</i>\n"
    
    text += f"\n┠ <i>Топ-10 в каждой категории</i>"
    
    await callback.message.delete()
    await callback.message.answer(
        text,
        reply_markup=back_button("main_menu")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("use_rum_"))
async def use_rum_for_cooldown(callback: CallbackQuery):
    location_id = callback.data.replace("use_rum_", "")
    
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == callback.from_user.id)
            .options(
                selectinload(User.inventory),
                selectinload(User.ship),
                selectinload(User.crew),
                selectinload(User.active_effects),
                selectinload(User.voyage)
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Ошибка загрузки данных", show_alert=True)
            return
        
        rum_item = None
        for item in user.inventory:
            if item.item_id == 'rum':
                rum_item = item
                break
        
        if not rum_item:
            await callback.answer("❌ Ром не найден!", show_alert=True)
            return
        
        if rum_item.quantity > 1:
            rum_item.quantity -= 1
        else:
            await session.delete(rum_item)
        
        from datetime import timedelta
        user.last_voyage_time = datetime.utcnow() - timedelta(hours=1)
        
        await session.commit()
        
        fake_callback = type('FakeCallback', (), {
            'message': callback.message,
            'from_user': callback.from_user,
            'data': f"voyage_to_{location_id}",
            'answer': lambda *args, **kwargs: None
        })()
        
        await voyage_to_location(fake_callback)


@router.callback_query(F.data.startswith("skip_cooldown_"))
async def skip_cooldown(callback: CallbackQuery):
    location_id = callback.data.replace("skip_cooldown_", "")
    
    from handlers.admin.admin_panel import get_cooldown_price
    price = get_cooldown_price()
    
    prices = [LabeledPrice(label="Пропуск перезарядки", amount=price)]
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"⭐ Оплатить {price} звезд",
            pay=True
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="◄ Отмена",
            callback_data="voyage_start"
        )
    )
    
    await callback.message.answer_invoice(
        title="Пропуск перезарядки",
        description="Мгновенно отправляет корабль в плавание без ожидания",
        payload=f"voyage_skip_cooldown_{location_id}",
        provider_token="",
        currency="XTR",
        prices=prices,
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()


@router.pre_checkout_query(F.invoice_payload.startswith("voyage_skip_cooldown_"))
async def voyage_pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment, F.successful_payment.invoice_payload.startswith("voyage_skip_cooldown_"))
async def voyage_successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    location_id = payload.replace("voyage_skip_cooldown_", "")
    
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == message.from_user.id)
            .options(
                selectinload(User.ship),
                selectinload(User.crew),
                selectinload(User.active_effects),
                selectinload(User.voyage)
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer("❌ Ошибка загрузки данных")
            return
        
        user.last_voyage_time = datetime.utcnow() - timedelta(hours=1)
        await session.commit()
        
        await message.answer(
            f"✅ <b>ПЕРЕЗАРЯДКА ПРОПУЩЕНА</b>\n\n┠ Отправляемся в плавание...",
            reply_markup=back_button("main_menu")
        )
        
        fake_callback = type('FakeCallback', (), {
            'message': message,
            'from_user': message.from_user,
            'data': f"voyage_to_{location_id}",
            'answer': lambda *args, **kwargs: None
        })()
        
        await voyage_to_location(fake_callback)