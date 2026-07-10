"""
battle_royale.py

Cog and UI components for Battle Royale style tournaments in Clash of Wits.
Manages the sign-up lobby, submission phase, matching brackets (including byes),
and the simulation/logging of all matches in the tournament bracket.
"""

import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import random
import os
from typing import List, Dict, Any
import config
import database
from ai_client import AIClient

ai_client = AIClient()

class BRSubmissionModal(discord.ui.Modal):
    """
    Discord UI Modal that allows tournament participants to submit their creation.
    Integrates theme-compliance checking using AIClient if active.
    """
    def __init__(self, user_id: int, view: 'BRSubmissionView'):
        """
        Initializes the submission modal for a specific user ID and parent view.
        """
        super().__init__(title="Submit Battle Royale Creation")
        self.user_id = user_id
        self.view = view

        self.creation_input = discord.ui.TextInput(
            label="What is your creation?",
            placeholder="e.g., A fire-breathing penguin; A black hole in a pocket...",
            style=discord.TextStyle.paragraph,
            max_length=400,
            required=True
        )
        self.add_item(self.creation_input)

    async def on_submit(self, interaction: discord.Interaction):
        """
        Handles the submission event. Performs theme validation if enabled,
        saves the player's creation, and refreshes the submission view state.
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
        self.view.creations[self.user_id] = creation_text
        
        # Increment creation submission count in DB
        member = interaction.guild.get_member(self.user_id)
        await database.update_player_stats(self.user_id, member.display_name if member else "Unknown", submitted=True)
        
        await interaction.followup.send("✅ Creation submitted and approved!", ephemeral=True)
        await self.view.update_status()


class BRSubmissionView(discord.ui.View):
    """
    Discord UI View managing player submissions during the Battle Royale phase.
    Enables early starts by the host/moderators.
    """
    def __init__(self, contestants: List[discord.Member], theme: dict, theme_check: bool, host: discord.Member, bot_interaction: discord.Interaction):
        """
        Initializes the submission view with target contestants, theme, host,
        and original interaction.
        """
        super().__init__(timeout=600) # 10 minutes to submit
        self.contestants = contestants
        self.theme = theme
        self.theme_check = theme_check
        self.host = host
        self.bot_interaction = bot_interaction
        self.creations = {} # user_id -> creation_text
        self.done_event = asyncio.Event()

    async def update_status(self):
        """
        Refreshes the status message list of ready contestants.
        Stops the view and triggers the completion event when all participants have submitted.
        """
        status_lines = []
        for c in self.contestants:
            status = "✅ Ready!" if c.id in self.creations else "⏳ Awaiting..."
            status_lines.append(f"👤 {c.mention}: {status}")

        theme_text = ""
        if self.theme:
            theme_text = f"**Theme/Setting:** {self.theme['name']}\n*Description:* {self.theme['description']}\n"
            if self.theme_check:
                theme_text += "⚠️ *Strict theme compliance checking is active! AI will inspect submissions.*\n"
            theme_text += "\n"

        embed = discord.Embed(
            title="👑 Battle Royale - Submission Phase",
            description=(
                f"{theme_text}"
                f"Contestants, submit your champion! You have 10 minutes.\n"
                f"Players who do not submit will be disqualified.\n\n"
                + "\n".join(status_lines)
            ),
            color=discord.Color.blue()
        )
        
        img_url, _ = config.get_theme_image(self.theme)
        if img_url:
            embed.set_image(url=img_url)
            
        try:
            await self.bot_interaction.edit_original_response(embed=embed, view=self)
        except Exception:
            pass

        # Check if all submitted
        if len(self.creations) == len(self.contestants):
            self.done_event.set()
            self.stop()

    @discord.ui.button(label="Submit Creation", style=discord.ButtonStyle.green, custom_id="br_submit")
    async def submit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Button click handler for registered players to submit their creations.
        """
        user_ids = [c.id for c in self.contestants]
        if interaction.user.id not in user_ids:
            await interaction.response.send_message("❌ You are not registered in this Battle Royale!", ephemeral=True)
            return

        if interaction.user.id in self.creations:
            await interaction.response.send_message("❌ You have already submitted your creation!", ephemeral=True)
            return

        modal = BRSubmissionModal(interaction.user.id, self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Start Clash", style=discord.ButtonStyle.blurple, custom_id="br_force_start")
    async def force_start_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Button click handler allowing the host or a moderator to start the tournament early,
        provided there are at least two submissions.
        """
        is_host = interaction.user.id == self.host.id
        is_mod = interaction.user.guild_permissions.manage_messages
        
        if not (is_host or is_mod):
            await interaction.response.send_message("❌ Only the host or a moderator can start the tournament early!", ephemeral=True)
            return
            
        if len(self.creations) < 2:
            await interaction.response.send_message("❌ You need at least 2 submissions to start the tournament!", ephemeral=True)
            return
            
        await interaction.response.send_message("🚀 Starting the tournament early with current submissions!", ephemeral=True)
        self.done_event.set()
        self.stop()

    async def on_timeout(self):
        """
        Fired when the submission phase's 10-minute timer expires.
        """
        self.stop()
        self.done_event.set()


class BRLobbyView(discord.ui.View):
    """
    Discord UI View representing the sign-up lobby for a Battle Royale tournament.
    """
    def __init__(self, host: discord.Member, theme: dict, bot_interaction: discord.Interaction):
        """
        Initializes the lobby with the host, target battle theme, and the interaction context.
        """
        super().__init__(timeout=300) # 5 minutes lobby before expiring
        self.host = host
        self.theme = theme
        self.bot_interaction = bot_interaction
        self.contestants: List[discord.Member] = []
        self.started = False
        self.done_event = asyncio.Event()

    def build_lobby_embed_and_file(self) -> tuple:
        """
        Constructs and returns the lobby status Embed and associated file attachment.
        
        Returns:
            tuple: (discord.Embed, discord.File or None)
        """
        contestant_list = "\n".join([f"• {c.mention}" for c in self.contestants]) if self.contestants else "*No one has joined yet.*"
        
        theme_text = ""
        embed = discord.Embed(
            title="👑 Battle Royale Lobby",
            color=discord.Color.gold()
        )
        
        file = None
        if self.theme:
            theme_text = f"**Setting/Theme:** {self.theme['name']}\n*Description:* {self.theme['description']}\n\n"
            img_url, file = config.get_theme_image(self.theme)
            if img_url:
                embed.set_image(url=img_url)

        embed.description = (
            f"Host: {self.host.mention}\n\n"
            f"{theme_text}"
            f"Click **Join** to enter the battle! (Max 8 players allowed)\n"
            f"The host can start the tournament when ready.\n\n"
            f"**Joined Contestants ({len(self.contestants)}/8):**\n{contestant_list}"
        )
        return embed, file

    async def update_lobby_embed(self):
        """
        Refreshes the active lobby message with updated contestant list.
        """
        embed, _ = self.build_lobby_embed_and_file()
        try:
            await self.bot_interaction.edit_original_response(embed=embed, view=self)
        except Exception:
            pass

    @discord.ui.button(label="Join", style=discord.ButtonStyle.green, emoji="⚔️")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Button click handler that signs a player up for the tournament.
        """
        if interaction.user.bot:
            await interaction.response.send_message("❌ Bots cannot join!", ephemeral=True)
            return

        if interaction.user in self.contestants:
            await interaction.response.send_message("❌ You have already joined the lobby!", ephemeral=True)
            return

        if len(self.contestants) >= 8:
            await interaction.response.send_message("❌ The lobby is full! (Maximum 8 players allowed).", ephemeral=True)
            return

        self.contestants.append(interaction.user)
        await interaction.response.send_message("✅ Joined the Battle Royale lobby!", ephemeral=True)
        await self.update_lobby_embed()

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.red, emoji="🛡️")
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Button click handler that removes a player from the lobby.
        """
        if interaction.user not in self.contestants:
            await interaction.response.send_message("❌ You are not in the lobby!", ephemeral=True)
            return

        self.contestants.remove(interaction.user)
        await interaction.response.send_message("✅ Left the lobby.", ephemeral=True)
        await self.update_lobby_embed()

    @discord.ui.button(label="Start Tournament", style=discord.ButtonStyle.blurple, emoji="🏆")
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Button click handler allowing the host or a moderator to lock in contestants
        and start the submission phase.
        """
        # Only the host or someone with manage_messages can start
        is_host = interaction.user.id == self.host.id
        is_admin = interaction.user.guild_permissions.manage_messages

        if not (is_host or is_admin):
            await interaction.response.send_message("❌ Only the lobby host or an admin can start the tournament!", ephemeral=True)
            return

        if len(self.contestants) < 2:
            await interaction.response.send_message("❌ You need at least 2 players to start a Battle Royale!", ephemeral=True)
            return

        self.started = True
        self.stop()
        self.done_event.set()
        await interaction.response.send_message("🚀 Starting the tournament!", ephemeral=True)

    async def on_timeout(self):
        """
        Fired when the lobby's 5-minute sign-up timer expires.
        """
        self.stop()
        self.done_event.set()


class BattleRoyaleCog(commands.Cog):
    """
    Discord Cog containing commands for launching and executing Battle Royale tournaments.
    """
    def __init__(self, bot):
        """
        Initializes BattleRoyaleCog with a reference to the running bot instance.
        """
        self.bot = bot

    @app_commands.command(name="clash_br", description="Starts a Clash of Creations Battle Royale tournament.")
    @app_commands.describe(
        theme_enabled="Whether to pick a random theme for this Battle Royale.",
        theme_check="If enabled, AI will reject submissions that do not fit the theme."
    )
    async def clash_br(self, interaction: discord.Interaction, theme_enabled: bool = True, theme_check: bool = True):
        """
        Slash command to host a Battle Royale tournament.
        Launches the sign-up lobby, coordinates submission, shuffles brackets,
        runs matchups using AI simulation, and crowns the final champion.
        """
        # Choose theme
        theme = config.get_random_theme() if theme_enabled else None
        
        # 1. Lobby Phase
        lobby_view = BRLobbyView(interaction.user, theme, interaction)
        embed, file = lobby_view.build_lobby_embed_and_file()
        if file:
            await interaction.response.send_message(embed=embed, view=lobby_view, file=file)
        else:
            await interaction.response.send_message(embed=embed, view=lobby_view)

        # Wait for start or timeout
        await lobby_view.done_event.wait()

        if not lobby_view.started:
            # Lobby expired or cancelled
            expire_embed = discord.Embed(
                title="👑 Battle Royale Cancelled",
                description="⏱️ The lobby timed out or was closed without starting.",
                color=discord.Color.red()
            )
            await interaction.edit_original_response(embed=expire_embed, view=None)
            return

        # 2. Submission Phase
        contestants = lobby_view.contestants.copy()
        submission_view = BRSubmissionView(contestants, theme, theme_check, interaction.user, interaction)
        await submission_view.update_status()

        # Wait for submissions
        await submission_view.done_event.wait()

        # Filter out contestants who didn't submit
        creations = submission_view.creations
        active_contestants = [c for c in contestants if c.id in creations]

        if len(active_contestants) < 2:
            cancel_embed = discord.Embed(
                title="👑 Battle Royale Cancelled",
                description="❌ Not enough creations were submitted. We need at least 2 active players to run the bracket.",
                color=discord.Color.red()
            )
            await interaction.edit_original_response(embed=cancel_embed, view=None)
            return

        # Update contestants to match active list
        contestants = active_contestants

        # Let the server know the bracket is locked
        locked_embed = discord.Embed(
            title="👑 Battle Royale Bracket Locked!",
            description=f"Locked in **{len(contestants)}** combatants. Simulating tournament brackets now...",
            color=discord.Color.orange()
        )
        try:
            await interaction.delete_original_response()
        except:
            pass
            
        await interaction.followup.send(embed=locked_embed)
        await asyncio.sleep(2) # Brief pause for effect

        # 3. Tournament Bracket Execution Loop
        round_num = 1
        current_round_players = contestants.copy()
        
        # Track all participants for final DB stats (br_played)
        all_participants = contestants.copy()

        # Let's announce the tournament start in the channel
        channel = interaction.channel

        while len(current_round_players) > 1:
            round_name = "Finals" if len(current_round_players) == 2 else f"Round {round_num}"
            if len(current_round_players) == 4:
                round_name = "Semi-Finals"

            round_announcement = discord.Embed(
                title=f"🏆 Clash of Creations BR - {round_name}",
                description=f"Matchups are being drawn for the **{len(current_round_players)}** remaining combatants!",
                color=discord.Color.blue()
            )
            await channel.send(embed=round_announcement)
            await asyncio.sleep(3)

            # Matchmaking: shuffle players
            random.shuffle(current_round_players)
            next_round_players = []

            # Handle odd number of players - give someone a bye
            if len(current_round_players) % 2 != 0:
                bye_player = current_round_players.pop()
                bye_embed = discord.Embed(
                    title="🍀 Lucky Break!",
                    description=f"{bye_player.mention} gets a **bye** this round and automatically advances to the next round!",
                    color=discord.Color.green()
                )
                await channel.send(embed=bye_embed)
                next_round_players.append(bye_player)
                await asyncio.sleep(3)

            # Pair them up
            matchups = []
            for i in range(0, len(current_round_players), 2):
                matchups.append((current_round_players[i], current_round_players[i+1]))

            # Run matches in the round
            for index, (p_a, p_b) in enumerate(matchups):
                match_header = discord.Embed(
                    title=f"⚔️ {round_name} - Match {index + 1}",
                    description=(
                        f"**{p_a.display_name}** vs **{p_b.display_name}**\n\n"
                        f"🛡️ **{p_a.display_name}'s Creation:** `{creations[p_a.id]}`\n"
                        f"🛡️ **{p_b.display_name}'s Creation:** `{creations[p_b.id]}`"
                    ),
                    color=discord.Color.purple()
                )
                header_msg = await channel.send(embed=match_header)

                # Show thinking status
                async with channel.typing():
                    # Generate battle narrative
                    try:
                        creation_a_desc, creation_b_desc, fight_narrative, winner_code, reason = await ai_client.generate_battle(
                            player_a_name=p_a.display_name,
                            creation_a=creations[p_a.id],
                            player_b_name=p_b.display_name,
                            creation_b=creations[p_b.id],
                            theme=theme
                        )
                    except Exception as e:
                        # Fallback error resolution
                        creation_a_desc = "A glitchy fighter."
                        creation_b_desc = "Another glitchy fighter."
                        fight_narrative = f"The battle was interrupted by a spatial rift! ({str(e)})"
                        winner_code = random.choice(['A', 'B'])
                        reason = "Random coin flip due to system error."

                winner = p_a if winner_code == 'A' else p_b
                loser = p_b if winner_code == 'A' else p_a
                winner_creation = creations[p_a.id] if winner_code == 'A' else creations[p_b.id]

                next_round_players.append(winner)

                # Format aggregate narrative log
                narrative_log = (
                    f"Combatants Analysis:\n"
                    f"- A ({p_a.display_name}): {creation_a_desc}\n"
                    f"- B ({p_b.display_name}): {creation_b_desc}\n\n"
                    f"Fight:\n{fight_narrative}\n\n"
                    f"Winner: {winner.display_name}\n"
                    f"Reason: {reason}"
                )

                # Log individual matches in the history database
                await database.log_match(
                    match_type='br',
                    player_a_id=p_a.id,
                    player_b_id=p_b.id,
                    creation_a=creations[p_a.id],
                    creation_b=creations[p_b.id],
                    winner_id=winner.id,
                    narrative=narrative_log
                )

                # Post match result
                result_embed = discord.Embed(
                    title=f"👑 {winner.display_name} Wins Match {index + 1}! 👑",
                    color=discord.Color.from_rgb(255, 215, 0) # Gold
                )
                result_embed.set_thumbnail(url=winner.display_avatar.url)
                
                theme_desc = ""
                if theme:
                    theme_desc = f"🎭 **Theme:** {theme['name']}\n"
                    
                result_embed.description = (
                    f"# {winner.mention} has claimed victory!\n\n"
                    f"🏆 **Winning Creation:** `{winner_creation}`\n\n"
                    f"💡 **Reason:** *{reason}*\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"{theme_desc}"
                )
                
                result_embed.add_field(
                    name=f"🔴 {p_a.display_name}'s `{creations[p_a.id]}`",
                    value=f"> *{creation_a_desc}*\n\u200b",
                    inline=False
                )
                result_embed.add_field(
                    name=f"🔵 {p_b.display_name}'s `{creations[p_b.id]}`",
                    value=f"> *{creation_b_desc}*\n\u200b",
                    inline=False
                )
                result_embed.add_field(
                    name="💥 The Clash",
                    value=f"### *{fight_narrative}*",
                    inline=False
                )
                
                img_url, file = config.get_theme_image(theme)
                if img_url:
                    result_embed.set_image(url=img_url)
                
                if file:
                    await channel.send(embed=result_embed, file=file)
                else:
                    await channel.send(embed=result_embed)
                
                # Sleep between matches to allow users to read the battle text
                await asyncio.sleep(12)

            current_round_players = next_round_players
            round_num += 1

        # 4. Final Champion Crowned
        champion = current_round_players[0]
        
        # Log stats for all players
        for player in all_participants:
            is_winner = (player.id == champion.id)
            await database.update_player_stats(player.id, player.display_name, br_win=is_winner)

        # Send final celebration embed
        victory_embed = discord.Embed(
            title="👑 BATTLE ROYALE CHAMPION 👑",
            description=(
                f"🎉 Congratulations to {champion.mention}! 🎉\n\n"
                f"Their creation `{creations[champion.id]}` has conquered the arena and outlasted all other creations to claim the ultimate title!\n\n"
                f"Check your updated standings on the `/leaderboard`!"
            ),
            color=discord.Color.from_rgb(255, 215, 0) # Shiny Gold
        )
        victory_embed.set_thumbnail(url=champion.display_avatar.url)
        
        await channel.send(content=champion.mention, embed=victory_embed)

async def setup(bot):
    """
    Asynchronous function to load the BattleRoyaleCog extension into the bot.
    """
    await bot.add_cog(BattleRoyaleCog(bot))
