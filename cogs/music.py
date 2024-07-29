from discord.commands import slash_command
from discord.ext import commands
import discord
import asyncio
import yt_dlp
import sys
import os
import re


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Importing the read_config() function from bot.py file
    sys.path.append(os.path.dirname(__file__)[:-4])
    from bot import read_config

    # Ensure FFmpeg is installed and available in your PATH
    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        # increase buffer size to prevent overflow crashes (needs long time observation)
        'options': '-vn -bufsize 64k'
    }

    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto'
    }

    config = read_config()
    song_queue = []
    currentPlayingSong = None
    player_volume = int(config["DEFAULT_PLAYER_VOLUME"])
    last_msg = None

    async def play_next_song(self, error, ctx):
        if not self.song_queue:
            return
        ctx.voice_client.play(discord.FFmpegPCMAudio(
            self.song_queue[0][0], **self.FFMPEG_OPTIONS), after=lambda error: asyncio.run_coroutine_threadsafe(self.play_next_song_wrapper(error, ctx), self.bot.loop))
        ctx.voice_client.source.volume = self.player_volume / 100

        await self.last_msg.edit_original_response(content=f'Now playing: `{self.song_queue[0][1]}`')
        self.currentPlayingSong = self.song_queue[0]
        self.song_queue.pop(0)

    async def play_next_song_wrapper(self, error, ctx):
        await self.play_next_song(error, ctx)

    async def get_youtube_link(self, query):
        # Regular expression to check if the string is a YouTube link
        youtube_link_regex = re.compile(
            r'^(https?\:\/\/)?(www\.youtube\.com|youtu\.?be)\/.+$'
        )

        ydl = yt_dlp.YoutubeDL(self.ydl_opts)
        with ydl:
            data = ydl.extract_info(query, download=False)
            # Check if the input string is a YouTube link
            if youtube_link_regex.match(query):
                audio_url = data['url']
                return audio_url, data['title']
            # If not, search for the keyword on YouTube
            else:
                try:
                    if data['entries']:
                        # take first item from a playlist
                        data = data['entries'][0]
                        # print(f"\n\nDuration: {data['duration']}")
                        return data['url'], data['title']
                    return None, None
                except IndexError:
                    return None, None

    async def fail_voice_check(self, ctx):
        if not ctx.author.voice:
            await ctx.respond("You are not connected to a voice channel.")
            return True
        if not ctx.voice_client:
            await ctx.respond("The bot is not connected to a voice channel.")
            return True
        if not ctx.voice_client.channel == ctx.author.voice.channel:
            await ctx.respond("You are not connected to the same voice channel as the bot.")
            return True

    @commands.Cog.listener()
    async def on_ready(self):
        discord.opus.load_opus(
            "/nix/store/bcrjdc1jc8b40401cvjldymp17rbaydk-libopus-1.5.1/lib/libopus.so")

    @slash_command(name='play',
                   guild_ids=config["GUILD_IDS"],
                   description='Play a song from YouTube')
    async def play(self, ctx, query: str):
        await self.join(ctx)
        song_url, title = await self.get_youtube_link(query)
        if not song_url:
            await self.last_msg.edit_original_response(content="Couldn't find that song!")
            return

        if ctx.voice_client.is_playing():
            # Queue action here | make queue with touples (query, url)
            self.last_msg = await self.last_msg.edit_original_response(content=f'[+] Already playing, adding to queue: `{title}`')
            self.song_queue.append((song_url, title))
        else:
            ctx.voice_client.stop()
            ctx.voice_client.play(discord.FFmpegPCMAudio(
                song_url, **self.FFMPEG_OPTIONS), after=lambda error: asyncio.run_coroutine_threadsafe(self.play_next_song_wrapper(error, ctx), self.bot.loop))
            ctx.voice_client.source.volume = self.player_volume / 100

            await self.last_msg.edit_original_response(content=f'Now playing: `{title}`')
            self.currentPlayingSong = (song_url, title)

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
        elif ctx.voice_client.channel == ctx.voice_client.channel and ctx.command.qualified_name == "join":
            self.last_msg = await ctx.respond("The bot is already connected to your voice channel.")
            return
        elif ctx.voice_client.channel == ctx.voice_client.channel and ctx.command.qualified_name == "play":
            self.last_msg = await ctx.respond("-# searching song")
            return
        else:
            await ctx.voice_client.disconnect()
            await voice_channel.connect()
        self.last_msg = await ctx.respond(f"Connected to {voice_channel}")

    @slash_command(name='leave',
                   guild_ids=config["GUILD_IDS"],
                   description='Disconnect the bot from the voice channel')
    async def leave(self, ctx):
        if await self.fail_voice_check(ctx):
            return
        await ctx.voice_client.disconnect()
        await ctx.respond("Disconnected from the voice channel.")

    @slash_command(name='pause',
                   guild_ids=config["GUILD_IDS"],
                   description='Pause the currently playing song')
    async def pause(self, ctx):
        if await self.fail_voice_check(ctx):
            return
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.respond("Paused the song.")
        else:
            await ctx.respond("No song is currently playing.")

    @slash_command(name='resume',
                   guild_ids=config["GUILD_IDS"],
                   description='Resume the currently paused song')
    async def resume(self, ctx):
        if await self.fail_voice_check(ctx):
            return
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.respond("Resumed the song.")
        else:
            await ctx.respond("The song is not paused.")

    @slash_command(name='stop',
                   guild_ids=config["GUILD_IDS"],
                   description='Stops the currently playing song and clears the queue')
    async def stop(self, ctx):
        if await self.fail_voice_check(ctx):
            return
        if not ctx.voice_client.is_playing():
            await ctx.respond("No song is currently playing.")
            return
        if self.song_queue:
            self.song_queue.clear()
        ctx.voice_client.stop()
        await ctx.respond("Stopped the song and cleared the queue.")

    @slash_command(name='queue',
                   guild_ids=config["GUILD_IDS"],
                   description='Display the current song queue')
    async def queue(self, ctx):
        if not self.song_queue:
            await ctx.respond("The queue is empty.")
            return
        queue_list = '\n'.join([f'{index}. `{song[1]}`' for index, song in enumerate(self.song_queue)])
        await ctx.respond(f'**Song Queue:**\n{queue_list}')
    
    @slash_command(name='skip',
                   guild_ids=config["GUILD_IDS"],
                   description='Skip the currently playing song')
    async def skip(self, ctx):
        if await self.fail_voice_check(ctx):
            return
        if not ctx.voice_client.is_playing():
            await ctx.respond("No song is currently playing.")
            return
        if not self.song_queue:
            await ctx.respond("Whoops thats already the end of the queue ¯\_(ツ)_/¯")
            return
        self.last_msg = await ctx.respond("Skipped the song.")
        ctx.voice_client.stop()
    
    @slash_command(name='nowplaying',
                    guild_ids=config["GUILD_IDS"],
                    description='Display the currently playing song')
    async def nowplaying(self, ctx):
        if not self.currentPlayingSong:
            await ctx.respond("No song is currently playing.")
            return
        self.last_msg = await ctx.respond(f'Now playing: `{self.currentPlayingSong[1]}`')

def setup(bot):
    bot.add_cog(Music(bot))
