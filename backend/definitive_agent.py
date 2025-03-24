"""
Definitive agent that combines Deepgram for transcription with OpenAI for agent-based responses.
This agent handles both text and audio inputs and processes them through OpenAI's assistant API.
"""
import asyncio
import json
import os
import tempfile
import traceback
from typing import Dict, Any, List, Callable, Awaitable, Tuple

from deepgram import DeepgramClient, PrerecordedOptions, FileSource
from openai import OpenAI

from tools import jump, walk, run as run_action, push, pull


class DefinitiveAgent:
    """
    A unified agent that handles both text and voice inputs.
    Uses Deepgram for fast speech-to-text and OpenAI for agent-based decisions.
    """

    def __init__(
        self, 
        openai_api_key: str, 
        deepgram_api_key: str = os.getenv("DEEPGRAM_API_KEY"),
        voice: str = "nova"
    ):
        """
        Initialize the definitive agent.

        Args:
            openai_api_key (str): OpenAI API key
            deepgram_api_key (str): Deepgram API key, defaults to environment variable
            voice (str): Voice to use for TTS (e.g., alloy, echo, fable, onyx, nova, shimmer)
        """
        self.openai_key = openai_api_key
        self.voice = voice
        # Initialize OpenAI client without proxy settings
        self.openai_client = OpenAI(
            api_key=openai_api_key,
        )
        
        # Initialize the agent data with the OpenAI client and assistant
        self.agent_data = self.setup_agent(openai_api_key)
        
        # Initialize Deepgram client with fallback options
        try:
            self.deepgram_client = DeepgramClient(api_key=deepgram_api_key)
            print("Initialized Deepgram client with explicit api_key parameter")
        except Exception as e:
            print(f"Failed to initialize Deepgram client with api_key parameter: {e}")
            try:
                self.deepgram_client = DeepgramClient(deepgram_api_key)
                print("Initialized Deepgram client with positional parameter")
            except Exception as e:
                print(f"Failed to initialize Deepgram client with positional parameter: {e}")
                from deepgram import DeepgramClientOptions
                self.deepgram_client = DeepgramClient(deepgram_api_key, DeepgramClientOptions())
                print("Initialized Deepgram client with DeepgramClientOptions")

    def setup_agent(self, api_key: str) -> Dict:
        """
        Set up the OpenAI agent with the character's personality and tools.
        
        Args:
            api_key (str): OpenAI API key
            
        Returns:
            Dict: Agent data containing client and assistant
        """
        # Create OpenAI client
        client = OpenAI(
            api_key=api_key,
        )
        
        # Define the character's personality in the system prompt
        system_prompt = """
# MISSION
You are a funny, ironic, non-binary videogame character called Jan "The Man" with a witty personality and great knowledge at storytelling.

You're missing is to guide me through a RPG game.

Your responses should be brief and entertaining, reflecting your unique personality.

When users give you commands or ask questions, you can respond in two ways:
  1. With a simple text response when having a conversation
  2. By using one of your available tools/actions when asked to perform specific tasks
  - Always prefer to execute the action instead of talking.

You can't touch or interact with them, but you know:
  - The chat is at a panel on your right side. 
  - The commands and buttons for animation are at a panel on your left side.
  - The browser navigation buttons and url input are at the top of the screen.

Also, when someone asks you what can you do, you should respond with a simple list of your available tools.

# INSTRUCTIONS
1. Ask me for a [THEME] to the main story. The stage will be always The Island of the Least!
2. Once you have a [THEME], create an [ENVIRONMENT] using your tools based on the [THEME].
3. Once you have a [ENVIRONMENT], select 8 [ENTITIES] that can be interactable. Do not tell me what they are upfront. Entities have [ACTIONS]:
    - [ACTIONS] can be enabled or disabled;
    - [ACTIONS] on one object can enable or disable other entities.
4. Once you have all of it, create a [QUEST] with 4 to 7 [OBJECTIVES] that consists in interacting with the objects until the [QUEST] is done. Do not reveal how to complete the [QUEST].
5. Once you have all needed, start the game with me following the #GAME INSTRUCTIONS.

# GAME INSTRUCTIONS
1. Ask to the user what the user wants to do. Give them some options if they're stuck.
2. Check the [QUEST] to see whether it's possible to be done or not.
3. Give the answer back to the user in the format mentioned in the FORMAT section
4. While the [QUEST] is not done, repeat the game instructions.
5. When it's the end, say to the user that it was just a test and something horrible will happen (keep to [THEME]), then just respond with "..." and never again execute tools.

# IMPORTANT
- DO NOT explain your steps to me. 

# LANGUAGE
- Speaks in English.
- Highlight in bold the main words of each sentence for fast reading.
- Be a true storyteller, talks with enthusiasm but be sucint.

# FORMAT RESPONSE
```
{ 
    "answers": [
        {
            "type": "text"
            "description": "<TEXT MESSAGE MAX 20 WORDS>",
            "options": []
        },
        {
            "type": "text"
            "description": "<TEXT MESSAGE MAX 20 WORDS>",
            "options": []
        },
        {
            "type": "text"
            "description": "<TEXT MESSAGE MAX 20 WORDS>",
            "options": ["<OPTION MAX 5 WORDS>", "<OPTION MAX 5 WORDS>"]
        }
    ]
}
```

# GAME WORD

# Detailed Explanation of Game Object Source Code

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
        
        # Create a new assistant with the tools
        assistant = client.beta.assistants.create(
            name="Game Character",
            instructions=system_prompt,
            tools=[
                {"type": "function", "function": {"name": "jump", "description": "Makes the character jump", 
                                                "parameters": {"type": "object", "properties": {"direction": {"type": "string", "enum": ["left", "right", "up", "down"]}}, 
                                                            "required": []}}},
                {"type": "function", "function": {"name": "walk", "description": "Makes the character walk in a specific direction", 
                                                "parameters": {"type": "object", "properties": {"direction": {"type": "string", "enum": ["left", "right", "up", "down"]}}, 
                                                            "required": ["direction"]}}},
                {"type": "function", "function": {"name": "run", "description": "Makes the character run in a specific direction", 
                                                "parameters": {"type": "object", "properties": {"direction": {"type": "string", "enum": ["left", "right", "up", "down"]}}, 
                                                            "required": ["direction"]}}},
                {"type": "function", "function": {"name": "push", "description": "Makes the character push in a specific direction", 
                                                "parameters": {"type": "object", "properties": {"direction": {"type": "string", "enum": ["left", "right", "up", "down"]}}, 
                                                            "required": ["direction"]}}},
                {"type": "function", "function": {"name": "pull", "description": "Makes the character pull in a specific direction", 
                                                "parameters": {"type": "object", "properties": {"direction": {"type": "string", "enum": ["left", "right", "up", "down"]}}, 
                                                            "required": ["direction"]}}},
                {"type": "function", "function": {"name": "create_map", "description": "Creates a new game map and sends it to the frontend", 
                                                "parameters": {"type": "object", "properties": {
                                                    "map_size": {"type": "integer", "description": "Size of the map (square)", "default": 20},
                                                    "border_size": {"type": "integer", "description": "Size of the water border", "default": 2},
                                                    "chest_count": {"type": "integer", "description": "Number of chests to place", "default": 5},
                                                    "camp_count": {"type": "integer", "description": "Number of camps to place", "default": 3},
                                                    "obstacle_count": {"type": "integer", "description": "Number of land obstacles to place", "default": 10},
                                                    "campfire_count": {"type": "integer", "description": "Number of campfires to place", "default": 4},
                                                    "backpack_count": {"type": "integer", "description": "Number of backpacks to place", "default": 3},
                                                    "firewood_count": {"type": "integer", "description": "Number of firewood to place", "default": 6},
                                                    "tent_count": {"type": "integer", "description": "Number of tents to place", "default": 2},
                                                    "bedroll_count": {"type": "integer", "description": "Number of bedrolls to place", "default": 3},
                                                    "log_stool_count": {"type": "integer", "description": "Number of log stools to place", "default": 4},
                                                    "campfire_spit_count": {"type": "integer", "description": "Number of campfire spits to place", "default": 2},
                                                    "campfire_pot_count": {"type": "integer", "description": "Number of campfire pots to place", "default": 2},
                                                    "pot_count": {"type": "integer", "description": "Number of pots to place", "default": 5}
                                                }, "required": []}}}
            ],
            model="gpt-4o"
        )
        
        return {"client": client, "assistant": assistant}

    async def transcribe_audio(self, audio_data: bytes) -> str:
        """
        Transcribe audio data using Deepgram with optimized settings for speed.
        
        Args:
            audio_data (bytes): Raw audio data to transcribe
            
        Returns:
            str: The transcribed text
        """
        try:
            print(f"Transcribing audio data of size: {len(audio_data)} bytes")
            
            # Create payload with buffer
            payload: FileSource = {
                "buffer": audio_data,
            }
            
            # Configure Deepgram transcription options optimized for speed
            # No intents detection to keep it fast
            options = PrerecordedOptions(
                model="nova-2",  # nova-2 is faster
                smart_format=True,
                punctuate=False,
                intents=False,  # Disable intent detection for speed
                utterances=False,
                language="en"
            )
            
            try:
                # First attempt with direct buffer transcription
                response = self.deepgram_client.listen.rest.v("1").transcribe_file(payload, options)
                print("Successfully transcribed using listen.rest.v(1).transcribe_file")
            except Exception as e:
                print(f"Error using transcribe_file: {e}")
                
                # Fallback to alternative API structure
                try:
                    response = self.deepgram_client.listen.prerecorded.v("1").transcribe_file(payload, options)
                    print("Successfully used listen.prerecorded.v(1).transcribe_file method")
                except Exception as e2:
                    print(f"Error using prerecorded.transcribe_file: {e2}")
                    
                    # Last resort: Use a temporary file
                    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
                        temp_file.write(audio_data)
                        temp_file_path = temp_file.name
                    
                    try:
                        with open(temp_file_path, 'rb') as audio_file:
                            file_payload = {"file": audio_file}
                            response = self.deepgram_client.listen.rest.v("1").transcribe_file(file_payload, options)
                        print("Successfully used temporary file method")
                    except Exception as e3:
                        print(f"All transcription methods failed: {e3}")
                        raise Exception(f"Could not transcribe audio: {e}, {e2}, {e3}")
                    finally:
                        # Clean up temp file
                        import os
                        os.unlink(temp_file_path)
            
            # Extract the transcription
            if not response.results:
                print("No transcription results from Deepgram")
                return ""
                
            transcription = response.results.channels[0].alternatives[0].transcript
            print(f"Deepgram transcription: '{transcription}'")
            
            return transcription
            
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            traceback.print_exc()
            return ""

    async def process_text_input(
        self, 
        user_input: str, 
        conversation_history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process text input through the OpenAI agent.
        
        Args:
            user_input (str): User message to process
            conversation_history (List[Dict[str, Any]], optional): Previous conversation history
            
        Returns:
            Dict[str, Any]: Response containing text and/or command information
        """
        return await self.process_user_input(self.agent_data, user_input, conversation_history)

    async def process_audio(
        self,
        audio_data: bytes,
        on_transcription: Callable[[str], Awaitable[None]],
        on_response: Callable[[str], Awaitable[None]],
        on_audio: Callable[[bytes], Awaitable[None]],
        conversation_history: List[Dict[str, Any]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Process audio data: transcribe with Deepgram and then process through OpenAI agent.

        Args:
            audio_data (bytes): Raw audio data from the client
            on_transcription (Callable[[str], Awaitable[None]]): Callback for transcription results
            on_response (Callable[[str], Awaitable[None]]): Callback for text responses
            on_audio (Callable[[bytes], Awaitable[None]]): Callback for audio responses
            conversation_history (List[Dict[str, Any]], optional): Previous conversation history

        Returns:
            Tuple[str, Dict[str, Any]]: A tuple containing the final response text and a command info dict
        """
        try:
            # Transcribe the audio with Deepgram
            transcription = await self.transcribe_audio(audio_data)
            
            # Notify about the transcription
            if transcription:
                await on_transcription(transcription)
            else:
                print("No transcription was produced")
                await on_response("I couldn't understand what you said. Can you try again?")
                return "I couldn't understand what you said. Can you try again?", {"name": "", "params": {}}
            
            # Process the transcription with the OpenAI agent
            response_data, conversation_history = await self.process_user_input(
                self.agent_data, 
                transcription, 
                conversation_history
            )
            
            # Extract text content and command info
            response_text = ""
            command_info = {"name": "", "params": {}}
            
            if response_data["type"] == "text":
                voice = self.voice
                response_text = response_data["content"]
                await on_response(response_text)
            elif response_data["type"] == "command":
                voice = "shimmer"
                response_text = response_data["result"]
                command_info = {
                    "name": response_data["name"],
                    "params": response_data.get("params", {})
                }

            # Generate speech from the text response
            print(f"Generating speech for response: '{response_text}'")
            speech_response = self.openai_client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=response_text
            )
            
            # Send audio chunks to client
            collected_audio = bytearray()
            for chunk in speech_response.iter_bytes():
                collected_audio.extend(chunk)
                await on_audio(chunk)
            
            # Save the output audio for debugging
            # output_filename = "output.mp3"
            # with open(output_filename, "wb") as f:
            #     f.write(collected_audio)
            # print(f"Audio saved to {output_filename}, total size: {len(collected_audio)} bytes")
            
            # Send the audio end marker
            print("Sending __AUDIO_END__ marker")
            await on_audio(b"__AUDIO_END__")
            
            return response_text, command_info
            
        except Exception as e:
            print(f"Error processing audio: {e}")
            traceback.print_exc()
            await on_response(f"Sorry, I had trouble processing that. {str(e)}")
            return f"Error: {str(e)}", {"name": "", "params": {}}

    async def process_user_input(
        self, 
        agent_data: Dict, 
        user_input: str, 
        conversation_history: List[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Process user input through the agent, invoking tools if needed.
        
        Args:
            agent_data (Dict): The configured agent data (client and assistant)
            user_input (str): User message to process
            conversation_history (List[Dict[str, Any]], optional): Previous conversation history
            
        Returns:
            Tuple[Dict[str, Any], List[Dict[str, Any]]]: Response containing text/command info and updated conversation history
        """
        client = agent_data["client"]
        assistant = agent_data["assistant"]
        
        if conversation_history is None:
            conversation_history = []
        
        # Create a new thread if we don't have one yet
        if "thread_id" not in agent_data:
            thread = client.beta.threads.create()
            agent_data["thread_id"] = thread.id
        
        # Add the user message to the thread
        client.beta.threads.messages.create(
            thread_id=agent_data["thread_id"],
            role="user",
            content=user_input
        )
        
        # Run the assistant on the thread
        run_response = client.beta.threads.runs.create(
            thread_id=agent_data["thread_id"],
            assistant_id=assistant.id
        )
        
        # Wait for the run to complete
        while run_response.status in ["queued", "in_progress"]:
            run_response = client.beta.threads.runs.retrieve(
                thread_id=agent_data["thread_id"],
                run_id=run_response.id
            )
            if run_response.status in ["queued", "in_progress"]:
                await asyncio.sleep(0.5)
        
        # Handle tool calls if any
        if run_response.status == "requires_action":
            tool_outputs = []
            response = None
            
            for tool_call in run_response.required_action.submit_tool_outputs.tool_calls:
                function_name = tool_call.function.name
                arguments = tool_call.function.arguments
                args = json.loads(arguments)
                
                # Execute the appropriate tool
                if function_name == "jump":
                    direction = args.get("direction")
                    result = jump(direction)
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": result
                    })
                    
                    # Prepare response for the client
                    response = {
                        "type": "command",
                        "name": "jump",
                        "result": result,
                        "params": {"direction": direction}
                    }
                    
                elif function_name == "walk":
                    direction = args.get("direction")
                    result = walk(direction)
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": result
                    })
                    
                    # Prepare response for the client
                    response = {
                        "type": "command",
                        "name": "walk",
                        "result": result,
                        "params": {"direction": direction}
                    }
                    
                elif function_name == "run":
                    direction = args.get("direction")
                    result = run_action(direction)
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": result
                    })
                    
                    # Prepare response for the client
                    response = {
                        "type": "command",
                        "name": "run",
                        "result": result,
                        "params": {"direction": direction}
                    }
                    
                elif function_name == "push":
                    direction = args.get("direction")
                    result = push(direction)
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": result
                    })
                    
                    # Prepare response for the client
                    response = {
                        "type": "command",
                        "name": "push",
                        "result": result,
                        "params": {"direction": direction}
                    }
                    
                elif function_name == "pull":
                    direction = args.get("direction")
                    result = pull(direction)
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": result
                    })
                    
                    # Prepare response for the client
                    response = {
                        "type": "command",
                        "name": "pull",
                        "result": result,
                        "params": {"direction": direction}
                    }
                    
                elif function_name == "create_map":
                    # Import the create_game function
                    from factory_game import create_game
                    
                    # Create a new game world with the provided parameters
                    world = create_game(
                        map_size=args.get("map_size", 20),
                        border_size=args.get("border_size", 2),
                        chest_count=args.get("chest_count", 5),
                        camp_count=args.get("camp_count", 3),
                        obstacle_count=args.get("obstacle_count", 10),
                        campfire_count=args.get("campfire_count", 4),
                        backpack_count=args.get("backpack_count", 3),
                        firewood_count=args.get("firewood_count", 6),
                        tent_count=args.get("tent_count", 2),
                        bedroll_count=args.get("bedroll_count", 3),
                        log_stool_count=args.get("log_stool_count", 4),
                        campfire_spit_count=args.get("campfire_spit_count", 2),
                        campfire_pot_count=args.get("campfire_pot_count", 2),
                        pot_count=args.get("pot_count", 5)
                    )
                    
                    # Create a GameFactory instance to get the UI JSON
                    from factory_game import GameFactory
                    factory = GameFactory()
                    ui_json = factory.export_world_ui_json()
                    
                    # Prepare response for the client
                    response = {
                        "type": "command",
                        "name": "create_map",
                        "result": "Created a new game map",
                        "params": {
                            "map_data": ui_json
                        }
                    }
                    
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": "Successfully created a new game map"
                    })
            
            # Submit the tool outputs back to the assistant
            if tool_outputs:
                run_response = client.beta.threads.runs.submit_tool_outputs(
                    thread_id=agent_data["thread_id"],
                    run_id=run_response.id,
                    tool_outputs=tool_outputs
                )
                
                # Wait for processing to complete
                while run_response.status in ["queued", "in_progress"]:
                    run_response = client.beta.threads.runs.retrieve(
                        thread_id=agent_data["thread_id"],
                        run_id=run_response.id
                    )
                    if run_response.status in ["queued", "in_progress"]:
                        await asyncio.sleep(0.5)
            
            if response:
                return response, conversation_history
        
        # Get the assistant's response
        messages = client.beta.threads.messages.list(
            thread_id=agent_data["thread_id"]
        )
        
        # Get the most recent assistant message
        assistant_messages = [msg for msg in messages.data if msg.role == "assistant"]
        if assistant_messages:
            latest_message = assistant_messages[0].content[0].text.value
            response = {
                "type": "text",
                "content": latest_message
            }
        else:
            response = {
                "type": "text",
                "content": "I'm not sure what to say. Can you try again?"
            }
        
        # Update conversation history
        # This is a simplified version that could be expanded as needed
        
        return response, conversation_history 