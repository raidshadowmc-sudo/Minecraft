import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging based on environment
log_level = logging.DEBUG if os.environ.get('FLASK_ENV') == 'development' else logging.INFO
logging.basicConfig(
    level=log_level,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log') if os.environ.get('FLASK_ENV') == 'production' else logging.NullHandler()
    ]
)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
database_url = os.environ.get("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url or f"sqlite:///{os.path.abspath('instance/bedwars_leaderboard.db')}"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

with app.app_context():
    # Import models and routes
    import models
    import routes
    import api_routes
    
    # Register translation filter
    from translations import register_translation_filter
    register_translation_filter(app)
    
    # Create all tables
    db.create_all()
    
    # Initialize default data
    try:
        from models import (Player, Quest, Achievement, CustomTitle, GradientTheme, 
                           SiteTheme, ShopItem, Badge, GameMode)
        
        # Create default quests
        if Quest.query.count() == 0:
            Quest.create_default_quests()
        
        # Create default achievements
        if Achievement.query.count() == 0:
            Achievement.create_default_achievements()
        
        # Create default titles
        if CustomTitle.query.count() == 0:
            CustomTitle.create_default_titles()
        
        # Create default gradient themes
        if GradientTheme.query.count() == 0:
            GradientTheme.create_default_themes()
        
        # Create default site themes
        if SiteTheme.query.count() == 0:
            SiteTheme.create_default_themes()
        
        # Create default shop items
        if ShopItem.query.count() == 0:
            ShopItem.create_default_items()
        
        # Create default badges
        if Badge.query.count() == 0:
            Badge.create_default_badges()
        
        # Create default game modes
        if GameMode.query.count() == 0:
            GameMode.create_default_modes()
        
        # Create demo player if none exist
        if Player.query.count() == 0:
            demo_player = Player()
            demo_player.nickname = "DemoPlayer"
            demo_player.experience = 12500
            demo_player.kills = 1250
            demo_player.final_kills = 320
            demo_player.deaths = 890
            demo_player.beds_broken = 180
            demo_player.wins = 95
            demo_player.games_played = 150
            demo_player.coins = 2500
            demo_player.iron_collected = 5000
            demo_player.gold_collected = 2500
            demo_player.diamond_collected = 450
            demo_player.emerald_collected = 120
            db.session.add(demo_player)
            db.session.commit()
            
    except Exception as e:
        app.logger.error(f"Error initializing default data: {e}")

if __name__ == '__main__':
    # Only run in debug mode if explicitly set for development
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
