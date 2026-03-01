import random
from typing import Dict, Tuple


def calculate_combat_outcome(attacker_level: int, defender_type: str,
                            ship_stats: Dict, crew_stats: Dict) -> Tuple[bool, Dict]:
    
    base_power = 10 + attacker_level * 2
    
    cannon_bonus = ship_stats.get('cannons_level', 0) * 0.1
    base_power *= (1 + cannon_bonus)

    gunner_bonus = crew_stats.get('gunner_level', 0) * 0.15
    base_power *= (1 + gunner_bonus)
    
    if defender_type == 'merchant':
        enemy_power = 20 + random.randint(0, 20)
    elif defender_type == 'kraken':
        enemy_power = 50 + ship_stats.get('copper_sheathing_level', 0) * 5
    else:
        enemy_power = 30
    
    luck = random.uniform(0.8, 1.2)
    base_power *= luck
    
    victory = base_power >= enemy_power
    
    modifiers = {
        'loot_multiplier': 2.0 if victory else 0.5,
        'damage': random.randint(10, 30) if not victory else random.randint(0, 10),
        'experience': 50 if victory else 10
    }
    
    if defender_type == 'kraken' and victory:
        modifiers['special_loot'] = 'kraken_eye'
    
    return victory, modifiers


def get_combat_description(defender_type: str, victory: bool) -> str:
    if defender_type == 'merchant':
        if victory:
            return "⚔️ Ты захватил торговое судно! Добыча удвоена!"
        else:
            return "💥 Торговец дал отпор! Корабль поврежден, добыча уменьшена."
    
    elif defender_type == 'kraken':
        if victory:
            return "🐙 Ты победил Кракена! Легендарный трофей твой!"
        else:
            return "🌊 Кракен утащил часть команды... Корабль серьезно поврежден."
    
    return "⚔️ Бой окончен."