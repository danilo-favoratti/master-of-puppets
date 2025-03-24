import uuid
from typing import Dict, List, Any

from .board import Board
from .entity import Entity, Position
from .factory_game import WeatherSystem, WeatherFactory, WeatherType, WeatherParameters
from .game_object import GameObject, Container
from .person import Person


class Game:
    """Main game class that manages the game state and logic."""
    
    def __init__(self, width: int = 10, height: int = 10):
        """Initialize a new game with a board of the specified dimensions."""
        self.board = Board(width, height)
        self.player = None  # The main player character
        self.turn_count = 0
        self.messages = []  # Game messages/feedback
        self.weather_system = WeatherSystem()  # Initialize the weather system
    
    def create_player(self, name: str, position: Position) -> Person:
        """Create and add a player character to the game."""
        player_id = f"player_{uuid.uuid4().hex[:8]}"
        self.player = Person(id=player_id, name=name)
        
        # Add player to the board
        self.board.add_entity(self.player, position)
        
        return self.player
    
    def create_object(self, obj_type: str, name: str, position: Position, **properties) -> GameObject:
        """Create and add a game object to the board."""
        obj_id = f"{obj_type}_{uuid.uuid4().hex[:8]}"
        
        # Create container or regular object
        if obj_type == "container":
            game_obj = Container(id=obj_id, name=name, **properties)
        else:
            game_obj = GameObject(id=obj_id, name=name, **properties)
            
        # Add object to the board
        self.board.add_entity(game_obj, position)
        
        return game_obj
    
    def log_message(self, message: str) -> None:
        """Add a message to the game log."""
        self.messages.append(message)
        
    def get_latest_messages(self, count: int = 5) -> List[str]:
        """Get the most recent game messages."""
        return self.messages[-count:] if self.messages else []
    
    def perform_action(self, action: str, **params) -> Dict[str, Any]:
        """Perform a player action based on the action type and parameters."""
        if not self.player:
            return {"success": False, "message": "No player character exists"}
            
        result = {"success": False, "message": "Unknown action"}
        
        # Movement actions
        if action == "walk":
            target_position = params.get("position")
            if target_position:
                result = self.player.move(self.board, target_position, is_running=False)
                
        elif action == "run":
            target_position = params.get("position")
            if target_position:
                result = self.player.move(self.board, target_position, is_running=True)
                
        elif action == "jump":
            target_position = params.get("position")
            if target_position:
                result = self.player.jump(self.board, target_position)
                
        # Object interaction actions
        elif action == "push":
            object_position = params.get("object_position")
            direction = params.get("direction")
            if object_position and direction:
                result = self.player.push(self.board, object_position, direction)
                
        elif action == "pull":
            object_position = params.get("object_position")
            if object_position:
                result = self.player.pull(self.board, object_position)
                
        elif action == "get":
            container_id = params.get("container_id")
            item_id = params.get("item_id")
            if container_id and item_id:
                container = self.board.get_entity(container_id)
                if container and isinstance(container, Container):
                    result = self.player.get_from_container(container, item_id)
                else:
                    result = {"success": False, "message": "Container not found"}
                    
        elif action == "put":
            container_id = params.get("container_id")
            item_id = params.get("item_id")
            if container_id and item_id:
                container = self.board.get_entity(container_id)
                if container and isinstance(container, Container):
                    result = self.player.put_in_container(item_id, container)
                else:
                    result = {"success": False, "message": "Container not found"}
                    
        elif action == "use":
            item1_id = params.get("item1_id")
            item2_id = params.get("item2_id")
            if item1_id and item2_id:
                result = self.player.use_object_with(item1_id, item2_id)
                
        # Information actions
        elif action == "look":
            direction = params.get("direction")
            result = self.player.look(self.board, direction)
            
        elif action == "say":
            message = params.get("message")
            if message:
                result = self.player.say(message)
                
        # Inventory management
        elif action == "inventory":
            items = self.player.inventory.get_contents()
            result = {
                "success": True, 
                "message": f"{self.player.name} has {len(items)} items",
                "items": items
            }
            
        # Log the result message
        if "message" in result:
            self.log_message(result["message"])
            
        # Increment turn counter for successful actions
        if result.get("success", False):
            self.turn_count += 1
            
        return result
    
    def get_visible_entities(self) -> List[Entity]:
        """Get all entities visible to the player."""
        # For simplicity, we'll say all entities on the board are visible
        # In a more complex game, you'd implement field of view calculations
        return self.board.get_all_entities()
    
    def find_entities(self, search_term: str) -> List[Entity]:
        """Find entities matching the search term."""
        return self.board.find_entities_by_name(search_term)
        
    def is_valid_action(self, action: str, **params) -> Dict[str, Any]:
        """Check if an action is valid with the given parameters."""
        # This would validate an action before performing it
        # For now, just a placeholder that could be expanded
        valid_actions = ["walk", "run", "jump", "push", "pull", "get", 
                         "put", "use", "look", "say", "inventory"]
                         
        if action not in valid_actions:
            return {"valid": False, "message": f"Unknown action: {action}"}
            
        return {"valid": True}
    
    def set_weather(self, weather_type: WeatherType, intensity: float = 0.5, 
                   duration: int = 100, coverage: float = 0.8) -> None:
        """Set a specific weather condition."""
        params = WeatherParameters(intensity=intensity, duration=duration, coverage=coverage)
        weather = WeatherFactory.create_weather(weather_type, params)
        
        # Clear previous weather of same type if present
        self.weather_system.current_weather = [w for w in self.weather_system.current_weather 
                                             if not isinstance(w, type(weather))]
        self.weather_system.add_weather(weather)
        
        # Log the weather change
        weather_name = weather_type.name.replace("_", " ").lower()
        self.log_message(f"The weather has changed to {weather_name}.")
    
    def update_weather(self, delta_time: float = 1.0) -> None:
        """Update the weather system."""
        self.weather_system.update(delta_time)
        
        # Get weather effects and apply them to the game world
        weather_state = self.weather_system.get_game_state()
        
        # You can add code here to apply weather effects to the game world
        # For example, affecting visibility, movement speed, etc.
        
        return weather_state
    
    def get_current_weather(self) -> Dict[str, Any]:
        """Get the current weather conditions and their effects."""
        return self.weather_system.get_game_state() 