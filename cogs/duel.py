import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os
import config
import database
from ai_client import AIClient

# Global AI Client instance
ai_client = AIClient()

class CreationModal(discord.ui.Modal):
    """
    A Discord UI modal that allows a player to type in and submit their creation.
    Validates theme compliance via AI checking if a theme is active.
    """
    def __init__(self, player_num: str, view: 'ClashSubmissionView'):
        super().__init__(title="Submit Your Creation")
        self.player_num = player_num # 'A' or 'B'
        self.view = view

        self.creation_input = discord.ui.TextInput(
            label="What is your creation?",
            placeholder="e.g., A laser-guided radioactive banana; The literal concept of gravity...",
            style=discord.TextStyle.paragraph,
            max_length=400,
            required=True
        )
        self.add_item(self.creation_input)

    async def on_submit(self, interaction: discord.Interaction):
        # Defer immediately since LLM API call can exceed the 3-second modal response limit
        await interaction.response.defer(ephemeral=True)
        
        creation_text = self.creation_input.value.strip()
        
        # Check theme fit if enabled
        if self.view.theme_check and self.view.theme:
            checking_msg = await interaction.followup.send(
                "🔮 *Checking if your creation complies with the theme setting...*",
                ephemeral=True
            )
            
            try:
                fits, reason = await ai_client.check_theme_fit(creation_text, self.view.theme)
            except Exception as e:
                fits, reason = True, f"Error running check (allowing by default): {str(e)}"
            
            # Delete checking message
            try:
                await checking_msg.delete()
            except:
                pass
            
            if not fits:
                reject_embed = discord.Embed(
                    title="❌ Theme Validation Failed",
                    description=(
                        f"Your submission was rejected by the **Arena Theme Compliance Officer**.\n\n"
                        f"**Theme:** {self.view.theme['name']}\n"
                        f"**Rule:** {self.view.theme['description']}\n\n"
                        f"**Your Creation:** `{creation_text}`\n"
                        f"**Reason for Rejection:** {reason}\n\n"
                        f"💡 *Please click the button to submit again, adapting your creation to fit the setting.*"
                    ),
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=reject_embed, ephemeral=True)
                return

        # Approved or theme checking is disabled
        if self.player_num == 'A':
            self.view.creation_a = creation_text
            # Update database count
            await database.update_player_stats(self.view.player_a.id, self.view.player_a.display_name, submitted=True)
        else:
            self.view.creation_b = creation_text
            # Update database count
            await database.update_player_stats(self.view.player_b.id, self.view.player_b.display_name, submitted=True)

        await interaction.followup.send("✅ Creation submitted and approved!", ephemeral=True)
        await self.view.update_status()


class ClashSubmissionView(discord.ui.View):
    """
    A view containing the 'Submit Creation' button during a 1v1 duel.
    Coordinates private modal submissions from both players and tracks status.
    """
    def __init__(self, player_a: discord.Member, player_b: discord.Member, theme: dict, theme_check: bool, bot_interaction: discord.Interaction):
        super().__init__(timeout=600)
        self.player_a = player_a
        self.player_b = player_b
        self.theme = theme
        self.theme_check = theme_check
        self.bot_interaction = bot_interaction
        self.creation_a = None
        self.creation_b = None
        self.done_event = asyncio.Event()

    async def update_status(self):
        # Build status string
        status_a = "✅ Ready!" if self.creation_a else "⏳ Awaiting submission..."
        status_b = "✅ Ready!" if self.creation_b else "⏳ Awaiting submission..."

        theme_text = ""
        if self.theme:
            theme_text = f"**Setting/Theme:** {self.theme['name']}\n*Description:* {self.theme['description']}\n"
            if self.theme_check:
                theme_text += "⚠️ *Strict theme compliance checking is active! AI will inspect submissions.*\n"
            theme_text += "\n"

        embed = discord.Embed(
            title="⚔️ Clash of Creations - Submission Phase",
            description=(
                f"{theme_text}"
                f"Both players have 10 minutes to submit their combatants.\n\n"
                f"👤 {self.player_a.mention}: {status_a}\n"
                f"👤 {self.player_b.mention}: {status_b}"
            ),
            color=discord.Color.blue()
        )
        
        img_url, _ = config.get_theme_image(self.theme)
        if img_url:
            embed.set_image(url=img_url)
        
        await self.bot_interaction.edit_original_response(embed=embed, view=self)

        # Check if both are done
        if self.creation_a and self.creation_b:
            self.done_event.set()
            self.stop()

    @discord.ui.button(label="Submit Creation", style=discord.ButtonStyle.green, custom_id="submit_creation")
    async def submit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.player_a.id:
            if self.creation_a:
                await interaction.response.send_message("❌ You have already submitted!", ephemeral=True)
            else:
                modal = CreationModal('A', self)
                await interaction.response.send_modal(modal)
        elif interaction.user.id == self.player_b.id:
            if self.creation_b:
                await interaction.response.send_message("❌ You have already submitted!", ephemeral=True)
            else:
                modal = CreationModal('B', self)
                await interaction.response.send_modal(modal)
        else:
            await interaction.response.send_message("❌ You are not part of this duel!", ephemeral=True)

    async def on_timeout(self):
        self.stop()
        self.done_event.set() # Awake the waiter loop to handle the timeout outcome


class ClashChallengeView(discord.ui.View):
    """
    A view containing 'Accept' and 'Decline' buttons for the challenged player in a 1v1 duel.
    """
    def __init__(self, player_a: discord.Member, player_b: discord.Member, theme: dict):
        super().__init__(timeout=300)
        self.player_a = player_a
        self.player_b = player_b
        self.theme = theme
        self.accepted = None
        self.response_interaction = None

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green, emoji="⚔️")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_b.id:
            await interaction.response.send_message("❌ You cannot accept this challenge!", ephemeral=True)
            return

        self.accepted = True
        self.response_interaction = interaction
        self.stop()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red, emoji="🛡️")
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_b.id:
            await interaction.response.send_message("❌ You cannot decline this challenge!", ephemeral=True)
            return

        self.accepted = False
        self.response_interaction = interaction
        self.stop()

    async def on_timeout(self):
        self.accepted = None
        self.stop()


class DuelCog(commands.Cog):
    """
    Discord Cog containing commands and handlers for 1v1 creation duels.
    """
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="clash", description="Challenge another player to a creative 1v1 duel.")
    @app_commands.describe(
        opponent="The player you want to challenge.",
        theme_enabled="Whether to pick a random theme for the battle.",
        theme_check="If enabled, AI will reject submissions that do not fit the theme."
    )
    async def clash(self, interaction: discord.Interaction, opponent: discord.Member, theme_enabled: bool = True, theme_check: bool = True):
        # Validations
        if opponent.bot:
            await interaction.response.send_message("❌ You cannot challenge bots! They are too smart for this game.", ephemeral=True)
            return
        if opponent.id == interaction.user.id:
            await interaction.response.send_message("❌ You cannot challenge yourself! Play with friends.", ephemeral=True)
            return

        # Choose a theme if enabled
        theme = config.get_random_theme() if theme_enabled else None
        theme_text = ""
        if theme:
            theme_text = f"**Setting/Theme:** {theme['name']}\n*Description:* {theme['description']}\n\n"

        # 1. Challenge phase
        view = ClashChallengeView(interaction.user, opponent, theme)
        embed = discord.Embed(
            title="⚔️ A Duel Challenge has been Issued!",
            description=(
                f"👤 {interaction.user.mention} has challenged {opponent.mention} to a Clash of Creations!\n\n"
                f"{theme_text}"
                f"**{opponent.display_name}**, do you accept this battle?"
            ),
            color=discord.Color.orange()
        )
        
        img_url, file = config.get_theme_image(theme)
        if img_url:
            embed.set_image(url=img_url)
        
        if file:
            await interaction.response.send_message(content=opponent.mention, embed=embed, view=view, file=file)
        else:
            await interaction.response.send_message(content=opponent.mention, embed=embed, view=view)
        
        # Wait for acceptor
        await view.wait()

        # Handle decline / timeout
        if view.accepted is None:
            embed.description = f"⏱️ Challenge to {opponent.mention} expired. Nobody home!"
            embed.color = discord.Color.dark_gray()
            await interaction.edit_original_response(embed=embed, view=None)
            return
        
        if not view.accepted:
            embed.description = f"🛡️ {opponent.mention} has declined the challenge. They retreated!"
            embed.color = discord.Color.red()
            await view.response_interaction.response.edit_message(embed=embed, view=None)
            return

        # 2. Submission phase (accepted!)
        submission_view = ClashSubmissionView(interaction.user, opponent, theme, theme_check, interaction)
        
        # We edit the message on the *accept* interaction to update it immediately and clean up buttons
        await view.response_interaction.response.defer() # Acknowledge acceptance
        await submission_view.update_status()

        # Wait for submissions or timeout
        await submission_view.done_event.wait()

        # Check outcomes of submission
        if not submission_view.creation_a or not submission_view.creation_b:
            # One or both timed out
            timeout_embed = discord.Embed(
                title="⚔️ Clash Cancelled",
                description="⏱️ The submission phase timed out. One or both players failed to submit their creations.",
                color=discord.Color.red()
            )
            await interaction.edit_original_response(embed=timeout_embed, view=None)
            return

        # Disable submit button during processing
        for child in submission_view.children:
            child.disabled = True
        await interaction.edit_original_response(view=submission_view)

        # 3. AI Judgment phase
        eval_embed = discord.Embed(
            title="🔮 The Arena Master is Evaluating...",
            description="Reading your creations and simulating the battle. Please wait...",
            color=discord.Color.purple()
        )
        await interaction.edit_original_response(embed=eval_embed, view=None)

        # Call AI asynchronously
        try:
            creation_a_desc, creation_b_desc, fight_narrative, winner_code, reason = await ai_client.generate_battle(
                player_a_name=interaction.user.display_name,
                creation_a=submission_view.creation_a,
                player_b_name=opponent.display_name,
                creation_b=submission_view.creation_b,
                theme=theme
            )
        except Exception as e:
            err_embed = discord.Embed(
                title="❌ Arena System Failure",
                description=f"An error occurred while simulating the battle: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.edit_original_response(embed=err_embed)
            return

        # Identify winner
        winner = interaction.user if winner_code == 'A' else opponent
        loser = opponent if winner_code == 'A' else interaction.user
        winner_creation = submission_view.creation_a if winner_code == 'A' else submission_view.creation_b
        
        # Save to DB
        await database.update_player_stats(winner.id, winner.display_name, duel_win=True)
        await database.update_player_stats(loser.id, loser.display_name, duel_win=False)
        
        # Format aggregate narrative log
        narrative_log = (
            f"Combatants Analysis:\n"
            f"- A ({interaction.user.display_name}): {creation_a_desc}\n"
            f"- B ({opponent.display_name}): {creation_b_desc}\n\n"
            f"Fight:\n{fight_narrative}\n\n"
            f"Winner: {winner.display_name}\n"
            f"Reason: {reason}"
        )
        
        await database.log_match(
            match_type='duel',
            player_a_id=interaction.user.id,
            player_b_id=opponent.id,
            creation_a=submission_view.creation_a,
            creation_b=submission_view.creation_b,
            winner_id=winner.id,
            narrative=narrative_log
        )

        # Show final result
        result_embed = discord.Embed(
            title=f"👑 {winner.display_name} Wins! 👑",
            color=discord.Color.from_rgb(255, 215, 0) # Gold
        )
        result_embed.set_thumbnail(url=winner.display_avatar.url)
        
        theme_desc = ""
        if theme:
            theme_desc = f"🎭 **Theme/Setting:** {theme['name']} - *{theme['description']}*\n"
            
        result_embed.description = (
            f"# {winner.mention} has claimed victory!\n\n"
            f"🏆 **Winning Creation:** `{winner_creation}`\n\n"
            f"💡 **Reason:** *{reason}*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{theme_desc}"
        )
            
        result_embed.add_field(
            name=f"🔴 {interaction.user.display_name}'s `{submission_view.creation_a}`",
            value=f"> *{creation_a_desc}*\n\u200b",
            inline=False
        )
        result_embed.add_field(
            name=f"🔵 {opponent.display_name}'s `{submission_view.creation_b}`",
            value=f"> *{creation_b_desc}*\n\u200b",
            inline=False
        )
        result_embed.add_field(
            name="💥 The Clash",
            value=f"### *{fight_narrative}*",
            inline=False
        )
        result_embed.set_footer(text="⚔️ Clash resolved! Check your /profile for stats.")
        
        img_url, file = config.get_theme_image(theme)
        if img_url:
            result_embed.set_image(url=img_url)
            
        try:
            await interaction.delete_original_response()
        except:
            pass
            
        if file:
            await interaction.followup.send(embed=result_embed, file=file)
        else:
            await interaction.followup.send(embed=result_embed)

async def setup(bot):
    await bot.add_cog(DuelCog(bot))
