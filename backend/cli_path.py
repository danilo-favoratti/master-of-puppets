import asyncio
import re
from typing import Dict, Any

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from colorama import init, Fore, Style
from board import Board  # Import the model's Board class
from game_object import Container, GameObject
from person import Person
from agent_path_researcher import find_path
from agent_puppet_master import create_puppet_master, GameState
from agents import Runner, trace

# Initialize colorama for cross-platform colored terminal output
init()

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
    
    # Find player position first (highest priority)
    player_pos = None
    for position in board._position_map:
        entities = board.get_entities_at(position)
        for entity in entities:
            if isinstance(entity, Person):
                player_pos = position
                board_map[position] = {
                    "symbol": "P",
                    "color": Fore.CYAN,
                    "name": entity.name,
                    "priority": -1  # Higher than start/end positions
                }
                legend["P"] = f"{Fore.CYAN}Player{Style.RESET_ALL}"
                break
        if player_pos:
            break
    
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
            "priority": 0  # High priority, but not as high as player
        }
        legend["S"] = f"{Fore.GREEN}Start position{Style.RESET_ALL}"
        
    if end_pos:
        board_map[end_pos] = {
            "symbol": "E",
            "color": Fore.RED,
            "name": "End position",
            "priority": 0  # High priority, but not as high as player
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
    print(f"- {Fore.YELLOW}Natural language commands{Style.RESET_ALL}:")
    print(f"  * 'Find a path from (0,0) to (14,9)'")
    print(f"  * 'What's at position (5,5)?'")
    print(f"  * 'Can I jump over the rock at (2,5)?'")
    print(f"  * 'How do I get to the chest?'")
    print(f"- {Fore.YELLOW}board{Style.RESET_ALL}: Redisplay the board without path")
    print(f"- {Fore.YELLOW}help{Style.RESET_ALL}: Show this help message")
    print(f"- {Fore.YELLOW}exit{Style.RESET_ALL}: Quit the program")
    
    print(f"\n{Fore.CYAN}=== How It Works ==={Style.RESET_ALL}")
    print("- Use natural language to describe what you want to do")
    print("- The agent will understand your intent and find appropriate paths")
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
    
    # Create a player for the agent
    player = Person(id="player1", name="Pathfinder", strength=10)
    board.move_entity(player, (0, 0))  # Start at top-left
    
    # Create game state for agent
    game_state = GameState()
    game_state.game_board = board
    game_state.person = player
    
    # Create the agent
    agent = create_puppet_master(complete_story_result, "Pathfinder")
    
    # Print initial board
    print_board(board)
    
    print(f"\n{Fore.CYAN}Welcome to the Natural Language Pathfinding CLI!{Style.RESET_ALL}")
    print(f"{Fore.GREEN}You can now use natural language to find paths and analyze positions.{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Type 'help' for available commands or 'exit' to quit.{Style.RESET_ALL}")
    
    # Initialize conversation history
    conversation_history = []
    
    # Custom trace handler to print tool calls
    def print_tool_call(tool_name: str, parameters: Dict[str, Any]) -> None:
        print(f"\n{Fore.YELLOW}Tool Call:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Tool:{Style.RESET_ALL} {tool_name}")
        print(f"{Fore.CYAN}Parameters:{Style.RESET_ALL}")
        for param, value in parameters.items():
            print(f"  - {param}: {value}")
        print()
    
    # Override the trace function to print tool calls
    original_trace = trace
    def custom_trace(*args, **kwargs):
        trace_context = original_trace(*args, **kwargs)
        
        # Store the original __enter__ method
        original_enter = trace_context.__enter__
        
        def custom_enter():
            result = original_enter()
            # Add our tool call printing functionality
            def custom_tool_call(self, tool_name, parameters):
                print_tool_call(tool_name, parameters)
                return self.original_tool_call(tool_name, parameters)
            
            # Store the original tool call method
            result.original_tool_call = result.tool_call
            # Replace with our custom method
            result.tool_call = custom_tool_call.__get__(result)
            return result
        
        trace_context.__enter__ = custom_enter
        return trace_context
    
    while True:
        try:
            # Get user input
            user_input = input(f"\n{Fore.YELLOW}You: {Style.RESET_ALL}")
            user_input = user_input.strip()
            
            # Handle special commands
            if user_input.lower() == 'exit':
                print(f"\n{Fore.CYAN}Exiting Pathfinding CLI.{Style.RESET_ALL}")
                break
                
            elif user_input.lower() == 'help':
                print_help()
                continue
                
            elif user_input.lower() == 'board':
                print_board(board)
                continue
            
            # Process natural language input through agent
            print(f"\n{Fore.CYAN}Thinking...{Style.RESET_ALL}")
            
            # Add user message to conversation history
            if not conversation_history:
                input_for_agent = user_input
            else:
                conversation_history.append({"role": "user", "content": user_input})
                input_for_agent = conversation_history
            
            # Run agent with conversation history using custom trace
            with custom_trace(workflow_name="PathfindingConversation", group_id="pathfinding-cli"):
                result = await Runner.run(
                    starting_agent=agent,
                    input=input_for_agent,
                    context=game_state,
                )
            
            # Display the response
            print(f"\n{Fore.GREEN}Pathfinder: {result.final_output}{Style.RESET_ALL}")
            
            # Update conversation history with agent's response
            if not conversation_history:
                conversation_history = result.to_input_list()
            else:
                conversation_history.append({"role": "assistant", "content": result.final_output})
            
            # Variables for path display
            path = None
            start_pos = None
            end_pos = None
            
            # Check if response contains path information
            if "path" in result.final_output.lower():
                # Try to find path coordinates in the response
                coords_pattern = r'\((\d+),\s*(\d+)\)'
                coords = re.findall(coords_pattern, result.final_output)
                
                if len(coords) >= 2:
                    start_pos = tuple(map(int, coords[0]))
                    end_pos = tuple(map(int, coords[-1]))
                    
                    # Print the find_path tool call
                    print_tool_call("find_path", {
                        "start_pos": start_pos,
                        "end_pos": end_pos,
                        "board": "current_board"
                    })
                    
                    # Find the path using the pathfinding algorithm
                    path_result = find_path(board, start_pos[0], start_pos[1], end_pos[0], end_pos[1])
                    if path_result["success"]:
                        path = path_result["path"]
            
            # Always update board display after each interaction
            print_board(board, path, start_pos, end_pos)
                
        except Exception as e:
            print(f"\n{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")

async def main():
    """Main entry point for the PathFinding CLI."""
    print(f"\n{Fore.CYAN}=== Pathfinding Test CLI ===={Style.RESET_ALL}")
    print(f"Initializing test board...")
    
    await run_pathfinding_cli()

if __name__ == "__main__":
    asyncio.run(main()) 