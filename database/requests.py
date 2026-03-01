from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from database.db import async_session
from database.models import User, Ship, Crew, Inventory, ActiveEffect
from datetime import datetime
from typing import List


async def get_or_create_user(telegram_id: int, username: str = None, 
                            first_name: str = None, last_name: str = None) -> User:
    """Получить пользователя или создать нового"""
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == telegram_id)
            .options(
                selectinload(User.ship),
                selectinload(User.crew)
            )
        )
        user = result.scalar_one_or_none()
        
        if user:
            user.last_activity = datetime.utcnow()
            await session.commit()
            
            session.expunge(user)
            return user
        
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        session.add(user)
        await session.flush()
        
        ship = Ship(user_id=user.id)
        session.add(ship)
        
        crew = Crew(user_id=user.id)
        session.add(crew)
        
        await session.commit()
        
        result = await session.execute(
            select(User)
            .where(User.id == user.id)
            .options(
                selectinload(User.ship),
                selectinload(User.crew)
            )
        )
        user = result.scalar_one()
        
        session.expunge(user)
        return user


async def update_user_money(user_id: int, amount: int, session: AsyncSession = None):
    if session:
        user = await session.get(User, user_id)
        if user:
            user.current_money += amount
            if amount > 0:
                user.total_money += amount
            await session.commit()
    else:
        async with async_session() as new_session:
            user = await new_session.get(User, user_id)
            if user:
                user.current_money += amount
                if amount > 0:
                    user.total_money += amount
                await new_session.commit()

async def get_user_inventory(user_id: int) -> List[Inventory]:
    async with async_session() as session:
        result = await session.execute(
            select(Inventory)
            .where(Inventory.user_id == user_id)
            .order_by(Inventory.item_id)
        )
        return result.scalars().all()


async def add_item_to_inventory(user_id: int, item_id: str, quantity: int = 1):
    async with async_session() as session:
        result = await session.execute(
            select(Inventory)
            .where(Inventory.user_id == user_id)
            .where(Inventory.item_id == item_id)
        )
        item = result.scalar_one_or_none()
        
        if item:
            item.quantity += quantity
        else:
            item = Inventory(
                user_id=user_id,
                item_id=item_id,
                quantity=quantity
            )
            session.add(item)
        
        await session.commit()
        return item


async def remove_item_from_inventory(user_id: int, item_id: str, quantity: int = 1) -> bool:
    async with async_session() as session:
        result = await session.execute(
            select(Inventory)
            .where(Inventory.user_id == user_id)
            .where(Inventory.item_id == item_id)
        )
        item = result.scalar_one_or_none()
        
        if not item or item.quantity < quantity:
            return False
        
        item.quantity -= quantity
        if item.quantity <= 0:
            await session.delete(item)
        
        await session.commit()
        return True


async def add_active_effect(user_id: int, effect_type: str, source_item: str, 
                           remaining_uses: int = 1, expires_at: datetime = None):
    async with async_session() as session:
        result = await session.execute(
            select(ActiveEffect)
            .where(ActiveEffect.user_id == user_id)
            .where(ActiveEffect.effect_type == effect_type)
            .where(ActiveEffect.remaining_uses > 0)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.remaining_uses += remaining_uses
            await session.commit()
            return existing
        
        effect = ActiveEffect(
            user_id=user_id,
            effect_type=effect_type,
            source_item=source_item,
            remaining_uses=remaining_uses,
            expires_at=expires_at,
            created_at=datetime.utcnow()
        )
        session.add(effect)
        await session.commit()
        
        await session.refresh(effect)
        return effect


async def get_active_effects(user_id: int) -> List[ActiveEffect]:
    async with async_session() as session:
        result = await session.execute(
            select(ActiveEffect)
            .where(ActiveEffect.user_id == user_id)
            .where(ActiveEffect.remaining_uses > 0)
            .order_by(ActiveEffect.created_at)
        )
        return result.scalars().all()


async def remove_active_effect(effect_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(ActiveEffect).where(ActiveEffect.id == effect_id)
        )
        effect = result.scalar_one_or_none()
        if effect:
            await session.delete(effect)
            await session.commit()
            return True
        return False


async def decrement_active_effects(user_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(ActiveEffect)
            .where(ActiveEffect.user_id == user_id)
            .where(ActiveEffect.remaining_uses > 0)
        )
        effects = result.scalars().all()
        
        for effect in effects:
            effect.remaining_uses -= 1
            if effect.remaining_uses <= 0:
                await session.delete(effect)
        
        await session.commit()
        return len(effects)

async def has_active_effect(user_id: int, effect_type: str) -> bool:
    async with async_session() as session:
        result = await session.execute(
            select(ActiveEffect)
            .where(ActiveEffect.user_id == user_id)
            .where(ActiveEffect.effect_type == effect_type)
            .where(ActiveEffect.remaining_uses > 0)
        )
        effect = result.scalar_one_or_none()
        return effect is not None


async def get_effect_remaining(user_id: int, effect_type: str) -> int:
    async with async_session() as session:
        result = await session.execute(
            select(ActiveEffect)
            .where(ActiveEffect.user_id == user_id)
            .where(ActiveEffect.effect_type == effect_type)
            .where(ActiveEffect.remaining_uses > 0)
        )
        effect = result.scalar_one_or_none()
        return effect.remaining_uses if effect else 0