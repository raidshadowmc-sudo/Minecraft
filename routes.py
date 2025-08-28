from flask import render_template, request, redirect, url_for, flash, session, jsonify, make_response
from app import app, db
import os
import csv
import io
from datetime import datetime, date, timedelta

# Import models
from models import (Player, Quest, PlayerQuest, Achievement, PlayerAchievement, 
                   CustomTitle, PlayerTitle, GradientTheme, PlayerGradientSetting, 
                   SiteTheme, ShopItem, ShopPurchase, PlayerActiveBooster, 
                   AdminCustomRole, PlayerAdminRole, Badge, PlayerBadge, 
                   ReputationLog, ASCENDData, Candidate, CandidateComment, 
                   CandidateReaction, GameMode, ASCENDHistory, Target, TargetReaction)

# API routes are handled directly in api_routes.py

# Admin password
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Minekillfire13!')

# Decorator to ensure admin access
def admin_required(f):
    """Decorator to check if the current user is an admin"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin', False):
            flash('Доступ запрещен! Требуется авторизация администратора.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_current_player():
    """Inject current player data into all templates"""
    current_player = None
    player_nickname = session.get('player_nickname')
    if player_nickname:
        current_player = Player.query.filter_by(nickname=player_nickname).first()

    # Set default language if not set
    if 'language' not in session:
        session['language'] = 'ru'

    # Get server statistics for footer
    try:
        server_stats = {
            'total_players': Player.query.count(),
            'online_players': Player.query.filter(Player.last_updated >= datetime.utcnow() - timedelta(minutes=30)).count(),
            'total_wins': db.session.query(db.func.sum(Player.wins)).scalar() or 0,
            'is_online': True
        }
    except Exception as e:
        app.logger.error(f"Error getting server stats: {e}")
        server_stats = {
            'total_players': 0,
            'online_players': 0,
            'total_wins': 0,
            'is_online': False
        }

    return dict(
        current_player=current_player,
        current_language=session.get('language', 'ru'),
        server_stats=server_stats
    )

@app.route('/')
@app.route('/index')
def index():
    """Display the enhanced leaderboard"""
    try:
        sort_by = request.args.get('sort', 'experience')
        search = request.args.get('search', '').strip()
        page = max(1, int(request.args.get('page', 1)))
        limit = min(int(request.args.get('limit', 50)), 50)  # Max 50 records
        offset = (page - 1) * limit

        # Получаем результаты лидерборда с оптимизацией
        try:
            if search:
                players = Player.search_players(search, limit=limit, offset=offset)
            else:
                players = Player.get_leaderboard(sort_by=sort_by, limit=limit, offset=offset)
        except Exception as e:
            app.logger.error(f"Error getting leaderboard data: {e}")
            players = []
            flash('Ошибка загрузки лидерборда. Попробуйте позже.', 'error')

        is_admin = session.get('is_admin', False)

        try:
            stats = Player.get_statistics()
        except Exception as e:
            app.logger.error(f"Error getting statistics: {e}")
            stats = {
                'total_players': 0,
                'total_kills': 0,
                'total_deaths': 0,
                'total_wins': 0,
                'total_games': 0,
                'average_level': 0
            }

        # Initialize theme in session if not set
        if 'current_theme' not in session:
            player_nickname = session.get('player_nickname')
            if player_nickname:
                try:
                    player = Player.query.filter_by(nickname=player_nickname).first()
                    if player and player.selected_theme:
                        theme = player.selected_theme
                        session['current_theme'] = {
                            'id': theme.id,
                            'name': theme.name,
                            'display_name': theme.display_name,
                            'primary_color': theme.primary_color,
                            'secondary_color': theme.secondary_color,
                            'background_color': theme.background_color,
                            'card_background': theme.card_background,
                            'text_color': theme.text_color,
                            'accent_color': theme.accent_color
                        }
                except Exception as e:
                    app.logger.error(f"Error loading theme: {e}")

        return render_template('index.html',
                             players=players,
                             current_sort=sort_by,
                             search_query=search,
                             is_admin=is_admin,
                             stats=stats,
                             limit=limit)
    except Exception as e:
        app.logger.error(f"Critical error in index route: {e}")
        return render_template('index.html',
                             players=[],
                             current_sort='experience',
                             search_query='',
                             is_admin=False,
                             stats={
                                 'total_players': 0,
                                 'total_kills': 0,
                                 'total_deaths': 0,
                                 'total_wins': 0,
                                 'total_games': 0,
                                 'average_level': 0
                             },
                             limit=50)

@app.route('/player/<int:player_id>')
def player_profile(player_id):
    """Display detailed player profile (admin view)"""
    player = Player.query.get_or_404(player_id)
    is_admin = session.get('is_admin', False)
    current_player = None

    # Check if current user is the player owner
    player_nickname = session.get('player_nickname')
    is_owner = False
    if player_nickname:
        current_player = Player.query.filter_by(nickname=player_nickname).first()
        is_owner = current_player and current_player.id == player.id

    # Get player's badges
    player_badges = PlayerBadge.query.filter_by(player_id=player.id, is_visible=True).all()
    badges_data = []
    for pb in player_badges:
        badge = Badge.query.get(pb.badge_id)
        if badge and badge.is_active:
            badges_data.append({
                'badge': badge,
                'display_name': badge.display_name,
                'icon': badge.icon,
                'color': badge.color,
                'background_color': badge.background_color,
                'border_color': badge.border_color,
                'rarity': badge.rarity,
                'has_gradient': badge.has_gradient,
                'gradient_start': badge.gradient_start,
                'gradient_end': badge.gradient_end,
                'is_animated': badge.is_animated
            })

    # Get player skill rating
    skill_rating = None
    try:
        from models import PlayerSkillRating
        skill_rating = PlayerSkillRating.get_or_create_rating(player.id)
    except Exception as e:
        app.logger.error(f"Error getting skill rating: {e}")

    return render_template('player_profile.html',
                         player=player,
                         is_admin=is_admin,
                         is_owner=is_owner,
                         player_badges=badges_data,
                         skill_rating=skill_rating)

@app.route('/public/<int:player_id>')
def public_profile(player_id):
    """Display public player profile (read-only view)"""
    player = Player.query.get_or_404(player_id)
    current_player = None

    # Check if profile is public
    if not player.profile_is_public:
        flash('Профиль игрока скрыт от публичного просмотра', 'warning')
        return redirect(url_for('index'))

    # Check if current user is the player owner
    player_nickname = session.get('player_nickname')
    is_owner = False
    if player_nickname:
        current_player = Player.query.filter_by(nickname=player_nickname).first()
        is_owner = current_player and current_player.id == player.id

    # Get player's visible badges
    player_badges = PlayerBadge.query.filter_by(player_id=player.id, is_visible=True).all()
    badges_data = []
    for pb in player_badges:
        badge = Badge.query.get(pb.badge_id)
        if badge and badge.is_active:
            badges_data.append({
                'badge': badge,
                'display_name': badge.display_name,
                'icon': badge.icon,
                'color': badge.color,
                'background_color': badge.background_color,
                'border_color': badge.border_color,
                'rarity': badge.rarity,
                'has_gradient': badge.has_gradient,
                'gradient_start': badge.gradient_start,
                'gradient_end': badge.gradient_end,
                'is_animated': badge.is_animated
            })

    return render_template('public_profile.html',
                         player=player,
                         is_owner=is_owner,
                         player_badges=badges_data)

@app.route('/compare')
def compare_players():
    """Player comparison page"""
    players = Player.query.order_by(Player.experience.desc()).all()
    return render_template('compare.html', players=players)

@app.route('/api/compare/<int:player1_id>/<int:player2_id>')
def api_compare_players(player1_id, player2_id):
    """API endpoint for player comparison"""
    try:
        player1 = Player.query.get_or_404(player1_id)
        player2 = Player.query.get_or_404(player2_id)

        comparison_data = {
            'player1': {
                'id': player1.id,
                'nickname': player1.nickname,
                'level': player1.level,
                'experience': player1.experience,
                'kills': player1.kills,
                'final_kills': player1.final_kills,
                'deaths': player1.deaths,
                'kd_ratio': player1.kd_ratio,
                'fkd_ratio': player1.fkd_ratio,
                'beds_broken': player1.beds_broken,
                'wins': player1.wins,
                'games_played': player1.games_played,
                'win_rate': player1.win_rate,
                'role': player1.display_role,
                'skin_url': player1.minecraft_skin_url,
                'star_rating': player1.star_rating
            },
            'player2': {
                'id': player2.id,
                'nickname': player2.nickname,
                'level': player2.level,
                'experience': player2.experience,
                'kills': player2.kills,
                'final_kills': player2.final_kills,
                'deaths': player2.deaths,
                'kd_ratio': player2.kd_ratio,
                'fkd_ratio': player2.fkd_ratio,
                'beds_broken': player2.beds_broken,
                'wins': player2.wins,
                'games_played': player2.games_played,
                'win_rate': player2.win_rate,
                'role': player2.display_role,
                'skin_url': player2.minecraft_skin_url,
                'star_rating': player2.star_rating
            }
        }

        return jsonify(comparison_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/statistics')
def statistics():
    """Display detailed statistics page"""
    stats = Player.get_statistics()
    top_players = {
        'experience': Player.get_leaderboard('experience', 5),
        'kills': Player.get_leaderboard('kills', 5),
        'final_kills': Player.get_leaderboard('final_kills', 5),
        'beds_broken': Player.get_leaderboard('beds_broken', 5),
        'wins': Player.get_leaderboard('wins', 5)
    }

    is_admin = session.get('is_admin', False)

    return render_template('statistics.html',
                         stats=stats,
                         top_players=top_players,
                         is_admin=is_admin)

@app.route('/admin')
def admin():
    """Admin panel"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен! Требуется авторизация администратора.', 'error')
        return redirect(url_for('login'))

    stats = Player.get_statistics()
    recent_players = Player.query.order_by(Player.created_at.desc()).limit(10).all()

    return render_template('admin.html',
                         stats=stats,
                         recent_players=recent_players)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == ADMIN_PASSWORD:
            session['is_admin'] = True
            flash('Добро пожаловать, администратор!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Неверный пароль!', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    """Admin logout"""
    session.pop('is_admin', None)
    flash('Вы вышли из системы', 'success')
    return redirect(url_for('index'))

@app.route('/admin/unlock-title', methods=['POST'])
@admin_required
def unlock_title():
    """Unlock title for player"""
    try:
        player_id = request.form.get('player_id')
        title_name = request.form.get('title_name')

        if not player_id or not title_name:
            flash('Выберите игрока и титул!', 'error')
            return redirect(url_for('admin_titles'))

        player = Player.query.get_or_404(player_id)
        title = CustomTitle.query.filter_by(name=title_name).first()

        if not title:
            flash('Титул не найден!', 'error')
            return redirect(url_for('admin_titles'))

        # Check if already unlocked
        existing = PlayerTitle.query.filter_by(
            player_id=player.id,
            title_id=title.id
        ).first()

        if existing:
            flash(f'Титул "{title.display_name}" уже разблокирован для {player.nickname}!', 'warning')
        else:
            # Create new title unlock
            player_title = PlayerTitle(
                player_id=player.id,
                title_id=title.id,
                unlocked_at=datetime.utcnow()
            )
            db.session.add(player_title)
            db.session.commit()

            flash(f'Титул "{title.display_name}" разблокирован для {player.nickname}!', 'success')

    except Exception as e:
        app.logger.error(f"Error unlocking title: {e}")
        flash('Ошибка при разблокировке титула!', 'error')
        db.session.rollback()

    return redirect(url_for('admin_titles'))

@app.route('/admin/embed-builder')
@admin_required
def admin_embed_builder():
    """Admin embed builder page"""
    return render_template('admin_embed_builder.html')

@app.route('/admin/send-embed', methods=['POST'])
@admin_required 
def send_embed():
    """Send embed via Discord bot"""
    try:
        import requests
        import json

        # Get form data
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        color = request.form.get('color', '#3498db')
        footer = request.form.get('footer', '').strip()
        image_url = request.form.get('image_url', '').strip()
        channel_id = request.form.get('channel_id', '').strip()

        if not title or not description:
            flash('Заголовок и описание обязательны!', 'error')
            return redirect(url_for('admin_embed_builder'))

        if not channel_id:
            flash('Укажите ID канала!', 'error')
            return redirect(url_for('admin_embed_builder'))

        # Create embed data
        embed_data = {
            'title': title,
            'description': description,
            'color': color,
            'footer': footer,
            'image_url': image_url,
            'channel_id': channel_id
        }

        # Here you would send this to your Discord bot
        # For now, we'll just flash a success message
        flash(f'Embed "{title}" успешно отправлен в канал!', 'success')

    except Exception as e:
        app.logger.error(f"Error sending embed: {e}")
        flash('Ошибка при отправке embed!', 'error')

    return redirect(url_for('admin_embed_builder'))

@app.route('/admin/titles')
@admin_required
def admin_titles():
    """Admin titles management page"""
    try:
        titles = CustomTitle.query.all()
        players = Player.query.order_by(Player.nickname).all()
        return render_template('admin_titles.html', titles=titles, players=players)
    except Exception as e:
        app.logger.error(f"Error in admin_titles: {e}")
        flash('Ошибка загрузки титулов!', 'error')
        return redirect(url_for('admin'))

@app.route('/admin/create-title', methods=['POST'])
@admin_required
def create_title():
    """Create new custom title"""
    try:
        name = request.form.get('name', '').strip()
        display_name = request.form.get('display_name', '').strip()
        color = request.form.get('color', '#ffc107')
        icon = request.form.get('icon', '').strip()
        rarity = request.form.get('rarity', 'common')

        if not name or not display_name:
            flash('Заполните обязательные поля!', 'error')
            return redirect(url_for('admin_titles'))

        # Check if exists
        existing = CustomTitle.query.filter_by(name=name).first()
        if existing:
            flash('Титул с таким названием уже существует!', 'error')
            return redirect(url_for('admin_titles'))

        # Create title
        title = CustomTitle(
            name=name,
            display_name=display_name,
            color=color,
            icon=icon,
            rarity=rarity
        )

        db.session.add(title)
        db.session.commit()

        flash(f'Титул "{display_name}" создан!', 'success')

    except Exception as e:
        app.logger.error(f"Error creating title: {e}")
        flash('Ошибка при создании титула!', 'error')
        db.session.rollback()

    return redirect(url_for('admin_titles'))

@app.route('/admin/roles')
@admin_required
def admin_roles():
    """Admin roles management page"""
    try:
        # Initialize default roles if none exist
        if AdminCustomRole.query.count() == 0:
            AdminCustomRole.create_default_roles()

        roles = AdminCustomRole.query.all()
        players = Player.query.order_by(Player.nickname).all()

        # Get role assignments
        role_assignments = {}
        for role in roles:
            assignments = PlayerAdminRole.query.filter_by(role_id=role.id, is_active=True).all()
            role_assignments[role.id] = [assignment.player for assignment in assignments]

        return render_template('admin_roles.html', 
                             roles=roles, 
                             players=players,
                             role_assignments=role_assignments)

    except Exception as e:
        app.logger.error(f"Error in admin_roles: {e}")
        flash('Ошибка загрузки ролей!', 'error')
        return redirect(url_for('admin'))

@app.route('/admin/gradients')
@admin_required
def admin_gradients():
    """Admin gradients management page"""
    try:
        # Initialize themes if none exist
        if GradientTheme.query.count() == 0:
            GradientTheme.create_default_themes()

        # Group themes by element type
        all_themes = GradientTheme.query.all()
        grouped_themes = {}
        for theme in all_themes:
            if theme.element_type not in grouped_themes:
                grouped_themes[theme.element_type] = []
            grouped_themes[theme.element_type].append(theme)

        players = Player.query.order_by(Player.nickname).all()

        return render_template('admin_gradients.html', 
                             grouped_themes=grouped_themes, 
                             players=players)

    except Exception as e:
        app.logger.error(f"Error in admin_gradients: {e}")
        flash('Ошибка загрузки градиентов!', 'error')
        return redirect(url_for('admin'))

@app.route('/admin/badges')
@admin_required
def admin_badges():
    """Admin badges management page"""
    try:
        # Initialize badges if none exist
        if Badge.query.count() == 0:
            Badge.create_default_badges()

        badges = Badge.query.all()
        players = Player.query.order_by(Player.nickname).all()

        # Get badge statistics
        badge_stats = []
        for badge in badges:
            assigned_count = PlayerBadge.query.filter_by(badge_id=badge.id).count()
            badge_stats.append({
                'badge': badge,
                'assigned_count': assigned_count
            })

        # Prepare badges data for JavaScript
        badges_data = []
        for badge in badges:
            badges_data.append({
                'id': badge.id,
                'name': badge.name,
                'display_name': badge.display_name,
                'description': badge.description,
                'icon': badge.icon,
                'emoji': badge.emoji,
                'emoji_url': badge.emoji_url,
                'color': badge.color,
                'background_color': badge.background_color,
                'border_color': badge.border_color,
                'rarity': badge.rarity,
                'has_gradient': badge.has_gradient,
                'gradient_start': badge.gradient_start,
                'gradient_end': badge.gradient_end,
                'is_animated': badge.is_animated,
                'is_active': badge.is_active
            })

        return render_template('admin_badges.html', 
                             badges=badges,
                             players=players,
                             badge_stats=badge_stats,
                             badges_data=badges_data)

    except Exception as e:
        app.logger.error(f"Error in admin_badges: {e}")
        flash('Ошибка загрузки бейджей!', 'error')
        return redirect(url_for('admin'))

@app.route('/admin/create-role', methods=['POST'])
@admin_required
def create_role():
    """Create new custom role"""
    try:
        name = request.form.get('name', '').strip()
        color = request.form.get('color', '#ffc107')
        emoji = request.form.get('emoji', '').strip()
        emoji_url = request.form.get('emoji_url', '').strip()
        emoji_class = request.form.get('emoji_class', '').strip()
        has_gradient = 'has_gradient' in request.form
        gradient_end_color = request.form.get('gradient_end_color', '#ffaa00') if has_gradient else None

        if not name:
            flash('Заполните обязательные поля!', 'error')
            return redirect(url_for('admin_roles'))

        # Check if exists
        existing = AdminCustomRole.query.filter_by(name=name).first()
        if existing:
            flash('Роль с таким названием уже существует!', 'error')
            return redirect(url_for('admin_roles'))

        # Create role
        role = AdminCustomRole(
            name=name,
            color=color,
            emoji=emoji,
            emoji_url=emoji_url,
            emoji_class=emoji_class,
            has_gradient=has_gradient,
            gradient_end_color=gradient_end_color,
            created_by=session.get('player_nickname', 'admin')
        )

        db.session.add(role)
        db.session.commit()

        flash(f'Роль "{name}" создана!', 'success')

    except Exception as e:
        app.logger.error(f"Error creating role: {e}")
        flash('Ошибка при создании роли!', 'error')
        db.session.rollback()

    return redirect(url_for('admin_roles'))

@app.route('/admin/assign-role', methods=['POST'])
@admin_required
def assign_role():
    """Assign role to player"""
    try:
        player_id = request.form.get('player_id')
        role_id = request.form.get('role_id')

        if not player_id or not role_id:
            flash('Выберите игрока и роль!', 'error')
            return redirect(url_for('admin_roles'))

        player = Player.query.get_or_404(player_id)
        role = AdminCustomRole.query.get_or_404(role_id)

        # Check if already assigned
        existing = PlayerAdminRole.query.filter_by(
            player_id=player.id,
            role_id=role.id,
            is_active=True
        ).first()

        if existing:
            flash(f'Роль "{role.name}" уже назначена игроку {player.nickname}!', 'warning')
        else:
            # Create role assignment
            player_role = PlayerAdminRole(
                player_id=player.id,
                role_id=role.id,
                is_active=True,
                assigned_by=session.get('player_nickname', 'admin'),
                assigned_at=datetime.utcnow()
            )
            db.session.add(player_role)
            db.session.commit()

            flash(f'Роль "{role.name}" назначена игроку {player.nickname}!', 'success')

    except Exception as e:
        app.logger.error(f"Error assigning role: {e}")
        flash('Ошибка при назначении роли!', 'error')
        db.session.rollback()

    return redirect(url_for('admin_roles'))

@app.route('/admin/create-badge', methods=['POST'])
@admin_required
def create_badge():
    """Create new badge"""
    try:
        name = request.form.get('name', '').strip()
        display_name = request.form.get('display_name', '').strip()
        description = request.form.get('description', '').strip()
        icon = request.form.get('icon', 'fas fa-medal')
        emoji = request.form.get('emoji', '').strip()
        emoji_url = request.form.get('emoji_url', '').strip()
        color = request.form.get('color', '#ffffff')
        background_color = request.form.get('background_color', '#343a40')
        border_color = request.form.get('border_color', '#ffd700')
        rarity = request.form.get('rarity', 'common')
        has_gradient = 'has_gradient' in request.form
        gradient_start = request.form.get('gradient_start', '#ffd700') if has_gradient else None
        gradient_end = request.form.get('gradient_end', '#ffaa00') if has_gradient else None
        is_animated = 'is_animated' in request.form

        if not name or not display_name:
            flash('Заполните обязательные поля!', 'error')
            return redirect(url_for('admin_badges'))

        # Check if exists
        existing = Badge.query.filter_by(name=name).first()
        if existing:
            flash('Бейдж с таким названием уже существует!', 'error')
            return redirect(url_for('admin_badges'))

        # Create badge
        badge = Badge(
            name=name,
            display_name=display_name,
            description=description,
            icon=icon,
            emoji=emoji,
            emoji_url=emoji_url,
            color=color,
            background_color=background_color,
            border_color=border_color,
            rarity=rarity,
            has_gradient=has_gradient,
            gradient_start=gradient_start,
            gradient_end=gradient_end,
            is_animated=is_animated
        )

        db.session.add(badge)
        db.session.commit()

        flash(f'Бейдж "{display_name}" создан!', 'success')

    except Exception as e:
        app.logger.error(f"Error creating badge: {e}")
        flash('Ошибка при создании бейджа!', 'error')
        db.session.rollback()

    return redirect(url_for('admin_badges'))

@app.route('/admin/assign-badge', methods=['POST'])
@admin_required
def assign_badge():
    """Assign badge to player"""
    try:
        player_id = request.form.get('player_id')
        badge_id = request.form.get('badge_id')

        if not player_id or not badge_id:
            flash('Выберите игрока и бейдж!', 'error')
            return redirect(url_for('admin_badges'))

        player = Player.query.get_or_404(player_id)
        badge = Badge.query.get_or_404(badge_id)

        # Check if already assigned
        existing = PlayerBadge.query.filter_by(
            player_id=player.id,
            badge_id=badge.id
        ).first()

        if existing:
            flash(f'Бейдж "{badge.display_name}" уже назначен игроку {player.nickname}!', 'warning')
        else:
            # Create badge assignment
            player_badge = PlayerBadge(
                player_id=player.id,
                badge_id=badge.id,
                is_visible=True,
                earned_at=datetime.utcnow()
            )
            db.session.add(player_badge)
            db.session.commit()

            flash(f'Бейдж "{badge.display_name}" назначен игроку {player.nickname}!', 'success')

    except Exception as e:
        app.logger.error(f"Error assigning badge: {e}")
        flash('Ошибка при назначении бейджа!', 'error')
        db.session.rollback()

    return redirect(url_for('admin_badges'))

@app.route('/admin/reputation')
@admin_required
def admin_reputation():
    """Admin reputation management page"""
    players = Player.query.order_by(Player.reputation.desc()).all()
    return render_template('admin_reputation.html', players=players)

@app.route('/admin/give-coins', methods=['POST'])
@admin_required
def admin_give_coins():
    """Give coins to player"""
    try:
        player_id = request.form.get('player_id')
        coins = request.form.get('coins', type=int)

        if not player_id or not coins:
            flash('Выберите игрока и укажите количество койнов!', 'error')
            return redirect(url_for('admin_reputation'))

        player = Player.query.get_or_404(player_id)
        player.coins += coins
        db.session.commit()

        flash(f'Выдано {coins} койнов игроку {player.nickname}!', 'success')

    except Exception as e:
        app.logger.error(f"Error giving coins: {e}")
        flash('Ошибка при выдаче койнов!', 'error')
        db.session.rollback()

    return redirect(url_for('admin_reputation'))

@app.route('/admin/give-reputation', methods=['POST'])
@admin_required
def admin_give_reputation():
    """Give reputation to player"""
    try:
        player_id = request.form.get('player_id')
        reputation = request.form.get('reputation', type=int)

        if not player_id or reputation is None:
            flash('Выберите игрока и укажите количество репутации!', 'error')
            return redirect(url_for('admin_reputation'))

        player = Player.query.get_or_404(player_id)
        player.reputation += reputation
        db.session.commit()

        action = "выдано" if reputation > 0 else "снято"
        flash(f'{action} {abs(reputation)} репутации игроку {player.nickname}!', 'success')

    except Exception as e:
        app.logger.error(f"Error giving reputation: {e}")
        flash('Ошибка при изменении репутации!', 'error')
        db.session.rollback()

    return redirect(url_for('admin_reputation'))

@app.route('/themes')
def themes():
    """Theme selection page"""
    try:
        # Initialize default themes if none exist
        try:
            if SiteTheme.query.count() == 0:
                SiteTheme.create_default_themes()
        except Exception as e:
            app.logger.error(f"Error checking/creating themes: {e}")
            # Create minimal default theme
            try:
                db.create_all()
                default_theme = SiteTheme(
                    name='default_dark',
                    display_name='Классическая тёмная',
                    description='Элегантная тёмная тема с золотыми акцентами',
                    primary_color='#ffc107',
                    secondary_color='#6c757d',
                    background_color='#0d1117',
                    card_background='#161b22',
                    text_color='#f0f6fc',
                    accent_color='#28a745',
                    is_default=True
                )
                db.session.add(default_theme)
                db.session.commit()
            except Exception as create_error:
                app.logger.error(f"Failed to create default theme: {create_error}")

        try:
            themes = SiteTheme.query.filter_by(is_active=True).all()
        except Exception as e:
            app.logger.error(f"Error querying themes: {e}")
            themes = []

        current_theme = None

        # Get current player's theme if logged in
        player_nickname = session.get('player_nickname')
        if player_nickname:
            try:
                player = Player.query.filter_by(nickname=player_nickname).first()
                if player and player.selected_theme:
                    current_theme = player.selected_theme
            except Exception as e:
                app.logger.error(f"Error getting player theme: {e}")

        # If no current theme, get default
        if not current_theme:
            try:
                current_theme = SiteTheme.query.filter_by(is_default=True).first()
                if not current_theme and themes:
                    current_theme = themes[0]
            except Exception as e:
                app.logger.error(f"Error getting default theme: {e}")

        return render_template('themes.html',
                             themes=themes,
                             current_theme=current_theme)

    except Exception as e:
        app.logger.error(f"Critical error in themes route: {e}")
        flash('Временная проблема с темами. Попробуйте позже.', 'error')
        return redirect(url_for('index'))

@app.route('/select-theme/<int:theme_id>', methods=['POST'])
def select_theme(theme_id):
    """Select a theme for current player"""
    player_nickname = session.get('player_nickname')
    if not player_nickname:
        flash('Необходимо войти в систему для выбора темы!', 'error')
        return redirect(url_for('player_login'))

    try:
        player = Player.query.filter_by(nickname=player_nickname).first_or_404()
        theme = SiteTheme.query.get_or_404(theme_id)

        player.selected_theme_id = theme_id
        db.session.commit()

        # Store theme in session for immediate application
        session['current_theme'] = {
            'id': theme.id,
            'name': theme.name,
            'display_name': theme.display_name,
            'primary_color': theme.primary_color,
            'secondary_color': theme.secondary_color,
            'background_color': theme.background_color,
            'card_background': theme.card_background,
            'text_color': theme.text_color,
            'accent_color': theme.accent_color
        }

        flash(f'Тема "{theme.display_name}" выбрана!', 'success')

    except Exception as e:
        app.logger.error(f"Error selecting theme: {e}")
        flash('Ошибка при выборе темы!', 'error')

    return redirect(url_for('themes'))

@app.route('/player_login', methods=['GET', 'POST'])
def player_login():
    """Player login page"""
    if request.method == 'POST':
        nickname = request.form.get('nickname', '').strip()
        password = request.form.get('password', '').strip()

        if nickname:
            player = Player.query.filter_by(nickname=nickname).first()
            if player:
                if player.has_password:
                    # Player has password, check it
                    if password:
                        import hashlib
                        password_hash = hashlib.sha256(password.encode()).hexdigest()
                        if player.password_hash == password_hash:
                            session['player_nickname'] = nickname
                            flash(f'Добро пожаловать, {nickname}!', 'success')
                            return redirect(url_for('quests'))
                        else:
                            flash('Неверный пароль!', 'error')
                    else:
                        flash('Введите пароль!', 'error')
                else:
                    # First time login, set password
                    if password:
                        import hashlib
                        password_hash = hashlib.sha256(password.encode()).hexdigest()
                        player.password_hash = password_hash
                        player.has_password = True
                        db.session.commit()
                        session['player_nickname'] = nickname
                        flash(f'Пароль установлен! Добро пожаловать, {nickname}!', 'success')
                        return redirect(url_for('quests'))
                    else:
                        flash('Введите пароль для первого входа!', 'error')
            else:
                flash('Игрок с таким ником не найден!', 'error')
        else:
            flash('Введите ваш игровой ник!', 'error')

    return render_template('player_login.html')

@app.route('/role_management')
def role_management():
    """Role and title management page"""
    player_nickname = session.get('player_nickname')
    if not player_nickname:
        flash('Необходимо войти в систему!', 'error')
        return redirect(url_for('player_login'))

    current_player = Player.query.filter_by(nickname=player_nickname).first_or_404()

    # Get available roles and titles
    # The Role and Title classes are no longer used due to the ImportError.
    # These lines are commented out as they reference non-existent models.
    # available_roles = Role.query.order_by(Role.priority.desc()).all()
    # available_titles = Title.query.all()

    # Get player's unlocked titles
    unlocked_titles = PlayerTitle.query.filter_by(player_id=current_player.id).all()

    return render_template('role_management.html',
                         current_player=current_player,
                         # available_roles=available_roles, # Commented out
                         # available_titles=available_titles, # Commented out
                         unlocked_titles=unlocked_titles)

@app.route('/my_profile')
def my_profile():
    """Current player's profile page"""
    player_nickname = session.get('player_nickname')
    if not player_nickname:
        flash('Необходимо войти в систему!', 'error')
        return redirect(url_for('player_login'))

    player = Player.query.filter_by(nickname=player_nickname).first()
    if not player:
        flash('Игрок не найден!', 'error')
        return redirect(url_for('player_login'))

    # Get player's badges safely
    badges_data = []
    try:
        player_badges = PlayerBadge.query.filter_by(player_id=player.id, is_visible=True).all()
        for pb in player_badges:
            badge = Badge.query.get(pb.badge_id)
            if badge and badge.is_active:
                badges_data.append({
                    'badge': badge,
                    'display_name': badge.display_name,
                    'icon': badge.icon,
                    'color': badge.color,
                    'background_color': badge.background_color,
                    'border_color': badge.border_color,
                    'rarity': badge.rarity,
                    'has_gradient': badge.has_gradient,
                    'gradient_start': badge.gradient_start,
                    'gradient_end': badge.gradient_end,
                    'is_animated': badge.is_animated
                })
    except Exception as e:
        app.logger.error(f"Error getting player badges: {e}")

    # Get available custom titles and player's active title safely
    available_titles = []
    player_title = None
    player_titles = []
    try:
        available_titles = CustomTitle.query.all()
        player_title = PlayerTitle.query.filter_by(player_id=player.id, is_active=True).first()
        player_titles = PlayerTitle.query.filter_by(player_id=player.id).all()
    except Exception as e:
        app.logger.error(f"Error getting titles: {e}")

    # Get available admin roles and player's active admin role safely
    available_admin_roles = []
    player_admin_role = None
    try:
        available_admin_roles = AdminCustomRole.query.filter_by(is_active=True).all()
        player_admin_role = PlayerAdminRole.query.filter_by(player_id=player.id, is_active=True).first()
    except Exception as e:
        app.logger.error(f"Error getting admin roles: {e}")

    # Check if player can set a custom role
    can_set_free_custom_role = player.level >= 50 or player.reputation >= 500 # Example conditions

    return render_template('my_profile.html',
                         player=player,
                         is_owner=True,
                         player_badges=badges_data,
                         available_titles=available_titles,
                         player_title=player_title,
                         player_titles=player_titles,
                         available_admin_roles=available_admin_roles,
                         player_admin_role=player_admin_role,
                         can_set_free_custom_role=can_set_free_custom_role)

@app.route('/inventory')
def inventory():
    """Player inventory page"""
    player_nickname = session.get('player_nickname')
    if not player_nickname:
        flash('Необходимо войти в систему для доступа к инвентарю!', 'error')
        return redirect(url_for('player_login'))

    current_player = Player.query.filter_by(nickname=player_nickname).first()
    if not current_player:
        flash('Игрок не найден!', 'error')
        return redirect(url_for('player_login'))

    return render_template('inventory.html', current_player=current_player)

@app.route('/inventory/use/<int:inventory_item_id>', methods=['POST'])
def use_inventory_item(inventory_item_id):
    """Use an item from inventory"""
    player_nickname = session.get('player_nickname')
    if not player_nickname:
        return jsonify({'success': False, 'error': 'Необходимо войти в систему'}), 401

    try:
        from models import InventoryItem
        inventory_item = InventoryItem.query.get_or_404(inventory_item_id)
        player = Player.query.filter_by(nickname=player_nickname).first()

        # Check if item belongs to player
        if inventory_item.player_id != player.id:
            return jsonify({'success': False, 'error': 'Предмет не принадлежит вам'}), 403

        # Use the item
        success, message = inventory_item.use_item()

        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({'success': False, 'error': message}), 400

    except Exception as e:
        app.logger.error(f"Error using inventory item: {e}")
        return jsonify({'success': False, 'error': 'Ошибка при использовании предмета'}), 500

@app.route('/player_logout')
def player_logout():
    """Player logout"""
    player_name = session.get('player_nickname', '')
    session.pop('player_nickname', None)
    flash(f'До свидания, {player_name}!', 'success')
    return redirect(url_for('index'))



@app.route('/targets')
def target_list():
    """Target list page"""
    is_admin = session.get('is_admin', False)
    current_player = None

    # Check if player is logged in
    player_nickname = session.get('player_nickname')
    if player_nickname:
        current_player = Player.query.filter_by(nickname=player_nickname).first()

    # Get targets from database
    try:
        from models import Target
        targets = Target.query.order_by(Target.date_added.desc()).all()
    except Exception as e:
        app.logger.error(f"Error getting targets: {e}")
        targets = []

    return render_template('target_list.html', 
                         targets=targets, 
                         is_admin=is_admin, 
                         current_player=current_player)

@app.route('/set_language/<language>')
def set_language(language):
    """Set user language preference"""
    supported_languages = ['ru', 'ua', 'en']
    if language in supported_languages:
        session['language'] = language
        flash('Язык изменен!', 'success')
    else:
        flash('Неподдерживаемый язык!', 'error')

    # Redirect back to referring page or index
    return redirect(request.referrer or url_for('index'))

@app.route('/add', methods=['POST'])
def add_player():
    """Add a new player to the leaderboard (admin only)"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен! Только администратор может добавлять игроков.', 'error')
        return redirect(url_for('index'))

    try:
        # Basic fields
        nickname = request.form.get('nickname', '').strip()
        gamemode = request.form.get('gamemode', 'bedwars')
        server_ip = request.form.get('server_ip', '').strip()

        # Validation
        if not nickname:
            flash('Ник не может быть пустым!', 'error')
            return redirect(url_for('admin'))

        if len(nickname) > 20:
            flash('Ник не может быть длиннее 20 символов!', 'error')
            return redirect(url_for('admin'))

        # Check if player already exists
        existing_player = Player.query.filter_by(nickname=nickname).first()
        if existing_player:
            # Update existing player with new gamemode stats
            player = existing_player
            flash(f'Обновляем статистику для {nickname}!', 'info')
        else:
            # Create new player
            player = Player(nickname=nickname, server_ip=server_ip)
            db.session.add(player)

        # Handle gamemode-specific stats
        if gamemode == 'bedwars':
            player.kills = request.form.get('kills', type=int, default=0)
            player.final_kills = request.form.get('final_kills', type=int, default=0)
            player.deaths = request.form.get('deaths', type=int, default=0)
            player.final_deaths = request.form.get('final_deaths', type=int, default=0)
            player.beds_broken = request.form.get('beds_broken', type=int, default=0)
            player.games_played = request.form.get('games_played', type=int, default=0)
            player.wins = request.form.get('wins', type=int, default=0)

            # Auto-calculate experience if not provided or if 0
            experience_input = request.form.get('experience', type=int, default=0)
            if experience_input == 0:
                player.experience = player.calculate_auto_experience()
            else:
                player.experience = experience_input

            # Validate bedwars stats
            if player.wins > player.games_played:
                flash('Количество побед не может превышать количество игр!', 'error')
                return redirect(url_for('admin'))

        elif gamemode == 'kitpvp':
            player.kitpvp_kills = request.form.get('kitpvp_kills', type=int, default=0)
            player.kitpvp_deaths = request.form.get('kitpvp_deaths', type=int, default=0)
            player.kitpvp_games = request.form.get('kitpvp_games', type=int, default=0)

        elif gamemode == 'skywars':
            player.skywars_wins = request.form.get('skywars_wins', type=int, default=0)
            player.skywars_solo_wins = request.form.get('skywars_solo_wins', type=int, default=0)
            player.skywars_team_wins = request.form.get('skywars_team_wins', type=int, default=0)
            player.skywars_mega_wins = request.form.get('skywars_mega_wins', type=int, default=0)
            player.skywars_mini_wins = request.form.get('skywars_mini_wins', type=int, default=0)
            player.skywars_ranked_wins = request.form.get('skywars_ranked_wins', type=int, default=0)
            player.skywars_kills = request.form.get('skywars_kills', type=int, default=0)
            player.skywars_solo_kills = request.form.get('skywars_solo_kills', type=int, default=0)
            player.skywars_team_kills = request.form.get('skywars_team_kills', type=int, default=0)
            player.skywars_mega_kills = request.form.get('skywars_mega_kills', type=int, default=0)
            player.skywars_mini_kills = request.form.get('skywars_mini_kills', type=int, default=0)
            player.skywars_ranked_kills = request.form.get('skywars_ranked_kills', type=int, default=0)

        elif gamemode == 'sumo':
            player.sumo_games_played = request.form.get('sumo_games_played', type=int, default=0)
            player.sumo_monthly_games = request.form.get('sumo_monthly_games', type=int, default=0)
            player.sumo_daily_games = request.form.get('sumo_daily_games', type=int, default=0)
            player.sumo_deaths = request.form.get('sumo_deaths', type=int, default=0)
            player.sumo_monthly_deaths = request.form.get('sumo_monthly_deaths', type=int, default=0)
            player.sumo_daily_deaths = request.form.get('sumo_daily_deaths', type=int, default=0)
            player.sumo_wins = request.form.get('sumo_wins', type=int, default=0)
            player.sumo_monthly_wins = request.form.get('sumo_monthly_wins', type=int, default=0)
            player.sumo_daily_wins = request.form.get('sumo_daily_wins', type=int, default=0)
            player.sumo_losses = request.form.get('sumo_losses', type=int, default=0)
            player.sumo_monthly_losses = request.form.get('sumo_monthly_losses', type=int, default=0)
            player.sumo_daily_losses = request.form.get('sumo_daily_losses', type=int, default=0)
            player.sumo_kills = request.form.get('sumo_kills', type=int, default=0)
            player.sumo_monthly_kills = request.form.get('sumo_monthly_kills', type=int, default=0)
            player.sumo_daily_kills = request.form.get('sumo_daily_kills', type=int, default=0)
            player.sumo_winstreak = request.form.get('sumo_winstreak', type=int, default=0)
            player.sumo_monthly_winstreak = request.form.get('sumo_monthly_winstreak', type=int, default=0)
            player.sumo_daily_winstreak = request.form.get('sumo_daily_winstreak', type=int, default=0)
            player.sumo_best_winstreak = request.form.get('sumo_best_winstreak', type=int, default=0)
            player.sumo_monthly_best_winstreak = request.form.get('sumo_monthly_best_winstreak', type=int, default=0)
            player.sumo_daily_best_winstreak = request.form.get('sumo_daily_best_winstreak', type=int, default=0)

        # Handle skin settings
        skin_type = request.form.get('skin_type', 'auto')
        is_premium = request.form.get('is_premium') == 'on'

        player.skin_type = skin_type
        player.is_premium = is_premium

        # Handle role assignment
        role = request.form.get('role', '').strip() or 'Игрок'
        if role == 'custom':
            custom_role = request.form.get('custom_role', '').strip()
            if custom_role:
                player.custom_role = custom_role
                player.custom_role_color = request.form.get('custom_role_color', '#ffc107')
                player.custom_role_gradient = request.form.get('custom_role_gradient', '')
                player.custom_role_emoji = request.form.get('custom_role_emoji', '')
                player.custom_role_animated = request.form.get('custom_role_animated', 'false') == 'true'
                player.custom_role_purchased = True
                role = custom_role
            else:
                role = 'Игрок'

        player.role = role
        player.last_updated = datetime.utcnow()

        db.session.commit()

        # Clear statistics cache
        Player.clear_statistics_cache()

        flash(f'Игрок {nickname} успешно добавлен/обновлен для режима {gamemode.upper()}!', 'success')

    except Exception as e:
        app.logger.error(f"Error adding player: {e}")
        flash('Произошла ошибка при добавлении игрока!', 'error')

    return redirect(url_for('admin'))

@app.route('/edit/<int:player_id>', methods=['POST'])
def edit_player(player_id):
    """Edit player statistics (admin only)"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('index'))

    player = Player.query.get_or_404(player_id)

    try:
        # Update fields
        player.kills = request.form.get('kills', type=int, default=player.kills)
        player.final_kills = request.form.get('final_kills', type=int, default=player.final_kills)
        player.deaths = request.form.get('deaths', type=int, default=player.deaths)
        player.final_deaths = request.form.get('final_deaths', type=int, default=player.final_deaths)
        player.beds_broken = request.form.get('beds_broken', type=int, default=player.beds_broken)
        player.games_played = request.form.get('games_played', type=int, default=player.games_played)
        player.wins = request.form.get('wins', type=int, default=player.wins)
        player.experience = request.form.get('experience', type=int, default=player.experience)
        # Handle role assignment
        role = request.form.get('role', '').strip() or 'Игрок'
        if role == 'custom':
            custom_role = request.form.get('custom_role', '').strip()
            if custom_role:
                role = custom_role
                # Handle custom role styling
                custom_role_color = request.form.get('custom_role_color', '#ffc107')
                custom_role_gradient = request.form.get('custom_role_gradient', '')
                custom_role_emoji = request.form.get('custom_role_emoji', '')
                custom_role_animated = request.form.get('custom_role_animated', 'false') == 'true'

                player.custom_role = custom_role
                player.custom_role_color = custom_role_color
                player.custom_role_gradient = custom_role_gradient
                player.custom_role_emoji = custom_role_emoji
                player.custom_role_animated = custom_role_animated
                player.custom_role_purchased = True
            else:
                role = 'Игрок'

        player.role = role
        player.server_ip = request.form.get('server_ip', default=player.server_ip)

        # Enhanced fields
        player.iron_collected = request.form.get('iron_collected', type=int, default=player.iron_collected)
        player.gold_collected = request.form.get('gold_collected', type=int, default=player.gold_collected)
        player.diamond_collected = request.form.get('diamond_collected', type=int, default=player.diamond_collected)
        player.emerald_collected = request.form.get('emerald_collected', type=int, default=player.emerald_collected)
        player.items_purchased = request.form.get('items_purchased', type=int, default=player.items_purchased)

        # Auto-update experience based on new statistics
        calculated_xp = player.calculate_auto_experience()
        if calculated_xp > player.experience:
            player.experience = calculated_xp

        player.last_updated = datetime.utcnow()
        db.session.commit()

        # Очистка кэша статистики
        Player.clear_statistics_cache()

        # Check for new achievements
        new_achievements = Achievement.check_player_achievements(player)

        success_message = f'Статистика игрока {player.nickname} обновлена!'
        if new_achievements:
            achievement_names = [a.title for a in new_achievements]
            success_message += f' Получены достижения: {", ".join(achievement_names)}'

        flash(success_message, 'success')

    except Exception as e:
        app.logger.error(f"Error editing player: {e}")
        flash('Произошла ошибка при редактировании игрока!', 'error')

    return redirect(url_for('player_profile', player_id=player_id))

@app.route('/modify/<int:player_id>', methods=['POST'])
def modify_player_stats(player_id):
    """Modify player statistics by adding/subtracting values (admin only)"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('index'))

    player = Player.query.get_or_404(player_id)

    try:
        operation = request.form.get('operation', 'add')  # 'add' or 'subtract'
        changes_made = []

        # Define stat fields and their names for logging
        stat_fields = {
            'kills': 'киллы',
            'final_kills': 'финальные киллы',
            'deaths': 'смерти',
            'final_deaths': 'финальные смерти',
            'beds_broken': 'кровати',
            'games_played': 'игры',
            'wins': 'победы',
            'experience': 'опыт',
            'iron_collected': 'железо',
            'gold_collected': 'золото',
            'diamond_collected': 'алмазы',
            'emerald_collected': 'изумруды',
            'items_purchased': 'покупки'
        }

        for field, display_name in stat_fields.items():
            value = request.form.get(field, type=int)
            if value and value != 0:
                current_value = getattr(player, field, 0)

                if operation == 'add':
                    new_value = current_value + value
                    changes_made.append(f"+{value} {display_name}")
                else:  # subtract
                    new_value = max(0, current_value - value)  # Не даем опускаться ниже 0
                    changes_made.append(f"-{value} {display_name}")

                setattr(player, field, new_value)

        if changes_made:
            # Auto-update experience based on new statistics
            calculated_xp = player.calculate_auto_experience()
            if calculated_xp > player.experience:
                player.experience = calculated_xp

            player.last_updated = datetime.utcnow()
            db.session.commit()

            # Очистка кэша статистики
            Player.clear_statistics_cache()

            operation_text = "Добавлено" if operation == 'add' else "Вычтено"
            flash(f'{operation_text} для {player.nickname}: {", ".join(changes_made)}', 'success')
        else:
            flash('Нет изменений для применения!', 'warning')

    except Exception as e:
        app.logger.error(f"Error modifying player stats: {e}")
        flash('Произошла ошибка при изменении статистики!', 'error')

    return redirect(url_for('player_profile', player_id=player_id))

@app.route('/delete/<int:player_id>', methods=['POST'])
def delete_player(player_id):
    """Delete a player (admin only)"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('index'))

    try:
        player = Player.query.get_or_404(player_id)
        nickname = player.nickname
        db.session.delete(player)
        db.session.commit()

        # Очистка кэша статистики
        Player.clear_statistics_cache()

        flash(f'Игрок {nickname} удален из таблицы лидеров!', 'success')
    except Exception as e:
        app.logger.error(f"Error deleting player: {e}")
        flash('Произошла ошибка при удалении игрока!', 'error')

    return redirect(url_for('admin'))

@app.route('/clear', methods=['POST'])
def clear_leaderboard():
    """Clear all players from the leaderboard (admin only)"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен! Только администратор может очистить таблицу.', 'error')
        return redirect(url_for('index'))

    try:
        Player.query.delete()
        db.session.commit()

        # Очистка кэша статистики
        Player.clear_statistics_cache()

        flash('Таблица лидеров очищена!', 'success')
    except Exception as e:
        app.logger.error(f"Error clearing leaderboard: {e}")
        flash('Произошла ошибка при очистке таблицы!', 'error')

    return redirect(url_for('admin'))

@app.route('/export')
def export_leaderboard():
    """Export leaderboard data as CSV"""
    try:
        players = Player.query.order_by(Player.experience.desc()).all()

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            'Ник', 'Уровень', 'Опыт', 'Киллы', 'Финальные киллы', 'Смерти',
            'K/D', 'FK/D', 'Кровати', 'Игры', 'Победы', 'Процент побед',
            'Роль', 'Сервер', 'Железо', 'Золото', 'Алмазы', 'Изумруды',
            'Покупки', 'Дата создания', 'Последнее обновление'
        ])

        # Data
        for player in players:
            writer.writerow([
                player.nickname, player.level, player.experience,
                player.kills, player.final_kills, player.deaths,
                player.kd_ratio, player.fkd_ratio, player.beds_broken,
                player.games_played, player.wins, player.win_rate,
                player.role, player.server_ip, player.iron_collected,
                player.gold_collected, player.diamond_collected,
                player.emerald_collected, player.items_purchased,
                player.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                player.last_updated.strftime('%Y-%m-%d %H:%M:%S')
            ])

        output.seek(0)

        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=bedwars_leaderboard_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

        return response

    except Exception as e:
        app.logger.error(f"Error exporting data: {e}")
        flash('Произошла ошибка при экспорте данных!', 'error')
        return redirect(url_for('index'))

@app.route('/admin/export-db')
def export_database():
    """Export full database as JSON (admin only)"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('login'))

    try:
        import json

        # Export all data
        data = {
            'players': [],
            'quests': [],
            'achievements': [],
            'custom_titles': [],
            'gradient_themes': [],
            'player_quests': [],
            'player_achievements': [],
            'player_titles': [],
            'player_gradient_settings': [],
            'shop_items': []
        }

        # Export players
        for player in Player.query.all():
            player_data = {
                'nickname': player.nickname,
                'kills': player.kills,
                'final_kills': player.final_kills,
                'deaths': player.deaths,
                'beds_broken': player.beds_broken,
                'games_played': player.games_played,
                'wins': player.wins,
                'experience': player.experience,
                'role': player.role,
                'server_ip': player.server_ip,
                'iron_collected': player.iron_collected,
                'gold_collected': player.gold_collected,
                'diamond_collected': player.diamond_collected,
                'emerald_collected': player.emerald_collected,
                'items_purchased': player.items_purchased,
                'skin_url': player.skin_url,
                'skin_type': player.skin_type,
                'is_premium': player.is_premium,
                'real_name': player.real_name,
                'bio': player.bio,
                'discord_tag': player.discord_tag,
                'youtube_channel': player.youtube_channel,
                'twitch_channel': player.twitch_channel,
                'favorite_server': player.favorite_server,
                'favorite_map': player.favorite_map,
                'preferred_gamemode': player.preferred_gamemode,
                'profile_banner_color': player.profile_banner_color,
                'profile_is_public': player.profile_is_public,
                'custom_status': player.custom_status,
                'location': player.location,
                'birthday': player.birthday.isoformat() if player.birthday else None,
                'custom_avatar_url': player.custom_avatar_url,
                'custom_banner_url': player.custom_banner_url,
                'banner_is_animated': player.banner_is_animated,
                'social_networks': player.social_networks,
                'stats_section_color': player.stats_section_color,
                'info_section_color': player.info_section_color,
                'social_section_color': player.social_section_color,
                'prefs_section_color': player.prefs_section_color,
                'password_hash': player.password_hash,
                'has_password': player.has_password,
                'leaderboard_name_color': player.leaderboard_name_color,
                'leaderboard_stats_color': player.leaderboard_stats_color,
                'leaderboard_use_gradient': player.leaderboard_use_gradient,
                'leaderboard_gradient_start': player.leaderboard_gradient_start,
                'leaderboard_gradient_end': player.leaderboard_gradient_end,
                'leaderboard_gradient_animated': player.leaderboard_gradient_animated,
                'created_at': player.created_at.isoformat(),
                'last_updated': player.last_updated.isoformat(),
                'karma': player.karma # Include karma here
            }
            data['players'].append(player_data)

        # Export other tables (simplified)
        for quest in Quest.query.all():
            data['quests'].append({
                'title': quest.title,
                'description': quest.description,
                'type': quest.type,
                'target_value': quest.target_value,
                'reward_xp': quest.reward_xp,
                'reward_title': quest.reward_title,
                'icon': quest.icon,
                'difficulty': quest.difficulty,
                'is_active': quest.is_active
            })

        for achievement in Achievement.query.all():
            data['achievements'].append({
                'title': achievement.title,
                'description': achievement.description,
                'icon': achievement.icon,
                'rarity': achievement.rarity,
                'unlock_condition': achievement.unlock_condition,
                'reward_xp': achievement.reward_xp,
                'reward_title': achievement.reward_title,
                'is_hidden': achievement.is_hidden
            })

        for shop_item in ShopItem.query.all():
            data['shop_items'].append({
                'name': shop_item.name,
                'display_name': shop_item.display_name,
                'description': shop_item.description,
                'category': shop_item.category,
                'price_coins': shop_item.price_coins,
                'price_reputation': shop_item.price_reputation,
                'unlock_level': shop_item.unlock_level,
                'rarity': shop_item.rarity,
                'icon': shop_item.icon,
                'item_data': shop_item.item_data,
                'is_limited_time': shop_item.is_limited_time,
                'is_active': shop_item.is_active
            })

        # Create JSON file
        json_output = json.dumps(data, ensure_ascii=False, indent=2, default=str)

        response = make_response(json_output)
        response.headers['Content-Type'] = 'application/json'
        response.headers['Content-Disposition'] = f'attachment; filename=bedwars_database_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

        return response

    except Exception as e:
        app.logger.error(f"Error exporting database: {e}")
        flash('Произошла ошибка при экспорте базы данных!', 'error')
        return redirect(url_for('admin'))

@app.route('/admin/import-db', methods=['GET', 'POST'])
def import_database():
    """Import database from JSON file (admin only)"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            import json
            from datetime import datetime, date

            if 'database_file' not in request.files:
                flash('Файл не выбран!', 'error')
                return redirect(url_for('import_database'))

            file = request.files['database_file']
            if file.filename == '':
                flash('Файл не выбран!', 'error')
                return redirect(url_for('import_database'))

            if not file.filename.endswith('.json'):
                flash('Неверный формат файла! Требуется JSON.', 'error')
                return redirect(url_for('import_database'))

            # Read and parse JSON
            content = file.read().decode('utf-8')
            data = json.loads(content)

            # Clear existing data (optional - ask user)
            clear_existing = request.form.get('clear_existing') == 'on'
            if clear_existing:
                # Clear all tables
                ShopPurchase.query.delete()
                ShopItem.query.delete()
                PlayerGradientSetting.query.delete()
                PlayerTitle.query.delete()
                PlayerAchievement.query.delete()
                PlayerQuest.query.delete()
                GradientTheme.query.delete()
                CustomTitle.query.delete()
                Achievement.query.delete()
                Quest.query.delete()
                Player.query.delete()
                db.session.commit()

            # Import players
            for player_data in data.get('players', []):
                existing = Player.query.filter_by(nickname=player_data['nickname']).first()
                if not existing:
                    player = Player(
                        nickname=player_data['nickname'],
                        kills=player_data.get('kills', 0),
                        final_kills=player_data.get('final_kills', 0),
                        deaths=player_data.get('deaths', 0),
                        beds_broken=player_data.get('beds_broken', 0),
                        games_played=player_data.get('games_played', 0),
                        wins=player_data.get('wins', 0),
                        experience=player_data.get('experience', 0),
                        role=player_data.get('role', 'Игрок'),
                        server_ip=player_data.get('server_ip', ''),
                        iron_collected=player_data.get('iron_collected', 0),
                        gold_collected=player_data.get('gold_collected', 0),
                        diamond_collected=player_data.get('diamond_collected', 0),
                        emerald_collected=player_data.get('emerald_collected', 0),
                        items_purchased=player_data.get('items_purchased', 0),
                        skin_url=player_data.get('skin_url'),
                        skin_type=player_data.get('skin_type', 'auto'),
                        is_premium=player_data.get('is_premium', False),
                        real_name=player_data.get('real_name'),
                        bio=player_data.get('bio'),
                        discord_tag=player_data.get('discord_tag'),
                        youtube_channel=player_data.get('youtube_channel'),
                        twitch_channel=player_data.get('twitch_channel'),
                        favorite_server=player_data.get('favorite_server'),
                        favorite_map=player_data.get('favorite_map'),
                        preferred_gamemode=player_data.get('preferred_gamemode'),
                        profile_banner_color=player_data.get('profile_banner_color', '#3498db'),
                        profile_is_public=player_data.get('profile_is_public', True),
                        custom_status=player_data.get('custom_status'),
                        location=player_data.get('location'),
                        custom_avatar_url=player_data.get('custom_avatar_url'),
                        custom_banner_url=player_data.get('custom_banner_url'),
                        banner_is_animated=player_data.get('banner_is_animated', False),
                        social_networks=player_data.get('social_networks'),
                        stats_section_color=player_data.get('stats_section_color', '#343a40'),
                        info_section_color=player_data.get('info_section_color', '#343a40'),
                        social_section_color=player_data.get('social_section_color', '#343a40'),
                        prefs_section_color=player_data.get('prefs_section_color', '#343a40'),
                        password_hash=player_data.get('password_hash'),
                        has_password=player_data.get('has_password', False),
                        leaderboard_name_color=player_data.get('leaderboard_name_color', '#ffffff'),
                        leaderboard_stats_color=player_data.get('leaderboard_stats_color', '#ffffff'),
                        leaderboard_use_gradient=player_data.get('leaderboard_use_gradient', False),
                        leaderboard_gradient_start=player_data.get('leaderboard_gradient_start', '#ff6b35'),
                        leaderboard_gradient_end=player_data.get('leaderboard_gradient_end', '#f7931e'),
                        leaderboard_gradient_animated=player_data.get('leaderboard_gradient_animated', False),
                        karma=player_data.get('karma', 0) # Add karma here
                    )

                    # Handle birthday
                    if player_data.get('birthday'):
                        try:
                            player.birthday = datetime.fromisoformat(player_data['birthday']).date()
                        except:
                            pass

                    # Handle timestamps
                    if player_data.get('created_at'):
                        try:
                            player.created_at = datetime.fromisoformat(player_data['created_at'])
                        except:
                            pass

                    if player_data.get('last_updated'):
                        try:
                            player.last_updated = datetime.fromisoformat(player_data['last_updated'])
                        except:
                            pass

                    db.session.add(player)

            # Import quests
            for quest_data in data.get('quests', []):
                existing = Quest.query.filter_by(title=quest_data['title']).first()
                if not existing:
                    quest = Quest(**quest_data)
                    db.session.add(quest)

            # Import achievements
            for achievement_data in data.get('achievements', []):
                existing = Achievement.query.filter_by(title=achievement_data['title']).first()
                if not existing:
                    achievement = Achievement(**achievement_data)
                    db.session.add(achievement)

            # Import shop items
            for item_data in data.get('shop_items', []):
                existing = ShopItem.query.filter_by(name=item_data['name']).first()
                if not existing:
                    shop_item = ShopItem(**item_data)
                    db.session.add(shop_item)


            db.session.commit()
            # Очистка кэша статистики
            Player.clear_statistics_cache()
            flash('База данных успешно импортирована!', 'success')

        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error importing database: {e}")
            flash(f'Ошибка при импорте базы данных: {e}', 'error')

        return redirect(url_for('admin'))

    return render_template('admin_import_db.html')

# Helper function to get current player, used in some routes
def get_current_player():
    """Helper function to get the current logged-in player"""
    player_nickname = session.get('player_nickname')
    if player_nickname:
        return Player.query.filter_by(nickname=player_nickname).first()
    return None



@app.route('/admin/edit_badge/<int:badge_id>')
def edit_badge(badge_id):
    """Edit badge page (admin only)"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('login'))

    from models import Badge
    badge = Badge.query.get_or_404(badge_id)
    return render_template('admin_edit_badge.html', badge=badge)

@app.route('/admin/update_badge/<int:badge_id>', methods=['POST'])
def update_badge(badge_id):
    """Update badge (admin only)"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('login'))

    try:
        from models import Badge
        import os
        import uuid

        badge = Badge.query.get_or_404(badge_id)

        # Update basic fields
        badge.display_name = request.form.get('display_name', badge.display_name).strip()
        badge.description = request.form.get('description', badge.description)
        badge.icon = request.form.get('icon', badge.icon)
        badge.color = request.form.get('color', badge.color)
        badge.background_color = request.form.get('background_color', badge.background_color)
        badge.border_color = request.form.get('border_color', badge.border_color)
        badge.rarity = request.form.get('rarity', badge.rarity)
        badge.has_gradient = request.form.get('has_gradient') == 'on'
        badge.gradient_start = request.form.get('gradient_start', '') if badge.has_gradient else None
        badge.gradient_end = request.form.get('gradient_end', '') if badge.has_gradient else None
        badge.is_animated = request.form.get('is_animated') == 'on'

        # Handle emoji updates
        emoji = request.form.get('emoji', '').strip()
        emoji_url = request.form.get('emoji_url', '').strip()

        # Handle file upload
        if 'emoji_file' in request.files:
            file = request.files['emoji_file']
            if file and file.filename:
                # Validate and save new file
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'avif'}
                if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                    if len(file.read()) <= 256 * 1024:
                        file.seek(0)

                        # Delete old file if exists
                        if badge.emoji_url and badge.emoji_url.startswith('/static/emojis/'):
                            old_file_path = os.path.join(app.static_folder, badge.emoji_url[1:])
                            if os.path.exists(old_file_path):
                                os.remove(old_file_path)

                        # Save new file
                        file_extension = file.filename.rsplit('.', 1)[1].lower()
                        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
                        emoji_dir = os.path.join(app.static_folder, 'emojis')
                        os.makedirs(emoji_dir, exist_ok=True)
                        file_path = os.path.join(emoji_dir, unique_filename)
                        file.save(file_path)

                        badge.emoji_url = f"/static/emojis/{unique_filename}"
                        badge.emoji = None  # Clear text emoji when file is uploaded
                    else:
                        flash('Файл слишком большой! Максимум 256KB', 'error')
                        return redirect(url_for('edit_badge', badge_id=badge_id))
        elif emoji_url:
            # Use URL emoji
            badge.emoji_url = emoji_url
            badge.emoji = None
        elif emoji:
            # Use text emoji
            badge.emoji = emoji
            badge.emoji_url = None

        db.session.commit()
        flash(f'Бейдж "{badge.display_name}" успешно обновлен!', 'success')

    except Exception as e:
        app.logger.error(f"Error updating badge: {e}")
        flash('Ошибка при обновлении бейджа!', 'error')

    return redirect(url_for('admin_badges'))

@app.route('/admin/players')
def admin_players():
    """Admin player management page"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('login'))

    # Get all players with search functionality
    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort', 'created_at')
    page = max(1, int(request.args.get('page', 1)))
    limit = 25

    query = Player.query

    if search:
        query = query.filter(Player.nickname.ilike(f'%{search}%'))

    if sort_by == 'nickname':
        query = query.order_by(Player.nickname.asc())
    elif sort_by == 'level':
        query = query.order_by(Player.experience.desc())
    elif sort_by == 'karma':
        query = query.order_by(Player.karma.desc())
    else:
        query = query.order_by(Player.created_at.desc())

    players = query.paginate(page=page, per_page=limit, error_out=False)

    stats = Player.get_statistics()

    return render_template('admin_players.html',
                         players=players,
                         search_query=search,
                         current_sort=sort_by,
                         stats=stats)

@app.route('/admin/modify-stats', methods=['POST'])
def admin_modify_stats():
    """Modify player statistics (admin only)"""
    if not get_current_player() and not session.get('is_admin', False): # Check for player login or admin status
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('index'))

    try:
        player_nickname = request.form.get('player_nickname')
        stat_type = request.form.get('stat_type')
        operation = request.form.get('operation')
        value = int(request.form.get('value', 0))

        if not all([player_nickname, stat_type, operation]): # Value can be 0, so don't check it directly here
            flash('Все поля должны быть заполнены!', 'error')
            return redirect(url_for('admin_players'))

        player = Player.query.filter_by(nickname=player_nickname).first()
        if not player:
            flash(f'Игрок {player_nickname} не найден!', 'error')
            return redirect(url_for('admin_players'))

        # Get current value
        current_value = getattr(player, stat_type, 0)

        # Calculate new value
        if operation == 'add':
            new_value = current_value + value
        elif operation == 'subtract':
            new_value = max(0, current_value - value)  # Don't go below 0
        elif operation == 'set':
            new_value = value
        else:
            flash('Неизвестная операция!', 'error')
            return redirect(url_for('admin_players'))

        # Update the value
        setattr(player, stat_type, new_value)

        db.session.commit()

        # Log the change
        app.logger.info(f"Admin modified {player_nickname} {stat_type}: {current_value} -> {new_value} (operation: {operation}, value: {value})")

        flash(f'Статистика игрока {player_nickname} обновлена! {stat_type}: {current_value} -> {new_value}', 'success')

    except ValueError:
        flash('Некорректное значение!', 'error')
    except AttributeError:
        flash('Недопустимый тип статистики!', 'error')
    except Exception as e:
        app.logger.error(f"Error modifying player stats: {e}")
        flash('Ошибка при изменении статистики!', 'error')
        db.session.rollback()

    return redirect(url_for('admin_players'))

# Quest system routes
@app.route('/quests')
def quests():
    """Display quest system with categories"""
    player_nickname = session.get('player_nickname')
    current_player = None
    player_progress = {}

    if player_nickname:
        current_player = Player.query.filter_by(nickname=player_nickname).first()
        if current_player:
            # Get player quest progress
            player_quests = PlayerQuest.query.filter_by(player_id=current_player.id).all()
            for pq in player_quests:
                player_progress[pq.quest_id] = pq

    # Refresh timed quests
    try:
        Quest.refresh_timed_quests()
    except Exception as e:
        app.logger.error(f"Error refreshing timed quests: {e}")

    all_quests = Quest.get_active_quests()

    # Categorize quests
    daily_quests = [q for q in all_quests if q.quest_category == 'daily']
    weekly_quests = [q for q in all_quests if q.quest_category == 'weekly']
    monthly_quests = [q for q in all_quests if q.quest_category == 'monthly']
    permanent_quests = [q for q in all_quests if q.quest_category == 'permanent']
    seasonal_quests = [q for q in all_quests if q.quest_category in ['thematic', 'seasonal']]

    is_admin = session.get('is_admin', False)

    return render_template('quests.html',
                         quests=all_quests,
                         daily_quests=daily_quests,
                         weekly_quests=weekly_quests,
                         monthly_quests=monthly_quests,
                         permanent_quests=permanent_quests,
                         seasonal_quests=seasonal_quests,
                         player_progress=player_progress,
                         current_player=current_player,
                         is_admin=is_admin)

@app.route('/achievements')
def achievements():
    """Display achievements page"""
    is_admin = session.get('is_admin', False)
    current_player = None

    # Check if player is logged in
    player_nickname = session.get('player_nickname')
    if player_nickname:
        current_player = Player.query.filter_by(nickname=player_nickname).first()

    # Initialize default achievements if none exist
    if Achievement.query.count() == 0:
        Achievement.create_default_achievements()

    all_achievements = Achievement.query.all()

    # Get player achievements if logged in
    player_achievements = []

    if current_player:
        player_achievements = PlayerAchievement.query.filter_by(
            player_id=current_player.id
        ).all()

    # Add earned count for display
    for achievement in all_achievements:
        achievement.earned_count = PlayerAchievement.query.filter_by(achievement_id=achievement.id).count()

    return render_template('achievements.html',
                         achievements=all_achievements,
                         player_achievements=player_achievements,
                         current_player=current_player,
                         is_admin=is_admin)

@app.route('/quest/<int:quest_id>/accept', methods=['POST'])
def accept_quest(quest_id):
    """Accept a quest (player must be logged in)"""
    player_nickname = session.get('player_nickname')
    if not player_nickname:
        flash('Необходимо войти в систему для принятия квестов!', 'error')
        return redirect(url_for('player_login'))

    try:
        player = Player.query.filter_by(nickname=player_nickname).first_or_404()
        quest = Quest.query.get_or_404(quest_id)

        # Check if quest already accepted
        existing_quest = PlayerQuest.query.filter_by(
            player_id=player.id,
            quest_id=quest_id
        ).first()

        if existing_quest and existing_quest.is_accepted:
            flash('Квест уже принят!', 'warning')
            return redirect(url_for('quests'))

        if not existing_quest:
            existing_quest = PlayerQuest()
            existing_quest.player_id = player.id
            existing_quest.quest_id = quest_id
            db.session.add(existing_quest)

        # Accept the quest and set baseline
        existing_quest.is_accepted = True
        existing_quest.accepted_at = datetime.utcnow()
        existing_quest.started_at = datetime.utcnow()

        # Set baseline value for quest tracking
        quest = Quest.query.get_or_404(quest_id)
        existing_quest.baseline_value = getattr(player, quest.type, 0)

        db.session.commit()
        flash(f'Квест "{quest.title}" принят!', 'success')

    except Exception as e:
        app.logger.error(f"Error accepting quest: {e}")
        flash('Ошибка при принятии квеста!', 'error')

    return redirect(url_for('quests'))

@app.route('/quest/<int:quest_id>/complete', methods=['POST'])
def complete_quest(quest_id):
    """Mark a quest as completed (admin only for demo)"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('quests'))

    try:
        quest = Quest.query.get_or_404(quest_id)
        sample_player = Player.query.first()

        if not sample_player:
            flash('Нет игроков для демонстрации!', 'error')
            return redirect(url_for('quests'))

        # Get or create player quest
        player_quest = PlayerQuest.query.filter_by(
            player_id=sample_player.id,
            quest_id=quest_id
        ).first()

        if not player_quest:
            player_quest = PlayerQuest()
            player_quest.player_id = sample_player.id
            player_quest.quest_id = quest_id
            player_quest.is_accepted = True
            player_quest.accepted_at = datetime.utcnow()
            player_quest.baseline_value = getattr(sample_player, quest.type, 0)
            db.session.add(player_quest)

        # Complete the quest only if not already completed
        if not player_quest.is_completed:
            player_quest.is_completed = True
            player_quest.completed_at = datetime.utcnow()
            player_quest.current_progress = quest.target_value

            # Award all rewards
            sample_player.experience += quest.reward_xp
            sample_player.coins += quest.reward_coins
            sample_player.reputation += quest.reward_reputation
            sample_player.karma += quest.reward_karma

            db.session.commit()

            # Очистка кэша статистики
            Player.clear_statistics_cache()

            rewards = []
            if quest.reward_xp > 0:
                rewards.append(f"{quest.reward_xp} XP")
            if quest.reward_coins > 0:
                rewards.append(f"{quest.reward_coins} койнов")
            if quest.reward_reputation > 0:
                rewards.append(f"{quest.reward_reputation} репутации")

            reward_text = ", ".join(rewards) if rewards else "награды"
            flash(f'Квест "{quest.title}" выполнен! Получено: {reward_text}!', 'success')
        else:
            flash('Квест уже выполнен! Награда не начислена повторно.', 'warning')

    except Exception as e:
        app.logger.error(f"Error completing quest: {e}")
        flash('Ошибка при выполнении квеста!', 'error')

    return redirect(url_for('quests'))

@app.route('/admin/quests')
def admin_quests():
    """Admin quest management"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('login'))

    quests = Quest.query.order_by(Quest.created_at.desc()).all()
    quest_stats = []

    for quest in quests:
        total_attempts = PlayerQuest.query.filter_by(quest_id=quest.id).count()
        completed = PlayerQuest.query.filter_by(quest_id=quest.id, is_completed=True).count()
        completion_rate = (completed / total_attempts * 100) if total_attempts > 0 else 0

        quest_stats.append({
            'quest': quest,
            'total_attempts': total_attempts,
            'completed': completed,
            'completion_rate': completion_rate
        })

    return render_template('admin_quests.html', quest_stats=quest_stats)

@app.route('/init_demo', methods=['POST'])
def init_demo():
    """Initialize demo data (admin only)"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('login'))

    try:
        # Force recreate achievements to ensure mythic ones exist
        Achievement.create_default_achievements()

        # Create demo players if they don't exist
        demo_players = [
            {
                'nickname': 'ProGamer2024',
                'kills': 150,
                'final_kills': 45,
                'deaths': 75,
                'beds_broken': 28,
                'games_played': 85,
                'wins': 52,
                'experience': 8500,
                'role': 'Опытный игрок',
                'iron_collected': 5000,
                'gold_collected': 2500,
                'diamond_collected': 800,
                'emerald_collected': 150,
                'items_purchased': 500
            },
            {
                'nickname': 'BedDestroyer',
                'kills': 89,
                'final_kills': 22,
                'deaths': 45,
                'beds_broken': 65,
                'games_played': 72,
                'wins': 38,
                'experience': 5200,
                'role': 'Разрушитель',
                'iron_collected': 3200,
                'gold_collected': 1800,
                'diamond_collected': 450,
                'emerald_collected': 85,
                'items_purchased': 320
            },
            {
                'nickname': 'NewbieFighter',
                'kills': 25,
                'final_kills': 8,
                'deaths': 32,
                'beds_broken': 12,
                'games_played': 35,
                'wins': 15,
                'experience': 1800,
                'role': 'Новичок',
                'iron_collected': 1200,
                'gold_collected': 600,
                'diamond_collected': 120,
                'emerald_collected': 25,
                'items_purchased': 150
            }
        ]

        for player_data in demo_players:
            existing = Player.query.filter_by(nickname=player_data['nickname']).first()
            if not existing:
                Player.add_player(**player_data)

        # Initialize quests and achievements
        Quest.create_default_quests()
        Achievement.create_default_achievements()
        CustomTitle.create_default_titles()
        GradientTheme.create_default_themes()
        ShopItem.create_default_items() # Initialize default shop items

        # Initialize achievement tracking for existing players
        players = Player.query.all()
        for player in players:
            Achievement.initialize_player_achievement_tracking(player)

        # Initialize game modes for ASCEND system
        from models import GameMode
        if GameMode.query.count() == 0:
            GameMode.create_default_modes()

        # Update quest progress for all players
        for player in players:
            PlayerQuest.update_player_quest_progress(player)

        # Очистка кэша статистики
        Player.clear_statistics_cache()

        flash('Демо-данные успешно инициализированы!', 'success')

    except Exception as e:
        app.logger.error(f"Error initializing demo data: {e}")
        flash('Ошибка при инициализации демо-данных!', 'error')

    return redirect(url_for('admin'))

@app.route('/admin/update_skin/<int:player_id>', methods=['POST'])
def update_player_skin(player_id):
    """Update player skin settings (admin only)"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('login'))

    player = Player.query.get_or_404(player_id)

    try:
        skin_type = request.form.get('skin_type', 'auto')
        namemc_url = request.form.get('namemc_url', '').strip()
        is_premium = request.form.get('is_premium') == 'on'

        player.is_premium = is_premium

        if skin_type == 'custom' and namemc_url:
            if player.set_custom_skin(namemc_url):
                flash(f'Кастомный скин установлен для {player.nickname}!', 'success')
            else:
                flash('Ошибка при установке кастомного скина!', 'error')
        else:
            player.skin_type = skin_type
            player.skin_url = None
            flash(f'Тип скина изменен на {skin_type} для {player.nickname}!', 'success')

        db.session.commit()

    except Exception as e:
        app.logger.error(f"Error updating player skin: {e}")
        flash('Ошибка при обновлении скина!', 'error')

    return redirect(url_for('player_profile', player_id=player_id))

@app.route('/admin/create_quest', methods=['POST'])
def create_quest():
    """Create custom quest (admin only)"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('login'))

    try:
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        target_value = request.form.get('target_value', '0')
        reward_experience = request.form.get('reward_experience', '0')

        quest_data = {
            'title': title,
            'description': description,
            'type': request.form.get('quest_type'),
            'difficulty': request.form.get('difficulty'),
            'target_value': int(target_value) if target_value.isdigit() else 0,
            'reward_xp': int(reward_experience) if reward_experience.isdigit() else 0,
            'reward_title': request.form.get('reward_title', '').strip() or None
        }

        quest = Quest(**quest_data)
        db.session.add(quest)
        db.session.commit()

        flash(f'Квест "{quest_data["title"]}" успешно создан!', 'success')

    except Exception as e:
        app.logger.error(f"Error creating quest: {e}")
        flash('Ошибка при создании квеста!', 'error')

    return redirect(url_for('admin_quests'))

@app.route('/admin/delete_quest/<int:quest_id>', methods=['DELETE'])
def delete_quest(quest_id):
    """Delete quest (admin only)"""
    if not session.get('is_admin', False):
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        quest = Quest.query.get_or_404(quest_id)
        # Delete related player quests first
        PlayerQuest.query.filter_by(quest_id=quest_id).delete()
        db.session.delete(quest)
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        app.logger.error(f"Error deleting quest: {e}")
        return jsonify({'error': 'Failed to delete quest'}), 500

@app.route('/admin/reset_quest/<int:quest_id>', methods=['POST'])
def reset_quest_progress(quest_id):
    """Reset quest progress for all players (admin only)"""
    if not session.get('is_admin', False):
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        PlayerQuest.query.filter_by(quest_id=quest_id).delete()
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        app.logger.error(f"Error resetting quest progress: {e}")
        return jsonify({'error': 'Failed to reset quest progress'}), 500




@app.route('/admin/assign_title', methods=['POST'])
def assign_title():
    """Assign title to player (admin only)"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('login'))

    try:
        player_id = request.form.get('player_id', type=int)
        title_id = request.form.get('title_id', type=int)

        if not player_id or not title_id:
            flash('Выберите игрока и титул!', 'error')
            return redirect(url_for('admin_titles')) # Assuming admin_titles is intended here

        player = Player.query.get_or_404(player_id)
        title = CustomTitle.query.get_or_404(title_id)

        # Remove any existing active title
        PlayerTitle.query.filter_by(player_id=player_id, is_active=True).update({'is_active': False})

        # Add new title
        player_title = PlayerTitle(
            player_id=player_id,
            title_id=title_id,
            is_active=True
        )

        db.session.add(player_title)
        db.session.commit()

        flash(f'Титул "{title.display_name}" присвоен игроку {player.nickname}!', 'success')

    except Exception as e:
        app.logger.error(f"Error assigning title: {e}")
        flash('Ошибка при присвоении титула!', 'error')

    return redirect(url_for('admin_titles')) # Assuming admin_titles is intended here

@app.route('/admin/remove_title/<int:player_id>', methods=['POST'])
def remove_title(player_id):
    """Remove title from player (admin only)"""
    if not session.get('is_admin', False):
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        PlayerTitle.query.filter_by(player_id=player_id, is_active=True).update({'is_active': False})
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        app.logger.error(f"Error removing title: {e}")
        return jsonify({'error': 'Failed to remove title'}), 500

@app.route('/admin/remove_all_titles', methods=['POST'])
def remove_all_titles():
    """Remove all custom titles from all players (admin only)"""
    if not session.get('is_admin', False):
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        PlayerTitle.query.update({'is_active': False})
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        app.logger.error(f"Error removing all titles: {e}")
        return jsonify({'error': 'Failed to remove all titles'}), 500


@app.route('/admin/themes')
def admin_themes():
    """Admin themes management"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('login'))

    # Initialize default themes if none exist
    if SiteTheme.query.count() == 0:
        SiteTheme.create_default_themes()

    themes = SiteTheme.query.all()
    return render_template('admin_themes.html', themes=themes)

@app.route('/admin/create_theme', methods=['POST'])
def admin_create_theme():
    """Create new theme (admin only)"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('login'))

    try:
        name = request.form.get('name', '').strip()
        display_name = request.form.get('display_name', '').strip()
        primary_color = request.form.get('primary_color', '#ffc107')
        secondary_color = request.form.get('secondary_color', '#17a2b8')
        background_color = request.form.get('background_color', '#121212')
        card_background = request.form.get('card_background', '#1e1e1e')
        text_color = request.form.get('text_color', '#ffffff')
        accent_color = request.form.get('accent_color', '#28a745')
        is_default = request.form.get('is_default') == 'on'

        if not name or not display_name:
            flash('Название и отображаемое имя обязательны!', 'error')
            return redirect(url_for('admin_themes'))

        # Check if theme already exists
        existing = SiteTheme.query.filter_by(name=name).first()
        if existing:
            flash('Тема с таким названием уже существует!', 'error')
            return redirect(url_for('admin_themes'))

        # If making this default, remove default from others
        if is_default:
            SiteTheme.query.update({'is_default': False})

        theme = SiteTheme(
            name=name,
            display_name=display_name,
            primary_color=primary_color,
            secondary_color=secondary_color,
            background_color=background_color,
            card_background=card_background,
            text_color=text_color,
            accent_color=accent_color,
            is_default=is_default
        )

        db.session.add(theme)
        db.session.commit()

        flash(f'Тема "{display_name}" успешно создана!', 'success')

    except Exception as e:
        app.logger.error(f"Error creating theme: {e}")
        flash('Ошибка при создании темы!', 'error')

    return redirect(url_for('admin_themes'))

@app.route('/admin/delete_theme/<int:theme_id>', methods=['DELETE'])
def admin_delete_theme(theme_id):
    """Delete theme (admin only)"""
    if not session.get('is_admin', False):
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        theme = SiteTheme.query.get_or_404(theme_id)

        if theme.is_default:
            return jsonify({'error': 'Нельзя удалить тему по умолчанию!'}), 400

        db.session.delete(theme)
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        app.logger.error(f"Error deleting theme: {e}")
        return jsonify({'error': 'Failed to delete theme'}), 500



@app.route('/shop')
def shop():
    """Shop page for purchasing items"""
    is_admin = session.get('is_admin', False)
    current_player = None

    # Check if player is logged in
    player_nickname = session.get('player_nickname')
    if player_nickname:
        current_player = Player.query.filter_by(nickname=player_nickname).first()

    # Initialize default shop items if none exist
    if ShopItem.query.count() == 0:
        ShopItem.create_default_items()

    # Get all active shop items grouped by category (excluding themes - they're free)
    categories = {
        'title': ShopItem.query.filter_by(category='title', is_active=True).all(),
        'booster': ShopItem.query.filter_by(category='booster', is_active=True).all(),
        'custom_role': ShopItem.query.filter_by(category='custom_role', is_active=True).all(),
        'emoji_slot': ShopItem.query.filter_by(category='emoji_slot', is_active=True).all(),
        'gradient': ShopItem.query.filter_by(category='gradient', is_active=True).all()
    }

    # Check purchase status and availability for each item
    shop_data = {}
    for category, items in categories.items():
        shop_data[category] = []
        for item in items:
            item_data = {
                'item': item,
                'can_purchase': True,
                'purchase_error': None,
                'already_purchased': False
            }

            if current_player:
                can_purchase, error_msg = item.can_purchase(current_player)
                item_data['can_purchase'] = can_purchase
                item_data['purchase_error'] = error_msg

                # Check if already purchased
                existing_purchase = ShopPurchase.query.filter_by(
                    player_id=current_player.id,
                    item_id=item.id
                ).first()
                item_data['already_purchased'] = bool(existing_purchase)
            else:
                item_data['can_purchase'] = False
                item_data['purchase_error'] = "Требуется авторизация"

            shop_data[category].append(item_data)

    return render_template('shop.html',
                         shop_data=shop_data,
                         current_player=current_player,
                         is_admin=is_admin)

@app.route('/shop/purchase', methods=['POST'])
def purchase_item():
    """Purchase an item from the shop"""
    player_nickname = session.get('player_nickname')
    if not player_nickname:
        return jsonify({'success': False, 'error': 'Необходимо войти в систему'}), 401

    try:
        data = request.get_json()
        item_id = data.get('item_id')

        if not item_id:
            return jsonify({'success': False, 'error': 'Не указан ID товара'}), 400

        player = Player.query.filter_by(nickname=player_nickname).first()
        if not player:
            return jsonify({'success': False, 'error': 'Игрок не найден'}), 404

        item = ShopItem.query.get(item_id)
        if not item or not item.is_active:
            return jsonify({'success': False, 'error': 'Товар не найден или недоступен'}), 404

        # Check if can purchase
        can_purchase, error_msg = item.can_purchase(player)
        if not can_purchase:
            return jsonify({'success': False, 'error': error_msg}), 400

        # Deduct currency
        player.coins -= item.price_coins
        player.reputation -= item.price_reputation

        # Create purchase record
        purchase = ShopPurchase(
            player_id=player.id,
            item_id=item.id,
            price_paid_coins=item.price_coins,
            price_paid_reputation=item.price_reputation
        )
        db.session.add(purchase)

        # Add item to inventory
        from models import InventoryItem
        inventory_item = InventoryItem(
            player_id=player.id,
            item_id=item.id,
            status='unused',
            quantity=1
        )
        db.session.add(inventory_item)

        # For immediate effect items (boosters), use them right away
        if item.category == 'booster':
            success, message = item.apply_item_effect(player)
            if success:
                inventory_item.status = 'used'
                inventory_item.used_at = datetime.utcnow()

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Товар "{item.display_name}" куплен и добавлен в инвентарь!',
            'new_coins': player.coins,
            'new_reputation': player.reputation
        })

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Purchase error: {e}")
        return jsonify({'success': False, 'error': 'Произошла ошибка при покупке'}), 500

@app.route('/admin/shop')
def admin_shop():
    """Shop management page for admins"""
    if not session.get('is_admin', False):
        flash('У вас нет доступа к этой функции!', 'error')
        return redirect(url_for('index'))

    shop_items = ShopItem.query.order_by(ShopItem.category, ShopItem.name).all()

    # Преобразуем объекты в словари для JSON сериализации
    shop_items_data = []
    for item in shop_items:
        shop_items_data.append({
            'id': item.id,
            'name': item.name,
            'display_name': item.display_name,
            'description': item.description,
            'category': item.category,
            'price_coins': item.price_coins,
            'price_reputation': item.price_reputation,
            'unlock_level': item.unlock_level,
            'rarity': item.rarity,
            'icon': item.icon,
            'image_url': item.image_url,
            'item_data': item.item_data,
            'is_limited_time': item.is_limited_time,
            'is_active': item.is_active
        })

    return render_template('admin_shop.html', shop_items=shop_items, shop_items_data=shop_items_data)

@app.route('/admin/add_shop_item', methods=['POST'])
def admin_add_shop_item():
    """Add new shop item (admin only)"""
    if not session.get('is_admin', False):
        flash('У вас нет доступа к этой функции!', 'error')
        return redirect(url_for('index'))

    try:
        name = request.form.get('name', '').strip()
        display_name = request.form.get('display_name', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        price_coins = int(request.form.get('price_coins', 0))
        price_reputation = int(request.form.get('price_reputation', 0))
        unlock_level = int(request.form.get('unlock_level', 1))
        rarity = request.form.get('rarity', 'common')
        icon = request.form.get('icon', 'fas fa-star')
        item_data = request.form.get('item_data', '').strip()
        is_limited_time = request.form.get('is_limited_time') == 'on'
        duration = int(request.form.get('duration', 0)) # Duration for boosters

        if not name or not display_name or not description or not category:
            flash('Все обязательные поля должны быть заполнены!', 'error')
            return redirect(url_for('admin_shop'))

        # Check if item already exists
        existing = ShopItem.query.filter_by(name=name).first()
        if existing:
            flash('Товар с таким названием уже существует!', 'error')
            return redirect(url_for('admin_shop'))

        # Validate JSON data
        if item_data:
            try:
                import json
                json.loads(item_data)
            except json.JSONDecodeError:
                flash('Некорректный JSON в данных товара!', 'error')
                return redirect(url_for('admin_shop'))

        shop_item = ShopItem(
            name=name,
            display_name=display_name,
            description=description,
            category=category,
            price_coins=price_coins,
            price_reputation=price_reputation,
            unlock_level=unlock_level,
            rarity=rarity,
            icon=icon,
            image_url=request.form.get('image_url', '').strip() or None,
            item_data=item_data,
            is_limited_time=is_limited_time,
            duration=duration if duration > 0 else None # Store duration only if valid
        )

        db.session.add(shop_item)
        db.session.commit()

        flash(f'Товар "{display_name}" успешно добавлен!', 'success')

    except Exception as e:
        app.logger.error(f"Error adding shop item: {e}")
        flash('Ошибка при добавлении товара!', 'error')

    return redirect(url_for('admin_shop'))

@app.route('/admin/toggle_shop_item/<int:item_id>', methods=['POST'])
def admin_toggle_shop_item(item_id):
    """Toggle shop item active status (admin only)"""
    if not session.get('is_admin', False):
        flash('У вас нет доступа к этой функции!', 'error')
        return redirect(url_for('index'))

    try:
        item = ShopItem.query.get_or_404(item_id)
        item.is_active = not item.is_active
        db.session.commit()

        status = "активирован" if item.is_active else "деактивирован"
        flash(f'Товар "{item.display_name}" {status}!', 'success')

    except Exception as e:
        app.logger.error(f"Error toggling shop item: {e}")
        flash('Ошибка при изменении статуса товара!', 'error')

    return redirect(url_for('admin_shop'))

@app.route('/admin/edit_shop_item/<int:item_id>', methods=['POST'])
def admin_edit_shop_item(item_id):
    """Edit shop item (admin only)"""
    if not session.get('is_admin', False):
        flash('У вас нет доступа к этой функции!', 'error')
        return redirect(url_for('index'))

    try:
        item = ShopItem.query.get_or_404(item_id)

        # Validate required fields
        name = request.form.get('name', '').strip()
        display_name = request.form.get('display_name', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()

        if not name or not display_name or not description or not category:
            flash('Все обязательные поля должны быть заполнены!', 'error')
            return redirect(url_for('admin_shop'))

        # Check if name is unique (excluding current item)
        existing = ShopItem.query.filter(ShopItem.name == name, ShopItem.id != item_id).first()
        if existing:
            flash('Товар с таким системным названием уже существует!', 'error')
            return redirect(url_for('admin_shop'))

        # Update item fields
        item.name = name
        item.display_name = display_name
        item.description = description
        item.category = category
        item.price_coins = int(request.form.get('price_coins', 0))
        item.price_reputation = int(request.form.get('price_reputation', 0))
        item.unlock_level = int(request.form.get('unlock_level', 1))
        item.rarity = request.form.get('rarity', 'common')
        item.icon = request.form.get('icon', 'fas fa-star')
        item.image_url = request.form.get('image_url', '').strip() or None
        item.item_data = request.form.get('item_data', '').strip() or None
        item.is_limited_time = request.form.get('is_limited_time') == 'on'
        item.duration = int(request.form.get('duration', 0)) or None # Duration for boosters

        # Validate JSON data if provided
        if item.item_data:
            try:
                import json
                json.loads(item.item_data)
            except json.JSONDecodeError:
                flash('Некорректный JSON в данных товара!', 'error')
                return redirect(url_for('admin_shop'))

        db.session.commit()
        flash(f'Товар "{display_name}" успешно обновлен!', 'success')

    except Exception as e:
        app.logger.error(f"Error editing shop item: {e}")
        flash('Ошибка при редактировании товара!', 'error')

    return redirect(url_for('admin_shop'))

@app.route('/admin/delete_shop_item/<int:item_id>', methods=['POST'])
def admin_delete_shop_item(item_id):
    """Delete shop item (admin only)"""
    if not session.get('is_admin', False):
        flash('У вас нет доступа к этой функции!', 'error')
        return redirect(url_for('index'))

    try:
        item = ShopItem.query.get_or_404(item_id)
        name = item.display_name

        # Delete related purchases first
        ShopPurchase.query.filter_by(item_id=item_id).delete()

        db.session.delete(item)
        db.session.commit()

        flash(f'Товар "{name}" удален!', 'success')

    except Exception as e:
        app.logger.error(f"Error deleting shop item: {e}")
        flash('Ошибка при удалении товара!', 'error')

    return redirect(url_for('admin_shop'))




@app.route('/admin/update_reputation', methods=['POST'])
def admin_update_reputation():
    """Update player reputation (admin only)"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('login'))

    try:
        target_player = request.form.get('target_player', '').strip()
        reputation_change = int(request.form.get('reputation_change', '0'))
        reason = request.form.get('reason', '').strip()

        if not target_player or reputation_change == 0:
            flash('Укажите никнейм игрока и измените значение репутации!', 'error')
            return redirect(url_for('admin_reputation'))

        player = Player.query.filter_by(nickname=target_player).first()
        if not player:
            flash('Игрок не найден!', 'error')
            return redirect(url_for('admin_reputation'))

        # Update reputation
        old_reputation = player.reputation
        player.reputation = max(0, player.reputation + reputation_change)

        # Log the change
        from models import ReputationLog
        log_entry = ReputationLog(
            player_id=player.id,
            change_amount=reputation_change,
            reason=reason or f"Изменение администратором",
            given_by='admin'
        )
        db.session.add(log_entry)

        db.session.commit()

        # Очистка кэша статистики
        Player.clear_statistics_cache()

        action = "Добавлено" if reputation_change > 0 else "Убрано"
        flash(f'{action} {abs(reputation_change)} репутации игроку {player.nickname}. Было: {old_reputation}, стало: {player.reputation}', 'success')

    except Exception as e:
        app.logger.error(f"Error updating reputation: {e}")
        flash('Ошибка при изменении репутации!', 'error')

    return redirect(url_for('admin_reputation'))



@app.route('/reputation-guide')
def reputation_guide():
    """Reputation earning guide"""
    current_player = None
    player_nickname = session.get('player_nickname')
    if player_nickname:
        current_player = Player.query.filter_by(nickname=player_nickname).first()

    return render_template('reputation_guide.html', current_player=current_player)

@app.route('/karma-guide')
def karma_guide():
    """Show karma FAQ page"""
    current_player = None
    player_nickname = session.get('player_nickname')
    if player_nickname:
        current_player = Player.query.filter_by(nickname=player_nickname).first()
    return render_template('karma_guide.html', current_player=current_player)

@app.route('/coins-guide')
def coins_guide():
    """Coins earning guide"""
    current_player = None
    player_nickname = session.get('player_nickname')
    if player_nickname:
        current_player = Player.query.filter_by(nickname=player_nickname).first()

    return render_template('coins_guide.html', current_player=current_player)

@app.route('/experience_guide')
def experience_guide():
    """Experience earning guide"""
    is_admin = session.get('is_admin', False)
    return render_template('experience_guide.html', is_admin=is_admin)

@app.route('/admin/player-quests')
def admin_player_quests():
    """View all player quests (admin only)"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('login'))

    players = Player.query.all()
    player_quests = {}

    for player in players:
        quests = PlayerQuest.query.filter_by(player_id=player.id).all()
        if quests:
            player_quests[player] = quests

    return render_template('admin_player_quests.html', player_quests=player_quests)

@app.route('/admin/achievements')
def admin_achievements():
    """Admin achievements management"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('login'))

    # Initialize default achievements if none exist
    if Achievement.query.count() == 0:
        Achievement.create_default_achievements()

    achievements = Achievement.query.order_by(Achievement.created_at.desc()).all()
    players = Player.query.order_by(Player.nickname).all()

    # Get player achievements for display
    player_achievements = PlayerAchievement.query.join(Player).join(Achievement).order_by(PlayerAchievement.earned_at.desc()).limit(50).all()

    return render_template('admin_achievements.html',
                         achievements=achievements,
                         players=players,
                         player_achievements=player_achievements,
                         PlayerAchievement=PlayerAchievement)

@app.route('/admin/create_achievement', methods=['POST'])
def create_achievement():
    """Create custom achievement (admin only)"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('login'))

    try:
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        icon = request.form.get('icon', 'fas fa-trophy')
        rarity = request.form.get('rarity', 'common')
        unlock_condition = request.form.get('unlock_condition', '{}')
        reward_xp = int(request.form.get('reward_xp', 0))
        reward_coins = int(request.form.get('reward_coins', 0))
        reward_reputation = int(request.form.get('reward_reputation', 0))
        reward_title = request.form.get('reward_title', '').strip() or None
        is_hidden = request.form.get('is_hidden') == 'on'

        if not title or not description:
            flash('Название и описание обязательны!', 'error')
            return redirect(url_for('admin_achievements'))

        # Validate JSON unlock condition
        try:
            import json
            json.loads(unlock_condition)
        except json.JSONDecodeError:
            flash('Некорректное условие разблокировки (должен быть валидный JSON)!', 'error')
            return redirect(url_for('admin_achievements'))

        achievement = Achievement(
            title=title,
            description=description,
            icon=icon,
            rarity=rarity,
            unlock_condition=unlock_condition,
            reward_xp=reward_xp,
            reward_coins=reward_coins,
            reward_reputation=reward_reputation,
            reward_title=reward_title,
            is_hidden=is_hidden
        )

        db.session.add(achievement)
        db.session.commit()

        flash(f'Достижение "{title}" успешно создано!', 'success')

    except Exception as e:
        app.logger.error(f"Error creating achievement: {e}")
        flash('Ошибка при создании достижения!', 'error')

    return redirect(url_for('admin_achievements'))



@app.route('/admin/assign_achievement', methods=['POST'])
def assign_achievement():
    """Assign achievement to player (admin only)"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('login'))

    try:
        player_id = request.form.get('player_id', type=int)
        achievement_id = request.form.get('achievement_id', type=int)

        if not player_id or not achievement_id:
            flash('Выберите игрока и достижение!', 'error')
            return redirect(url_for('admin_achievements'))

        player = Player.query.get_or_404(player_id)
        achievement = Achievement.query.get_or_404(achievement_id)

        # Check if player already has this achievement
        existing = PlayerAchievement.query.filter_by(
            player_id=player_id,
            achievement_id=achievement_id
        ).first()

        if existing:
            flash('Игрок уже имеет это достижение!', 'warning')
            return redirect(url_for('admin_achievements'))

        # Award achievement
        player_achievement = PlayerAchievement(
            player_id=player_id,
            achievement_id=achievement_id
        )
        db.session.add(player_achievement)

        # Award rewards
        player.experience += achievement.reward_xp
        player.coins += achievement.reward_coins
        player.reputation += achievement.reward_reputation

        db.session.commit()

        flash(f'Достижение "{achievement.title}" присвоено игроку {player.nickname}!', 'success')

    except Exception as e:
        app.logger.error(f"Error assigning achievement: {e}")
        flash('Ошибка при присвоении достижения!', 'error')

    return redirect(url_for('admin_achievements'))

@app.route('/admin/remove_achievement/<int:player_id>/<int:achievement_id>', methods=['POST'])
def remove_achievement(player_id, achievement_id):
    """Remove achievement from player (admin only)"""
    if not session.get('is_admin', False):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    try:
        player_achievement = PlayerAchievement.query.filter_by(
            player_id=player_id,
            achievement_id=achievement_id
        ).first()

        if not player_achievement:
            return jsonify({'success': False, 'error': 'Achievement not found'}), 404

        db.session.delete(player_achievement)
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        app.logger.error(f"Error removing achievement: {e}")
        return jsonify({'success': False, 'error': 'Failed to remove achievement'}), 500

@app.route('/admin/player-achievements')
def admin_player_achievements():
    """View all player achievements (admin only)"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('login'))

    players = Player.query.all()
    player_achievements = {}

    for player in players:
        achievements = PlayerAchievement.query.filter_by(player_id=player.id).all()
        if achievements:
            player_achievements[player] = achievements

    return render_template('admin_player_achievements.html', player_achievements=player_achievements)


@app.route('/admin/create_gradient', methods=['POST'])
def create_gradient():
    """Create new gradient theme (admin only)"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('login'))

    try:
        name = request.form.get('name', '').strip().lower()
        display_name = request.form.get('display_name', '').strip()
        element_type = request.form.get('element_type', '').strip()
        color1 = request.form.get('color1', '#ffffff')
        color2 = request.form.get('color2', '#000000')
        color3 = request.form.get('color3', '').strip() or None
        gradient_direction = request.form.get('gradient_direction', '45deg')
        animation_enabled = request.form.get('animation_enabled') == 'on'

        if not name or not display_name or not element_type:
            flash('Все обязательные поля должны быть заполнены!', 'error')
            return redirect(url_for('admin_gradients'))

        # Check if theme already exists
        existing = GradientTheme.query.filter_by(name=name).first()
        if existing:
            flash('Градиент с таким названием уже существует!', 'error')
            return redirect(url_for('admin_gradients'))

        theme = GradientTheme(
            name=name,
            display_name=display_name,
            element_type=element_type,
            color1=color1,
            color2=color2,
            color3=color3,
            gradient_direction=gradient_direction,
            animation_enabled=animation_enabled
        )

        db.session.add(theme)
        db.session.commit()

        flash(f'Градиент "{display_name}" успешно создан!', 'success')

    except Exception as e:
        app.logger.error(f"Error creating gradient: {e}")
        flash('Ошибка при создании градиента!', 'error')

    return redirect(url_for('admin_gradients'))

@app.route('/admin/assign_gradient', methods=['POST'])
def assign_gradient():
    """Assign gradient to player (admin only)"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('login'))

    try:
        player_id = request.form.get('player_id', type=int)
        element_type = request.form.get('element_type', '').strip()
        gradient_theme_id = request.form.get('gradient_theme_id', type=int)
        custom_color1 = request.form.get('custom_color1', '').strip() or None
        custom_color2 = request.form.get('custom_color2', '').strip() or None
        custom_color3 = request.form.get('custom_color3', '').strip() or None

        if not player_id or not element_type:
            flash('Выберите игрока и тип элемента!', 'error')
            return redirect(url_for('admin_gradients'))

        player = Player.query.get_or_404(player_id)

        # Remove existing gradient for this element type
        PlayerGradientSetting.query.filter_by(
            player_id=player_id,
            element_type=element_type
        ).delete()

        # Create new gradient setting
        gradient_setting = PlayerGradientSetting(
            player_id=player_id,
            element_type=element_type,
            gradient_theme_id=gradient_theme_id if gradient_theme_id else None,
            custom_color1=custom_color1,
            custom_color2=custom_color2,
            custom_color3=custom_color3,
            is_enabled=True
        )

        db.session.add(gradient_setting)
        db.session.commit()

        theme_name = "кастомный градиент"
        if gradient_theme_id:
            theme = GradientTheme.query.get(gradient_theme_id)
            theme_name = theme.display_name if theme else "градиент"

        flash(f'Градиент "{theme_name}" присвоен игроку {player.nickname} для {element_type}!', 'success')

    except Exception as e:
        app.logger.error(f"Error assigning gradient: {e}")
        flash('Ошибка при присвоении градиента!', 'error')

    return redirect(url_for('admin_gradients'))

@app.route('/remove_gradient/<int:player_id>/<element_type>', methods=['POST'])
def remove_gradient(player_id, element_type):
    """Remove gradient from player (admin only)"""
    if not session.get('is_admin', False):
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        PlayerGradientSetting.query.filter_by(
            player_id=player_id,
            element_type=element_type
        ).delete()
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        app.logger.error(f"Error removing gradient: {e}")
        return jsonify({'error': 'Failed to remove gradient'}), 500



@app.route('/profile/<nickname>')
def public_profile_by_nickname(nickname):
    """Display public player profile by nickname"""
    player = Player.query.filter_by(nickname=nickname).first()

    # If player doesn't exist, show a beautiful error page
    if not player:
        return render_template('player_not_found.html', nickname=nickname)

    if not player.profile_is_public and session.get('player_nickname') != nickname:
        flash('Профиль этого игрока приватный!', 'error')
        return redirect(url_for('index'))

    is_owner = session.get('player_nickname') == nickname
    is_admin = session.get('is_admin', False)

    # Get player's visible badges
    player_badges = PlayerBadge.query.filter_by(player_id=player.id, is_visible=True).all()
    visible_badges_data = []
    for pb in player_badges:
        badge = Badge.query.get(pb.badge_id)
        if badge and badge.is_active:
            visible_badges_data.append({
                'badge': badge,
                'display_name': badge.display_name,
                'icon': badge.icon,
                'color': badge.color,
                'background_color': badge.background_color,
                'border_color': badge.border_color,
                'rarity': badge.rarity,
                'has_gradient': badge.has_gradient,
                'gradient_start': badge.gradient_start,
                'gradient_end': badge.gradient_end,
                'is_animated': badge.is_animated
            })

    # Get game modes for ASCEND card
    from models import GameMode
    if GameMode.query.count() == 0:
        GameMode.create_default_modes()
    game_modes_query = GameMode.query.filter_by(is_active=True).all()
    game_modes = [
        {
            'id': mode.id,
            'name': mode.name,
            'display_name': mode.display_name,
            'icon': mode.icon,
            'color': mode.color
        }
        for mode in game_modes_query
    ]

    return render_template('public_profile.html',
                         player=player,
                         is_owner=is_owner,
                         is_admin=is_admin,
                         visible_badges=visible_badges_data,
                         game_modes=game_modes)



@app.route('/update-profile', methods=['POST'])
def update_profile():
    """Update current player's profile"""
    player_nickname = session.get('player_nickname')
    if not player_nickname:
        flash('Необходимо войти в систему!', 'error')
        return redirect(url_for('player_login'))

    player = Player.query.filter_by(nickname=player_nickname).first_or_404()

    try:
        # Update personal information
        player.real_name = request.form.get('real_name', '').strip() or None
        player.bio = request.form.get('bio', '').strip() or None
        player.discord_tag = request.form.get('discord_tag', '').strip() or None
        player.youtube_channel = request.form.get('youtube_channel', '').strip() or None
        player.twitch_channel = request.form.get('twitch_channel', '').strip() or None
        player.favorite_server = request.form.get('favorite_server', '').strip() or None
        player.favorite_map = request.form.get('favorite_map', '').strip() or None
        player.preferred_gamemode = request.form.get('preferred_gamemode', '').strip() or None
        player.profile_banner_color = request.form.get('profile_banner_color', '#3498db')
        player.profile_is_public = request.form.get('profile_is_public') == 'on'
        player.custom_status = request.form.get('custom_status', '').strip() or None
        player.location = request.form.get('location', '').strip() or None

        # Handle birthday
        birthday_str = request.form.get('birthday', '').strip()
        if birthday_str:
            from datetime import datetime
            try:
                player.birthday = datetime.strptime(birthday_str, '%Y-%m-%d').date()
            except ValueError:
                player.birthday = None
        else:
            player.birthday = None

        # Handle custom avatar and banner
        player.custom_avatar_url = request.form.get('custom_avatar_url', '').strip() or None

        # Only allow banner customization for level 20+
        if player.level >= 20:
            player.custom_banner_url = request.form.get('custom_banner_url', '').strip() or None
            player.banner_is_animated = request.form.get('banner_is_animated') == 'on'

        # Profile section colors
        player.stats_section_color = request.form.get('stats_section_color', '#343a40')
        player.info_section_color = request.form.get('info_section_color', '#343a40')
        player.social_section_color = request.form.get('social_section_color', '#343a40')
        player.prefs_section_color = request.form.get('prefs_section_color', '#343a40')

        # Handle custom social networks
        social_types = request.form.getlist('social_type[]')
        social_values = request.form.getlist('social_value[]')

        if social_types and social_values:
            social_networks = []
            for i, (social_type, social_value) in enumerate(zip(social_types, social_values)):
                if social_type and social_value.strip():
                    social_networks.append({
                        'type': social_type,
                        'value': social_value.strip()
                    })
            player.set_social_networks_list(social_networks)
        else:
            player.set_social_networks_list([])

        db.session.commit()
        # Очистка кэша статистики
        Player.clear_statistics_cache()
        flash('Профиль успешно обновлен!', 'success')

    except Exception as e:
        app.logger.error(f"Error updating profile: {e}")
        flash('Ошибка при обновлении профиля!', 'error')

    return redirect(url_for('my_profile'))

@app.route('/apply-gradient', methods=['POST'])
def apply_gradient():
    """Apply gradient to player's elements"""
    player_nickname = session.get('player_nickname')
    if not player_nickname:
        flash('Необходимо войти в систему!', 'error')
        return redirect(url_for('player_login'))

    player = Player.query.filter_by(nickname=player_nickname).first_or_404()

    try:
        element_type = request.form.get('element_type')
        gradient_theme_id = request.form.get('gradient_theme_id', type=int)

        if not element_type:
            flash('Тип элемента обязателен!', 'error')
            return redirect(url_for('my_profile'))

        # Remove existing gradient for this element type
        PlayerGradientSetting.query.filter_by(
            player_id=player.id,
            element_type=element_type
        ).delete()

        # Add new gradient if theme selected
        if gradient_theme_id:
            gradient_setting = PlayerGradientSetting(
                player_id=player.id,
                element_type=element_type,
                gradient_theme_id=gradient_theme_id,
                is_enabled=True
            )
            db.session.add(gradient_setting)

        db.session.commit()
        flash('Градиент применен!', 'success')

    except Exception as e:
        app.logger.error(f"Error applying gradient: {e}")
        flash('Ошибка при применении градиента!', 'error')

    return redirect(url_for('my_profile'))

@app.route('/activate_title', methods=['POST'])
def activate_title():
    """Activate a title for player"""
    player_nickname = session.get('player_nickname')
    if not player_nickname:
        flash('Необходимо войти в систему!', 'error')
        return redirect(url_for('player_login'))

    player = Player.query.filter_by(nickname=player_nickname).first_or_404()

    try:
        title_name = request.form.get('title_name')

        if player.set_active_title(title_name):
            if title_name:
                flash('Титул активирован!', 'success')
            else:
                flash('Титул убран!', 'success')
        else:
            flash('Ошибка при изменении титула!', 'error')

    except Exception as e:
        app.logger.error(f"Error activating title: {e}")
        flash('Ошибка при активации титула!', 'error')

    return redirect(url_for('role_management'))


# Function to initialize shop items, including boosters
def initialize_shop_items():
    """Initialize default shop items if they don't exist"""
    try:
        # Create boosters if they don't exist
        if ShopItem.query.filter_by(category='booster').count() == 0:

            # Import json at the top if not already imported
            import json

            boosters = [
                {
                    'name': 'coin_booster_1h',
                    'display_name': '🪙 Бустер койнов (1ч)',
                    'description': '+50% к получаемым койнам на 1 час',
                    'category': 'booster',
                    'price_coins': 100,
                    'price_reputation': 0,
                    'unlock_level': 1,
                    'rarity': 'common',
                    'icon': 'fas fa-coins',
                    'item_data': json.dumps({
                        'type': 'coin_multiplier',
                        'multiplier': 1.5,
                        'duration_hours': 1
                    }),
                    'is_active': True
                },
                {
                    'name': 'rep_booster_1h',
                    'display_name': '⭐ Бустер репутации (1ч)',
                    'description': '+50% к получаемой репутации на 1 час',
                    'category': 'booster',
                    'price_coins': 150,
                    'price_reputation': 0,
                    'unlock_level': 1,
                    'rarity': 'common',
                    'icon': 'fas fa-star',
                    'item_data': json.dumps({
                        'type': 'reputation_multiplier',
                        'multiplier': 1.5,
                        'duration_hours': 1
                    }),
                    'is_active': True
                }
            ]

            for booster_data in boosters:
                booster = ShopItem(**booster_data)
                db.session.add(booster)

            db.session.commit()
            app.logger.info("Default boosters created")

    except Exception as e:
        app.logger.error(f"Error initializing shop items: {e}")

# Call this function after app initialization
with app.app_context():
    initialize_shop_items()

@app.route('/clans')
def clans():
    """Orders page"""
    current_player = None
    player_clan = None

    # Check if player is logged in
    player_nickname = session.get('player_nickname')
    if player_nickname:
        current_player = Player.query.filter_by(nickname=player_nickname).first()
        if current_player:
            # Get player's clan
            try:
                from models import ClanMember
                clan_member = ClanMember.query.filter_by(player_id=current_player.id).first()
                if clan_member:
                    player_clan = clan_member.clan
            except ImportError:
                pass

    # Get search and sorting parameters
    search_query = request.args.get('search', '').strip()
    current_sort = request.args.get('sort', 'rating')

    # Get clans (placeholder - will work when Clan model is properly defined)
    clans = []
    try:
        from models import Clan
        query = Clan.query

        if search_query:
            query = query.filter(
                db.or_(
                    Clan.name.ilike(f'%{search_query}%'),
                    Clan.tag.ilike(f'%{search_query}%')
                )
            )

        if current_sort == 'rating':
            query = query.order_by(Clan.rating.desc())
        elif current_sort == 'level':
            query = query.order_by(Clan.level.desc())
        elif current_sort == 'members':
            query = query.order_by(Clan.member_count.desc())
        elif current_sort == 'created':
            query = query.order_by(Clan.created_at.desc())

        clans = query.all()
    except ImportError:
        # Clan model not yet implemented
        pass
    except Exception as e:
        app.logger.error(f"Error loading tournaments: {e}")

    return render_template('clans.html',
                         clans=clans,
                         current_player=current_player,
                         player_clan=player_clan,
                         search_query=search_query,
                         current_sort=current_sort)

@app.route('/create_clan', methods=['GET', 'POST'])
def create_clan():
    """Create order page"""
    player_nickname = session.get('player_nickname')
    if not player_nickname:
        flash('Необходимо войти в систему для создания ордена!', 'error')
        return redirect(url_for('player_login'))

    current_player = Player.query.filter_by(nickname=player_nickname).first()
    if not current_player:
        flash('Игрок не найден!', 'error')
        return redirect(url_for('player_login'))

    # Check if player already in an order
    try:
        from models import ClanMember
        existing_membership = ClanMember.query.filter_by(player_id=current_player.id).first()
        if existing_membership:
            flash('Вы уже состоите в ордене!', 'error')
            return redirect(url_for('clans'))
    except ImportError:
        pass

    if request.method == 'POST':
        try:
            from models import Clan, ClanMember

            name = request.form.get('name', '').strip()
            tag = request.form.get('tag', '').strip().upper()
            description = request.form.get('description', '').strip()
            clan_type = request.form.get('clan_type', 'open')
            max_members = int(request.form.get('max_members', 20))

            # Validation
            if not name or not tag:
                flash('Название и тег ордена обязательны!', 'error')
                return render_template('create_clan.html', current_player=current_player)

            if len(name) < 3 or len(name) > 30:
                flash('Название ордена должно быть от 3 до 30 символов!', 'error')
                return render_template('create_clan.html', current_player=current_player)

            if len(tag) < 2 or len(tag) > 10:
                flash('Тег ордена должен быть от 2 до 10 символов!', 'error')
                return render_template('create_clan.html', current_player=current_player)

            # Check if name or tag already exists
            existing_name = Clan.query.filter_by(name=name).first()
            if existing_name:
                flash('Орден с таким названием уже существует!', 'error')
                return render_template('create_clan.html', current_player=current_player)

            existing_tag = Clan.query.filter_by(tag=tag).first()
            if existing_tag:
                flash('Орден с таким тегом уже существует!', 'error')
                return render_template('create_clan.html', current_player=current_player)

            # Create clan
            clan = Clan(
                name=name,
                tag=tag,
                description=description,
                clan_type=clan_type,
                max_members=max_members,
                leader_id=current_player.id
            )
            db.session.add(clan)
            db.session.flush()  # Get clan ID

            # Add creator as leader
            clan_member = ClanMember(
                clan_id=clan.id,
                player_id=current_player.id,
                role='leader',
                joined_at=datetime.utcnow()
            )
            db.session.add(clan_member)
            db.session.commit()

            flash(f'Орден "{name}" [{tag}] успешно создан!', 'success')
            return redirect(url_for('clan_detail', clan_id=clan.id))

        except ImportError:
            flash('Система орденов временно недоступна!', 'error')
        except Exception as e:
            app.logger.error(f"Error creating clan: {e}")
            flash('Ошибка при создании ордена!', 'error')

    return render_template('create_clan.html', current_player=current_player)

@app.route('/clan/<int:clan_id>')
def clan_detail(clan_id):
    """Order detail page"""
    try:
        from models import Clan, ClanMember
        clan = Clan.query.get_or_404(clan_id)

        # Get clan members
        members = ClanMember.query.filter_by(clan_id=clan_id).all()

        # Check if current player is in this clan
        current_player = None
        player_membership = None
        player_nickname = session.get('player_nickname')
        if player_nickname:
            current_player = Player.query.filter_by(nickname=player_nickname).first()
            if current_player:
                player_membership = ClanMember.query.filter_by(
                    clan_id=clan_id,
                    player_id=current_player.id
                ).first()

        return render_template('clan_detail.html',
                             clan=clan,
                             members=members,
                             current_player=current_player,
                             player_membership=player_membership)

    except ImportError:
        flash('Система орденов временно недоступна!', 'error')
        return redirect(url_for('index'))

@app.route('/tournaments')
def tournaments():
    """Tournaments page"""
    current_player = None
    is_admin = session.get('is_admin', False)

    # Check if player is logged in
    player_nickname = session.get('player_nickname')
    if player_nickname:
        current_player = Player.query.filter_by(nickname=player_nickname).first()

    # Get tournaments (placeholder - will work when Tournament model is properly defined)
    tournaments = []
    current_status = request.args.get('status', 'all')

    try:
        from models import Tournament
        query = Tournament.query

        if current_status != 'all':
            query = query.filter_by(status=current_status)

        tournaments = query.order_by(Tournament.start_date.desc()).all()
    except ImportError:
        # Tournament model not yet implemented
        pass
    except Exception as e:
        app.logger.error(f"Error loading tournaments: {e}")

    return render_template('tournaments.html',
                         tournaments=tournaments,
                         current_player=current_player,
                         is_admin=is_admin,
                         current_status=current_status)

@app.route('/tournament/<int:tournament_id>')
def tournament_detail(tournament_id):
    """Tournament detail page"""
    try:
        from models import Tournament, TournamentParticipant

        tournament = Tournament.query.get_or_404(tournament_id)

        # Check if current player is participant
        is_participant = False
        current_player = None
        player_nickname = session.get('player_nickname')
        if player_nickname:
            current_player = Player.query.filter_by(nickname=player_nickname).first()
            if current_player:
                is_participant = TournamentParticipant.query.filter_by(
                    tournament_id=tournament_id,
                    player_id=current_player.id
                ).first() is not None

        # Get participants
        participants = TournamentParticipant.query.filter_by(tournament_id=tournament_id).all()

        return render_template('tournament_detail.html',
                             tournament=tournament,
                             participants=participants,
                             current_player=current_player,
                             is_participant=is_participant)

    except ImportError:
        flash('Система турниров временно недоступна!', 'error')
        return redirect(url_for('index'))

@app.route('/create_tournament', methods=['GET', 'POST'])
def create_tournament():
    """Create tournament page (admin only)"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            from models import Tournament

            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            tournament_type = request.form.get('tournament_type', 'singles')
            start_date_str = request.form.get('start_date', '')
            entry_fee = int(request.form.get('entry_fee', 0))
            prize_pool = int(request.form.get('prize_pool', 0))
            max_participants = int(request.form.get('max_participants', 100))

            if not name or not start_date_str:
                flash('Название и дата начала обязательны!', 'error')
                return render_template('create_tournament.html')

            # Parse start date
            from datetime import datetime
            start_date = datetime.fromisoformat(start_date_str)

            tournament = Tournament(
                name=name,
                description=description,
                tournament_type=tournament_type,
                start_date=start_date,
                entry_fee=entry_fee,
                prize_pool=prize_pool,
                max_participants=max_participants,
                organizer_id=session.get('admin_id', 1)  # Placeholder admin ID
            )

            db.session.add(tournament)
            db.session.commit()

            flash(f'Турнир "{name}" успешно создан!', 'success')
            return redirect(url_for('tournaments'))

        except ImportError:
            flash('Система турниров временно недоступна!', 'error')
        except Exception as e:
            app.logger.error(f"Error creating tournament: {e}")
            flash('Ошибка при создании турнира!', 'error')

    return render_template('create_tournament.html')

@app.route('/join_tournament/<int:tournament_id>', methods=['POST'])
def join_tournament(tournament_id):
    """Join tournament"""
    player_nickname = session.get('player_nickname')
    if not player_nickname:
        flash('Необходимо войти в систему для участия в турнире!', 'error')
        return redirect(url_for('player_login'))

    try:
        from models import Tournament, TournamentParticipant

        tournament = Tournament.query.get_or_404(tournament_id)
        player = Player.query.filter_by(nickname=player_nickname).first()

        if not player:
            flash('Игрок не найден!', 'error')
            return redirect(url_for('tournaments'))

        # Check if tournament can accept participants
        if not tournament.can_join:
            flash('Регистрация на турнир закрыта!', 'error')
            return redirect(url_for('tournament_detail', tournament_id=tournament_id))

        # Check if already participating
        existing = TournamentParticipant.query.filter_by(
            tournament_id=tournament_id,
            player_id=player.id
        ).first()

        if existing:
            flash('Вы уже зарегистрированы на этот турнир!', 'warning')
            return redirect(url_for('tournament_detail', tournament_id=tournament_id))

        # Check entry fee
        if tournament.entry_fee > 0 and player.coins < tournament.entry_fee:
            flash(f'Недостаточно койнов для участия! Требуется: {tournament.entry_fee}', 'error')
            return redirect(url_for('tournament_detail', tournament_id=tournament_id))

        # Deduct entry fee
        if tournament.entry_fee > 0:
            player.coins -= tournament.entry_fee

        # Add participant
        participant = TournamentParticipant(
            tournament_id=tournament_id,
            player_id=player.id
        )
        db.session.add(participant)
        db.session.commit()

        flash(f'Вы успешно зарегистрированы на турнир "{tournament.name}"!', 'success')
        return redirect(url_for('tournament_detail', tournament_id=tournament_id))

    except ImportError:
        flash('Система турниров временно недоступна!', 'error')
        return redirect(url_for('tournaments'))
    except Exception as e:
        app.logger.error(f"Error joining tournament: {e}")
        flash('Ошибка при регистрации на турнир!', 'error')
        return redirect(url_for('tournaments'))

@app.route('/targets/add', methods=['POST'])
def add_target():
    """Add new target to list (admin only)"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('target_list'))

    try:
        from models import Target

        nickname = request.form.get('nickname', '').strip()
        gamemode = request.form.get('gamemode', '').strip()
        server_ip = request.form.get('server_ip', '').strip()
        reason = request.form.get('reason', '').strip()
        priority = request.form.get('priority', 'medium').strip()

        if not all([nickname, gamemode, server_ip, reason]):
            flash('Заполните все поля!', 'error')
            return redirect(url_for('target_list'))

        # Validate priority
        valid_priorities = ['low', 'medium', 'high', 'critical']
        if priority not in valid_priorities:
            priority = 'medium'

        # Check if target already exists
        existing = Target.query.filter_by(nickname=nickname, gamemode=gamemode).first()
        if existing:
            flash('Цель с таким никнеймом и режимом уже существует!', 'error')
            return redirect(url_for('target_list'))

        target = Target(
            nickname=nickname,
            gamemode=gamemode,
            server=server_ip,
            reason=reason,
            priority=priority,
            added_by=session.get('player_nickname', 'admin'),
            status='active'
        )

        db.session.add(target)
        db.session.commit()

        flash(f'Цель "{nickname}" добавлена в список!', 'success')

    except Exception as e:
        app.logger.error(f"Error adding target: {e}")
        flash('Ошибка при добавлении цели!', 'error')

    return redirect(url_for('target_list'))

@app.route('/targets/<int:target_id>/complete', methods=['POST'])
def complete_target(target_id):
    """Mark target as completed (admin only)"""
    if not session.get('is_admin', False):
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        from models import Target
        target = Target.query.get_or_404(target_id)
        target.status = 'completed'
        target.date_completed = datetime.utcnow()

        db.session.commit()
        return jsonify({'success': True})

    except Exception as e:
        app.logger.error(f"Error completing target: {e}")
        return jsonify({'error': 'Failed to complete target'}), 500

@app.route('/targets/<int:target_id>/delete', methods=['POST'])
def delete_target(target_id):
    """Delete target from list (admin only)"""
    if not session.get('is_admin', False):
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        from models import Target
        target = Target.query.get_or_404(target_id)

        db.session.delete(target)
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        app.logger.error(f"Error deleting target: {e}")
        return jsonify({'error': 'Failed to delete target'}), 500

@app.route('/candidates')
def candidates():
    """Candidates list page"""
    try:
        from models import Candidate

        # Get filter parameters
        status_filter = request.args.get('status', 'all')
        search_query = request.args.get('search', '').strip()
        sort_by = request.args.get('sort', 'date_added')

        # Base query
        query = Candidate.query

        # Apply filters
        if status_filter != 'all':
            query = query.filter(Candidate.status == status_filter)

        if search_query:
            query = query.filter(Candidate.nickname.ilike(f'%{search_query}%'))

        # Apply sorting
        if sort_by == 'nickname':
            query = query.order_by(Candidate.nickname.asc())
        elif sort_by == 'status':
            query = query.order_by(Candidate.status.asc())
        elif sort_by == 'rating':
            query = query.order_by(Candidate.rating.desc())
        elif sort_by == 'likes':
            query = query.order_by(Candidate.likes.desc())
        else:  # date_added
            query = query.order_by(Candidate.date_added.desc())

        candidates = query.all()

        return render_template('candidates.html',
                             candidates=candidates,
                             status_filter=status_filter,
                             search_query=search_query,
                             sort_by=sort_by)

    except Exception as e:
        app.logger.error(f"Error loading candidates: {e}")
        flash('Ошибка загрузки кандидатов', 'error')
        return render_template('candidates.html', candidates=[])

# Add missing badge management routes
@app.route('/admin/toggle_badge_status/<int:badge_id>')
def toggle_badge_status(badge_id):
    """Toggle badge active status (admin only)"""
    if not session.get('is_admin', False):
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        badge = Badge.query.get_or_404(badge_id)
        badge.is_active = not badge.is_active
        db.session.commit()

        return jsonify({
            'success': True,
            'new_status': badge.is_active
        })

    except Exception as e:
        app.logger.error(f"Error toggling badge status: {e}")
        return jsonify({'error': 'Failed to toggle status'}), 500

@app.route('/admin/remove_badge_permanently/<int:badge_id>', methods=['DELETE'])
def remove_badge_permanently(badge_id):
    """Permanently remove badge (admin only)"""
    if not session.get('is_admin', False):
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        badge = Badge.query.get_or_404(badge_id)

        # Remove all player assignments first
        PlayerBadge.query.filter_by(badge_id=badge_id).delete()

        # Remove badge
        db.session.delete(badge)
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        app.logger.error(f"Error removing badge: {e}")
        return jsonify({'error': 'Failed to remove badge'}), 500

@app.route('/admin/remove_all_player_badges/<int:player_id>', methods=['POST'])
def remove_all_player_badges(player_id):
    """Remove all badges from player (admin only)"""
    if not session.get('is_admin', False):
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        PlayerBadge.query.filter_by(player_id=player_id).delete()
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        app.logger.error(f"Error removing player badges: {e}")
        return jsonify({'error': 'Failed to remove badges'}), 500

@app.route('/admin/create_default_badges', methods=['POST'])
def create_default_badges():
    """Create default badges (admin only)"""
    if not session.get('is_admin', False):
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        Badge.create_default_badges()
        return jsonify({'success': True})

    except Exception as e:
        app.logger.error(f"Error creating default badges: {e}")
        return jsonify({'error': 'Failed to create badges'}), 500

@app.route('/admin/export_badges')
def export_badges():
    """Export badges data (admin only)"""
    if not session.get('is_admin', False):
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('login'))

    try:
        badges = Badge.query.all()

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            'ID', 'Name', 'Display Name', 'Description', 'Icon', 'Color',
            'Background Color', 'Border Color', 'Rarity', 'Is Active', 'Created At'
        ])

        # Data
        for badge in badges:
            writer.writerow([
                badge.id, badge.name, badge.display_name, badge.description or '',
                badge.icon, badge.color, badge.background_color, badge.border_color,
                badge.rarity, badge.is_active, badge.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])

        output.seek(0)

        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=badges_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

        return response

    except Exception as e:
        app.logger.error(f"Error exporting badges: {e}")
        flash('Ошибка при экспорте бейджей!', 'error')
        return redirect(url_for('admin_badges'))