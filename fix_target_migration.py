
#!/usr/bin/env python3
"""
Alternative target table migration script
"""

from app import app, db
from sqlalchemy import text
import os

def fix_target_table():
    """Fix target table by adding missing column"""
    print("🔧 Fixing target table...")
    
    try:
        with app.app_context():
            database_url = os.environ.get('DATABASE_URL', '')
            is_postgresql = database_url.startswith('postgresql://') or database_url.startswith('postgres://')
            
            try:
                if is_postgresql:
                    print("📊 PostgreSQL - Adding last_updated column...")
                    # Try to add column
                    db.session.execute(text("""
                        ALTER TABLE target 
                        ADD COLUMN IF NOT EXISTS last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    """))
                    
                    # Update existing records
                    db.session.execute(text("""
                        UPDATE target 
                        SET last_updated = COALESCE(date_added, CURRENT_TIMESTAMP)
                        WHERE last_updated IS NULL
                    """))
                    
                else:
                    print("📊 SQLite - Adding last_updated column...")
                    # Check if column exists
                    result = db.session.execute(text("PRAGMA table_info(target)"))
                    columns = [row[1] for row in result.fetchall()]
                    
                    if 'last_updated' not in columns:
                        db.session.execute(text("""
                            ALTER TABLE target 
                            ADD COLUMN last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                        """))
                        
                        # Update existing records
                        db.session.execute(text("""
                            UPDATE target 
                            SET last_updated = COALESCE(date_added, datetime('now'))
                            WHERE last_updated IS NULL
                        """))
                
                db.session.commit()
                print("✅ Target table fixed successfully!")
                return True
                
            except Exception as e:
                print(f"⚠️ Migration error: {e}")
                db.session.rollback()
                return False
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    fix_target_table()
