from app import db
from datetime import datetime
from sqlalchemy import func, case, text, Index
from sqlalchemy.orm import joinedload, selectinload
from functools import lru_cache
import json

class ASCENDHistory(db.Model):
    """Model for storing ASCEND evaluation history"""
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    gamemode = db.Column(db.String(50), default='bedwars', nullable=False)

    # Previous values
    old_overall_tier = db.Column(db.String(3), nullable=True)
    new_overall_tier = db.Column(db.String(3), nullable=False)

    # Score changes
    old_scores = db.Column(db.Text, nullable=True)  # JSON
    new_scores = db.Column(db.Text, nullable=False)  # JSON

    # Change details
    change_type = db.Column(db.String(20), default='update', nullable=False)  # update, upgrade, downgrade
    evaluator_name = db.Column(db.String(100), nullable=False)
    comment = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    player = db.relationship('Player', backref='ascend_history')

    def to_dict(self):
        """Convert to dictionary for API responses"""
        import json
        return {
            'id': self.id,
            'player_id': self.player_id,
            'gamemode': self.gamemode,
            'old_overall_tier': self.old_overall_tier,
            'new_overall_tier': self.new_overall_tier,
            'old_scores': json.loads(self.old_scores) if self.old_scores else None,
            'new_scores': json.loads(self.new_scores) if self.new_scores else None,
            'change_type': self.change_type,
            'evaluator_name': self.evaluator_name,
            'comment': self.comment,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class ASCENDData(db.Model):
    """Model for storing ASCEND performance card data"""
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    gamemode = db.Column(db.String(50), default='bedwars', nullable=False)

    # Skill categories - varies by gamemode
    skill1_name = db.Column(db.String(50), default='PVP', nullable=False)
    skill1_tier = db.Column(db.String(3), default='D', nullable=False)
    skill1_score = db.Column(db.Integer, default=25, nullable=False)

    skill2_name = db.Column(db.String(50), default='Clutching', nullable=False)
    skill2_tier = db.Column(db.String(3), default='D', nullable=False)
    skill2_score = db.Column(db.Integer, default=25, nullable=False)

    skill3_name = db.Column(db.String(50), default='Block Placement', nullable=False)
    skill3_tier = db.Column(db.String(3), default='D', nullable=False)
    skill3_score = db.Column(db.Integer, default=25, nullable=False)

    skill4_name = db.Column(db.String(50), default='Gamesense', nullable=False)
    skill4_tier = db.Column(db.String(3), default='D', nullable=False)
    skill4_score = db.Column(db.Integer, default=25, nullable=False)

    # Legacy fields for backwards compatibility
    pvp_tier = db.Column(db.String(3), default='D', nullable=False)
    clutching_tier = db.Column(db.String(3), default='D', nullable=False)
    block_placement_tier = db.Column(db.String(3), default='D', nullable=False)
    gamesense_tier = db.Column(db.String(3), default='D', nullable=False)
    overall_tier = db.Column(db.String(3), default='D', nullable=False)

    pvp_score = db.Column(db.Integer, default=25, nullable=False)
    clutching_score = db.Column(db.Integer, default=25, nullable=False)
    block_placement_score = db.Column(db.Integer, default=25, nullable=False)
    gamesense_score = db.Column(db.Integer, default=25, nullable=False)

    # Custom comment
    comment = db.Column(db.Text, nullable=True)

    # Evaluator info
    evaluator_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=True)
    evaluator_name = db.Column(db.String(100), default='Elite Squad', nullable=False)

    # Previous tier for history
    previous_tier = db.Column(db.String(3), nullable=True)

    # Global ranking
    global_rank = db.Column(db.Integer, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    player = db.relationship('Player', foreign_keys=[player_id], backref='ascend_data')
    evaluator = db.relationship('Player', foreign_keys=[evaluator_id])

    @classmethod
    def get_or_create(cls, player_id, gamemode='bedwars'):
        """Get existing ASCEND data or create new with defaults for specific gamemode"""
        ascend_data = cls.query.filter_by(player_id=player_id, gamemode=gamemode).first()
        if not ascend_data:
            # Get gamemode config for proper skill names
            from models import GameMode
            gamemode_obj = GameMode.query.filter_by(name=gamemode).first()

            ascend_data = cls(
                player_id=player_id,
                gamemode=gamemode,
                skill1_name=gamemode_obj.skill1_name if gamemode_obj else 'PVP',
                skill2_name=gamemode_obj.skill2_name if gamemode_obj else 'Clutching',
                skill3_name=gamemode_obj.skill3_name if gamemode_obj else 'Block Placement',
                skill4_name=gamemode_obj.skill4_name if gamemode_obj else 'Gamesense'
            )
            db.session.add(ascend_data)
            db.session.commit()
        return ascend_data

    def save_to_history(self):
        """Save current state to history before making changes"""
        import json

        # Get old data if exists for the same gamemode
        old_data = ASCENDData.query.filter_by(
            player_id=self.player_id,
            gamemode=self.gamemode
        ).filter(ASCENDData.id != self.id).first()

        if old_data:
            # Determine change type
            change_type = 'update'
            if old_data.overall_tier != self.overall_tier:
                tier_values = {'D': 1, 'C': 2, 'C+': 3, 'B': 4, 'B+': 5, 'A': 6, 'A+': 7, 'S': 8, 'S+': 9}
                if tier_values.get(self.overall_tier, 1) > tier_values.get(old_data.overall_tier, 1):
                    change_type = 'upgrade'
                else:
                    change_type = 'downgrade'

            # Create history entry
            history = ASCENDHistory(
                player_id=self.player_id,
                gamemode=self.gamemode,
                old_overall_tier=old_data.overall_tier,
                new_overall_tier=self.overall_tier,
                old_scores=json.dumps({
                    'skill1': old_data.skill1_score,
                    'skill2': old_data.skill2_score,
                    'skill3': old_data.skill3_score,
                    'skill4': old_data.skill4_score
                }),
                new_scores=json.dumps({
                    'skill1': self.skill1_score,
                    'skill2': self.skill2_score,
                    'skill3': self.skill3_score,
                    'skill4': self.skill4_score
                }),
                change_type=change_type,
                evaluator_name=self.evaluator_name,
                comment=self.comment
            )
            db.session.add(history)

    def update_global_rank(self):
        """Update global rank based on overall performance within the same gamemode"""
        # Calculate average score
        avg_score = (self.skill1_score + self.skill2_score + self.skill3_score + self.skill4_score) / 4

        # Count players with higher scores in same gamemode only
        higher_count = db.session.query(ASCENDData).filter(
            ASCENDData.gamemode == self.gamemode,
            ASCENDData.player_id != self.player_id,  # Exclude current player
            (ASCENDData.skill1_score + ASCENDData.skill2_score + ASCENDData.skill3_score + ASCENDData.skill4_score) / 4 > avg_score
        ).count()

        self.global_rank = higher_count + 1

    def calculate_tier_from_score(self, score):
        """Calculate tier based on score"""
        if score >= 95:
            return 'S+'
        elif score >= 90:
            return 'S'
        elif score >= 85:
            return 'A+'
        elif score >= 80:
            return 'A'
        elif score >= 75:
            return 'B+'
        elif score >= 70:
            return 'B'
        elif score >= 60:
            return 'C+'
        elif score >= 50:
            return 'C'
        else:
            return 'D'

    def update_tiers_from_scores(self):
        """Update all tiers based on their scores"""
        self.skill1_tier = self.calculate_tier_from_score(self.skill1_score)
        self.skill2_tier = self.calculate_tier_from_score(self.skill2_score)
        self.skill3_tier = self.calculate_tier_from_score(self.skill3_score)
        self.skill4_tier = self.calculate_tier_from_score(self.skill4_score)

        # Calculate overall tier from average score
        average_score = (self.skill1_score + self.skill2_score + self.skill3_score + self.skill4_score) / 4
        self.overall_tier = self.calculate_tier_from_score(average_score)

        # Update legacy fields for backwards compatibility
        self.pvp_tier = self.skill1_tier
        self.clutching_tier = self.skill2_tier
        self.block_placement_tier = self.skill3_tier
        self.gamesense_tier = self.skill4_tier

        self.pvp_score = self.skill1_score
        self.clutching_score = self.skill2_score
        self.block_placement_score = self.skill3_score
        self.gamesense_score = self.skill4_score

    def to_dict(self):
        """Convert to dictionary for API responses"""
        # Ensure tiers are up to date
        self.update_tiers_from_scores()

        return {
            'id': self.id,
            'player_id': self.player_id,
            'gamemode': self.gamemode,
            'skill1_name': self.skill1_name,
            'skill1_tier': self.skill1_tier,
            'skill1_score': self.skill1_score,
            'skill2_name': self.skill2_name,
            'skill2_tier': self.skill2_tier,
            'skill2_score': self.skill2_score,
            'skill3_name': self.skill3_name,
            'skill3_tier': self.skill3_tier,
            'skill3_score': self.skill3_score,
            'skill4_name': self.skill4_name,
            'skill4_tier': self.skill4_tier,
            'skill4_score': self.skill4_score,
            'overall_tier': self.overall_tier,
            'global_rank': self.global_rank,
            'comment': self.comment,
            'evaluator_name': self.evaluator_name,
            'previous_tier': self.previous_tier,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            # Legacy compatibility
            'pvp_tier': self.pvp_tier,
            'clutching_tier': self.clutching_tier,
            'block_placement_tier': self.block_placement_tier,
            'gamesense_tier': self.gamesense_tier,
            'pvp_score': self.pvp_score,
            'clutching_score': self.clutching_score,
            'block_placement_score': self.block_placement_score,
            'gamesense_score': self.gamesense_score
        }

class GameMode(db.Model):
    """Model for different game modes with their skill categories"""
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(50), default='fas fa-gamepad')
    color = db.Column(db.String(7), default='#ffc107')

    # Skill categories for this gamemode
    skill1_name = db.Column(db.String(50), nullable=False)
    skill1_description = db.Column(db.String(200), nullable=True)
    skill1_icon = db.Column(db.String(50), default='fas fa-star')

    skill2_name = db.Column(db.String(50), nullable=False)
    skill2_description = db.Column(db.String(200), nullable=True)
    skill2_icon = db.Column(db.String(50), default='fas fa-star')

    skill3_name = db.Column(db.String(50), nullable=False)
    skill3_description = db.Column(db.String(200), nullable=True)
    skill3_icon = db.Column(db.String(50), default='fas fa-star')

    skill4_name = db.Column(db.String(50), nullable=False)
    skill4_description = db.Column(db.String(200), nullable=True)
    skill4_icon = db.Column(db.String(50), default='fas fa-star')

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'icon': self.icon,
            'color': self.color,
            'skills': [
                {
                    'name': self.skill1_name,
                    'description': self.skill1_description,
                    'icon': self.skill1_icon
                },
                {
                    'name': self.skill2_name,
                    'description': self.skill2_description,
                    'icon': self.skill2_icon
                },
                {
                    'name': self.skill3_name,
                    'description': self.skill3_description,
                    'icon': self.skill3_icon
                },
                {
                    'name': self.skill4_name,
                    'description': self.skill4_description,
                    'icon': self.skill4_icon
                }
            ],
            'is_active': self.is_active
        }

    @classmethod
    def create_default_modes(cls):
        """Create default game modes with their skill categories"""
        default_modes = [
            {
                'name': 'bedwars',
                'display_name': 'Bedwars',
                'description': 'Classic Bedwars gameplay',
                'icon': 'fas fa-bed',
                'color': '#e74c3c',
                'skill1_name': 'PVP',
                'skill1_description': 'Combat effectiveness and dueling skills',
                'skill1_icon': 'fas fa-sword',
                'skill2_name': 'Clutching',
                'skill2_description': 'Performance under pressure situations',
                'skill2_icon': 'fas fa-fire',
                'skill3_name': 'Block Placement',
                'skill3_description': 'Strategic building and defensive positioning',
                'skill3_icon': 'fas fa-cube',
                'skill4_name': 'Gamesense',
                'skill4_description': 'Game awareness and tactical decision making',
                'skill4_icon': 'fas fa-brain'
            },
            {
                'name': 'kitpvp',
                'display_name': 'KitPVP',
                'description': 'Kit-based PvP combat',
                'icon': 'fas fa-sword',
                'color': '#f39c12',
                'skill1_name': 'Aiming',
                'skill1_description': 'Accuracy and target acquisition',
                'skill1_icon': 'fas fa-crosshairs',
                'skill2_name': 'Healing (soups/pots)',
                'skill2_description': 'Health management and healing efficiency',
                'skill2_icon': 'fas fa-heart',
                'skill3_name': 'Movement',
                'skill3_description': 'Mobility and positioning',
                'skill3_icon': 'fas fa-running',
                'skill4_name': 'Spacing',
                'skill4_description': 'Distance control and positioning',
                'skill4_icon': 'fas fa-expand-arrows-alt'
            },
            {
                'name': 'skywars',
                'display_name': 'SkyWars',
                'description': 'Sky-based survival combat',
                'icon': 'fas fa-cloud',
                'color': '#3498db',
                'skill1_name': 'Looting',
                'skill1_description': 'Efficient resource gathering',
                'skill1_icon': 'fas fa-search',
                'skill2_name': 'Potting',
                'skill2_description': 'Potion usage and timing',
                'skill2_icon': 'fas fa-flask',
                'skill3_name': 'Pearling',
                'skill3_description': 'Ender pearl mechanics and timing',
                'skill3_icon': 'fas fa-circle',
                'skill4_name': 'Melee',
                'skill4_description': 'Close combat effectiveness',
                'skill4_icon': 'fas fa-fist-raised'
            },
            {
                'name': 'sumo',
                'display_name': 'Sumo',
                'description': 'Knockback-based combat',
                'icon': 'fas fa-hand-rock',
                'color': '#e67e22',
                'skill1_name': 'Gamesense',
                'skill1_description': 'Strategic thinking and positioning',
                'skill1_icon': 'fas fa-brain',
                'skill2_name': 'KB control',
                'skill2_description': 'Knockback manipulation and resistance',
                'skill2_icon': 'fas fa-hand-paper',
                'skill3_name': 'Mechanics',
                'skill3_description': 'Technical execution and timing',
                'skill3_icon': 'fas fa-cogs',
                'skill4_name': 'Movement',
                'skill4_description': 'Positioning and mobility',
                'skill4_icon': 'fas fa-running'
            }
        ]

        for mode_data in default_modes:
            existing = cls.query.filter_by(name=mode_data['name']).first()
            if not existing:
                mode = cls(**mode_data)
                db.session.add(mode)

        db.session.commit()

class TargetList(db.Model):
    """Model for clan target list entries"""
    __tablename__ = 'target_list'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(100), nullable=False)
    gamemode = db.Column(db.String(50), nullable=False)  # bedwars, kitpvp, etc.
    server_ip = db.Column(db.String(100), nullable=False)  # hypixel.net, etc.
    reason = db.Column(db.Text, nullable=False)  # Max 320 characters via frontend validation
    priority = db.Column(db.String(20), default='medium', nullable=False)  # low, medium, high
    status = db.Column(db.String(20), default='active', nullable=False)  # active, completed, removed
    added_by = db.Column(db.String(100), nullable=True)  # Who added this target
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    date_completed = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'nickname': self.nickname,
            'gamemode': self.gamemode,
            'server_ip': self.server_ip,
            'reason': self.reason,
            'priority': self.priority,
            'status': self.status,
            'added_by': self.added_by,
            'date_added': self.date_added.isoformat() if self.date_added else None,
            'date_completed': self.date_completed.isoformat() if self.date_completed else None,
            'notes': self.notes
        }

class Candidate(db.Model):
    """Model for clan candidates"""
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)  # Qualities, strengths, etc.
    servers = db.Column(db.Text, nullable=False)  # JSON array of servers
    contact = db.Column(db.String(200), nullable=True)  # Discord/other contact
    status = db.Column(db.String(50), default='candidate', nullable=False)  # candidate, in_progress, invited, accepted, rejected
    added_by = db.Column(db.String(100), nullable=True)  # Who added this candidate
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)  # Internal notes

    # Reaction system
    likes = db.Column(db.Integer, default=0, nullable=False)
    comments_count = db.Column(db.Integer, default=0, nullable=False)
    rating = db.Column(db.Float, default=0.0, nullable=False)  # Average rating

    def to_dict(self):
        """Convert to dictionary for API responses"""
        import json
        servers_list = []
        try:
            if self.servers:
                servers_list = json.loads(self.servers)
        except:
            servers_list = [self.servers] if self.servers else []

        return {
            'id': self.id,
            'nickname': self.nickname,
            'description': self.description,
            'servers': servers_list,
            'contact': self.contact,
            'status': self.status,
            'added_by': self.added_by,
            'date_added': self.date_added.isoformat() if self.date_added else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'notes': self.notes,
            'likes': self.likes,
            'comments_count': self.comments_count,
            'rating': self.rating
        }

    def get_servers_list(self):
        """Get parsed servers list"""
        import json
        try:
            if self.servers:
                return json.loads(self.servers)
        except:
            return [self.servers] if self.servers else []
        return []

    def set_servers_list(self, servers_list):
        """Set servers list"""
        import json
        self.servers = json.dumps(servers_list) if servers_list else None

class CandidateComment(db.Model):
    """Model for candidate comments"""
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

    candidate = db.relationship('Candidate', backref='comments')

    def to_dict(self):
        return {
            'id': self.id,
            'candidate_id': self.candidate_id,
            'author': self.author,
            'comment': self.comment,
            'date_added': self.date_added.isoformat() if self.date_added else None
        }

class CandidateReaction(db.Model):
    """Model for candidate reactions (likes, ratings)"""
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'), nullable=False)
    user = db.Column(db.String(100), nullable=False)
    reaction_type = db.Column(db.String(20), nullable=False)  # like, rating
    value = db.Column(db.Float, nullable=True)  # For ratings (1-5), null for likes
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

    candidate = db.relationship('Candidate', backref='reactions')

    # Unique constraint to prevent duplicate reactions from same user
    __table_args__ = (db.UniqueConstraint('candidate_id', 'user', 'reaction_type'),)

class Badge(db.Model):
    """Model for player badges/achievements"""
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    display_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(100), default='fas fa-medal')
    emoji = db.Column(db.String(10), nullable=True)
    emoji_url = db.Column(db.String(255), nullable=True)

    # Colors and styling
    color = db.Column(db.String(7), default='#ffffff')
    background_color = db.Column(db.String(7), default='#343a40')
    border_color = db.Column(db.String(7), default='#ffd700')

    # Gradient support
    has_gradient = db.Column(db.Boolean, default=False)
    gradient_start = db.Column(db.String(7), nullable=True)
    gradient_end = db.Column(db.String(7), nullable=True)

    # Properties
    rarity = db.Column(db.String(20), default='common')  # common, rare, epic, legendary, mythic
    is_animated = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(100), default='system')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'icon': self.icon,
            'emoji': self.emoji,
            'emoji_url': self.emoji_url,
            'color': self.color,
            'background_color': self.background_color,
            'border_color': self.border_color,
            'has_gradient': self.has_gradient,
            'gradient_start': self.gradient_start,
            'gradient_end': self.gradient_end,
            'rarity': self.rarity,
            'is_animated': self.is_animated,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def create_default_badges(cls):
        """Create default badges"""
        default_badges = [
            {
                'name': 'first_blood',
                'display_name': 'Первая кровь',
                'description': 'Совершил свое первое убийство',
                'icon': 'fas fa-sword',
                'emoji': '⚔️',
                'color': '#ffffff',
                'background_color': '#dc3545',
                'border_color': '#ff6b6b',
                'rarity': 'common'
            },
            {
                'name': 'bed_destroyer',
                'display_name': 'Разрушитель кроватей',
                'description': 'Сломал 10 кроватей',
                'icon': 'fas fa-bed',
                'emoji': '🛏️',
                'color': '#ffffff',
                'background_color': '#e74c3c',
                'border_color': '#f39c12',
                'rarity': 'rare'
            },
            {
                'name': 'speed_demon',
                'display_name': 'Демон скорости',
                'description': 'Выиграл игру менее чем за 5 минут',
                'icon': 'fas fa-bolt',
                'emoji': '⚡',
                'color': '#212529',
                'has_gradient': True,
                'gradient_start': '#f1c40f',
                'gradient_end': '#e67e22',
                'border_color': '#f39c12',
                'rarity': 'epic',
                'is_animated': True
            },
            {
                'name': 'untouchable',
                'display_name': 'Неприкасаемый',
                'description': 'Выиграл игру без единой смерти',
                'icon': 'fas fa-shield-alt',
                'emoji': '🛡️',
                'color': '#ffffff',
                'has_gradient': True,
                'gradient_start': '#28a745',
                'gradient_end': '#20c997',
                'border_color': '#28a745',
                'rarity': 'legendary',
                'is_animated': True
            },
            {
                'name': 'veteran',
                'display_name': 'Ветеран',
                'description': 'Сыграл более 1000 игр',
                'icon': 'fas fa-star',
                'emoji': '⭐',
                'color': '#ffd700',
                'background_color': '#212529',
                'border_color': '#ffd700',
                'rarity': 'epic'
            }
        ]

        for badge_data in default_badges:
            existing = cls.query.filter_by(name=badge_data['name']).first()
            if not existing:
                badge = cls(**badge_data)
                db.session.add(badge)

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error creating default badges: {e}")

class PlayerBadge(db.Model):
    """Association table for player badges"""
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    badge_id = db.Column(db.Integer, db.ForeignKey('badge.id'), nullable=False)

    # Display settings
    is_visible = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)

    # Metadata
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
    given_by = db.Column(db.String(100), default='system')

    # Relationships
    player = db.relationship('Player', backref='player_badges')
    badge = db.relationship('Badge', backref='player_assignments')

    # Ensure unique badge per player
    __table_args__ = (db.UniqueConstraint('player_id', 'badge_id'),)

    def to_dict(self):
        return {
            'id': self.id,
            'player_id': self.player_id,
            'badge_id': self.badge_id,
            'is_visible': self.is_visible,
            'display_order': self.display_order,
            'earned_at': self.earned_at.isoformat() if self.earned_at else None,
            'given_by': self.given_by,
            'badge': self.badge.to_dict() if self.badge else None
        }

class Target(db.Model):
    """Model for clan target list entries"""
    __tablename__ = 'target'

    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(100), nullable=False)
    server = db.Column(db.String(100), nullable=False)
    gamemode = db.Column(db.String(50), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='medium', nullable=False)  # low, medium, high, critical
    status = db.Column(db.String(20), default='active', nullable=False)  # active, completed, removed, inactive
    added_by = db.Column(db.String(100), nullable=True)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)
    date_completed = db.Column(db.DateTime, nullable=True)

    # Новые поля
    tags = db.Column(db.Text, nullable=True)  # JSON array of tags
    description = db.Column(db.Text, nullable=True)  # Дополнительные заметки
    mention_count = db.Column(db.Integer, default=1, nullable=False)  # Счетчик упоминаний
    priority_rank = db.Column(db.Integer, default=3, nullable=False)  # Числовой ранг 1-5

    # История изменений (JSON)
    edit_history = db.Column(db.Text, nullable=True)

    # Reaction counts - 8 типов реакций
    fragged_count = db.Column(db.Integer, default=0, nullable=False)
    killed_count = db.Column(db.Integer, default=0, nullable=False)
    exploded_count = db.Column(db.Integer, default=0, nullable=False)
    slayed_count = db.Column(db.Integer, default=0, nullable=False)
    destroyed_count = db.Column(db.Integer, default=0, nullable=False)
    eliminated_count = db.Column(db.Integer, default=0, nullable=False)
    rekt_count = db.Column(db.Integer, default=0, nullable=False)
    obliterated_count = db.Column(db.Integer, default=0, nullable=False)
    has_bleeding_effect = db.Column(db.Boolean, default=False, nullable=False)

    # Лайки и дизлайки
    likes = db.Column(db.Integer, default=0, nullable=False)
    dislikes = db.Column(db.Integer, default=0, nullable=False)

    @property
    def total_reactions(self):
        return (self.fragged_count + self.killed_count + self.exploded_count +
                self.slayed_count + self.destroyed_count + self.eliminated_count +
                self.rekt_count + self.obliterated_count)

    @property
    def reactions(self):
        """Return reactions in a format compatible with templates"""
        return {
            'fragged': self.fragged_count,
            'killed': self.killed_count,
            'exploded': self.exploded_count,
            'slayed': self.slayed_count,
            'destroyed': self.destroyed_count,
            'eliminated': self.eliminated_count,
            'rekt': self.rekt_count,
            'obliterated': self.obliterated_count
        }

    def check_bleeding_effect(self):
        """Check if target should get bleeding effect"""
        if self.total_reactions >= 10 and not self.has_bleeding_effect:
            self.has_bleeding_effect = True
            return True
        return False

    def get_tags_list(self):
        """Get parsed tags list"""
        import json
        try:
            if self.tags:
                return json.loads(self.tags)
        except:
            return []
        return []

    def set_tags_list(self, tags_list):
        """Set tags list"""
        import json
        self.tags = json.dumps(tags_list) if tags_list else None

    def get_edit_history(self):
        """Get parsed edit history"""
        import json
        try:
            if self.edit_history:
                return json.loads(self.edit_history)
        except:
            return []
        return []

    def add_edit_record(self, editor, action, changes):
        """Add edit record to history"""
        import json
        history = self.get_edit_history()
        history.append({
            'editor': editor,
            'action': action,
            'changes': changes,
            'timestamp': datetime.utcnow().isoformat()
        })
        # Keep only last 10 records
        if len(history) > 10:
            history = history[-10:]
        self.edit_history = json.dumps(history)

    def to_dict(self):
        return {
            'id': self.id,
            'nickname': self.nickname,
            'server': self.server,
            'gamemode': self.gamemode,
            'reason': self.reason,
            'priority': self.priority,
            'priority_rank': self.priority_rank,
            'status': self.status,
            'added_by': self.added_by,
            'date_added': self.date_added.isoformat() if self.date_added else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'date_completed': self.date_completed.isoformat() if self.date_completed else None,
            'tags': self.get_tags_list(),
            'description': self.description,
            'mention_count': self.mention_count,
            'reactions': self.reactions,
            'total_reactions': self.total_reactions,
            'has_bleeding_effect': self.has_bleeding_effect,
            'likes': self.likes,
            'dislikes': self.dislikes,
            'edit_history': self.get_edit_history()
        }

class TargetReaction(db.Model):
    """Model for target reactions"""
    __tablename__ = 'target_reaction'

    id = db.Column(db.Integer, primary_key=True)
    target_id = db.Column(db.Integer, db.ForeignKey('target.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=True)
    reaction_type = db.Column(db.String(20), nullable=False)  # fragged, destroyed, eliminated
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    target = db.relationship('Target', backref='reaction_history')
    player = db.relationship('Player', backref='target_reactions')

    @classmethod
    def add_reaction(cls, target_id, reaction_type, player_id=None):
        """Add reaction and update target counts"""
        # Validate reaction type
        valid_reactions = ['fragged', 'killed', 'exploded', 'slayed', 'destroyed', 'eliminated', 'rekt', 'obliterated']
        if reaction_type not in valid_reactions:
            raise ValueError(f"Invalid reaction type: {reaction_type}")

        reaction = cls(
            target_id=target_id,
            reaction_type=reaction_type,
            player_id=player_id
        )
        db.session.add(reaction)

        # Update target counts
        target = Target.query.get(target_id)
        if target:
            if reaction_type == 'fragged':
                target.fragged_count += 1
            elif reaction_type == 'killed':
                target.killed_count += 1
            elif reaction_type == 'exploded':
                target.exploded_count += 1
            elif reaction_type == 'slayed':
                target.slayed_count += 1
            elif reaction_type == 'destroyed':
                target.destroyed_count += 1
            elif reaction_type == 'eliminated':
                target.eliminated_count += 1
            elif reaction_type == 'rekt':
                target.rekt_count += 1
            elif reaction_type == 'obliterated':
                target.obliterated_count += 1

            # Check for bleeding effect
            target.check_bleeding_effect()

        return reaction

class Player(db.Model):
    """Enhanced model for storing player profile and general information"""

    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(100), nullable=False, unique=True, index=True)

    # General profile fields (non-gamemode specific)
    role = db.Column(db.String(50), default='Игрок', nullable=False)
    server_ip = db.Column(db.String(100), default='', nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Legacy Bedwars fields (for backward compatibility)
    kills = db.Column(db.Integer, default=0, nullable=False, index=True)
    final_kills = db.Column(db.Integer, default=0, nullable=False, index=True)
    deaths = db.Column(db.Integer, default=0, nullable=False)
    final_deaths = db.Column(db.Integer, default=0, nullable=False)
    beds_broken = db.Column(db.Integer, default=0, nullable=False, index=True)
    games_played = db.Column(db.Integer, default=0, nullable=False)
    wins = db.Column(db.Integer, default=0, nullable=False, index=True)
    experience = db.Column(db.Integer, default=0, nullable=False, index=True)

    # KitPVP Stats
    kitpvp_kills = db.Column(db.Integer, default=0, nullable=False)
    kitpvp_deaths = db.Column(db.Integer, default=0, nullable=False)
    kitpvp_games = db.Column(db.Integer, default=0, nullable=False)

    # SkyWars Stats
    skywars_wins = db.Column(db.Integer, default=0, nullable=False)
    skywars_solo_wins = db.Column(db.Integer, default=0, nullable=False)
    skywars_team_wins = db.Column(db.Integer, default=0, nullable=False)
    skywars_mega_wins = db.Column(db.Integer, default=0, nullable=False)
    skywars_mini_wins = db.Column(db.Integer, default=0, nullable=False)
    skywars_ranked_wins = db.Column(db.Integer, default=0, nullable=False)
    skywars_kills = db.Column(db.Integer, default=0, nullable=False)
    skywars_solo_kills = db.Column(db.Integer, default=0, nullable=False)
    skywars_team_kills = db.Column(db.Integer, default=0, nullable=False)
    skywars_mega_kills = db.Column(db.Integer, default=0, nullable=False)
    skywars_mini_kills = db.Column(db.Integer, default=0, nullable=False)
    skywars_ranked_kills = db.Column(db.Integer, default=0, nullable=False)

    # Sumo Stats
    sumo_games_played = db.Column(db.Integer, default=0, nullable=False)
    sumo_monthly_games = db.Column(db.Integer, default=0, nullable=False)
    sumo_daily_games = db.Column(db.Integer, default=0, nullable=False)
    sumo_deaths = db.Column(db.Integer, default=0, nullable=False)
    sumo_monthly_deaths = db.Column(db.Integer, default=0, nullable=False)
    sumo_daily_deaths = db.Column(db.Integer, default=0, nullable=False)
    sumo_wins = db.Column(db.Integer, default=0, nullable=False)
    sumo_monthly_wins = db.Column(db.Integer, default=0, nullable=False)
    sumo_daily_wins = db.Column(db.Integer, default=0, nullable=False)
    sumo_losses = db.Column(db.Integer, default=0, nullable=False)
    sumo_monthly_losses = db.Column(db.Integer, default=0, nullable=False)
    sumo_daily_losses = db.Column(db.Integer, default=0, nullable=False)
    sumo_kills = db.Column(db.Integer, default=0, nullable=False)
    sumo_monthly_kills = db.Column(db.Integer, default=0, nullable=False)
    sumo_daily_kills = db.Column(db.Integer, default=0, nullable=False)
    sumo_winstreak = db.Column(db.Integer, default=0, nullable=False)
    sumo_monthly_winstreak = db.Column(db.Integer, default=0, nullable=False)
    sumo_daily_winstreak = db.Column(db.Integer, default=0, nullable=False)
    sumo_best_winstreak = db.Column(db.Integer, default=0, nullable=False)
    sumo_monthly_best_winstreak = db.Column(db.Integer, default=0, nullable=False)
    sumo_daily_best_winstreak = db.Column(db.Integer, default=0, nullable=False)

    # New fields for enhanced statistics
    iron_collected = db.Column(db.Integer, default=0, nullable=False)
    gold_collected = db.Column(db.Integer, default=0, nullable=False)
    diamond_collected = db.Column(db.Integer, default=0, nullable=False)
    emerald_collected = db.Column(db.Integer, default=0, nullable=False)
    items_purchased = db.Column(db.Integer, default=0, nullable=False)

    # Minecraft skin system
    skin_url = db.Column(db.String(255), nullable=True)  # Custom skin URL from NameMC
    skin_type = db.Column(db.String(10), default='auto', nullable=False)  # auto, steve, alex, custom
    is_premium = db.Column(db.Boolean, default=False, nullable=False)  # Licensed Minecraft account

    # Personal profile information
    real_name = db.Column(db.String(100), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    discord_tag = db.Column(db.String(50), nullable=True)
    youtube_channel = db.Column(db.String(100), nullable=True)
    twitch_channel = db.Column(db.String(100), nullable=True)
    favorite_server = db.Column(db.String(100), nullable=True)
    favorite_map = db.Column(db.String(100), nullable=True)
    preferred_gamemode = db.Column(db.String(50), nullable=True)
    profile_banner_color = db.Column(db.String(7), default='#3498db', nullable=True)
    profile_is_public = db.Column(db.Boolean, default=True, nullable=False)
    custom_status = db.Column(db.String(100), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    birthday = db.Column(db.Date, nullable=True)

    # Custom profile customization
    custom_avatar_url = db.Column(db.String(255), nullable=True)
    custom_banner_url = db.Column(db.String(255), nullable=True)
    banner_is_animated = db.Column(db.Boolean, default=False, nullable=False)

    # Extended social networks
    social_networks = db.Column(db.Text, nullable=True)  # JSON array of social networks

    # Profile section backgrounds
    stats_section_color = db.Column(db.String(7), default='#343a40', nullable=True)
    info_section_color = db.Column(db.String(7), default='#343a40', nullable=True)
    social_section_color = db.Column(db.String(7), default='#343a40', nullable=True)
    prefs_section_color = db.Column(db.String(7), default='#343a40', nullable=True)

    # Password system
    password_hash = db.Column(db.String(255), nullable=True)
    has_password = db.Column(db.Boolean, default=False, nullable=False)

    # Theme system
    selected_theme_id = db.Column(db.Integer, db.ForeignKey('site_theme.id'), nullable=True)
    selected_theme = db.relationship('SiteTheme', backref='users')

    # Leaderboard customization
    leaderboard_name_color = db.Column(db.String(7), default='#ffffff', nullable=True)
    leaderboard_stats_color = db.Column(db.String(7), default='#ffffff', nullable=True)
    leaderboard_use_gradient = db.Column(db.Boolean, default=False, nullable=False)
    leaderboard_gradient_start = db.Column(db.String(7), default='#ff6b35', nullable=True)
    leaderboard_gradient_end = db.Column(db.String(7), default='#f7931e', nullable=True)
    leaderboard_gradient_animated = db.Column(db.Boolean, default=False, nullable=False)

    # Inventory system
    inventory_data = db.Column(db.Text, nullable=True)  # JSON data for player inventory

    # Relationships for quest system
    player_quests = db.relationship('PlayerQuest', backref='player', lazy=True, cascade='all, delete-orphan')
    player_achievements = db.relationship('PlayerAchievement', backref='player', lazy=True, cascade='all, delete-orphan')

    # Economy system fields
    coins = db.Column(db.Integer, default=0, nullable=False)
    reputation = db.Column(db.Integer, default=0, nullable=False)

    # Karma system fields (NEW)
    karma = db.Column(db.Integer, default=0, nullable=False, index=True)

    # Индексы для оптимизации PostgreSQL
    __table_args__ = (
        Index('idx_player_stats', 'experience', 'wins', 'kills'),
        Index('idx_player_updated', 'last_updated'),
        Index('idx_player_level_calc', 'experience', 'wins', 'games_played'),
        Index('idx_player_karma', 'karma'),
        Index('idx_player_nickname_search', 'nickname'),
        Index('idx_player_kd_calc', 'kills', 'deaths'),
        Index('idx_player_winrate_calc', 'wins', 'games_played'),
        {'extend_existing': True}
    )

    # Custom role system
    custom_role = db.Column(db.String(100), nullable=True)
    custom_role_color = db.Column(db.String(7), nullable=True)
    custom_role_gradient = db.Column(db.Text, nullable=True)
    custom_role_emoji = db.Column(db.String(10), nullable=True)
    custom_role_animated = db.Column(db.Boolean, default=False, nullable=False)
    custom_role_purchased = db.Column(db.Boolean, default=False, nullable=False)
    custom_emoji_slots = db.Column(db.Integer, default=0, nullable=False) # Added for custom emoji slots
    custom_role_tier = db.Column(db.String(50), nullable=True) # Added for custom role tier

    # Cursor customization removed for stability

    @property
    def active_custom_title(self):
        """Get player's active custom title"""
        try:
            player_title = PlayerTitle.query.filter_by(
                player_id=self.id,
                is_active=True
            ).first()
            return player_title.title if player_title else None
        except Exception:
            return None

    def get_gradient_for_element(self, element_type):
        """Get gradient setting for specific element type"""
        setting = PlayerGradientSetting.query.filter_by(
            player_id=self.id,
            element_type=element_type,
            is_enabled=True
        ).first()
        return setting.css_gradient if setting else None

    @property
    def nickname_gradient(self):
        """Get nickname gradient CSS"""
        return self.get_gradient_for_element('nickname')

    @property
    def stats_gradient(self):
        """Get stats gradient CSS"""
        return self.get_gradient_for_element('stats')

    @property
    def title_gradient(self):
        """Get title gradient CSS"""
        return self.get_gradient_for_element('title')

    @property
    def kills_gradient(self):
        """Get kills gradient CSS"""
        return self.get_gradient_for_element('kills')

    @property
    def deaths_gradient(self):
        """Get deaths gradient CSS"""
        return self.get_gradient_for_element('deaths')

    @property
    def wins_gradient(self):
        """Get wins gradient CSS"""
        return self.get_gradient_for_element('wins')

    @property
    def beds_gradient(self):
        """Get beds gradient CSS"""
        return self.get_gradient_for_element('beds')

    @property
    def status_gradient(self):
        """Get status gradient CSS"""
        return self.get_gradient_for_element('status')

    @property
    def bio_gradient(self):
        """Get bio gradient CSS"""
        return self.get_gradient_for_element('bio')

    @property
    def role_gradient(self):
        """Get role gradient CSS"""
        return self.get_gradient_for_element('role')

    @property
    def can_use_static_gradients(self):
        """Check if player can use static gradients (level 80+)"""
        return self.level >= 80

    @property
    def can_use_animated_gradients(self):
        """Check if player can use animated gradients (level 150+)"""
        return self.level >= 150

    @property
    def can_customize_colors(self):
        """Check if player can customize interface colors (level 40+)"""
        return self.level >= 40

    @property
    def can_use_custom_avatars(self):
        """Check if player can use custom avatars (level 20+)"""
        return self.level >= 20

    @property
    def can_use_animated_avatars(self):
        """Check if player can use animated avatars (level 70+)"""
        return self.level >= 70

    @property
    def can_use_custom_banners(self):
        """Check if player can use custom banners (level 30+)"""
        return self.level >= 30

    @property
    def can_use_animated_banners(self):
        """Check if player can use animated banners (level 135+)"""
        return self.level >= 135

    @property
    def can_use_leaderboard_gradients(self):
        """Check if player can use gradients in leaderboard (level 50+)"""
        return self.level >= 50

    @property
    def can_use_leaderboard_animated_gradients(self):
        """Check if player can use animated gradients in leaderboard (level 75+)"""
        return self.level >= 75

    @property
    def can_buy_basic_custom_role(self):
        """Check if player can buy basic custom role (level 10+)"""
        return self.level >= 10

    @property
    def can_buy_gradient_custom_role(self):
        """Check if player can buy gradient custom role (level 40+)"""
        return self.level >= 40

    @property
    def can_set_free_custom_role(self):
        """Check if player can set free custom role (level 500+)"""
        return self.level >= 500

    @property
    def active_admin_role(self):
        """Get player's active admin custom role"""
        try:
            from models import PlayerAdminRole
            admin_role = PlayerAdminRole.query.filter_by(
                player_id=self.id,
                is_active=True
            ).first()
            return admin_role if admin_role else None
        except Exception:
            return None

    @property
    def all_admin_roles(self):
        """Get all admin roles assigned to player"""
        return PlayerAdminRole.query.filter_by(player_id=self.id).all()



    def get_badges(self):
        """Get all badges for this player"""
        return PlayerBadge.query.filter_by(player_id=self.id).all()

    @property
    def visible_badges(self):
        """Get all visible badges assigned to player"""
        try:
            from models import PlayerBadge, Badge
            return PlayerBadge.query.filter_by(
                player_id=self.id,
                is_visible=True
            ).join(Badge).filter(Badge.is_active == True).all()
        except Exception:
            return []

    @property
    def karma_level(self):
        """Get karma level name"""
        karma = self.karma or 0
        if karma <= -1000:
            return "Поглощённый Тьмой"
        elif karma <= -500:
            return "Тёмный Пилигрим"
        elif karma < 500:
            return "Серый Балансир"
        elif karma < 1000:
            return "Светоносец"
        elif karma < 2500:
            return "Избранный"
        else:
            return "Апофеоз"

    @property
    def display_role(self):
        """Get the role to display - admin role replaces regular role"""
        # Priority 1: Admin role replaces regular role
        admin_role = self.active_admin_role
        if admin_role and admin_role.role:
            return admin_role.role.name
        # Priority 2: Custom role if purchased
        elif self.custom_role_purchased and self.custom_role:
            return self.custom_role
        # Priority 3: Regular role
        return self.role

    @property
    def effective_role_data(self):
        """Get complete role data for display"""
        # Check for admin role first (replaces regular role)
        admin_role = self.active_admin_role
        if admin_role and admin_role.role:
            return {
                'type': 'admin',
                'name': admin_role.role.name,
                'color': getattr(admin_role.role, 'color', '#ffd700'),
                'emoji': getattr(admin_role.role, 'emoji', ''),
                'has_gradient': getattr(admin_role.role, 'has_gradient', False),
                'gradient_start': getattr(admin_role.role, 'gradient_start', None),
                'gradient_end': getattr(admin_role.role, 'gradient_end', None),
                'is_animated': getattr(admin_role.role, 'is_animated', False)
            }
        # Custom role
        elif self.custom_role_purchased and self.custom_role:
            return {
                'type': 'custom',
                'name': self.custom_role,
                'color': self.custom_role_color or '#ffd700',
                'emoji': self.custom_role_emoji or '',
                'has_gradient': bool(self.custom_role_gradient),
                'gradient': self.custom_role_gradient,
                'is_animated': self.custom_role_animated
            }
        # Default role
        else:
            return {
                'type': 'default',
                'name': self.role,
                'color': '#ffffff',
                'has_gradient': False
            }

    @property
    def role_style_html(self):
        """Get inline CSS style for role display"""
        role_data = self.effective_role_data
        color = role_data.get('color', '#ffffff')

        if role_data.get('has_gradient') and role_data['type'] == 'custom' and role_data.get('gradient'):
            return f"background: {role_data['gradient']}; color: white; padding: 4px 12px; border-radius: 8px; border: 1px solid {color}; font-weight: bold;"
        elif role_data.get('has_gradient') and role_data['type'] == 'admin':
            gradient_start = role_data.get('gradient_start', color)
            gradient_end = role_data.get('gradient_end', color)
            gradient = f"linear-gradient(45deg, {gradient_start}, {gradient_end})"
            return f"background: {gradient}; color: white; padding: 4px 12px; border-radius: 8px; border: 1px solid {gradient_start}; font-weight: bold;"
        else:
            return f"background-color: {color}; color: white; padding: 4px 12px; border-radius: 8px; border: 1px solid {color}; font-weight: bold;"

    @property
    def role_display_html(self):
        """Get HTML for role display with proper styling preservation"""
        role_data = self.effective_role_data
        role_name = role_data['name']
        role_type = role_data['type']
        color = role_data.get('color', '#6c757d')
        emoji = role_data.get('emoji', '')
        has_gradient = role_data.get('has_gradient', False)

        # Determine CSS classes and styles
        css_classes = ['role-display']
        style_parts = []

        if role_type == 'admin':
            css_classes.append('admin-role')
            css_classes.append('role-admin')
            if has_gradient:
                css_classes.append('gradient-role')
                gradient_start = role_data.get('gradient_start', color)
                gradient_end = role_data.get('gradient_end', color)
                gradient = f"linear-gradient(45deg, {gradient_start}, {gradient_end})"
                style_parts.extend([
                    f"background: {gradient}",
                    f"-webkit-background-clip: text",
                    f"-webkit-text-fill-color: transparent",
                    f"background-clip: text",
                    f"background-size: 200% 200%"
                ])
            else:
                style_parts.append(f"color: {color} !important")

        elif role_type == 'custom':
            css_classes.append('custom-role')
            css_classes.append('role-custom')
            if has_gradient:
                css_classes.append('gradient-role')
                gradient_css = role_data.get('gradient', f"linear-gradient(45deg, {color}, {color})")
                style_parts.extend([
                    f"background: {gradient_css}",
                    f"-webkit-background-clip: text",
                    f"-webkit-text-fill-color: transparent",
                    f"background-clip: text",
                    f"background-size: 200% 200%"
                ])
            else:
                style_parts.append(f"color: {color} !important")

        else:
            css_classes.append('default-role')
            css_classes.append('role-default')
            style_parts.append(f"color: {color} !important")

        # Build final HTML
        class_attr = ' '.join(css_classes)
        style_attr = '; '.join(style_parts) if style_parts else ''
        emoji_part = f'<span class="role-emoji">{emoji}</span> ' if emoji else ""

        return f'<span class="{class_attr}" style="{style_attr}">{emoji_part}{role_name}</span>'

    @property
    def nickname_display_html(self):
        """Get HTML for nickname display with gradients"""
        nickname = self.nickname
        gradient = self.nickname_gradient

        if gradient:
            style_parts = [
                f"background: {gradient}",
                "background-size: 200% 200%",
                "-webkit-background-clip: text",
                "-webkit-text-fill-color: transparent",
                "background-clip: text"
            ]

            # Check if gradient should be animated (level 150+)
            if self.can_use_animated_gradients:
                style_parts.append("animation: gradientShift 3s ease-in-out infinite")

            style_attr = f'style="{"; ".join(style_parts)}"'
            return f'<span class="nickname-display gradient-nickname" {style_attr}>{nickname}</span>'

        return f'<span class="nickname-display">{nickname}</span>'

    @property
    def can_set_free_custom_role_progress(self):
        """Get progress towards free custom role unlock (level 500)"""
        if self.level >= 500:
            return 100
        return round((self.level / 500) * 100, 1)

    def get_gamemode_stats(self, gamemode):
        """Get stats for specific gamemode"""
        if gamemode == 'bedwars':
            return {
                'kills': self.kills,
                'final_kills': self.final_kills,
                'deaths': self.deaths,
                'final_deaths': self.final_deaths,
                'beds_broken': self.beds_broken,
                'wins': self.wins,
                'games_played': self.games_played,
                'experience': self.experience,
                'kd_ratio': self.kd_ratio,
                'fkd_ratio': self.fkd_ratio,
                'win_rate': self.win_rate,
                'level': self.level
            }
        elif gamemode == 'kitpvp':
            kd = round(self.kitpvp_kills / self.kitpvp_deaths, 2) if self.kitpvp_deaths > 0 else self.kitpvp_kills
            return {
                'kills': self.kitpvp_kills,
                'deaths': self.kitpvp_deaths,
                'games': self.kitpvp_games,
                'kd_ratio': kd
            }
        elif gamemode == 'skywars':
            return {
                'wins': self.skywars_wins,
                'solo_wins': self.skywars_solo_wins,
                'team_wins': self.skywars_team_wins,
                'mega_wins': self.skywars_mega_wins,
                'mini_wins': self.skywars_mini_wins,
                'ranked_wins': self.skywars_ranked_wins,
                'kills': self.skywars_kills,
                'solo_kills': self.skywars_solo_kills,
                'team_kills': self.skywars_team_kills,
                'mega_kills': self.skywars_mega_kills,
                'mini_kills': self.skywars_mini_kills,
                'ranked_kills': self.skywars_ranked_kills
            }
        elif gamemode == 'sumo':
            return {
                'games_played': self.sumo_games_played,
                'monthly_games': self.sumo_monthly_games,
                'daily_games': self.sumo_daily_games,
                'deaths': self.sumo_deaths,
                'monthly_deaths': self.sumo_monthly_deaths,
                'daily_deaths': self.sumo_daily_deaths,
                'wins': self.sumo_wins,
                'monthly_wins': self.sumo_monthly_wins,
                'daily_wins': self.sumo_daily_wins,
                'losses': self.sumo_losses,
                'monthly_losses': self.sumo_monthly_losses,
                'daily_losses': self.sumo_daily_losses,
                'kills': self.sumo_kills,
                'monthly_kills': self.sumo_monthly_kills,
                'daily_kills': self.sumo_daily_kills,
                'winstreak': self.sumo_winstreak,
                'monthly_winstreak': self.sumo_monthly_winstreak,
                'daily_winstreak': self.sumo_daily_winstreak,
                'best_winstreak': self.sumo_best_winstreak,
                'monthly_best_winstreak': self.sumo_monthly_best_winstreak,
                'daily_best_winstreak': self.sumo_daily_best_winstreak
            }
        return {}

    @property
    def custom_role_features_available(self):
        """Get available features for player's custom role tier"""
        if not self.custom_role_purchased:
            return {}

        tier = self.custom_role_tier or 'basic'

        # Define features based on tier
        features = {
            'basic': {
                'color': True,
                'emoji': False,
                'gradient': False,
                'animation': False,
                'glow': False,
                'shadow': False,
                'font_styling': False,
                'border': False,
                'background': False
            },
            'premium': {
                'color': True,
                'emoji': True,
                'gradient': True,
                'animation': False,
                'glow': True,
                'shadow': False,
                'font_styling': True,
                'border': False,
                'background': False
            },
            'legendary': {
                'color': True,
                'emoji': True,
                'gradient': True,
                'animation': True,
                'glow': True,
                'shadow': True,
                'font_styling': True,
                'border': True,
                'background': False
            },
            'mythic': {
                'color': True,
                'emoji': True,
                'gradient': True,
                'animation': True,
                'glow': True,
                'shadow': True,
                'font_styling': True,
                'border': True,
                'background': True
            }
        }

        return features.get(tier, features['basic'])

    def get_social_networks_list(self):
        """Get parsed social networks list"""
        if not self.social_networks:
            return []
        try:
            import json
            return json.loads(self.social_networks)
        except:
            return []

    def set_social_networks_list(self, networks_list):
        """Set social networks list"""
        import json
        self.social_networks = json.dumps(networks_list) if networks_list else None

    def get_inventory(self):
        """Get parsed inventory data"""
        if not self.inventory_data:
            return {}
        try:
            import json
            return json.loads(self.inventory_data)
        except:
            return {}

    def set_inventory(self, inventory_dict):
        """Set inventory data"""
        import json
        self.inventory_data = json.dumps(inventory_dict) if inventory_dict else None

    def add_inventory_item(self, item_type, item_id, quantity=1):
        """Add item to player inventory"""
        inventory = self.get_inventory()
        if item_type not in inventory:
            inventory[item_type] = {}

        if item_id in inventory[item_type]:
            inventory[item_type][item_id] += quantity
        else:
            inventory[item_type][item_id] = quantity

        self.set_inventory(inventory)

    def remove_inventory_item(self, item_type, item_id, quantity=1):
        """Remove item from player inventory"""
        inventory = self.get_inventory()
        if item_type in inventory and item_id in inventory[item_type]:
            inventory[item_type][item_id] -= quantity
            if inventory[item_type][item_id] <= 0:
                del inventory[item_type][item_id]
            if not inventory[item_type]:
                del inventory[item_type]
            self.set_inventory(inventory)
            return True
        return False

    def get_inventory_item_count(self, item_type, item_id):
        """Get count of specific item in inventory"""
        inventory = self.get_inventory()
        return inventory.get(item_type, {}).get(item_id, 0)

    def get_shop_purchases(self):
        """Get all shop purchases made by player"""
        try:
            from models import ShopPurchase
            return ShopPurchase.query.filter_by(player_id=self.id).all()
        except Exception:
            return []

    def get_badges(self):
        """Get all badges assigned to player (for template compatibility)"""
        try:
            return PlayerBadge.query.filter_by(player_id=self.id).all()
        except Exception:
            return []

    def __repr__(self):
        return f'<Player {self.nickname}: Level {self.level} ({self.experience} XP)>'

    @property
    def kd_ratio(self):
        """Calculate kill/death ratio"""
        if self.deaths == 0:
            return self.kills if self.kills > 0 else 0
        return round(self.kills / self.deaths, 2)

    @property
    def fkd_ratio(self):
        """Calculate final kill/death ratio"""
        if self.final_deaths == 0:
            return self.final_kills if self.final_kills > 0 else 0
        return round(self.final_kills / self.final_deaths, 2)

    @property
    def win_rate(self):
        """Calculate win rate percentage"""
        if self.games_played == 0:
            return 0
        return round((self.wins / self.games_played) * 100, 1)

    @property
    def level(self):
        """Calculate player level based on Hypixel experience system"""
        # Hypixel level thresholds
        level_thresholds = [
            0, 10000, 22500, 37500, 55000, 75000, 97500, 122500, 150000, 180000,
            212500, 247500, 285000, 325000, 367500, 412500, 460000, 510000, 562500, 617500,
            675000, 735000, 797500, 862500, 930000, 1000000, 1072500, 1147500, 1225000, 1305000,
            1387500, 1472500, 1560000, 1650000, 1742500, 1837500, 1935000, 2035000, 2137500, 2242500,
            2350000, 2460000, 2572500, 2687500, 2805000, 2925000, 3047500, 3172500, 3300000, 3430000,
            3562500, 3697500, 3835000, 3975000, 4117500, 4262500, 4410000, 4560000, 4712500, 4867500,
            5025000, 5185000, 5347500, 5512500, 5680000, 5850000, 6022500, 6197500, 6375000, 6555000,
            6737500, 6922500, 7110000, 7300000, 7492500, 7687500, 7885000, 8085000, 8287500, 8492500,
            8700000, 8910000, 9122500, 9337500, 9555000, 9775000, 9997500, 10222500, 10450000, 10680000,
            10912500, 11147500, 11385000, 11625000, 11867500, 12112500, 12360000, 12610000, 12862500, 13117500
        ]

        for level, threshold in enumerate(level_thresholds, 1):
            if self.experience < threshold:
                return max(1, level - 1)

        # For levels 100+, each level requires 2500 more XP than the previous
        if self.experience >= 13117500:
            additional_levels = (self.experience - 13117500) // 2500
            return min(1000, 100 + additional_levels)

        return 100

    @property
    def level_progress(self):
        """Calculate progress to next level as percentage"""
        current_level = self.level
        if current_level >= 1000:
            return 100

        # Hypixel level thresholds
        level_thresholds = [
            0, 10000, 22500, 37500, 55000, 75000, 97500, 122500, 150000, 180000,
            212500, 247500, 285000, 325000, 367500, 412500, 460000, 510000, 562500, 617500,
            675000, 735000, 797500, 862500, 930000, 1000000, 1072500, 1147500, 1225000, 1305000,
            1387500, 1472500, 1560000, 1650000, 1742500, 1837500, 1935000, 2035000, 2137500, 2242500,
            2350000, 2460000, 2572500, 2687500, 2805000, 2925000, 3047500, 3172500, 3300000, 3430000,
            3562500, 3697500, 3835000, 3975000, 4117500, 4262500, 4410000, 4560000, 4712500, 4867500,
            5025000, 5185000, 5347500, 5512500, 5680000, 5850000, 6022500, 6197500, 6375000, 6555000,
            6737500, 6922500, 7110000, 7300000, 7492500, 7687500, 7885000, 8085000, 8287500, 8492500,
            8700000, 8910000, 9122500, 9337500, 9555000, 9775000, 9997500, 10222500, 10450000, 10680000,
            10912500, 11147500, 11385000, 11625000, 11867500, 12112500, 12360000, 12610000, 12862500, 13117500
        ]

        if current_level <= 100:
            current_threshold = level_thresholds[current_level - 1] if current_level > 0 else 0
            next_threshold = level_thresholds[current_level] if current_level < len(level_thresholds) else level_thresholds[-1] + 2500
        else:
            # For levels 100+
            current_threshold = 13117500 + (current_level - 100) * 2500
            next_threshold = 13117500 + (current_level - 99) * 2500

        if next_threshold == current_threshold:
            return 100

        progress = ((self.experience - current_threshold) / (next_threshold - current_threshold)) * 100
        return min(100, max(0, round(progress, 1)))

    @property
    def total_resources(self):
        """Calculate total resources collected"""
        return self.iron_collected + self.gold_collected + self.diamond_collected + self.emerald_collected

    @property
    def star_rating(self):
        """Calculate star rating based on overall performance"""
        # Complex formula considering multiple factors
        base_score = 0

        # XP contribution (0-20 points)
        base_score += min(20, self.level * 0.5)

        # K/D ratio contribution (0-15 points)
        base_score += min(15, self.kd_ratio * 3)

        # Win rate contribution (0-15 points)
        base_score += min(15, self.win_rate * 0.15)

        # Bed breaking contribution (0-10 points)
        base_score += min(10, self.beds_broken * 0.1)

        # Final kills contribution (0-10 points)
        base_score += min(10, self.final_kills * 0.05)

        # Games played bonus (0-5 points for activity)
        base_score += min(5, self.games_played * 0.01)

        # Convert to 1-5 star rating
        return min(5, max(1, round(base_score / 13)))

    @property
    def minecraft_skin_url(self):
        """Get Minecraft skin URL based on skin type and settings"""
        # Use custom avatar if set
        if self.custom_avatar_url:
            return self.custom_avatar_url

        if self.skin_type == 'custom' and self.skin_url:
            return self.skin_url
        elif self.skin_type == 'steve':
            return 'https://mc-heads.net/avatar/steve/128'
        elif self.skin_type == 'alex':
            return 'https://mc-heads.net/avatar/alex/128'
        elif self.skin_type == 'auto':
            # Auto mode: try to get skin by nickname first, then fallback
            if self.nickname:
                return f'https://mc-heads.net/avatar/{self.nickname}/128'
            else:
                return 'https://mc-heads.net/avatar/steve/128'
        elif self.is_premium and self.nickname:
            # Try to get premium skin by nickname
            return f'https://mc-heads.net/avatar/{self.nickname}/128'
        else:
            # Default to steve/alex randomly based on nickname hash
            import hashlib
            hash_val = int(hashlib.md5(self.nickname.encode()).hexdigest(), 16)
            default_skin = 'alex' if hash_val % 2 else 'steve'
            return f'https://mc-heads.net/avatar/{default_skin}/128'

    def set_custom_skin(self, namemc_url):
        """Set custom skin from NameMC URL"""
        if namemc_url and 'namemc.com' in namemc_url:
            # Extract UUID or username from NameMC URL
            try:
                import re
                # Extract username from NameMC URL
                match = re.search(r'namemc\.com/profile/([^/]+)', namemc_url)
                if match:
                    username = match.group(1)
                    # Use Crafatar to get skin
                    self.skin_url = f'https://crafatar.com/avatars/{username}?size=128'
                    self.skin_type = 'custom'
                    return True
            except:
                pass
        return False

    @classmethod
    def get_leaderboard(cls, sort_by='experience', limit=50, offset=0):
        """Get top players ordered by specified field with optimized queries"""
        try:
            limit = min(max(1, limit), 100)
            offset = max(0, offset)

            # Базовый запрос с eager loading для связанных объектов
            from sqlalchemy.orm import joinedload, selectinload
            base_query = cls.query.options(
                joinedload(cls.selected_theme),
                selectinload(cls.player_badges)
            )

            # Оптимизированные запросы по полям с индексами
            sort_mapping = {
                'experience': cls.experience.desc(),
                'kills': cls.kills.desc(),
                'final_kills': cls.final_kills.desc(),
                'beds_broken': cls.beds_broken.desc(),
                'wins': cls.wins.desc(),
                'karma': cls.karma.desc()
            }

            if sort_by in sort_mapping:
                return base_query.order_by(sort_mapping[sort_by]).offset(offset).limit(limit).all()

            # Для вычисляемых полям используем более эффективные запросы
            elif sort_by == 'kd_ratio':
                return base_query.filter(cls.deaths > 0).order_by(
                    (cls.kills / cls.deaths).desc()
                ).offset(offset).limit(limit).all()
            elif sort_by == 'win_rate':
                return base_query.filter(cls.games_played > 0).order_by(
                    (cls.wins * 100.0 / cls.games_played).desc()
                ).offset(offset).limit(limit).all()
            else:
                return base_query.order_by(cls.experience.desc()).offset(offset).limit(limit).all()

        except Exception as e:
            from app import app
            app.logger.error(f"Error getting leaderboard: {e}")
            return []

    @classmethod
    def search_players(cls, query, limit=50, offset=0):
        """Search players by nickname with error handling"""
        try:
            if not query or len(query.strip()) < 1:
                return []

            limit = min(max(1, limit), 100)
            offset = max(0, offset)
            query = query.strip()[:50]  # Limit query length

            return cls.query.filter(cls.nickname.ilike(f'%{query}%')).offset(offset).limit(limit).all()
        except Exception as e:
            from app import app
            app.logger.error(f"Error searching players: {e}")
            return []

    @classmethod
    def get_statistics(cls):
        """Get overall leaderboard statistics with caching"""
        return cls._get_cached_statistics()

    @classmethod
    def _get_cached_statistics(cls):
        """Get cached statistics with Redis support"""
        from cache import Cache

        # Пытаемся получить из Redis кэша
        cached_stats = Cache.get('player_statistics')
        if cached_stats:
            return cached_stats
        try:
            total_players = cls.query.count()
        except Exception as e:
            from app import app
            if "no such column" in str(e).lower():
                app.logger.error(f"Database schema error in statistics: {e}")
                app.logger.info("Database schema needs to be updated. Please restart the application.")
            else:
                app.logger.error(f"Error getting statistics: {e}")
            # Return empty statistics if there's an error
            return {
                'total_players': 0,
                'total_kills': 0,
                'total_deaths': 0,
                'total_games': 0,
                'total_wins': 0,
                'total_beds_broken': 0,
                'average_level': 0,
                'total_coins': 0,
                'total_reputation': 0,
                'total_karma': 0, # Added karma
                'average_coins': 0,
                'average_reputation': 0,
                'average_karma': 0, # Added karma
                'top_player': None,
                'richest_player': None,
                'most_reputable_player': None,
                'most_karma_player': None # Added karma
            }

        if total_players == 0:
            return {
                'total_players': 0,
                'total_kills': 0,
                'total_deaths': 0,
                'total_games': 0,
                'total_wins': 0,
                'total_beds_broken': 0,
                'average_level': 0,
                'total_coins': 0,
                'total_reputation': 0,
                'total_karma': 0, # Added karma
                'average_coins': 0,
                'average_reputation': 0,
                'average_karma': 0, # Added karma
                'top_player': None,
                'richest_player': None,
                'most_reputable_player': None,
                'most_karma_player': None # Added karma
            }

        # Оптимизированный запрос статистики одним запросом включая все режимы
        from sqlalchemy import case
        stats_result = db.session.query(
            func.count(cls.id).label('total_players'),
            # Bedwars stats
            func.sum(cls.kills).label('total_kills'),
            func.sum(cls.deaths).label('total_deaths'),
            func.sum(cls.games_played).label('total_games'),
            func.sum(cls.wins).label('total_wins'),
            func.sum(cls.beds_broken).label('total_beds_broken'),
            # KitPVP stats
            func.sum(cls.kitpvp_kills).label('total_kitpvp_kills'),
            func.sum(cls.kitpvp_deaths).label('total_kitpvp_deaths'),
            func.sum(cls.kitpvp_games).label('total_kitpvp_games'),
            # SkyWars stats
            func.sum(cls.skywars_wins).label('total_skywars_wins'),
            func.sum(cls.skywars_kills).label('total_skywars_kills'),
            # Sumo stats
            func.sum(cls.sumo_games_played).label('total_sumo_games'),
            func.sum(cls.sumo_wins).label('total_sumo_wins'),
            func.sum(cls.sumo_kills).label('total_sumo_kills'),
            # Economy
            func.sum(cls.coins).label('total_coins'),
            func.sum(cls.reputation).label('total_reputation'),
            func.sum(cls.karma).label('total_karma'),
            func.avg(cls.experience).label('average_experience'),
            func.avg(cls.coins).label('average_coins'),
            func.avg(cls.reputation).label('average_reputation'),
            func.avg(cls.karma).label('average_karma'),
            func.sum(case((cls.karma > 0, 1), else_=0)).label('players_with_karma')
        ).first()

        stats = stats_result
        total_players = stats.total_players

        top_player = cls.query.order_by(cls.experience.desc()).first()
        richest_player = cls.query.order_by(cls.coins.desc()).first()
        most_reputable_player = cls.query.order_by(cls.reputation.desc()).first()
        most_karma_player = cls.query.order_by(cls.karma.desc()).first() # Added karma player

        # Additional karma statistics
        players_with_karma = cls.query.filter(cls.karma > 0).count()
        karma_percentage = round((players_with_karma / total_players * 100), 1) if total_players > 0 else 0

        result = {
            'total_players': total_players,
            # Bedwars
            'total_kills': int(stats.total_kills) if stats and stats.total_kills else 0,
            'total_deaths': int(stats.total_deaths) if stats and stats.total_deaths else 0,
            'total_games': int(stats.total_games) if stats and stats.total_games else 0,
            'total_wins': int(stats.total_wins) if stats and stats.total_wins else 0,
            'total_beds_broken': int(stats.total_beds_broken) if stats and stats.total_beds_broken else 0,
            # KitPVP
            'total_kitpvp_kills': int(stats.total_kitpvp_kills) if stats and stats.total_kitpvp_kills else 0,
            'total_kitpvp_deaths': int(stats.total_kitpvp_deaths) if stats and stats.total_kitpvp_deaths else 0,
            'total_kitpvp_games': int(stats.total_kitpvp_games) if stats and stats.total_kitpvp_games else 0,
            # SkyWars
            'total_skywars_wins': int(stats.total_skywars_wins) if stats and stats.total_skywars_wins else 0,
            'total_skywars_kills': int(stats.total_skywars_kills) if stats and stats.total_skywars_kills else 0,
            # Sumo
            'total_sumo_games': int(stats.total_sumo_games) if stats and stats.total_sumo_games else 0,
            'total_sumo_wins': int(stats.total_sumo_wins) if stats and stats.total_sumo_wins else 0,
            'total_sumo_kills': int(stats.total_sumo_kills) if stats and stats.total_sumo_kills else 0,
            # Economy
            'total_coins': int(stats.total_coins) if stats and stats.total_coins else 0,
            'total_reputation': int(stats.total_reputation) if stats and stats.total_reputation else 0,
            'total_karma': int(stats.total_karma) if stats and stats.total_karma else 0,
            'average_level': round(stats.average_experience / 1000) if stats and stats.average_experience else 0,
            'average_coins': round(stats.average_coins) if stats and stats.average_coins else 0,
            'average_reputation': round(stats.average_reputation) if stats and stats.average_reputation else 0,
            'average_karma': round(stats.average_karma) if stats and stats.average_karma else 0,
            'top_player': top_player.nickname if top_player else None,
            'richest_player': richest_player.nickname if richest_player else None,
            'most_reputable_player': most_reputable_player.nickname if most_reputable_player else None,
            'most_karma_player': most_karma_player.nickname if most_karma_player else None,
            'karma_percentage': karma_percentage,
            # Gamemode leaders
            'top_kitpvp_player': cls.query.filter(cls.kitpvp_kills > 0).order_by(cls.kitpvp_kills.desc()).first(),
            'top_skywars_player': cls.query.filter(cls.skywars_wins > 0).order_by(cls.skywars_wins.desc()).first(),
            'top_sumo_player': cls.query.filter(cls.sumo_wins > 0).order_by(cls.sumo_wins.desc()).first()
        }

        # Cache result for 5 minutes
        from cache import Cache
        Cache.set('player_statistics', result, 300)
        return result

    @classmethod
    def clear_statistics_cache(cls):
        """Clear statistics cache when data changes"""
        try:
            from cache import Cache
            Cache.delete('player_statistics')
            Cache.clear_pattern('leaderboard:*')
            Cache.clear_pattern('player:*')
        except Exception:
            # Cache module may not be available
            pass




# Gamemode-specific statistics models

class BedwarsStats(db.Model):
    """Bedwars statistics for individual players"""

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False, index=True)

    # Core Bedwars stats
    kills = db.Column(db.Integer, default=0, nullable=False, index=True)
    final_kills = db.Column(db.Integer, default=0, nullable=False, index=True)
    deaths = db.Column(db.Integer, default=0, nullable=False)
    final_deaths = db.Column(db.Integer, default=0, nullable=False)
    beds_broken = db.Column(db.Integer, default=0, nullable=False, index=True)
    beds_lost = db.Column(db.Integer, default=0, nullable=False)
    games_played = db.Column(db.Integer, default=0, nullable=False)
    wins = db.Column(db.Integer, default=0, nullable=False, index=True)
    winstreak = db.Column(db.Integer, default=0, nullable=False)

    # Resources
    iron_collected = db.Column(db.Integer, default=0, nullable=False)
    gold_collected = db.Column(db.Integer, default=0, nullable=False)
    diamond_collected = db.Column(db.Integer, default=0, nullable=False)
    emerald_collected = db.Column(db.Integer, default=0, nullable=False)
    items_purchased = db.Column(db.Integer, default=0, nullable=False)

    # Rating and experience
    experience = db.Column(db.Integer, default=0, nullable=False, index=True)
    rating = db.Column(db.Integer, default=800, nullable=False, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    player = db.relationship('Player', backref='bedwars_stats')

    @property
    def kd_ratio(self):
        if self.deaths == 0:
            return self.kills if self.kills > 0 else 0
        return round(self.kills / self.deaths, 2)

    @property
    def fkd_ratio(self):
        if self.final_deaths == 0:
            return self.final_kills if self.final_kills > 0 else 0
        return round(self.final_kills / self.final_deaths, 2)

    @property
    def win_rate(self):
        if self.games_played == 0:
            return 0
        return round((self.wins / self.games_played) * 100, 1)

    @property
    def level(self):
        # Simplified level calculation for Bedwars
        return max(1, self.experience // 10000)

    def to_dict(self):
        return {
            'player_id': self.player_id,
            'kills': self.kills,
            'final_kills': self.final_kills,
            'deaths': self.deaths,
            'final_deaths': self.final_deaths,
            'beds_broken': self.beds_broken,
            'beds_lost': self.beds_lost,
            'games_played': self.games_played,
            'wins': self.wins,
            'winstreak': self.winstreak,
            'kd_ratio': self.kd_ratio,
            'fkd_ratio': self.fkd_ratio,
            'win_rate': self.win_rate,
            'level': self.level,
            'experience': self.experience,
            'rating': self.rating,
            'iron_collected': self.iron_collected,
            'gold_collected': self.gold_collected,
            'diamond_collected': self.diamond_collected,
            'emerald_collected': self.emerald_collected,
            'items_purchased': self.items_purchased
        }

class KitPvPStats(db.Model):
    """KitPvP statistics for individual players"""

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False, index=True)

    # Core KitPvP stats
    kills = db.Column(db.Integer, default=0, nullable=False, index=True)
    deaths = db.Column(db.Integer, default=0, nullable=False)
    assists = db.Column(db.Integer, default=0, nullable=False)
    killstreak = db.Column(db.Integer, default=0, nullable=False)
    best_killstreak = db.Column(db.Integer, default=0, nullable=False)

    # Damage and healing
    damage_dealt = db.Column(db.Integer, default=0, nullable=False)
    damage_taken = db.Column(db.Integer, default=0, nullable=False)
    healing_done = db.Column(db.Integer, default=0, nullable=False)

    # Kit usage
    favorite_kit = db.Column(db.String(50), default='Warrior', nullable=False)
    kits_unlocked = db.Column(db.Integer, default=1, nullable=False)

    # Rating and experience
    experience = db.Column(db.Integer, default=0, nullable=False, index=True)
    rating = db.Column(db.Integer, default=1000, nullable=False, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    player = db.relationship('Player', backref='kitpvp_stats')

    @property
    def kd_ratio(self):
        if self.deaths == 0:
            return self.kills if self.kills > 0 else 0
        return round(self.kills / self.deaths, 2)

    @property
    def level(self):
        return max(1, self.experience // 5000)

    def to_dict(self):
        return {
            'player_id': self.player_id,
            'kills': self.kills,
            'deaths': self.deaths,
            'kd_ratio': self.kd_ratio
        }

class SkyWarsStats(db.Model):
    """SkyWars statistics for individual players"""

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False, index=True)

    # Core SkyWars stats
    kills = db.Column(db.Integer, default=0, nullable=False, index=True)
    deaths = db.Column(db.Integer, default=0, nullable=False)
    assists = db.Column(db.Integer, default=0, nullable=False)
    games_played = db.Column(db.Integer, default=0, nullable=False)
    wins = db.Column(db.Integer, default=0, nullable=False, index=True)
    winstreak = db.Column(db.Integer, default=0, nullable=False)

    # SkyWars specific
    chests_opened = db.Column(db.Integer, default=0, nullable=False)
    items_enchanted = db.Column(db.Integer, default=0, nullable=False)
    arrows_shot = db.Column(db.Integer, default=0, nullable=False)
    arrows_hit = db.Column(db.Integer, default=0, nullable=False)

    # Rating and experience
    experience = db.Column(db.Integer, default=0, nullable=False, index=True)
    rating = db.Column(db.Integer, default=1200, nullable=False, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    player = db.relationship('Player', backref='skywars_stats')

    @property
    def kd_ratio(self):
        if self.deaths == 0:
            return self.kills if self.kills > 0 else 0
        return round(self.kills / self.deaths, 2)

    @property
    def win_rate(self):
        if self.games_played == 0:
            return 0
        return round((self.wins / self.games_played) * 100, 1)

    @property
    def accuracy(self):
        if self.arrows_shot == 0:
            return 0
        return round((self.arrows_hit / self.arrows_shot) * 100, 1)

    @property
    def level(self):
        return max(1, self.experience // 7500)

    def to_dict(self):
        return {
            'player_id': self.player_id,
            'kills': self.kills,
            'deaths': self.deaths,
            'assists': self.assists,
            'games_played': self.games_played,
            'wins': self.wins,
            'winstreak': self.winstreak,
            'kd_ratio': self.kd_ratio,
            'win_rate': self.win_rate,
            'level': self.level,
            'experience': self.experience,
            'rating': self.rating,
            'chests_opened': self.chests_opened,
            'items_enchanted': self.items_enchanted,
            'arrows_shot': self.arrows_shot,
            'arrows_hit': self.arrows_hit,
            'accuracy': self.accuracy
        }

class BridgeFightStats(db.Model):
    """BridgeFight statistics for individual players"""

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False, index=True)

    # Core BridgeFight stats
    games_played = db.Column(db.Integer, default=0, nullable=False)
    wins = db.Column(db.Integer, default=0, nullable=False, index=True)
    losses = db.Column(db.Integer, default=0, nullable=False)
    goals = db.Column(db.Integer, default=0, nullable=False, index=True)
    winstreak = db.Column(db.Integer, default=0, nullable=False)

    # Bridge specific
    blocks_placed = db.Column(db.Integer, default=0, nullable=False)
    bridges_built = db.Column(db.Integer, default=0, nullable=False)
    fastest_bridge = db.Column(db.Float, default=0.0, nullable=False)  # seconds

    # Rating and experience
    experience = db.Column(db.Integer, default=0, nullable=False, index=True)
    rating = db.Column(db.Integer, default=1000, nullable=False, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    player = db.relationship('Player', backref='bridgefight_stats')

    @property
    def win_rate(self):
        if self.games_played == 0:
            return 0
        return round((self.wins / self.games_played) * 100, 1)

    @property
    def goals_per_game(self):
        if self.games_played == 0:
            return 0
        return round(self.goals / self.games_played, 2)

    @property
    def level(self):
        return max(1, self.experience // 6000)

    def to_dict(self):
        return {
            'player_id': self.player_id,
            'games_played': self.games_played,
            'wins': self.wins,
            'losses': self.losses,
            'goals': self.goals,
            'winstreak': self.winstreak,
            'win_rate': self.win_rate,
            'goals_per_game': self.goals_per_game,
            'level': self.level,
            'experience': self.experience,
            'rating': self.rating,
            'blocks_placed': self.blocks_placed,
            'bridges_built': self.bridges_built,
            'fastest_bridge': self.fastest_bridge
        }

class SumoStats(db.Model):
    """Sumo statistics for individual players"""

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False, index=True)

    # Core Sumo stats
    games_played = db.Column(db.Integer, default=0, nullable=False)
    wins = db.Column(db.Integer, default=0, nullable=False, index=True)
    losses = db.Column(db.Integer, default=0, nullable=False)
    winstreak = db.Column(db.Integer, default=0, nullable=False)
    best_winstreak = db.Column(db.Integer, default=0, nullable=False)

    # Sumo specific
    knockouts = db.Column(db.Integer, default=0, nullable=False)
    time_survived = db.Column(db.Integer, default=0, nullable=False)  # seconds

    # Rating and experience
    experience = db.Column(db.Integer, default=0, nullable=False, index=True)
    rating = db.Column(db.Integer, default=900, nullable=False, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    player = db.relationship('Player', backref='sumo_stats')

    @property
    def win_rate(self):
        if self.games_played == 0:
            return 0
        return round((self.wins / self.games_played) * 100, 1)

    @property
    def avg_survival_time(self):
        if self.games_played == 0:
            return 0
        return round(self.time_survived / self.games_played, 1)

    @property
    def level(self):
        return max(1, self.experience // 4000)

    def to_dict(self):
        return {
            'player_id': self.player_id,
            'games_played': self.games_played,
            'wins': self.wins,
            'losses': self.losses,
            'winstreak': self.winstreak,
            'best_winstreak': self.best_winstreak,
            'win_rate': self.win_rate,
            'level': self.level,
            'experience': self.experience,
            'rating': self.rating,
            'knockouts': self.knockouts,
            'time_survived': self.time_survived,
            'avg_survival_time': self.avg_survival_time
        }

class FireballFightStats(db.Model):
    """Fireball Fight statistics for individual players"""

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False, index=True)

    # Core Fireball Fight stats
    games_played = db.Column(db.Integer, default=0, nullable=False)
    wins = db.Column(db.Integer, default=0, nullable=False, index=True)
    losses = db.Column(db.Integer, default=0, nullable=False)
    kills = db.Column(db.Integer, default=0, nullable=False, index=True)
    deaths = db.Column(db.Integer, default=0, nullable=False)

    # Fireball specific
    fireballs_shot = db.Column(db.Integer, default=0, nullable=False)
    fireballs_hit = db.Column(db.Integer, default=0, nullable=False)

    # Rating and experience
    experience = db.Column(db.Integer, default=0, nullable=False, index=True)
    rating = db.Column(db.Integer, default=1100, nullable=False, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    player = db.relationship('Player', backref='fireballfight_stats')

    @property
    def win_rate(self):
        if self.games_played == 0:
            return 0
        return round((self.wins / self.games_played) * 100, 1)

    @property
    def kd_ratio(self):
        if self.deaths == 0:
            return self.kills if self.kills > 0 else 0
        return round(self.kills / self.deaths, 2)

    @property
    def accuracy(self):
        if self.fireballs_shot == 0:
            return 0
        return round((self.fireballs_hit / self.fireballs_shot) * 100, 1)

    @property
    def level(self):
        return max(1, self.experience // 5500)

    def to_dict(self):
        return {
            'player_id': self.player_id,
            'games_played': self.games_played,
            'wins': self.wins,
            'losses': self.losses,
            'kills': self.kills,
            'deaths': self.deaths,
            'kd_ratio': self.kd_ratio,
            'win_rate': self.win_rate,
            'level': self.level,
            'experience': self.experience,
            'rating': self.rating,
            'fireballs_shot': self.fireballs_shot,
            'fireballs_hit': self.fireballs_hit,
            'accuracy': self.accuracy
        }

# Utility class for gamemode management
class GameModeManager:
    """Utility class for managing different game modes and their statistics"""

    GAMEMODE_MODELS = {
        'bedwars': BedwarsStats,
        'kitpvp': KitPvPStats,
        'skywars': SkyWarsStats,
        'bridgefight': BridgeFightStats,
        'sumo': SumoStats,
        'fireball_fight': FireballFightStats
    }

    GAMEMODE_NAMES = {
        'bedwars': 'Bedwars',
        'kitpvp': 'KitPvP',
        'skywars': 'SkyWars',
        'bridgefight': 'BridgeFight',
        'sumo': 'Sumo',
        'fireball_fight': 'Fireball Fight'
    }

    @classmethod
    def get_player_stats(cls, player_id, gamemode):
        """Get player statistics for specific gamemode"""
        if gamemode not in cls.GAMEMODE_MODELS:
            return None

        model = cls.GAMEMODE_MODELS[gamemode]
        return model.query.filter_by(player_id=player_id).first()

    @classmethod
    def get_or_create_stats(cls, player_id, gamemode):
        """Get or create player statistics for specific gamemode"""
        if gamemode not in cls.GAMEMODE_MODELS:
            return None

        model = cls.GAMEMODE_MODELS[gamemode]
        stats = model.query.filter_by(player_id=player_id).first()

        if not stats:
            stats = model(player_id=player_id)
            db.session.add(stats)
            db.session.commit()

        return stats

    @classmethod
    def get_gamemode_leaderboard(cls, gamemode, sort_by='rating', limit=50):
        """Get leaderboard for specific gamemode"""
        if gamemode not in cls.GAMEMODE_MODELS:
            return []

        model = cls.GAMEMODE_MODELS[gamemode]

        # Define sorting options for each gamemode
        sort_options = {
            'rating': model.rating.desc(),
            'experience': model.experience.desc(),
            'level': model.experience.desc(),  # Level is calculated from experience
        }

        # Add gamemode-specific sort options
        if hasattr(model, 'kills'):
            sort_options['kills'] = model.kills.desc()
        if hasattr(model, 'wins'):
            sort_options['wins'] = model.wins.desc()
        if hasattr(model, 'goals'):
            sort_options['goals'] = model.goals.desc()

        sort_column = sort_options.get(sort_by, model.rating.desc())

        return model.query.join(Player).order_by(sort_column).limit(limit).all()

    @classmethod
    def clear_statistics_cache(cls):
        """Clear statistics cache when data changes"""
        from cache import Cache
        Cache.delete('player_statistics')
        Cache.clear_pattern('leaderboard:*')
        Cache.clear_pattern('player:*')

    def calculate_auto_experience(self):
        """Calculate experience based on player statistics (improved formula)"""
        base_xp = 0

        # XP from kills (15 XP per kill - increased)
        base_xp += self.kills * 15

        # XP from final kills (75 XP per final kill - increased)
        base_xp += self.final_kills * 75

        # XP from beds broken (150 XP per bed - increased)
        base_xp += self.beds_broken * 150

        # XP from wins (300 XP per win - increased)
        base_xp += self.wins * 300

        # XP from games played (40 XP per game - increased)
        base_xp += self.games_played * 40

        # XP from resources collected (1 XP per 8 resources - improved ratio)
        base_xp += self.total_resources // 8

        # Bonus XP for good performance
        if self.kd_ratio >= 3.0:
            base_xp = int(base_xp * 1.4)  # 40% bonus for excellent K/D
        elif self.kd_ratio >= 2.0:
            base_xp = int(base_xp * 1.25)  # 25% bonus
        elif self.kd_ratio >= 1.5:
            base_xp = int(base_xp * 1.15)  # 15% bonus

        if self.win_rate >= 85:
            base_xp = int(base_xp * 1.5)  # 50% bonus for high win rate
        elif self.win_rate >= 75:
            base_xp = int(base_xp * 1.35)  # 35% bonus
        elif self.win_rate >= 50:
            base_xp = int(base_xp * 1.2)  # 20% bonus

        # Bonus for high bed destruction rate
        if self.games_played > 0:
            bed_rate = self.beds_broken / self.games_played
            if bed_rate >= 1.0:
                base_xp = int(base_xp * 1.2)  # 20% bonus for bed breaking

        return base_xp

    def update_stats(self, **kwargs):
        """Update player statistics and auto-calculate experience"""
        old_stats = {
            'kills': self.kills,
            'final_kills': self.final_kills,
            'beds_broken': self.beds_broken,
            'wins': self.wins,
            'games_played': self.games_played
        }

        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

        # Only auto-update XP if stats changed significantly
        if any(getattr(self, key) != old_stats.get(key, 0) for key in old_stats):
            # Don't override manually set experience, just set a baseline
            calculated_xp = self.calculate_auto_experience()
            if self.experience < calculated_xp:
                self.experience = calculated_xp

        self.last_updated = datetime.utcnow()
        db.session.commit()
        return True

    @classmethod
    def add_player(cls, nickname, kills=0, final_kills=0, deaths=0, final_deaths=0, beds_broken=0,
                   games_played=0, wins=0, experience=0, role='Игрок', server_ip='',
                   iron_collected=0, gold_collected=0, diamond_collected=0,
                   emerald_collected=0, items_purchased=0, coins=0, reputation=0, karma=0):
        """Add a new player to the leaderboard"""
        player = cls(
            nickname=nickname,
            kills=kills,
            final_kills=final_kills,
            deaths=deaths,
            final_deaths=final_deaths,
            beds_broken=beds_broken,
            games_played=games_played,
            wins=wins,
            experience=experience,
            role=role,
            server_ip=server_ip,
            iron_collected=iron_collected,
            gold_collected=gold_collected,
            diamond_collected=diamond_collected,
            emerald_collected=emerald_collected,
            items_purchased=items_purchased,
            coins=coins,
            reputation=reputation,
            karma=karma # Added karma
        )
        db.session.add(player)
        db.session.commit()
        return player


class Quest(db.Model):
    """Quest system for gamification"""

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), nullable=False)  # kills, beds, wins, etc.
    target_value = db.Column(db.Integer, nullable=False)
    reward_xp = db.Column(db.Integer, default=0)
    reward_coins = db.Column(db.Integer, default=0)
    reward_reputation = db.Column(db.Integer, default=0)
    reward_karma = db.Column(db.Integer, default=0)
    # reward_title = db.Column(db.String(100), nullable=True) # reward_title removed - titles should be separate system
    icon = db.Column(db.String(50), default='fas fa-trophy')
    difficulty = db.Column(db.String(20), default='medium', nullable=False)  # easy, medium, hard, epic
    quest_category = db.Column(db.String(20), default='permanent', nullable=False)  # daily, weekly, monthly, thematic, mythic, permanent
    is_active = db.Column(db.Boolean, default=True)
    is_repeatable = db.Column(db.Boolean, default=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_refresh = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship with player quest progress
    player_quests = db.relationship('PlayerQuest', backref='quest', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Quest {self.title}>'

    @property
    def completion_rate(self):
        """Calculate overall completion rate"""
        total_attempts = PlayerQuest.query.filter_by(quest_id=self.id).count()
        if total_attempts == 0:
            return 0
        completed = PlayerQuest.query.filter_by(quest_id=self.id, is_completed=True).count()
        return round((completed / total_attempts) * 100, 1)

    @classmethod
    def get_active_quests(cls):
        """Get all active quests"""
        return cls.query.filter_by(is_active=True).all()

    @classmethod
    def refresh_timed_quests(cls):
        """Refresh daily, weekly, and monthly quests"""
        from datetime import datetime, timedelta, date

        current_time = datetime.utcnow()
        current_date = current_time.date()

        # Check and refresh daily quests (check if it's a new day)
        daily_quests = cls.query.filter_by(quest_category='daily', is_active=True).all()
        for quest in daily_quests:
            if not quest.last_refresh or quest.last_refresh.date() < current_date:
                quest.last_refresh = current_time
                # Reset all player progress for this quest
                PlayerQuest.query.filter_by(quest_id=quest.id).update({
                    'is_completed': False,
                    'is_accepted': False,
                    'current_progress': 0,
                    'baseline_value': 0
                })

        # Check and refresh weekly quests (check if it's a new week - Monday)
        weekly_quests = cls.query.filter_by(quest_category='weekly', is_active=True).all()
        for quest in weekly_quests:
            if not quest.last_refresh:
                quest.last_refresh = current_time
                continue

            # Calculate start of current week (Monday)
            current_monday = current_date - timedelta(days=current_date.weekday())

            # Calculate start of week when quest was last refreshed
            last_refresh_date = quest.last_refresh.date()
            last_refresh_monday = last_refresh_date - timedelta(days=last_refresh_date.weekday())

            # If we've crossed into a new week, reset the quest
            if last_refresh_monday < current_monday:
                quest.last_refresh = current_time
                PlayerQuest.query.filter_by(quest_id=quest.id).update({
                    'is_completed': False,
                    'is_accepted': False,
                    'current_progress': 0,
                    'baseline_value': 0
                })

        # Check and refresh monthly quests (check if it's a new month)
        monthly_quests = cls.query.filter_by(quest_category='monthly', is_active=True).all()
        for quest in monthly_quests:
            if not quest.last_refresh:
                quest.last_refresh = current_time
                continue

            if (quest.last_refresh.year < current_time.year or
                (quest.last_refresh.year == current_time.year and quest.last_refresh.month < current_time.month)):
                quest.last_refresh = current_time
                PlayerQuest.query.filter_by(quest_id=quest.id).update({
                    'is_completed': False,
                    'is_accepted': False,
                    'current_progress': 0,
                    'baseline_value': 0
                })

        db.session.commit()

    @classmethod
    def create_default_quests(cls):
        """Create default quests for the game"""
        # Permanent quests
        permanent_quests = [
            {
                'title': 'Первая кровь',
                'description': 'Убейте 10 игроков в режиме Bedwars',
                'type': 'kills',
                'target_value': 10,
                'reward_xp': 1000,
                'reward_coins': 250,
                'reward_reputation': 10,
                'reward_karma': 2,
                # 'reward_title': 'Воин', # reward_title removed
                'icon': 'fas fa-sword',
                'difficulty': 'easy',
                'quest_category': 'permanent',
                'is_repeatable': False
            },
            {
                'title': 'Разрушитель кроватей',
                'description': 'Сломайте 5 кроватей противников',
                'type': 'beds_broken',
                'target_value': 5,
                'reward_xp': 1500,
                'reward_coins': 300,
                'reward_reputation': 15,
                'reward_karma': 2,
                # 'reward_title': 'Разрушитель', # reward_title removed
                'icon': 'fas fa-bed',
                'difficulty': 'easy',
                'quest_category': 'permanent',
                'is_repeatable': False
            },
        ]

        # Daily quests
        daily_quests = [
            {
                'title': 'Ежедневный воин',
                'description': 'Убейте 15 игроков сегодня',
                'type': 'kills',
                'target_value': 15,
                'reward_xp': 500,
                'reward_coins': 100,
                'reward_reputation': 5,
                'reward_karma': 5,
                'icon': 'fas fa-sword',
                'difficulty': 'easy',
                'quest_category': 'daily'
            },
            {
                'title': 'Ежедневная охота',
                'description': 'Совершите 5 финальных убийств',
                'type': 'final_kills',
                'target_value': 5,
                'reward_xp': 800,
                'reward_coins': 150,
                'reward_reputation': 8,
                'reward_karma': 5,
                'icon': 'fas fa-crosshairs',
                'difficulty': 'medium',
                'quest_category': 'daily'
            },
            {
                'title': 'Ежедневный разрушитель',
                'description': 'Сломайте 3 кровати',
                'type': 'beds_broken',
                'target_value': 3,
                'reward_xp': 600,
                'reward_coins': 120,
                'reward_reputation': 6,
                'reward_karma': 5,
                'icon': 'fas fa-bed',
                'difficulty': 'easy',
                'quest_category': 'daily'
            },
            {
                'title': 'Ежедневный победитель',
                'description': 'Выиграйте 2 игры',
                'type': 'wins',
                'target_value': 2,
                'reward_xp': 1000,
                'reward_coins': 200,
                'reward_reputation': 10,
                'reward_karma': 5,
                'icon': 'fas fa-trophy',
                'difficulty': 'medium',
                'quest_category': 'daily'
            },
            {
                'title': 'Ежедневный майнер',
                'description': 'Соберите 500 единиц железа',
                'type': 'iron_collected',
                'target_value': 500,
                'reward_xp': 400,
                'reward_coins': 80,
                'reward_reputation': 4,
                'reward_karma': 5,
                'icon': 'fas fa-hammer',
                'difficulty': 'easy',
                'quest_category': 'daily'
            }
        ]

        # Weekly quests
        weekly_quests = [
            {
                'title': 'Еженедельный воин',
                'description': 'Убейте 100 игроков за неделю',
                'type': 'kills',
                'target_value': 100,
                'reward_xp': 3000,
                'reward_coins': 750,
                'reward_reputation': 30,
                'reward_karma': 15,
                'icon': 'fas fa-sword',
                'difficulty': 'hard',
                'quest_category': 'weekly'
            },
            {
                'title': 'Мастер финальных убийств',
                'description': 'Совершите 25 финальных убийств',
                'type': 'final_kills',
                'target_value': 25,
                'reward_xp': 4000,
                'reward_coins': 1000,
                'reward_reputation': 40,
                'reward_karma': 15,
                'icon': 'fas fa-skull',
                'difficulty': 'hard',
                'quest_category': 'weekly'
            },
            {
                'title': 'Недельный чемпион',
                'description': 'Выиграйте 15 игр за неделю',
                'type': 'wins',
                'target_value': 15,
                'reward_xp': 5000,
                'reward_coins': 1250,
                'reward_reputation': 50,
                'reward_karma': 15,
                'icon': 'fas fa-crown',
                'difficulty': 'epic',
                'quest_category': 'weekly'
            }
        ]

        # Monthly quests
        monthly_quests = [
            {
                'title': 'Легенда месяца',
                'description': 'Убейте 500 игроков за месяц',
                'type': 'kills',
                'target_value': 500,
                'reward_xp': 15000,
                'reward_coins': 3000,
                'reward_reputation': 150,
                'reward_karma': 30,
                'icon': 'fas fa-fire',
                'difficulty': 'epic',
                'quest_category': 'monthly'
            },
            {
                'title': 'Разрушитель империй',
                'description': 'Сломайте 100 кроватей за месяц',
                'type': 'beds_broken',
                'target_value': 100,
                'reward_xp': 12000,
                'reward_coins': 2500,
                'reward_reputation': 120,
                'reward_karma': 30,
                'icon': 'fas fa-meteor',
                'difficulty': 'epic',
                'quest_category': 'monthly'
            },
            {
                'title': 'Непобедимый',
                'description': 'Выиграйте 50 игр за месяц',
                'type': 'wins',
                'target_value': 50,
                'reward_xp': 20000,
                'reward_coins': 4000,
                'reward_reputation': 200,
                'reward_karma': 30,
                # 'reward_role': 'Непобедимый', # reward_title removed
                'icon': 'fas fa-crown',
                'difficulty': 'epic',
                'quest_category': 'monthly'
            }
        ]

        # Thematic quests (one-time only)
        thematic_quests = [
            {
                'title': 'Рождественское чудо',
                'description': 'Выиграйте 25 игр в рождественский сезон',
                'type': 'wins',
                'target_value': 25,
                'reward_xp': 10000,
                'reward_coins': 2000,
                'reward_reputation': 100,
                'reward_karma': 100,
                # 'reward_role': 'Рождественский герой', # reward_title removed
                'icon': 'fas fa-gifts',
                'difficulty': 'epic',
                'quest_category': 'thematic',
                'is_repeatable': False
            },
            {
                'title': 'Хэллоуинский кошмар',
                'description': 'Совершите 100 финальных убийств в октябре',
                'type': 'final_kills',
                'target_value': 100,
                'reward_xp': 12000,
                'reward_coins': 2500,
                'reward_reputation': 120,
                'reward_karma': 100,
                # 'reward_role': 'Призрак Хэллоуина', # reward_title removed
                'icon': 'fas fa-ghost',
                'difficulty': 'epic',
                'quest_category': 'thematic',
                'is_repeatable': False
            }
        ]

        # Mythic quests (ultra rare, one-time only)
        mythic_quests = [
            {
                'title': 'Властелин Bedwars',
                'description': 'Достигните 1000 побед и K/D 5.0',
                'type': 'wins',
                'target_value': 1000,
                'reward_xp': 50000,
                'reward_coins': 10000,
                'reward_reputation': 500,
                # 'reward_role': 'Властелин Bedwars', # reward_title removed
                # 'reward_title': 'Властелин', # reward_title removed
                'icon': 'fas fa-dragon',
                'difficulty': 'mythic',
                'quest_category': 'mythic',
                'is_repeatable': False
            },
            {
                'title': 'Божество разрушения',
                'description': 'Сломайте 2000 кроватей',
                'type': 'beds_broken',
                'target_value': 2000,
                'reward_xp': 75000,
                'reward_coins': 15000,
                'reward_reputation': 750,
                # 'reward_role': 'Божество разрушения', # reward_title removed
                # 'reward_title': 'Разрушитель миров', # reward_title removed
                'icon': 'fas fa-meteor',
                'difficulty': 'mythic',
                'quest_category': 'mythic',
                'is_repeatable': False
            }
        ]

        all_quests = permanent_quests + daily_quests + weekly_quests + monthly_quests + thematic_quests + mythic_quests

        for quest_data in all_quests:
            existing = cls.query.filter_by(title=quest_data['title']).first()
            if not existing:
                quest = cls(**quest_data)
                db.session.add(quest)

        db.session.commit()

class PlayerQuest(db.Model):
    """Player progress on quests"""

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    quest_id = db.Column(db.Integer, db.ForeignKey('quest.id'), nullable=False)
    current_progress = db.Column(db.Integer, default=0)
    baseline_value = db.Column(db.Integer, default=0)  # Starting value when quest was accepted
    is_completed = db.Column(db.Boolean, default=False)
    is_accepted = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    accepted_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<PlayerQuest {self.player_id}:{self.quest_id}>'

    @property
    def progress_percentage(self):
        """Calculate progress percentage"""
        quest_obj = Quest.query.get(self.quest_id)
        if not quest_obj or quest_obj.target_value == 0:
            return 100
        return min(100, round((self.current_progress / quest_obj.target_value) * 100))

    def check_completion(self, player_stat_value):
        """Check if quest should be completed"""
        # Calculate progress from baseline
        progress_from_baseline = max(0, player_stat_value - self.baseline_value)
        self.current_progress = progress_from_baseline
        quest_obj = Quest.query.get(self.quest_id)

        if not self.is_completed and quest_obj and self.current_progress >= quest_obj.target_value:
            self.is_completed = True
            self.completed_at = datetime.utcnow()
            return True
        return False

    @classmethod
    def update_player_quest_progress(cls, player):
        """Update quest progress only for accepted quests"""
        completed_quests = []

        # Only update progress for accepted quests
        accepted_quests = cls.query.filter_by(
            player_id=player.id,
            is_accepted=True,
            is_completed=False
        ).all()

        for player_quest in accepted_quests:
            quest = player_quest.quest

            # Get current stat value
            current_stat_value = getattr(player, quest.type, 0)

            # Check completion based on progress from baseline
            if player_quest.check_completion(current_stat_value):
                completed_quests.append(quest)

                # Award XP, coins, reputation and karma
                player.experience += quest.reward_xp
                player.coins += quest.reward_coins
                player.reputation += quest.reward_reputation
                player.karma += quest.reward_karma

        if completed_quests:
            db.session.commit()

        return completed_quests


class ShopItem(db.Model):
    """Shop items for purchase"""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    display_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # title, theme, gradient, avatar, cursor
    price_coins = db.Column(db.Integer, default=0, nullable=False)
    price_reputation = db.Column(db.Integer, default=0, nullable=False)
    unlock_level = db.Column(db.Integer, default=1, nullable=False)
    rarity = db.Column(db.String(20), default='common', nullable=False)
    icon = db.Column(db.String(50), default='fas fa-star', nullable=False)
    image_url = db.Column(db.String(500), nullable=True)  # URL for item image
    item_data = db.Column(db.Text, nullable=True)  # JSON data for item effects
    is_limited_time = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    purchases = db.relationship('ShopPurchase', backref='shop_item', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ShopItem {self.display_name}>'

    def can_purchase(self, player):
        """Check if player can purchase this item"""
        # Check level requirement
        if player.level < self.unlock_level:
            return False, f"Требуется {self.unlock_level} уровень"

        # Check if player has enough resources
        if player.coins < self.price_coins:
            return False, "Недостаточно койнов"

        if player.reputation < self.price_reputation:
            return False, "Недостаточно репутации"

        # Check if already purchased (for non-consumable items)
        if self.category in ['title', 'theme', 'cursor', 'avatar']:
            existing = ShopPurchase.query.filter_by(
                player_id=player.id,
                item_id=self.id
            ).first()
            if existing:
                return False, "Уже приобретено"

        return True, "OK"

    def apply_item_effect(self, player):
        """Apply item effect to player"""
        try:
            import json
            data = json.loads(self.item_data) if self.item_data else {}

            if self.category == 'custom_role':
                # Enable custom role for player with tier
                role_tier = data.get('role_tier', 'basic')
                player.custom_role_purchased = True
                player.custom_role_tier = role_tier

                # Set default role if not set
                if not player.custom_role:
                    tier_names = {
                        'basic': 'Новичок',
                        'premium': 'Опытный',
                        'legendary': 'Легенда',
                        'mythic': 'Мифический воин'
                    }
                    player.custom_role = tier_names.get(role_tier, 'Кастомная роль')
                return True, f"Кастомная роль '{player.custom_role}' активирована!"

            elif self.category == 'emoji_slot':
                # Add emoji slots to player
                emoji_slots = data.get('emoji_slots', 1)
                if not hasattr(player, 'custom_emoji_slots'):
                    player.custom_emoji_slots = 0
                player.custom_emoji_slots += emoji_slots
                return True, f"Добавлено {emoji_slots} слотов для эмодзи!"

            elif self.category == 'title':
                # Create or find existing custom title
                title_text = data.get('title_text', self.display_name)
                existing_title = CustomTitle.query.filter_by(name=title_text.lower().replace(' ', '_')).first()

                if not existing_title:
                    title = CustomTitle(
                        name=title_text.lower().replace(' ', '_'),
                        display_name=title_text,
                        color=data.get('title_color', '#ffd700'),
                        glow_color=data.get('title_color', '#ffd700')
                    )
                    db.session.add(title)
                    db.session.flush()
                    title_id = title.id
                else:
                    title_id = existing_title.id

                # Check if player already has this title
                existing_player_title = PlayerTitle.query.filter_by(
                    player_id=player.id,
                    title_id=title_id
                ).first()

                if not existing_player_title:
                    # Deactivate other titles first
                    PlayerTitle.query.filter_by(player_id=player.id, is_active=True).update({'is_active': False})

                    # Assign to player
                    player_title = PlayerTitle(
                        player_id=player.id,
                        title_id=title_id,
                        is_active=True
                    )
                    db.session.add(player_title)
                    db.session.commit() # Commit here to ensure title is assigned
                    return True, f"Титул '{title.display_name}' установлен!"
                else:
                    # If player already has the title, just make it active
                    existing_player_title.is_active = True
                    db.session.commit()
                    return True, f"Титул '{title.display_name}' активирован!"


            elif self.category == 'booster':
                # Apply immediate booster effects
                booster_type = data.get('booster_type', 'xp')
                boost_duration = data.get('duration_minutes', 60) # Default duration 60 minutes

                # Check if an active booster of the same type exists
                existing_booster = PlayerBooster.get_active_booster(player.id, f'active_{booster_type}_booster')
                if existing_booster:
                    # Extend duration if booster exists
                    existing_booster.expires_at += timedelta(minutes=boost_duration)
                    # Update multiplier if needed (e.g., if buying a stronger booster)
                    if booster_type == 'xp':
                        existing_booster.multiplier = max(existing_booster.multiplier, data.get('multiplier', 1.5))
                    elif booster_type == 'coins':
                        existing_booster.multiplier = max(existing_booster.multiplier, data.get('multiplier', 1.5))
                    elif booster_type == 'reputation':
                        existing_booster.multiplier = max(existing_booster.multiplier, data.get('multiplier', 1.5))
                    db.session.commit()
                    return True, f"Длительность бустера '{booster_type}' продлена!"
                else:
                    # Create new booster
                    new_booster = PlayerBooster(
                        player_id=player.id,
                        booster_type=f'active_{booster_type}_booster',
                        multiplier=data.get('multiplier', 1.5),
                        duration_minutes=boost_duration,
                        expires_at=datetime.utcnow() + timedelta(minutes=boost_duration)
                    )
                    db.session.add(new_booster)
                    db.session.commit()
                    return True, f"Бустер '{booster_type}' активирован на {boost_duration} минут!"


            elif self.category == 'theme':
                # Apply theme to player (would need theme system implementation)
                player.selected_theme_id = self.id
                player.experience += 500
                db.session.commit()
                return True, f"Тема '{self.display_name}' применена!"

            elif self.category == 'gradient':
                # Apply gradient theme to player
                gradient_css = data.get('gradient_css')
                is_animated = data.get('is_animated', False)
                if gradient_css:
                    # Find or create a GradientTheme entry
                    gradient_name = self.name # Use the item name as a unique identifier for the gradient
                    existing_gradient = GradientTheme.query.filter_by(name=gradient_name).first()

                    if not existing_gradient:
                        # Attempt to parse gradient CSS to extract colors and direction
                        # This is a simplified approach; a robust parser would be better
                        import re
                        match = re.search(r'linear-gradient\(([^,]+,\s*[^,]+,\s*[^)]+)\)', gradient_css)
                        if match:
                            gradient_parts = match.group(1).split(',')
                            gradient_direction = '45deg' # Default direction
                            colors = []
                            if len(gradient_parts) >= 2:
                                first_part = gradient_parts[0].strip()
                                if 'deg' in first_part or 'rad' in first_part or 'turn' in first_part:
                                    gradient_direction = first_part
                                    colors = [p.strip() for p in gradient_parts[1:]]
                                else:
                                    colors = [p.strip() for p in gradient_parts]

                                if len(colors) >= 2:
                                    existing_gradient = GradientTheme.query.filter_by(
                                        name=gradient_name,
                                        element_type='custom', # Assign a generic type for player-created gradients
                                        color1=colors[0],
                                        color2=colors[1],
                                        gradient_direction=gradient_direction,
                                        animation_enabled=is_animated
                                    ).first()

                                    if not existing_gradient:
                                        existing_gradient = GradientTheme(
                                            name=gradient_name,
                                            display_name=self.display_name,
                                            element_type='custom',
                                            color1=colors[0],
                                            color2=colors[1] if len(colors) > 1 else colors[0],
                                            color3=colors[2] if len(colors) > 2 else None,
                                            gradient_direction=gradient_direction,
                                            animation_enabled=is_animated,
                                            is_active=True
                                        )
                                        db.session.add(existing_gradient)
                                        db.session.flush()

                    if existing_gradient:
                        # Assign the gradient to the player for a specific element type (e.g., nickname, stats)
                        # This requires a more dynamic way to handle which element the gradient applies to.
                        # For now, we'll assume a default or that the player chooses later.
                        # Let's add a setting for 'nickname' as an example.
                        player_gradient_setting = PlayerGradientSetting.query.filter_by(
                            player_id=player.id,
                            element_type='nickname' # Default to nickname, or could be chosen by player
                        ).first()

                        if not player_gradient_setting:
                            player_gradient_setting = PlayerGradientSetting(
                                player_id=player.id,
                                element_type='nickname',
                                gradient_theme_id=existing_gradient.id,
                                is_enabled=True
                            )
                            db.session.add(player_gradient_setting)
                        else:
                            player_gradient_setting.gradient_theme_id = existing_gradient.id
                            player_gradient_setting.is_enabled = True

                        # Add experience as a reward for purchasing the gradient item
                        player.experience += 300
                        db.session.commit() # Commit here
                        return True, f"Градиент '{self.display_name}' применен!"


            # Handle Inventory items separately
            elif self.category in ['coins', 'experience', 'reputation', 'custom_role', 'emoji_slot', 'title', 'booster']:
                # These items are applied directly and not added to inventory
                pass # Already handled above

            else:
                # For items that go into inventory (e.g., consumables, cosmetics)
                # We create an InventoryItem entry
                existing_inventory_item = InventoryItem.query.filter_by(
                    player_id=player.id,
                    item_id=self.id,
                    status='unused'
                ).first()

                if existing_inventory_item:
                    existing_inventory_item.quantity += 1
                    db.session.commit()
                    return True, f"Количество '{self.display_name}' в инвентаре увеличено."
                else:
                    inventory_item = InventoryItem(
                        player_id=player.id,
                        item_id=self.id,
                        quantity=1,
                        status='unused'
                    )
                    db.session.add(inventory_item)
                    db.session.commit()
                    return True, f"'{self.display_name}' добавлен в ваш инвентарь."


        # Default case if no specific category matched or for generic rewards
        # Add experience as a reward for purchasing the gradient item
                player.experience += 300
                return True, f"Градиент '{self.display_name}' применен!"

            # Default case
            return True, f"Эффект товара '{self.display_name}' применен"

        except Exception as e:
            from app import app
            app.logger.error(f"Error applying item effect: {e}")
            return False, f"Ошибка при применении эффекта: {str(e)}"

    @classmethod
    def create_default_items(cls):
        """Create default shop items"""
        # Titles
        default_items = [
            {
                'name': 'pro_gamer_title',
                'display_name': 'Про-Геймер',
                'description': 'Эксклюзивный титул для настоящих профессионалов',
                'category': 'title',
                'price_coins': 5000,
                'price_reputation': 100,
                'unlock_level': 25,
                'rarity': 'epic',
                'icon': 'fas fa-crown',
                'item_data': '{"title_text": "Про-Геймер", "title_color": "#6f42c1"}'
            },
            {
                'name': 'legend_title',
                'display_name': 'Легенда',
                'description': 'Титул для истинных легенд Bedwars',
                'category': 'title',
                'price_coins': 15000,
                'price_reputation': 500,
                'unlock_level': 50,
                'rarity': 'legendary',
                'icon': 'fas fa-dragon',
                'item_data': '{"title_text": "Легенда", "title_color": "#ff9800", "is_gradient": true, "gradient_colors": "linear-gradient(45deg, #ff9800, #ffc107)"}'
            },
            {
                'name': 'mythic_warrior_title',
                'display_name': 'Мифический Воин',
                'description': 'Сверхредкий титул для избранных',
                'category': 'title',
                'price_coins': 50000,
                'price_reputation': 2000,
                'unlock_level': 75,
                'rarity': 'mythic',
                'icon': 'fas fa-bolt',
                'item_data': '{"title_text": "Мифический Воин", "title_color": "#9400d3", "is_gradient": true, "gradient_colors": "linear-gradient(45deg, #9400d3, #4b0082, #0000ff)"}'
            },

            # Boosters
            {
                'name': 'xp_booster_small',
                'display_name': 'Малый бустер опыта',
                'description': 'Получите +1000 опыта мгновенно',
                'category': 'booster',
                'price_coins': 1000,
                'price_reputation': 0,
                'unlock_level': 1,
                'rarity': 'common',
                'item_data': '{"booster_type": "xp", "bonus_amount": 1000, "duration_minutes": 60, "multiplier": 1.5}'
            },
            {
                'name': 'xp_booster_large',
                'display_name': 'Большой бустер опыта',
                'description': 'Получите +10000 опыта мгновенно',
                'category': 'booster',
                'price_coins': 8000,
                'price_reputation': 0,
                'unlock_level': 10,
                'rarity': 'epic',
                'item_data': '{"booster_type": "xp", "bonus_amount": 10000, "duration_minutes": 120, "multiplier": 2.0}'
            },
            {
                'name': 'coin_booster',
                'display_name': 'Бустер койнов',
                'description': 'Получите +2500 койнов мгновенно',
                'category': 'booster',
                'price_coins': 3000,
                'price_reputation': 50,
                'unlock_level': 15,
                'rarity': 'uncommon',
                'item_data': '{"booster_type": "coins", "bonus_amount": 2500, "duration_minutes": 90, "multiplier": 1.5}'
            },
            {
                'name': 'reputation_booster',
                'display_name': 'Бустер репутации',
                'description': 'Получите +200 репутации мгновенно',
                'category': 'booster',
                'price_coins': 5000,
                'price_reputation': 0,
                'unlock_level': 20,
                'rarity': 'rare',
                'item_data': '{"booster_type": "reputation", "bonus_amount": 200, "duration_minutes": 180, "multiplier": 1.5}'
            },

            # Custom Roles
            {
                'name': 'basic_custom_role',
                'display_name': 'Обычная кастомная роль',
                'description': 'Создайте свою роль со статичным цветом',
                'category': 'custom_role',
                'price_coins': 5000,
                'price_reputation': 0,
                'unlock_level': 10,
                'rarity': 'common',
                'item_data': '{"role_tier": "basic", "allows_color": true, "allows_gradient": false, "allows_animation": false, "allows_emoji": false}'
            },
            {
                'name': 'gradient_custom_role',
                'display_name': 'Особая роль с градиентом',
                'description': 'Роль с красивым градиентом',
                'category': 'custom_role',
                'price_coins': 50000,
                'price_reputation': 0,
                'unlock_level': 40,
                'rarity': 'epic',
                'item_data': '{"role_tier": "premium", "allows_color": true, "allows_gradient": true, "allows_animation": false, "allows_emoji": false}'
            },
            {
                'name': 'animated_custom_role',
                'display_name': 'Особая анимированная роль',
                'description': 'Роль с анимированным градиентом и эмодзи',
                'category': 'custom_role',
                'price_coins': 75000,
                'price_reputation': 0,
                'unlock_level': 40,
                'rarity': 'legendary',
                'item_data': '{"role_tier": "legendary", "allows_color": true, "allows_gradient": true, "allows_animation": true, "allows_emoji": true}'
            },
            {
                'name': 'premium_animated_custom_role',
                'display_name': 'Премиум анимированная роль',
                'description': 'Топовая роль с максимальными возможностями',
                'category': 'custom_role',
                'price_coins': 100000,
                'price_reputation': 0,
                'unlock_level': 40,
                'rarity': 'mythic',
                'item_data': '{"role_tier": "mythic", "allows_color": true, "allows_gradient": true, "allows_animation": true, "allows_emoji": true}'
            },
             {
                'name': 'emoji_slot_basic',
                'display_name': 'Слот для эмодзи (базовый)',
                'description': 'Добавляет 1 слот для кастомного эмодзи к роли',
                'category': 'emoji_slot',
                'price_coins': 10000,
                'price_reputation': 200,
                'unlock_level': 10,
                'rarity': 'uncommon',
                'item_data': '{"emoji_slots": 1}'
            },
            {
                'name': 'emoji_slot_premium',
                'display_name': 'Слот для эмодзи (премиум)',
                'description': 'Добавляет 2 слота для кастомного эмодзи к роли',
                'category': 'emoji_slot',
                'price_coins': 25000,
                'price_reputation': 500,
                'unlock_level': 30,
                'rarity': 'rare',
                'item_data': '{"emoji_slots": 2}'
            },
            {
                'name': 'emoji_slot_legendary',
                'display_name': 'Слот для эмодзи (легендарный)',
                'description': 'Добавляет 3 слота для кастомного эмодзи к роли',
                'category': 'emoji_slot',
                'price_coins': 50000,
                'price_reputation': 1000,
                'unlock_level': 50,
                'rarity': 'legendary',
                'item_data': '{"emoji_slots": 3}'
            },

            # Themes
            {
                'name': 'neon_theme',
                'display_name': 'Неоновая тема',
                'description': 'Яркая неоновая тема оформления',
                'category': 'theme',
                'price_coins': 12000,
                'price_reputation': 300,
                'unlock_level': 30,
                'rarity': 'epic',
                'item_data': '{"theme_colors": {"primary": "#00ffff", "secondary": "#ff00ff"}}'
            },
            {
                'name': 'galaxy_theme',
                'display_name': 'Галактическая тема',
                'description': 'Космическая тема с эффектами галактики',
                'category': 'theme',
                'price_coins': 25000,
                'price_reputation': 800,
                'unlock_level': 60,
                'rarity': 'legendary',
                'item_data': '{"theme_colors": {"primary": "#483d8b", "secondary": "#9400d3"}}'
            },

            # Gradients for customization
            {
                'name': 'fire_gradient',
                'display_name': 'Огненный градиент',
                'description': 'Яркий огненный градиент для любого элемента',
                'category': 'gradient',
                'price_coins': 2500,
                'price_reputation': 50,
                'unlock_level': 15,
                'rarity': 'uncommon',
                'icon': 'fas fa-fire',
                'item_data': '{"gradient_css": "linear-gradient(45deg, #ff6b35, #ffaa00)", "is_animated": true}'
            },
            {
                'name': 'ocean_gradient',
                'display_name': 'Морской градиент',
                'description': 'Прохладный морской градиент',
                'category': 'gradient',
                'price_coins': 2000,
                'price_reputation': 30,
                'unlock_level': 10,
                'rarity': 'common',
                'icon': 'fas fa-water',
                'item_data': '{"gradient_css": "linear-gradient(45deg, #00d2ff, #3a7bd5)", "is_animated": false}'
            },
            {
                'name': 'rainbow_gradient',
                'display_name': 'Радужный градиент',
                'description': 'Яркий радужный градиент с анимацией',
                'category': 'gradient',
                'price_coins': 5000,
                'price_reputation': 100,
                'unlock_level': 25,
                'rarity': 'epic',
                'icon': 'fas fa-rainbow',
                'item_data': '{"gradient_css": "linear-gradient(45deg, #ff0000, #ffff00, #00ff00, #0000ff, #8b00ff)", "is_animated": true}'
            },
            {
                'name': 'galaxy_gradient',
                'display_name': 'Галактический градиент',
                'description': 'Космический градиент для избранных',
                'category': 'gradient',
                'price_coins': 15000,
                'price_reputation': 300,
                'unlock_level': 50,
                'rarity': 'legendary',
                'icon': 'fas fa-star',
                'item_data': '{"gradient_css": "linear-gradient(45deg, #2c3e50, #4a6741, #9b59b6, #e74c3c)", "is_animated": true}'
            },
            # Custom Roles
            {
                'name': 'gradient_custom_role',
                'display_name': 'Особая роль с градиентом',
                'description': 'Роль с красивым градиентом',
                'category': 'custom_role',
                'price_coins': 50000,
                'price_reputation': 0,
                'unlock_level': 40,
                'rarity': 'epic',
                'item_data': '{"role_tier": "premium", "allows_color": true, "allows_gradient": true, "allows_animation": false, "allows_emoji": false}'
            },
        ]

        for item_data in default_items:
            existing = cls.query.filter_by(name=item_data['name']).first()
            if not existing:
                item = cls(**item_data)
                db.session.add(item)

        db.session.commit()

    @classmethod
    def create_default_items(cls):
        """Create default shop items"""
        # Этот метод можно оставить пустым или добавить базовые предметы
        pass


class ShopPurchase(db.Model):
    """Purchase history for shop items"""

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('shop_item.id'), nullable=False)
    price_paid_coins = db.Column(db.Integer, default=0, nullable=False)
    price_paid_reputation = db.Column(db.Integer, default=0)
    purchased_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    player = db.relationship('Player', backref='shop_purchases_rel')


class InventoryItem(db.Model):
    """Player inventory items"""
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('shop_item.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    status = db.Column(db.String(20), default='unused', nullable=False)  # unused, used, expired
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    used_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    player = db.relationship('Player', backref='inventory_items_rel')
    item = db.relationship('ShopItem', backref='inventory_instances')

    @property
    def can_use(self):
        """Check if item can be used"""
        return self.status == 'unused' and self.quantity > 0

    def use_item(self):
        """Use the inventory item"""
        if not self.can_use:
            return False, "Предмет не может быть использован"

        try:
            # Apply item effect based on type
            if self.item.category == 'coins': # Assuming item.category can be 'coins', 'experience', etc.
                self.player.coins += self.item.item_data.get('effect_value', 0)
            elif self.item.category == 'experience':
                self.player.experience += self.item.item_data.get('effect_value', 0)
            elif self.item.category == 'reputation':
                self.player.reputation += self.item.item_data.get('effect_value', 0)
            elif self.item.category == 'custom_title':
                # Add custom title to player
                title_id = self.item.item_data.get('title_id')
                if title_id:
                    title = CustomTitle.query.get(title_id)
                    if title:
                        player_title = PlayerTitle(
                            player_id=self.player.id,
                            title_id=title.id,
                            is_active=False
                        )
                        db.session.add(player_title)

            # Mark as used
            self.status = 'used'
            self.used_at = datetime.utcnow()
            self.quantity -= 1

            db.session.commit()
            return True, f"Использован предмет: {self.item.display_name}"

        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при использовании предмета: {str(e)}"


class PlayerPurchase(db.Model):
    """Player purchases from the shop"""

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('shop_item.id'), nullable=False)
    purchase_price_coins = db.Column(db.Integer, nullable=False)
    purchase_price_reputation = db.Column(db.Integer, default=0)
    purchased_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    player = db.relationship('Player')


class PlayerBooster(db.Model):
    """Active boosters for players"""

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    booster_type = db.Column(db.String(20), nullable=False)  # experience, reputation, coins
    multiplier = db.Column(db.Float, default=1.5)  # 1.5x, 2.0x, etc.
    duration_minutes = db.Column(db.Integer, nullable=False)
    activated_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    given_by_admin = db.Column(db.String(100), nullable=True)

    # Relationships
    player = db.relationship('Player', backref='player_boosters')

    def __repr__(self):
        return f'<PlayerBooster {self.player_id}:{self.booster_type}>'

    @property
    def is_expired(self):
        return datetime.utcnow() > self.expires_at

    @property
    def time_remaining(self):
        if self.is_expired:
            return 0
        delta = self.expires_at - datetime.utcnow()
        return int(delta.total_seconds() / 60)  # minutes

    @classmethod
    def get_active_booster(cls, player_id, booster_type):
        """Get active booster for player"""
        return cls.query.filter_by(
            player_id=player_id,
            booster_type=booster_type,
            is_active=True
        ).filter(cls.expires_at > datetime.utcnow()).first()

    @classmethod
    def cleanup_expired(cls):
        """Remove expired boosters"""
        expired = cls.query.filter(cls.expires_at < datetime.utcnow()).all()
        for booster in expired:
            booster.is_active = False


class ReputationLog(db.Model):
    """Log of reputation changes"""

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    change_amount = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    given_by = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    player = db.relationship('Player', backref='reputation_logs')

    def __repr__(self):
        return f'<ReputationLog {self.player_id}:{self.change_amount}>'


class Clan(db.Model):
    """Clan system for players"""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    tag = db.Column(db.String(10), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    clan_type = db.Column(db.String(20), default='open', nullable=False)  # open, invite_only, closed
    max_members = db.Column(db.Integer, default=50, nullable=False)
    experience = db.Column(db.Integer, default=0, nullable=False)
    rating = db.Column(db.Integer, default=1000, nullable=False)
    leader_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    leader = db.relationship('Player', foreign_keys=[leader_id], backref='led_clans')
    members = db.relationship('ClanMember', backref='clan', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Clan {self.name} [{self.tag}]>'

    @property
    def level(self):
        """Calculate clan level based on experience"""
        # Simple level calculation: level = experience // 10000 + 1
        return min(100, max(1, self.experience // 10000 + 1))

    @property
    def member_count(self):
        """Get current member count"""
        return ClanMember.query.filter_by(clan_id=self.id, is_active=True).count()

    @property
    def can_join(self):
        """Check if clan can accept new members"""
        return self.clan_type == 'open' and self.member_count < self.max_members

    def get_members_by_role(self, role):
        """Get clan members by role"""
        return ClanMember.query.filter_by(clan_id=self.id, role=role, is_active=True).all()

    @classmethod
    def get_top_clans(cls, limit=10):
        """Get top clans by rating"""
        return cls.query.filter_by(is_active=True).order_by(cls.rating.desc()).limit(limit).all()

    @classmethod
    def search_clans(cls, query):
        """Search clans by name or tag"""
        return cls.query.filter(
            db.or_(
                cls.name.ilike(f'%{query}%'),
                cls.tag.ilike(f'%{query}%')
            ),
            cls.is_active == True
        ).all()


class ClanMember(db.Model):
    """Clan membership"""

    id = db.Column(db.Integer, primary_key=True)
    clan_id = db.Column(db.Integer, db.ForeignKey('clan.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    role = db.Column(db.String(20), default='member', nullable=False)  # leader, officer, member
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    contribution = db.Column(db.Integer, default=0, nullable=False)

    # Relationships
    player = db.relationship('Player', backref='clan_memberships')

    def __repr__(self):
        return f'<ClanMember {self.player_id}:{self.clan_id}>'

    @property
    def role_display(self):
        """Get display name for role"""
        role_names = {
            'leader': '👑 Лидер',
            'officer': '⭐ Офицер',
            'member': '👤 Участник'
        }
        return role_names.get(self.role, '👤 Участник')


class Tournament(db.Model):
    """Tournament system"""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    tournament_type = db.Column(db.String(20), default='singles', nullable=False)  # singles, teams, clans
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=True)
    entry_fee = db.Column(db.Integer, default=0, nullable=False)
    prize_pool = db.Column(db.Integer, default=0, nullable=False)
    max_participants = db.Column(db.Integer, default=100, nullable=False)
    status = db.Column(db.String(20), default='upcoming', nullable=False)  # upcoming, active, completed
    organizer_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    organizer = db.relationship('Player', backref='organized_tournaments')
    participants = db.relationship('TournamentParticipant', backref='tournament', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Tournament {self.name}>'

    @property
    def status_display(self):
        """Get display name for status"""
        status_names = {
            'upcoming': '🕐 Предстоящий',
            'active': '⚡ Активный',
            'completed': '✅ Завершён'
        }
        return status_names.get(self.status, '❓ Неизвестно')

    @property
    def can_join(self):
        """Check if tournament is open for registration"""
        return self.status == 'upcoming' and self.participant_count < self.max_participants

    @property
    def participant_count(self):
        """Get current participant count"""
        return TournamentParticipant.query.filter_by(tournament_id=self.id).count()

    @classmethod
    def get_active_tournaments(cls):
        """Get all active tournaments"""
        return cls.query.filter_by(status='active').all()

    @classmethod
    def get_upcoming_tournaments(cls):
        """Get all upcoming tournaments"""
        return cls.query.filter_by(status='upcoming').order_by(cls.start_date.asc()).all()


class TournamentParticipant(db.Model):
    """Tournament participation"""

    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    team_name = db.Column(db.String(100), nullable=True)  # For team tournaments
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    placement = db.Column(db.Integer, nullable=True)  # Final placement in tournament
    eliminated_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    player = db.relationship('Player', backref='tournament_participations')

    def __repr__(self):
        return f'<TournamentParticipant {self.player_id}:{self.tournament_id}>'


class Achievement(db.Model):
    """Achievement system for special accomplishments"""

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    icon = db.Column(db.String(50), default='fas fa-medal')
    rarity = db.Column(db.String(20), default='common')  # common, uncommon, epic, legendary, mythic
    unlock_condition = db.Column(db.Text, nullable=False)  # JSON condition
    reward_xp = db.Column(db.Integer, default=0)
    reward_coins = db.Column(db.Integer, default=0)
    reward_reputation = db.Column(db.Integer, default=0)
    reward_title = db.Column(db.String(100), nullable=True) # reward_title removed - titles should be separate system
    is_hidden = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship with player achievements
    player_achievements = db.relationship('PlayerAchievement', backref='achievement', lazy=True)

    def __repr__(self):
        return f'<Achievement {self.title}>'

    def check_unlock_condition(self, player):
        """Check if player meets achievement unlock condition"""
        try:
            import json
            condition = json.loads(self.unlock_condition)

            for key, required_value in condition.items():
                if key == 'kd_ratio':
                    if float(player.kd_ratio) < float(required_value):
                        return False
                elif key == 'win_rate':
                    if float(player.win_rate) < float(required_value):
                        return False
                elif key == 'total_resources':
                    if player.total_resources < required_value:
                        return False
                else:
                    player_value = getattr(player, key, 0)
                    if player_value < required_value:
                        return False

            return True
        except Exception as e:
            print(f"Error checking achievement condition: {e}")
            return False

    @classmethod
    def check_player_achievements(cls, player):
        """Check and award new achievements for player with bulk operations"""
        new_achievements = []

        # Оптимизированный запрос с NOT EXISTS
        earned_subquery = db.session.query(PlayerAchievement.achievement_id).filter(
            PlayerAchievement.player_id == player.id
        ).subquery()

        unearned_achievements = cls.query.filter(
            ~cls.id.in_(db.session.query(earned_subquery.c.achievement_id))
        ).all()

        # Собираем данные для bulk операций
        new_player_achievements = []
        total_xp = 0
        total_coins = 0
        total_reputation = 0

        for achievement in unearned_achievements:
            if achievement.check_unlock_condition(player):
                new_player_achievements.append({
                    'player_id': player.id,
                    'achievement_id': achievement.id,
                    'earned_at': datetime.utcnow()
                })

                total_xp += achievement.reward_xp
                total_coins += achievement.reward_coins
                total_reputation += achievement.reward_reputation
                new_achievements.append(achievement)

        # Bulk insert достижений - optimized for PostgreSQL
        if new_player_achievements:
            try:
                db.session.bulk_insert_mappings(PlayerAchievement, new_player_achievements)
            except Exception as e:
                # Fallback to individual inserts if bulk fails
                for achievement_data in new_player_achievements:
                    player_achievement = PlayerAchievement(**achievement_data)
                    db.session.add(player_achievement)

            # Обновляем награды одним запросом
            player.experience += total_xp
            player.coins += total_coins
            player.reputation += total_reputation

            db.session.commit()

        return new_achievements

    @classmethod
    def create_default_achievements(cls):
        """Create default achievements with enhanced reward system"""
        # Common achievements (basic rewards)
        default_achievements = [
            {
                'title': 'Новичок',
                'description': 'Сыграйте первую игру',
                'icon': 'fas fa-baby',
                'rarity': 'common',
                'unlock_condition': '{"games_played": 1}',
                'reward_xp': 500,
                'reward_coins': 100,
                'reward_reputation': 5
            },
            {
                'title': 'Первые шаги',
                'description': 'Убейте 10 игроков',
                'icon': 'fas fa-sword',
                'rarity': 'common',
                'unlock_condition': '{"kills": 10}',
                'reward_xp': 750,
                'reward_coins': 150,
                'reward_reputation': 8
            },
            {
                'title': 'Разрушитель',
                'description': 'Сломайте 5 кроватей',
                'icon': 'fas fa-bed',
                'rarity': 'common',
                'unlock_condition': '{"beds_broken": 5}',
                'reward_xp': 800,
                'reward_coins': 200,
                'reward_reputation': 10
            },

            # Uncommon achievements (moderate rewards)
            {
                'title': 'Боец',
                'description': 'Убейте 50 игроков',
                'icon': 'fas fa-fist-raised',
                'rarity': 'uncommon',
                'unlock_condition': '{"kills": 50}',
                'reward_xp': 1500,
                'reward_coins': 300,
                'reward_reputation': 15
            },
            {
                'title': 'Коллекционер',
                'description': 'Соберите 1000 единиц ресурсов',
                'icon': 'fas fa-gem',
                'rarity': 'uncommon',
                'unlock_condition': '{"total_resources": 1000}',
                'reward_xp': 1200,
                'reward_coins': 250,
                'reward_reputation': 12
            },
            {
                'title': 'Победитель',
                'description': 'Выиграйте 10 игр',
                'icon': 'fas fa-trophy',
                'rarity': 'uncommon',
                'unlock_condition': '{"wins": 10}',
                'reward_xp': 2000,
                'reward_coins': 400,
                'reward_reputation': 20
            },

            # Epic achievements (high rewards) - Made more challenging
            {
                'title': 'Неудержимый',
                'description': 'Убейте 500 игроков с K/D > 2.0',
                'icon': 'fas fa-fire',
                'rarity': 'epic',
                'unlock_condition': '{"kills": 500, "kd_ratio": 2.0}',
                'reward_xp': 8000,
                'reward_coins': 1500,
                'reward_reputation': 75,
                'is_hidden': True
            },
            {
                'title': 'Мастер ресурсов',
                'description': 'Соберите 25000 единиц ресурсов и выиграйте 75 игр',
                'icon': 'fas fa-coins',
                'rarity': 'epic',
                'unlock_condition': '{"total_resources": 25000, "wins": 75}',
                'reward_xp': 10000,
                'reward_coins': 2000,
                'reward_reputation': 100,
                'is_hidden': True
            },
            {
                'title': 'Чемпион арены',
                'description': 'Выиграйте 150 игр с 75%+ винрейтом',
                'icon': 'fas fa-crown',
                'rarity': 'epic',
                'unlock_condition': '{"wins": 150, "win_rate": 75.0}',
                'reward_xp': 12000,
                'reward_coins': 2500,
                'reward_reputation': 125
            },
            {
                'title': 'Разрушитель империй',
                'description': 'Сломайте 200 кроватей с 60%+ винрейтом',
                'icon': 'fas fa-hammer',
                'rarity': 'epic',
                'unlock_condition': '{"beds_broken": 200, "win_rate": 60.0}',
                'reward_xp': 9000,
                'reward_coins': 1800,
                'reward_reputation': 90,
                'is_hidden': True
            },

            # Legendary achievements (very high rewards) - Significantly more challenging
            {
                'title': 'Мастер Bedwars',
                'description': 'Достигните K/D 4.0+ при 200+ играх',
                'icon': 'fas fa-star',
                'rarity': 'legendary',
                'unlock_condition': '{"kd_ratio": 4.0, "games_played": 200}',
                'reward_xp': 20000,
                'reward_coins': 4000,
                'reward_reputation': 200,
                'reward_title': 'Мастер'
            },
            {
                'title': 'Великий воин',
                'description': 'Убейте 1500 игроков с 80%+ винрейтом',
                'icon': 'fas fa-shield',
                'rarity': 'legendary',
                'unlock_condition': '{"kills": 1500, "win_rate": 80.0}',
                'reward_xp': 25000,
                'reward_coins': 5000,
                'reward_reputation': 250,
                'reward_title': 'Великий воин'
            },
            {
                'title': 'Легенда арены',
                'description': 'Выиграйте 300 игр с 90%+ винрейтом',
                'icon': 'fas fa-medal',
                'rarity': 'legendary',
                'unlock_condition': '{"wins": 300, "win_rate": 90.0}',
                'reward_xp': 30000,
                'reward_coins': 6000,
                'reward_reputation': 300,
                'reward_title': 'Легенда арены'
            },
            {
                'title': 'Безжалостный убийца',
                'description': 'Совершите 750 финальных убийств с K/D > 3.5',
                'icon': 'fas fa-skull-crossbones',
                'rarity': 'legendary',
                'unlock_condition': '{"final_kills": 750, "kd_ratio": 3.5}',
                'reward_xp': 22000,
                'reward_coins': 4500,
                'reward_reputation': 220,
                'reward_title': 'Безжалостный',
                'is_hidden': True
            },

            # Mythic achievements (maximum rewards)
            {
                'title': 'Божество PVP',
                'description': 'Достигните K/D соотношения 5.0 и совершите 1000+ убийств',
                'icon': 'fas fa-bolt',
                'rarity': 'mythic',
                'unlock_condition': '{"kd_ratio": 5.0, "kills": 1000, "experience": 450000}',
                'reward_xp': 25000,
                'reward_coins': 5000,
                'reward_reputation': 250,
                'reward_title': 'Божество PVP',
                'is_hidden': True
            },
            {
                'title': 'Разрушитель миров',
                'description': 'Сломайте 500 кроватей',
                'icon': 'fas fa-meteor',
                'rarity': 'mythic',
                'unlock_condition': '{"beds_broken": 500}',
                'reward_xp': 30000,
                'reward_coins': 6000,
                'reward_reputation': 300,
                'reward_title': 'Разрушитель миров',
                'is_hidden': True
            },
            {
                'title': 'Легенда сервера',
                'description': 'Достигните 95% процента побед при 100+ играх',
                'icon': 'fas fa-dragon',
                'rarity': 'mythic',
                'unlock_condition': '{"wins": 100, "win_rate": 95.0}',
                'reward_xp': 40000,
                'reward_coins': 8000,
                'reward_reputation': 400,
                'reward_title': 'Легенда сервера',
                'is_hidden': True
            },
            {
                'title': 'Повелитель ресурсов',
                'description': 'Соберите 100,000 единиц ресурсов',
                'icon': 'fas fa-gem',
                'rarity': 'mythic',
                'unlock_condition': '{"total_resources": 100000}',
                'reward_xp': 35000,
                'reward_coins': 7000,
                'reward_reputation': 350,
                'reward_title': 'Повелитель ресурсов',
                'is_hidden': True
            },
            {
                'title': 'Абсолютный чемпион',
                'description': 'Выиграйте 1000 игр и достигните 98% побед',
                'icon': 'fas fa-infinity',
                'rarity': 'mythic',
                'unlock_condition': '{"wins": 1000, "win_rate": 98.0}',
                'reward_xp': 50000,
                'reward_coins': 10000,
                'reward_reputation': 500,
                'reward_title': 'Абсолютный чемпион',
                'is_hidden': True
            },
            {
                'title': 'Всевидящее око',
                'description': 'Совершите 2000 финальных убийств',
                'icon': 'fas fa-eye',
                'rarity': 'mythic',
                'unlock_condition': '{"final_kills": 2000}',
                'reward_xp': 45000,
                'reward_coins': 9000,
                'reward_reputation': 450,
                'reward_title': 'Всевидящее око',
                'is_hidden': True
            },
            {
                'title': 'Архитектор разрушения',
                'description': 'Сломайте 1000 кроватей',
                'icon': 'fas fa-hammer',
                'rarity': 'mythic',
                'unlock_condition': '{"beds_broken": 1000}',
                'reward_xp': 55000,
                'reward_coins': 11000,
                'reward_reputation': 550,
                'reward_title': 'Архитектор разрушения',
                'is_hidden': True
            },
            {
                'title': 'Неуязвимый',
                'description': 'Достигните уровня 200 с K/D > 4.0',
                'icon': 'fas fa-shield-alt',
                'rarity': 'mythic',
                'unlock_condition': '{"experience": 1500000, "kd_ratio": 4.0}',
                'reward_xp': 60000,
                'reward_coins': 12000,
                'reward_reputation': 600,
                'reward_title': 'Неуязвимый',
                'is_hidden': True
            }
        ]

        for achievement_data in default_achievements:
            existing = cls.query.filter_by(title=achievement_data['title']).first()
            if not existing:
                achievement = cls(**achievement_data)
                db.session.add(achievement)

        db.session.commit()


class PlayerAchievement(db.Model):
    """Player progress on achievements with baseline tracking"""

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievement.id'), nullable=False)
    current_progress = db.Column(db.Integer, default=0)
    baseline_values = db.Column(db.Text, nullable=True)  # JSON data for baseline stats when achievement was tracked
    is_earned = db.Column(db.Boolean, default=False)
    earned_at = db.Column(db.DateTime, nullable=True)
    started_tracking_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<PlayerAchievement {self.player_id}:{self.achievement_id}>'


class AdminCustomRole(db.Model):
    """Admin-created custom roles for players"""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    color = db.Column(db.String(7), default='#ffd700')  # Hex color
    emoji = db.Column(db.String(10), nullable=True)  # Legacy emoji field
    emoji_url = db.Column(db.String(256), nullable=True)  # Custom emoji file path
    emoji_filename = db.Column(db.String(256), nullable=True)  # Filename for uploaded emoji
    emoji_is_animated = db.Column(db.Boolean, default=False) # Flag for animated emoji
    emoji_class = db.Column(db.String(64), nullable=True)  # Font Awesome class
    has_gradient = db.Column(db.Boolean, default=False)
    gradient_end_color = db.Column(db.String(7), nullable=True)  # Second gradient color
    is_visible = db.Column(db.Boolean, default=True)  # Show in profile
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(100), default='admin')
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    player_roles = db.relationship('PlayerAdminRole', backref='role', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<AdminCustomRole {self.name}>'

    @property
    def gradient_css(self):
        """Get CSS gradient if enabled"""
        if self.has_gradient and self.gradient_end_color:
            return f"linear-gradient(45deg, {self.color}, {self.gradient_end_color})"
        return None

    @property
    def players_count(self):
        """Get count of players with this role"""
        return PlayerAdminRole.query.filter_by(role_id=self.id, is_active=True).count()

    @property
    def display_emoji(self):
        """Get emoji display HTML"""
        if self.emoji_filename:
            # Use uploaded file
            emoji_path = f"/static/emojis/{self.emoji_filename}"
            css_class = "emoji animated-emoji" if self.emoji_is_animated else "emoji"
            return f'<img src="{emoji_path}" class="{css_class}" alt="custom emoji">'
        elif self.emoji_url:
            return f'<img src="{self.emoji_url}" class="emoji" alt="custom emoji">'
        elif self.emoji_class:
            return f'<i class="{self.emoji_class}"></i>'
        elif self.emoji:
            return self.emoji
        return ''


    @classmethod
    def create_default_roles(cls):
        """Create default admin roles"""
        default_roles = [
            {
                'name': 'VIP',
                'color': '#ffd700',
                'emoji_class': 'fas fa-star',
                'has_gradient': False,
                'is_visible': True
            },
            {
                'name': 'Premium',
                'color': '#ff6b35',
                'emoji_class': 'fas fa-crown',
                'has_gradient': True,
                'gradient_end_color': '#ff4444',
                'is_visible': True
            },
            {
                'name': 'Модератор',
                'color': '#28a745',
                'emoji_class': 'fas fa-shield',
                'has_gradient': False,
                'is_visible': True
            },
            {
                'name': 'Администратор',
                'color': '#dc3545',
                'emoji_class': 'fas fa-hammer',
                'has_gradient': True,
                'gradient_end_color': '#c82333',
                'is_visible': True
            }
        ]

        for role_data in default_roles:
            existing = cls.query.filter_by(name=role_data['name']).first()
            if not existing:
                role = cls(**role_data)
                db.session.add(role)

        db.session.commit()


class PlayerAdminRole(db.Model):
    """Players assigned admin custom roles"""

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('admin_custom_role.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_by = db.Column(db.String(100), default='admin')
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    player = db.relationship('Player', backref='admin_roles')

    def __repr__(self):
        return f'<PlayerAdminRole {self.player_id}:{self.role_id}>'


class CustomTitle(db.Model):
    """Custom titles that players can unlock and display"""
    __tablename__ = 'custom_title'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)  # Internal name
    display_name = db.Column(db.String(100), nullable=False)  # What users see
    description = db.Column(db.Text, nullable=True)
    color = db.Column(db.String(20), default='#ffd700', nullable=False)
    glow_color = db.Column(db.String(20), nullable=True)  # For glow effects
    icon = db.Column(db.String(50), nullable=True)  # FontAwesome icon
    rarity = db.Column(db.String(20), default='common', nullable=False)  # common, rare, epic, legendary, mythic
    unlock_condition = db.Column(db.Text, nullable=True)  # JSON string describing how to unlock
    is_hidden = db.Column(db.Boolean, default=False, nullable=False)  # Hidden until unlocked
    unlock_level = db.Column(db.Integer, default=1, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<CustomTitle {self.name}>'

    @classmethod
    def create_default_titles(cls):
        """Create default titles if they don't exist"""
        default_titles = [
            {
                'name': 'rookie',
                'display_name': '🌟 Новичок',
                'description': 'Первые шаги в мире Bedwars',
                'color': '#28a745',
                'rarity': 'common',
                'unlock_level': 1
            },
            {
                'name': 'killer',
                'display_name': '⚔️ Убийца',
                'description': 'Для тех, кто любит сражения',
                'color': '#dc3545',
                'rarity': 'common',
                'unlock_level': 5
            },
            {
                'name': 'destroyer',
                'display_name': '💥 Разрушитель',
                'description': 'Мастер разрушения кроватей',
                'color': '#fd7e14',
                'rarity': 'rare',
                'unlock_level': 10
            },
            {
                'name': 'legend',
                'display_name': '👑 Легенда',
                'description': 'Легендарный игрок',
                'color': '#ffc107',
                'glow_color': '#ffed4e',
                'rarity': 'legendary',
                'unlock_level': 50
            }
        ]

        for title_data in default_titles:
            existing = cls.query.filter_by(name=title_data['name']).first()
            if not existing:
                title = cls(**title_data)
                db.session.add(title)

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error creating default titles: {e}")

    @classmethod
    def get_unlockable_for_player(cls, player):
        """Get titles that a player can unlock based on their stats"""
        unlockable = cls.query.filter(
            cls.unlock_level <= player.level,
            cls.is_hidden == False
        ).all()

        # Check if player already has these titles
        player_titles = PlayerTitle.query.filter_by(player_id=player.id).all()
        owned_title_ids = [pt.title_id for pt in player_titles]

        return [title for title in unlockable if title.id not in owned_title_ids]


class PlayerTitle(db.Model):
    """Custom titles assigned to players by admins"""

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    title_id = db.Column(db.Integer, db.ForeignKey('custom_title.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_by = db.Column(db.String(100), default='admin')
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    player = db.relationship('Player', backref='custom_titles')
    title = db.relationship('CustomTitle', backref='assigned_players')

    def __repr__(self):
        return f'<PlayerTitle {self.player_id}:{self.title_id}>'


class PlayerActiveBooster(db.Model):
    """Active boosters that players currently have"""

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    booster_type = db.Column(db.String(50), nullable=False)  # active_coins_booster, active_reputation_booster, etc.
    multiplier = db.Column(db.Float, nullable=False, default=1.0)  # 1.5, 2.0, 3.0 etc.
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    # Relationship
    player = db.relationship('Player', backref='active_boosters')

    def __repr__(self):
        return f'<PlayerActiveBooster {self.player_id}:{self.booster_type}>'

    @property
    def is_expired(self):
        return datetime.utcnow() > self.expires_at

    @property
    def time_remaining(self):
        if self.is_expired:
            return 0
        return int((self.expires_at - datetime.utcnow()).total_seconds())

    @classmethod
    def get_active_boosters(cls, player_id):
        """Get all active boosters for a player"""
        return cls.query.filter_by(
            player_id=player_id,
            is_active=True
        ).filter(cls.expires_at > datetime.utcnow()).all()

    @classmethod
    def get_coins_multiplier(cls, player_id):
        """Get current coins multiplier for a player"""
        boosters = cls.query.filter_by(
            player_id=player_id,
            is_active=True
        ).filter(
            cls.expires_at > datetime.utcnow(),
            cls.booster_type.in_(['active_coins_booster', 'active_mega_booster'])
        ).all()

        multiplier = 1.0
        for booster in boosters:
            multiplier *= booster.multiplier
        return multiplier

    @classmethod
    def get_reputation_multiplier(cls, player_id):
        """Get current reputation multiplier for a player"""
        boosters = cls.query.filter_by(
            player_id=player_id,
            is_active=True
        ).filter(
            cls.expires_at > datetime.utcnow(),
            cls.booster_type.in_(['active_reputation_booster', 'active_mega_booster'])
        ).all()

        multiplier = 1.0
        for booster in boosters:
            multiplier *= booster.multiplier
        return multiplier


class GradientTheme(db.Model):
    """Gradient themes for various UI elements"""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    element_type = db.Column(db.String(30), nullable=False)  # 'nickname', 'stats', 'role', etc.
    color1 = db.Column(db.String(7), nullable=False)  # Hex color
    color2 = db.Column(db.String(7), nullable=False)  # Hex color
    color3 = db.Column(db.String(7), nullable=True)   # Optional third color
    gradient_direction = db.Column(db.String(20), default='45deg')
    animation_enabled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<GradientTheme {self.name}>'

    @property
    def css_gradient(self):
        """Generate CSS gradient string"""
        if self.color3:
            return f"linear-gradient({self.gradient_direction}, {self.color1}, {self.color2}, {self.color3})"
        return f"linear-gradient({self.gradient_direction}, {self.color1}, {self.color2})"

    @classmethod
    def create_default_themes(cls):
        """Create default gradient themes"""
        default_themes = [
            # Nickname gradients
            {
                'name': 'fire_nickname',
                'display_name': '🔥 Лавовый Взрыв',
                'element_type': 'nickname',
                'color1': '#ff6b35',
                'color2': '#f7931e',
                'color3': '#ffaa00',
                'gradient_direction': '45deg',
                'animation_enabled': True
            },
            {
                'name': 'ocean_nickname',
                'display_name': '🌊 Глубины Океана',
                'element_type': 'nickname',
                'color1': '#00d2ff',
                'color2': '#3a7bd5',
                'gradient_direction': '45deg',
                'animation_enabled': False
            },
            {
                'name': 'purple_nickname',
                'display_name': '🔮 Эссенция Энда',
                'element_type': 'nickname',
                'color1': '#667eea',
                'color2': '#764ba2',
                'gradient_direction': '45deg',
                'animation_enabled': False
            },
            {
                'name': 'rainbow_nickname',
                'display_name': '🌈 Радужный',
                'element_type': 'nickname',
                'color1': '#ff0000',
                'color2': '#ffff00',
                'color3': '#00ff00',
                'gradient_direction': '90deg',
                'animation_enabled': True
            },

            # Stats gradients
            {
                'name': 'gold_stats',
                'display_name': '🥇 Золотые Слитки',
                'element_type': 'stats',
                'color1': '#ffd700',
                'color2': '#ffed4e',
                'gradient_direction': '45deg',
                'animation_enabled': False
            },
            {
                'name': 'emerald_stats',
                'display_name': '💎 Изумрудная Руда',
                'element_type': 'stats',
                'color1': '#50c878',
                'color2': '#00ff7f',
                'gradient_direction': '45deg',
                'animation_enabled': False
            },
            {
                'name': 'blood_stats',
                'display_name': '🩸 Кровавый Закат',
                'element_type': 'stats',
                'color1': '#dc143c',
                'color2': '#ff1744',
                'gradient_direction': '45deg',
                'animation_enabled': False
            },

            # Individual stat gradients
            {
                'name': 'fire_kills',
                'display_name': '🔥 Огненные киллы',
                'element_type': 'kills',
                'color1': '#ff6b35',
                'color2': '#f7931e',
                'gradient_direction': '45deg',
                'animation_enabled': True
            },
            {
                'name': 'ice_deaths',
                'display_name': '❄️ Ледяные смерти',
                'element_type': 'deaths',
                'color1': '#74b9ff',
                'color2': '#0984e3',
                'gradient_direction': '45deg',
                'animation_enabled': False
            },
            {
                'name': 'golden_wins',
                'display_name': '🏆 Золотые победы',
                'element_type': 'wins',
                'color1': '#ffd700',
                'color2': '#ffaa00',
                'gradient_direction': '45deg',
                'animation_enabled': True
            },
            {
                'name': 'diamond_beds',
                'display_name': '💎 Алмазные кровати',
                'element_type': 'beds',
                'color1': '#74b9ff',
                'color2': '#0984e3',
                'color3': '#6c5ce7',
                'gradient_direction': '45deg',
                'animation_enabled': False
            },

            # Title gradients
            {
                'name': 'legendary_title',
                'display_name': '👑 Легендарный титул',
                'element_type': 'title',
                'color1': '#ffd700',
                'color2': '#ff6b35',
                'color3': '#8e44ad',
                'gradient_direction': '45deg',
                'animation_enabled': True
            },
            {
                'name': 'crystal_title',
                'display_name': '💎 Кристальный титул',
                'element_type': 'title',
                'color1': '#74b9ff',
                'color2': '#0984e3',
                'gradient_direction': '45deg',
                'animation_enabled': False
            },

            # Status gradients (level 20+)
            {
                'name': 'sunset_status',
                'display_name': '🌅 Закатный статус',
                'element_type': 'status',
                'color1': '#ff6b35',
                'color2': '#f7931e',
                'gradient_direction': '45deg',
                'animation_enabled': False
            },
            {
                'name': 'ocean_status',
                'display_name': '🌊 Океанский статус',
                'element_type': 'status',
                'color1': '#00d2ff',
                'color2': '#3a7bd5',
                'gradient_direction': '45deg',
                'animation_enabled': False
            },
            {
                'name': 'mystic_status',
                'display_name': '🔮 Мистический статус',
                'element_type': 'status',
                'color1': '#667eea',
                'color2': '#764ba2',
                'gradient_direction': '45deg',
                'animation_enabled': True
            },

            # Bio gradients (level 20+)
            {
                'name': 'elegant_bio',
                'display_name': '✨ Элегантное био',
                'element_type': 'bio',
                'color1': '#ffd700',
                'color2': '#ffed4e',
                'gradient_direction': '45deg',
                'animation_enabled': False
            },
            {
                'name': 'royal_bio',
                'display_name': '👑 Королевское био',
                'element_type': 'bio',
                'color1': '#8e44ad',
                'color2': '#3498db',
                'gradient_direction': '45deg',
                'animation_enabled': False
            },
            {
                'name': 'cosmic_bio',
                'display_name': '🌌 Космическое био',
                'element_type': 'bio',
                'color1': '#667eea',
                'color2': '#764ba2',
                'color3': '#f093fb',
                'gradient_direction': '45deg',
                'animation_enabled': True
            },

            # Role gradients
            {
                'name': 'admin_role',
                'display_name': '👑 Администраторская роль',
                'element_type': 'role',
                'color1': '#ff6b35',
                'color2': '#f7931e',
                'gradient_direction': '45deg',
                'animation_enabled': True
            },
            {
                'name': 'vip_role',
                'display_name': '💎 VIP роль',
                'element_type': 'role',
                'color1': '#8e44ad',
                'color2': '#3498db',
                'gradient_direction': '45deg',
                'animation_enabled': False
            },
            {
                'name': 'pro_role',
                'display_name': '⭐ Профессиональная роль',
                'element_type': 'role',
                'color1': '#28a745',
                'color2': '#20c997',
                'gradient_direction': '45deg',
                'animation_enabled': False
            }
        ]

        for theme_data in default_themes:
            existing = cls.query.filter_by(name=theme_data['name']).first()
            if not existing:
                theme = cls(**theme_data)
                db.session.add(theme)

        db.session.commit()


class PlayerGradientSetting(db.Model):
    """Player's gradient settings"""

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    element_type = db.Column(db.String(50), nullable=False)  # nickname, stats, etc.
    gradient_theme_id = db.Column(db.Integer, db.ForeignKey('gradient_theme.id'), nullable=True)
    custom_color1 = db.Column(db.String(7), nullable=True)
    custom_color2 = db.Column(db.String(7), nullable=True)
    custom_color3 = db.Column(db.String(7), nullable=True)
    is_enabled = db.Column(db.Boolean, default=True)
    assigned_by = db.Column(db.String(100), default='admin')
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    player = db.relationship('Player', backref='gradient_settings')
    gradient_theme = db.relationship('GradientTheme', backref='player_settings')

    def __repr__(self):
        return f'<PlayerGradientSetting {self.player_id}:{self.element_type}>'

    @property
    def css_gradient(self):
        """Get CSS gradient for this setting"""
        if self.gradient_theme_id and self.gradient_theme:
            return self.gradient_theme.css_gradient
        elif self.custom_color1 and self.custom_color2:
            if self.custom_color3:
                return f"linear-gradient(45deg, {self.custom_color1}, {self.custom_color2}, {self.custom_color3})"
            return f"linear-gradient(45deg, {self.custom_color1}, {self.custom_color2})"
        return None


class SiteTheme(db.Model):
    """Site themes for different visual styles"""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    primary_color = db.Column(db.String(7), default='#ffc107')
    secondary_color = db.Column(db.String(7), default='#6c757d')
    background_color = db.Column(db.String(7), default='#1a1a1a')
    card_background = db.Column(db.String(7), default='#2d2d2d')
    text_color = db.Column(db.String(7), default='#ffffff')
    accent_color = db.Column(db.String(7), default='#ffaa00')
    is_active = db.Column(db.Boolean, default=True)
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<SiteTheme {self.name}>'

    @property
    def css_variables(self):
        """Generate CSS variables for the theme"""
        return {
            '--primary-color': self.primary_color,
            '--secondary-color': self.secondary_color,
            '--bg-primary': f'linear-gradient(135deg, {self.background_color} 0%, {self.card_background} 100%)',
            '--bg-secondary': f'linear-gradient(135deg, {self.card_background} 0%, {self.background_color} 100%)',
            '--text-color': self.text_color,
            '--accent-color': self.accent_color
        }

    @classmethod
    def create_default_themes(cls):
        """Create default site themes"""
        default_themes = [
            {
                'name': 'default_dark',
                'display_name': 'Классическая тёмная',
                'description': 'Элегантная тёмная тема с золотыми акцентами',
                'primary_color': '#ffc107',
                'secondary_color': '#6c757d',
                'background_color': '#0d1117',
                'card_background': '#161b22',
                'text_color': '#f0f6fc',
                'accent_color': '#28a745',
                'is_default': True
            },
            {
                'name': 'cyber_matrix',
                'display_name': 'Киберматрица',
                'description': 'Футуристическая тема в стиле "Матрицы"',
                'primary_color': '#00ff41',
                'secondary_color': '#008f11',
                'background_color': '#000000',
                'card_background': '#001100',
                'text_color': '#00ff41',
                'accent_color': '#39ff14'
            },
            {
                'name': 'royal_purple',
                'display_name': 'Королевский пурпур',
                'description': 'Роскошная тёмно-фиолетовая тема',
                'primary_color': '#9146ff',
                'secondary_color': '#772ce8',
                'background_color': '#0e0a20',
                'card_background': '#1f0a3e',
                'text_color': '#ffffff',
                'accent_color': '#bf94ff'
            },
            {
                'name': 'ocean_depths',
                'display_name': 'Морские глубины',
                'description': 'Глубокая синяя тема океана',
                'primary_color': '#00b4d8',
                'secondary_color': '#0077b6',
                'background_color': '#03045e',
                'card_background': '#023e8a',
                'text_color': '#caf0f8',
                'accent_color': '#90e0ef'
            },
            {
                'name': 'volcano_fire',
                'display_name': '🌋 Лавовое Озеро',
                'description': 'Раскаленная магма Нижнего мира',
                'primary_color': '#ff4500',
                'secondary_color': '#dc2626',
                'background_color': '#1a0000',
                'card_background': '#330000',
                'text_color': '#fef2f2',
                'accent_color': '#fb923c'
            },
            {
                'name': 'midnight_blue',
                'display_name': '🌙 Ночное Небо',
                'description': 'Темнота звездной ночи',
                'primary_color': '#60a5fa',
                'secondary_color': '#3b82f6',
                'background_color': '#0f172a',
                'card_background': '#1e293b',
                'text_color': '#f1f5f9',
                'accent_color': '#38bdf8'
            },
            {
                'name': 'emerald_forest',
                'display_name': '🌲 Изумрудный Биом',
                'description': 'Зеленые просторы джунглей',
                'primary_color': '#10b981',
                'secondary_color': '#059669',
                'background_color': '#064e3b',
                'card_background': '#065f46',
                'text_color': '#ecfdf5',
                'accent_color': '#34d399'
            },
            {
                'name': 'sunset_orange',
                'display_name': 'Закатный оранжевый',
                'description': 'Тёплая оранжево-красная тема',
                'primary_color': '#f97316',
                'secondary_color': '#ea580c',
                'background_color': '#431407',
                'card_background': '#7c2d12',
                'text_color': '#fff7ed',
                'accent_color': '#fb923c'
            },
            {
                'name': 'pink_neon',
                'display_name': 'Неоновый розовый',
                'description': 'Яркая розово-фиолетовая тема',
                'primary_color': '#ec4899',
                'secondary_color': '#db2777',
                'background_color': '#500724',
                'card_background': '#831843',
                'text_color': '#fdf2f8',
                'accent_color': '#f472b6'
            },
            {
                'name': 'golden_luxury',
                'display_name': 'Золотая роскошь',
                'description': 'Роскошная золотисто-чёрная тема',
                'primary_color': '#fbbf24',
                'secondary_color': '#f59e0b',
                'background_color': '#1c1917',
                'card_background': '#292524',
                'text_color': '#fef3c7',
                'accent_color': '#fcd34d'
            },
            {
                'name': 'ice_crystal',
                'display_name': 'Ледяной кристалл',
                'description': 'Холодная голубо-белая тема',
                'primary_color': '#0ea5e9',
                'secondary_color': '#0284c7',
                'background_color': '#0c4a6e',
                'card_background': '#075985',
                'text_color': '#e0f2fe',
                'accent_color': '#38bdf8'
            }
        ]

        for theme_data in default_themes:
            existing = cls.query.filter_by(name=theme_data['name']).first()
            if not existing:
                theme = cls(**theme_data)
                db.session.add(theme)

        db.session.commit()


class CursorTheme(db.Model):
    """Cursor themes for customization"""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    color1 = db.Column(db.String(7), default='#ffc107')
    color2 = db.Column(db.String(7), default='#ffaa00')
    animation = db.Column(db.String(50), default='glow')  # glow, pulse, rotate, rainbow
    size = db.Column(db.String(10), default='normal')  # small, normal, large
    shape = db.Column(db.String(20), default='circle')  # circle, square, diamond, star
    is_premium = db.Column(db.Boolean, default=False)
    price_coins = db.Column(db.Integer, default=0)
    unlock_level = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<CursorTheme {self.name}>'

    @classmethod
    def create_default_cursors(cls):
        """Create default cursor themes"""
        default_cursors = [
            {
                'name': 'classic',
                'display_name': '🎯 Классический',
                'description': 'Стандартный игровой курсор',
                'color1': '#ffc107',
                'color2': '#ffaa00',
                'animation': 'glow',
                'price_coins': 0
            },
            {
                'name': 'fire',
                'display_name': '🔥 Огненный',
                'description': 'Пылающий курсор для настоящих воинов',
                'color1': '#ff6b35',
                'color2': '#f7931e',
                'animation': 'pulse',
                'price_coins': 50,
                'unlock_level': 5
            },
            {
                'name': 'ice',
                'display_name': '❄️ Ледяной',
                'description': 'Холодный как лед курсор',
                'color1': '#74b9ff',
                'color2': '#0984e3',
                'animation': 'glow',
                'price_coins': 75,
                'unlock_level': 10
            },
            {
                'name': 'lightning',
                'display_name': '⚡ Молния',
                'description': 'Быстрый как молния курсор',
                'color1': '#fdcb6e',
                'color2': '#e17055',
                'animation': 'pulse',
                'shape': 'diamond',
                'price_coins': 100,
                'unlock_level': 15,
                'is_premium': True
            },
            {
                'name': 'rainbow',
                'display_name': '🌈 Радужный',
                'description': 'Переливающийся всеми цветами курсор',
                'color1': '#ff0000',
                'color2': '#00ff00',
                'animation': 'rainbow',
                'price_coins': 200,
                'unlock_level': 25,
                'is_premium': True
            },
            {
                'name': 'galaxy',
                'display_name': '🌌 Галактический',
                'description': 'Космический курсор для покорителей вселенной',
                'color1': '#6c5ce7',
                'color2': '#a29bfe',
                'animation': 'rotate',
                'shape': 'star',
                'price_coins': 500,
                'unlock_level': 50,
                'is_premium': True
            }
        ]

        for cursor_data in default_cursors:
            existing = cls.query.filter_by(name=cursor_data['name']).first()
            if not existing:
                cursor = cls(**cursor_data)
                db.session.add(cursor)

        db.session.commit()

    @classmethod
    def create_default_items(cls):
        """Create default shop items"""
        # Этот метод можно оставить пустым или добавить базовые предметы
        pass


class ShopCategory(db.Model):
    """Shop categories for organizing items"""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(50), default='fas fa-shopping-bag')
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<ShopCategory {self.name}>'