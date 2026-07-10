import os
import random
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Discord Configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "210022124423741440"))

# AI Configuration
# Support "gemini" or "ollama"
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# List of battle themes and their descriptions/rules
THEMES = [
    {
        "name": "Cyberpunk Neon Grid",
        "description": "A rain-slicked, neon-lit alleyway in a futuristic megacity. Tech-glitches, cybernetics, and hacking are highly effective."
    },
    {
        "name": "Medieval Dragon's Lair",
        "description": "Inside a volcanic cavern filled with piles of gold and a sleeping dragon. High stakes, magic, and chivalry rule the day."
    },
    {
        "name": "Deep Ocean Trench",
        "description": "Under crushing water pressure surrounded by bioluminescent creatures. Movement is extremely slow, and water-based logic applies."
    },
    {
        "name": "Kitchen Counter Brawl",
        "description": "Shrunk down to 1 inch tall on a busy kitchen counter. Utensils, ingredients, boiling pots, and toaster heat are deadly hazards."
    },
    {
        "name": "Low Gravity Moon",
        "description": "On the dusty lunar surface. Jumps fly hundreds of feet high, impact is slow, and there is no air to carry sound."
    },
    {
        "name": "High Noon Saloon",
        "description": "A dusty wild west town at exactly 12:00 PM. High tension, dramatic pauses, tumbleweeds, and quick-draw speed are key."
    },
    {
        "name": "Glitchy Retro Game",
        "description": "An 8-bit platformer filled with lag, pixelation, random power-up blocks, floating platforms, and lava pits."
    },
    {
        "name": "Disco Inferno",
        "description": "On a glowing dance floor under a giant disco ball. Combatants must dance to fight, and style points are factored into power."
    },
    {
        "name": "Microscopic Petri Dish",
        "description": "Battles occur at the cellular level. Giant amoebas, bacteria, and white blood cells roam the arena like wild beasts."
    },
    {
        "name": "Mad Max Wasteland",
        "description": "A scorched desert with scrap-metal cars, rusted spikes, roaring engines, and sandstorms."
    },
    {
        "name": "Silent Film Era",
        "description": "The battle is black-and-white, slapstick-heavy, accompanied by a fast-paced piano track. Speeches are displayed on title cards."
    },
    {
        "name": "Unstable Dimension",
        "description": "Every few seconds, the laws of physics and gravity invert. What was once up is now down, and objects randomly change weight."
    },
    {
        "name": "Giant Toy Box",
        "description": "In a messy kid's playroom. Cardboard castles, building blocks, rubber ducks, and action figures serve as weapons or terrain."
    },
    {
        "name": "Candyland Sugar Rush",
        "description": "A land made entirely of sweets. Sticky marshmallow bogs, sharp candy canes, soda geysers, and extreme sugar rushes."
    },
    {
        "name": "Ancient Roman Colosseum",
        "description": "Before thousands of cheering spectating citizens. Gladiatorial weapons, lion cages, and satisfying the crowd are essential."
    }
]

def get_random_theme() -> dict:
    """Returns a randomly selected theme dictionary."""
    return random.choice(THEMES)
