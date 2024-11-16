import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import os
import json

# Charger le token du bot depuis les variables d'environnement
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Données globales
user_choices = {
    "Tank": [],
    "Healer": [],
    "Debuffer": [],
    "Assa": [],
    "DPS": [],
    "Absent": []
}

# Emojis valides pour Discord
role_emojis = {
    "Tank": "🛡️",  # Bouclier
    "Healer": "❤️",  # Cœur
    "Debuffer": "✨",  # Éclat
    "Assa": "⚔️",  # Épées croisées
    "DPS": "🏹",  # Arc
    "Absent": "❌"  # Croix rouge
}

weight_emojis = {
    "Lourd": "🪨",  # Marteau et pioche
    "Moyen": "⚖️",  # Balance
    "Leger": "🍃"  # Feuille
}

weapon_emojis = {
    "SnS": "🛡️",  # Bouclier
    "FnS": "⚙️",  # Engrenage
    "Hatchet": "🪓",  # Hache
    "Spear": "🏹",  # Arc (remplaçant une lance)
    "WH": "🔨",  # Marteau
    "GA": "🪚",  # Scie
    "Bow": "🏹",  # Arc
    "Musket": "🔫",  # Pistolet
    "FS": "🔥",  # Flamme
    "LS": "✨",  # Éclat
    "IG": "❄️",  # Flocon de neige
    "VG": "🌌",  # Vortex spatial
    "Rapier": "🗡️",  # Dague
    "BB": "🔮",  # Boule de cristal
    "GS": "⚔️",  # Épées croisées
}

roles = ["Tank", "Healer", "Debuffer", "Assa", "DPS", "Absent"]
weights = ["Lourd", "Moyen", "Leger"]
weapons = [
    "SnS", "FnS", "Hatchet", "Spear", "WH", "GA", "GS",
    "Bow", "Musket", "FS", "LS", "IG", "VG", "Rapier", "BB"
]


@bot.event
async def on_ready():
    print(f"{bot.user} est connecté et prêt !")
    try:
        await bot.tree.sync()
        print("Commandes synchronisées.")
    except Exception as e:
        print(f"Erreur lors de la synchronisation des commandes : {e}")


@bot.tree.command(name="nextwar", description="Affiche les détails pour la prochaine guerre dans un channel")
@app_commands.describe(
    channel="Le channel où envoyer le message",
    title="Titre personnalisé pour la prochaine guerre (obligatoire)"
)
async def nextwar(interaction: discord.Interaction, channel: discord.TextChannel, title: str):
    global main_message

    if not title.strip():
        await interaction.response.send_message("Le titre est obligatoire et ne peut pas être vide.", ephemeral=True)
        return

    await interaction.response.defer()

    embed = generate_summary_embed(title)

    try:
        main_message = await channel.send(embed=embed, view=SelectionView())
        await interaction.followup.send(
            f"Message envoyé dans {channel.mention} avec le titre : {title}", ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(
            f"Une erreur est survenue lors de l'envoi du message : {e}", ephemeral=True
        )
        print(f"Erreur lors de l'envoi du message : {e}")


def generate_summary_embed(title: str):
    """Génère un embed récapitulatif des inscriptions avec un titre personnalisé."""
    embed = discord.Embed(
        title=title,
        description="Choisissez vos builds, armes, et armures pour la prochaine guerre.",
        color=discord.Color.blurple()
    )

    for role, users in user_choices.items():
        if users:
            user_list = "\n".join(
                [f"- {user[0]} | {user[1]} | {user[2]} + {user[3]}" if role != "Absent" else f"- {user[0]}" for user in users]
            )
        else:
            user_list = "Aucun inscrit"

        embed.add_field(
            name=f"{role_emojis.get(role, '')} {role}",
            value=user_list,
            inline=False
        )

    return embed


class SelectionView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.temp_choices = {}  # Stock temporaire pour chaque utilisateur
        self.add_item(RoleSelect(self))
        self.add_item(WeightSelect(self))
        self.add_item(WeaponSelect1(self))
        self.add_item(WeaponSelect2(self))
        self.add_item(ConfirmButton(self))
        self.add_item(MarkAbsentButton())
        self.add_item(ExportJsonButton())
        self.add_item(ResetButton())


class RoleSelect(discord.ui.Select):
    def __init__(self, selection_view: SelectionView):
        options = [
            discord.SelectOption(
                label=role,
                emoji=role_emojis.get(role, ""),
                description=f"Choisissez {role}"
            )
            for role in roles
        ]
        super().__init__(placeholder="Choisissez un rôle", options=options, min_values=1, max_values=1)
        self.selection_view = selection_view

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        if user_id not in self.selection_view.temp_choices:
            self.selection_view.temp_choices[user_id] = {}
        self.selection_view.temp_choices[user_id]['role'] = self.values[0]
        await interaction.response.defer()


class WeightSelect(discord.ui.Select):
    def __init__(self, selection_view: SelectionView):
        options = [
            discord.SelectOption(
                label=weight,
                emoji=weight_emojis.get(weight, ""),
                description=f"Choisissez un poids {weight.lower()}"
            )
            for weight in weights
        ]
        super().__init__(placeholder="Choisissez le poids de l'armure", options=options, min_values=1, max_values=1)
        self.selection_view = selection_view

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        if user_id not in self.selection_view.temp_choices:
            self.selection_view.temp_choices[user_id] = {}
        self.selection_view.temp_choices[user_id]['weight'] = self.values[0]
        await interaction.response.defer()


class WeaponSelect1(discord.ui.Select):
    def __init__(self, selection_view: SelectionView):
        options = [
            discord.SelectOption(
                label=weapon,
                emoji=weapon_emojis.get(weapon, ""),
                description=f"Première arme : {weapon}"
            )
            for weapon in weapons
        ]
        super().__init__(placeholder="Choisissez votre première arme", options=options, min_values=1, max_values=1)
        self.selection_view = selection_view

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        if user_id not in self.selection_view.temp_choices:
            self.selection_view.temp_choices[user_id] = {}
        
        weapons = self.selection_view.temp_choices[user_id].setdefault('weapons', [])

        if self.values[0] not in weapons:
            weapons.append(self.values[0])

        if len(weapons) > 2:
            weapons = weapons[:2]

        self.selection_view.temp_choices[user_id]['weapons'] = weapons
        await interaction.response.defer()


class WeaponSelect2(discord.ui.Select):
    def __init__(self, selection_view: SelectionView):
        options = [
            discord.SelectOption(
                label=weapon,
                emoji=weapon_emojis.get(weapon, ""),
                description=f"Deuxième arme : {weapon}"
            )
            for weapon in weapons
        ]
        super().__init__(placeholder="Choisissez votre deuxième arme", options=options, min_values=1, max_values=1)
        self.selection_view = selection_view

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        if user_id not in self.selection_view.temp_choices:
            self.selection_view.temp_choices[user_id] = {}

        weapons = self.selection_view.temp_choices[user_id].setdefault('weapons', [])

        if self.values[0] not in weapons:
            weapons.append(self.values[0])

        if len(weapons) > 2:
            weapons = weapons[:2]

        self.selection_view.temp_choices[user_id]['weapons'] = weapons
        await interaction.response.defer()


class ConfirmButton(discord.ui.Button):
    def __init__(self, selection_view: SelectionView):
        super().__init__(label="Confirmer", style=discord.ButtonStyle.green)
        self.selection_view = selection_view

    async def callback(self, interaction: discord.Interaction):
        global main_message

        user_id = interaction.user.id
        user_name = interaction.user.display_name
        choices = self.selection_view.temp_choices.get(user_id, {})

        role = choices.get('role')
        weight = choices.get('weight')
        weapons = choices.get('weapons', [])


        # Validation stricte : rôle, poids et exactement 2 armes différentes
        if not role or not weight or len(weapons) != 2:
            await interaction.response.send_message(
                "Veuillez choisir un rôle, un poids d'armure, et exactement deux armes différentes avant de confirmer.",
                ephemeral=True
            )
            return

        # Supprimer les choix précédents de l'utilisateur dans tous les rôles
        for r, users in user_choices.items():
            user_choices[r] = [u for u in users if u[0] != user_name]

        # Ajouter les nouveaux choix
        user_choices[role].append((user_name, weight, weapons[0], weapons[1]))
        self.selection_view.temp_choices.pop(user_id, None)

        # Mettre à jour le message principal
        if main_message:
            title = main_message.embeds[0].title or "Prochaine guerre"
            await main_message.edit(embed=generate_summary_embed(title))

        await interaction.response.defer()


class MarkAbsentButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Me marquer absent", style=discord.ButtonStyle.red)

    async def callback(self, interaction: discord.Interaction):
        global main_message

        user_name = interaction.user.display_name

        for r, users in user_choices.items():
            user_choices[r] = [u for u in users if u[0] != user_name]

        user_choices["Absent"].append((user_name,))
        await interaction.response.defer()

        if main_message:
            title = main_message.embeds[0].title or "Prochaine guerre"
            await main_message.edit(embed=generate_summary_embed(title))


class ExportJsonButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Exporter JSON", style=discord.ButtonStyle.blurple)

    async def callback(self, interaction: discord.Interaction):
        data = {}
        for role, users in user_choices.items():
            data[role] = [
                {
                    "name": user[0],
                    "weight": user[1] if role != "Absent" else None,
                    "first_weapon": user[2] if role != "Absent" else None,
                    "second_weapon": user[3] if role != "Absent" else None
                }
                for user in users
            ]

        json_file = "war_participants.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        await interaction.response.send_message("Voici le fichier JSON :", ephemeral=True)
        await interaction.followup.send(file=discord.File(json_file))

# Liste des IDs autorisés à utiliser le bouton Reset
authorized_roles = [
    1296149632245567503, # GM
    1296149632233246727, # Admin Discord
    1296149632245567499, # Modo Discord
    1298265423468298312, # Référent
    1296149632245567501, # Officier
    1296149632245567500, # RL
] 

class ResetButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Reset", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        global user_choices, main_message, is_valid_permision
        
        is_valid_permision = False
        # Vérification si l'interaction vient d'une guild
        if interaction.guild is None:
            await interaction.response.send_message(
                "Cette commande ne peut être utilisée qu'à l'intérieur d'un serveur Discord.", ephemeral=True
            )
            return

        # Récupérer le membre
        member = interaction.guild.get_member(interaction.user.id)
        
        
        if member:
            for role in member.roles:
                for r in authorized_roles:
                    if role.id == r:
                        is_valid_permision = True
                        break
        else:
            is_valid_permision = False
            
        # Vérification des permissions par rôles
        if not is_valid_permision:
            await interaction.response.send_message(
                "Vous n'avez pas la permission d'utiliser cette fonction.", ephemeral=True
            )
            return

        # Réinitialisation des données
        user_choices = {role: [] for role in roles}

        # Mise à jour du message principal si disponible
        if main_message:
            title = main_message.embeds[0].title or "Prochaine guerre"
            await main_message.edit(embed=generate_summary_embed(title))

        await interaction.response.send_message("Toutes les inscriptions ont été réinitialisées.", ephemeral=True)



if TOKEN is not None:
    bot.run(TOKEN)
