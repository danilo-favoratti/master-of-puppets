import json
import logging
import os
import asyncio # Added
import traceback
from prompt.storyteller_prompts import get_storyteller_system_prompt, get_game_mechanics_reference
# Adjusted imports: Removed Entity, Position (pulled in via game_object), added Person, GameObject, Container
from agent_copywriter_direct import Environment, CompleteStoryResult
from person import Person # Added
from game_object import GameObject, Container # Added

from typing import Dict, Any, Tuple, Awaitable, Callable, List, Optional

# Added for schema debugging
from pydantic.json_schema import models_json_schema

# Third-party imports
try:
    from agents import Agent, Runner, function_tool, \
        RunContextWrapper # Added RunContextWrapper here
except ImportError:
    print("\\nERROR: Could not import 'agents'.")
    print("Please ensure the OpenAI Agents SDK is installed correctly.")
    raise
try:
    from openai import OpenAI, OpenAIError, BadRequestError
    from pydantic import BaseModel, Field, ValidationError
except ImportError:
    print("\\nERROR: Could not import 'openai' or 'pydantic'.")
    print("Please install them (`pip install openai pydantic`).")
    raise
try:
    from deepgram import (
        DeepgramClient,
        PrerecordedOptions,
        FileSource
    )
except ImportError:
    print("\\nERROR: Could not import 'deepgram'.")
    print("Please install it (`pip install deepgram-sdk`).")
    raise

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
# Create a logger specific to this final agent
logger = logging.getLogger("StorytellerAgentFinal")
if DEBUG_MODE:
    logger.info("🔧 Debug mode enabled for StorytellerAgentFinal.")


# --- Pydantic Models for Storyteller Output --- (Unchanged from direct)
class Answer(BaseModel):
    """Represents a single piece of dialogue or interaction option."""
    type: str = Field(..., description="The type of answer, MUST be 'text'.")
    description: str = Field(
        ...,
        description="Text message with a maximum of 20 words."
    )
    options: List[str] = Field(
        default_factory=list,
        description="List of options, each with a maximum of 5 words."
    )
    isThinking: Optional[bool] = Field(None, description="Indicates if the agent is processing in the background.")


class AnswerSet(BaseModel):
    """The required JSON structure for all storyteller responses."""
    answers: List[Answer]
    model_config = {
        "json_schema_extra": {
            "example": {
                "answers": [
                    {"type": "text", "description": "The salty air whips around you.", "options": []},
                    {"type": "text", "description": "What will you do?", "options": ["Look around", "Check map"]}
                ]
            }
        }
    }

# --- Helper Code Copied from agent_puppet_master.py ---

class DirectionHelper:
    """Helper class for handling relative directions and movement."""
    @staticmethod
    def get_relative_position(current_pos: Tuple[int, int], direction: str) -> Tuple[int, int]:
        x, y = current_pos
        direction = direction.lower()
        if direction == "left": return (x - 1, y)
        if direction == "right": return (x + 1, y)
        if direction == "up": return (x, y - 1)
        if direction == "down": return (x, y + 1)
        return current_pos

    @staticmethod
    def get_direction_vector(from_pos: Tuple[int, int], to_pos: Tuple[int, int]) -> Tuple[int, int]:
        fx, fy = from_pos
        tx, ty = to_pos
        return (tx - fx, ty - fy)

    @staticmethod
    def get_direction_name(direction: Tuple[int, int]) -> str:
        dx, dy = direction
        if dx == -1 and dy == 0: return "left"
        if dx == 1 and dy == 0: return "right"
        if dx == 0 and dy == -1: return "up"
        if dx == 0 and dy == 1: return "down"
        return "unknown"

    @staticmethod
    async def move_continuously(story_result: CompleteStoryResult, direction: str) -> str:
        logger.info(f"🔄 Starting continuous movement: {direction} from {story_result.person.position}")
        moves = 0
        max_moves = 50
        
        # Get storyteller reference for WebSocket commands
        storyteller = getattr(story_result, '_storyteller_agent', None)
        can_send_websocket = storyteller and hasattr(storyteller, 'send_command_to_frontend')
        
        while moves < max_moves:
            current_pos = story_result.person.position
            target_pos = DirectionHelper.get_relative_position(current_pos, direction)
            logger.debug(f"  Continuous move attempt #{moves + 1}: {current_pos} -> {target_pos}")
            result = story_result.person.move(story_result.environment, target_pos, False)
            
            if not result["success"]:
                logger.info(f"🛑 Continuous movement stopped: {result['message']}")
                stop_reason = f"stopped: {result['message']}"
                return f"Moved {moves} steps {direction} and {stop_reason}"
                
            sync_story_state(story_result) # Sync after successful move
            moves += 1
            
            # Send a WebSocket command for this single step to animate on frontend
            if can_send_websocket:
                try:
                    # Create command params for frontend - always single movement 
                    command_params = {
                        "direction": direction,
                        "is_running": False,
                        "continuous": False  # Always single movement for frontend
                    }
                    
                    # Result text for this step
                    step_result = f"Step {moves}: Moved {direction} to {story_result.person.position}"
                    
                    # Send command to frontend
                    logger.info(f"🚀 CONTINUOUS: Sending step {moves} move to frontend: {direction}")
                    await storyteller.send_command_to_frontend("move", command_params, step_result)
                    
                    # Add a small delay between steps to let frontend animate
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"❌ CONTINUOUS: Error sending WebSocket command: {e}")
            
            # Check for edge or next obstacle *before* next loop
            next_pos_check = DirectionHelper.get_relative_position(story_result.person.position, direction)
            if not story_result.environment.is_valid_position(next_pos_check):
                logger.info(f"🌍 Reached board edge at {story_result.person.position}")
                return f"Moved {moves} steps {direction} and reached the edge."
            elif not story_result.environment.can_move_to(next_pos_check):
                 obstacle = story_result.environment.get_object_at(next_pos_check)
                 obstacle_name = obstacle.name if obstacle else "an obstacle"
                 logger.info(f"🚧 Reached {obstacle_name} at {next_pos_check}")
                 return f"Moved {moves} steps {direction} and reached {obstacle_name}."
                 
        logger.warning(f"⚠️ Hit move limit ({max_moves}) moving {direction}")
        return f"Moved {moves} steps {direction} and stopped (max distance)."

def sync_story_state(story_result: CompleteStoryResult):
    """Synchronize the story state (nearby objects, entity maps)."""
    logger.debug("🔄 Syncing story state...")
    if not hasattr(story_result, 'person') or not story_result.person:
        logger.warning("❌ Cannot sync: No person in story_result.")
        return
    if not hasattr(story_result, 'environment') or not story_result.environment:
        logger.warning("❌ Cannot sync: No environment in story_result.")
        return
    if not hasattr(story_result, 'entities') or story_result.entities is None: # Check for None too
        logger.warning("❌ Cannot sync: No entities list in story_result.")
        story_result.entities = [] # Initialize if missing

    # Ensure environment has necessary attributes
    if not hasattr(story_result.environment, '_position_map'):
        story_result.environment._position_map = {}
    if not hasattr(story_result.environment, '_entity_map'):
        story_result.environment._entity_map = {}

    story_result.environment._position_map.clear()
    story_result.environment._entity_map.clear()

    # Populate maps
    for entity in story_result.entities:
        entity_id = getattr(entity, 'id', None)
        if entity_id:
             story_result.environment._entity_map[entity_id] = entity

        position = None
        pos_attr = getattr(entity, 'position', None)
        if pos_attr:
            if hasattr(pos_attr, 'x') and hasattr(pos_attr, 'y'):
                position = (pos_attr.x, pos_attr.y)
            elif isinstance(pos_attr, (tuple, list)) and len(pos_attr) >= 2:
                position = (pos_attr[0], pos_attr[1])

        if position:
            if position not in story_result.environment._position_map:
                story_result.environment._position_map[position] = []
            story_result.environment._position_map[position].append(entity)

    # Patch environment methods if they don't exist (idempotent)
    if not hasattr(story_result.environment.__class__, '_get_entities_at_patched'):
        def get_entities_at_patched(self, position):
            if hasattr(position, 'x') and hasattr(position, 'y'): pos_tuple = (position.x, position.y)
            elif isinstance(position, (tuple, list)) and len(position) >= 2: pos_tuple = (position[0], position[1])
            else: pos_tuple = position # Assume tuple if not object/list
            return self._position_map.get(pos_tuple, [])
        story_result.environment.__class__.get_entities_at = get_entities_at_patched
        story_result.environment.__class__._get_entities_at_patched = True

    if not hasattr(story_result.environment.__class__, '_get_object_at_patched'):
        def get_object_at_patched(self, position):
            entities = self.get_entities_at(position)
            # Prioritize GameObjects (movable, etc.) over basic Entities
            for entity in entities:
                if isinstance(entity, GameObject): return entity
            # Fallback: return first entity if no GameObject found
            return entities[0] if entities else None
        story_result.environment.__class__.get_object_at = get_object_at_patched
        story_result.environment.__class__._get_object_at_patched = True

    # Update nearby_objects using person's look() method
    if hasattr(story_result.person, 'look') and callable(story_result.person.look):
         look_result = story_result.person.look(story_result.environment)
         if look_result.get("success", False):
             story_result.nearby_objects = {obj.id: obj for obj in look_result.get("objects", []) if hasattr(obj, 'id')}
             logger.debug(f"👀 Found {len(story_result.nearby_objects)} nearby objects after sync.")
         else:
             logger.warning(f"⚠️ Person look failed during sync: {look_result.get('message')}")
             story_result.nearby_objects = {} # Clear if look fails
    else:
         logger.warning("🤷 Person object missing 'look' method, cannot update nearby_objects.")
         story_result.nearby_objects = {} # Ensure it exists

    logger.debug("✅ Story state sync complete.")


def get_weight_description(weight: int) -> str:
    """Convert a numerical weight to a descriptive term."""
    if weight <= 1: return "very light"
    if weight <= 3: return "light"
    if weight <= 5: return "moderately heavy"
    if weight <= 8: return "heavy"
    return "extremely heavy"

# --- Tool Definitions Copied from agent_puppet_master.py ---

# NOTE: These tools now operate directly on the ctx.context (CompleteStoryResult)
# They need access to story_result.person, story_result.environment, etc.

@function_tool
async def move(ctx: RunContextWrapper[CompleteStoryResult], direction: str, is_running: bool, continuous: bool) -> str:
    """Move the player in a given direction (up, down, left, right).
    
    Args:
        ctx: The RunContext containing the game state.
        direction: Direction to move (up, down, left, right).
        is_running: Whether to run (move faster) or walk.
        continuous: Whether to keep moving until hitting obstacle.
        
    Returns:
        str: Description of the movement result
    """
    try:
        # Normalize direction parameter to ensure compatibility with frontend
        direction = direction.lower()
        # Convert compass directions to cardinal directions
        if direction == "north": direction = "up"
        elif direction == "south": direction = "down"
        elif direction == "east": direction = "right"
        elif direction == "west": direction = "left"
        
        story_result = ctx.context
        person = story_result.person
        environment = story_result.environment
        
        # Make sure position exists
        if person.position is None:
            person.position = (20, 20)  # Default starting position
            
        orig_pos = person.position
        logger.info(f"🏃 Starting {'continuous ' if continuous else ''}movement: {direction} from {orig_pos}")
        
        # Always use single movement when sending to frontend to prevent continuous movement
        # loops, even if the backend was requested to do continuous movement
        frontend_continuous = False  # Override continuous flag for frontend
        
        if continuous:
            # Call the helper to keep moving until hitting obstacle
            return await DirectionHelper.move_continuously(story_result, direction)
            
        # Single step movement
        # Calculate target position based on current position and direction
        current_x, current_y = person.position
        target_x, target_y = current_x, current_y
        
        # Determine new position based on direction
        if direction == "up":
            target_y += 1
        elif direction == "down":
            target_y -= 1
        elif direction == "left":
            target_x -= 1
        elif direction == "right":
            target_x += 1
            
        target_position = (target_x, target_y)
        logger.info(f"🎯 Target position: {target_position}")

        # Attempt the move in the backend
        result = person.move(environment, target_position, is_running)
        
        # Get speed and result text
        speed_text = "ran to" if is_running else "walked to"
        result_text = f"Successfully {speed_text} {target_position}. Now at {person.position}."
        
        if result["success"]:
            # Update state after successful move
            sync_story_state(story_result)
            
            # DIRECT WEBSOCKET COMMAND: Send move command to frontend
            # Access the StorytellerAgentFinal instance through the story_result
            storyteller = getattr(story_result, '_storyteller_agent', None)
            
            if storyteller and hasattr(storyteller, 'send_command_to_frontend'):
                try:
                    # Create command params for frontend
                    command_params = {
                        "direction": direction,
                        "is_running": is_running,
                        "continuous": frontend_continuous  # Always use single movement for frontend
                    }
                    
                    # Send command to frontend
                    logger.info(f"🚀 TOOL: Sending move command to frontend via websocket: direction={direction}, continuous={frontend_continuous}")
                    await storyteller.send_command_to_frontend("move", command_params, result_text)
                    logger.info(f"✅ TOOL: Command sent to frontend")
                except Exception as e:
                    logger.error(f"❌ TOOL: Error sending WebSocket command: {e}")
            else:
                logger.warning(f"⚠️ TOOL: Could not access storyteller agent to send WebSocket command")
            
            return result_text
        else:
            return f"Couldn't move {direction}: {result['message']}"
    except Exception as e:
        logger.error(f"💥 TOOL: Error during movement: {str(e)}", exc_info=True)
        return f"Error during movement: {str(e)}"

@function_tool
async def jump(ctx: RunContextWrapper[CompleteStoryResult], target_x: int, target_y: int) -> str:
    """Jump the player character over one square to land at the target coordinates (target_x, target_y)."""
    logger.info(f"🤸 Tool: jump(target_x={target_x}, target_y={target_y})")
    try:
        story_result = ctx.context
        if not story_result.person: return "❌ Error: Player character not found."
        current_pos = story_result.person.position
        logger.debug(f"  Attempting jump: {current_pos} -> ({target_x}, {target_y})")
        result = story_result.person.jump(story_result.environment, (target_x, target_y))
        result_msg = result["message"]
        logger.info(f"  Jump result: {'✅ Success' if result['success'] else '❌ Failed'} - {result_msg}")
        
        if result["success"]:
            sync_story_state(story_result)
            
            # Send jump command directly to frontend
            storyteller = getattr(story_result, '_storyteller_agent', None)
            
            if storyteller and hasattr(storyteller, 'send_command_to_frontend'):
                try:
                    # Create command params
                    command_params = {
                        "target_x": target_x,
                        "target_y": target_y
                    }
                    
                    # Send command to frontend
                    logger.info(f"🚀 TOOL: Sending jump command to frontend via websocket")
                    await storyteller.send_command_to_frontend("jump", command_params, result_msg)
                    logger.info(f"✅ TOOL: Jump command sent to frontend")
                except Exception as e:
                    logger.error(f"❌ TOOL: Error sending jump command: {e}")
            else:
                logger.warning(f"⚠️ TOOL: Could not access storyteller agent to send jump command")
        
        return result_msg
    except Exception as e:
        logger.error(f"💥 TOOL: Error during jump: {str(e)}", exc_info=True)
        return f"Error during jump: {str(e)}"

@function_tool
async def push(ctx: RunContextWrapper[CompleteStoryResult], object_id: str, direction: str) -> str:
    """Push a specified object (by object_id) in a given direction ('left', 'right', 'up', 'down'). Player moves into the object's original space."""
    logger.info(f"👉 Tool: push(object_id='{object_id}', direction='{direction}')")
    story_result = ctx.context
    if not story_result.person: return "❌ Error: Player character not found."
    sync_story_state(story_result) # Ensure nearby_objects is up-to-date
    if object_id not in story_result.nearby_objects:
        return f"❓ Cannot push '{object_id}'. It's not nearby."
    obj = story_result.nearby_objects[object_id]
    if not hasattr(obj, 'position') or not obj.position:
         return f"❓ Cannot push '{object_id}'. It has no position."
    logger.debug(f"  Attempting push: Player at {story_result.person.position}, Object '{obj.name}' at {obj.position}")
    target_pos = DirectionHelper.get_relative_position(obj.position, direction)
    push_vector = DirectionHelper.get_direction_vector(obj.position, target_pos)
    result = story_result.person.push(story_result.environment, obj.position, push_vector)
    result_msg = result["message"]
    logger.info(f"  Push result: {'✅ Success' if result['success'] else '❌ Failed'} - {result_msg}")
    if result["success"]:
        sync_story_state(story_result)
    return result_msg

@function_tool
async def pull(ctx: RunContextWrapper[CompleteStoryResult], object_x: int, object_y: int) -> str:
    """Pull an object located at (object_x, object_y) towards the player. Player moves back one step, object takes player's original space."""
    logger.info(f"👈 Tool: pull(object_x={object_x}, object_y={object_y})")
    story_result = ctx.context
    if not story_result.person: return "❌ Error: Player character not found."
    target_obj_pos = (object_x, object_y)
    logger.debug(f"  Attempting pull: Player at {story_result.person.position}, Object at {target_obj_pos}")
    result = story_result.person.pull(story_result.environment, target_obj_pos)
    result_msg = result["message"]
    logger.info(f"  Pull result: {'✅ Success' if result['success'] else '❌ Failed'} - {result_msg}")
    if result["success"]:
        sync_story_state(story_result)
    return result_msg

@function_tool
async def get_from_container(ctx: RunContextWrapper[CompleteStoryResult], container_id: str, item_id: str) -> str:
    """Get an item (by item_id) from a container (by container_id) and add it to player inventory."""
    logger.info(f"📥 Tool: get_from_container(container_id='{container_id}', item_id='{item_id}')")
    story_result = ctx.context
    if not story_result.person: return "❌ Error: Player character not found."
    sync_story_state(story_result) # Ensure nearby_objects is up-to-date
    accessible_containers = {
        obj_id: obj for obj_id, obj in story_result.nearby_objects.items()
        if isinstance(obj, Container) # Check type directly
    }
    if container_id not in accessible_containers:
        return f"❓ Cannot find container '{container_id}' nearby."
    container = accessible_containers[container_id]
    logger.debug(f"  Attempting get: Item '{item_id}' from Container '{container.name}'")
    result = story_result.person.get_from_container(container, item_id)
    result_msg = result["message"]
    logger.info(f"  Get result: {'✅ Success' if result['success'] else '❌ Failed'} - {result_msg}")
    # No explicit sync needed here, inventory/container state handled by person method
    return result_msg

@function_tool
async def put_in_container(ctx: RunContextWrapper[CompleteStoryResult], container_id: str, item_id: str) -> str:
    """Put an item (by item_id) from player inventory into a container (by container_id)."""
    logger.info(f"📤 Tool: put_in_container(container_id='{container_id}', item_id='{item_id}')")
    story_result = ctx.context
    if not story_result.person: return "❌ Error: Player character not found."
    sync_story_state(story_result) # Ensure nearby_objects is up-to-date
    accessible_containers = {
        obj_id: obj for obj_id, obj in story_result.nearby_objects.items()
        if isinstance(obj, Container)
    }
    if container_id not in accessible_containers:
        return f"❓ Cannot find container '{container_id}' nearby."
    container = accessible_containers[container_id]
    logger.debug(f"  Attempting put: Item '{item_id}' into Container '{container.name}'")
    result = story_result.person.put_in_container(item_id, container)
    result_msg = result["message"]
    logger.info(f"  Put result: {'✅ Success' if result['success'] else '❌ Failed'} - {result_msg}")
    # No explicit sync needed here
    return result_msg

@function_tool
async def use_object_with(ctx: RunContextWrapper[CompleteStoryResult], item1_id: str, item2_id: str) -> str:
    """Use an item from inventory (item1_id) with another object (item2_id, can be in world or inventory)."""
    logger.info(f"🛠️ Tool: use_object_with(item1_id='{item1_id}', item2_id='{item2_id}')")
    story_result = ctx.context
    if not story_result.person: return "❌ Error: Player character not found."
    sync_story_state(story_result) # Sync state before use action
    logger.debug(f"  Attempting use: Item1 '{item1_id}' with Item2 '{item2_id}'")
    result = story_result.person.use_object_with(item1_id, item2_id, story_result.environment, story_result.nearby_objects)
    result_msg = result["message"]
    logger.info(f"  Use result: {'✅ Success' if result['success'] else '❌ Failed'} - {result_msg}")
    if result["success"]:
        sync_story_state(story_result) # Sync state after successful use action
    return result_msg

@function_tool
async def look_around(ctx: RunContextWrapper[CompleteStoryResult]) -> str:
    """Look around the player in a 7x7 square area, revealing all objects and terrain features."""
    logger.info("👀 Tool: look_around()")
    story_result = ctx.context
    if not story_result.person: return "❌ Error: Player character not found."
    sync_story_state(story_result) # Crucial to update nearby_objects first
    
    player_pos = story_result.person.position
    logger.debug(f"  Looking around from position: {player_pos}")
    
    # Define scan radius (3 tiles in each direction for a 7x7 grid)
    SCAN_RADIUS = 3
    
    descriptions = ["You scan the area around you:"]
    objects_found = []
    objects_by_distance = {}  # Group objects by Manhattan distance for organized output
    
    # Get terrain description for context
    terrain_desc = getattr(story_result, 'terrain_description', None)
    if terrain_desc:
        descriptions.append(f"Terrain: {terrain_desc}")
    
    # Scan the entire 7x7 area
    for dy in range(-SCAN_RADIUS, SCAN_RADIUS + 1):
        for dx in range(-SCAN_RADIUS, SCAN_RADIUS + 1):
            # Skip the center (player's position)
            if dx == 0 and dy == 0:
                continue
                
            # Calculate target position
            check_x = player_pos[0] + dx
            check_y = player_pos[1] + dy
            check_pos = (check_x, check_y)
            
            # Calculate Manhattan distance for sorting
            manhattan_distance = abs(dx) + abs(dy)
            
            # Check if position is valid
            if not story_result.environment.is_valid_position(check_pos):
                # Add to appropriate distance group
                if manhattan_distance not in objects_by_distance:
                    objects_by_distance[manhattan_distance] = []
                    
                # Get compass direction for better context
                direction = get_direction_label(dx, dy)
                objects_by_distance[manhattan_distance].append(
                    f"  • {direction} ({check_x},{check_y}): Edge of the map"
                )
                continue
                
            # Check what's at this position
            can_move = story_result.environment.can_move_to(check_pos)
            entities_at_pos = story_result.environment.get_entities_at(check_pos)
            
            # If there are entities or it's impassable terrain, describe it
            if entities_at_pos or not can_move:
                if manhattan_distance not in objects_by_distance:
                    objects_by_distance[manhattan_distance] = []
                
                direction = get_direction_label(dx, dy)
                
                if entities_at_pos:
                    for entity in entities_at_pos:
                        obj_name = getattr(entity, 'name', 'unknown object')
                        obj_id = getattr(entity, 'id', 'unknown_id')
                        objects_by_distance[manhattan_distance].append(
                            f"  • {direction} ({check_x},{check_y}): {obj_name} ({obj_id})"
                        )
                        objects_found.append(entity)
                elif not can_move:
                    objects_by_distance[manhattan_distance].append(
                        f"  • {direction} ({check_x},{check_y}): Impassable terrain"
                    )
    
    # Add objects at the player's position
    entities_at_player = story_result.environment.get_entities_at(player_pos)
    if len(entities_at_player) > 1:  # More than just the player
        descriptions.append("At your position:")
        for entity in entities_at_player:
            if entity != story_result.person:  # Don't include the player
                obj_name = getattr(entity, 'name', 'unknown object')
                obj_id = getattr(entity, 'id', 'unknown_id')
                descriptions.append(f"  • {obj_name} ({obj_id})")
                objects_found.append(entity)
                
    # Build description sorted by distance (nearest first)
    for distance in sorted(objects_by_distance.keys()):
        descriptions.append(f"Distance {distance} from you:")
        descriptions.extend(objects_by_distance[distance])
    
    # Handle case where nothing was found
    if len(descriptions) <= 2:  # Just the initial line and maybe terrain
        descriptions.append("You don't see anything notable around you.")
    
    result_msg = "\n".join(descriptions)
    logger.info(f"  Look result: Found {len(objects_found)} objects in a 7x7 area.")
    
    # Update nearby_objects with what we found
    story_result.nearby_objects.update({obj.id: obj for obj in objects_found if hasattr(obj, 'id')})
    
    return result_msg

# Helper function to get a readable direction label
def get_direction_label(dx: int, dy: int) -> str:
    """Convert relative coordinates to a readable compass direction."""
    if dx == 0:
        return "North" if dy < 0 else "South"
    elif dy == 0:
        return "East" if dx > 0 else "West"
    else:
        ns = "North" if dy < 0 else "South"
        ew = "East" if dx > 0 else "West"
        return f"{ns}{ew}"

@function_tool
async def look_at(ctx: RunContextWrapper[CompleteStoryResult], object_id: str) -> str:
    """Look closely at a specific object (by object_id) either nearby or in inventory to get its description."""
    logger.info(f"👁️ Tool: look_at(object_id='{object_id}')")
    # This is essentially the same as examine_object, we can alias it or call examine directly.
    # Let's call examine_object for consistency.
    return await examine_object(ctx, object_id)

@function_tool
async def say(ctx: RunContextWrapper[CompleteStoryResult], message: str) -> str:
    """Make the player character say a message out loud."""
    logger.info(f"💬 Tool: say(message='{message[:50]}...')")
    story_result = ctx.context
    if not story_result.person: return "❌ Error: Player character not found."
    result = story_result.person.say(message)
    result_msg = result["message"]
    logger.info(f"  Say result: {result_msg}")
    # No state change, no sync needed
    return result_msg

@function_tool
async def check_inventory(ctx: RunContextWrapper[CompleteStoryResult]) -> str:
    """Check the player's inventory (legacy). Use 'inventory' instead for better formatting."""
    logger.info("🎒 Tool: check_inventory() (Legacy)")
    story_result = ctx.context
    if not story_result.person: return "❌ Error: Player character not found."
    if not hasattr(story_result.person, 'inventory') or not story_result.person.inventory:
        return f"{story_result.person.name} has no inventory."
    if not story_result.person.inventory.contents:
        return f"{story_result.person.name}'s inventory is empty."
    items = story_result.person.inventory.contents
    item_descriptions = [f"- {item.id}: {getattr(item, 'name', 'Unknown Item')}" for item in items]
    result_msg = f"{story_result.person.name}'s inventory contains:\n" + "\n".join(item_descriptions)
    logger.info("  Checked inventory (legacy format).")
    return result_msg

@function_tool
async def inventory(ctx: RunContextWrapper[CompleteStoryResult]) -> str:
    """Check the player's inventory and list the items contained within."""
    logger.info("🎒 Tool: inventory()")
    story_result = ctx.context
    if not story_result.person: return "❌ Error: Player character not found."
    if not hasattr(story_result.person, 'inventory') or not story_result.person.inventory:
        return f"{story_result.person.name} has no inventory."

    items = story_result.person.inventory.contents
    if not items:
        return "Your inventory is empty."

    item_descriptions = []
    for item in items:
        desc = getattr(item, 'name', 'Unknown Item')
        weight = getattr(item, 'weight', None)
        if weight is not None:
            desc += f" (Weight: {weight})"
        item_descriptions.append(f"- {desc}")

    result_msg = "You check your inventory. It contains:\n" + "\n".join(item_descriptions)
    logger.info(f"  Inventory check result: Found {len(items)} items.")
    return result_msg

@function_tool
async def examine_object(ctx: RunContextWrapper[CompleteStoryResult], object_id: str) -> str:
    """Examine an object (by object_id) nearby or in inventory to get a detailed description including its properties and state."""
    logger.info(f"🔍 Tool: examine_object(object_id='{object_id}')")
    story_result = ctx.context
    if not story_result.person: return "❌ Error: Player character not found."
    sync_story_state(story_result) # Ensure lists are up-to-date

    target_obj = None
    source = None

    # 1. Check nearby objects
    if hasattr(story_result, 'nearby_objects') and object_id in story_result.nearby_objects:
        target_obj = story_result.nearby_objects[object_id]
        source = "nearby"
        logger.debug(f"  Found '{object_id}' nearby.")

    # 2. Check inventory if not found nearby
    if not target_obj and hasattr(story_result.person, 'inventory'):
        for item in story_result.person.inventory.contents:
            if hasattr(item, 'id') and item.id == object_id:
                target_obj = item
                source = "inventory"
                logger.debug(f"  Found '{object_id}' in inventory.")
                break

    # 3. Check all entities if still not found (fallback)
    if not target_obj and hasattr(story_result, 'entities'):
         if story_result.environment._entity_map and object_id in story_result.environment._entity_map:
              target_obj = story_result.environment._entity_map[object_id]
              source = "world"
              logger.debug(f"  Found '{object_id}' in world entities map.")

    if not target_obj:
        logger.warning(f"  Object '{object_id}' not found.")
        return f"You can't find anything called '{object_id}' to examine."

    # Build description
    name = getattr(target_obj, 'name', 'the object')
    desc_list = [f"You examine {name} ({object_id}):"]

    base_desc = getattr(target_obj, 'description', None)
    if base_desc: desc_list.append(f"- Description: {base_desc}")

    position = getattr(target_obj, 'position', None)
    if position and source != "inventory": desc_list.append(f"- Location: ({position[0]},{position[1]})")

    weight = getattr(target_obj, 'weight', None)
    if weight is not None: desc_list.append(f"- Weight: {weight} ({get_weight_description(weight)})")

    if hasattr(target_obj, 'is_movable'): desc_list.append(f"- Movable: {'Yes' if target_obj.is_movable else 'No'}")
    if hasattr(target_obj, 'is_jumpable'): desc_list.append(f"- Jumpable: {'Yes' if target_obj.is_jumpable else 'No'}")
    if hasattr(target_obj, 'is_collectable'): desc_list.append(f"- Collectable: {'Yes' if target_obj.is_collectable else 'No'}")

    usable_with = getattr(target_obj, 'usable_with', None)
    if usable_with: desc_list.append(f"- Usable with: {', '.join(usable_with)}")

    possible_actions = getattr(target_obj, 'possible_actions', None)
    if possible_actions: desc_list.append(f"- Actions: {', '.join(possible_actions)}")

    state = getattr(target_obj, 'state', None)
    if state: desc_list.append(f"- State: {state}")

    # Container specific details
    if isinstance(target_obj, Container):
        is_open = getattr(target_obj, 'is_open', False)
        desc_list.append(f"- Container Status: {'Open' if is_open else 'Closed'}")
        desc_list.append(f"- Capacity: {getattr(target_obj, 'capacity', 'N/A')}")
        contents = getattr(target_obj, 'contents', [])
        if is_open:
            if contents:
                item_names = [getattr(item, 'name', 'an item') for item in contents]
                desc_list.append(f"- Contains: {', '.join(item_names)}")
            else:
                desc_list.append("- It's empty.")
        else:
             desc_list.append("- You can't see inside while it's closed.")

    result_msg = "\n".join(desc_list)
    logger.info(f"  Examination complete for '{object_id}'.")
    return result_msg


@function_tool
async def execute_movement_sequence(ctx: RunContextWrapper[CompleteStoryResult], commands: List[Dict[str, Any]]) -> str:
    """Execute a sequence of movement commands ('move', 'jump') provided as a list. Stops if any command fails."""
    logger.info(f"⏯️ Tool: execute_movement_sequence(commands={len(commands)})")
    story_result = ctx.context
    if not story_result.person: return "❌ Error: Player character not found."
    results = []
    logger.debug(f"  Commands: {json.dumps(commands, indent=2)}")
    for i, cmd in enumerate(commands):
        tool_name = cmd.get('tool')
        params = cmd.get('parameters', {})
        logger.debug(f"  Executing command #{i+1}: {tool_name} with params {params}")
        step_result = ""
        success = False
        try:
            if tool_name == 'move':
                direction = params.get('direction')
                is_running = params.get('is_running', False)
                continuous = params.get('continuous', False) # Note: Continuous within sequence might be complex
                if direction:
                     step_result = await move(ctx, direction, is_running, continuous)
                     # Check if move was successful (crude check, depends on message format)
                     if "moved" in step_result.lower() or "reached" in step_result.lower() or "already there" in step_result.lower() : success = True
                     else: success = False
                else:
                     step_result = "Move command missing direction."
                     success = False
            elif tool_name == 'jump':
                target_x = params.get('target_x')
                target_y = params.get('target_y')
                if target_x is not None and target_y is not None:
                    step_result = await jump(ctx, target_x, target_y)
                    if "jumped" in step_result.lower(): success = True
                    else: success = False
                else:
                    step_result = "Jump command missing target coordinates."
                    success = False
            else:
                step_result = f"Unknown movement command: {tool_name}"
                success = False

            results.append(f"Step {i+1} ({tool_name}): {step_result}")
            logger.info(f"  Step {i+1} result: {'✅ Success' if success else '❌ Failed'} - {step_result}")

            if not success:
                results.append("Sequence stopped due to failure.")
                logger.warning("  Movement sequence stopped due to failure.")
                break
        except Exception as e:
            logger.error(f"  Error executing step {i+1}: {e}", exc_info=True)
            results.append(f"Step {i+1} ({tool_name}): Error - {e}")
            results.append("Sequence stopped due to error.")
            break

    result_msg = "\n".join(results)
    logger.info("🏁 Movement sequence finished.")
    return result_msg

# Add the continuous move tool separately if needed (move handles continuous flag now)
# @function_tool
# async def move_continuously(ctx: RunContextWrapper[CompleteStoryResult], direction: str) -> str:
#     """Move continuously in a direction ('left', 'right', 'up', 'down') until an obstacle or edge is reached."""
#     logger.info(f"↔️ Tool: move_continuously(direction='{direction}')")
#     story_result = ctx.context
#     if not story_result.person: return "❌ Error: Player character not found."
#     # Call the static helper method directly
#     result_msg = await DirectionHelper.move_continuously(story_result, direction)
#     logger.info(f"  Continuous move result: {result_msg}")
#     # Syncing is handled within the helper now
#     return result_msg


# List of all available tools for the agent
ALL_GAME_TOOLS = [
    move,
    jump,
    push,
    pull,
    get_from_container,
    put_in_container,
    use_object_with,
    look_around,
    look_at, # Alias for examine
    say,
    check_inventory, # Legacy
    inventory, # Preferred inventory check
    examine_object,
    # Temporarily remove this tool until we fix the schema issue
    # execute_movement_sequence,
    # move_continuously # Covered by move(continuous=True)
]


# --- Storyteller Agent Class (FINAL VERSION) ---

class StorytellerAgentFinal:
    def __init__(
            self,
            # puppet_master_agent: Agent, # REMOVED
            complete_story_result: CompleteStoryResult,
            openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY"),
            deepgram_api_key: Optional[str] = os.getenv("DEEPGRAM_API_KEY"),
            voice: str = "nova",
            websocket = None  # Add websocket parameter
    ):
        logger.info("🚀 Initializing StorytellerAgentFinal...")
        self.openai_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.deepgram_key = deepgram_api_key or os.getenv("DEEPGRAM_API_KEY")
        self.voice = voice or os.getenv("CHARACTER_VOICE") or "nova"
        self.websocket = websocket  # Store the websocket connection

        if not self.openai_key: raise ValueError("❌ OpenAI API key is required.")
        if not self.deepgram_key: logger.warning("⚠️ Deepgram API key missing, voice input won't work.")

        try:
            self.openai_client = OpenAI(api_key=self.openai_key)
            logger.info("✅ Initialized OpenAI client.")
        except Exception as e:
            logger.critical(f"💥 Failed to initialize OpenAI client: {e}", exc_info=True)
            raise

        try:
            self.deepgram_client = DeepgramClient(api_key=self.deepgram_key)
            logger.info("✅ Initialized Deepgram client.")
        except Exception as e:
            logger.critical(f"💥 Failed to initialize Deepgram client: {e}", exc_info=True)
            raise

        # --- Game Context Setup ---
        if not isinstance(complete_story_result, CompleteStoryResult):
            logger.error(f"❌ Invalid complete_story_result type: {type(complete_story_result)}. Expected CompleteStoryResult.")
            # Create a minimal error state context
            env_error_state = Environment(width=0, height=0, grid=[])
            # Ensure Person exists even in error state for tool safety
            error_person = Person(id="error_person", name="Error", position=(0,0))
            self.game_context = CompleteStoryResult(
                theme="Error", environment=env_error_state, person=error_person,
                terrain_description="Error loading story", entity_descriptions={},
                narrative_components={}, entities=[], complete_narrative="",
                error="Invalid story data provided to StorytellerAgentFinal."
            )
        else:
            self.game_context: CompleteStoryResult = complete_story_result
             # Ensure person object exists in the context for tools
            if not hasattr(self.game_context, 'person') or not self.game_context.person:
                 logger.warning("🤔 Game context missing 'person', creating a default one.")
                 # Try to find a person entity or create a default one
                 person_entity = next((e for e in self.game_context.entities if isinstance(e, Person)), None)
                 if person_entity:
                     self.game_context.person = person_entity
                     logger.info(f"🧍 Found existing Person entity '{person_entity.name}' to use.")
                 else:
                     default_pos = (self.game_context.environment.width // 2, self.game_context.environment.height // 2) if self.game_context.environment else (0,0)
                     self.game_context.person = Person(id="player_default", name="Player", position=default_pos)
                     logger.info(f"🧍 Created default Person 'Player' at {default_pos}.")
                     if not hasattr(self.game_context, 'entities') or self.game_context.entities is None:
                         self.game_context.entities = []
                     self.game_context.entities.append(self.game_context.person) # Add to entities list

            # Make sure nearby_objects exists
            if not hasattr(self.game_context, 'nearby_objects'):
                self.game_context.nearby_objects = {}
                
            # Initial state sync
            sync_story_state(self.game_context)
            logger.info(f"✅ Game context loaded. Theme: '{self.game_context.theme}', Person: '{self.game_context.person.name}'")
            if self.game_context.error:
                logger.warning(f"⚠️ Loaded game context has an error: {self.game_context.error}")

        # --- Agent Setup ---
        self.agent_data = self._setup_agent_internal(self.game_context)
        logger.info("✅ Storyteller agent core setup completed.")

    def _setup_agent_internal(self, story_context: CompleteStoryResult) -> Dict[str, Agent]:
        """Sets up the internal OpenAI Agent with integrated tools."""
        logger.info("🛠️ Setting up internal Storyteller Agent core...")
        theme = getattr(story_context, 'theme', 'Unknown Theme')
        quest_title = "the main quest"
        if isinstance(story_context.narrative_components, dict):
            quest_data = story_context.narrative_components.get('quest', {})
            if isinstance(quest_data, dict):
                quest_title = quest_data.get('title', quest_title)

        # --- MODIFIED SYSTEM PROMPT ---
        system_prompt = f"""You are Jan, the Storyteller and Game Master for a '{theme}' themed adventure.

Your Goal: Guide the player through the story, describe the world, react to their actions, and manage the game state using your tools.

Your Responsibilities:
1.  **Narrate:** Describe scenes, events, and the results of player actions vividly. Use the game's theme and tone.
2.  **Respond to Player:** Understand player text or voice input. If it's a command to interact with the world, use the appropriate tool. If it's dialogue or a question, respond in character.
3.  **Use Tools:** You have direct access to tools for player actions (move, look, jump, push, pull, get, put, use, examine, inventory, say). Use these tools when the player wants to perform an action.
4.  **Manage Quest:** Keep track of the current quest: '{quest_title}'. Guide the player towards objectives.
5.  **Format Output:** ALWAYS respond with a JSON object matching the `AnswerSet` schema. Each answer in the list should be short (max 20 words). Provide relevant action options (max 5 words each) in the *last* answer object.
6.  **Game Mechanics:** Adhere to the basic game mechanics (movement, interaction limits, etc.). Reference:
    {get_game_mechanics_reference()}

Example Interaction:
Player: "Look around"
You: (Use 'look_around' tool) -> Tool returns "You see a dusty chest."
Your JSON Response:
```json
{{
  "answers": [
    {{"type": "text", "description": "You scan your surroundings.", "options": []}},
    {{"type": "text", "description": "You see a dusty chest.", "options": ["Examine chest", "Move closer"]}}
  ]
}}
```

Player: "Open the chest"
You: (Use 'examine_object' tool with 'chest' ID) -> Tool returns "The chest is unlocked. It contains a gold key."
Your JSON Response:
```json
{{
  "answers": [
    {{"type": "text", "description": "You try the lid. It creaks open!", "options": []}},
    {{"type": "text", "description": "Inside, you find a gold key.", "options": ["Take key", "Close chest"]}}
  ]
}}
```

IMPORTANT: Use the movement tool (move) when the player wants to move in any direction or go somewhere.
Player commands like 'go east', 'walk left', 'move forward', etc. should use the move tool, not just be described.
Always use the push, pull, and jump tools for those specific actions rather than describing them.

**Important:** Be concise. Ensure every response strictly follows the `AnswerSet` JSON format. Use your tools to make the game world interactive!"""

        try:
            storyteller_agent_core = Agent[CompleteStoryResult]( # Use context type hint
                name="Jan \'The Man\'", # Renamed
                instructions=system_prompt,
                # Provide the actual tool functions directly
                tools=ALL_GAME_TOOLS,
                output_type=AnswerSet, # Expect AnswerSet JSON
                model="gpt-4o" # Or your preferred model
            )
            
            # Add a reference to the parent StorytellerAgentFinal instance
            # This allows tools to access the websocket connection through this reference
            storyteller_agent_core.invoked_by = self
            
            logger.info(f"✅ Internal Agent '{storyteller_agent_core.name}' created with {len(ALL_GAME_TOOLS)} tools.")
            return {"agent": storyteller_agent_core}
        except Exception as e:
            logger.error(f"💥 Unexpected error during Storyteller initialization: {e}")
            traceback.print_exc()
            return

    async def _call_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """Call a tool function by name with the provided input parameters."""
        # This method shouldn't be needed in the original implementation
        logger.error("_call_tool called but not implemented")
        return "Tool execution not implemented"
        
    def update_nearby_objects(self):
        """Updates nearby objects for the player.
        
        This method uses the person's look method to identify objects around the player.
        """
        logger.info("📍 Updating nearby objects")
        
        # Check if game_context and person exist
        if not hasattr(self, 'game_context') or not self.game_context:
            logger.warning("❌ No game context available")
            return
            
        if not hasattr(self.game_context, 'person') or not self.game_context.person:
            logger.warning("❌ No person object in game context")
            return
            
        # Store a reference to self in the context so tools can access it
        self.game_context._storyteller_agent = self
            
        # Initialize nearby_objects if not present
        if not hasattr(self.game_context, 'nearby_objects'):
            self.game_context.nearby_objects = {}
            
        # Use the person's look method if available
        person = self.game_context.person
        if hasattr(person, 'look') and callable(person.look):
            try:
                look_result = person.look(self.game_context.environment)
                if look_result and look_result.get("success", False):
                    nearby_objects = look_result.get("nearby_objects", {})
                    self.game_context.nearby_objects = nearby_objects
                    logger.debug(f"👀 Found {len(nearby_objects)} nearby objects")
                else:
                    logger.warning(f"⚠️ Look operation failed: {look_result.get('message', 'Unknown error')}")
            except Exception as e:
                logger.error(f"💥 Error updating nearby objects: {e}")
        else:
            logger.warning("🤷 Person object missing 'look' method")
        
        # Ensure nearby_objects is not None
        if self.game_context.nearby_objects is None:
            self.game_context.nearby_objects = {}

    def process_user_input_completion(self, response: Dict[str, Any], history: List[Dict[str, Any]], command_info: Optional[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Process the completion result."""
        # This method shouldn't be needed in the original implementation
        logger.error("process_user_input_completion called but not implemented")
        return self._create_error_response("Method not implemented", history)
        
    async def process_text_input(
            self,
            user_input: str,
            conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Process text input from user and return a response object."""
        logger.info(f"⌨️ Processing text input: '{user_input}'")
        
        # Basic history management
        if conversation_history is None:
            conversation_history = []
            
        # Call our minimal nearby_objects update
        self.update_nearby_objects()
        
        try:
            # Get the agent core
            agent_core = self.agent_data.get("agent")
            if not agent_core:
                logger.error("💥 Agent core instance not found!")
                return self._create_error_response("Agent core not initialized.", conversation_history)
                
            # Ensure the invoked_by reference is up to date
            if not hasattr(agent_core, 'invoked_by') or agent_core.invoked_by != self:
                logger.info("🔄 Refreshing agent_core.invoked_by reference to self")
                agent_core.invoked_by = self
                
            # Run the agent
            logger.info(f"🤖 Running agent with input: '{user_input}'")
            run_result = await Runner.run(
                starting_agent=agent_core,
                input=user_input,
                context=self.game_context
            )
            logger.info(f"✅ Agent run completed")
            
            # Extract result data
            final_output = getattr(run_result, 'final_output', None)
            tool_calls = getattr(run_result, 'tool_calls', [])
            
            logger.info(f"📊 Agent output: Final output type: {type(final_output)}, Tool calls: {len(tool_calls)}")
            if tool_calls:
                for i, tool_call in enumerate(tool_calls):
                    tool_name = getattr(tool_call, 'name', 'unknown')
                    logger.info(f"🛠️ Tool call #{i+1}: {tool_name}")
            
            # Handle tool call if present
            if tool_calls:
                # Process first tool call
                tool_call = tool_calls[0]
                tool_name = getattr(tool_call, 'name', 'unknown_tool')
                tool_input = getattr(tool_call, 'input', {})
                tool_output_raw = getattr(tool_call, 'output', "Action performed.")
                tool_output_str = str(tool_output_raw)
                
                logger.info(f"🛠️ Using tool call: '{tool_name}'")
                logger.info(f"  Input: {tool_input}")
                logger.info(f"  Output: {tool_output_str}")
                
                # Translate to game command
                logger.info(f"🎮 Translating tool '{tool_name}' to game command")
                command_info = self._translate_tool_to_game_command(tool_name, tool_input, tool_output_str)
                logger.info(f"🎮 Translated command: {command_info}")
                
                # Get response content
                response_content = final_output.model_dump_json() if isinstance(final_output, AnswerSet) else self._create_basic_answer_json(tool_output_str)
                
                # Prepare command response
                command_response = {
                    "type": "command",
                    "name": command_info["name"],
                    "params": command_info["params"],
                    "result": command_info["result"],
                    "content": response_content,
                    "command_info": command_info
                }
                
                logger.info(f"📤 Returning command response: {command_response['name']}")
                
                # Return command type response
                return command_response, conversation_history
            else:
                # Direct response without tool call
                logger.info("💬 Agent provided direct AnswerSet response (no tool).")
                
                if isinstance(final_output, AnswerSet):
                    response_content = final_output.model_dump_json()
                    return {"type": "json", "content": response_content}, conversation_history
                else:
                    # Fallback for non-AnswerSet output
                    response_content = self._create_basic_answer_json("I'm processing your request.")
                    return {"type": "json", "content": response_content}, conversation_history
                    
        except Exception as e:
            logger.error(f"💥 Error processing text input: {e}", exc_info=True)
            return self._create_error_response(f"Error processing input: {e}", conversation_history)

    def _create_error_response(self, error_message: str, history: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Create a standardized error response."""
        response_content = self._create_basic_answer_json(f"Error: {error_message}", options=["Try again"])
        return {"type": "error", "content": response_content, "error": error_message}, history

    def _create_basic_answer_json(self, message: str, options: List[str] = None) -> str:
        """Create a basic AnswerSet JSON response with the given message."""
        if options is None:
            options = []
        answer_set = AnswerSet(answers=[Answer(type="text", description=message, options=options)])
        return answer_set.model_dump_json()
        
    def _translate_tool_to_game_command(self, tool_name: str, tool_input: Dict[str, Any], tool_output: str) -> Dict[str, Any]:
        """Translates a tool call to a game command for the frontend."""
        logger.info(f"🎮 Translating tool '{tool_name}' to game command")
        
        # Default command info
        command_info = {
            "name": "text",
            "params": {},
            "result": tool_output
        }
        
        # Map tool names to game commands
        if tool_name == "move":
            command_info["name"] = "move"
            
            # Get direction and ensure it's in lowercase for consistency
            direction = tool_input.get("direction", "")
            if direction:
                direction = direction.lower()
                
            # Normalize compass directions to cardinal directions for frontend
            if direction == "north":
                direction = "up"
            elif direction == "south":
                direction = "down"
            elif direction == "east":
                direction = "right"
            elif direction == "west":
                direction = "left"
                
            # Set params with normalized direction
            command_info["params"] = {
                "direction": direction,
                "is_running": tool_input.get("is_running", False),
                "continuous": tool_input.get("continuous", False)
            }
            
            # Debug log for move direction
            logger.info(f"🚶 Move command direction: '{direction}'")
            
        elif tool_name == "jump":
            command_info["name"] = "jump"
            command_info["params"] = {
                "target_x": tool_input.get("target_x", 0),
                "target_y": tool_input.get("target_y", 0)
            }
        elif tool_name == "look_around":
            command_info["name"] = "look"
            command_info["params"] = {}
        elif tool_name == "inventory" or tool_name == "check_inventory":
            command_info["name"] = "inventory"
            command_info["params"] = {}
        
        logger.debug(f"  Command translation: {command_info}")
        return command_info

    async def process_audio(
            self,
            audio_data: bytes,
            on_transcription: Callable[[str], Awaitable[None]],
            on_response: Callable[[str], Awaitable[None]], # Expects JSON string
            on_audio: Callable[[bytes], Awaitable[None]], # MP3 chunks
            conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[str, Dict[str, Any], List[Dict[str, Any]]]: # Returns display text, command info, history
        """Process audio input from user by transcribing and handling the result."""
        logger.info(f"🎤 Processing audio input ({len(audio_data)} bytes)")
        
        if not audio_data or len(audio_data) < 100:
            logger.warning("Audio data too small to process")
            await on_transcription("(Audio too short to process)")
            return "", {}, conversation_history or []
            
        # Transcribe the audio
        try:
            transcript_text = await self.transcribe_audio(audio_data)
            logger.info(f"🎙️ Transcription: '{transcript_text}'")
            
            # Send transcription to client
            await on_transcription(transcript_text)
            
            # Process the transcribed text
            response_data, conversation_history = await self.process_text_input(
                transcript_text, 
                conversation_history or []
            )
            
            # Send response
            response_content = response_data.get("content", "{}")
            await on_response(response_content)
            
            # Generate TTS if there's a content
            if "content" in response_data:
                try:
                    json_content = json.loads(response_data["content"])
                    answers = json_content.get("answers", [])
                    if answers:
                        tts_text = " ".join([a.get("description", "") for a in answers if a.get("description")])
                        if tts_text.strip() and self.openai_client:
                            logger.info(f"🔊 Generating TTS for: '{tts_text[:50]}...'")
                            speech_response = await self.openai_client.audio.speech.create(
                                model="tts-1",
                                voice=self.voice,
                                input=tts_text
                            )
                            
                            # Send audio to client
                            for chunk in speech_response.iter_bytes(chunk_size=4096):
                                await on_audio(chunk)
                                
                            # Signal end of audio
                            await on_audio(b"__AUDIO_END__")
                except Exception as e:
                    logger.error(f"Error generating TTS: {e}")
            
            # Extract command info for return
            command_info = response_data.get("command_info", {})
            
            return transcript_text, command_info, conversation_history or []
        except Exception as e:
            logger.error(f"Error processing audio: {e}", exc_info=True)
            error_response = self._create_basic_answer_json(f"Error processing voice input: {e}")
            await on_response(error_response)
            return f"Error: {e}", {}, conversation_history or []

    async def transcribe_audio(self, audio_data: bytes) -> str:
        """Transcribe audio data to text.
        
        Args:
            audio_data: The audio data in bytes
            
        Returns:
            str: The transcribed text
        """
        logger.info(f"🎙️ Transcribing audio ({len(audio_data)} bytes)")
        
        if not self.deepgram_client:
            raise ValueError("Deepgram client not initialized")
            
        try:
            from deepgram import (
                PrerecordedOptions,
                FileSource
            )
            
            # Create options for transcription
            options = PrerecordedOptions(
                model="nova-2",
                smart_format=True,
                language="en"
            )
            
            # Generate buffer source from bytes
            source = FileSource(buffer=audio_data)
            
            # Get transcription response
            response = await self.deepgram_client.listen.prerecorded.v("1").transcribe_file(source, options)
            
            # Extract transcript from response
            if hasattr(response, 'results') and hasattr(response.results, 'channels') and len(response.results.channels) > 0:
                transcript = response.results.channels[0].alternatives[0].transcript
                return transcript if transcript else ""
            else:
                logger.warning("No transcript found in Deepgram response")
                return ""
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}", exc_info=True)
            raise ValueError(f"Audio transcription failed: {e}")

    async def send_command_to_frontend(self, command_name: str, command_params: Dict[str, Any], result: str = None) -> bool:
        """Send command directly to the frontend via websocket.
        
        Args:
            command_name: The name of the command (move, jump, etc.)
            command_params: Parameters for the command
            result: Optional result message
            
        Returns:
            bool: True if command was sent, False otherwise
        """
        if not self.websocket:
            logger.error("❌ Cannot send command to frontend: No websocket connection available")
            return False
            
        # Create command message
        cmd_data = {
            "type": "command",
            "name": command_name,
            "params": command_params,
            "result": result or f"{command_name.capitalize()} command executed",
            "sender": "system"  # Commands are system messages
        }
        
        try:
            # Convert to JSON and send via websocket
            cmd_json = json.dumps(cmd_data)
            logger.info(f"📤 DIRECT COMMAND TO FRONTEND: {command_name}")
            logger.info(f"📤 COMMAND JSON: {cmd_json}")
            
            # Actually send the command
            await self.websocket.send_text(cmd_json)
            logger.info(f"✅ Command sent successfully to frontend: {command_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send command to frontend: {e}")
            return False


# --- Example Usage (Updated for Final Agent) ---
async def example_run():
    """Example test function."""
    pass
    
if __name__ == "__main__":
    pass
