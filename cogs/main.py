from discord.ext import commands
import sys
import os


class Main(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Importing the read_config() function from bot.py file 
    sys.path.append(os.path.dirname(__file__)[:-4])
    from bot import read_config

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"Logged in as: \033[36m{self.bot.user.name}\033[90m#\033[37m{self.bot.user.discriminator}\033[0m")

def setup(bot):
    bot.add_cog(Main(bot))