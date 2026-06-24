import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import asyncio
import os
import dateparser
import json

from google.oauth2 import service_account
from googleapiclient.discovery import build

# ---------------- TOKEN ----------------
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# ---------------- GOOGLE CALENDAR ----------------
CALENDAR_ID = os.getenv("CALENDAR_ID")

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_service():
    creds_info = json.loads(os.getenv("GOOGLE_CREDS"))

    creds = service_account.Credentials.from_service_account_info(
        creds_info,
        scopes=SCOPES
    )

    return build("calendar", "v3", credentials=creds)

# ---------------- GUILD ----------------
GUILD_ID = 1505354242276462632
GUILD = discord.Object(id=GUILD_ID)

# ---------------- BOT ----------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- STORAGE ----------------
aufstellungen = {}
events = {}
abwesende = {}

# =========================================================
# 🚗 AUFSTELLUNG SYSTEM (UNVERÄNDERT)
# =========================================================

class AufstellungView(discord.ui.View):

    def __init__(self, event_name):
        super().__init__(timeout=None)
        self.event_name = event_name

        if event_name not in aufstellungen:
            aufstellungen[event_name] = []

    @discord.ui.button(label="✅ Anmelden", style=discord.ButtonStyle.green)
    async def anmelden(self, interaction: discord.Interaction, button: discord.ui.Button):

        user = interaction.user.display_name

        if user not in aufstellungen[self.event_name]:
            aufstellungen[self.event_name].append(user)

        await self.update(interaction)

    @discord.ui.button(label="❌ Abmelden", style=discord.ButtonStyle.red)
    async def abmelden(self, interaction: discord.Interaction, button: discord.ui.Button):

        user = interaction.user.display_name

        if user in aufstellungen[self.event_name]:
            aufstellungen[self.event_name].remove(user)

        await self.update(interaction)

    async def update(self, interaction: discord.Interaction):

        spieler = "\n".join(aufstellungen[self.event_name]) or "Noch niemand angemeldet"

        embed = discord.Embed(
            title="🚗 Familien-Aufstellung",
            description=f"**Event:** {self.event_name}",
            color=discord.Color.gold()
        )

        embed.add_field(
            name=f"👥 Teilnehmer ({len(aufstellungen[self.event_name])})",
            value=spieler,
            inline=False
        )

        await interaction.response.edit_message(embed=embed, view=self)

# =========================================================
# 🚗 EVENT SYSTEM (UNVERÄNDERT)
# =========================================================

class EventView(discord.ui.View):

    def __init__(self, event_name):
        super().__init__(timeout=None)
        self.event_name = event_name

        if event_name not in events:
            events[event_name] = {"dabei": [], "nicht": []}

    @discord.ui.button(label="🟢 Bin dabei", style=discord.ButtonStyle.green)
    async def dabei(self, interaction: discord.Interaction, button: discord.ui.Button):

        user = interaction.user.display_name

        if user not in events[self.event_name]["dabei"]:
            events[self.event_name]["dabei"].append(user)

        if user in events[self.event_name]["nicht"]:
            events[self.event_name]["nicht"].remove(user)

        await self.update(interaction)

    @discord.ui.button(label="🔴 Kann nicht", style=discord.ButtonStyle.red)
    async def nicht(self, interaction: discord.Interaction, button: discord.ui.Button):

        user = interaction.user.display_name

        if user not in events[self.event_name]["nicht"]:
            events[self.event_name]["nicht"].append(user)

        if user in events[self.event_name]["dabei"]:
            events[self.event_name]["dabei"].remove(user)

        await self.update(interaction)

    async def update(self, interaction: discord.Interaction):

        dabei = "\n".join(events[self.event_name]["dabei"]) or "Noch niemand"
        nicht = "\n".join(events[self.event_name]["nicht"]) or "Noch niemand"

        embed = discord.Embed(
            title=f"🚗 Event: {self.event_name}",
            color=discord.Color.gold()
        )

        embed.add_field(name="🟢 Dabei", value=dabei, inline=True)
        embed.add_field(name="🔴 Kann nicht", value=nicht, inline=True)

        await interaction.response.edit_message(embed=embed, view=self)

# =========================================================
# 📌 EVENT COMMAND (UNVERÄNDERT)
# =========================================================

@bot.tree.command(
    name="event",
    description="Erstellt ein Event",
    guild=GUILD
)
async def event(interaction: discord.Interaction, name: str):

    events[name] = {"dabei": [], "nicht": []}

    embed = discord.Embed(
        title=f"🚗 Event: {name}",
        description="Klicke unten auf einen Button:",
        color=discord.Color.gold()
    )

    embed.add_field(name="🟢 Dabei", value="Noch niemand", inline=True)
    embed.add_field(name="🔴 Kann nicht", value="Noch niemand", inline=True)

    await interaction.response.send_message(embed=embed, view=EventView(name))

# =========================================================
# 📅 NEU: GOOGLE CALENDAR ABWESENHEIT (ERSATZ)
# =========================================================

@bot.tree.command(
    name="abwesenheit",
    description="Abwesenheit mit Uhrzeit + Google Kalender",
    guild=GUILD
)
@app_commands.describe(
    von="Start (z.B. 25.06.2026 14:00)",
    bis="Ende (z.B. 25.06.2026 18:00)",
    grund="Grund der Abwesenheit"
)
async def abwesenheit(interaction: discord.Interaction, von: str, bis: str, grund: str):

    user_name = interaction.user.display_name

    start = dateparser.parse(von, languages=["de"])
    end = dateparser.parse(bis, languages=["de"])

    if not start or not end:
        await interaction.response.send_message("❌ Datum/Uhrzeit konnte nicht erkannt werden.")
        return

    service = get_calendar_service()

    event_data = {
        "summary": f"Abwesenheit: {user_name}",
        "description": f"Discord: {user_name}\nGrund: {grund}",
        "start": {
            "dateTime": start.isoformat(),
            "timeZone": "Europe/Berlin"
        },
        "end": {
            "dateTime": end.isoformat(),
            "timeZone": "Europe/Berlin"
        }
    }

    service.events().insert(
        calendarId=CALENDAR_ID,
        body=event_data
    ).execute()

    embed = discord.Embed(
        title="📅 Abwesenheit gespeichert",
        color=discord.Color.green()
    )

    embed.add_field(name="👤 Name", value=user_name, inline=False)
    embed.add_field(name="📅 Von", value=von, inline=False)
    embed.add_field(name="📅 Bis", value=bis, inline=False)
    embed.add_field(name="📌 Grund", value=grund, inline=False)

    await interaction.response.send_message(embed=embed)

# =========================================================
# 📋 ABWESENDE LISTE (UNVERÄNDERT)
# =========================================================

@bot.tree.command(
    name="abwesend",
    description="Zeigt alle Abwesenden",
    guild=GUILD
)
async def abwesend(interaction: discord.Interaction):

    if not abwesende:
        await interaction.response.send_message("✅ Niemand abwesend.")
        return

    text = ""

    for user_id, data in abwesende.items():
        try:
            user = await bot.fetch_user(user_id)
            text += f"**{user.name}**\n📅 {data['von']} - {data['bis']}\n📌 {data['grund']}\n\n"
        except:
            pass

    embed = discord.Embed(
        title="📋 Abwesende Mitglieder",
        description=text,
        color=discord.Color.red()
    )

    await interaction.response.send_message(embed=embed)

# =========================================================
# 🔄 CLEANER (UNVERÄNDERT)
# =========================================================

async def abwesenheit_checker():

    await bot.wait_until_ready()

    while not bot.is_closed():

        now = datetime.now()
        to_delete = []

        for user_id, data in abwesende.items():
            try:
                bis = datetime.strptime(data["bis"], "%d.%m.%Y")

                if now >= bis:
                    to_delete.append(user_id)
            except:
                pass

        for user_id in to_delete:
            del abwesende[user_id]

        await asyncio.sleep(60)

# =========================================================
# 🤖 READY EVENT
# =========================================================

@bot.event
async def on_ready():

    await bot.tree.sync(guild=GUILD)

    print(f"🤖 {bot.user} ist online!")

    bot.loop.create_task(abwesenheit_checker())

# =========================================================
# 🚀 START
# =========================================================

bot.run(TOKEN)
