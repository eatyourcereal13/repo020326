from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from keyboards.inline import back_button
from typing import Dict
from database.db import async_session
from database.models import User
from game_logic.casino import DiceGame

router = Router()


@router.callback_query(F.data == "casino_main")
async def casino_main(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Ошибка загрузки данных", show_alert=True)
            return
    
    bet_types = DiceGame.get_bet_types()
    
    builder = InlineKeyboardBuilder()
    
    for i, bet in enumerate(bet_types):
        multiplier = bet['multiplier']
        if multiplier == int(multiplier):
            multiplier = int(multiplier)
        
        builder.button(
            text=f"{bet['emoji']} {bet['name']}  x{multiplier}",
            callback_data=f"casino_bet_{bet['type']}"
        )
    
    builder.adjust(2)
    
    builder.row(
        InlineKeyboardButton(text="💰 МОИ МОНЕТЫ", callback_data="casino_balance"),
        width=1
    )
    builder.row(
        InlineKeyboardButton(text="◄ НАЗАД", callback_data="main_menu"),
        width=1
    )
    
    text = (
        f"🎰 <b>ПИРАТСКОЕ КАЗИНО</b>\n\n"
        f"┠ <b>Баланс:</b> <code>{user.current_money}</code> монет\n\n"
        f"┠ <i>Введи сумму ставки после выбора</i>"
    )
    
    await callback.message.delete()
    await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("casino_bet_"))
async def casino_bet_type(callback: CallbackQuery):
    bet_type = callback.data.replace("casino_bet_", "")
    
    bet_types = {b['type']: b for b in DiceGame.get_bet_types()}
    bet = bet_types.get(bet_type, {})
    
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Ошибка загрузки данных", show_alert=True)
            return
    
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🔹 10", callback_data=f"casino_play_{bet_type}_10"),
        InlineKeyboardButton(text="🔹 50", callback_data=f"casino_play_{bet_type}_50"),
        InlineKeyboardButton(text="🔹 100", callback_data=f"casino_play_{bet_type}_100"),
        width=3
    )
    builder.row(
        InlineKeyboardButton(text="🔹 500", callback_data=f"casino_play_{bet_type}_500"),
        InlineKeyboardButton(text="🔹 1000", callback_data=f"casino_play_{bet_type}_1000"),
        InlineKeyboardButton(text="🔹 5000", callback_data=f"casino_play_{bet_type}_5000"),
        width=3
    )
    builder.row(
        InlineKeyboardButton(text="◄ НАЗАД", callback_data="casino_main"),
        width=1
    )
    
    text = (
        f"🎰 <b>{bet.get('emoji', '🎲')} {bet.get('name', bet_type)}</b>\n\n"
        f"┠ <b>Баланс:</b> <code>{user.current_money}</code> монет\n"
        f"┠ <b>Множитель:</b> <code>x{bet.get('multiplier', 2)}</code>\n\n"
        f"┠ <b>СУММА СТАВКИ:</b>"
    )
    
    await callback.message.delete()
    await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("casino_play_"))
async def casino_play(callback: CallbackQuery):
    parts = callback.data.split("_")
    bet_type = parts[2]
    amount = int(parts[3])
    
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
        
        if user.current_money < amount:
            await callback.answer(
                f"❌ Нужно: {amount} | У тебя: {user.current_money} ",
                show_alert=True
            )
            return
        
        dice = DiceGame.roll_dice()
        result_dict = DiceGame.calculate_result(dice)
        win, multiplier = DiceGame.check_bet(bet_type, result_dict)
        
        dice_display = DiceGame.format_dice(dice)
        
        if win:
            winnings = int(amount * multiplier)
            user.current_money += winnings - amount
            user.total_money += winnings - amount
            result_text = f"🎉 <b>ВЫИГРЫШ:</b> +{winnings}"
        else:
            user.current_money -= amount
            result_text = f"💔 <b>ПРОИГРЫШ:</b> -{amount}"
        
        await session.commit()
        
        bet_types = {b['type']: b for b in DiceGame.get_bet_types()}
        bet = bet_types.get(bet_type, {})
        
        probability = DiceGame.get_probability(bet_type)
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="🎰 ЕЩЕ", callback_data="casino_main"),
            InlineKeyboardButton(text="⚓ В ПЛАВАНИЕ", callback_data="voyage_start"),
            width=2
        )
        builder.row(
            InlineKeyboardButton(text="◄ ГЛАВНОЕ МЕНЮ", callback_data="main_menu"),
            width=1
        )
        
        text = (
            f"🎲 <b>РЕЗУЛЬТАТ БРОСКА</b>\n\n"
            f"┠ {dice_display}\n\n"
            f"┠ <b>Сумма:</b> {result_dict['total']}\n"
            f"┠ <b>Комбинация:</b> {DiceGame.get_combination_name(result_dict)}\n\n"
            f"┠ <b>Ставка:</b> {amount}\n"
            f"┠ <b>Тип:</b> {bet.get('name', bet_type)}  x{bet.get('multiplier', 2)}\n"
            f"┠ <b>Шанс:</b> {probability:.1f}%\n\n"
            f"{result_text}\n\n"
            f"┠ <b>НОВЫЙ БАЛАНС:</b> <code>{user.current_money}</code> "
        )
        
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=builder.as_markup())
        await callback.answer()

@router.callback_query(F.data == "casino_balance")
async def casino_balance(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Ошибка загрузки данных", show_alert=True)
            return
    
    text = (
        f"💰 <b>ТВОЙ БАЛАНС</b>\n\n"
        f"┠ Монеты: <code>{user.current_money}</code>\n"
        f"┠ Всего заработано: <code>{user.total_money}</code>\n"
        f"┠ Рейдов: <b>{user.voyages_completed}</b>\n\n"
        f"┠ <i>Следи за кошельком, пират!</i> 🏴‍☠️"
    )
    
    await callback.message.delete()
    await callback.message.answer(text, reply_markup=back_button("casino_main"))
    await callback.answer()