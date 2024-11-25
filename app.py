import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select
import asyncio
import json
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Initialisation du bot avec les intents nécessaires
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)

# Structure pour stocker les données des guerres
wars = {}  # Dictionnaire où chaque clé est un identifiant de guerre


class War:
    """Classe représentant une guerre."""
    def __init__(self, id):
        self.id = id
        self.name = f"Guerre {id}"  # Nom par défaut basé sur l'ID
        self.registrations = {
            "Tank": [],
            "Healer": [],
            "Debuffer": [],
            "Bruiser": [],
            "Assassins": [],
            "DPS": []
        }
        self.recap_message = None
        self.recap_lock = asyncio.Lock()


class RegistrationView(View):
    def __init__(self, war_id):
        super().__init__(timeout=None)
        self.war_id = war_id
        self.add_item(RoleSelect(war_id))


class RoleSelect(Select):
    def __init__(self, war_id):
        super().__init__(placeholder="Choisissez un rôle", options=[
            discord.SelectOption(label="Tank", description=""),
            discord.SelectOption(label="Healer", description=""),
            discord.SelectOption(label="Debuffer", description=""),
            discord.SelectOption(label="Bruiser", description=""),
            discord.SelectOption(label="Assassins", description=""),
            discord.SelectOption(label="DPS", description="")
        ])
        self.war_id = war_id

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            role = self.values[0]

            # Inclure le discord_id dans les données utilisateur
            user_data = {
                "name": interaction.user.display_name,
                "discord_id": interaction.user.id,
                "role": role
            }

            # Transition vers la sélection du poids d'armure
            armor_view = ArmorWeightView(self.war_id, user_data)
            await interaction.followup.send(
                content=f"Vous avez sélectionné : **{role}**.\nChoisissez votre poids d'armure :",
                view=armor_view,
                ephemeral=True
            )
        except Exception as e:
            print(f"Erreur dans RoleSelect callback : {e}")
            await interaction.followup.send("Une erreur est survenue.", ephemeral=True)


class ArmorWeightView(View):
    def __init__(self, war_id, user_data):
        super().__init__(timeout=None)
        self.add_item(ArmorWeightSelect(war_id, user_data))


class ArmorWeightSelect(Select):
    def __init__(self, war_id, user_data):
        super().__init__(placeholder="Choisissez un poids d'armure", options=[
            discord.SelectOption(label="Léger", description=""),
            discord.SelectOption(label="Moyen", description=""),
            discord.SelectOption(label="Lourd", description="")
        ])
        self.war_id = war_id
        self.user_data = user_data

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            self.user_data["armor"] = self.values[0]

            # Transition vers la sélection de la première arme
            weapon1_view = WeaponSelectView(self.war_id, self.user_data, "Arme 1")
            await interaction.followup.send(
                content="Choisissez votre première arme :",
                view=weapon1_view,
                ephemeral=True
            )
        except Exception as e:
            print(f"Erreur dans ArmorWeightSelect callback : {e}")
            await interaction.followup.send("Une erreur est survenue.", ephemeral=True)


class WeaponSelectView(View):
    def __init__(self, war_id, user_data, placeholder):
        super().__init__(timeout=None)
        self.add_item(WeaponSelect(war_id, user_data, placeholder))


class WeaponSelect(Select):
    def __init__(self, war_id, user_data, placeholder):
        super().__init__(placeholder=placeholder, options=[
            discord.SelectOption(label="SnS", description="Épée et Bouclier"),
            discord.SelectOption(label="FnS", description="Hachette et Bouclier"),
            discord.SelectOption(label="WH", description="Marteau de Guerre"),
            discord.SelectOption(label="GA", description="Hache Double"),
            discord.SelectOption(label="Spear", description="Lance"),
            discord.SelectOption(label="Hatchet", description="Hachette"),
            discord.SelectOption(label="Bow", description="Arc"),
            discord.SelectOption(label="Musket", description="Mousquet"),
            discord.SelectOption(label="FS", description="Bâton de Feu"),
            discord.SelectOption(label="LS", description="Bâton de Vie"),
            discord.SelectOption(label="IG", description="Gantelet de Glace"),
            discord.SelectOption(label="VG", description="Gantelet du Néant"),
            discord.SelectOption(label="Rapier", description="Rapière"),
            discord.SelectOption(label="BB", description="Tromblon"),
            discord.SelectOption(label="GS", description="Grande Épée")
        ])
        self.war_id = war_id
        self.user_data = user_data

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            if "weapon1" not in self.user_data:
                self.user_data["weapon1"] = self.values[0]
                weapon2_view = WeaponSelectView(self.war_id, self.user_data, "Arme 2")
                await interaction.followup.send(
                    content="Choisissez votre seconde arme :",
                    view=weapon2_view,
                    ephemeral=True
                )
            else:
                if self.values[0] == self.user_data["weapon1"]:
                    await interaction.followup.send(
                        "Vous ne pouvez pas sélectionner la même arme deux fois.",
                        ephemeral=True
                    )
                    return

                self.user_data["weapon2"] = self.values[0]

                # Ajout final aux inscriptions
                war = wars[self.war_id]
                war.registrations[self.user_data["role"]].append({
                    "name": self.user_data["name"],
                    "discord_id": self.user_data["discord_id"],
                    "weight": self.user_data["armor"],
                    "weapon": self.user_data["weapon1"],
                    "weapon_2": self.user_data["weapon2"]
                })

                # Mise à jour immédiate du récapitulatif
                await update_recap_message(self.war_id, interaction.channel)
                await interaction.followup.send(
                    "Votre inscription a été enregistrée !",
                    ephemeral=True
                )
        except Exception as e:
            print(f"Erreur dans WeaponSelect callback : {e}")
            await interaction.followup.send("Une erreur est survenue.", ephemeral=True)


async def update_recap_message(war_id, channel):
    """Met à jour le message de récapitulatif sous forme d'embed avec compteurs."""
    war = wars[war_id]

    async with war.recap_lock:
        # Extraire les IDs uniques
        unique_users = set()
        for participants in war.registrations.values():
            unique_users.update(p["discord_id"] for p in participants)

        total_inscriptions = len(unique_users)  # Nombre d'utilisateurs uniques

        embed = discord.Embed(
            title=f"{war.name} (ID: {war.id})",
            description=f"Total des inscrits : **{total_inscriptions}**",
            color=discord.Color.blue()
        )

        for role, participants in war.registrations.items():
            role_count = len(participants)
            if participants:
                value = "\n".join(
                    [f"• **{p['name']}** | {p['weight']} | {p['weapon']} + {p['weapon_2']}" for p in participants]
                )
            else:
                value = "*Aucun inscrit*"
            embed.add_field(
                name=f"{role} ({role_count})",  # Ajout du compteur par rôle
                value=value,
                inline=False
            )

        if war.recap_message:
            await war.recap_message.edit(embed=embed)
        else:
            war.recap_message = await channel.send(embed=embed)


@bot.tree.command(name="nextwar", description="Créer une guerre interactive.")
@app_commands.describe(title="Titre de la guerre (facultatif)")
async def nextwar(interaction: discord.Interaction, title: str = None):
    await interaction.response.defer()

    war_id = len(wars) + 1
    war = War(war_id)

    war.name = title if title else f"Guerre #{war_id}"

    wars[war_id] = war

    view = RegistrationView(war_id)

    war.recap_message = await interaction.channel.send(
        "Choisissez votre rôle ci-dessous :", view=view
    )
    await update_recap_message(war_id, interaction.channel)


@bot.tree.command(name="export_json", description="Exporter les données d'une guerre au format JSON.")
@app_commands.describe(war_id="L'ID de la guerre à exporter")
async def export_json(interaction: discord.Interaction, war_id: int):
    await interaction.response.defer(ephemeral=True)

    if war_id not in wars:
        await interaction.followup.send(f"Aucune guerre trouvée avec l'ID {war_id}.", ephemeral=True)
        return

    war = wars[war_id]
    war_data = {
        "id": war.id,
        "name": war.name,
        "registrations": war.registrations
    }
    filename = f"war_{war_id}.json"

    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(war_data, f, ensure_ascii=False, indent=4)

        await interaction.followup.send(
            content=f"Données de la guerre **{war.name}** exportées avec succès.",
            file=discord.File(filename),
            ephemeral=True
        )
    except Exception as e:
        print(f"Erreur lors de l'exportation : {e}")
        await interaction.followup.send("Erreur lors de l'exportation des données.", ephemeral=True)
    finally:
        if os.path.exists(filename):
            os.remove(filename)


@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
        print(f"Bot connecté et commandes synchronisées : {bot.user}")
    except Exception as e:
        print(f"Erreur lors de la synchronisation des commandes : {e}")


if BOT_TOKEN:
    bot.run(BOT_TOKEN)
else:
    print("Le jeton du bot est introuvable. Vérifiez votre fichier .env.")
