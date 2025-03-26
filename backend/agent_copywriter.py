import logging
import os
import traceback
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple, Optional

from agents import Runner, Agent, function_tool, RunContextWrapper
from deepgram import DeepgramClient
from openai import OpenAI
from pydantic import BaseModel, Field

from agent_copywriter_pydantic import GameMap
from factory_game import MAP_SIZE

DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"
logging.basicConfig(level=logging.DEBUG if DEBUG_MODE else logging.INFO)
logger = logging.getLogger(__name__)
logger.debug("Debug mode enabled.")

class Environment(BaseModel):
    size: int
    border_size: int
    grid: List[List[int]]

class Position(BaseModel):
    x: int
    y: int

class SmallEntity(BaseModel):
    id: Optional[str] = None
    type: Optional[str] = None
    name: str
    position: Optional[Position] = None
    state: Optional[str] = None
    variant: Optional[str] = None
    isMovable: Optional[bool] = False
    isJumpable: Optional[bool] = False
    isUsableAlone: Optional[bool] = False
    isCollectable: Optional[bool] = False
    isWearable: Optional[bool] = False
    weight: int = 1
    possibleActions: List[str] = Field(default_factory=list, alias="possibleActions")
    durability: Optional[int] = None
    maxDurability: Optional[int] = Field(default=None, alias="maxDurability")
    size: Optional[str] = None
    description: Optional[str] = None

class Entity(BaseModel):
    id: Optional[str] = None
    type: Optional[str] = None
    name: str
    position: Optional[Position] = None
    state: Optional[str] = None
    variant: Optional[str] = None
    isMovable: Optional[bool] = False
    isJumpable: Optional[bool] = False
    isUsableAlone: Optional[bool] = False
    isCollectable: Optional[bool] = False
    isWearable: Optional[bool] = False
    weight: int = 1
    possibleActions: List[str] = Field(default_factory=list, alias="possibleActions")
    durability: Optional[int] = None
    maxDurability: Optional[int] = Field(default=None, alias="maxDurability")
    size: Optional[str] = None
    description: Optional[str] = None
    contents: Optional[List[SmallEntity]] = None
    capacity: Optional[int] = None

    class Config:
        allow_population_by_field_name = True

class Quest(BaseModel):
    objectives: List[str]

class StoryTellerGameContext(BaseModel):
    name: str = "game_context"
    theme: Optional[str] = None
    environment: Optional[Environment] = None
    entities: List[Entity] = Field(default_factory=list)
    quest: Optional[Quest] = None
    game_instructions: Optional[str] = Field(default=None, alias="game-instructions")

    class Config:
        allow_population_by_field_name = True


@dataclass
class GameContext(BaseModel):
    name: str
    theme: Optional[str]
    environment: Optional[Dict[str, Any]]
    entities: List[Dict[str, Any]]
    quest: Optional[Dict[str, Any]]
    game_instructions: str

    def __init__(self, /, **data: Any):
        super().__init__(**data)
        self.name = "game_context"
        self.theme = None
        self.environment = None
        self.entities = []
        self.quest = None
        self.game_instructions = None


@function_tool
async def create_map(
        ctx: RunContextWrapper[GameContext],
        chest_count: int,
        camp_count: int,
        obstacle_count: int,
        campfire_count: int,
        backpack_count: int,
        firewood_count: int,
        tent_count: int,
        bedroll_count: int,
        log_stool_count: int,
        campfire_spit_count: int,
        campfire_pot_count: int,
        pot_count: int
) -> Dict[str, Any]:
    logger.info("Entered create_map function.")
    try:
        logger.info("Starting map creation process.")
        # Set defaults for any missing parameters
        chest_count = chest_count or 5
        camp_count = camp_count or 3
        obstacle_count = obstacle_count or 10
        campfire_count = campfire_count or 4
        backpack_count = backpack_count or 3
        firewood_count = firewood_count or 6
        tent_count = tent_count or 2
        bedroll_count = bedroll_count or 3
        log_stool_count = log_stool_count or 4
        campfire_spit_count = campfire_spit_count or 2
        campfire_pot_count = campfire_pot_count or 2
        pot_count = pot_count or 5

        logger.info(
            f"Map parameters - chests: {chest_count}, camps: {camp_count}, obstacles: {obstacle_count}, "
            f"campfires: {campfire_count}, backpacks: {backpack_count}, firewood: {firewood_count}, "
            f"tents: {tent_count}, bedrolls: {bedroll_count}, log stools: {log_stool_count}, "
            f"campfire spits: {campfire_spit_count}, campfire pots: {campfire_pot_count}, pots: {pot_count}"
        )

        from factory_game import create_game
        logger.info("Imported create_game from factory_game.")

        logger.info("Creating game world...")

        from factory_game import GameFactory
        factory = GameFactory()
        world = factory.generate_world(
            chest_count=chest_count,
            camp_count=camp_count,
            obstacle_count=obstacle_count,
            campfire_count=campfire_count,
            backpack_count=backpack_count,
            firewood_count=firewood_count,
            tent_count=tent_count,
            bedroll_count=bedroll_count,
            log_stool_count=log_stool_count,
            campfire_spit_count=campfire_spit_count,
            campfire_pot_count=campfire_pot_count,
            pot_count=pot_count
        )
        logger.info("GameFactory instance created.")
        logger.info("Exporting UI JSON from game factory...")

        ui_json = factory.export_world_ui_json()
        logger.info("UI JSON exported successfully.")

        # Create a GameMap object from the UI JSON
        try:
            game_map = GameMap.from_factory_json(ui_json)
            logger.info(f"GameMap created with {len(game_map.entities or [])} entities")
        except ValueError as e:
            logger.error(f"Error creating GameMap: {str(e)}")
            return {"error": str(e)}

        # Save map details in context
        logger.info("Storing map details in context.")
        ctx.context.environment = {
            "map_size": MAP_SIZE,
            "map_data": ui_json
        }

        # Convert to dict for return value
        map_dict = game_map.dict() if hasattr(game_map, 'dict') else game_map.model_dump()
        logger.info(f"Map creation completed with {len(map_dict.get('entities', []))} entities")
        return map_dict
    except Exception as e:
        error_message = f"Error creating map: {str(e)}"
        logger.error(error_message, exc_info=True)
        return {"error": error_message}


class CopywriterAgent:
    """
    Agent for creating the game framework.
    """

    def __init__(
            self,
            openai_api_key: str = os.getenv("OPENAI_API_KEY"),
            deepgram_api_key: str = os.getenv("DEEPGRAM_API_KEY"),
            voice: str = os.getenv("CHARACTER_VOICE"),
    ):
        logger.info("Initializing CopywriterAgent.")
        self.openai_key = openai_api_key
        self.voice = voice

        self.openai_client = OpenAI(api_key=openai_api_key)
        logger.info("Initialized OpenAI client.")

        # Use the GameContext as our AgentContext
        self.game_context = StoryTellerGameContext(name="game_context")
        logger.info("Game context initialized.")

        self.agent_data = self.setup_agent()
        logger.info("Agent data setup completed.")

        try:
            self.deepgram_client = DeepgramClient(api_key=deepgram_api_key)
            logger.info("Initialized Deepgram client with explicit api_key parameter")
        except Exception as e:
            logger.error(f"Failed to initialize Deepgram client: {e}", exc_info=True)

    def setup_agent(self) -> Dict:
        logger.info("Setting up the OpenAI agent with system prompt and tools.")
        system_prompt = """
# MISSION
You are a creative copywriter tasked with crafting the core of an RPG game story. Your goal is to design a rich narrative structure with all necessary game parameters.

# INSTRUCTIONS
1. **Theme:** Use the user's first input as the **[THEME]**. If none is provided, ask for it. The setting is always *The Island of the Least!*.
2. **Map:** Create a creative **[MAP]** based on the **[THEME]** using your internal tools.
3. **Entities:** Define 20-30 **[ENTITIES]** with a set of **[ACTIONS]** each.
4. **Quest:** Develop a **[QUEST]** with 4 to 7 **[OBJECTIVES]**, each being an interaction with the entities.
5. **Output:** Return a JSON object including **theme, map, entities, quest, and game parameters** for the Storyteller.

- Use a witty, humorous tone.
- **Bold** the main words.
- Respond in valid JSON format.

Example JSON Structure:
{
  "name": "Great Day To Die Alone"
  "theme": "Abandoned Island",
  "environment": {
    "size": 4,
    "border_size": 1,
    "grid": [
      [0, 0, 0, 0],
      [0, 1, 1, 0],
      [0, 1, 1, 0],
      [0, 0, 0, 0]
    ]
  },
  "entities": { 
    "anyOf": [
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
          "isMovable": false,
          "isJumpable": true,
          "isUsableAlone": true,
          "isCollectable": false,
          "isWearable": false,
          "weight": 5,
          "possibleActions": [
            "light",
            "extinguish"
          ],
          "description": "A pile of dry wood ready to be lit."
        },
        {
          "id": "chest-1",
          "type": "chest",
          "name": "Magical Chest",
          "position": {
            "x": 1,
            "y": 1
          },
          "state": "locked",
          "variant": "magical",
          "isMovable": false,
          "isJumpable": false,
          "isUsableAlone": true,
          "isCollectable": false,
          "isWearable": false,
          "weight": 10,
          "contents": [
            {
              "name": "legendary_weapon",
              "tier": "magical",
              "quantity": 2
            },
            {
              "name": "magic_wand",
              "tier": "golden",
              "quantity": 1
            }
          ],
          "description": "A container for storing valuable items."
        },
        {
          "id": "pot-1",
          "type": "pot",
          "name": "Pot",
          "position": {
            "x": 0,
            "y": 3
          },
          "state": "default",
          "variant": "1",
          "isMovable": true,
          "isJumpable": false,
          "isUsableAlone": true,
          "isCollectable": false,
          "isWearable": false,
          "weight": 10,
          "capacity": 5,
          "durability": 75,
          "maxDurability": 75,
          "size": "medium",
          "description": "A simple pot, useful for various tasks."
        }
    }
  ],
  "quest": {
    "objectives": [
      "Open the Chest",
      "Get the key"
    ]
  },
  "game-instructions": "You have to find a open secret treasure chest."
}


# GAME WORD
This document explains the structure of the source code for various game objects and mechanics. 
It outlines the objects, their properties, available actions, the factory methods used to create them, 
and how they integrate with the overall game world (including the board, player, and weather systems). 
Use this as a comprehensive reference when prompting your game-creation agent.

---

## Entity

All Items are Entities and they can have this values: 
id: str = None
type: str = None
name: str
position: Position = None
state: str = None
variant: str = None
isMovable: bool = False
isJumpable: bool = False
isUsableAlone: bool = False
isCollectable: bool = False
isWearable: bool = False
weight: int = 1
possibleActions: List[str] = Field(default_factory=list, alias="possibleActions")
durability: int = None
maxDurability: int = Field(default=None, alias="maxDurability")
size: str = None
description: str = None
contents: List[SmallEntity]] = None
capacity: int] = None

SmallEntity is a Entity without contents and capacity 

Position is x, y

## 1. Interactive Items and Their Factories

### 1.1. Backpack (Entity)
- **Class:** `Backpack` (inherits from `GameObject`)
- **Properties:**
  - `contained_items`: A list of item names currently held.
  - `possible_alone_actions`: A set of actions available when the backpack is used alone.
  - `weight`: Set to `2`
  - `usable_with`: Initially an empty set.
  - **Preset Data:**
    - Name: `"Small Backpack"`
    - Description: `"A small backpack that can hold a few items."`
    - Max Capacity: `5`
  - **ID Generation:** Automatically generates an ID if not provided.

---
# Simplified Game Object Definitions

---

## 1.2. Bedroll
- **Class:** `Bedroll` (inherits from `GameObject`)
- **Properties:**
  - `max_capacity`: 1 (holds one person)
  - `contained_items`: list of users
  - `possible_alone_actions`: includes `"sleep"`
  - `weight`: 2  
  - **Interaction Flags:** movable, not jumpable, usable alone
- **Action:** Uses `"sleep"`
- **Methods:** `to_dict()`
- **Factory:** `BedrollFactory` (variant: `"standard"`)
  - **Preset Data:**
    - Name: `"Bedroll"`
    - Description: `"A comfortable bedroll for sleeping."`
- **ID Generation:** Auto-generated if missing

---

## 1.3. Campfire Pot
- **Class:** `CampfirePot` (inherits from `GameObject`)
- **Properties:**
  - `pot_type`: defaults to `POT_TRIPOD`
  - `state`: starts as `POT_EMPTY`
  - `max_items`: 1 (for one cooking item)
  - `contained_items`: items being cooked
  - `weight`: 3  
  - **Interaction Flags:** movable, not jumpable, usable alone  
  - `usable_with`: `{CAMPFIRE_BURNING, CAMPFIRE_DYING}`
- **Possible Actions:**
  - Empty: `{ACTION_PLACE}`
  - Cooking/Burning: `{ACTION_REMOVE}`
  - Cooked: `{ACTION_REMOVE, ACTION_EMPTY}`
- **Methods:** `to_dict()`
- **Factory:** `CampfirePotFactory`
  - **Preset Data Example:**
    - **Tripod:** Name: `"Cooking Tripod"`, Description: `"A sturdy metal tripod for cooking."`
    - **Spit:** Name: `"Roasting Spit"`, Description: `"A long metal spit for roasting meat."`
- **ID Generation:** Auto-generated if not provided

---

## 1.4. Spit Item
- **Class:** `SpitItem` (inherits from `GameObject`)
- **Properties:**
  - `item_type`: e.g., `SPIT_BIRD`
  - `state`: begins as `SPIT_ITEM_RAW`
  - `cooking_time`: default is 5 turns
  - `is_edible`: `True`
  - `weight`: 1  
  - **Interaction Flags:** movable, not jumpable, usable alone  
  - `usable_with`: `{POT_SPIT}`
- **Possible Actions:**
  - Raw: `{ACTION_PLACE_ON_SPIT}`
  - Cooking/Burning: `{ACTION_REMOVE_FROM_SPIT}`
  - Cooked: `{ACTION_REMOVE_FROM_SPIT, ACTION_EAT}`
- **Methods:** `to_dict()`
- **Factory:** `SpitItemFactory`
  - **Preset Data Example (for SPIT_BIRD):**
    - Name: `"Raw Bird"`
    - Description: `"A plucked bird ready for roasting."`
- **ID Generation:** Auto-generated if not provided

---

## 1.5. Campfire Spit
- **Class:** `CampfireSpit` (inherits from `GameObject`)
- **Properties:**
  - `quality`: e.g., `SPIT_QUALITY_BASIC`
  - `durability` & `max_durability`: default 100 (may vary with quality)
  - `cooking_bonus`: default 0 (may vary with quality)
  - `weight`: 2  
  - **Interaction Flags:** movable, not jumpable, usable alone  
  - `usable_with`: `{POT_SPIT}`
- **Methods:** `to_dict()`
- **Factory:** `CampfireSpitFactory`
  - **Variants:**
    - **Basic:** Name: `"Basic Campfire Spit"`, Durability: 100, Bonus: 0
    - **Sturdy:** Name: `"Sturdy Campfire Spit"`, Durability: 150, Bonus: 1
    - **Reinforced:** Name: `"Reinforced Campfire Spit"`, Durability: 200, Bonus: 2
- **ID Generation:** Auto-generated if missing

---

## 1.6. Campfire
- **Class:** `Campfire` (inherits from `GameObject`)
- **Properties:**
  - `state`: one of `CAMPFIRE_UNLIT`, `CAMPFIRE_BURNING`, `CAMPFIRE_DYING`, `CAMPFIRE_EXTINGUISHED`
  - `weight`: 5  
  - **Interaction Flags:** not movable, jumpable, usable alone
  - `usable_with`: empty set (but can interact with items like wood or water)
- **Possible Actions:**
  - Unlit or Extinguished: `{ACTION_LIGHT}`
  - Burning/Dying: `{ACTION_EXTINGUISH}`
- **Methods:** `to_dict()`
- **Factory:** `CampfireFactory`
- **ID Generation:** Provided if missing

---

## 1.7. Chest
- **Class:** `Chest` (inherits from `Container`)
- **Properties:**
  - `chest_type`: type identifier (e.g., `CHEST_BASIC_WOODEN`, etc.)
  - `is_locked`: boolean flag
  - `lock_difficulty`: scale from 0 to 10
  - `durability`: value from 0 to 100
  - `weight`: typically around 10 (may vary)
  - **Interaction Flags:** movable, not jumpable, usable alone
- **Factories:**
  - **ChestFactory:** Contains a variety of chest types
  - **Random Creation:** `create_chest(chest_type: str = None)` randomly selects a type
  - **Contents & Lock Types:** Defined by rarity tiers and preset item lists
- **ID Generation:** Managed automatically

---

## 1.8. Firewood
- **Class:** `Firewood` (inherits from `GameObject`)
- **Properties:**
  - `description`
  - `weight`: 1  
  - **Interaction Flags:** movable, not jumpable, usable alone, collectable  
  - `possible_alone_actions`: includes `"collect"`
- **Methods:** `to_dict()`
- **Factory:** `FirewoodFactory` (variant: `"branch"`)
  - **Preset Data:**
    - Name: `"Fallen Branch"`
    - Description: `"A dry branch that can be collected for firewood."`
- **ID Generation:** Auto-handled

---

## 1.9. Land Obstacles
- **Factory:** `LandObstacleFactory` provides static creation methods for environmental obstacles:
  - **`create_hole`:**
    - Name: `"Hole"`
    - **Flags:** non-movable, non-collectable, jumpable; weight: 0
  - **`create_fallen_log`:**
    - Size options: `small`, `medium`, `large`
    - Name varies accordingly (e.g., `"Small Fallen Log"`)
  - **`create_tree_stump`:**
    - Accepts a height (1–3) to set name and weight
  - **`create_rock`:**
    - Types: `"pebble"`, `"stone"`, `"boulder"` (properties vary)
  - **`create_plant`:**
    - Types include `"bush"`, `"wild-bush"`, `"leafs"`, `"tall-grass"`, etc.
  - **`create_chestnut_tree`:**
    - A special non-jumpable tree
  - **`create_random_obstacle`:**
    - Randomly selects one of the obstacles
  - **Wrapper Function:** `create_land_obstacle(obstacle_type: str = None, **props)`
- **ID Generation:** Not explicitly specified

---

## 1.10. Log Stool
- **Class:** `LogStool` (inherits from `GameObject`)
- **Properties:**
  - `description`
  - `weight`: 3  
  - **Interaction Flags:** movable, not jumpable, usable alone  
  - `possible_alone_actions`: includes `"sit"`
- **Methods:** `to_dict()`
- **Factory:** `LogStoolFactory` (variant: `"squat"`)
  - **Preset Data:**
    - Name: `"Squat Log"`
    - Description: `"A short, sturdy log that can be used as a stool."`

---

## 1.11. Pot
- **Class:** `Pot` (inherits from `Container`)
- **Properties:**
  - `pot_size`: options: `"small"`, `"medium"`, `"big"`
  - `state`: one of `POT_STATE_DEFAULT`, `POT_STATE_BREAKING`, or `POT_STATE_BROKEN`
  - `max_durability` & `current_durability`: set according to pot size
  - `capacity`:  
    - `"small"`: 3 items  
    - `"medium"`: 5 items  
    - `"big"`: 8 items
  - `weight`: varies (e.g., 5, 10, or 20)
  - **Interaction Flags:** usable alone, not collectable
- **Additional Methods:**
  - `damage(amount)`: reduces durability and updates state
  - `add_item(item)`: prevents adding items if broken
  - `to_dict()`
- **Factory:** `PotFactory`
  - **Preset Data:** stored in `_pot_data`
  - **Helper Function:** `create_pot(size: str = None, state: str = None)` (chooses random size if none specified)

---

## 1.12. Tent
- **Class:** `Tent` (inherits from `GameObject`)
- **Properties:**
  - `max_capacity`: 1 (for one person)
  - `contained_items`: list of sheltered users
  - `weight`: 5  
  - **Interaction Flags:** movable, not jumpable, usable alone
  - **Possible Actions:** `{ACTION_ENTER, ACTION_EXIT}` (for entering and exiting)
- **Factory:** `TentFactory` (variant: `"small"`)
  - **Preset Data:**
    - Name: `"Tent"`
    - Description: `"A small tent that can shelter one person."`

---

## 2. Weather System

The weather system simulates environmental effects that influence gameplay.

### 2.1. Weather Types (Enum: `WeatherType`)
- **Members:**
  - `CLOUD_COVER`
  - `RAINFALL`
  - `SNOWFALL`
  - `LIGHTNING_STRIKES`
  - `SNOW_COVER`
  - `CLEAR`

### 2.2. Weather Parameters
- **Class:** `WeatherParameters`
  - **Attributes:**
    - `intensity`: Float (0.0–1.0)
    - `duration`: Duration in game turns
    - `coverage`: Fraction of the map affected (0.0–1.0)

### 2.3. Weather Base Class and Subclasses
- **Base Class:** `Weather`
  - Manages remaining duration.
  - **Methods:**
    - `update(delta_time)`: Decrements the remaining duration.
    - `is_active()`: Returns whether the weather is still in effect.
    - `get_effects()`: Returns a dictionary of effects (empty in the base class).
- **Subclasses:**
  - **`CloudCover`:**  
    - Effects: Reduced visibility, slight temperature drop, mood modifier.
  - **`Rainfall`:**  
    - Effects: Reduced movement speed, lower visibility, chance to extinguish fires, temperature and mood modifiers.
  - **`Snowfall`:**  
    - Effects: Heavy impact on movement/visibility, significant temperature drop, nuanced mood effects.
  - **`LightningStrikes`:**  
    - Effects: Chance for lightning strikes causing damage, fire-starting, and a momentary visibility flash.
  - **`SnowCover`:**  
    - Effects: Slower movement, tracking bonus, temperature reduction, concealment penalty.
  - **`Clear`:**  
    - Effects: Bonus visibility, improved mood, temperature boost.
- **Factory:** `WeatherFactory`
  - Creates weather objects based on a given `WeatherType` and parameters.
- **WeatherSystem:**
  - Manages active weather conditions.
  - **Methods:**
    - `add_weather(weather)`: Adds a weather condition.
    - `update(delta_time)`: Updates all weather conditions and removes inactive ones.
    - `get_combined_effects()`: Aggregates effects from all active weather conditions.
    - `get_game_state()`: Provides the current weather state and combined effects.
    - `get_random_weather(exclude_types)`: Generates a random weather condition (with optional exclusions).

---

## 3. Core Game Infrastructure

### 3.1. The Board Class
- **Purpose:**  
  Represents the 2D game world and manages the placement and movement of entities.
- **Key Properties:**
  - `width` and `height`: Dimensions of the board.
  - `_position_map`: A mapping from positions to lists of entities (using a `defaultdict`).
  - `_entity_map`: A mapping from entity IDs to entities.
- **Key Methods:**
  - `is_valid_position(position)`: Checks if a given position is within the board.
  - `add_entity(entity, position)`: Places an entity on the board and updates maps.
  - `remove_entity(entity)`: Removes an entity from the board and clears its position.
  - `move_entity(entity, new_position)`: Moves an entity to a new position with rollback on failure.
  - `get_entity(entity_id)`: Retrieves an entity by its ID.
  - `get_entities_at(position)`: Returns all entities at a specific position.
  - `get_object_at(position)`: Returns the first `GameObject` found at a position.
  - `can_move_to(position)`: Checks if a position is free (within bounds and not blocked by a `GameObject`).
  - `get_all_entities()`: Returns a list of all entities on the board.
  - `find_entities_by_name(name)`: Finds entities whose names match the given string (partial match).
  - `find_entities_by_type(entity_type)`: Finds entities of a specific type.

### 3.2. The Entity Class
- **Purpose:**  
  The base class for any object that exists on the board.
- **Key Properties:**
  - `id`: Unique identifier.
  - `name`: The entity's name.
  - `position`: Coordinates on the board (or `None` if not placed).
  - `description`: A text description.
  - `properties`: Additional custom properties (stored as a dictionary).
- **Key Methods:**
  - `set_position(position)`: Sets the entity's position.
  - `get_position()`: Retrieves the current position.

---

## 4. The Person Class

The `Person` class models a character in the game who can move, interact, and manage an inventory.

- **Inherits from:** `Entity`
- **Key Properties:**
  - `inventory`: A `Container` that holds the person's items.
  - `wearable_items`: A list of items currently worn.
  - `strength`: Determines how heavy an object the person can move.
- **Key Methods:**
  - **Movement:**
    - `move(game_board, target_position, is_running=False)`: Walks or runs to an adjacent tile.
    - `jump(game_board, target_position)`: Jumps two squares over a jumpable obstacle.
  - **Object Interaction:**
    - `push(game_board, object_position, direction)`: Pushes an adjacent object.
    - `pull(game_board, object_position)`: Pulls an adjacent object.
    - `get_from_container(container, item_id)`: Retrieves an item from a container into the inventory.
    - `put_in_container(item_id, container)`: Places an item from the inventory into a container.
    - `use_object_with(item1_id, item2_id)`: Uses one item in combination with another.
  - **Observation and Communication:**
    - `look(game_board, direction=None)`: Looks around (or in a specified direction) to see nearby entities.
    - `say(message)`: Outputs a message.
  - **Wearing Items:**
    - `wear_item(item_id)`: Equips a wearable item.
    - `remove_item(item_id)`: Removes a worn item and returns it to inventory.
    - `get_worn_items()`: Retrieves a list of currently worn items.
    - `is_wearing(item_id)`: Checks if a specific item is being worn.

---

## 5. The Game Class

The `Game` class is the central hub that manages the overall game state, including the board, player, turn count, messages, and the weather system.

- **Key Properties:**
  - `board`: An instance of `Board` representing the game world.
  - `player`: The main player character (a `Person`).
  - `turn_count`: Tracks the number of game turns.
  - `messages`: A log of game messages and feedback.
  - `weather_system`: Manages weather conditions (using `WeatherSystem` and `WeatherFactory`).
- **Key Methods:**
  - `create_player(name, position)`: Creates a player and adds them to the board.
  - `create_object(obj_type, name, position, **properties)`: Creates and places a game object (or container) on the board.
  - `log_message(message)`: Logs a message.
  - `get_latest_messages(count=5)`: Retrieves recent messages.
  - `perform_action(action, **params)`: Processes player actions (movement, object interaction, communication, inventory management, etc.).
  - `get_visible_entities()`: Retrieves all entities visible to the player.
  - `find_entities(search_term)`: Searches for entities by name.
  - `is_valid_action(action, **params)`: Validates whether a given action can be performed.
  - **Weather Integration:**
    - `set_weather(weather_type, intensity, duration, coverage)`: Sets a specific weather condition.
    - `update_weather(delta_time=1.0)`: Updates weather conditions and applies their effects.
    - `get_current_weather()`: Returns the current weather state and combined effects.

---

## 6. Action Constants and Other Strings

- **Action Examples:**
  - `"sleep"`, `"place"`, `"remove"`, `"empty"`, `"place_on_spit"`, `"remove_from_spit"`, `"eat"`, `"light"`, `"extinguish"`, `"collect"`, `"sit"`, `"enter"`, `"exit"`
- **Chest Rarity Types:** `"wooden"`, `"silver"`, `"golden"`, `"magical"`
- **Lock Types:** Defined per chest rarity (e.g., for `"wooden"`: `["simple", "broken", None]`)
- **Other Constants:**  
  - Pot types (`POT_TRIPOD`, `POT_SPIT`)
  - Spit item types (`SPIT_BIRD`, `SPIT_FISH`, `SPIT_MEAT`)
  - Campfire states (`CAMPFIRE_UNLIT`, `CAMPFIRE_BURNING`, `CAMPFIRE_DYING`, `CAMPFIRE_EXTINGUISHED`)

---

## Summary for Agent Prompt

When instructing your game-creation agent, mention that the game world includes:
- **Interactive Items:** Backpacks, bedrolls, campfire pots, spit items, campfire spits, campfires, chests, firewood, tents, and seating (log stools).
- **Dynamic Environment:** Randomly generated land obstacles (holes, logs, stumps, rocks, plants, chestnut trees) and a weather system that affects movement, visibility, temperature, and mood.
- **Customization and Randomization:**  
  - Use factory methods to generate objects with preset attributes or random variations (unique IDs, random chest contents, random weather, etc.).
  - All objects support a `to_dict()` method for easy integration.
- **Interactions:**  
  - Items support specific actions (e.g., sleep on a bedroll, sit on a log stool, collect firewood) as defined by their `possible_alone_actions`.

This detailed markdown explanation provides a complete reference to all objects, constants, subitems, and available interactions present in the source code, ensuring your agent can fully utilize these elements when creating your game.
"""
        agent = Agent[GameContext](
            name="Copywriter",
            instructions=system_prompt,
            tools=[create_map],
            output_type=StoryTellerGameContext
        )
        logger.info("Agent created with system prompt and tools.")
        return {"agent": agent}

    async def process_user_input(
            self,
            user_input: str,
            conversation_history: List[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        logger.info("Processing user input through Copywriter agent.")
        agent = self.agent_data["agent"]

        # Check if this is a theme selection
        if not self.game_context.theme:
            # Extract theme after the "theme:" prefix
            theme = user_input
            self.game_context.theme = theme
            logger.info(f"Theme set in game context: {self.game_context.theme}")

        # Normal processing for non-theme messages
        try:
            result = await Runner.run(
                starting_agent=agent,
                input=user_input
            )
            logger.info(f"Runner.run completed. Result type: {type(result).__name__}")

            # Process the result
            try:
                logger.info("Adapting runner output")
                result_json = adapter.adapt_runner_output(result)
                logger.info(
                    f"Adapted result to JSON. Keys: {list(result_json.keys()) if isinstance(result_json, dict) else 'not a dict'}")
            except Exception as adapter_error:
                logger.error(f"Adapter error: {str(adapter_error)}", exc_info=True)
                # Fallback to direct output
                if hasattr(result, 'final_output'):
                    result_json = {"text": result.final_output}
                else:
                    result_json = {"text": str(result)}

            # Handle the result and store in context
            if isinstance(result_json, dict) and "error" not in result_json:
                # Check if this is a map result (from create_map)
                if "grid" in result_json and "size" in result_json:
                    # This is the direct output from create_map function
                    self.game_context.environment = result_json
                    self.game_context.entities = result_json.get("entities", [])
                    logger.info(f"Map data stored directly in context with {len(self.game_context.entities)} entities")
                else:
                    # Otherwise, this is a regular response from the agent with multiple parts
                    self.game_context.environment = result_json.get("map", {})
                    self.game_context.entities = result_json.get("entities", [])
                    self.game_context.quest = result_json.get("quest", {})
                    logger.info("Full game data stored in context")

                response = {"type": "system", "content": "Adventure Created"}
                logger.info("Formatted JSON response processed from agent.")
                return response, conversation_history
            else:
                logger.info("Result not in valid JSON format; using raw output.")
                # Check if result is an error message
                if isinstance(result_json, dict) and "error" in result_json:
                    error_msg = result_json["error"]
                    response = {"type": "error", "content": f"Error: {error_msg}"}
                else:
                    response = {"type": "text",
                                "content": str(result.final_output) if hasattr(result, 'final_output') else str(result)}
                return response, conversation_history

        except Exception as e:
            logger.error(f"Error processing user input: {e}", exc_info=True)
            # More detailed error information
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(
                f"Error during agent execution. Context: {vars(self.game_context) if hasattr(self.game_context, '__dict__') else 'no context vars'}")

            traceback.print_exc()
            response = {"type": "text", "content": f"Error: {str(e)}"}
            return response, conversation_history
