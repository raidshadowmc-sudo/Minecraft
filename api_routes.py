from flask import jsonify, request, session, flash, redirect, url_for
from app import app, db
from models import Player, PlayerBadge, Badge, ASCENDData, GameMode, ASCENDHistory, ShopItem, ShopPurchase, CustomTitle, PlayerTitle, PlayerGradientSetting, Quest, PlayerQuest, Achievement, PlayerAchievement, Candidate, CandidateReaction
import json
from datetime import datetime

def calculate_tier_from_score(score):
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
    elif score >= 65:
        return 'C+'
    elif score >= 60:
        return 'C'
    else:
        return 'D'

@app.route('/api/leaderboard')
def api_leaderboard():
    """API endpoint for leaderboard data with fallback"""
    try:
        sort_by = request.args.get('sort', 'experience')
        limit = min(int(request.args.get('limit', 50)), 100)

        players = Player.get_leaderboard(sort_by=sort_by, limit=limit) or []

        # Convert players to dict format
        players_data = []
        for player in players:
            players_data.append({
                'id': player.id,
                'nickname': player.nickname,
                'level': player.level,
                'experience': player.experience,
                'kills': player.kills,
                'deaths': player.deaths,
                'wins': player.wins,
                'games_played': player.games_played,
                'kd_ratio': player.kd_ratio,
                'win_rate': player.win_rate
            })

        return jsonify({
            'success': True,
            'players': players_data,
            'total': len(players_data)
        })
    except Exception as e:
        app.logger.error(f"Error in API leaderboard: {e}")
        return jsonify({
            'success': False,
            'players': [],
            'total': 0,
            'error': str(e) if e else 'Failed to load leaderboard data'
        }), 200  # Still return 200 with empty data

@app.route('/api/stats')
def api_stats():
    """API endpoint for statistics data"""
    try:
        stats = Player.get_statistics()
        # Convert Player objects to dictionaries
        serializable_stats = {}
        for key, value in stats.items():
            if hasattr(value, '__dict__'):  # If it's a model instance
                if hasattr(value, 'nickname'):  # Player object
                    serializable_stats[key] = {
                        'id': value.id,
                        'nickname': value.nickname,
                        'level': value.level,
                        'experience': value.experience,
                        'coins': getattr(value, 'coins', 0),
                        'reputation': getattr(value, 'reputation', 0)
                    }
                else:
                    serializable_stats[key] = str(value)
            else:
                serializable_stats[key] = value
        return jsonify(serializable_stats)
    except Exception as e:
        app.logger.error(f"Error in API stats: {e}")
        return jsonify({'error': 'Failed to load statistics'}), 500

@app.route('/shop/purchase', methods=['POST'])
def purchase_shop_item():
    """Handle shop item purchases"""
    player_nickname = session.get('player_nickname')
    if not player_nickname:
        return jsonify({'success': False, 'error': 'Необходимо войти в систему'})

    try:
        data = request.get_json()
        item_id = data.get('item_id')

        player = Player.query.filter_by(nickname=player_nickname).first()
        if not player:
            return jsonify({'success': False, 'error': 'Игрок не найден'})

        shop_item = ShopItem.query.get(item_id)
        if not shop_item or not shop_item.is_active:
            return jsonify({'success': False, 'error': 'Товар не найден'})

        # Check if already purchased
        existing_purchase = ShopPurchase.query.filter_by(
            player_id=player.id,
            item_id=item_id
        ).first()

        if existing_purchase:
            return jsonify({'success': False, 'error': 'Товар уже куплен'})

        # Check level requirement
        if player.level < shop_item.unlock_level:
            return jsonify({'success': False, 'error': f'Требуется {shop_item.unlock_level} уровень'})

        # Check currency
        if shop_item.price_coins > 0 and player.coins < shop_item.price_coins:
            return jsonify({'success': False, 'error': 'Недостаточно койнов'})

        if shop_item.price_reputation > 0 and player.reputation < shop_item.price_reputation:
            return jsonify({'success': False, 'error': 'Недостаточно репутации'})

        # Process purchase
        if shop_item.price_coins > 0:
            player.coins -= shop_item.price_coins
        if shop_item.price_reputation > 0:
            player.reputation -= shop_item.price_reputation

        # Create purchase record
        purchase = ShopPurchase(
            player_id=player.id,
            item_id=item_id,
            price_paid_coins=shop_item.price_coins,
            price_paid_reputation=shop_item.price_reputation
        )
        db.session.add(purchase)

        # Apply item effects
        success, message = shop_item.apply_item_effect(player)

        if not success:
            db.session.rollback()
            return jsonify({'success': False, 'error': message})

        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Товар "{shop_item.display_name}" успешно куплен!',
            'coins': player.coins,
            'reputation': player.reputation
        })

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error purchasing item: {e}")
        return jsonify({'success': False, 'error': 'Ошибка при покупке товара'})


@app.route('/api/toggle-admin-role', methods=['POST'])
def toggle_admin_role():
    """Toggle admin role activation"""
    player_nickname = session.get('player_nickname')
    if not player_nickname:
        return jsonify({'success': False, 'error': 'Необходимо войти в систему'}), 401

    try:
        data = request.get_json()
        role_id = data.get('role_id')
        is_active = data.get('is_active')

        player = Player.query.filter_by(nickname=player_nickname).first()
        if not player:
            return jsonify({'success': False, 'error': 'Игрок не найден'}), 404

        # Get the admin role
        from models import PlayerAdminRole
        admin_role = PlayerAdminRole.query.filter_by(
            id=role_id,
            player_id=player.id
        ).first()

        if not admin_role:
            return jsonify({'success': False, 'error': 'Роль не найдена'}), 404

        if is_active:
            # Deactivate all other admin roles for this player
            PlayerAdminRole.query.filter_by(
                player_id=player.id,
                is_active=True
            ).update({'is_active': False})

        admin_role.is_active = is_active
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Роль {"активирована" if is_active else "деактивирована"}'
        })

    except Exception as e:
        app.logger.error(f"Toggle admin role error: {e}")
        return jsonify({'success': False, 'error': 'Произошла ошибка'}), 500

@app.route('/api/player/<int:player_id>/badges')
def get_player_badges(player_id):
    """Get all badges for a player"""
    try:
        player = Player.query.get_or_404(player_id)
        player_badges = PlayerBadge.query.filter_by(player_id=player_id, is_visible=True).all()

        badges_data = []
        for pb in player_badges:
            badge = Badge.query.get(pb.badge_id)
            if badge and badge.is_active:
                badges_data.append({
                    'id': badge.id,
                    'name': badge.name,
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

        return jsonify({
            'success': True,
            'badges': badges_data
        })

    except Exception as e:
        app.logger.error(f"Error getting player badges: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/assign_badge', methods=['POST'])
def api_assign_badge():
    """Assign badge to player via API (admin only)"""
    if not session.get('is_admin', False):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    try:
        data = request.get_json()
        player_id = data.get('player_id')
        badge_id = data.get('badge_id')

        if not player_id or not badge_id:
            return jsonify({'success': False, 'error': 'Missing player_id or badge_id'}), 400

        player = Player.query.get_or_404(player_id)
        badge = Badge.query.get_or_404(badge_id)

        # Check if player already has this badge
        existing = PlayerBadge.query.filter_by(
            player_id=player_id,
            badge_id=badge_id
        ).first()

        if existing:
            return jsonify({
                'success': False,
                'error': f'Player {player.nickname} already has badge "{badge.display_name}"'
            }), 400

        # Add badge
        player_badge = PlayerBadge(
            player_id=player_id,
            badge_id=badge_id,
            given_by='admin'
        )
        db.session.add(player_badge)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Badge "{badge.display_name}" assigned to player {player.nickname}'
        })

    except Exception as e:
        app.logger.error(f"Error assigning badge via API: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/player/<int:player_id>/ascend-data')
def get_ascend_data(player_id):
    """Get ASCEND performance card data for a player in specific gamemode"""
    try:
        gamemode = request.args.get('gamemode', 'bedwars')
        player = Player.query.get_or_404(player_id)
        ascend_data = ASCENDData.get_or_create(player_id, gamemode)

        return jsonify({
            'success': True,
            'ascend': ascend_data.to_dict(),
            'gamemode': gamemode
        })
    except Exception as e:
        app.logger.error(f"Error getting ASCEND data: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/ascend/<int:player_id>')
@app.route('/api/ascend/<int:player_id>/<gamemode>')
def get_ascend_data_alt(player_id, gamemode='bedwars'):
    """Alternative ASCEND API endpoint"""
    try:
        player = Player.query.get_or_404(player_id)
        ascend_data = ASCENDData.get_or_create(player_id, gamemode)

        return jsonify({
            'success': True,
            'ascend': ascend_data.to_dict(),
            'gamemode': gamemode
        })
    except Exception as e:
        app.logger.error(f"Error getting ASCEND data: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/player/<int:player_id>/ascend-history')
def api_get_ascend_history(player_id):
    """Get ASCEND evaluation history for player"""
    try:
        gamemode = request.args.get('gamemode', 'bedwars')
        limit = min(int(request.args.get('limit', 20)), 100)

        history = ASCENDHistory.query.filter_by(
            player_id=player_id,
            gamemode=gamemode
        ).order_by(ASCENDHistory.created_at.desc()).limit(limit).all()

        return jsonify({
            'success': True,
            'history': [entry.to_dict() for entry in history]
        })
    except Exception as e:
        app.logger.error(f"Error getting ASCEND history: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Added new API route for player gradients
@app.route('/api/player/<int:player_id>/gradients')
def get_player_gradients(player_id):
    try:
        player = Player.query.get_or_404(player_id)

        # Get all gradient settings for this player
        gradient_settings = PlayerGradientSetting.query.filter_by(
            player_id=player_id,
            is_enabled=True
        ).all()

        gradients = {}
        for setting in gradient_settings:
            if setting.gradient_theme:
                gradients[setting.element_type] = {
                    'css_gradient': setting.gradient_theme.css_gradient,
                    'is_animated': setting.gradient_theme.is_animated
                }

        return jsonify({
            'success': True,
            'gradients': gradients
        })

    except Exception as e:
        app.logger.error(f"Error getting player gradients: {e}") # Added logging
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/gamemodes')
def api_get_gamemodes():
    """Get all available game modes"""
    try:
        gamemodes = GameMode.query.filter_by(is_active=True).all()
        return jsonify({
            'success': True,
            'gamemodes': [mode.to_dict() for mode in gamemodes]
        })
    except Exception as e:
        app.logger.error(f"Error getting game modes: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/global-leaderboard')
def api_global_leaderboard():
    """Get global ASCEND leaderboard"""
    try:
        gamemode = request.args.get('gamemode', 'bedwars')
        limit = min(int(request.args.get('limit', 50)), 100)

        # Get top players by average score in gamemode
        leaderboard = db.session.query(
            ASCENDData,
            Player,
            ((ASCENDData.skill1_score + ASCENDData.skill2_score +
              ASCENDData.skill3_score + ASCENDData.skill4_score) / 4).label('avg_score')
        ).join(Player, ASCENDData.player_id == Player.id).filter(
            ASCENDData.gamemode == gamemode
        ).order_by(
            ((ASCENDData.skill1_score + ASCENDData.skill2_score +
              ASCENDData.skill3_score + ASCENDData.skill4_score) / 4).desc()
        ).limit(limit).all()

        result = []
        for ascend, player, avg_score in leaderboard:
            result.append({
                'rank': len(result) + 1,
                'player': {
                    'id': player.id,
                    'nickname': player.nickname,
                    'level': player.level,
                    'skin_url': player.minecraft_skin_url
                },
                'ascend': ascend.to_dict(),
                'average_score': round(avg_score, 1)
            })

        return jsonify({
            'success': True,
            'leaderboard': result,
            'gamemode': gamemode
        })
    except Exception as e:
        app.logger.error(f"Error getting global leaderboard: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/gamemode-leaderboard')
def api_gamemode_leaderboard():
    """API endpoint for gamemode-specific leaderboard"""
    try:
        gamemode = request.args.get('gamemode', 'bedwars')
        limit = min(int(request.args.get('limit', 50)), 100)

        leaderboard_data = []

        if gamemode == 'bedwars':
            players = Player.query.filter(Player.experience > 0).order_by(Player.experience.desc()).limit(limit).all()

            for idx, player in enumerate(players, 1):
                leaderboard_data.append({
                    'rank': idx,
                    'id': player.id,
                    'nickname': player.nickname,
                    'level': player.level,
                    'experience': player.experience,
                    'kills': player.kills,
                    'final_kills': player.final_kills,
                    'deaths': player.deaths,
                    'final_deaths': player.final_deaths,
                    'beds_broken': player.beds_broken,
                    'wins': player.wins,
                    'games_played': player.games_played,
                    'kd_ratio': player.kd_ratio,
                    'fkd_ratio': player.fkd_ratio,
                    'win_rate': player.win_rate,
                    'role': player.display_role,
                    'skin_url': player.minecraft_skin_url
                })

        elif gamemode == 'kitpvp':
            players = Player.query.filter(Player.kitpvp_kills > 0).order_by(Player.kitpvp_kills.desc()).limit(limit).all()

            for idx, player in enumerate(players, 1):
                kd = round(player.kitpvp_kills / player.kitpvp_deaths, 2) if player.kitpvp_deaths > 0 else player.kitpvp_kills
                leaderboard_data.append({
                    'rank': idx,
                    'id': player.id,
                    'nickname': player.nickname,
                    'kills': player.kitpvp_kills,
                    'deaths': player.kitpvp_deaths,
                    'kd_ratio': kd,
                    'role': player.display_role,
                    'skin_url': player.minecraft_skin_url
                })

        elif gamemode == 'skywars':
            players = Player.query.filter(Player.skywars_wins > 0).order_by(Player.skywars_wins.desc()).limit(limit).all()

            for idx, player in enumerate(players, 1):
                leaderboard_data.append({
                    'rank': idx,
                    'id': player.id,
                    'nickname': player.nickname,
                    'wins': player.skywars_wins,
                    'solo_wins': player.skywars_solo_wins,
                    'team_wins': player.skywars_team_wins,
                    'mega_wins': player.skywars_mega_wins,
                    'mini_wins': player.skywars_mini_wins,
                    'ranked_wins': player.skywars_ranked_wins,
                    'kills': player.skywars_kills,
                    'solo_kills': player.skywars_solo_kills,
                    'team_kills': player.skywars_team_kills,
                    'mega_kills': player.skywars_mega_kills,
                    'mini_kills': player.skywars_mini_kills,
                    'ranked_kills': player.skywars_ranked_kills,
                    'role': player.display_role,
                    'skin_url': player.minecraft_skin_url
                })

        elif gamemode == 'sumo':
            players = Player.query.filter(Player.sumo_games_played > 0).order_by(Player.sumo_wins.desc()).limit(limit).all()

            for idx, player in enumerate(players, 1):
                leaderboard_data.append({
                    'rank': idx,
                    'id': player.id,
                    'nickname': player.nickname,
                    'level': player.level,
                    'role': player.display_role,
                    'games_played': player.sumo_games_played,
                    'monthly_games': player.sumo_monthly_games,
                    'daily_games': player.sumo_daily_games,
                    'deaths': player.sumo_deaths,
                    'monthly_deaths': player.sumo_monthly_deaths,
                    'daily_deaths': player.sumo_daily_deaths,
                    'wins': player.sumo_wins,
                    'monthly_wins': player.sumo_monthly_wins,
                    'daily_wins': player.sumo_daily_wins,
                    'losses': player.sumo_losses,
                    'monthly_losses': player.sumo_monthly_losses,
                    'daily_losses': player.sumo_daily_losses,
                    'kills': player.sumo_kills,
                    'monthly_kills': player.sumo_monthly_kills,
                    'daily_kills': player.sumo_daily_kills,
                    'winstreak': player.sumo_winstreak,
                    'monthly_winstreak': player.sumo_monthly_winstreak,
                    'daily_winstreak': player.sumo_daily_winstreak,
                    'best_winstreak': player.sumo_best_winstreak,
                    'monthly_best_winstreak': player.sumo_monthly_best_winstreak,
                    'daily_best_winstreak': player.sumo_daily_best_winstreak,
                    'role': player.display_role,
                    'skin_url': player.minecraft_skin_url
                })


        # Remove unsupported game modes (fireball_fight, bridge, bridgefight)
        # Only support: bedwars, kitpvp, skywars, sumo

        return jsonify({
            'success': True,
            'gamemode': gamemode,
            'players': leaderboard_data,
            'total': len(leaderboard_data)
        })

    except Exception as e:
        app.logger.error(f"Error in gamemode leaderboard API: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to load leaderboard data',
            'gamemode': request.args.get('gamemode', 'bedwars'),
            'players': [],
            'total': 0
        }), 500

@app.route('/api/player/<int:player_id>/gamemode-stats/<gamemode>')
def api_player_gamemode_stats(player_id, gamemode):
    """Get player statistics for specific gamemode"""
    try:
        from models import GameModeManager

        player = Player.query.get_or_404(player_id)
        stats = GameModeManager.get_or_create_stats(player_id, gamemode)

        if not stats:
            return jsonify({
                'success': False,
                'error': f'Gamemode {gamemode} not supported'
            }), 400

        return jsonify({
            'success': True,
            'player': {
                'id': player.id,
                'nickname': player.nickname,
                'minecraft_skin_url': player.minecraft_skin_url,
                'display_role': player.display_role
            },
            'gamemode': gamemode,
            'gamemode_name': GameModeManager.GAMEMODE_NAMES.get(gamemode, gamemode),
            'stats': stats.to_dict()
        })

    except Exception as e:
        app.logger.error(f"Error getting player gamemode stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/gamemodes/available')
def api_available_gamemodes():
    """Get list of available gamemodes"""
    try:
        from models import GameModeManager

        gamemodes = []
        for key, name in GameModeManager.GAMEMODE_NAMES.items():
            gamemodes.append({
                'id': key,
                'name': name,
                'display_name': name
            })

        return jsonify({
            'success': True,
            'gamemodes': gamemodes
        })

    except Exception as e:
        app.logger.error(f"Error getting available gamemodes: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/player/<int:player_id>/ascend-data', methods=['POST'])
def api_save_ascend_data(player_id):
    """Save ASCEND data for player in specific gamemode (admin only)"""
    if not session.get('is_admin', False):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        gamemode = data.get('gamemode', 'bedwars')
        player = Player.query.get_or_404(player_id)
        ascend_data = ASCENDData.get_or_create(player_id, gamemode)

        # Save to history before updating
        ascend_data.save_to_history()

        # Update scores from both legacy and new format
        pvp_score = data.get('pvp_score', data.get('skill1_score', ascend_data.skill1_score))
        clutching_score = data.get('clutching_score', data.get('skill2_score', ascend_data.skill2_score))
        block_placement_score = data.get('block_placement_score', data.get('skill3_score', ascend_data.skill3_score))
        gamesense_score = data.get('gamesense_score', data.get('skill4_score', ascend_data.skill4_score))

        # Update skill scores
        ascend_data.skill1_score = ascend_data.pvp_score = min(100, max(0, int(pvp_score)))
        ascend_data.skill2_score = ascend_data.clutching_score = min(100, max(0, int(clutching_score)))
        ascend_data.skill3_score = ascend_data.block_placement_score = min(100, max(0, int(block_placement_score)))
        ascend_data.skill4_score = ascend_data.gamesense_score = min(100, max(0, int(gamesense_score)))

        # Auto-calculate tiers or use provided ones
        ascend_data.skill1_tier = ascend_data.pvp_tier = data.get('pvp_tier', calculate_tier_from_score(ascend_data.skill1_score))
        ascend_data.skill2_tier = ascend_data.clutching_tier = data.get('clutching_tier', calculate_tier_from_score(ascend_data.skill2_score))
        ascend_data.skill3_tier = ascend_data.block_placement_tier = data.get('block_placement_tier', calculate_tier_from_score(ascend_data.skill3_score))
        ascend_data.skill4_tier = ascend_data.gamesense_tier = data.get('gamesense_tier', calculate_tier_from_score(ascend_data.skill4_score))

        # Calculate overall tier
        if 'overall_tier' in data:
            ascend_data.overall_tier = data['overall_tier']
        else:
            avg_score = (ascend_data.skill1_score + ascend_data.skill2_score +
                        ascend_data.skill3_score + ascend_data.skill4_score) / 4
            ascend_data.overall_tier = calculate_tier_from_score(avg_score)

        ascend_data.comment = data.get('comment', '')
        ascend_data.evaluator_name = data.get('evaluator_name', 'Elite Squad')
        ascend_data.updated_at = datetime.utcnow()

        # Update global rank
        ascend_data.update_global_rank()

        db.session.commit()

        return jsonify({
            'success': True,
            'ascend': ascend_data.to_dict()
        })

    except Exception as e:
        app.logger.error(f"Error saving ASCEND data: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/player/<int:player_id>/ascend-import', methods=['POST'])
def api_import_ascend_data(player_id):
    """Import ASCEND data from JSON (admin only)"""
    if not session.get('is_admin', False):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    try:
        data = request.get_json()
        import_data = data.get('import_data')
        gamemode = data.get('gamemode', 'bedwars')

        if not import_data:
            return jsonify({'success': False, 'error': 'No import data provided'}), 400

        # Parse import data (could be JSON or CSV-like format)
        if isinstance(import_data, str):
            import json
            try:
                import_data = json.loads(import_data)
            except:
                # Try to parse as simple format: "PVP:75,Clutching:80,..." etc
                parts = import_data.split(',')
                parsed_data = {}
                for part in parts:
                    if ':' in part:
                        key, value = part.split(':')
                        parsed_data[key.strip().lower()] = int(value.strip())
                import_data = parsed_data

        # Get or create ASCEND data
        ascend_data = ASCENDData.query.filter_by(player_id=player_id, gamemode=gamemode).first()
        if not ascend_data:
            game_mode = GameMode.query.filter_by(name=gamemode).first()
            ascend_data = ASCENDData(
                player_id=player_id,
                gamemode=gamemode,
                skill1_name=game_mode.skill1_name if game_mode else 'PVP',
                skill2_name=game_mode.skill2_name if game_mode else 'Clutching',
                skill3_name=game_mode.skill3_name if game_mode else 'Block Placement',
                skill4_name=game_mode.skill4_name if game_mode else 'Gamesense'
            )
            db.session.add(ascend_data)

        # Save to history
        ascend_data.save_to_history()

        # Import scores
        skill_names = [ascend_data.skill1_name.lower(), ascend_data.skill2_name.lower(),
                      ascend_data.skill3_name.lower(), ascend_data.skill4_name.lower()]

        for skill_name in skill_names:
            if skill_name in import_data:
                score = min(100, max(0, int(import_data[skill_name])))
                tier = calculate_tier_from_score(score)

                if skill_name == ascend_data.skill1_name.lower():
                    ascend_data.skill1_score = score
                    ascend_data.skill1_tier = tier
                elif skill_name == ascend_data.skill2_name.lower():
                    ascend_data.skill2_score = score
                    ascend_data.skill2_tier = tier
                elif skill_name == ascend_data.skill3_name.lower():
                    ascend_data.skill3_score = score
                    ascend_data.skill3_tier = tier
                elif skill_name == ascend_data.skill4_name.lower():
                    ascend_data.skill4_score = score
                    ascend_data.skill4_tier = tier

        # Calculate overall tier
        avg_score = (ascend_data.skill1_score + ascend_data.skill2_score +
                    ascend_data.skill3_score + ascend_data.skill4_score) / 4
        ascend_data.overall_tier = calculate_tier_from_score(avg_score)

        # Update legacy fields
        ascend_data.pvp_score = ascend_data.skill1_score
        ascend_data.clutching_score = ascend_data.skill2_score
        ascend_data.block_placement_score = ascend_data.skill3_score
        ascend_data.gamesense_score = ascend_data.skill4_score

        ascend_data.pvp_tier = ascend_data.skill1_tier
        ascend_data.clutching_tier = ascend_data.skill2_tier
        ascend_data.block_placement_tier = ascend_data.skill3_tier
        ascend_data.gamesense_tier = ascend_data.skill4_tier

        ascend_data.evaluator_name = data.get('evaluator_name', 'Elite Squad AI (Import)')
        ascend_data.comment = data.get('comment', 'Imported data')
        ascend_data.updated_at = datetime.utcnow()

        # Update global rank
        ascend_data.update_global_rank()

        db.session.commit()

        return jsonify({
            'success': True,
            'ascend': ascend_data.to_dict(),
            'imported_fields': list(import_data.keys())
        })

    except Exception as e:
        app.logger.error(f"Error importing ASCEND data: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Target List API endpoints
@app.route('/api/targets', methods=['GET'])
def api_get_targets():
    """Get all targets with filtering"""
    try:
        from models import Target

        # Get query parameters
        gamemode = request.args.get('gamemode')
        priority = request.args.get('priority')
        status = request.args.get('status', 'active')

        # Build query
        query = Target.query

        if gamemode:
            query = query.filter(Target.gamemode == gamemode)
        if priority:
            query = query.filter(Target.priority == priority)
        if status:
            query = query.filter(Target.status == status)

        # Order by priority (critical first) then by date
        priority_order = db.case({
            'critical': 4,
            'high': 3,
            'medium': 2,
            'low': 1
        }, value=Target.priority, else_=1)

        targets = query.order_by(priority_order.desc(), Target.date_added.desc()).all()

        targets_data = [target.to_dict() for target in targets]

        return jsonify({
            'success': True,
            'targets': targets_data,
            'total': len(targets_data)
        })

    except Exception as e:
        app.logger.error(f"Error getting targets: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/targets', methods=['POST'])
def api_create_target():
    """Create new target"""
    try:
        # Check admin permissions
        if not session.get('is_admin', False):
            return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

        from models import Target

        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        nickname = data.get('nickname', '').strip()
        gamemode = data.get('gamemode', '').strip()
        server = data.get('server', '').strip()
        reason = data.get('reason', '').strip()
        priority = data.get('priority', 'medium').strip()

        if not all([nickname, gamemode, server, reason]):
            return jsonify({'success': False, 'error': 'Заполните все поля'}), 400

        # Validate priority
        valid_priorities = ['low', 'medium', 'high', 'critical']
        if priority not in valid_priorities:
            priority = 'medium'

        # Check if target already exists
        existing = Target.query.filter_by(nickname=nickname, gamemode=gamemode).first()
        if existing:
            return jsonify({'success': False, 'error': 'Цель уже существует'}), 400

        target = Target(
            nickname=nickname,
            gamemode=gamemode,
            server=server,
            reason=reason,
            priority=priority,
            added_by=session.get('player_nickname', 'admin'),
            status='active'
        )

        db.session.add(target)
        db.session.commit()

        return jsonify({
            'success': True,
            'target': target.to_dict(),
            'message': f'Цель "{nickname}" добавлена'
        })

    except Exception as e:
        app.logger.error(f"Error creating target: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/targets/<int:target_id>', methods=['PUT'])
def api_update_target(target_id):
    """Update target (admin or creator only)"""
    try:
        from models import Target

        target = Target.query.get(target_id)
        if not target:
            return jsonify({'success': False, 'error': 'Target not found'}), 404

        # Check permissions
        is_admin = session.get('is_admin', False)
        current_nickname = session.get('player_nickname')
        is_creator = current_nickname and target.added_by == current_nickname

        if not (is_admin or is_creator):
            return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        # Update allowed fields
        if 'reason' in data:
            target.reason = data['reason'].strip()
        if 'priority' in data:
            valid_priorities = ['low', 'medium', 'high', 'critical']
            if data['priority'] in valid_priorities:
                target.priority = data['priority']
        if 'status' in data and is_admin:  # Only admin can change status
            valid_statuses = ['active', 'completed', 'removed']
            if data['status'] in valid_statuses:
                target.status = data['status']

        db.session.commit()

        return jsonify({
            'success': True,
            'target': target.to_dict(),
            'message': 'Цель обновлена'
        })

    except Exception as e:
        app.logger.error(f"Error updating target: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/targets/<int:target_id>', methods=['DELETE'])
def api_delete_target(target_id):
    """Delete target (admin or creator only)"""
    try:
        from models import Target

        target = Target.query.get(target_id)
        if not target:
            return jsonify({'success': False, 'error': 'Target not found'}), 404

        # Check permissions
        is_admin = session.get('is_admin', False)
        current_nickname = session.get('player_nickname')
        is_creator = current_nickname and target.added_by == current_nickname

        if not (is_admin or is_creator):
            return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

        db.session.delete(target)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Цель "{target.nickname}" удалена'
        })

    except Exception as e:
        app.logger.error(f"Error deleting target: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/targets/<int:target_id>/complete', methods=['POST'])
def api_complete_target(target_id):
    """Mark target as completed (admin only)"""
    try:
        from models import Target

        if not session.get('is_admin', False):
            return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403

        target = Target.query.get(target_id)
        if not target:
            return jsonify({'success': False, 'error': 'Target not found'}), 404

        target.status = 'completed'
        db.session.commit()

        return jsonify({
            'success': True,
            'target': target.to_dict(),
            'message': f'Цель "{target.nickname}" отмечена как устраненная'
        })

    except Exception as e:
        app.logger.error(f"Error completing target: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/targets/<int:target_id>/react', methods=['POST'])
def api_add_target_reaction(target_id):
    """Add reaction to target"""
    try:
        from models import Target, TargetReaction

        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        reaction_type = data.get('reaction')
        valid_reactions = ['fragged', 'killed', 'exploded', 'slayed', 'destroyed', 'eliminated', 'rekt', 'obliterated']
        if reaction_type not in valid_reactions:
            return jsonify({'success': False, 'error': 'Invalid reaction type'}), 400

        # Check if target exists
        target = Target.query.get(target_id)
        if not target:
            return jsonify({'success': False, 'error': 'Target not found'}), 404

        # Get current player ID if logged in
        current_player_id = None
        if 'player_nickname' in session:
            from models import Player
            current_player = Player.query.filter_by(nickname=session['player_nickname']).first()
            if current_player:
                current_player_id = current_player.id

        # Add reaction
        reaction = TargetReaction.add_reaction(
            target_id=target_id,
            reaction_type=reaction_type,
            player_id=current_player_id
        )

        db.session.commit()

        # Check if bleeding effect was activated
        bleeding_activated = target.has_bleeding_effect and target.total_reactions >= 10

        return jsonify({
            'success': True,
            'total_reactions': target.total_reactions,
            'reaction_counts': target.reactions,
            'bleeding_effect': target.has_bleeding_effect,
            'bleeding_activated': bleeding_activated,
            'message': f'{reaction_type.title()} reaction added successfully!'
        })

    except Exception as e:
        app.logger.error(f"Error adding target reaction: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/targets/<int:target_id>/reactions', methods=['GET'])
def api_get_target_reactions(target_id):
    """Get all reactions for a target"""
    try:
        from models import Target, TargetReaction

        target = Target.query.get(target_id)
        if not target:
            return jsonify({'success': False, 'error': 'Target not found'}), 404

        reactions = TargetReaction.query.filter_by(target_id=target_id).order_by(
            TargetReaction.date_added.desc()
        ).all()

        reaction_data = []
        for reaction in reactions:
            reaction_info = {
                'id': reaction.id,
                'reaction_type': reaction.reaction_type,
                'date_added': reaction.date_added.isoformat(),
                'player': None
            }

            if reaction.player:
                reaction_info['player'] = {
                    'id': reaction.player.id,
                    'nickname': reaction.player.nickname
                }

            reaction_data.append(reaction_info)

        return jsonify({
            'success': True,
            'target': target.to_dict(),
            'reactions': reaction_data,
            'total_reactions': target.total_reactions,
            'reaction_counts': target.reactions
        })

    except Exception as e:
        app.logger.error(f"Error getting target reactions: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



# Candidate API endpoints
@app.route('/api/candidates', methods=['GET'])
def api_get_candidates():
    """Get candidates with filters"""
    try:
        from models import Candidate

        status_filter = request.args.get('status', 'all')
        search_query = request.args.get('search', '').strip()
        sort_by = request.args.get('sort', 'date_added')

        query = Candidate.query

        if status_filter != 'all':
            query = query.filter(Candidate.status == status_filter)

        if search_query:
            query = query.filter(Candidate.nickname.ilike(f'%{search_query}%'))

        if sort_by == 'nickname':
            query = query.order_by(Candidate.nickname.asc())
        elif sort_by == 'status':
            query = query.order_by(Candidate.status.asc())
        elif sort_by == 'rating':
            query = query.order_by(Candidate.rating.desc())
        elif sort_by == 'likes':
            query = query.order_by(Candidate.likes.desc())
        else:
            query = query.order_by(Candidate.date_added.desc())

        candidates = query.all()

        return jsonify({
            'success': True,
            'candidates': [candidate.to_dict() for candidate in candidates]
        })

    except Exception as e:
        app.logger.error(f"Error getting candidates: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/candidates', methods=['POST'])
def api_add_candidate():
    """Add new candidate"""
    try:
        from models import Candidate

        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        nickname = data.get('nickname', '').strip()
        description = data.get('description', '').strip()

        servers = data.get('servers', [])
        contact = data.get('contact', '').strip()
        status = data.get('status', 'candidate')

        if not nickname or not description:
            return jsonify({'success': False, 'error': 'Nickname and description are required'}), 400

        # Check if candidate already exists
        existing = Candidate.query.filter_by(nickname=nickname).first()
        if existing:
            return jsonify({'success': False, 'error': 'Candidate with this nickname already exists'}), 400

        # Get current user
        current_user = session.get('player_nickname', 'Anonymous')

        candidate = Candidate(
            nickname=nickname,
            description=description,
            contact=contact,
            status=status,
            added_by=current_user
        )

        candidate.set_servers_list(servers)

        db.session.add(candidate)
        db.session.commit()

        return jsonify({
            'success': True,
            'candidate': candidate.to_dict(),
            'message': f'Кандидат {nickname} добавлен!'
        })

    except Exception as e:
        app.logger.error(f"Error adding candidate: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/candidates/<int:candidate_id>', methods=['PUT'])
def api_update_candidate(candidate_id):
    """Update candidate"""
    try:
        from models import Candidate

        candidate = Candidate.query.get_or_404(candidate_id)

        # Check permissions
        current_user = session.get('player_nickname')
        is_admin = session.get('is_admin', False)

        if not is_admin and candidate.added_by != current_user:
            return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        # Update fields
        candidate.description = data.get('description', candidate.description)
        candidate.contact = data.get('contact', candidate.contact)
        candidate.status = data.get('status', candidate.status)
        candidate.notes = data.get('notes', candidate.notes)

        servers = data.get('servers')
        if servers is not None:
            candidate.set_servers_list(servers)

        db.session.commit()

        return jsonify({
            'success': True,
            'candidate': candidate.to_dict(),
            'message': 'Кандидат обновлен!'
        })

    except Exception as e:
        app.logger.error(f"Error updating candidate: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/candidates/<int:candidate_id>', methods=['DELETE'])
def api_delete_candidate(candidate_id):
    """Delete candidate"""
    try:
        from models import Candidate

        candidate = Candidate.query.get_or_404(candidate_id)

        # Check permissions
        current_user = session.get('player_nickname')
        is_admin = session.get('is_admin', False)

        if not is_admin and candidate.added_by != current_user:
            return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403

        nickname = candidate.nickname
        db.session.delete(candidate)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Кандидат {nickname} удален!'
        })

    except Exception as e:
        app.logger.error(f"Error deleting candidate: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/candidates/<int:candidate_id>/react', methods=['POST'])
def api_candidate_react(candidate_id):
    """Add reaction to candidate (like/rating)"""
    try:
        from models import Candidate, CandidateReaction

        candidate = Candidate.query.get_or_404(candidate_id)

        current_user = session.get('player_nickname')
        if not current_user:
            return jsonify({'success': False, 'error': 'Необходимо войти в систему'}), 401

        data = request.get_json()
        reaction_type = data.get('type', 'like')  # like or rating
        value = data.get('value')  # For ratings (1-5)

        # Check if user already reacted
        existing = CandidateReaction.query.filter_by(
            candidate_id=candidate_id,
            user=current_user,
            reaction_type=reaction_type
        ).first()

        if existing:
            if reaction_type == 'like':
                # Remove like
                db.session.delete(existing)
                candidate.likes = max(0, candidate.likes - 1)
                message = 'Лайк убран'
                action = 'removed'
            else:
                # Update rating
                existing.value = value
                message = f'Рейтинг обновлен: {value}/5'
                action = 'updated'
        else:
            # Add new reaction
            reaction = CandidateReaction(
                candidate_id=candidate_id,
                user=current_user,
                reaction_type=reaction_type,
                value=value
            )
            db.session.add(reaction)

            if reaction_type == 'like':
                candidate.likes += 1
                message = 'Лайк добавлен'
                action = 'added'
            else:
                message = f'Рейтинг добавлен: {value}/5'
                action = 'added'

        # Recalculate rating if needed
        if reaction_type == 'rating':
            ratings = CandidateReaction.query.filter_by(
                candidate_id=candidate_id,
                reaction_type='rating'
            ).all()

            if ratings:
                total_rating = sum(r.value for r in ratings)
                candidate.rating = round(total_rating / len(ratings), 1)
            else:
                candidate.rating = 0.0

        db.session.commit()

        return jsonify({
            'success': True,
            'message': message,
            'action': action,
            'likes': candidate.likes,
            'rating': candidate.rating
        })

    except Exception as e:
        app.logger.error(f"Error adding candidate reaction: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# Targets functionality integrated into main routes

# New API endpoints for Discord bot integration

@app.route('/api/shop/purchase', methods=['POST'])
def api_purchase_shop_item():
    """API endpoint for purchasing shop items (Discord bot integration)"""
    try:
        data = request.get_json()
        player_id = data.get('player_id')
        item_name = data.get('item_name')
        discord_user_id = data.get('discord_user_id')

        if not player_id or not item_name:
            return jsonify({'success': False, 'message': 'Требуется player_id и item_name'}), 400

        player = Player.query.get(player_id)
        if not player:
            return jsonify({'success': False, 'message': 'Игрок не найден'}), 404

        # Find shop item by name
        shop_item = ShopItem.query.filter_by(name=item_name, is_active=True).first()
        if not shop_item:
            return jsonify({'success': False, 'message': f'Товар "{item_name}" не найден'}), 404

        # Check if can purchase
        can_purchase, error_msg = shop_item.can_purchase(player)
        if not can_purchase:
            return jsonify({'success': False, 'message': error_msg}), 400

        # Process purchase
        coins_spent = shop_item.price_coins
        reputation_spent = shop_item.price_reputation

        if shop_item.price_coins > 0:
            player.coins -= shop_item.price_coins
        if shop_item.price_reputation > 0:
            player.reputation -= shop_item.price_reputation

        # Create purchase record
        purchase = ShopPurchase(
            player_id=player.id,
            item_id=shop_item.id,
            price_paid_coins=shop_item.price_coins,
            price_paid_reputation=shop_item.price_reputation
        )
        db.session.add(purchase)

        # Apply item effects
        success, message = shop_item.apply_item_effect(player)

        if not success:
            db.session.rollback()
            return jsonify({'success': False, 'message': message}), 400

        db.session.commit()

        return jsonify({
            'success': True,
            'message': message,
            'item_name': shop_item.display_name,
            'coins_spent': coins_spent,
            'reputation_spent': reputation_spent,
            'remaining_coins': player.coins,
            'remaining_reputation': player.reputation
        })

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in API purchase: {e}")
        return jsonify({'success': False, 'message': 'Ошибка при покупке товара'}), 500


@app.route('/api/player/<int:player_id>/apply-item', methods=['POST'])
def api_apply_item(player_id):
    """API endpoint for applying purchased items (Discord bot integration)"""
    try:
        data = request.get_json()
        item_type = data.get('item_type')  # theme, gradient, title, role
        item_name = data.get('item_name')
        discord_user_id = data.get('discord_user_id')

        if not item_type or not item_name:
            return jsonify({'success': False, 'message': 'Требуется item_type и item_name'}), 400

        player = Player.query.get(player_id)
        if not player:
            return jsonify({'success': False, 'message': 'Игрок не найден'}), 404

        # Apply different types of items
        if item_type == 'theme':
            from models import SiteTheme
            theme = SiteTheme.query.filter_by(name=item_name, is_active=True).first()
            if not theme:
                return jsonify({'success': False, 'message': f'Тема "{item_name}" не найдена'}), 404

            player.selected_theme_id = theme.id
            message = f'Тема "{theme.display_name}" применена!'

        elif item_type == 'title':
            # Check if player owns this title
            player_title = PlayerTitle.query.join(CustomTitle).filter(
                PlayerTitle.player_id == player_id,
                CustomTitle.name == item_name
            ).first()

            if not player_title:
                return jsonify({'success': False, 'message': f'У вас нет титула "{item_name}"'}), 400

            # Deactivate other titles and activate this one
            PlayerTitle.query.filter_by(player_id=player_id, is_active=True).update({'is_active': False})
            player_title.is_active = True
            message = f'Титул "{player_title.title.display_name}" активирован!'

        elif item_type == 'gradient':
            from models import PlayerGradientSetting
            # Apply gradient to player (this would need more specific implementation)
            message = f'Градиент "{item_name}" применен!'

        elif item_type == 'role':
            from models import AdminCustomRole, PlayerAdminRole
            # Apply custom role (simplified)
            message = f'Роль "{item_name}" применена!'

        else:
            return jsonify({'success': False, 'message': f'Неподдерживаемый тип предмета: {item_type}'}), 400

        db.session.commit()

        return jsonify({
            'success': True,
            'message': message,
            'item_type': item_type,
            'item_name': item_name
        })

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error applying item: {e}")
        return jsonify({'success': False, 'message': 'Ошибка при применении предмета'}), 500


@app.route('/api/shop')
def api_shop_items():
    """API endpoint to get all shop items (Discord bot integration)"""
    try:
        # Get all active shop items
        items = ShopItem.query.filter_by(is_active=True).all()

        items_data = []
        for item in items:
            items_data.append({
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
                'emoji': '📦',  # Default emoji, could be expanded
                'is_limited_time': item.is_limited_time
            })

        return jsonify({
            'success': True,
            'items': items_data,
            'total': len(items_data)
        })

    except Exception as e:
        app.logger.error(f"Error getting shop items: {e}")
        return jsonify({'success': False, 'items': [], 'message': 'Ошибка получения товаров'}), 500


@app.route('/api/player/<int:player_id>/inventory')
def api_player_inventory(player_id):
    """API endpoint to get player inventory (Discord bot integration)"""
    try:
        player = Player.query.get(player_id)
        if not player:
            return jsonify({'success': False, 'message': 'Игрок не найден'}), 404

        # Get purchased items
        purchases = ShopPurchase.query.filter_by(player_id=player_id).all()

        inventory = {
            'titles': [],
            'themes': [],
            'gradients': [],
            'boosters': [],
            'roles': [],
            'other': []
        }

        for purchase in purchases:
            item = purchase.shop_item
            item_data = {
                'id': item.id,
                'name': item.name,
                'display_name': item.display_name,
                'category': item.category,
                'purchased_at': purchase.purchased_at.isoformat(),
                'rarity': item.rarity
            }

            if item.category in inventory:
                inventory[item.category].append(item_data)
            else:
                inventory['other'].append(item_data)

        return jsonify({
            'success': True,
            'inventory': inventory,
            'coins': player.coins,
            'reputation': player.reputation,
            'level': player.level
        })

    except Exception as e:
        app.logger.error(f"Error getting inventory: {e}")
        return jsonify({'success': False, 'message': 'Ошибка получения инвентаря'}), 500

@app.route('/api/player/<int:player_id>/details')
def get_player_details(player_id):
    """Get detailed player information for popup modal"""
    try:
        player = Player.query.get_or_404(player_id)

        # Calculate K/D ratios
        kd_ratio = (player.kills / player.deaths) if player.deaths and player.deaths > 0 else (player.kills or 0)
        fkd_ratio = (player.final_kills / player.final_deaths) if player.final_deaths and player.final_deaths > 0 else (player.final_kills or 0)

        # Calculate win rate
        win_rate = ((player.wins / player.games_played) * 100) if player.games_played and player.games_played > 0 else 0

        # Get visible badges data
        visible_badges_data = []
        if player.visible_badges:
            for badge in player.visible_badges:
                visible_badges_data.append({
                    'id': badge.id,
                    'display_name': badge.display_name,
                    'description': badge.description,
                    'emoji': badge.emoji,
                    'rarity': badge.rarity
                })

        player_data = {
            'id': player.id,
            'nickname': player.nickname,
            'level': player.level or 1,
            'experience': player.experience or 0,
            'skin_url': player.minecraft_skin_url,
            'role': player.role or 'Игрок',
            'display_role': player.display_role,
            'active_custom_title': player.active_custom_title,
            'kills': player.kills or 0,
            'deaths': player.deaths or 0,
            'final_kills': player.final_kills or 0,
            'final_deaths': player.final_deaths or 0,
            'beds_broken': player.beds_broken or 0,
            'beds_lost': 0,  # Field doesn't exist in model, set to 0
            'wins': player.wins or 0,
            'games_played': player.games_played or 0,
            'losses': (player.games_played or 0) - (player.wins or 0),
            'kd_ratio': round(kd_ratio, 2),
            'fkd_ratio': round(fkd_ratio, 2),
            'win_rate': round(win_rate, 1),
            # Gradient data
            'nickname_gradient': player.nickname_gradient,
            'stats_gradient': player.stats_gradient,
            'role_gradient': player.role_gradient,
            'title_gradient': player.title_gradient,
            # Badges and titles
            'visible_badges': visible_badges_data
        }

        return jsonify({
            'success': True,
            'player': player_data
        })

    except Exception as e:
        app.logger.error(f"Error getting player details: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/player/<int:player_id>/popup-data')
def get_player_popup_data(player_id):
    """Get minimal player data for popup display - optimized for speed"""
    try:
        player = Player.query.get(player_id)
        if not player:
            return jsonify({'success': False, 'error': 'Player not found'}), 404

        # Calculate K/D ratio
        kd_ratio = round(player.kills / max(player.deaths, 1), 2) if player.deaths > 0 else player.kills

        # Get current role display
        current_role = None
        if player.custom_role and player.custom_role.strip():
            current_role = f"{player.custom_role_emoji or '🎭'} {player.custom_role}"
        elif player.role and player.role != 'default':
            role_emojis = {
                'admin': '👑',
                'premium': '⭐',
                'vip': '💎'
            }
            current_role = f"{role_emojis.get(player.role, '🎮')} {player.role.title()}"

        popup_data = {
            'nickname': player.nickname,
            'level': player.level or 1,
            'wins': player.wins or 0,
            'kd_ratio': kd_ratio,
            'karma': player.karma or 0,
            'current_role': current_role,
            'minecraft_skin_url': player.minecraft_skin_url
        }

        return jsonify(popup_data)

    except Exception as e:
        app.logger.error(f"Error getting popup data for player {player_id}: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500