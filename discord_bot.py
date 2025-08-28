import discord
from discord.ext import commands, tasks
import asyncio
import aiohttp
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import json
import io
import base64

# Проверяем доступность Pillow для создания изображений
PIL_AVAILABLE = False
Image = None
ImageDraw = None
ImageFont = None

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    print("⚠️ Pillow не установлен. Функции создания изображений будут недоступны.")
    print("Установите Pillow командой: pip install Pillow")

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")
WEBSITE_URL = os.getenv("WEBSITE_URL", "http://localhost:5000")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не задан в .env файле")
if not CLIENT_ID:
    raise ValueError("❌ CLIENT_ID не задан в .env файле")
if not WEBSITE_URL:
    raise ValueError("❌ WEBSITE_URL не задан в .env файле")

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=['!', '/'], intents=intents, help_command=None)

async def fetch_json(session, url, description):
    try:
        async with session.get(url, timeout=10) as resp:
            if resp.status != 200:
                print(f"Ошибка {description}: HTTP {resp.status}")
                return None
            return await resp.json()
    except asyncio.TimeoutError:
        print(f"Ошибка {description}: таймаут запроса")
    except aiohttp.ClientError as e:
        print(f"Ошибка {description}: {e}")
    return None

def get_tier_color(tier):
    colors = {
        'S+': 0xff1744, 'S': 0xff5722,
        'A+': 0xff9800, 'A': 0xffc107,
        'B+': 0x4caf50, 'B': 0x2196f3,
        'C+': 0x9c27b0, 'C': 0x607d8b,
        'D': 0x795548
    }
    return colors.get(tier, 0x607d8b)

def get_skill_emojis(gamemode):
    emoji_maps = {
        'bedwars': ['⚔️', '🔥', '🧱', '🧠'],
        'kitpvp': ['🎯', '❤️', '🏃', '📏'],
        'skywars': ['🔍', '🧪', '⚫', '👊'],
        'bridgefight': ['✏️', '🌉', '🧠', '⚔️'],
        'sumo': ['🧠', '✋', '⚙️', '🏃'],
        'fireball_fight': ['🛡️', '🔥', '🧠', '⚔️'],
        'bridge': ['⏩', '🛡️', '🧠', '⚔️']
    }
    return emoji_maps.get(gamemode, ['⭐', '⭐', '⭐', '⭐'])

# Discord UI Components
class ASCENDView(discord.ui.View):
    def __init__(self, player_id, nickname, gamemode):
        super().__init__(timeout=300)
        self.player_id = player_id
        self.nickname = nickname
        self.gamemode = gamemode

    @discord.ui.button(label='Сменить режим', style=discord.ButtonStyle.primary, emoji='🎮')
    async def change_gamemode(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Simple gamemode rotation
        gamemodes = ['bedwars', 'kitpvp', 'skywars', 'bridgefight']
        current_index = gamemodes.index(self.gamemode) if self.gamemode in gamemodes else 0
        new_gamemode = gamemodes[(current_index + 1) % len(gamemodes)]
        
        await interaction.response.send_message(f"🔄 Переключаю на {new_gamemode}...", ephemeral=True)
        
        # Re-run ascend command with new gamemode
        try:
            async with aiohttp.ClientSession() as session:
                ascend_data = await fetch_json(session, f"{WEBSITE_URL}/api/player/{self.player_id}/ascend-data?gamemode={new_gamemode}", "получения ASCEND данных")
                if ascend_data and ascend_data.get('success'):
                    # Update the view
                    self.gamemode = new_gamemode
                    await interaction.edit_original_response(content=f"✅ Режим изменен на {new_gamemode}", view=self)
        except Exception as e:
            await interaction.edit_original_response(content="❌ Ошибка при смене режима")

class QuestReviewView(discord.ui.View):
    def __init__(self, user_id, quest_name):
        super().__init__(timeout=3600)  # 1 hour timeout
        self.user_id = user_id
        self.quest_name = quest_name

    @discord.ui.button(label='Одобрить', style=discord.ButtonStyle.success, emoji='✅')
    async def approve_quest(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"✅ Квест **{self.quest_name}** одобрен для пользователя <@{self.user_id}>")
        self.clear_items()
        await interaction.edit_original_response(view=self)

    @discord.ui.button(label='Отклонить', style=discord.ButtonStyle.danger, emoji='❌')
    async def reject_quest(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"❌ Квест **{self.quest_name}** отклонен для пользователя <@{self.user_id}>")
        self.clear_items()
        await interaction.edit_original_response(view=self)

class EmbedBuilderModal(discord.ui.Modal, title="🎨 Создать красивое сообщение"):
    def __init__(self):
        super().__init__()

    title_input = discord.ui.TextInput(
        label="Заголовок",
        placeholder="Введите заголовок сообщения...",
        max_length=256,
        required=True
    )
    
    description_input = discord.ui.TextInput(
        label="Описание",
        placeholder="Основной текст сообщения...",
        style=discord.TextStyle.paragraph,
        max_length=4000,
        required=True
    )
    
    color_input = discord.ui.TextInput(
        label="Цвет (hex или название)",
        placeholder="например: #ff0000, red, 0xff0000",
        max_length=20,
        required=False,
        default="#3498db"
    )
    
    footer_input = discord.ui.TextInput(
        label="Подпись внизу",
        placeholder="Текст внизу сообщения (необязательно)...",
        max_length=2048,
        required=False
    )
    
    image_url_input = discord.ui.TextInput(
        label="URL изображения",
        placeholder="https://example.com/image.png (необязательно)",
        max_length=2048,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Парсинг цвета
            color_value = 0x3498db  # По умолчанию синий
            if self.color_input.value:
                color_str = self.color_input.value.strip()
                try:
                    # Hex цвет с #
                    if color_str.startswith('#'):
                        color_value = int(color_str[1:], 16)
                    # Hex цвет с 0x
                    elif color_str.startswith('0x'):
                        color_value = int(color_str, 16)
                    # Именованные цвета
                    elif color_str.lower() in ['red', 'красный']:
                        color_value = 0xff0000
                    elif color_str.lower() in ['green', 'зеленый']:
                        color_value = 0x00ff00
                    elif color_str.lower() in ['blue', 'синий']:
                        color_value = 0x0000ff
                    elif color_str.lower() in ['yellow', 'желтый']:
                        color_value = 0xffff00
                    elif color_str.lower() in ['purple', 'фиолетовый']:
                        color_value = 0x8b4fa5
                    else:
                        # Попытка интерпретировать как hex без префикса
                        color_value = int(color_str, 16)
                except ValueError:
                    # Если не удалось распарсить, используем цвет по умолчанию
                    color_value = 0x3498db

            # Создание embed
            embed = discord.Embed(
                title=self.title_input.value,
                description=self.description_input.value,
                color=color_value,
                timestamp=datetime.utcnow()
            )

            if self.footer_input.value:
                embed.set_footer(text=self.footer_input.value)

            if self.image_url_input.value:
                try:
                    embed.set_image(url=self.image_url_input.value)
                except:
                    pass  # Игнорируем ошибки с изображениями

            embed.set_author(name=f"Создано: {interaction.user.display_name}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)

            # Показать предпросмотр с кнопками
            view = EmbedActionView(embed)
            await interaction.response.send_message("✨ Embed создан! Выберите действие:", embed=embed, view=view, ephemeral=True)

        except Exception as e:
            print(f"Ошибка в EmbedBuilderModal: {e}")
            await interaction.response.send_message("❌ Произошла ошибка при создании сообщения", ephemeral=True)

class EmbedActionView(discord.ui.View):
    def __init__(self, embed):
        super().__init__(timeout=300)
        self.embed = embed

    @discord.ui.button(label='Отправить в этот канал', style=discord.ButtonStyle.success, emoji='📤')
    async def send_to_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_message("✅ Сообщение отправлено!", ephemeral=True)
            await interaction.followup.send(embed=self.embed)
        except Exception as e:
            await interaction.response.send_message("❌ Ошибка при отправке сообщения", ephemeral=True)

    @discord.ui.button(label='Редактировать', style=discord.ButtonStyle.secondary, emoji='✏️')
    async def edit_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Повторно открыть модальное окно с текущими значениями
        modal = EmbedBuilderModal()
        modal.title_input.default = self.embed.title
        modal.description_input.default = self.embed.description
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Отмена', style=discord.ButtonStyle.danger, emoji='❌')
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Создание embed отменено", embed=None, view=None)

@bot.event
async def on_ready():
    print(f'{bot.user} подключен к Discord!')
    if bot.user:
        print(f'Bot ID: {bot.user.id}')
    await bot.change_presence(activity=discord.Game(name="Elite Squad ASCEND | /help"))

    # Start background tasks
    leaderboard_update.start()
    karma_monitor.start()
    auto_role_update.start()  # Запуск автоматического обновления ролей

    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"Синхронизировано {len(synced)} slash-команд")
    except Exception as e:
        print(f"Ошибка синхронизации команд: {e}")

@tasks.loop(hours=1)
async def leaderboard_update():
    """Update bot status with current leaderboard info"""
    try:
        async with aiohttp.ClientSession() as session:
            stats = await fetch_json(session, f"{WEBSITE_URL}/api/stats", "получения статистики")
            if stats and stats.get('total_players'):
                activity = discord.Game(name=f"Elite Squad | {stats['total_players']} игроков")
                await bot.change_presence(activity=activity)
    except Exception as e:
        print(f"Ошибка обновления статуса: {e}")

@tasks.loop(minutes=30)
async def karma_monitor():
    """Monitor players with low karma and send warnings"""
    try:
        async with aiohttp.ClientSession() as session:
            # Get players with low karma (< 20)
            players = await fetch_json(session, f"{WEBSITE_URL}/api/leaderboard?sort=reputation&limit=100", "получения игроков")
            if players and players.get('players'):
                low_karma_players = [p for p in players['players'] if p.get('reputation', 0) < 20]

                if low_karma_players:
                    # Find main guild and general channel
                    for guild in bot.guilds:
                        general = discord.utils.get(guild.text_channels, name='general') or \
                                 discord.utils.get(guild.text_channels, name='main') or \
                                 discord.utils.get(guild.text_channels, name='chat') or \
                                 (guild.text_channels[0] if guild.text_channels else None)
                        if general and hasattr(general, 'send'):
                            embed = discord.Embed(
                                title="⚠️ Мониторинг кармы",
                                description=f"Найдено {len(low_karma_players)} игроков с низкой кармой",
                                color=0xff6b6b,
                                timestamp=datetime.utcnow()
                            )

                            karma_list = []
                            for player in low_karma_players[:5]:
                                karma_list.append(f"**{player['nickname']}** - Карма: {player.get('reputation', 0)}")

                            embed.add_field(name="Игроки с низкой кармой:", value="\n".join(karma_list), inline=False)
                            embed.add_field(name="Последствия низкой кармы:",
                                          value="• Ограничения в чате\n• Снижение дропа ресурсов\n• Ограничение участия в турнирах",
                                          inline=False)

                            await general.send(embed=embed)
                        break
    except Exception as e:
        print(f"Ошибка мониторинга кармы: {e}")

@leaderboard_update.before_loop
async def before_leaderboard_update():
    await bot.wait_until_ready()

@karma_monitor.before_loop
async def before_karma_monitor():
    await bot.wait_until_ready()

# Bot Commands
@bot.tree.command(name="ascend", description="Показать ASCEND карточку игрока с изображением")
async def ascend_card(interaction: discord.Interaction, nickname: str, gamemode: str = "bedwars", visual: bool = False):
    try:
        await interaction.response.defer()

        async with aiohttp.ClientSession() as session:
            data = await fetch_json(session, f"{WEBSITE_URL}/api/search?q={nickname}", "поиска игрока")
            if not data or not data.get('players'):
                await interaction.followup.send(f"❌ Игрок `{nickname}` не найден", ephemeral=True)
                return

            player = data['players'][0]
            player_id = player['id']

            ascend_data = await fetch_json(session, f"{WEBSITE_URL}/api/player/{player_id}/ascend-data?gamemode={gamemode}", "получения ASCEND данных")
            if not ascend_data or not ascend_data.get('success'):
                await interaction.followup.send("❌ ASCEND данные недоступны", ephemeral=True)
                return

            ascend = ascend_data['ascend']

        embed = discord.Embed(
            title="🎮 ASCEND Performance Card",
            description=f"**{player['nickname']}** | Уровень {player['level']} | {gamemode.title()}",
            color=get_tier_color(ascend['overall_tier']),
            timestamp=datetime.utcnow()
        )

        # Use dynamic skill names
        skill_emojis = get_skill_emojis(gamemode)
        skills = [
            (ascend.get('skill1_name', 'PVP'), ascend.get('skill1_tier', 'D'), ascend.get('skill1_score', 25)),
            (ascend.get('skill2_name', 'Clutching'), ascend.get('skill2_tier', 'D'), ascend.get('skill2_score', 25)),
            (ascend.get('skill3_name', 'Block Placement'), ascend.get('skill3_tier', 'D'), ascend.get('skill3_score', 25)),
            (ascend.get('skill4_name', 'Gamesense'), ascend.get('skill4_tier', 'D'), ascend.get('skill4_score', 25))
        ]

        for i, (name, tier, score) in enumerate(skills):
            emoji = skill_emojis[i] if i < len(skill_emojis) else "⭐"
            embed.add_field(name=f"{emoji} {name}", value=f"**{tier}** ({score}/100)", inline=True)

        embed.add_field(name="👑 Overall", value=f"**{ascend['overall_tier']}** TIER", inline=True)

        avg_score = sum(skill[2] for skill in skills) / 4
        embed.add_field(name="📊 Средняя оценка", value=f"**{avg_score:.1f}/100**", inline=True)

        if ascend.get('global_rank'):
            embed.add_field(name="🌍 Глобальный ранг", value=f"**#{ascend['global_rank']}**", inline=True)

        if ascend.get('comment'):
            embed.add_field(name="💬 Оценка эксперта", value=f"*{ascend['comment'][:1000]}*", inline=False)

        embed.set_thumbnail(url=f"https://mc-heads.net/avatar/{player['nickname']}/100")
        embed.set_footer(text=f"Оценщик: {ascend.get('evaluator_name', 'Elite Squad')} | Elite Squad ASCEND")

        view = ASCENDView(player_id, player['nickname'], gamemode)
        await interaction.followup.send(embed=embed, view=view)

    except Exception as e:
        print(f"Ошибка в команде ascend: {e}")
        await interaction.followup.send("❌ Произошла ошибка при получении данных", ephemeral=True)

@bot.tree.command(name="help", description="Показать список команд")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Команды Elite Squad Bot v3.0",
        description="Все доступные команды бота с новыми функциями",
        color=0x9b59b6,
        timestamp=datetime.utcnow()
    )

    embed.add_field(
        name="🎮 Игровые команды",
        value="""
        `/ascend <nickname> [gamemode] [visual]` - ASCEND карточка
        `/player <nickname>` - Статистика игрока
        `/stats` - Статистика сервера
        """,
        inline=False
    )

    embed.add_field(
        name="💜 Система кармы",
        value="""
        `/karma [nickname]` - Информация о карме
        """,
        inline=False
    )

    embed.add_field(
        name="🛒 Магазин и инвентарь",
        value="""
        `/shop [category]` - Просмотр магазина
        `/buy <item_name> [nickname]` - Купить товар
        `/inventory <nickname>` - Инвентарь игрока
        `/apply <type> <name> [nickname]` - Применить предмет
        """,
        inline=False
    )

    embed.add_field(
        name="📜 Квесты",
        value="""
        `/quests <nickname>` - Квесты игрока
        `/submit_quest <name> [screenshot]` - Отправить на проверку
        """,
        inline=False
    )
    
    embed.add_field(
        name="🎨 Утилиты",
        value="""
        `/embed` - Создать красивое сообщение
        """,
        inline=False
    )
    
    embed.add_field(
        name="🏆 Система ролей",
        value="""
        `/check_stats <nickname>` - Проверить роли игрока
        `/update_roles <nickname>` - Обновить роли (админ)
        """,
        inline=False
    )

    embed.add_field(name="🎮 Режимы игры для ASCEND",
                   value="bedwars, kitpvp, skywars, bridgefight, sumo, fireball_fight, bridge", inline=False)
    embed.add_field(name="🔗 Сайт", value=f"[Открыть Elite Squad]({WEBSITE_URL})", inline=False)

    embed.set_footer(text="Elite Squad ASCEND Bot v3.0 | Полная интеграция!")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="karma", description="Показать информацию о карме игрока")
async def karma_info(interaction: discord.Interaction, nickname: str = ""):
    try:
        await interaction.response.defer()

        if not nickname or nickname == "":
            # Show general karma info
            embed = discord.Embed(
                title="🔮 Система кармы Elite Squad",
                description="Карма влияет на ваш игровой опыт",
                color=0x8b4fa5,
                timestamp=datetime.utcnow()
            )

            embed.add_field(
                name="💜 Преимущества высокой кармы (80+)",
                value="• Увеличенный дроп ресурсов\n• Доступ к эксклюзивным турнирам\n• Приоритет в очереди\n• Специальные роли в Discord",
                inline=False
            )

            embed.add_field(
                name="⚠️ Последствия низкой кармы (20-)",
                value="• Ограничения в чате\n• Снижение дропа ресурсов\n• Ограничение участия в турнирах\n• Автоматический мониторинг",
                inline=False
            )

            embed.add_field(
                name="📈 Как повысить карму",
                value="• Побеждайте в играх\n• Выполняйте квесты\n• Помогайте другим игрокам\n• Участвуйте в сообществе",
                inline=False
            )

            await interaction.followup.send(embed=embed)
            return

        async with aiohttp.ClientSession() as session:
            data = await fetch_json(session, f"{WEBSITE_URL}/api/search?q={nickname}", "поиска игрока")
            if not data or not data.get('players'):
                await interaction.followup.send(f"❌ Игрок `{nickname}` не найден", ephemeral=True)
                return

            player = data['players'][0]

        karma = player.get('reputation', 0)

        # Determine karma level and color
        if karma >= 80:
            level = "Высокая"
            color = 0x00ff00
            emoji = "💚"
        elif karma >= 50:
            level = "Средняя"
            color = 0xffff00
            emoji = "💛"
        elif karma >= 20:
            level = "Низкая"
            color = 0xff8800
            emoji = "🧡"
        else:
            level = "Критическая"
            color = 0xff0000
            emoji = "💔"

        embed = discord.Embed(
            title=f"🔮 Карма игрока {player['nickname']}",
            color=color,
            timestamp=datetime.utcnow()
        )

        embed.add_field(name="💜 Текущая карма", value=f"**{karma}** {emoji}", inline=True)
        embed.add_field(name="📊 Уровень", value=f"**{level}**", inline=True)
        embed.add_field(name="⭐ Игровой уровень", value=f"**{player['level']}**", inline=True)

        if karma < 20:
            embed.add_field(
                name="⚠️ Предупреждение",
                value="У вас критически низкая карма! Это влияет на игровой опыт.",
                inline=False
            )

        embed.set_thumbnail(url=f"https://mc-heads.net/avatar/{player['nickname']}/100")
        embed.set_footer(text="Карма обновляется в реальном времени")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        print(f"Ошибка в команде karma: {e}")
        await interaction.followup.send("❌ Произошла ошибка при получении данных кармы", ephemeral=True)

@bot.tree.command(name="shop", description="Просмотреть магазин товаров")
async def shop_command(interaction: discord.Interaction, category: str = "all"):
    try:
        await interaction.response.defer()

        async with aiohttp.ClientSession() as session:
            # Get shop items
            shop_data = await fetch_json(session, f"{WEBSITE_URL}/api/shop", "получения товаров магазина")
            if not shop_data or not shop_data.get('items'):
                await interaction.followup.send("❌ Магазин временно недоступен", ephemeral=True)
                return

        items = shop_data['items']
        if category != "all":
            items = [item for item in items if item.get('category') == category]

        if not items:
            await interaction.followup.send(f"❌ Товары в категории `{category}` не найдены", ephemeral=True)
            return

        embed = discord.Embed(
            title="🛒 Магазин Elite Squad",
            description=f"Доступно товаров: {len(items)}",
            color=0x00ff00,
            timestamp=datetime.utcnow()
        )

        # Show first 10 items
        for item in items[:10]:
            price_text = ""
            if item.get('price_coins', 0) > 0:
                price_text += f"💰 {item['price_coins']:,} койнов"
            if item.get('price_reputation', 0) > 0:
                if price_text:
                    price_text += " | "
                price_text += f"💜 {item['price_reputation']} кармы"

            embed.add_field(
                name=f"{item.get('emoji', '📦')} {item['display_name']}",
                value=f"{item.get('description', 'Нет описания')}\n**Цена:** {price_text}",
                inline=True
            )

        embed.add_field(
            name="💡 Как купить",
            value=f"Используйте `/buy <название_товара>` или зайдите на сайт: {WEBSITE_URL}/shop",
            inline=False
        )

        embed.set_footer(text="Цены указаны в койнах и карме")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        print(f"Ошибка в команде shop: {e}")
        await interaction.followup.send("❌ Произошла ошибка при получении товаров", ephemeral=True)

@bot.tree.command(name="inventory", description="Просмотреть инвентарь игрока")
async def inventory_command(interaction: discord.Interaction, nickname: str):
    try:
        await interaction.response.defer()

        async with aiohttp.ClientSession() as session:
            data = await fetch_json(session, f"{WEBSITE_URL}/api/search?q={nickname}", "поиска игрока")
            if not data or not data.get('players'):
                await interaction.followup.send(f"❌ Игрок `{nickname}` не найден", ephemeral=True)
                return

            player = data['players'][0]
            player_id = player['id']

            # Get inventory data
            inventory_data = await fetch_json(session, f"{WEBSITE_URL}/api/player/{player_id}/inventory", "получения инвентаря")

        embed = discord.Embed(
            title=f"🎒 Инвентарь {player['nickname']}",
            color=0x3498db,
            timestamp=datetime.utcnow()
        )

        embed.add_field(name="💰 Койны", value=f"**{player.get('coins', 0):,}**", inline=True)
        embed.add_field(name="💜 Карма", value=f"**{player.get('reputation', 0)}**", inline=True)
        embed.add_field(name="⭐ Уровень", value=f"**{player['level']}**", inline=True)

        # Show inventory items if available
        if inventory_data and inventory_data.get('success'):
            inventory = inventory_data.get('inventory', {})

            for category, items in inventory.items():
                if items:
                    items_text = []
                    for item_id, quantity in items.items():
                        items_text.append(f"• ID {item_id}: x{quantity}")

                    embed.add_field(
                        name=f"📦 {category.title()}",
                        value="\n".join(items_text[:5]) + ("..." if len(items_text) > 5 else ""),
                        inline=True
                    )

        embed.set_thumbnail(url=f"https://mc-heads.net/avatar/{player['nickname']}/100")
        embed.set_footer(text="Обновлено в реальном времени")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        print(f"Ошибка в команде inventory: {e}")
        await interaction.followup.send("❌ Произошла ошибка при получении инвентаря", ephemeral=True)

@bot.tree.command(name="buy", description="Купить товар из магазина")
async def buy_command(interaction: discord.Interaction, item_name: str, player_nickname: str = ""):
    """Покупка товара из магазина через Discord бота"""
    try:
        await interaction.response.defer()
        
        # Если ник не указан, используем Discord username как fallback
        if not player_nickname:
            player_nickname = interaction.user.display_name
        
        async with aiohttp.ClientSession() as session:
            # Найти игрока
            player_data = await fetch_json(session, f"{WEBSITE_URL}/api/search?q={player_nickname}", "поиска игрока")
            if not player_data or not player_data.get('players'):
                await interaction.followup.send(f"❌ Игрок `{player_nickname}` не найден", ephemeral=True)
                return
            
            player = player_data['players'][0]
            player_id = player['id']
            
            # Попытка покупки
            purchase_response = await session.post(
                f"{WEBSITE_URL}/api/shop/purchase",
                json={
                    'player_id': player_id,
                    'item_name': item_name,
                    'discord_user_id': str(interaction.user.id)
                }
            )
            
            if purchase_response.status != 200:
                error_data = await purchase_response.json()
                await interaction.followup.send(f"❌ {error_data.get('message', 'Ошибка покупки')}", ephemeral=True)
                return
            
            result = await purchase_response.json()
            
        # Успешная покупка
        embed = discord.Embed(
            title="✅ Покупка успешна!",
            description=f"**{player['nickname']}** приобрел товар **{result.get('item_name', item_name)}**",
            color=0x00ff00,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="💰 Потрачено койнов", value=f"{result.get('coins_spent', 0):,}", inline=True)
        embed.add_field(name="💜 Потрачено кармы", value=f"{result.get('reputation_spent', 0)}", inline=True)
        embed.add_field(name="💡 Статус", value=result.get('message', 'Товар добавлен в инвентарь'), inline=False)
        
        embed.set_thumbnail(url=f"https://mc-heads.net/avatar/{player['nickname']}/100")
        embed.set_footer(text="Проверьте свой инвентарь на сайте или через /inventory")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        print(f"Ошибка в команде buy: {e}")
        await interaction.followup.send("❌ Произошла ошибка при покупке товара", ephemeral=True)

@bot.tree.command(name="embed", description="Создать и отправить красивое embed-сообщение")
async def embed_builder_command(interaction: discord.Interaction):
    """Интерактивный создатель embed-сообщений"""
    try:
        # Показать модальное окно для создания embed
        modal = EmbedBuilderModal()
        await interaction.response.send_modal(modal)
        
    except Exception as e:
        print(f"Ошибка в команде embed: {e}")
        await interaction.response.send_message("❌ Произошла ошибка при создании embed-builder", ephemeral=True)

# === DISCORD ROLE SYSTEM ===

# Роли Elite Squad основанные на статистике Bedwars
CLAN_ROLES = {
    # Клановые роли от низшей к высшей
    'Umi': {'min_kdr': 2.38, 'min_kills': 500, 'min_beds': 200, 'discord_role_name': '《FR》🇯🇵Umi 軍隊🍙'},
    'Asigaro': {'min_kdr': 2.34, 'min_kills': 1000, 'min_beds': 400, 'discord_role_name': '《FR》🇯🇵Asigaro 軍隊🍙'},
    'Yakuin': {'min_kdr': 2.2, 'min_kills': 1500, 'min_beds': 600, 'discord_role_name': '《FR》🇯🇵Yakuin 軍隊🍙'},
    'Ronin': {'min_kdr': 2.1, 'min_kills': 2000, 'min_beds': 800, 'discord_role_name': '《FR》🇯🇵Ronin 軍隊🍙'},
    'Samurai': {'min_kdr': 2.07, 'min_kills': 4000, 'min_beds': 1200, 'discord_role_name': '《FR》🇯🇵Samurai 軍隊🀄'},
    'Kirito': {'min_kdr': 2.0, 'min_kills': 5000, 'min_beds': 1500, 'discord_role_name': '《FR》🇯🇵Kirito 軍隊🀄'},
    'Gokenin': {'min_kdr': 1.97, 'min_kills': 6000, 'min_beds': 1800, 'discord_role_name': '《FR》🇯🇵Gokenin軍隊🎴'},
    'Hatamoto': {'min_kdr': 1.93, 'min_kills': 7000, 'min_beds': 2100, 'discord_role_name': '《FR》🇯🇵Hatamoto軍隊🎴'},
    'Semyo': {'min_kdr': 1.89, 'min_kills': 8000, 'min_beds': 2230, 'discord_role_name': '《FR》🇯🇵Semyo軍隊🎴'},
    'Sekio': {'min_kdr': 1.82, 'min_kills': 9900, 'min_beds': 2470, 'discord_role_name': '《FR》🇯🇵Sekio軍隊🎴'},
    'SengokuJidai': {'min_kdr': 1.79, 'min_kills': 10900, 'min_beds': 2540, 'discord_role_name': '《FR》🇯🇵Sengoku-Jidai軍隊🎴'},
    'Shugodaimy': {'min_kdr': 1.73, 'min_kills': 11900, 'min_beds': 2920, 'discord_role_name': '《FR》🇯🇵Shugo daimyō軍隊🎴'},
    'Daimyo': {'min_kdr': 1.7, 'min_kills': 12900, 'min_beds': 3260, 'discord_role_name': '《FR》🇯🇵Daimyo 将軍🎴'},
    'Tokygava': {'min_kdr': 1.68, 'min_kills': 13600, 'min_beds': 3960, 'discord_role_name': '《FR》🇯🇵Tokygava 将軍⛩'},
    'Eshin': {'min_kdr': 1.63, 'min_kills': 14200, 'min_beds': 4120, 'discord_role_name': '《FR》🇯🇵Eshin 将軍⛩'},
    'Shogun': {'min_kdr': 1.55, 'min_kills': 15555, 'min_beds': 4400, 'discord_role_name': '《FR》🇯🇵Shogun 将軍⛩'},
    'Tenno': {'min_kdr': 1.42, 'min_kills': 18200, 'min_beds': 4990, 'discord_role_name': '《FR》🇯🇵Tenno 将軍💯'},
    'Daisin': {'min_kdr': 1.37, 'min_kills': 20520, 'min_beds': 5320, 'discord_role_name': '《FR》🇯🇵Dai-sin 将軍🈴'},
    'Daiti': {'min_kdr': 1.26, 'min_kills': 21720, 'min_beds': 5840, 'discord_role_name': '《FR》🇯🇵Dai-ti 将軍🈴'},
    'Shogi': {'min_kdr': 1.21, 'min_kills': 22480, 'min_beds': 6000, 'discord_role_name': '《FR》🇯🇵Dai-gi 将軍🈲'},
    'Daigi': {'min_kdr': 1.13, 'min_kills': 23540, 'min_beds': 6100, 'discord_role_name': '《FR》🇯🇵Dai-gi 将軍🈲'},
    'Shoshin': {'min_kdr': 1.02, 'min_kills': 25000, 'min_beds': 6200, 'discord_role_name': '《FR》🇯🇵Sho-shin 将軍㊗'},
    'Daishin': {'min_kdr': 0.93, 'min_kills': 28730, 'min_beds': 7600, 'discord_role_name': '《FR》🇯🇵Dai-shin 将軍㊗'},
    'Shorai': {'min_kdr': 0.87, 'min_kills': 31185, 'min_beds': 10500, 'discord_role_name': '《FR》🇯🇵Sho-rai 将軍㊙'},
    'Dairai': {'min_kdr': 0.85, 'min_kills': 38700, 'min_beds': 13700, 'discord_role_name': '《FR》🇯🇵Dai-rai 将軍㊙'},
    'Shonin': {'min_kdr': 0.8, 'min_kills': 51300, 'min_beds': 26950, 'discord_role_name': '《FR》🇯🇵Sho-nin 将軍🉐'},
    'Dainin': {'min_kdr': 0.79, 'min_kills': 56000, 'min_beds': 28700, 'discord_role_name': '《FR》🇯🇵Dai-nin 将軍🉐'},
    'Shotoku': {'min_kdr': 0.76, 'min_kills': 81500, 'min_beds': 40000, 'discord_role_name': '《FR》🇯🇵Sho-toku 将軍🈹'},
    'Daitoku': {'min_kdr': 0.74, 'min_kills': 85000, 'min_beds': 43000, 'discord_role_name': '《FR》🇯🇵Dai-toku 将軍🈹'},
    'Hattori': {'min_kdr': 0.57, 'min_kills': 100000, 'min_beds': 50000, 'discord_role_name': '《FR》🇯🇵HATTORI 将軍🐱‍👤'}
}

# Престижные роли
PRESTIGE_ROLES = {
    'ClanCore': {'condition': 'clan_member_since', 'value': '2021-08-08', 'discord_role_name': '«💦» Истинная Единица'},
    'Diamond': {'condition': 'special_recognition', 'discord_role_name': '«💎» Неогранённый Алмаз'},
    'Murderous': {'condition': 'total_kills', 'value': 40000, 'discord_role_name': '«🗡» Потрашитель'},
    'Unstoppable': {'condition': 'low_hp_final_kill', 'discord_role_name': '«🗻» Несокрушимый'},
    'TechnoCool': {'condition': 'moonwalk_blocks', 'value': 32, 'discord_role_name': '«👟» Техно-Денсер'},
    'MonstaX': {'condition': 'kills_per_game', 'value': 120, 'discord_role_name': '«⚔» 𝙼𝙾𝙽𝚂𝚃𝙰 𝚇'},
    'Mindless': {'condition': 'no_emeralds_wins', 'value': 15, 'discord_role_name': '«🗿» Без рассудка'},
    'Striker': {'condition': 'fireball_only_win', 'discord_role_name': '«⛑» Страйкер'}
}

def determine_clan_role(player_stats):
    """Определить клановую роль игрока по статистике"""
    kdr = player_stats.get('kd_ratio', 0)
    kills = player_stats.get('kills', 0)
    beds = player_stats.get('beds_broken', 0)
    
    # Сортируем роли по приоритету (от высшей к низшей)
    sorted_roles = sorted(CLAN_ROLES.items(), key=lambda x: x[1]['min_kdr'], reverse=True)
    
    for role_name, requirements in sorted_roles:
        if (kdr >= requirements['min_kdr'] and 
            kills >= requirements['min_kills'] and 
            beds >= requirements['min_beds']):
            return {
                'role_name': role_name,
                'discord_role_name': requirements['discord_role_name'],
                'type': 'clan',
                'requirements': requirements
            }
    
    return None

def check_prestige_roles(player_stats):
    """Проверить престижные роли игрока"""
    earned_roles = []
    
    # Проверка роли Потрашитель
    total_kills = player_stats.get('kills', 0)
    if total_kills >= 40000:
        earned_roles.append({
            'role_name': 'Murderous',
            'discord_role_name': '«🗡» Потрашитель',
            'type': 'prestige',
            'reason': f'40000+ убийств ({total_kills})'
        })
    
    # Другие престижные роли требуют специальной проверки
    # Их можно добавлять вручную через админские команды
    
    return earned_roles

def format_role_info(role_data, player_stats):
    """Форматировать информацию о роли для отображения"""
    if not role_data:
        return "❌ Роль не найдена по текущей статистике"
    
    kdr = player_stats.get('kd_ratio', 0)
    kills = player_stats.get('kills', 0)
    beds = player_stats.get('beds_broken', 0)
    
    info = f"**{role_data['discord_role_name']}**\n"
    info += f"📊 Текущая статистика:\n"
    info += f"• KDR: **{kdr}** (требуется: {role_data['requirements']['min_kdr']})\n"
    info += f"• Убийства: **{kills}** (требуется: {role_data['requirements']['min_kills']})\n"
    info += f"• Кровати: **{beds}** (требуется: {role_data['requirements']['min_beds']})\n"
    
    return info

async def assign_discord_role(guild, member, role_name):
    """Выдать Discord роль участнику сервера"""
    try:
        role = discord.utils.get(guild.roles, name=role_name)
        if role:
            if role not in member.roles:
                await member.add_roles(role)
                return f"✅ Роль {role_name} выдана!"
            else:
                return f"ℹ️ Роль {role_name} уже есть у пользователя"
        else:
            return f"❌ Роль {role_name} не найдена на сервере"
    except Exception as e:
        return f"❌ Ошибка при выдаче роли: {e}"

async def remove_discord_role(guild, member, role_name):
    """Удалить Discord роль у участника сервера"""
    try:
        role = discord.utils.get(guild.roles, name=role_name)
        if role and role in member.roles:
            await member.remove_roles(role)
            return f"✅ Роль {role_name} удалена!"
        return f"ℹ️ У пользователя нет роли {role_name}"
    except Exception as e:
        return f"❌ Ошибка при удалении роли: {e}"

# === НОВЫЕ КОМАНДЫ ===

@bot.tree.command(name="check_stats", description="Проверить статистику игрока и соответствующие роли")
async def check_stats_command(interaction: discord.Interaction, nickname: str):
    """Команда для проверки статистики игрока и определения ролей"""
    try:
        await interaction.response.defer()

        async with aiohttp.ClientSession() as session:
            # Поиск игрока
            data = await fetch_json(session, f"{WEBSITE_URL}/api/search?q={nickname}", "поиска игрока")
            if not data or not data.get('players'):
                await interaction.followup.send(f"❌ Игрок `{nickname}` не найден", ephemeral=True)
                return

            player = data['players'][0]

        # Определение клановой роли
        clan_role = determine_clan_role(player)
        prestige_roles = check_prestige_roles(player)

        # Создание embed
        embed = discord.Embed(
            title=f"📊 Статистика и роли: {player['nickname']}",
            color=0x9b59b6,
            timestamp=datetime.utcnow()
        )

        # Основная статистика
        embed.add_field(
            name="🎯 Основная статистика",
            value=f"**KDR:** {player.get('kd_ratio', 0)}\n"
                  f"**Убийства:** {player.get('kills', 0):,}\n"
                  f"**Смерти:** {player.get('deaths', 0):,}\n"
                  f"**Кровати:** {player.get('beds_broken', 0):,}\n"
                  f"**Уровень:** {player.get('level', 1)}",
            inline=True
        )

        # Клановая роль
        if clan_role:
            embed.add_field(
                name="👑 Клановая роль",
                value=format_role_info(clan_role, player),
                inline=False
            )
        else:
            # Найти ближайшую роль
            sorted_roles = sorted(CLAN_ROLES.items(), key=lambda x: x[1]['min_kdr'])
            next_role = None
            for role_name, requirements in sorted_roles:
                if (player.get('kd_ratio', 0) < requirements['min_kdr'] or 
                    player.get('kills', 0) < requirements['min_kills'] or 
                    player.get('beds_broken', 0) < requirements['min_beds']):
                    next_role = (role_name, requirements)
                    break
            
            if next_role:
                role_name, req = next_role
                missing_kdr = max(0, req['min_kdr'] - player.get('kd_ratio', 0))
                missing_kills = max(0, req['min_kills'] - player.get('kills', 0))
                missing_beds = max(0, req['min_beds'] - player.get('beds_broken', 0))
                
                embed.add_field(
                    name="⬆️ Следующая роль",
                    value=f"**{req['discord_role_name']}**\n"
                          f"Нужно еще:\n"
                          f"• KDR: +{missing_kdr:.2f}\n"
                          f"• Убийства: +{missing_kills:,}\n"
                          f"• Кровати: +{missing_beds:,}",
                    inline=False
                )

        # Престижные роли
        if prestige_roles:
            roles_text = "\n".join([f"• {role['discord_role_name']} - {role['reason']}" for role in prestige_roles])
            embed.add_field(
                name="⭐ Престижные роли",
                value=roles_text,
                inline=False
            )

        embed.set_thumbnail(url=f"https://mc-heads.net/avatar/{player['nickname']}/100")
        embed.set_footer(text="Elite Squad - Система ролей")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        print(f"Ошибка в команде check_stats: {e}")
        await interaction.followup.send("❌ Произошла ошибка при проверке статистики", ephemeral=True)

@bot.tree.command(name="update_roles", description="Обновить роли игрока согласно статистике (только для администраторов)")
async def update_roles_command(interaction: discord.Interaction, nickname: str, force: bool = False):
    """Команда для автоматического обновления ролей игрока"""
    try:
        # Проверка прав администратора
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ У вас нет прав для использования этой команды", ephemeral=True)
            return

        await interaction.response.defer()

        async with aiohttp.ClientSession() as session:
            # Поиск игрока
            data = await fetch_json(session, f"{WEBSITE_URL}/api/search?q={nickname}", "поиска игрока")
            if not data or not data.get('players'):
                await interaction.followup.send(f"❌ Игрок `{nickname}` не найден", ephemeral=True)
                return

            player = data['players'][0]

        # Поиск участника Discord по нику
        member = None
        for guild_member in interaction.guild.members:
            if guild_member.display_name.lower() == nickname.lower() or guild_member.name.lower() == nickname.lower():
                member = guild_member
                break

        if not member and not force:
            await interaction.followup.send(f"❌ Участник Discord с ником `{nickname}` не найден на сервере\nИспользуйте `force=True` для игнорирования", ephemeral=True)
            return

        # Определение ролей
        clan_role = determine_clan_role(player)
        prestige_roles = check_prestige_roles(player)

        result_messages = []

        # Обновление клановой роли
        if clan_role and member:
            # Удаление старых клановых ролей
            old_clan_roles = [role for role in member.roles if any(clan_name in role.name for clan_name in CLAN_ROLES.keys())]
            for old_role in old_clan_roles:
                result = await remove_discord_role(interaction.guild, member, old_role.name)
                result_messages.append(result)

            # Выдача новой роли
            result = await assign_discord_role(interaction.guild, member, clan_role['discord_role_name'])
            result_messages.append(result)

        # Выдача престижных ролей
        if prestige_roles and member:
            for prestige_role in prestige_roles:
                result = await assign_discord_role(interaction.guild, member, prestige_role['discord_role_name'])
                result_messages.append(result)

        # Создание отчета
        embed = discord.Embed(
            title=f"🔄 Обновление ролей: {player['nickname']}",
            color=0x00ff00 if member else 0xffaa00,
            timestamp=datetime.utcnow()
        )

        if clan_role:
            embed.add_field(
                name="👑 Новая клановая роль",
                value=clan_role['discord_role_name'],
                inline=False
            )

        if prestige_roles:
            roles_text = "\n".join([role['discord_role_name'] for role in prestige_roles])
            embed.add_field(
                name="⭐ Престижные роли",
                value=roles_text,
                inline=False
            )

        if result_messages:
            embed.add_field(
                name="📋 Результат обновления",
                value="\n".join(result_messages),
                inline=False
            )
        elif not member:
            embed.add_field(
                name="⚠️ Предупреждение",
                value="Участник Discord не найден - роли не обновлены",
                inline=False
            )

        embed.set_thumbnail(url=f"https://mc-heads.net/avatar/{player['nickname']}/100")
        embed.set_footer(text="Elite Squad - Автоматическое обновление ролей")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        print(f"Ошибка в команде update_roles: {e}")
        await interaction.followup.send("❌ Произошла ошибка при обновлении ролей", ephemeral=True)

# Добавляем периодическую задачу для автоматического обновления ролей
@tasks.loop(hours=6)  # Каждые 6 часов
async def auto_role_update():
    """Автоматическое обновление ролей топ игроков"""
    try:
        async with aiohttp.ClientSession() as session:
            # Получаем топ-50 игроков
            leaderboard = await fetch_json(session, f"{WEBSITE_URL}/api/leaderboard?sort=experience&limit=50", "получения лидерборда")
            if not leaderboard or not leaderboard.get('players'):
                return

            print("🔄 Начинаем автоматическое обновление ролей...")
            updated_count = 0

            for guild in bot.guilds:
                for player in leaderboard['players']:
                    # Поиск участника Discord
                    member = None
                    for guild_member in guild.members:
                        if (guild_member.display_name.lower() == player['nickname'].lower() or 
                            guild_member.name.lower() == player['nickname'].lower()):
                            member = guild_member
                            break

                    if not member:
                        continue

                    # Определение ролей
                    clan_role = determine_clan_role(player)
                    if not clan_role:
                        continue

                    # Проверка, есть ли уже правильная роль
                    has_correct_role = any(clan_role['discord_role_name'] == role.name for role in member.roles)
                    if has_correct_role:
                        continue

                    # Удаление старых клановых ролей
                    old_clan_roles = [role for role in member.roles if any(clan_name in role.name for clan_name in CLAN_ROLES.keys())]
                    for old_role in old_clan_roles:
                        await remove_discord_role(guild, member, old_role.name)

                    # Выдача новой роли
                    result = await assign_discord_role(guild, member, clan_role['discord_role_name'])
                    if "✅" in result:
                        updated_count += 1
                        print(f"✅ Обновлена роль для {player['nickname']}: {clan_role['discord_role_name']}")

            print(f"🎉 Автоматическое обновление завершено! Обновлено ролей: {updated_count}")

    except Exception as e:
        print(f"Ошибка в автоматическом обновлении ролей: {e}")

@auto_role_update.before_loop
async def before_auto_role_update():
    await bot.wait_until_ready()

def run_bot():
    try:
        bot.run(BOT_TOKEN)
    except discord.errors.LoginFailure:
        print("❌ Ошибка: Неверный токен бота. Пожалуйста, проверьте ваш BOT_TOKEN в .env файле.")
    except Exception as e:
        print(f"❌ Произошла непредвиденная ошибка при запуске бота: {e}")

if __name__ == "__main__":
    run_bot()