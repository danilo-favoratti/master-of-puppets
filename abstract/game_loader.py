"""
Game Loader - Utility for loading and displaying games from JSON files
"""

import json
import os
from typing import Dict, List, Any, Optional, Tuple

class GameLoader:
    """Utility class to load and parse game data from JSON files"""
    
    @staticmethod
    def load_game(file_path: str) -> Dict[str, Any]:
        """Load a game from a JSON file"""
        try:
            with open(file_path, 'r') as f:
                game_data = json.load(f)
            return game_data
        except Exception as e:
            print(f"Error loading game: {e}")
            return {}
    
    @staticmethod
    def print_board(game_data: Dict[str, Any]) -> None:
        """Print a visualization of the board from game data"""
        if not game_data or "board" not in game_data or "entities" not in game_data:
            print("Invalid game data")
            return
        
        width = game_data["board"]["width"]
        height = game_data["board"]["height"]
        
        # Create an empty board
        board = [[None for _ in range(width)] for _ in range(height)]
        
        # Place entities on the board
        for entity in game_data["entities"]:
            if entity.get("position"):
                x = entity["position"]["x"]
                y = entity["position"]["y"]
                # Prioritize certain entity types
                if entity["type"] == "player":
                    board[y][x] = "player"
                elif board[y][x] is None or entity["type"] in ["door", "container", "chest"]:
                    board[y][x] = entity["type"]
        
        # Print the board
        print(f"Board ({width}x{height}):")
        for row in board:
            row_str = ""
            for cell in row:
                if cell is None:
                    row_str += "[          ]"
                else:
                    row_str += f"[{cell:<10}]"
            print(row_str)
    
    @staticmethod
    def get_entity_counts(game_data: Dict[str, Any]) -> Dict[str, int]:
        """Count entities by type"""
        if not game_data or "entities" not in game_data:
            return {}
        
        counts = {}
        for entity in game_data["entities"]:
            entity_type = entity["type"]
            counts[entity_type] = counts.get(entity_type, 0) + 1
        
        return counts
    
    @staticmethod
    def get_contained_items(game_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Get a mapping of container IDs to the items they contain"""
        if not game_data or "entities" not in game_data:
            return {}
        
        containers = {}
        entities_by_id = {entity["id"]: entity for entity in game_data["entities"]}
        
        for entity in game_data["entities"]:
            if entity["type"] in ["container", "chest", "backpack"] and "contents" in entity:
                container_id = entity["id"]
                item_names = []
                
                for item_id in entity["contents"]:
                    if item_id in entities_by_id:
                        item_names.append(entities_by_id[item_id]["name"])
                    else:
                        item_names.append(f"Unknown item: {item_id}")
                
                containers[container_id] = {
                    "name": entity["name"],
                    "items": item_names
                }
        
        return containers
    
    @staticmethod
    def find_key_door_pairs(game_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find all key-door pairs in the game"""
        if not game_data or "entities" not in game_data:
            return []
        
        keys = {}
        doors = {}
        
        # First, collect all keys and doors
        for entity in game_data["entities"]:
            if entity["type"] == "key":
                keys[entity["id"]] = entity
            elif entity["type"] == "door" and "key_id" in entity:
                doors[entity["id"]] = entity
        
        # Then find matching pairs
        pairs = []
        for door_id, door in doors.items():
            key_id = door.get("key_id")
            if key_id in keys:
                pairs.append({
                    "door": door["name"],
                    "door_id": door_id,
                    "key": keys[key_id]["name"],
                    "key_id": key_id
                })
        
        return pairs
    
    @staticmethod
    def get_player_info(game_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about the player"""
        if not game_data or "entities" not in game_data:
            return {}
        
        for entity in game_data["entities"]:
            if entity["type"] == "player":
                player_info = {
                    "name": entity["name"],
                    "position": entity["position"],
                    "inventory": [],
                    "strength": entity.get("strength", 0),
                    "abilities": entity.get("can_perform", [])
                }
                
                # Get inventory items
                entities_by_id = {e["id"]: e for e in game_data["entities"]}
                for item_id in entity.get("inventory", []):
                    if item_id in entities_by_id:
                        player_info["inventory"].append(entities_by_id[item_id]["name"])
                    else:
                        player_info["inventory"].append(f"Unknown item: {item_id}")
                
                return player_info
        
        return {}

def main():
    """Load and display example game files"""
    # Try each of our example files
    for filename in ["small_game_example.json", "medium_game_example.json", "large_game_example.json"]:
        if os.path.exists(filename):
            print(f"\n=== Loading {filename} ===")
            game_data = GameLoader.load_game(filename)
            
            if not game_data:
                print(f"Failed to load {filename}")
                continue
            
            # Print the board
            GameLoader.print_board(game_data)
            
            # Print entity counts
            entity_counts = GameLoader.get_entity_counts(game_data)
            print("\nEntity counts:")
            for entity_type, count in entity_counts.items():
                print(f"  {entity_type}: {count}")
            
            # Print player info
            player_info = GameLoader.get_player_info(game_data)
            if player_info:
                print("\nPlayer information:")
                print(f"  Name: {player_info['name']}")
                print(f"  Position: ({player_info['position']['x']}, {player_info['position']['y']})")
                print(f"  Strength: {player_info['strength']}")
                print(f"  Abilities: {', '.join(player_info['abilities'])}")
                print(f"  Inventory: {', '.join(player_info['inventory'])}")
            
            # Print container contents
            containers = GameLoader.get_contained_items(game_data)
            if containers:
                print("\nContainer contents:")
                for container_id, info in containers.items():
                    print(f"  {info['name']} contains: {', '.join(info['items'])}")
            
            # Print key-door pairs
            key_door_pairs = GameLoader.find_key_door_pairs(game_data)
            if key_door_pairs:
                print("\nKey-door pairs:")
                for pair in key_door_pairs:
                    print(f"  {pair['key']} unlocks {pair['door']}")
            
            print("\n" + "="*50)

if __name__ == "__main__":
    main() 