import asyncio
import os
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from colorama import init, Fore, Style
from board import Board  # Import the model's Board class
from game_object import Container, GameObject
from person import Person
from agent_path_researcher import PathFinder, PathNode, PathContext
from agents import Agent, Runner, function_tool, RunContextWrapper, trace

# A* Pathfinding implementation
import heapq
from typing import List, Optional, Tuple, Dict, Any

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
                # - Regular move costs 1
                # - Jump costs 1.5 (slightly higher to prefer regular moves when equal)
                is_jump = neighbor_pos in jump_neighbors
                move_cost = 1.5 if is_jump else 1.0
                neighbor.g = current_node.g + move_cost
                
                # h cost: estimated cost from this neighbor to goal (Manhattan distance)
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

# Initialize colorama for cross-platform colored terminal output
init()

def find_path(game_map, start_x: int, start_y: int, end_x: int, end_y: int) -> dict:
    """Find the shortest path between two positions on the game map.
    
    Args:
        game_map: The game map object
        start_x: Starting X coordinate
        start_y: Starting Y coordinate
        end_x: Ending X coordinate
        end_y: Ending Y coordinate
        
    Returns:
        Dictionary with path information and status
    """
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
    
    # Find the path using PathFinder from agent_path_researcher.py
    path = PathFinder.find_path(game_map, start_pos, end_pos)
    
    if not path:
        return {
            "success": False,
            "message": f"No path found from {start_pos} to {end_pos}",
            "path": []
        }
    
    # Determine if the path includes jumps
    jumps = []
    for i in range(len(path) - 2):
        pos1, pos2, pos3 = path[i], path[i+1], path[i+2]
        
        # Check if this might be a jump (if distance > 1)
        dx1 = pos2[0] - pos1[0]
        dy1 = pos2[1] - pos1[1]
        dx2 = pos3[0] - pos2[0]
        dy2 = pos3[1] - pos2[1]
        
        if (abs(dx1) > 1 or abs(dy1) > 1) or (abs(dx2) > 1 or abs(dy2) > 1):
            jumps.append(f"Jump from {pos1} over {pos2} to {pos3}")
    
    return {
        "success": True,
        "message": f"Path found with {len(path)-1} steps" + (f" including {len(jumps)} jumps" if jumps else ""),
        "path": path,
        "steps": len(path) - 1,
        "jumps": jumps
    }

def analyze_position(game_map, x: int, y: int) -> dict:
    """Analyze a position on the game map to check if it's valid, occupied, and get object information.
    
    Args:
        game_map: The game map object
        x: X coordinate to analyze
        y: Y coordinate to analyze
        
    Returns:
        Dictionary with position analysis
    """
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

def print_board(board, path=None, start_pos=None, end_pos=None):
    """Print a visual representation of the game board with path overlay.
    
    Args:
        board: The game board instance
        path: Optional list of positions forming a path
        start_pos: Optional starting position to highlight
        end_pos: Optional ending position to highlight
    """
    # Print separator line
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    
    # Print header
    print(f"\n{Fore.CYAN}=== Pathfinding Test Board ({board.width}x{board.height}) ===\n{Style.RESET_ALL}")
    
    # Cell width and spacing configuration
    cell_width = 3
    spacing = 3  # Space between cells
    total_cell_width = cell_width + spacing
    
    # Print coordinates header
    print("    ", end="")  # Extra space for alignment
    for x in range(board.width):
        print(f"{x:^{total_cell_width}}", end="")
    print("\n   ", end="")  # Three spaces for alignment
    print("-" * (board.width * total_cell_width + 2))  # Adjust border width
    
    # Get current board state
    board_map = {}
    legend = {}
    
    # Add path positions to board_map if provided
    if path:
        for i, pos in enumerate(path):
            if i == 0 and start_pos:
                continue  # Skip start position, we'll add it separately
            if i == len(path) - 1 and end_pos:
                continue  # Skip end position, we'll add it separately
                
            # Show path as numbers for sequence
            board_map[pos] = {
                "symbol": f"{i}",
                "color": Fore.MAGENTA,
                "name": f"Path step {i}",
                "priority": 3  # Lower than objects
            }
        legend["1..n"] = f"{Fore.MAGENTA}Path step{Style.RESET_ALL}"
    
    # Add start and end positions with high priority
    if start_pos:
        board_map[start_pos] = {
            "symbol": "S",
            "color": Fore.GREEN,
            "name": "Start position",
            "priority": 0  # Highest priority
        }
        legend["S"] = f"{Fore.GREEN}Start position{Style.RESET_ALL}"
        
    if end_pos:
        board_map[end_pos] = {
            "symbol": "E",
            "color": Fore.RED,
            "name": "End position",
            "priority": 0  # Highest priority
        }
        legend["E"] = f"{Fore.RED}End position{Style.RESET_ALL}"
    
    # Add entities to board_map
    for position in board._position_map:
        entities = board.get_entities_at(position)
        for entity in entities:
            # Skip if there's already something with higher priority
            if position in board_map and board_map[position]["priority"] <= 1:
                continue
                
            if isinstance(entity, Container):
                symbol = "C"
                color = Fore.YELLOW
                priority = 1
                legend[symbol] = f"{color}Container{Style.RESET_ALL}"
            elif isinstance(entity, GameObject):
                is_jumpable = getattr(entity, "is_jumpable", False)
                
                if is_jumpable:
                    symbol = "J"
                    color = Fore.BLUE
                    priority = 2
                    legend[symbol] = f"{color}Jumpable Object{Style.RESET_ALL}"
                elif entity.is_movable:
                    symbol = "O"
                    color = Fore.BLUE
                    priority = 2
                    legend[symbol] = f"{color}Movable Object{Style.RESET_ALL}"
                else:
                    symbol = "X"
                    color = Fore.RED
                    priority = 1
                    legend[symbol] = f"{color}Immovable Object{Style.RESET_ALL}"
            else:
                continue
            
            board_map[position] = {
                "symbol": symbol,
                "color": color,
                "name": entity.name,
                "priority": priority
            }
    
    # Print the board
    for y in range(board.height):
        print(f"{y:3}|", end="")  # Three digits for row numbers
        for x in range(board.width):
            pos = (x, y)
            if pos in board_map:
                entity_info = board_map[pos]
                symbol = entity_info["symbol"]
                # Create 3-character centered cell with dots as padding
                cell = f"{entity_info['color']}{symbol:^{cell_width}}{Style.RESET_ALL}"
                print(f"{cell.replace(' ', '.')}" + " " * spacing, end="")
            else:
                # Empty cell with dots
                empty_cell = "." * cell_width
                print(empty_cell + " " * spacing, end="")
        print("|")
    
    # Print bottom border
    print("   ", end="")  # Three spaces for alignment
    print("-" * (board.width * total_cell_width + 2))
    
    # Print legend
    print(f"\n{Fore.CYAN}=== Legend ==={Style.RESET_ALL}")
    for symbol, description in legend.items():
        print(f"{symbol}: {description}")
    print(f"{'.' * cell_width}: Empty space\n")
    
    print(f"{Fore.CYAN}==========================={Style.RESET_ALL}\n")

async def setup_test_board():
    """Set up a test board with obstacles and jumpable objects."""
    # Create a game board
    board = Board(width=15, height=10)
    
    # Create some objects on the board
    
    # Create a wall-like barrier with a gap
    for x in range(3, 8):
        if x != 5:  # Leave a gap at x=5
            wall = GameObject(
                id=f"wall{x}", 
                name="Stone Wall", 
                description="A solid stone wall", 
                is_movable=False,
                is_jumpable=False
            )
            board.add_entity(wall, (x, 3))
    
    # Create some rocks (jumpable objects)
    positions = [(2, 5), (5, 5), (8, 5), (10, 7), (4, 8)]
    for i, pos in enumerate(positions):
        rock = GameObject(
            id=f"rock{i+1}",
            name=f"Rock {i+1}",
            description="A large rock that can be jumped over",
            is_movable=False,
            is_jumpable=True
        )
        board.add_entity(rock, pos)
    
    # Create some movable objects
    positions = [(7, 1), (9, 4), (12, 6)]
    for i, pos in enumerate(positions):
        box = GameObject(
            id=f"box{i+1}",
            name=f"Wooden Box {i+1}",
            description="A wooden box that can be moved",
            is_movable=True,
            is_jumpable=False
        )
        board.add_entity(box, pos)
    
    # Create a fallen log (both movable and jumpable)
    log = GameObject(
        id="log1",
        name="Fallen Log",
        description="A fallen log that can be moved or jumped over",
        is_movable=True,
        is_jumpable=True
    )
    board.add_entity(log, (7, 7))
    
    return board

def print_help():
    """Print available commands and usage information."""
    print(f"\n{Fore.CYAN}=== Available Commands ==={Style.RESET_ALL}")
    print(f"- {Fore.YELLOW}find x1,y1 x2,y2{Style.RESET_ALL}: Find path from (x1,y1) to (x2,y2)")
    print(f"- {Fore.YELLOW}analyze x,y{Style.RESET_ALL}: Analyze position (x,y)")
    print(f"- {Fore.YELLOW}board{Style.RESET_ALL}: Redisplay the board without path")
    print(f"- {Fore.YELLOW}help{Style.RESET_ALL}: Show this help message")
    print(f"- {Fore.YELLOW}exit{Style.RESET_ALL}: Quit the program")
    
    print(f"\n{Fore.CYAN}=== Examples ==={Style.RESET_ALL}")
    print(f"- {Fore.YELLOW}find 0,0 14,9{Style.RESET_ALL}")
    print(f"- {Fore.YELLOW}analyze 5,5{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}=== How It Works ==={Style.RESET_ALL}")
    print("- Movement is restricted to the four cardinal directions (up, down, left, right)")
    print("- Diagonal movement is not allowed")
    print("- Green 'S' marks the start position")
    print("- Red 'E' marks the end position")
    print("- Magenta numbers show the path sequence")
    print("- Blue 'J' represents jumpable objects")
    print("- Red 'X' represents immovable obstacles")
    print(f"{Fore.CYAN}==========================={Style.RESET_ALL}\n")

async def run_pathfinding_cli():
    """Run the CLI for testing the pathfinding algorithm."""
    # Set up the test board
    board = await setup_test_board()
    
    # Print initial board
    print_board(board)
    
    print(f"\n{Fore.CYAN}Welcome to the Pathfinding Test CLI!{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Movement is restricted to the four cardinal directions (up, down, left, right).{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Type 'help' for available commands or 'exit' to quit.{Style.RESET_ALL}")
    
    while True:
        try:
            # Get user input
            user_input = input(f"\n{Fore.YELLOW}Command: {Style.RESET_ALL}")
            user_input = user_input.strip().lower()
            
            # Handle commands
            if user_input == 'exit':
                print(f"\n{Fore.CYAN}Exiting Pathfinding CLI.{Style.RESET_ALL}")
                break
                
            elif user_input == 'help':
                print_help()
                continue
                
            elif user_input == 'board':
                print_board(board)
                continue
                
            elif user_input.startswith('find'):
                # Extract coordinates from input
                coords_pattern = r'find\s+(\d+)\s*,\s*(\d+)\s+(\d+)\s*,\s*(\d+)'
                match = re.match(coords_pattern, user_input)
                
                if not match:
                    print(f"{Fore.RED}Invalid format. Use: find x1,y1 x2,y2{Style.RESET_ALL}")
                    continue
                
                start_x, start_y, end_x, end_y = map(int, match.groups())
                start_pos = (start_x, start_y)
                end_pos = (end_x, end_y)
                
                # Validate positions
                if not board.is_valid_position(start_pos):
                    print(f"{Fore.RED}Invalid starting position: {start_pos}{Style.RESET_ALL}")
                    continue
                
                if not board.is_valid_position(end_pos):
                    print(f"{Fore.RED}Invalid ending position: {end_pos}{Style.RESET_ALL}")
                    continue
                
                print(f"\n{Fore.CYAN}Finding path from {start_pos} to {end_pos}...{Style.RESET_ALL}")
                
                # Execute pathfinding directly
                result = find_path(board, start_x, start_y, end_x, end_y)
                
                # Extract result
                print(f"\n{Fore.GREEN}Result: {result['message']}{Style.RESET_ALL}")
                
                # Display the path on the board
                path = result["path"]
                print_board(board, path, start_pos, end_pos)
                
                # Display path details
                if path:
                    print(f"{Fore.CYAN}Path found with {len(path)-1} steps:{Style.RESET_ALL}")
                    for i, pos in enumerate(path):
                        print(f"{i}: {pos}")
                    
                    jumps = result.get("jumps", [])
                    if jumps:
                        print(f"\n{Fore.CYAN}Path includes {len(jumps)} jumps:{Style.RESET_ALL}")
                        for i, jump_desc in enumerate(jumps):
                            print(f"Jump {i+1}: {jump_desc}")
                else:
                    print(f"{Fore.RED}No path found between {start_pos} and {end_pos}{Style.RESET_ALL}")
            
            elif user_input.startswith('analyze'):
                # Extract coordinates from input
                coords_pattern = r'analyze\s+(\d+)\s*,\s*(\d+)'
                match = re.match(coords_pattern, user_input)
                
                if not match:
                    print(f"{Fore.RED}Invalid format. Use: analyze x,y{Style.RESET_ALL}")
                    continue
                
                x, y = map(int, match.groups())
                position = (x, y)
                
                # Validate position
                if not board.is_valid_position(position):
                    print(f"{Fore.RED}Invalid position: {position}{Style.RESET_ALL}")
                    continue
                
                print(f"\n{Fore.CYAN}Analyzing position {position}...{Style.RESET_ALL}")
                
                # Execute position analysis directly
                result = analyze_position(board, x, y)
                
                # Display the result
                print(f"\n{Fore.GREEN}Position {position} analysis:{Style.RESET_ALL}")
                
                if result["success"]:
                    print(f"Valid position: {result['is_valid']}")
                    print(f"Can move to: {result['can_move_to']}")
                    
                    if result["object"]:
                        obj = result["object"]
                        print(f"\nObject found: {obj['name']} (ID: {obj['id']})")
                        print(f"Movable: {obj['is_movable']}")
                        print(f"Jumpable: {obj['is_jumpable']}")
                        
                        if "description" in obj:
                            print(f"Description: {obj['description']}")
                    else:
                        print("\nNo object at this position")
                else:
                    print(f"{Fore.RED}{result['message']}{Style.RESET_ALL}")
                
                # Highlight the analyzed position on the board
                print_board(board, None, position, None)
                
            else:
                print(f"{Fore.RED}Unknown command. Type 'help' for available commands.{Style.RESET_ALL}")
                
        except Exception as e:
            print(f"\n{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")

async def main():
    """Main entry point for the PathFinding CLI."""
    print(f"\n{Fore.CYAN}=== Pathfinding Test CLI ===={Style.RESET_ALL}")
    print(f"Initializing test board...")
    
    await run_pathfinding_cli()

if __name__ == "__main__":
    asyncio.run(main()) 