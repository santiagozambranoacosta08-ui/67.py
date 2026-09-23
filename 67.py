import asyncio
import os
import random
import re
import json
from collections import defaultdict, deque
from datetime import timedelta

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands


# =========================================================
# CONFIGURACION
# =========================================================

TOKEN = os.getenv("MTU1MjExNjIyNjUzNTE5NDY4NA.GYmJTD.Vx1_V9eICQroSHccq4qDi1EVLKIoeSg95_qN5I", "MTU1MjExNjIyNjUzNTE5NDY4NA.GYmJTD.Vx1_V9eICQroSHccq4qDi1EVLKIoeSg95_qN5I")

OWNER_ID = 1407748413239463956

DATA_FILE = "santy_data.json"


# =========================================================
# INTENTS
# =========================================================

intents = discord.Intents.default()

intents.members = True
intents.message_content = True
intents.guilds = True


bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)


# =========================================================
# DATOS
# =========================================================

data = {
    "guilds": {},
    "warnings": {}
}


spam_cache = defaultdict(
    lambda: deque(maxlen=8)
)


# =========================================================
# CARGAR Y GUARDAR DATOS
# =========================================================

def cargar_datos():

    global data

    if not os.path.exists(DATA_FILE):
        return

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as archivo:

            data = json.load(archivo)

    except Exception:

        data = {
            "guilds": {},
            "warnings": {}
        }


def guardar_datos():

    try:

        with open(
            DATA_FILE,
            "w",
            encoding="utf-8"
        ) as archivo:

            json.dump(
                data,
                archivo,
                indent=4,
                ensure_ascii=False
            )

    except Exception as error:

        print(
            "Error guardando datos:",
            error
        )


def configuracion_servidor(guild_id):

    guild_id = str(guild_id)

    if guild_id not in data["guilds"]:

        data["guilds"][guild_id] = {

            "antilink": False,

            "antispam": False,

            "automod": False,

            "filter": False,

            "log_channel": None,

            "welcome_channel": None,

            "autorole": None
        }

        guardar_datos()

    return data["guilds"][guild_id]


cargar_datos()


# =========================================================
# PERMISO DEL DUEÑO
# =========================================================

async def verificar_dueno(interaction):

    if interaction.user.id != OWNER_ID:

        await interaction.response.send_message(
            "❌ No tienes permiso para usar este comando.",
            ephemeral=True
        )

        return False

    return True


async def responder_ok(interaction):

    if not interaction.response.is_done():

        await interaction.response.send_message(
            "OK",
            ephemeral=True
        )


# =========================================================
# LOGS
# =========================================================

async def enviar_log(
    guild,
    titulo,
    descripcion
):

    if guild is None:
        return

    config = configuracion_servidor(
        guild.id
    )

    canal_id = config.get(
        "log_channel"
    )

    if not canal_id:
        return

    canal = guild.get_channel(
        canal_id
    )

    if canal is None:
        return

    embed = discord.Embed(
        title=titulo,
        description=descripcion,
        timestamp=discord.utils.utcnow()
    )

    try:

        await canal.send(
            embed=embed
        )

    except Exception:

        pass


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    try:

        await bot.tree.sync()

    except Exception as error:

        print(
            "Error sincronizando comandos:",
            error
        )

    print(
        "========================================"
    )

    print(
        "S4NTY BOT INICIADO"
    )

    print(
        "Bot:",
        bot.user
    )

    print(
        "ID:",
        bot.user.id
    )

    print(
        "Servidores:",
        len(bot.guilds)
    )

    print(
        "========================================"
    )


# =========================================================
# ANTI-LINK / ANTI-SPAM / AUTOMOD
# =========================================================

URL_REGEX = re.compile(
    r"(https?://|www\.|discord\.gg/|discord\.com/invite/)",
    re.IGNORECASE
)


BAD_WORDS = {

    "palabramala",

    "insulto",

    "spamword"
}


@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # DM
    if message.guild is None:

        await bot.process_commands(
            message
        )

        return

    config = configuracion_servidor(
        message.guild.id
    )

    usuario_id = message.author.id


    # -----------------------------------------------------
    # ANTI-SPAM
    # -----------------------------------------------------

    if config.get("antispam"):

        ahora = (
            discord.utils.utcnow()
            .timestamp()
        )

        clave = (
            message.guild.id,
            usuario_id
        )

        spam_cache[clave].append(
            ahora
        )

        recientes = [

            tiempo

            for tiempo in spam_cache[clave]

            if ahora - tiempo <= 5
        ]

        if len(recentes) >= 6:

            try:

                await message.delete()

            except Exception:

                pass

            try:

                await message.channel.send(
                    f"{message.author.mention}, no hagas spam.",
                    delete_after=5
                )

            except Exception:

                pass

            await enviar_log(
                message.guild,
                "🚨 Anti-Spam",
                f"Usuario: {message.author.mention}"
            )

            return


    # -----------------------------------------------------
    # ANTI-LINK
    # -----------------------------------------------------

    if config.get("antilink"):

        if URL_REGEX.search(
            message.content
        ):

            if message.author.id != OWNER_ID:

                try:

                    await message.delete()

                except Exception:

                    pass

                try:

                    await message.channel.send(
                        f"{message.author.mention}, "
                        "los enlaces están bloqueados.",
                        delete_after=5
                    )

                except Exception:

                    pass

                return


    # -----------------------------------------------------
    # AUTOMOD
    # -----------------------------------------------------

    if config.get("automod"):

        texto = message.content.lower()

        if (
            "@everyone" in texto
            or
            "@here" in texto
        ):

            if message.author.id != OWNER_ID:

                try:

                    await message.delete()

                except Exception:

                    pass

                try:

                    await message.channel.send(
                        f"{message.author.mention}, "
                        "esa mención está bloqueada.",
                        delete_after=5
                    )

                except Exception:

                    pass

                return


    # -----------------------------------------------------
    # FILTRO
    # -----------------------------------------------------

    if config.get("filter"):

        texto = message.content.lower()

        if any(
            palabra in texto
            for palabra in BAD_WORDS
        ):

            if message.author.id != OWNER_ID:

                try:

                    await message.delete()

                except Exception:

                    pass

                try:

                    await message.channel.send(
                        f"{message.author.mention}, "
                        "ese mensaje fue bloqueado.",
                        delete_after=5
                    )

                except Exception:

                    pass

                return


    await bot.process_commands(
        message
    )


# =========================================================
# BIENVENIDA Y AUTOROL
# =========================================================

@bot.event
async def on_member_join(member):

    config = configuracion_servidor(
        member.guild.id
    )

    canal_id = config.get(
        "welcome_channel"
    )

    if canal_id:

        canal = member.guild.get_channel(
            canal_id
        )

        if canal:

            try:

                await canal.send(
                    f"👋 Bienvenido/a "
                    f"{member.mention} a "
                    f"**{member.guild.name}**."
                )

            except Exception:

                pass


    rol_id = config.get(
        "autorole"
    )

    if rol_id:

        rol = member.guild.get_role(
            rol_id
        )

        if rol:

            try:

                await member.add_roles(
                    rol,
                    reason="Autorol S4NTY BOT"
                )

            except Exception:

                pass


# =========================================================
# SAY
# SERVIDOR + DM
# =========================================================

@bot.tree.command(
    name="say",
    description="Hace que el bot envíe un mensaje"
)
@app_commands.allowed_contexts(
    guilds=True,
    dms=True,
    private_channels=True
)
@app_commands.allowed_installs(
    guilds=True,
    users=True
)
async def say(
    interaction,
    mensaje: str
):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )

    try:

        await interaction.followup.send(
            mensaje
        )

    except Exception as error:

        print(
            "Error en /say:",
            error
        )


# =========================================================
# BAN
# =========================================================

@bot.tree.command(
    name="ban",
    description="Banea a un usuario"
)
async def ban(
    interaction,
    miembro: discord.Member,
    razon: str = "Sin razón"
):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )

    try:

        await miembro.ban(
            reason=razon
        )

        await enviar_log(
            interaction.guild,
            "🔨 Usuario baneado",
            f"Usuario: {miembro.mention}\n"
            f"Razón: {razon}"
        )

        await interaction.followup.send(
            f"🔨 {miembro.mention} fue baneado."
        )

    except Exception as error:

        await interaction.followup.send(
            f"No pude banear al usuario: {error}"
        )


# =========================================================
# UNBAN
# =========================================================

@bot.tree.command(
    name="unban",
    description="Quita el baneo de un usuario"
)
async def unban(
    interaction,
    usuario_id: str
):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )

    try:

        usuario = await bot.fetch_user(
            int(usuario_id)
        )

        await interaction.guild.unban(
            usuario
        )

        await interaction.followup.send(
            f"✅ Baneo quitado para {usuario}."
        )

    except Exception as error:

        await interaction.followup.send(
            f"No pude quitar el baneo: {error}"
        )


# =========================================================
# KICK
# =========================================================

@bot.tree.command(
    name="kick",
    description="Expulsa a un usuario"
)
async def kick(
    interaction,
    miembro: discord.Member,
    razon: str = "Sin razón"
):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )

    try:

        await miembro.kick(
            reason=razon
        )

        await enviar_log(
            interaction.guild,
            "👢 Usuario expulsado",
            f"Usuario: {miembro.mention}\n"
            f"Razón: {razon}"
        )

        await interaction.followup.send(
            f"👢 {miembro.mention} fue expulsado."
        )

    except Exception as error:

        await interaction.followup.send(
            f"No pude expulsar al usuario: {error}"
        )


# =========================================================
# TIMEOUT
# =========================================================

@bot.tree.command(
    name="timeout",
    description="Silencia temporalmente a un usuario"
)
async def timeout(
    interaction,
    miembro: discord.Member,
    minutos: int,
    razon: str = "Sin razón"
):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )

    if minutos < 1 or minutos > 40320:

        await interaction.followup.send(
            "Los minutos deben estar entre 1 y 40320."
        )

        return

    try:

        await miembro.timeout(
            timedelta(
                minutes=minutos
            ),
            reason=razon
        )

        await interaction.followup.send(
            f"🔇 {miembro.mention} fue silenciado "
            f"durante {minutos} minutos."
        )

    except Exception as error:

        await interaction.followup.send(
            f"No pude aplicar el silencio: {error}"
        )


# =========================================================
# WARN
# =========================================================

@bot.tree.command(
    name="warn",
    description="Advierte a un usuario"
)
async def warn(
    interaction,
    miembro: discord.Member,
    razon: str = "Sin razón"
):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )

    servidor = str(
        interaction.guild.id
    )

    usuario = str(
        miembro.id
    )

    if servidor not in data["warnings"]:

        data["warnings"][servidor] = {}


    if usuario not in data["warnings"][servidor]:

        data["warnings"][servidor][usuario] = []


    data["warnings"][servidor][usuario].append({

        "razon": razon

    })


    guardar_datos()


    await interaction.followup.send(
        f"⚠️ {miembro.mention} recibió "
        f"una advertencia.\n"
        f"Razón: {razon}"
    )


# =========================================================
# WARNINGS
# =========================================================

@bot.tree.command(
    name="warnings",
    description="Muestra las advertencias"
)
async def warnings(
    interaction,
    miembro: discord.Member
):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )

    servidor = str(
        interaction.guild.id
    )

    usuario = str(
        miembro.id
    )

    lista = data["warnings"].get(
        servidor,
        {}
    ).get(
        usuario,
        []
    )


    if not lista:

        await interaction.followup.send(
            f"{miembro.mention} no tiene advertencias."
        )

        return


    texto = []

    for numero, advertencia in enumerate(
        lista,
        1
    ):

        texto.append(
            f"{numero}. {advertencia['razon']}"
        )


    await interaction.followup.send(
        f"⚠️ Advertencias de "
        f"{miembro.mention}:\n"
        +
        "\n".join(texto)
    )


# =========================================================
# CLEAR
# =========================================================

@bot.tree.command(
    name="clear",
    description="Elimina mensajes"
)
async def clear(
    interaction,
    cantidad: int
):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )

    if cantidad < 1 or cantidad > 100:

        await interaction.followup.send(
            "La cantidad debe estar entre 1 y 100."
        )

        return


    if not isinstance(
        interaction.channel,
        discord.TextChannel
    ):

        await interaction.followup.send(
            "Este comando solo funciona "
            "en canales de texto."
        )

        return


    try:

        mensajes = await interaction.channel.purge(
            limit=cantidad
        )

        await interaction.followup.send(
            f"🧹 Se eliminaron "
            f"{len(mensajes)} mensajes.",
            delete_after=5
        )

    except Exception as error:

        await interaction.followup.send(
            f"No pude eliminar los mensajes: {error}"
        )


# =========================================================
# LOCK
# =========================================================

@bot.tree.command(
    name="lock",
    description="Bloquea el canal"
)
async def lock(interaction):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )

    if interaction.guild is None:

        await interaction.followup.send(
            "Este comando solo funciona en servidores."
        )

        return


    try:

        permiso = interaction.channel.overwrites_for(
            interaction.guild.default_role
        )

        permiso.send_messages = False

        await interaction.channel.set_permissions(
            interaction.guild.default_role,
            overwrite=permiso
        )

        await interaction.followup.send(
            "🔒 Canal bloqueado."
        )

    except Exception as error:

        await interaction.followup.send(
            f"No pude bloquear el canal: {error}"
        )


# =========================================================
# UNLOCK
# =========================================================

@bot.tree.command(
    name="unlock",
    description="Desbloquea el canal"
)
async def unlock(interaction):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )

    if interaction.guild is None:

        await interaction.followup.send(
            "Este comando solo funciona en servidores."
        )

        return


    try:

        permiso = interaction.channel.overwrites_for(
            interaction.guild.default_role
        )

        permiso.send_messages = True

        await interaction.channel.set_permissions(
            interaction.guild.default_role,
            overwrite=permiso
        )

        await interaction.followup.send(
            "🔓 Canal desbloqueado."
        )

    except Exception as error:

        await interaction.followup.send(
            f"No pude desbloquear el canal: {error}"
        )


# =========================================================
# SLOWMODE
# =========================================================

@bot.tree.command(
    name="slowmode",
    description="Configura el modo lento"
)
async def slowmode(
    interaction,
    segundos: int
):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )

    if segundos < 0 or segundos > 21600:

        await interaction.followup.send(
            "Los segundos deben estar entre 0 y 21600."
        )

        return


    try:

        await interaction.channel.edit(
            slowmode_delay=segundos
        )

        await interaction.followup.send(
            f"🐌 Modo lento: "
            f"{segundos} segundos."
        )

    except Exception as error:

        await interaction.followup.send(
            f"No pude configurar el modo lento: {error}"
        )


# =========================================================
# ANTI-LINK
# =========================================================

@bot.tree.command(
    name="antilink",
    description="Activa o desactiva el Anti-Link"
)
async def antilink(
    interaction,
    estado: bool
):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )

    config = configuracion_servidor(
        interaction.guild.id
    )

    config["antilink"] = estado

    guardar_datos()

    texto = (
        "activado"
        if estado
        else
        "desactivado"
    )

    await interaction.followup.send(
        f"🔗 Anti-Link {texto}."
    )


# =========================================================
# ANTI-SPAM
# =========================================================

@bot.tree.command(
    name="antispam",
    description="Activa o desactiva el Anti-Spam"
)
async def antispam(
    interaction,
    estado: bool
):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )

    config = configuracion_servidor(
        interaction.guild.id
    )

    config["antispam"] = estado

    guardar_datos()

    texto = (
        "activado"
        if estado
        else
        "desactivado"
    )

    await interaction.followup.send(
        f"🚨 Anti-Spam {texto}."
    )


# =========================================================
# AUTOMOD
# =========================================================

@bot.tree.command(
    name="automod",
    description="Activa o desactiva el AutoMod"
)
async def automod(
    interaction,
    estado: bool
):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )

    config = configuracion_servidor(
        interaction.guild.id
    )

    config["automod"] = estado

    guardar_datos()

    texto = (
        "activado"
        if estado
        else
        "desactivado"
    )

    await interaction.followup.send(
        f"🤖 AutoMod {texto}."
    )


# =========================================================
# FILTER
# =========================================================

@bot.tree.command(
    name="filter",
    description="Activa o desactiva el filtro"
)
async def filter_command(
    interaction,
    estado: bool
):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )

    config = configuracion_servidor(
        interaction.guild.id
    )

    config["filter"] = estado

    guardar_datos()

    texto = (
        "activado"
        if estado
        else
        "desactivado"
    )

    await interaction.followup.send(
        f"🛡️ Filtro {texto}."
    )


# =========================================================
# LOGCHANNEL
# =========================================================

@bot.tree.command(
    name="logchannel",
    description="Configura el canal de registros"
)
async def logchannel(
    interaction,
    canal: discord.TextChannel
):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )

    config = configuracion_servidor(
        interaction.guild.id
    )

    config["log_channel"] = canal.id

    guardar_datos()

    await interaction.followup.send(
        f"📋 Canal de registros: "
        f"{canal.mention}"
    )


# =========================================================
# WELCOME
# =========================================================

@bot.tree.command(
    name="welcome",
    description="Configura el canal de bienvenida"
)
async def welcome(
    interaction,
    canal: discord.TextChannel
):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )

    config = configuracion_servidor(
        interaction.guild.id
    )

    config["welcome_channel"] = canal.id

    guardar_datos()

    await interaction.followup.send(
        f"👋 Canal de bienvenida: "
        f"{canal.mention}"
    )


# =========================================================
# AUTOROLE
# =========================================================

@bot.tree.command(
    name="autorole",
    description="Configura el rol automático"
)
async def autorole(
    interaction,
    rol: discord.Role
):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )

    config = configuracion_servidor(
        interaction.guild.id
    )

    config["autorole"] = rol.id

    guardar_datos()

    await interaction.followup.send(
        f"🎭 Autorol configurado: "
        f"{rol.mention}"
    )


# =========================================================
# TICKET
# =========================================================

@bot.tree.command(
    name="ticket",
    description="Crea un ticket privado"
)
async def ticket(interaction):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )

    if interaction.guild is None:

        await interaction.followup.send(
            "Los tickets solo funcionan en servidores."
        )

        return


    guild = interaction.guild

    nombre = (
        f"ticket-{interaction.user.name}"
        .lower()
    )


    existente = discord.utils.get(
        guild.text_channels,
        name=nombre
    )


    if existente:

        await interaction.followup.send(
            f"Ya existe tu ticket: "
            f"{existente.mention}"
        )

        return


    permisos = {

        guild.default_role:
            discord.PermissionOverwrite(
                view_channel=False
            ),

        interaction.user:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            ),

        guild.me:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True
            )
    }


    try:

        canal = await guild.create_text_channel(
            nombre,
            overwrites=permisos,
            reason="Ticket S4NTY BOT"
        )


        await canal.send(
            f"🎫 Ticket creado para "
            f"{interaction.user.mention}.\n\n"
            "Usa `/cerrarticket` para cerrarlo."
        )


        await interaction.followup.send(
            f"🎫 Ticket creado: "
            f"{canal.mention}"
        )


    except Exception as error:

        await interaction.followup.send(
            f"No pude crear el ticket: {error}"
        )


# =========================================================
# CERRAR TICKET
# =========================================================

@bot.tree.command(
    name="cerrarticket",
    description="Cierra el ticket actual"
)
async def cerrarticket(interaction):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )

    if interaction.guild is None:

        await interaction.followup.send(
            "Este comando solo funciona "
            "en servidores."
        )

        return


    if not interaction.channel.name.startswith(
        "ticket-"
    ):

        await interaction.followup.send(
            "Este canal no parece ser un ticket."
        )

        return


    await interaction.followup.send(
        "🔒 Cerrando ticket..."
    )

    await asyncio.sleep(2)


    try:

        await interaction.channel.delete(
            reason="Ticket cerrado"
        )

    except Exception as error:

        print(
            "Error cerrando ticket:",
            error
        )


# =========================================================
# FAKE IP SEGURA
# =========================================================

@bot.tree.command(
    name="fakeip",
    description="Genera una IP falsa para pruebas"
)
@app_commands.allowed_contexts(
    guilds=True,
    dms=True,
    private_channels=True
)
@app_commands.allowed_installs(
    guilds=True,
    users=True
)
async def fakeip(interaction):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )


    rangos = [

        "192.0.2.",

        "198.51.100.",

        "203.0.113."
    ]


    ip = (
        random.choice(rangos)
        +
        str(
            random.randint(
                1,
                254
            )
        )
    )


    await interaction.followup.send(
        f"🌐 IP falsa de prueba: `{ip}`"
    )


# =========================================================
# AVATAR DISCORD
# =========================================================

@bot.tree.command(
    name="avatar",
    description="Muestra el avatar de un usuario"
)
@app_commands.allowed_contexts(
    guilds=True,
    dms=True,
    private_channels=True
)
@app_commands.allowed_installs(
    guilds=True,
    users=True
)
async def avatar(
    interaction,
    usuario: discord.User = None
):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )

    usuario = (
        usuario
        or
        interaction.user
    )


    embed = discord.Embed(
        title=f"🖼️ Avatar de {usuario}"
    )


    embed.set_image(
        url=usuario.display_avatar.url
    )


    await interaction.followup.send(
        embed=embed
    )


# =========================================================
# USERINFO DISCORD
# =========================================================

@bot.tree.command(
    name="userinfo",
    description="Muestra información de un usuario"
)
@app_commands.allowed_contexts(
    guilds=True,
    dms=True,
    private_channels=True
)
@app_commands.allowed_installs(
    guilds=True,
    users=True
)
async def userinfo(
    interaction,
    usuario: discord.User = None
):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )

    usuario = (
        usuario
        or
        interaction.user
    )


    embed = discord.Embed(
        title="👤 Información del usuario"
    )


    embed.add_field(
        name="Nombre",
        value=str(usuario),
        inline=False
    )


    embed.add_field(
        name="ID",
        value=str(usuario.id),
        inline=False
    )


    embed.set_thumbnail(
        url=usuario.display_avatar.url
    )


    await interaction.followup.send(
        embed=embed
    )


# =========================================================
# INFORMACION DEL SERVIDOR
# =========================================================

@bot.tree.command(
    name="server",
    description="Muestra información del servidor"
)
async def server(interaction):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )

    if interaction.guild is None:

        await interaction.followup.send(
            "Este comando solo funciona en servidores."
        )

        return


    guild = interaction.guild


    embed = discord.Embed(
        title=f"🌐 {guild.name}"
    )


    embed.add_field(
        name="🆔 ID",
        value=str(guild.id),
        inline=False
    )


    embed.add_field(
        name="👥 Miembros",
        value=str(guild.member_count),
        inline=True
    )


    embed.add_field(
        name="📁 Canales",
        value=str(len(guild.channels)),
        inline=True
    )


    if guild.icon:

        embed.set_thumbnail(
            url=guild.icon.url
        )


    await interaction.followup.send(
        embed=embed
    )


# =========================================================
# ENCUESTA
# =========================================================

@bot.tree.command(
    name="poll",
    description="Crea una encuesta"
)
@app_commands.allowed_contexts(
    guilds=True,
    dms=True,
    private_channels=True
)
@app_commands.allowed_installs(
    guilds=True,
    users=True
)
async def poll(
    interaction,
    pregunta: str
):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )


    mensaje = await interaction.followup.send(
        f"📊 **ENCUESTA**\n\n"
        f"{pregunta}\n\n"
        "👍 Sí\n"
        "👎 No",
        wait=True
    )


    try:

        await mensaje.add_reaction(
            "👍"
        )

        await mensaje.add_reaction(
            "👎"
        )

    except Exception:

        pass


# =========================================================
# REGLAS
# =========================================================

@bot.tree.command(
    name="rules",
    description="Muestra las reglas"
)
@app_commands.allowed_contexts(
    guilds=True,
    dms=True,
    private_channels=True
)
@app_commands.allowed_installs(
    guilds=True,
    users=True
)
async def rules(interaction):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )


    await interaction.followup.send(

        "📜 **REGLAS**\n\n"

        "1. Respeta a los demás.\n"

        "2. No hagas spam.\n"

        "3. No envíes enlaces prohibidos.\n"

        "4. No abuses de las menciones.\n"

        "5. Respeta las normas de Discord.\n"

        "6. Sigue las indicaciones de moderación."

    )


# =========================================================
# ROBLOX - PETICIONES
# =========================================================

async def roblox_peticion(
    url,
    metodo="GET",
    datos=None
):

    try:

        timeout = aiohttp.ClientTimeout(
            total=15
        )


        async with aiohttp.ClientSession(
            timeout=timeout
        ) as sesion:


            if metodo == "POST":

                async with sesion.post(
                    url,
                    json=datos
                ) as respuesta:


                    if respuesta.status != 200:

                        return None


                    return await respuesta.json()


            async with sesion.get(
                url
            ) as respuesta:


                if respuesta.status != 200:

                    return None


                return await respuesta.json()


    except Exception as error:

        print(
            "Error Roblox:",
            error
        )

        return None


# =========================================================
# BUSCAR ROBLOX POR USUARIO
# =========================================================

async def buscar_roblox_por_usuario(
    nombre
):

    url = (
        "https://users.roblox.com/"
        "v1/usernames/users"
    )


    datos = {

        "usernames": [
            nombre
        ],

        "excludeBannedUsers": False
    }


    resultado = await roblox_peticion(
        url,
        "POST",
        datos
    )


    if not resultado:

        return None


    usuarios = resultado.get(
        "data",
        []
    )


    if not usuarios:

        return None


    return usuarios[0]


# =========================================================
# INFORMACION DEL USUARIO ROBLOX
# =========================================================

async def obtener_usuario_roblox(
    user_id
):

    url = (
        "https://users.roblox.com/"
        f"v1/users/{user_id}"
    )


    return await roblox_peticion(
        url
    )


# =========================================================
# AVATAR ROBLOX
# =========================================================

async def obtener_avatar_roblox(
    user_id
):

    url = (
        "https://avatar.roblox.com/"
        f"v2/avatar/users/{user_id}/avatar"
    )


    return await roblox_peticion(
        url
    )


# =========================================================
# IMAGEN AVATAR ROBLOX
# =========================================================

async def obtener_imagen_avatar_roblox(
    user_id
):

    url = (
        "https://thumbnails.roblox.com/"
        "v1/users/avatar"
        f"?userIds={user_id}"
        "&size=720x720"
        "&format=Png"
        "&isCircular=false"
    )


    resultado = await roblox_peticion(
        url
    )


    if not resultado:

        return None


    datos = resultado.get(
        "data",
        []
    )


    if not datos:

        return None


    return datos[0].get(
        "imageUrl"
    )


# =========================================================
# IMAGEN DEL ACCESORIO
# =========================================================

async def obtener_imagen_accesorio(
    asset_id
):

    url = (
        "https://thumbnails.roblox.com/"
        "v1/assets"
        f"?assetIds={asset_id}"
        "&size=420x420"
        "&format=Png"
        "&isCircular=false"
    )


    resultado = await roblox_peticion(
        url
    )


    if not resultado:

        return None


    datos = resultado.get(
        "data",
        []
    )


    if not datos:

        return None


    return datos[0].get(
        "imageUrl"
    )


# =========================================================
# ROBLOX POR USUARIO
# =========================================================

@bot.tree.command(
    name="roblox",
    description="Busca un perfil de Roblox por usuario"
)
@app_commands.allowed_contexts(
    guilds=True,
    dms=True,
    private_channels=True
)
@app_commands.allowed_installs(
    guilds=True,
    users=True
)
async def roblox(
    interaction,
    usuario: str
):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )


    datos = await buscar_roblox_por_usuario(
        usuario
    )


    if not datos:

        await interaction.followup.send(
            "❌ No encontré ese usuario de Roblox."
        )

        return


    user_id = datos.get(
        "id"
    )


    informacion = await obtener_usuario_roblox(
        user_id
    )


    if not informacion:

        await interaction.followup.send(
            "❌ No pude obtener la información."
        )

        return


    await enviar_perfil_roblox(
        interaction,
        informacion
    )


# =========================================================
# ROBLOX POR ID
# =========================================================

@bot.tree.command(
    name="robloxid",
    description="Busca un perfil de Roblox por ID"
)
@app_commands.allowed_contexts(
    guilds=True,
    dms=True,
    private_channels=True
)
@app_commands.allowed_installs(
    guilds=True,
    users=True
)
async def robloxid(
    interaction,
    id_usuario: int
):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )


    informacion = await obtener_usuario_roblox(
        id_usuario
    )


    if not informacion:

        await interaction.followup.send(
            "❌ No encontré ese ID de Roblox."
        )

        return


    await enviar_perfil_roblox(
        interaction,
        informacion
    )


# =========================================================
# MOSTRAR PERFIL ROBLOX
# =========================================================

async def enviar_perfil_roblox(
    interaction,
    informacion
):

    user_id = informacion.get(
        "id"
    )


    nombre = informacion.get(
        "name",
        "Desconocido"
    )


    display_name = informacion.get(
        "displayName",
        nombre
    )


    descripcion = informacion.get(
        "description"
    )


    if not descripcion:

        descripcion = (
            "Este usuario no tiene descripción."
        )


    perfil_url = (
        "https://www.roblox.com/users/"
        f"{user_id}/profile"
    )


    avatar_url = await obtener_imagen_avatar_roblox(
        user_id
    )


    avatar = await obtener_avatar_roblox(
        user_id
    )


    embed = discord.Embed(

        title=f"🎮 {display_name}",

        description=descripcion[:4000],

        url=perfil_url
    )


    embed.add_field(

        name="👤 Usuario",

        value=f"`{nombre}`",

        inline=True
    )


    embed.add_field(

        name="🆔 ID",

        value=f"`{user_id}`",

        inline=True
    )


    embed.add_field(

        name="🔗 Perfil",

        value=(
            f"[Abrir perfil de Roblox]"
            f"({perfil_url})"
        ),

        inline=False
    )


    if avatar_url:

        embed.set_image(
            url=avatar_url
        )


    # -----------------------------------------------------
    # ACCESORIOS
    # -----------------------------------------------------

    accesorios = []


    if avatar:

        assets = avatar.get(
            "assets",
            []
        )


        for asset in assets[:12]:

            asset_id = asset.get(
                "id"
            )


            if not asset_id:

                continue


            asset_name = asset.get(
                "name",
                "Accesorio"
            )


            imagen = await obtener_imagen_accesorio(
                asset_id
            )


            accesorios.append({

                "nombre": asset_name,

                "id": asset_id,

                "imagen": imagen
            })


    if accesorios:

        nombres = []


        for accesorio in accesorios:

            nombres.append(

                f"• **{accesorio['nombre']}** "
                f"(`{accesorio['id']}`)"

            )


        texto = "\n".join(
            nombres
        )


        embed.add_field(

            name="👕 Accesorios puestos",

            value=texto[:1024],

            inline=False
        )


    else:

        embed.add_field(

            name="👕 Accesorios",

            value=(
                "No se pudieron obtener "
                "los accesorios."
            ),

            inline=False
        )


    embed.set_footer(

        text=(
            "S4NTY BOT • "
            "Información de Roblox"
        )
    )


    # -----------------------------------------------------
    # BOTON ROBLOX
    # -----------------------------------------------------

    boton = discord.ui.Button(

        label="Ver Roblox",

        style=discord.ButtonStyle.link,

        url=perfil_url
    )


    vista = discord.ui.View()

    vista.add_item(
        boton
    )


    await interaction.followup.send(

        embed=embed,

        view=vista
    )


# =========================================================
# GIVEAWAY
# =========================================================

def convertir_duracion(
    texto
):

    texto = texto.lower().strip()


    coincidencia = re.fullmatch(

        r"(\d+)\s*([smhd])",

        texto
    )


    if not coincidencia:

        return None


    cantidad = int(
        coincidencia.group(1)
    )


    unidad = coincidencia.group(2)


    multiplicadores = {

        "s": 1,

        "m": 60,

        "h": 3600,

        "d": 86400
    }


    return (
        cantidad
        *
        multiplicadores[unidad]
    )


@bot.tree.command(
    name="giveaway",
    description="Crea un sorteo"
)
async def giveaway(
    interaction,
    duracion: str,
    ganadores: int,
    premio: str
):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )


    segundos = convertir_duracion(
        duracion
    )


    if segundos is None:

        await interaction.followup.send(

            "❌ Duración inválida.\n"

            "Ejemplos: `30s`, `10m`, "
            "`2h`, `1d`."

        )

        return


    if segundos < 10:

        await interaction.followup.send(

            "❌ El sorteo debe durar "
            "al menos 10 segundos."

        )

        return


    if ganadores < 1 or ganadores > 20:

        await interaction.followup.send(

            "❌ Los ganadores deben estar "
            "entre 1 y 20."

        )

        return


    if interaction.guild is None:

        await interaction.followup.send(

            "❌ El giveaway necesita "
            "un servidor."

        )

        return


    tiempo_final = (

        discord.utils.utcnow()

        +
        timedelta(
            seconds=segundos
        )
    )


    embed = discord.Embed(

        title="🎉 GIVEAWAY",

        description=(

            f"🎁 **Premio:** {premio}\n\n"

            f"🏆 **Ganadores:** "
            f"{ganadores}\n\n"

            f"⏰ **Termina:** "
            f"<t:{int(tiempo_final.timestamp())}:R>\n\n"

            "🎉 Pulsa la reacción "
            "para participar."
        )
    )


    embed.set_footer(

        text="S4NTY BOT • Giveaway"
    )


    mensaje = await interaction.followup.send(

        embed=embed,

        wait=True
    )


    try:

        await mensaje.add_reaction(
            "🎉"
        )

    except Exception:

        pass


    await asyncio.sleep(
        segundos
    )


    try:

        mensaje = await interaction.channel.fetch_message(
            mensaje.id
        )

    except Exception:

        return


    reaccion = discord.utils.get(

        mensaje.reactions,

        emoji="🎉"
    )


    participantes = []


    if reaccion:

        try:

            participantes = [

                usuario

                async for usuario
                in reaccion.users()

                if not usuario.bot
            ]

        except Exception:

            participantes = []


    if not participantes:

        embed_final = discord.Embed(

            title="🎉 GIVEAWAY TERMINADO",

            description=(

                f"🎁 **Premio:** "
                f"{premio}\n\n"

                "❌ No hubo participantes."
            )
        )


        await mensaje.edit(

            embed=embed_final
        )


        return


    cantidad = min(

        ganadores,

        len(participantes)
    )


    ganadores_finales = random.sample(

        participantes,

        cantidad
    )


    menciones = " ".join(

        usuario.mention

        for usuario
        in ganadores_finales
    )


    embed_final = discord.Embed(

        title="🎉 GIVEAWAY TERMINADO",

        description=(

            f"🎁 **Premio:** "
            f"{premio}\n\n"

            f"🏆 **Ganador(es):**\n"
            f"{menciones}"
        )
    )


    await mensaje.edit(

        embed=embed_final
    )


    await interaction.channel.send(

        f"🎉 ¡Felicidades {menciones}!\n"

        f"Ganaste **{premio}**."
    )


# =========================================================
# HELP
# =========================================================

@bot.tree.command(
    name="help",
    description="Muestra todos los comandos"
)
@app_commands.allowed_contexts(
    guilds=True,
    dms=True,
    private_channels=True
)
@app_commands.allowed_installs(
    guilds=True,
    users=True
)
async def help_command(
    interaction
):

    if not await verificar_dueno(
        interaction
    ):
        return

    await responder_ok(
        interaction
    )


    embed = discord.Embed(

        title="🤖 S4NTY BOT",

        description=(
            "Panel de comandos"
        )
    )


    embed.add_field(

        name="🔨 Moderación",

        value=(

            "/ban\n"
            "/unban\n"
            "/kick\n"
            "/timeout\n"
            "/warn\n"
            "/warnings\n"
            "/clear"

        ),

        inline=True
    )


    embed.add_field(

        name="🔒 Canales",

        value=(

            "/lock\n"
            "/unlock\n"
            "/slowmode"

        ),

        inline=True
    )


    embed.add_field(

        name="🛡️ Seguridad",

        value=(

            "/antilink\n"
            "/antispam\n"
            "/automod\n"
            "/filter\n"
            "/logchannel"

        ),

        inline=True
    )


    embed.add_field(

        name="🎫 Sistema",

        value=(

            "/ticket\n"
            "/cerrarticket\n"
            "/welcome\n"
            "/autorole"

        ),

        inline=True
    )


    embed.add_field(

        name="🎮 Roblox",

        value=(

            "/roblox\n"
            "/robloxid"

        ),

        inline=True
    )


    embed.add_field(

        name="🎉 Sorteos",

        value=(

            "/giveaway"

        ),

        inline=True
    )


    embed.add_field(

        name="⚙️ Utilidades",

        value=(

            "/say\n"
            "/avatar\n"
            "/userinfo\n"
            "/server\n"
            "/poll\n"
            "/rules\n"
            "/fakeip\n"
            "/help"

        ),

        inline=True
    )


    await interaction.followup.send(

        embed=embed
    )


# =========================================================
# ERRORES
# =========================================================

@bot.tree.error
async def error_comando(
    interaction,
    error
):

    print(
        "Error del comando:",
        repr(error)
    )


    try:

        if interaction.response.is_done():

            await interaction.followup.send(

                "❌ Ocurrió un error "
                "al ejecutar el comando.",

                ephemeral=True
            )

        else:

            await interaction.response.send_message(

                "❌ Ocurrió un error "
                "al ejecutar el comando.",

                ephemeral=True
            )

    except Exception:

        pass


# =========================================================
# INICIO SEGURO
# =========================================================

async def principal():

    print(
        "🚀 Iniciando S4NTY BOT..."
    )


    async with bot:

        await bot.start(
            TOKEN
        )


def iniciar_bot():

    try:

        bucle = asyncio.get_running_loop()

    except RuntimeError:

        asyncio.run(
            principal()
        )

    else:

        bucle.create_task(
            principal()
        )


iniciar_bot()