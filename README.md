# Clash of Creations Discord Bot ⚔️👑

A Discord bot similar to Ghosty bot's "Clash of Creations: Battle Royale", utilizing either the **Gemini API** or **Ollama models** (like Llama 3) to judge creative, high-concept battles.

Players submit any creation they can imagine (objects, concepts, characters) and the AI simulates an epic, hilarious narrative of the fight, determines a victor, tracks database stats, and crowns server champions.

---

## ✨ Features

- **🎭 Random Battle Themes:** Every duel or Battle Royale can optionally generate a random theme setting (e.g., *Cyberpunk*, *Kitchen Counter*, *Low Gravity*, *Silent Film*). The narrative will adapt to this setting, and players are warned of the theme beforehand!
- **⚔️ 1v1 Duels (`/clash`):** Challenge a user. If they accept, both players submit their creations privately using a Discord modal. The AI evaluates the matchup and prints the battle story.
- **👑 Battle Royale (`/clash_br`):** Start a lobby where any player can join. Once started, all joined players submit their creations. The bot automatically creates a tournament bracket, generates narratives for each match, awards "byes" if there is an odd number of players, and advances winners round-by-round until a final champion is crowned.
- **📊 Profile & Stats (`/profile` & `/leaderboard`):** A persistent SQLite database stores duel wins, BR wins, and overall win rates. `/leaderboard` displays the top 10 champions in the server.
- **🤖 Dual AI Engines:** Works out of the box with the **Gemini API** (using the fast and free-tier friendly `gemini-2.5-flash` model) or **Ollama** (for running free, local LLMs like `llama3` or `mistral`).

---

## 🚀 Getting Started

### 1. Requirements
- Python 3.10 or higher
- A Discord Bot Token (from the [Discord Developer Portal](https://discord.com/developers/applications))
- An LLM provider:
  - **Gemini:** A free API key from [Google AI Studio](https://aistudio.google.com/).
  - **Ollama:** Ollama running locally (`ollama run llama3`) on `http://localhost:11434`.

### 2. Installation
Clone/download the repository, then install the dependencies in your virtual environment:

```bash
# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration
Copy the `.env.example` file to `.env` and fill in your keys:

```bash
cp .env.example .env
```

Open `.env` and fill in:
```ini
DISCORD_TOKEN=your_discord_bot_token_here
OWNER_ID=your_discord_user_id

# Choose "gemini" or "ollama"
AI_PROVIDER=gemini

# For Gemini:
GEMINI_API_KEY=your_google_ai_studio_api_key

# For Ollama:
OLLAMA_API_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

### 4. Running the Bot
Start the bot script:

```bash
python main.py
```
The bot will automatically connect to Discord, initialize the local SQLite database (`clash_of_wits.db`), and register the slash commands globally.

---

## 🎮 Commands

- `/clash opponent: @User [theme_enabled: True/False]` - Challenges another member to a 1v1 duel.
- `/clash_br [theme_enabled: True/False]` - Starts a multiplayer Battle Royale tournament lobby.
- `/profile [member]` - Views the specified member's (or your own) wins, losses, win rate, and total submissions.
- `/leaderboard` - Displays the top 10 fighters in the server based on total wins (Duels + Battle Royales).

---

## 🛠️ Project Structure

- `main.py` - Sets up the Discord bot client, loads extensions, and syncs slash commands.
- `config.py` - Manages environment variables and stores the database of random themes.
- `database.py` - Implements the SQLite database connection, queries, and transactions.
- `ai_client.py` - Direct asynchronous client for Gemini API and Ollama, processing JSON outputs.
- `cogs/`
  - `duel.py` - Handles 1v1 challenges, acceptance views, and modal inputs.
  - `battle_royale.py` - Coordinates tournament lobbies, brackets, matches, and progression.
  - `stats.py` - Implements the leaderboard and user profiles.
