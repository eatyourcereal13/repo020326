from sqlalchemy import Column, Integer, String, BigInteger, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database.db import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    # == Игровые параметры ==
    level = Column(Integer, default=1)
    exp = Column(Integer, default=0)
    total_money = Column(BigInteger, default=0)
    current_money = Column(BigInteger, default=0)
    reputation = Column(Integer, default=0)
    last_voyage_location = Column(String(50), default='navirettnye_ostrova')

    # == Статистика ==
    voyages_completed = Column(Integer, default=0)
    legendary_finds = Column(Integer, default=0)
    traders_attacked = Column(Integer, default=0)
    kraken_defeated = Column(Integer, default=0)
    last_voyage_time = Column(DateTime, nullable=True)

    # == Текущая локация ==
    current_location = Column(String(50), default='navirettnye_ostrova')

    # == Системные поля ==
    registered_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)

    # == Связи ==
    ship = relationship("Ship", back_populates="user", uselist=False, cascade="all, delete-orphan")
    crew = relationship("Crew", back_populates="user", uselist=False, cascade="all, delete-orphan")
    inventory = relationship("Inventory", back_populates="user", cascade="all, delete-orphan")
    voyage = relationship("Voyage", back_populates="user", uselist=False, cascade="all, delete-orphan")


class Ship(Base):
    __tablename__ = 'ships'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True)

    sails_level = Column(Integer, default=0)  # == Паруса ==
    hull_level = Column(Integer, default=0)  # == Корпус ==
    cannons_level = Column(Integer, default=0)  # == Пушки ==
    hold_level = Column(Integer, default=0)  # == Трюм ==
    copper_sheathing_level = Column(Integer, default=0)  # == Обшивка ==
    steam_engine_level = Column(Integer, default=0)  # == Двигатель ==

    health = Column(Integer, default=100)  # == ХП сейчас ==
    max_health = Column(Integer, default=100)  # == ХП макс

    user = relationship("User", back_populates="ship")


class Crew(Base):
    __tablename__ = 'crew'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True)

    boatswain_level = Column(Integer, default=0)  # == Боцман ==
    cook_level = Column(Integer, default=0)  # == Cock ну типа член поняли ==
    gunner_level = Column(Integer, default=0)  # == Пушечник ==
    navigator_level = Column(Integer, default=0)  # == Штурман ==
    parrot_level = Column(Integer, default=0)  # == Попугай ==

    morale = Column(Integer, default=100)  # == Мораль ==

    user = relationship("User", back_populates="crew")


class Inventory(Base):
    __tablename__ = 'inventory'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    item_id = Column(String(50))
    quantity = Column(Integer, default=0)
    acquired_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="inventory")


class Voyage(Base):
    __tablename__ = 'voyages'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True)

    
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    location = Column(String(50))
    
    
    active_effects = Column(Text, nullable=True)
    current_event = Column(Text, nullable=True)
    event_resolved = Column(Boolean, default=False)

    loot_json = Column(Text, nullable=True)
    event_happened = Column(String(50), nullable=True)
    experience_gained = Column(Integer, default=0)
    money_gained = Column(Integer, default=0)

    user = relationship("User", back_populates="voyage")


class Treasure(Base):
    __tablename__ = 'treasures'

    id = Column(Integer, primary_key=True)
    treasure_id = Column(String(50), unique=True)
    name = Column(String(100))
    rarity = Column(String(20))
    base_price = Column(Integer)
    description = Column(Text, nullable=True)
    min_level = Column(Integer, default=1)


class Upgrade(Base):
    __tablename__ = 'upgrades'

    id = Column(Integer, primary_key=True)
    upgrade_id = Column(String(50), unique=True)
    name = Column(String(100))
    category = Column(String(20))
    description = Column(Text)
    max_level = Column(Integer, default=10)

    price_json = Column(Text)

    effect_json = Column(Text)


class ActiveEffect(Base):
    """Активные эффекты от предметов"""
    __tablename__ = 'active_effects'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), index=True)
    effect_type = Column(String(50))
    source_item = Column(String(50))
    remaining_uses = Column(Integer, default=1)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", backref="active_effects")


class GroupSettings(Base):
    __tablename__ = 'group_settings'
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, unique=True, nullable=False, index=True)
    casino_enabled = Column(Boolean, default=True)
    min_level_for_voyage = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Lottery(Base):
    __tablename__ = 'lotteries'
    
    id = Column(Integer, primary_key=True)
    prize_item_id = Column(String(50), nullable=False)
    prize_quantity = Column(Integer, default=1)
    entry_price = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    participants = relationship("LotteryParticipant", back_populates="lottery", cascade="all, delete-orphan")


class LotteryParticipant(Base):
    __tablename__ = 'lottery_participants'
    
    id = Column(Integer, primary_key=True)
    lottery_id = Column(Integer, ForeignKey('lotteries.id', ondelete='CASCADE'))
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    payment_id = Column(String(255), nullable=True)
    participated_at = Column(DateTime, default=datetime.utcnow)
    
    lottery = relationship("Lottery", back_populates="participants")
    user = relationship("User")