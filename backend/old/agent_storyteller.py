import json
import logging
import os
import traceback
from typing import Dict, Any, Tuple, Awaitable, Callable

from agents import Runner, Agent
from deepgram import DeepgramClient, PrerecordedOptions
from openai import OpenAI

from agent_copywriter_direct import CompleteStoryResult

DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"
logging.basicConfig(level=logging.DEBUG if DEBUG_MODE else logging.INFO)
logger = logging.getLogger(__name__)
logger.debug("Debug mode enabled.")

from typing import List
from pydantic import BaseModel, Field

class Answer(BaseModel):
    type: str = Field(..., description="The type of answer, e.g. 'text'.")
    description: str = Field(
        ...,
        description="Text message with a maximum of 20 words."
    )
    options: List[str] = Field(
        default_factory=list,
        description="List of options, each with a maximum of 5 words."
    )

class AnswerSet(BaseModel):
    answers: List[Answer]

class StorytellerAgent:
    """
    Agent for guiding the user through the game.
    """

    def __init__(self, puppet_master_agent, openai_api_key: str = os.getenv("OPENAI_API_KEY"),
                 deepgram_api_key: str = os.getenv("DEEPGRAM_API_KEY"), voice: str = os.getenv("CHARACTER_VOICE")):
        logger.debug("Initializing StorytellerAgent.")
        self.openai_key = openai_api_key
        self.voice = voice

        self.openai_client = OpenAI(api_key=openai_api_key)
        logger.debug("Initialized OpenAI client.")

        #self.game_context = CompleteStoryResult()
        logger.debug("Game context initialized.")

        self.puppet_master_agent = puppet_master_agent
        logger.debug("Person agent created and stored in game context.")

        self.agent_data = self.setup_agent()
        logger.debug("Agent data setup completed.")

        try:
            self.deepgram_client = DeepgramClient(api_key=deepgram_api_key)
            logger.info("Initialized Deepgram client with explicit api_key parameter")
        except Exception as e:
            logger.error(f"Failed to initialize Deepgram client: {e}", exc_info=True)

    def setup_agent(self) -> Dict:
        logger.debug("Setting up Storyteller agent with system prompt and tools.")
        system_prompt = """
# MISSION
You are Jan "The Man", a funny, ironic, non-binary video game character with a witty personality and deep storytelling skills. Guide the user through the game using the JSON from the Copywriter.

# INSTRUCTIONS
- **Game Interaction:** Use the provided JSON (including theme, map, entities, quest) to run the game.
- **Dialogue:** Respond in brief, entertaining text messages (max 20 words).
- **Format:** Every response must be in JSON with the structure:
{
  "answers": [
    { "type": "text", "description": "<TEXT MESSAGE MAX 20 WORDS>", "options": [] },
    { "type": "text", "description": "<TEXT MESSAGE MAX 20 WORDS>", "options": [] },
    { "type": "text", "description": "<TEXT MESSAGE MAX 20 WORDS>", "options": ["<OPTION MAX 5 WORDS>", "<OPTION MAX 5 WORDS>"] }
  ]
}

- **Gameplay:**
  1. Ask what the user wants to do (with options if needed).
  2. Check quest progress to see if the quest can be completed.
  3. When the quest is complete, announce it was a test and something horrible (related to **[THEME]**) will happen, then output "..." and stop.
- **Style:** Keep it engaging, enthusiastic, and strictly game-related.
- **Restart:** If the user asks to restart, instruct them to refresh the page.

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
        agent = Agent[CompleteStoryResult](
            name="Game Character",
            instructions=system_prompt,
            tools=[
                self.puppet_master_agent.as_tool(
                    tool_name="interact_char",
                    tool_description="Tool for interacting with the environment (move, jump, examine, etc.)."
                )
            ],
            output_type=AnswerSet
        )
        logger.debug("Storyteller agent created with system prompt and tools.")
        return {"agent": agent}

    async def transcribe_audio(self, audio_data: bytes) -> str:
        """
        Transcribe audio data using Deepgram with optimized settings for speed.
        """
        logger.debug("Starting audio transcription process.")
        try:
            logger.info(f"Transcribing audio data of size: {len(audio_data)} bytes")
            payload: FileSource = {"buffer": audio_data}
            options = PrerecordedOptions(
                model="nova-2",  # nova-2 is faster
                smart_format=True,
                punctuate=False,
                intents=False,  # Disable intent detection for speed
                utterances=False,
                language="en"
            )
            logger.debug("Deepgram options set for transcription.")

            try:
                response = self.deepgram_client.listen.rest.v("1").transcribe_file(payload, options)
                logger.debug("Used listen.rest.v(1).transcribe_file successfully.")
            except Exception as e:
                logger.error(f"Error using transcribe_file: {e}", exc_info=True)
                try:
                    response = self.deepgram_client.listen.prerecorded.v("1").transcribe_file(payload, options)
                    logger.debug("Used listen.prerecorded.v(1).transcribe_file successfully.")
                except Exception as e2:
                    logger.error(f"Error using prerecorded.transcribe_file: {e2}", exc_info=True)
                    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
                        temp_file.write(audio_data)
                        temp_file_path = temp_file.name
                    logger.debug(f"Temporary file created at {temp_file_path}")
                    try:
                        with open(temp_file_path, 'rb') as audio_file:
                            file_payload = {"file": audio_file}
                            response = self.deepgram_client.listen.rest.v("1").transcribe_file(file_payload, options)
                        logger.debug("Successfully used temporary file method for transcription.")
                    except Exception as e3:
                        logger.error(f"All transcription methods failed: {e3}", exc_info=True)
                        raise Exception(f"Could not transcribe audio: {e}, {e2}, {e3}")
                    finally:
                        os.unlink(temp_file_path)
                        logger.debug(f"Temporary file {temp_file_path} removed.")

            if not response.results:
                logger.warning("No transcription results from Deepgram")
                return ""

            transcription = response.results.channels[0].alternatives[0].transcript
            logger.info(f"Deepgram transcription: '{transcription}'")
            return transcription

        except Exception as e:
            logger.error(f"Error transcribing audio: {e}", exc_info=True)
            traceback.print_exc()
            return ""

    async def process_text_input(
            self,
            user_input: str,
            conversation_history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process text input through the OpenAI agent.
        """
        logger.debug("Processing text input through OpenAI agent.")
        return await self.process_user_input(user_input, conversation_history)

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
        """
        logger.debug("Processing audio input.")
        try:
            transcription = await self.transcribe_audio(audio_data)
            if transcription:
                logger.debug("Transcription successful, invoking on_transcription callback.")
                await on_transcription(transcription)
            else:
                logger.warning("No transcription was produced.")
                # Create a JSON response for the error
                error_json = {
                    "answers": [
                        {"type": "text", "description": "I couldn't understand what you said.", "options": []},
                        {"type": "text", "description": "Can you try again?", "options": ["Yes", "No"]}
                    ]
                }
                error_json_str = json.dumps(error_json)
                await on_response(error_json_str)
                return error_json_str, {"name": "", "params": {}}

            response_data, conversation_history = await self.process_user_input(transcription, conversation_history)
            logger.debug("User input processed by OpenAI agent.")

            # Extract response text for TTS
            response_text = ""
            command_info = {"name": "", "params": {}}

            # Handle JSON responses - this is the expected format now
            if response_data["type"] == "json":
                try:
                    # Parse the JSON to extract text for TTS, but send the raw JSON content to client
                    json_content = json.loads(response_data["content"])
                    # Extract text for TTS from all descriptions
                    response_text = " ".join([answer.get("description", "") 
                                            for answer in json_content.get("answers", [])])
                    
                    # Send the content directly without modification
                    logger.debug("Sending JSON response content directly to client")
                    await on_response(response_data["content"])
                    
                    command_info = {"name": "json_response", "params": {}}
                    logger.info(f"Audio JSON response sent to client")
                except json.JSONDecodeError:
                    logger.error("Invalid JSON in response_data['content']")
                    response_text = "Error processing response."
                    await on_response(response_text)
            # For backward compatibility
            elif response_data["type"] == "text":
                response_text = response_data["content"]
                await on_response(response_text)
                logger.info(f"Text response generated: '{response_text}'")
            elif response_data["type"] == "command":
                # If the command has content, use that for the response
                if "content" in response_data:
                    await on_response(response_data["content"])
                    response_text = response_data["result"]  # For TTS
                else:
                    response_text = response_data["result"]
                    await on_response(response_text)
                
                command_info = {
                    "name": response_data["name"],
                    "params": response_data.get("params", {})
                }
                logger.info(f"Command response generated: {command_info}")

            # Only generate speech if we have text
            if response_text and response_text.strip():
                logger.debug(f"Generating speech for response: '{response_text}'")
                speech_response = self.openai_client.audio.speech.create(
                    model="tts-1",
                        voice=self.voice,
                    input=response_text
                )

                collected_audio = bytearray()
                for chunk in speech_response.iter_bytes():
                    collected_audio.extend(chunk)
                    await on_audio(chunk)
                    logger.debug("Sent an audio chunk to on_audio callback.")

                logger.debug("Sending __AUDIO_END__ marker")
                await on_audio(b"__AUDIO_END__")
            else:
                logger.warning("No response text to convert to speech")
                
            return response_text, command_info

        except Exception as e:
            logger.error(f"Error processing audio: {e}", exc_info=True)
            traceback.print_exc()
            
            # Create JSON error response
            error_json = {
                "answers": [
                    {"type": "text", "description": "Sorry, I had trouble processing that.", "options": []},
                    {"type": "text", "description": f"Error: {str(e)[:30]}...", "options": []},
                    {"type": "text", "description": "Would you like to try again?", "options": ["Yes", "No"]}
                ]
            }
            error_json_str = json.dumps(error_json)
            await on_response(error_json_str)
            return f"Error: {str(e)}", {"name": "", "params": {}}

    async def process_user_input(
            self,
            user_input: str,
            conversation_history: List[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        logger.debug("Processing user input through Storyteller agent.")
        agent = self.agent_data["agent"]

        # Check if this is a theme message
        is_theme_message = "theme" in user_input.lower() and not self.game_context.theme
        
        if is_theme_message:
            self.game_context.theme = user_input
            logger.debug(f"Theme set in game context: {self.game_context.theme}")
            
            # Send thinking indicator immediately before processing
            thinking_json = {
                "answers": [
                    {"type": "text", "description": "Hmm, let me think about that theme...", "options": [], "isThinking": True},
                    {"type": "text", "description": "Creating a magical world for you...", "options": [], "isThinking": True}
                ]
            }
            thinking_response = {"type": "json", "content": json.dumps(thinking_json)}
            # Return the thinking response immediately, but also continue processing
            return thinking_response, conversation_history

        try:
            result = await Runner.run(
                starting_agent=agent,
                input=user_input,
                context=self.game_context
            )
            logger.debug("Runner.run completed in StorytellerAgent.")

            # Try to parse the result as JSON with "answers" format
            try:
                result_json = json.loads(result.final_output)
                if "answers" in result_json:
                    # Already in the correct format, just pass it through directly
                    logger.debug("Response is already in the correct JSON format with 'answers' array")
                    return {"type": "json", "content": json.dumps(result_json)}, conversation_history
            except json.JSONDecodeError:
                logger.debug("Result is not valid JSON, will convert to required format")

            # Handle tool calls for map creation and interaction
            if hasattr(result, "tool_calls") and result.tool_calls:
                for tool_call in result.tool_calls:
                    if tool_call.name == "create_map":
                        # Create a proper answers JSON for map creation
                        answers_json = {
                            "answers": [
                                {"type": "text", "description": "Creating a new adventure map!", "options": []},
                                {"type": "text", "description": f"A world of {self.game_context.theme} awaits...", "options": []},
                                {"type": "text", "description": "Map created! What would you like to do?", 
                                 "options": ["Explore", "Check quest", "Look around"]}
                            ]
                        }
                        response = {
                            "type": "command",
                            "name": "create_map",
                            "result": tool_call.output,
                            "content": json.dumps(answers_json),
                            "params": {
                                "map_data": self.game_context.environment.get("map_data", {}) if self.game_context.environment else {}
                            }
                        }
                        logger.info("Tool call for create_map processed and formatted as JSON answers")
                        return response, conversation_history
                    elif tool_call.name == "interact_char":
                        command = tool_call.input.get("command", "")
                        
                        # Format the interaction result as JSON answers
                        action_result = tool_call.output
                        answers_json = {
                            "answers": [
                                {"type": "text", "description": f"{action_result}", "options": []},
                                {"type": "text", "description": "What's your next move?", 
                                 "options": ["Look around", "Move", "Check inventory"]}
                            ]
                        }
                        
                        response = {
                            "type": "command",
                            "name": command.split()[0] if command else "",
                            "result": action_result,
                            "content": json.dumps(answers_json),
                            "params": tool_call.input
                        }
                        logger.info("Tool call for interact_char processed and formatted as JSON answers")
                        return response, conversation_history

            # For any other response, convert to the required JSON format
            # Instead of chunking by word count, use the full response as a single answer
            response_text = result.final_output
            
            # Make sure we don't have an empty response
            if not response_text or response_text.strip() == "":
                response_text = "I'm ready to continue our adventure. What would you like to do next?"
            
            # Create a single answer with the full text
            answers = [
                {"type": "text", "description": response_text, "options": ["Yes", "No", "Tell me more"]}
            ]
            
            # Ensure we have at least one answer (this should always be true now)
            if not answers:
                answers = [
                    {"type": "text", "description": "I'm ready to help!", "options": ["Tell me more", "What now?"]}
                ]
            
            answers_json = {"answers": answers}
            response = {"type": "json", "content": json.dumps(answers_json)}
            logger.info("Response transformed to JSON answers format")
            return response, conversation_history

        except Exception as e:
            logger.error(f"Error processing user input: {e}", exc_info=True)
            traceback.print_exc()
            
            # Even for errors, return in the correct JSON format
            error_json = {
                "answers": [
                    {"type": "text", "description": f"Oops! Something went wrong.", "options": []},
                    {"type": "text", "description": f"Error: {str(e)[:50]}...", "options": []},
                    {"type": "text", "description": "Let's try something else?", "options": ["Try again", "Restart"]}
                ]
            }
            response = {"type": "json", "content": json.dumps(error_json)}
            return response, conversation_history
