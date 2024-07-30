from discord.commands import slash_command
from discord.ext import commands
from functools import partial
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
        'options': '-vn -bufsize 64k -loglevel panic'
    }

    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto'
    }

    config = read_config()
    queues = {}
    currentPlayingSong = {}
    player_volume = int(config["DEFAULT_PLAYER_VOLUME"])
    last_msg = {}

    def seconds_to_hhmmss(self, seconds):
        # Calculate the number of hours, minutes, and seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        remaining_seconds = seconds % 60
        
        # Format the result as hh:mm:ss
        return f"{hours:02}:{minutes:02}:{remaining_seconds:02}"
    
    def on_future_done(self, future, ctx):
        self.last_msg[ctx.guild.id] = future.result()

    def play_next_song(self, error, ctx):
        if not self.queues[ctx.guild.id]:
            future = asyncio.run_coroutine_threadsafe(
                self.last_msg[ctx.guild.id].edit(content=f'Queue finished!'), self.bot.loop)
            return
        self.currentPlayingSong[ctx.guild.id] = self.queues[ctx.guild.id][0]
        self.queues[ctx.guild.id].pop(0)
        ctx.voice_client.play(discord.FFmpegPCMAudio(
            self.currentPlayingSong[ctx.guild.id][0], **self.FFMPEG_OPTIONS), after=lambda error: self.play_next_song(error, ctx))
        ctx.voice_client.source.volume = self.player_volume / 100

        future = asyncio.run_coroutine_threadsafe(self.last_msg[ctx.guild.id].edit(
            content=f'**Now playing :musical_note:**\n [{self.seconds_to_hhmmss(int(self.currentPlayingSong[ctx.guild.id][3]))}] :clock10: | [{self.currentPlayingSong[ctx.guild.id][1]}](<{self.currentPlayingSong[ctx.guild.id][2]}>)'), self.bot.loop)
        future.add_done_callback(partial(self.on_future_done, ctx=ctx))

    async def get_youtube_info(self, query):
        # Regular expression to check if the string is a YouTube link
        youtube_link_regex = re.compile(
            r'^(https?\:\/\/)?(www\.youtube\.com|youtu\.?be)\/.+$')

        ydl = yt_dlp.YoutubeDL(self.ydl_opts)
        with ydl:
            data = ydl.extract_info(query, download=False)
            # Check if the input string is a YouTube link
            if youtube_link_regex.match(query):
                audio_url = data['url']
                return audio_url, data['title'], data['webpage_url'], data['duration']
            # If not, search for the keyword on YouTube
            else:
                try:
                    if data['entries']:
                        # take first item from a playlist
                        data = data['entries'][0]
                        # print(f"\n\nDuration: {data['duration']}")
                        return data['url'], data['title'], data['webpage_url'], data['duration']
                    return None, None, None, None
                except IndexError:
                    return None, None, None, None

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
        discord.opus.load_opus(self.config["LIBOPUS_PATH"])

    @slash_command(name='play',
                   guild_ids=config["GUILD_IDS"],
                   description='Play a song from YouTube')
    async def play(self, ctx, query: str):
        await self.join(ctx)
        if ctx.guild.id not in self.queues:
            self.queues[ctx.guild.id] = []
        song_url, title, yt_url, duration = await self.get_youtube_info(query)
        if not song_url:
            await self.last_msg[ctx.guild.id].edit(content="Couldn't find that song!")
            return
        if not ctx.voice_client:
            return
        if ctx.voice_client.is_playing():
            # Queue action here | make queue with touples (query, url)
            self.last_msg[ctx.guild.id] = await self.last_msg[ctx.guild.id].edit(content=f'**Adding to queue :clipboard:**\n [{self.seconds_to_hhmmss(int(duration))}] :clock10: | [{title}](<{yt_url}>)')
            self.queues[ctx.guild.id].append((song_url, title, yt_url, duration))
        else:
            self.queues[ctx.guild.id].append((song_url, title, yt_url, duration))
            self.currentPlayingSong[ctx.guild.id] = (song_url, title, yt_url, duration)
            self.play_next_song(None, ctx)

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
            self.last_msg[ctx.guild.id] = await ctx.respond("The bot is already connected to your voice channel.")
            return
        elif ctx.voice_client.channel == ctx.voice_client.channel and ctx.command.qualified_name == "play":
            self.last_msg[ctx.guild.id] = await ctx.respond("-# searching song")
            return
        else:
            await ctx.voice_client.disconnect()
            await voice_channel.connect()
        self.last_msg[ctx.guild.id] = await ctx.respond(f"Connected to {voice_channel.mention}")

    @slash_command(name='leave',
                   guild_ids=config["GUILD_IDS"],
                   description='Disconnect the bot from the voice channel')
    async def leave(self, ctx):
        if await self.fail_voice_check(ctx):
            return
        await ctx.voice_client.disconnect()
        await ctx.respond(f"Disconnected from {ctx.author.voice.channel.mention}")

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
        if ctx.guild.id in self.queues:
            self.queues[ctx.guild.id].clear()
        ctx.voice_client.stop()
        await ctx.respond("Stopped the song and cleared the queue.")

    @slash_command(name='queue',
                   guild_ids=config["GUILD_IDS"],
                   description='Display the current song queue')
    async def queue(self, ctx):
        if not ctx.guild.id in self.queues:
            await ctx.respond("The queue is empty.")
            return
        if not self.queues[ctx.guild.id]:
            await ctx.respond("The queue is empty.")
            return
        queue_list = '\n'.join(
            [f'{index}.  [{self.seconds_to_hhmmss(int(song[3]))}] :clock10: | [{song[1]}](<{song[2]}>)' for index, song in enumerate(self.queues[ctx.guild.id])])
        self.last_msg[ctx.guild.id] = await ctx.respond(f'## Song Queue\n{queue_list}')

    @slash_command(name='skip',
                   guild_ids=config["GUILD_IDS"],
                   description='Skip the currently playing song')
    async def skip(self, ctx):
        if await self.fail_voice_check(ctx):
            return
        if not ctx.voice_client.is_playing():
            await ctx.respond("No song is currently playing.")
            return
        if not self.queues[ctx.guild.id]:
            await ctx.respond("Whoops thats already the end of the queue ¯\_(ツ)_/¯")
            return
        self.last_msg[ctx.guild.id] = await ctx.respond("Skipped the song.")
        ctx.voice_client.stop()

    @slash_command(name='nowplaying',
                   guild_ids=config["GUILD_IDS"],
                   description='Display the currently playing song')
    async def nowplaying(self, ctx):
        if ctx.guild.id not in self.currentPlayingSong:
            await ctx.respond("No song is currently playing.")
            return
        self.last_msg[ctx.guild.id] = await ctx.respond(f'**Now playing :musical_note:**\n [{self.seconds_to_hhmmss(int(self.currentPlayingSong[ctx.guild.id][3]))}] :clock10: | [{self.currentPlayingSong[ctx.guild.id][1]}](<{self.currentPlayingSong[ctx.guild.id][2]}>)')


def setup(bot):
    bot.add_cog(Music(bot))
