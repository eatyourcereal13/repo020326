import json
import random
import os
from typing import List, Dict
from config import config

ITEMS_PATH = os.path.join(config.BASE_DIR, 'data', 'items.json')
with open(ITEMS_PATH, 'r', encoding='utf-8') as f:
    ITEMS_DATA = json.load(f)

SELLABLE_ITEMS = ITEMS_DATA['sellable']

RARITY_CHANCES = {
    'common': 60,
    'uncommon': 25,
    'rare': 10,
    'epic': 4,
    'legendary': 1
}

BASE_LOOT_COUNT = 3

ITEMS_BY_RARITY = {
    'common': [],
    'uncommon': [],
    'rare': [],
    'epic': [],
    'legendary': []
}

for item_id, item in SELLABLE_ITEMS.items():
    rarity = item.get('rarity', 'common')
    if rarity in ITEMS_BY_RARITY:
        ITEMS_BY_RARITY[rarity].append((item_id, item))


def get_random_rarity(luck_multiplier: float = 1.0, rare_chance_bonus: int = 0) -> str:
    chances = RARITY_CHANCES.copy()
    
    if rare_chance_bonus > 0:
        bonus_rare = rare_chance_bonus
        bonus_epic = rare_chance_bonus * 0.4
        bonus_legendary = rare_chance_bonus * 0.2
        
        chances['rare'] += bonus_rare
        chances['epic'] += bonus_epic
        chances['legendary'] += bonus_legendary
        chances['common'] -= bonus_rare + bonus_epic + bonus_legendary
    
    if luck_multiplier > 1.0:
        luck_bonus = 0.3
        chances['rare'] *= (1 + luck_bonus * 0.5)
        chances['epic'] *= (1 + luck_bonus)
        chances['legendary'] *= (1 + luck_bonus)
        chances['common'] /= (1 + luck_bonus)
    
    total = sum(chances.values())
    if abs(total - 100) > 0.1:
        for rarity in chances:
            chances[rarity] = (chances[rarity] / total) * 100
    
    rand = random.uniform(0, 100)
    cumulative = 0
    for rarity, chance in chances.items():
        cumulative += chance
        if rand <= cumulative:
            return rarity
    
    return 'common'


def get_random_sellable_item(rarity: str) -> Dict:
    items = ITEMS_BY_RARITY.get(rarity, [])
    
    if not items:
        items = ITEMS_BY_RARITY.get('common', [])
    
    if items:
        item_id, item = random.choice(items)
        result = item.copy()
        result['id'] = item_id
        return result
    
    return {
        'id': 'rope',
        'name': '🪢 Веревка',
        'emoji': '🪢',
        'price': 5,
        'rarity': 'common'
    }


def generate_loot(user_level: int, location_multiplier: float = 1.0, 
                  luck_multiplier: float = 1.0, guaranteed_chest: bool = False,
                  loot_quantity_bonus: int = 0, loot_value_bonus: int = 0,
                  rare_chance_bonus: int = 0, is_death_island: bool = False) -> List[Dict]:
    loot = []
    
    # ========== ОСОБЫЙ РЕЖИМ ДЛЯ ОСТРОВА СМЕРТИ ==========
    if is_death_island:
        count = BASE_LOOT_COUNT + loot_quantity_bonus + 2
        guaranteed_chest = True
    else:
        count = BASE_LOOT_COUNT + loot_quantity_bonus
    # ======================================================
    
    if guaranteed_chest:
        legendary_items = ITEMS_BY_RARITY.get('legendary', [])
        if legendary_items:
            item_id, item = random.choice(legendary_items)
            chest = item.copy()
            chest['id'] = item_id
            loot.append(chest)
        else:
            loot.append({
                'id': 'treasure_chest',
                'name': '🧰 Сундук с сокровищами',
                'emoji': '🧰',
                'price': 2000,
                'rarity': 'legendary'
            })
        count -= 1
    
    for i in range(count):
        if is_death_island:
            death_rarity_chances = {
                'rare': 60,
                'epic': 30,
                'legendary': 10
            }
            
            rand = random.uniform(0, 100)
            cumulative = 0
            rarity = 'rare'
            for r, chance in death_rarity_chances.items():
                cumulative += chance
                if rand <= cumulative:
                    rarity = r
                    break
        else:
            rarity = get_random_rarity(luck_multiplier, rare_chance_bonus)
        
        item = get_random_sellable_item(rarity)
        
        if is_death_island:
            item['price'] = int(item['price'] * 2.0)
        
        if loot_value_bonus > 0:
            item['price'] = int(item['price'] * (1 + loot_value_bonus / 100))
        
        if location_multiplier != 1.0:
            item['price'] = int(item['price'] * location_multiplier)
        
        loot.append(item)
    
    random.shuffle(loot)
    return loot


def calculate_loot_value(loot: List[Dict]) -> int:
    return sum(item['price'] for item in loot)


def format_loot_message(loot: List[Dict]) -> str:
    lines = ["┠ <b>НАЙДЕННЫЕ ПРЕДМЕТЫ:</b>"]
    
    rarity_emojis = {
        'common': '⚪',
        'uncommon': '🟢',
        'rare': '🔵',
        'epic': '🟣',
        'legendary': '🟡'
    }
    
    for item in loot:
        rarity = item.get('rarity', 'common')
        emoji = rarity_emojis.get(rarity, '⚪')
        if rarity == 'legendary':
            lines.append(f"┠ ✨ {emoji} <b>{item['name']}</b> — <code>{item['price']}</code>💰 ✨")
        else:
            lines.append(f"┠ {emoji}  {item['name']} — <code>{item['price']}</code>💰")
    
    total = calculate_loot_value(loot)
    lines.append(f"\n┠ <b>ОБЩАЯ СТОИМОСТЬ:</b> <code>{total}</code>💰")
    lines.append(f"┠ <i>Продай предметы в магазине</i>")
    
    return "\n".join(lines)


def get_loot_stats(rare_chance_bonus: int = 0, luck_multiplier: float = 1.0) -> Dict:
    base_chances = RARITY_CHANCES.copy()
    modified_chances = {}
    
    if rare_chance_bonus > 0 or luck_multiplier > 1.0:
        for _ in range(1000):
            rarity = get_random_rarity(luck_multiplier, rare_chance_bonus)
            modified_chances[rarity] = modified_chances.get(rarity, 0) + 1
        
        for rarity in modified_chances:
            modified_chances[rarity] = modified_chances[rarity] / 10
    
    return {
        'base': base_chances,
        'modified': modified_chances
    }