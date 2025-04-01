import os
import asyncio
import json
import logging
from typing import Tuple, List, Dict, Any

from agents import (
    Agent,
    function_tool,
    RunContextWrapper
)

from agent_copywriter_direct import CompleteStoryResult
from game_object import Container

# --- Configuration ---
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = logging.DEBUG if DEBUG_MODE else logging.INFO
DEFAULT_VOICE = "nova"

# --- Logging Setup ---
root_logger = logging.getLogger()
if root_logger.hasHandlers():
    root_logger.handlers.clear()

logging.basicConfig(level=LOG_LEVEL,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
if DEBUG_MODE:
    logger.info("Debug mode enabled.")

# System message for the Puppet Master agent
PUPPET_MASTER_SYSTEM_MESSAGE = """You are a Puppet Master agent that controls a character in a story world.

As the Puppet Master, you:
1. Control the actions of the character by using tools
2. Interpret user commands in natural language
3. Provide descriptive responses about what the character sees and experiences
4. Help the user navigate and interact with the story world

Available actions:
- Look around to see nearby objects (look_around)
- Look at specific objects for more details (look_at)
- Move in different directions (move)
- Move continuously until blocked (move_continuously)
- Jump over obstacles (jump)
- Push and pull objects (push, pull)
- Check your inventory (inventory, check_inventory)
- Get items from containers (get_from_container)
- Put items into containers (put_in_container)
- Use objects with other objects (use_object_with)
- Say things (say)
- Examine objects in detail (examine_object)
- Execute a sequence of movement commands (execute_movement_sequence)

Always respond in a descriptive, narrative style that helps immerse the user in the story world.
"""


class DirectionHelper:
    """Helper class for handling relative directions and movement in the game world.
    
    This class provides static methods to handle direction-related calculations,
    coordinate transformations, and continuous movement functionality.
    """

    @staticmethod
    def get_relative_position(current_pos: Tuple[int, int], direction: str) -> Tuple[int, int]:
        """Convert a relative direction to target coordinates.
        
        Args:
            current_pos (Tuple[int, int]): The current (x, y) position
            direction (str): Direction to move ('left', 'right', 'up', 'down')
            
        Returns:
            Tuple[int, int]: The new (x, y) coordinates after moving in the specified direction
        """
        x, y = current_pos
        direction = direction.lower()
        if direction == "left":
            return (x - 1, y)
        elif direction == "right":
            return (x + 1, y)
        elif direction == "up":
            return (x, y - 1)
        elif direction == "down":
            return (x, y + 1)
        return current_pos

    @staticmethod
    def get_direction_vector(from_pos: Tuple[int, int], to_pos: Tuple[int, int]) -> Tuple[int, int]:
        """Get the direction vector between two positions.
        
        Args:
            from_pos (Tuple[int, int]): Starting (x, y) position
            to_pos (Tuple[int, int]): Target (x, y) position
            
        Returns:
            Tuple[int, int]: Direction vector (dx, dy) representing the movement
        """
        fx, fy = from_pos
        tx, ty = to_pos
        return (tx - fx, ty - fy)

    @staticmethod
    def get_direction_name(direction: Tuple[int, int]) -> str:
        """Convert a direction vector to a cardinal direction name.
        
        Args:
            direction (Tuple[int, int]): Direction vector (dx, dy)
            
        Returns:
            str: Cardinal direction name ('left', 'right', 'up', 'down', or 'unknown')
        """
        dx, dy = direction
        if dx == -1 and dy == 0:
            return "left"
        elif dx == 1 and dy == 0:
            return "right"
        elif dx == 0 and dy == -1:
            return "up"
        elif dx == 0 and dy == 1:
            return "down"
        return "unknown"

    @staticmethod
    async def move_continuously(story_result: CompleteStoryResult, direction: str) -> str:
        """Move continuously in a direction until blocked or at board edge.
        
        Args:
            story_result (CompleteStoryResult): Current story state containing environment and person
            direction (str): Direction to move ('left', 'right', 'up', 'down')
            
        Returns:
            str: Message describing the movement result and reason for stopping
            
        Notes:
            - Maximum 50 moves to prevent infinite loops
            - Stops on obstacles, board edges, or movement failures
        """
        logger.info(f"🔄 Starting continuous movement in direction: {direction}")
        logger.info(f"🎯 Starting position: {story_result.person.position}")

        moves = 0
        last_message = ""
        max_moves = 50

        while moves < max_moves:
            current_pos = story_result.person.position
            target_pos = DirectionHelper.get_relative_position(current_pos, direction)
            logger.debug(f"Move attempt #{moves + 1}: {current_pos} → {target_pos}")

            result = story_result.person.move(
                story_result.environment,
                target_pos,
                False
            )

            if not result["success"]:
                logger.info(f"🛑 Movement stopped: {result['message']}")
                if moves == 0:
                    return result["message"]
                else:
                    return f"Moved {moves} steps {direction} and stopped: {result['message']}"

            sync_story_state(story_result)
            moves += 1
            last_message = result["message"]

            next_pos = DirectionHelper.get_relative_position(target_pos, direction)
            if not story_result.environment.is_valid_position(next_pos):
                logger.info(f"🌍 Reached board edge at {target_pos}")
                return f"Moved {moves} steps {direction} and reached the board edge"
            elif not story_result.environment.can_move_to(next_pos):
                logger.info(f"🚧 Reached obstacle at {next_pos}")
                return f"Moved {moves} steps {direction} and reached an obstacle"

        logger.warning(f"⚠️ Hit move limit ({max_moves}) while moving {direction}")
        return f"Moved {moves} steps {direction} and stopped at the maximum move limit."


# Extend CompleteStoryResult with the functionality needed
def sync_story_state(story_result: CompleteStoryResult):
    """Synchronize the story state by updating nearby objects and containers based on entities and positions.
    
    Args:
        story_result (CompleteStoryResult): The story state to synchronize
    """
    logger.info("🔄 Synchronizing story state...")

    if not hasattr(story_result, 'nearby_objects'):
        story_result.nearby_objects = {}

    if not hasattr(story_result, 'person') or not story_result.person:
        logger.warning("❌ No person found in story state, cannot sync properly")
        return

    if not hasattr(story_result, 'environment') or not story_result.environment:
        logger.warning("❌ No environment found in story state, cannot sync properly")
        return

    if not hasattr(story_result, 'entities') or not story_result.entities:
        logger.warning("❌ No entities found in story state, cannot sync properly")
        return

    # Set up entity position lookup for the environment
    # This allows the environment's get_entities_at to work properly
    if not hasattr(story_result.environment, '_position_map'):
        story_result.environment._position_map = {}

    story_result.environment._position_map.clear()

    # Track entities by position
    for entity in story_result.entities:
        position = None
        if hasattr(entity, 'position') and entity.position:
            # Handle different position formats
            if hasattr(entity.position, 'x') and hasattr(entity.position, 'y'):
                position = (entity.position.x, entity.position.y)
            elif isinstance(entity.position, (tuple, list)) and len(entity.position) >= 2:
                position = (entity.position[0], entity.position[1])

        if position:
            if position not in story_result.environment._position_map:
                story_result.environment._position_map[position] = []
            story_result.environment._position_map[position].append(entity)

    # Create a lookup of entities by ID for the environment
    if not hasattr(story_result.environment, '_entity_map'):
        story_result.environment._entity_map = {}

    story_result.environment._entity_map.clear()
    for entity in story_result.entities:
        if hasattr(entity, 'id'):
            story_result.environment._entity_map[entity.id] = entity

    # Add entity lookup methods to the Environment class if they don't exist
    if not hasattr(story_result.environment.__class__, '_get_entities_at_original'):
        # Store the original method
        story_result.environment.__class__._get_entities_at_original = story_result.environment.__class__.get_entities_at

        # Replace with a method that uses the position map
        def get_entities_at(self, position):
            # Handle different position formats
            if hasattr(position, 'x') and hasattr(position, 'y'):
                position = (position.x, position.y)
            elif isinstance(position, (tuple, list)) and len(position) >= 2:
                position = (position[0], position[1])

            # Return entities at this position
            return self._position_map.get(position, [])

        story_result.environment.__class__.get_entities_at = get_entities_at

    if not hasattr(story_result.environment.__class__, '_get_object_at_original'):
        # Store the original method
        story_result.environment.__class__._get_object_at_original = story_result.environment.__class__.get_object_at

        # Replace with a method that uses the position map and filters for GameObjects
        def get_object_at(self, position):
            entities = self.get_entities_at(position)
            for entity in entities:
                # Check if it's a GameObject (has is_movable attribute)
                if hasattr(entity, 'is_movable'):
                    return entity
            return None

        story_result.environment.__class__.get_object_at = get_object_at

    # Update nearby_objects based on person's position
    if story_result.person.position:
        # Use the person's look function to update nearby objects
        look_result = story_result.person.look(story_result.environment)
        if look_result.get("success", False):
            story_result.nearby_objects = {obj.id: obj for obj in look_result.get("objects", [])}

    logger.info(f"✅ Story state synchronized. Found {len(story_result.nearby_objects)} nearby objects.")


# Tool definitions - using CompleteStoryResult instead of GameState
@function_tool
async def move(
        ctx: RunContextWrapper[CompleteStoryResult],
        direction: str,
        is_running: bool,
        continuous: bool
) -> str:
    """Move the player in a specified direction.
    
    Args:
        ctx (RunContextWrapper[CompleteStoryResult]): Context containing story state
        direction (str): Direction to move ('left', 'right', 'up', 'down')
        is_running (bool): If True, moves up to 2 tiles; if False, moves 1 tile
        continuous (bool): If True, keeps moving until blocked or at board edge
        
    Returns:
        str: Message describing the movement result
        
    Notes:
        - Syncs story state after successful movement
        - Supports both single-step and continuous movement
        - Validates movement before execution
    """
    logger.info(f"🎮 MOVE called with params: direction='{direction}', running={is_running}, continuous={continuous}")
    story_result = ctx.context
    logger.info(f"📍 Current position: {story_result.person.position}")

    if continuous:
        result = await DirectionHelper.move_continuously(story_result, direction)
    else:
        current_pos = story_result.person.position
        target_pos = DirectionHelper.get_relative_position(current_pos, direction)
        logger.info(f"🎯 Target position: {target_pos}")

        result = story_result.person.move(
            story_result.environment,
            target_pos,
            is_running
        )
        logger.info(f"{'✅' if result['success'] else '❌'} Move result: {result['message']}")

        if result["success"]:
            sync_story_state(story_result)
            logger.info(f"📍 New position: {story_result.person.position}")

    return result["message"]


@function_tool
async def jump(
        ctx: RunContextWrapper[CompleteStoryResult],
        target_x: int,
        target_y: int
) -> str:
    """Jump over one square to land two squares away.
    
    Args:
        ctx (RunContextWrapper[CompleteStoryResult]): Context containing story state
        target_x (int): X-coordinate of the landing position
        target_y (int): Y-coordinate of the landing position
        
    Returns:
        str: Message describing the jump result
        
    Notes:
        - Must be a valid jumpable distance (2 squares away)
        - Path must be clear for jumping
    """
    logger.info(f"🦘 JUMP called with params: target_x={target_x}, target_y={target_y}")
    story_result = ctx.context
    result = story_result.person.jump(
        story_result.environment,
        (target_x, target_y)
    )

    return result["message"]


@function_tool
async def push(
        ctx: RunContextWrapper[CompleteStoryResult],
        object_id: str,
        direction: str
) -> str:
    """Push an object in a specified direction.
    
    Args:
        ctx (RunContextWrapper[CompleteStoryResult]): Context containing story state
        object_id (str): ID of the object to push
        direction (str): Direction to push ('left', 'right', 'up', 'down')
        
    Returns:
        str: Message describing the push result
        
    Notes:
        - Player moves into object's original position
        - Object must be movable and within reach
        - Target position must be clear
    """
    logger.info(f"👉 PUSH called with params: object_id='{object_id}', direction='{direction}'")
    story_result = ctx.context

    # Find the object
    if not hasattr(story_result, 'nearby_objects') or object_id not in story_result.nearby_objects:
        return f"Cannot find object {object_id} nearby"

    obj = story_result.nearby_objects[object_id]
    if not hasattr(obj, 'position') or not obj.position:
        return f"Object {object_id} has no position"

    # Calculate push direction
    direction_pos = DirectionHelper.get_relative_position(obj.position, direction)
    push_vector = DirectionHelper.get_direction_vector(obj.position, direction_pos)

    result = story_result.person.push(
        story_result.environment,
        obj.position,
        push_vector
    )

    if result["success"]:
        sync_story_state(story_result)

    return result["message"]


@function_tool
async def pull(
        ctx: RunContextWrapper[CompleteStoryResult],
        object_x: int,
        object_y: int
) -> str:
    """Pull an object into the player's current position.
    
    Args:
        ctx (RunContextWrapper[CompleteStoryResult]): Context containing story state
        object_x (int): The x-coordinate of the object to pull
        object_y (int): The y-coordinate of the object to pull
        
    Returns:
        str: Message describing the pull result
    """
    logger.info(f"👈 PULL called with params: object_x={object_x}, object_y={object_y}")
    story_result = ctx.context
    result = story_result.person.pull(
        story_result.environment,
        (object_x, object_y)
    )

    return result["message"]


@function_tool
async def get_from_container(
        ctx: RunContextWrapper[CompleteStoryResult],
        container_id: str,
        item_id: str
) -> str:
    """Get an item from a container and put it in the person's inventory.
    
    Args:
        ctx (RunContextWrapper[CompleteStoryResult]): Context containing story state
        container_id (str): ID of the container to get item from
        item_id (str): ID of the item to retrieve
        
    Returns:
        str: Message describing the retrieval result
        
    Notes:
        - Container must be accessible and open
        - Item must exist in container
        - Person's inventory must have space
    """
    logger.info(f"📥 GET_FROM_CONTAINER called with params: container_id='{container_id}', item_id='{item_id}'")
    story_result = ctx.context

    # Get accessible containers from nearby objects
    accessible_containers = {
        obj_id: obj
        for obj_id, obj in story_result.nearby_objects.items()
        if hasattr(obj, 'is_container') and obj.is_container
    }

    logger.info(f"📦 Available containers: {list(accessible_containers.keys())}")

    if container_id not in accessible_containers:
        logger.warning(f"❌ Container {container_id} not found nearby")
        return f"Container {container_id} not found nearby"

    container = accessible_containers[container_id]
    logger.info(f"📦 Container contents before: {[item.id for item in container.contents]}")
    logger.info(f"🎒 Inventory before: {[item.id for item in story_result.person.inventory.contents]}")

    result = story_result.person.get_from_container(container, item_id)

    if result["success"]:
        logger.info(f"📦 Container contents after: {[item.id for item in container.contents]}")
        logger.info(f"🎒 Inventory after: {[item.id for item in story_result.person.inventory.contents]}")

    return result["message"]


@function_tool
async def put_in_container(
        ctx: RunContextWrapper[CompleteStoryResult],
        container_id: str,
        item_id: str
) -> str:
    """Put an item from the person's inventory into a container.
    
    Args:
        ctx (RunContextWrapper[CompleteStoryResult]): Context containing story state
        container_id (str): The ID of the container
        item_id (str): The ID of the item to put in the container
        
    Returns:
        str: Message describing the result
    """
    logger.info(f"📤 PUT_IN_CONTAINER called with params: container_id='{container_id}', item_id='{item_id}'")
    story_result = ctx.context

    # Get accessible containers from nearby objects
    accessible_containers = {
        obj_id: obj
        for obj_id, obj in story_result.nearby_objects.items()
        if hasattr(obj, 'is_container') and obj.is_container
    }

    if container_id not in accessible_containers:
        return f"Container {container_id} not found nearby"

    container = accessible_containers[container_id]
    result = story_result.person.put_in_container(item_id, container)

    return result["message"]


@function_tool
async def use_object_with(
        ctx: RunContextWrapper[CompleteStoryResult],
        item1_id: str,
        item2_id: str
) -> str:
    """Use one object with another.
    
    Args:
        ctx (RunContextWrapper[CompleteStoryResult]): Context containing story state
        item1_id (str): The ID of the first item (must be in inventory)
        item2_id (str): The ID of the second item
        
    Returns:
        str: Message describing the result
    """
    logger.info(f"🔧 USE_OBJECT_WITH called with params: item1_id='{item1_id}', item2_id='{item2_id}'")
    story_result = ctx.context
    result = story_result.person.use_object_with(item1_id, item2_id)

    return result["message"]


@function_tool
async def look_around(ctx: RunContextWrapper[CompleteStoryResult]) -> str:
    """Look around to find objects up to 5 positions away.
    
    Args:
        ctx (RunContextWrapper[CompleteStoryResult]): Context containing story state
        
    Returns:
        str: Description of visible objects and their locations
        
    Notes:
        - Uses Manhattan distance for visibility calculation
        - Includes object descriptions and distances
        - Updates story state with visible objects
    """
    logger.info(f"👀 LOOK_AROUND called")
    story_result = ctx.context

    # Sync state and update story state information
    sync_story_state(story_result)

    if not hasattr(story_result, 'nearby_objects') or not story_result.nearby_objects:
        return "You don't see anything interesting nearby."

    object_descriptions = []
    player_pos = story_result.person.position

    for obj in story_result.nearby_objects.values():
        if obj.position and player_pos:
            # Calculate Manhattan distance between the player and the object
            distance = abs(obj.position[0] - player_pos[0]) + abs(obj.position[1] - player_pos[1])
            if distance > 5:
                continue  # Skip objects further than 5 positions away

            desc = f"{obj.name} is at position {obj.position} (distance: {distance})"
        else:
            desc = f"{obj.name} at unknown position"

        if hasattr(obj, "description") and obj.description:
            desc += f" - {obj.description}"

        object_descriptions.append(desc)

    if not object_descriptions:
        return "You look around but nothing within 5 positions catches your eye."

    return "You look around:\n" + "\n".join(object_descriptions)


@function_tool
async def say(
        ctx: RunContextWrapper[CompleteStoryResult],
        message: str
) -> str:
    """Say something.
    
    Args:
        ctx (RunContextWrapper[CompleteStoryResult]): Context containing story state
        message (str): The message to say
        
    Returns:
        str: Result message
    """
    logger.info(f"💬 SAY called with message: '{message}'")
    story_result = ctx.context
    result = story_result.person.say(message)

    return result["message"]


@function_tool
async def check_inventory(
        ctx: RunContextWrapper[CompleteStoryResult]
) -> str:
    """Legacy function to check what items are in the player's inventory.
    Same as inventory but with different formatting.
    
    Args:
        ctx (RunContextWrapper[CompleteStoryResult]): Context containing story state
        
    Returns:
        str: List of inventory items with IDs
    """
    logger.info(f"🎒 CHECK_INVENTORY called")
    story_result = ctx.context

    if not story_result.person.inventory or not story_result.person.inventory.contents:
        return f"{story_result.person.name}'s inventory is empty"

    items = story_result.person.inventory.contents
    item_descriptions = [f"{item.id}: {item.name}" for item in items]

    return f"{story_result.person.name}'s inventory contains:\n" + "\n".join(item_descriptions)


@function_tool
async def examine_object(
        ctx: RunContextWrapper[CompleteStoryResult],
        object_id: str
) -> str:
    """Examine an object to get more information about it.
    
    Args:
        ctx (RunContextWrapper[CompleteStoryResult]): Context containing story state
        object_id (str): ID of the object to examine
        
    Returns:
        str: Detailed description of the object
        
    Notes:
        - Works for both nearby objects and inventory items
        - Shows all relevant object attributes
        - Includes special properties for containers
    """
    logger.info(f"🔍 EXAMINE_OBJECT called with object_id: '{object_id}'")
    story_result = ctx.context

    # Ensure nearby_objects exists
    if not hasattr(story_result, 'nearby_objects'):
        story_result.nearby_objects = {}
        sync_story_state(story_result)

    # Log available objects
    logger.info(f"🌍 Nearby objects: {list(story_result.nearby_objects.keys())}")
    logger.info(f"🎒 Inventory items: {[item.id for item in story_result.person.inventory.contents]}")

    # Check in nearby objects
    if object_id in story_result.nearby_objects:
        obj = story_result.nearby_objects[object_id]
        logger.info(f"📍 Found object nearby: {obj.name} at position {obj.position}")

        # Log all object attributes
        logger.info("📝 Object attributes:")
        for attr in dir(obj):
            if not attr.startswith('_'):  # Skip private attributes
                try:
                    value = getattr(obj, attr)
                    if not callable(value):  # Skip methods
                        logger.info(f"  - {attr}: {value}")
                except Exception as e:
                    logger.warning(f"  - {attr}: <error reading value: {e}>")

        # Gather information about the object
        info = [
            f"Name: {obj.name}",
            f"Position: {obj.position}",
            f"Description: {obj.description if hasattr(obj, 'description') else 'No description'}"
        ]

        # Add object-specific properties
        if hasattr(obj, "is_movable"):
            info.append(f"Movable: {'Yes' if obj.is_movable else 'No'}")
        if hasattr(obj, "is_jumpable"):
            info.append(f"Jumpable: {'Yes' if obj.is_jumpable else 'No'}")
        if hasattr(obj, "weight"):
            info.append(f"Weight: {obj.weight}")
        if hasattr(obj, "usable_with") and obj.usable_with:
            info.append(f"Can be used with: {', '.join(obj.usable_with)}")

        # If container, show contents
        if isinstance(obj, Container):
            if obj.contents:
                contents = [f"- {item.name}" for item in obj.contents]
                info.append(f"Contains:\n" + "\n".join(contents))
            else:
                info.append("This container is empty")

            info.append(f"Capacity: {obj.capacity}")
            info.append(f"Status: {'Open' if obj.is_open else 'Closed'}")

        return "\n".join(info)

    # Check in inventory
    for item in story_result.person.inventory.contents:
        if item.id == object_id:
            info = [
                f"Name: {item.name}",
                f"Description: {item.description if hasattr(item, 'description') else 'No description'}"
            ]

            # Add object-specific properties
            if hasattr(item, "is_movable"):
                info.append(f"Movable: {'Yes' if item.is_movable else 'No'}")
            if hasattr(item, "weight"):
                info.append(f"Weight: {item.weight}")
            if hasattr(item, "usable_with") and item.usable_with:
                info.append(f"Can be used with: {', '.join(item.usable_with)}")

            return "\n".join(info)

    return f"Object with ID {object_id} not found nearby or in inventory"


@function_tool
async def execute_movement_sequence(
        ctx: RunContextWrapper[CompleteStoryResult],
        commands: List[Dict[str, Any]]
) -> str:
    """Execute a sequence of movement instructions provided as a list of commands.

    Each command is expected to be a dict with the keys 'tool' and 'parameters'.
    Supported tools: 'move' and 'jump'.
    
    Args:
        ctx (RunContextWrapper[CompleteStoryResult]): Context containing story state
        commands (List[Dict[str, Any]]): List of command dictionaries, each with:
            - tool (str): The tool to execute ('move' or 'jump')
            - parameters (Dict[str, Any]): Parameters for the tool
                For move:
                    - direction (str): Direction to move ('left', 'right', 'up', 'down')
                    - is_running (bool): Whether to run (move 2 tiles)
                    - continuous (bool): Whether to move continuously
                For jump:
                    - target_x (int): Target X coordinate
                    - target_y (int): Target Y coordinate
                    
    Returns:
        str: Combined results of executing all commands in sequence
    """
    logger.info(f"📋 EXECUTE_MOVEMENT_SEQUENCE called with commands:\n{json.dumps(commands, indent=2)}")
    results = []
    for cmd in commands:
        tool_name = cmd.get('tool')
        params = cmd.get('parameters', {})
        if tool_name == 'move':
            direction = params.get('direction')
            is_running = params.get('is_running', False)
            continuous = params.get('continuous', False)
            res = await move(ctx, direction, is_running, continuous)
            results.append(f"move {direction}: {res}")
        elif tool_name == 'jump':
            target_x = params.get('target_x')
            target_y = params.get('target_y')
            res = await jump(ctx, target_x, target_y)
            results.append(f"jump to ({target_x},{target_y}): {res}")
        else:
            results.append(f"Unknown command: {cmd}")
    return "\n".join(results)


@function_tool
async def look_at(
        ctx: RunContextWrapper[CompleteStoryResult],
        object_id: str
) -> str:
    """Look at and examine a specific object to get more detailed information.
    
    Args:
        ctx (RunContextWrapper[CompleteStoryResult]): Context containing story state
        object_id (str): ID of the object to examine
        
    Returns:
        str: Description of the object
    """
    logger.info(f"👁️ LOOK_AT called with object_id: {object_id}")
    story_result = ctx.context

    # Find object in nearby objects or inventory
    target_obj = None

    # Check nearby objects
    if object_id in story_result.nearby_objects:
        target_obj = story_result.nearby_objects[object_id]
        logger.info(f"Found object {object_id} in nearby objects")

    # Check inventory
    elif story_result.person and story_result.person.inventory:
        for item in story_result.person.inventory.contents:
            if item.id == object_id:
                target_obj = item
                logger.info(f"Found object {object_id} in inventory")
                break

    # Check entities (for objects not in nearby_objects but in the world)
    if not target_obj and hasattr(story_result, 'entities'):
        for entity in story_result.entities:
            if hasattr(entity, 'id') and entity.id == object_id:
                target_obj = entity
                logger.info(f"Found object {object_id} in entities list")
                break

    if not target_obj:
        return f"You don't see any {object_id} nearby or in your inventory."

    # Generate description
    description = f"You examine the {target_obj.name}. "

    if hasattr(target_obj, 'description') and target_obj.description:
        description += target_obj.description

    # Add position if applicable
    if hasattr(target_obj, 'position') and target_obj.position:
        pos_text = f"It's located at position {target_obj.position}."
        description += f" {pos_text}"

    # Add weight if applicable
    if hasattr(target_obj, 'weight'):
        weight_text = f"It looks {get_weight_description(target_obj.weight)}."
        description += f" {weight_text}"

    # Add mobility info
    if hasattr(target_obj, 'is_movable'):
        mobility = "can be moved" if target_obj.is_movable else "cannot be moved"
        description += f" It {mobility}."

    # If it's a container, show contents
    if hasattr(target_obj, 'contents') and hasattr(target_obj, 'is_open'):
        if target_obj.is_open:
            if target_obj.contents:
                items = [f"{item.name}" for item in target_obj.contents]
                description += f" It contains: {', '.join(items)}."
            else:
                description += " It's empty."
        else:
            description += " It's closed."

    return description


@function_tool
async def inventory(
        ctx: RunContextWrapper[CompleteStoryResult]
) -> str:
    """Check what items are in your inventory.
    
    Args:
        ctx (RunContextWrapper[CompleteStoryResult]): Context containing story state
        
    Returns:
        str: Description of inventory contents
    """
    logger.info("🎒 INVENTORY called")
    story_result = ctx.context

    if not story_result.person or not story_result.person.inventory:
        return "You don't have an inventory."

    items = story_result.person.inventory.contents

    if not items:
        return "Your inventory is empty."

    item_descriptions = []
    for item in items:
        desc = item.name
        if hasattr(item, 'weight'):
            desc += f" (weight: {item.weight})"
        item_descriptions.append(desc)

    return f"Your inventory contains: {', '.join(item_descriptions)}"


def get_weight_description(weight: int) -> str:
    """Convert a numerical weight to a descriptive term.
    
    Args:
        weight (int): Numerical weight value
        
    Returns:
        str: Description of the weight
    """
    if weight <= 1:
        return "very light"
    elif weight <= 3:
        return "light"
    elif weight <= 5:
        return "moderately heavy"
    elif weight <= 8:
        return "heavy"
    else:
        return "extremely heavy"


@function_tool
async def move_continuously(
        ctx: RunContextWrapper[CompleteStoryResult],
        direction: str
) -> str:
    """Move continuously in a direction until reaching an obstacle or edge.
    
    Args:
        ctx (RunContextWrapper[CompleteStoryResult]): Context containing story state
        direction (str): Direction to move ('left', 'right', 'up', 'down')
        
    Returns:
        str: Description of the movement result
        
    Notes:
        - Will continue moving until blocked by an obstacle or at board edge
        - Updates nearby objects after each move
    """
    logger.info(f"🔄 MOVE_CONTINUOUSLY called with direction: {direction}")
    story_result = ctx.context

    # Call the static helper method
    result = await DirectionHelper.move_continuously(story_result, direction)

    return result


# Create the agent with all tools
def create_puppet_master(story_result: CompleteStoryResult, person_name: str = "Game Character") -> Agent[CompleteStoryResult]:
    """Create a new puppet master agent to control game character actions.
    
    Args:
        story_result (CompleteStoryResult): The story state containing environment, entities, and person
        person_name (str): Name of the character being controlled
        
    Returns:
        Agent[CompleteStoryResult]: Configured agent with all available tools
    """
    # Initialize person if not exists
    if not hasattr(story_result, 'person') or not story_result.person:
        from person import Person
        story_result.person = Person(id="person1", name=person_name, strength=10)
        logger.info(f"Created new person '{person_name}' in story")

    # Initialize environment's position tracking
    if hasattr(story_result, 'environment') and story_result.environment:
        if not hasattr(story_result.environment, '_position_map'):
            story_result.environment._position_map = {}

        if not hasattr(story_result.environment, '_entity_map'):
            story_result.environment._entity_map = {}

    # Ensure nearby_objects exists
    if not hasattr(story_result, 'nearby_objects'):
        story_result.nearby_objects = {}

    # Create the agent with all tools
    agent = Agent[CompleteStoryResult](
        name="PuppetMaster",
        instructions=PUPPET_MASTER_SYSTEM_MESSAGE,
        handoff_description="Executed when the char wants to interact with the physical world.",
        tools=[
            look_around,
            look_at,
            move,
            move_continuously,
            jump,
            push,
            pull,
            inventory,
            get_from_container,
            put_in_container,
            use_object_with,
            say,
            check_inventory,
            examine_object,
            execute_movement_sequence
        ]
    )

    # Log creation
    logger.info(f"PuppetMaster agent created for character: {person_name}")

    return agent


# Setup conversation handler
async def run_continuous_conversation(story_result: CompleteStoryResult, agent_name: str = "Game Character") -> None:
    """Run a continuous conversation with the user, processing commands through the agent.
    
    Args:
        story_result (CompleteStoryResult): The story state to operate on
        agent_name (str): Name to use for the game agent in conversation
        
    Returns:
        None
    """
    logger.info("🎮 Starting continuous conversation with agent...")

    # Create the puppet master agent
    agent = create_puppet_master(story_result, agent_name)

    # Initially sync the state
    sync_story_state(story_result)

    # Initial welcome message
    print(f"\n🧠 {agent_name} is ready to help you navigate the world!")
    print("📜 Type your commands or questions, or 'exit' to quit.\n")

    # Main conversation loop
    while True:
        try:
            # Get user input
            user_input = input("👤 You: ")
            if user_input.lower() in ["exit", "quit", "bye"]:
                print(f"\n👋 {agent_name} says: Goodbye!")
                break

            print(f"\n🤔 {agent_name} is thinking...")

            # Process the input through the agent
            try:
                # Try with the new run_sync method
                response = await agent.run_sync(user_input)
            except AttributeError:
                # Fall back to the Runner approach if run_sync is not available
                from agents import Runner
                runner = Runner()
                result = await runner.run(starting_agent=agent, input=user_input, context=story_result)
                response = result.final_output

            # Display the agent's response
            print(f"\n🧠 {agent_name}: {response}\n")

            # Sync the story state after each interaction
            sync_story_state(story_result)

        except KeyboardInterrupt:
            print("\n\n👋 Conversation interrupted. Goodbye!")
            break
        except Exception as e:
            logger.error(f"Error in conversation: {e}", exc_info=True)
            print(f"\n⚠️ Something went wrong: {str(e)}")
            print("Let's continue from where we left off.")

    logger.info("🎮 Ending continuous conversation with agent.")


# Example of using the agent
async def example_usage() -> None:
    """Demonstrates how to use the puppet master with a CompleteStoryResult."""
    logger.info("🎮 Starting story simulation")

    from agent_copywriter_direct import Environment, CompleteStoryResult
    from person import Person
    from game_object import Container, GameObject

    # Create a sample environment
    grid = [[0 for _ in range(10)] for _ in range(10)]
    # Create a small island in the center (1 = traversable land)
    for y in range(3, 7):
        for x in range(3, 7):
            grid[y][x] = 1

    environment = Environment(width=10, height=10, grid=grid)

    # Initialize position tracking maps in environment
    environment._position_map = {}
    environment._entity_map = {}

    # Create a person
    player = Person(id="player1", name="Hero", position=(5, 5), strength=10)

    # Create a sample story result
    story_result = CompleteStoryResult(
        person=player,
        theme="Fantasy Adventure",
        environment=environment,
        terrain_description="A small island surrounded by water",
        entity_descriptions={},
        narrative_components={},
        entities=[],
        complete_narrative="A sample story for testing the puppet master.",
        nearby_objects={}
    )

    # Add some sample entities
    box = GameObject(id="box1", name="Wooden Box", description="A simple wooden box", is_movable=True)
    story_result.entities.append(box)
    environment._position_map[(5, 6)] = [box]  # Add to position map
    box.position = (5, 6)  # South/Down from player

    table = GameObject(id="table1", name="Table", description="A wooden table", is_movable=False)
    story_result.entities.append(table)
    environment._position_map[(4, 5)] = [table]  # Add to position map
    table.position = (4, 5)  # West/Left from player

    chest = Container(id="chest1", name="Treasure Chest", description="A mysterious chest", is_open=True)
    story_result.entities.append(chest)
    environment._position_map[(6, 5)] = [chest]  # Add to position map
    chest.position = (6, 5)  # East/Right from player

    key = GameObject(id="key1", name="Rusty Key", description="An old rusty key", is_movable=True, weight=1)
    chest.add_item(key)

    sword = GameObject(id="sword1", name="Iron Sword", description="A sharp iron sword", is_movable=True, weight=2)
    player.inventory.add_item(sword)

    # Create entity map for the environment
    environment._entity_map = {
        player.id: player,
        box.id: box,
        table.id: table,
        chest.id: chest,
        key.id: key,
        sword.id: sword
    }

    # Initial sync of story state
    sync_story_state(story_result)

    print("\n🌍 Story world initialized!")
    print(f"👤 Player is at position {player.position}")
    print("💡 Try commands like:")
    print("- 'look around'")
    print("- 'move right'")
    print("- 'push box1 down'")
    print("- 'get key1 from chest1'")

    # Run conversation
    await run_continuous_conversation(story_result, "Hero")


if __name__ == "__main__":
    asyncio.run(example_usage())
