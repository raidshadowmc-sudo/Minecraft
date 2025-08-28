
#!/usr/bin/env python3
"""
Database check script to verify migration
"""

from app import app, db
from sqlalchemy import text

def check_database():
    """Check database schema and tables"""
    print("🔍 Checking database schema...")

    with app.app_context():
        try:
            # Check player table columns
            cursor = db.session.execute(text("PRAGMA table_info(player)"))
            columns = [row[1] for row in cursor.fetchall()]
            
            print(f"📊 Player table has {len(columns)} columns")
            
            # Check for key columns
            required_columns = [
                'kitpvp_kills', 'kitpvp_deaths', 'kitpvp_games',
                'skywars_wins', 'skywars_kills', 
                'sumo_games_played', 'sumo_wins', 'sumo_kills',
                'karma', 'coins', 'reputation'
            ]
            
            missing_columns = []
            for col in required_columns:
                if col not in columns:
                    missing_columns.append(col)
            
            if missing_columns:
                print(f"❌ Missing columns: {missing_columns}")
                return False
            else:
                print("✅ All required columns present!")
            
            # Test basic query
            player_count = db.session.execute(text("SELECT COUNT(*) FROM player")).scalar()
            print(f"👥 Players in database: {player_count}")
            
            # Check other tables
            tables = ['quest', 'achievement', 'ascend_data', 'target_list', 'candidate']
            for table in tables:
                try:
                    count = db.session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    print(f"📋 {table}: {count} records")
                except Exception as e:
                    print(f"⚠️  Table {table}: {e}")
            
            print("✅ Database check completed!")
            return True
            
        except Exception as e:
            print(f"❌ Database check failed: {e}")
            return False

if __name__ == '__main__':
    check_database()
