import discord
import subprocess
import re
import asyncio
import json
import requests
import time
import os


class MyClient(discord.Client):
    async def on_ready(self):
        print(f"Logged on as {self.user}!")

intents = discord.Intents.all()
client = MyClient(intents=intents)
tree = discord.app_commands.CommandTree(client)

user_shroom_running = []
shroom_api_key = os.getenv("SHROOM_BOT_API_KEY")
shroom_discord_token = os.getenv("SHROOM_BOT_DISCORD_TOKEN")

@tree.command(
    name="leaderboard",
    description="Mushroom island leaderboard command",
    guild=discord.Object(id=720723932738486323)
)
async def leaderboard(
    interaction: discord.Interaction,
    count: int = 10,
    largebiomes: bool = False
):
    await interaction.response.defer(thinking=True)
    endpoint = "https://shroomweb.0xa.pw/sb_leaderboard"
    if largebiomes:
        endpoint = "https://shroomweb.0xa.pw/lb_leaderboard"
    limit = count
    if limit > 20:
        limit = 20

    params = {
        'count': limit
    }
    response = requests.get(endpoint, params, timeout=10)
    message = "@silent\n```Position, User, Seed, Claimed_size, calculated_size, result_id\n"
    if(response.status_code == 200):
        json_response = json.loads(response)
        for x in range(1, limit):
            message += f"{x}: <@{json_response['discord_id']}>, {json_response['seed']}, {json_response['claimed_size']}, {json_response['calculated_size']}, {json_response['result_id']}\n"
        interaction.response.send_message(message)
    else:
        interaction.response.send_message("Zoinks scoob! That one didn't work.", ephemeral=True)
@tree.command(
    name="register",
    description="Register your discord account for shroomin",
    guild=discord.Object(id=720723932738486323)
)
async def register(
    interaction: discord.Interaction
):
    data = {
        "discord_id": interaction.user.id,
    }
    headers = {
        "api-key": shroom_api_key
    }
    response = requests.post(
        "https://shroomweb.0xa.pw/register",
        headers=headers,
        json=data,
        timeout=10
    )
    if(response.status_code == 200):
        await interaction.response.send_message(response.content, ephemeral=True)
    else:
        await interaction.response.send_message("You already exist!", ephemeral=True)

    
@tree.command(
    name="shroom",
    description="Test a seed and coordinates for mushroom island size",
    guild=discord.Object(id=720723932738486323)
)
async def shroom(
    interaction: discord.Interaction,
    worldseed: str,  # string to allow large seeds
    x: int,
    z: int,
    largebiomes: bool = False
):
    # Step 1: Defer immediately (so Discord doesn't timeout)
    await interaction.response.defer(thinking=True)
    if largebiomes:
        user_shroom_running.append(interaction.user.id)
    cmd = [
        "./sizeCheck",
        "--worldseed", worldseed,
        "--x", str(x),
        "--z", str(z),
        "--largebiomes", str(largebiomes)
    ]

    try:
        # Step 2: Run subprocess asynchronously
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            await interaction.followup.send(
                f"❌ Error running subprocess:\n```{stderr.decode().strip()}```"
            )
            return

        stdout = stdout.decode().strip()

    except Exception as e:
        await interaction.followup.send(f"❌ Exception: {e}")
        return

    # Step 3: Parse output
    if "does not exist" in stdout or "could otherwise not be measured" in stdout:
        await interaction.followup.send("⚠️ Coordinates are wrong.")
        return

    x_coord_match = re.search(r"X: (\d+)", stdout);
    z_coord_match = re.search(r"Z: (\d+)", stdout);
    message_string = ""
    if x_coord_match:
        message_string += f"X: {x_coord_match.group(1)}\n"
    if z_coord_match:
        message_string += f"Z: {z_coord_match.group(1)}\n"
    match = re.search(r"Area:\s+(\d+)\s+square blocks", stdout)
    if match:
        message_string += f"✅ Area is {match.group(1)} blocks"
        await interaction.followup.send(message_string)
    else:
        await interaction.followup.send(
            "❌ Error: Could not parse area output.\n"
            f"```{stdout}```"
        )
    if largebiomes:
        user_shroom_running.remove(interaction.user.id)
# Don’t forget to sync commands on startup
@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=720723932738486323))
    print(f"Synced commands to test guild!")
    print(f"Logged on as {client.user}!")

client.run(shroom_discord_token)