from .game import Game


def run_example():
    """Run a simple example to demonstrate game functionality."""
    # Create a new game with a 5x5 board
    game = Game(width=5, height=5)
    
    # Create a player
    player = game.create_player("Adventurer", position=(0, 0))
    
    # Create some objects
    key = game.create_object(
        obj_type="item", 
        name="Brass Key", 
        position=(1, 1),
        is_movable=True, 
        weight=1,
        description="A small brass key with ornate patterns."
    )
    
    # Add usable_with property (door can be used with key)
    key.usable_with.add("door_123")
    
    table = game.create_object(
        obj_type="furniture", 
        name="Wooden Table", 
        position=(2, 2),
        is_movable=True, 
        is_jumpable=True,
        weight=10,
        description="A sturdy wooden table."
    )
    
    chest = game.create_object(
        obj_type="container", 
        name="Treasure Chest", 
        position=(3, 3),
        is_movable=False,
        is_open=False,
        capacity=5,
        description="A locked wooden chest with iron fittings."
    )
    
    door = game.create_object(
        obj_type="door", 
        name="Oak Door", 
        position=(4, 4),
        is_movable=False,
        description="A heavy oak door. It appears to be locked."
    )
    door.id = "door_123"  # Set ID to match the key's usable_with
    
    # Example actions
    print("Game example started:")
    
    # Walking
    result = game.perform_action("walk", position=(1, 0))
    print(result["message"])
    
    # Looking around
    result = game.perform_action("look")
    print(result["message"])
    print(f"Found {len(result['objects'])} objects: {[obj.name for obj in result['objects']]}")
    
    # Moving to and picking up key
    result = game.perform_action("walk", position=(1, 1))
    print(result["message"])
    
    # Moving object
    result = game.perform_action("push", object_position=(1, 1), direction=(0, 1))
    print(result["message"])
    
    # Looking at inventory
    result = game.perform_action("inventory")
    print(result["message"])
    
    # Show game messages log
    print("\nGame log:")
    for message in game.get_latest_messages():
        print(f"- {message}")

if __name__ == "__main__":
    run_example() 