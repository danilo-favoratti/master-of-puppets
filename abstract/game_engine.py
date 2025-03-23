"""
Game Engine - loads games from JSON files and provides a simple API
"""

import json
import random
from typing import Dict, List, Tuple, Any, Optional

class GameEngine:
    """A simple game engine that can load games from JSON files"""
    
    def __init__(self, json_file_path=None):
        """Initialize the game engine, optionally loading from a JSON file"""
        self.width = 0
        self.height = 0
        self.board = []
        self.entities = {}  # Maps entity IDs to their data
        self.entity_positions = {}  # Maps positions (x,y) to entity IDs
        self.player = None  # Reference to player entity
        
        if json_file_path:
            self.load_game(json_file_path)
    
    def load_game(self, json_file_path: str) -> bool:
        """Load a game from a JSON file"""
        try:
            with open(json_file_path, 'r') as f:
                game_data = json.load(f)
            
            # Extract board dimensions
            self.width = game_data["board"]["width"]
            self.height = game_data["board"]["height"]
            
            # Create empty board
            self.board = [[None for _ in range(self.width)] for _ in range(self.height)]
            
            # Reset entity tracking
            self.entities = {}
            self.entity_positions = {}
            
            # Process entities
            for entity in game_data["entities"]:
                # Store entity data
                entity_id = entity["id"]
                self.entities[entity_id] = entity
                
                # Update board and position tracking
                x = entity["position"]["x"]
                y = entity["position"]["y"]
                self.board[y][x] = entity["type"]
                self.entity_positions[(x, y)] = entity_id
                
                # Track player specifically
                if entity["type"] == "player":
                    self.player = entity
            
            return True
            
        except Exception as e:
            print(f"Error loading game: {e}")
            return False
    
    def save_game(self, json_file_path: str) -> bool:
        """Save the current game state to a JSON file"""
        try:
            game_data = {
                "board": {
                    "width": self.width,
                    "height": self.height,
                    "squares": [
                        {
                            "position": {"x": x, "y": y},
                            "contains_entity": self.board[y][x] is not None
                        }
                        for y in range(self.height)
                        for x in range(self.width)
                    ]
                },
                "entities": list(self.entities.values())
            }
            
            with open(json_file_path, 'w') as f:
                json.dump(game_data, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Error saving game: {e}")
            return False
    
    def print_board(self) -> None:
        """Print the current state of the board"""
        for row in self.board:
            row_str = ""
            for cell in row:
                if cell is None:
                    row_str += "[          ]"
                else:
                    row_str += f"[{cell:<10}]"
            print(row_str)
    
    def get_entity_at(self, x: int, y: int) -> Optional[Dict[str, Any]]:
        """Get the entity at the specified position"""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return None
            
        entity_id = self.entity_positions.get((x, y))
        if entity_id:
            return self.entities[entity_id]
        
        return None
    
    def move_entity(self, entity_id: str, new_x: int, new_y: int) -> bool:
        """Move an entity to a new position"""
        # Check if entity exists
        if entity_id not in self.entities:
            return False
            
        # Check if target position is valid
        if not (0 <= new_x < self.width and 0 <= new_y < self.height):
            return False
            
        # Check if target position is occupied
        if (new_x, new_y) in self.entity_positions:
            return False
            
        # Get current position
        entity = self.entities[entity_id]
        old_x = entity["position"]["x"]
        old_y = entity["position"]["y"]
        
        # Update entity position
        entity["position"]["x"] = new_x
        entity["position"]["y"] = new_y
        
        # Update board and position tracking
        self.board[old_y][old_x] = None
        self.board[new_y][new_x] = entity["type"]
        del self.entity_positions[(old_x, old_y)]
        self.entity_positions[(new_x, new_y)] = entity_id
        
        return True
    
    def player_move(self, direction: str) -> Dict[str, Any]:
        """Move the player in the specified direction (up, down, left, right)"""
        if not self.player:
            return {"success": False, "message": "No player in the game"}
            
        current_x = self.player["position"]["x"]
        current_y = self.player["position"]["y"]
        
        # Calculate new position based on direction
        new_x, new_y = current_x, current_y
        if direction == "up":
            new_y -= 1
        elif direction == "down":
            new_y += 1
        elif direction == "left":
            new_x -= 1
        elif direction == "right":
            new_x += 1
        else:
            return {"success": False, "message": "Invalid direction"}
        
        # Try to move player
        if self.move_entity(self.player["id"], new_x, new_y):
            return {"success": True, "message": f"Player moved {direction}"}
        else:
            return {"success": False, "message": "Cannot move in that direction"}
    
    def interact_with(self, x: int, y: int) -> Dict[str, Any]:
        """Interact with an entity at the specified position"""
        entity = self.get_entity_at(x, y)
        if not entity:
            return {"success": False, "message": "No entity at that position"}
            
        # Check if player is adjacent
        if not self.player:
            return {"success": False, "message": "No player in the game"}
            
        player_x = self.player["position"]["x"]
        player_y = self.player["position"]["y"]
        
        # Check adjacency (including diagonals)
        is_adjacent = abs(player_x - x) <= 1 and abs(player_y - y) <= 1
        if not is_adjacent:
            return {"success": False, "message": "Entity is not adjacent to player"}
        
        # Handle different types of interactions
        entity_type = entity["type"]
        
        if entity_type == "door":
            if entity.get("is_locked", False):
                # Check if player has the key
                key_id = entity.get("key_id")
                if not key_id:
                    return {"success": False, "message": "Door is locked but has no key defined"}
                    
                # Check player inventory for key
                has_key = False
                for item_id in self.player.get("inventory", []):
                    if item_id == key_id:
                        has_key = True
                        break
                        
                if has_key:
                    entity["is_locked"] = False
                    return {"success": True, "message": "Door unlocked with key"}
                else:
                    return {"success": False, "message": "Door is locked, you need a key"}
            else:
                return {"success": True, "message": "Door is unlocked"}
                
        elif entity_type in ["container", "chest", "backpack"]:
            if entity.get("is_open", True):
                contents = entity.get("contents", [])
                if contents:
                    content_names = [self.entities[item_id]["name"] for item_id in contents if item_id in self.entities]
                    return {"success": True, "message": f"Contains: {', '.join(content_names)}", "contents": contents}
                else:
                    return {"success": True, "message": "Container is empty"}
            else:
                return {"success": False, "message": "Container is closed"}
                
        elif entity_type == "key":
            # Add key to player inventory
            if "inventory" not in self.player:
                self.player["inventory"] = []
                
            self.player["inventory"].append(entity["id"])
            
            # Remove key from board
            old_x = entity["position"]["x"]
            old_y = entity["position"]["y"]
            self.board[old_y][old_x] = None
            del self.entity_positions[(old_x, old_y)]
            
            return {"success": True, "message": f"Picked up {entity['name']}"}
            
        else:
            return {"success": True, "message": f"You see: {entity['description'] if 'description' in entity else entity['name']}"}
    
    def get_game_state(self) -> Dict[str, Any]:
        """Get the current game state as a dictionary"""
        return {
            "board": {
                "width": self.width,
                "height": self.height
            },
            "player": self.player,
            "entities_count": len(self.entities)
        }

    def print_entity_details(self) -> None:
        """Print details about entities in the game"""
        print("\nEntities:")
        for entity_id, entity in self.entities.items():
            print(f"- {entity['name']} ({entity_id})")
            if entity.get("position"):
                print(f"  Position: ({entity['position']['x']}, {entity['position']['y']})")
            if entity.get("is_movable"):
                print(f"  Movable: {entity['is_movable']}")
            if entity.get("type") in ["container", "chest", "backpack"]:
                print(f"  Capacity: {entity.get('capacity', 'unlimited')}")
                print(f"  Contents: {len(entity.get('contents', []))} items")

# Example usage
if __name__ == "__main__":
    import os
    
    # List of example files to try
    example_files = ["small_game.json", "medium_game.json", "large_game.json"]
    
    # Try to load each file
    for filename in example_files:
        if os.path.exists(filename):
            print(f"\nLoading game from {filename}...")
            engine = GameEngine(filename)
            
            # Print the board
            print("\nGame Board:")
            engine.print_board()
            
            # Show game state
            state = engine.get_game_state()
            print("\nGame State:")
            print(f"Board dimensions: {state['board']['width']}x{state['board']['height']}")
            print(f"Total entities: {state['entities_count']}")
            
            if state['player']:
                print(f"Player position: ({state['player']['position']['x']}, {state['player']['position']['y']})")
                
            # Try moving the player
            if state['player']:
                directions = ["up", "right", "down", "left"]
                for direction in directions:
                    result = engine.player_move(direction)
                    print(f"\nMoving player {direction}: {result['message']}")
                    if result['success']:
                        break
                
            # Show updated board
            print("\nUpdated Game Board:")
            engine.print_board()
            
            break
    else:
        print("No example game files found. Run simple_test.py first to generate them.") 