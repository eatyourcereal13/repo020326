import json
import random
import os
from typing import Dict, Optional, Tuple
from config import config

EVENTS_PATH = os.path.join(config.BASE_DIR, 'data', 'events.json')
with open(EVENTS_PATH, 'r', encoding='utf-8') as f:
    EVENTS_DATA = json.load(f)


def get_random_event(user_level: int, location_multiplier: float = 1.0,
                    storm_reduction: float = 0.0) -> Optional[Dict]:
    available_events = []
    event_weights = []
    
    for event_id, event in EVENTS_DATA.items():
        if event.get('min_level', 1) <= user_level:
            if event_id == 'storm' and storm_reduction > 0:
                modified_chance = event.get('chance', 10) * (1 - storm_reduction)
                if modified_chance <= 0:
                    continue
                event_weights.append(modified_chance)
            else:
                event_weights.append(event.get('chance', 10))
            
            available_events.append((event_id, event))
    
    if not available_events:
        return None
    
    event_weights = [w * location_multiplier for w in event_weights]
    
    total_weight = sum(event_weights)
    rand = random.uniform(0, total_weight)
    cumulative = 0
    selected_event = None
    
    for i, (event_id, event) in enumerate(available_events):
        weight = event_weights[i]
        cumulative += weight
        if rand <= cumulative:
            selected_event = (event_id, event)
            break
    
    if not selected_event:
        return None
    
    event_id, event = selected_event
    
    return {
        'id': event_id,
        **event
    }


def process_event_choice(event_id: str, choice: str, user_data: Dict) -> Tuple[str, Dict]:
    
    result_text = ""
    modifiers = {
        'loot_multiplier': 1.0,
        'damage': 0,
        'money': 0,
        'effect': None,
        'guaranteed_loot': None,
        'use_ticket': False,
        'morale_change': 0,
        'exp_gained': 0
    }
    
    current_money = user_data.get('current_money', 0)
    
    if event_id == 'storm':
        if choice == 'storm_wait':
            result_text = "┠ 🌊 Шторм задержал корабль. Ты потерял время, но нашел выброшенный на палубу ящик."
            modifiers['loot_multiplier'] = 1.2
        elif choice == 'storm_pay':
            cost = 30
            if current_money >= cost:
                result_text = "┠ 💰 Матросы справились со штормом! Они довольны дополнительной платой."
                modifiers['money'] = -cost
                modifiers['morale_change'] = 10
            else:
                result_text = f"┠ ❌ У тебя недостаточно монет! Нужно {cost}. Пришлось пережидать шторм."
                modifiers['loot_multiplier'] = 1.2
    
    elif event_id == 'merchant':
        if choice == 'merchant_attack':
            result_text = "┠ ⚔️ Ты атаковал торговца! Бой начинается..."
            modifiers['effect'] = 'combat_merchant'
        elif choice == 'merchant_trade':
            cost = 200
            if current_money >= cost:
                result_text = "┠ 🤝 Торговец предлагает товары. Ты покупаешь кое-что интересное."
                modifiers['effect'] = 'merchant_discount'
                modifiers['money'] = -cost
            else:
                result_text = f"┠ ❌ У тебя недостаточно монет! Нужно {cost}. Пришлось проплыть мимо."
        elif choice == 'merchant_ignore':
            result_text = "┠ ⏩ Ты проплыл мимо. Торговец скрылся за горизонтом."
    
    elif event_id == 'kraken':
        if choice == 'kraken_fight':
            result_text = "┠ ⚔️ Ты решил сразиться с Кракеном!"
            modifiers['effect'] = 'combat_kraken'
        elif choice == 'kraken_run':
            result_text = "┠ 🏃‍♂️ Ты быстро уплываешь, но Кракен повредил корабль."
            modifiers['damage'] = 30
            modifiers['loot_multiplier'] = 0.7
    
    elif event_id == 'island':
        if choice == 'island_land':
            result_text = "┠ 🏝️ На острове ты нашел тайник с сокровищами!"
            modifiers['loot_multiplier'] = 1.8
        elif choice == 'island_ignore':
            result_text = "┠ ⏩ Остров остается загадкой..."
    
    elif event_id == 'whale':
        if choice == 'whale_watch':
            result_text = "┠ 🐋 Наблюдение за китом принесло удачу!"
            modifiers['loot_multiplier'] = 1.3
        elif choice == 'whale_ignore':
            result_text = "┠ ⏩ Ты плывешь дальше."
    
    elif event_id == 'siren':
        if choice == 'siren_resist':
            result_text = "┠ 👂 Ты заткнул уши и быстро прошел опасный участок!"
            modifiers['loot_multiplier'] = 1.2
        elif choice == 'siren_follow':
            result_text = "┠ 🎵 Корабль налетел на скалы! Ты потерял часть груза."
            modifiers['loot_multiplier'] = 0.5
            modifiers['damage'] = 40
    
    return result_text, modifiers