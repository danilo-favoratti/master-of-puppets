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

# --- Helper Code Copied from agent_puppet_master.py ---

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
    def get_relative_position(current_pos: Tuple[int, int], direction: str) -> Tuple[int, int]:
        x, y = current_pos
        direction = direction.lower()
        if direction == "left": return (x - 1, y)
        if direction == "right": return (x + 1, y)
        # Invert Y-axis movement to match frontend coordinate system
        if direction == "up": return (x, y + 1)
        if direction == "down": return (x, y - 1)
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
        # Invert Y-axis direction naming to match frontend coordinate system
        if dx == 0 and dy == -1: return "up"    # Changed from dy==-1 to dy==-1 (no change, already correct)
        if dx == 0 and dy == 1: return "down"   # Changed from dy==1 to dy==1 (no change, already correct)
        return "unknown"

    @staticmethod
    async def move_continuously(story_result: CompleteStoryResult, direction: str) -> str:
        logger.info(f"🔄 Starting continuous movement: {direction} from {story_result.person.position}")
        moves = 0
        max_moves = 50
        
        storyteller = getattr(story_result, '_storyteller_agent', None)
        can_send_websocket = storyteller and hasattr(storyteller, 'send_command_to_frontend')
        
        final_message = ""

        while moves < max_moves:
            current_pos = story_result.person.position
            # Ensure current_pos is a tuple for DirectionHelper
            current_pos_tuple = None
            if hasattr(current_pos, 'x') and hasattr(current_pos, 'y'):
                current_pos_tuple = (current_pos.x, current_pos.y)
            elif isinstance(current_pos, (tuple, list)) and len(current_pos) >= 2:
                current_pos_tuple = (current_pos[0], current_pos[1])
            else:
                logger.error(f"❌ Invalid current_pos format in move_continuously: {current_pos}")
                final_message = "Error: Could not determine starting position."
                break # Exit loop on error
                
            target_pos_tuple = DirectionHelper.get_relative_position(current_pos_tuple, direction)
            logger.debug(f"  Continuous move attempt #{moves + 1}: {current_pos_tuple} -> {target_pos_tuple}")
            
            # Pass tuple to person.move if it expects it, otherwise pass original object if needed
            # Assuming person.move internally handles tuple or object position based on its implementation
            result = story_result.person.move(story_result.environment, target_pos_tuple, False)
            
            if not result["success"]:
                logger.info(f"🛑 Continuous movement stopped: {result['message']}")
                stop_reason = f"stopped: {result['message']}"
                final_message = f"Moved {moves} steps {direction} and {stop_reason}"
                break # Exit loop
                
            # sync_story_state(story_result) # Syncing after every step might be slow, sync at end?
            moves += 1
            
            # --- REMOVED: Don't send move_step for each step --- 
            # if can_send_websocket:
            #     try:
            #         command_params = {"direction": direction, "is_running": False, "continuous": False}
            #         await storyteller.send_command_to_frontend("move_step", command_params, None)
            #         await asyncio.sleep(0.1)
            #     except Exception as e:
            #         logger.error(f"❌ CONTINUOUS: Error sending WebSocket command: {e}")
            # --------
            
            # Check for edge or next obstacle *before* next loop
            next_pos_check_tuple = DirectionHelper.get_relative_position(story_result.person.position, direction)
            if not story_result.environment.is_valid_position(next_pos_check_tuple):
                logger.info(f"🌍 Reached board edge at {story_result.person.position}")
                final_message = f"Moved {moves} steps {direction} and reached the edge."
                break # Exit loop
            elif not story_result.environment.can_move_to(next_pos_check_tuple):
                 obstacle = story_result.environment.get_object_at(next_pos_check_tuple)
                 obstacle_name = obstacle.name if obstacle else "an obstacle"
                 logger.info(f"🚧 Reached {obstacle_name} at {next_pos_check_tuple}")
                 final_message = f"Moved {moves} steps {direction} and reached {obstacle_name}."
                 break # Exit loop
                 
        if not final_message: # If loop finished due to max_moves
            logger.warning(f"⚠️ Hit move limit ({max_moves}) moving {direction}")
            final_message = f"Moved {moves} steps {direction} and stopped (max distance)."

        # Sync state once at the end of the movement sequence
        sync_story_state(story_result)
        
        # --- ADDED: Send ONE move command if steps were taken --- 
        if moves > 0 and can_send_websocket:
            try:
                command_params = {
                    "direction": direction,
                    "steps": moves, # Add the number of steps
                    "is_running": False
                    # No need for "continuous" flag in frontend command anymore
                }
                logger.info(f"🚀 Sending final multi-step move command to frontend: direction={direction}, steps={moves}")
                # Send command as 'move' type, let frontend handle multi-step animation
                await storyteller.send_command_to_frontend("move", command_params, None) # Result sent separately by agent
            except Exception as e:
                logger.error(f"❌ Error sending final multi-step WebSocket command: {e}")
        # --------
                 
        return final_message

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

# --- Pathfinding Helper Code (Copied and Adapted from agent_path_researcher.py) ---

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
        # Prioritize lower f cost, then lower h cost as tie-breaker
        if self.f != other.f:
            return self.f < other.f
        return self.h < other.h

    def __hash__(self):
        return hash(self.position)

class PathFinder:
    """Class implementing A* path-finding algorithm with jump support for Storyteller context."""

    @staticmethod
    def manhattan_distance(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> int:
        """Calculate Manhattan distance between two positions."""
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    @staticmethod
    def get_neighbors(position: Tuple[int, int], environment: Environment) -> List[Tuple[int, int]]:
        """Get valid, movable neighboring positions (cardinal directions only).
        
        Uses coordinate system where:
        - (0, -1): Up (decrease Y)
        - (1, 0): Right (increase X)
        - (0, 1): Down (increase Y)
        - (-1, 0): Left (decrease X)
        """
        x, y = position
        neighbors = []
        # Order: Up, Right, Down, Left
        for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
            new_pos = (x + dx, y + dy)
            # Use environment methods for validation
            if environment.is_valid_position(new_pos) and environment.can_move_to(new_pos):
                neighbors.append(new_pos)
        return neighbors

    @staticmethod
    def get_jump_neighbors(position: Tuple[int, int], environment: Environment) -> List[Tuple[int, int]]:
        """Get positions reachable by jumping from the current position.
        
        Uses coordinate system where:
        - (0, -1): Up (decrease Y) 
        - (1, 0): Right (increase X)
        - (0, 1): Down (increase Y)
        - (-1, 0): Left (decrease X)
        """
        x, y = position
        jump_neighbors = []
        # Order: Up, Right, Down, Left
        for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
            middle_pos = (x + dx, y + dy)
            landing_pos = (x + 2*dx, y + 2*dy)

            if environment.is_valid_position(middle_pos) and environment.is_valid_position(landing_pos):
                middle_obj = environment.get_object_at(middle_pos)
                # Check if middle object exists, is jumpable, and landing spot is clear
                if middle_obj and getattr(middle_obj, 'is_jumpable', False) and environment.can_move_to(landing_pos):
                    jump_neighbors.append(landing_pos)
        return jump_neighbors

    @staticmethod
    def find_path(environment: Environment, start_pos: Tuple[int, int], end_pos: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Find the shortest path using A*.

        Returns:
            List of positions (tuples) from start to end, or empty list if no path.
        """
        logger.debug(f"PATHFINDER: Finding path from {start_pos} to {end_pos}")
        if not environment.is_valid_position(start_pos) or not environment.is_valid_position(end_pos):
            logger.warning("PATHFINDER: Start or end position invalid.")
            return []
        # Optimization: If start and end are the same
        if start_pos == end_pos:
             return [start_pos]

        start_node = PathNode(start_pos)
        end_node = PathNode(end_pos)

        open_list = [] # Priority queue (min-heap)
        closed_set = set() # Set of visited positions

        heapq.heappush(open_list, start_node)

        while open_list:
            current_node = heapq.heappop(open_list)

            if current_node.position in closed_set:
                continue # Already processed this position via a better path
            closed_set.add(current_node.position)

            # Goal check
            if current_node.position == end_node.position:
                path = []
                temp = current_node
                while temp:
                    path.append(temp.position)
                    temp = temp.parent
                logger.debug(f"PATHFINDER: Path found with {len(path)-1} steps.")
                return path[::-1] # Return reversed path

            # Explore neighbors (Move + Jump)
            neighbors_pos = PathFinder.get_neighbors(current_node.position, environment)
            jump_neighbors_pos = PathFinder.get_jump_neighbors(current_node.position, environment)

            for neighbor_pos in neighbors_pos + jump_neighbors_pos:
                if neighbor_pos in closed_set:
                    continue

                # Determine cost (g value)
                move_cost = 5 if neighbor_pos in jump_neighbors_pos else 1 # Jump costs 5, move costs 1
                new_g = current_node.g + move_cost

                # Check if neighbor is already in open_list and if this path is better
                existing_node = next((node for node in open_list if node.position == neighbor_pos), None)

                if existing_node and new_g >= existing_node.g:
                    continue # Found a better or equal path already

                # Create or update neighbor node
                neighbor_node = PathNode(neighbor_pos, current_node)
                neighbor_node.g = new_g
                neighbor_node.h = PathFinder.manhattan_distance(neighbor_pos, end_pos)
                neighbor_node.f = neighbor_node.g + neighbor_node.h

                # Add to open list (or update priority if already exists)
                # heapq handles priority updates implicitly if node is re-inserted
                heapq.heappush(open_list, neighbor_node)

        logger.warning("PATHFINDER: No path found.")
        return [] # No path found

# --- END Pathfinding Helper Code ---


# --- Tool Definitions Copied from agent_puppet_master.py --- 

# NOTE: These tools now operate directly on the ctx.context (CompleteStoryResult)
# They need access to story_result.person, story_result.environment, etc.

# --- ADDED NEW TOOL: moveToObject ---
@function_tool
async def move_to_object(ctx: RunContextWrapper[CompleteStoryResult], target_x: int, target_y: int) -> str:
    """Moves the player character to a valid, empty space adjacent to the target coordinates.
    This is useful for approaching objects or locations without needing to land exactly on them.
    The tool calculates the path and executes the necessary move/jump steps.

    Args:
        ctx: The RunContext containing the game state.
        target_x: The X coordinate of the target object/location.
        target_y: The Y coordinate of the target object/location.

    Returns:
        str: Description of the movement result (success, failure, path taken) or an error message.
    """
    tool_name = "moveToObject"
    logger.info(f"🛠️ TOOL ENTRY: {tool_name}(target_x={target_x}, target_y={target_y})")
    try:
        story_result = ctx.context
        if not story_result.person:
            logger.error(f"💥 TOOL {tool_name}: Player character not found.")
            return "❌ Error: Player character not found."
        if not story_result.environment:
            logger.error(f"💥 TOOL {tool_name}: Game environment not found.")
            return "❌ Error: Game environment not found."

        person = story_result.person
        environment = story_result.environment

        # --- Get and Validate Player Position ---
        current_pos_tuple = None
        if person.position:
            if hasattr(person.position, 'x') and hasattr(person.position, 'y'):
                 current_pos_tuple = (person.position.x, person.position.y)
            elif isinstance(person.position, (tuple, list)) and len(person.position) >= 2:
                 current_pos_tuple = (person.position[0], person.position[1])

        if not current_pos_tuple or not environment.is_valid_position(current_pos_tuple):
            logger.error(f"💥 TOOL {tool_name}: Invalid or missing player start position: {person.position}")
            sync_story_state(story_result) # Attempt to sync state to fix position
            # Re-check position after sync
            if person.position and isinstance(person.position, (tuple, list)) and len(person.position) >= 2:
                current_pos_tuple = (person.position[0], person.position[1])
                if not environment.is_valid_position(current_pos_tuple):
                    logger.error(f"💥 TOOL {tool_name}: Player position still invalid after sync.")
                    return "Error: Cannot determine player's valid starting position even after sync."
            else:
                logger.error(f"💥 TOOL {tool_name}: Could not determine player position after sync.")
                return "Error: Cannot determine player's starting position."

        target_pos = (target_x, target_y)
        logger.info(f"  {tool_name}: Player at {current_pos_tuple}, Target location {target_pos}")

        # If already adjacent, no need to move
        if PathFinder.manhattan_distance(current_pos_tuple, target_pos) == 1 and environment.can_move_to(current_pos_tuple):
            logger.info(f"  {tool_name}: Player is already adjacent to the target location.")
            return f"You are already standing next to the location ({target_x},{target_y})."

        # --- Find Valid, Empty Adjacent Target Positions ---
        adjacent_candidates = []
        for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]: # Up, Right, Down, Left
            adj_pos = (target_pos[0] + dx, target_pos[1] + dy)
            if environment.is_valid_position(adj_pos) and environment.can_move_to(adj_pos):
                adjacent_candidates.append(adj_pos)

        if not adjacent_candidates:
            logger.warning(f"  {tool_name}: No valid, empty adjacent spaces found around target {target_pos}")
            obj_at_target = environment.get_object_at(target_pos)
            obj_name = getattr(obj_at_target, 'name', 'the target location') if obj_at_target else 'the target location'
            return f"There are no free spaces to stand next to {obj_name} at ({target_x},{target_y})."

        logger.info(f"  {tool_name}: Found {len(adjacent_candidates)} potential adjacent spots: {adjacent_candidates}")

        # --- Select Best Adjacent Spot (Closest to Player) ---
        best_destination = None
        min_dist = float('inf')
        for dest_pos in adjacent_candidates:
            dist = PathFinder.manhattan_distance(current_pos_tuple, dest_pos)
            if dist < min_dist:
                min_dist = dist
                best_destination = dest_pos

        if not best_destination:
             logger.error(f"💥 TOOL {tool_name}: Failed to select a best destination despite having candidates.")
             return "Error: Could not determine the best adjacent spot to move to."

        logger.info(f"  {tool_name}: Selected best adjacent destination: {best_destination} (Distance: {min_dist})")

        # --- Find Path to Best Adjacent Spot ---
        logger.info(f"  {tool_name}: Finding path from {current_pos_tuple} to {best_destination}")
        path = PathFinder.find_path(environment, current_pos_tuple, best_destination)

        if not path or len(path) < 2: # Need at least start and end points
            logger.warning(f"  {tool_name}: No path found from {current_pos_tuple} to {best_destination}")
            return f"Cannot find a path to reach the space next to ({target_x},{target_y})."

        logger.info(f"  {tool_name}: Path found with {len(path) - 1} steps: {path}")

        # --- Generate Movement Commands from Path ---
        movement_commands = []
        results_log = [f"Starting path towards ({target_x},{target_y})..."]
        for i in range(len(path) - 1):
            start_step = path[i]
            end_step = path[i+1]
            dx = end_step[0] - start_step[0]
            dy = end_step[1] - start_step[1]

            tool_name_step = None
            params_step = {}

            if abs(dx) + abs(dy) == 1: # Cardinal move
                tool_name_step = "move"
                if dx == 1: direction = "right"
                elif dx == -1: direction = "left"
                elif dy == 1: direction = "down" # Frontend +Y is Down
                else: direction = "up"           # Frontend -Y is Up
                params_step = {"direction": direction, "is_running": False, "continuous": False}
            elif abs(dx) + abs(dy) == 2: # Jump move
                tool_name_step = "jump"
                params_step = {"target_x": end_step[0], "target_y": end_step[1]}
            else:
                logger.error(f"💥 TOOL {tool_name}: Invalid step in path: {start_step} -> {end_step}. Stopping.")
                results_log.append(f"Step {i+1}: Invalid movement detected, stopping.")
                break # Stop if path contains invalid step

            movement_commands.append({"tool": tool_name_step, "parameters": params_step})

        # --- Execute Movement Commands Sequentially ---
        logger.info(f"  {tool_name}: Executing {len(movement_commands)} movement commands...")
        final_outcome = f"Failed to reach the destination near ({target_x},{target_y})."
        movement_successful = False

        for i, cmd in enumerate(movement_commands):
            tool_name_step = cmd['tool']
            params_step = cmd['parameters']
            logger.info(f"    {tool_name}: Executing Step {i+1}/{len(movement_commands)}: {tool_name_step} with {params_step}")
            step_result = ""
            success = False
            try:
                if tool_name_step == 'move':
                    step_result = await move(ctx, **params_step)
                    # More robust check for success
                    if "Successfully" in step_result or "already there" in step_result.lower():
                        success = True
                elif tool_name_step == 'jump':
                    step_result = await jump(ctx, **params_step)
                    if "Successfully jumped" in step_result or "jumped" in step_result.lower():
                        success = True

                results_log.append(f"Step {i+1} ({tool_name_step}): {step_result}")
                if not success:
                    logger.warning(f"  {tool_name}: Movement failed at step {i+1}: {step_result}")
                    final_outcome = f"Stopped moving towards ({target_x},{target_y}) after step {i+1}: {step_result}"
                    break # Stop sequence on failure
                else:
                    # If this is the last command and it succeeded
                    if i == len(movement_commands) - 1:
                        movement_successful = True
                        # Ensure position is updated in the message
                        final_player_pos = story_result.person.position
                        final_outcome = f"Successfully moved next to the location ({target_x},{target_y}). Now at {final_player_pos}."
                        logger.info(f"  {tool_name}: Reached final step successfully. Final position: {final_player_pos}")

            except Exception as e_step:
                logger.error(f"💥 TOOL {tool_name}: Error executing step {i+1} ({tool_name_step}): {e_step}", exc_info=True)
                results_log.append(f"Step {i+1} ({tool_name_step}): Error - {e_step}")
                final_outcome = f"An error occurred during movement towards ({target_x},{target_y})."
                break

        logger.info(f"🏁 TOOL EXIT: {tool_name} finished. Outcome: {final_outcome}")
        # Optionally return detailed log: return "\n".join(results_log)
        return final_outcome

    except Exception as e:
        logger.error(f"💥 TOOL {tool_name}: Unexpected error: {e}", exc_info=True)
        return f"❌ Error in {tool_name}: {e}"

# --- END ADDED TOOL ---

@function_tool
async def move(ctx: RunContextWrapper[CompleteStoryResult], direction: str, is_running: bool, continuous: bool) -> str:
    """Move the player character one step in a given cardinal direction (up, down, left, right).
    Diagonal movement is not supported.

    Args:
        ctx: The RunContext containing the game state.
        direction: Cardinal direction to move (up, down, left, right, or north, south, east, west).
        is_running: Whether to run (move faster) or walk. Not applicable for continuous movement.
        continuous: Whether to keep moving in the specified cardinal direction until hitting an obstacle or edge.

    Returns:
        str: Description of the movement result or an error message.
    """
    tool_name = "move"
    # Normalize direction early
    direction_norm = direction.lower()
    if direction_norm == "north": direction_norm = "up"
    elif direction_norm == "south": direction_norm = "down"
    elif direction_norm == "east": direction_norm = "right"
    elif direction_norm == "west": direction_norm = "left"

    logger.info(f"🛠️ TOOL ENTRY: {tool_name}(direction='{direction_norm}', is_running={is_running}, continuous={continuous})")
    try:
        # Validate normalized direction
        allowed_directions = ["up", "down", "left", "right"]
        if direction_norm not in allowed_directions:
            logger.warning(f"🚫 TOOL {tool_name}: Invalid move direction received: '{direction}'. Allowed: {allowed_directions}")
            return f"Cannot move '{direction}'. Movement is only possible in cardinal directions (up, down, left, right)."

        story_result = ctx.context
        person = story_result.person
        environment = story_result.environment

        if person.position is None:
            default_pos = (environment.width // 2, environment.height // 2) if environment else (20, 20)
            person.position = default_pos
            logger.warning(f"TOOL {tool_name}: Player position was None, set to default: {person.position}")
        if person.position is None:
             logger.error(f"💥 TOOL {tool_name}: Critical error - Player position is still None after default.")
             return "Error: Cannot determine player's starting position."

        # Ensure position is usable tuple
        current_pos_tuple = None
        if hasattr(person.position, 'x') and hasattr(person.position, 'y'):
             current_pos_tuple = (person.position.x, person.position.y)
        elif isinstance(person.position, (tuple, list)) and len(person.position) >= 2:
             current_pos_tuple = (person.position[0], person.position[1])
        else:
            logger.error(f"💥 TOOL {tool_name}: Invalid current_pos format: {person.position}")
            return "Error: Could not determine valid starting coordinates."

        orig_pos = current_pos_tuple
        logger.info(f"  {tool_name}: Player at {orig_pos}. Trying to move {direction_norm}{' continuously' if continuous else ''}.")

        # Handle continuous movement
        if continuous:
            logger.info(f"  {tool_name}: Handing off to continuous movement helper.")
            # Pass the validated tuple position
            result_msg = await DirectionHelper.move_continuously(story_result, direction_norm)
            logger.info(f"🏁 TOOL EXIT: {tool_name} (continuous) finished. Result: {result_msg}")
            return result_msg

        # Single step movement
        target_pos_tuple = DirectionHelper.get_relative_position(orig_pos, direction_norm)
        logger.info(f"  {tool_name}: Target position for single step: {target_pos_tuple}")

        # Attempt the move in the backend
        result = person.move(environment, target_pos_tuple, is_running)
        speed_text = "ran" if is_running else "walked"

        if result["success"]:
            final_pos = person.position # Get potentially updated position
            result_text = f"Successfully {speed_text} {direction_norm}. Now at {final_pos}."
            logger.info(f"  {tool_name}: Move successful. Backend position: {final_pos}")
            sync_story_state(story_result) # Sync state after successful move

            # Send command to frontend
            storyteller = getattr(story_result, '_storyteller_agent', None)
            if storyteller and hasattr(storyteller, 'send_command_to_frontend'):
                try:
                    command_params = {
                        "direction": direction_norm, # Send normalized direction
                        "is_running": is_running,
                        "continuous": False
                    }
                    logger.info(f"  {tool_name}: Sending command to frontend: move with params {command_params}")
                    await storyteller.send_command_to_frontend("move", command_params, result_text)
                    logger.info(f"  {tool_name}: Command sent to frontend successfully.")
                except Exception as e_ws:
                    logger.error(f"💥 TOOL {tool_name}: Error sending WebSocket command: {e_ws}", exc_info=True)
            else:
                logger.warning(f"⚠️ TOOL {tool_name}: Could not access storyteller agent to send WebSocket command.")

            logger.info(f"🏁 TOOL EXIT: {tool_name} finished successfully. Result: {result_text}")
            return result_text
        else:
            # Move failed
            result_msg = result['message']
            logger.warning(f"  {tool_name}: Move failed: {result_msg}")
            logger.info(f"🏁 TOOL EXIT: {tool_name} finished with failure. Result: {result_msg}")
            return f"Couldn't move {direction_norm}: {result_msg}"

    except Exception as e:
        logger.error(f"💥 TOOL {tool_name}: Unexpected error: {e}", exc_info=True)
        return f"❌ Error during movement: {e}"

@function_tool
async def jump(ctx: RunContextWrapper[CompleteStoryResult], target_x: int, target_y: int) -> str:
    """Jump the player character over one square to land at the target coordinates (target_x, target_y)."""
    tool_name = "jump"
    logger.info(f"🛠️ TOOL ENTRY: {tool_name}(target_x={target_x}, target_y={target_y})")
    try:
        story_result = ctx.context
        if not story_result.person:
            logger.error(f"💥 TOOL {tool_name}: Player character not found.")
            return "❌ Error: Player character not found."

        current_pos = story_result.person.position
        target_pos = (target_x, target_y)
        logger.info(f"  {tool_name}: Player at {current_pos}. Attempting jump to {target_pos}")

        result = story_result.person.jump(story_result.environment, target_pos)
        result_msg = result["message"]

        if result["success"]:
            logger.info(f"  {tool_name}: Jump successful. Result: {result_msg}")
            sync_story_state(story_result)

            # Send command to frontend
            storyteller = getattr(story_result, '_storyteller_agent', None)
            if storyteller and hasattr(storyteller, 'send_command_to_frontend'):
                try:
                    command_params = {"target_x": target_x, "target_y": target_y}
                    logger.info(f"  {tool_name}: Sending command to frontend: jump with params {command_params}")
                    await storyteller.send_command_to_frontend("jump", command_params, result_msg)
                    logger.info(f"  {tool_name}: Command sent to frontend successfully.")
                except Exception as e_ws:
                    logger.error(f"💥 TOOL {tool_name}: Error sending WebSocket command: {e_ws}", exc_info=True)
            else:
                 logger.warning(f"⚠️ TOOL {tool_name}: Could not access storyteller agent to send jump command.")

            logger.info(f"🏁 TOOL EXIT: {tool_name} finished successfully. Result: {result_msg}")
        else:
            logger.warning(f"  {tool_name}: Jump failed. Result: {result_msg}")
            logger.info(f"🏁 TOOL EXIT: {tool_name} finished with failure. Result: {result_msg}")

        return result_msg
    except Exception as e:
        logger.error(f"💥 TOOL {tool_name}: Unexpected error: {e}", exc_info=True)
        return f"❌ Error during jump: {e}"

@function_tool
async def push(ctx: RunContextWrapper[CompleteStoryResult], object_id: str, direction: str) -> str:
    """Push a specified object (by object_id) in a given direction ('left', 'right', 'up', 'down'). Player moves into the object's original space."""
    tool_name = "push"
    logger.info(f"🛠️ TOOL ENTRY: {tool_name}(object_id='{object_id}', direction='{direction}')")
    try:
        story_result = ctx.context
        if not story_result.person:
            logger.error(f"💥 TOOL {tool_name}: Player character not found.")
            return "❌ Error: Player character not found."

        sync_story_state(story_result) # Ensure nearby_objects is up-to-date
        logger.debug(f"  {tool_name}: Nearby objects after sync: {list(story_result.nearby_objects.keys())}")

        if object_id not in story_result.nearby_objects:
            logger.warning(f"  {tool_name}: Object '{object_id}' not found nearby.")
            return f"❓ Cannot push '{object_id}'. It's not nearby."

        obj = story_result.nearby_objects[object_id]
        obj_name = getattr(obj, 'name', object_id)
        obj_pos_attr = getattr(obj, 'position', None)

        if not obj_pos_attr:
             logger.warning(f"  {tool_name}: Object '{obj_name}' ({object_id}) has no position.")
             return f"❓ Cannot push '{obj_name}'. It has no position."

        # Ensure object position is a tuple for DirectionHelper
        obj_pos_tuple = None
        if hasattr(obj_pos_attr, 'x') and hasattr(obj_pos_attr, 'y'):
            obj_pos_tuple = (obj_pos_attr.x, obj_pos_attr.y)
        elif isinstance(obj_pos_attr, (tuple, list)) and len(obj_pos_attr) >= 2:
            obj_pos_tuple = (obj_pos_attr[0], obj_pos_attr[1])

        if obj_pos_tuple is None:
            logger.error(f"💥 TOOL {tool_name}: Could not determine valid coordinates for '{obj_name}' ({object_id}). Position: {obj_pos_attr}")
            return f"❓ Could not determine valid coordinates for '{obj_name}'."

        logger.info(f"  {tool_name}: Attempting push: Player at {story_result.person.position}, Object '{obj_name}' at {obj_pos_tuple}, Direction '{direction}'")

        # Calculate target position and push vector
        target_pos_tuple = DirectionHelper.get_relative_position(obj_pos_tuple, direction)
        push_vector = DirectionHelper.get_direction_vector(obj_pos_tuple, target_pos_tuple)
        logger.debug(f"  {tool_name}: Calculated target position {target_pos_tuple}, push vector {push_vector}")

        # Attempt the push
        result = story_result.person.push(story_result.environment, obj_pos_attr, push_vector)
        result_msg = result["message"]

        if result["success"]:
            logger.info(f"  {tool_name}: Push successful. Result: {result_msg}")
            sync_story_state(story_result)
            logger.info(f"🏁 TOOL EXIT: {tool_name} finished successfully. Result: {result_msg}")
        else:
            logger.warning(f"  {tool_name}: Push failed. Result: {result_msg}")
            logger.info(f"🏁 TOOL EXIT: {tool_name} finished with failure. Result: {result_msg}")

        return result_msg
    except Exception as e:
        logger.error(f"💥 TOOL {tool_name}: Unexpected error: {e}", exc_info=True)
        return f"❌ Error during push: {e}"

@function_tool
async def pull(ctx: RunContextWrapper[CompleteStoryResult], object_x: int, object_y: int) -> str:
    """Pull an object located at (object_x, object_y) towards the player. Player moves back one step, object takes player's original space."""
    tool_name = "pull"
    logger.info(f"🛠️ TOOL ENTRY: {tool_name}(object_x={object_x}, object_y={object_y})")
    try:
        story_result = ctx.context
        if not story_result.person:
            logger.error(f"💥 TOOL {tool_name}: Player character not found.")
            return "❌ Error: Player character not found."

        target_obj_pos = (object_x, object_y)
        player_pos = story_result.person.position
        logger.info(f"  {tool_name}: Attempting pull: Player at {player_pos}, Object at {target_obj_pos}")

        # Attempt the pull
        result = story_result.person.pull(story_result.environment, target_obj_pos)
        result_msg = result["message"]

        if result["success"]:
            logger.info(f"  {tool_name}: Pull successful. Result: {result_msg}")
            sync_story_state(story_result)
            logger.info(f"🏁 TOOL EXIT: {tool_name} finished successfully. Result: {result_msg}")
        else:
            logger.warning(f"  {tool_name}: Pull failed. Result: {result_msg}")
            logger.info(f"🏁 TOOL EXIT: {tool_name} finished with failure. Result: {result_msg}")

        return result_msg
    except Exception as e:
        logger.error(f"💥 TOOL {tool_name}: Unexpected error: {e}", exc_info=True)
        return f"❌ Error during pull: {e}"

@function_tool
async def get_from_container(ctx: RunContextWrapper[CompleteStoryResult], container_id: str, item_id: str) -> str:
    """Get an item (by item_id) from a container (by container_id) and add it to player inventory."""
    tool_name = "getFromContainer"
    logger.info(f"🛠️ TOOL ENTRY: {tool_name}(container_id='{container_id}', item_id='{item_id}')")
    try:
        story_result = ctx.context
        if not story_result.person:
            logger.error(f"💥 TOOL {tool_name}: Player character not found.")
            return "❌ Error: Player character not found."

        sync_story_state(story_result) # Ensure nearby_objects is up-to-date
        logger.debug(f"  {tool_name}: Nearby objects after sync: {list(story_result.nearby_objects.keys())}")

        accessible_containers = {
            obj_id: obj for obj_id, obj in story_result.nearby_objects.items()
            if isinstance(obj, Container)
        }
        logger.debug(f"  {tool_name}: Accessible containers nearby: {list(accessible_containers.keys())}")

        if container_id not in accessible_containers:
            logger.warning(f"  {tool_name}: Container '{container_id}' not found nearby.")
            return f"❓ Cannot find container '{container_id}' nearby."

        container = accessible_containers[container_id]
        container_name = getattr(container, 'name', container_id)
        logger.info(f"  {tool_name}: Attempting get: Item '{item_id}' from Container '{container_name}' ({container_id})")

        # Attempt the action
        result = story_result.person.get_from_container(container, item_id)
        result_msg = result["message"]

        if result["success"]:
            logger.info(f"  {tool_name}: Get successful. Result: {result_msg}")
            # No explicit sync needed here by design, inventory handled by person method
            logger.info(f"🏁 TOOL EXIT: {tool_name} finished successfully. Result: {result_msg}")
        else:
            logger.warning(f"  {tool_name}: Get failed. Result: {result_msg}")
            logger.info(f"🏁 TOOL EXIT: {tool_name} finished with failure. Result: {result_msg}")

        return result_msg
    except Exception as e:
        logger.error(f"💥 TOOL {tool_name}: Unexpected error: {e}", exc_info=True)
        return f"❌ Error getting item from container: {e}"

@function_tool
async def put_in_container(ctx: RunContextWrapper[CompleteStoryResult], container_id: str, item_id: str) -> str:
    """Put an item (by item_id) from player inventory into a container (by container_id)."""
    tool_name = "putInContainer"
    logger.info(f"🛠️ TOOL ENTRY: {tool_name}(container_id='{container_id}', item_id='{item_id}')")
    try:
        story_result = ctx.context
        if not story_result.person:
            logger.error(f"💥 TOOL {tool_name}: Player character not found.")
            return "❌ Error: Player character not found."

        sync_story_state(story_result) # Ensure nearby_objects is up-to-date
        logger.debug(f"  {tool_name}: Nearby objects after sync: {list(story_result.nearby_objects.keys())}")

        accessible_containers = {
            obj_id: obj for obj_id, obj in story_result.nearby_objects.items()
            if isinstance(obj, Container)
        }
        logger.debug(f"  {tool_name}: Accessible containers nearby: {list(accessible_containers.keys())}")

        if container_id not in accessible_containers:
            logger.warning(f"  {tool_name}: Container '{container_id}' not found nearby.")
            return f"❓ Cannot find container '{container_id}' nearby."

        container = accessible_containers[container_id]
        container_name = getattr(container, 'name', container_id)
        logger.info(f"  {tool_name}: Attempting put: Item '{item_id}' into Container '{container_name}' ({container_id})")

        # Check if item is in inventory first
        inventory_item = next((item for item in story_result.person.inventory.contents if hasattr(item, 'id') and item.id == item_id), None)
        if not inventory_item:
            logger.warning(f"  {tool_name}: Item '{item_id}' not found in player inventory.")
            return f"You don't have '{item_id}' in your inventory."

        # Attempt the action
        result = story_result.person.put_in_container(item_id, container)
        result_msg = result["message"]

        if result["success"]:
            logger.info(f"  {tool_name}: Put successful. Result: {result_msg}")
            # No explicit sync needed here by design
            logger.info(f"🏁 TOOL EXIT: {tool_name} finished successfully. Result: {result_msg}")
        else:
            logger.warning(f"  {tool_name}: Put failed. Result: {result_msg}")
            logger.info(f"🏁 TOOL EXIT: {tool_name} finished with failure. Result: {result_msg}")

        return result_msg
    except Exception as e:
        logger.error(f"💥 TOOL {tool_name}: Unexpected error: {e}", exc_info=True)
        return f"❌ Error putting item into container: {e}"

@function_tool
async def use_object_with(ctx: RunContextWrapper[CompleteStoryResult], item1_id: str, item2_id: str) -> str:
    """Use an item from inventory (item1_id) with another object (item2_id, can be in world or inventory)."""
    tool_name = "useObjectWith"
    logger.info(f"🛠️ TOOL ENTRY: {tool_name}(item1_id='{item1_id}', item2_id='{item2_id}')")
    try:
        story_result = ctx.context
        if not story_result.person:
            logger.error(f"💥 TOOL {tool_name}: Player character not found.")
            return "❌ Error: Player character not found."

        sync_story_state(story_result) # Sync state before use action
        logger.info(f"  {tool_name}: Attempting use: Item1 '{item1_id}' with Item2 '{item2_id}'")
        logger.debug(f"  {tool_name}: Nearby objects after sync: {list(story_result.nearby_objects.keys())}")
        inventory_ids = [item.id for item in story_result.person.inventory.contents if hasattr(item, 'id')]
        logger.debug(f"  {tool_name}: Inventory contents: {inventory_ids}")


        # Attempt the action
        result = story_result.person.use_object_with(item1_id, item2_id, story_result.environment, story_result.nearby_objects)
        result_msg = result["message"]

        if result["success"]:
            logger.info(f"  {tool_name}: Use successful. Result: {result_msg}")
            sync_story_state(story_result) # Sync state after successful use action
            logger.info(f"🏁 TOOL EXIT: {tool_name} finished successfully. Result: {result_msg}")
        else:
            logger.warning(f"  {tool_name}: Use failed. Result: {result_msg}")
            logger.info(f"🏁 TOOL EXIT: {tool_name} finished with failure. Result: {result_msg}")

        return result_msg
    except Exception as e:
        logger.error(f"💥 TOOL {tool_name}: Unexpected error: {e}", exc_info=True)
        return f"❌ Error using object with another: {e}"

@function_tool
async def look_around(ctx: RunContextWrapper[CompleteStoryResult]) -> str:
    """Look around the player in a 7x7 square area, revealing all objects and terrain features."""
    tool_name = "lookAround"
    logger.info(f"🛠️ TOOL ENTRY: {tool_name}()")
    try:
        story_result = ctx.context
        if not story_result.person:
            logger.error(f"💥 TOOL {tool_name}: Player character not found.")
            return "❌ Error: Player character not found."

        sync_story_state(story_result) # Crucial to update nearby_objects first
        logger.debug(f"  {tool_name}: Nearby objects synced.")

        player_pos_attr = story_result.person.position
        if not player_pos_attr:
            logger.error(f"💥 TOOL {tool_name}: Player has no position!")
            return "Error: Cannot determine your location."

        player_x, player_y = None, None
        if hasattr(player_pos_attr, 'x') and hasattr(player_pos_attr, 'y'):
            player_x, player_y = player_pos_attr.x, player_pos_attr.y
        elif isinstance(player_pos_attr, (tuple, list)) and len(player_pos_attr) >= 2:
            player_x, player_y = player_pos_attr[0], player_pos_attr[1]

        if player_x is None or player_y is None:
            logger.error(f"💥 TOOL {tool_name}: Could not extract player coordinates from position: {player_pos_attr}")
            return "Error: Cannot determine your exact coordinates."

        player_pos_tuple = (player_x, player_y)
        logger.info(f"  {tool_name}: Looking around from position: {player_pos_tuple}")

        SCAN_RADIUS = 3
        descriptions = ["You scan the area around you:"]
        objects_found = []
        objects_by_distance = {}

        terrain_desc = getattr(story_result, 'terrain_description', None)
        if terrain_desc: descriptions.append(f"Terrain: {terrain_desc}")

        for dy in range(-SCAN_RADIUS, SCAN_RADIUS + 1):
            for dx in range(-SCAN_RADIUS, SCAN_RADIUS + 1):
                if dx == 0 and dy == 0: continue # Skip player's exact spot

                check_x, check_y = player_pos_tuple[0] + dx, player_pos_tuple[1] + dy
                check_pos = (check_x, check_y)
                manhattan_distance = abs(dx) + abs(dy)

                if manhattan_distance not in objects_by_distance: objects_by_distance[manhattan_distance] = []

                direction = get_direction_label(dx, dy)

                if not story_result.environment.is_valid_position(check_pos):
                    objects_by_distance[manhattan_distance].append(f"  • {direction} ({check_x},{check_y}): Edge of the map")
                    continue

                can_move = story_result.environment.can_move_to(check_pos)
                entities_at_pos = story_result.environment.get_entities_at(check_pos)

                if entities_at_pos:
                    for entity in entities_at_pos:
                        obj_name = getattr(entity, 'name', 'unknown object')
                        obj_id = getattr(entity, 'id', 'unknown_id')
                        objects_by_distance[manhattan_distance].append(f"  • {direction} ({check_x},{check_y}): {obj_name} ({obj_id})")
                        objects_found.append(entity)
                elif not can_move:
                    objects_by_distance[manhattan_distance].append(f"  • {direction} ({check_x},{check_y}): Impassable terrain")

        # Add objects at the player's position (excluding player)
        entities_at_player = story_result.environment.get_entities_at(player_pos_tuple)
        player_location_items = []
        for entity in entities_at_player:
            if entity != story_result.person:
                obj_name = getattr(entity, 'name', 'unknown object')
                obj_id = getattr(entity, 'id', 'unknown_id')
                player_location_items.append(f"  • {obj_name} ({obj_id})")
                objects_found.append(entity)
        if player_location_items:
             descriptions.append("At your position:")
             descriptions.extend(player_location_items)

        # Build final description sorted by distance
        for distance in sorted(objects_by_distance.keys()):
            if objects_by_distance[distance]: # Only add if there's something at this distance
                descriptions.append(f"Distance {distance} from you:")
                descriptions.extend(objects_by_distance[distance])

        if len(descriptions) <= 2: # Only initial line and maybe terrain
            descriptions.append("You don't see anything notable nearby.")

        result_msg = "\n".join(descriptions)
        logger.info(f"  {tool_name}: Look result: Found {len(objects_found)} objects in a 7x7 area.")

        # Update nearby_objects with all found objects
        story_result.nearby_objects.update({obj.id: obj for obj in objects_found if hasattr(obj, 'id')})
        logger.debug(f"  {tool_name}: Updated nearby_objects: {list(story_result.nearby_objects.keys())}")

        logger.info(f"🏁 TOOL EXIT: {tool_name} finished successfully.")
        return result_msg
    except Exception as e:
        logger.error(f"💥 TOOL {tool_name}: Unexpected error: {e}", exc_info=True)
        return f"❌ Error looking around: {e}"

# Helper function to get a readable direction label
def get_direction_label(dx: int, dy: int) -> str:
    """Convert relative coordinates to a readable compass direction.
    Uses frontend coordinate system where:
    - Positive Y is South (down on screen)
    - Negative Y is North (up on screen)
    - Positive X is East (right on screen)
    - Negative X is West (left on screen)
    """
    if dx == 0 and dy == 0: return "Here" # Added case for player's own spot
    vertical = "North" if dy < 0 else "South"
    horizontal = "East" if dx > 0 else "West"
    
    if dx == 0: return vertical
    if dy == 0: return horizontal
    return f"{vertical}{horizontal}"

@function_tool
async def look_at(ctx: RunContextWrapper[CompleteStoryResult], object_id: str) -> str:
    """Look closely at a specific object (by object_id) either nearby or in inventory to get its description."""
    tool_name = "lookAt"
    logger.info(f"🛠️ TOOL ENTRY: {tool_name}(object_id='{object_id}')")
    # This tool is just an alias for examine_object
    try:
        logger.info(f"  {tool_name}: Alias for examine_object. Calling examine_object...")
        result = await examine_object(ctx, object_id)
        logger.info(f"🏁 TOOL EXIT: {tool_name} finished.")
        return result
    except Exception as e:
        logger.error(f"💥 TOOL {tool_name}: Unexpected error calling examine_object: {e}", exc_info=True)
        return f"❌ Error looking at object: {e}"

@function_tool
async def say(ctx: RunContextWrapper[CompleteStoryResult], message: str) -> str:
    """Make the player character say a message out loud."""
    tool_name = "say"
    logger.info(f"🛠️ TOOL ENTRY: {tool_name}(message='{message[:50]}...')")
    try:
        story_result = ctx.context
        if not story_result.person:
            logger.error(f"💥 TOOL {tool_name}: Player character not found.")
            return "❌ Error: Player character not found."

        logger.info(f"  {tool_name}: Player '{story_result.person.name}' says: '{message}'")
        result = story_result.person.say(message)
        result_msg = result["message"]

        logger.info(f"  {tool_name}: Say result: {result_msg}")
        logger.info(f"🏁 TOOL EXIT: {tool_name} finished successfully. Result: {result_msg}")
        return result_msg
    except Exception as e:
        logger.error(f"💥 TOOL {tool_name}: Unexpected error: {e}", exc_info=True)
        return f"❌ Error saying message: {e}"

@function_tool
async def check_inventory(ctx: RunContextWrapper[CompleteStoryResult]) -> str:
    """Check the player's inventory (legacy). Use 'inventory' instead for better formatting."""
    tool_name = "checkInventory (Legacy)"
    logger.info(f"🛠️ TOOL ENTRY: {tool_name}()")
    try:
        story_result = ctx.context
        if not story_result.person:
            logger.error(f"💥 TOOL {tool_name}: Player character not found.")
            return "❌ Error: Player character not found."

        logger.info(f"  {tool_name}: Checking inventory for '{story_result.person.name}'")
        if not hasattr(story_result.person, 'inventory') or not story_result.person.inventory:
            logger.info(f"  {tool_name}: Player has no inventory object.")
            return f"{story_result.person.name} has no inventory."

        items = story_result.person.inventory.contents
        if not items:
            logger.info(f"  {tool_name}: Inventory is empty.")
            return f"{story_result.person.name}'s inventory is empty."

        item_descriptions = []
        for item in items:
            item_id = getattr(item, 'id', 'unknown_id')
            item_name = getattr(item, 'name', 'Unknown Item')
            item_descriptions.append(f"- {item_id}: {item_name}")

        result_msg = f"{story_result.person.name}'s inventory contains:\n" + "\n".join(item_descriptions)
        logger.info(f"  {tool_name}: Found {len(items)} items (legacy format).")
        logger.info(f"🏁 TOOL EXIT: {tool_name} finished successfully.")
        return result_msg
    except Exception as e:
        logger.error(f"💥 TOOL {tool_name}: Unexpected error: {e}", exc_info=True)
        return f"❌ Error checking inventory (legacy): {e}"

@function_tool
async def inventory(ctx: RunContextWrapper[CompleteStoryResult]) -> str:
    """Check the player's inventory and list the items contained within."""
    tool_name = "inventory"
    logger.info(f"🛠️ TOOL ENTRY: {tool_name}()")
    try:
        story_result = ctx.context
        if not story_result.person:
            logger.error(f"💥 TOOL {tool_name}: Player character not found.")
            return "❌ Error: Player character not found."

        person_name = getattr(story_result.person, 'name', 'Player')
        logger.info(f"  {tool_name}: Checking inventory for '{person_name}'")

        if not hasattr(story_result.person, 'inventory') or not story_result.person.inventory:
            logger.info(f"  {tool_name}: Player has no inventory object.")
            return f"{person_name} has no inventory."

        items = story_result.person.inventory.contents
        if not items:
            logger.info(f"  {tool_name}: Inventory is empty.")
            return "Your inventory is empty."

        item_descriptions = []
        for item in items:
            item_name = getattr(item, 'name', 'Unknown Item')
            weight = getattr(item, 'weight', None)
            desc = item_name
            if weight is not None: desc += f" (Weight: {weight})"
            item_descriptions.append(f"- {desc}")

        result_msg = "You check your inventory. It contains:\n" + "\n".join(item_descriptions)
        logger.info(f"  {tool_name}: Inventory check found {len(items)} items.")
        logger.info(f"🏁 TOOL EXIT: {tool_name} finished successfully.")
        return result_msg
    except Exception as e:
        logger.error(f"💥 TOOL {tool_name}: Unexpected error: {e}", exc_info=True)
        return f"❌ Error checking inventory: {e}"

@function_tool
async def examine_object(ctx: RunContextWrapper[CompleteStoryResult], object_id: str) -> str:
    """Examine an object (by object_id) nearby or in inventory to get a detailed description including its properties and state."""
    tool_name = "examineObject"
    logger.info(f"🛠️ TOOL ENTRY: {tool_name}(object_id='{object_id}')")
    try:
        story_result = ctx.context
        if not story_result.person:
            logger.error(f"💥 TOOL {tool_name}: Player character not found.")
            return "❌ Error: Player character not found."

        sync_story_state(story_result) # Ensure lists are up-to-date
        logger.info(f"  {tool_name}: Searching for object '{object_id}'...")
        logger.debug(f"  {tool_name}: Nearby objects after sync: {list(story_result.nearby_objects.keys())}")
        inventory_ids = [item.id for item in story_result.person.inventory.contents if hasattr(item, 'id')]
        logger.debug(f"  {tool_name}: Inventory contents: {inventory_ids}")


        target_obj = None
        source = None

        # Order: Inventory -> Nearby -> World Map
        if hasattr(story_result.person, 'inventory'):
            for item in story_result.person.inventory.contents:
                if hasattr(item, 'id') and item.id == object_id:
                    target_obj = item
                    source = "inventory"
                    logger.info(f"  {tool_name}: Found '{object_id}' in inventory.")
                    break

        if not target_obj and hasattr(story_result, 'nearby_objects') and object_id in story_result.nearby_objects:
            target_obj = story_result.nearby_objects[object_id]
            source = "nearby"
            logger.info(f"  {tool_name}: Found '{object_id}' nearby.")

        if not target_obj and hasattr(story_result.environment, '_entity_map') and object_id in story_result.environment._entity_map:
            target_obj = story_result.environment._entity_map[object_id]
            source = "world"
            logger.info(f"  {tool_name}: Found '{object_id}' in world entity map (fallback).")

        if not target_obj:
            logger.warning(f"  {tool_name}: Object '{object_id}' not found anywhere.")
            return f"You can't find anything called '{object_id}' to examine."

        # Build description
        name = getattr(target_obj, 'name', 'the object')
        desc_list = [f"You examine {name} ({object_id}):"]

        base_desc = getattr(target_obj, 'description', None)
        if base_desc: desc_list.append(f"- Description: {base_desc}")

        if source != "inventory":
            position_attr = getattr(target_obj, 'position', None)
            if position_attr:
                pos_x, pos_y = None, None
                if hasattr(position_attr, 'x') and hasattr(position_attr, 'y'): pos_x, pos_y = position_attr.x, position_attr.y
                elif isinstance(position_attr, (tuple, list)) and len(position_attr) >= 2: pos_x, pos_y = position_attr[0], position_attr[1]
                if pos_x is not None and pos_y is not None: desc_list.append(f"- Location: ({pos_x},{pos_y})")

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
        logger.info(f"  {tool_name}: Examination complete for '{object_id}'.")
        logger.info(f"🏁 TOOL EXIT: {tool_name} finished successfully.")
        return result_msg
    except Exception as e:
        logger.error(f"💥 TOOL {tool_name}: Unexpected error: {e}", exc_info=True)
        return f"❌ Error examining object: {e}"

# --- ADDED NEW TOOL: changeState ---
@function_tool
async def change_state(ctx: RunContextWrapper[CompleteStoryResult], object_id: str, new_state: str) -> str:
    """Change the state of a specified object (by object_id) to a new state.
    Use this as a fallback tool for actions that modify an object's condition when no other specific tool applies.
    Examples: 'light campfire', 'extinguish torch', 'open box', 'close door', 'unlock chest'.

    Args:
        ctx: The RunContext containing the game state.
        object_id: The unique ID of the object whose state needs to change.
        new_state: The desired new state for the object (e.g., 'lit', 'unlit', 'open', 'closed', 'locked', 'unlocked').

    Returns:
        str: Description of the state change result or an error message.
    """
    tool_name = "changeState"
    logger.info(f"🛠️ TOOL ENTRY: {tool_name}(object_id='{object_id}', new_state='{new_state}')")
    try:
        story_result = ctx.context
        if not story_result.person:
            logger.error(f"💥 TOOL {tool_name}: Player character not found.")
            return "❌ Error: Player character not found."

        sync_story_state(story_result) # Ensure lists are up-to-date
        logger.info(f"  {tool_name}: Searching for object '{object_id}' to change state...")
        logger.debug(f"  {tool_name}: Nearby objects after sync: {list(story_result.nearby_objects.keys())}")
        inventory_ids = [item.id for item in story_result.person.inventory.contents if hasattr(item, 'id')]
        logger.debug(f"  {tool_name}: Inventory contents: {inventory_ids}")


        target_obj = None
        source = None

        # Order: Inventory -> Nearby -> World Map
        if hasattr(story_result.person, 'inventory'):
            for item in story_result.person.inventory.contents:
                if hasattr(item, 'id') and item.id == object_id:
                    target_obj = item
                    source = "inventory"
                    logger.info(f"  {tool_name}: Found '{object_id}' in inventory.")
                    break

        if not target_obj and hasattr(story_result, 'nearby_objects') and object_id in story_result.nearby_objects:
            target_obj = story_result.nearby_objects[object_id]
            source = "nearby"
            logger.info(f"  {tool_name}: Found '{object_id}' nearby.")

        if not target_obj and hasattr(story_result.environment, '_entity_map') and object_id in story_result.environment._entity_map:
            target_obj = story_result.environment._entity_map[object_id]
            source = "world"
            logger.info(f"  {tool_name}: Found '{object_id}' in world entity map (fallback).")

        if not target_obj:
            logger.warning(f"  {tool_name}: Object '{object_id}' not found anywhere.")
            return f"You can't find anything called '{object_id}' to change its state."

        object_name = getattr(target_obj, 'name', object_id)

        # Check if the object has a 'state' attribute
        if not hasattr(target_obj, 'state'):
            logger.warning(f"  {tool_name}: Object '{object_name}' ({object_id}) does not have a settable 'state' attribute.")
            return f"The {object_name} doesn't seem to have a state that can be changed."

        # Change the state
        old_state = getattr(target_obj, 'state', 'unknown')
        setattr(target_obj, 'state', new_state)
        # Optional: Sync state again after modification? Let's assume setattr works reliably for now.
        # sync_story_state(story_result)
        logger.info(f"  {tool_name}: Successfully changed state of '{object_name}' ({object_id}) from '{old_state}' to '{new_state}'.")
        result_msg = f"You changed the state of the {object_name} to '{new_state}'."
        logger.info(f"🏁 TOOL EXIT: {tool_name} finished successfully. Result: {result_msg}")
        return result_msg
    except Exception as e:
        logger.error(f"💥 TOOL {tool_name}: Error setting state for '{object_id}': {e}", exc_info=True)
        return f"❌ An error occurred while trying to change the state of the {object_name}."

# --- END ADDED TOOL ---

@function_tool
async def execute_movement_sequence(ctx: RunContextWrapper[CompleteStoryResult], commands: List[Dict[str, Any]]) -> str:
    """Execute a sequence of movement commands ('move', 'jump') provided as a list. Stops if any command fails."""
    tool_name = "executeMovementSequence"
    logger.info(f"🛠️ TOOL ENTRY: {tool_name}(commands_count={len(commands)})")
    try:
        story_result = ctx.context
        if not story_result.person:
            logger.error(f"💥 TOOL {tool_name}: Player character not found.")
            return "❌ Error: Player character not found."

        results = []
        logger.debug(f"  {tool_name}: Commands: {json.dumps(commands, indent=2)}")

        for i, cmd in enumerate(commands):
            tool_name_step = cmd.get('tool')
            params_step = cmd.get('parameters', {})
            logger.info(f"  {tool_name}: Executing Step {i+1}/{len(commands)}: {tool_name_step} with params {params_step}")
            step_result = ""
            success = False
            try:
                if tool_name_step == 'move':
                    direction = params_step.get('direction')
                    is_running = params_step.get('is_running', False)
                    continuous = params_step.get('continuous', False)
                    if direction:
                         step_result = await move(ctx, direction, is_running, continuous)
                         if "Successfully" in step_result or "already there" in step_result.lower(): success = True
                         else: success = False
                    else:
                         step_result = "Move command missing direction."
                         success = False
                elif tool_name_step == 'jump':
                    target_x = params_step.get('target_x')
                    target_y = params_step.get('target_y')
                    if target_x is not None and target_y is not None:
                        step_result = await jump(ctx, target_x, target_y)
                        if "Successfully jumped" in step_result or "jumped" in step_result.lower(): success = True
                        else: success = False
                    else:
                        step_result = "Jump command missing target coordinates."
                        success = False
                else:
                    step_result = f"Unknown movement command: {tool_name_step}"
                    logger.warning(f"  {tool_name}: Unknown command '{tool_name_step}' in sequence.")
                    success = False

                results.append(f"Step {i+1} ({tool_name_step}): {step_result}")
                logger.info(f"  {tool_name}: Step {i+1} result: {'✅ Success' if success else '❌ Failed'} - {step_result}")

                if not success:
                    results.append("Sequence stopped due to failure.")
                    logger.warning(f"  {tool_name}: Movement sequence stopped at step {i+1} due to failure.")
                    break
            except Exception as e_step:
                logger.error(f"💥 TOOL {tool_name}: Error executing step {i+1} ({tool_name_step}): {e_step}", exc_info=True)
                results.append(f"Step {i+1} ({tool_name_step}): Error - {e_step}")
                results.append("Sequence stopped due to error.")
                break

        result_msg = "\n".join(results)
        logger.info(f"🏁 TOOL EXIT: {tool_name} finished. Final Result:\n{result_msg}")
        return result_msg
    except Exception as e:
        logger.error(f"💥 TOOL {tool_name}: Unexpected error: {e}", exc_info=True)
        return f"❌ Error executing movement sequence: {e}"

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
    move_to_object,
    jump,
    push,
    pull,
    get_from_container,
    put_in_container,
    use_object_with,
    look_around,
    look_at, # Alias for examine
    inventory, # Preferred inventory check
    examine_object,
    change_state, # Add the new tool here
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
        system_prompt = get_storyteller_system_prompt(theme, quest_title, get_game_mechanics_reference())

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
                context=self.game_context,
                # You could potentially adjust max_turns here if needed
                # max_turns=10 
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
            logger.error(f"💥 Agent hit max turns limit: {e}", exc_info=False) # Don't need full traceback here
            user_message = "I seem to have gotten stuck in a loop thinking about that. Could you try rephrasing your request or giving a different command?"
            response_content = self._create_basic_answer_json(user_message, options=["Okay"])
            return {"type": "json", "content": response_content}, conversation_history

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
            # --- MODIFICATION: Moved imports inside the function --- 
            from deepgram import (
                PrerecordedOptions,
                FileSource
            )
            # --- END MODIFICATION --- 

            # Create options for transcription
            options = PrerecordedOptions(
                model="nova-3",
                smart_format=True,
                language="en"
            )

            # Generate buffer source from bytes
            source: FileSource = {"buffer": audio_data} # Use dict literal as per Deepgram SDK docs

            # Get transcription response
            # --- MODIFICATION: Removed await as transcribe_file seems synchronous here ---
            response = self.deepgram_client.listen.prerecorded.v("1").transcribe_file(source, options)
            # --- END MODIFICATION ---

            # Extract transcript from response
            if response and hasattr(response, 'results') and hasattr(response.results, 'channels') and len(response.results.channels) > 0:
                transcript = response.results.channels[0].alternatives[0].transcript
                logger.info(f"  Deepgram Transcript: '{transcript}'")
                return transcript if transcript else ""
            else:
                logger.warning("No transcript found in Deepgram response")
                logger.debug(f"Deepgram full response: {response}")
                return ""
        except Exception as e:
            logger.error(f"Error transcribing audio with Deepgram: {e}", exc_info=True)
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
