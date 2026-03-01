import json
import os
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, PreCheckoutQuery, LabeledPrice, Message
from handlers.admin.admin_panel import get_item_price
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from keyboards.inline import shop_menu, back_button, upgrades_menu, upgrade_details
from database.db import async_session
from database.models import User, Inventory
from config import config

router = Router()

UPGRADES_PATH = os.path.join(config.BASE_DIR, 'data', 'upgrades.json')
with open(UPGRADES_PATH, 'r', encoding='utf-8') as f:
    UPGRADES_DATA = json.load(f)

ITEMS_PATH = os.path.join(config.BASE_DIR, 'data', 'items.json')
with open(ITEMS_PATH, 'r', encoding='utf-8') as f:
    ITEMS_DATA = json.load(f)

SPECIAL_ITEMS = ITEMS_DATA.get('special', {})
USABLE_ITEMS = ITEMS_DATA.get('usable', {})

STAR_ITEMS = {}

for item_id, item_data in SPECIAL_ITEMS.items():
    if 'price_stars' in item_data:
        STAR_ITEMS[item_id] = {**item_data, 'category': 'special'}

for item_id, item_data in USABLE_ITEMS.items():
    if 'price_stars' in item_data:
        STAR_ITEMS[item_id] = {**item_data, 'category': 'usable'}


@router.callback_query(F.data == "shop_main")
async def shop_main(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Ошибка загрузки данных", show_alert=True)
            return
        
        text = (
            f"🏪 <b>ПИРАТСКАЯ ЛАВКА</b>\n\n"
            f"┠ <b>Твои монеты:</b> <code>{user.current_money}</code> ⚜️\n\n"
            f"┠ <i>Выбери, что хочешь улучшить:</i>"
        )
    
    await callback.message.delete()
    await callback.message.answer(text, reply_markup=shop_menu())
    await callback.answer()


@router.callback_query(F.data == "shop_ship")
async def shop_ship(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == callback.from_user.id)
            .options(selectinload(User.ship))
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.ship:
            await callback.answer("❌ Ошибка загрузки данных", show_alert=True)
            return
        
        current_levels = {
            'sails': user.ship.sails_level,
            'hull': user.ship.hull_level,
            'cannons': user.ship.cannons_level,
            'hold': user.ship.hold_level,
            'copper_sheathing': user.ship.copper_sheathing_level,
            'steam_engine': user.ship.steam_engine_level
        }
        
        upgrades_list = []
        for upgrade_id, upgrade_data in UPGRADES_DATA['ship'].items():
            upgrades_list.append({
                'id': upgrade_id,
                'name': upgrade_data['name'],
                'max_level': upgrade_data['max_level']
            })
    
    text = (
        f"⚓ <b>УЛУЧШЕНИЯ КОРАБЛЯ</b>\n\n"
        f"┠ <i>Выбери, что хочешь прокачать:</i>"
    )
    
    await callback.message.delete()
    await callback.message.answer(
        text, 
        reply_markup=upgrades_menu(upgrades_list, 'ship', current_levels)
    )
    await callback.answer()


@router.callback_query(F.data == "shop_crew")
async def shop_crew(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == callback.from_user.id)
            .options(selectinload(User.crew))
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.crew:
            await callback.answer("❌ Ошибка загрузки данных", show_alert=True)
            return
        
        current_levels = {
            'boatswain': user.crew.boatswain_level,
            'cook': user.crew.cook_level,
            'gunner': user.crew.gunner_level,
            'navigator': user.crew.navigator_level,
            'parrot': user.crew.parrot_level
        }
        
        upgrades_list = []
        for upgrade_id, upgrade_data in UPGRADES_DATA['crew'].items():
            upgrades_list.append({
                'id': upgrade_id,
                'name': upgrade_data['name'],
                'max_level': upgrade_data['max_level']
            })
    
    text = (
        f"👥 <b>УЛУЧШЕНИЯ КОМАНДЫ</b>\n\n"
        f"┠ <i>Выбери, кого хочешь нанять или прокачать:</i>"
    )
    
    await callback.message.delete()
    await callback.message.answer(
        text, 
        reply_markup=upgrades_menu(upgrades_list, 'crew', current_levels)
    )
    await callback.answer()


@router.callback_query(F.data == "shop_items")
async def shop_items(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Ошибка загрузки данных", show_alert=True)
            return
    
    builder = InlineKeyboardBuilder()
    
    for item_id, item_data in STAR_ITEMS.items():
        stars = get_item_price(item_id)
        emoji = item_data.get('emoji', '📦')
        name = item_data.get('name', item_id)
        
        category_mark = ""
        if item_data.get('category') == 'usable':
            category_mark = "⚡ "
        elif item_data.get('category') == 'special':
            category_mark = "🔮 "
        
        builder.row(
            InlineKeyboardButton(
                text=f"{category_mark}{emoji} {name} — {stars} ⭐",
                callback_data=f"buy_stars_{item_id}"
            ),
            width=1
        )
    
    builder.row(
        InlineKeyboardButton(text="◄ НАЗАД", callback_data="shop_main"),
        width=1
    )
    
    text = (
        f"⭐ <b>ОСОБЫЕ ПРЕДМЕТЫ</b>\n\n"
        f"┠ Покупай уникальные предметы за звезды Telegram!\n"
        f"┠ ⚡ — используемые предметы (активируются в инвентаре)\n"
        f"┠ 🔮 — особые предметы (пассивные эффекты)\n\n"
        f"┠ <i>После покупки предмет появится в твоем инвентаре.</i>"
    )
    
    await callback.message.delete()
    await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("upgrade_ship_"))
async def upgrade_ship_detail(callback: CallbackQuery):
    upgrade_id = callback.data.replace("upgrade_ship_", "")
    
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == callback.from_user.id)
            .options(selectinload(User.ship))
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.ship:
            await callback.answer("❌ Ошибка загрузки данных", show_alert=True)
            return
        
        current_level = getattr(user.ship, f"{upgrade_id}_level", 0)
        
        upgrade_data = UPGRADES_DATA['ship'][upgrade_id]
        max_level = upgrade_data['max_level']
        
        if current_level < max_level:
            next_level = current_level + 1
            price = int(upgrade_data['base_price'] * (upgrade_data['price_multiplier'] ** (current_level)))
            
            effect_value = upgrade_data['effect_per_level'] * next_level
            text = (
                f"⚓ <b>{upgrade_data['name']}</b>\n\n"
                f"┠ {upgrade_data['description']}\n\n"
                f"┠ <b>Текущий уровень:</b> <code>{current_level}/{max_level}</code>\n"
                f"┠ <b>Следующий уровень:</b> <code>{next_level}</code>\n"
                f"┠ <b>Бонус после улучшения:</b> <code>+{effect_value}{upgrade_data['effect_unit']}</code>\n"
                f"┠ <b>Цена:</b> <code>{price}</code> ⚜️\n\n"
                f"┠ <i>Купить улучшение?</i>"
            )
            
            can_afford = user.current_money >= price
        else:
            text = (
                f"⚓ <b>{upgrade_data['name']}</b>\n\n"
                f"┠ {upgrade_data['description']}\n\n"
                f"┠ ✅ <b>Достигнут максимальный уровень ({max_level})!</b>\n"
                f"┠ Текущий бонус: <code>+{upgrade_data['effect_per_level'] * max_level}{upgrade_data['effect_unit']}</code>"
            )
            can_afford = False
            price = 0
    
    await callback.message.delete()
    await callback.message.answer(
        text,
        reply_markup=upgrade_details(
            upgrade_id, 'ship', current_level, max_level, price, can_afford
        )
    )
    await callback.answer()


@router.callback_query(F.data.startswith("upgrade_crew_"))
async def upgrade_crew_detail(callback: CallbackQuery):
    upgrade_id = callback.data.replace("upgrade_crew_", "")
    
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == callback.from_user.id)
            .options(selectinload(User.crew))
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.crew:
            await callback.answer("❌ Ошибка загрузки данных", show_alert=True)
            return
        
        current_level = getattr(user.crew, f"{upgrade_id}_level", 0)
        
        upgrade_data = UPGRADES_DATA['crew'][upgrade_id]
        max_level = upgrade_data['max_level']
        
        if current_level < max_level:
            next_level = current_level + 1
            price = int(upgrade_data['base_price'] * (upgrade_data['price_multiplier'] ** (current_level)))
            
            effect_value = upgrade_data['effect_per_level'] * next_level
            text = (
                f"👤 <b>{upgrade_data['name']}</b>\n\n"
                f"┠ {upgrade_data['description']}\n\n"
                f"┠ <b>Текущий уровень:</b> <code>{current_level}/{max_level}</code>\n"
                f"┠ <b>Следующий уровень:</b> <code>{next_level}</code>\n"
                f"┠ <b>Эффект:</b> <code>+{effect_value}{upgrade_data['effect_unit']}</code>\n"
                f"┠ <b>Цена:</b> <code>{price}</code> ⚜️\n\n"
                f"┠ <i>Нанять/улучшить?</i>"
            )
            
            can_afford = user.current_money >= price
        else:
            text = (
                f"👤 <b>{upgrade_data['name']}</b>\n\n"
                f"┠ {upgrade_data['description']}\n\n"
                f"┠ ✅ <b>Достигнут максимальный уровень ({max_level})!</b>"
            )
            can_afford = False
            price = 0
    
    await callback.message.delete()
    await callback.message.answer(
        text,
        reply_markup=upgrade_details(
            upgrade_id, 'crew', current_level, max_level, price, can_afford
        )
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_stars_"))
async def buy_stars_item(callback: CallbackQuery):
    item_id = callback.data.replace("buy_stars_", "")
    
    item_data = STAR_ITEMS.get(item_id)
    
    if not item_data:
        await callback.answer("❌ Предмет не найден!", show_alert=True)
        return
    
    stars = get_item_price(item_id)
    category = item_data.get('category', 'special')
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"💳 Оплатить {stars} ⭐",
            pay=True
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="◄ ОТМЕНА",
            callback_data="shop_items"
        )
    )
    
    prices = [LabeledPrice(label=item_data['name'], amount=stars)]
    
    await callback.message.answer_invoice(
        title=item_data['name'],
        description=item_data['description'],
        payload=f"buy_item_{category}_{item_id}",
        provider_token="",
        currency="XTR",
        prices=prices,
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment, F.successful_payment.invoice_payload.startswith("buy_item_"))
async def successful_payment_handler(message: Message):
    payload = message.successful_payment.invoice_payload
    
    parts = payload.replace("buy_item_", "").split("_")
    category = parts[0]
    item_id = "_".join(parts[1:])
    
    item_data = None
    if category == 'special':
        item_data = SPECIAL_ITEMS.get(item_id)
    elif category == 'usable':
        item_data = USABLE_ITEMS.get(item_id)
    
    if item_data:
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                result = await session.execute(
                    select(Inventory)
                    .where(Inventory.user_id == user.id)
                    .where(Inventory.item_id == item_id)
                )
                inv = result.scalar_one_or_none()
                
                if inv:
                    inv.quantity += 1
                else:
                    new_item = Inventory(
                        user_id=user.id,
                        item_id=item_id,
                        quantity=1
                    )
                    session.add(new_item)
                
                await session.commit()
                
                extra_info = ""
                if item_id == 'death_island_ticket':
                    extra_info = "\n\n┠ 🎫 Билет нужно активировать при плавании!\n┠ Он даст доступ на 3 рейда."
                
                await message.answer(
                    f"✅ <b>ПОКУПКА УСПЕШНА!</b>\n\n"
                    f"┠ Ты получил: {item_data['emoji']} {item_data['name']}\n"
                    f"┠ Предмет добавлен в инвентарь!{extra_info}",
                    reply_markup=back_button("shop_items")
                )
                return
    
    await message.answer("❌ Ошибка при покупке")


@router.callback_query(F.data.startswith("buy_ship_"))
async def buy_ship_upgrade(callback: CallbackQuery):
    upgrade_id = callback.data.replace("buy_ship_", "")
    
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == callback.from_user.id)
            .options(selectinload(User.ship))
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.ship:
            await callback.answer("❌ Ошибка загрузки данных", show_alert=True)
            return
        
        current_level = getattr(user.ship, f"{upgrade_id}_level", 0)
        
        upgrade_data = UPGRADES_DATA['ship'][upgrade_id]
        max_level = upgrade_data['max_level']
        
        if current_level >= max_level:
            await callback.answer("❌ Уже максимальный уровень!", show_alert=True)
            return
        
        price = int(upgrade_data['base_price'] * (upgrade_data['price_multiplier'] ** (current_level)))
        
        if user.current_money < price:
            await callback.answer("❌ Недостаточно монет!", show_alert=True)
            return
        
        user.current_money -= price
        
        new_level = current_level + 1
        setattr(user.ship, f"{upgrade_id}_level", new_level)
        
        await session.commit()
        
        text = (
            f"✅ <b>УЛУЧШЕНИЕ КУПЛЕНО!</b>\n\n"
            f"┠ {upgrade_data['name']} теперь <b>{new_level}</b> уровня!\n"
            f"┠ Осталось монет: <code>{user.current_money}</code> ⚜️"
        )
    
    await callback.message.delete()
    await callback.message.answer(text, reply_markup=back_button("shop_ship"))
    await callback.answer()


@router.callback_query(F.data.startswith("buy_crew_"))
async def buy_crew_upgrade(callback: CallbackQuery):
    upgrade_id = callback.data.replace("buy_crew_", "")
    
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == callback.from_user.id)
            .options(selectinload(User.crew))
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.crew:
            await callback.answer("❌ Ошибка загрузки данных", show_alert=True)
            return
        
        current_level = getattr(user.crew, f"{upgrade_id}_level", 0)
        
        upgrade_data = UPGRADES_DATA['crew'][upgrade_id]
        max_level = upgrade_data['max_level']
        
        if current_level >= max_level:
            await callback.answer("❌ Уже максимальный уровень!", show_alert=True)
            return
        
        price = int(upgrade_data['base_price'] * (upgrade_data['price_multiplier'] ** (current_level)))
        
        if user.current_money < price:
            await callback.answer("❌ Недостаточно монет!", show_alert=True)
            return
        
        user.current_money -= price
        
        new_level = current_level + 1
        setattr(user.crew, f"{upgrade_id}_level", new_level)
        
        await session.commit()
        
        text = (
            f"✅ <b>УЛУЧШЕНИЕ КУПЛЕНО!</b>\n\n"
            f"┠ {upgrade_data['name']} теперь <b>{new_level}</b> уровня!\n"
            f"┠ Осталось монет: <code>{user.current_money}</code> ⚜️"
        )
    
    await callback.message.delete()
    await callback.message.answer(text, reply_markup=back_button("shop_crew"))
    await callback.answer()


@router.callback_query(F.data == "no_money")
async def no_money(callback: CallbackQuery):
    await callback.answer("💰 Не хватает монет! Соверши рейд, чтобы заработать.", show_alert=True)