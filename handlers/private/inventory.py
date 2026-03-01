import json
import os
from aiogram import Router, F
from typing import Dict
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from keyboards.inline import (
    inventory_categories_menu, category_items_menu,
    item_detail_menu, back_button
)
from database.db import async_session
from database.models import User, Inventory
from config import config

router = Router()

ITEMS_PATH = os.path.join(config.BASE_DIR, 'data', 'items.json')
with open(ITEMS_PATH, 'r', encoding='utf-8') as f:
    ITEMS_DATA = json.load(f)


def get_item_category(item_id: str) -> str:
    if item_id in ITEMS_DATA['sellable']:
        return 'sellable'
    elif item_id in ITEMS_DATA['usable']:
        return 'usable'
    elif item_id in ITEMS_DATA['special']:
        return 'special'
    raise ValueError(f"Предмет {item_id} не найден ни в одной категории!")


def is_pure_sellable(item_id: str) -> bool:
    in_sellable = item_id in ITEMS_DATA.get('sellable', {})
    in_usable = item_id in ITEMS_DATA.get('usable', {})
    in_special = item_id in ITEMS_DATA.get('special', {})
    return in_sellable and not in_usable and not in_special


@router.callback_query(F.data == "sell_all_items")
async def sell_all_items(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Ошибка загрузки данных", show_alert=True)
            return
        inventory_result = await session.execute(
            select(Inventory).where(Inventory.user_id == user.id)
        )
        items = inventory_result.scalars().all()
        
        ITEMS_PATH = os.path.join(config.BASE_DIR, 'data', 'items.json')
        with open(ITEMS_PATH, 'r', encoding='utf-8') as f:
            items_data = json.load(f)
        
        sellable_items = items_data.get('sellable', {})
        
        total_money = 0
        sold_items = []
        items_to_sell = []
        
        for item in items:
            if get_item_category(item.item_id) == 'sellable':
                item_data = sellable_items[item.item_id]
                price = item_data.get('price', 0)
                
                items_to_sell.append(item)
                total_money += price * item.quantity
                sold_items.append(f"┠ {item_data.get('emoji', '📦')} {item_data.get('name', item.item_id)} x{item.quantity}")
        
        if not items_to_sell:
            await callback.answer("❌ Нет предметов для продажи!", show_alert=True)
            return
        
        for item in items_to_sell:
            await session.delete(item)
        
        user.current_money += total_money
        user.total_money += total_money
        
        await session.commit()
        
        items_list = "\n".join(sold_items)
        text = (
            f"💰 <b>МАССОВАЯ ПРОДАЖА</b>\n\n"
            f"{items_list}\n\n"
            f"┠ <b>Получено:</b> <code>+{total_money}</code> монет\n"
            f"┠ <b>Новый баланс:</b> <code>{user.current_money}</code> монет"
        )
        
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=back_button("inventory_category_sellable"))
        await callback.answer()


@router.callback_query(F.data == "inventory")
async def inventory_main(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Ошибка загрузки данных", show_alert=True)
            return
        
        inventory = await session.execute(
            select(Inventory).where(Inventory.user_id == user.id)
        )
        items = inventory.scalars().all()
        
        sellable_count = 0
        usable_count = 0
        special_count = 0
        
        for item in items:
            category = get_item_category(item.item_id)
            if category == 'sellable':
                sellable_count += item.quantity
            elif category == 'usable':
                usable_count += item.quantity
            elif category == 'special':
                special_count += item.quantity
        
        text = (
            f"🎒 <b>ИНВЕНТАРЬ</b>\n\n"
            f"┠ <b>Баланс:</b> <code>{user.current_money}</code> монет\n\n"
            f"┠ <b>КАТЕГОРИИ:</b>\n"
            f"┠ 💰 На продажу: <code>{sellable_count}</code> шт.\n"
            f"┠ ✨ Используемые: <code>{usable_count}</code> шт.\n"
            f"┠ 🔮 Особые: <code>{special_count}</code> шт.\n\n"
            f"┠ <i>Продавай в магазине, используй с умом!</i>"
        )
    
    await callback.message.delete()
    await callback.message.answer(text, reply_markup=inventory_categories_menu(sellable_count, usable_count, special_count))
    await callback.answer()


@router.callback_query(F.data.startswith("inventory_category_") & ~F.data.contains("_page_"))
async def inventory_category(callback: CallbackQuery):
    category = callback.data.replace("inventory_category_", "")
    await inventory_category_with_page(callback, category, 0)


@router.callback_query(F.data.startswith("inventory_category_") & F.data.contains("_page_"))
async def inventory_category_paginated(callback: CallbackQuery):
    parts = callback.data.split("_page_")
    category_part = parts[0]
    page = int(parts[1])
    
    category = category_part.replace("inventory_category_", "")
    await inventory_category_with_page(callback, category, page)


async def inventory_category_with_page(callback: CallbackQuery, category: str, page: int = 0):
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Ошибка загрузки данных", show_alert=True)
            return
        
        inventory = await session.execute(
            select(Inventory).where(Inventory.user_id == user.id)
        )
        all_items = inventory.scalars().all()
        
        category_items = []
        for inv_item in all_items:
            if get_item_category(inv_item.item_id) == category:
                category_items.append(inv_item)
        
        if not category_items:
            category_names = {
                'sellable': 'продажи',
                'usable': 'использования',
                'special': 'особых'
            }
            text = f"┠ <b>Нет предметов для {category_names.get(category, 'этой категории')}</b>"
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=back_button("inventory"))
            await callback.answer()
            return
        
        items_per_page = 5
        total_pages = (len(category_items) + items_per_page - 1) // items_per_page
        
        if page >= total_pages:
            page = total_pages - 1
        
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        page_items = category_items[start_idx:end_idx]
        
        items_for_menu = []
        for inv_item in page_items:
            category_data = ITEMS_DATA.get(category, {})
            item_data = category_data.get(inv_item.item_id, {})
            items_for_menu.append({
                'item_id': inv_item.item_id,
                'name': item_data.get('name', inv_item.item_id),
                'emoji': item_data.get('emoji', '📦'),
                'quantity': inv_item.quantity,
                'category': category
            })
        
        category_title = {
            'sellable': '💰 НА ПРОДАЖУ',
            'usable': '✨ ИСПОЛЬЗУЕМЫЕ',
            'special': '🔮 ОСОБЫЕ'
        }.get(category, category.upper())
        
        text = (
            f"<b>{category_title}</b>\n"
            f"┠ Страница {page+1}/{total_pages}\n\n"
            f"┠ Выбери предмет:"
        )
    
    await callback.message.delete()
    await callback.message.answer(
        text,
        reply_markup=category_items_menu(items_for_menu, page, total_pages, category)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("item_"))
async def item_detail(callback: CallbackQuery):
    parts = callback.data.split("_")
    category = parts[1]
    item_id = "_".join(parts[2:])
    
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Ошибка загрузки данных", show_alert=True)
            return
        
        result = await session.execute(
            select(Inventory)
            .where(Inventory.user_id == user.id)
            .where(Inventory.item_id == item_id)
        )
        inventory_items = result.scalars().all()
        if not inventory_items:
            await callback.answer("❌ Предмет не найден!", show_alert=True)
            return

        total_quantity = sum(item.quantity for item in inventory_items)
        
        ITEMS_PATH = os.path.join(config.BASE_DIR, 'data', 'items.json')
        with open(ITEMS_PATH, 'r', encoding='utf-8') as f:
            ITEMS_DATA = json.load(f)
        
        category_data = ITEMS_DATA.get(category, {})
        item_data = category_data.get(item_id, {})
        
        text = (
            f"{item_data.get('emoji', '📦')} <b>{item_data.get('name', item_id)}</b>\n\n"
            f"┠ {item_data.get('description', 'Нет описания')}\n\n"
            f"┠ <b>Количество:</b> <code>{total_quantity}</code> шт.\n"
        )
        
        if category == 'sellable':
            text += f"┠ <b>Цена продажи:</b> <code>{item_data.get('price', 0)}</code> монет\n\n"
            text += f"┠ <i>Можно продать в магазине</i>"
        
        elif category == 'usable':
            if item_id == 'death_island_ticket':
                text += (
                    f"\n┠ <b>Билет на Остров смерти</b>\n"
                    f"┠ • Действует 3 рейда\n"
                    f"┠ • Активируется автоматически\n\n"
                    f"┠ <i>Просто выбери Остров смерти!</i>"
                )
            else:
                text += f"┠ <b>Эффект:</b> {item_data.get('effect', 'неизвестный')}\n"
                text += f"┠ <b>Применение:</b> {item_data.get('duration', 'мгновенно')}\n\n"
                text += f"┠ <i>Используй, чтобы получить эффект</i>"
        
        elif category == 'special':
            text += f"┠ <b>Особый эффект:</b> {item_data.get('effect', 'неизвестный')}\n"
            text += f"┠ <b>Длительность:</b> {item_data.get('duration', 'постоянно')}\n\n"
            text += f"┠ <i>Ценный предмет, используй с умом!</i>"
    
    await callback.message.delete()
    await callback.message.answer(
        text,
        reply_markup=item_detail_menu(item_id, category, total_quantity, item_data)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("sell_"))
async def sell_item(callback: CallbackQuery):
    parts = callback.data.split("_")
    category = parts[1]
    item_id = "_".join(parts[2:])
    
    if category != 'sellable':
        await callback.answer("❌ Этот предмет нельзя продать!", show_alert=True)
        return
    
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == callback.from_user.id)
            .options(selectinload(User.ship))
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Ошибка загрузки данных", show_alert=True)
            return
        
        result = await session.execute(
            select(Inventory)
            .where(Inventory.user_id == user.id)
            .where(Inventory.item_id == item_id)
        )
        inventory_items = result.scalars().all()
        
        if not inventory_items:
            await callback.answer("❌ У тебя нет этого предмета!", show_alert=True)
            return
        
        total_quantity = sum(item.quantity for item in inventory_items)
        
        if total_quantity < 1:
            await callback.answer("❌ У тебя нет этого предмета!", show_alert=True)
            return
        
        ITEMS_PATH = os.path.join(config.BASE_DIR, 'data', 'items.json')
        with open(ITEMS_PATH, 'r', encoding='utf-8') as f:
            items_data = json.load(f)
        
        sellable_items = items_data.get('sellable', {})
        
        if item_id not in sellable_items:
            await callback.answer("❌ Этот предмет нельзя продать!", show_alert=True)
            return
        
        item_data = sellable_items[item_id]
        price = item_data.get('price', 0)
        
        if price <= 0:
            await callback.answer("❌ Этот предмет нельзя продать!", show_alert=True)
            return
        
        remaining_to_remove = 1
        for inv_item in inventory_items:
            if remaining_to_remove <= 0:
                break
            
            if inv_item.quantity >= remaining_to_remove:
                inv_item.quantity -= remaining_to_remove
                remaining_to_remove = 0
                if inv_item.quantity == 0:
                    await session.delete(inv_item)
            else:
                remaining_to_remove -= inv_item.quantity
                await session.delete(inv_item)

        user.current_money += price
        user.total_money += price
        
        await session.commit()
        
        text = (
            f"💰 <b>ПРОДАЖА</b>\n\n"
            f"┠ Продано: {item_data.get('emoji', '')} {item_data.get('name', item_id)}\n"
            f"┠ Получено: <code>+{price}</code> монет\n\n"
            f"┠ <b>Новый баланс:</b> <code>{user.current_money}</code> монет"
        )
    
    await callback.message.delete()
    await callback.message.answer(text, reply_markup=back_button(f"inventory_category_{category}"))
    await callback.answer()


@router.callback_query(F.data.startswith("use_"))
async def use_item(callback: CallbackQuery):
    parts = callback.data.split("_")
    category = parts[1]
    item_id = "_".join(parts[2:])
    
    if category not in ['usable', 'special']:
        await callback.answer("❌ Этот предмет нельзя использовать!", show_alert=True)
        return
    
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == callback.from_user.id)
            .options(
                selectinload(User.ship),
                selectinload(User.crew),
                selectinload(User.active_effects)
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Ошибка загрузки данных", show_alert=True)
            return
        
        result = await session.execute(
            select(Inventory)
            .where(Inventory.user_id == user.id)
            .where(Inventory.item_id == item_id)
        )
        inv_item = result.scalar_one_or_none()
        
        if not inv_item or inv_item.quantity < 1:
            await callback.answer("❌ У тебя нет этого предмета!", show_alert=True)
            return
        
        ITEMS_PATH = os.path.join(config.BASE_DIR, 'data', 'items.json')
        with open(ITEMS_PATH, 'r', encoding='utf-8') as f:
            items_data = json.load(f)
        
        category_data = items_data.get(category, {})
        item_data = category_data.get(item_id, {})
        
        success, message = await apply_item_effect(user, item_data, session)
        
        if success:
            if inv_item.quantity > 1:
                inv_item.quantity -= 1
            else:
                await session.delete(inv_item)
            
            await session.commit()
            text = f"✅ <b>ПРЕДМЕТ ИСПОЛЬЗОВАН</b>\n\n┠ {message}"
        else:
            text = f"❌ <b>ОШИБКА</b>\n\n┠ {message}"
    
    await callback.message.delete()
    await callback.message.answer(text, reply_markup=back_button(f"inventory_category_{category}"))
    await callback.answer()


async def apply_item_effect(user: User, item_data: Dict, session) -> tuple:
    effect = item_data.get('effect')
    
    if effect == 'repair_ship':
        if user.ship.health >= user.ship.max_health:
            return False, "Корабль уже в идеальном состоянии!"
        heal = int(user.ship.max_health * (item_data.get('effect_value', 50) / 100))
        user.ship.health = min(user.ship.health + heal, user.ship.max_health)
        return True, f"Корабль отремонтирован! Прочность: {user.ship.health}/{user.ship.max_health}"
    
    elif effect == 'morale_boost':
        user.crew.morale = min(100, user.crew.morale + item_data.get('effect_value', 20))
        return True, f"Мораль команды повышена до {user.crew.morale}!"
    
    elif effect == 'reset_cooldown' and item_data.get('id') == 'rum':
        from datetime import datetime, timedelta
        user.last_voyage_time = datetime.utcnow() - timedelta(hours=1)
        return True, "Перезарядка корабля сброшена!"
    
    elif effect in ['guaranteed_chest', 'luck_boost', 'choose_event']:
        from database.requests import add_active_effect
        duration = item_data.get('duration', 'next_voyage')
        
        remaining_uses = 1
        if duration == 'voyages_3':
            remaining_uses = 3
        elif duration == 'permanent':
            remaining_uses = 999
        
        await add_active_effect(
            user_id=user.id,
            effect_type=effect,
            source_item=item_data.get('id', 'unknown'),
            remaining_uses=remaining_uses
        )
        
        effect_names = {
            'guaranteed_chest': 'Сундук гарантирован',
            'luck_boost': 'Удача повышена',
            'choose_event': 'Выбор события'
        }
        return True, f"{effect_names.get(effect, 'Эффект')} активирован на {remaining_uses} рейд(а)!"
    
    elif effect == 'unlock_location':
        from database.requests import add_active_effect
        await add_active_effect(
            user_id=user.id,
            effect_type='death_island_access',
            source_item=item_data.get('id', 'unknown'),
            remaining_uses=3
        )
        return True, "Остров смерти теперь доступен на 3 рейда!"
    
    return False, "Неизвестный эффект"


@router.callback_query(F.data == "inventory_category_sellable_empty")
@router.callback_query(F.data == "inventory_category_usable_empty")
@router.callback_query(F.data == "inventory_category_special_empty")
async def empty_category(callback: CallbackQuery):
    category_map = {
        "inventory_category_sellable_empty": "продажи",
        "inventory_category_usable_empty": "использования",
        "inventory_category_special_empty": "особых"
    }
    category_name = category_map.get(callback.data, "этой категории")
    await callback.answer(f"📦 В категории '{category_name}' нет предметов", show_alert=True)