import heapq  # Add heapq import for PathFinder
import inspect
import json
import logging
import os
import asyncio  # Added for audio processing delays
import time
import traceback
from functools import wraps
from typing import Dict, Any, Tuple, Awaitable, Callable, List, Optional, Union, Literal, Annotated

from pydantic import BaseModel, Field, field_validator
from pydantic.json_schema import models_json_schema

from fastapi import WebSocket

from agent_copywriter_direct import Environment, CompleteStoryResult, Position
from game_object import GameObject, Container  # Added
from person import Person  # Added
from prompt.storyteller_prompts import get_storyteller_system_prompt, get_game_mechanics_reference

# Import shared logging utils
from utils import log_tool_execution, _format_result_for_logging

try:
    from agents import Agent, Runner, function_tool, \
        RunContextWrapper  # Added RunContextWrapper here
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

# --- Constants, Config & Logger Setup ---
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = logging.DEBUG if DEBUG_MODE else logging.INFO
DEFAULT_VOICE = "nova"
# Use environment variable or empty string
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")

root_logger = logging.getLogger()
if root_logger.hasHandlers():
    root_logger.handlers.clear()

logging.basicConfig(level=LOG_LEVEL,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("StorytellerAgentFinal")
if DEBUG_MODE:
    logger.info("🔧 Debug mode enabled for StorytellerAgentFinal.")


# --- Utility Functions ---
# Remove duplicated log_tool_execution decorator
# def log_tool_execution(func: Callable) -> Callable:
# ... (entire function removed) ...

# Remove duplicated _format_result_for_logging helper
# def _format_result_for_logging(result: Any) -> tuple[str, Any]:
# ... (entire function removed) ...


# --- Model Definitions ---

# --- Movement Command Models ---

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
        instance = info.context.get("instance", {})
        command_type = instance.get("command_type")

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


@function_tool
@log_tool_execution
async def execute_movement_sequence(
    ctx: RunContextWrapper[CompleteStoryResult],
    commands: List[MovementCommand]
) -> str:
    """Executes a sequence of movement commands.

    Args:
        ctx: The RunContext containing the game state.
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
                    result = await _internal_move(
                        ctx,
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
                    result = await _internal_jump(
                        ctx,
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

    return "\n".join(results)


# --- End Movement Command Models ---


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


class DirectionHelper:
    """Helper class for handling relative directions and movement.

    Coordinate system:
    - X-axis: Positive values go right, negative values go left
    - Y-axis: Positive values go down, negative values go up
              (inverted compared to traditional Cartesian coordinates to match frontend)

    This matches the frontend Three.js coordinate system and browser coordinate system
    where (0,0) is at the top-left corner.
    """

    @staticmethod
    def get_relative_position(
        current_pos: Tuple[int, int], direction: str) -> Tuple[int, int]:
        x, y = current_pos
        direction = direction.lower()
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
            is_person = hasattr(entity, 'id') and entity.id == person.id
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


async def _internal_move(ctx: RunContextWrapper[CompleteStoryResult], direction: str, is_running: bool,
                         continuous: bool, steps: int) -> str:
    """Internal logic for moving the player character. DOES NOT send commands to frontend."""
    # Safety check for ctx and context
    if ctx is None:
        logger.error("💥 INTERNAL: Critical error - ctx parameter is None")
        return "Error: Game context is missing. Please try setting the theme again."

    # Get the context object and check if it's valid
    story_result = getattr(ctx, "context", None)
    if story_result is None:
        logger.error("💥 INTERNAL: Critical error - ctx.context is None")
        return "Error: Game state is not properly initialized. Please try setting the theme again."

    # Check if person exists
    if not hasattr(story_result, 'person') or story_result.person is None:
        logger.error(
            "💥 INTERNAL: Critical error - story_result.person is missing or None")
        return "Error: Player character not found in game. Please try setting the theme again."

    # Check if environment exists
    if not hasattr(story_result, 'environment') or story_result.environment is None:
        logger.error(
            "💥 INTERNAL: Critical error - story_result.environment is missing or None")
        return "Error: Game environment not found. Please try setting the theme again."
    else:
        # CORRECT: Assign environment here, since we know it exists
        environment = story_result.environment
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

    person = story_result.person
    logger.info(
        f"Executing internal move logic: Dir={direction}, Steps={steps}, Running={is_running}, Cont={continuous}")

    direction_map = {
        "north": "up", "south": "down", "east": "right", "west": "left",
        "up": "up", "down": "down", "left": "left", "right": "right"
    }
    direction_label = direction.lower()
    if direction_label not in direction_map:
        return f"❌ Unknown direction: '{direction}'. Use north, south, east, west, up, down, left, or right."
    direction_internal = direction_map[direction_label]

    if continuous:
        logger.info(f"  Calculating continuous move {direction_label}...")
        # FIXED: Use DirectionHelper.move_continuously that we already fixed above
        # instead of directly calling a non-existent method on person
        result_msg = await DirectionHelper.move_continuously(story_result, direction_internal)
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

            # FIXED: Check the Person.move method's parameter order
            # Now correctly create a Position object and pass it to move
            try:
                if target_pos_tuple:
                    # Create Position object from target_pos_tuple
                    target_position = Position(
    x=target_pos_tuple[0], y=target_pos_tuple[1])
                    # Call person.move with correct parameters
                    step_result = person.move(
    story_result.environment, target_position, is_running)
                else:
                    # Cannot determine target position
                    step_result = {
    "success": False,
     "message": "Could not determine target position for movement"}
            except Exception as e:
                logger.error(f"Failed to call move: {e}")
                return f"❌ Error executing move command: {str(e)}"

            # Ensure step_result is not None before accessing properties
            if step_result is None:
                logger.error(
                    "Move method returned None instead of a result dictionary")
                step_result_msg = "Move method returned None"
                break  # Stop trying to move
            else:
                step_result_msg = step_result.get('message', 'Unknown reason')
                if step_result.get("success", False):
                    actual_steps_taken += 1
                else:
                    logger.info(
                        f"    Step {i + 1}/{steps} failed (reported by person.move): {step_result_msg}. Stopping.")  # Clarified log source
                    break  # Stop moving if a step fails

        if actual_steps_taken > 0:
            action_verb = "ran" if is_running else "walked"
            return f"✅ Successfully {action_verb} {direction_label} {actual_steps_taken} step{'s' if actual_steps_taken != 1 else ''}. Now at {person.position}."
        else:
            return f"❌ Could not move {direction_label} from {start_pos}. Reason: {step_result_msg}"


async def _internal_jump(
    ctx: RunContextWrapper[CompleteStoryResult],
    target_x: int,
     target_y: int) -> str:
    """Internal logic for making the player character jump. DOES NOT send commands to frontend."""
    # Safety check for ctx and context
    if ctx is None:
        logger.error("💥 INTERNAL: Critical error - ctx parameter is None")
        return "Error: Game context is missing. Please try setting the theme again."

    # Get the context object and check if it's valid
    story_result = getattr(ctx, "context", None)
    if story_result is None:
        logger.error("💥 INTERNAL: Critical error - ctx.context is None")
        return "Error: Game state is not properly initialized. Please try setting the theme again."

    # Check if person exists
    if not hasattr(story_result, 'person') or story_result.person is None:
        logger.error(
            "💥 INTERNAL: Critical error - story_result.person is missing or None")
        return "Error: Player character not found in game. Please try setting the theme again."

    # Check if environment exists
    if not hasattr(
    story_result,
     'environment') or story_result.environment is None:
        logger.error(
            "💥 INTERNAL: Critical error - story_result.environment is missing or None")
        return "Error: Game environment not found. Please try setting the theme again."

    person = story_result.person
    environment = story_result.environment
    logger.info(f"Executing internal jump logic to: ({target_x}, {target_y})")

    target_pos = Position(x=target_x, y=target_y)
    result = person.jump(target_pos, environment)

    if result.get("success", False):
         return f"✅ {result.get('message', 'Jump successful')}. Now at {person.position}."
    else:
         return f"❌ {result.get('message', 'Jump failed')}"


# --- Reconstructed Tool Definitions ---

@function_tool
@log_tool_execution
async def look_around(
    ctx: RunContextWrapper[CompleteStoryResult],
     radius: int) -> str:
    """Looks around the player's current position within a given radius to identify nearby objects and entities.

    Args:
        ctx: The RunContext containing the game state.
        radius: How far to look (number of squares, between 1 and 10).

    Returns:
        str: A description of what the player sees nearby.
    """
    # Enhanced logging to track context issues
    logger.info(f"🔍 look_around called with radius={radius}")

    # Handle missing context gracefully
    if ctx is None:
        logger.error("❌ ctx is None in look_around!")
        return "Error: Context is missing. Please try reloading the theme."

    # Get story_result from context with a fallback for direct access
    story_result = getattr(ctx, "context", None)

    # If context is still None, try to get it from global sources
    if story_result is None:
        logger.error(
            "❌ ctx.context is None in look_around! Attempting to recover context...")
        # We need to get the context from global sources, like active_connections in main.py
        # For now, just return an error asking the user to reload
        return "Error: Game state is missing. Please try reloading the theme and making a new command."

    # Check if story_result has required attributes
    if not story_result or not hasattr(
    story_result,
     'person') or not story_result.person:
        logger.error(
            f"❌ Missing person object in story_result: {getattr(story_result, 'person', None)}")
        return "Cannot look around - the player character is missing."

    if not hasattr(
    story_result,
     'environment') or not story_result.environment:
        logger.error(
            f"❌ Missing environment object in story_result: {getattr(story_result, 'environment', None)}")
        return "Cannot look around - the game environment is missing."

    # Validate radius internally (don't use default parameter)
    if radius <= 0:
        logger.warning(
            f"Invalid radius value {radius} provided, using minimum value 1 instead")
        radius = 1
    elif radius > 10:
        logger.warning(
            f"Radius value {radius} exceeds maximum, clamping to 10")
        radius = 10

    person = story_result.person
    environment = story_result.environment

    # Ensure position exists
    if not person.position:
        logger.error("❌ Person position is None in look_around")
        return "You don't seem to be anywhere specific to look around from."

    # Debug position information
    if hasattr(person.position, 'x') and hasattr(person.position, 'y'):
        logger.info(
            f"👤 Player position: ({person.position.x}, {person.position.y})")
    elif isinstance(person.position, (tuple, list)) and len(person.position) >= 2:
        logger.info(
            f"👤 Player position: ({person.position[0]}, {person.position[1]})")
    else:
        logger.warning(f"⚠️ Unusual position format: {person.position}")

    try:
        # Enhanced error checking for look method
        if not hasattr(person, 'look') or not callable(person.look):
            logger.error("❌ Person object is missing the 'look' method!")
            # Create a basic description of surroundings
            return "You look around but can't focus. (Error: Character functionality is limited)"

        # Ensure the environment is properly set up for looking
        if not hasattr(
    environment,
    'is_valid_position') or not callable(
        environment.is_valid_position):
            logger.error("❌ Environment is missing is_valid_position method!")
            return "You scan the area but can't make sense of your surroundings. (Error: Map functionality is limited)"

        # Call the look method with extra error handling
        look_result = person.look(environment=environment, radius=radius)

        if not look_result.get("success"):
            logger.warning(
                f"⚠️ look failed: {look_result.get('message', 'Unknown reason')}")
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

        # Store nearby objects in story_result for future reference
        # IMPORTANT: Always create a fresh dictionary to prevent stale
        # references
        if not hasattr(
    story_result,
     'nearby_objects') or story_result.nearby_objects is None:
            story_result.nearby_objects = {}

        # IMPROVED: Update with complete objects including position information
        # First clear the dictionary to remove any stale references
        story_result.nearby_objects.clear()

        # Add objects with full details
        for obj_id, obj in nearby_objects.items():
            # Only store actual objects, not just IDs
            if hasattr(obj, 'id'):
                story_result.nearby_objects[obj_id] = obj
                logger.debug(
                    f"Added object to nearby_objects: {obj_id}, pos={getattr(obj, 'position', 'unknown')}")

        # Add entities with full details
        for ent_id, ent in nearby_entities.items():
            # Only store actual objects, not just IDs
            if hasattr(ent, 'id'):
                story_result.nearby_objects[ent_id] = ent
                logger.debug(
                    f"Added entity to nearby_objects: {ent_id}, pos={getattr(ent, 'position', 'unknown')}")

        # Log the count of objects stored
        logger.info(
            f"✅ Updated nearby_objects with {len(story_result.nearby_objects)} items")

        return "You look around. " + ". ".join(descriptions) + "."

    except Exception as e:
        logger.error(
    f"❌ Error during look_around execution: {e}",
     exc_info=True)
        return f"An unexpected error occurred while trying to look around: {e}"


@function_tool
@log_tool_execution
async def get_inventory(ctx: RunContextWrapper[CompleteStoryResult]) -> str:
    """Checks the player's inventory and lists the items being carried.

    Args:
        ctx: The RunContext containing the game state.

    Returns:
        str: A list of items in the inventory or a message saying it's empty.
    """
    story_result = ctx.context
    if not story_result or not story_result.person:
        return "❌ Error: Cannot check inventory. Player not found."

    person = story_result.person
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

    return f"You check your inventory. You are carrying: {', '.join(item_names)}."


@function_tool
@log_tool_execution
async def get_object_details(
    ctx: RunContextWrapper[CompleteStoryResult],
     object_id: str) -> str:
    """Examines a specific nearby object or an item in the inventory to get more details about it.

    Args:
        ctx: The RunContext containing the game state.
        object_id: The unique ID of the object or item to examine.

    Returns:
        str: A description of the object/item, or an error message if not found.
    """
    story_result = ctx.context
    if not story_result or not story_result.person or not story_result.environment:
        return "❌ Error: Game state not ready to examine objects."

    person = story_result.person
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
                break

    # 2. Check nearby objects (if not found in inventory)
    if not target_object:
        # Ensure nearby_objects exists and is updated
        if not hasattr(story_result, 'nearby_objects'):
            logger.warning(
                "⚠️ nearby_objects not found in context for get_object_details. Attempting look.")
            await look_around(ctx)  # Try to update nearby objects

        if hasattr(
    story_result,
     'nearby_objects') and story_result.nearby_objects:
            target_object = story_result.nearby_objects.get(object_id)

    # 3. Check environment map as a last resort (less reliable)
    if not target_object and hasattr(story_result.environment, 'entity_map'):
        target_object = story_result.environment.entity_map.get(object_id)

    if not target_object:
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

    return " ".join(details)


@function_tool
@log_tool_execution
async def use_object_with(
    ctx: RunContextWrapper[CompleteStoryResult],
    item1_id: str,
     item2_id: str) -> str:
    """Uses one item (item1_id from inventory) with another item or object (item2_id from inventory or nearby).

    Args:
        ctx: The RunContext containing the game state.
        item1_id: The ID of the item from inventory to use.
        item2_id: The ID of the target item/object (in inventory or nearby).

    Returns:
        str: A message describing the result of the action (success or failure).
    """
    story_result = ctx.context
    if not story_result or not story_result.person or not story_result.environment:
        return "❌ Error: Game state not ready for item interaction."

    person = story_result.person
    # Pass environment if needed by use_with
    environment = story_result.environment

    # Ensure nearby_objects is populated for the Person method to use
    if not hasattr(story_result, 'nearby_objects'):
        logger.warning(
            "⚠️ nearby_objects not found in context for use_object_with. Attempting look.")
        await look_around(ctx)  # Try to update nearby objects

    nearby_objects_dict = getattr(story_result, 'nearby_objects', {})

    if not hasattr(
    person,
    'use_object_with') or not callable(
        person.use_object_with):
        logger.error(
            "❌ Person object is missing the 'use_object_with' method!")
        return "❌ Error: Interaction logic is missing for the character."

    try:
        # Call the method on the Person instance, passing necessary context
        result = person.use_object_with(
            item1_id=item1_id,
            item2_id=item2_id,
            environment=environment,  # Pass environment
            nearby_objects=nearby_objects_dict  # Pass nearby objects dict
        )

        if isinstance(result, dict):
            return result.get(
    "message", "❓ Interaction occurred, but result unclear.")
        else:
            # Handle cases where the underlying method might not return a dict
            logger.warning(
                f"⚠️ Unexpected return type from person.use_object_with: {type(result)}. Result: {result}")
            # Return raw result if not dict
            return f"❓ Interaction result: {result}"

    except Exception as e:
        logger.error(
    f"❌ Error during use_object_with execution: {e}",
     exc_info=True)
        return f"❌ An unexpected error occurred while trying to use '{item1_id}' with '{item2_id}': {e}"


# --- End Reconstructed Tool Definitions ---


@function_tool
@log_tool_execution
async def move_to_object(
    ctx: RunContextWrapper[CompleteStoryResult],
    target_x: int,
     target_y: int) -> str:
    """Moves the player towards an object by finding an adjacent path and executing the steps.
    This is useful for approaching objects or locations without needing to land exactly on them.
    The tool calculates the path and executes the necessary move/jump steps.

    Args:
        ctx: The RunContext containing the game state.
        target_x: The X coordinate of the target object/location.
        target_y: The Y coordinate of the target object/location.

    Returns:
        str: Description of the movement result (success, failure, path taken) or an error message.
    """
    logger.info(
        f"🚶‍♂️ Tool: move_to_object(target_x={target_x}, target_y={target_y})")

    # Safety check for context and other required objects
    if ctx is None or not hasattr(ctx, 'context'):
        return "❌ Error: Game context not available"

    story_result = ctx.context
    if not story_result:
        return "❌ Error: Game state is missing"

    if not hasattr(story_result, 'person') or not story_result.person:
        return "❌ Error: Player character not found."

    if not hasattr(
    story_result,
     'environment') or not story_result.environment:
        return "❌ Error: Game environment not found."

    person = story_result.person
    environment = story_result.environment

    # Ensure we have a valid current position
    current_pos_tuple = None
    if person.position:
        if hasattr(person.position, 'x') and hasattr(person.position, 'y'):
             current_pos_tuple = (person.position.x, person.position.y)
        elif isinstance(person.position, (tuple, list)) and len(person.position) >= 2:
             current_pos_tuple = (person.position[0], person.position[1])

    if not current_pos_tuple:
        logger.error(
            f"💥 TOOL moveToObject: Invalid or missing player start position: {person.position}")
        sync_story_state(story_result)  # Attempt to sync state to fix position
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
        f"  Player at {current_pos_tuple}, Target location {target_pos}")

    # Check if already adjacent to target
    if PathFinder.manhattan_distance(current_pos_tuple, target_pos) == 1:
        logger.info("  Player is already adjacent to the target location.")
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
            f"  No valid, empty adjacent spaces found around target {target_pos}")
        obj_at_target = environment.get_object_at(target_pos)
        obj_name = getattr(
    obj_at_target,
    'name',
     'the target location') if obj_at_target else 'the target location'
        return f"There are no free spaces to stand next to {obj_name} at ({target_x},{target_y})."

    logger.debug(
        f"  Found {len(adjacent_candidates)} potential adjacent spots: {adjacent_candidates}")

    # Find the best adjacent position (closest to player)
    best_destination = None
    min_dist = float('inf')
    for dest_pos in adjacent_candidates:
        dist = PathFinder.manhattan_distance(current_pos_tuple, dest_pos)
        if dist < min_dist:
            min_dist = dist
            best_destination = dest_pos

    if not best_destination:
         logger.error(
             "  Failed to select a best destination despite having candidates.")
         return "Error: Could not determine the best adjacent spot to move to."

    logger.info(f"  Selected best adjacent destination: {best_destination}")

    # Find path to best destination
    path = PathFinder.find_path(
    environment,
    current_pos_tuple,
     best_destination)

    if not path:
        logger.warning(
            f"  No path found from {current_pos_tuple} to {best_destination}")
        return f"Cannot find a path to reach the space next to ({target_x},{target_y})."

    if len(path) < 2:  # Need at least start and end points
        logger.warning(
            f"  Invalid path (too short) from {current_pos_tuple} to {best_destination}")
        return f"Already at or too close to target location ({target_x},{target_y})."

    logger.info(f"  Path found with {len(path) - 1} steps: {path}")

    # Generate movement commands for the path
    movement_commands_models: List[MovementCommand] = []
    try:
        for i in range(len(path) - 1):
            start_step = path[i]
            end_step = path[i + 1]
            dx = end_step[0] - start_step[0]
            dy = end_step[1] - start_step[1]

            tool_name: Literal['move', 'jump'] | None = None
            params_dict: Dict[str, Any] = {}

            if abs(dx) + abs(dy) == 1:  # Cardinal move
                tool_name = "move"
                if dx == 1:
                    direction = "right"
                elif dx == -1:
                    direction = "left"
                elif dy == 1:
                    direction = "down"  # Assuming Y+ is down
                else:
                    direction = "up"  # Assuming Y- is up
                params_dict = {
    "direction": direction,
    "is_running": False,
    "continuous": False,
     "steps": 1}
            elif abs(dx) + abs(dy) == 2:  # Jump move
                tool_name = "jump"
                params_dict = {
    "target_x": end_step[0],
     "target_y": end_step[1]}
            else:
                logger.error(
                    f"  Invalid step in path: {start_step} -> {end_step}. Stopping command generation.")
                return f"Internal error: Invalid step found in generated path near {start_step}."

            if tool_name:
                try:
                    if tool_name == 'move':
                        validated_params = MovementCommand(
                            command_type=tool_name, **params_dict)
                    elif tool_name == 'jump':
                        validated_params = MovementCommand(
                            command_type=tool_name, **params_dict)
                    else:
                        raise ValueError("Invalid tool name")
                    movement_commands_models.append(validated_params)
                except ValidationError as e:
                    logger.error(
                        f"  Pydantic validation error generating command for step {i + 1}: {e}")
                    return f"Internal error: Failed to create valid command for step {i + 1}. Details: {e}"
    except Exception as path_error:
        logger.error(f"Error processing path: {path_error}")
        return f"Error calculating movement commands: {str(path_error)}"

    if not movement_commands_models:
        logger.warning(
            f"  No movement commands generated for path from {current_pos_tuple} to {best_destination}")
        return "No movement required or path was invalid."

    logger.info(
        f"  Generated {len(movement_commands_models)} step commands for sequence.")

    try:
        logger.info(
            f"  Calling execute_movement_sequence to run generated steps...")
        execution_result = await execute_movement_sequence(ctx, movement_commands_models)
        logger.info(
            f"  execute_movement_sequence call finished: {execution_result}")
        return execution_result
    except Exception as e:
        logger.error(
    f"  Error calling execute_movement_sequence: {e}",
     exc_info=True)
        return f"An error occurred while trying to execute the movement sequence: {e}"


@function_tool
@log_tool_execution
async def move(
    ctx: RunContextWrapper[CompleteStoryResult],
    direction: Literal["up", "down", "left", "right"],
    is_running: bool,
    continuous: bool,
    steps: int
) -> str:
    """Move the player character step-by-step or continuously in a given cardinal direction.

    Args:
        ctx: The RunContext containing the game state.
        direction: Cardinal direction (up, down, left, right).
        is_running: Whether to run (move faster).
        continuous: If True, keeps moving until hitting an obstacle or edge.
        steps: The number of steps to take if continuous is False.

    Returns:
        str: Description of the movement result or an error message.
    """
    try:
        # Safety check for ctx and context
        if ctx is None:
            logger.error("💥 TOOL: Critical error - ctx parameter is None")
            return "Error: Game context is missing. Please try setting the theme again."

        # Get the context object and check if it's valid
        story_result = getattr(ctx, "context", None)
        if story_result is None:
            logger.error("💥 TOOL: Critical error - ctx.context is None")
            return "Error: Game state is not properly initialized. Please try setting the theme again."

        # Normalize direction parameter
        direction = direction.lower()

        # Set default value for steps internally if needed
        if steps <= 0:
            steps = 1
            logger.warning(
                f"Invalid steps value {steps} provided, using default value 1 instead")

        # Check if person exists
        if not hasattr(story_result, 'person') or story_result.person is None:
            logger.error(
                "💥 TOOL: Critical error - story_result.person is missing or None")
            return "Error: Player character not found in game. Please try setting the theme again."

        # Check if environment exists
        if not hasattr(
    story_result,
     'environment') or story_result.environment is None:
            logger.error(
                "💥 TOOL: Critical error - story_result.environment is missing or None")
            return "Error: Game environment not found. Please try setting the theme again."

        person = story_result.person
        environment = story_result.environment

        # Log debug information about objects
        logger.debug(
            f"Person object: {type(person)}, Environment object: {type(environment)}")

        # Make sure position exists
        if person.position is None:
            # Try to get position from environment if available, otherwise
            # default
            default_pos = (
    environment.width //
    2,
    environment.height //
    2) if environment else (
        20,
         20)
            person.position = default_pos
            logger.warning(
                f"Player position was None, set to default: {person.position}")

        # Handle potential None position again after default assignment attempt
        if person.position is None:
            logger.error(
                "💥 TOOL: Critical error - Player position is still None after attempting default assignment.")
            return "Error: Cannot determine player's starting position."

        # Ensure position is usable (convert if needed, though Person class
        # should handle tuples)
        current_pos_tuple = None
        if hasattr(person.position, 'x') and hasattr(person.position, 'y'):
             current_pos_tuple = (person.position.x, person.position.y)
        elif isinstance(person.position, (tuple, list)) and len(person.position) >= 2:
             current_pos_tuple = (person.position[0], person.position[1])
        else:
            logger.error(
                f"💥 TOOL: Invalid current_pos format in move tool: {person.position}")
            return "Error: Could not determine valid starting coordinates."

        orig_pos = current_pos_tuple  # Use the validated tuple
        logger.info(
            f"🏃 Starting {'continuous ' if continuous else ''}movement: {direction} from {orig_pos}")

        # Use the DirectionHelper for continuous movement
        if continuous:
            # Pass the validated tuple position to the helper
            return await DirectionHelper.move_continuously(story_result, direction)

        # Execute the steps one at a time
        result = await _internal_move(ctx, direction=direction, is_running=is_running, continuous=continuous, steps=steps)

        # --- START RE-ADDITION: Send command for NON-CONTINUOUS moves ---
        if not continuous and result and result.startswith("✅ Successfully"):
            storyteller = getattr(story_result, '_storyteller_agent', None)
            if storyteller and hasattr(storyteller, 'send_command_to_frontend'):
                try:
                    # Attempt to parse actual steps taken from the result string
                    import re
                    match = re.search(r" (\\d+) step", result)
                    actual_steps_taken = int(match.group(1)) if match else steps

                    command_params = {
                        "direction": direction,
                        "steps": actual_steps_taken,
                        "is_running": is_running,
                        "continuous": False
                    }
                    logger.info(f"🚀 TOOL (non-continuous): Sending move command to frontend: {command_params}")
                    # Use the result string from _internal_move as the message
                    await storyteller.send_command_to_frontend("move", command_params, result)
                    logger.info("✅ TOOL (non-continuous): Move command sent to frontend.")
                except Exception as e:
                    logger.error(f"❌ TOOL (non-continuous): Error sending move command to frontend: {e}")
            else:
                 logger.warning("⚠️ TOOL (non-continuous): Could not access storyteller agent to send move command.")
        # --- END RE-ADDITION ---

        # Note: Continuous move commands are sent from DirectionHelper.move_continuously

        return result
    except Exception as e:
        logger.error(
    f"💥 TOOL: Unexpected error during movement: {str(e)}",
     exc_info=True)
        return f"Error during movement: {str(e)}"


@function_tool
@log_tool_execution
async def jump(
    ctx: RunContextWrapper[CompleteStoryResult],
    target_x: int,
    target_y: int
) -> str:
    """Makes the player character jump two squares horizontally or vertically over an obstacle.

    Args:
        ctx: The RunContext containing the game state.
        target_x: The destination X coordinate (must be 2 squares away).
        target_y: The destination Y coordinate (must be 2 squares away).

    Returns:
        str: Description of the jump result or an error message.
    """
    logger.info(f"🤸 Tool: jump(target_x={target_x}, target_y={target_y})")
    try:
        # Safety check for ctx and context
        if ctx is None:
            logger.error("💥 TOOL: Critical error - ctx parameter is None")
            return "Error: Game context is missing. Please try setting the theme again."

        # Get the context object and check if it's valid
        story_result = getattr(ctx, "context", None)
        if story_result is None:
            logger.error("💥 TOOL: Critical error - ctx.context is None")
            return "Error: Game state is not properly initialized. Please try setting the theme again."

        # Check if person exists
        if not hasattr(story_result, 'person') or story_result.person is None:
            logger.error(
                "💥 TOOL: Critical error - story_result.person is missing or None")
            return "Error: Player character not found in game. Please try setting the theme again."

        # Check if environment exists
        if not hasattr(
    story_result,
     'environment') or story_result.environment is None:
            logger.error(
                "💥 TOOL: Critical error - story_result.environment is missing or None")
            return "Error: Game environment not found. Please try setting the theme again."

        result = await _internal_jump(ctx, target_x=target_x, target_y=target_y)

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
                logger.info(
                    f"🚀 TOOL: Sending jump command to frontend via websocket")
                await storyteller.send_command_to_frontend("jump", command_params, result)
                logger.info(f"✅ TOOL: Jump command sent to frontend")
            except Exception as e:
                logger.error(f"❌ TOOL: Error sending jump command: {e}")
        else:
            logger.warning(
                f"⚠️ TOOL: Could not access storyteller agent to send jump command")

        return result
    except Exception as e:
        logger.error(f"💥 TOOL: Error during jump: {str(e)}", exc_info=True)
        return f"Error during jump: {str(e)}"


@function_tool
@log_tool_execution
async def find_entity_by_type(
    ctx: RunContextWrapper[CompleteStoryResult],
    entity_type: str
) -> str:
    """Finds entities of a specific type in the game environment and returns their locations.

    Args:
        ctx: The RunContext containing the game state.
        entity_type: The type of entity to search for (e.g. "log_stool", "campfire", "chest").

    Returns:
        str: Information about found entities including their IDs, names, and positions.
    """
    logger.info(f"🔍 Searching for entities of type: {entity_type}")

    # Safety check for ctx and context
    if ctx is None:
        logger.error("💥 TOOL: Critical error - ctx parameter is None")
        return "Error: Game context is missing. Please try setting the theme again."

    # Get the context object and check if it's valid
    story_result = getattr(ctx, "context", None)
    if story_result is None:
        logger.error("💥 TOOL: Critical error - ctx.context is None")
        return "Error: Game state is not properly initialized. Please try setting the theme again."

    # Check if environment exists
    if not hasattr(
    story_result,
     'environment') or story_result.environment is None:
        logger.error(
            "💥 TOOL: Critical error - story_result.environment is missing or None")
        return "Error: Game environment not found. Please try setting the theme again."

    environment = story_result.environment

    # Get all entities from the environment
    entities = []

    # First try to get entities from the story_result
    if hasattr(story_result, 'entities') and story_result.entities:
        entities.extend(story_result.entities)

    # Then try to get from environment.entity_map if available
    if hasattr(environment, 'entity_map') and environment.entity_map:
        for entity_id, entity in environment.entity_map.items():
            if entity not in entities:
                entities.append(entity)

    if not entities:
        return f"No entities found in the game environment."

    # Helper function to normalize entity types for matching
    def normalize_entity_type(type_str):
        if not type_str:
            return ""
        # Convert to lowercase
        normalized = type_str.lower()
        # Handle special cases
        mapping = {
            "stool": "log_stool",  # Map stool to log_stool
            "log": "log_stool",    # Map log to log_stool
            "fire": "campfire",    # Map fire to campfire
            "pot": "campfire_pot"  # Map pot to campfire_pot
        }
        # Check both the original and for each word in the type
        words = normalized.split('_')
        for word in words:
            if word in mapping:
                return mapping[word]
        # Return the original normalized string if no mapping applies
        return normalized

    # Normalize the search type
    normalized_search_type = normalize_entity_type(entity_type)
    logger.debug(
        f"Normalized search type from '{entity_type}' to '{normalized_search_type}'")

    # Filter entities by type
    matching_entities = []
    for entity in entities:
        entity_type_value = getattr(entity, 'type', None)

        if not entity_type_value:
            continue

        # Normalize the entity's type
        normalized_entity_type = normalize_entity_type(entity_type_value)

        # Check for exact match or partial match (with normalized values)
        if (normalized_entity_type == normalized_search_type or
            normalized_search_type in normalized_entity_type or
            normalized_entity_type in normalized_search_type or
            entity_type.lower() in entity_type_value.lower() or
            entity_type_value.lower() in entity_type.lower()):
            matching_entities.append(entity)

    if not matching_entities:
        # If no matches with normalization, try matching against entity names
        # too
        for entity in entities:
            entity_name = getattr(entity, 'name', '').lower()
            if entity_name and entity_type.lower() in entity_name:
                matching_entities.append(entity)

    if not matching_entities:
        return f"No entities of type '{entity_type}' found in the game environment."

    # Construct response with entity details
    response_parts = [
        f"Found {len(matching_entities)} entities of type '{entity_type}':"]

    for entity in matching_entities:
        entity_id = getattr(entity, 'id', 'unknown_id')
        entity_name = getattr(entity, 'name', f"Unnamed {entity_type}")
        entity_type_value = getattr(entity, 'type', 'unknown_type')

        # Get position information
        position_str = "unknown position"
        position = getattr(entity, 'position', None)

        if position:
            if hasattr(position, 'x') and hasattr(position, 'y'):
                position_str = f"({position.x}, {position.y})"
            elif isinstance(position, (tuple, list)) and len(position) >= 2:
                position_str = f"({position[0]}, {position[1]})"

        response_parts.append(
            f"- {entity_name} (ID: {entity_id}, Type: {entity_type_value}) at {position_str}")

    return "\n".join(response_parts)


@function_tool
@log_tool_execution
async def go_to_entity_type(
    ctx: RunContextWrapper[CompleteStoryResult],
    entity_type: str
) -> str:
    """A combined tool that finds an entity of the specified type and moves the player to it.
    This is a convenience tool that handles both finding and navigating to the entity.

    Args:
        ctx: The RunContext containing the game state.
        entity_type: The type of entity to find and move to (e.g. "log_stool", "campfire", "chest").

    Returns:
        str: Description of the result of the find and move operation.
    """
    logger.info(f"🚶‍♂️ Moving to entity of type: {entity_type}")

    # Safety check for ctx and context
    if ctx is None:
        logger.error("💥 TOOL: Critical error - ctx parameter is None")
        return "Error: Game context is missing. Please try setting the theme again."

    # Get the context object and check if it's valid
    story_result = getattr(ctx, "context", None)
    if story_result is None:
        logger.error("💥 TOOL: Critical error - ctx.context is None")
        return "Error: Game state is not properly initialized. Please try setting the theme again."

    # Check if environment exists
    if not hasattr(
    story_result,
     'environment') or story_result.environment is None:
        logger.error(
            "💥 TOOL: Critical error - story_result.environment is missing or None")
        return "Error: Game environment not found. Please try setting the theme again."

    environment = story_result.environment

    # Helper function to normalize entity types for matching
    def normalize_entity_type(type_str):
        if not type_str:
            return ""
        # Convert to lowercase
        normalized = type_str.lower()
        # Handle special cases
        mapping = {
            "stool": "log_stool",  # Map stool to log_stool
            "log": "log_stool",    # Map log to log_stool
            "fire": "campfire",    # Map fire to campfire
            "pot": "campfire_pot"  # Map pot to campfire_pot
        }
        # Check both the original and for each word in the type
        words = normalized.split('_')
        for word in words:
            if word in mapping:
                return mapping[word]
        # Return the original normalized string if no mapping applies
        return normalized

    # Normalize the search type
    normalized_search_type = normalize_entity_type(entity_type)
    logger.debug(
        f"Normalized search type from '{entity_type}' to '{normalized_search_type}'")

    # IMPROVED: First check nearby_objects for matching entities
    # This prioritizes objects the player can already see
    nearby_matching_entities = []

    if hasattr(story_result, 'nearby_objects') and story_result.nearby_objects:
        logger.info(
            f"Checking {len(story_result.nearby_objects)} nearby objects first")

        for entity_id, entity in story_result.nearby_objects.items():
            entity_type_value = getattr(entity, 'type', None)
            if not entity_type_value:
                continue

            # Normalize the entity's type
            normalized_entity_type = normalize_entity_type(entity_type_value)

            # Check for match with normalized types
            if (normalized_entity_type == normalized_search_type or
                normalized_search_type in normalized_entity_type or
                normalized_entity_type in normalized_search_type or
                entity_type.lower() in entity_type_value.lower() or
                entity_type_value.lower() in entity_type.lower()):
                nearby_matching_entities.append(entity)

        # Also check entity names if type didn't match
        if not nearby_matching_entities:
            for entity_id, entity in story_result.nearby_objects.items():
                entity_name = getattr(entity, 'name', '').lower()
                if entity_name and entity_type.lower() in entity_name:
                    nearby_matching_entities.append(entity)

    # If we found nearby matches, use those first
    if nearby_matching_entities:
        logger.info(
            f"Found {len(nearby_matching_entities)} matching entities in nearby objects")
        matching_entities = nearby_matching_entities
    else:
        # Otherwise fall back to searching all entities in the environment
        logger.info(
            "No matching nearby entities found, searching entire environment")

        # Get all entities from the environment
        all_entities = []

        # First try to get entities from the story_result
        if hasattr(story_result, 'entities') and story_result.entities:
            all_entities.extend(story_result.entities)

        # Then try to get from environment.entity_map if available
        if hasattr(environment, 'entity_map') and environment.entity_map:
            for entity_id, entity in environment.entity_map.items():
                if entity not in all_entities:
                    all_entities.append(entity)

        if not all_entities:
            return f"No entities found in the game environment."

        # Filter all entities by type
        matching_entities = []
        for entity in all_entities:
            entity_type_value = getattr(entity, 'type', None)

            if not entity_type_value:
                continue

            # Normalize the entity's type
            normalized_entity_type = normalize_entity_type(entity_type_value)

            # Check for match with normalized types
            if (normalized_entity_type == normalized_search_type or
                normalized_search_type in normalized_entity_type or
                normalized_entity_type in normalized_search_type or
                entity_type.lower() in entity_type_value.lower() or
                entity_type_value.lower() in entity_type.lower()):
                matching_entities.append(entity)

        if not matching_entities:
            # If no matches with normalization, try matching against entity
            # names too
            for entity in all_entities:
                entity_name = getattr(entity, 'name', '').lower()
                if entity_name and entity_type.lower() in entity_name:
                    matching_entities.append(entity)

    if not matching_entities:
        return f"No entities of type '{entity_type}' found in the game environment."

    # Extract entity details for logging and selection
    entities_found = []
    for entity in matching_entities:
        entity_id = getattr(entity, 'id', 'unknown_id')
        entity_name = getattr(entity, 'name', f"Unnamed {entity_type}")
        entity_type_value = getattr(entity, 'type', 'unknown_type')

        # Get position information
        position = getattr(entity, 'position', None)

        if position:
            if hasattr(position, 'x') and hasattr(position, 'y'):
                x, y = position.x, position.y
                entities_found.append(
    (entity_name, entity_id, entity_type_value, x, y))
            elif isinstance(position, (tuple, list)) and len(position) >= 2:
                x, y = position[0], position[1]
                entities_found.append(
    (entity_name, entity_id, entity_type_value, x, y))

    if not entities_found:
        logger.warning(
            f"⚠️ Found entities of type '{entity_type}' but could not determine their positions")
        return f"Found entities of type '{entity_type}' but could not determine their locations."

    # Get the first entity from the found list
    if len(entities_found) > 1:
        logger.info(
            f"Found multiple entities ({len(entities_found)}), selecting the first one for movement")

    # Get the first entity (in future could select nearest)
    selected_entity_name, selected_entity_id, selected_entity_type, target_x, target_y = entities_found[
        0]

    # Step 3: Move to the entity
    from_nearby = matching_entities == nearby_matching_entities
    nearby_message = "nearby visible" if from_nearby else "found in environment"
    logger.info(
        f"Moving to {nearby_message} {selected_entity_name} ({selected_entity_type}) at ({target_x}, {target_y})")

    # Since we can't call the move_to_object function tool directly, we need to
    # implement the core logic here without trying to call it as a function
    story_result = ctx.context
    person = story_result.person
    environment = story_result.environment

    # Log starting position
    start_pos = "unknown"
    if hasattr(person.position, 'x') and hasattr(person.position, 'y'):
        start_pos = f"({person.position.x}, {person.position.y})"
    elif isinstance(person.position, (tuple, list)) and len(person.position) >= 2:
        start_pos = f"({person.position[0]}, {person.position[1]})"

    # Find adjacent positions to target
    target_pos = (target_x, target_y)
    adjacent_candidates = []
    for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:  # Up, Right, Down, Left
        adj_pos = (target_pos[0] + dx, target_pos[1] + dy)
        if environment.is_valid_position(
            adj_pos) and environment.can_move_to(adj_pos):
            adjacent_candidates.append(adj_pos)

    # If there are no adjacent spots, report that
    if not adjacent_candidates:
        return f"Found {nearby_message} {selected_entity_type} '{selected_entity_name}' at {target_pos}, but there are no free spaces to stand nearby."

    # Find the best adjacent position to move to
    current_pos_tuple = None
    if hasattr(person.position, 'x') and hasattr(person.position, 'y'):
        current_pos_tuple = (person.position.x, person.position.y)
    elif isinstance(person.position, (tuple, list)) and len(person.position) >= 2:
        current_pos_tuple = (person.position[0], person.position[1])
    else:
        return f"Found {selected_entity_type} '{selected_entity_name}' at {target_pos}, but couldn't determine player position."

    # If we're already adjacent, report success
    for adj_pos in adjacent_candidates:
        if adj_pos == current_pos_tuple:
            return f"You're already standing next to the {selected_entity_type} '{selected_entity_name}' at {target_pos}."

    # Find the nearest adjacent position
    best_adj_pos = min(adjacent_candidates,
                       key=lambda pos: abs(pos[0] - current_pos_tuple[0]) + abs(pos[1] - current_pos_tuple[1]))

    # Move to that position - use a simple approach for now
    direction_x = best_adj_pos[0] - current_pos_tuple[0]
    direction_y = best_adj_pos[1] - current_pos_tuple[1]

    # Determine direction based on the largest component
    move_direction = ""
    if abs(direction_x) > abs(direction_y):
        # FIXED: Proper direction mapping for x-axis
        move_direction = "right" if direction_x > 0 else "left"
    else:
        # FIXED: Proper direction mapping for y-axis (up decreases y, down
        # increases y)
        move_direction = "down" if direction_y > 0 else "up"

    # Execute the move
    steps_required = max(abs(direction_x), abs(direction_y))

    # Try to execute the move command using our movement implementation
    try:
        # Use a series of regular moves instead of continuous movement
        # since Person doesn't have a move_continuously method
        result = await _internal_move(ctx,
                                    direction=move_direction,
                                    is_running=False,
                                    continuous=False,  # Use regular step by step movement
                                    steps=steps_required)

        # Check if we successfully moved
        logger.info(f"Move result: {result}")
        if "Successfully" in result or "Moved" in result:
            # FIXED: Send the movement command to the frontend to update visual
            # display
            storyteller = getattr(story_result, '_storyteller_agent', None)
            if storyteller and hasattr(
    storyteller, 'send_command_to_frontend'):
                try:
                    command_params = {
                        "direction": move_direction,
                        "is_running": False,
                        "steps": steps_required,
                        "continuous": False
                    }
                    logger.info(
                        f"🚀 Sending move command to frontend: direction={move_direction}, steps={steps_required}")
                    await storyteller.send_command_to_frontend("move", command_params, result)
                except Exception as e:
                    logger.error(f"❌ Error sending WebSocket command: {e}")

            return f"Moved to {nearby_message} {selected_entity_type} '{selected_entity_name}' at {target_pos}."
        else:
            return f"Found {nearby_message} {selected_entity_type} '{selected_entity_name}' at {target_pos}, but couldn't get there: {result}"
    except Exception as e:
        logger.error(f"❌ Error during movement to {selected_entity_name}: {e}")
        return f"Found {nearby_message} {selected_entity_type} '{selected_entity_name}' at {target_pos}, but encountered an error moving there: {str(e)}"


# --- Agent Class Definition ---
class StorytellerAgentFinal:
    """The final version of the Storyteller agent, handling game state and interaction logic."""

    def __init__(self, complete_story_result: CompleteStoryResult, websocket: WebSocket):
        logger.info("🚀 Initializing StorytellerAgentFinal...")
        self.websocket = websocket
        self.game_context = complete_story_result
        self.voice = os.getenv("CHARACTER_VOICE", DEFAULT_VOICE)
        self.openai_client = None
        self.deepgram_client = None
        self.agent = None

        # Store a reference to self in the game_context for tools to access
        # IMPORTANT: This bidirectional reference is crucial for context persistence
        self.game_context._storyteller_agent = self

        # Store a session reference to ensure tools can access it
        if hasattr(complete_story_result, '_session_data'):
            self.session_data = complete_story_result._session_data
        else:
            self.session_data = {}
            complete_story_result._session_data = self.session_data

        # Log information about the game context
        logger.info(f"🔍 Game context initialized: Person={hasattr(self.game_context, 'person')}, "
                   f"Environment={hasattr(self.game_context, 'environment')}, "
                   f"Theme={getattr(self.game_context, 'theme', 'Unknown')}")

        # Initialize OpenAI client
        try:
            self.openai_client = OpenAI()
            logger.info("✅ Initialized OpenAI client.")
        except Exception as e:
            logger.error(f"❌ Failed to initialize OpenAI client: {e}")
            raise  # Re-raise the exception to prevent agent init without client

        # Initialize Deepgram client
        try:
            if DEEPGRAM_API_KEY:
                self.deepgram_client = DeepgramClient(DEEPGRAM_API_KEY)
                logger.info("✅ Initialized Deepgram client.")
            else:
                logger.warning("⚠️ DEEPGRAM_API_KEY not provided - voice transcription unavailable")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Deepgram client: {e}")
            # Not raising - voice functionality is optional

        # Ensure Person exists in game_context and has a position
        if not hasattr(self.game_context, 'person') or not self.game_context.person:
            logger.warning("🤷 Person not found in loaded story result. Creating default.")
            # Ensure environment exists and has dimensions before creating default person
            if (hasattr(self.game_context, 'environment') and
                    self.game_context.environment and
                    hasattr(self.game_context.environment, 'width') and
                    hasattr(self.game_context.environment, 'height')):
                start_x = self.game_context.environment.width // 2
                start_y = self.game_context.environment.height // 2
                self.game_context.person = Person(id="game-char", name="Player", position=(start_x, start_y))
                logger.info(f"👤 Default person created at ({start_x}, {start_y})")
            else:
                logger.error("❌ Cannot create default person: Environment or dimensions missing.")
                raise ValueError("Environment data missing, cannot create default person.")
        elif not self.game_context.person.position:
            # Ensure person has a position
            if (hasattr(self.game_context, 'environment') and
                self.game_context.environment and
                hasattr(self.game_context.environment, 'width') and
                hasattr(self.game_context.environment, 'height')):
                # Set default position at the center of the map
                start_x = self.game_context.environment.width // 2
                start_y = self.game_context.environment.height // 2
                self.game_context.person.position = (start_x, start_y)
                logger.info(f"👤 Reset person position to ({start_x}, {start_y})")
            else:
                # Set to a reasonable default position
                self.game_context.person.position = (20, 20)
                logger.info("👤 Reset person position to default (20, 20)")

        # Add serialization capabilities to Environment object if needed
        if (hasattr(self.game_context, 'environment') and
            self.game_context.environment and
            not hasattr(self.game_context.environment, 'to_dict')):
            self._add_environment_serialization(self.game_context.environment)

        # Initialize nearby_objects if missing
        if not hasattr(self.game_context, 'nearby_objects') or self.game_context.nearby_objects is None:
            self.game_context.nearby_objects = {}
            logger.info("📦 Initialized empty nearby_objects dictionary")

        # Synchronize state after loading and potentially creating person
        logger.info("🔄 Performing initial state synchronization...")
        sync_success = sync_story_state(self.game_context)
        if sync_success:
            logger.info("✅ Initial state synchronized successfully.")
            # ---> LOG ENV ID <---
            if hasattr(self.game_context, 'environment') and self.game_context.environment:
                 logger.info(f"SYNC CHECK: Environment ID after sync in __init__: {id(self.game_context.environment)}")
            else:
                 logger.warning("SYNC CHECK: Environment missing after sync in __init__")
        else:
            logger.warning("⚠️ Issues during initial state synchronization.")

        # Ensure context reference is strong by assigning back to self
        # This reinforces bidirectional references
        self.game_context = complete_story_result

        # Setup the internal agent instance
        self._setup_agent_internal(self.game_context)
        logger.info("✅ StorytellerAgentFinal initialization complete.")

    def _add_environment_serialization(self, environment):
        """Add serialization methods to Environment object if needed."""
        # Instead of modifying the Environment object directly (which fails for Pydantic models),
        # we'll create a wrapper function that can be used in serialization

        # Define a standalone serialization function that doesn't modify the object
        def serialize_environment(env):
            """Convert Environment object to dictionary for serialization."""
            # If model_dump exists (Pydantic v2+), use it
            if hasattr(env, 'model_dump') and callable(env.model_dump):
                return env.model_dump()

            # If dict exists (Pydantic v1), use it
            if hasattr(env, 'dict') and callable(env.dict):
                return env.dict()

            # Manual conversion as fallback
            result = {}

            # Copy basic attributes
            for attr in ['width', 'height', 'name', 'terrain_type', 'description']:
                if hasattr(env, attr):
                    result[attr] = getattr(env, attr)

            # Handle the grid (terrain map)
            if hasattr(env, 'grid'):
                if callable(getattr(env, 'grid', None)):
                    result['grid'] = env.grid()
                else:
                    result['grid'] = env.grid

            # Map of default states that the frontend can properly render
            supported_states = {
                "campfire": {"default": "unlit", "folded": "unlit", "rolled": "unlit"},
                "chest": {"default": "closed", "folded": "closed", "rolled": "closed"},
                "pot": {"default": "empty", "folded": "empty", "rolled": "empty"},
                "tent": {"default": "setup", "folded": "setup", "rolled": "setup"},
                "bedroll": {"default": "unrolled", "folded": "unrolled", "rolled": "unrolled"},
                "backpack": {"default": "filled", "folded": "filled", "rolled": "filled"},
                "log_stool": {"default": "default", "folded": "default", "rolled": "default"}
            }

            # Handle entity positions
            result['entities'] = []
            if hasattr(env, 'entity_map') and env.entity_map:
                for entity_id, entity in env.entity_map.items():
                    if hasattr(entity, 'position'):
                        pos = entity.position
                        pos_tuple = None
                        if hasattr(pos, 'x') and hasattr(pos, 'y'):
                            pos_tuple = (pos.x, pos.y)
                        elif isinstance(pos, (tuple, list)) and len(pos) >= 2:
                            pos_tuple = tuple(pos[:2])

                        if pos_tuple:
                            # Create a complete entity data dictionary with all necessary properties
                            entity_data = {
                                'id': entity_id,
                                'position': pos_tuple,
                                'type': getattr(entity, 'type', 'unknown')
                            }

                            # Ensure name is present
                            entity_data['name'] = getattr(entity, 'name', f"Unknown {entity_data['type']}")

                            # CRITICAL: Ensure state is never null - set default state based on entity type
                            entity_type = entity_data['type']
                            current_state = getattr(entity, 'state', 'default')

                            if current_state is None or current_state in ['default', 'folded', 'rolled']:
                                # Map to supported states
                                if entity_type in supported_states and current_state in supported_states[entity_type]:
                                    entity_data['state'] = supported_states[entity_type][current_state]
                                elif entity_type == 'campfire':
                                    entity_data['state'] = 'unlit'
                                elif entity_type == 'chest':
                                    entity_data['state'] = 'closed'
                                elif entity_type == 'pot':
                                    entity_data['state'] = 'empty'
                                elif entity_type == 'tent':
                                    entity_data['state'] = 'setup'
                                elif entity_type == 'bedroll':
                                    entity_data['state'] = 'unrolled'
                                elif entity_type == 'firewood':
                                    entity_data['state'] = 'dry'
                                elif entity_type == 'backpack':
                                    entity_data['state'] = 'filled'
                                else:
                                    # Use alternate state name
                                    entity_data['state'] = 'unlit' if entity_type in ['campfire', 'campfire_spit', 'campfire_pot'] else 'closed'
                            else:
                                entity_data['state'] = current_state

                            # Copy other useful attributes
                            for attr in ['description', 'is_jumpable', 'is_movable', 'is_collectable',
                                        'is_container', 'weight', 'possible_actions', 'contents']:
                                if hasattr(entity, attr):
                                    entity_data[attr] = getattr(entity, attr)

                            # Set appropriate variant based on entity type
                            if not hasattr(entity, 'variant') or getattr(entity, 'variant') is None:
                                if entity_type == 'campfire':
                                    entity_data['variant'] = 'medium'
                                elif entity_type == 'chest':
                                    entity_data['variant'] = 'wooden'
                                elif entity_type == 'tent':
                                    entity_data['variant'] = 'medium'
                                elif entity_type == 'log_stool':
                                    entity_data['variant'] = 'medium'
                                elif entity_type == 'bedroll':
                                    entity_data['variant'] = 'basic'
                                else:
                                    entity_data['variant'] = 'default'
                            else:
                                entity_data['variant'] = getattr(entity, 'variant')

                            result['entities'].append(entity_data)

            return result

        # Store the serialization function as a class attribute instead of trying to modify the Environment
        self._environment_serializer = serialize_environment
        logger.info("✅ Created environment serialization function")

    def _setup_agent_internal(self, game_context: CompleteStoryResult):
        """ Sets up the internal OpenAI Agent instance. """
        logger.info("⚙️ Setting up internal OpenAI Agent...")

        # Get mechanics reference first
        mechanics_ref = get_game_mechanics_reference()

        # Get theme from game context
        theme = getattr(game_context, 'theme', "Unknown Theme")
        logger.info(f"Using theme from context: '{theme}'")

        # Safely get quest title, provide default if missing
        quest_title = "Explore and Survive"  # Default title
        if (hasattr(game_context, 'narrative_components') and
                isinstance(game_context.narrative_components, dict) and
                'quest' in game_context.narrative_components and
                isinstance(game_context.narrative_components['quest'], dict) and
                'title' in game_context.narrative_components['quest']):
            quest_title = game_context.narrative_components['quest']['title']
            logger.info(f"Using quest title from context: '{quest_title}'")
        else:
            logger.warning(f"Quest title not found in narrative_components, using default: '{quest_title}'")

        # Call prompt function with the correct parameter names - add theme parameter
        full_system_prompt = get_storyteller_system_prompt(
            theme=theme,
            quest_title=quest_title,
            game_mechanics_reference=mechanics_ref
        )

        # Add specific instructions about response format to ensure Answer objects with options
        format_instructions = """
IMPORTANT TOOL SELECTION GUIDELINES:
1. When user asks to "go to X" or "find X" where X is any object type (stool, log, campfire, etc.):
   - Use go_to_entity_type(entity_type="X") DIRECTLY - this handles both finding and moving
   - DO NOT use hardcoded coordinates - they're often wrong

2. For debugging entity locations only:
   - Use find_entity_by_type(entity_type="X") to just see where things are without moving

3. For direct movement:
   - Use move_to_object only when you have exact coordinates from find_entity_by_type
   - Use move for direction-based movement (up/down/left/right)

4. All object interactions require being adjacent to the object first

Remember to match entity types flexibly - "stool" will match "log_stool", "fire" will match "campfire", etc.
"""

        # Append the format instructions to the full system prompt
        full_system_prompt += "\n\n" + format_instructions

        # Make sure ALL defined tools are passed to the Agent
        # These should be the DECORATED functions/tool objects
        all_tools = [
            move, jump, look_around, get_inventory, get_object_details,
            use_object_with, execute_movement_sequence, move_to_object, find_entity_by_type,
            go_to_entity_type
            # Add any other decorated tools defined elsewhere here
        ]

        # Check if self.openai_client exists before using it
        if not self.openai_client:
            logger.error("❌ OpenAI client not initialized before agent setup!")
            raise ValueError("OpenAI client must be initialized before setting up the agent.")

        # Initialize the agent with the correct parameters
        self.agent = Agent(
            name="Game Storyteller",
            instructions=full_system_prompt,
            tools=all_tools,
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            output_type=AnswerSet
        )
        logger.info(f"✅ Internal Agent setup complete with {len(all_tools)} tools.")

    # --- Reconstructed Methods ---

    async def send_command_to_frontend(self, name: str, params: Dict[str, Any], result: Optional[str]):
        """Sends a command message to the connected WebSocket client."""
        if not self.websocket:
            logger.error("❌ Cannot send command: WebSocket connection not available.")
            return

        if not name or not isinstance(name, str):
            logger.error(f"❌ Invalid command name type: {type(name)}. Command not sent.")
            return
        if not isinstance(params, dict):
            logger.error(f"❌ Invalid command params type: {type(params)}. Command not sent.")
            params = {}  # Default to empty dict to avoid crashing json.dumps

        # Generate a default result string if none is provided
        if result is None:
            param_str = ", ".join(f"{k}={v}" for k, v in params.items())
            result = f"Executing {name}({param_str})"

        cmd_data = {
            "type": "command",
            "name": name,
            "params": params,
            "result": result,  # Include the result message
            "sender": "system"
        }

        try:
            # Custom JSON serialization function
            def serialize_for_json(obj):
                # Use our environment serializer for Environment objects
                if hasattr(self, '_environment_serializer') and 'Environment' in obj.__class__.__name__:
                    return self._environment_serializer(obj)

                # Standard Pydantic model handling
                if hasattr(obj, 'model_dump') and callable(obj.model_dump):
                    return obj.model_dump()
                elif hasattr(obj, 'dict') and callable(obj.dict):
                    return obj.dict()
                elif hasattr(obj, '__dict__'):
                    return obj.__dict__
                else:
                    return str(obj)

            # Serialize with custom encoder
            serialized_cmd = json.dumps(cmd_data, default=serialize_for_json)

            logger.info(f"🎮 Sending command to frontend: {name}, Params: {params}")
            await self.websocket.send_text(serialized_cmd)
            logger.debug(f"✅ Command '{name}' sent successfully.")
        except Exception as e:
            logger.error(f"❌ WebSocket error sending command '{name}': {e}")
            # Attempt to close the connection gracefully if send fails?
            # Or just log the error. For now, just log.

    async def process_text_input(self, text: str, conversation_history: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Processes text input using the internal agent."""
        logger.info(f"Processing text input: '{text}'")
        if not self.agent:
            logger.error("❌ Agent not initialized. Cannot process text.")
            return {"type": "error", "content": "Agent not ready."}, conversation_history

        # Append user message to history
        conversation_history.append({"role": "user", "content": text})

        try:
            # Make sure the agent has the current game context
            # This ensures that even if context gets lost, it's reattached before processing
            if not hasattr(self, 'game_context') or self.game_context is None:
                logger.error("❌ Game context is missing during text processing")
                return {"type": "error", "content": "Game state lost, please try setting the theme again."}, conversation_history

            # ---> LOG ENV ID <---
            if hasattr(self.game_context, 'environment') and self.game_context.environment:
                 logger.info(f"SYNC CHECK: Environment ID in process_text_input before run: {id(self.game_context.environment)}")
            else:
                 logger.warning("SYNC CHECK: Environment missing in process_text_input before run")

            # Create a Runner instance for the agent
            runner = Runner()
            runner.agent = self.agent

            # CRITICAL: Properly set the context object for the agent runner
            # This ensures tools can access ctx.context
            runner.context = self.game_context

            # Set a reference to the storyteller agent in the context for tool access
            self.game_context._storyteller_agent = self

            # Log context data to verify it's properly set
            logger.info(f"✅ Context set for agent: Person={getattr(self.game_context, 'person', None) is not None}, Environment={getattr(self.game_context, 'environment', None) is not None}")

            # Run the agent using the runner with explicit context
            response = await runner.run(starting_agent=self.agent, input=text, context=self.game_context)

            final_response_data = None

            # --- Handle Tool Calls (if any) ---
            if hasattr(response, 'tool_calls') and response.tool_calls:
                logger.info("🛠️ Agent response included tool calls")
                first_tool_call = response.tool_calls[0]
                tool_name = first_tool_call.function.name
                tool_args = json.loads(first_tool_call.function.arguments)
                final_response_data = {"type": "command", "name": tool_name, "params": tool_args}

            # --- Handle Direct Content Response ---
            elif hasattr(response, 'final_output'):
                assistant_response_content = response.final_output

                # Check if response is already an AnswerSet object (with output_type=AnswerSet)
                if isinstance(assistant_response_content, AnswerSet):
                    logger.info("✅ Received direct AnswerSet object from agent")
                    # Use the object directly without conversion
                    final_response_data = {
                        "type": "json",
                        "content": assistant_response_content.model_dump()
                    }
                    # Add to conversation history as string representation
                    conversation_history.append({"role": "assistant", "content": str(assistant_response_content.model_dump())})

                # Check if the response is JSON (likely an AnswerSet)
                elif isinstance(assistant_response_content, str):
                    if assistant_response_content.strip().startswith('{'):
                        try:
                            # Validate it's our expected AnswerSet format (or similar)
                            json_content = json.loads(assistant_response_content)

                            # Check if it's already in the AnswerSet format
                            if "answers" in json_content and isinstance(json_content["answers"], list):
                                final_response_data = {"type": "json", "content": assistant_response_content}
                                # Convert to AnswerSet format
                                logger.info("⚠️ Response is JSON but not in AnswerSet format, converting...")
                                answer_set = self._format_as_answer_set(assistant_response_content)
                                final_response_data = {"type": "json", "content": answer_set}
                        except json.JSONDecodeError:
                            logger.warning(f"Assistant response looked like JSON but failed to parse: {assistant_response_content[:100]}...")
                            # Convert plain text to AnswerSet format
                            answer_set = self._format_as_answer_set(assistant_response_content)
                            final_response_data = {"type": "json", "content": answer_set}
                    else:
                        # Handle plain text response - convert to AnswerSet format
                        logger.info("Converting plain text response to AnswerSet format")
                        answer_set = self._format_as_answer_set(assistant_response_content)
                        final_response_data = {"type": "json", "content": answer_set}

                    # Append assistant response to history (original string format)
                    conversation_history.append({"role": "assistant", "content": str(assistant_response_content)})
                else:
                    # Handle other response types
                    logger.warning(f"Unexpected response type: {type(assistant_response_content)}")
                    answer_set = self._format_as_answer_set(str(assistant_response_content))
                    final_response_data = {"type": "json", "content": answer_set}

                    # Append assistant response to history (stringified)
                    conversation_history.append({"role": "assistant", "content": str(assistant_response_content)})

            else:
                logger.error(f"❌ Unexpected agent response structure: {response}")
                final_response_data = {"type": "error", "content": "Received unexpected response from agent."}

            return final_response_data, conversation_history

        except Exception as e:
            logger.error(f"❌ Error during agent text processing: {e}", exc_info=True)
            return {"type": "error", "content": f"Error processing input: {e}"}, conversation_history

    def _format_as_answer_set(self, text: str) -> str:
        """Format a text response as an AnswerSet JSON with options.

        Args:
            text: The text to format

        Returns:
            str: JSON string in the AnswerSet format
        """
        try:
            # Generate 2-4 relevant options based on the text
            sentences = [s.strip() for s in text.split('.') if s.strip()]

            # Extract key words for options
            import re
            words = re.findall(r'\b\w+\b', text.lower())
            action_words = [w for w in words if len(w) > 3 and w not in
                           {'this', 'that', 'with', 'from', 'have', 'what', 'when', 'where',
                            'there', 'their', 'about', 'would', 'could', 'should'}]

            # Create options based on text content
            options = []

            # Add movement options if relevant
            if any(word in words for word in ['move', 'walk', 'go', 'turn', 'north', 'south', 'east', 'west',
                                             'left', 'right', 'up', 'down', 'forward', 'backward']):
                options.append("Look around")

            # Add look option if relevant
            if any(word in words for word in ['see', 'look', 'observe', 'watch', 'view']):
                options.append("Look closer")

            # Add inventory option if relevant
            if any(word in words for word in ['inventory', 'item', 'carry', 'holding', 'have']):
                options.append("Check inventory")

            # Add interaction options
            if len(action_words) >= 3:
                # Use some action words to create options
                action_words = list(set(action_words))  # Remove duplicates
                import random
                random.shuffle(action_words)

                # Create action phrases
                if len(options) < 3 and len(action_words) >= 2:
                    options.append(f"{action_words[0].capitalize()} {action_words[1]}")

                if len(options) < 4 and len(action_words) >= 4:
                    options.append(f"{action_words[2].capitalize()} {action_words[3]}")

            # Always include a question option
            if "?" not in text and len(options) < 4:
                options.append("Ask questions")

            # If we still need options, add generic ones
            generic_options = ["Explore more", "Try something else", "What next?", "Continue"]
            while len(options) < 2:
                if generic_options:
                    options.append(generic_options.pop(0))
                else:
                    break

            # Limit options to 4
            options = options[:4]

            # Create the answer object
            answer = {
                "type": "text",
                "description": text[:400],  # Limit to 400 chars
                "options": options
            }

            # Create the answer set
            answer_set = {
                "answers": [answer]
            }

            return json.dumps(answer_set)
        except Exception as e:
            logger.error(f"❌ Error formatting answer set: {e}")
            # Fallback
            fallback_answer = {
                "answers": [{
                    "type": "text",
                    "description": text[:400] if text else "No response",
                    "options": ["What next?", "Explore more"]
                }]
            }
            return json.dumps(fallback_answer)

    async def process_audio(self, audio_data: bytes, on_transcription: Callable[[str], Awaitable[None]],
                            on_response: Callable[[str], Awaitable[None]], on_audio: Callable[[bytes], Awaitable[None]],
                            conversation_history: List[Dict[str, Any]]) -> Tuple[
        str, Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """Processes audio input: Transcribe -> Process Text -> Generate TTS."""
        logger.info(f"Processing audio data: {len(audio_data)} bytes")
        if not self.agent or not self.deepgram_client or not self.openai_client:
            logger.error("❌ Agent or required clients not initialized. Cannot process audio.")
            await on_response(json.dumps({"type": "error", "content": "Audio processing components not ready."}))
            return "", None, conversation_history

        transcribed_text = ""
        command_info = None

        try:
            # 1. Transcribe using Deepgram
            source = {'buffer': audio_data, 'mimetype': 'audio/webm'}  # Adjust mimetype if needed
            options = PrerecordedOptions(model="nova-2", smart_format=True)
            dg_response = await self.deepgram_client.listen.prerecorded.v("1").transcribe_file(source, options)
            transcribed_text = dg_response.results.channels[0].alternatives[0].transcript
            logger.info(f"🎤 Transcription: '{transcribed_text}'")
            await on_transcription(transcribed_text)  # Send transcription back to client

            if not transcribed_text.strip():
                logger.warning("⚠️ Transcription resulted in empty text.")
                # Send a message indicating silence or no speech?
                # For now, just return early.
                return "", None, conversation_history

            # 2. Process the transcribed text using the agent (similar to process_text_input)
            response_data, conversation_history = await self.process_text_input(transcribed_text, conversation_history)
            logger.debug(f"Agent response data after audio transcription: {response_data}")

            # 3. Handle Agent Response (JSON for TTS, Command, or Error)
            response_type = response_data.get("type")
            response_content = response_data.get("content")

            if response_type == "json":
                await on_response(response_content)  # Send the JSON response
                try:
                    # Extract text for TTS from JSON (assuming AnswerSet structure)
                    tts_text = ""
                    # Check if response_content is a dict or a JSON string
                    if isinstance(response_content, dict):
                        json_content = response_content
                    else:
                        json_content = json.loads(response_content)

                    answers = json_content.get("answers", [])
                    tts_text = " ".join([ans.get("description", "") for ans in answers if isinstance(ans, dict)])

                    if tts_text.strip():
                        logger.info(f"🔊 Generating TTS for: '{tts_text[:50]}...'")
                        # Generate TTS using OpenAI
                        speech_response = self.openai_client.audio.speech.create(
                            model="tts-1",
                            voice=self.voice,
                            input=tts_text,
                            response_format="mp3"
                        )

                        # Stream audio chunks (handle bytes content)
                        session_data = {"audio_sent_metadata": False}

                        # Send audio_start metadata if needed
                        if not session_data["audio_sent_metadata"]:
                            await on_response(json.dumps({
                                "type": "audio_start",
                                "format": "mp3",
                                "timestamp": time.time()
                            }))
                            session_data["audio_sent_metadata"] = True
                            await asyncio.sleep(0.2)  # Small delay after metadata

                        # Handle content as a bytes object
                        content_bytes = speech_response.content
                        chunk_size = 4096

                        # Send in chunks
                        for i in range(0, len(content_bytes), chunk_size):
                            chunk = content_bytes[i:i+chunk_size]
                            if chunk:
                                await on_audio(chunk)
                                await asyncio.sleep(0.02)  # Small delay between chunks

                        # Signal end of audio
                            await on_audio(b"__AUDIO_END__")
                    else:
                        logger.warning("⚠️ No text found in JSON response for TTS.")
                except json.JSONDecodeError:
                    logger.error(f"❌ Failed to decode JSON response for TTS: {response_content[:100]}...")
                except Exception as e:
                    logger.error(f"❌ Error during TTS generation/streaming: {e}", exc_info=True)

            elif response_type == "command":
                command_info = {"name": response_data.get("name"), "params": response_data.get("params")}
                logger.info(f"🎮 Agent returned command: {command_info}")
                # Command will be sent by main.py after this function returns

            elif response_type == "text":  # Handle plain text response from agent if it occurs
                # Convert to AnswerSet format with options
                answer_set = self._format_as_answer_set(response_content)
                await on_response(answer_set)
                # Generate TTS for the text
                logger.info(f"🔊 Generating TTS for plain text: '{response_content[:50]}...'")
                try:
                    speech_response = self.openai_client.audio.speech.create(
                        model="tts-1",
                        voice=self.voice,
                        input=response_content,
                        response_format="mp3"
                    )

                    # Stream audio chunks (handle bytes content)
                    session_data = {"audio_sent_metadata": False}

                    # Send audio_start metadata if needed
                    if not session_data["audio_sent_metadata"]:
                        await on_response(json.dumps({
                            "type": "audio_start",
                            "format": "mp3",
                            "timestamp": time.time()
                        }))
                        session_data["audio_sent_metadata"] = True
                        await asyncio.sleep(0.2)  # Small delay after metadata

                    # Handle content as a bytes object
                    content_bytes = speech_response.content
                    chunk_size = 4096

                    # Send in chunks
                    for i in range(0, len(content_bytes), chunk_size):
                        chunk = content_bytes[i:i+chunk_size]
                        if chunk:
                            await on_audio(chunk)
                            await asyncio.sleep(0.02)  # Small delay between chunks

                    # Signal end of audio
                    await on_audio(b"__AUDIO_END__")
                except Exception as e:
                    logger.error(f"❌ Error during plain text TTS generation: {e}", exc_info=True)

            elif response_type == "error":
                await on_response(json.dumps(response_data))  # Forward error to client

            else:
                logger.warning(f"⚠️ Unhandled agent response type in process_audio: {response_type}")

        except Exception as e:
            logger.error(f"❌ Error during audio processing pipeline: {e}", exc_info=True)
            error_msg = {"type": "error", "content": f"Error processing audio: {e}", "sender": "system"}
            try:
                await on_response(json.dumps(error_msg))
            except Exception as send_err:
                logger.error(f"❌ Failed to send error message to client: {send_err}")

        return transcribed_text, command_info, conversation_history


# --- End Reconstructed Methods ---

async def example_run():
    """Example test function."""
    pass


if __name__ == "__main__":
    pass
