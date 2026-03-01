from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, PreCheckoutQuery, LabeledPrice
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta

from database.db import async_session
from database.models import User, Inventory
from game_logic.loot_tables import generate_loot, format_loot_message
from game_logic.events import get_random_event, process_event_choice
from game_logic.cooldown import get_remaining_cooldown, format_cooldown
from config import config
import json
import os

router = Router()

LOCATIONS_PATH = os.path.join(config.BASE_DIR, 'data', 'locations.json')
with open(LOCATIONS_PATH, 'r', encoding='utf-8') as f:
    LOCATIONS_DATA = json.load(f)


async def get_user(message: Message):
    from database.requests import get_or_create_user
    return await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )


async def check_allowed_group(message: Message) -> bool:
    if message.chat.id in config.ALLOWED_GROUPS:
        return True
    await message.reply("❌ Этот бот не работает в данной группе. Покидаю чат.")
    await message.bot.leave_chat(message.chat.id)
    return False


@router.message(F.chat.type.in_({"group", "supergroup"}), Command("voyage"))
async def group_voyage(message: Message):
    if not await check_allowed_group(message):
        return
    
    user = await get_user(message)
    
    from handlers.admin.admin_panel import get_cooldown_price
    price = get_cooldown_price()
    
    remaining = get_remaining_cooldown(user)
    if remaining > 0:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=f"⭐ Пропустить ожидание за {price} звезд",
                callback_data=f"skip_cooldown_group"
            )
        )
        
        await message.reply(
            f"⏳ {message.from_user.first_name}, корабль ещё не готов!\n"
            f"Осталось: {format_cooldown(remaining)}\n\n"
            f"Хочешь пропустить ожидание?",
            reply_markup=builder.as_markup()
        )
        return
    
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == message.from_user.id)
            .options(
                selectinload(User.ship),
                selectinload(User.crew),
                selectinload(User.inventory),
                selectinload(User.active_effects)
            )
        )
        user = result.scalar_one_or_none()
    
    if not user:
        await message.reply("❌ Ошибка загрузки данных")
        return
    
    location_id = user.last_voyage_location
    location_data = LOCATIONS_DATA.get(location_id)
    
    if not location_data:
        location_id = 'navirettnye_ostrova'
        location_data = LOCATIONS_DATA[location_id]
    
    if user.level < location_data.get('min_level', 1):
        await message.reply(
            f"❌ Твой уровень {user.level}, а для {location_data['name']} нужен {location_data['min_level']}\n"
            f"Сходи в личные сообщения и выбери другую локацию."
        )
        return
    
    if location_id == 'ostrov_smerti':
        has_access = any(
            effect.effect_type == 'death_island_access' and effect.remaining_uses > 0
            for effect in user.active_effects
        )
        has_ticket = any(item.item_id == 'death_island_ticket' for item in user.inventory)
        
        if not has_access and not has_ticket:
            await message.reply("❌ Нужен билет на Остров смерти!")
            return
        
        if has_ticket and not has_access:
            async with async_session() as session:
                session.add(user)
                ticket = next(item for item in user.inventory if item.item_id == 'death_island_ticket')
                if ticket.quantity > 1:
                    ticket.quantity -= 1
                else:
                    await session.delete(ticket)
                
                from database.requests import add_active_effect
                await add_active_effect(
                    user_id=user.id,
                    effect_type='death_island_access',
                    source_item='death_island_ticket',
                    remaining_uses=3
                )
                await session.commit()
            
            await message.reply("🎫 Билет активирован! Отправляемся на Остров смерти...")
    
    active_effects = []
    for effect in user.active_effects:
        if effect.remaining_uses > 0:
            active_effects.append({
                'type': effect.effect_type,
                'source': effect.source_item
            })
    
    storm_reduction = user.crew.parrot_level * 0.1
    event = get_random_event(
        user_level=user.level,
        location_multiplier=location_data.get('event_chance', 0.1),
        storm_reduction=storm_reduction
    )
    
    if event:
        result_text, modifiers = process_event_choice(event['id'], 'default', {
            'ship': user.ship,
            'crew': user.crew,
            'level': user.level
        })
        
        await message.reply(f"🌊 {event['name']}\n\n{result_text}")
        
        async with async_session() as session:
            session.add(user)
            
            if modifiers.get('damage', 0) > 0:
                user.ship.health = max(0, user.ship.health - modifiers['damage'])
            
            if modifiers.get('money', 0) != 0:
                user.current_money += modifiers['money']
                if modifiers['money'] > 0:
                    user.total_money += modifiers['money']
            
            await session.commit()
        
        await complete_group_voyage(message, user, location_id, active_effects, 
                                   event_text=result_text,
                                   loot_multiplier=modifiers.get('loot_multiplier', 1.0))
    else:
        await complete_group_voyage(message, user, location_id, active_effects)


@router.callback_query(F.data == "skip_cooldown_group")
async def skip_cooldown_group(callback: CallbackQuery):
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
    
    await callback.message.answer_invoice(
        title="Пропуск перезарядки",
        description="Мгновенно отправляет корабль в плавание без ожидания",
        payload="group_skip_cooldown",
        provider_token="",
        currency="XTR",
        prices=prices,
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()


@router.callback_query(F.data == "cancel_skip")
async def cancel_skip(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


@router.pre_checkout_query(F.invoice_payload == "group_skip_cooldown")
async def group_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment, F.successful_payment.invoice_payload == "group_skip_cooldown")
async def group_successful_payment(message: Message):
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == message.from_user.id)
            .options(
                selectinload(User.ship),
                selectinload(User.crew),
                selectinload(User.active_effects),
                selectinload(User.inventory)
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer("❌ Ошибка загрузки данных")
            return
        
        user.last_voyage_time = datetime.utcnow() - timedelta(hours=1)
        await session.commit()
        
        await message.answer(f"✅ Перезарядка пропущена! Отправляемся в плавание...")
        
        fake_message = type('FakeMessage', (), {
            'from_user': message.from_user,
            'chat': message.chat,
            'reply': lambda text: None,
            'answer': lambda text: None
        })()
        
        await group_voyage(fake_message)


async def complete_group_voyage(message: Message, user, location_id: str, active_effects: list, 
                                event_text=None, loot_multiplier=1.0):
    location_data = LOCATIONS_DATA.get(location_id)
    
    loot_quantity_bonus = user.ship.sails_level
    loot_value_bonus = user.ship.hold_level * 5
    rare_chance_bonus = user.ship.copper_sheathing_level * 3
    
    luck_multiplier = 1.3 if any(e.get('type') == 'luck_boost' for e in active_effects) else 1.0
    
    loot = generate_loot(
        user_level=user.level,
        location_multiplier=location_data.get('loot_multiplier', 1.0) * loot_multiplier,
        luck_multiplier=luck_multiplier,
        guaranteed_chest=any(e.get('type') == 'guaranteed_chest' for e in active_effects),
        loot_quantity_bonus=loot_quantity_bonus,
        loot_value_bonus=loot_value_bonus,
        rare_chance_bonus=rare_chance_bonus
    )
    
    exp_gained = 10 + len(loot) * 2
    
    async with async_session() as session:
        session.add(user)
        
        user.voyages_completed += 1
        user.exp += exp_gained
        user.last_voyage_time = datetime.utcnow()
        
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
        
        await session.commit()
    
    loot_text = format_loot_message(loot)
    
    bonus_text = ""
    if loot_quantity_bonus > 0:
        bonus_text += f"\n⚓ Паруса: +{loot_quantity_bonus} предмет"
    if loot_value_bonus > 0:
        bonus_text += f"\n📦 Трюм: +{loot_value_bonus}% ценности"
    if rare_chance_bonus > 0:
        bonus_text += f"\n⚓ Обшивка: +{rare_chance_bonus}% к шансу редких"
    
    if event_text:
        full_text = (
            f"{event_text}\n\n"
            f"🏴‍☠️ {message.from_user.first_name} вернулся из плавания!\n\n"
            f"📍 {location_data['name']}\n"
            f"{loot_text}\n"
            f"{bonus_text}\n\n"
            f"✨ Опыт: +{exp_gained}"
        )
    else:
        full_text = (
            f"🏴‍☠️ {message.from_user.first_name} вернулся из плавания!\n\n"
            f"📍 {location_data['name']}\n"
            f"{loot_text}\n"
            f"{bonus_text}\n\n"
            f"✨ Опыт: +{exp_gained}"
        )
    
    await message.reply(full_text)