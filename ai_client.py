"""
ai_client.py

AI Client module for Clash of Wits.
Interfaces with Gemini and Ollama APIs to evaluate battles, generate fight narratives,
and validate if submissions fit battle themes.
"""

import json
import re
import aiohttp
from typing import Dict, Any, Tuple
import config

class AIClient:
    """
    Client for interacting with LLM providers (Gemini/Ollama) to perform theme checking
    and simulate clashes between player creations.
    """
    def __init__(self):
        """
        Initializes the AIClient with provider configurations loaded from config.py.
        """
        self.provider = config.AI_PROVIDER
        self.gemini_key = config.GEMINI_API_KEY
        self.gemini_model = config.GEMINI_MODEL
        self.ollama_url = config.OLLAMA_API_URL
        self.ollama_model = config.OLLAMA_MODEL

    async def generate_battle(
        self,
        player_a_name: str,
        creation_a: str,
        player_b_name: str,
        creation_b: str,
        theme: Dict[str, str] = None
    ) -> Tuple[str, str, str, str, str]:
        """
        Generates a battle between two creations.
        Returns a tuple: (creation_a_desc, creation_b_desc, fight_narrative, winner_code ['A' or 'B'], reason)
        """
        # Prepare theme prompt
        if theme:
            theme_str = f"Battle Setting/Theme: {theme['name']} - {theme['description']}\n(The battle must be set in this theme and follow its style/rules!)\n"
        else:
            theme_str = "Battle Setting: A standard neutral combat arena.\n"

        system_prompt = (
            "You are the Ultimate Arena Master and Judge of the Clash of Creations.\n"
            "Two creations submitted by players are going to battle. Your job is to analyze them, describe a quick fight, and pick the winner.\n"
            "You must return a JSON response containing:\n"
            "1. A funny, roast-style one-liner or short satirical sentence describing Creation A.\n"
            "2. A funny, roast-style one-liner or short satirical sentence describing Creation B.\n"
            "3. A 1-to-2 sentence fast-paced, funny description of the fight itself.\n"
            "4. The winner code ('A' or 'B') and the winning reason.\n\n"
            "You MUST respond ONLY with a JSON object matching this schema:\n"
            "{\n"
            '  "creation_a_desc": "A funny, roast-style one-liner or short satirical sentence describing Creation A",\n'
            '  "creation_b_desc": "A funny, roast-style one-liner or short satirical sentence describing Creation B",\n'
            '  "fight_narrative": "A quick, action-packed description of the clash (strictly 1 to 2 sentences)",\n'
            '  "winner": "A" or "B",\n'
            '  "reason": "One sentence summary explaining why they won"\n'
            "}\n"
            "Do not include any markdown formatting (like ```json) outside of the JSON block if possible, or if you do, ensure it is standard JSON inside."
        )

        user_prompt = (
            f"{theme_str}\n"
            f"Creation A: \"{creation_a}\" (controlled by {player_a_name})\n"
            f"Creation B: \"{creation_b}\" (controlled by {player_b_name})\n\n"
            f"Let the clash begin!"
        )

        try:
            raw_response = await self._post_to_ai(system_prompt, user_prompt)
            return self._parse_battle_json(raw_response)
        except Exception as e:
            return (
                f"A weird creation of spatial magic.",
                f"An opposing temporal anomaly.",
                f"The battle was interrupted by a spatial anomaly: {str(e)}",
                "A",
                "Anomaly resolved."
            )

    async def check_theme_fit(self, creation: str, theme: Dict[str, str]) -> Tuple[bool, str]:
        """
        Validates if a creation description fits within the chosen theme.
        Returns a tuple: (fits [True or False], reason [str])
        """
        if not theme:
            return True, "No theme is currently active."

        system_prompt = (
            "You are the Arena Theme Compliance Officer. Your job is to verify if a player's submitted creation fits the constraints of the battle theme.\n"
            "Analyze if the submission complies with or fits into the theme/rules.\n"
            "Be reasonably lenient and creative, but reject things that completely ignore the theme or violate explicit constraints. "
            "For example, if the theme is 'Kitchen Counter Brawl', a 'giant laser dinosaur' should be rejected (it's not kitchen related), but a 'laser-guided toaster' or 'sentient chef knife' is fine. "
            "If the theme is 'Deep Ocean Trench', it must make sense under water (e.g., standard fire-based creations fail unless protected by a bubble/shell, etc.).\n\n"
            "You MUST respond ONLY with a JSON object matching this schema:\n"
            "{\n"
            '  "fits": true or false,\n'
            '  "reason": "If fits is false, explain why it was rejected. If true, explain briefly how it fits."\n'
            "}"
        )

        user_prompt = (
            f"Theme: {theme['name']}\n"
            f"Description/Rules: {theme['description']}\n\n"
            f"Player's Submission: \"{creation}\"\n\n"
            f"Does this submission fit the theme? Answer in the exact JSON format requested."
        )

        try:
            raw_response = await self._post_to_ai(system_prompt, user_prompt)
            return self._parse_theme_json(raw_response)
        except Exception as e:
            # If AI validation fails, we default to allowing it to not disrupt the game
            return True, f"Validation system error (allowing by default): {str(e)}"

    async def generate_themed_creation(self, theme: Dict[str, str] = None) -> str:
        """
        Generates a themed creation for the bot to use in training mode.
        
        Args:
            theme (Dict[str, str]): The current theme dictionary.
            
        Returns:
            str: A short description of a generated themed creation.
        """
        if theme:
            theme_str = f"Theme: {theme['name']} - {theme['description']}"
        else:
            theme_str = "Theme: A standard neutral combat arena."

        system_prompt = (
            "You are the Ultimate Arena Master.\n"
            "Generate a creative, funny, and interesting combatant/creation that fits the given theme.\n"
            "The creation must be described in a single short phrase or sentence (maximum 15 words).\n"
            "Example: For 'Cyberpunk Neon Grid', you might output: 'A cybernetic alley cat with hacking implants'.\n"
            "Respond ONLY with the creation description, no quotes, no markdown, and no extra text."
        )

        user_prompt = f"Please generate a creation for this theme:\n{theme_str}"

        try:
            raw_response = await self._post_to_ai(system_prompt, user_prompt)
            return raw_response.strip().strip('"').strip("'")
        except Exception as e:
            # Fallback creation if AI fails
            return "A rusty training dummy with a wooden sword."

    async def _post_to_ai(self, system_prompt: str, user_prompt: str) -> str:
        """Dispatches the prompt to the configured AI provider and returns the raw response string."""
        if self.provider == "gemini":
            return await self._call_gemini_api(system_prompt, user_prompt)
        elif self.provider == "ollama":
            return await self._call_ollama_api(system_prompt, user_prompt)
        else:
            raise ValueError(f"Unknown AI Provider: '{self.provider}'")

    async def _call_gemini_api(self, system_prompt: str, user_prompt: str) -> str:
        """
        Calls the Gemini API asynchronously using aiohttp.
        
        Args:
            system_prompt (str): The instructions for the model's behavior.
            user_prompt (str): The prompt containing the specific request.
            
        Returns:
            str: The raw text response from the Gemini model.
        """
        if not self.gemini_key:
            raise ValueError("GEMINI_API_KEY is not configured in the .env file.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_key}"
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "contents": [{
                "parts": [{"text": user_prompt}]
            }],
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": 0.8,
                "responseMimeType": "application/json"
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    text = await response.text()
                    raise Exception(f"Gemini API returned status {response.status}: {text}")
                
                data = await response.json()
                try:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError):
                    raise Exception(f"Malformed Gemini API response structure. Raw: {data}")

    async def _call_ollama_api(self, system_prompt: str, user_prompt: str) -> str:
        """
        Calls the Ollama API asynchronously using aiohttp.
        
        Args:
            system_prompt (str): The system prompt detailing constraints and schema.
            user_prompt (str): The user prompt describing the matchup or theme.
            
        Returns:
            str: The raw text response from the Ollama model.
        """
        url = f"{self.ollama_url}/api/chat"
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "model": self.ollama_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.8
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    text = await response.text()
                    raise Exception(f"Ollama API returned status {response.status}: {text}")
                
                data = await response.json()
                return data["message"]["content"]

    def _parse_battle_json(self, raw_text: str) -> Tuple[str, str, str, str, str]:
        """Parses the JSON response from the LLM, extracting descriptions, narrative, winner, and reason."""
        try:
            cleaned = self._clean_json_markdown(raw_text)
            parsed = json.loads(cleaned)
            
            creation_a_desc = parsed.get("creation_a_desc", "A funny challenger.")
            creation_b_desc = parsed.get("creation_b_desc", "An interesting opponent.")
            fight_narrative = parsed.get("fight_narrative", "They clashed, and one emerged victorious.")
            
            winner_raw = parsed.get("winner", "A").upper().strip()
            # Ensure winner is A or B
            winner = "A" if "A" in winner_raw else "B"
            reason = parsed.get("reason", "No reason provided by the judge.")
            
            return creation_a_desc, creation_b_desc, fight_narrative, winner, reason
        except Exception:
            # Fallback regex search if JSON is malformed
            c_a_match = re.search(r'"creation_a_desc"\s*:\s*"([^"]+)"', raw_text)
            c_b_match = re.search(r'"creation_b_desc"\s*:\s*"([^"]+)"', raw_text)
            fight_match = re.search(r'"fight_narrative"\s*:\s*"([^"]+)"', raw_text)
            winner_match = re.search(r'"winner"\s*:\s*"([^"]+)"', raw_text)
            reason_match = re.search(r'"reason"\s*:\s*"([^"]+)"', raw_text)
            
            creation_a_desc = c_a_match.group(1) if c_a_match else "The first creation."
            creation_b_desc = c_b_match.group(1) if c_b_match else "The second creation."
            fight_narrative = fight_match.group(1) if fight_match else "The battle was chaotic."
            winner_val = winner_match.group(1).upper() if winner_match else "A"
            winner = "A" if "A" in winner_val else "B"
            reason = reason_match.group(1) if reason_match else "AI did not return structured JSON."
            
            return creation_a_desc, creation_b_desc, fight_narrative, winner, reason

    def _parse_theme_json(self, raw_text: str) -> Tuple[bool, str]:
        """Parses the JSON response from the LLM, extracting fits and reason."""
        try:
            cleaned = self._clean_json_markdown(raw_text)
            parsed = json.loads(cleaned)
            fits = bool(parsed.get("fits", True))
            reason = parsed.get("reason", "Approved.")
            return fits, reason
        except Exception as e:
            return True, f"Approved by default (parsing error: {str(e)})."

    def _clean_json_markdown(self, raw_text: str) -> str:
        """
        Removes code blocks (```json ... ```) wrapping the JSON output.
        
        Args:
            raw_text (str): The raw response string from the AI model.
            
        Returns:
            str: The cleaned string containing only the JSON structure.
        """
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\n", "", cleaned)
            cleaned = re.sub(r"\n```$", "", cleaned)
        return cleaned.strip()
