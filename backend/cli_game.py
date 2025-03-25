import asyncio
import os

from agents import Runner, trace
from colorama import init, Fore, Style

from agent_puppet_master import GameState, create_puppet_master
from board import Board  # Import the model's Board class
from game_object import Container, GameObject
from person import Person

# Initialize colorama for cross-platform colored terminal output
init()

def print_board(board: Board, game_state: GameState):
    """Print a visual representation of the game board.
    
    Args:
        board: The game board instance
        game_state: The current game state containing the player and board state
    """
    # Clear screen
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Print header
    print(f"\n{Fore.CYAN}=== Game Board ({board.width}x{board.height}) ===\n{Style.RESET_ALL}")
    
    # Print coordinates header - handle double digits
    print("   ", end="")  # Extra space for alignment
    for x in range(board.width):
        print(f"{x:2}", end="")
    print("\n  ", end="")  # Two spaces for alignment
    print("-" * (board.width * 2 + 2))  # Adjust border width
    
    # Get current board state
    board_map = {}
    legend = {}
    
    # Get player from game state
    player = game_state.person
    if player and player.position:
        board_map[player.position] = {
            "symbol": "P",
            "color": Fore.GREEN,
            "name": player.name,
            "priority": 0  # Player has highest display priority
        }
        legend["P"] = f"{Fore.GREEN}Player ({player.name}){Style.RESET_ALL}"
    
    # Add other entities to board_map
    for position in board._position_map:
        entities = board.get_entities_at(position)
        for entity in entities:
            # Skip the player as we've already added them
            if entity == player:
                continue
                
            # Only show the highest priority entity at each position
            if position in board_map and board_map[position]["priority"] <= 1:
                continue
                
            if isinstance(entity, Container):
                symbol = "C"
                color = Fore.YELLOW
                priority = 1
                legend[symbol] = f"{color}Container{Style.RESET_ALL}"
            elif isinstance(entity, GameObject):
                if entity.is_movable:
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
        print(f"{y:2}|", end="")  # Two digits for row numbers
        for x in range(board.width):
            pos = (x, y)
            if pos in board_map:
                entity_info = board_map[pos]
                print(f"{entity_info['color']}{entity_info['symbol']}{Style.RESET_ALL} ", end="")
            else:
                print(". ", end="")
        print("|")
    
    # Print bottom border
    print("  ", end="")  # Two spaces for alignment
    print("-" * (board.width * 2 + 2))  # Adjust border width
    
    # Print legend
    print(f"\n{Fore.CYAN}=== Legend ==={Style.RESET_ALL}")
    for symbol, description in legend.items():
        print(f"{symbol}: {description}")
    print(f".: Empty space\n")
    
    # Print player's current position from game state
    if player and player.position:
        x, y = player.position
        print(f"{Fore.GREEN}Your position: ({x}, {y}){Style.RESET_ALL}\n")
    
    print(f"{Fore.CYAN}==========================={Style.RESET_ALL}\n")

async def run_game_with_board_display(game_state):
    """Run the game with a visual board display after each interaction.
    
    Args:
        game_state: The game state containing the board, player, and other game information
    """
    agent = create_puppet_master(game_state.person.name)
    
    # Thread ID for tracing
    thread_id = f"game-conversation-{game_state.person.id}"
    
    # Initial sync of game state
    game_state.sync_game_state()
    
    # Print initial board
    print_board(game_state.game_board, game_state)
    
    print(f"\n{Fore.CYAN}{game_state.person.name} is ready to act in the game world.{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Type 'exit' to quit or 'help' for available commands.{Style.RESET_ALL}")
    
    # Initialize conversation history
    conversation_history = []
    
    # Make the agent look around first to initialize its knowledge of surroundings
    print(f"\n{Fore.CYAN}Looking around to understand the surroundings...{Style.RESET_ALL}")
    with trace(workflow_name="GameCharacterConversation", group_id=thread_id):
        result = await Runner.run(
            starting_agent=agent,
            input="look around",
            context=game_state,
        )
    print(f"\n{Fore.GREEN}{game_state.person.name}: {result.final_output}{Style.RESET_ALL}")
    
    # Sync and display board after looking around
    game_state.sync_game_state()
    print_board(game_state.game_board, game_state)
    
    while True:
        try:
            # Get user input
            user_input = input(f"\n{Fore.YELLOW}You: {Style.RESET_ALL}")
            
            # Check for exit command
            if user_input.lower() == 'exit':
                print(f"\n{Fore.CYAN}Game session ended.{Style.RESET_ALL}")
                break
            
            # Help command
            if user_input.lower() == 'help':
                print_help()
                continue
                
            # Show board command
            if user_input.lower() == 'board':
                game_state.sync_game_state()
                print_board(game_state.game_board, game_state)
                continue
            
            # Add user message to conversation history
            if not conversation_history:
                # First message - just use the text input
                input_for_agent = user_input
            else:
                # Add the new user message to existing conversation
                conversation_history.append({"role": "user", "content": user_input})
                input_for_agent = conversation_history
            
            # Run agent with conversation history
            print(f"\n{Fore.CYAN}Thinking...{Style.RESET_ALL}")
            
            with trace(workflow_name="GameCharacterConversation", group_id=thread_id):
                result = await Runner.run(
                    starting_agent=agent,
                    input=input_for_agent,
                    context=game_state,
                )
            
            # Display the response and update board if position changed
            print(f"\n{Fore.GREEN}{game_state.person.name}: {result.final_output}{Style.RESET_ALL}")
            
            # Sync game state and refresh the board to capture any state changes
            game_state.sync_game_state()
            print_board(game_state.game_board, game_state)
            
            # Update conversation history with agent's response
            if not conversation_history:
                # Initialize history with the first exchange
                conversation_history = result.to_input_list()
            else:
                # Update existing history with agent's response
                conversation_history.append({"role": "assistant", "content": result.final_output})
                
        except Exception as e:
            print(f"\n{Fore.RED}Error during conversation: {str(e)}{Style.RESET_ALL}")
            
def print_help():
    """Print available commands and game information."""
    print(f"\n{Fore.CYAN}=== Available Commands ==={Style.RESET_ALL}")
    print(f"- {Fore.YELLOW}exit{Style.RESET_ALL}: Quit the game")
    print(f"- {Fore.YELLOW}help{Style.RESET_ALL}: Show this help message")
    print(f"- {Fore.YELLOW}board{Style.RESET_ALL}: Redisplay the game board")
    
    print(f"\n{Fore.CYAN}=== How to Play ==={Style.RESET_ALL}")
    print("Talk to the agent using natural language. Examples:")
    print(f"- {Fore.YELLOW}look around{Style.RESET_ALL} - See what's nearby")
    print(f"- {Fore.YELLOW}move to 6,5{Style.RESET_ALL} - Move to coordinates (6,5)")
    print(f"- {Fore.YELLOW}push the box{Style.RESET_ALL} - Push an object")
    print(f"- {Fore.YELLOW}check my inventory{Style.RESET_ALL} - See what you're carrying")
    print(f"- {Fore.YELLOW}examine the chest{Style.RESET_ALL} - Get details about an object")
    print(f"- {Fore.YELLOW}get the key from the chest{Style.RESET_ALL} - Interact with containers")
    print(f"- {Fore.YELLOW}jump over the box{Style.RESET_ALL} - Jump over obstacles")
    
    print(f"\n{Fore.CYAN}=== Game Tips ==={Style.RESET_ALL}")
    print("- Objects have properties like weight, movability, etc.")
    print("- You can only move to adjacent empty spaces")
    print("- Some objects can be used with others")
    print("- Always look around first to understand your environment")
    print(f"{Fore.CYAN}==========================={Style.RESET_ALL}\n")

async def setup_game_world():
    """Set up the initial game world with a board, player, and objects."""
    # Create game board
    board = Board(width=15, height=10)  # Use the model's Board class
    
    # Create player
    player = Person(id="player1", name="Alex", strength=10)
    board.add_entity(player, (9, 0))  # Start at top-right corner
    
    # Create objects
    table = GameObject(id="table1", name="Table", description="A wooden table", is_movable=False)
    board.add_entity(table, (4, 4))
    
    chair = GameObject(id="chair1", name="Chair", description="A wooden chair", is_movable=True, weight=2)
    board.add_entity(chair, (4, 5))
    
    bookshelf = Container(id="bookshelf1", name="Bookshelf", description="A tall bookshelf filled with books", is_movable=False, capacity=10)
    board.add_entity(bookshelf, (8, 3))
    
    # Create containers
    chest = Container(id="chest1", name="Treasure Chest", description="A mysterious chest", is_open=True)
    board.add_entity(chest, (7, 7))
    
    backpack = Container(id="backpack1", name="Backpack", description="A leather backpack", is_open=True, capacity=5)
    board.add_entity(backpack, (3, 7))
    
    # Add items to containers
    key = GameObject(id="key1", name="Rusty Key", description="An old rusty key", is_movable=True, weight=1)
    chest.add_item(key)
    
    book = GameObject(id="book1", name="Ancient Book", description="A dusty, leather-bound book", is_movable=True, weight=1)
    bookshelf.add_item(book)
    
    apple = GameObject(id="apple1", name="Red Apple", description="A fresh red apple", is_movable=True, weight=1)
    backpack.add_item(apple)
    
    # Add items to player's inventory
    sword = GameObject(id="sword1", name="Iron Sword", description="A sharp iron sword", is_movable=True, weight=2)
    player.inventory.add_item(sword)
    
    # Create game state context
    game_state = GameState()
    game_state.game_board = board
    game_state.person = player
    
    return game_state

async def main():
    """Main entry point for the game."""
    print(f"\n{Fore.CYAN}=== Welcome to the Adventure Game ===={Style.RESET_ALL}")
    print(f"Initializing game world...")
    
    # Set up the game world
    game_state = await setup_game_world()
    
    # Run the game
    await run_game_with_board_display(game_state)

if __name__ == "__main__":
    asyncio.run(main()) 