import discord
from discord.ext import commands
import os
import asyncio
import logging
import config
import database

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("ClashOfWits")

class DiscordBot(commands.Bot):
    def __init__(self):
        # We need message_content intent to read prefix commands (like !sync)
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix="!", 
            intents=intents, 
            owner_id=config.OWNER_ID
        )

    async def setup_hook(self):
        # 1. Initialize SQLite Database
        logger.info("Initializing database...")
        await database.init_db()
        logger.info("Database initialized successfully.")

        # 2. Load Cogs
        extensions = [
            "cogs.stats",
            "cogs.duel",
            "cogs.battle_royale"
        ]
        
        for extension in extensions:
            try:
                await self.load_extension(extension)
                logger.info(f"Loaded extension: {extension}")
            except Exception as e:
                logger.error(f"Failed to load extension {extension}: {e}")

        # Note: Auto-sync removed from here to prevent API rate-limiting on every restart.

    async def on_ready(self):
        logger.info(f"🤖 Bot is logged in as: {self.user.name} (ID: {self.user.id})")
        logger.info("------ Bot Ready ------")
        logger.info("Commands are NOT auto-synced. Use the prefix command `!sync` in your server to register slash commands.")

    async def on_connect(self):
        logger.info(f"Connected to Discord gateway. Connected to {len(self.guilds)} servers.")

bot = DiscordBot()

# On-demand sync command (Owner Only)
@bot.command(name="sync")
@commands.is_owner()
async def sync_commands(ctx: commands.Context, scope: str = None):
    """
    On-demand slash command syncing.
    Usage:
      !sync          -> Syncs global commands to the current guild (instant for testing).
      !sync global   -> Syncs commands globally (takes up to 24 hours).
      !sync clear    -> Clears guild-specific commands.
    """
    await ctx.send("⚙️ *Processing sync request...*")
    
    try:
        if scope == "global":
            synced = await bot.tree.sync()
            await ctx.send(f"✅ Successfully synced `{len(synced)}` application command(s) **globally**.")
            logger.info(f"Owner synced {len(synced)} commands globally.")
            
        elif scope == "clear":
            bot.tree.clear_commands(guild=ctx.guild)
            await bot.tree.sync(guild=ctx.guild)
            await ctx.send("🧹 Cleared guild-specific commands from this server.")
            logger.info("Owner cleared guild commands.")
            
        elif scope == "clear_global":
            bot.tree.clear_commands(guild=None)
            await bot.tree.sync()
            await ctx.send("🧹 Cleared global commands from Discord's cache. (This may take up to 24 hours to propagate).")
            logger.info("Owner cleared global commands.")
            
        else:
            # Default: clear the guild commands first to wipe any duplicates
            bot.tree.clear_commands(guild=ctx.guild)
            await bot.tree.sync(guild=ctx.guild)
            
            # Now copy global commands to current guild and sync
            bot.tree.copy_global_to(guild=ctx.guild)
            synced = await bot.tree.sync(guild=ctx.guild)
            await ctx.send(
                f"✅ Successfully wiped existing local commands and synced `{len(synced)}` command(s) **locally to this guild**.\n"
                f"💡 *Note: If you have doubling due to global commands, run `!sync clear_global` to remove them.*"
            )
            logger.info(f"Owner synced {len(synced)} commands to guild: {ctx.guild.name} (ID: {ctx.guild.id}) after clearing.")
            
    except Exception as e:
        await ctx.send(f"❌ Failed to sync: `{str(e)}`")
        logger.error(f"Sync failed: {e}")

# Error handler for sync command permissions
@sync_commands.error
async def sync_error(ctx: commands.Context, error: Exception):
    if isinstance(error, commands.NotOwner):
        await ctx.send("❌ Only the bot owner can execute the sync command.")

async def main():
    if not config.DISCORD_TOKEN:
        logger.error("❌ DISCORD_TOKEN is missing! Please configure it in your .env file.")
        return

    # Start bot
    try:
        await bot.start(config.DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")

if __name__ == "__main__":
    asyncio.run(main())
