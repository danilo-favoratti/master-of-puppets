"""Simple test file to check if imports are working correctly."""
import os
import sys

# Add parent directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

print("Testing imports...")

# Import from the model package
try:
    from game import Game
    print("✓ Successfully imported Game")
except ImportError as e:
    print(f"✗ Failed to import Game: {e}")

try:
    from entity import Position
    print("✓ Successfully imported Position")
except ImportError as e:
    print(f"✗ Failed to import Position: {e}")

try:
    from board import Board
    print("✓ Successfully imported Board")
except ImportError as e:
    print(f"✗ Failed to import Board: {e}")

try:
    from game_object import GameObject, Container
    print("✓ Successfully imported GameObject and Container")
except ImportError as e:
    print(f"✗ Failed to import GameObject and Container: {e}")

try:
    from person import Person
    print("✓ Successfully imported Person")
except ImportError as e:
    print(f"✗ Failed to import Person: {e}")

try:
    from game_engine import GameEngine
    print("✓ Successfully imported GameEngine")
except ImportError as e:
    print(f"✗ Failed to import GameEngine: {e}")

print("Import tests completed.")

if __name__ == "__main__":
    # Try to create a simple game and objects
    try:
        game = Game(width=3, height=3)
        print("✓ Successfully created Game instance")
        
        player = game.create_player("Test Player", (0, 0))
        print("✓ Successfully created Player")
        
        container = game.create_object("container", "Test Box", (1, 1), capacity=3)
        print("✓ Successfully created Container")
        
        item = game.create_object("item", "Test Item", (2, 2))
        print("✓ Successfully created item GameObject")
        
        print("All tests passed!")
    except Exception as e:
        print(f"✗ Test failed: {e}") 