#!/usr/bin/env python3
"""
Скрипт для инициализации товаров в магазине Elite Squad
Добавляет роли, титулы, градиенты, темы и другие товары
"""

from app import app, db
from models import ShopItem, CustomTitle, SiteTheme, AdminCustomRole
from datetime import datetime


def create_shop_themes():
    """Создать темы для магазина"""
    themes = [
        {
            'name': 'midnight_purple',
            'display_name': 'Midnight Purple',
            'description': 'Темная фиолетовая тема с градиентами',
            'price_coins': 5000,
            'rarity': 'epic',
            'icon': '🌌'
        },
        {
            'name': 'ocean_blue',
            'display_name': 'Ocean Blue',
            'description': 'Глубокая синяя тема как океан',
            'price_coins': 3500,
            'rarity': 'rare',
            'icon': '🌊'
        },
        {
            'name': 'fire_red',
            'display_name': 'Fire Red',
            'description': 'Яркая красная тема с огненными эффектами',
            'price_coins': 4000,
            'rarity': 'epic',
            'icon': '🔥'
        },
        {
            'name': 'nature_green',
            'display_name': 'Nature Green',
            'description': 'Природная зеленая тема',
            'price_coins': 2500,
            'rarity': 'uncommon',
            'icon': '🌿'
        },
        {
            'name': 'golden_sunset',
            'display_name': 'Golden Sunset',
            'description': 'Золотая тема заката',
            'price_coins': 7500,
            'price_reputation': 50,
            'rarity': 'legendary',
            'icon': '🌅'
        },
        {
            'name': 'cyberpunk_neon',
            'display_name': 'Cyberpunk Neon',
            'description': 'Неоновая киберпанк тема',
            'price_coins': 6000,
            'price_reputation': 25,
            'rarity': 'epic',
            'icon': '⚡'
        }
    ]
    
    for theme_data in themes:
        existing = ShopItem.query.filter_by(name=theme_data['name'], category='theme').first()
        if not existing:
            shop_item = ShopItem(
                name=theme_data['name'],
                display_name=theme_data['display_name'],
                description=theme_data['description'],
                category='theme',
                price_coins=theme_data['price_coins'],
                price_reputation=theme_data.get('price_reputation', 0),
                unlock_level=theme_data.get('unlock_level', 1),
                rarity=theme_data['rarity'],
                icon=theme_data['icon'],
                is_active=True
            )
            db.session.add(shop_item)
    
    print("✅ Темы добавлены в магазин")


def create_shop_titles():
    """Создать титулы для магазина"""
    titles = [
        {
            'name': 'bedwars_master',
            'display_name': 'Bedwars Master',
            'description': 'Титул для мастеров Bedwars',
            'color': '#ff6b6b',
            'price_coins': 2000,
            'unlock_level': 10,
            'rarity': 'rare',
            'icon': '⚔️'
        },
        {
            'name': 'pvp_legend',
            'display_name': 'PvP Legend',
            'description': 'Легендарный PvP боец',
            'color': '#4ecdc4',
            'price_coins': 3500,
            'unlock_level': 15,
            'rarity': 'epic',
            'icon': '🗡️'
        },
        {
            'name': 'elite_player',
            'display_name': 'Elite Player',
            'description': 'Элитный игрок сервера',
            'color': '#45b7d1',
            'price_coins': 5000,
            'price_reputation': 30,
            'unlock_level': 20,
            'rarity': 'epic',
            'icon': '👑'
        },
        {
            'name': 'discord_champion',
            'display_name': 'Discord Champion',
            'description': 'Чемпион Discord сообщества',
            'color': '#7289da',
            'price_coins': 1500,
            'unlock_level': 5,
            'rarity': 'uncommon',
            'icon': '🎮'
        },
        {
            'name': 'server_veteran',
            'display_name': 'Server Veteran',
            'description': 'Ветеран сервера',
            'color': '#f39c12',
            'price_coins': 4000,
            'price_reputation': 50,
            'unlock_level': 25,
            'rarity': 'legendary',
            'icon': '🏆'
        },
        {
            'name': 'grinder',
            'display_name': 'The Grinder',
            'description': 'Неутомимый фармер',
            'color': '#9b59b6',
            'price_coins': 2500,
            'unlock_level': 12,
            'rarity': 'rare',
            'icon': '⛏️'
        }
    ]
    
    for title_data in titles:
        # Создать CustomTitle если не существует
        custom_title = CustomTitle.query.filter_by(name=title_data['name']).first()
        if not custom_title:
            custom_title = CustomTitle(
                name=title_data['name'],
                display_name=title_data['display_name'],
                description=title_data['description'],
                color=title_data['color']
            )
            db.session.add(custom_title)
            db.session.flush()  # Чтобы получить ID
        
        # Создать ShopItem для титула
        existing = ShopItem.query.filter_by(name=title_data['name'], category='title').first()
        if not existing:
            shop_item = ShopItem(
                name=title_data['name'],
                display_name=title_data['display_name'],
                description=title_data['description'],
                category='title',
                price_coins=title_data['price_coins'],
                price_reputation=title_data.get('price_reputation', 0),
                unlock_level=title_data['unlock_level'],
                rarity=title_data['rarity'],
                icon=title_data['icon'],
                is_active=True
            )
            db.session.add(shop_item)
    
    print("✅ Титулы добавлены в магазин")


def create_shop_gradients():
    """Создать градиенты для магазина"""
    gradients = [
        {
            'name': 'rainbow_gradient',
            'display_name': 'Rainbow Gradient',
            'description': 'Радужный градиент для ника',
            'price_coins': 3000,
            'unlock_level': 8,
            'rarity': 'rare',
            'icon': '🌈'
        },
        {
            'name': 'fire_gradient',
            'display_name': 'Fire Gradient',
            'description': 'Огненный градиент красно-оранжевый',
            'price_coins': 2500,
            'unlock_level': 6,
            'rarity': 'uncommon',
            'icon': '🔥'
        },
        {
            'name': 'ocean_gradient',
            'display_name': 'Ocean Gradient',
            'description': 'Океанский бирюзово-синий градиент',
            'price_coins': 2500,
            'unlock_level': 6,
            'rarity': 'uncommon',
            'icon': '🌊'
        },
        {
            'name': 'royal_gradient',
            'display_name': 'Royal Gradient',
            'description': 'Королевский фиолетово-золотой градиент',
            'price_coins': 4500,
            'price_reputation': 20,
            'unlock_level': 15,
            'rarity': 'epic',
            'icon': '👑'
        },
        {
            'name': 'galaxy_gradient',
            'display_name': 'Galaxy Gradient',
            'description': 'Галактический градиент с звездами',
            'price_coins': 6000,
            'price_reputation': 35,
            'unlock_level': 20,
            'rarity': 'legendary',
            'icon': '🌌'
        },
        {
            'name': 'toxic_gradient',
            'display_name': 'Toxic Gradient',
            'description': 'Токсичный зелено-желтый градиент',
            'price_coins': 3500,
            'unlock_level': 10,
            'rarity': 'rare',
            'icon': '☢️'
        }
    ]
    
    for gradient_data in gradients:
        existing = ShopItem.query.filter_by(name=gradient_data['name'], category='gradient').first()
        if not existing:
            shop_item = ShopItem(
                name=gradient_data['name'],
                display_name=gradient_data['display_name'],
                description=gradient_data['description'],
                category='gradient',
                price_coins=gradient_data['price_coins'],
                price_reputation=gradient_data.get('price_reputation', 0),
                unlock_level=gradient_data['unlock_level'],
                rarity=gradient_data['rarity'],
                icon=gradient_data['icon'],
                is_active=True
            )
            db.session.add(shop_item)
    
    print("✅ Градиенты добавлены в магазин")


def create_shop_roles():
    """Создать роли для магазина"""
    roles = [
        {
            'name': 'vip_member',
            'display_name': 'VIP Member',
            'description': 'VIP статус в Discord',
            'color': '#f1c40f',
            'price_coins': 8000,
            'price_reputation': 40,
            'unlock_level': 18,
            'rarity': 'epic',
            'icon': '💎'
        },
        {
            'name': 'elite_supporter',
            'display_name': 'Elite Supporter',
            'description': 'Поддержка Elite Squad',
            'color': '#e74c3c',
            'price_coins': 5000,
            'price_reputation': 25,
            'unlock_level': 12,
            'rarity': 'rare',
            'icon': '❤️'
        },
        {
            'name': 'content_creator',
            'display_name': 'Content Creator',
            'description': 'Роль для создателей контента',
            'color': '#9b59b6',
            'price_coins': 6000,
            'price_reputation': 30,
            'unlock_level': 15,
            'rarity': 'epic',
            'icon': '📹'
        },
        {
            'name': 'event_winner',
            'display_name': 'Event Winner',
            'description': 'Победитель мероприятий',
            'color': '#2ecc71',
            'price_coins': 4000,
            'unlock_level': 10,
            'rarity': 'rare',
            'icon': '🏆'
        },
        {
            'name': 'squad_legend',
            'display_name': 'Squad Legend',
            'description': 'Легенда Elite Squad',
            'color': '#e67e22',
            'price_coins': 12000,
            'price_reputation': 75,
            'unlock_level': 30,
            'rarity': 'legendary',
            'icon': '⭐'
        }
    ]
    
    for role_data in roles:
        # Создать AdminCustomRole если не существует
        custom_role = AdminCustomRole.query.filter_by(name=role_data['name']).first()
        if not custom_role:
            custom_role = AdminCustomRole(
                name=role_data['name'],
                color=role_data['color']
            )
            db.session.add(custom_role)
            db.session.flush()
        
        # Создать ShopItem для роли
        existing = ShopItem.query.filter_by(name=role_data['name'], category='custom_role').first()
        if not existing:
            shop_item = ShopItem(
                name=role_data['name'],
                display_name=role_data['display_name'],
                description=role_data['description'],
                category='custom_role',
                price_coins=role_data['price_coins'],
                price_reputation=role_data['price_reputation'],
                unlock_level=role_data['unlock_level'],
                rarity=role_data['rarity'],
                icon=role_data['icon'],
                is_active=True
            )
            db.session.add(shop_item)
    
    print("✅ Роли добавлены в магазин")


def create_shop_boosters():
    """Создать бустеры для магазина"""
    boosters = [
        {
            'name': 'xp_booster_1h',
            'display_name': 'XP Booster (1 час)',
            'description': '+50% опыта на 1 час',
            'price_coins': 1000,
            'unlock_level': 1,
            'rarity': 'common',
            'icon': '⚡'
        },
        {
            'name': 'xp_booster_24h',
            'display_name': 'XP Booster (24 часа)',
            'description': '+50% опыта на 24 часа',
            'price_coins': 5000,
            'unlock_level': 5,
            'rarity': 'uncommon',
            'icon': '🚀'
        },
        {
            'name': 'coin_booster_1h',
            'display_name': 'Coin Booster (1 час)',
            'description': '+25% койнов на 1 час',
            'price_coins': 800,
            'unlock_level': 1,
            'rarity': 'common',
            'icon': '💰'
        },
        {
            'name': 'super_booster_1h',
            'display_name': 'Super Booster (1 час)',
            'description': '+75% всего на 1 час',
            'price_coins': 2500,
            'price_reputation': 10,
            'unlock_level': 8,
            'rarity': 'rare',
            'icon': '💫'
        },
        {
            'name': 'legendary_booster',
            'display_name': 'Legendary Booster (7 дней)',
            'description': '+100% всего на 7 дней',
            'price_coins': 15000,
            'price_reputation': 100,
            'unlock_level': 25,
            'rarity': 'legendary',
            'icon': '🌟'
        }
    ]
    
    for booster_data in boosters:
        existing = ShopItem.query.filter_by(name=booster_data['name'], category='booster').first()
        if not existing:
            shop_item = ShopItem(
                name=booster_data['name'],
                display_name=booster_data['display_name'],
                description=booster_data['description'],
                category='booster',
                price_coins=booster_data['price_coins'],
                price_reputation=booster_data.get('price_reputation', 0),
                unlock_level=booster_data['unlock_level'],
                rarity=booster_data['rarity'],
                icon=booster_data['icon'],
                is_active=True
            )
            db.session.add(shop_item)
    
    print("✅ Бустеры добавлены в магазин")


def create_shop_special_items():
    """Создать специальные товары"""
    special_items = [
        {
            'name': 'emoji_slot_extra',
            'display_name': 'Дополнительный слот эмодзи',
            'description': 'Дополнительный слот для пользовательского эмодзи в Discord',
            'category': 'emoji_slot',
            'price_coins': 3000,
            'price_reputation': 15,
            'unlock_level': 10,
            'rarity': 'rare',
            'icon': '😀'
        },
        {
            'name': 'name_color_change',
            'display_name': 'Смена цвета ника',
            'description': 'Возможность изменить цвет ника на сайте',
            'category': 'customization',
            'price_coins': 2000,
            'unlock_level': 7,
            'rarity': 'uncommon',
            'icon': '🎨'
        },
        {
            'name': 'priority_support',
            'display_name': 'Приоритетная поддержка',
            'description': 'Приоритетное рассмотрение обращений',
            'category': 'service',
            'price_coins': 7500,
            'price_reputation': 50,
            'unlock_level': 20,
            'rarity': 'epic',
            'icon': '🎫'
        }
    ]
    
    for item_data in special_items:
        existing = ShopItem.query.filter_by(name=item_data['name'], category=item_data['category']).first()
        if not existing:
            shop_item = ShopItem(
                name=item_data['name'],
                display_name=item_data['display_name'],
                description=item_data['description'],
                category=item_data['category'],
                price_coins=item_data['price_coins'],
                price_reputation=item_data.get('price_reputation', 0),
                unlock_level=item_data['unlock_level'],
                rarity=item_data['rarity'],
                icon=item_data['icon'],
                is_active=True
            )
            db.session.add(shop_item)
    
    print("✅ Специальные товары добавлены в магазин")


def main():
    """Основная функция инициализации товаров"""
    with app.app_context():
        print("🛍️ Инициализация товаров магазина Elite Squad...")
        
        try:
            # Создаем все категории товаров
            create_shop_themes()
            create_shop_titles()
            create_shop_gradients()
            create_shop_roles()
            create_shop_boosters()
            create_shop_special_items()
            
            # Сохраняем изменения
            db.session.commit()
            print("✅ Все товары успешно добавлены в магазин!")
            
            # Статистика
            total_items = ShopItem.query.filter_by(is_active=True).count()
            print(f"📊 Всего активных товаров в магазине: {total_items}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Ошибка при инициализации товаров: {e}")


if __name__ == "__main__":
    main()