#!/usr/bin/env python3
"""
PostgreSQL database migration and initialization script
"""

from app import app, db
from sqlalchemy import text, inspect
import time

def migrate_postgresql():
    """Migrate PostgreSQL database and initialize data"""
    print("🚀 Starting PostgreSQL migration and initialization...")

    try:
        with app.app_context():
            # Create all missing tables
            db.create_all()
            print("✅ All tables created/updated")
            
            # Initialize default themes with Minecraft-style names
            init_minecraft_themes()
            
            # Initialize demo data
            init_demo_data()
            
            # Initialize default achievements  
            init_achievements()
            
            # Initialize default quests
            init_quests()
            
            # Initialize default shop items
            init_shop_items()
            
            print("✅ PostgreSQL migration completed successfully!")

    except Exception as e:
        print(f"❌ Error during migration: {e}")
        db.session.rollback()
        return False

    return True

def init_minecraft_themes():
    """Initialize Minecraft-themed site themes"""
    try:
        from models import SiteTheme
        
        # Check if themes already exist
        if SiteTheme.query.count() > 0:
            print("🎨 Themes already exist, updating...")
            # Update existing themes with Minecraft names
            themes_to_update = [
                ("default_dark", "Эссенция Энда", "Тёмная тема с энергией Края"),
                ("nether_theme", "Пламя Нижнего мира", "Огненная тема в стиле Незера"),
                ("ocean_theme", "Глубины Океана", "Прохладная водная тема"),
                ("forest_theme", "Лесные недра", "Зелёная природная тема"),
                ("crystal_theme", "Кристальные пещеры", "Блестящая тема драгоценных камней"),
            ]
            
            for old_name, new_display_name, new_description in themes_to_update:
                theme = SiteTheme.query.filter_by(name=old_name).first()
                if theme:
                    theme.display_name = new_display_name
                    theme.description = new_description
        else:
            # Create new Minecraft-style themes
            themes = [
                SiteTheme(
                    name='ender_essence',
                    display_name='Эссенция Энда',
                    description='Тёмная тема с энергией Края и фиолетовыми акцентами',
                    primary_color='#8b5cf6',
                    secondary_color='#a855f7',
                    background_color='#0f0f23',
                    card_background='#1e1b4b',
                    text_color='#e2e8f0',
                    accent_color='#8b5cf6',
                    is_default=True
                ),
                SiteTheme(
                    name='nether_flame',
                    display_name='Пламя Нижнего мира',
                    description='Огненная тема в стиле Незера с красными акцентами',
                    primary_color='#dc2626',
                    secondary_color='#ef4444',
                    background_color='#1f1f1f',
                    card_background='#450a0a',
                    text_color='#fef2f2',
                    accent_color='#dc2626'
                ),
                SiteTheme(
                    name='ocean_depths',
                    display_name='Глубины Океана',
                    description='Прохладная водная тема с синими оттенками',
                    primary_color='#0ea5e9',
                    secondary_color='#0284c7',
                    background_color='#0c1426',
                    card_background='#1e3a8a',
                    text_color='#dbeafe',
                    accent_color='#0ea5e9'
                ),
                SiteTheme(
                    name='forest_essence',
                    display_name='Лесные недра',
                    description='Зелёная природная тема с земными оттенками',
                    primary_color='#16a34a',
                    secondary_color='#22c55e',
                    background_color='#0f1f0f',
                    card_background='#14532d',
                    text_color='#dcfce7',
                    accent_color='#16a34a'
                ),
                SiteTheme(
                    name='crystal_caves',
                    display_name='Кристальные пещеры',
                    description='Блестящая тема с оттенками драгоценных камней',
                    primary_color='#06b6d4',
                    secondary_color='#0891b2',
                    background_color='#164e63',
                    card_background='#0e7490',
                    text_color='#cffafe',
                    accent_color='#06b6d4'
                )
            ]
            
            for theme in themes:
                db.session.add(theme)
        
        db.session.commit()
        print("✅ Minecraft themes initialized")
        
    except Exception as e:
        print(f"⚠️ Error initializing themes: {e}")

def init_demo_data():
    """Initialize demo players"""
    try:
        from models import Player
        
        # Create demo player if none exist
        if Player.query.count() == 0:
            demo_player = Player(
                nickname='SmoK3_FuRY',
                kills=1250,
                final_kills=890,
                deaths=520,
                final_deaths=150,
                beds_broken=680,
                games_played=420,
                wins=315,
                experience=89000,
                coins=5000,
                reputation=1500,
                karma=750,
                role='Владелец',
                custom_role='👑 Основатель',
                custom_role_color='#ffd700',
                profile_is_public=True,
                bio='Основатель Elite Squad'
            )
            db.session.add(demo_player)
            db.session.commit()
            print("✅ Demo player created")
        else:
            print("✅ Players already exist")
            
    except Exception as e:
        print(f"⚠️ Error creating demo data: {e}")

def init_achievements():
    """Initialize default achievements"""
    try:
        from models import Achievement
        
        if Achievement.query.count() == 0:
            achievements = [
                Achievement(
                    name="first_kill",
                    display_name="Первая кровь",
                    description="Получите своё первое убийство",
                    icon="fas fa-sword",
                    rarity="common",
                    coins_reward=50,
                    reputation_reward=10
                ),
                Achievement(
                    name="bed_destroyer", 
                    display_name="Разрушитель кроватей",
                    description="Сломайте 100 кроватей",
                    icon="fas fa-bed",
                    rarity="rare",
                    coins_reward=500,
                    reputation_reward=100
                ),
                Achievement(
                    name="legend",
                    display_name="Легенда",
                    description="Достигните 50 уровня",
                    icon="fas fa-crown",
                    rarity="legendary",
                    coins_reward=2000,
                    reputation_reward=500
                )
            ]
            
            for achievement in achievements:
                db.session.add(achievement)
            
            db.session.commit()
            print("✅ Achievements initialized")
            
    except Exception as e:
        print(f"⚠️ Error initializing achievements: {e}")

def init_quests():
    """Initialize default quests"""
    try:
        from models import Quest
        from datetime import datetime, timedelta
        
        if Quest.query.count() == 0:
            quests = [
                Quest(
                    name="daily_wins",
                    display_name="Ежедневные победы",
                    description="Выиграйте 5 игр",
                    quest_type="daily",
                    target_value=5,
                    coins_reward=100,
                    reputation_reward=25,
                    expires_at=datetime.utcnow() + timedelta(days=1)
                ),
                Quest(
                    name="weekly_beds",
                    display_name="Недельный разрушитель",
                    description="Сломайте 50 кроватей за неделю",
                    quest_type="weekly", 
                    target_value=50,
                    coins_reward=500,
                    reputation_reward=100,
                    expires_at=datetime.utcnow() + timedelta(weeks=1)
                )
            ]
            
            for quest in quests:
                db.session.add(quest)
            
            db.session.commit()
            print("✅ Quests initialized")
            
    except Exception as e:
        print(f"⚠️ Error initializing quests: {e}")

def init_shop_items():
    """Initialize default shop items"""
    try:
        from models import ShopItem
        
        if ShopItem.query.count() == 0:
            items = [
                ShopItem(
                    name="custom_role_color",
                    display_name="Цветная роль",
                    description="Настройте цвет своей роли",
                    price=1000,
                    currency="coins",
                    item_type="cosmetic",
                    rarity="rare"
                ),
                ShopItem(
                    name="profile_theme",
                    display_name="Тема профиля",
                    description="Уникальная тема для профиля",
                    price=2000,
                    currency="coins", 
                    item_type="cosmetic",
                    rarity="epic"
                )
            ]
            
            for item in items:
                db.session.add(item)
            
            db.session.commit()
            print("✅ Shop items initialized")
            
    except Exception as e:
        print(f"⚠️ Error initializing shop items: {e}")

if __name__ == '__main__':
    print("🚀 Starting PostgreSQL migration...")
    if migrate_postgresql():
        print("✅ Migration completed successfully!")
    else:
        print("❌ Migration failed!")