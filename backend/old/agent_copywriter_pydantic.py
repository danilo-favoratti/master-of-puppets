from typing import List, Dict, Any, Optional, Union, Set
from pydantic import BaseModel, Field
import json
import re


def to_camel_case(snake_str: str) -> str:
    """Convert a snake_case string to camelCase"""
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class Position(BaseModel):
    """Position of an entity on the map"""
    x: int
    y: int


class Entity(BaseModel):
    """Game entity model"""
    id: Optional[str] = None
    name: str
    type: Optional[str] = None
    actions: List[str] = Field(alias="possibleActions", default_factory=list)
    description: Optional[str] = None
    position: Optional[Position] = None
    variant: Optional[str] = None
    state: Optional[str] = None
    is_movable: bool = Field(alias="isMovable", default=False)
    is_jumpable: bool = Field(alias="isJumpable", default=False)
    is_usable_alone: bool = Field(alias="isUsableAlone", default=False)
    is_collectable: bool = Field(alias="isCollectable", default=False)
    is_wearable: bool = Field(alias="isWearable", default=False)
    weight: int = 1
    
    # Additional fields that might be in entities
    capacity: Optional[int] = None
    durability: Optional[int] = None
    max_durability: Optional[int] = Field(alias="maxDurability", default=None)
    size: Optional[str] = None
    locked: Optional[bool] = None
    lock_type: Optional[str] = Field(alias="lockType", default=None)
    contents: Optional[List[Dict[str, Any]]] = None
    
    class Config:
        # Allow population by alias
        populate_by_name = True
        # Allow extra fields
        extra = "allow"
    
    def to_camel_case_dict(self) -> Dict[str, Any]:
        """Convert the entity to a dictionary with camelCase keys"""
        # Handle both Pydantic v1 and v2
        data = self.dict(exclude_none=True) if hasattr(self, 'dict') else self.model_dump(exclude_none=True)
        
        result = {}
        for key, value in data.items():
            if key == "actions":
                result["possibleActions"] = value
            elif key == "max_durability":
                result["maxDurability"] = value
            elif key == "lock_type":
                result["lockType"] = value
            elif key.startswith("is_"):
                result[f"is{key[3:].title()}"] = value
            else:
                # Convert regular snake_case to camelCase
                camel_key = to_camel_case(key)
                result[camel_key] = value
                
        return result


class Objective(BaseModel):
    """Quest objective model"""
    description: str
    target_entity: Optional[str] = None
    completed: bool = False


class Quest(BaseModel):
    """Game quest model"""
    objectives: List[str]
    title: Optional[str] = None
    description: Optional[str] = None
    reward: Optional[str] = None


class MapTile(BaseModel):
    """Individual map tile"""
    type: int  # 0 for water, 1 for land


class GameMap(BaseModel):
    """Game map structure"""
    size: int
    border_size: int = Field(alias="borderSize")
    grid: List[List[int]]
    entities: Optional[List[Dict[str, Any]]] = None
    
    class Config:
        populate_by_name = True
    
    @staticmethod
    def from_factory_json(ui_json: Dict[str, Any]) -> 'GameMap':
        """
        Create a GameMap instance from the factory's UI JSON output.
        
        Args:
            ui_json: The JSON dictionary from factory.export_world_ui_json()
            
        Returns:
            GameMap: A populated GameMap instance
        """
        if not ui_json or not isinstance(ui_json, dict):
            raise ValueError("Invalid UI JSON provided")
            
        map_data = ui_json.get("map", {})
        if not map_data:
            raise ValueError("Missing map data in UI JSON")
            
        return GameMap(
            size=map_data.get("size", 60),
            border_size=map_data.get("borderSize", 15),
            grid=map_data.get("grid", []),
            entities=ui_json.get("entities", [])
        )


class GameData(BaseModel):
    """Main game data model"""
    theme: str
    map: Dict[str, Any]
    entities: List[Dict[str, Any]]
    quest: Dict[str, Any]
    gameInstructions: str
    
    class Config:
        populate_by_name = True


class CopywriterAgentAdapter:
    """Adapter class to handle data conversion for CopywriterAgent"""
    
    @staticmethod
    def map_from_factory(factory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert factory_game.py's generate_world() output to compatible map data"""
        # The factory data already has the format expected by the agent
        # Extract what we need from the world data
        if "map" in factory_data:
            grid = factory_data["map"]
        else:
            grid = []
            
        # Create a standard map format
        return {
            "size": factory_data.get("map_size", 60),
            "borderSize": factory_data.get("border_size", 15),
            "grid": grid
        }
    
    @staticmethod
    def create_entity(name: str, actions: List[str], **kwargs) -> Dict[str, Any]:
        """Create an entity dictionary with the required format"""
        # Generate an ID if not provided
        if "id" not in kwargs:
            import random
            entity_type = kwargs.get("type", "entity")
            kwargs["id"] = f"{entity_type}-{random.randint(1, 1000)}"
            
        entity = Entity(
            name=name,
            possibleActions=actions,  # Using the alias
            **kwargs
        )
        
        # Convert to camelCase format
        return entity.to_camel_case_dict()
    
    @staticmethod
    def create_quest(objectives: List[str], **kwargs) -> Dict[str, Any]:
        """Create a quest dictionary with the required format"""
        quest = Quest(
            objectives=objectives,
            **kwargs
        )
        # Handle both Pydantic v1 and v2
        return quest.dict(exclude_none=True) if hasattr(quest, 'dict') else quest.model_dump(exclude_none=True)
    
    @staticmethod
    def format_game_data(theme: str, map_data: Dict[str, Any], 
                         entities: List[Dict[str, Any]], quest: Dict[str, Any], 
                         instructions: str) -> Dict[str, Any]:
        """Format all game data into the expected JSON structure"""
        game_data = GameData(
            theme=theme,
            map=map_data,
            entities=entities,
            quest=quest,
            gameInstructions=instructions
        )
        # Handle both Pydantic v1 and v2
        return game_data.dict() if hasattr(game_data, 'dict') else game_data.model_dump()
    
    @staticmethod
    def validate_game_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the game data against the expected schema"""
        try:
            game_data = GameData(**data)
            # Handle both Pydantic v1 and v2
            return game_data.dict() if hasattr(game_data, 'dict') else game_data.model_dump()
        except Exception as e:
            print(f"Game data validation error: {str(e)}")
            return {"error": str(e)}
    
    @staticmethod
    def adapt_runner_output(output) -> Dict[str, Any]:
        """Adapt the Runner.run output to a proper JSON format"""
        if hasattr(output, 'final_output'):
            try:
                # Try to parse as JSON
                data = json.loads(output.final_output)
                # Validate the data against our schema
                return CopywriterAgentAdapter.validate_game_data(data)
            except (json.JSONDecodeError, TypeError):
                # If not valid JSON, return as text
                return {"text": str(output.final_output)}
        elif isinstance(output, dict):
            # If it's already a dictionary, validate it
            return CopywriterAgentAdapter.validate_game_data(output)
        elif hasattr(output, '__dict__'):
            # If it's an object with a __dict__, convert it to a dictionary
            return output.__dict__
        else:
            # Fall back to string representation
            return {"error": f"Invalid output format: {str(output)}"}

    @staticmethod
    def prepare_agent_context(context: Any) -> Dict[str, Any]:
        """
        Prepare a context object for use with the Agent Runner.
        Validates and formats the context to ensure it's compatible.
        
        Args:
            context: The context object to prepare (typically a GameContext)
            
        Returns:
            Dict: A dictionary representation of the context
            
        Raises:
            ValueError: If the context is invalid
        """
        # Check if context has a to_dict method (from TContext)
        if hasattr(context, 'to_dict'):
            context_data = context.to_dict()
        # Check if context has __dict__ attribute
        elif hasattr(context, '__dict__'):
            context_data = context.__dict__
        # Handle dict-like objects
        elif hasattr(context, 'get') and hasattr(context, 'items'):
            context_data = dict(context)
        else:
            raise ValueError(f"Invalid context object type: {type(context).__name__}")
        
        # Ensure required fields exist
        if 'name' not in context_data:
            context_data['name'] = 'game_context'
            
        # Make sure entities is a list
        if 'entities' in context_data and not isinstance(context_data['entities'], list):
            context_data['entities'] = []
            
        return context_data


# Modify the CopywriterAgent to use this adapter
def modify_copywriter_agent_code():
    """
    Changes needed in CopywriterAgent.process_user_input method (around line 728):
    
    ```python
    try:
        result = await Runner.run(
            starting_agent=agent,
            input=user_input,
            context=self.game_context
        )
        logger.info("Runner.run completed in CopywriterAgent.")

        # Use the adapter to process the result
        adapter = CopywriterAgentAdapter()
        result_json = adapter.adapt_runner_output(result)
        
        if isinstance(result_json, dict) and "error" not in result_json:
            self.game_context.environment = result_json.get("map", {})
            self.game_context.entities = result_json.get("entities", [])
            self.game_context.quest = result_json.get("quest", {})

            response = {"type": "system", "content": "Adventure Created"}
            logger.info("Formatted JSON response processed from agent.")
            return response, conversation_history
    ```
    """
    pass


# Example usage:
if __name__ == "__main__":
    import factory_game
    
    # Create a game factory
    factory = factory_game.GameFactory()
    
    # Generate world data
    world = factory.generate_world()
    
    # Use the adapter to convert the map
    adapter = CopywriterAgentAdapter()
    
    # Convert directly from the factory export method
    ui_json = factory.export_world_ui_json()
    
    # Create a simple quest for testing
    quest = adapter.create_quest(
        objectives=["Find the secret chest", "Open the locked chest"],
        title="Treasure Hunt",
        description="Search for valuable treasure on the Least Island!"
    )
    
    # Create game data with the factory map and entities plus our quest
    game_data = adapter.format_game_data(
        theme="Adventure Island",
        map_data=ui_json["map"],
        entities=ui_json["entities"],
        quest=quest,
        instructions="Explore the island and find the hidden treasure!"
    )
    
    # Test against expected format
    expected_format = {
        "theme": "Abandoned Island",
        "map": {
            "size": 4,
            "borderSize": 1,
            "grid": [
                [0, 0, 0, 0],
                [0, 1, 1, 0],
                [0, 1, 1, 0],
                [0, 0, 0, 0]
            ]
        },
        "entities": [
            {
                "id": "campfire-1",
                "type": "campfire",
                "name": "Camp Fire",
                "position": {
                    "x": 2,
                    "y": 2
                },
                "state": "unlit",
                "variant": "1",
                "isMovable": False,
                "isJumpable": True,
                "isUsableAlone": True,
                "isCollectable": False,
                "isWearable": False,
                "weight": 5,
                "possibleActions": [
                    "light",
                    "extinguish"
                ],
                "description": "A pile of dry wood ready to be lit."
            }
        ],
        "quest": {
            "objectives": [
                "Open the Chest",
                "Get the key"
            ]
        },
        "gameInstructions": "You have to find a open secret treasure chest."
    }
    
    # Validate the expected format too
    print("Validating expected format...")
    validated_expected = adapter.validate_game_data(expected_format)
    if "error" in validated_expected:
        print(f"Expected format does not validate: {validated_expected['error']}")
    else:
        print("Expected format validates correctly!")
    
    # Validate our game data
    print("\nValidating generated game data...")
    validated_game_data = adapter.validate_game_data(game_data)
    if "error" in validated_game_data:
        print(f"Generated format does not validate: {validated_game_data['error']}")
    else:
        print("Generated game data validates correctly!")
    
    # Print comparison with expected format
    print("\nGenerated output has the same structure as the expected format:")
    print(f"- Has 'theme' field: {'theme' in game_data}")
    print(f"- Has 'map' field with required properties: {'map' in game_data and all(k in game_data['map'] for k in ['size', 'borderSize', 'grid'])}")
    print(f"- Has 'entities' field with array: {'entities' in game_data and isinstance(game_data['entities'], list)}")
    
    if len(game_data['entities']) > 0:
        entity = game_data['entities'][0]
        print("\nSample entity fields:")
        print(f"- Has 'id': {'id' in entity}")
        print(f"- Has 'type': {'type' in entity}")
        print(f"- Has 'name': {'name' in entity}")
        print(f"- Has 'position': {'position' in entity}")
        print(f"- Has 'isMovable' camelCase prop: {'isMovable' in entity}")
        print(f"- Has 'possibleActions': {'possibleActions' in entity}")
    
    print(f"- Has 'quest' field: {'quest' in game_data and 'objectives' in game_data['quest']}")
    print(f"- Has 'gameInstructions': {'gameInstructions' in game_data}")
    
    # See the first few entities as an example
    print("\nSample output (first 3 entities):")
    print(json.dumps({
        "theme": game_data["theme"],
        "map": game_data["map"],
        "entities": game_data["entities"][:3] if len(game_data["entities"]) >= 3 else game_data["entities"],
        "quest": game_data["quest"],
        "gameInstructions": game_data["gameInstructions"]
    }, indent=2)) 