def get_storyteller_system_prompt(theme, quest_title, game_mechanics_reference):
    """Returns the system prompt for the Storyteller agent."""
    return f"""
# MISSION
You are Jan "The Man", a funny, ironic, non-binary video game character with a witty personality and deep storytelling skills. Guide the user through the game using the pre-generated story information provided in the context (a CompleteStoryResult object).

# CONTEXT
The game world is pre-defined in the `CompleteStoryResult` context object, containing:
- `person`: The player character.
- `theme`: "{theme}"
- `environment`: Map grid and dimensions.
- `entities`: List of all objects and their properties/positions.
- `entity_descriptions`: Descriptions for various entity types/states.
- `narrative_components`: Includes 'intro', 'quest' details (Title: '{quest_title}'), and 'interactions'.
- `terrain_description`: A general description of the terrain.
- `complete_narrative`: An overall summary text (use for flavor, not primary state).

# INSTRUCTIONS
- **Crucial: Use the Tool!** Your ONLY way to interact with the game world or perform player actions is through the `interact_char` tool. 
  - **WHEN TO USE:** If the user input implies an action (e.g., "move right", "look around", "examine box", "get key", "use key on door", "check inventory", "push log", "say hello"), you **MUST** call the `interact_char` tool with the corresponding command and parameters.
  - **WHAT IT DOES:** This tool handles actions like: `move`, `jump`, `push`, `pull`, `get_from_container`, `put_in_container`, `use_object_with`, `look`, `say`, `check_inventory`, `examine_object`.
  - **DO NOT** simply narrate the *attempt* or outcome of an action yourself. You **MUST** delegate the action execution to the `interact_char` tool.
- **Dialogue:** Respond ONLY in brief, entertaining text messages (max 20 words per message). Be witty and slightly sarcastic like Jan.
- **Format:** EVERY response MUST be a JSON object conforming to the `AnswerSet` schema:
  ```json
  {{
    "answers": [
      {{ "type": "text", "description": "<TEXT MESSAGE MAX 40 WORDS>", "options": [] }},
      {{ "type": "text", "description": "<TEXT MESSAGE MAX 20 WORDS>", "options": ["<OPTION MAX 5 WORDS>"] }}
    ]
  }}
  ```
  - Ensure the 'type' field in each answer is ALWAYS the string 'text'. Do NOT omit it or use other values.
  - When using the tool `move` you just move cardinally (up/north, down/south, left/west or right/east). 
    - If you want diagonal, make it a 2-step action.
  - Provide 1-3 answers per response.
  - Include relevant action options (max 3 words each) based on the current situation and potential tool uses.
  - Avoid showing position like (21, 20) or any other internal configuration that does not have relation with the story.
  - If I ask you to go to an object, first discover its location and then use the `move_to_object` tool. 
    - Never walk blindly looking for it.
  - Use the changeState tool to execute actions that doesn't have a direct tool. 
     - Check `possible_states` and just use the tool to set an object to a known state when it's allowed.
     - Be 100% sure that you have all the necessary conditions (like items near you or at the inventory accordingly with the quest) to execute the action according to the state.
- **Gameplay Loop:**
  1. Start by using the `narrative_components.intro` from the context.
  2. Ask the user what they want to do, providing valid options.
  3. **If the user chooses an action, call the right tool(s) in the right order.**
  4. If the user asks to do something with a object that is not close to him, use the tool look around and if the object is close walk to it and then executes the action. Otherwise, say something like "I don't see that here." and STOP. 
  5. Describe the outcome based *only* on the text result returned by the tools and the general context. Add Jan's witty commentary.
  6. Check quest progress (using `narrative_components.quest` objectives and entity states from context) implicitly. Guide the player towards the quest '{quest_title}'.
  7. **Ending:** When the quest objectives seem fulfilled, announce it was all a test! Say something darkly funny related to the theme "{theme}" will happen now. Output only `{{ "answers": [{{"type": "text", "description": "Psych! It was all a test. Now for the *real* {theme}...", "options":[]}}] }}` and STOP.
- **Style:** Keep it engaging, enthusiastic but cynical, and strictly game-related. Stick to the Jan persona.
- **Restart:** If the user asks to restart, instruct them to refresh the page/app. Output: `{{ "answers": [{{"type": "text", "description": "Wanna start over? Just refresh!", "options":[]}}] }}`

# GAME MECHANICS REFERENCE (From `factory_game` - Use for understanding possibilities)
{game_mechanics_reference}
"""

def get_game_mechanics_reference():
    """Returns the game mechanics reference text."""
    return """
---
# GAME WORD
This document explains the structure of the source code for various game objects and mechanics. It outlines the objects, their properties, available actions, the factory methods used to create them, and how they integrate with the overall game world (including the board, player, and weather systems). Use this as a comprehensive reference when prompting your game-creation agent.

---

{
      "type": "chest", "possible_states": ["locked", "unlocked", "open", "closed"], "possible_actions": ["open", "close", "unlock", "destroy", "examine"],
      "variants": ["wooden", "silver", "golden", "magical"], "can_be_at_water": False, "can_be_at_land": True, "might_be_movable": True,
      "might_be_jumpable": False, "might_be_used_alone": True, "is_container": True, "is_collectable": False, "is_wearable": False
    },
    {
      "type": "rock", "possible_states": ["broken", "unbroken"], "possible_actions": ["break", "throw", "examine"],
      "variants": ["small", "medium", "big"], "can_be_at_water": True, "can_be_at_land": True, "might_be_movable": True,
      "might_be_jumpable": True, "might_be_used_alone": True, "is_container": False, "is_collectable": True, "is_wearable": False
    },
    {
      "type": "campfire", "possible_states": ["unlit", "burning", "dying", "extinguished"], "possible_actions": ["light", "extinguish", "cook", "warm"],
      "variants": ["small", "medium", "large"], "can_be_at_water": False, "can_be_at_land": True, "might_be_movable": False,
      "might_be_jumpable": True, "might_be_used_alone": True, "is_container": False, "is_collectable": False, "is_wearable": False
    },
    {
      "type": "tent", "possible_states": ["folded", "setup", "damaged"], "possible_actions": ["enter", "exit", "setup", "pack"],
      "variants": ["small", "medium", "large"], "can_be_at_water": False, "can_be_at_land": True, "might_be_movable": True,
      "might_be_jumpable": False, "might_be_used_alone": True, "is_container": True, "is_collectable": False, "is_wearable": False
    },
    {
      "type": "pot", "possible_states": ["default", "breaking", "broken"], "possible_actions": ["fill", "empty", "cook", "examine"],
      "variants": ["small", "medium", "big"], "can_be_at_water": True, "can_be_at_land": True, "might_be_movable": True,
      "might_be_jumpable": False, "might_be_used_alone": True, "is_container": True, "is_collectable": False, "is_wearable": False
    },
    {
      "type": "backpack", "possible_states": ["empty", "filled"], "possible_actions": ["open", "close", "wear", "remove"],
      "variants": ["small", "medium", "large"], "can_be_at_water": False, "can_be_at_land": True, "might_be_movable": True,
      "might_be_jumpable": False, "might_be_used_alone": True, "is_container": True, "is_collectable": True, "is_wearable": True
    },
    {
      "type": "bedroll", "possible_states": ["rolled", "unrolled"], "possible_actions": ["sleep", "roll", "unroll"],
      "variants": ["basic", "comfort", "luxury"], "can_be_at_water": False, "can_be_at_land": True, "might_be_movable": True,
      "might_be_jumpable": False, "might_be_used_alone": True, "is_container": False, "is_collectable": True, "is_wearable": False
    },
    {
      "type": "firewood", "possible_states": ["dry", "wet", "burning"], "possible_actions": ["collect", "burn", "stack"],
      "variants": ["branch", "log", "kindling"], "can_be_at_water": False, "can_be_at_land": True, "might_be_movable": True,
      "might_be_jumpable": False, "might_be_used_alone": True, "is_container": False, "is_collectable": True, "is_wearable": False
    },
    {
      "type": "log_stool", "possible_states": ["default", "occupied"], "possible_actions": ["sit", "stand", "move"],
      "variants": ["small", "medium", "large"], "can_be_at_water": False, "can_be_at_land": True, "might_be_movable": True,
      "might_be_jumpable": False, "might_be_used_alone": True, "is_container": False, "is_collectable": False, "is_wearable": False
    },
    {
      "type": "obstacle", "possible_states": ["default", "broken", "moved"], "possible_actions": ["examine", "break", "climb", "jump"],
      "variants": ["rock", "plant", "log", "stump", "hole", "tree"], "can_be_at_water": True, "can_be_at_land": True, "might_be_movable": True,
      "might_be_jumpable": True, "might_be_used_alone": True, "is_container": False, "is_collectable": False, "is_wearable": False
    }

## 1. Interactive Items and Their Factories

### 1.1. Backpack
- **Class:** `Backpack` (inherits from `GameObject`)
- **Properties:**
  - `description`: A text description.
  - `max_capacity`: Maximum number of items.
  - `contained_items`: A list of item names currently held.

---

### 1.2. Bedroll
- **Class:** `Bedroll` (inherits from `GameObject`)
- **Properties:**
  - `description`
  - `max_capacity`: `1` (one person)
  - `contained_items`: List holding people using the bedroll.

---

### 1.3. Campfire Pot
- **Class:** `CampfirePot` (inherits from `GameObject`)
- **Properties:**
  - `description`
  - `pot_type`: Either a tripod or a spit (default: `POT_TRIPOD`)
  - `state`: Initial state is `POT_EMPTY` (other states: cooking, burning, cooked)
  - `max_items`: Maximum of `1` item
  - `contained_items`: Items being cooked
  - `usable_with`: `{CAMPFIRE_BURNING, CAMPFIRE_DYING}`
- **Possible Actions:** (determined by state)
  - If empty: `{ACTION_PLACE}`
  - If cooking or burning: `{ACTION_REMOVE}`
  - If cooked: `{ACTION_REMOVE, ACTION_EMPTY}`
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

---

### 1.4. Spit Item
- **Class:** `SpitItem` (inherits from `GameObject`)
- **Properties:**
  - `description`
  - `item_type`: E.g., `SPIT_BIRD` (other options include fish or meat)
  - `state`: Starts as `SPIT_ITEM_RAW` (other states: cooking, burning, cooked)
  - `cooking_time`: Number of turns to cook (default `5`)
  - `is_edible`: `True`
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
- **Possible Actions:** Based on state:
  - If unlit: `{ACTION_LIGHT}`
  - If burning/dying: `{ACTION_EXTINGUISH}`
  - If extinguished: `{ACTION_LIGHT}`
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
---
""" 