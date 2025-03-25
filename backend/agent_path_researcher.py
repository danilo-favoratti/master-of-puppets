import asyncio
import heapq
from typing import List, Tuple, Any

from agents import (
    Agent,
    Runner,
    function_tool,
    RunContextWrapper,
    trace
)

class PathNode:
    """Node used in the A* path-finding algorithm."""
    def __init__(self, position, parent=None):
        self.position = position  # (x, y) tuple
        self.parent = parent  # parent PathNode
        
        # f = g + h
        self.g = 0  # cost from start to current node
        self.h = 0  # heuristic (estimated cost from current to goal)
        self.f = 0  # total cost
    
    def __eq__(self, other):
        return self.position == other.position
    
    def __lt__(self, other):
        return self.f < other.f
    
    def __hash__(self):
        return hash(self.position)

class PathFinder:
    """Class implementing A* path-finding algorithm with jump support."""
    
    @staticmethod
    def manhattan_distance(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> int:
        """Calculate Manhattan distance between two positions."""
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
    
    @staticmethod
    def get_neighbors(position: Tuple[int, int], game_map) -> List[Tuple[int, int]]:
        """Get all valid neighboring positions (cardinal directions only - no diagonals)."""
        x, y = position
        # Define only the 4 cardinal directions
        directions = [
            (0, -1),  # up
            (1, 0),   # right
            (0, 1),   # down
            (-1, 0)   # left
        ]
        
        neighbors = []
        for dx, dy in directions:
            new_pos = (x + dx, y + dy)
            if game_map.is_valid_position(new_pos) and game_map.can_move_to(new_pos):
                neighbors.append(new_pos)
        
        return neighbors
    
    @staticmethod
    def get_jump_neighbors(position: Tuple[int, int], game_map) -> List[Tuple[int, int]]:
        """Get positions that can be reached by jumping from the current position."""
        x, y = position
        # Define the 4 cardinal directions
        directions = [
            (0, -1),  # up
            (1, 0),   # right
            (0, 1),   # down
            (-1, 0)   # left
        ]
        
        jump_neighbors = []
        for dx, dy in directions:
            # Calculate the positions for the jump
            middle_pos = (x + dx, y + dy)  # Position to jump over
            landing_pos = (x + dx*2, y + dy*2)  # Position to land on
            
            # Check if the jump is valid:
            # 1. The middle position must be valid
            # 2. The object at middle position must be jumpable
            # 3. The landing position must be valid and empty
            if (game_map.is_valid_position(middle_pos) and
                game_map.is_valid_position(landing_pos) and
                game_map.can_move_to(landing_pos)):
                
                # Get the object at the middle position
                middle_obj = game_map.get_object_at(middle_pos)
                if middle_obj and hasattr(middle_obj, 'is_jumpable') and middle_obj.is_jumpable:
                    jump_neighbors.append(landing_pos)
        
        return jump_neighbors
    
    @staticmethod
    def find_path(game_map, start_pos: Tuple[int, int], end_pos: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        Find the shortest path from start_pos to end_pos using A* algorithm.
        
        Args:
            game_map: The game map with position information
            start_pos: Starting position (x, y)
            end_pos: Goal position (x, y)
            
        Returns:
            List of positions forming the path, or empty list if no path found
        """
        # Check if start or end positions are invalid
        if not game_map.is_valid_position(start_pos) or not game_map.is_valid_position(end_pos):
            return []
        
        # Create start and end nodes
        start_node = PathNode(start_pos)
        end_node = PathNode(end_pos)
        
        # Initialize open and closed lists
        open_list = []
        closed_set = set()
        
        # Add the start node to the open list
        heapq.heappush(open_list, start_node)
        
        # Loop until the open list is empty
        while open_list:
            # Get the node with the lowest f value from the open list
            current_node = heapq.heappop(open_list)
            closed_set.add(current_node.position)
            
            # Check if we've reached the goal
            if current_node.position == end_node.position:
                # Reconstruct the path
                path = []
                while current_node:
                    path.append(current_node.position)
                    current_node = current_node.parent
                # Return the path in correct order (start to end)
                return path[::-1]
            
            # Get neighbors (including regular moves and jumps)
            neighbors = PathFinder.get_neighbors(current_node.position, game_map)
            jump_neighbors = PathFinder.get_jump_neighbors(current_node.position, game_map)
            
            # Combine all neighbors
            all_neighbors = neighbors + jump_neighbors
            
            # Process each neighbor
            for neighbor_pos in all_neighbors:
                # Skip if already in closed set
                if neighbor_pos in closed_set:
                    continue
                
                # Create neighbor node
                neighbor = PathNode(neighbor_pos, current_node)
                
                # Calculate costs
                # g cost: path cost from start to this neighbor
                # - Walking cardinally costs 1
                # - Regular move costs 8
                # - Jump costs 5
                is_jump = neighbor_pos in jump_neighbors
                is_cardinal = neighbor_pos in neighbors and abs(neighbor_pos[0] - current_node.position[0]) + abs(neighbor_pos[1] - current_node.position[1]) == 1
                
                if is_jump:
                    move_cost = 5
                elif is_cardinal:
                    move_cost = 1
                else:
                    move_cost = 8
                    
                neighbor.g = current_node.g + move_cost
                
                # h cost: estimated cost from this neighbor to goal (Manhattan distance)
                # Use minimum possible cost (1) for heuristic to ensure optimality
                neighbor.h = PathFinder.manhattan_distance(neighbor_pos, end_pos)
                
                # f cost: total estimated cost
                neighbor.f = neighbor.g + neighbor.h
                
                # Check if neighbor is already in open list with a better path
                skip = False
                for i, open_node in enumerate(open_list):
                    if (open_node.position == neighbor.position and 
                        open_node.g <= neighbor.g):
                        skip = True
                        break
                
                if skip:
                    continue
                
                # Add neighbor to open list
                heapq.heappush(open_list, neighbor)
        
        # No path found
        return []


# Type for path-finding context
class PathContext:
    game_map: Any  # The game map with grid and object information
    
    def __init__(self, game_map):
        self.game_map = game_map

# Tool definition for path finding
@function_tool
async def find_path(
    ctx: RunContextWrapper[PathContext],
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int
) -> dict:
    """Find the shortest path between two positions on the game map.
    
    Args:
        start_x: Starting X coordinate
        start_y: Starting Y coordinate
        end_x: Ending X coordinate
        end_y: Ending Y coordinate
        
    Returns:
        Dictionary with path information and status
    """
    game_map = ctx.context.game_map
    
    start_pos = (start_x, start_y)
    end_pos = (end_x, end_y)
    
    # Validate positions
    if not game_map.is_valid_position(start_pos):
        return {
            "success": False,
            "message": f"Invalid starting position: {start_pos}",
            "path": []
        }
    
    if not game_map.is_valid_position(end_pos):
        return {
            "success": False,
            "message": f"Invalid ending position: {end_pos}",
            "path": []
        }
    
    # Find the path
    path = PathFinder.find_path(game_map, start_pos, end_pos)
    
    if not path:
        return {
            "success": False,
            "message": f"No path found from {start_pos} to {end_pos}",
            "path": []
        }
    
    # Determine if the path includes jumps (for informational purposes)
    jumps = []
    for i in range(len(path) - 2):
        pos1, pos2, pos3 = path[i], path[i+1], path[i+2]
        dx1 = pos2[0] - pos1[0]
        dy1 = pos2[1] - pos1[1]
        dx2 = pos3[0] - pos2[0]
        dy2 = pos3[1] - pos2[1]
        if (abs(dx1) > 1 or abs(dy1) > 1) or (abs(dx2) > 1 or abs(dy2) > 1):
            jumps.append(f"Jump from {pos1} over {pos2} to {pos3}")
    
    # Convert the path into a sequence of movement commands
    movement_commands = []
    for i in range(1, len(path)):
        prev = path[i-1]
        curr = path[i]
        dx = curr[0] - prev[0]
        dy = curr[1] - prev[1]
        if abs(dx) + abs(dy) == 1:
            # Regular move command
            if dx == 1:
                direction = "right"
            elif dx == -1:
                direction = "left"
            elif dy == 1:
                direction = "down"
            elif dy == -1:
                direction = "up"
            command = {"tool": "move", "parameters": {"direction": direction, "is_running": False, "continuous": False}}
        elif abs(dx) + abs(dy) == 2:
            # Jump command
            command = {"tool": "jump", "parameters": {"target_x": curr[0], "target_y": curr[1]}}
        else:
            # Fallback (should not occur)
            command = {"tool": "move", "parameters": {"direction": "up", "is_running": False, "continuous": False}}
        movement_commands.append(command)
    
    return {
        "success": True,
        "message": f"Path found with {len(path)-1} steps" + (f" including {len(jumps)} jumps" if jumps else ""),
        "path": path,
        "steps": len(path) - 1,
        "jumps": jumps,
        "movement_commands": movement_commands
    }

@function_tool
async def analyze_position(
    ctx: RunContextWrapper[PathContext],
    x: int,
    y: int
) -> dict:
    """Analyze a position on the game map to check if it's valid, occupied, and get object information.
    
    Args:
        x: X coordinate to analyze
        y: Y coordinate to analyze
        
    Returns:
        Dictionary with position analysis
    """
    game_map = ctx.context.game_map
    position = (x, y)
    
    # Check if position is valid
    is_valid = game_map.is_valid_position(position)
    
    # Default response for invalid positions
    if not is_valid:
        return {
            "success": False,
            "message": f"Position {position} is invalid (outside map boundaries)",
            "is_valid": False,
            "can_move_to": False,
            "object": None
        }
    
    # Check if we can move to this position
    can_move_to = game_map.can_move_to(position)
    
    # Get object at position if any
    obj = game_map.get_object_at(position)
    obj_info = None
    
    if obj:
        # Extract relevant object information
        obj_info = {
            "id": obj.id,
            "name": obj.name,
            "is_movable": getattr(obj, "is_movable", False),
            "is_jumpable": getattr(obj, "is_jumpable", False)
        }
        
        # Add description if available
        if hasattr(obj, "description"):
            obj_info["description"] = obj.description
    
    return {
        "success": True,
        "message": f"Position {position} analyzed successfully",
        "is_valid": is_valid,
        "can_move_to": can_move_to,
        "object": obj_info
    }

# Create the path-finding agent
def create_path_agent():
    return Agent[PathContext](
        name="PathFinder",
        instructions="""You are a path-finding agent in a game world. Your primary purpose is to find the optimal paths between positions on the game grid.

You have full access to the game map through the context, which provides information about:
- The grid size and boundaries
- Objects placed on the grid and their properties
- Whether positions are valid and can be moved to

Your main capabilities include:
1. Finding the shortest path between two positions using the A* algorithm
2. Considering both normal movement and jumping over jumpable objects
3. Analyzing specific positions to check their status and contents

Movement restrictions:
- Characters can ONLY move in the four cardinal directions (up, down, left, right)
- Diagonal movement is NOT allowed
- Each step must be to an adjacent cell in one of these four directions

When finding paths:
- You consider both regular moves to adjacent cells and jumps over jumpable objects
- Jumps are treated as slightly more costly than regular moves to prefer regular paths when equal
- The path returned will be a list of positions from start to end

The game uses a coordinate system where:
- X increases from left to right
- Y increases from top to bottom
- The top-left corner is at (0, 0)

Key features of your path-finding:
- You'll automatically detect when jumping is possible and incorporate it into paths
- You can handle obstacles by finding paths around them
- If no path exists, you'll clearly indicate that

Always validate input positions before attempting to find paths to ensure they are within map boundaries and represent valid starting/ending points.

Use the analyze_position tool to gather information about specific grid locations when needed.
""",
        tools=[
            find_path,
            analyze_position
        ],
    )

# Example usage function
async def example_usage():
    """Example of how to use the path-finding agent."""
    # Create a mock game map (similar to the one in agent_puppet_master.py)
    class SimpleGameMap:
        def __init__(self):
            self.entities = {}
            self.size = (15, 10)  # Match the actual game board dimensions
        
        def is_valid_position(self, position):
            x, y = position
            return 0 <= x < self.size[0] and 0 <= y < self.size[1]
        
        def can_move_to(self, position):
            if not self.is_valid_position(position):
                return False
            
            # Check if position is occupied by non-movable entity
            for entity in self.entities.values():
                if entity.position == position and hasattr(entity, 'is_movable') and not entity.is_movable:
                    return False
            
            return True
        
        def get_object_at(self, position):
            for entity in self.entities.values():
                if entity.position == position:
                    return entity
            return None
        
        def add_entity(self, entity):
            self.entities[entity.id] = entity
            entity.set_position(entity.position)
    
    # Mock GameObject class
    class GameObject:
        def __init__(self, id, name, position, is_movable=False, is_jumpable=False, description=None):
            self.id = id
            self.name = name
            self.position = position
            self.is_movable = is_movable
            self.is_jumpable = is_jumpable
            self.description = description
        
        def set_position(self, position):
            self.position = position
    
    # Create a game map
    game_map = SimpleGameMap()
    
    # Add some objects to the map
    rock = GameObject(id="rock1", name="Large Rock", position=(3, 3), 
                      is_movable=False, is_jumpable=True, description="A large rock that can be jumped over")
    game_map.add_entity(rock)
    
    wall = GameObject(id="wall1", name="Stone Wall", position=(5, 2), 
                     is_movable=False, is_jumpable=False, description="A solid stone wall")
    game_map.add_entity(wall)
    
    log = GameObject(id="log1", name="Fallen Log", position=(7, 5), 
                    is_movable=True, is_jumpable=True, description="A fallen log that can be moved or jumped over")
    game_map.add_entity(log)
    
    # Create path context
    path_context = PathContext(game_map)
    
    # Create the agent
    agent = create_path_agent()
    
    # Thread ID for tracing
    thread_id = "path-finding-example"
    
    # Example query: find path from (1,1) to (8,8)
    print("\nFinding path from (1,1) to (8,8)...")
    
    with trace(workflow_name="PathFinding", group_id=thread_id):
        result = await Runner.run(
            starting_agent=agent,
            input="Find the shortest path from position (1,1) to position (8,8)",
            context=path_context,
        )
    
    print(f"Result: {result.final_output}")
    
    # Example query: analyze position with object
    print("\nAnalyzing position (3,3) that contains a rock...")
    
    with trace(workflow_name="PositionAnalysis", group_id=thread_id):
        result = await Runner.run(
            starting_agent=agent,
            input="What is at position (3,3)?",
            context=path_context,
        )
    
    print(f"Result: {result.final_output}")

if __name__ == "__main__":
    asyncio.run(example_usage()) 