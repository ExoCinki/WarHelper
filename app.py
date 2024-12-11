import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select
import asyncio
import json
import os
from dotenv import load_dotenv


load_dotenv()
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")


intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)

# Gestions des tableau de guerres
wars = {}  


# Role IDs autorisés pour les commandes
ALLOWED_ROLE_IDS = [ 
    1311100972113858600, # Gouverneur
    1311101366063730748, # Consul
    1311101618627936329, # Officier
    1311126111249371218 # RaidLead
] 


def has_allowed_role():
    async def predicate(ctx):
        if ctx.author.guild_permissions.administrator:
            return True
        user_role_ids = [role.id for role in ctx.author.roles]
        return any(role_id in ALLOWED_ROLE_IDS for role_id in user_role_ids)
    return commands.check(predicate)

class War:
    """Classe représentant une guerre."""
    def __init__(self, id):
        self.id = id
        self.name = f"Guerre {id}" 
        self.registrations = {
            "Tank": [],
            "Healer": [],
            "Debuffer": [],
            "Bruiser": [],
            "Assassins": [],
            "DPS": [],
            "Absent": []
        }
        self.recap_message = None
        self.recap_lock = asyncio.Lock()
        self.user_specs = {}


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
            discord.SelectOption(label="DPS", emoji="🔥"),
            discord.SelectOption(label="Absent", emoji="🚫")  # Nouvelle option "Absent"
        ])
        self.war_id = war_id

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            role = self.values[0]

            war = wars[self.war_id]
            user_id = interaction.user.id

            
            if role != "Absent":
                war.registrations["Absent"] = [
                    participant for participant in war.registrations["Absent"]
                    if participant["discord_id"] != user_id
                ]

            
            if role == "Absent":
                for role_name, participants in war.registrations.items():
                    war.registrations[role_name] = [
                        participant for participant in participants
                        if participant["discord_id"] != user_id
                    ]

                
                war.registrations[role].append({
                    "name": interaction.user.display_name,
                    "discord_id": user_id,
                    "spec": 1  
                })

                await update_recap_message(self.war_id, interaction.channel)
                await interaction.followup.send(
                    f"Vous avez été marqué comme **Absent** pour la guerre.",
                    ephemeral=True
                )
                return

            
            if user_id not in war.user_specs:
                war.user_specs[user_id] = 1

            spec = war.user_specs[user_id]
            war.user_specs[user_id] += 1

            user_data = {
                "name": interaction.user.display_name,
                "discord_id": user_id,
                "role": role,
                "spec": spec
            }

           
            armor_view = ArmorWeightView(self.war_id, user_data)
            await interaction.followup.send(
                content=f"Vous avez sélectionné : **{role}** (spec: {spec}).\nChoisissez votre poids d'armure :",
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
            discord.SelectOption(label="Léger", emoji="⚡"),   
            discord.SelectOption(label="Moyen", emoji="🏋️"),
            discord.SelectOption(label="Lourd", emoji="🛡️") 
        ])
        self.war_id = war_id
        self.user_data = user_data

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            self.user_data["armor"] = self.values[0]

            
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
            discord.SelectOption(label="FnS", description="Fléau et Bouclier", emoji="🪓"),
            discord.SelectOption(label="WH", description="Marteau", emoji="🔨"),
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
            discord.SelectOption(label="GS", description="Glaive", emoji="⚔️")
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
                    "weapon_2": self.user_data["weapon2"],
                    "spec": self.user_data["spec"]
                })

               
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
        unique_users = set()
        for participants in war.registrations.values():
            unique_users.update(p["discord_id"] for p in participants)

        total_inscriptions = len(unique_users)

        embed = discord.Embed(
            title=f"{war.name} (ID: {war.id})   \u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003\u2003.",
            description=f"Total des inscrits : **{total_inscriptions}**",
            color=discord.Color.blue()
        )

        emoji_mapping = {
            "Tank": "🛡️",
            "Healer": "💉",
            "Debuffer": "🌀",
            "Bruiser": "⚔️",
            "Assassins": "🔪",
            "DPS": "🔥",
            "Absent": "🚫"
        }

        roles = ["Tank", "Healer", "Debuffer", "Bruiser", "Assassins", "DPS", "Absent"]
        column_1 = []
        column_2 = []

        for i, role in enumerate(roles):
            participants = war.registrations[role]
            emoji = emoji_mapping.get(role, "")

            role_total = len(participants)

            
            content = "\n".join(
                [
                    f"**{p['name']}**"
                    + (f" ({p.get('weight', 'N/A')} | {p.get('weapon', 'N/A')} + {p.get('weapon_2', 'N/A')})" if role != "Absent" else "")
                    for p in participants
                ]
            ) or "*Aucun inscrit*"

            role_header = f"{emoji} **{role} ({role_total})**"
            role_content = f"{role_header}\n{content}"

            
            if i % 2 == 0:
                column_1.append(role_content)
            else:
                column_2.append(role_content)

        
        embed.add_field(name="", value="\n\n".join(column_1), inline=True)
        embed.add_field(name="", value="\n\n".join(column_2), inline=True)

        
        if war.recap_message:
            await war.recap_message.edit(embed=embed)
        else:
            war.recap_message = await channel.send(embed=embed)







@bot.tree.command(name="nextwar", description="Créer une guerre interactive.")
@has_allowed_role()
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
@has_allowed_role()
@app_commands.describe(war_id="L'ID de la guerre à exporter")
async def export_json(interaction: discord.Interaction, war_id: int):
    await interaction.response.defer(ephemeral=True)

    if war_id not in wars:
        await interaction.followup.send(f"Aucune guerre trouvée avec l'ID {war_id}.", ephemeral=True)
        return

    war = wars[war_id]

    filtered_registrations = {
        role: participants
        for role, participants in war.registrations.items()
        if role != "Absent"
    }

    war_data = {
        "id": war.id,
        "name": war.name,
        "registrations": filtered_registrations
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


@bot.tree.command(name="ping", description="Ping les personnes avec un rôle spécifique qui ne sont pas inscrites.")
@has_allowed_role()
@app_commands.describe(war_id="L'ID de la guerre pour vérifier les inscriptions")
async def ping(interaction: discord.Interaction, war_id: int):
    await interaction.response.defer()  # Pas d'éphémère ici, on prépare une réponse publique

    # Vérifier si la guerre existe
    if war_id not in wars:
        await interaction.followup.send(f"Aucune guerre trouvée avec l'ID {war_id}.")
        return

    war = wars[war_id]

    # ID du rôle à vérifier
    ROLE_ID_TO_CHECK = 1311102143012405352  

    # Récupérer tous les membres ayant le rôle
    guild = interaction.guild
    role = guild.get_role(ROLE_ID_TO_CHECK)

    if not role:
        await interaction.followup.send(f"Le rôle avec l'ID {ROLE_ID_TO_CHECK} est introuvable.")
        return

    # Collecte des membres ayant ce rôle
    role_members = set(member.id for member in role.members)

    # Collecte des membres déjà inscrits
    registered_members = set(
        participant["discord_id"]
        for participants in war.registrations.values()
        for participant in participants
    )

    # Membres non inscrits ayant le rôle
    unregistered_members = role_members - registered_members

    if not unregistered_members:
        await interaction.followup.send("Tous les membres avec ce rôle sont inscrits.")
        return

    # Construire les mentions par lots
    mentions = [f"<@{member_id}>" for member_id in unregistered_members]
    chunks = [mentions[i:i+50] for i in range(0, len(mentions), 50)]  # 50 mentions par message max

    
    first_message = f"Les membres suivants ne sont pas inscrits à la guerre **{war.name}** :"
    await interaction.channel.send(first_message)

    
    for chunk in chunks:
        await interaction.channel.send(' '.join(chunk))


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
