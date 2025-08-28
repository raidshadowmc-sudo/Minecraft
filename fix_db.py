
#!/usr/bin/env python3
"""
Database fix script to resolve table conflicts
"""

import os
from app import app, db
from sqlalchemy import text

def fix_database():
    """Fix database table conflicts"""
    print("🔧 Fixing database conflicts...")
    
    with app.app_context():
        try:
            # Drop problematic tables if they exist
            db.session.execute(text("DROP TABLE IF EXISTS ascend_history"))
            db.session.execute(text("DROP TABLE IF EXISTS inventory_item"))
            db.session.commit()
            print("✅ Dropped conflicting tables")
            
            # Recreate all tables
            db.create_all()
            print("✅ Database tables recreated successfully")
            
        except Exception as e:
            print(f"❌ Error fixing database: {e}")
            db.session.rollback()

if __name__ == '__main__':
    fix_database()
