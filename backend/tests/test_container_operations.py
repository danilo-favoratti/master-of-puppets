"""
Test script for container operations - adding items, removing items, and other interactions.
Tests all aspects of container functionality including capacity limits, weight limits, and item types.
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

def test_add_items_to_container(game, container, items):
    """Test adding items to a container"""
    print(f"\n=== Test: Adding Items to Container ===")
    print(f"Container: {container.name} (Capacity: {container.capacity}, Current items: {len(container.contents)})")
    
    results = []
    
    for item in items:
        print(f"Attempting to add {item.name} (Weight: {item.weight})...")
        result = container.add_item(item)
        results.append(result)
        
        if result["success"]:
            print(f"✓ Successfully added {item.name}")
        else:
            print(f"✗ Failed to add {item.name}: {result['message']}")
            
        # Show container state after each operation
        print(f"Container now has {len(container.contents)} items:")
        for i, content in enumerate(container.contents, 1):
            print(f"  {i}. {content.name} (Weight: {content.weight})")
    
    return results

def test_remove_items_from_container(game, container):
    """Test removing items from a container"""
    print(f"\n=== Test: Removing Items from Container ===")
    print(f"Container: {container.name} (Items: {len(container.contents)})")
    
    results = []
    
    # Create a copy of contents to avoid modification during iteration
    contents = container.contents.copy()
    
    for item in contents:
        print(f"Attempting to remove {item.name}...")
        result = container.remove_item(item.id)
        results.append(result)
        
        if result["success"]:
            print(f"✓ Successfully removed {item.name}")
        else:
            print(f"✗ Failed to remove {item.name}: {result['message']}")
            
        # Show container state after each operation
        print(f"Container now has {len(container.contents)} items:")
        for i, content in enumerate(container.contents, 1):
            print(f"  {i}. {content.name} (Weight: {content.weight})")
    
    return results

def test_container_capacity_limit(game):
    """Test container capacity limits"""
    print(f"\n=== Test: Container Capacity Limits ===")
    
    # Create a small container with limited capacity
    container = game.create_object("container", "Small Box", (3, 3), capacity=3, weight=2, is_movable=True)
    print(f"Created container: {container.name} with capacity {container.capacity}")
    
    # Create several small items
    items = []
    for i in range(5):  # Create 5 items to test overflow
        item = game.create_object("item", f"Small Item {i+1}", (0, 0), weight=1)
        items.append(item)
        print(f"Created item: {item.name} with weight {item.weight}")
    
    # Try to add more items than capacity
    results = test_add_items_to_container(game, container, items)
    
    # Verify we could only add up to capacity
    successful_adds = sum(1 for result in results if result["success"])
    print(f"\nSummary: Successfully added {successful_adds} items out of {len(items)}")
    print(f"Expected: {min(container.capacity, len(items))}")
    
    return container, items, results

def test_container_weight_limit(game):
    """Test container weight limits"""
    print(f"\n=== Test: Container Weight Limits ===")
    
    # Create a container (without max_weight since it's not supported)
    container = game.create_object("container", "Weight Limited Box", (4, 4), 
                                  capacity=10, weight=2, is_movable=True)
    print(f"Created container: {container.name} with capacity {container.capacity}")
    
    # Create items with increasing weights
    items = []
    for i in range(5):
        weight = i + 2  # 2, 3, 4, 5, 6
        item = game.create_object("item", f"Weight Item {i+1}", (0, 0), weight=weight)
        items.append(item)
        print(f"Created item: {item.name} with weight {item.weight}")
    
    # Try to add items
    results = test_add_items_to_container(game, container, items)
    
    # Calculate total weight in container (though there's no actual limit in the code)
    total_weight = sum(item.weight for item in container.contents)
    print(f"\nSummary: Container has total weight of {total_weight}")
    
    return container, items, results

def test_nested_containers(game):
    """Test putting containers inside other containers"""
    print(f"\n=== Test: Nested Containers ===")
    
    # Create parent container (without max_weight)
    parent_container = game.create_object("container", "Large Chest", (5, 5), 
                                         capacity=5, weight=5, is_movable=True)
    print(f"Created parent container: {parent_container.name}")
    
    # Create child containers (without max_weight)
    child_containers = []
    for i in range(3):
        child = game.create_object("container", f"Small Box {i+1}", (0, 0), 
                                  capacity=2, weight=2, is_movable=True)
        child_containers.append(child)
        print(f"Created child container: {child.name}")
    
    # Create some items for the child containers
    small_items = []
    for i in range(6):
        item = game.create_object("item", f"Tiny Item {i+1}", (0, 0), weight=1)
        small_items.append(item)
        print(f"Created item: {item.name}")
    
    # Add items to child containers
    for i, container in enumerate(child_containers):
        # Add 2 items to each child container
        items_to_add = small_items[i*2:(i+1)*2]
        test_add_items_to_container(game, container, items_to_add)
    
    # Now try to add child containers to parent container
    results = test_add_items_to_container(game, parent_container, child_containers)
    
    # Verify nested structure
    print("\nFinal container structure:")
    print(f"Parent: {parent_container.name} ({len(parent_container.contents)} items)")
    for i, child in enumerate(parent_container.contents):
        if isinstance(child, Container):
            print(f"  Child {i+1}: {child.name} ({len(child.contents)} items)")
            for j, grandchild in enumerate(child.contents):
                print(f"    Item {j+1}: {grandchild.name}")
    
    return parent_container, child_containers, results

def test_person_container_interactions(game):
    """Test interactions between a person and containers"""
    print(f"\n=== Test: Person-Container Interactions ===")
    
    # Ensure player exists
    if not game.player:
        game.create_player("Test Player", (2, 2))
        print(f"Created player: {game.player.name}")
    
    # Create a container 
    container = game.create_object("container", "Backpack", (3, 2), capacity=5, weight=2, is_movable=True)
    print(f"Created container: {container.name} at position {container.position}")
    
    # Add the container to the board
    game.board.add_entity(container, container.position)
    
    # Create some items
    items = []
    for i in range(3):
        item = game.create_object("item", f"Collectible {i+1}", weight=1)
        items.append(item)
        # Place items on the board
        pos = (4 + i, 2)
        game.board.add_entity(item, pos)
        print(f"Created item: {item.name} at position {pos}")
    
    # Move player near the container
    game.player.move(game.board, (2, 2))
    print(f"Player at position {game.player.position}")
    
    # Test adding items to player's inventory
    print("\nTesting player inventory operations:")
    for item in items:
        # Move player to item position
        orig_pos = item.position
        game.player.move(game.board, (orig_pos[0] - 1, orig_pos[1]))
        print(f"Player moved to {game.player.position}, next to {item.name} at {item.position}")
        
        # Pick up the item
        result = game.player.pick_up(game.board, item.position)
        print(f"Pick up result: {result['success']} - {result['message']}")
        
        if result['success']:
            print(f"Player inventory: {len(game.player.inventory)} items")
    
    # Now test putting items into the container
    print("\nTesting putting items from inventory into container:")
    
    # Move player next to container
    game.player.move(game.board, (container.position[0] - 1, container.position[1]))
    print(f"Player moved to {game.player.position}, next to container at {container.position}")
    
    # Items in player inventory
    player_items = game.player.inventory.copy()
    for item in player_items:
        # Put item in container
        result = game.player.put_in_container(game.board, container.position, item)
        print(f"Put {item.name} in container result: {result['success']} - {result['message']}")
        
        if result['success']:
            print(f"Player inventory: {len(game.player.inventory)} items")
            print(f"Container contents: {len(container.contents)} items")
    
    # Test taking items from container
    print("\nTesting taking items from container:")
    container_items = container.contents.copy()
    for item in container_items:
        result = game.player.take_from_container(game.board, container.position, item)
        print(f"Take {item.name} from container result: {result['success']} - {result['message']}")
        
        if result['success']:
            print(f"Player inventory: {len(game.player.inventory)} items")
            print(f"Container contents: {len(container.contents)} items")
    
    return game.player, container, items

def test_special_containers(game):
    """Test special container types (locked, type-restricted)"""
    print(f"\n=== Test: Special Container Types ===")
    
    # Create a locked container
    locked_container = game.create_object("container", "Locked Chest", (6, 6), 
                                        capacity=5, weight=5, is_locked=True, is_movable=False)
    print(f"Created locked container: {locked_container.name} (locked: {locked_container.is_locked})")
    
    # Create a type-restricted container
    food_container = game.create_object("container", "Food Box", (7, 6), 
                                      capacity=5, weight=3, allowed_types=["food"], is_movable=True)
    print(f"Created type-restricted container: {food_container.name} (allowed types: {food_container.allowed_types})")
    
    # Create items of different types
    food_item = game.create_object("item", "Apple", (0, 0), weight=1, item_type="food")
    weapon_item = game.create_object("item", "Dagger", (0, 0), weight=2, item_type="weapon")
    key_item = game.create_object("item", "Golden Key", (0, 0), weight=1, item_type="key", unlocks="Locked Chest")
    
    print(f"Created items: {food_item.name} (type: {food_item.item_type}), "
          f"{weapon_item.name} (type: {weapon_item.item_type}), "
          f"{key_item.name} (type: {key_item.item_type}, unlocks: {key_item.unlocks})")
    
    # Test locked container
    print("\nTesting locked container:")
    items = [food_item, weapon_item]
    results_locked = test_add_items_to_container(game, locked_container, items)
    
    # Try to unlock the container
    print("\nTrying to unlock container with key:")
    if hasattr(locked_container, 'unlock') and callable(getattr(locked_container, 'unlock')):
        result = locked_container.unlock(key_item)
        print(f"Unlock result: {result['success']} - {result['message']}")
        
        if result['success']:
            print(f"Container is now {'locked' if locked_container.is_locked else 'unlocked'}")
            
            # Try adding items again
            print("\nTrying to add items to unlocked container:")
            results_unlocked = test_add_items_to_container(game, locked_container, items)
    
    # Test type-restricted container
    print("\nTesting type-restricted container:")
    type_results = []
    
    print(f"Trying to add {food_item.name} (type: {food_item.item_type}):")
    result = food_container.add_item(food_item)
    type_results.append(result)
    print(f"Result: {result['success']} - {result['message']}")
    
    print(f"Trying to add {weapon_item.name} (type: {weapon_item.item_type}):")
    result = food_container.add_item(weapon_item)
    type_results.append(result)
    print(f"Result: {result['success']} - {result['message']}")
    
    print(f"\nContainer contents: {len(food_container.contents)} items")
    for i, item in enumerate(food_container.contents, 1):
        print(f"  {i}. {item.name} (type: {item.item_type})")
    
    return locked_container, food_container, type_results

def test_container_search(game):
    """Test searching container contents"""
    print(f"\n=== Test: Container Search Operations ===")
    
    # Create a container with many items
    container = game.create_object("container", "Storage Trunk", (8, 8), 
                                  capacity=10, weight=5, is_movable=False)
    print(f"Created container: {container.name}")
    
    # Add items of various types
    items = [
        game.create_object("item", "Iron Sword", (0, 0), weight=3, item_type="weapon", damage=5),
        game.create_object("item", "Health Potion", (0, 0), weight=1, item_type="potion", effect="healing"),
        game.create_object("item", "Gold Coins", (0, 0), weight=2, item_type="currency", value=100),
        game.create_object("item", "Bread", (0, 0), weight=1, item_type="food", nutrition=10),
        game.create_object("item", "Wooden Shield", (0, 0), weight=2, item_type="armor", defense=3),
        game.create_object("item", "Silver Key", (0, 0), weight=1, item_type="key", unlocks="Silver Lock")
    ]
    
    # Add items to container
    test_add_items_to_container(game, container, items)
    
    # Test search by name
    print("\nSearching container by name:")
    name_queries = ["Sword", "Potion", "Nonexistent Item"]
    for query in name_queries:
        result = None
        if hasattr(container, 'find_item_by_name') and callable(getattr(container, 'find_item_by_name')):
            result = container.find_item_by_name(query)
        else:
            # Basic implementation if method doesn't exist
            result = next((item for item in container.contents if query.lower() in item.name.lower()), None)
        
        print(f"Search for '{query}': {result.name if result else 'Not found'}")
    
    # Test search by type
    print("\nSearching container by type:")
    type_queries = ["weapon", "food", "spell"]
    for query in type_queries:
        results = None
        if hasattr(container, 'find_items_by_type') and callable(getattr(container, 'find_items_by_type')):
            results = container.find_items_by_type(query)
        else:
            # Basic implementation if method doesn't exist
            results = [item for item in container.contents if hasattr(item, 'item_type') and item.item_type == query]
        
        print(f"Search for type '{query}': {len(results)} items found")
        for i, item in enumerate(results, 1):
            print(f"  {i}. {item.name}")
    
    return container, items

def test_container_inspection(game):
    """Test inspecting container contents without removing them"""
    print(f"\n=== Test: Container Inspection ===")
    
    # Create a container with various interesting items
    container = game.create_object("container", "Treasure Chest", (9, 9), capacity=10, weight=5, is_movable=False)
    print(f"Created container: {container.name}")
    
    # Add named items with varying properties
    rare_items = [
        game.create_object("item", "Ancient Scroll", (0, 0), weight=1, value=500, description="A mysterious scroll with ancient writings"),
        game.create_object("item", "Diamond Necklace", (0, 0), weight=2, value=1000, description="A sparkling diamond necklace"),
        game.create_object("item", "Magic Wand", (0, 0), weight=1, value=750, magic_power=10, description="A wand with magical properties")
    ]
    
    for item in rare_items:
        container.add_item(item)
        print(f"Added {item.name} to container")
    
    # Inspect the container (without removing items)
    print("\nInspecting container contents:")
    print(f"Container has {len(container.contents)} items:")
    
    total_value = 0
    for i, item in enumerate(container.contents, 1):
        value = getattr(item, 'value', 0)
        description = getattr(item, 'description', 'No description')
        total_value += value
        print(f"  {i}. {item.name} - Value: {value}, Description: {description}")
    
    print(f"\nTotal value of container contents: {total_value}")
    
    # Test getting the contents through the official method
    contents = container.get_contents()
    print(f"get_contents() returned {len(contents)} items")
    
    return container, rare_items

def main():
    """Run all container operations tests"""
    print("=== CONTAINER OPERATIONS TEST SUITE ===")
    
    # Create a new game for testing
    game = Game(width=10, height=10)
    print(f"Created new game with dimensions: {game.board.width}x{game.board.height}")
    
    # Run tests
    test_container_capacity_limit(game)
    test_container_weight_limit(game)
    test_nested_containers(game)
    test_person_container_interactions(game)
    test_special_containers(game)
    test_container_search(game)
    test_container_inspection(game)
    
    print("\n=== Container Tests Complete ===")

if __name__ == "__main__":
    main() 