from discord.commands import slash_command
from discord.ext import commands
import discord
import yt_dlp
import sys
import os


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Importing the read_config() function from bot.py file 
    sys.path.append(os.path.dirname(__file__)[:-4])
    from bot import read_config

    # Ensure FFmpeg is installed and available in your PATH
    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
    }

    def testfunc(self, error):
        print(f'Hello after the music is done {error}')

    @commands.Cog.listener()
    async def on_ready(self):
        discord.opus.load_opus("/nix/store/bcrjdc1jc8b40401cvjldymp17rbaydk-libopus-1.5.1/lib/libopus.so")

    @slash_command(name='play', help='Play a song from YouTube')
    async def play(self, ctx, url: str):
        if not ctx.author.voice:
            await ctx.respond("You are not connected to a voice channel.")
            return

        voice_channel = ctx.author.voice.channel

        if ctx.voice_client is None:
            await voice_channel.connect()

        ydl = yt_dlp.YoutubeDL(self.ydl_opts)

        with ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info['url']

        ctx.voice_client.stop()
        ctx.voice_client.play(discord.FFmpegPCMAudio(audio_url, **self.FFMPEG_OPTIONS), after=self.testfunc)

        await ctx.respond(f'Now playing: {info["title"]}')

    @slash_command(name='leave', help='Disconnect the bot from the voice channel')
    async def leave(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.respond("Disconnected from the voice channel.")
        else:
            await ctx.respond("The bot is not connected to a voice channel.")

    @slash_command(name='pause', help='Pause the currently playing song')
    async def pause(self, ctx):
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.respond("Paused the song.")
        else:
            await ctx.respond("No song is currently playing.")

    @slash_command(name='resume', help='Resume the currently paused song')
    async def resume(self, ctx):
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.respond("Resumed the song.")
        else:
            await ctx.respond("The song is not paused.")

    @slash_command(name='stop', help='Stop the currently playing song')
    async def stop(self, ctx):
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.respond("Stopped the song.")
        else:
            await ctx.respond("No song is currently playing.")

def setup(bot):
    bot.add_cog(Music(bot))