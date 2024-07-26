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
        'options': '-vn -bufsize 64k' # increase buffer size to prevent overflow crashes (needs long time observation)
    }

    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True
    }

    config = read_config()
    song_queue = []
    currentPlayingSong = None
    player_volume = int(config["DEFAULT_PLAYER_VOLUME"])
    join_msg = None

    def testfunc(self, error):
        print(f'Hello after the music is done {error}')

    @commands.Cog.listener()
    async def on_ready(self):
        discord.opus.load_opus(
            "/nix/store/bcrjdc1jc8b40401cvjldymp17rbaydk-libopus-1.5.1/lib/libopus.so")

    @slash_command(name='test',
                   guild_ids=config["GUILD_IDS"],
                   description='just a test here')
    async def test(self, ctx, query: str):
        ydl = yt_dlp.YoutubeDL(self.ydl_opts)
        with ydl:
            info = ydl.extract_info(query, download=False)
            audio_url = info['url']
            print(info)

    @slash_command(name='play',
                   guild_ids=config["GUILD_IDS"],
                   description='Play a song from YouTube')
    async def play(self, ctx, query: str):
        await self.join(ctx)

        if ctx.voice_client.is_playing():
            # Queue action here | make queue with touples (query, url)
            pass
        else:

            ydl = yt_dlp.YoutubeDL(self.ydl_opts)

            with ydl:
                info = ydl.extract_info(query, download=False)
                audio_url = info['url']

            ctx.voice_client.stop()
            ctx.voice_client.play(discord.FFmpegPCMAudio(
                audio_url, **self.FFMPEG_OPTIONS), after=self.testfunc)
            ctx.voice_client.source.volume = self.player_volume / 100

            await self.join_msg.edit_original_response(content=f'Now playing: `{info["title"]}`')
    @slash_command(name='join',
                   guild_ids=config["GUILD_IDS"],
                   description='Summons the bot to your current channel')
    async def join(self, ctx):
        if not ctx.author.voice:
            await ctx.respond("You are not connected to a voice channel.")
            return
        voice_channel = ctx.author.voice.channel
        if not ctx.voice_client:
            await voice_channel.connect()
        else:
            await ctx.voice_client.move_to(ctx.author.voice.channel)
        self.join_msg = await ctx.respond(f"Connected to {voice_channel}")

    @slash_command(name='leave',
                   guild_ids=config["GUILD_IDS"],
                   description='Disconnect the bot from the voice channel')
    async def leave(self, ctx):
        if not ctx.voice_client:
            await ctx.respond("The bot is not connected to a voice channel.")
            return

        if not ctx.author.voice:
            await ctx.respond("You are not connected to a voice channel.")
            return

        if not ctx.voice_client.channel == ctx.author.voice.channel:
            await ctx.respond("You are not connected to the same voice channel as the bot.")
            return

        await ctx.voice_client.disconnect()
        await ctx.respond("Disconnected from the voice channel.")

    @slash_command(name='pause',
                   guild_ids=config["GUILD_IDS"],
                   description='Pause the currently playing song')
    async def pause(self, ctx):
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.respond("Paused the song.")
        else:
            await ctx.respond("No song is currently playing.")

    @slash_command(name='resume',
                   guild_ids=config["GUILD_IDS"],
                   description='Resume the currently paused song')
    async def resume(self, ctx):
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.respond("Resumed the song.")
        else:
            await ctx.respond("The song is not paused.")

    @slash_command(name='stop',
                   guild_ids=config["GUILD_IDS"],
                   description='Stop the currently playing song')
    async def stop(self, ctx):
        if not ctx.voice_client:
            await ctx.respond("The bot is not connected to a voice channel.")
            return
        if not ctx.voice_client.is_playing():
            await ctx.respond("No song is currently playing.")
            return
        
        ctx.voice_client.stop()
        await ctx.respond("Stopped the song.")


def setup(bot):
    bot.add_cog(Music(bot))
