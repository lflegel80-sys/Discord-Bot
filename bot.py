import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import asyncio
import os

# ---------------- TOKEN ----------------
TOKEN = os.getenv("TOKEN")

# ---------------- GUILD ----------------
GUILD_ID = 1505354242276462632
GUILD = discord.Object(id=GUILD_ID)

# ---------------- BOT ----------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- STORAGE ----------------
events = {}
abwesende = {}

# =========================================================
# 🚗 EVENT SYSTEM (Kolonnenfahrt etc.)
# =========================================================

class EventView(discord.ui.View):

    def __init__(self, event_name):
        super().__init__(timeout=None)
        self.event_name = event_name

        if event_name not in events:
            events[event_name] = {
                "dabei": [],
                "nicht": []
            }

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
# 📌 EVENT COMMAND
# =========================================================

@bot.tree.command(name="event", description="Erstellt ein Event (z.B. Kolonnenfahrt)", guild=GUILD)
async def event(interaction: discord.Interaction, name: str):

    events[name] = {
        "dabei": [],
        "nicht": []
    }

    embed = discord.Embed(
        title=f"🚗 Event: {name}",
        description="Klicke unten auf einen Button:",
        color=discord.Color.gold()
    )

    embed.add_field(name="🟢 Dabei", value="Noch niemand", inline=True)
    embed.add_field(name="🔴 Kann nicht", value="Noch niemand", inline=True)

    await interaction.response.send_message(embed=embed, view=EventView(name))

# =========================================================
# 📌 ABWESENHEIT
# =========================================================

@bot.tree.command(name="abwesenheit", description="Melde dich abwesend", guild=GUILD)
async def abwesenheit(interaction: discord.Interaction, von: str, bis: str, grund: str):

    abwesende[interaction.user.id] = {
        "name": interaction.user.name,
        "von": von,
        "bis": bis,
        "grund": grund
    }

    await interaction.response.send_message(
        f"📌 Abwesenheit gespeichert bis {bis}"
    )

# =========================================================
# 📋 ABWESEND LISTE
# =========================================================

@bot.tree.command(name="abwesend", description="Zeigt alle Abwesenden", guild=GUILD)
async def abwesend(interaction: discord.Interaction):

    if not abwesende:
        await interaction.response.send_message("✅ Niemand abwesend.")
        return

    text = ""

    for user_id, data in abwesende.items():

        try:
            user = await bot.fetch_user(user_id)

            text += (
                f"**{user.name}**\n"
                f"📅 {data['von']} - {data['bis']}\n"
                f"📌 {data['grund']}\n\n"
            )
        except:
            pass

    embed = discord.Embed(
        title="📋 Abwesende Mitglieder",
        description=text,
        color=discord.Color.red()
    )

    await interaction.response.send_message(embed=embed)

# =========================================================
# 🔄 AUTO ABWESENHEIT CLEANER
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
            print(f"🧹 Abwesenheit gelöscht: {user_id}")

        await asyncio.sleep(60)

# =========================================================
# 🤖 READY EVENT
# =========================================================

@bot.event
async def on_ready():

    try:
        synced = await bot.tree.sync(guild=GUILD)
        print(f"✅ {len(synced)} Slash Commands synchronisiert.")
    except Exception as e:
        print(e)

    print(f"🤖 {bot.user} ist online!")

    bot.loop.create_task(abwesenheit_checker())

# =========================================================
# 🚀 START
# =========================================================

bot.run(TOKEN)
