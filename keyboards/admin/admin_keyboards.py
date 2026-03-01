from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def admin_main_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    
    builder.row(
        KeyboardButton(text="📊 Статистика"),
        KeyboardButton(text="📨 Рассылка"),
        width=2
    )
    builder.row(
        KeyboardButton(text="👥 Пользователи"),
        KeyboardButton(text="📈 Топ"),
        width=2
    )
    builder.row(
        KeyboardButton(text="🎲 Лотерея"),
        KeyboardButton(text="🔄 Ресет прогресса"),
        width=2
    )
    builder.row(
        KeyboardButton(text="⚙️ Настройки"),
        KeyboardButton(text="🔙 Выход"),
        width=2
    )
    
    return builder.as_markup(resize_keyboard=True)


def admin_back_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🔙 Назад"))
    return builder.as_markup(resize_keyboard=True)


def admin_broadcast_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    
    builder.row(
        KeyboardButton(text="✅ Отправить"),
        KeyboardButton(text="❌ Отмена"),
        width=2
    )
    
    return builder.as_markup(resize_keyboard=True)


def admin_reset_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    
    builder.row(
        KeyboardButton(text="⚠️ ПОЛНЫЙ СБРОС"),
        KeyboardButton(text="🔙 Назад"),
        width=2
    )
    
    return builder.as_markup(resize_keyboard=True)


def admin_settings_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    
    builder.row(
        KeyboardButton(text="💰 Цена пропуска"),
        width=1
    )
    builder.row(
        KeyboardButton(text="🏪 Цены в магазине"),
        width=1
    )
    builder.row(
        KeyboardButton(text="🔙 Назад"),
        width=1
    )
    
    return builder.as_markup(resize_keyboard=True)


def admin_price_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    
    builder.row(
        KeyboardButton(text="1 🌟"),
        KeyboardButton(text="2 🌟"),
        KeyboardButton(text="3 🌟"),
        width=3
    )
    builder.row(
        KeyboardButton(text="5 🌟"),
        KeyboardButton(text="10 🌟"),
        KeyboardButton(text="15 🌟"),
        width=3
    )
    builder.row(
        KeyboardButton(text="20 🌟"),
        KeyboardButton(text="🔙 Назад"),
        width=2
    )
    
    return builder.as_markup(resize_keyboard=True)


def admin_lottery_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    
    builder.row(
        KeyboardButton(text="🎫 Билет на Остров смерти"),
        KeyboardButton(text="🗺️ Карта сокровищ"),
        width=2
    )
    builder.row(
        KeyboardButton(text="🍀 Амулет удачи"),
        KeyboardButton(text="🔙 Назад"),
        width=2
    )
    
    return builder.as_markup(resize_keyboard=True)


def admin_lottery_quantity_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    
    builder.row(
        KeyboardButton(text="1"),
        KeyboardButton(text="2"),
        KeyboardButton(text="3"),
        width=3
    )
    builder.row(
        KeyboardButton(text="5"),
        KeyboardButton(text="10"),
        KeyboardButton(text="🔙 Назад"),
        width=3
    )
    
    return builder.as_markup(resize_keyboard=True)


def admin_lottery_price_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    
    builder.row(
        KeyboardButton(text="1 ⭐"),
        KeyboardButton(text="2 ⭐"),
        KeyboardButton(text="3 ⭐"),
        width=3
    )
    builder.row(
        KeyboardButton(text="5 ⭐"),
        KeyboardButton(text="10 ⭐"),
        KeyboardButton(text="🔙 Назад"),
        width=3
    )
    
    return builder.as_markup(resize_keyboard=True)


def admin_active_lottery_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    
    builder.row(
        KeyboardButton(text="📊 Статус лотереи"),
        width=1
    )
    builder.row(
        KeyboardButton(text="✅ Завершить лотерею"),
        KeyboardButton(text="🔙 Назад"),
        width=2
    )
    
    return builder.as_markup(resize_keyboard=True)

def admin_shop_prices_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    
    builder.row(
        KeyboardButton(text="Билет на Остров смерти"),
        KeyboardButton(text="Карта сокровищ"),
        width=2
    )
    builder.row(
        KeyboardButton(text="Амулет удачи"),
        KeyboardButton(text="🔙 Назад"),
        width=2
    )
    
    return builder.as_markup(resize_keyboard=True)


def admin_item_price_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    
    builder.row(
        KeyboardButton(text="1 ✨"),
        KeyboardButton(text="2 ✨"),
        KeyboardButton(text="3 ✨"),
        width=3
    )
    builder.row(
        KeyboardButton(text="5 ✨"),
        KeyboardButton(text="10 ✨"),
        KeyboardButton(text="15 ✨"),
        width=3
    )
    builder.row(
        KeyboardButton(text="20 ✨"),
        KeyboardButton(text="🔙 Назад"),
        width=2
    )
    
    return builder.as_markup(resize_keyboard=True)