import sqlite3
import asyncio
from pathlib import Path

DB_PATH = Path(__file__).parent / "clash_of_wits.db"

def _init_db_sync():
    """Initializes the database schema synchronously."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Players table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                duels_played INTEGER DEFAULT 0,
                duels_won INTEGER DEFAULT 0,
                br_played INTEGER DEFAULT 0,
                br_won INTEGER DEFAULT 0,
                creations_submitted INTEGER DEFAULT 0
            )
        """)
        
        # Match history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS match_history (
                match_id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_type TEXT NOT NULL, -- 'duel' or 'br'
                player_a_id INTEGER NOT NULL,
                player_b_id INTEGER NOT NULL,
                creation_a TEXT NOT NULL,
                creation_b TEXT NOT NULL,
                winner_id INTEGER NOT NULL,
                narrative TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

async def init_db():
    """Initializes the database schema asynchronously."""
    await asyncio.to_thread(_init_db_sync)

def _update_player_stats_sync(user_id: int, username: str, duel_win: bool = None, br_win: bool = None, submitted: bool = False):
    """Updates a player's stats synchronously."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Ensure player exists
        cursor.execute(
            "INSERT OR IGNORE INTO players (user_id, username) VALUES (?, ?)",
            (user_id, username)
        )
        # Always update username in case it changed
        cursor.execute(
            "UPDATE players SET username = ? WHERE user_id = ?",
            (username, user_id)
        )
        
        if submitted:
            cursor.execute(
                "UPDATE players SET creations_submitted = creations_submitted + 1 WHERE user_id = ?",
                (user_id,)
            )
            
        if duel_win is not None:
            if duel_win:
                cursor.execute(
                    "UPDATE players SET duels_played = duels_played + 1, duels_won = duels_won + 1 WHERE user_id = ?",
                    (user_id,)
                )
            else:
                cursor.execute(
                    "UPDATE players SET duels_played = duels_played + 1 WHERE user_id = ?",
                    (user_id,)
                )
                
        if br_win is not None:
            if br_win:
                cursor.execute(
                    "UPDATE players SET br_played = br_played + 1, br_won = br_won + 1 WHERE user_id = ?",
                    (user_id,)
                )
            else:
                cursor.execute(
                    "UPDATE players SET br_played = br_played + 1 WHERE user_id = ?",
                    (user_id,)
                )
        conn.commit()

async def update_player_stats(user_id: int, username: str, duel_win: bool = None, br_win: bool = None, submitted: bool = False):
    """Updates a player's stats asynchronously."""
    await asyncio.to_thread(_update_player_stats_sync, user_id, username, duel_win, br_win, submitted)

def _get_player_stats_sync(user_id: int) -> dict:
    """Gets a player's stats synchronously."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

async def get_player_stats(user_id: int) -> dict:
    """Gets a player's stats asynchronously."""
    return await asyncio.to_thread(_get_player_stats_sync, user_id)

def _get_leaderboard_sync(limit: int) -> list:
    """Gets the leaderboard synchronously, sorted by total wins (duels + br)."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, username, duels_won, br_won, (duels_won + br_won) as total_wins
            FROM players
            ORDER BY total_wins DESC, username ASC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

async def get_leaderboard(limit: int = 10) -> list:
    """Gets the leaderboard asynchronously."""
    return await asyncio.to_thread(_get_leaderboard_sync, limit)

def _log_match_sync(match_type: str, player_a_id: int, player_b_id: int, creation_a: str, creation_b: str, winner_id: int, narrative: str):
    """Logs a match to database synchronously."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO match_history (match_type, player_a_id, player_b_id, creation_a, creation_b, winner_id, narrative)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (match_type, player_a_id, player_b_id, creation_a, creation_b, winner_id, narrative))
        conn.commit()

async def log_match(match_type: str, player_a_id: int, player_b_id: int, creation_a: str, creation_b: str, winner_id: int, narrative: str):
    """Logs a match to database asynchronously."""
    await asyncio.to_thread(_log_match_sync, match_type, player_a_id, player_b_id, creation_a, creation_b, winner_id, narrative)
