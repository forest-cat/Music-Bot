from discord.commands import slash_command
from discord.ext import commands
import icmplib
import sys
import os


class Main(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Importing the read_config() function from bot.py file
    sys.path.append(os.path.dirname(__file__)[:-4])
    from bot import read_config

    config = read_config()

    async def host_ping(self, host):
        ping = icmplib.ping(address=host, count=4, privileged=False)
        return int(round(ping.avg_rtt))

    @commands.Cog.listener()
    async def on_ready(self):
        print(
            f"Logged in as: \033[36m{self.bot.user.name}\033[90m#\033[37m{self.bot.user.discriminator}\033[0m")

    @slash_command(name='ping',
                   guild_ids=config["GUILD_IDS"],
                   description="Shows you the bots latency all the used services")
    async def ping(self, ctx):
        msg = await ctx.respond("-# *pinging* <a:loadingemoji:1266532115634323507>")
        await msg.edit_original_response(content=f"""Discord.com: `{await self.host_ping('discord.com')}`ms\nYouTube.de: `{await self.host_ping('youtube.de')}`ms\nYouTube.com: `{await self.host_ping('youtube.com')}`ms""")


def setup(bot):
    bot.add_cog(Main(bot))
