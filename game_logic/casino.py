import random
from typing import Dict, Tuple, List


class DiceGame:
    
    ODDS = {
        'high': 48.0,
        'low': 48.0,       
        'field': 44.0,     
        'double': 16.67,   
        'triple': 2.78,    
        'sum_10': 12.5,    
        'sum_11': 12.5,    
    }
    
    MULTIPLIERS = {
        'high': 2,
        'low': 2,
        'field': 2.2,
        'double': 5,
        'triple': 30,
        'sum_10': 8,
        'sum_11': 8,
        'lucky_7': 4,
    }
    
    @staticmethod
    def roll_dice() -> Tuple[int, int, int]:
        return (
            random.randint(1, 6),
            random.randint(1, 6),
            random.randint(1, 6)
        )
    
    @staticmethod
    def calculate_result(dice: Tuple[int, int, int]) -> Dict:
        d1, d2, d3 = dice
        total = d1 + d2 + d3
        is_double = (d1 == d2) or (d1 == d3) or (d2 == d3)
        is_triple = (d1 == d2 == d3)
        
        sorted_dice = sorted(dice)
        
        return {
            'dice': dice,
            'sorted': sorted_dice,
            'total': total,
            'is_double': is_double,
            'is_triple': is_triple,
            'high': total >= 11,
            'low': total <= 6,
            'field': total not in [7, 8],
            'sum_10': total == 10,
            'sum_11': total == 11,
            'lucky_7': total == 7,
        }
    
    @staticmethod
    def check_bet(bet_type: str, result: Dict) -> Tuple[bool, float]:
        if bet_type not in DiceGame.MULTIPLIERS:
            return False, 0
        
        win = result.get(bet_type, False)
        multiplier = DiceGame.MULTIPLIERS[bet_type] if win else 0
        
        return win, multiplier
    
    @staticmethod
    def get_random_bot_result() -> Dict:
        dice = DiceGame.roll_dice()
        return DiceGame.calculate_result(dice)
    
    @staticmethod
    def format_dice(dice: Tuple[int, int, int]) -> str:
        dice_emoji = {
            1: "1️⃣",
            2: "2️⃣",
            3: "3️⃣",
            4: "4️⃣",
            5: "5️⃣",
            6: "6️⃣"
        }
        return f"{dice_emoji[dice[0]]} {dice_emoji[dice[1]]} {dice_emoji[dice[2]]}"
    
    @staticmethod
    def format_dice_simple(dice: Tuple[int, int, int]) -> str:
        return f"{dice[0]}-{dice[1]}-{dice[2]}"
    
    @staticmethod
    def get_bet_types() -> List[Dict]:
        return [
            {'type': 'high', 'name': 'Больше 10', 'multiplier': 2, 'emoji': '⬆️', 'description': 'Сумма 11-18'},
            {'type': 'low', 'name': 'Меньше 7', 'multiplier': 2, 'emoji': '⬇️', 'description': 'Сумма 3-6'},
            {'type': 'field', 'name': 'Поле', 'multiplier': 2.2, 'emoji': '🎯', 'description': 'Всё кроме 7 и 8'},
            {'type': 'double', 'name': 'Дубль', 'multiplier': 5, 'emoji': '🔄', 'description': 'Две одинаковые'},
            {'type': 'triple', 'name': 'Трипл', 'multiplier': 30, 'emoji': '🎲', 'description': 'Три одинаковых'},
            {'type': 'sum_10', 'name': 'Сумма 10', 'multiplier': 8, 'emoji': '🔟', 'description': 'Ровно 10'},
            {'type': 'sum_11', 'name': 'Сумма 11', 'multiplier': 8, 'emoji': '1️⃣1️⃣', 'description': 'Ровно 11'},
            {'type': 'lucky_7', 'name': 'Счастливое 7', 'multiplier': 4, 'emoji': '7️⃣', 'description': 'Ровно 7'},
        ]
    
    @staticmethod
    def calculate_house_edge() -> Dict[str, float]:
        edges = {}
        
        edges['high'] = 100 - (15/36 * 100 * 2)
        edges['low'] = 100 - (15/36 * 100 * 2)
        
        edges['field'] = 100 - (20/36 * 100 * 2.2)
        
        edges['double'] = 100 - (6/36 * 100 * 5)
        
        edges['triple'] = 100 - (6/216 * 100 * 30)
        
        return edges
    
    @staticmethod
    def get_probability(bet_type: str) -> float:
        probabilities = {
            'high': 15/36 * 100,
            'low': 15/36 * 100,
            'field': 20/36 * 100,
            'double': 6/36 * 100,
            'triple': 6/216 * 100,
            'sum_10': 27/216 * 100,
            'sum_11': 27/216 * 100,
            'lucky_7': 15/216 * 100,
        }
        return probabilities.get(bet_type, 0)
    
    @staticmethod
    def get_combination_name(result: Dict) -> str:
        if result['is_triple']:
            return f"Трипл {result['dice'][0]}"
        elif result['is_double']:
            dice = result['dice']
            if dice[0] == dice[1]:
                double_num = dice[0]
            elif dice[0] == dice[2]:
                double_num = dice[0]
            else:
                double_num = dice[1]
            return f"Дубль {double_num}"
        else:
            return "Разные"