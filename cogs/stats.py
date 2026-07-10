"""
stats.py

Cog containing statistics commands for Clash of Wits.
Provides `/profile` to view individual stats and `/leaderboard` to view the top players.
"""

import discord
from discord import app_commands
from discord.ext import commands
import database

class StatsCog(commands.Cog):
    """
    Discord Cog containing commands for displaying player profiles, statistics,
    and the global wins leaderboard.
    """
    def __init__(self, bot):
        """
        Initializes StatsCog with a reference to the running bot instance.
        """
        self.bot = bot

    @app_commands.command(name="profile", description="Shows a player's Clash of Creations profile and stats.")
    @app_commands.describe(member="The member whose profile you want to view (defaults to you).")
    async def profile(self, interaction: discord.Interaction, member: discord.Member = None):
        """
        Slash command to retrieve and display stats for a specific member,
        or the calling user if no member is specified.
        """
        target = member or interaction.user
        
        # Defer reply because db query is async (though fast, standard practice)
        await interaction.response.defer()
        
        stats = await database.get_player_stats(target.id)
        
        if not stats:
            embed = discord.Embed(
                title=f"🏆 {target.display_name}'s Profile",
                description="This player has not entered the arena yet! Use `/clash` or join `/clash_br` to make your mark.",
                color=discord.Color.dark_gray()
            )
            embed.set_thumbnail(url=target.display_avatar.url)
            await interaction.followup.send(embed=embed)
            return

        # Calculate metrics
        duels_played = stats['duels_played']
        duels_won = stats['duels_won']
        duels_lost = duels_played - duels_won
        duel_win_rate = (duels_won / duels_played * 100) if duels_played > 0 else 0.0

        br_played = stats['br_played']
        br_won = stats['br_won']
        br_lost = br_played - br_won
        br_win_rate = (br_won / br_played * 100) if br_played > 0 else 0.0

        total_played = duels_played + br_played
        total_won = duels_won + br_won
        total_win_rate = (total_won / total_played * 100) if total_played > 0 else 0.0

        # Create beautiful embed
        # Use premium deep blue/violet-like color (dark theme accent)
        embed = discord.Embed(
            title=f"🏆 {target.display_name}'s Arena Profile",
            color=discord.Color.from_rgb(114, 137, 218) # Discord Blurple
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        
        # Global stats summary
        embed.add_field(
            name="📊 Overall Record",
            value=f"**Wins:** {total_won} | **Losses:** {total_played - total_won}\n**Win Rate:** {total_win_rate:.1f}%\n**Creations Submitted:** {stats['creations_submitted']}",
            inline=False
        )
        
        # Duel breakdown
        embed.add_field(
            name="⚔️ Duels (1v1)",
            value=f"**Played:** {duels_played}\n**Wins:** {duels_won} | **Losses:** {duels_lost}\n**Win Rate:** {duel_win_rate:.1f}%",
            inline=True
        )

        # BR breakdown
        embed.add_field(
            name="👑 Battle Royale",
            value=f"**Played:** {br_played}\n**Wins:** {br_won} | **Losses:** {br_lost}\n**Win Rate:** {br_win_rate:.1f}%",
            inline=True
        )

        embed.set_footer(text="May the best creation win! • Clash of Wits")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="leaderboard", description="Displays the top 10 Clash of Creations champions.")
    async def leaderboard(self, interaction: discord.Interaction):
        """
        Slash command to retrieve and display the top 10 players on the server,
        ranked by total wins.
        """
        await interaction.response.defer()
        
        leaderboard_data = await database.get_leaderboard(10)
        
        if not leaderboard_data:
            embed = discord.Embed(
                title="🏆 Clash of Creations Leaderboard",
                description="No champions have claimed victory yet! Start the clash with `/clash`.",
                color=discord.Color.gold()
            )
            await interaction.followup.send(embed=embed)
            return

        embed = discord.Embed(
            title="🏆 Clash of Creations Leaderboard",
            description="The most victorious arena fighters in the server, ranked by total wins (Duels + Battle Royales).",
            color=discord.Color.from_rgb(255, 215, 0) # Gold
        )

        medals = ["🥇", "🥈", "🥉", "🏅", "🏅", "🏅", "🏅", "🏅", "🏅", "🏅"]
        
        leaderboard_lines = []
        for index, row in enumerate(leaderboard_data):
            medal = medals[index] if index < len(medals) else "🏅"
            # Highlight top three
            username = row['username']
            if index < 3:
                username = f"**{username}**"
            
            line = (
                f"{medal} `{index + 1:02d}` {username} — "
                f"**{row['total_wins']} Wins** ({row['duels_won']} ⚔️, {row['br_won']} 👑)"
            )
            leaderboard_lines.append(line)
            
        embed.description = "\n".join(leaderboard_lines)
        embed.set_footer(text="Are you ready to climb the ranks? • Clash of Wits")
        await interaction.followup.send(embed=embed)

async def setup(bot):
    """
    Asynchronous function to load the StatsCog extension into the bot.
    """
    await bot.add_cog(StatsCog(bot))
