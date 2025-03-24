import os
import shlex
import sys
from typing import List, Tuple

from colorama import init, Fore, Style

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import model
from model import Person, Container, GameObject, Position

# Initialize colorama for cross-platform colored terminal output
init()

class GameBoard:
    def __init__(self, width=15, height=10):
        self.entities = {}
        self.size = (width, height)
    
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
    
    def move_entity(self, entity, position):
        if entity.id in self.entities:
            entity.set_position(position)
        else:
            self.add_entity(entity)
            entity.set_position(position)
    
    def add_entity(self, entity):
        self.entities[entity.id] = entity
    
    def get_object_at(self, position):
        for entity in self.entities.values():
            if entity.position == position:
                return entity
        return None
    
    def get_entities_at(self, position):
        return [entity for entity in self.entities.values() if entity.position == position]
    
    def print_board(self, player):
        """Print a visual representation of the game board."""
        # Print header
        print(f"\n{Fore.CYAN}=== Game Board ({self.size[0]}x{self.size[1]}) ===\n{Style.RESET_ALL}")
        
        # Print coordinates header
        print(f"  ", end="")
        for x in range(self.size[0]):
            print(f"{x:2}", end="")
        print("\n  ", end="")
        for x in range(self.size[0]):
            print("--", end="")
        print()
        
        # Categorize entities for display priority
        board_map = {}
        legend = {}
        
        # Add player to board_map with highest priority
        if player.position:
            board_map[player.position] = {
                "symbol": "P",
                "color": Fore.GREEN,
                "name": player.name
            }
            legend["P"] = f"{Fore.GREEN}Player ({player.name}){Style.RESET_ALL}"
        
        # Add other entities to board_map
        for entity_id, entity in self.entities.items():
            if entity.position and entity != player:
                if isinstance(entity, Container):
                    symbol = "C"
                    color = Fore.YELLOW
                    legend[symbol] = f"{color}Container{Style.RESET_ALL}"
                elif hasattr(entity, 'is_movable') and entity.is_movable:
                    symbol = "O"
                    color = Fore.BLUE
                    legend[symbol] = f"{color}Movable Object{Style.RESET_ALL}"
                else:
                    symbol = "X"
                    color = Fore.RED
                    legend[symbol] = f"{color}Immovable Object{Style.RESET_ALL}"
                
                board_map[entity.position] = {
                    "symbol": symbol,
                    "color": color,
                    "name": entity.name
                }
        
        # Print the board
        for y in range(self.size[1]):
            print(f"{y:2}|", end="")
            for x in range(self.size[0]):
                pos = (x, y)
                if pos in board_map:
                    entity_info = board_map[pos]
                    print(f"{entity_info['color']}{entity_info['symbol']}{Style.RESET_ALL} ", end="")
                else:
                    print(". ", end="")
            print("|")
        
        # Print bottom border
        print("  ", end="")
        for x in range(self.size[0]):
            print("--", end="")
        print()
        
        # Print legend
        print(f"\n{Fore.CYAN}=== Legend ==={Style.RESET_ALL}")
        for symbol, description in legend.items():
            print(f"{symbol}: {description}")
        print(f".: Empty space\n")
        
        # Print player's current position
        if player.position:
            x, y = player.position
            print(f"{Fore.GREEN}Your position: ({x}, {y}){Style.RESET_ALL}\n")
        
        print(f"{Fore.CYAN}==========================={Style.RESET_ALL}\n")

class GameState:
    def __init__(self):
        self.game_board = None
        self.person = None
        self.nearby_objects = {}
        self.containers = {}

def parse_command(command_str: str) -> Tuple[str, List[str]]:
    """Parse a command string into a command and arguments."""
    parts = shlex.split(command_str.lower())
    if not parts:
        return "", []
    
    command = parts[0]
    args = parts[1:] if len(parts) > 1 else []
    
    return command, args

def run_game_with_direct_commands():
    """Run a simple command-line based game where the user directly inputs commands."""
    # Create the game world
    game_state = setup_game_world()
    
    # Print initial board
    game_state.game_board.print_board(game_state.person)
    
    print(f"\n{Fore.CYAN}{game_state.person.name} is ready for your commands.{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Type 'help' for available commands or 'exit' to quit.{Style.RESET_ALL}")
    
    while True:
        try:
            # Get user input with a more visible prompt
            print(f"\n{Fore.YELLOW}> {Style.RESET_ALL}", end="", flush=True)
            user_input = input().strip()
            
            print(f"Debug: Received input: '{user_input}'")  # Debug print
            
            if not user_input:
                continue
                
            # Check for exit command
            if user_input.lower() == 'exit':
                print(f"\n{Fore.CYAN}Game session ended.{Style.RESET_ALL}")
                break
            
            # Process the command
            command, args = parse_command(user_input)
            print(f"Debug: Parsed command: '{command}', args: {args}")  # Debug print
            
            # Process command
            message = process_command(command, args, game_state)
            print(f"\n{Fore.GREEN}{message}{Style.RESET_ALL}")
            
            # Update the board after each command
            game_state.game_board.print_board(game_state.person)
            
        except Exception as e:
            print(f"\n{Fore.RED}Error occurred: {str(e)}{Style.RESET_ALL}")
            continue

def process_command(command: str, args: List[str], game_state: GameState) -> str:
    """Process a game command and return a message."""
    person = game_state.person
    board = game_state.game_board
    
    # Basic commands
    if command == "help":
        return print_help_and_return()
        
    elif command == "look":
        direction = None
        if len(args) >= 2:
            try:
                dir_x = int(args[0])
                dir_y = int(args[1])
                direction = (dir_x, dir_y)
            except ValueError:
                pass
                
        result = person.look(board, direction)
        
        # Update nearby objects for future commands
        if result["success"]:
            game_state.nearby_objects = {obj.id: obj for obj in result.get("objects", [])}
            
            # Update containers
            for obj_id, obj in game_state.nearby_objects.items():
                if isinstance(obj, Container):
                    game_state.containers[obj_id] = obj
        
        # Format a descriptive response
        if result["success"]:
            objects = result.get("objects", [])
            if not objects:
                return "You look around but don't see anything interesting."
            
            descriptions = []
            for obj in objects:
                pos_str = f"at ({obj.position[0]}, {obj.position[1]})" if obj.position else ""
                descriptions.append(f"- {obj.name} {pos_str}")
            
            return f"You see:\n" + "\n".join(descriptions)
        else:
            return result["message"]
    
    elif command == "move":
        if len(args) >= 2:
            try:
                target_x = int(args[0])
                target_y = int(args[1])
                is_running = "run" in args or "running" in args
                
                result = person.move(board, (target_x, target_y), is_running)
                return result["message"]
            except ValueError:
                return "Invalid position format. Use 'move x y' with numbers."
        else:
            return "Not enough arguments. Use 'move x y'."
    
    elif command == "jump":
        if len(args) >= 2:
            try:
                target_x = int(args[0])
                target_y = int(args[1])
                
                result = person.jump(board, (target_x, target_y))
                return result["message"]
            except ValueError:
                return "Invalid position format. Use 'jump x y' with numbers."
        else:
            return "Not enough arguments. Use 'jump x y'."
    
    elif command == "push":
        if len(args) >= 4:
            try:
                obj_x = int(args[0])
                obj_y = int(args[1])
                dir_x = int(args[2])
                dir_y = int(args[3])
                
                result = person.push(board, (obj_x, obj_y), (dir_x, dir_y))
                return result["message"]
            except ValueError:
                return "Invalid format. Use 'push obj_x obj_y dir_x dir_y' with numbers."
        else:
            return "Not enough arguments. Use 'push obj_x obj_y dir_x dir_y'."
    
    elif command == "pull":
        if len(args) >= 2:
            try:
                obj_x = int(args[0])
                obj_y = int(args[1])
                
                result = person.pull(board, (obj_x, obj_y))
                return result["message"]
            except ValueError:
                return "Invalid format. Use 'pull obj_x obj_y' with numbers."
        else:
            return "Not enough arguments. Use 'pull obj_x obj_y'."
    
    elif command == "inventory" or command == "inv":
        if not person.inventory or not person.inventory.contents:
            return f"{person.name}'s inventory is empty"
        
        items = person.inventory.contents
        item_descriptions = [f"- {item.id}: {item.name}" for item in items]
        
        return f"{person.name}'s inventory contains:\n" + "\n".join(item_descriptions)
    
    elif command == "get":
        if len(args) >= 2:
            container_id = args[0]
            item_id = args[1]
            
            if container_id in game_state.containers:
                container = game_state.containers[container_id]
                result = person.get_from_container(container, item_id)
                return result["message"]
            else:
                return f"Container {container_id} not found nearby"
        else:
            return "Not enough arguments. Use 'get container_id item_id'."
    
    elif command == "put":
        if len(args) >= 2:
            item_id = args[0]
            container_id = args[1]
            
            if container_id in game_state.containers:
                container = game_state.containers[container_id]
                result = person.put_in_container(item_id, container)
                return result["message"]
            else:
                return f"Container {container_id} not found nearby"
        else:
            return "Not enough arguments. Use 'put item_id container_id'."
    
    elif command == "use":
        if len(args) >= 2:
            item1_id = args[0]
            item2_id = args[1]
            
            result = person.use_object_with(item1_id, item2_id)
            return result["message"]
        else:
            return "Not enough arguments. Use 'use item1_id item2_id'."
    
    elif command == "examine" or command == "x":
        if len(args) >= 1:
            object_id = args[0]
            
            # Check in nearby objects
            if object_id in game_state.nearby_objects:
                obj = game_state.nearby_objects[object_id]
                info = [
                    f"Name: {obj.name}",
                    f"Position: {obj.position}",
                    f"Description: {obj.description}"
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
            for item in person.inventory.contents:
                if item.id == object_id:
                    info = [
                        f"Name: {item.name}",
                        f"Description: {item.description}"
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
        else:
            return "Not enough arguments. Use 'examine object_id'."
            
    elif command == "say":
        if args:
            message = " ".join(args)
            result = person.say(message)
            return result["message"]
        else:
            return "What do you want to say? Use 'say message'."
    
    else:
        return f"Unknown command: {command}. Type 'help' to see available commands."

def print_help_and_return() -> str:
    """Print help information and return it as a string."""
    help_text = [
        f"{Fore.CYAN}=== Available Commands ==={Style.RESET_ALL}",
        f"- {Fore.YELLOW}look [x y]{Style.RESET_ALL}: Look around or in specific direction",
        f"- {Fore.YELLOW}move x y [run]{Style.RESET_ALL}: Move to coordinates (x,y), add 'run' to run",
        f"- {Fore.YELLOW}jump x y{Style.RESET_ALL}: Jump to coordinates (x,y)",
        f"- {Fore.YELLOW}push obj_x obj_y dir_x dir_y{Style.RESET_ALL}: Push object at (obj_x,obj_y) in direction (dir_x,dir_y)",
        f"- {Fore.YELLOW}pull obj_x obj_y{Style.RESET_ALL}: Pull object at (obj_x,obj_y)",
        f"- {Fore.YELLOW}inventory (or inv){Style.RESET_ALL}: Show your inventory",
        f"- {Fore.YELLOW}get container_id item_id{Style.RESET_ALL}: Get item from container",
        f"- {Fore.YELLOW}put item_id container_id{Style.RESET_ALL}: Put item in container",
        f"- {Fore.YELLOW}use item1_id item2_id{Style.RESET_ALL}: Use items together",
        f"- {Fore.YELLOW}examine (or x) object_id{Style.RESET_ALL}: Examine an object",
        f"- {Fore.YELLOW}say message{Style.RESET_ALL}: Say something",
        f"- {Fore.YELLOW}help{Style.RESET_ALL}: Show this help",
        f"- {Fore.YELLOW}exit{Style.RESET_ALL}: Exit the game",
        "",
        f"{Fore.CYAN}=== Game Tips ==={Style.RESET_ALL}",
        "- Always look around first to find objects",
        "- Object IDs are used for interaction commands",
        "- You can only move to adjacent empty spaces",
        "- To push or pull, you must be adjacent to the object",
        "- To jump, you need a jumpable object to jump over"
    ]
    
    return "\n".join(help_text)

def setup_game_world() -> GameState:
    """Set up the game world with objects and return the game state."""
    # Create game objects
    board = GameBoard(width=15, height=10)
    
    # Create a player
    player = Person(id="player1", name="Alex", strength=10)
    board.move_entity(player, (5, 5))
    
    # Create some objects
    box = GameObject(id="box1", name="Wooden Box", description="A sturdy wooden box", is_movable=True, is_jumpable=True, weight=3)
    board.move_entity(box, (6, 5))
    
    table = GameObject(id="table1", name="Table", description="A wooden table", is_movable=False)
    board.move_entity(table, (4, 4))
    
    chair = GameObject(id="chair1", name="Chair", description="A wooden chair", is_movable=True, weight=2)
    board.move_entity(chair, (4, 5))
    
    bookshelf = Container(id="bookshelf1", name="Bookshelf", description="A tall bookshelf filled with books", is_movable=False, capacity=10)
    board.move_entity(bookshelf, (8, 3))
    
    # Create containers
    chest = Container(id="chest1", name="Treasure Chest", description="A mysterious chest", is_open=True)
    board.move_entity(chest, (7, 7))
    
    backpack = Container(id="backpack1", name="Backpack", description="A leather backpack", is_open=True, capacity=5)
    board.move_entity(backpack, (3, 7))
    
    # Add items to containers
    key = GameObject(id="key1", name="Rusty Key", description="An old rusty key", is_movable=True, weight=1)
    chest.add_item(key)
    
    book = GameObject(id="book1", name="Ancient Book", description="A dusty, leather-bound book", is_movable=True, weight=1)
    bookshelf.add_item(book)  # Let's pretend bookshelves can hold items too
    
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

def main():
    """Main entry point for the game."""
    try:
        print(f"\n{Fore.CYAN}=== Welcome to the Adventure Game ===={Style.RESET_ALL}")
        print(f"Initializing game world...")
        
        # Run the game
        run_game_with_direct_commands()
    except Exception as e:
        print(f"\n{Fore.RED}Fatal error: {str(e)}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 