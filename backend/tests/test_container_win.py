"""
Test script for container operations - adding items, removing items, and other interactions.
Simpler version for Windows compatibility.
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
from game_object import Container


def test_basic_container_operations():
    """Test basic container operations"""
    print("=== Testing Basic Container Operations ===")
    
    # Create a game
    game = Game(width=5, height=5)
    print("Created game with dimensions 5x5")
    
    # Create a container
    container = game.create_object("container", "Test Box", (1, 1), capacity=5, weight=2)
    print(f"Created container: {container.name} with capacity {container.capacity}")
    
    # Create some items
    items = []
    for i in range(3):
        item = game.create_object("item", f"Test Item {i+1}", (0, 0), weight=1)
        items.append(item)
        print(f"Created item: {item.name}")
    
    # Add items to container
    print("\nAdding items to container:")
    for item in items:
        result = container.add_item(item)
        if result["success"]:
            print(f"  ✓ Added {item.name} to {container.name}")
        else:
            print(f"  ✗ Failed to add {item.name}: {result['message']}")
    
    # List contents
    print("\nContainer contents:")
    for i, item in enumerate(container.contents):
        print(f"  {i+1}. {item.name}")
    
    # Remove items
    print("\nRemoving items from container:")
    removed_item = container.contents[0]
    result = container.remove_item(removed_item)
    if result["success"]:
        print(f"  ✓ Removed {removed_item.name} from {container.name}")
    else:
        print(f"  ✗ Failed to remove item: {result['message']}")
    
    # List contents after removal
    print("\nContainer contents after removal:")
    for i, item in enumerate(container.contents):
        print(f"  {i+1}. {item.name}")
    
    print("\nBasic container operations test complete")
    return container, items

def test_container_limits():
    """Test container capacity and weight limits"""
    print("\n=== Testing Container Limits ===")
    
    # Create a game
    game = Game(width=5, height=5)
    
    # Create a limited container (only capacity limit, no weight limit supported)
    container = game.create_object("container", "Limited Box", (2, 2), 
                                  capacity=3, weight=2)
    print(f"Created container with capacity {container.capacity}")
    
    # Test capacity limit
    print("\nTesting capacity limit:")
    items = []
    for i in range(5):  # Create more items than capacity
        item = game.create_object("item", f"Capacity Item {i+1}", (0, 0), weight=1)
        items.append(item)
        
        result = container.add_item(item)
        if result["success"]:
            print(f"  ✓ Added {item.name} to container ({len(container.contents)}/{container.capacity})")
        else:
            print(f"  ✗ Failed to add {item.name}: {result['message']}")
    
    # Use a new container for the weight test (just to show total weight calculation)
    container = game.create_object("container", "Weight Box", (3, 3), 
                                  capacity=10, weight=2)
    
    # Test adding items and track weight (no actual weight limit exists)
    print("\nTesting item weights (no weight limit implemented):")
    for i in range(5):
        weight = i + 1
        item = game.create_object("item", f"Weight Item {i+1}", (0, 0), weight=weight)
        
        result = container.add_item(item)
        total_weight = sum(item.weight for item in container.contents)
        
        if result["success"]:
            print(f"  ✓ Added {item.name} (weight {weight}) - Total container weight: {total_weight}")
        else:
            print(f"  ✗ Failed to add {item.name} (weight {weight}): {result['message']}")
    
    print("\nContainer limits test complete")
    return container

def test_nested_containers():
    """Test putting containers inside containers"""
    print("\n=== Testing Nested Containers ===")
    
    # Create a game
    game = Game(width=5, height=5)
    
    # Create parent container
    parent = game.create_object("container", "Parent Container", (2, 2), 
                               capacity=5, weight=3)
    print(f"Created parent container: {parent.name}")
    
    # Create child container
    child = game.create_object("container", "Child Container", (3, 3), 
                              capacity=3, weight=2)
    print(f"Created child container: {child.name}")
    
    # Create items for child container
    items = []
    for i in range(2):
        item = game.create_object("item", f"Small Item {i+1}", (0, 0), weight=1)
        items.append(item)
        child.add_item(item)
        print(f"Added {item.name} to child container")
    
    # Add child to parent
    result = parent.add_item(child)
    if result["success"]:
        print(f"✓ Added child container to parent container")
        
        # Show the nested structure
        print("\nNested container structure:")
        print(f"Parent: {parent.name} ({len(parent.contents)} items)")
        for i, item in enumerate(parent.contents):
            if isinstance(item, Container):
                print(f"  Child {i+1}: {item.name} ({len(item.contents)} items)")
                for j, grandchild in enumerate(item.contents):
                    print(f"    Item {j+1}: {grandchild.name}")
    else:
        print(f"✗ Failed to add child to parent: {result['message']}")
    
    print("\nNested containers test complete")
    return parent, child, items

def main():
    """Run container operation tests"""
    print("=== CONTAINER OPERATIONS TEST SUITE ===\n")
    
    try:
        test_basic_container_operations()
        test_container_limits()
        test_nested_containers()
        
        print("\n=== ALL TESTS COMPLETED SUCCESSFULLY ===")
    except Exception as e:
        print(f"\n!!! TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 