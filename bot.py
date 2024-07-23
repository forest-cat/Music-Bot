import discord
from discord.ext import commands
import yt_dlp
import os

# Ensure FFmpeg is installed and available in your PATH
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ydl_opts = {
    'format': 'bestaudio/best',
    'noplaylist': True,
}

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

def testfunc(error):
    print(f'Hello after the music is done {error}')

@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user}')
    discord.opus.load_opus("/nix/store/bcrjdc1jc8b40401cvjldymp17rbaydk-libopus-1.5.1/lib/libopus.so")

@bot.command(name='play', help='Play a song from YouTube')
async def play(ctx, url: str):
    if not ctx.author.voice:
        await ctx.send("You are not connected to a voice channel.")
        return

    voice_channel = ctx.author.voice.channel

    if ctx.voice_client is None:
        await voice_channel.connect()

    ydl = yt_dlp.YoutubeDL(ydl_opts)

    with ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

    ctx.voice_client.stop()
    ctx.voice_client.play(discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS), after=testfunc)

    await ctx.send(f'Now playing: {info["title"]}')

@bot.command(name='leave', help='Disconnect the bot from the voice channel')
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Disconnected from the voice channel.")
    else:
        await ctx.send("The bot is not connected to a voice channel.")

@bot.command(name='pause', help='Pause the currently playing song')
async def pause(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("Paused the song.")
    else:
        await ctx.send("No song is currently playing.")

@bot.command(name='resume', help='Resume the currently paused song')
async def resume(ctx):
    if ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("Resumed the song.")
    else:
        await ctx.send("The song is not paused.")

@bot.command(name='stop', help='Stop the currently playing song')
async def stop(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Stopped the song.")
    else:
        await ctx.send("No song is currently playing.")

bot.run('Bot Token')
