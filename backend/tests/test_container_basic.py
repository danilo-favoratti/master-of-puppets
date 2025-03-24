"""
Minimal test for container operations - just the basics
"""
import os
import sys

# Add parent directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import from the model package
from model.game import Game
from model.game_object import Container, GameObject

def main():
    """Run basic container test"""
    print("=== BASIC CONTAINER TEST ===")
    
    # Create a game
    game = Game(width=3, height=3)
    print("Created game")
    
    # Create a container 
    container = Container(id="container1", name="Test Box", capacity=3)
    print(f"Created container: {container.name}, capacity: {container.capacity}")
    
    # Create some items
    item1 = GameObject(id="item1", name="Test Item 1", weight=1)
    item2 = GameObject(id="item2", name="Test Item 2", weight=2)
    print(f"Created items: {item1.name}, {item2.name}")
    
    # Add items to container
    result1 = container.add_item(item1)
    print(f"Add {item1.name}: {result1['success']} - {result1['message']}")
    
    result2 = container.add_item(item2)
    print(f"Add {item2.name}: {result2['success']} - {result2['message']}")
    
    # Show contents
    print(f"Container has {len(container.contents)} items:")
    for i, item in enumerate(container.contents, 1):
        print(f"  {i}. {item.name} (weight: {item.weight})")
    
    # Remove an item
    remove_result = container.remove_item(item1.id)
    print(f"Remove {item1.name}: {remove_result['success']} - {remove_result['message']}")
    
    # Show contents after removal
    print(f"Container now has {len(container.contents)} items:")
    for i, item in enumerate(container.contents, 1):
        print(f"  {i}. {item.name} (weight: {item.weight})")
    
    print("=== TEST COMPLETE ===")

if __name__ == "__main__":
    main() 