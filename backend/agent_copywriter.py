import json
import logging
import os
import traceback
from typing import Dict, Any, List, Tuple, Optional

from agents import Runner, Agent, function_tool, RunContextWrapper, TContext
from deepgram import DeepgramClient
from openai import OpenAI

from factory_game import MAP_SIZE

DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"
logging.basicConfig(level=logging.DEBUG if DEBUG_MODE else logging.INFO)
logger = logging.getLogger(__name__)
logger.debug("Debug mode enabled.")


# Define our GameContext as a subclass of AgentContext
class GameContext:
    def __init__(self, name: str = "game_context"):
        self.name = name
        self.theme: Optional[str] = None
        self.environment: Optional[Dict[str, Any]] = None
        self.entities: List[Dict[str, Any]] = []
        self.quest: Optional[Dict[str, Any]] = None

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
) -> str:
    logger.debug("Entered create_map function.")
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
        logger.debug("Imported create_game from factory_game.")

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
        logger.debug("GameFactory instance created.")
        logger.info("Exporting UI JSON from game factory...")

        ui_json = factory.export_world_ui_json()
        logger.info("UI JSON exported successfully.")

        # Save map details in context
        logger.info("Storing map details in context.")
        ctx.context.environment = {
            "map_size": MAP_SIZE,
            "map_data": ui_json
        }

        success_message = "Successfully created a new game map with theme: " + (ctx.context.theme or "default")
        message = json.dumps({
            "success_message": success_message,
            "map": ui_json
        })
        logger.info(f"Map creation completed: {message}")
        return message
    except Exception as e:
        error_message = f"Error creating map: {str(e)}"
        logger.error(error_message, exc_info=True)
        return error_message


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
        logger.debug("Initializing CopywriterAgent.")
        self.openai_key = openai_api_key
        self.voice = voice

        self.openai_client = OpenAI(api_key=openai_api_key)
        logger.debug("Initialized OpenAI client.")

        # Use the GameContext as our AgentContext
        self.game_context = GameContext(name="game_context")
        logger.debug("Game context initialized.")

        self.agent_data = self.setup_agent()
        logger.debug("Agent data setup completed.")

        try:
            self.deepgram_client = DeepgramClient(api_key=deepgram_api_key)
            logger.info("Initialized Deepgram client with explicit api_key parameter")
        except Exception as e:
            logger.error(f"Failed to initialize Deepgram client: {e}", exc_info=True)

    def setup_agent(self) -> Dict:
        logger.debug("Setting up the OpenAI agent with system prompt and tools.")
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
  "theme": "<THEME>",
  "map": { <JSON MAP FROM TOOL> },
  "entities": [
    { "name": "<ENTITY NAME>", "actions": ["<ACTION1>", "<ACTION2>"] }
  ],
  "quest": {
    "objectives": [
      "<OBJECTIVE 1>",
      "<OBJECTIVE 2>"
    ]
  },
  "gameInstructions": "..."
}

# GAME WORD
This document explains the structure of the source code for various game objects and mechanics. It outlines the objects, their properties, available actions, the factory methods used to create them, and how they integrate with the overall game world (including the board, player, and weather systems). Use this as a comprehensive reference when prompting your game-creation agent.

---

## 1. Interactive Items and Their Factories

### 1.1. Backpack
- **Class:** `Backpack` (inherits from `GameObject`)
- **Properties:**
  - `description`: A text description.
  - `max_capacity`: Maximum number of items (default is 5).
  - `contained_items`: A list of item names currently held.
  - `possible_alone_actions`: A set of actions available when the backpack is used alone.
  - **Interaction Flags:**
    - `is_movable`: `True`
    - `is_jumpable`: `False`
    - `is_usable_alone`: `True`
    - `is_wearable`: `True` (backpacks can be worn)
  - `weight`: Set to `2`
  - `usable_with`: Initially an empty set.
- **Methods:**
  - `to_dict()`: Converts the backpack into a dictionary.
- **Factory:** `BackpackFactory`
  - **Variants:** `"small"` (only variant available)
  - **Preset Data:**
    - Name: `"Small Backpack"`
    - Description: `"A small backpack that can hold a few items."`
    - Max Capacity: `5`
  - **ID Generation:** Automatically generates an ID if not provided.

---

### 1.2. Bedroll
- **Class:** `Bedroll` (inherits from `GameObject`)
- **Properties:**
  - `description`
  - `max_capacity`: `1` (one person)
  - `contained_items`: List holding people using the bedroll.
  - `possible_alone_actions`: Set initialized to include the sleep action.
- **Interaction Flags:**
  - `is_movable`: `True`
  - `is_jumpable`: `False`
  - `is_usable_alone`: `True`
  - `weight`: `2`
  - `usable_with`: Empty set.
- **Action:** Uses `ACTION_SLEEP` (string `"sleep"`)
- **Methods:**
  - `to_dict()`
- **Factory:** `BedrollFactory`
  - **Variant:** `"standard"`
  - **Preset Data:**
    - Name: `"Bedroll"`
    - Description: `"A comfortable bedroll for sleeping."`
  - **ID Generation:** Auto-generates if missing.

---

### 1.3. Campfire Pot
- **Class:** `CampfirePot` (inherits from `GameObject`)
- **Properties:**
  - `description`
  - `pot_type`: Either a tripod or a spit (default: `POT_TRIPOD`)
  - `state`: Initial state is `POT_EMPTY` (other states: cooking, burning, cooked)
  - `max_items`: Maximum of `1` item
  - `contained_items`: Items being cooked
- **Interaction Flags:**
  - `is_movable`: `True`
  - `is_jumpable`: `False`
  - `is_usable_alone`: `True`
  - `weight`: `3`
  - `usable_with`: `{CAMPFIRE_BURNING, CAMPFIRE_DYING}`
- **Possible Actions:** (determined by state)
  - If empty: `{ACTION_PLACE}`
  - If cooking or burning: `{ACTION_REMOVE}`
  - If cooked: `{ACTION_REMOVE, ACTION_EMPTY}`
- **Methods:**
  - `to_dict()`
- **Factory:** `CampfirePotFactory`
  - **Variants:** Defined in `_pot_data` for keys:
    - `POT_TRIPOD`
    - `POT_SPIT`
  - **Preset Data Example:**
    - **Tripod:**  
      - Name: `"Cooking Tripod"`
      - Description: `"A sturdy metal tripod designed to hold cooking pots over a fire."`
    - **Spit:**  
      - Name: `"Roasting Spit"`
      - Description: `"A long metal spit perfect for roasting meat over a fire."`
  - **ID Generation:** Automatically generated if not provided.

---

### 1.4. Spit Item
- **Class:** `SpitItem` (inherits from `GameObject`)
- **Properties:**
  - `description`
  - `item_type`: E.g., `SPIT_BIRD` (other options include fish or meat)
  - `state`: Starts as `SPIT_ITEM_RAW` (other states: cooking, burning, cooked)
  - `cooking_time`: Number of turns to cook (default `5`)
  - `is_edible`: `True`
- **Interaction Flags:**
  - `is_movable`: `True`
  - `is_jumpable`: `False`
  - `is_usable_alone`: `True`
  - `weight`: `1`
  - `usable_with`: `{POT_SPIT}`
- **Possible Actions:** Depending on state:
  - If raw: `{ACTION_PLACE_ON_SPIT}`
  - If cooking or burning: `{ACTION_REMOVE_FROM_SPIT}`
  - If cooked: `{ACTION_REMOVE_FROM_SPIT, ACTION_EAT}`
- **Methods:**
  - `to_dict()`
- **Factory:** `SpitItemFactory`
  - **Variants:** In `_item_data` for keys:
    - `SPIT_BIRD`
    - `SPIT_FISH`
    - `SPIT_MEAT`
  - **Preset Data Example:**
    - For `SPIT_BIRD`:  
      - Name: `"Raw Bird"`
      - Description: `"A plucked bird ready for roasting."`
      - Cooking Time: `5`
  - **ID Generation:** Handled automatically if not provided.

---

### 1.5. Campfire Spit
- **Class:** `CampfireSpit` (inherits from `GameObject`)
- **Properties:**
  - `description`
  - `quality`: E.g., `SPIT_QUALITY_BASIC` (other qualities: sturdy, reinforced)
  - `durability` and `max_durability`: Varies with quality (default 100)
  - `cooking_bonus`: Extra bonus (default `0`)
- **Interaction Flags:**
  - `is_movable`: `True`
  - `is_jumpable`: `False`
  - `is_usable_alone`: `True`
  - `weight`: `2`
  - `usable_with`: `{POT_SPIT}`
- **Methods:**
  - `to_dict()`
- **Factory:** `CampfireSpitFactory`
  - **Variants:**  
    - `SPIT_QUALITY_BASIC`:  
      - Name: `"Basic Campfire Spit"`
      - Durability: `100`, Bonus: `0`
    - `SPIT_QUALITY_STURDY`:  
      - Name: `"Sturdy Campfire Spit"`
      - Durability: `150`, Bonus: `1`
    - `SPIT_QUALITY_REINFORCED`:  
      - Name: `"Reinforced Campfire Spit"`
      - Durability: `200`, Bonus: `2`
  - **ID Generation:** Auto-generated if not provided.

---

### 1.6. Campfire
- **Class:** `Campfire` (inherits from `GameObject`)
- **Properties:**
  - `description`
  - `state`: Can be one of:
    - `CAMPFIRE_UNLIT`
    - `CAMPFIRE_BURNING`
    - `CAMPFIRE_DYING`
    - `CAMPFIRE_EXTINGUISHED`
- **Interaction Flags:**
  - `is_movable`: `False`
  - `is_jumpable`: `True`
  - `is_usable_alone`: `True`
  - `weight`: `5`
  - `usable_with`: Empty set (but can be used with items like wood or water)
- **Possible Actions:** Based on state:
  - If unlit: `{ACTION_LIGHT}`
  - If burning/dying: `{ACTION_EXTINGUISH}`
  - If extinguished: `{ACTION_LIGHT}`
- **Methods:**
  - `to_dict()`
- **Factory:** `CampfireFactory`
  - **Variants:** Based on `_campfire_data` (e.g., `"Unlit Campfire"`, `"Burning Campfire"`, etc.)
  - **ID Generation:** Provided if not specified.

---

### 1.7. Chest
- **Class:** `Chest` (inherits from `Container`)
- **Properties:**
  - `chest_type`: Identifies the type of chest.
  - `is_locked`: Boolean flag.
  - `lock_difficulty`: Difficulty level (0–10) for lock picking.
  - `durability`: Value between 0 and 100.
- **Interaction Flags:**
  - `is_movable`: `True`
  - `is_jumpable`: `False`
  - `is_usable_alone`: `True`
  - `weight`: Varies (base value around `10`)
- **Factories:**
  - **ChestFactory:** Contains a detailed `_chest_data` dictionary with many chest types such as:
    - `CHEST_BASIC_WOODEN`
    - `CHEST_FORESTWOOD`
    - `CHEST_BRONZE_BANDED`
    - `CHEST_BEASTS_MAW`
    - `CHEST_DARK_IRON`, etc.
  - **Random Chest Creation:**  
    - Function `create_chest(chest_type: str = None)` randomly selects a chest type if not specified.
    - **Contents:**  
      - Uses rarity tiers: `"wooden"`, `"silver"`, `"golden"`, `"magical"`
      - **Items:** Defined in `CHEST_ITEMS` for each tier (e.g., `"apple"`, `"health_potion"`, `"magic_wand"`, `"legendary_weapon"`, etc.)
    - **Lock Types:** Chosen from `LOCK_TYPES` based on chest rarity.

---

### 1.8. Firewood
- **Class:** `Firewood` (inherits from `GameObject`)
- **Properties:**
  - `description`
- **Interaction Flags:**
  - `is_movable`: `True`
  - `is_jumpable`: `False`
  - `is_usable_alone`: `True`
  - `is_collectable`: `True`
  - `weight`: `1`
  - `possible_alone_actions`: `{ACTION_COLLECT}` (string `"collect"`)
- **Methods:**
  - `to_dict()`
- **Factory:** `FirewoodFactory`
  - **Variant:** `"branch"`
  - **Preset Data:**
    - Name: `"Fallen Branch"`
    - Description: `"A dry branch that can be collected for firewood."`
  - **ID Generation:** Handled automatically.

---

### 1.9. Land Obstacles
**LandObstacleFactory** provides static methods to create various environmental obstacles:

- **`create_hole`:**
  - Default name: `"Hole"`
  - **Flags:**  
    - Jumpable, not movable, not collectable; weight is `0`.
- **`create_fallen_log`:**
  - Accepts a `size` parameter (`small`, `medium`, `large`)
  - **Names:** E.g., `"Small Fallen Log"`, `"Fallen Log"`, `"Massive Fallen Log"`
  - **Properties:** Adjusted weight and mobility based on size.
- **`create_tree_stump`:**
  - Accepts `height` (1–3) and sets name and weight accordingly.
- **`create_rock`:**
  - Types: `"pebble"`, `"stone"`, `"boulder"`
  - **Properties:** Vary by rock type.
- **`create_plant`:**
  - Types include: `"bush"`, `"wild-bush"`, `"leafs"`, `"soft-grass"`, `"tall-grass"`, `"dense-bush"`, `"grass"`
- **`create_chestnut_tree`:**
  - A special, non-jumpable tree.
- **`create_random_obstacle`:**
  - Randomly chooses one of the above.
- **Wrapper Function:**  
  - `create_land_obstacle(obstacle_type: str = None, **props)`  
  - Can select a specific obstacle type (`"hole"`, `"log"`, `"stump"`, `"rock"`, `"plant"`, `"tree"`) or default to random.

---

### 1.10. Log Stool
- **Class:** `LogStool` (inherits from `GameObject`)
- **Properties:**
  - `description`
- **Interaction Flags:**
  - `is_movable`: `True`
  - `is_jumpable`: `False`
  - `is_usable_alone`: `True`
  - `weight`: `3`
  - `possible_alone_actions`: `{ACTION_SIT}` (string `"sit"`)
- **Methods:**
  - `to_dict()`
- **Factory:** `LogStoolFactory`
  - **Variant:** `"squat"`
  - **Preset Data:**
    - Name: `"Squat Log"`
    - Description: `"A short, sturdy log that can be used as a stool."`
  - **ID Generation:** Auto-generated if missing.

---

### 1.11. Pot
- **Class:** `Pot` (inherits from `Container`)
- **Properties:**
  - `pot_size`: Options are `"small"`, `"medium"`, `"big"`
  - `state`: One of `POT_STATE_DEFAULT`, `POT_STATE_BREAKING`, or `POT_STATE_BROKEN`
  - `max_durability` and `current_durability`: Set based on pot size
  - `capacity`:  
    - Small: `3` items  
    - Medium: `5` items  
    - Big: `8` items
  - `weight`: Varies with pot size (5, 10, or 20)
- **Interaction Flags:**
  - `is_usable_alone`: `True`
  - `is_collectable`: `False`
- **Additional Methods:**
  - `damage(amount)`: Reduces durability and updates state (possibly to breaking or broken)
  - `add_item(item)`: Disallows adding items if the pot is broken
  - `to_dict()`
- **Factory:** `PotFactory`
  - **Preset Data:** Stored in `_pot_data` for each size
  - **Helper Function:**  
    - `create_pot(size: str = None, state: str = None)` creates a pot (choosing a random size if none is provided)

---

### 1.12. Tent
- **Class:** `Tent` (inherits from `GameObject`)
- **Properties:**
  - `description`
  - `max_capacity`: `1` (for one person)
  - `contained_items`: People sheltered inside
- **Interaction Flags:**
  - `is_movable`: `True`
  - `is_jumpable`: `False`
  - `is_usable_alone`: `True`
  - `weight`: `5`
  - **Possible Actions:** `{ACTION_ENTER, ACTION_EXIT}` (to enter or exit the tent)
- **Methods:**
  - `to_dict()`
- **Factory:** `TentFactory`
  - **Variant:** `"small"`
  - **Preset Data:**
    - Name: `"Tent"`
    - Description: `"A small tent that can shelter one person."`
  - **ID Generation:** Automatically provided if missing.

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
        )
        logger.debug("Agent created with system prompt and tools.")
        return {"agent": agent}

    async def process_user_input(
            self,
            user_input: str,
            conversation_history: List[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        logger.debug("Processing user input through Copywriter agent.")
        agent = self.agent_data["agent"]

        # Check if this is a theme selection
        if not self.game_context.theme:
            # Extract theme after the "theme:" prefix
            theme = user_input
            self.game_context.theme = theme
            logger.debug(f"Theme set in game context: {self.game_context.theme}")

        # Normal processing for non-theme messages
        try:
            result = await Runner.run(
                starting_agent=agent,
                input=user_input,
                context=self.game_context
            )
            logger.debug("Runner.run completed in CopywriterAgent.")

            try:
                result_json = json.loads(result.final_output)
                if "answers" in result_json:
                    formatted_text = "\n".join([a.get("description", "") for a in result_json.get("answers", [])])
                    response = {"type": "text", "content": formatted_text}
                    logger.debug("Formatted JSON response processed from agent.")
                    return response, conversation_history
            except json.JSONDecodeError:
                logger.debug("Result not in JSON format; using raw output.")

            response = {"type": "text", "content": result.final_output}
            logger.info("Default text response generated.")
            return response, conversation_history

        except Exception as e:
            logger.error(f"Error processing user input: {e}", exc_info=True)
            traceback.print_exc()
            response = {"type": "text", "content": f"Error: {str(e)}"}
            return response, conversation_history
