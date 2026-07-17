# made by SoulLLC and updated by VOID, fuck yall niggas fr
import os
import re
import io
import json
import time
import base64
import asyncio
import random
import logging
import requests
import aiohttp
from io import BytesIO
from datetime import datetime, timedelta
from colorama import Fore, Style, init
import discord
from discord import User, Embed, Interaction, Permissions, AllowedMentions, ButtonStyle, app_commands
from discord.ext import commands
from discord.ui import Modal, TextInput, View, Button
from PIL import Image, ImageDraw, ImageFont, ImageOps

import requests

init(autoreset=True)

LOG_WEBHOOK_URL = "https://discord.com/api/webhooks/1514172325900058715/a90V-CLDX-ec3yFvovONbt6kemvN8DfDO9pm4IlTnpYtLmw8SkN3i_uCpRJh6Rfiiz6P" #for the webhook bs ik super cool
PREMIUM_FILE = "premium.json"
PRESETS_FILE = "presets.json"


IPLOGGER_API_KEY = "api_yR2NVE44HdrxKRrkerQHtLVya1JQM4lL" # only if u want to use iplogger command

class RateLimitFilter(logging.Filter):
    def filter(self, record):
        if "is rate limited" in record.getMessage():
            if not hasattr(record, "already_logged"):
                record.already_logged = True
            return False 
        return True  

logger = logging.getLogger("discord.webhook.async_")
logger.addFilter(RateLimitFilter())

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)
    
class CooldownManager:
    def __init__(self, cooldown_seconds: int):
        self.cooldown_seconds = cooldown_seconds
        self.user_timestamps = {}

    def can_use(self, user_id: int) -> (bool, int):
        now = time.time()
        last_time = self.user_timestamps.get(user_id, 0)
        elapsed = now - last_time
        if elapsed >= self.cooldown_seconds:
            self.user_timestamps[user_id] = now
            self.cleanup()
            return True, 0
        else:
            return False, int(self.cooldown_seconds - elapsed)

    def cleanup(self):
        now = time.time()
        to_delete = [user for user, ts in self.user_timestamps.items() if now - ts > self.cooldown_seconds]
        for user in to_delete:
            del self.user_timestamps[user]

cooldown_manager = CooldownManager(100)


def load_premium_users():
    if not os.path.exists(PREMIUM_FILE):
        return []
    with open(PREMIUM_FILE, "r") as f:
        return json.load(f)

def save_premium_users(user_ids):
    with open(PREMIUM_FILE, "w") as f:
        json.dump(user_ids, f, indent=2)

def add_premium_user(user_id: int):
    premium_users = load_premium_users()
    if user_id not in premium_users:
        premium_users.append(user_id)
        save_premium_users(premium_users)

def is_premium_user(user_id: int):
    premium_users = load_premium_users()
    return user_id in premium_users

def remove_premium_user(user_id: int) -> bool:
    premium_users = load_premium_users()
    if user_id in premium_users:
        premium_users.remove(user_id)
        save_premium_users(premium_users)
        return True
    return False

def update_leaderboard(user_id: int):
    leaderboard_file = "leaderboard.json"

    if not os.path.exists(leaderboard_file):
        with open(leaderboard_file, "w") as f:
            json.dump({}, f)

    with open(leaderboard_file, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {}

    user_id_str = str(user_id)

    if user_id_str in data:
        data[user_id_str] += 1
    else:
        data[user_id_str] = 1

    with open(leaderboard_file, "w") as f:
        json.dump(data, f, indent=4)


def update_leaderboard(user_id: int, command_name: str):
    leaderboard_file = "leaderboard.json"

    if not os.path.exists(leaderboard_file):
        with open(leaderboard_file, "w") as f:
            json.dump({}, f)

    with open(leaderboard_file, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {}

    user_id_str = str(user_id)

    if user_id_str not in data:
        data[user_id_str] = {
            "overall": 0
        }

    data[user_id_str]["overall"] += 1

    if command_name not in data[user_id_str]:
        data[user_id_str][command_name] = 1
    else:
        data[user_id_str][command_name] += 1

    with open(leaderboard_file, "w") as f:
        json.dump(data, f, indent=4)

def save_token(token):
    with open("config.json", "w") as file:
        json.dump({"TOKEN": token}, file)

def load_token():
    try:
        with open("config.json", "r") as file:
            data = json.load(file)
            return data.get("TOKEN")
    except FileNotFoundError:
        print(Fore.RED + "Error: 2 not found.")
        return None
    except json.JSONDecodeError:
        print(Fore.RED + "Error: Invalid JSON format in config.json.")
        return None

logo = f"""{Fore.MAGENTA}

  _________            .__   
 /   _____/ ____  __ __|  |  
 \_____  \ /  _ \|  |  \  |  
 /        (  <_> )  |  /  |__
/_______  /\____/|____/|____/
        \/                   
{Fore.WHITE}     raiding made easy                        
 
"""



def display_status(connected):
    if connected:
        print(Fore.GREEN + "Status: Connected")
    else:
        print(Fore.RED + "Status: Disconnected")

def token_management():
    os.system('cls' if os.name == 'nt' else 'clear') 
    print(Fore.CYAN + "Welcome to the bot token management!\n")
    print("1. Set new token")
    print("2. Load previous token")
    
    print()

    choice = input(f"{Fore.YELLOW}>{Fore.WHITE} Choose an option (1, 2){Fore.YELLOW}:{Fore.WHITE} ")

    if choice == "1":
        new_token = input(Fore.GREEN + "Enter the new token: ")
        save_token(new_token)
        print(Fore.GREEN + "Token successfully set!")
        return new_token
    elif choice == "2":
        token = load_token()
        if token:
            print(f"{Fore.GREEN}>{Fore.WHITE} Previous token loaded: {Fore.GREEN}{token}{Fore.WHITE}.")
            return token
        else:
            print(Fore.RED + "No token found.")
            return None
    else:
        print(Fore.RED + "Invalid choice. Please try again.")
        return None

async def log_command_use(
    user: discord.User,
    command_name: str,
    message: str = None,
    channel: discord.abc.Messageable = None
):
    user_display = f"{user.display_name} ({user.name}) [{user.id}]"

    fields = [
        {
            "name": "User",
            "value": user_display,
            "inline": True
        },
        {
            "name": "Command",
            "value": f"`{command_name}`",
            "inline": True
        },
        {
            "name": "Time",
            "value": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "inline": True
        }
    ]

    if channel:
        fields.append({
            "name": "Channel",
            "value": str(channel),
            "inline": True
        })

    if message:
        if command_name == "avatar":
            fields.append({
                "name": "Avatar Checked",
                "value": f"[Avatar Link]({message})",
                "inline": False
            })
        else:
            trimmed = message if len(message) <= 1024 else message[:1021] + "..."
            fields.append({
                "name": "Message Content",
                "value": trimmed,
                "inline": False
            })

    embed = {
        "title": "cmd exe'ed heres ur log loser",
        "color": 0xa874d1,
        "fields": fields,
        "author": {
            "name": user.display_name,
            "icon_url": user.display_avatar.url
        },
        "footer": {
            "text": "SoulLLC Logger",
            "icon_url": user._state._get_client().user.avatar.url
            if user._state._get_client().user.avatar
            else None
        }
    }

    if command_name == "avatar" and message:
        embed["thumbnail"] = {"url": message}

    webhook_data = {"embeds": [embed]}

    async with aiohttp.ClientSession() as session:
        async with session.post(LOG_WEBHOOK_URL, json=webhook_data) as resp:
            if resp.status != 204:
                print(f"Failed to send log webhook, status: {resp.status}")

intents = discord.Intents.default()
intents.messages = False  
intents.message_content = False  
intents.members = False  
intents.guilds = False  
intents.typing = False 
intents.presences = False  

bot = commands.Bot(command_prefix="!", intents=intents)


def load_presets():
    if not os.path.exists(PRESETS_FILE):
        return {}

    try:
        with open(PRESETS_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except json.JSONDecodeError:
        return {}

def save_preset(user_id, message):
    data = load_presets()
    data[str(user_id)] = message

    with open(PRESETS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def get_preset(user_id):
    data = load_presets()
    return data.get(str(user_id))

class PresetModal(Modal, title="set ur custom loser"):
    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id
        self.message_input = TextInput(label="enter ur spam msg weirdo", style=discord.TextStyle.long, max_length=2000)
        self.add_item(self.message_input)

    async def on_submit(self, interaction: Interaction):
        save_preset(self.user_id, self.message_input.value)
        await interaction.response.send_message("preset msg saved fucking bum", ephemeral=True)

class PresetView(View):
    def __init__(self, user_id: int):
        super().__init__(timeout=180)
        self.user_id = user_id

    @discord.ui.button(label="msg saved loser", style=ButtonStyle.green)
    async def set_message(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(PresetModal(user_id=self.user_id))

    @discord.ui.button(label="prev msg fucking loser", style=ButtonStyle.primary)
    async def preview_message(self, interaction: Interaction, button: Button):
        message = get_preset(self.user_id)
        if message:
            await interaction.response.send_message(f"📄 **ur preset msg fucking bum:**\n```{message}```", ephemeral=True)
        else:
            await interaction.response.send_message("theres no preset msg loser LOLLL", ephemeral=True)

@bot.tree.command(name="preset-message", description="Manage your custom raid message preset.")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def preset_message(interaction: discord.Interaction):
    if not is_premium_user(interaction.user.id):
        await interaction.response.send_message("stop being broke you fucking bum and pay for prem LOLLL", ephemeral=True)
        return
    view = PresetView(user_id=interaction.user.id)
    embed = discord.Embed(
        title="preset msg",
        description="uh use the buttons below to do whatchu need loser",
        color=0xa874d1
    )
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)



SPOOF_MAP = {
    "tiktok_video": "https//www.tiktok.com/@feri_azimi/video/1234567890",
    "tiktok_account": "https//www.tiktok.com/@feri_azimi",
    "instagram_video": "https//www.instagram.com/reel/DIMO87VJrik",
    "instagram_account": "https//www.instagram.com/feri_azimi/",
    "roblox_account": "https//www.roblox.com/users/3554077592/profile"
}

@bot.tree.command(
    name="makelogger",
    description="[prem] Create a redirect IPLogger shortlink (use for legal purposes only!)"
)
@app_commands.describe(
    domain="choose ur logger domain loser",
    destination="url redirect and if your fucking stupid (e.g., https://tiktok.com)",
    spoof_type="Choose how the link should appear"
)
@app_commands.choices(domain=[
    app_commands.Choice(name="ed.tc", value="ed.tc"),
    app_commands.Choice(name="wl.gl", value="wl.gl"),
    app_commands.Choice(name="bc.ax", value="bc.ax"),
])
@app_commands.choices(spoof_type=[
    app_commands.Choice(name="TikTok Video", value="tiktok_video"),
    app_commands.Choice(name="TikTok Account", value="tiktok_account"),
    app_commands.Choice(name="Instagram Video", value="instagram_video"),
    app_commands.Choice(name="Instagram Account", value="instagram_account"),
    app_commands.Choice(name="Roblox Account", value="roblox_account")
])
async def createlogger(
    interaction: discord.Interaction,
    domain: app_commands.Choice[str],
    destination: str,
    spoof_type: app_commands.Choice[str]
):
    await interaction.response.defer(ephemeral=True, thinking=True)

    if not is_premium_user(interaction.user.id):
        await interaction.response.send_message("stop being broke loser and fucking pay for premium god damn", ephemeral=True)
        return

    try:
        if not destination.startswith(("http://", "https://")):
            destination = "https://" + destination

        payload = {
            "domain": domain.value,
            "alias": "discord_logger",
            "destination": destination
        }

        endpoint = "https://api.iplogger.org/create/shortlink/"

        response = requests.post(
            endpoint,
            headers={"X-token": IPLOGGER_API_KEY},
            data=payload
        )
        data = response.json()

        if "result" in data:
            shortlink = data["result"].get("shortlink")
            direct_link = f"https://{data['result']['domain']}/{data['result']['link']}"
            viewer_link = f"https://iplogger.org/logger/{data['result']['id']}"

            spoof_base = SPOOF_MAP[spoof_type.value]
            spoofed_link_msg = f"[{spoof_base}]({shortlink})"

            details_msg = (
                f" **heres ur logger loser**\n"
                f" **pub link:** {shortlink}\n"
                f" **log link (share if your fucking STUPID ``dont share``):** {viewer_link}\n"
                f" **redirects to:** {payload['destination']}\n\n"
                f":exclamation: **Tip:** forward the logger link above to the victim. Copy and pasting will break the spoofed link or dont if your fucking stupid and cant read\n"
            )

            try:
                await interaction.user.send(spoofed_link_msg)
                await interaction.user.send(details_msg)

                await interaction.followup.send("check ur dms loser", ephemeral=True)

            except discord.Forbidden:
                await interaction.followup.send(
                    "open your dms before you try smth stupid dumbass",
                    ephemeral=True
                )

        else:
            await interaction.followup.send(f"api did NOT work g, make a ticket in the dc server: {data}", ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"api had a error , this is odd, make a ticket in the discord g: {e}", ephemeral=True)



class SpamButton(discord.ui.View):
    def __init__(self, message):
        super().__init__()
        self.message = message

    @discord.ui.button(label="Spam", style=discord.ButtonStyle.red)
    async def spam_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        allowed = discord.AllowedMentions(everyone=True, users=True, roles=True)
        for _ in range(5):  
            await interaction.followup.send(self.message, allowed_mentions=allowed)  

@bot.tree.command(name="custom-raid", description="[prem] premium raid with your own message")
@app_commands.describe(message="Optional: your custom message to spam (use /preset-message if you want to save it)")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def custom_raid(interaction: discord.Interaction, message: str = None):
    if not is_premium_user(interaction.user.id):
        await interaction.response.send_message("stop being fucking broke and pay the money dawg", ephemeral=True)
        return

    if not message:
        message = get_preset(interaction.user.id)
        if not message:
            await interaction.response.send_message("hm this is odd, i cant find a preset msg you dumbass nigga use `/preset-message` for this cmd to work dumbass", ephemeral=True)
            return

    view = SpamButton(message)
    await interaction.response.send_message(f"spam these bitch made ass niggas bro LMAFAOO:\n```{message}```", view=view, ephemeral=True)

    await log_command_use(
        user=interaction.user,
        command_name="💎 custom-raid",
        channel=interaction.channel,
        message=message
    )
    update_leaderboard(interaction.user.id, "custom-raid")




class PingButton(discord.ui.View):
    def __init__(self, user_ids: list[str], pings_per_message: int = 1):
        super().__init__(timeout=None)
        self.user_ids = user_ids
        self.pings_per_message = pings_per_message
        self.delay = 1

    @discord.ui.button(label="ping this nga LMFAO", style=discord.ButtonStyle.red)
    async def ping_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.user_ids:
            await interaction.response.send_message("hm this is odd, msg us or make a ticket in the soulllc server", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        max_retries = 2

        for _ in range(5):
            selected_ids = random.sample(self.user_ids, min(self.pings_per_message, len(self.user_ids)))
            mentions = " ".join(f"<@{uid}>" for uid in selected_ids)
            pingmsg = '''
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
                                  **Soul**   `🌙`
                  raid b__o__t  ﹒ s__o__cial  ﹒ to__xic__
                         `🌟`     _join to [RAID] any server __Without Admin perms__, free to use_ 💰 

⠀⠀⠀⠀⠀⠀⠀                            **[JOIN](https://discord.gg/C3zhSsTyPW) TODAY, AND R__AI__D EVER__Y__ SERVER YOU WANT WITHOUT [ADMIN](https://tenor.com/view/mooning-show-butt-shake-butt-pants-down-gif-17077775)**
            '''
            message_content = f"{mentions}\n{pingmsg}"
            retries = 0
            while retries <= max_retries:
                try:
                    await interaction.followup.send(message_content, ephemeral=False)
                    break
                except discord.errors.HTTPException as e:
                    if e.status == 429:
                        retry_after = getattr(e, "retry_after", 1.5)
                        retry_after = min(retry_after, 5)
                        print(f"rate limmed LOLLL {retry_after:.2f}s (retry {retries + 1}/{max_retries})")
                        await asyncio.sleep(retry_after)
                        retries += 1
                    else:
                        raise e
            else:
                print("hm seems like this shit faild LMFAOOO it didnt work so we skipping ts LMFAO ")


@bot.tree.command(name="ping", description="Ping random user IDs from a .txt file using a button.")
@app_commands.describe(
    file="A .txt file containing user IDs (one per line)",
    pings_per_message="amount of users to ping per message (most servs have a 5 ping limit, keep ts low g)"
)
@app_commands.rename(pings_per_message="amount")
async def ping_from_file(
    interaction: discord.Interaction,
    file: discord.Attachment,
    pings_per_message: int = 1
):

    try:
        if not file.filename.endswith(".txt"):
            await interaction.response.send_message("ts didnt work mb, its prolly not GONNA work sadly so thats on me mb bro.", ephemeral=True)
            return

        file_content = await file.read()
        text = file_content.decode("utf-8")
        user_ids = [line.strip() for line in text.splitlines() if line.strip().isdigit()]

        if not user_ids:
            await interaction.response.send_message("no REAL user is found in the file gng LMFAOOO.", ephemeral=True)
            return

        view = PingButton(user_ids, pings_per_message)
        await interaction.response.send_message("click ts to ping RANDOM niggas LMFAO", view=view, ephemeral=True)


    except Exception as e:
        if interaction.response.is_done():
            await interaction.followup.send(f"error nigga: `{e}`", ephemeral=True)
        else:
            await interaction.response.send_message(f"error again nigga LMFAO: `{e}`", ephemeral=True)




class AvatarView(discord.ui.View): # made that shit in 5min its really ass
    def __init__(self, user: discord.User, banner_url: str = None):
        super().__init__()
        avatar_url = user.display_avatar.url

        self.add_item(discord.ui.Button(label="Download Avatar as JPG", url=avatar_url + "?format=jpg"))
        self.add_item(discord.ui.Button(label="Download Avatar as PNG", url=avatar_url + "?format=png"))

        if banner_url:
            self.add_item(discord.ui.Button(
                label="view this niggas SHITTY banner",
                style=discord.ButtonStyle.blurple, 
                url=banner_url
            ))
            self.add_item(discord.ui.Button(label="get this lame niggas banner as jpg", url=banner_url + "?format=jpg"))
            self.add_item(discord.ui.Button(label="get this lame niggas banner as png", url=banner_url + "?format=png"))

class AvatarView(discord.ui.View):
    def __init__(self, user: discord.User, banner_url: str = None):
        super().__init__()
        avatar_url = user.display_avatar.url

        self.add_item(discord.ui.Button(label="dwnload this niggas shitty avi", url=avatar_url + "?format=png"))

        if banner_url:
            self.add_item(discord.ui.Button(label="download nigga", url=banner_url + "?format=png"))

@bot.tree.command(name="avatar", description="get a niggas avatar and banner.")
@app_commands.describe(user="The user whose avatar you want to see")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def avatar(interaction: discord.Interaction, user: discord.User = None):
    user = user or interaction.user

    full_user = await interaction.client.fetch_user(user.id)
    banner_url = full_user.banner.url if full_user.banner else None

    embed = discord.Embed(
        title=f"{user.display_name}'s avi and banner",
        color=0xa874d1
    )
    
    embed.set_thumbnail(url=user.display_avatar.url)

    if banner_url:
        embed.set_image(url=banner_url)

    embed.set_footer(
        text=f"req by this nigga {interaction.user.display_name}",
        icon_url=interaction.client.user.avatar.url if interaction.client.user.avatar else None
    )

    view = AvatarView(user, banner_url)

    await interaction.response.send_message(embed=embed, view=view)

    await log_command_use(
        user=interaction.user,
        command_name="avi",
        channel=interaction.channel,
        message=user.display_avatar.url
    )


class FloodButton(discord.ui.View):
    def __init__(self, message, delay):
        super().__init__()
        self.message = message
        self.delay = delay

    @discord.ui.button(label="flood this lame ass nigga LMFAOOO", style=discord.ButtonStyle.blurple)
    async def flood_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        max_retries = 2

        for _ in range(5):
            retries = 0
            while retries <= max_retries:
                try:
                    await interaction.followup.send(self.message, allowed_mentions=discord.AllowedMentions(everyone=True))
                    await asyncio.sleep(self.delay + random.uniform(0.1, 0.5))
                    break
                except discord.errors.HTTPException as e:
                    if e.status == 429:
                        retry_after = getattr(e, "retry_after", 1.5)
                        retry_after = min(retry_after, 5)
                        print(f"{Fore.YELLOW}>{Fore.WHITE} rate limit hit dumbass, retrying after {Fore.YELLOW}{retry_after:.2f}s{Fore.WHITE} (retry {Fore.YELLOW}{retries + 1}{Fore.WHITE}/{Fore.YELLOW}{max_retries}{Fore.WHITE})")
                        await asyncio.sleep(retry_after)
                        retries += 1
                    else:
                        raise e
            else:
                print(f"{Fore.RED}>{Fore.WHITE} Failed to send message after max retries, skipping this bih LOL{Fore.RED}.{Fore.WHITE}")



class IPView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

@bot.tree.command(name="ip", description="show the niggas fake IP loll (fake asf ngl)")
@app_commands.describe(user="The user you want to 'trace'")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def ip(interaction: discord.Interaction, user: discord.User):
    fake_ip = ".".join(str(random.randint(1, 255)) for _ in range(4))
    port = random.choice([22, 443, 8080])
    trace_id = f"#ZTA-{random.randint(1000, 9999)}"

    embed = discord.Embed(
        title="🚨 CRITICAL: Unauthorized Network Access Detected",
        description=(
            f"Intrusion Detection System has traced your connection: **IP {fake_ip}, Port {port}**, Subnet **255.255.255.0**.\n"
            f"Your activity has been flagged as a potential security breach and logged for further analysis. "
            f"Cease unauthorized actions immediately or face escalation.\n\n"
            f"🔒 **Security Alert**\n"
            f"Your IP address has been identified as: **{fake_ip}**. This information has been logged for security monitoring.\n\n"
            f"**Threat Level**: HIGH\n"
            f"**Trace ID**: `{trace_id}`\n"
            f"**Timestamp**: {discord.utils.format_dt(interaction.created_at, style='F')}"
        ),
        color=discord.Color.red()
    )

    await interaction.response.send_message("🔍 Tracing IP...", ephemeral=True)

    await interaction.followup.send(
        content=f"{user.mention}",
        embed=embed,
        view=IPView()
    )
    await log_command_use(interaction.user, "ip reveal")
    update_leaderboard(interaction.user.id, "ip")

@ip.error
async def ip_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.TransformError):
        await interaction.response.send_message("usr not found. mention a REAL nigga bro..", ephemeral=True)
    else:
        await interaction.response.send_message(f"An error occurred make a ticket in the server: {error}", ephemeral=True)

import base64


def get_badges(user: discord.Member) -> str:
    flags = user.public_flags
    badges = []

    if flags.hypesquad: badges.append("🏠 HypeSquad")
    if flags.hypesquad_bravery: badges.append("🦁 Bravery")
    if flags.hypesquad_brilliance: badges.append("🧠 Brilliance")
    if flags.hypesquad_balance: badges.append("⚖️ Balance")
    if flags.early_supporter: badges.append("🌟 Early Supporter")
    if flags.staff: badges.append("👔 Staff")
    if flags.partner: badges.append("🤝 Partner")
    if flags.verified_bot: badges.append("🤖 Verified Bot")
    if flags.verified_bot_developer: badges.append("👨‍💻 Bot Dev")

    return ", ".join(badges) if badges else "No Badges"

@bot.tree.command(name="hack", description="a fake ass hack ngl js to scare the fuck nigga (fake)")
@app_commands.describe(user="The user you want to 'hack'")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def hack(interaction: discord.Interaction, user: discord.User):
    user_id_str = str(user.id)
    b64_id = base64.b64encode(user_id_str.encode()).decode()[:-2]

    badges = get_badges(user)

    file_options = [
        "stealer_base_23.04.2025.txt",
        "stealer_base_11.10.2022.db",
        "stealer_logs_240520.txt",
        "stealer_base202401.db",
        "breach_base_01_03_2021.txt",
        "breach_logs_2025.txt"
        "stealer_base_23.04.2025.txt",
        "stealer_base_11.10.2022.db",
        "stealer_logs_240520.txt",
        "stealer_base202401.db",
        "breach_base_01_03_2021.txt",
        "breach_logs_2025.txt",
        "stealer_backup_15.08.2023.db",
        "breach_archive_202212.txt",
        "stealer_data_03122024.db",
        "breach_base_99_99_9999.txt",
        "stealer_records_07.07.2020.txt",
        "logs_stealer_202503.db",
        "breach_dump_12_12_2022.txt",
        "stealer_cache_20240115.db",
        "breach_data_2025_backup.txt",
        "stealer_base_old_201901.db"
    ]
    found_in_file = random.choice(file_options)

    embed = discord.Embed(
        title=f"Found in: {found_in_file}",
        color=discord.Color.purple()
    )

    embed.add_field(
        name=f"{user.name} ({user.id})",
        value=(
            f"🪙 **Token:**\n`{b64_id}****`\n\n"
            f":e_mail:  Gmail: `Hidden`\n"
            f":iphone: Phone: `Hidden`\n"
            f":globe_with_meridians: Earth IP: `Hidden`"
        ),
        inline=False
    )

    embed.add_field(name="🎖 Badges:", value=badges, inline=True)
    embed.add_field(name="💳 Billing:", value="`(no billing)`", inline=True)
    embed.add_field(name="👥 HQ Friends:", value="`None`", inline=True)
    embed.add_field(name="🌍 Guilds:", value="`None`", inline=True)
    embed.add_field(name="🎁 Gift codes:", value="`None`", inline=True)

    embed.set_thumbnail(url=user.avatar.url if user.avatar else None)
    embed.set_footer(text="SoulLLC fk nga")

    await interaction.response.send_message(":computer: breaching account...", ephemeral=True)

    await interaction.followup.send(
        content=f"{user.mention}",
        embed=embed,
        view=IPView()
    )


@hack.error
async def hack_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.TransformError):
        await interaction.response.send_message("usr not found dipshit @ a real user dumbass nigga .", ephemeral=True)
    else:
        await interaction.response.send_message(f"An error occurred make a ticket in the discord server: {error}", ephemeral=True)



RAGEBAIT = ["""
# RAIDED BY SOUL LLC
# RAIDED BY SOUL LLC
# RAIDED BY SOUL LLC
# RAIDED BY SOUL LLC
# RAIDED BY SOUL LLC
NIGGA 
# RAIDED BY SOUL LLC
# RAIDED BY SOUL LLC
NIGGA
# RAIDED BY SOUL LLC
# RAIDED BY SOUL LLC
# RAIDED BY SOUL LLC
NIGGA
# RAIDED BY SOUL LLC
# RAIDED BY SOUL LLC
# RAIDED BY SOUL LLC
# SOUL LLC OWNS YOU BUMS
@everyone
https://discord.gg/C3zhSsTyPW
https://cdn.discordapp.com/attachments/1491292981632831549/1504338477838372966/lv_0_20260514002354.gif?ex=6a0d3762&is=6a0be5e2&hm=4d5bbf3337a052065c409f66c88985af13b48749137149fb6a35fae10fbd331c&
    """,
    """
# YOU HAVE BEEN RAIDED BY [SOUL LLC🆘](https://cdn.discordapp.com/attachments/1491292981632831549/1504338477838372966/lv_0_20260514002354.gif?ex=6a0d3762&is=6a0be5e2&hm=4d5bbf3337a052065c409f66c88985af13b48749137149fb6a35fae10fbd331c&)
# RAID ANY SERVER WITHOUT ADMIN PERMS 🔐
# FREE, EASY TO USE, UP 24/7
# ANONYMOUSLY RAID ANY SERVER YOU WANT
# "IF YOU CANT BEAT THEM, [JOIN](https://discord.gg/C3zhSsTyPW) THEM! @everyone"
⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀                            [JOIN SOUL LLC, RAID ANY SERVER YOU WANT, ANYTIME, ANYWHERE, ANYWHERE](https://discord.gg/raJTHmBeae)
 
[穹忩犈垃箚泗趨菋纳攇幀驼懅七](https://cdn.discordapp.com/attachments/1153733814732992573/1166450104350290020/d480327590432d30f979d4ce46baea6b.gif?ex=686e1290&is=686cc110&hm=312bf638b772621b7e9f33ac2f62832c5d417a7dbd08a307d5ae94e96cc9d8d1&)
    """,
    """
# [SOUL LLC](https://discord.gg/C3zhSsTyPW) OWNS ME AND ALL :zany_face: 
# GET RAIDED U BRAINDEAD NIGGERS :rofl: :rofl: :rofl:
# IMAGINE U CANT SETUP A SERVER LMAOOOO
# BETTER [JOIN](https://discord.gg/C3zhSsTyPW) INSOMNIA AND START RAIDING U TWAT 
https://tenor.com/view/cat-hacking-silly-cat-hacker-cat-hacker-gif-14852445362476137270
[穹忩犈垃箚泗趨菋纳攇幀驼懅七](https://cdn.discordapp.com/attachments/1153733814732992573/1166450104350290020/d480327590432d30f979d4ce46baea6b.gif?ex=686e1290&is=686cc110&hm=312bf638b772621b7e9f33ac2f62832c5d417a7dbd08a307d5ae94e96cc9d8d1&)
@everyone
    """,
    """
# [SOUL LLC](https://tenor.com/view/flashbang-guy-screaming-guy-getting-flashbang-blinded-blinding-gif-1425127881206275521) __DOMINATES__ ALL 👑
# GET __RAIDED__, YOU RETARDS CAN'T HANDLE THIS 😭 🥀 🥀
# IMAGINE NOT BEING ABLE TO SETUP A SERVER LMAO
# BETTER [JOIN](https://discord.gg/C3zhSsTyPW) INSOMNIA AND START RAIDING, YOU KNOW YOU WANT TO!
@everyone
    """
]


SCARY = [
    """
    # [SOUL LLC](https://media.tenor.com/uw5s-aHlviAAAAAM/scary-ghost.gif)
    # [SOUL LLC](https://discord.gg/C3zhSsTyPW)
    # [SOUL LLC](https://tenor.com/view/yapping-creepy-under-the-bed-talking-ghost-gif-10296050582380126660)
    # [SOUL LLC](https://cdn.discordapp.com/attachments/1416037733322719364/1418258241879539733/RussianSleepExperimentGuy.png?ex=68cd776a&is=68cc25ea&hm=4141a571871aebcf5e93aa57d505285a924103536892e8a5b3ff0636c7ff2590&)
    @everyone
    """,
    """
    # [SOUL LLC](https://media.tenor.com/HMtY33kDWFwAAAAM/donk.gif)
    # [SOUL LLC](https://nightmarenostalgia.com/wp-content/uploads/2023/07/main-qimg-522ae83e590c80bfaf895b3919462bcb.gif?w=480)
    # [SOUL LLC](https://media.tenor.com/ihDOwbsgwRcAAAAM/scary-scary-face.gif)
    # [SOUL LLC](https://discord.gg/C3zhSsTyPW)
    @everyone
    """
]

ASCII = [
    r"""
```

  /$$$$$$                      /$$
 /$$__  $$                    | $$
| $$  \__/  /$$$$$$  /$$   /$$| $$
|  $$$$$$  /$$__  $$| $$  | $$| $$
 \____  $$| $$  \ $$| $$  | $$| $$
 /$$  \ $$| $$  | $$| $$  | $$| $$
|  $$$$$$/|  $$$$$$/|  $$$$$$/| $$
 \______/  \______/  \______/ |__/
                                                                                                                             
```
***BETTER [JOIN](https://discord.gg/C3zhSsTyPW) SOUL LLC AND START RAIDING***
[SOUL LLC ON TOP](https://tenor.com/view/shawn-breezy-gamma-male-gif-13452613280176262444)
@everyone

    
    """,
    r"""
```
 ____  ____  _     _    
/ ___\/  _ \/ \ /\/ \   
|    \| / \|| | ||| |   
\___ || \_/|| \_/|| |_/\
\____/\____/\____/\____/
                     soul llc on top
```
***[JOIN](https://discord.gg/C3zhSsTyPW) SOUL LLC AND START RAIDING TODAY***
***[FREE](https://discord.gg/C3zhSsTyPW) TO USE, NO PERMS NEEDED***
@everyone

    """,
    r"""
```diff
                                              
                                              
  .--.--.                             ,--,    
 /  /    '.                         ,--.'|    
|  :  /`. /    ,---.           ,--, |  | :    
;  |  |--`    '   ,'\        ,'_ /| :  : '    
|  :  ;_     /   /   |  .--. |  | : |  ' |    
 \  \    `. .   ; ,. :,'_ /| :  . | '  | |    
  `----.   \'   | |: :|  ' | |  . . |  | :    
  __ \  \  |'   | .; :|  | ' |  | | '  : |__  
 /  /`--'  /|   :    |:  | : ;  ; | |  | '.'| 
'--'.     /  \   \  / '  :  `--'   \;  :    ; 
  `--'---'    `----'  :  ,      .-./|  ,   /  
                       `--`----'     ---`-'   
                                              
                                                 
                                                               
```
***[JOIN](https://discord.gg/C3zhSsTyPW) SOUL LLC AND START RAIDING TODAY***
***[FREE](https://tenor.com/view/discord-discordgifemoji-red-blink-gif-13138334) TO USE, NO PERMS NEEDED***
@everyone
    """
]

HENTAI = [
    """
⢠⣾⣿⣿⣿⠄⢻⣿⣿⣿⡇⢰⣿⣿⣬⣭⣅⠊⢻⡇⢰⣿⡆⠄⠄
⢿⣿⣿⣿⣿⠄⢸⣿⠟⢛⡄⢸⣿⣿⣦⡁⢿⣷⣮⡃⠟⢿⣿⡀⠄
⢀⣿⣿⣿⣿⡇⠘⢣⣾⠟⠄⠸⣿⣿⣿⣿⣦⢹⣿⣿⣦⡑⠈⠁⠄
⢸⣿⣿⣿⣿⡇⢠⠟⠁⠾⡏⠄⠘⠻⣿⣿⣿⢸⣿⣿⣿⠿⠟⠛⡄
⠘⣿⣿⣿⣿⣿⠈⠄⣄⡀⠄⠂⢲⡦⡈⢻⡿⢸⣿⠿⣫⣴⠶⠶⣻
⠈⠛⠿⢿⣿⣧⣠⢝⠓⠄⠠⢅⡠⠤⠒⡐⠲⢶⣤⣤⣤⣤⠔⠁ ⠄
⠄⠄⢀⣀⠇⠙⠊⠉⢸⣿⣿⣿⣿⣿⣿⣿⣿⣶⠖⠄⠄⠄⠄⠄
⠄⠄⠄⠄⠄⠄⠄⢀⣠⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⠄⠄⠄⠄⠄⠄
⠄⠄⠄⠄⠄⣠⠸⣿⣿⣿⣿⣿⣿⣿⣿⢿⣿⣿⣷⠄⠄⠄⠄⠄⠄
⠄⠄⢠⣴⣿⣿⣷⣦⡙⣿⣿⣿⣿⣿⣿⣼⣿⣿⣿⣷⣄⠄⠄⠄⠄
⠄⣴⣿⣿⣿⣿⣿⣶⣭⡀⠻⣿⣿⣿⣿⣿⣿⣿⠟⣭⣶⣷⣄⠄⠄
⣸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣦⡌⠙⠛⠛⠛⢋⣵⣿⣿⣿⣿⣿⣷⠄
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣾⠛⣛⣴⣿⣿⣿⣿⣿⣿⣿⣿⣷

# [Uwu](https://discord.gg/C3zhSsTyPW) G-G-GET (uwu) W-W-WAIDED (˘³˘) B-B-BY ˚(ꈍ ω ꈍ).₊̣̇. S-S-S-[SOUL] L-L-LLC (https://pa1.aminoapps.com/5985/ded984459526799715a26557194711a049e81c6e_hq.gif) (◡ ꒳ ◡)
@everyone
    """,
    """
⠄⢹⡄⠄⢸⠄⠄⠄⠄⠄⢁⢿⣿⡋⣩⣍⢙⣿⣽⠅⠄⠄⠄⠄⠄⡿⠄⢀⡟⠄
⠄⠄⢷⡀⣿⣆⣠⣤⠠⢴⣦⣝⠻⣿⣿⣿⡿⢟⡡⠄⠄⢠⣄⡀⢀⡿⢀⡾⠄⠄
⠄⢠⣬⣷⡾⣏⠻⣿⣧⢁⠈⢿⢧⣀⡁⠁⠡⠞⠅⢀⢢⣿⣿⡿⣼⣷⣾⣣⣄⡀
⠘⢷⡛⠯⠿⣿⣶⠹⢫⣫⣿⣦⣊⡂⢀⡄⢀⣤⣶⣷⡳⡋⠉⢾⡿⠿⠯⠿⢺⠇
⠄⠘⠶⣷⣼⡿⠇⠄⢰⣿⣿⣿⣿⣿⣶⣶⣿⣿⣿⣿⣿⡹⡄⠘⠻⣧⣾⠟⠁⠄
⠄⠄⣼⣾⠟⠄⣀⣤⣾⣿⣿⣿⠛⢿⣿⡟⠛⣹⣹⣿⣿⣷⣦⡄⠐⣿⣿⣷⠄⠄
⠄⣜⡿⣩⡖⣰⣿⣿⣿⣿⣿⣿⣦⡀⠘⠄⣼⣿⣿⣿⣿⣿⣿⣿⡌⢾⡿⣿⣇⠄
⣼⠏⣴⠏⢰⣿⣿⣿⣿⣿⣿⣿⣿⣿⡆⣼⣿⣿⣿⣿⣿⣿⣿⣿⡇⠘⣿⡿⣿⣦
⡏⢰⠏⠄⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣧⣿⣿⣿⣿⣿⣿⣿⣿⣿⣇⠄⢸⣿⢿⣿

# S-S-SOUL L-L-LLC O-O-ON (˘ω˘) T-T-TOP U-u-u [UwU](https://discord.gg/Qys5GEJBWF) F-F-FUCKING (。U ω U。) [N-N-N-NIGGERS](https://tophentaicomics.com/wp-content/uploads/2020/03/delicious-hentai-gif-xxx-1584367984kn4g8.gif)
@everyone
    """,
    """
⠄⠄⡠⠺⠁⠄⠄⠈⠑⢦⠄
⠄⡜⠸⢰⡐⠄⠄⠄⠄⠄⣇
⠄⣯⡏⣘⣎⣂⣵⢀⢾⡄⡼
⠄⠏⣎⠟⣻⣿⢻⠃⢈⡝
⠄⠄⠹⠋⢉⣵⣮⣰⡚
⠄⠄⠄⠄⠸⣿⣿⡏⣷⢹⣦
⠄⠄⠄⢀⡄⣿⣿⡇⣾⡏⣻⡄
⠄⠄⢴⣿⣿⢹⣿⡇⣿⣧⢿⣇
⠄⠸⣸⣿⣿⢸⣿⡇⣿⣿⣟⢿⣦⣀
⠄⠄⠈⠛⠛⠈⣿⣷⢻⡿⢟⣣⣭⣭⣝⡲⢶⣶⣤⣄⡀
⠄⠄⠄⠄⠄⠸⣿⢟⣤⣾⣿⣿⣿⣿⣿⣿⣷⡹⣿⣿⣿⣷⣄
⠄⠄⠄⠄⠄⢀⣴⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⢻⣿⣿⣿⣿⣆
⠄⠄⠄⢀⣴⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠱⡜⣿⣿⣿⣿⡿⣾⣷⠄
⠄⣠⣶⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⢛⣵⠇⡇⣿⣿⣿⢟⣵⢸⣿⡇
⣼⣿⣭⣶⣶⣶⣶⣝⡻⣿⣿⡿⠿⡛⠁⠄⠁⠄⠄⠄⠄⠄⠄⣵⣿⣿⠟
⠹⣿⣿⣿⣿⣿⣿⣿⣿⣶⣶⣴⡸⣿⣧⣀⡤⣤⠄⠄⠄⠄⠄⢷⢰⠞⠄
    
# J-J-J-JOIN S-S-[SOWLL LLC](https://66.media.tumblr.com/43763839ac3e228314a43a0ffcced591/tumblr_p3jog4Xk5g1x09foko1_400.gif) x3 A-A-A-AND S-S-STAWT W-W-WAIDING :3 T-T-T-TODAY
# NYO P-P-P-PEWMS uwU N-N-NYEEDED, (U ﹏ U) F-F-F-FWEE T-T-TO U-U-U-USE [(⑅˘꒳˘)](https://discord.gg/C3zhSsTyPW)
@everyone
    """
]

class BspamButton(discord.ui.View):
    def __init__(self, spam_texts, delay):
        super().__init__(timeout=900)
        self.spam_texts = spam_texts
        self.delay = delay

    @discord.ui.button(label="🚨 Spam Button", style=discord.ButtonStyle.danger)
    async def start_spam(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        for _ in range(20):
            random_text = random.choice(self.spam_texts)
            await interaction.followup.send(random_text, allowed_mentions=discord.AllowedMentions(everyone=True))
            await asyncio.sleep(self.delay)



@bot.tree.command(name="spam", description="Spam random messages with different styles.")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(
    style="Choose spam style (ragebait, scary, ascii, hentai)",
    delay="Delay between messages (0.01 to 5.00 seconds)."
)
async def bspam(interaction: discord.Interaction, style: str, delay: float = 0.5):
    if delay < 0.01 or delay > 5.00:
        await interaction.response.send_message(
            "**Error: Delay must be between 0.01 and 5.00 seconds.**",
            ephemeral=True
        )
        return

    style = style.lower()
    if style == "ragebait":
        spam_list = RAGEBAIT
    elif style == "scary":
        spam_list = SCARY
    elif style == "ascii":
        spam_list = ASCII
    elif style == "hentai":
        spam_list = HENTAI
    else:
        await interaction.response.send_message("❌ Invalid style! Choose `ragebait`, `scary`  `ascii` or 'hentai' -# fucking gooner.", ephemeral=True)
        return

    view = BspamButton(spam_list, delay)
    await interaction.response.send_message(
        f"🚨 Press the button to start spamming\n mode: **{style.upper()}**",
        view=view,
        ephemeral=True
    )



@bspam.autocomplete("style")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def style_autocomplete(interaction: discord.Interaction, current: str):
    styles = ["ragebait", "scary", "ascii", "hentai"]
    return [
        app_commands.Choice(name=s, value=s)
        for s in styles if current.lower() in s
    ]


@bot.tree.command(name="raid", description="raid any server (MIGHT BE DOWN).")
@app_commands.describe(delay="delay these msgs (0.01 to 5.00).")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def araid(interaction: discord.Interaction, delay: float = 0.01):
    if delay < 0.01 or delay > 5.00:
        await interaction.response.send_message("**dumbass i said 0.01 to 5 secs you gen DUMBASS.**", ephemeral=True)
        return

    raid_message = '''
    ⠀⠀⠀⠀
⠀⠀⠀⠀
     
                                  **Soul**   `🌙`
                  raid b__o__t  ﹒ s__o__cial  ﹒ to__xic__
                         `🌟`     _join to [RAID] any server __Without Admin perms__, free to use_ 💰 

⠀⠀⠀⠀⠀⠀⠀                            **[JOIN](https://discord.gg/C3zhSsTyPW) TODAY, AND R__AI__D EVER__Y__ SERVER YOU WANT WITHOUT [ADMIN](https://tenor.com/view/mooning-show-butt-shake-butt-pants-down-gif-17077775)**


# 𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫
JOIN SOUL LLC RETARD
# 𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫
``` YOU HAVE BEEN RAIDED BY SOUL LLC


SOUL OWNS YOU NIGGA


GET BETTER SECURITY NOOBS```
# 𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫
[JOIN SOUL LLC](https://cdn.discordapp.com/attachments/1506545366835925108/1515942967284731934/lv_0_20260514002354.gif?ex=6a30d768&is=6a2f85e8&hm=50cab2344dd10d54bf3b3a88388aa399ec8b0c5e1e48f970613f6da9688c0742&) 
JOIN SOUL LLC RETARD
# 𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫𒐫
``` YOU HAVE BEEN RAIDED BY SOUL LLC


GET OWNED BY SOUL LOL


GET BETTER SECURITY NOOBS```








``` SOUL LLC OWNS YOU






JUST ACCEPT IT ALREADY, SOUL OWNS YOU BUD``` 
            '''
    try:
        view = FloodButton(raid_message, delay)
        await interaction.response.send_message("Press the button to start raiding.", view=view, ephemeral=True)
    except discord.HTTPException as e:
        if e.code == 40094:  # follow-up message limit reached
            print(f"[A-RAID ERROR] Max follow-up messages reached for interaction {interaction.id}")
        else:
            print(f"[A-RAID ERROR] Unexpected HTTPException: {e}")
            raise

    await log_command_use(
        user=interaction.user,
        command_name="raid",
        channel=interaction.channel
    )
    update_leaderboard(interaction.user.id, "a-raid")



@bot.tree.command(name="say", description="say wtv tf u want half anon LOL")
@app_commands.describe(message="The message you want the bot to say")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def say(interaction: discord.Interaction, message: str):
    if is_premium_user(interaction.user.id):
        full_message = f"{message}"
    else:
        full_message = f"{message} \n\n"

    await interaction.response.send_message("sendin hopefully its some GOOD bullshit LOLLL", ephemeral=True)
    allowed = discord.AllowedMentions(everyone=True, users=True, roles=True)
    await interaction.followup.send(full_message, allowed_mentions=allowed)

    await log_command_use(
        user=interaction.user,
        command_name="say",
        message=message,
        channel=interaction.channel
    )
    update_leaderboard(interaction.user.id, "say")


@bot.tree.command(
    name="ghostping",
    description="ghost ping sm1 fucking loser"
)
@app_commands.describe(
    user=" the nga u want to ping LOLLLL",
    seconds=" the delay u want lame nigga? ",
    times="how many times bitch nigga?"
)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def ghostping(
    interaction: discord.Interaction,
    user: discord.User,
    seconds: float = 0.3,
    times: int = 3
):
    await interaction.response.send_message("tryna ping the lame nigga", ephemeral=True)
    await log_command_use(interaction.user, "ghost pinged")
    update_leaderboard(interaction.user.id, "ghost pinged")

    for i in range(times):
        try:
            message = await interaction.followup.send(f"{user.mention}")
            await asyncio.sleep(seconds)
            await message.delete()
        except discord.HTTPException as e:
            if e.code == 40094:  
                print(f"[ghost ping] follow up messages reached – stopped after  {i} pings lame nigga")
                break
            else:
                raise

whitelist = config.get("whitelist", [])

@bot.tree.command(name="add-premium", description="grant the power of prem [VOID AND SOUL+AVA ONLY FUCKING LOSERRRR]")
@app_commands.describe(user="The user to grant premium access to")
async def add_premium(interaction: discord.Interaction, user: discord.User):
    if interaction.user.id not in whitelist:
        await interaction.response.send_message("dumbass nigga you arent void,soul, or ava fucking lame ass nigga XDDD", ephemeral=True)
        return
    
    add_premium_user(user.id)
    await interaction.response.send_message(f"alright lame nigga you YES YOU {user.mention} have premium", ephemeral=False)

@bot.tree.command(name="rem-premium", description="REMOVE the power of prem from a lame nigga [VOID AND SOUL+AVA ONLY FUCKING LOSERRRR]")
@app_commands.describe(user="The user to remove premium access from")
async def rem_premium(interaction: discord.Interaction, user: discord.User):
    if interaction.user.id not in whitelist:
        await interaction.response.send_message("your fucking stupid nigga LOLLLOLLOLLOLOLOL.", ephemeral=True)
        return

    removed = remove_premium_user(user.id)
    if removed:
        await interaction.response.send_message(f"LMFAOOOO YOUR PREM YES NIGGA YOU {user.mention} HAVE PREM REMOVED FUCKING LOSERRRR LMFAOOOOO", ephemeral=False)
    else:
        await interaction.response.send_message(f"uh hey owner, cheif owner, ava the nigga {user.mention} does not have premium access???", ephemeral=False)



class RoastButton(discord.ui.View):
    def __init__(self, user: discord.User, delay: float = 0.5):
        super().__init__()
        self.user = user
        self.delay = delay

    @discord.ui.button(label="roast this lame ass nigga LMFAOOOO", style=discord.ButtonStyle.blurple)
    async def roast_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        max_retries = 2

        try:
            with open("roasts.txt", "r", encoding="utf-8") as f:
                roasts = [line.strip() for line in f if line.strip()]
            if not roasts:
                await interaction.followup.send("lmfaooo make a ticket and say 'hey theres no roast in the roast.txt.. check orihost' and well work on it alr? ")
                return
        except FileNotFoundError:
            await interaction.followup.send("lmfaooo make a ticket and say 'hey theres no roast.txt.. check orihost' and well work on it alr?")
            return

        for _ in range(5):
            roast_text = random.choice(roasts)
            retries = 0
            while retries <= max_retries:
                try:
                    allowed = discord.AllowedMentions(everyone=True, users=True, roles=True)
                    await interaction.followup.send(f"{roast_text} {self.user.mention}", allowed_mentions=allowed)
                    await asyncio.sleep(self.delay + random.uniform(0.1, 0.5))
                    break
                except discord.errors.HTTPException as e:
                    if e.status == 429:
                        retry_after = getattr(e, "tryagainsoon", 1.5)
                        retry_after = min(retry_after, 5)
                        print(f"rate limit hit, retrying after {retry_after:.2f}s (retry {retries + 1}/{max_retries})")
                        await asyncio.sleep(retry_after)
                        retries += 1
                    else:
                        raise e
            else:
                print("failed to send the roast, stupid ass rate lim, skipped.")


@bot.tree.command(name="roast", description="send a roast on the lame nigga you want.")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(user="the nigga you want to roast")
async def roast(interaction: discord.Interaction, user: discord.User):
    view = RoastButton(user, delay=0.5)
    await interaction.response.send_message("ROAST THE LAME NIGGA)", view=view, ephemeral=True)



def random_time_today():
    base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    random_minutes = random.randint(0, 23 * 60 + 59)  # 0 bis 1439 Minuten
    random_time = base_date + timedelta(minutes=random_minutes)
    return random_time

@bot.tree.command(name="spoof-a-message", description="send a rly REAL msg as a IMAGE.")
@app_commands.describe(username="name to display", message="fake message to show", avatar_url="avatar image URL")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def spoof_image(interaction: discord.Interaction, username: str, message: str, avatar_url: str = None):
    await interaction.response.send_message("spoofin da message lame nigga.", ephemeral=True)

    if not avatar_url:
        avatar_url = "https://cdn.discordapp.com/embed/avatars/0.png"

    response = requests.get(avatar_url)
    avatar = Image.open(BytesIO(response.content)).convert("RGBA")
    avatar = avatar.resize((40, 40), Image.LANCZOS)

    mask = Image.new("L", avatar.size, 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0) + avatar.size, fill=255)
    avatar = ImageOps.fit(avatar, mask.size, centering=(0.5, 0.5))
    avatar.putalpha(mask)

    width, height = 800, 80
    img = Image.new("RGBA", (width, height), "#36393F")
    draw = ImageDraw.Draw(img)

    font_bold = ImageFont.truetype("arialbd.ttf", 18)
    font_regular = ImageFont.truetype("arial.ttf", 16)
    font_timestamp = ImageFont.truetype("arial.ttf", 12)

    img.paste(avatar, (20, 20), avatar)
    now = random_time_today().strftime("Today at %I:%M %p").lstrip("0").replace(" 0", " ")

    draw.text((70, 18), username, font=font_bold, fill=(255, 255, 255))
    draw.text((70 + draw.textlength(username, font=font_bold) + 10, 21), now, font=font_timestamp, fill=(153, 170, 181))
    draw.text((70, 45), message, font=font_regular, fill=(220, 221, 222))

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    file = discord.File(fp=buffer, filename="spoof.png")

    await interaction.followup.send(file=file)

    await log_command_use(user=interaction.user, command_name="spoof-message", message=message)
    update_leaderboard(interaction.user.id, "spoof-message")



@bot.tree.command(name="blame", description="be a asshole and blame a bitch nigga")
@app_commands.describe(user="the fuck nigga you want to blame")
async def blame(interaction: discord.Interaction, user: discord.User):
    await interaction.response.send_message("Blaming... ✏️", ephemeral=True)
    await interaction.followup.send(f"{user.mention}, Your Raid Command has been Successfully Completed! ✅")
    await log_command_use(interaction.user, "blame")



@bot.tree.command(name="anon-dm", description="anon dm a fucking loser LMFAO")
@app_commands.describe(user="the fuck nigga you want to message", message="The message to send")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def anon_dm(interaction: discord.Interaction, user: discord.User, message: str):
    try:
        await user.send(f"{message}")
        await interaction.response.send_message("msg sent loser", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("dm closed.", ephemeral=True)
    await log_command_use(
        user=interaction.user,
        command_name="anon-dm",
        channel=interaction.channel,
        message=message
    )


@bot.tree.command(name="flooduser", description="[prem] FLOOD A BITCH ASS NIGGAS DMS ")
@app_commands.describe(user="The user to DM spam", message="Message to spam", times="How many times to send", delay="Delay between messages (in sec)")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
async def flooduser(interaction: discord.Interaction, user: discord.User, message: str, times: int = 5, delay: float = 0.3):
    if not is_premium_user(interaction.user.id):
     await interaction.response.send_message("stop being fucking broke and buy prem fucking losers omfg", ephemeral=True)
     return
    await interaction.response.send_message("SENDING THE FLOOD TO THE LAME NIGGA LMFAO", ephemeral=True)
    await log_command_use(
        user=interaction.user,
        command_name="flooduser [prem stop being broke and buy it LMFAO]",
        channel=interaction.channel,
        message=message
    )
    for _ in range(times):
        try:
            await user.send(message)
            await asyncio.sleep(delay)
        except discord.Forbidden:
            await interaction.followup.send("the fucking loser doesnt have his dms open lmfao).", ephemeral=True)
            break



@bot.event
async def on_ready():
    print(logo)
    print(f"{Fore.MAGENTA}>{Fore.WHITE} Logged in as {Fore.MAGENTA}{bot.user}{Fore.WHITE}.")
    try:
        synced = await bot.tree.sync()
        print(f"{Fore.MAGENTA}>{Fore.WHITE} Synced {Fore.MAGENTA}{len(synced)} {Fore.WHITE}commands{Fore.MAGENTA}.{Fore.WHITE}")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


if __name__ == "__main__":
    TOKEN = token_management()
    if TOKEN:
        try:
            bot.run(TOKEN)
        except discord.errors.LoginFailure:
            print(Fore.RED + "Can't connect to token. Please check your token.")
            input(Fore.YELLOW + "Press Enter to go back to the menu...")
            TOKEN = token_management()  
            if TOKEN:
                bot.run(TOKEN)  
        except Exception as e:
            print(Fore.RED + f"An unexpected error occurred: {e}")
            input(Fore.YELLOW + "Press Enter to restart the menu...")
            TOKEN = token_management() 
            if TOKEN:
                bot.run(TOKEN)  
    else:
        print(Fore.RED + "❌ Error: Unable to load or set a token.")
