from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict


def main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🏴‍☠️ В плавание", callback_data="voyage_start"),
        InlineKeyboardButton(text="⚓ Корабль", callback_data="ship_info"),
        width=2
    )
    builder.row(
        InlineKeyboardButton(text="🏪 Магазин", callback_data="shop_main"),
        InlineKeyboardButton(text="🎒 Инвентарь", callback_data="inventory"),
        width=2
    )
    builder.row(
        InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
        InlineKeyboardButton(text="🎰 Казино", callback_data="casino_main"),
        width=2
    )
    builder.row(
        InlineKeyboardButton(text="🏆 Рейтинги", callback_data="ratings"),
        width=1
    )
    
    return builder.as_markup()


def shop_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="⚓ Улучшения корабля", callback_data="shop_ship"),
        width=1
    )
    builder.row(
        InlineKeyboardButton(text="👥 Улучшения команды", callback_data="shop_crew"),
        width=1
    )
    builder.row(
        InlineKeyboardButton(text="🎒 Особые предметы", callback_data="shop_items"),
        width=1
    )
    builder.row(
        InlineKeyboardButton(text="◀ Назад", callback_data="main_menu"),
        width=1
    )
    
    return builder.as_markup()


def upgrades_menu(upgrades: List[Dict], category: str, current_levels: Dict) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for upgrade in upgrades:
        upgrade_id = upgrade['id']
        current_level = current_levels.get(upgrade_id, 0)
        max_level = upgrade['max_level']
        
        if current_level >= max_level:
            name = f"✅ {upgrade['name']} (MAX)"
        else:
            name = f"{upgrade['name']} [{current_level}/{max_level}]"
        
        builder.row(
            InlineKeyboardButton(
                text=name,
                callback_data=f"upgrade_{category}_{upgrade_id}"
            ),
            width=1
        )
    
    builder.row(
        InlineKeyboardButton(text="◀ Назад", callback_data="shop_main"),
        width=1
    )
    
    return builder.as_markup()


def upgrade_details(upgrade_id: str, category: str, current_level: int, 
                   max_level: int, price: int, can_afford: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    if current_level < max_level:
        if can_afford:
            builder.row(
                InlineKeyboardButton(
                    text=f"💰 Купить за {price} монет",
                    callback_data=f"buy_{category}_{upgrade_id}"
                ),
                width=1
            )
        else:
            builder.row(
                InlineKeyboardButton(
                    text=f"❌ Не хватает монет ({price})",
                    callback_data="no_money"
                ),
                width=1
            )
    
    builder.row(
        InlineKeyboardButton(
            text="◀ Назад",
            callback_data=f"shop_{category}"
        ),
        width=1
    )
    
    return builder.as_markup()


def inventory_categories_menu(sellable: int, usable: int, special: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    if sellable > 0:
        builder.row(
            InlineKeyboardButton(text=f"💰 На продажу ({sellable})", callback_data="inventory_category_sellable"),
            width=1
        )
    else:
        builder.row(
            InlineKeyboardButton(text=f"💰 На продажу (0)", callback_data="inventory_category_sellable_empty"),
            width=1
        )
    
    if usable > 0:
        builder.row(
            InlineKeyboardButton(text=f"✨ Используемые ({usable})", callback_data="inventory_category_usable"),
            width=1
        )
    else:
        builder.row(
            InlineKeyboardButton(text=f"✨ Используемые (0)", callback_data="inventory_category_usable_empty"),
            width=1
        )
    
    if special > 0:
        builder.row(
            InlineKeyboardButton(text=f"🔮 Особые ({special})", callback_data="inventory_category_special"),
            width=1
        )
    else:
        builder.row(
            InlineKeyboardButton(text=f"🔮 Особые (0)", callback_data="inventory_category_special_empty"),
            width=1
        )
    
    builder.row(
        InlineKeyboardButton(text="◀ Назад", callback_data="main_menu"),
        width=1
    )
    
    return builder.as_markup()


def category_items_menu(items: List[Dict], page: int, total_pages: int, category: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for item in items:
        builder.row(
            InlineKeyboardButton(
                text=f"{item['emoji']} {item['name']} x{item['quantity']}",
                callback_data=f"item_{category}_{item['item_id']}"
            ),
            width=1
        )
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="◀", callback_data=f"inventory_category_{category}_page_{page-1}")
        )
    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(text="▶", callback_data=f"inventory_category_{category}_page_{page+1}")
        )
    
    if nav_buttons:
        builder.row(*nav_buttons, width=2)
    
    if category == 'sellable' and items:
        builder.row(
            InlineKeyboardButton(text="💰 ПРОДАТЬ ВСЁ", callback_data="sell_all_items"),
            width=1
        )
    
    builder.row(
        InlineKeyboardButton(text="◄ НАЗАД", callback_data="inventory"),
        width=1
    )
    
    return builder.as_markup()


def item_detail_menu(item_id: str, category: str, quantity: int, item_data: Dict) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    if quantity > 0:
        if category == 'sellable':
            price = item_data.get('price', 0)
            if price > 0:
                builder.row(
                    InlineKeyboardButton(
                        text=f"💰 Продать за {price} монет",
                        callback_data=f"sell_{category}_{item_id}"
                    ),
                    width=1
                )
        elif category in ['usable', 'special']:
            builder.row(
                InlineKeyboardButton(
                    text="✨ Использовать",
                    callback_data=f"use_{category}_{item_id}"
                ),
                width=1
            )
    
    builder.row(
        InlineKeyboardButton(text="◀ Назад", callback_data=f"inventory_category_{category}"),
        width=1
    )
    
    return builder.as_markup()


def active_effects_menu(effects: List[Dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    if effects:
        for effect in effects:
            name = f"{effect['emoji']} {effect['name']} ({effect['remaining']})"
            builder.row(
                InlineKeyboardButton(text=name, callback_data=f"effect_{effect['id']}"),
                width=1
            )
    else:
        builder.row(
            InlineKeyboardButton(text="✨ Нет активных эффектов", callback_data="noop"),
            width=1
        )
    
    builder.row(
        InlineKeyboardButton(text="◀ Назад", callback_data="inventory"),
        width=1
    )
    
    return builder.as_markup()


def back_button(callback: str = "main_menu") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀ Назад", callback_data=callback))
    return builder.as_markup()


def yes_no_buttons(action: str, back_callback: str = "main_menu") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да", callback_data=f"{action}_confirm"),
        InlineKeyboardButton(text="❌ Нет", callback_data=back_callback),
        width=2
    )
    return builder.as_markup()


def confirm_cancel(action: str, back_callback: str = "main_menu") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"{action}_confirm"),
        InlineKeyboardButton(text="❌ Отмена", callback_data=back_callback),
        width=2
    )
    return builder.as_markup()


def event_choice_menu(event_id: str, options: List[Dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for option in options:
        builder.row(
            InlineKeyboardButton(
                text=option['text'],
                callback_data=f"event_{event_id}_{option['callback']}"
            ),
            width=1
        )
    
    return builder.as_markup()