"""
training.py

Cog and UI components for single-player training mode in Clash of Wits.
Allows a user to practice against bot-generated creations under a random theme.
"""

import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import config
import database
from ai_client import AIClient

# Global AI Client instance
ai_client = AIClient()

class TrainingSubmissionModal(discord.ui.Modal):
    """
    Discord UI Modal that allows the player in training mode to submit their creation.
    Integrates theme-compliance checking using AIClient if active.
    """
    def __init__(self, view: 'TrainingView'):
        """
        Initializes the training submission modal.
        """
        super().__init__(title="Submit Your Creation")
        self.view = view

        self.creation_input = discord.ui.TextInput(
            label="What is your creation?",
            placeholder="e.g., A magnet-powered giant toaster; A black hole in a jar...",
            style=discord.TextStyle.paragraph,
            max_length=400,
            required=True
        )
        self.add_item(self.creation_input)

    async def on_submit(self, interaction: discord.Interaction):
        """
        Handles the submission event. Performs theme validation if enabled,
        saves the player's creation, and initiates the battle simulation.
        """
        # Defer immediately since calling LLM check takes time
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
        self.view.user_creation = creation_text
        
        # Increment creation submission count in DB
        await database.update_player_stats(interaction.user.id, interaction.user.display_name, submitted=True)
        
        await interaction.followup.send("✅ Creation submitted!", ephemeral=True)
        await self.view.run_battle(interaction)


class TrainingView(discord.ui.View):
    """
    Discord UI View managing the single player training interface, including
    the submission button and battle trigger.
    """
    def __init__(self, user: discord.Member, theme: dict, theme_check: bool, bot_creation: str, bot_interaction: discord.Interaction):
        """
        Initializes the training view with details of the participant,
        the active theme settings, the bot's creation, and the initiating interaction.
        """
        super().__init__(timeout=600)
        self.user = user
        self.theme = theme
        self.theme_check = theme_check
        self.bot_creation = bot_creation
        self.bot_interaction = bot_interaction
        self.user_creation = None

    @discord.ui.button(label="Submit Creation", style=discord.ButtonStyle.green, custom_id="submit_training_creation")
    async def submit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Button click handler that opens the TrainingSubmissionModal for the practicing player.
        """
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ This training session is not for you!", ephemeral=True)
            return

        modal = TrainingSubmissionModal(self)
        await interaction.response.send_modal(modal)

    async def run_battle(self, submission_interaction: discord.Interaction):
        """
        Simulates the battle between the user's creation and the bot's creation,
        logs the match history, and displays the final result.
        """
        # Disable submit button during processing
        for child in self.children:
            child.disabled = True
        await self.bot_interaction.edit_original_response(view=self)

        # Show evaluating status
        eval_embed = discord.Embed(
            title="🔮 The Arena Master is Evaluating...",
            description="Reading your creations and simulating the battle. Please wait...",
            color=discord.Color.purple()
        )
        await self.bot_interaction.edit_original_response(embed=eval_embed, view=None)

        # Call AI asynchronously
        try:
            creation_a_desc, creation_b_desc, fight_narrative, winner_code, reason = await ai_client.generate_battle(
                player_a_name=self.user.display_name,
                creation_a=self.user_creation,
                player_b_name="Arena Bot",
                creation_b=self.bot_creation,
                theme=self.theme
            )
        except Exception as e:
            err_embed = discord.Embed(
                title="❌ Arena System Failure",
                description=f"An error occurred while simulating the battle: {str(e)}",
                color=discord.Color.red()
            )
            await self.bot_interaction.edit_original_response(embed=err_embed)
            return

        # Identify winner
        user_won = (winner_code == 'A')
        winner_name = self.user.display_name if user_won else "Arena Bot"
        
        # Save to DB history (using ID 0 for the bot)
        narrative_log = (
            f"Combatants Analysis:\n"
            f"- A ({self.user.display_name}): {creation_a_desc}\n"
            f"- B (Arena Bot): {creation_b_desc}\n\n"
            f"Fight:\n{fight_narrative}\n\n"
            f"Winner: {winner_name}\n"
            f"Reason: {reason}"
        )
        
        await database.log_match(
            match_type='training',
            player_a_id=self.user.id,
            player_b_id=0,
            creation_a=self.user_creation,
            creation_b=self.bot_creation,
            winner_id=self.user.id if user_won else 0,
            narrative=narrative_log
        )

        # Show final result
        result_color = discord.Color.green() if user_won else discord.Color.red()
        result_title = "🏆 Training Victory! 🏆" if user_won else "💀 Training Defeat! 💀"

        result_embed = discord.Embed(
            title=result_title,
            color=result_color
        )
        
        theme_desc = ""
        if self.theme:
            theme_desc = f"🎭 **Theme/Setting:** {self.theme['name']} - *{self.theme['description']}*\n"
            
        result_embed.description = (
            f"# {self.user.mention} " + ("defeated the Arena Bot!" if user_won else "was defeated by the Arena Bot!") + "\n\n"
            f"🏆 **Winner:** `{winner_name}`\n\n"
            f"💡 **Reason:** *{reason}*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{theme_desc}"
        )
            
        result_embed.add_field(
            name=f"🔴 {self.user.display_name}'s `{self.user_creation}`",
            value=f"> *{creation_a_desc}*\n\u200b",
            inline=True
        )
        result_embed.add_field(
            name=f"🤖 Arena Bot's `{self.bot_creation}`",
            value=f"> *{creation_b_desc}*\n\u200b",
            inline=True
        )
        result_embed.set_footer(text="🎯 Training completed! Keep practicing to climb the ranks.")
        
        img_url, file = config.get_theme_image(self.theme)
        if img_url:
            result_embed.set_image(url=img_url)
            
        try:
            await self.bot_interaction.delete_original_response()
        except:
            pass
            
        if file:
            await self.bot_interaction.followup.send(embed=result_embed, file=file)
        else:
            await self.bot_interaction.followup.send(embed=result_embed)

    async def on_timeout(self):
        """
        Fired when the submission phase's 10-minute timer expires.
        """
        self.stop()


class TrainingCog(commands.Cog):
    """
    Discord Cog containing commands for managing single-player training matches against the bot.
    """
    def __init__(self, bot):
        """
        Initializes TrainingCog with a reference to the running bot instance.
        """
        self.bot = bot

    @app_commands.command(name="clash_train", description="Start a single-player training match against the bot.")
    @app_commands.describe(
        theme_enabled="Whether to pick a random theme for the training match.",
        theme_check="If enabled, AI will reject submissions that do not fit the theme."
    )
    async def clash_train(self, interaction: discord.Interaction, theme_enabled: bool = True, theme_check: bool = True):
        """
        Slash command to initialize a training match. Generates the theme and bot's creation,
        then presents the user with the challenge.
        """
        await interaction.response.defer()

        # Pick a theme if enabled
        theme = config.get_random_theme() if theme_enabled else None
        
        # Generate the bot's themed creation
        bot_creation = await ai_client.generate_themed_creation(theme)

        theme_text = ""
        if theme:
            theme_text = f"**Setting/Theme:** {theme['name']}\n*Description:* {theme['description']}\n\n"

        embed = discord.Embed(
            title="🎯 Single-Player Training Mode",
            description=(
                f"Prepare yourself! You are sparring against the **Arena Bot**.\n\n"
                f"{theme_text}"
                f"🤖 **Arena Bot's Creation to Beat:** `{bot_creation}`\n\n"
                f"Click **Submit Creation** to write a combatant that can defeat it!"
            ),
            color=discord.Color.blue()
        )

        img_url, file = config.get_theme_image(theme)
        if img_url:
            embed.set_image(url=img_url)

        view = TrainingView(interaction.user, theme, theme_check, bot_creation, interaction)

        if file:
            await interaction.followup.send(embed=embed, view=view, file=file)
        else:
            await interaction.followup.send(embed=embed, view=view)


async def setup(bot):
    """
    Asynchronous function to load the TrainingCog extension into the bot.
    """
    await bot.add_cog(TrainingCog(bot))
