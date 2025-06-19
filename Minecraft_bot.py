import discord
from discord import app_commands
import asyncio
import socket
import os
from dotenv import load_dotenv
load_dotenv()

# === CẤU HÌNH ===
TOKEN = os.getenv("TOKEN")
CHECK_INTERVAL = 5  # giây
MESSAGE_FILE = 'message_id.txt'
CONFIG_FILE = 'server_config.txt'

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# === Biến toàn cục ===
domain = "play.purpleprison.net"
port = 25565
status_message = None
last_status = None
channel_id = None
msg = None


def is_server_online(host, port):
    try:
        socket.create_connection((host, port), timeout=3)
        return True
    except:
        return False

def get_status_emoji(status):
    return '🟢' if status else '⚫'

def get_status_text(status):
    return 'ONLINE' if status else 'OFFLINE'

def get_display_address():
    return f"{domain}" if port == 25565 else f"{domain}:{port}"

async def update_status_message(channel):
    global status_message, last_status

    status = is_server_online(domain, port)
    if status != last_status:
        embed = discord.Embed(title="🎮 Minecraft Server Status",description=f"🌐 Địa chỉ: `{get_display_address()}`",color=discord.Color.green() if status else discord.Color.dark_gray())
        embed.add_field(name="Trạng thái", value=f"{get_status_emoji(status)} **{get_status_text(status)}**", inline=False)
        embed.set_footer(text="Tự động cập nhật mỗi 5 giây")

        if status_message:
            await status_message.edit(embed=embed)
        else:
            status_message = await channel.send(embed=embed)
            with open(MESSAGE_FILE, 'w') as f:
                f.write(str(status_message.id))

        last_status = status




def load_config():
    global domain, port
    config_path = "mc_config.txt"

    # Nếu file chưa tồn tại → tạo với giá trị mặc định
    if not os.path.exists(config_path):
        with open(config_path, "w") as f:
            f.write("domain=mc.hypixel.net\n")
            f.write("port=25565\n")
        domain = "mc.hypixel.net"
        port = 25565
        print("⚙️ Đã tạo file cấu hình mặc định mc_config.txt")
        return

    # Đọc file nếu đã có
    with open(config_path, "r") as f:
        for line in f:
            if line.startswith("domain="):
                domain = line.strip().split("=")[1]
            elif line.startswith("port="):
                try:
                    port = int(line.strip().split("=")[1])
                except:
                    port = 25565


def save_config():
    with open("mc_config.txt", "w") as f:
        f.write(f"domain={domain}\n")
        f.write(f"port={port}\n")


@client.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập: {client.user}")
    await tree.sync()
    print("🔧 Slash commands đã sync.")

    load_config()

    # Đọc lại channel_id nếu đã có cấu hình
    global channel_id, status_message
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            try:
                channel_id = int(f.read().strip())
            except:
                pass

    if channel_id:
        channel = client.get_channel(channel_id)
        if os.path.exists(MESSAGE_FILE):
            try:
                with open(MESSAGE_FILE, 'r') as f:
                    msg_id = int(f.read().strip())
                    status_message = await channel.fetch_message(msg_id)
            except:
                pass
        asyncio.create_task(status_loop(channel))


async def status_loop(channel):
    while True:
        await update_status_message(channel)
        await asyncio.sleep(CHECK_INTERVAL)

# === LỆNH /start: bot lưu channel hiện tại để cập nhật trạng thái
@tree.command(name="start", description="Bắt đầu theo dõi trạng thái server Minecraft")
async def start(interaction: discord.Interaction):
    global channel_id, status_message

    channel_id = interaction.channel.id
    with open(CONFIG_FILE, 'w') as f:
        f.write(str(channel_id))

    await interaction.response.send_message("✅ Bot đã được thiết lập để theo dõi server trong kênh này.",ephemeral=True)

    channel = interaction.channel
    if status_message == None:
        embed  = discord.Embed(title="🎮 Minecraft Server Status",description=f"🌐 Địa chỉ: {get_display_address()}",color=discord.Color.green() if is_server_online(domain, port) else discord.Color.dark_gray())
        embed.add_field(name="Trạng thái", value=f"{get_status_emoji(is_server_online(domain, port))} **{get_status_text(is_server_online(domain, port))}**", inline=False)
        embed.set_footer(text="Tự động cập nhật mỗi 5 giây")
        status_message = await interaction.channel.send(embed=embed)
        with open(MESSAGE_FILE, 'w') as f:
            f.write(str(status_message.id))


    asyncio.create_task(status_loop(channel))


# === LỆNH /setdomain
@tree.command(name="setdomain", description="Cập nhật domain server")
async def setdomain(interaction: discord.Interaction, new_domain: str):
    global domain
    domain = new_domain

    save_config()
    await interaction.response.send_message(f"✅ Đã cập nhật domain thành `{domain}`", ephemeral=True)

    await update_status_message(interaction.channel)



# === LỆNH /setport
@tree.command(name="setport", description="Cập nhật cổng server")
async def setport(interaction: discord.Interaction, new_port: int):
    global port
    port = new_port
    save_config()
    await interaction.response.send_message(f"✅ Đã cập nhật port thành `{port}`", ephemeral=True)

    # Cập nhật lại tin nhắn trạng thái
    await update_status_message(interaction.channel)
    



# === LỆNH /status: gửi lại tin nhắn nếu tin cũ mất
@tree.command(name="status", description="Gửi lại trạng thái hiện tại của server")
async def status(interaction: discord.Interaction):
    global status_message

    embed  = discord.Embed(title="🎮 Minecraft Server Status",description=f"🌐 Địa chỉ: {get_display_address()}",color=discord.Color.green() if is_server_online(domain, port) else discord.Color.dark_gray())
    embed.add_field(name="Trạng thái", value=f"{get_status_emoji(is_server_online(domain, port))} **{get_status_text(is_server_online(domain, port))}**", inline=False)
    embed.set_footer(text="Tự động cập nhật mỗi 5 giây")

    status_message = await interaction.channel.send(embed=embed)
    with open(MESSAGE_FILE, 'w') as f:
        f.write(str(status_message.id))
    await interaction.response.send_message("✅ Đã gửi lại trạng thái server.", ephemeral=True)



client.run(TOKEN)
