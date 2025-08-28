
#!/usr/bin/env python3
"""
Migration script to create candidates tables
"""

from app import app, db
from models import Candidate, CandidateComment, CandidateReaction

def migrate_candidates():
    """Create candidates tables"""
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            
            print("✅ Candidate tables created successfully!")
            print("📋 Created tables:")
            print("  - candidate")
            print("  - candidate_comment") 
            print("  - candidate_reaction")
            
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            return False
            
        return True

if __name__ == '__main__':
    print("🚀 Creating candidates tables...")
    if migrate_candidates():
        print("✅ Migration completed successfully!")
    else:
        print("❌ Migration failed!")
