import asyncio
from typing import Optional, Tuple, Dict, Any

from agents import (
    Agent,
    Runner,
    function_tool,
    RunContextWrapper,
    trace
)

from person import Person
from game_object import Container


class DirectionHelper:
    """Helper class for handling relative directions."""
    @staticmethod
    def get_relative_position(current_pos: Tuple[int, int], direction: str) -> Tuple[int, int]:
        """Convert a relative direction to target coordinates."""
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
        """Get the direction vector between two positions."""
        fx, fy = from_pos
        tx, ty = to_pos
        return (tx - fx, ty - fy)

    @staticmethod
    def get_direction_name(direction: Tuple[int, int]) -> str:
        """Convert a direction vector to a name."""
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
    async def move_continuously(game_state: 'GameState', direction: str) -> str:
        """Move continuously in a direction until blocked or at board edge."""
        moves = 0
        last_message = ""
        max_moves = 50  # Maximum number of moves to prevent infinite loops
        
        while moves < max_moves:
            current_pos = game_state.person.position
            target_pos = DirectionHelper.get_relative_position(current_pos, direction)
            
            # Try to move
            result = game_state.person.move(game_state.game_board, target_pos, False)
            
            # If move failed, we're done
            if not result["success"]:
                if moves == 0:
                    return result["message"]
                else:
                    return f"Moved {moves} steps {direction} and stopped: {result['message']}"
            
            # Update state and continue
            game_state.sync_game_state()
            moves += 1
            last_message = result["message"]
            
            # Check if we've reached a boundary or obstacle
            next_pos = DirectionHelper.get_relative_position(target_pos, direction)
            if not game_state.game_board.is_valid_position(next_pos) or not game_state.game_board.can_move_to(next_pos):
                return f"Moved {moves} steps {direction} and reached {'the board edge' if not game_state.game_board.is_valid_position(next_pos) else 'an obstacle'}"
        
        # If we hit the move limit, return how far we got
        return f"Moved {moves} steps {direction} and stopped at the maximum move limit."

# Type for game state context
class GameState:
    game_board: Any  # The game board
    person: Person  # Current person being controlled
    nearby_objects: Dict[str, Any] = {}  # Objects the person can interact with
    containers: Dict[str, Container] = {}  # Accessible containers
    
    def sync_game_state(self):
        """Synchronize the game state after any action."""
        if not self.person or not self.game_board:
            return
            
        # Get all objects in visible range
        result = self.person.look(self.game_board)
        if result["success"]:
            # Update nearby objects
            self.nearby_objects = {obj.id: obj for obj in result.get("objects", [])}
            
            # Update containers
            self.containers = {
                obj_id: obj 
                for obj_id, obj in self.nearby_objects.items() 
                if isinstance(obj, Container)
            }
            
        return result.get("message", "")

# Tool definitions - wrapping Person class actions
@function_tool
async def move(
    ctx: RunContextWrapper[GameState], 
    direction: str,
    is_running: bool,
    continuous: bool
) -> str:
    """Move the person in a specified direction.
    
    Args:
        direction: The direction to move ("left", "right", "up", "down")
        is_running: Whether to run (move up to 2 tiles) or walk (move 1 tile)
        continuous: Whether to keep moving until blocked or at board edge
    """
    game_state = ctx.context
    
    # Handle continuous movement
    if continuous:
        return await DirectionHelper.move_continuously(game_state, direction)
    
    # Regular single-step movement
    current_pos = game_state.person.position
    target_pos = DirectionHelper.get_relative_position(current_pos, direction)
    
    result = game_state.person.move(
        game_state.game_board, 
        target_pos, 
        is_running
    )
    
    if result["success"]:
        game_state.sync_game_state()
    
    return result["message"]

@function_tool
async def jump(
    ctx: RunContextWrapper[GameState], 
    target_x: int, 
    target_y: int
) -> str:
    """Jump over one square to land two squares away.
    
    Args:
        target_x: The x-coordinate to jump to
        target_y: The y-coordinate to jump to
    """
    game_state = ctx.context
    result = game_state.person.jump(
        game_state.game_board, 
        (target_x, target_y)
    )
    
    return result["message"]

@function_tool
async def push(
    ctx: RunContextWrapper[GameState], 
    object_id: str,
    direction: str
) -> str:
    """Push an object in a specified direction.
    The person will move into the object's original position.
    
    Args:
        object_id: The ID of the object to push
        direction: The direction to push ("left", "right", "up", "down")
    """
    game_state = ctx.context
    
    # Find the object
    if object_id not in game_state.nearby_objects:
        return f"Cannot find object {object_id} nearby"
    
    obj = game_state.nearby_objects[object_id]
    if not hasattr(obj, 'position') or not obj.position:
        return f"Object {object_id} has no position"
        
    # Calculate push direction
    direction_pos = DirectionHelper.get_relative_position(obj.position, direction)
    push_vector = DirectionHelper.get_direction_vector(obj.position, direction_pos)
    
    result = game_state.person.push(
        game_state.game_board, 
        obj.position,
        push_vector
    )
    
    if result["success"]:
        game_state.sync_game_state()
    
    return result["message"]

@function_tool
async def pull(
    ctx: RunContextWrapper[GameState], 
    object_x: int, 
    object_y: int
) -> str:
    """Pull an object into the person's current position.
    
    Args:
        object_x: The x-coordinate of the object to pull
        object_y: The y-coordinate of the object to pull
    """
    game_state = ctx.context
    result = game_state.person.pull(
        game_state.game_board, 
        (object_x, object_y)
    )
    
    return result["message"]

@function_tool
async def get_from_container(
    ctx: RunContextWrapper[GameState], 
    container_id: str, 
    item_id: str
) -> str:
    """Get an item from a container and put it in the person's inventory.
    
    Args:
        container_id: The ID of the container
        item_id: The ID of the item to get
    """
    game_state = ctx.context
    
    if container_id not in game_state.containers:
        return f"Container {container_id} not found nearby"
    
    container = game_state.containers[container_id]
    result = game_state.person.get_from_container(container, item_id)
    
    return result["message"]

@function_tool
async def put_in_container(
    ctx: RunContextWrapper[GameState], 
    container_id: str, 
    item_id: str
) -> str:
    """Put an item from the person's inventory into a container.
    
    Args:
        container_id: The ID of the container
        item_id: The ID of the item to put in the container
    """
    game_state = ctx.context
    
    if container_id not in game_state.containers:
        return f"Container {container_id} not found nearby"
    
    container = game_state.containers[container_id]
    result = game_state.person.put_in_container(item_id, container)
    
    return result["message"]

@function_tool
async def use_object_with(
    ctx: RunContextWrapper[GameState], 
    item1_id: str, 
    item2_id: str
) -> str:
    """Use one object with another.
    
    Args:
        item1_id: The ID of the first item (must be in inventory)
        item2_id: The ID of the second item
    """
    game_state = ctx.context
    result = game_state.person.use_object_with(item1_id, item2_id)
    
    return result["message"]

@function_tool
async def look(ctx: RunContextWrapper[GameState]) -> str:
    """Look around to find objects up to 5 positions away.

    This function scans for nearby objects whose positions are within a
    Manhattan distance of 5 from the player's current location.
    """
    game_state = ctx.context

    # Sync state and update game state information
    sync_message = game_state.sync_game_state()

    if not game_state.nearby_objects:
        return "You don't see anything interesting nearby."

    object_descriptions = []
    person_pos = game_state.person.position

    for obj in game_state.nearby_objects.values():
        if obj.position and person_pos:
            # Calculate Manhattan distance between the player and the object
            distance = abs(obj.position[0] - person_pos[0]) + abs(obj.position[1] - person_pos[1])
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
    ctx: RunContextWrapper[GameState], 
    message: str
) -> str:
    """Say something.
    
    Args:
        message: The message to say
    """
    game_state = ctx.context
    result = game_state.person.say(message)
    
    return result["message"]

@function_tool
async def check_inventory(
    ctx: RunContextWrapper[GameState]
) -> str:
    """Check what items are in the person's inventory."""
    game_state = ctx.context
    
    if not game_state.person.inventory or not game_state.person.inventory.contents:
        return f"{game_state.person.name}'s inventory is empty"
    
    items = game_state.person.inventory.contents
    item_descriptions = [f"{item.id}: {item.name}" for item in items]
    
    return f"{game_state.person.name}'s inventory contains:\n" + "\n".join(item_descriptions)

@function_tool
async def examine_object(
    ctx: RunContextWrapper[GameState],
    object_id: str
) -> str:
    """Examine an object to get more information about it.
    
    Args:
        object_id: The ID of the object to examine
    """
    game_state = ctx.context
    
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
    for item in game_state.person.inventory.contents:
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

@function_tool
async def execute_movement_sequence(
    ctx: RunContextWrapper[GameState], 
    commands: list
) -> str:
    """Execute a sequence of movement instructions provided as a list of commands.

    Each command is expected to be a dict with the keys 'tool' and 'parameters'.
    Supported tools: 'move' and 'jump'.
    """
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

# Create the agent with all tools
def create_puppet_master(person_name="Game Character"):
    return Agent[GameState](
        name=person_name,
        instructions=f"""You control {person_name}, a character in a game world.\n\nYou have full access to your game state through the context, including:\n- Your current position on the board\n- Your inventory contents\n- Nearby objects and their positions\n- The game board layout\n\nWhen provided with a JSON input containing a 'commands' key, execute the movement commands sequentially using tools:\n- 'move': parameters include 'direction', 'is_running', and 'continuous'\n- 'jump': parameters include 'target_x' and 'target_y'\n\nAlways print the list of tools you are using in your response.""",
        tools=[
            move,
            jump,
            push,
            pull,
            get_from_container,
            put_in_container,
            use_object_with,
            look,
            say,
            check_inventory,
            examine_object,
            execute_movement_sequence
        ]
    )

# Setup conversation handler
async def run_continuous_conversation(game_state: GameState, person_name="Game Character"):
    agent = create_puppet_master(person_name)

    # Thread ID for tracing
    thread_id = f"game-conversation-{game_state.person.id}"
    
    print(f"\n{person_name} is ready to act in the game world. Type 'exit' to quit.")
    
    # Initialize conversation history
    conversation_history = []
    
    while True:
        try:
            # Get user input
            user_input = input("\nYou: ")
            
            # Check for exit command
            if user_input.lower() == 'exit':
                print("\nGame session ended.")
                break
            
            # Add user message to conversation history
            if not conversation_history:
                # First message - just use the text input
                input_for_agent = user_input
            else:
                # Add the new user message to existing conversation
                conversation_history.append({"role": "user", "content": user_input})
                input_for_agent = conversation_history
            
            # Run agent with conversation history
            print("\nThinking...")
            
            with trace(workflow_name="GameCharacterConversation", group_id=thread_id):
                result = await Runner.run(
                    starting_agent=agent,
                    input=input_for_agent,
                    context=game_state,
                )
            
            # Display the response
            print(f"\n{person_name}: {result.final_output}")
            
            # Update conversation history with agent's response
            if not conversation_history:
                # Initialize history with the first exchange
                conversation_history = result.to_input_list()
            else:
                # Update existing history with agent's response
                conversation_history.append({"role": "assistant", "content": result.final_output})
                
        except Exception as e:
            print(f"\nError during conversation: {str(e)}")

# Example of using the agent
async def example_usage():
    from person import Person
    from game_object import Container, GameObject
    
    # Create a game board (mock)
    class SimpleGameBoard:
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
        
        def get_nearby_objects(self, position, radius=2):
            """Get all objects within a certain radius of a position."""
            x, y = position
            nearby = []
            for entity in self.entities.values():
                if entity.position:
                    ex, ey = entity.position
                    if abs(ex - x) <= radius and abs(ey - y) <= radius:
                        nearby.append(entity)
            return nearby
    
    # Create game objects
    board = SimpleGameBoard()
    
    # Create a player
    player = Person(id="player1", name="Alex", strength=10)
    board.move_entity(player, (5, 5))
    
    # Create some objects in specific directions
    box = GameObject(id="box1", name="Wooden Box", description="A sturdy wooden box", is_movable=True, weight=3)
    board.move_entity(box, (5, 6))  # South/Down from player
    
    table = GameObject(id="table1", name="Table", description="A wooden table", is_movable=False)
    board.move_entity(table, (4, 5))  # West/Left from player
    
    chest = Container(id="chest1", name="Treasure Chest", description="A mysterious chest", is_open=True)
    board.move_entity(chest, (6, 5))  # East/Right from player
    
    key = GameObject(id="key1", name="Rusty Key", description="An old rusty key", is_movable=True, weight=1)
    chest.add_item(key)
    
    sword = GameObject(id="sword1", name="Iron Sword", description="A sharp iron sword", is_movable=True, weight=2)
    player.inventory.add_item(sword)
    
    # Create game state context
    game_state = GameState()
    game_state.game_board = board
    game_state.person = player
    
    # Initial sync of game state
    game_state.sync_game_state()
    
    print("\nGame world initialized!")
    print("Player is at position (5,5)")
    print("Try commands like:")
    print("- 'look around'")
    print("- 'move right'")
    print("- 'push box1 down'")
    print("- 'get key1 from chest1'")
    
    # Run conversation
    await run_continuous_conversation(game_state, "Alex")

if __name__ == "__main__":
    asyncio.run(example_usage())
