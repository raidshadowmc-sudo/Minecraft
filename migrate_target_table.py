#!/usr/bin/env python3
"""
Target table migration script to add missing last_updated column
"""

from app import app, db
from sqlalchemy import text
import os

def migrate_target_table():
    """Add missing last_updated column to target table"""
    print("🚀 Starting target table migration...")

    try:
        with app.app_context():
            # Check if we're using PostgreSQL or SQLite
            database_url = os.environ.get('DATABASE_URL', '')
            is_postgresql = database_url.startswith('postgresql://') or database_url.startswith('postgres://')

            if is_postgresql:
                print("📊 Detected PostgreSQL database")
                try:
                    # Check if column exists
                    result = db.session.execute(text("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name='target' AND column_name='last_updated'
                    """))

                    if not result.fetchone():
                        print("➕ Adding last_updated column...")
                        # Add the missing column
                        db.session.execute(text("""
                            ALTER TABLE target 
                            ADD COLUMN last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        """))

                        # Set last_updated to date_added for existing records
                        db.session.execute(text("""
                            UPDATE target 
                            SET last_updated = COALESCE(date_added, CURRENT_TIMESTAMP)
                        """))

                        print("✅ Added last_updated column to target table (PostgreSQL)")
                    else:
                        print("ℹ️ Column last_updated already exists")

                except Exception as e:
                    print(f"⚠️ PostgreSQL migration error: {e}")
                    # If there's an error, try to rollback and continue
                    db.session.rollback()

            else:
                print("📊 Detected SQLite database")
                try:
                    # Check if column exists in SQLite
                    result = db.session.execute(text("PRAGMA table_info(target)"))
                    columns = [row[1] for row in result.fetchall()]

                    if 'last_updated' not in columns:
                        print("➕ Adding last_updated column...")
                        db.session.execute(text("""
                            ALTER TABLE target 
                            ADD COLUMN last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                        """))

                        # Set last_updated to date_added for existing records
                        db.session.execute(text("""
                            UPDATE target 
                            SET last_updated = COALESCE(date_added, datetime('now'))
                        """))

                        print("✅ Added last_updated column to target table (SQLite)")
                    else:
                        print("ℹ️ Column last_updated already exists")

                except Exception as e:
                    print(f"⚠️ SQLite migration error: {e}")
                    # If there's an error, try to rollback and continue
                    db.session.rollback()

            # Try to commit changes
            try:
                db.session.commit()
                print("✅ Target table migration completed successfully!")
                return True
            except Exception as commit_error:
                print(f"❌ Error committing changes: {commit_error}")
                db.session.rollback()
                return False

    except Exception as e:
        print(f"❌ Error during target table migration: {e}")
        try:
            db.session.rollback()
        except:
            pass
        return False

def verify_migration():
    """Verify that the migration was successful"""
    print("🔍 Verifying migration...")

    try:
        with app.app_context():
            # Try to query the target table with last_updated column
            result = db.session.execute(text("""
                SELECT id, nickname, last_updated 
                FROM target 
                LIMIT 1
            """))

            row = result.fetchone()
            if row:
                print("✅ Migration verification successful - can query last_updated column")
                print(f"   Sample record: ID={row[0]}, Nickname={row[1]}, LastUpdated={row[2]}")
            else:
                print("ℹ️ Migration successful but no records found in target table")

            return True

    except Exception as e:
        print(f"❌ Migration verification failed: {e}")
        return False

if __name__ == '__main__':
    print("🚀 Starting target table migration...")

    # Run migration
    migration_success = migrate_target_table()

    if migration_success:
        # Verify migration
        verification_success = verify_migration()

        if verification_success:
            print("🎉 Migration completed and verified successfully!")
        else:
            print("⚠️ Migration completed but verification failed")
    else:
        print("❌ Migration failed!")

    print("📝 Migration process finished.")