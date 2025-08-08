from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from datetime import datetime, timedelta
import os
import uuid
from typing import Optional
import math
import time

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/')
client = MongoClient(MONGO_URL)
db = client.clicker_game

# Character levels configuration
CHARACTER_LEVELS = {
    1: {"name": "Junior", "multiplier": 1, "max_energy": 100, "advancement_cost": 5000},
    2: {"name": "Deishi", "multiplier": 2, "max_energy": 150, "advancement_cost": 5000000},
    3: {"name": "Shugo", "multiplier": 3, "max_energy": 200, "advancement_cost": 500000000},
    4: {"name": "Seishi", "multiplier": 5, "max_energy": 250, "advancement_cost": 50000000000},
    5: {"name": "Shihan", "multiplier": 8, "max_energy": 300, "advancement_cost": None}  # Max level
}

# Pydantic models
class PlayerCreate(BaseModel):
    player_id: str

class ClickAction(BaseModel):
    player_id: str

class UpgradePurchase(BaseModel):
    player_id: str
    upgrade_level: int

class CharacterAdvancement(BaseModel):
    player_id: str

def format_number(num):
    """Format numbers with K, M, B, T suffixes"""
    if num < 1000:
        return str(int(num))
    elif num < 1000000:
        return f"{num/1000:.1f}K"
    elif num < 1000000000:
        return f"{num/1000000:.1f}M"
    elif num < 1000000000000:
        return f"{num/1000000000:.1f}B"
    else:
        return f"{num/1000000000000:.1f}T"

def get_upgrade_cost(level):
    """Calculate upgrade cost: 100 → 2,500 → 25,000... (10x multiplier progression)"""
    if level == 0:
        return 100
    return int(100 * (2.5 ** level))

def calculate_points_per_click(upgrade_level):
    """Calculate points per click based on upgrade level (10% rule)"""
    if upgrade_level == 0:
        return 1
    
    total_points = 0
    for i in range(upgrade_level):
        cost = get_upgrade_cost(i)
        total_points += cost * 0.1  # 10% of cost becomes points per click
    return total_points

def get_or_create_player(player_id: str):
    """Get existing player or create new one"""
    player = db.players.find_one({"player_id": player_id})
    if not player:
        player = {
            "player_id": player_id,
            "points": 0,
            "energy": 100,  # Start with full energy
            "character_level": 1,
            "upgrade_level": 0,
            "last_energy_update": datetime.utcnow(),
            "last_passive_income": datetime.utcnow()
        }
        db.players.insert_one(player)
    return player

def update_energy(player):
    """Update energy based on time elapsed"""
    now = datetime.utcnow()
    last_update = player.get("last_energy_update", now)
    
    # Energy regenerates at 1 per 10 seconds
    time_diff = (now - last_update).total_seconds()
    energy_to_add = int(time_diff / 10)  # 1 energy per 10 seconds
    
    if energy_to_add > 0:
        character_config = CHARACTER_LEVELS[player["character_level"]]
        max_energy = character_config["max_energy"]
        
        new_energy = min(player["energy"] + energy_to_add, max_energy)
        db.players.update_one(
            {"player_id": player["player_id"]},
            {
                "$set": {
                    "energy": new_energy,
                    "last_energy_update": now
                }
            }
        )
        player["energy"] = new_energy
        player["last_energy_update"] = now
    
    return player

def update_passive_income(player):
    """Update passive income (1 click per minute)"""
    now = datetime.utcnow()
    last_passive = player.get("last_passive_income", now)
    
    # Calculate minutes elapsed
    minutes_elapsed = (now - last_passive).total_seconds() / 60
    passive_clicks = int(minutes_elapsed)
    
    if passive_clicks > 0:
        character_config = CHARACTER_LEVELS[player["character_level"]]
        base_points = calculate_points_per_click(player["upgrade_level"])
        passive_points = passive_clicks * base_points * character_config["multiplier"]
        
        new_points = player["points"] + passive_points
        
        db.players.update_one(
            {"player_id": player["player_id"]},
            {
                "$set": {
                    "points": new_points,
                    "last_passive_income": now
                }
            }
        )
        player["points"] = new_points
        player["last_passive_income"] = now
    
    return player

@app.get("/api/player/{player_id}")
async def get_player(player_id: str):
    """Get player data with updated energy and passive income"""
    try:
        player = get_or_create_player(player_id)
        player = update_energy(player)
        player = update_passive_income(player)
        
        character_config = CHARACTER_LEVELS[player["character_level"]]
        
        # Calculate next upgrade cost
        next_upgrade_cost = get_upgrade_cost(player["upgrade_level"])
        points_per_click = calculate_points_per_click(player["upgrade_level"])
        
        # Calculate energy regeneration time
        energy_regen_seconds = (character_config["max_energy"] - player["energy"]) * 10
        
        # Get last save info
        last_save = player.get("last_save", player.get("last_energy_update", datetime.utcnow()))
        
        return {
            "player_id": player["player_id"],
            "points": player["points"],
            "points_formatted": format_number(player["points"]),
            "energy": player["energy"],
            "max_energy": character_config["max_energy"],
            "character_level": player["character_level"],
            "character_name": character_config["name"],
            "character_multiplier": character_config["multiplier"],
            "upgrade_level": player["upgrade_level"],
            "points_per_click": points_per_click * character_config["multiplier"],
            "next_upgrade_cost": next_upgrade_cost,
            "next_upgrade_cost_formatted": format_number(next_upgrade_cost),
            "advancement_cost": character_config.get("advancement_cost"),
            "advancement_cost_formatted": format_number(character_config.get("advancement_cost", 0)) if character_config.get("advancement_cost") else None,
            "can_advance": player["character_level"] < 5 and player["points"] >= character_config.get("advancement_cost", float('inf')),
            "energy_regen_seconds": energy_regen_seconds,
            "last_save": last_save.isoformat(),
            "last_save_formatted": last_save.strftime("%Y-%m-%d %H:%M:%S UTC")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/click")
async def click(action: ClickAction):
    """Handle player click"""
    try:
        player = get_or_create_player(action.player_id)
        player = update_energy(player)
        player = update_passive_income(player)
        
        # Check if player has enough energy
        if player["energy"] < 2:
            raise HTTPException(status_code=400, detail="Not enough energy")
        
        # Calculate points earned
        character_config = CHARACTER_LEVELS[player["character_level"]]
        base_points = calculate_points_per_click(player["upgrade_level"])
        points_earned = base_points * character_config["multiplier"]
        
        # Update player
        new_points = player["points"] + points_earned
        new_energy = player["energy"] - 2
        
        db.players.update_one(
            {"player_id": action.player_id},
            {
                "$set": {
                    "points": new_points,
                    "energy": new_energy,
                    "last_save": datetime.utcnow()
                }
            }
        )
        
        return {
            "success": True,
            "points_earned": points_earned,
            "new_points": new_points,
            "new_points_formatted": format_number(new_points),
            "new_energy": new_energy
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upgrade")
async def purchase_upgrade(upgrade: UpgradePurchase):
    """Purchase upgrade"""
    try:
        player = get_or_create_player(upgrade.player_id)
        player = update_energy(player)
        player = update_passive_income(player)
        
        # Check if this is the next upgrade level
        if upgrade.upgrade_level != player["upgrade_level"]:
            raise HTTPException(status_code=400, detail="Invalid upgrade level")
        
        # Calculate cost
        cost = get_upgrade_cost(upgrade.upgrade_level)
        
        # Check if player has enough points
        if player["points"] < cost:
            raise HTTPException(status_code=400, detail="Not enough points")
        
        # Purchase upgrade
        new_points = player["points"] - cost
        new_upgrade_level = player["upgrade_level"] + 1
        
        db.players.update_one(
            {"player_id": upgrade.player_id},
            {
                "$set": {
                    "points": new_points,
                    "upgrade_level": new_upgrade_level,
                    "last_save": datetime.utcnow()
                }
            }
        )
        
        return {
            "success": True,
            "new_points": new_points,
            "new_points_formatted": format_number(new_points),
            "new_upgrade_level": new_upgrade_level,
            "new_points_per_click": calculate_points_per_click(new_upgrade_level) * CHARACTER_LEVELS[player["character_level"]]["multiplier"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/advance")
async def advance_character(advancement: CharacterAdvancement):
    """Advance character level (with reset)"""
    try:
        player = get_or_create_player(advancement.player_id)
        player = update_energy(player)
        player = update_passive_income(player)
        
        # Check if advancement is possible
        if player["character_level"] >= 5:
            raise HTTPException(status_code=400, detail="Already at maximum level")
        
        character_config = CHARACTER_LEVELS[player["character_level"]]
        advancement_cost = character_config.get("advancement_cost")
        
        if not advancement_cost or player["points"] < advancement_cost:
            raise HTTPException(status_code=400, detail="Not enough points for advancement")
        
        # Advance character and reset progress
        new_level = player["character_level"] + 1
        new_character_config = CHARACTER_LEVELS[new_level]
        
        db.players.update_one(
            {"player_id": advancement.player_id},
            {
                "$set": {
                    "character_level": new_level,
                    "points": 0,  # Reset points
                    "upgrade_level": 0,  # Reset upgrades
                    "energy": new_character_config["max_energy"],  # Full energy at new level
                    "last_energy_update": datetime.utcnow(),
                    "last_passive_income": datetime.utcnow(),
                    "last_save": datetime.utcnow()
                }
            }
        )
        
        return {
            "success": True,
            "new_character_level": new_level,
            "new_character_name": new_character_config["name"],
            "new_character_multiplier": new_character_config["multiplier"],
            "new_max_energy": new_character_config["max_energy"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/save")
async def manual_save(save_data: PlayerCreate):
    """Manual save - force update last_save timestamp"""
    try:
        player = get_or_create_player(save_data.player_id)
        player = update_energy(player)
        player = update_passive_income(player)
        
        # Update last_save timestamp
        now = datetime.utcnow()
        db.players.update_one(
            {"player_id": save_data.player_id},
            {
                "$set": {
                    "last_save": now
                }
            }
        )
        
        return {
            "success": True,
            "message": "Game saved successfully",
            "save_time": now.isoformat(),
            "save_time_formatted": now.strftime("%Y-%m-%d %H:%M:%S UTC")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/export/{player_id}")
async def export_save_data(player_id: str):
    """Export player save data"""
    try:
        player = get_or_create_player(player_id)
        player = update_energy(player)
        player = update_passive_income(player)
        
        # Create exportable save data
        save_data = {
            "player_id": player["player_id"],
            "points": player["points"],
            "energy": player["energy"],
            "character_level": player["character_level"],
            "upgrade_level": player["upgrade_level"],
            "last_energy_update": player["last_energy_update"].isoformat(),
            "last_passive_income": player["last_passive_income"].isoformat(),
            "last_save": player.get("last_save", datetime.utcnow()).isoformat(),
            "export_timestamp": datetime.utcnow().isoformat(),
            "game_version": "1.0"
        }
        
        return {
            "success": True,
            "save_data": save_data,
            "export_info": {
                "export_time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                "character_name": CHARACTER_LEVELS[player["character_level"]]["name"],
                "total_progress": f"{player['points']} points, Level {player['character_level']}"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ImportSaveData(BaseModel):
    player_id: str
    save_data: dict

@app.post("/api/import")
async def import_save_data(import_data: ImportSaveData):
    """Import player save data"""
    try:
        save_data = import_data.save_data
        
        # Validate save data structure
        required_fields = ['points', 'energy', 'character_level', 'upgrade_level']
        missing_fields = [field for field in required_fields if field not in save_data]
        
        if missing_fields:
            raise HTTPException(status_code=400, detail=f"Invalid save data: missing fields {missing_fields}")
        
        # Validate data ranges
        if save_data['character_level'] < 1 or save_data['character_level'] > 5:
            raise HTTPException(status_code=400, detail="Invalid character level")
        
        if save_data['energy'] < 0 or save_data['energy'] > CHARACTER_LEVELS[save_data['character_level']]['max_energy']:
            raise HTTPException(status_code=400, detail="Invalid energy value")
        
        if save_data['points'] < 0 or save_data['upgrade_level'] < 0:
            raise HTTPException(status_code=400, detail="Invalid points or upgrade level")
        
        # Parse timestamps
        now = datetime.utcnow()
        try:
            last_energy_update = datetime.fromisoformat(save_data.get('last_energy_update', now.isoformat()))
            last_passive_income = datetime.fromisoformat(save_data.get('last_passive_income', now.isoformat()))
        except:
            last_energy_update = now
            last_passive_income = now
        
        # Import the save data
        db.players.update_one(
            {"player_id": import_data.player_id},
            {
                "$set": {
                    "points": save_data['points'],
                    "energy": save_data['energy'],
                    "character_level": save_data['character_level'],
                    "upgrade_level": save_data['upgrade_level'],
                    "last_energy_update": last_energy_update,
                    "last_passive_income": last_passive_income,
                    "last_save": now
                }
            },
            upsert=True
        )
        
        return {
            "success": True,
            "message": "Save data imported successfully",
            "imported_data": {
                "points": save_data['points'],
                "character_level": save_data['character_level'],
                "character_name": CHARACTER_LEVELS[save_data['character_level']]["name"],
                "upgrade_level": save_data['upgrade_level']
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)