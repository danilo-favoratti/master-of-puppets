"""
Test script to load a tiny 3x3 game, pull a container, and verify the result.
This version tests all possible pull scenarios including edge cases.
"""
import os
import sys

# Add parent directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import from the model package
from game import Game
from entity import Position
from board import Board
from game_object import GameObject, Container
from person import Person
from game_engine import GameEngine

def setup_test_board(engine, player_x, player_y, container_x, container_y):
    """Setup the board with player and container at specific positions"""
    # Make sure the board is at least 3x3
    assert engine.width >= 3 and engine.height >= 3, "Board must be at least 3x3"
    
    # Reset the board (clear existing entities)
    player_id = engine.player["id"]
    container = None
    for entity_id, entity in engine.entities.items():
        if entity["type"] == "container" and entity.get("is_movable", True):
            container = entity
            container_id = entity_id
            break
    
    if not container:
        print("Movable container not found")
        return False
    
    # Position the player and container
    if not (0 <= player_x < engine.width and 0 <= player_y < engine.height):
        print(f"Invalid player position: ({player_x}, {player_y})")
        return False
        
    if not (0 <= container_x < engine.width and 0 <= container_y < engine.height):
        print(f"Invalid container position: ({container_x}, {container_y})")
        return False
    
    # Make sure the positions don't overlap
    if player_x == container_x and player_y == container_y:
        print("Player and container cannot occupy the same position")
        return False
    
    # Move entities to their new positions
    engine.move_entity(player_id, player_x, player_y)
    engine.move_entity(container_id, container_x, container_y)
    
    print(f"Setup: Player at ({player_x}, {player_y}), Container at ({container_x}, {container_y})")
    print("Initial board state:")
    engine.print_board()  # Print the board after setup
    return True

def create_game_from_engine(engine):
    """Create a Game instance from the GameEngine's data"""
    # Create a new game
    game = Game(width=engine.width, height=engine.height)
    
    # Map of entity IDs to instances
    entity_instances = {}
    
    # Create all entities
    for entity_id, entity_data in engine.entities.items():
        entity_type = entity_data["type"]
        name = entity_data.get("name", entity_type)
        
        # Get position
        if "position" in entity_data:
            pos = (entity_data["position"]["x"], entity_data["position"]["y"])
        else:
            pos = None
            
        # Handle player
        if entity_type == "player":
            player = game.create_player(name, pos)
            entity_instances[entity_id] = player
        else:
            # Extract properties
            properties = {k: v for k, v in entity_data.items() 
                         if k not in ["id", "type", "name", "position", "contents"]}
            
            # Create game object
            obj = game.create_object(entity_type, name, pos, **properties)
            entity_instances[entity_id] = obj
    
    # Handle container contents after all entities are created
    for entity_id, entity_data in engine.entities.items():
        if entity_data.get("type") in ["container", "chest"] and "contents" in entity_data:
            container = entity_instances.get(entity_id)
            if container and isinstance(container, Container):
                for item_id in entity_data["contents"]:
                    if item_id in entity_instances:
                        container.contents.append(entity_instances[item_id])
    
    return game, entity_instances

def test_pull_successful(engine):
    """Test successful pull scenarios (all 4 directions)"""
    tests = [
        # [player_x, player_y, container_x, container_y, direction_name]
        # Pull from down (player below container, pulls down)
        [1, 2, 1, 1, "down"],
        # Pull from up (player above container, pulls up)
        [1, 0, 1, 1, "up"],
        # Pull from right (player to right of container, pulls right)
        [2, 1, 1, 1, "right"],
        # Pull from left (player to left of container, pulls left)
        [0, 1, 1, 1, "left"]
    ]
    
    for i, test in enumerate(tests):
        player_x, player_y, container_x, container_y, direction_name = test
        
        print(f"\n=== Test {i+1}: Pull {direction_name} ===")
        
        # Setup the board
        setup_success = setup_test_board(engine, player_x, player_y, container_x, container_y)
        if not setup_success:
            print("Setup failed, skipping test")
            continue
        
        # Create a Game instance from the engine data
        game, entity_map = create_game_from_engine(engine)
        
        # Find the container
        container = None
        container_position = None
        for entity in game.board.get_all_entities():
            if isinstance(entity, Container) and entity.is_movable:
                container = entity
                container_position = entity.position
                break
        
        if not container:
            print("Container not found in the game, skipping test")
            continue
            
        # Perform the pull using the Person.pull method
        if game.player:
            result = game.player.pull(game.board, container_position)
            
            print(f"Pull result: {result['success']}")
            print(f"Message: {result['message']}")
            
            # Show the updated positions
            if result['success']:
                print(f"Original player position: ({player_x}, {player_y})")
                print(f"Original container position: ({container_x}, {container_y})")
                print(f"New player position: {game.player.position}")
                print(f"New container position: {container.position}")
                
            # Show the board state (we need to manually print since we're using a different Game instance)
            print("Board state after pull:")
            for y in range(game.board.height):
                row = ""
                for x in range(game.board.width):
                    entities = game.board.get_entities_at((x, y))
                    if entities:
                        entity_type = entities[0].__class__.__name__
                        if isinstance(entities[0], Person):
                            row += "[player    ]"
                        elif isinstance(entities[0], Container):
                            row += "[container ]"
                        else:
                            row += f"[{entity_type:<10}]"
                    else:
                        row += "[          ]"
                print(row)
        else:
            print("Player not found in the game, skipping test")

def test_pull_failures(engine):
    """Test pull failure scenarios"""
    tests = [
        # [desc, player_x, player_y, container_x, container_y]
        # Player would go off the board
        ["Player off board (top)", 0, 0, 0, 1],
        ["Player off board (bottom)", 0, 2, 0, 1],
        ["Player off board (left)", 0, 0, 1, 0],
        ["Player off board (right)", 2, 0, 1, 0],
        
        # Object and player not adjacent
        ["Not adjacent (diagonal)", 0, 0, 1, 1],
        ["Not adjacent (too far)", 0, 0, 0, 2],
    ]
    
    for i, test in enumerate(tests):
        desc, player_x, player_y, container_x, container_y = test
        
        print(f"\n=== Test Failure {i+1}: {desc} ===")
        
        # Setup the board
        setup_success = setup_test_board(engine, player_x, player_y, container_x, container_y)
        if not setup_success:
            print("Setup failed, skipping test")
            continue
            
        # Create a Game instance from the engine data
        game, entity_map = create_game_from_engine(engine)
        
        # Find the container
        container = None
        container_position = None
        for entity in game.board.get_all_entities():
            if isinstance(entity, Container) and hasattr(entity, 'is_movable') and entity.is_movable:
                container = entity
                container_position = entity.position
                break
        
        if not container:
            print("Container not found in the game, skipping test")
            continue
            
        # Attempt to pull using the Person.pull method
        if game.player:
            result = game.player.pull(game.board, container_position)
            
            print(f"Pull attempt result: {'Failed as expected' if not result['success'] else 'Unexpectedly succeeded'}")
            print(f"Message: {result['message']}")
            
            # Show the board state
            print("Board state after pull attempt:")
            for y in range(game.board.height):
                row = ""
                for x in range(game.board.width):
                    entities = game.board.get_entities_at((x, y))
                    if entities:
                        entity_type = entities[0].__class__.__name__
                        if isinstance(entities[0], Person):
                            row += "[player    ]"
                        elif isinstance(entities[0], Container):
                            row += "[container ]"
                        else:
                            row += f"[{entity_type:<10}]"
                    else:
                        row += "[          ]"
                print(row)
        else:
            print("Player not found in the game, skipping test")

def test_blocked_pull(engine):
    """Test pull where the target position for the player is blocked by another object"""
    print("\n=== Test: Blocked Pull ===")
    
    # Setup player and container
    setup_success = setup_test_board(engine, 0, 1, 1, 1)
    if not setup_success:
        print("Setup failed, skipping test")
        return
    
    # Create a blocking object where the player would move during a pull
    blocking_obj = {"id": "blocking_obj", "type": "furniture", "name": "Blocking Object", 
                    "position": {"x": -1, "y": 1}, "is_movable": False}
    engine.entities["blocking_obj"] = blocking_obj
    engine.board[1][-1 if -1 < engine.width else 0] = "furniture"
    engine.entity_positions[(-1, 1) if -1 < engine.width else (0, 1)] = "blocking_obj"
    
    print("Added blocking object at (-1,1)")
    engine.print_board()
    
    # Create a Game instance from the engine data
    game, entity_map = create_game_from_engine(engine)
    
    # Find the container
    container = None
    container_position = None
    for entity in game.board.get_all_entities():
        if isinstance(entity, Container) and hasattr(entity, 'is_movable') and entity.is_movable:
            container = entity
            container_position = entity.position
            break
    
    if not container:
        print("Container not found in the game, skipping test")
        return
        
    # Try to pull container using the Person.pull method
    if game.player:
        result = game.player.pull(game.board, container_position)
        
        print(f"Pull attempt result: {'Failed as expected' if not result['success'] else 'Unexpectedly succeeded'}")
        print(f"Message: {result['message']}")
        
        # Show the board state
        print("Board state after pull attempt:")
        for y in range(game.board.height):
            row = ""
            for x in range(game.board.width):
                entities = game.board.get_entities_at((x, y))
                if entities:
                    entity_type = entities[0].__class__.__name__
                    if isinstance(entities[0], Person):
                        row += "[player    ]"
                    elif isinstance(entities[0], Container):
                        row += "[container ]"
                    else:
                        row += f"[{entity_type:<10}]"
                else:
                    row += "[          ]"
            print(row)
    else:
        print("Player not found in the game, skipping test")
    
    # Clean up
    if "blocking_obj" in engine.entities:
        del engine.entities["blocking_obj"]
        engine.board[1][-1 if -1 < engine.width else 0] = None
        if (-1, 1) in engine.entity_positions:
            del engine.entity_positions[(-1, 1)]
        elif (0, 1) in engine.entity_positions and engine.entity_positions[(0, 1)] == "blocking_obj":
            del engine.entity_positions[(0, 1)]

def test_pull_heavy_object(engine):
    """Test pulling an object that is too heavy for the player's strength"""
    print("\n=== Test: Pull Heavy Object ===")
    
    # Setup player and container
    setup_success = setup_test_board(engine, 0, 1, 1, 1)
    if not setup_success:
        print("Setup failed, skipping test")
        return
    
    # Make the container very heavy
    for entity_id, entity in engine.entities.items():
        if entity["type"] == "container" and entity.get("is_movable", True):
            entity["weight"] = 100  # Very heavy, beyond normal player strength
            break
    
    print("Set container weight to 100 (very heavy)")
    
    # Create a Game instance from the engine data
    game, entity_map = create_game_from_engine(engine)
    
    # Find the container
    container = None
    container_position = None
    for entity in game.board.get_all_entities():
        if isinstance(entity, Container) and hasattr(entity, 'is_movable') and entity.is_movable:
            container = entity
            container_position = entity.position
            break
    
    if not container:
        print("Container not found in the game, skipping test")
        return
        
    # Try to pull the heavy container
    if game.player:
        result = game.player.pull(game.board, container_position)
        
        print(f"Pull attempt result: {'Failed as expected' if not result['success'] else 'Unexpectedly succeeded'}")
        print(f"Message: {result['message']}")
        
        # Show the board state
        print("Board state after pull attempt:")
        for y in range(game.board.height):
            row = ""
            for x in range(game.board.width):
                entities = game.board.get_entities_at((x, y))
                if entities:
                    entity_type = entities[0].__class__.__name__
                    if isinstance(entities[0], Person):
                        row += "[player    ]"
                    elif isinstance(entities[0], Container):
                        row += "[container ]"
                    else:
                        row += f"[{entity_type:<10}]"
                else:
                    row += "[          ]"
            print(row)
    else:
        print("Player not found in the game, skipping test")

def test_load_custom_examples():
    """Test loading custom example files for pull testing"""
    example_files = [
        os.path.join(parent_dir, "examples", "tiny_game_example.json"),
        os.path.join(parent_dir, "examples", "small_game_example.json")
    ]
    
    for file_path in example_files:
        if os.path.exists(file_path):
            print(f"\n=== Testing with file: {file_path} ===")
            
            engine = GameEngine(file_path)
            if engine:
                print(f"Loaded game with dimensions: {engine.width}x{engine.height}")
                engine.print_board()
                
                # Run tests with this engine
                if engine.width >= 3 and engine.height >= 3:
                    test_pull_successful(engine)
                    test_pull_failures(engine)
                    test_blocked_pull(engine)
                    test_pull_heavy_object(engine)
                else:
                    print("Board too small for pull tests (need at least 3x3)")
                
                break
    else:
        print("No example files found. Please create a test game file first.")

def main():
    """Run all pull action tests"""
    print("=== PULL ACTION TEST SUITE ===")
    
    # Find and load the game file
    file_path = os.path.join(parent_dir, "examples", "tiny_game_example.json")
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        test_load_custom_examples()
        return
    
    # Use GameEngine to load the game
    engine = GameEngine(file_path)
    if not engine:
        print("Failed to load game")
        return
    
    print(f"Loaded game with dimensions: {engine.width}x{engine.height}")
    engine.print_board()
    engine.print_entity_details()
    
    # Run the test suite
    if engine.width >= 3 and engine.height >= 3:
        test_pull_successful(engine)
        test_pull_failures(engine)
        test_blocked_pull(engine)
        test_pull_heavy_object(engine)
    else:
        print("Board too small for pull tests (need at least 3x3)")

if __name__ == "__main__":
    main() 