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
            discord.SelectOption(label="Tank", emoji="🛡️"),
            discord.SelectOption(label="Healer", emoji="💉"),
            discord.SelectOption(label="Debuffer", emoji="🌀"),
            discord.SelectOption(label="Bruiser", emoji="⚔️"),
            discord.SelectOption(label="Assassins", emoji="🔪"),
            discord.SelectOption(label="DPS", emoji="🔥")
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
            discord.SelectOption(label="Léger", emoji="⚡"),   # Symbole pour léger
            discord.SelectOption(label="Moyen", emoji="🏋️"), # Symbole pour moyen
            discord.SelectOption(label="Lourd", emoji="🛡️")  # Symbole pour lourd
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
            discord.SelectOption(label="SnS", description="Épée et Bouclier", emoji="🛡️"),
            discord.SelectOption(label="FnS", description="Hachette et Bouclier", emoji="🪓"),
            discord.SelectOption(label="WH", description="Marteau de Guerre", emoji="🔨"),
            discord.SelectOption(label="GA", description="Hache Double", emoji="🪓"),
            discord.SelectOption(label="Spear", description="Lance", emoji="🔱"),
            discord.SelectOption(label="Hatchet", description="Hachette", emoji="🪓"),
            discord.SelectOption(label="Bow", description="Arc", emoji="🏹"),
            discord.SelectOption(label="Musket", description="Mousquet", emoji="🔫"),
            discord.SelectOption(label="FS", description="Bâton de Feu", emoji="🔥"),
            discord.SelectOption(label="LS", description="Bâton de Vie", emoji="💚"),
            discord.SelectOption(label="IG", description="Gantelet de Glace", emoji="❄️"),
            discord.SelectOption(label="VG", description="Gantelet du Néant", emoji="⚫"),
            discord.SelectOption(label="Rapier", description="Rapière", emoji="🗡️"),
            discord.SelectOption(label="BB", description="Tromblon", emoji="🎇"),
            discord.SelectOption(label="GS", description="Grande Épée", emoji="⚔️")
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
    """Met à jour le message de récapitulatif avec des émojis pour chaque rôle répartis sur deux colonnes."""
    war = wars[war_id]

    async with war.recap_lock:
        # Extraire les IDs uniques
        unique_users = set()
        for participants in war.registrations.values():
            unique_users.update(p["discord_id"] for p in participants)

        total_inscriptions = len(unique_users)  # Nombre d'utilisateurs uniques

        embed = discord.Embed(
            title=f"{war.name} (ID: {war.id})   \u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003.",
            description=f"Total des inscrits : **{total_inscriptions}**",
            color=discord.Color.blue()
        )

        # Ajouter des émojis pour chaque rôle
        emoji_mapping = {
            "Tank": "🛡️",      # Bouclier
            "Healer": "💉",    # Seringue ou soin
            "Debuffer": "🌀",  # Vortex
            "Bruiser": "⚔️",   # Épées croisées
            "Assassins": "🔪", # Couteau
            "DPS": "🔥"        # Feu
        }

        # Diviser les rôles en deux colonnes
        roles = ["Tank", "Healer", "Debuffer", "Bruiser", "Assassins", "DPS"]
        column_1 = []
        column_2 = []

        for i, role in enumerate(roles):
            participants = war.registrations[role]
            emoji = emoji_mapping.get(role, "")  # Ajoute l'émoji associé

            # Total des participants pour ce rôle
            role_total = len(participants)

            # Contenu des participants
            content = "\n".join(
                [f"**{p['name']}** ({p['weight']} | {p['weapon']} + {p['weapon_2']})" for p in participants]
            ) or "*Aucun inscrit*"

            # Ajouter l'émoji, le rôle et le total
            role_header = f"{emoji} **{role} ({role_total})**"
            role_content = f"{role_header}\n{content}"

            # Répartir les rôles entre les colonnes
            if i % 2 == 0:  # Rôles pairs dans la colonne 1
                column_1.append(role_content)
            else:           # Rôles impairs dans la colonne 2
                column_2.append(role_content)

        # Ajouter les colonnes au message embed
        embed.add_field(name="", value="\n\n".join(column_1), inline=True)
        embed.add_field(name="", value="\n\n".join(column_2), inline=True)

        # Éditer ou envoyer le message récapitulatif
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
