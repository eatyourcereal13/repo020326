from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, PreCheckoutQuery, LabeledPrice
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from datetime import datetime
import random
import asyncio

from database.db import async_session
from database.models import User, Lottery, LotteryParticipant
from config import config
from keyboards.admin import admin_keyboards
from database.requests import add_item_to_inventory

router = Router()

PRIZES = {
    "death_island_ticket": {
        "name": "🎫 Билет на Остров смерти",
        "emoji": "🎫",
        "description": "Открывает доступ к Острову смерти на 3 рейда"
    },
    "treasure_map": {
        "name": "🗺️ Карта сокровищ",
        "emoji": "🗺️",
        "description": "Гарантирует сундук в следующем рейде"
    },
    "luck_amulet": {
        "name": "🍀 Амулет удачи",
        "emoji": "🍀",
        "description": "Повышает редкость добычи на 3 рейда"
    }
}

lottery_creation = {}


def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


@router.message(F.text == "🎲 Лотерея")
async def admin_lottery_menu(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    async with async_session() as session:
        active_lottery = await session.execute(
            select(Lottery).where(Lottery.is_active == True)
        )
        active_lottery = active_lottery.scalar_one_or_none()
    
    if active_lottery:
        await message.answer(
            "🎲 Управление лотереей\n\n"
            "Активная лотерея существует. Выбери действие:",
            reply_markup=admin_keyboards.admin_active_lottery_keyboard()
        )
    else:
        await message.answer(
            "🎲 Создание лотереи\n\n"
            "Выбери приз:",
            reply_markup=admin_keyboards.admin_lottery_keyboard()
        )


@router.message(F.text.in_(["🎫 Билет на Остров смерти", "🗺️ Карта сокровищ", "🍀 Амулет удачи"]))
async def admin_lottery_select_prize(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    prize_map = {
        "🎫 Билет на Остров смерти": "death_island_ticket",
        "🗺️ Карта сокровищ": "treasure_map",
        "🍀 Амулет удачи": "luck_amulet"
    }
    
    prize_id = prize_map.get(message.text)
    if not prize_id:
        return
    
    lottery_creation[message.from_user.id] = {
        'prize_id': prize_id,
        'stage': 'quantity'
    }
    
    await message.answer(
        f"Выбран приз: {PRIZES[prize_id]['name']}\n\n"
        f"Сколько штук разыгрываем?",
        reply_markup=admin_keyboards.admin_lottery_quantity_keyboard()
    )


@router.message(F.text.in_(["1", "2", "3", "5", "10"]))
async def admin_lottery_select_quantity(message: Message):
    if message.from_user.id not in lottery_creation:
        return
    
    quantity = int(message.text)
    lottery_creation[message.from_user.id]['quantity'] = quantity
    lottery_creation[message.from_user.id]['stage'] = 'price'
    
    await message.answer(
        f"Количество: {quantity} шт.\n\n"
        f"Цена участия (в звездах):",
        reply_markup=admin_keyboards.admin_lottery_price_keyboard()
    )


@router.message(F.text.in_(["1 ⭐", "2 ⭐", "3 ⭐", "5 ⭐", "10 ⭐"]))
async def admin_lottery_select_price(message: Message):
    if message.from_user.id not in lottery_creation:
        return
    
    price = int(message.text.split()[0])
    data = lottery_creation[message.from_user.id]
    
    async with async_session() as session:
        lottery = Lottery(
            prize_item_id=data['prize_id'],
            prize_quantity=data['quantity'],
            entry_price=price,
            is_active=True
        )
        session.add(lottery)
        await session.commit()
        
        lottery_id = lottery.id
    
    del lottery_creation[message.from_user.id]
    
    await send_lottery_notification(message.bot, lottery_id, data['prize_id'], data['quantity'], price)
    
    await message.answer(
        f"✅ Лотерея создана!\n\n"
        f"Приз: {PRIZES[data['prize_id']]['name']} x{data['quantity']}\n"
        f"Цена участия: {price} ⭐\n\n"
        f"Все пользователи оповещены.",
        reply_markup=admin_keyboards.admin_main_keyboard()
    )


async def send_lottery_notification(bot, lottery_id: int, prize_id: str, quantity: int, price: int):
    async with async_session() as session:
        result = await session.execute(select(User.telegram_id))
        user_ids = [row[0] for row in result.all()]
    
    prize = PRIZES[prize_id]
    
    text = (
        f"🎲 <b>ЛОТЕРЕЯ!</b>\n\n"
        f"┠ Приз: {prize['emoji']} {prize['name']} x{quantity}\n"
        f"┠ {prize['description']}\n\n"
        f"┠ 💰 Цена участия: {price} ⭐\n\n"
        f"👇 Нажми кнопку ниже, чтобы участвовать!"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"⭐ Участвовать за {price} звезд",
            callback_data=f"lottery_join_{lottery_id}"
        )
    )
    
    sent = 0
    for user_id in user_ids:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=builder.as_markup()
            )
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            print(f"Ошибка отправки {user_id}: {e}")
    
    print(f"Лотерея разослана {sent} пользователям")


@router.callback_query(F.data.startswith("lottery_join_"))
async def lottery_join(callback: CallbackQuery):
    lottery_id = int(callback.data.replace("lottery_join_", ""))
    
    async with async_session() as session:
        lottery = await session.get(Lottery, lottery_id)
        if not lottery or not lottery.is_active:
            await callback.answer("❌ Эта лотерея уже закончилась", show_alert=True)
            return
        
        user = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = user.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        participant = await session.execute(
            select(LotteryParticipant)
            .where(LotteryParticipant.lottery_id == lottery_id)
            .where(LotteryParticipant.user_id == user.id)
        )
        if participant.scalar_one_or_none():
            await callback.answer("❌ Ты уже участвуешь в этой лотерее", show_alert=True)
            return
    
    prices = [LabeledPrice(label="Участие в лотерее", amount=lottery.entry_price)]
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"⭐ Оплатить {lottery.entry_price} звезд",
            pay=True
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="◀ Отмена",
            callback_data="lottery_cancel"
        )
    )
    
    await callback.message.answer_invoice(
        title="Участие в лотерее",
        description=f"Приз: {PRIZES[lottery.prize_item_id]['name']} x{lottery.prize_quantity}",
        payload=f"lottery_payment_{lottery_id}",
        provider_token="",
        currency="XTR",
        prices=prices,
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()


@router.callback_query(F.data == "lottery_cancel")
async def lottery_cancel(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


@router.pre_checkout_query(F.invoice_payload.startswith("lottery_payment_"))
async def lottery_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment, F.successful_payment.invoice_payload.startswith("lottery_payment_"))
async def lottery_successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    lottery_id = int(payload.replace("lottery_payment_", ""))
    
    async with async_session() as session:
        user_result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            await message.answer("❌ Ошибка: пользователь не найден")
            return
        
        lottery = await session.get(Lottery, lottery_id)
        if not lottery or not lottery.is_active:
            await message.answer("❌ Эта лотерея уже закончилась")
            return
        
        existing = await session.execute(
            select(LotteryParticipant)
            .where(LotteryParticipant.lottery_id == lottery_id)
            .where(LotteryParticipant.user_id == user.id)
        )
        if existing.scalar_one_or_none():
            await message.answer("❌ Ты уже участвуешь в этой лотерее")
            return
        
        participant = LotteryParticipant(
            lottery_id=lottery_id,
            user_id=user.id,
            payment_id=message.successful_payment.telegram_payment_charge_id
        )
        session.add(participant)
        await session.commit()
        
        participants_count = await session.scalar(
            select(func.count(LotteryParticipant.id))
            .where(LotteryParticipant.lottery_id == lottery_id)
        )
    
    prize_info = PRIZES[lottery.prize_item_id]
    await message.answer(
        f"✅ <b>ТЫ УЧАСТВУЕШЬ В ЛОТЕРЕЕ!</b>\n\n"
        f"┠ {prize_info['emoji']} Приз: {prize_info['name']} x{lottery.prize_quantity}\n"
        f"┠ 👥 Участников: {participants_count}\n"
        f"┠ ⭐ Потрачено: {lottery.entry_price}\n\n"
        f"┠ <i>Результаты будут объявлены после завершения. Удачи! 🍀</i>"
    )


@router.message(F.text == "📊 Статус лотереи")
async def admin_lottery_status(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    async with async_session() as session:
        lottery = await session.execute(
            select(Lottery).where(Lottery.is_active == True)
        )
        lottery = lottery.scalar_one_or_none()
        
        if not lottery:
            await message.answer("❌ Нет активной лотереи")
            return
        
        participants_count = await session.scalar(
            select(func.count(LotteryParticipant.id))
            .where(LotteryParticipant.lottery_id == lottery.id)
        )
        
        total_stars = participants_count * lottery.entry_price
        
        participants = await session.execute(
            select(LotteryParticipant)
            .where(LotteryParticipant.lottery_id == lottery.id)
            .options(selectinload(LotteryParticipant.user))
            .limit(10)
        )
        participants = participants.scalars().all()
    
    text = (
        f"📊 <b>СТАТУС ЛОТЕРЕИ</b>\n\n"
        f"┠ Приз: {PRIZES[lottery.prize_item_id]['emoji']} {PRIZES[lottery.prize_item_id]['name']} x{lottery.prize_quantity}\n"
        f"┠ Цена участия: {lottery.entry_price} ⭐\n\n"
        f"┠ 👥 Участников: <code>{participants_count}</code>\n"
        f"┠ ⭐ Собрано звезд: <code>{total_stars}</code>\n\n"
    )
    
    if participants:
        text += "┠ <b>ПОСЛЕДНИЕ УЧАСТНИКИ:</b>\n"
        for p in participants:
            name = p.user.first_name or f"ID{p.user.telegram_id}" if p.user else "Неизвестный"
            text += f"┠ • {name}\n"
    
    await message.answer(text, reply_markup=admin_keyboards.admin_active_lottery_keyboard())


@router.message(F.text == "✅ Завершить лотерею")
async def admin_lottery_end(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    async with async_session() as session:
        lottery = await session.execute(
            select(Lottery).where(Lottery.is_active == True)
        )
        lottery = lottery.scalar_one_or_none()
        
        if not lottery:
            await message.answer("❌ Нет активной лотереи")
            return
        
        participants = await session.execute(
            select(LotteryParticipant)
            .where(LotteryParticipant.lottery_id == lottery.id)
            .options(selectinload(LotteryParticipant.user))
        )
        participants = participants.scalars().all()
        
        if not participants:
            await message.answer("❌ Нет участников")
            lottery.is_active = False
            lottery.ended_at = datetime.utcnow()
            await session.commit()
            return
        
        winner = random.choice(participants)
        
        winner_user = winner.user
        
        await add_item_to_inventory(
            user_id=winner.user_id,
            item_id=lottery.prize_item_id,
            quantity=lottery.prize_quantity
        )
        
        lottery.is_active = False
        lottery.ended_at = datetime.utcnow()
        await session.commit()
    
    await notify_lottery_results(message.bot, lottery, participants, winner_user)
    
    await message.answer(
        f"✅ <b>ЛОТЕРЕЯ ЗАВЕРШЕНА!</b>\n\n"
        f"┠ 🏆 Победитель: {winner_user.first_name}\n"
        f"┠ 🎁 Приз: {PRIZES[lottery.prize_item_id]['emoji']} {PRIZES[lottery.prize_item_id]['name']} x{lottery.prize_quantity}\n\n"
        f"┠ Все участники оповещены.",
        reply_markup=admin_keyboards.admin_main_keyboard()
    )


async def notify_lottery_results(bot, lottery, participants, winner_user):
    prize = PRIZES[lottery.prize_item_id]
    
    for participant in participants:
        try:
            if participant.user_id == winner_user.id:
                text = (
                    f"🎉 <b>ТЫ ВЫИГРАЛ В ЛОТЕРЕЕ!</b>\n\n"
                    f"┠ Приз: {prize['emoji']} {prize['name']} x{lottery.prize_quantity}\n"
                    f"┠ {prize['description']}\n\n"
                    f"┠ Приз уже в твоем инвентаре! 🎁"
                )
                await bot.send_message(chat_id=participant.user.telegram_id, text=text)
            else:
                text = (
                    f"🍀 <b>ЛОТЕРЕЯ ЗАВЕРШЕНА</b>\n\n"
                    f"┠ Приз: {prize['emoji']} {prize['name']} x{lottery.prize_quantity}\n"
                    f"┠ Победитель: {winner_user.first_name}\n\n"
                    f"┠ В следующий раз повезет! ✨"
                )
                await bot.send_message(chat_id=participant.user.telegram_id, text=text)
            
            await asyncio.sleep(0.05)
        except Exception as e:
            print(f"Ошибка уведомления пользователя {participant.user_id}: {e}")