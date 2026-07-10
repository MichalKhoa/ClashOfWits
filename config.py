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
        "description": "A rain-slicked, neon-lit alleyway in a futuristic megacity. Tech-glitches, cybernetics, and hacking are highly effective.",
        "image": "cyberpunk_neon_grid.png"
    },
    {
        "name": "Medieval Dragon's Lair",
        "description": "Inside a volcanic cavern filled with piles of gold and a sleeping dragon. High stakes, magic, and chivalry rule the day.",
        "image": "medieval_dragons_lair.png"
    },
    {
        "name": "Deep Ocean Trench",
        "description": "Under crushing water pressure surrounded by bioluminescent creatures. Movement is extremely slow, and water-based logic applies.",
        "image": "deep_ocean_trench.png"
    },
    {
        "name": "Kitchen Counter Brawl",
        "description": "Shrunk down to 1 inch tall on a busy kitchen counter. Utensils, ingredients, boiling pots, and toaster heat are deadly hazards.",
        "image": "kitchen_counter_brawl.png"
    },
    {
        "name": "Low Gravity Moon",
        "description": "On the dusty lunar surface. Jumps fly hundreds of feet high, impact is slow, and there is no air to carry sound.",
        "image": "low_gravity_moon.png"
    },
    {
        "name": "High Noon Saloon",
        "description": "A dusty wild west town at exactly 12:00 PM. High tension, dramatic pauses, tumbleweeds, and quick-draw speed are key.",
        "image": "high_noon_saloon.png"
    },
    {
        "name": "Glitchy Retro Game",
        "description": "An 8-bit platformer filled with lag, pixelation, random power-up blocks, floating platforms, and lava pits.",
        "image": "glitchy_retro_game.png"
    },
    {
        "name": "Disco Inferno",
        "description": "On a glowing dance floor under a giant disco ball. Combatants must dance to fight, and style points are factored into power.",
        "image": "disco_inferno.png"
    },
    {
        "name": "Microscopic Petri Dish",
        "description": "Battles occur at the cellular level. Giant amoebas, bacteria, and white blood cells roam the arena like wild beasts.",
        "image": "microscopic_petri_dish.png"
    },
    {
        "name": "Mad Max Wasteland",
        "description": "A scorched desert with scrap-metal cars, rusted spikes, roaring engines, and sandstorms.",
        "image": "mad_max_wasteland.png"
    },
    {
        "name": "Silent Film Era",
        "description": "The battle is black-and-white, slapstick-heavy, accompanied by a fast-paced piano track. Speeches are displayed on title cards.",
        "image": "silent_film_era.png"
    },
    {
        "name": "Unstable Dimension",
        "description": "Every few seconds, the laws of physics and gravity invert. What was once up is now down, and objects randomly change weight.",
        "image": "unstable_dimension.png"
    },
    {
        "name": "Giant Toy Box",
        "description": "In a messy kid's playroom. Cardboard castles, building blocks, rubber ducks, and action figures serve as weapons or terrain.",
        "image": "giant_toy_box.png"
    },
    {
        "name": "Candyland Sugar Rush",
        "description": "A land made entirely of sweets. Sticky marshmallow bogs, sharp candy canes, soda geysers, and extreme sugar rushes.",
        "image": "candyland_sugar_rush.png"
    },
    {
        "name": "Ancient Roman Colosseum",
        "description": "Before thousands of cheering spectating citizens. Gladiatorial weapons, lion cages, and satisfying the crowd are essential.",
        "image": "ancient_roman_colosseum.png"
    },
    {
        "name": "Haunted Victorian Mansion",
        "description": "Creaking floorboards, floating candelabras, and shifting paintings. Ghostly encounters, possessions, and spooky illusions are highly effective.",
        "image": "haunted_victorian_mansion.png"
    },
    {
        "name": "Prehistoric Dinosaur Jungle",
        "description": "A humid, ancient jungle dominated by towering ferns and active volcanoes. Beware of roaming T-Rexes, falling meteors, and primitive weapons.",
        "image": "prehistoric_dinosaur_jungle.png"
    },
    {
        "name": "Corporate Boardroom",
        "description": "A sterile, high-stakes meeting room of a mega-corporation. Synergies, leverage, buzzwords, PowerPoint slides, and coffee spills are lethal weapons.",
        "image": "corporate_boardroom.png"
    },
    {
        "name": "Space Opera Fleet Battle",
        "description": "Fighting in the vacuum of space between two colossal capital ships. Blaster fire, shield configurations, gravity wells, and dramatic monologues are key.",
        "image": "space_opera_fleet_battle.png"
    },
    {
        "name": "Magical Girl Anime Stadium",
        "description": "A sparkling, colorful arena filled with rainbows and glitter. Attacks must be shouted in long, overly-dramatic magical phrases with transformation sequences.",
        "image": "magical_girl_anime_stadium.png"
    },
    {
        "name": "Pirate Galleon in a Maelstrom",
        "description": "On the deck of a wooden galleon caught in a massive swirling whirlpool. Cannons, swinging ropes, sea shanties, and slippery decks dictate the battle.",
        "image": "pirate_galleon_in_a_maelstrom.png"
    },
    {
        "name": "Cyber-Garden Greenhouse",
        "description": "A giant glass dome filled with genetically engineered hyper-intelligent plants. Carnivorous vines, glowing pollen, and photosynthesis boosts are in play.",
        "image": "cyber_garden_greenhouse.png"
    },
    {
        "name": "Viking Fjord Snowstorm",
        "description": "A freezing, blizzard-swept fjord. Frozen weapons, frostbite hazards, loud war cries, and warm mead power-ups are common.",
        "image": "viking_fjord_snowstorm.png"
    },
    {
        "name": "Antique Library of Secrets",
        "description": "A labyrinth of towering bookshelves with magical books. Shushing librarians, paper cuts, flying spellbooks, and literal word-play are dominant.",
        "image": "antique_library_of_secrets.png"
    },
    {
        "name": "Retro-Futuristic Steampunk Airship",
        "description": "A massive, brass-and-wood airship soaring through the clouds. Steam-powered gadgets, clockwork gears, soot clouds, and structural damage hazards abound.",
        "image": "retro_futuristic_steampunk_airship.png"
    },
    {
        "name": "Inside a Living Motherboard",
        "description": "Combatants are digitized and fight on a green motherboard circuit. Antivirus bots, logic gates, firewalls, and data packets can be weaponized.",
        "image": "inside_a_living_motherboard.png"
    },
    {
        "name": "Dream Realm of Whimsy",
        "description": "A bizarre dreamscape where thoughts manifest instantly. Logic is optional, colors change based on mood, and pillow fights can be devastating.",
        "image": "dream_realm_of_whimsy.png"
    },
    {
        "name": "Haunted Amusement Park",
        "description": "A decaying theme park at midnight. Creepy clown animatronics, runaway roller coasters, hall of mirrors reflections, and cotton candy traps.",
        "image": "haunted_amusement_park.png"
    },
    {
        "name": "Comic Book Action Bubble",
        "description": "Every physical impact spawns giant, stylized sound effects ('POW!', 'BAM!', 'ZOOM!'). The hero or villain with the most dramatic backstory gets a stat boost.",
        "image": "comic_book_action_bubble.png"
    },
    {
        "name": "Cooking Show Kitchen",
        "description": "A high-pressure television cooking set. Combatants must prepare a culinary masterpiece while fighting, using spices, frying pans, and chef critiques as weapons.",
        "image": "cooking_show_kitchen.png"
    }
]

def get_random_theme() -> dict:
    """Returns a randomly selected theme dictionary."""
    return random.choice(THEMES)

def get_theme_image(theme: dict) -> tuple:
    """
    Given a theme dictionary, returns a tuple: (image_url_or_attachment_link, discord_file_object)
    
    - If the image is a URL, returns (image_url, None)
    - If the image is a local filename, constructs the path and returns ('attachment://filename.png', discord.File(path))
    - If not found or no image, returns (None, None)
    """
    import discord
    if not theme or not theme.get("image"):
        return None, None
        
    img = theme["image"]
    if img.startswith("http://") or img.startswith("https://"):
        return img, None
        
    # Check local path
    local_path = os.path.join("assets", "themes", img)
    if os.path.exists(local_path):
        return f"attachment://{img}", discord.File(local_path, filename=img)
        
    return None, None
