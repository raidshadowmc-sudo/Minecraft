
#!/usr/bin/env python3
"""
Complete database migration script to add missing columns to existing tables
"""

from app import app, db
import sqlite3
import os
from sqlalchemy import text, inspect
import time

def migrate_database():
    """Migrate database to add missing columns"""
    print("🚀 Starting complete database migration...")

    try:
        with app.app_context():
            # Get database file path
            db_path = app.config.get('SQLALCHEMY_DATABASE_URI', '').replace('sqlite:///', '')
            if not db_path:
                db_path = 'instance/bedwars_leaderboard.db'
            
            print(f"📍 Database path: {db_path}")
            
            # Check existing columns in player table
            cursor = db.session.execute(text("PRAGMA table_info(player)"))
            existing_columns = [row[1] for row in cursor.fetchall()]
            print(f"🔍 Found {len(existing_columns)} existing columns")

            # Define all missing columns that need to be added
            new_columns = [
                # KitPVP Stats
                ("kitpvp_kills", "INTEGER DEFAULT 0 NOT NULL"),
                ("kitpvp_deaths", "INTEGER DEFAULT 0 NOT NULL"),
                ("kitpvp_games", "INTEGER DEFAULT 0 NOT NULL"),
                
                # SkyWars Stats
                ("skywars_wins", "INTEGER DEFAULT 0 NOT NULL"),
                ("skywars_solo_wins", "INTEGER DEFAULT 0 NOT NULL"),
                ("skywars_team_wins", "INTEGER DEFAULT 0 NOT NULL"),
                ("skywars_mega_wins", "INTEGER DEFAULT 0 NOT NULL"),
                ("skywars_mini_wins", "INTEGER DEFAULT 0 NOT NULL"),
                ("skywars_ranked_wins", "INTEGER DEFAULT 0 NOT NULL"),
                ("skywars_kills", "INTEGER DEFAULT 0 NOT NULL"),
                ("skywars_solo_kills", "INTEGER DEFAULT 0 NOT NULL"),
                ("skywars_team_kills", "INTEGER DEFAULT 0 NOT NULL"),
                ("skywars_mega_kills", "INTEGER DEFAULT 0 NOT NULL"),
                ("skywars_mini_kills", "INTEGER DEFAULT 0 NOT NULL"),
                ("skywars_ranked_kills", "INTEGER DEFAULT 0 NOT NULL"),
                
                # Sumo Stats
                ("sumo_games_played", "INTEGER DEFAULT 0 NOT NULL"),
                ("sumo_monthly_games", "INTEGER DEFAULT 0 NOT NULL"),
                ("sumo_daily_games", "INTEGER DEFAULT 0 NOT NULL"),
                ("sumo_deaths", "INTEGER DEFAULT 0 NOT NULL"),
                ("sumo_monthly_deaths", "INTEGER DEFAULT 0 NOT NULL"),
                ("sumo_daily_deaths", "INTEGER DEFAULT 0 NOT NULL"),
                ("sumo_wins", "INTEGER DEFAULT 0 NOT NULL"),
                ("sumo_monthly_wins", "INTEGER DEFAULT 0 NOT NULL"),
                ("sumo_daily_wins", "INTEGER DEFAULT 0 NOT NULL"),
                ("sumo_losses", "INTEGER DEFAULT 0 NOT NULL"),
                ("sumo_monthly_losses", "INTEGER DEFAULT 0 NOT NULL"),
                ("sumo_daily_losses", "INTEGER DEFAULT 0 NOT NULL"),
                ("sumo_kills", "INTEGER DEFAULT 0 NOT NULL"),
                ("sumo_monthly_kills", "INTEGER DEFAULT 0 NOT NULL"),
                ("sumo_daily_kills", "INTEGER DEFAULT 0 NOT NULL"),
                ("sumo_winstreak", "INTEGER DEFAULT 0 NOT NULL"),
                ("sumo_monthly_winstreak", "INTEGER DEFAULT 0 NOT NULL"),
                ("sumo_daily_winstreak", "INTEGER DEFAULT 0 NOT NULL"),
                ("sumo_best_winstreak", "INTEGER DEFAULT 0 NOT NULL"),
                ("sumo_monthly_best_winstreak", "INTEGER DEFAULT 0 NOT NULL"),
                ("sumo_daily_best_winstreak", "INTEGER DEFAULT 0 NOT NULL"),
                
                # Enhanced statistics
                ("iron_collected", "INTEGER DEFAULT 0 NOT NULL"),
                ("gold_collected", "INTEGER DEFAULT 0 NOT NULL"),
                ("diamond_collected", "INTEGER DEFAULT 0 NOT NULL"),
                ("emerald_collected", "INTEGER DEFAULT 0 NOT NULL"),
                ("items_purchased", "INTEGER DEFAULT 0 NOT NULL"),
                
                # Minecraft skin system
                ("skin_url", "VARCHAR(255)"),
                ("skin_type", "VARCHAR(10) DEFAULT 'auto' NOT NULL"),
                ("is_premium", "BOOLEAN DEFAULT FALSE NOT NULL"),
                
                # Personal profile information
                ("real_name", "VARCHAR(100)"),
                ("bio", "TEXT"),
                ("discord_tag", "VARCHAR(50)"),
                ("youtube_channel", "VARCHAR(100)"),
                ("twitch_channel", "VARCHAR(100)"),
                ("favorite_server", "VARCHAR(100)"),
                ("favorite_map", "VARCHAR(100)"),
                ("preferred_gamemode", "VARCHAR(50)"),
                ("profile_banner_color", "VARCHAR(7) DEFAULT '#3498db'"),
                ("profile_is_public", "BOOLEAN DEFAULT TRUE NOT NULL"),
                ("custom_status", "VARCHAR(100)"),
                ("location", "VARCHAR(100)"),
                ("birthday", "DATE"),
                
                # Custom profile customization
                ("custom_avatar_url", "VARCHAR(255)"),
                ("custom_banner_url", "VARCHAR(255)"),
                ("banner_is_animated", "BOOLEAN DEFAULT FALSE NOT NULL"),
                
                # Extended social networks
                ("social_networks", "TEXT"),
                
                # Profile section backgrounds
                ("stats_section_color", "VARCHAR(7) DEFAULT '#343a40'"),
                ("info_section_color", "VARCHAR(7) DEFAULT '#343a40'"),
                ("social_section_color", "VARCHAR(7) DEFAULT '#343a40'"),
                ("prefs_section_color", "VARCHAR(7) DEFAULT '#343a40'"),
                
                # Password system
                ("password_hash", "VARCHAR(255)"),
                ("has_password", "BOOLEAN DEFAULT FALSE NOT NULL"),
                
                # Theme system
                ("selected_theme_id", "INTEGER"),
                
                # Leaderboard customization
                ("leaderboard_name_color", "VARCHAR(7) DEFAULT '#ffffff'"),
                ("leaderboard_stats_color", "VARCHAR(7) DEFAULT '#ffffff'"),
                ("leaderboard_use_gradient", "BOOLEAN DEFAULT FALSE NOT NULL"),
                ("leaderboard_gradient_start", "VARCHAR(7) DEFAULT '#ff6b35'"),
                ("leaderboard_gradient_end", "VARCHAR(7) DEFAULT '#f7931e'"),
                ("leaderboard_gradient_animated", "BOOLEAN DEFAULT FALSE NOT NULL"),
                
                # Inventory system
                ("inventory_data", "TEXT"),
                
                # Economy system fields
                ("coins", "INTEGER DEFAULT 0 NOT NULL"),
                ("reputation", "INTEGER DEFAULT 0 NOT NULL"),
                ("karma", "INTEGER DEFAULT 0 NOT NULL"),
                
                # Custom role system
                ("custom_role", "VARCHAR(100)"),
                ("custom_role_color", "VARCHAR(7)"),
                ("custom_role_gradient", "TEXT"),
                ("custom_role_emoji", "VARCHAR(10)"),
                ("custom_role_animated", "BOOLEAN DEFAULT FALSE NOT NULL"),
                ("custom_role_purchased", "BOOLEAN DEFAULT FALSE NOT NULL"),
                ("custom_emoji_slots", "INTEGER DEFAULT 0 NOT NULL"),
                ("custom_role_tier", "VARCHAR(50)"),
            ]

            # Add missing columns
            columns_added = 0
            for column_name, column_def in new_columns:
                if column_name not in existing_columns:
                    try:
                        sql = f"ALTER TABLE player ADD COLUMN {column_name} {column_def}"
                        db.session.execute(text(sql))
                        print(f"✅ Added column: {column_name}")
                        columns_added += 1
                    except Exception as e:
                        print(f"⚠️  Failed to add column {column_name}: {e}")

            # Create indexes for performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_player_karma ON player(karma)",
                "CREATE INDEX IF NOT EXISTS idx_player_kitpvp_kills ON player(kitpvp_kills)",
                "CREATE INDEX IF NOT EXISTS idx_player_skywars_wins ON player(skywars_wins)",
                "CREATE INDEX IF NOT EXISTS idx_player_sumo_wins ON player(sumo_wins)",
            ]

            for index_sql in indexes:
                try:
                    db.session.execute(text(index_sql))
                except Exception as e:
                    print(f"⚠️  Index creation warning: {e}")

            # Commit all changes
            db.session.commit()
            
            print(f"✅ Database migration completed successfully!")
            print(f"📊 Added {columns_added} new columns")
            
            # Create all other tables that might be missing
            db.create_all()
            print("✅ All tables created/updated")

    except Exception as e:
        print(f"❌ Error during migration: {e}")
        db.session.rollback()
        return False

    return True

if __name__ == '__main__':
    print("🚀 Starting database migration...")
    if migrate_database():
        print("✅ Migration completed successfully!")
    else:
        print("❌ Migration failed!")
