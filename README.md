# Документация

## Содержание
1. [Общая архитектура](#общая-архитектура)
2. [Модели данных](#модели-данных)
3. [Категории предметов](#категории-предметов)
4. [Локации](#локации)
5. [События](#события)
6. [Улучшения](#улучшения)
7. [Магазин и платежи](#магазин-и-платежи)
8. [Инвентарь](#инвентарь)
9. [Плавание](#плавание)
10. [Структура файлов](#структура-файлов)

## Общая архитектура

Бот построен на aiogram 3.x и SQLAlchemy с asyncpg. База данных - PostgreSQL. Используются Telegram Stars для внутриигровых покупок.

Основные принципы:
- Каждое действие пользователя - отдельный callback
- Сообщения удаляются и создаются заново (чистый интерфейс)
- Состояние хранится в БД, FSM не используется
- Мгновенные рейды без таймеров

## Модели данных

### User
```python
id: int                    # Первичный ключ
telegram_id: bigint        # ID в Telegram (уникальный)
username: str              # Username в Telegram
first_name: str            # Имя
last_name: str             # Фамилия

# Игровые параметры
level: int                 # Текущий уровень (default=1)
exp: int                   # Опыт (default=0)
total_money: bigint        # Всего заработано монет
current_money: bigint      # Текущие монеты
reputation: int            # Репутация

# Статистика
voyages_completed: int     # Всего рейдов
legendary_finds: int       # Легендарных находок
traders_attacked: int      # Атак на торговцев
kraken_defeated: int       # Побед над кракеном

# Системные
current_location: str      # Текущая локация
registered_at: datetime    # Дата регистрации
last_activity: datetime    # Последняя активность
is_active: bool           # Активен ли пользователь
is_admin: bool            # Админ или нет

# Связи
ship: Ship                 # Корабль (one-to-one)
crew: Crew                 # Команда (one-to-one)
inventory: List[Inventory] # Инвентарь
voyage: Voyage            # Текущий рейд
active_effects: List[ActiveEffect] # Активные эффекты
```

### Ship
```python
user_id: int              # Внешний ключ к User
sails_level: int          # Паруса (0-10)
hull_level: int           # Корпус (0-10)
cannons_level: int        # Пушки (0-10)
hold_level: int           # Трюм (0-10)
copper_sheathing_level: int # Медная обшивка (0-10)
steam_engine_level: int   # Паровой двигатель (0-5)
health: int               # Текущая прочность (default=100)
max_health: int           # Максимальная прочность (default=100)
```

### Crew
```python
user_id: int              # Внешний ключ к User
boatswain_level: int      # Боцман (0-1)
cook_level: int           # Кок (0-5)
gunner_level: int         # Канонир (0-5)
navigator_level: int      # Штурман (0-5)
parrot_level: int         # Попугай (0-3)
morale: int               # Мораль команды (default=100)
```

### Inventory
```python
user_id: int              # Внешний ключ к User
item_id: str              # ID предмета (из items.json)
quantity: int             # Количество
acquired_at: datetime     # Дата получения
```

### Voyage
```python
user_id: int              # Внешний ключ к User (unique)
location: str             # Текущая локация
active_effects: text      # JSON с активными эффектами
current_event: text       # JSON с текущим событием
event_resolved: bool      # Обработано ли событие
loot_json: text          # JSON с добычей
event_happened: str      # Какое событие случилось
experience_gained: int    # Получено опыта
money_gained: int         # Получено монет (0 - монеты только от продажи)
```

### ActiveEffect
```python
user_id: int              # Внешний ключ к User
effect_type: str          # Тип эффекта (luck_boost, death_island_access...)
source_item: str          # Предмет-источник
remaining_uses: int       # Осталось использований/рейдов
expires_at: datetime      # Дата истечения (если есть)
created_at: datetime      # Дата создания
```

## Категории предметов

Все предметы хранятся в `data/items.json` в трех категориях:

### sellable (продаваемые)
Предметы, которые игрок находит в рейдах. Можно только продать за монеты.
```json
{
  "item_id": {
    "name": "Название",
    "emoji": "🪢",
    "price": 5,           # Цена продажи в монетах
    "rarity": "common",   # Редкость для шансов выпадения
    "description": "Описание"
  }
}
```

### usable (используемые)
Предметы с эффектами, которые можно активировать.
```json
{
  "item_id": {
    "name": "Название",
    "emoji": "🧪",
    "price": 150,          # Цена продажи (если есть)
    "price_stars": 10,     # Цена в звездах (для магазина)
    "effect": "repair_ship", # Тип эффекта
    "effect_value": 50,    # Значение эффекта
    "description": "Описание",
    "duration": "instant"  # Длительность (instant, next_voyage, voyages_3)
  }
}
```

### special (особые)
Редкие предметы с пассивными эффектами.
```json
{
  "item_id": {
    "name": "Название",
    "emoji": "🗺️",
    "price_stars": 5,      # Цена в звездах
    "effect": "guaranteed_chest",
    "description": "Описание",
    "duration": "next_voyage",
    "max_stack": 3
  }
}
```

## Локации

Файл `data/locations.json`:
```json
{
  "location_id": {
    "name": "Название локации",
    "description": "Описание",
    "min_level": 1,           # Минимальный уровень
    "base_time": 25,          # Базовое время (не используется)
    "loot_multiplier": 1.0,   # Множитель добычи
    "event_chance": 0.1,      # Шанс события
    "unlock_cost": 0,         # Цена открытия (не используется)
    "requires_item": "item_id", # Требуемый предмет (для острова смерти)
    "image": "file.png"       # Изображение
  }
}
```

Доступность локации определяется:
- Уровнем игрока (`min_level`)
- Наличием предмета (`requires_item`) - для острова смерти проверяется активный эффект `death_island_access`, а не сам билет

## События

Файл `data/events.json`:
```json
{
  "event_id": {
    "name": "🌊 Шторм",
    "description": "Описание",
    "chance": 60,          # Вес события (относительный)
    "min_level": 1,        # Минимальный уровень
    "options": [
      {
        "text": "Текст кнопки",
        "callback": "storm_wait",  # ID выбора
        "result": "time_double"     # Результат (для логики)
      }
    ]
  }
}
```

События выбираются случайно с учетом весов. Попугай уменьшает шанс шторма на `parrot_level * 10%`.

## Улучшения

Файл `data/upgrades.json`:

### ship (корабль)
```json
{
  "upgrade_id": {
    "name": "⛵ Новые паруса",
    "description": "Описание",
    "base_price": 100,        # Базовая цена
    "price_multiplier": 1.5,  # Множитель цены за уровень
    "effect": "time_reduction", # Тип эффекта
    "effect_per_level": 2,    # Эффект за уровень
    "effect_unit": "минут",   # Единица измерения
    "max_level": 10           # Максимальный уровень
  }
}
```

### crew (команда)
Аналогичная структура для улучшений команды.

## Магазин и платежи

### Покупка за монеты
- Улучшения корабля и команды покупаются за монеты
- Цена растет с каждым уровнем: `base_price * (price_multiplier ** current_level)`

### Покупка за звезды
- Особые и используемые предметы покупаются за Telegram Stars
- Интеграция через `answer_invoice` с валютой `XTR`
- Кнопка оплаты должна иметь `pay=True`
- После успешной оплаты предмет добавляется в инвентарь

## Инвентарь

### Категории
1. **На продажу (sellable)** - предметы из рейдов, можно продать поштучно или все сразу
2. **Используемые (usable)** - предметы с эффектами, кроме билета на остров смерти
3. **Особые (special)** - редкие предметы с пассивными эффектами

### Особенности билета на остров смерти
- Находится в категории `usable`
- Не имеет кнопки "Использовать"
- Активируется автоматически при входе на остров
- При активации создает эффект `death_island_access` с 3 использованиями
- После каждого рейда на острове счетчик уменьшается

## Плавание

### Процесс
1. Игрок выбирает локацию из списка
2. Проверяется доступность (уровень, эффекты)
3. Случайно выбирается событие (с учетом весов)
4. Если событие есть - игрок выбирает действие
5. Генерируется лут (только предметы из `sellable`)
6. Предметы добавляются в инвентарь
7. Опыт начисляется, монеты НЕ начисляются
8. Активные эффекты уменьшаются на 1

### Генерация лута
```python
def generate_loot(user_level, location_multiplier, luck_multiplier, guaranteed_chest):
    # Базовое количество: 3 предмета
    # Редкость: 60% common, 25% uncommon, 10% rare, 4% epic, 1% legendary
    # Сундук гарантирован при guaranteed_chest=True
    # Множитель удачи увеличивает шансы редких предметов
```

### Эффекты удачи
- `luck_boost` - увеличивает шансы редких предметов на 30%
- `guaranteed_chest` - гарантирует легендарный предмет

## Структура файлов

```
pirate_bot/
├── bot.py                 # Точка входа
├── config.py              # Конфигурация
├── database/
│   ├── db.py             # Подключение к БД
│   ├── models.py         # Модели SQLAlchemy
│   └── requests.py       # Запросы к БД
├── handlers/
│   └── private/
│       ├── start.py      # Старт и профиль
│       ├── voyage.py     # Плавание и события
│       ├── ship.py       # Информация о корабле
│       ├── shop.py       # Магазин и платежи
│       └── inventory.py  # Инвентарь
├── keyboards/
│   └── inline.py         # Инлайн-клавиатуры
├── game_logic/
│   ├── loot_tables.py    # Генерация лута
│   ├── events.py         # События
│   └── combat.py         # Боевая система
└── data/
    ├── items.json        # Предметы
    ├── locations.json    # Локации
    ├── events.json       # События
    └── upgrades.json     # Улучшения
```

## Правила и логика

### Монеты
- Монеты НЕ даются за рейды напрямую
- Монеты даются только за продажу предметов из категории `sellable`
- Цена продажи = `price` из `items.json`

### Опыт и уровни
- За рейд: `10 + количество_предметов * 2`
- За остров смерти: дополнительно +100 опыта
- Уровни определены в `start.py` (LEVELS)
- Прогресс отображается квадратиками 🟩 и ⬛

### Билет на остров смерти
1. Покупается за звезды в магазине
2. Лежит в инвентаре (категория usable)
3. При попытке зайти на остров предлагается активировать
4. Активация создает эффект на 3 рейда
5. После 3 рейдов эффект исчезает, нужен новый билет

### Активные эффекты
- Хранятся в таблице `active_effects`
- Уменьшаются после каждого рейда
- При достижении 0 удаляются автоматически
- Могут суммироваться (например, несколько билетов)

### Проверка доступа к острову смерти
```python
# Не по наличию билета, а по наличию эффекта!
has_access = any(
    effect.effect_type == 'death_island_access' 
    for effect in user.active_effects
)
```