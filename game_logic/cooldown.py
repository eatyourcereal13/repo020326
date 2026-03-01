from datetime import datetime, timedelta
from typing import Optional
from database.models import User

BASE_COOLDOWN = 15 * 60

MIN_COOLDOWN = 60


def calculate_cooldown(user: User) -> int:
    cooldown = BASE_COOLDOWN
    
    cooldown -= user.ship.sails_level * 30
    cooldown -= user.ship.hull_level * 20
    cooldown -= user.ship.copper_sheathing_level * 15
    cooldown -= user.ship.steam_engine_level * 60
    
    if user.crew.boatswain_level > 0:
        cooldown = int(cooldown * 0.9)
    
    return max(MIN_COOLDOWN, cooldown)


def get_remaining_cooldown(user: User) -> Optional[int]:
    if not user.last_voyage_time:
        return 0
    
    cooldown = calculate_cooldown(user)
    next_available = user.last_voyage_time + timedelta(seconds=cooldown)
    now = datetime.utcnow()
    
    if now >= next_available:
        return 0
    
    remaining = (next_available - now).seconds
    return remaining


def format_cooldown(seconds: int) -> str:
    if seconds >= 60:
        minutes = seconds // 60
        secs = seconds % 60
        if minutes >= 60:
            hours = minutes // 60
            mins = minutes % 60
            return f"{hours}ч {mins}м"
        return f"{minutes}м {secs}с"
    return f"{seconds}с"

def can_skip_cooldown(user: User) -> bool:
    return True


def get_skip_price() -> int:
    return 1