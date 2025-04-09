import asyncio  # Added for audio processing delays
import heapq  # Add heapq import for PathFinder
import json
import logging
import os
import time
from typing import Dict, Any, Tuple, Awaitable, Callable, List, Optional, Literal
from collections import deque # Import deque for the message queue

from fastapi import WebSocket
from pydantic import BaseModel, Field, field_validator
from pydantic.json_schema import models_json_schema

from agent_copywriter_direct import Environment, CompleteStoryResult, Position
from game_object import Container  # Added
from prompt.storyteller_prompts import get_game_mechanics_reference, get_storyteller_system_prompt

# Global movement command cache for duplicate detection
# Stores {command_key: timestamp} pairs
MOVEMENT_COMMAND_CACHE = {}
# Max age in seconds for a cached command to be considered a duplicate
MOVEMENT_CACHE_TTL = 3.0

# Import shared logging utils

try:
    from openai import OpenAI, OpenAIError, BadRequestError, AssistantEventHandler, AsyncOpenAI
    from openai.types.beta.threads import Run # Import Run for type hinting
    from openai.types.beta.threads.runs import ToolCall # Import ToolCall
    from pydantic import BaseModel, Field, ValidationError
except ImportError:
    print("\\nERROR: Could not import 'openai' or 'pydantic'.")
    print("Please install them (`pip install openai pydantic`).")
    raise
try:
    from deepgram import (
        DeepgramClient,
        PrerecordedOptions,
        FileSource,
        DeepgramClientOptions
    )
except ImportError:
    print("\\nERROR: Could not import 'deepgram'.")
    print("Please install it (`pip install deepgram-sdk`).")
    raise

# --- Constants, Config & Logger Setup ---
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = logging.DEBUG if DEBUG_MODE else logging.INFO
DEFAULT_VOICE = "nova"
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
ASSISTANT_NAME = "Game Storyteller Assistant" # Name to identify/retrieve the assistant
ASSISTANT_MODEL = os.getenv("LLM_MODEL", "gpt-4o")

root_logger = logging.getLogger()
if root_logger.hasHandlers():
    root_logger.handlers.clear()

logging.basicConfig(level=LOG_LEVEL,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("StorytellerAgentFinal")
if DEBUG_MODE:
    logger.info("🔧 Debug mode enabled for StorytellerAgentFinal.")


# --- Utility Functions ---
# Remove log_tool_execution decorator usage from tools later
# We might keep the helper functions if they are generally useful

# Helper to get tool schemas
def get_tool_schemas() -> List[Dict[str, Any]]:
    """Generates the JSON schemas for all available tools."""
    # Manually define schemas for each tool function
    # This could potentially be automated using pydantic or inspect
    # but manual definition ensures correctness for the Assistants API.
    schemas = [
        {
            "type": "function",
            "function": {
                "name": "execute_movement_sequence",
                "description": "Executes a sequence of movement commands (move or jump).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "commands": {
                            "type": "array",
                            "description": "List of movement commands.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "command_type": {"type": "string", "enum": ["move", "jump"]},
                                    "direction": {"type": "string", "enum": ["up", "down", "left", "right"], "description": "Direction for move."},
                                    "is_running": {"type": "boolean", "description": "Whether to run (move)."},
                                    "continuous": {"type": "boolean", "description": "Whether to move continuously (move)."},
                                    "steps": {"type": "integer", "description": "Number of steps (move)."},
                                    "target_x": {"type": "integer", "description": "Target X for jump."},
                                    "target_y": {"type": "integer", "description": "Target Y for jump."},
                                },
                                "required": ["command_type"],
                                # Add logic here or in the function to validate required fields based on command_type
                            }
                        }
                    },
                    "required": ["commands"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "look_around",
                "description": "Looks around the player's current position within a given radius to identify nearby objects and entities.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "radius": {"type": "integer", "description": "How far to look (number of squares, 1-10)."}
                    },
                    "required": ["radius"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_inventory",
                "description": "Checks the player's inventory and lists the items being carried.",
                "parameters": {"type": "object", "properties": {}} # No parameters
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_object_details",
                "description": "Examines a specific nearby object or an item in the inventory to get more details about it.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "object_id": {"type": "string", "description": "The unique ID of the object or item to examine."}
                    },
                    "required": ["object_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "use_object_with",
                "description": "Uses one item (item1_id from inventory) with another item or object (item2_id from inventory or nearby).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "item1_id": {"type": "string", "description": "The ID of the item from inventory to use."},
                        "item2_id": {"type": "string", "description": "The ID of the target item/object (in inventory or nearby)."}
                    },
                    "required": ["item1_id", "item2_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "move_to_object",
                "description": "Moves the player towards an object/location by finding an adjacent path and executing the steps.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_x": {"type": "integer", "description": "The X coordinate of the target object/location."},
                        "target_y": {"type": "integer", "description": "The Y coordinate of the target object/location."}
                    },
                    "required": ["target_x", "target_y"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "move", # Single move command
                "description": "Move the player character step-by-step or continuously in a given cardinal direction.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "direction": {"type": "string", "enum": ["up", "down", "left", "right"], "description": "Cardinal direction."},
                        "is_running": {"type": "boolean", "description": "Whether to run."},
                        "continuous": {"type": "boolean", "description": "If True, move until obstacle/edge."},
                        "steps": {"type": "integer", "description": "Number of steps if continuous is False."}
                    },
                    "required": ["direction", "is_running", "continuous", "steps"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "jump", # Single jump command
                "description": "Makes the player character jump two squares horizontally or vertically over an obstacle.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_x": {"type": "integer", "description": "Destination X coordinate (must be 2 squares away)."},
                        "target_y": {"type": "integer", "description": "Destination Y coordinate (must be 2 squares away)."}
                    },
                    "required": ["target_x", "target_y"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "find_entity_by_type",
                "description": "Finds entities of a specific type in the game environment and returns their locations.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_type": {"type": "string", "description": "The type of entity to search for (e.g. \"log_stool\", \"campfire\", \"chest\")."}
                    },
                    "required": ["entity_type"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "go_to_entity_type",
                "description": "Finds an entity of the specified type and moves the player next to it.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_type": {"type": "string", "description": "The type of entity to find and move to (e.g. \"log_stool\", \"campfire\", \"chest\")."}
                    },
                    "required": ["entity_type"]
                }
            }
        }
    ]
    return schemas



# --- Model Definitions ---

# --- Movement Command Models ---
# (Keep MovementCommand and validation as it's used by execute_movement_sequence)
class MovementCommand(BaseModel):
    """Base model for movement commands."""
    command_type: Literal["move",
    "jump"] = Field(...,
     description="The type of movement command.")
    # Move parameters
    direction: Optional[Literal["up", "down", "left", "right"]] = Field(
        None, description="Direction for move command.")
    is_running: Optional[bool] = Field(
    None, description="Whether to run (move faster).")
    continuous: Optional[bool] = Field(
    None, description="If True, keeps moving until hitting an obstacle or edge.")
    steps: Optional[int] = Field(
    None, description="Number of steps for move command.")
    # Jump parameters
    target_x: Optional[int] = Field(
    None, description="Target X coordinate for jump command.")
    target_y: Optional[int] = Field(
    None, description="Target Y coordinate for jump command.")

    @field_validator("*")
    def validate_command_fields(cls, v, info):
        field_name = info.field_name
        # Pydantic v2 uses model_context for context
        instance_data = info.model_context if hasattr(info, 'model_context') else {}
        command_type = instance_data.get("command_type")

        if command_type == "move":
            if field_name in [
    "direction",
    "is_running",
    "continuous",
     "steps"]:
                if field_name == "direction" and v is None:
                    raise ValueError("direction is required for move command")
                if field_name == "is_running" and v is None:
                    raise ValueError("is_running is required for move command")
                if field_name == "continuous" and v is None:
                    raise ValueError("continuous is required for move command")
                if field_name == "steps" and v is None:
                    raise ValueError("steps is required for move command")
            elif field_name in ["target_x", "target_y"] and v is not None:
                raise ValueError(
                    f"{field_name} should not be set for move command")

        elif command_type == "jump":
            if field_name in ["target_x", "target_y"]:
                if v is None:
                    raise ValueError(
                        f"{field_name} is required for jump command")
            elif field_name in ["direction", "is_running", "continuous", "steps"] and v is not None:
                raise ValueError(
                    f"{field_name} should not be set for jump command")

        return v


# Remove @function_tool decorator
# Remove @log_tool_execution decorator for now (can re-add logging inside)
async def execute_movement_sequence(
    story_context: CompleteStoryResult, # Changed context parameter
    commands: List[MovementCommand]
) -> str:
    """Executes a sequence of movement commands.

    Args:
        story_context: The game state context. # Updated description
        commands: List of movement commands to execute. Each command must specify:
            - command_type: "move" or "jump"
            For move commands:
            - direction: "up", "down", "left", or "right"
            - is_running: whether to run
            - continuous: whether to move continuously
            - steps: number of steps to take
            For jump commands:
            - target_x: destination X coordinate
            - target_y: destination Y coordinate

    Returns:
        str: Description of the movement execution results.
    """
    logger.info(f"Executing movement sequence with {len(commands)} commands.") # Added logging
    results = []

    for i, command in enumerate(commands, 1):
        try:
            if command.command_type == "move":
                if not all(
    x is not None for x in [
        command.direction,
        command.is_running,
        command.continuous,
         command.steps]):
                    results.append(
                        f"Step {i}: Invalid move command - missing required parameters")
                    continue

                # Validate steps is a positive number
                if command.steps <= 0:
                    results.append(
                        f"Step {i}: Invalid move command - steps must be a positive number")
                    continue

                try:
                    result = await _internal_move( # Pass story_context directly
                        story_context,
                        direction=command.direction,
                        is_running=command.is_running,
                        continuous=command.continuous,
                        steps=command.steps
                    )

                    # Ensure result is not None
                    if result is None:
                        results.append(
                            f"Step {i}: Move command failed - no result returned")
                    else:
                        results.append(f"Step {i}: {result}")
                except Exception as move_error:
                    logger.error(f"Error during move command: {move_error}")
                    results.append(f"Step {i}: Move error - {str(move_error)}")

            elif command.command_type == "jump":
                if command.target_x is None or command.target_y is None:
                    results.append(
                        f"Step {i}: Invalid jump command - missing coordinates")
                    continue

                try:
                    result = await _internal_jump( # Pass story_context directly
                        story_context,
                        target_x=command.target_x,
                        target_y=command.target_y
                    )

                    # Ensure result is not None
                    if result is None:
                        results.append(
                            f"Step {i}: Jump command failed - no result returned")
                    else:
                        results.append(f"Step {i}: {result}")
                except Exception as jump_error:
                    logger.error(f"Error during jump command: {jump_error}")
                    results.append(f"Step {i}: Jump error - {str(jump_error)}")

            else:
                results.append(
                    f"Step {i}: Unknown command type '{command.command_type}'")

        except Exception as e:
            logger.error(f"Error executing movement step {i}: {e}")
            results.append(f"Step {i}: Error - {str(e)}")
            break

    final_result = "\n".join(results)
    logger.info(f"Movement sequence result: {final_result}") # Added logging
    return final_result


# --- End Movement Command Models ---


# Keep Answer/AnswerSet for potential direct formatting if needed,
# but Assistant might handle JSON output directly.
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

class AnswerSet(BaseModel):
    """The required JSON structure for all storyteller responses."""
    answers: List[Answer]

# --- Direction Helper ---
# (Keep DirectionHelper as it's used internally by movement logic)
class DirectionHelper:
    """Helper class for handling relative directions and movement.

    Coordinate system:
    - X-axis: Positive values go right, negative values go left
    - Y-axis: Positive values go down, negative values go up
              (inverted compared to traditional Cartesian coordinates to match frontend)

    This matches the frontend Three.js coordinate system and browser coordinate system
    where (0,0) is at the top-left corner.
    """

    # Add cardinal direction mapping for better user experience
    CARDINAL_MAPPING = {
        # Primary directions
        "north": "up",
        "south": "down",
        "east": "right", 
        "west": "left",
        # Accept abbreviations
        "n": "up",
        "s": "down", 
        "e": "right",
        "w": "left",
        # Already correct
        "up": "up",
        "down": "down",
        "left": "left",
        "right": "right"
    }

    @staticmethod
    def normalize_direction(direction: str) -> str:
        """Convert a user-friendly direction to internal direction."""
        direction = direction.lower().strip()
        return DirectionHelper.CARDINAL_MAPPING.get(direction, direction)

    @staticmethod
    def get_relative_position(
        current_pos: Tuple[int, int], direction: str) -> Tuple[int, int]:
        x, y = current_pos
        # Normalize direction first
        direction = DirectionHelper.normalize_direction(direction)
        if direction == "left": return (x - 1, y)
        if direction == "right": return (x + 1, y)
        # FIXED: Direction mapping was inverted. "up" should decrease y, "down"
        # should increase y
        if direction == "up": return (x, y - 1)
        if direction == "down": return (x, y + 1)
        return current_pos

    @staticmethod
    def get_direction_vector(
        from_pos: Tuple[int, int], to_pos: Tuple[int, int]) -> Tuple[int, int]:
        fx, fy = from_pos
        tx, ty = to_pos
        return (tx - fx, ty - fy)

    @staticmethod
    def get_direction_name(direction: Tuple[int, int]) -> str:
        dx, dy = direction
        if dx == -1 and dy == 0: return "left"
        if dx == 1 and dy == 0: return "right"
        # FIXED: Direction mapping to match updated get_relative_position
        if dx == 0 and dy == -1: return "up"
        if dx == 0 and dy == 1: return "down"
        return "unknown"

    @staticmethod
    async def move_continuously(
    story_result: CompleteStoryResult,
     direction: str) -> str:
        """Move continuously in the specified direction until hitting an obstacle or edge.

        This method implements continuous movement manually by executing
        individual move steps.
        """
        # Normalize direction first
        direction = DirectionHelper.normalize_direction(direction)
        logger.info(
            f"🔄 Starting continuous movement: {direction} from {story_result.person.position}")

        if hasattr(
    story_result.person,
    'move_continuously') and callable(
        story_result.person.move_continuously):
            # If person has the move_continuously method, use it directly
            logger.info("Using person.move_continuously method")
            result_msg = story_result.person.move_continuously(
                direction, story_result.environment)
            return f"✅ Continuous move {direction}: {result_msg}. Now at {story_result.person.position}."

        # Otherwise, implement continuous movement manually with individual
        # steps
        moves = 0
        max_moves = 50

        # Access storyteller agent directly from context if needed for frontend commands
        storyteller = getattr(story_result, '_storyteller_agent', None)
        can_send_websocket = storyteller and hasattr(
            storyteller, 'send_command_to_frontend')

        final_message = ""

        while moves < max_moves:
            current_pos = story_result.person.position
            current_pos_tuple = None
            if hasattr(current_pos, 'x') and hasattr(current_pos, 'y'):
                current_pos_tuple = (current_pos.x, current_pos.y)
            elif isinstance(current_pos, (tuple, list)) and len(current_pos) >= 2:
                current_pos_tuple = (current_pos[0], current_pos[1])
            else:
                logger.error(
                    f"❌ Invalid current_pos format in move_continuously: {current_pos}")
                final_message = "Error: Could not determine starting position."
                break  # Exit loop on error

            target_pos_tuple = DirectionHelper.get_relative_position(
                current_pos_tuple, direction)
            logger.debug(
                f"  Continuous move attempt #{moves + 1}: {current_pos_tuple} -> {target_pos_tuple}")

            # FIXED: Previously tried to use direction string instead of target position
            # Now correctly create a target position object and pass it to
            # person.move
            result = None

            try:
                # Create Position object from target_pos_tuple
                target_position = Position(
    x=target_pos_tuple[0], y=target_pos_tuple[1])
                # Call person.move with environment, target position, and
                # is_running
                result = story_result.person.move(
    story_result.environment, target_position, False)
            except Exception as e:
                logger.error(f"Error during move: {e}")
                result = {"success": False, "message": f"Move error: {e}"}

            if not result or not isinstance(result, dict):
                result = {
    "success": False,
     "message": "Unknown move error (no result)"}

            if not result["success"]:
                logger.info(
                    f"🛑 Continuous movement stopped: {result['message']}")
                stop_reason = f"stopped: {result['message']}"
                final_message = f"Moved {moves} steps {direction} and {stop_reason}"
                break  # Exit loop

            moves += 1

            next_pos_check_tuple = DirectionHelper.get_relative_position(
                # Get current position after move
                (story_result.person.position.x, story_result.person.position.y)
                if hasattr(story_result.person.position, 'x') and hasattr(story_result.person.position, 'y')
                else story_result.person.position[:2] if isinstance(story_result.person.position, (tuple, list))
                else (0, 0),  # Fallback
                direction
            )

            if not story_result.environment.is_valid_position(
                next_pos_check_tuple):
                logger.info(
                    f"🌍 [Continuous Loop] Reached board edge at {story_result.person.position}. Next step {next_pos_check_tuple} is invalid.")
                final_message = f"Moved {moves} steps {direction} and reached the edge."
                break  # Exit loop
            else:
                logger.debug(
                    f"🕵️ [Continuous Loop] Pre-check: NextPos={next_pos_check_tuple}, EnvType={type(story_result.environment)}")  # Log Env Type
                can_move_next_result = story_result.environment.can_move_to(
                    next_pos_check_tuple)
                logger.debug(
                    f"🕵️ [Continuous Loop] Result of environment.can_move_to({next_pos_check_tuple}): {can_move_next_result}")  # Log Check Result

                if not can_move_next_result:
                    obstacle = story_result.environment.get_object_at(
                        next_pos_check_tuple)
                    obstacle_name = obstacle.name if obstacle else "an obstacle"
                    logger.info(
                        f"🚧 [Continuous Loop] Reached {obstacle_name} at {next_pos_check_tuple}. Stopping continuous move.")
                    final_message = f"Moved {moves} steps {direction} and reached {obstacle_name}."
                    break  # Exit loop

        if not final_message:  # If loop finished due to max_moves
            logger.warning(
                f"⚠️ Hit move limit ({max_moves}) moving {direction}")
            final_message = f"Moved {moves} steps {direction} and stopped (max distance)."

        sync_story_state(story_result)

        if moves > 0 and can_send_websocket:
            try:
                command_params = {
                    "direction": direction,
                    "steps": moves,  # Add the number of steps
                    "is_running": False,
                    "continuous": True
                }
                logger.info(
                    f"🚀 Sending final multi-step move command to frontend: direction={direction}, steps={moves}")
                await storyteller.send_command_to_frontend("move", command_params, final_message)
            except Exception as e:
                logger.error(
                    f"❌ Error sending final multi-step WebSocket command: {e}")

        return final_message


# --- sync_story_state, get_weight_description, PathNode, PathFinder ---
# (Keep these helper classes/functions as they are used internally)
def sync_story_state(story_result: CompleteStoryResult):
    """Synchronize the story state (environment maps, nearby objects) using Environment methods.

    Returns:
        bool: True if synchronization was successful, False otherwise
    """
    try:
        if not story_result:
            logger.error("❌ Cannot sync: story_result is None")
            return False

        if not isinstance(story_result, CompleteStoryResult):
            logger.error(
                f"❌ Cannot sync: story_result is not a CompleteStoryResult but {type(story_result)}")
            return False

        logger.debug("🔄 Syncing story state...")
        if not hasattr(story_result, 'person') or not story_result.person:
            logger.warning("❌ Cannot sync: No person in story_result.")
            return False

        if not hasattr(
    story_result,
     'environment') or not story_result.environment:
            logger.warning("❌ Cannot sync: No environment in story_result.")
            return False

        if not hasattr(
    story_result,
     'entities') or story_result.entities is None:
            logger.warning("❌ Cannot sync: No entities list in story_result.")
            story_result.entities = []  # Initialize if missing
            logger.info("✅ Created new empty entities list")

        # DEDENTING THE FOLLOWING BLOCK
        environment = story_result.environment
        person = story_result.person

        # Debug person and environment
        logger.debug(f"👤 Person: id={getattr(person, 'id', 'missing')},"
                    f" position={getattr(person, 'position', 'missing')}")
        logger.debug(f"🌍 Environment: width={getattr(environment, 'width', 'missing')},"
                   f" height={getattr(environment, 'height', 'missing')}")

        # Safeguard against crucial missing methods on environment
        if not hasattr(
    environment,
    'add_entity') or not callable(
        environment.add_entity):
            logger.error(
                "❌ Environment is missing add_entity method - cannot properly sync")
            # Try to add a minimal implementation

            def simple_add_entity(self, entity, position=None):
                """Simple add_entity method when missing from Environment."""
                if not hasattr(self, 'entity_map'):
                    self.entity_map = {}
                if hasattr(entity, 'id'):
                    self.entity_map[entity.id] = entity
                    # IMPROVED: Also update entity position if provided
                    if position is not None and hasattr(
                        entity, 'position'):
                        entity.position = position
                    return True
                return False

            import types
            environment.add_entity = types.MethodType(
                simple_add_entity, environment)
            logger.info("✅ Added simple add_entity method to Environment")

        all_entities_to_sync = list(
    story_result.entities)  # Make a mutable copy

        # ---> ADD DETAILED LOGGING FOR PERSON CHECK <---
        person_id_to_check = getattr(person, 'id', 'PERSON_HAS_NO_ID')
        ids_in_initial_list = [getattr(e, 'id', 'NO_ID') for e in all_entities_to_sync]
        logger.info(f"SYNC: Checking Person ID '{person_id_to_check}' against initial entity IDs: {ids_in_initial_list}")
        person_object_in_list = person in all_entities_to_sync
        person_id_in_list = person_id_to_check in ids_in_initial_list
        logger.info(f"SYNC: Is Person object in initial list? {person_object_in_list}. Is Person ID in initial list? {person_id_in_list}.")

        # Ensure the person is included for syncing, avoid duplicates if
        # already in entities list
        if not person_object_in_list and not person_id_in_list:
            logger.info(f"🔄 SYNC: Adding person '{person_id_to_check}' to sync list.") # Changed level to INFO
            all_entities_to_sync.append(person)
        elif person_object_in_list:
            logger.info(f"🔄 SYNC: Person '{person_id_to_check}' object already in entities list.") # Changed level to INFO
        elif person_id_in_list:
             logger.info(f"🔄 SYNC: Person ID '{person_id_to_check}' already found in entities list.") # Changed level to INFO

        # Clear existing entities from the environment maps using remove_entity if possible
        # This is safer than directly clearing internal maps
        if hasattr(
    environment,
    'entity_map') and isinstance(
        environment.entity_map,
         dict):
            current_entity_ids = list(environment.entity_map.keys())
            logger.debug(
                f"Clearing {len(current_entity_ids)} existing entities from environment map...")
            cleared_count = 0
            failed_clear_count = 0
            for entity_id in current_entity_ids:
                entity_to_remove = environment.entity_map.get(entity_id)
                if entity_to_remove:
                    if hasattr(
    environment, 'remove_entity') and callable(
        environment.remove_entity):
                        if environment.remove_entity(entity_to_remove):
                            cleared_count += 1
                        else:
                            logger.warning(
                                f"  Failed to remove entity {entity_id} during sync clear.")
                            failed_clear_count += 1
                    else:
                        # If remove_entity doesn't exist, do a direct
                        # dictionary update
                        if entity_id in environment.entity_map:
                            del environment.entity_map[entity_id]
                            cleared_count += 1
                else:
                    logger.warning(
                        f"  Entity ID {entity_id} was in map keys but not retrievable.")
            logger.debug(
                f"  Clear complete: {cleared_count} removed, {failed_clear_count} failed.")
        else:
            logger.warning(
                "Environment entity_map not found or not a dict, cannot reliably clear entities.")
            # Create a new entity_map if it doesn't exist
            if not hasattr(environment, 'entity_map'):
                environment.entity_map = {}
                logger.info("✅ Created new entity_map on Environment")

        # Add all entities (including the person) using add_entity
        added_count = 0
        failed_add_count = 0
        logger.debug(
            f"Adding {len(all_entities_to_sync)} entities to environment...")
        for entity in all_entities_to_sync:
            # ---> ADD LOGGING HERE <---
            is_person = hasattr(entity, 'id') and hasattr(person, 'id') and entity.id == person.id
            if is_person:
                logger.info(f"🔄 SYNC: Processing PERSON entity: ID={entity.id}, Pos={getattr(entity, 'position', 'None')}")

            pos = getattr(entity, 'position', None)
            # Use the entity's position if available
            if hasattr(
    environment,
    'add_entity') and callable(
        environment.add_entity):

                # ---> ADD LOGGING HERE <---
                if is_person:
                    logger.info(f"🔄 SYNC: Calling environment.add_entity for PERSON (ID={entity.id}) at Pos={pos}")

                add_success = environment.add_entity(entity, pos)

                # ---> ADD LOGGING HERE <---
                if is_person:
                     logger.info(f"🔄 SYNC: environment.add_entity result for PERSON: {'Success' if add_success else 'Failed'}")

                if add_success:
                    added_count += 1
                else:
                    logger.warning(
                        f"  Failed to add entity {getattr(entity, 'id', 'UNKNOWN_ID')} during sync.")
                    # Try direct mapping as a fallback
                    if hasattr(
    entity, 'id') and hasattr(
        environment, 'entity_map'):
                        environment.entity_map[entity.id] = entity
                        added_count += 1
                        logger.info(
                            f"  Recovered by directly adding entity {entity.id} to map")
                    else:
                        failed_add_count += 1
            else:
                # Direct dictionary update if add_entity isn't available
                if hasattr(
    entity, 'id') and hasattr(
        environment, 'entity_map'):

                    # ---> ADD LOGGING HERE <---
                    if is_person:
                         logger.info(f"🔄 SYNC: Directly adding PERSON (ID={entity.id}) to entity_map (add_entity missing)")

                    environment.entity_map[entity.id] = entity
                    added_count += 1
                else:
                    failed_add_count += 1
                    logger.warning(
                        f"  Cannot add entity - missing id or entity_map")

        logger.debug(
            f"  Add complete: {added_count} added, {failed_add_count} failed.")
        # END OF DEDENTED BLOCK

        # Update nearby objects using the person's look method
        if hasattr(
    story_result.person,
    'look') and callable(
        story_result.person.look):
            # Ensure the environment passed to look is the updated one
            try:
                # Pass environment directly from story_result to avoid potential local variable issues
                look_result = story_result.person.look(story_result.environment)
                if look_result.get("success", False):
                        # Make sure nearby_objects is initialized
                        if not hasattr(
    story_result,
     'nearby_objects') or story_result.nearby_objects is None:
                            story_result.nearby_objects = {}

                        # IMPROVED: Update with complete objects including position information
                        # First clear the dictionary to remove any stale
                        # references
                        story_result.nearby_objects.clear()

                        # Add objects with full details
                        nearby_objs_from_look = look_result.get(
                            "nearby_objects", {})
                        nearby_ents_from_look = look_result.get(
                            "nearby_entities", {})

                        # Add objects with full details
                        for obj_id, obj in nearby_objs_from_look.items():
                            # Only store actual objects, not just IDs
                            if hasattr(obj, 'id'):
                                story_result.nearby_objects[obj_id] = obj
                                logger.debug(
                                    f"Added object to nearby_objects: {obj_id}, pos={getattr(obj, 'position', 'unknown')}")

                        # Add entities with full details
                        for ent_id, ent in nearby_ents_from_look.items():
                            # Only store actual objects, not just IDs
                            if hasattr(ent, 'id'):
                                story_result.nearby_objects[ent_id] = ent
                                logger.debug(
                                    f"Added entity to nearby_objects: {ent_id}, pos={getattr(ent, 'position', 'unknown')}")

                        # Log the count of objects stored
                        logger.info(
                            f"✅ Updated nearby_objects with {len(story_result.nearby_objects)} items")
                else:
                 logger.warning(
                     f"⚠️ Person look failed during sync: {look_result.get('message')}")
                story_result.nearby_objects = {}  # Clear if look fails
            except Exception as e:
                logger.error(f"❌ Error during look operation in sync: {e}")
                story_result.nearby_objects = {}  # Ensure it exists
        else:
            logger.warning(
                "🤷 Person object missing 'look' method, cannot update nearby_objects.")
            story_result.nearby_objects = {}  # Ensure it exists

            # Store entity counts in the story_result for easier access
            if hasattr(environment, 'entity_map'):
                entity_count = len(environment.entity_map)
                logger.info(
                    f"📊 Synchronized with {entity_count} entities in map")
                story_result._entity_count = entity_count

            # Also store a reference to the timestamp of last successful sync
            story_result._last_sync = time.time()

        logger.debug("✅ Story state sync complete.")
        return True
    except Exception as e:
        logger.error(
    f"❌ Unexpected error during story sync: {e}",
     exc_info=True)
        return False


def get_weight_description(weight: int) -> str:
    """Convert a numerical weight to a descriptive term."""
    if weight <= 1: return "very light"
    if weight <= 3: return "light"
    if weight <= 5: return "moderately heavy"
    if weight <= 8: return "heavy"
    return "extremely heavy"


class PathNode:
    """Node used in the A* path-finding algorithm."""

    def __init__(self, position, parent=None):
        self.position: Tuple[int, int] = position  # (x, y) tuple
        self.parent: Optional[PathNode] = parent  # parent PathNode
        self.g: int = 0  # cost from start to current node
        self.h: int = 0  # heuristic (estimated cost from current to goal)
        self.f: int = 0  # total cost (g + h)

    def __eq__(self, other):
        if not isinstance(other, PathNode):
            return NotImplemented
        return self.position == other.position

    def __lt__(self, other):
        if not isinstance(other, PathNode):
            return NotImplemented
        if self.f != other.f:
            return self.f < other.f
        return self.h < other.h

    def __hash__(self):
        return hash(self.position)


class PathFinder:
    """Class implementing A* path-finding algorithm with jump support for Storyteller context."""

    @staticmethod
    def manhattan_distance(
        pos1: Tuple[int, int], pos2: Tuple[int, int]) -> int:
        """Calculate Manhattan distance between two positions."""
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    @staticmethod
    def get_neighbors(
        position: Tuple[int, int], environment: Environment) -> List[Tuple[int, int]]:
        """Get valid, movable neighboring positions (cardinal directions only).

        Uses coordinate system where:
        - (0, -1): Up (decrease Y)
        - (1, 0): Right (increase X)
        - (0, 1): Down (increase Y)
        - (-1, 0): Left (decrease X)
        """
        x, y = position
        neighbors = []
        for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
            new_pos = (x + dx, y + dy)
            if environment.is_valid_position(
                new_pos) and environment.can_move_to(new_pos):
                neighbors.append(new_pos)
        return neighbors

    @staticmethod
    def get_jump_neighbors(
        position: Tuple[int, int], environment: Environment) -> List[Tuple[int, int]]:
        """Get positions reachable by jumping from the current position.

        Uses coordinate system where:
        - (0, -1): Up (decrease Y)
        - (1, 0): Right (increase X)
        - (0, 1): Down (increase Y)
        - (-1, 0): Left (decrease X)
        """
        x, y = position
        jump_neighbors = []
        for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
            middle_pos = (x + dx, y + dy)
            landing_pos = (x + 2 * dx, y + 2 * dy)

            if environment.is_valid_position(
                middle_pos) and environment.is_valid_position(landing_pos):
                middle_obj = environment.get_object_at(middle_pos)
                if middle_obj and getattr(
    middle_obj,
    'is_jumpable',
     False) and environment.can_move_to(landing_pos):
                    jump_neighbors.append(landing_pos)
        return jump_neighbors

    @staticmethod
    def find_path(environment: Environment, start_pos: Tuple[int, int], end_pos: Tuple[int, int]) -> List[
        Tuple[int, int]]:
        """Find the shortest path using A*.

        Returns:
            List of positions (tuples) from start to end, or empty list if no path.
        """
        logger.debug(f"PATHFINDER: Finding path from {start_pos} to {end_pos}")
        if not environment.is_valid_position(
            start_pos) or not environment.is_valid_position(end_pos):
            logger.warning("PATHFINDER: Start or end position invalid.")
            return []
        if start_pos == end_pos:
             return [start_pos]

        start_node = PathNode(start_pos)
        end_node = PathNode(end_pos)

        open_list = []  # Priority queue (min-heap)
        closed_set = set()  # Set of visited positions

        heapq.heappush(open_list, start_node)

        while open_list:
            current_node = heapq.heappop(open_list)

            if current_node.position in closed_set:
                continue  # Already processed this position via a better path
            closed_set.add(current_node.position)

            if current_node.position == end_node.position:
                path = []
                temp = current_node
                while temp:
                    path.append(temp.position)
                    temp = temp.parent
                logger.debug(
                    f"PATHFINDER: Path found with {len(path) - 1} steps.")
                return path[::-1]  # Return reversed path

            neighbors_pos = PathFinder.get_neighbors(
                current_node.position, environment)
            jump_neighbors_pos = PathFinder.get_jump_neighbors(
                current_node.position, environment)

            for neighbor_pos in neighbors_pos + jump_neighbors_pos:
                if neighbor_pos in closed_set:
                    continue

                # Jump costs 5, move costs 1
                move_cost = 5 if neighbor_pos in jump_neighbors_pos else 1
                new_g = current_node.g + move_cost

                existing_node = next(
    (node for node in open_list if node.position == neighbor_pos), None)

                if existing_node and new_g >= existing_node.g:
                    continue  # Found a better or equal path already

                neighbor_node = PathNode(neighbor_pos, current_node)
                neighbor_node.g = new_g
                neighbor_node.h = PathFinder.manhattan_distance(
                    neighbor_pos, end_pos)
                neighbor_node.f = neighbor_node.g + neighbor_node.h

                heapq.heappush(open_list, neighbor_node)

        logger.warning("PATHFINDER: No path found.")
        return []  # No path found


# --- Internal Movement Logic ---
async def _internal_move(story_context: CompleteStoryResult, direction: str, is_running: bool,
                         continuous: bool, steps: int) -> str:
    """Internal logic for moving the player character. DOES NOT send commands to frontend."""
    # Safety check for story_context
    if story_context is None:
        logger.error("💥 INTERNAL: Critical error - story_context parameter is None")
        return "Error: Game context is missing. Please try setting the theme again."

    # Check if person exists
    if not hasattr(story_context, 'person') or story_context.person is None:
        logger.error(
            "💥 INTERNAL: Critical error - story_context.person is missing or None")
        return "Error: Player character not found in game. Please try setting the theme again."

    # Check if environment exists
    if not hasattr(story_context, 'environment') or story_context.environment is None:
        logger.error(
            "💥 INTERNAL: Critical error - story_context.environment is missing or None")
        return "Error: Game environment not found. Please try setting the theme again."
    else:
        # CORRECT: Assign environment here, since we know it exists
        environment = story_context.environment
        # ---> LOG ENV ID <---
        logger.info(f"SYNC CHECK: Environment ID in _internal_move: {id(environment)}")
        logger.debug(
            f"🕵️ Type of environment at start of _internal_move: {type(environment)}")
        # Optionally keep the check for valid methods if useful
        if not isinstance(environment, str):
            logger.debug(
                f"  environment.is_valid_position exists: {hasattr(environment, 'is_valid_position')}")

    if not environment or isinstance(environment, str):
        logger.error(
            f"❌ Environment is invalid (type: {type(environment)}) in _internal_move!")
        return f"❌ Error: Game environment is invalid (Type: {type(environment)})."

    person = story_context.person

    # Normalize the direction for better user experience
    normalized_direction = DirectionHelper.normalize_direction(direction)
    if normalized_direction != direction:
        logger.info(f"🧭 Normalized direction from '{direction}' to '{normalized_direction}'")
        direction = normalized_direction
    
    logger.info(
        f"Executing internal move logic: Dir={direction}, Steps={steps}, Running={is_running}, Cont={continuous}")

    # Use the normalized direction
    direction_internal = direction

    # If continuous, calculate maximum steps before hitting obstacle
    if continuous:
        logger.info(f"  Calculating continuous move {direction_internal}...")
        result_msg = await DirectionHelper.move_continuously(story_context, direction_internal)
        return result_msg
    else:
        actual_steps_taken = 0
        start_pos = person.position  # Record position before steps
        step_result_msg = "Blocked"  # Default message if loop doesn't run

        for i in range(steps):
            current_pos_tuple_debug = None
            if hasattr(person.position, 'x') and hasattr(person.position, 'y'):
                current_pos_tuple_debug = (
    person.position.x, person.position.y)
            elif isinstance(person.position, (tuple, list)) and len(person.position) >= 2:
                current_pos_tuple_debug = (
    person.position[0], person.position[1])

            if current_pos_tuple_debug:
                target_pos_tuple = DirectionHelper.get_relative_position(
                    current_pos_tuple_debug, direction_internal)
                is_valid = environment.is_valid_position(target_pos_tuple)
                can_move = environment.can_move_to(
                    target_pos_tuple) if is_valid else False
                logger.debug(
                    f"  [Check BEFORE person.move] Step {i + 1}/{steps}: Current={current_pos_tuple_debug}, Target={target_pos_tuple}, IsValid={is_valid}, CanMoveTo={can_move}")
            else:
                logger.error(
                    f"  [Check BEFORE person.move] Step {i + 1}/{steps}: Could not determine current position: {person.position}")
                target_pos_tuple = None

            try:
                if target_pos_tuple:
                    target_position = Position(
    x=target_pos_tuple[0], y=target_pos_tuple[1])
                    step_result = person.move(
    story_context.environment, target_position, is_running)
                else:
                    step_result = {
    "success": False,
     "message": "Could not determine target position for movement"}
            except Exception as e:
                logger.error(f"Failed to call move: {e}")
                return f"❌ Error executing move command: {str(e)}"

            if step_result is None:
                logger.error(
                    "Move method returned None instead of a result dictionary")
                step_result_msg = "Move method returned None"
                break
            else:
                step_result_msg = step_result.get('message', 'Unknown reason')
                if step_result.get("success", False):
                    actual_steps_taken += 1
                else:
                    logger.info(
                        f"    Step {i + 1}/{steps} failed (reported by person.move): {step_result_msg}. Stopping.")
                    break

        if actual_steps_taken > 0:
            action_verb = "ran" if is_running else "walked"
            return f"✅ Successfully {action_verb} {direction_internal} {actual_steps_taken} step{'s' if actual_steps_taken != 1 else ''}. Now at {person.position}."
        else:
            return f"❌ Could not move {direction_internal} from {start_pos}. Reason: {step_result_msg}"


async def _internal_jump(
    story_context: CompleteStoryResult, # Changed context parameter
    target_x: int,
     target_y: int) -> str:
    """Internal logic for making the player character jump. DOES NOT send commands to frontend."""
    # Safety check for story_context
    if story_context is None:
        logger.error("💥 INTERNAL: Critical error - story_context parameter is None")
        return "Error: Game context is missing. Please try setting the theme again."

    # Get the context object and check if it's valid
    # story_result = getattr(ctx, "context", None) # No longer needed
    # if story_result is None:
    #     logger.error("💥 INTERNAL: Critical error - ctx.context is None")
    #     return "Error: Game state is not properly initialized. Please try setting the theme again."

    # Check if person exists
    if not hasattr(story_context, 'person') or story_context.person is None:
        logger.error(
            "💥 INTERNAL: Critical error - story_context.person is missing or None")
        return "Error: Player character not found in game. Please try setting the theme again."

    # Check if environment exists
    if not hasattr(
    story_context,
     'environment') or story_context.environment is None:
        logger.error(
            "💥 INTERNAL: Critical error - story_context.environment is missing or None")
        return "Error: Game environment not found. Please try setting the theme again."

    person = story_context.person
    environment = story_context.environment
    logger.info(f"Executing internal jump logic to: ({target_x}, {target_y})")

    target_pos = Position(x=target_x, y=target_y)
    result = person.jump(target_pos, environment)

    if result.get("success", False):
         return f"✅ {result.get('message', 'Jump successful')}. Now at {person.position}."
    else:
         return f"❌ {result.get('message', 'Jump failed')}"


# --- Tool Definitions (Refactored for Assistants API) ---

# Remove @function_tool and @log_tool_execution decorators
async def look_around(
    story_context: CompleteStoryResult, # Changed context parameter
     radius: int) -> str:
    """Looks around the player's current position within a given radius to identify nearby objects and entities.

    Args:
        story_context: The game state context. # Updated description
        radius: How far to look (number of squares, between 1 and 10).

    Returns:
        str: A description of what the player sees nearby.
    """
    # Enhanced logging to track context issues
    logger.info(f"🔍 TOOL: look_around called with radius={radius}") # Added TOOL prefix

    # Handle missing context gracefully
    if story_context is None:
        logger.error("❌ TOOL: story_context is None in look_around!")
        return "Error: Context is missing. Please try reloading the theme."

    # Check if story_context has required attributes
    if not hasattr(
    story_context,
     'person') or not story_context.person:
        logger.error(
            f"❌ TOOL: Missing person object in story_context: {getattr(story_context, 'person', None)}")
        return "Cannot look around - the player character is missing."

    if not hasattr(
    story_context,
     'environment') or not story_context.environment:
        logger.error(
            f"❌ TOOL: Missing environment object in story_context: {getattr(story_context, 'environment', None)}")
        return "Cannot look around - the game environment is missing."

    # Validate radius internally (don't use default parameter)
    if radius <= 0:
        logger.warning(
            f"TOOL: Invalid radius value {radius} provided, using minimum value 1 instead")
        radius = 1
    elif radius > 10:
        logger.warning(
            f"TOOL: Radius value {radius} exceeds maximum, clamping to 10")
        radius = 10

    person = story_context.person
    environment = story_context.environment

    # Ensure position exists
    if not person.position:
        logger.error("❌ TOOL: Person position is None in look_around")
        return "You don't seem to be anywhere specific to look around from."

    # Debug position information
    if hasattr(person.position, 'x') and hasattr(person.position, 'y'):
        logger.info(
            f"👤 TOOL: Player position: ({person.position.x}, {person.position.y})")
    elif isinstance(person.position, (tuple, list)) and len(person.position) >= 2:
        logger.info(
            f"👤 TOOL: Player position: ({person.position[0]}, {person.position[1]})")
    else:
        logger.warning(f"⚠️ TOOL: Unusual position format: {person.position}")

    try:
        # Enhanced error checking for look method
        if not hasattr(person, 'look') or not callable(person.look):
            logger.error("❌ TOOL: Person object is missing the 'look' method!")
            # Create a basic description of surroundings
            return "You look around but can't focus. (Error: Character functionality is limited)"

        # Ensure the environment is properly set up for looking
        if not hasattr(
    environment,
    'is_valid_position') or not callable(
        environment.is_valid_position):
            logger.error("❌ TOOL: Environment is missing is_valid_position method!")
            return "You scan the area but can't make sense of your surroundings. (Error: Map functionality is limited)"

        # Call the look method with extra error handling
        look_result = person.look(environment=environment, radius=radius)

        if not look_result.get("success"):
            logger.warning(
                f"⚠️ TOOL: look failed: {look_result.get('message', 'Unknown reason')}")
            return f"Failed to look around: {look_result.get('message', 'Unknown reason')}"

        nearby_objects = look_result.get("nearby_objects", {})
        nearby_entities = look_result.get("nearby_entities", {})

        if not nearby_objects and not nearby_entities:
            return "You look around but see nothing of interest nearby."

        descriptions = []
        if nearby_objects:
            obj_names = [
    obj.name for obj in nearby_objects.values() if hasattr(
        obj, 'name')]
            if obj_names:
                descriptions.append(f"Nearby objects: {', '.join(obj_names)}")
        if nearby_entities:
            ent_names = [
    ent.name for ent in nearby_entities.values() if hasattr(
        ent, 'name')]
            if ent_names:
                descriptions.append(f"Nearby entities: {', '.join(ent_names)}")

        # Store nearby objects in story_context for future reference
        # IMPORTANT: Always create a fresh dictionary to prevent stale
        # references
        if not hasattr(
    story_context,
     'nearby_objects') or story_context.nearby_objects is None:
            story_context.nearby_objects = {}

        # IMPROVED: Update with complete objects including position information
        # First clear the dictionary to remove any stale references
        story_context.nearby_objects.clear()

        # Add objects with full details
        for obj_id, obj in nearby_objects.items():
            # Only store actual objects, not just IDs
            if hasattr(obj, 'id'):
                story_context.nearby_objects[obj_id] = obj
                logger.debug(
                    f"TOOL: Added object to nearby_objects: {obj_id}, pos={getattr(obj, 'position', 'unknown')}")

        # Add entities with full details
        for ent_id, ent in nearby_entities.items():
            # Only store actual objects, not just IDs
            if hasattr(ent, 'id'):
                story_context.nearby_objects[ent_id] = ent
                logger.debug(
                    f"TOOL: Added entity to nearby_objects: {ent_id}, pos={getattr(ent, 'position', 'unknown')}")

        # Log the count of objects stored
        logger.info(
            f"✅ TOOL: Updated nearby_objects with {len(story_context.nearby_objects)} items")

        return "You look around. " + ". ".join(descriptions) + "."

    except Exception as e:
        logger.error(
    f"❌ TOOL: Error during look_around execution: {e}",
     exc_info=True)
        return f"An unexpected error occurred while trying to look around: {e}"


# Remove decorators
async def get_inventory(story_context: CompleteStoryResult) -> str: # Changed context parameter
    """Checks the player's inventory and lists the items being carried.

    Args:
        story_context: The game state context. # Updated description

    Returns:
        str: A list of items in the inventory or a message saying it's empty.
    """
    logger.info("🎒 TOOL: get_inventory called") # Added logging
    # story_result = ctx.context # No longer needed
    if not story_context or not story_context.person:
        return "❌ Error: Cannot check inventory. Player not found."

    person = story_context.person
    if not hasattr(person, 'inventory') or not person.inventory:
        return "❌ Error: Player inventory is missing or invalid."

    if not hasattr(
    person.inventory,
     'contents') or not person.inventory.contents:
        return "Your inventory is empty."

    item_names = [
    item.name for item in person.inventory.contents if hasattr(
        item, 'name')]
    if not item_names:
        return "You have some items, but they are indescribable."  # Should ideally not happen

    result = f"You check your inventory. You are carrying: {', '.join(item_names)}."
    logger.info(f"🎒 TOOL: Inventory contents: {result}") # Added logging
    return result


# Remove decorators
async def get_object_details(
    story_context: CompleteStoryResult, # Changed context parameter
     object_id: str) -> str:
    """Examines a specific nearby object or an item in the inventory to get more details about it.

    Args:
        story_context: The game state context. # Updated description
        object_id: The unique ID of the object or item to examine.

    Returns:
        str: A description of the object/item, or an error message if not found.
    """
    logger.info(f"🧐 TOOL: get_object_details called for ID: {object_id}") # Added logging
    # story_result = ctx.context # No longer needed
    if not story_context or not story_context.person or not story_context.environment:
        return "❌ Error: Game state not ready to examine objects."

    person = story_context.person
    target_object = None

    # 1. Check inventory
    if hasattr(
    person,
    'inventory') and person.inventory and hasattr(
        person.inventory,
         'contents'):
        for item in person.inventory.contents:
            if hasattr(item, 'id') and item.id == object_id:
                target_object = item
                logger.debug(f"🧐 TOOL: Found '{object_id}' in inventory.")
                break

    # 2. Check nearby objects (if not found in inventory)
    if not target_object:
        # Ensure nearby_objects exists and is updated
        if not hasattr(story_context, 'nearby_objects'):
            logger.warning(
                "⚠️ TOOL: nearby_objects not found in context for get_object_details. Attempting look.")
            await look_around(story_context)  # Try to update nearby objects

        if hasattr(
    story_context,
     'nearby_objects') and story_context.nearby_objects:
            target_object = story_context.nearby_objects.get(object_id)
            if target_object:
                logger.debug(f"🧐 TOOL: Found '{object_id}' in nearby objects.")


    # 3. Check environment map as a last resort (less reliable)
    if not target_object and hasattr(story_context.environment, 'entity_map'):
        target_object = story_context.environment.entity_map.get(object_id)
        if target_object:
            logger.debug(f"🧐 TOOL: Found '{object_id}' in environment map.")


    if not target_object:
        logger.warning(f"🧐 TOOL: Could not find object with ID '{object_id}'.")
        return f"❌ You look for '{object_id}', but can't find anything with that ID nearby or in your inventory."

    # Construct description
    description = getattr(target_object, 'description', None)
    name = getattr(target_object, 'name', 'an object')
    details = [f"You examine the {name}."]

    if description:
        details.append(description)
    else:  # Fallback details if no description attribute
        obj_type = getattr(target_object, 'type', 'unknown type')
        details.append(f"It appears to be a {obj_type}.")
        if hasattr(target_object, 'weight'):
            details.append(
                f"It feels {get_weight_description(target_object.weight)}.")
        if getattr(target_object, 'is_movable', False):
            details.append("It looks like it could be moved.")
        if getattr(target_object, 'is_container', False):
            details.append("It could hold other items.")
        if getattr(target_object, 'is_collectable', False):
            details.append("You could probably pick it up.")

    # Add container contents if applicable
    if isinstance(
    target_object,
    Container) and hasattr(
        target_object,
         'contents'):
        if target_object.contents:
            item_names = [
    item.name for item in target_object.contents if hasattr(
        item, 'name')]
            details.append(f"Inside, you see: {', '.join(item_names)}.")
        else:
            details.append("It's empty inside.")

    result = " ".join(details)
    logger.info(f"🧐 TOOL: Object details: {result}") # Added logging
    return result


# Remove decorators
async def use_object_with(
    story_context: CompleteStoryResult, # Changed context parameter
    item1_id: str,
     item2_id: str) -> str:
    """Uses one item (item1_id from inventory) with another item or object (item2_id from inventory or nearby).

    Args:
        story_context: The game state context. # Updated description
        item1_id: The ID of the item from inventory to use.
        item2_id: The ID of the target item/object (in inventory or nearby).

    Returns:
        str: A message describing the result of the action (success or failure).
    """
    logger.info(f"🤝 TOOL: use_object_with called: item1='{item1_id}', item2='{item2_id}'") # Added logging
    # story_result = ctx.context # No longer needed
    if not story_context or not story_context.person or not story_context.environment:
        return "❌ Error: Game state not ready for item interaction."

    person = story_context.person
    # Pass environment if needed by use_with
    environment = story_context.environment

    # Ensure nearby_objects is populated for the Person method to use
    if not hasattr(story_context, 'nearby_objects'):
        logger.warning(
            "⚠️ TOOL: nearby_objects not found in context for use_object_with. Attempting look.")
        await look_around(story_context)  # Try to update nearby objects

    nearby_objects_dict = getattr(story_context, 'nearby_objects', {})

    if not hasattr(
    person,
    'use_object_with') or not callable(
        person.use_object_with):
        logger.error(
            "❌ TOOL: Person object is missing the 'use_object_with' method!")
        return "❌ Error: Interaction logic is missing for the character."

    try:
        # Call the method on the Person instance, passing necessary context
        result_data = person.use_object_with( # Renamed variable to avoid confusion
            item1_id=item1_id,
            item2_id=item2_id,
            environment=environment,  # Pass environment
            nearby_objects=nearby_objects_dict  # Pass nearby objects dict
        )

        result_str = "" # Initialize result string
        if isinstance(result_data, dict):
            result_str = result_data.get(
    "message", "❓ Interaction occurred, but result unclear.")
        else:
            # Handle cases where the underlying method might not return a dict
            logger.warning(
                f"⚠️ TOOL: Unexpected return type from person.use_object_with: {type(result_data)}. Result: {result_data}")
            # Return raw result if not dict
            result_str = f"❓ Interaction result: {result_data}"

        logger.info(f"🤝 TOOL: Interaction result: {result_str}") # Added logging
        return result_str

    except Exception as e:
        logger.error(
    f"❌ TOOL: Error during use_object_with execution: {e}",
     exc_info=True)
        return f"❌ An unexpected error occurred while trying to use '{item1_id}' with '{item2_id}': {e}"


# Remove decorators
async def move_to_object(
    story_context: CompleteStoryResult, # Changed context parameter
    target_x: int,
     target_y: int) -> str:
    """Moves the player towards an object by finding an adjacent path and executing the steps.
    This is useful for approaching objects or locations without needing to land exactly on them.
    The tool calculates the path and executes the necessary move/jump steps.

    Args:
        story_context: The game state context. # Updated description
        target_x: The X coordinate of the target object/location.
        target_y: The Y coordinate of the target object/location.

    Returns:
        str: Description of the movement result (success, failure, path taken) or an error message.
    """
    logger.info(
        f"🚶‍♂️ TOOL: move_to_object(target_x={target_x}, target_y={target_y})")

    # Safety check for context and other required objects
    if story_context is None:
        return "❌ Error: Game context not available"

    # story_result = ctx.context # No longer needed
    # if not story_result:
    #     return "❌ Error: Game state is missing"

    if not hasattr(story_context, 'person') or not story_context.person:
        return "❌ Error: Player character not found."

    if not hasattr(
    story_context,
     'environment') or not story_context.environment:
        return "❌ Error: Game environment not found."

    person = story_context.person
    environment = story_context.environment

    # Ensure we have a valid current position
    current_pos_tuple = None
    if person.position:
        if hasattr(person.position, 'x') and hasattr(person.position, 'y'):
             current_pos_tuple = (person.position.x, person.position.y)
        elif isinstance(person.position, (tuple, list)) and len(person.position) >= 2:
             current_pos_tuple = (person.position[0], person.position[1])

    if not current_pos_tuple:
        logger.error(
            f"💥 TOOL move_to_object: Invalid or missing player start position: {person.position}")
        sync_story_state(story_context)  # Attempt to sync state to fix position
        if person.position and isinstance(
    person.position, (tuple, list)) and len(
        person.position) >= 2:
            current_pos_tuple = (person.position[0], person.position[1])
            if not environment.is_valid_position(current_pos_tuple):
                 return "Error: Cannot determine player's valid starting position even after sync."
        else:
             return "Error: Cannot determine player's starting position."

    # Validate target position
    target_pos = (target_x, target_y)
    if not environment.is_valid_position(target_pos):
        return f"Error: Target location ({target_x},{target_y}) is outside the valid map area."

    logger.debug(
        f"  TOOL: Player at {current_pos_tuple}, Target location {target_pos}")

    # Check if already adjacent to target
    if PathFinder.manhattan_distance(current_pos_tuple, target_pos) == 1:
        logger.info("  TOOL: Player is already adjacent to the target location.")
        return f"You are already standing next to the location ({target_x},{target_y})."

    # Find adjacent positions where player can stand
    adjacent_candidates = []
    for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:  # Up, Right, Down, Left
        adj_pos = (target_pos[0] + dx, target_pos[1] + dy)
        if environment.is_valid_position(
            adj_pos) and environment.can_move_to(adj_pos):
            adjacent_candidates.append(adj_pos)

    if not adjacent_candidates:
        logger.warning(
            f"  TOOL: No valid, empty adjacent spaces found around target {target_pos}")
        obj_at_target = environment.get_object_at(target_pos)
        obj_name = getattr(
    obj_at_target,
    'name',
     'the target location') if obj_at_target else 'the target location'
        return f"There are no free spaces to stand next to {obj_name} at ({target_x},{target_y})."

    logger.debug(
        f"  TOOL: Found {len(adjacent_candidates)} potential adjacent spots: {adjacent_candidates}")

    # Find the closest adjacent spot to the player's current position
    adjacent_candidates.sort(key=lambda pos: PathFinder.manhattan_distance(current_pos_tuple, pos))
    closest_adjacent_pos = adjacent_candidates[0]
    logger.debug(f"  TOOL: Closest adjacent spot: {closest_adjacent_pos}")

    # Find path to the closest adjacent position
    path = PathFinder.find_path(environment, current_pos_tuple, closest_adjacent_pos)

    if not path:
        logger.warning(f"  TOOL: No path found from {current_pos_tuple} to {closest_adjacent_pos}")
        return f"Cannot find a path to get next to the location ({target_x},{target_y})."

    # Convert path to a sequence of movement commands
    move_commands = []
    for i in range(len(path) - 1):
        start = path[i]
        end = path[i+1]
        dx = end[0] - start[0]
        dy = end[1] - start[1]

        if abs(dx) + abs(dy) == 1: # Standard move
            direction = DirectionHelper.get_direction_name((dx, dy))
            move_commands.append(MovementCommand(
                command_type="move",
                direction=direction,
                is_running=False, # Default to walking for move_to_object
                continuous=False,
                steps=1
            ))
        elif abs(dx) + abs(dy) == 2: # Jump
            move_commands.append(MovementCommand(
                command_type="jump",
                target_x=end[0],
                target_y=end[1]
            ))
        else:
            logger.warning(f"  TOOL: Invalid step in path: {start} -> {end}. Skipping.")

    if not move_commands:
        return "Found a path, but could not translate it into movement commands."

    # Execute the movement sequence
    logger.info(f"  TOOL: Executing {len(move_commands)} steps to reach adjacent spot...")
    movement_result = await execute_movement_sequence(story_context, move_commands)

    # Sync state after movement
    sync_story_state(story_context)

    logger.info(f"  TOOL: Movement result: {movement_result}")
    return f"Attempting to move towards ({target_x},{target_y}):\n{movement_result}"


# --- Added Tool Functions ---

async def move(story_context: CompleteStoryResult, direction: str, is_running: bool, continuous: bool, steps: int) -> str:
    """
    Move the player character step-by-step or continuously in a given cardinal direction.

    Args:
        story_context: The current game state context.
        direction: Cardinal direction ("up", "down", "left", "right", "north", "south", "east", "west").
        is_running: Whether to run (move faster).
        continuous: If True, move until an obstacle or the edge of the map is hit.
        steps: Number of steps to take if continuous is False.

    Returns:
        str: A message describing the result of the move action.
    """
    logger.info(f"🚶 TOOL: move called: Dir={direction}, Running={is_running}, Cont={continuous}, Steps={steps}")
    # Validate context first
    if not story_context or not story_context.person or not story_context.environment:
        logger.error("❌ TOOL move: Missing context, person, or environment.")
        return "Error: Cannot move, game state is incomplete."

    # Basic validation for steps if not continuous
    if not continuous and (not isinstance(steps, int) or steps <= 0):
        logger.warning(f"TOOL move: Invalid steps value '{steps}' for non-continuous move. Defaulting to 1.")
        steps = 1

    # Normalize direction using DirectionHelper
    normalized_direction = DirectionHelper.normalize_direction(direction)
    if normalized_direction != direction:
        logger.info(f"🧭 TOOL: Normalized direction from '{direction}' to '{normalized_direction}'")
    
    try:
        result = await _internal_move(
            story_context=story_context,
            direction=normalized_direction,
            is_running=is_running,
            continuous=continuous,
            steps=steps
        )
        # Sync state after movement
        sync_story_state(story_context)
        logger.info(f"✅ TOOL move result: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ TOOL move: Error during execution: {e}", exc_info=True)
        return f"An unexpected error occurred during the move: {e}"


async def jump(story_context: CompleteStoryResult, target_x: int, target_y: int) -> str:
    """
    Makes the player character jump two squares horizontally or vertically over an obstacle.

    Args:
        story_context: The current game state context.
        target_x: Destination X coordinate (must be 2 squares away).
        target_y: Destination Y coordinate (must be 2 squares away).

    Returns:
        str: A message describing the result of the jump action.
    """
    logger.info(f"🤸 TOOL: jump called: Target=({target_x}, {target_y})")
    # Validate context first
    if not story_context or not story_context.person or not story_context.environment:
        logger.error("❌ TOOL jump: Missing context, person, or environment.")
        return "Error: Cannot jump, game state is incomplete."

    try:
        result = await _internal_jump(
            story_context=story_context,
            target_x=target_x,
            target_y=target_y
        )
        # Sync state after movement
        sync_story_state(story_context)
        logger.info(f"✅ TOOL jump result: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ TOOL jump: Error during execution: {e}", exc_info=True)
        return f"An unexpected error occurred during the jump: {e}"


async def find_entity_by_type(story_context: CompleteStoryResult, entity_type: str) -> str:
    """
    Finds entities of a specific type in the game environment and returns their locations.

    Args:
        story_context: The current game state context.
        entity_type: The type of entity to search for (e.g. "log_stool", "campfire", "chest").

    Returns:
        str: A message listing found entities and their locations, or a 'not found' message.
    """
    logger.info(f"🔍 TOOL: find_entity_by_type called: Type='{entity_type}'")
    if not story_context or not story_context.environment:
        logger.error("❌ TOOL find_entity_by_type: Missing context or environment.")
        return "Error: Cannot search for entities, game environment is missing."

    # Ensure environment state is reasonably up-to-date
    sync_story_state(story_context)

    found_entities = []
    # Prefer iterating through the environment's canonical map if available
    entities_to_search = []
    if hasattr(story_context.environment, 'entity_map') and isinstance(story_context.environment.entity_map, dict):
        entities_to_search = story_context.environment.entity_map.values()
        logger.debug("Searching using environment.entity_map")
    elif hasattr(story_context, 'entities') and isinstance(story_context.entities, list):
        # Fallback to the list stored in story_context if map is unavailable
        entities_to_search = story_context.entities
        logger.debug("Searching using story_context.entities list (fallback)")
    else:
        logger.error("❌ TOOL find_entity_by_type: No searchable entity collection found.")
        return "Error: Cannot access entities in the environment."


    for entity in entities_to_search:
        # Check if entity has a 'type' attribute matching the query (case-insensitive)
        entity_actual_type = getattr(entity, 'type', None)
        if entity_actual_type and isinstance(entity_actual_type, str) and \
           entity_actual_type.lower() == entity_type.lower():
            # Get name and position safely
            name = getattr(entity, 'name', f'Unnamed {entity_type}')
            pos = getattr(entity, 'position', None)
            pos_str = f"at ({pos.x},{pos.y})" if hasattr(pos, 'x') and hasattr(pos, 'y') else "at unknown location"
            found_entities.append(f"{name} ({pos_str})")

    if not found_entities:
        logger.info(f"  TOOL: No entities found matching type '{entity_type}'.")
        return f"You couldn't find any entities of type '{entity_type}' nearby."
    else:
        result_str = f"Found the following '{entity_type}' entities: {'; '.join(found_entities)}."
        logger.info(f"  TOOL: Found entities: {result_str}")
        return result_str


async def go_to_entity_type(story_context: CompleteStoryResult, entity_type: str) -> str:
    """
    Finds an entity of the specified type and moves the player next to it.
    It searches for the nearest entity of that type and uses move_to_object.

    Args:
        story_context: The current game state context.
        entity_type: The type of entity to find and move to (e.g. "log_stool", "campfire", "chest").

    Returns:
        str: A message describing the outcome (moving towards entity, entity not found, path not found).
    """
    logger.info(f"🎯 TOOL: go_to_entity_type called: Type='{entity_type}'")
    if not story_context or not story_context.person or not story_context.environment:
        logger.error("❌ TOOL go_to_entity_type: Missing context, person, or environment.")
        return "Error: Cannot go to entity, game state is incomplete."

    # Ensure environment state is reasonably up-to-date
    sync_story_state(story_context)

    person = story_context.person
    environment = story_context.environment

    # Get player's current position
    current_pos_tuple = None
    if person.position:
        if hasattr(person.position, 'x') and hasattr(person.position, 'y'):
             current_pos_tuple = (person.position.x, person.position.y)
        elif isinstance(person.position, (tuple, list)) and len(person.position) >= 2:
             current_pos_tuple = (person.position[0], person.position[1])
    if not current_pos_tuple:
        logger.error("❌ TOOL go_to_entity_type: Could not determine player's current position.")
        return "Error: Cannot determine your current location to start moving."


    # Find all entities of the specified type
    matching_entities = []
    entities_to_search = []
    if hasattr(environment, 'entity_map') and isinstance(environment.entity_map, dict):
        entities_to_search = environment.entity_map.values()
    elif hasattr(story_context, 'entities') and isinstance(story_context.entities, list):
        entities_to_search = story_context.entities
    else:
         return "Error: Cannot access entities in the environment to search."

    for entity in entities_to_search:
        entity_actual_type = getattr(entity, 'type', None)
        if entity_actual_type and isinstance(entity_actual_type, str) and \
           entity_actual_type.lower() == entity_type.lower():
            pos = getattr(entity, 'position', None)
            if pos and hasattr(pos, 'x') and hasattr(pos, 'y'):
                matching_entities.append(entity)

        if not matching_entities:
            logger.info(f"  TOOL: No entities found matching type '{entity_type}' for go_to.")
            return f"You couldn't find any '{entity_type}' to go to."

    # Find the nearest matching entity
    matching_entities.sort(key=lambda e: PathFinder.manhattan_distance(current_pos_tuple, (e.position.x, e.position.y)))
    nearest_entity = matching_entities[0]
    target_pos = (nearest_entity.position.x, nearest_entity.position.y)
    entity_name = getattr(nearest_entity, 'name', f'the nearest {entity_type}')

    logger.info(f"  TOOL: Nearest '{entity_type}' found: {entity_name} at {target_pos}. Moving towards it.")

    # Use move_to_object to get adjacent to the target entity's position
    result = await move_to_object(story_context, target_pos[0], target_pos[1])

    # Potentially enhance the result message
    if "Successfully" in result or "already standing next to" in result:
        return f"You head towards {entity_name}. {result}"
    elif "Cannot find a path" in result or "no free spaces" in result:
        return f"You found {entity_name}, but couldn't find a clear path to get right next to it. {result}"
    else: # General failure or error message from move_to_object
        return f"Tried to move towards {entity_name}, but encountered an issue. {result}"

# --- End Added Tool Functions ---


# --- StorytellerAgent Class ---

# Map tool names to actual functions
AVAILABLE_TOOLS = {
    "execute_movement_sequence": execute_movement_sequence,
    "look_around": look_around,
    "get_inventory": get_inventory,
    "get_object_details": get_object_details,
    "use_object_with": use_object_with,
    "move_to_object": move_to_object,
    "move": move,
    "jump": jump,
    "find_entity_by_type": find_entity_by_type,
    "go_to_entity_type": go_to_entity_type,
}

print("DEBUG: Defining StorytellerAgentFinal class...") # DEBUG
class StorytellerAgentFinal:
    """Handles the game narrative, interactions, and uses tools based on user input via OpenAI Assistant."""
    
    def __init__(
        self,
        complete_story_result: CompleteStoryResult,
        websocket: WebSocket,
        openai_api_key: str = os.getenv("OPENAI_API_KEY", ""),
        deepgram_api_key: str = os.getenv("DEEPGRAM_API_KEY", ""),
        assistant_id: Optional[str] = None,
        voice: str = DEFAULT_VOICE,
    ):
        """
        Initializes the Storyteller Agent with OpenAI Assistant.

        Args:
            complete_story_result: The initial game state and context.
            websocket: The WebSocket connection to the frontend.
            openai_api_key: OpenAI API key.
            deepgram_api_key: Deepgram API key.
            assistant_id: Optional existing OpenAI Assistant ID to reuse.
            voice: The voice to use for TTS.
        """
        logger.info(f"🚀 Initializing StorytellerAgentFinal with theme: {complete_story_result.theme}")
        self.story_context = complete_story_result  # Store the game context
        self.websocket = websocket  # Store the websocket connection
        self.openai_api_key = openai_api_key
        self.deepgram_api_key = deepgram_api_key
        self.assistant_id = assistant_id
        self.voice = voice
        self.assistant = None
        self.thread = None
        
        # Keep track if a message is being processed
        self.is_processing_message = False 
        
        # Store a reference to self in the game_context for tools to access from AVAILABLE_TOOLS
        self.story_context._storyteller_agent = self
        
        # Ensure API keys are provided
        if not self.openai_api_key:
            raise ValueError("OpenAI API key is missing.")
        
        # Initialize OpenAI client (AsyncOpenAI for async operations)
        try:
            from openai import AsyncOpenAI
            self.openai_client = AsyncOpenAI(api_key=self.openai_api_key)
            # --- ADDED: Initialize separate client for TTS specifically ---
            # This avoids potential conflicts if Assistant API uses client differently
            self.openai_tts_client = AsyncOpenAI(api_key=self.openai_api_key)
            logger.info("✅ Initialized AsyncOpenAI clients (Assistant & TTS)")
        except Exception as e:
            logger.error(f"❌ Failed to initialize OpenAI client: {e}")
            raise  # Re-raise to prevent agent init without client
        
        # Initialize Deepgram client if API key is available
        if not self.deepgram_api_key:
            logger.warning("Deepgram API key is missing. Audio input will not work.")
            self.deepgram_client = None
        else:
            try:
                from deepgram import DeepgramClientOptions
                dg_config = DeepgramClientOptions(verbose=logging.DEBUG if DEBUG_MODE else logging.INFO)
                self.deepgram_client = DeepgramClient(self.deepgram_api_key, dg_config)
                logger.info("✅ Initialized Deepgram client")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize Deepgram client: {e}")
                self.deepgram_client = None
                    
        # Initialize conversation history
        self.conversation_history = []
            
    # <<< START OF METHODS TO RE-INSERT >>>
    async def initialize_assistant_and_thread(self):
        """Asynchronously sets up the OpenAI Assistant and Thread."""
        logger.info("🔧 Setting up OpenAI Assistant and Thread...")
        try:
            # Find or create assistant
            if self.assistant_id:
                logger.info(f"Retrieving existing assistant with ID: {self.assistant_id}")
                self.assistant = await self.openai_client.beta.assistants.retrieve(self.assistant_id)
                logger.info(f"Retrieved assistant '{self.assistant.name}' (ID: {self.assistant.id})")
            else:
                logger.info(f"Searching for assistant named '{ASSISTANT_NAME}'...")
                assistants = await self.openai_client.beta.assistants.list(order="desc", limit=20)
                for assistant in assistants.data:
                    if assistant.name == ASSISTANT_NAME:
                        self.assistant = assistant
                        logger.info(f"Found existing assistant '{self.assistant.name}' (ID: {self.assistant.id})")
                        break

                if not self.assistant:
                    logger.info(f"Creating new assistant '{ASSISTANT_NAME}'...")
                    game_mechanics = get_game_mechanics_reference()
                    system_prompt = get_storyteller_system_prompt(
                        theme=self.story_context.theme,
                        quest_title=self.story_context.narrative_components.get('quest', {}).get('title', 'Untitled Quest'),
                        game_mechanics_reference=game_mechanics
                    )
                    full_instructions = f"{system_prompt}\n\n{game_mechanics}"

                    self.assistant = await self.openai_client.beta.assistants.create(
                        name=ASSISTANT_NAME,
                        instructions=full_instructions,
                        model=ASSISTANT_MODEL,
                        tools=get_tool_schemas(),
                    )
                    self.assistant_id = self.assistant.id
                    logger.info(f"Created assistant '{self.assistant.name}' (ID: {self.assistant.id})")

            # Create a new thread for the session
            logger.info("Creating thread for this session...")
            self.thread = await self.openai_client.beta.threads.create()
            logger.info(f"Thread created with ID: {self.thread.id}")
            
            # Sync state after setup is complete
            sync_story_state(self.story_context)
            
            return True
        except Exception as e:
            logger.error(f"Error during assistant setup: {e}", exc_info=True)
            raise

    async def start(self):
        """Starts the game by initializing the assistant and thread, and sending an initial 'start' message."""
        logger.info(f"🚀 Starting game for theme: {self.story_context.theme}")
        
        # Initialize assistant and thread
        await self.initialize_assistant_and_thread() # Ensure this is called first
        
        # Send initial "start" message to trigger game start
        logger.info("🚀 Sending initial 'start' message to Assistant...")
        try:
            # Use process_text_input to handle the full loop (send, run, get response)
            await self.process_text_input(user_input="start", source="system_init")
            logger.info("✅ Initial 'start' message processed.")
        except Exception as start_err:
            logger.error(f"❌ Error processing initial 'start' message: {start_err}", exc_info=True)
            try:
                await self.websocket.send_text(json.dumps({"type": "error", "content": "Failed to initialize game start."}))
            except Exception:
                pass # Ignore errors sending errors
        
        return self # Return the initialized agent instance
    # <<< END OF METHODS TO RE-INSERT >>>

    # --- Existing methods like setup_assistant (if needed), WebSocket methods, _handle_tool_calls, etc. should follow ---
    
    # Example: Keep the original setup_assistant if it was meant to co-exist or be called elsewhere
    # async def setup_assistant(self): 
    #    # ... original setup_assistant code ...
    #    pass 
    
    # WebSocket methods
    async def send_command_to_frontend(self, command_name: str, params: Dict[str, Any], result_narrative: str = ""):
        """Sends a command object to the frontend via WebSocket.
        """
        if not self.websocket:
            logger.error("❌ Cannot send command to frontend: WebSocket is not set.")
            return

        cmd_data = {
            "type": "command",
            "name": command_name,
            # Include narrative result if provided
            "result": result_narrative if result_narrative else f"{command_name.capitalize()} executed.",
            "params": params,
            "sender": "system" # Commands originate from the system/agent
        }
        try:
            logger.info(f"🎮 Sending command '{command_name}' to frontend. Params: {params}")
            await self.websocket.send_text(json.dumps(cmd_data))
            logger.debug(f"✅ Command '{command_name}' sent successfully.")
                
        except Exception as e:
            logger.error(f"❌ Error sending command '{command_name}' via WebSocket: {e}")
    
    async def _handle_tool_calls(self, run_id: str, tool_calls: List[ToolCall]) -> Tuple[Optional[Dict[str, Any]], str]:
        """Handle tool calls from the Assistant during a run.
        
        Returns:
            Tuple containing (command_info, result_narrative)
            command_info: Information about the command if one was executed, None otherwise
            result_narrative: A text description of the action result
        """
        if not tool_calls or not self.thread:
            return None, "No actions were taken."
        
        # Log each tool call received
        for tool_call in tool_calls:
            logger.info(f"🛠️ Assistant requested tool: {tool_call.function.name}")
            
        # CONSOLIDATE MOVEMENT COMMANDS
        # First parse all commands to identify consecutive move commands
        parsed_tools = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            tool_id = tool_call.id
            tool_args = json.loads(tool_call.function.arguments)
            logger.info(f"Tool arguments: {tool_args}")
            parsed_tools.append({"id": tool_id, "name": tool_name, "args": tool_args})
        
        # Consolidate consecutive non-continuous "move" commands in the same direction
        consolidated_tools = []
        i = 0
        while i < len(parsed_tools):
            current = parsed_tools[i]
            
            # If this is a non-continuous move command, look ahead for more of the same
            if (current["name"] == "move" and 
                not current["args"].get("continuous", False) and
                i + 1 < len(parsed_tools)):
                
                direction = current["args"].get("direction", "")
                is_running = current["args"].get("is_running", False)
                total_steps = current["args"].get("steps", 1)
                combined_ids = [current["id"]]
                
                # Look ahead for consecutive moves in the same direction
                j = i + 1
                while j < len(parsed_tools):
                    next_cmd = parsed_tools[j]
                    if (next_cmd["name"] == "move" and
                        not next_cmd["args"].get("continuous", False) and
                        next_cmd["args"].get("direction") == direction and
                        next_cmd["args"].get("is_running") == is_running):
                        # Add steps from this command
                        total_steps += next_cmd["args"].get("steps", 1)
                        combined_ids.append(next_cmd["id"])
                        j += 1
                    else:
                        break
                
                # If we found consecutive commands, consolidate them
                if len(combined_ids) > 1:
                    logger.info(f"🔄 Consolidating {len(combined_ids)} consecutive '{direction}' moves into a single command with {total_steps} steps")
                    consolidated_tools.append({
                        "id": combined_ids[0],  # Use first ID for the consolidated command
                        "name": "move",
                        "args": {
                            "direction": direction,
                            "is_running": is_running,
                            "continuous": False,
                            "steps": total_steps
                        },
                        "combined_ids": combined_ids  # Store all IDs for output handling
                    })
                    i = j  # Skip to after the last consolidated command
                else:
                    # No consolidation possible, add as-is
                    consolidated_tools.append(current)
                    i += 1
            else:
                # Not a move command or not suitable for consolidation
                consolidated_tools.append(current)
                i += 1
                
        # Process all tool calls in sequence
        tool_outputs = []
        command_info = None
        result_narrative = ""
        
        for tool_info in consolidated_tools:
            tool_name = tool_info["name"]
            tool_id = tool_info["id"]
            tool_args = tool_info["args"]
            error_msg = None  # Initialize error_msg at the start
            
            try:
                # Check if tool exists in available tools
                if tool_name not in AVAILABLE_TOOLS:
                    error_msg = f"Unknown tool: {tool_name}"
                    logger.error(f"❌ {error_msg}")
                    
                    # If this is a consolidated command, need to provide output for all IDs
                    if "combined_ids" in tool_info:
                        for combined_id in tool_info["combined_ids"]:
                            tool_outputs.append({
                                "tool_call_id": combined_id,
                                "output": json.dumps({"error": error_msg})
                            })
                    else:
                        tool_outputs.append({
                            "tool_call_id": tool_id,
                            "output": json.dumps({"error": error_msg})
                        })
                    continue
                
                # Execute the requested tool
                tool_function = AVAILABLE_TOOLS[tool_name]
                
                # All tools expect story_context as their first parameter
                if "story_context" not in tool_args:
                    execution_args = {"story_context": self.story_context, **tool_args}
                else:
                    execution_args = tool_args
                    
                # Execute the tool function with unpacked arguments
                result = await tool_function(**execution_args)
                logger.info(f"📝 Tool execution result: {result}")
                
                # If this is a consolidated command, provide the result to all IDs
                if "combined_ids" in tool_info:
                    for combined_id in tool_info["combined_ids"]:
                        tool_outputs.append({
                            "tool_call_id": combined_id,
                            "output": json.dumps({"result": result})
                        })
                else:
                    tool_outputs.append({
                        "tool_call_id": tool_id,
                        "output": json.dumps({"result": result})
                    })
                
                # If this is a movement command, send it to the frontend
                if tool_name in ["move", "jump", "move_to_object", "go_to_entity_type", "execute_movement_sequence"]:
                    if tool_name == "move":
                        is_continuous = tool_args.get("continuous", False)
                        current_direction = tool_args.get("direction", "")
                        current_steps = tool_args.get("steps", 0)
                        is_running = tool_args.get("is_running", False)
                        
                        # Send the command
                        await self.send_command_to_frontend(
                            "move",
                            {
                                "direction": current_direction,
                                "is_running": is_running,
                                "continuous": is_continuous,
                                "steps": current_steps
                            },
                            result
                        )
                        logger.info(f"🚶 Executed movement: {current_direction}_{current_steps}_{is_running}_{is_continuous}")
                    elif tool_name == "jump":
                        # Send jump command as-is
                        await self.send_command_to_frontend(tool_name, tool_args, result)
                    elif tool_name in ["move_to_object", "go_to_entity_type", "execute_movement_sequence"]:
                        # Frontend only supports simple move and jump commands
                        # Convert complex movement tools to basic move commands
                        logger.info(f"Converting complex movement command '{tool_name}' to basic move for frontend")
                        
                        # Extract any movement information for feedback
                        if tool_name == "move_to_object":
                            target_x = tool_args.get("target_x", 0)
                            target_y = tool_args.get("target_y", 0)
                            feedback_msg = f"Moving to position ({target_x}, {target_y}): {result}"
                            
                            # Just send a single move in the general direction as visual feedback
                            # Get player position to determine direction
                            player_pos = None
                            if hasattr(self.story_context.person, 'position'):
                                pos = self.story_context.person.position
                                if hasattr(pos, 'x') and hasattr(pos, 'y'):
                                    player_pos = (pos.x, pos.y)
                            
                            # Default to right if we can't determine direction
                            direction = "right" 
                            if player_pos:
                                # Determine primary direction to target
                                dx = target_x - player_pos[0]
                                dy = target_y - player_pos[1]
                                if abs(dx) > abs(dy):
                                    direction = "right" if dx > 0 else "left"
                                else:
                                    direction = "down" if dy > 0 else "up"
                            
                            # Send a basic move command to show visual feedback
                            await self.send_command_to_frontend(
                                "move",
                                {
                                    "direction": direction,
                                    "is_running": False,
                                    "continuous": False,
                                    "steps": 1
                                },
                                feedback_msg
                            )
                        else:
                            # For other complex movement commands, just show the result without animation
                            await self.websocket.send_text(json.dumps({
                                "type": "info", 
                                "content": result
                            }))
                    
                    # Store the last command info and result
                    command_info = {"name": tool_name, "params": tool_args}
                    result_narrative = result
                    
            except Exception as e:
                error_msg = f"Error executing {tool_name}: {str(e)}"
                logger.error(f"❌ {error_msg}", exc_info=True)
                
                # If this is a consolidated command, provide the error to all IDs
                if "combined_ids" in tool_info:
                    for combined_id in tool_info["combined_ids"]:
                        tool_outputs.append({
                            "tool_call_id": combined_id,
                            "output": json.dumps({"error": error_msg})
                        })
                else:
                    tool_outputs.append({
                        "tool_call_id": tool_id,
                        "output": json.dumps({"error": error_msg})
                    })
        
        # Submit all tool outputs at once
        try:
            await self.openai_client.beta.threads.runs.submit_tool_outputs(
                thread_id=self.thread.id,
                run_id=run_id,
                tool_outputs=tool_outputs
            )
        except Exception as submit_error:
            logger.error(f"❌ Error submitting tool outputs to Assistant: {submit_error}")
            
        return command_info, result_narrative
    
    async def process_text_input(self, user_input: str, 
                                 conversation_history: Optional[List[Dict[str, str]]] = None,
                                 source: str = "text" # Add source parameter
                                 ) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
        """Process text input via Assistant.
        
        Args:
            user_input: The text input from the user
            conversation_history: Optional list of previous conversation messages
            source: Where the message originated ('text' or 'audio')
            
        Returns:
            Tuple containing:
            - Dict containing the formatted response data
            - Updated conversation history
        """
        # If already processing, inform the user
        if self.is_processing_message:
            logger.info(f"Currently processing another message. Will handle '{user_input}' after completion.")
            info_response = {"type": "info", "content": "Currently processing another message. Please wait."}
            await self.websocket.send_text(json.dumps(info_response))
            return info_response, conversation_history if conversation_history else []
        
        # ---- Process the message ----
        logger.info(f"Processing text input: '{user_input}'")
        self.is_processing_message = True # Mark as processing
        
        if not self.assistant or not self.thread:
            logger.error("❌ Assistant not initialized")
            error_response = {"type": "error", "content": "Assistant not ready"}
            await self.websocket.send_text(json.dumps(error_response))
            self.is_processing_message = False # Reset flag on error
            return error_response, []
        
        try:
            # Initialize conversation history if not provided
            if conversation_history is None:
                conversation_history = []
            
            # Add message to thread
            await self.openai_client.beta.threads.messages.create(
                thread_id=self.thread.id,
                role="user",
                content=user_input
            )
            logger.debug(f"Added message to thread {self.thread.id}")
            
            # Update conversation history (local copy)
            conversation_history.append({"role": "user", "content": user_input})
            
            # Start a run
            run = await self.openai_client.beta.threads.runs.create(
                thread_id=self.thread.id,
                assistant_id=self.assistant.id,
            )
            run_id = run.id
            logger.debug(f"Created run {run_id}")
            
            # Poll for run completion
            command_executed = None
            command_narrative = ""
            max_polls = 60  # Maximum number of polling attempts
            poll_interval = 1  # Seconds between polls
            
            final_response = None # Store the final response data
            
            for _ in range(max_polls):
                # Get current run status
                run = await self.openai_client.beta.threads.runs.retrieve(
                    thread_id=self.thread.id,
                    run_id=run_id
                )
                
                # Check run status
                if run.status == "completed":
                    logger.info("✅ Run completed successfully")
                    break
                    
                elif run.status == "requires_action":
                    if run.required_action and run.required_action.submit_tool_outputs and run.required_action.submit_tool_outputs.tool_calls:
                        logger.info("🛠️ Run requires tool calls")
                        command_executed, command_narrative = await self._handle_tool_calls(
                            run_id=run_id,
                            tool_calls=run.required_action.submit_tool_outputs.tool_calls
                        )
                        
                elif run.status in ["failed", "cancelled", "expired"]:
                    logger.error(f"❌ Run ended with status: {run.status}")
                    error_detail = run.last_error.message if run.last_error else "Unknown error"
                    error_response = {"type": "error", "content": f"Assistant run {run.status}: {error_detail}"}
                    await self.websocket.send_text(json.dumps(error_response))
                    self.is_processing_message = False # Reset flag
                    return error_response, conversation_history
                
                # Wait before polling again
                await asyncio.sleep(poll_interval)
            else:
                 # Handle timeout case (loop finished without completion)
                 logger.error(f"❌ Run polling timed out after {max_polls * poll_interval} seconds.")
                 error_response = {"type": "error", "content": "Assistant took too long to respond."}
                 await self.websocket.send_text(json.dumps(error_response))
                 self.is_processing_message = False # Reset flag
                 return error_response, conversation_history
            
            # Retrieve the final messages
            messages = await self.openai_client.beta.threads.messages.list(
                thread_id=self.thread.id,
                order="desc",
                limit=1 # Get only the latest assistant response
            )
            
            if not messages.data or messages.data[0].role != 'assistant':
                # Check if a command was executed and use its narrative if no text response
                if command_executed:
                    logger.warning("No text response from Assistant, using command narrative.")
                    response_text = command_narrative or "Action completed." # Use narrative or default
                    formatted_answer = self._format_as_answer_set(response_text)
                    final_response = {"type": "json", "content": formatted_answer}
                    # Send the command narrative formatted as JSON
                    await self.websocket.send_text(json.dumps(final_response))
                    # Reset processing flag
                    self.is_processing_message = False
                    # Return the command narrative as the result
                    return final_response if final_response else {}, conversation_history
                else:
                    # No command and no assistant message
                    logger.error("No response or non-assistant message received from Assistant thread.")
                    error_response = {"type": "error", "content": "No valid response received from Assistant"}
                    # Send error, reset flag, and return error
                    await self.websocket.send_text(json.dumps(error_response))
                    self.is_processing_message = False
                    return error_response, conversation_history
            else:
                # Process the assistant's text response
                last_message = messages.data[0]
                content_parts = last_message.content
            
                if not content_parts:
                    logger.error("Received empty response content from Assistant")
                    error_response = {"type": "error", "content": "Received empty response from Assistant"}
                    await self.websocket.send_text(json.dumps(error_response))
                    self.is_processing_message = False # Reset flag
                    return error_response, conversation_history
            
                # Handle text responses
                response_text = ""
                for part in content_parts:
                    if hasattr(part, 'text') and part.text and hasattr(part.text, 'value'):
                        response_text += part.text.value + "\n\n"

                # Add logging to inspect raw response text
                logger.info(f"🕵️ RAW Assistant Response Text (check for newlines): {repr(response_text)}")

                # Update conversation history with assistant's response
                conversation_history.append({"role": "assistant", "content": response_text})
            
                # Check if response contains valid JSON
                try:
                    if response_text.strip().startswith('{') and "answers" in response_text:
                        json_data = json.loads(response_text)
                        final_response = {"type": "json", "content": json_data}
                    else:
                        # Format as AnswerSet if not already
                        formatted_answer = self._format_as_answer_set(response_text)
                        final_response = {"type": "json", "content": formatted_answer}

                        logger.info(f"✅ Checking if TTS should be generated for response (source='{source}')")

                        # Generate and stream TTS if the response is not empty
                        if response_text.strip():
                            logger.info(f"🔊 Generating TTS for response: '{response_text[:50]}...'")
                            try:
                                # Use the dedicated function, passing the initialized client
                                await generate_and_stream_tts(self.websocket,
                                                              response_text.strip(),
                                                              client=self.openai_tts_client)
                            except Exception as tts_error:
                                logger.error(f"❌ Error calling generate_and_stream_tts: {tts_error}")

                        # Send JSON response to frontend
                        await self.websocket.send_text(json.dumps(final_response))

                except json.JSONDecodeError:
                    # Not valid JSON, just format as AnswerSet
                    formatted_answer = self._format_as_answer_set(response_text)
                    final_response = {"type": "json", "content": formatted_answer}

                    # Also attempt TTS for non-JSON text responses
                    if response_text.strip():
                        logger.info(f"🔊 Generating TTS for non-JSON response: '{response_text[:50]}...'")
                        try:
                            await generate_and_stream_tts(self.websocket,
                                                          response_text.strip(),
                                                          client=self.openai_tts_client)
                        except Exception as tts_error:
                            logger.error(f"❌ Error calling generate_and_stream_tts (non-JSON path): {tts_error}")

                        await self.websocket.send_text(json.dumps(final_response))

                # Return the final response and history
                return final_response if final_response else {}, conversation_history

        except Exception as e:
            logger.error(f"❌ Error during text processing: {e}", exc_info=True)
            error_response = {"type": "error", "content": f"Error processing message: {str(e)}"}
            await self.websocket.send_text(json.dumps(error_response))
            return error_response, conversation_history
        
        finally:
            # Reset processing flag when done
            logger.debug(f"Resetting is_processing_message flag after handling '{user_input[:20]}...'")
            self.is_processing_message = False
    
    def _format_as_answer_set(self, text: str) -> Dict[str, Any]:
        """Format a text response as an AnswerSet JSON with options.

        Args:
            text: The text to format

        Returns:
            Dict: AnswerSet in dictionary format
        """
        try:
            # 1. Split text into sentences using regex (handles ., ?, !)
            import re
            sentences = re.split(r'(?<=[.?!])\s+', text.strip()) # Split after punctuation + space
            # Filter out any empty strings resulting from the split
            sentences = [s.strip() for s in sentences if s.strip()]

            if not sentences:
                # Handle case where text has no sentences or is empty
                return {"answers": [{
                    "type": "text",
                    "description": text[:400] if text else "...", # Show original if weird split
                    "options": ["What next?", "Explore more"]
                }]}

            # 2. Generate options based on the *entire original text* for context
            original_text_words = re.findall(r'\b\w+\b', text.lower())
            action_words = [w for w in original_text_words if len(w) > 3 and w not in
                           {'this', 'that', 'with', 'from', 'have', 'what', 'when', 'where',
                            'there', 'their', 'about', 'would', 'could', 'should'}]

            generated_options = []
            if any(word in original_text_words for word in ['move', 'walk', 'go', 'turn', 'north', 'south', 'east', 'west', 'left', 'right', 'up', 'down', 'forward', 'backward']):
                generated_options.append("Look around")
            if any(word in original_text_words for word in ['see', 'look', 'observe', 'watch', 'view']):
                generated_options.append("Look closer")
            if any(word in original_text_words for word in ['inventory', 'item', 'carry', 'holding', 'have']):
                generated_options.append("Check inventory")

            if len(action_words) >= 3:
                action_words = list(set(action_words))
                import random
                random.shuffle(action_words)
                if len(generated_options) < 3 and len(action_words) >= 2:
                    generated_options.append(f"{action_words[0].capitalize()} {action_words[1]}")
                if len(generated_options) < 4 and len(action_words) >= 4:
                    generated_options.append(f"{action_words[2].capitalize()} {action_words[3]}")

            if "?" not in text and len(generated_options) < 4:
                generated_options.append("Ask questions")

            generic_options = ["Explore more", "Try something else", "What next?", "Continue"]
            while len(generated_options) < 2:
                if generic_options:
                    generated_options.append(generic_options.pop(0))
                else:
                    break
            generated_options = generated_options[:4]

            # 3. Create an answer object for each sentence
            all_answers = []
            for i, sentence in enumerate(sentences):
                is_last_sentence = (i == len(sentences) - 1)
                answer = {
                    "type": "text",
                    "description": sentence, # Use the individual sentence
                    "options": generated_options if is_last_sentence else [] # Options only on last
                }
                all_answers.append(answer)

            # 4. Create the final answer set
            answer_set = {
                "answers": all_answers
            }

            return answer_set
        except Exception as e:
            logger.error(f"❌ Error formatting answer set by sentence: {e}")
    
    async def process_audio(self, 
                           audio_data: bytes,
                           on_transcription: Callable[[str], Awaitable[None]] = None,
                           on_response: Callable[[str], Awaitable[None]] = None,
                           on_audio: Callable[[bytes], Awaitable[None]] = None,
                           conversation_history: Optional[List[Dict[str, str]]] = None
                           ) -> Tuple[str, Optional[Dict[str, Any]], List[Dict[str, str]]]:
        """Process audio: Transcribe, then process immediately.
        
        Args:
            audio_data: The binary audio data to process
            on_transcription: Optional callback for transcription results
            on_response: Optional callback for text responses
            on_audio: Optional callback for audio responses
            conversation_history: Optional conversation history
            
        Returns:
            Tuple containing transcription, command info, and updated conversation history
        """
        logger.info(f"Processing audio input: {len(audio_data)} bytes")
        
        if not self.deepgram_client:
            logger.error("❌ Cannot process audio: Deepgram client not initialized")
            await self.websocket.send_text(json.dumps({"type": "error", "content": "Speech recognition not available"}))
            return "", None, conversation_history or []
            
        if not self.openai_client or not self.assistant or not self.thread:
            logger.error("❌ Cannot process audio: OpenAI Assistant not initialized")
            await self.websocket.send_text(json.dumps({"type": "error", "content": "AI Assistant not available"}))
            return "", None, conversation_history or []
            
        transcribed_text = ""
        command_info = None
        
        # Initialize conversation history if not provided
        if conversation_history is None:
            conversation_history = []

        try:
            # Step 1: Transcribe using Deepgram
            source = {'buffer': audio_data, 'mimetype': 'audio/webm'}
            options = PrerecordedOptions(model="nova-2", smart_format=True)
            
            # The Deepgram SDK might have changed - fix the await pattern
            try:
                # First try the async method (newer SDK versions)
                dg_response = await self.deepgram_client.listen.prerecorded.v("1").transcribe_file(source, options)
                transcribed_text = dg_response.results.channels[0].alternatives[0].transcript
            except Exception as deepgram_err:
                # If that fails, try the sync method or handle differently
                logger.warning(f"⚠️ Error with async Deepgram transcription, trying alternative approach: {deepgram_err}")
                # Try calling without await if it's not an awaitable function
                dg_response = self.deepgram_client.listen.prerecorded.v("1").transcribe_file(source, options)
                
                # Properly extract transcription from the response object
                if hasattr(dg_response, 'results') and hasattr(dg_response.results, 'channels'):
                    transcribed_text = dg_response.results.channels[0].alternatives[0].transcript
                else:
                    # If structure is different, try to find transcript in the response
                    logger.error(f"⚠️ Unexpected Deepgram response structure: {dg_response}")
                    if isinstance(dg_response, dict) and 'results' in dg_response:
                        # Handle dictionary response format
                        transcribed_text = dg_response.get('results', {}).get('channels', [{}])[0].get('alternatives', [{}])[0].get('transcript', '')
                    else:
                        # Last resort: prevent further errors
                        transcribed_text = ""
                        logger.error(f"❌ Could not extract transcript from Deepgram response: {dg_response}")
            
            logger.info(f"🎤 Transcription: '{transcribed_text}'")
            
            # Send transcription result using callback or WebSocket
            if on_transcription:
                await on_transcription(transcribed_text)
            else:
                await self.websocket.send_text(json.dumps({"type": "transcription", "content": transcribed_text}))

            if not transcribed_text.strip():
                logger.warning("⚠️ Transcription resulted in empty text")
                await self.websocket.send_text(json.dumps({"type": "warning", "content": "I couldn't hear anything. Please try again."}))
                return transcribed_text, None, conversation_history

            # If agent is already processing a message, tell the user
            if self.is_processing_message:
                logger.info(f"Currently processing another message. Will handle audio input later.")
                info_response = {"type": "info", "content": "Currently processing another message. Please wait."}
                await self.websocket.send_text(json.dumps(info_response))
                return transcribed_text, None, conversation_history
            else:
                # Process immediately since not busy, passing 'audio' source
                response_data, updated_history = await self.process_text_input(transcribed_text, conversation_history, source="audio")
                return transcribed_text, None, updated_history

        except Exception as e:
            logger.error(f"❌ Error in audio processing pipeline: {e}", exc_info=True)
            await self.websocket.send_text(json.dumps({"type": "error", "content": f"Error processing your audio: {str(e)}"}))
            
        # Return transcription, empty command info, and original conversation history on error
        return transcribed_text, None, conversation_history

    async def send_audio_chunks(self, audio_iterator):
        """Sends audio chunks with metadata via the websocket."""
        if not self.websocket:
            logger.error("❌ Cannot send audio: WebSocket not set.")
            return
        try:
            # Send metadata on first audio chunk
            await self.websocket.send_text(json.dumps({
                "type": "audio_start",
                "format": "mp3", # Assuming mp3 format from OpenAI TTS
                "timestamp": time.time()
            }))
            await asyncio.sleep(0.1) # Small delay for client prep

            # Stream audio chunks
            async for chunk in audio_iterator:
                if chunk:
                    await self.websocket.send_bytes(chunk)
                    await asyncio.sleep(0.01) # Slight delay between chunks

            # Signal end of audio stream
            await self.websocket.send_text(json.dumps({"type": "audio_end"}))
            logger.debug("✅ Audio stream finished.")
        except Exception as e:
            logger.error(f"❌ Error sending audio stream: {e}")

# Add the generate_and_stream_tts function back
async def generate_and_stream_tts(websocket: WebSocket, text: str, client: AsyncOpenAI, voice: str = DEFAULT_VOICE, model: str = "tts-1"):
    """
    Generates TTS audio using OpenAI and streams it chunk by chunk over the WebSocket.

    Args:
        websocket: The FastAPI WebSocket connection to send audio data to.
        text: The text to convert to speech.
        client: An initialized AsyncOpenAI client instance.
        voice: The OpenAI TTS voice to use (e.g., 'alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer').
        model: The TTS model to use (e.g., 'tts-1', 'tts-1-hd').
    """
    if not websocket:
        logger.error("❌ Cannot stream TTS: WebSocket is not available.")
        return
    
    # Check if provided client is valid
    if not client or not isinstance(client, AsyncOpenAI):
        logger.error("❌ Cannot stream TTS: Invalid AsyncOpenAI client provided.")
        # Optionally send an error message back
        try:
            await websocket.send_text(json.dumps({"type": "error", "content": "TTS Client Configuration Error"}))
        except Exception: 
            pass # Ignore errors sending errors
        return
        
    logger.info(f"[TTS] Generating audio for: '{text[:30]}...' using voice '{voice}' with provided client.")
        
    try:
        start_time = time.time()
        # Use the provided client instance
        response = await client.audio.speech.create( 
            model=model,
            voice=voice,
            input=text,
            response_format="mp3" # Specify streaming format
        )
        latency = time.time() - start_time
        logger.info(f"[TTS] OpenAI speech generation latency: {latency:.2f}s")

        # Send audio stream start signal
        await websocket.send_text(json.dumps({
            "type": "audio_start",
            "format": "mp3",
            "timestamp": time.time()
        }))
        logger.debug("[TTS] Sent audio_start signal")
        # Small delay might help client prepare
        await asyncio.sleep(0.05) 

        # Stream the audio data chunk by chunk
        chunk_count = 0
        # await the coroutine to get the iterator
        async for chunk in await response.aiter_bytes(chunk_size=4096): # Adjust chunk size if needed
            if chunk:
                await websocket.send_bytes(chunk)
                chunk_count += 1
                # Optional small delay between chunks if needed
                # await asyncio.sleep(0.01) 
        
        logger.info(f"[TTS] Streamed {chunk_count} audio chunks.")

        # Signal end of audio stream
        await websocket.send_text(json.dumps({"type": "audio_end"}))
        logger.debug("[TTS] Sent audio_end signal")

    except BadRequestError as bre:
        logger.error(f"❌ [TTS] OpenAI BadRequestError: {bre.message}")
        # Send error details to frontend if possible
        await websocket.send_text(json.dumps({"type": "error", "content": f"TTS Generation Error: {bre.message}"}))
    except OpenAIError as e:
        logger.error(f"❌ [TTS] OpenAI API error: {e}", exc_info=True)
        # Send generic error to frontend
        await websocket.send_text(json.dumps({"type": "error", "content": "TTS Generation Error"}))
    except Exception as e:
        logger.error(f"❌ [TTS] Unexpected error during TTS generation or streaming: {e}", exc_info=True)
        # Send generic error to frontend
        await websocket.send_text(json.dumps({"type": "error", "content": "Unexpected TTS Error"}))

# --- End of generate_and_stream_tts definition ---
