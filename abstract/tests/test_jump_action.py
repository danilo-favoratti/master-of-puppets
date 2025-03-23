def test_jump_successful(engine):
    """Test successful jump scenarios (all 4 directions)"""
    tests = [
        # [player_x, player_y, middle_obj_x, middle_obj_y, jump_x, jump_y, description]
        # Jump down
        [1, 0, 1, 1, 1, 2, "Jump down"],
        # Jump up
        [1, 2, 1, 1, 1, 0, "Jump up"],
        # Jump right
        [0, 1, 1, 1, 2, 1, "Jump right"],
        # Jump left
        [2, 1, 1, 1, 0, 1, "Jump left"]
    ]
    
    for test in tests:
        player_x, player_y, middle_obj_x, middle_obj_y, jump_x, jump_y, desc = test
        
        print(f"\n=== Test: {desc} ===")
        
        # Setup the board with player
        engine.move_entity(engine.player["id"], player_x, player_y)
        
        # Create a jumpable object in the middle position
        middle_obj_id = "jumpable_obj"
        if middle_obj_id not in engine.entities:
            middle_obj = {
                "id": middle_obj_id, 
                "type": "furniture", 
                "name": "Jumpable Object",
                "position": {"x": middle_obj_x, "y": middle_obj_y},
                "is_movable": False,
                "is_jumpable": True  # Critical for jump tests
            }
            engine.entities[middle_obj_id] = middle_obj
            engine.board[middle_obj_y][middle_obj_x] = "furniture"
            engine.entity_positions[(middle_obj_x, middle_obj_y)] = middle_obj_id
        else:
            # Update position if object already exists
            engine.move_entity(middle_obj_id, middle_obj_x, middle_obj_y)
            engine.entities[middle_obj_id]["is_jumpable"] = True
        
        print(f"Setup: Player at ({player_x}, {player_y}), Jumpable object at ({middle_obj_x}, {middle_obj_y})")
        print("Initial board state:")
        engine.print_board()
        
        # Attempt to jump
        result = engine.move_entity(engine.player["id"], jump_x, jump_y)
        
        # Verify the position
        player_pos = engine.player["position"]
        
        # Check if jump was successful
        success = (
            result and
            player_pos["x"] == jump_x and
            player_pos["y"] == jump_y
        )
        
        print(f"Jump result: {success}")
        print(f"Player: ({player_pos['x']}, {player_pos['y']})")
        
        # Show the board
        print("Final board state:")
        engine.print_board()

def test_jump_failures(engine):
    """Test jump failure scenarios"""
    tests = [
        # [desc, player_x, player_y, middle_obj_x, middle_obj_y, jump_x, jump_y, make_jumpable]
        # No object in the middle
        ["No middle object", 0, 0, None, None, 2, 0, False],
        # Object in middle is not jumpable
        ["Non-jumpable object", 0, 0, 1, 0, 2, 0, False],
        # Target position is off the board
        ["Target off board", 0, 0, 1, 0, 3, 0, True],
        # Target position is occupied
        ["Target occupied", 0, 0, 1, 0, 2, 0, True],
        # Jump distance too short (1 space)
        ["Too short (1 space)", 0, 0, None, None, 1, 0, False],
        # Jump distance too long (3+ spaces)
        ["Too long (3 spaces)", 0, 0, 1, 0, 3, 0, True],
        # Diagonal jump (not allowed)
        ["Diagonal jump", 0, 0, 1, 1, 2, 2, True],
    ]
    
    for test in tests:
        desc, player_x, player_y, middle_obj_x, middle_obj_y, jump_x, jump_y, make_jumpable = test
        
        print(f"\n=== Test Failure: {desc} ===")
        
        # Reset the board
        # Clear existing objects
        for entity_id in list(engine.entities.keys()):
            if entity_id != engine.player["id"] and entity_id.startswith("jumpable_obj"):
                del engine.entities[entity_id]
                
        # Position the player
        engine.move_entity(engine.player["id"], player_x, player_y)
        
        # Create middle object if needed
        if middle_obj_x is not None and middle_obj_y is not None:
            middle_obj_id = "jumpable_obj"
            middle_obj = {
                "id": middle_obj_id,
                "type": "furniture",
                "name": "Object",
                "position": {"x": middle_obj_x, "y": middle_obj_y},
                "is_movable": False,
                "is_jumpable": make_jumpable
            }
            engine.entities[middle_obj_id] = middle_obj
            engine.board[middle_obj_y][middle_obj_x] = "furniture"
            engine.entity_positions[(middle_obj_x, middle_obj_y)] = middle_obj_id
        
        # Create blocking object at target for "Target occupied" test
        if desc == "Target occupied":
            blocking_id = "blocking_obj"
            blocking = {
                "id": blocking_id,
                "type": "furniture",
                "name": "Blocking Object",
                "position": {"x": jump_x, "y": jump_y},
                "is_movable": False
            }
            engine.entities[blocking_id] = blocking
            engine.board[jump_y][jump_x] = "furniture"
            engine.entity_positions[(jump_x, jump_y)] = blocking_id
            
        print("Initial board state:")
        engine.print_board()
        
        # Attempt to jump
        result = engine.move_entity(engine.player["id"], jump_x, jump_y)
        
        print(f"Jump attempt result: {'Failed as expected' if not result else 'Unexpectedly succeeded'}")
        print("Final board state:")
        engine.print_board()
        
        # Clean up any test objects
        if desc == "Target occupied":
            if "blocking_obj" in engine.entities:
                del engine.entities["blocking_obj"]
                engine.board[jump_y][jump_x] = None
                del engine.entity_positions[(jump_x, jump_y)]

def test_jump_edge_cases(engine):
    """Test jump edge cases"""
    tests = [
        # Test jumping to board edges
        ["Jump to edge (right)", 0, 1, 1, 1, 2, 1, True],
        ["Jump to edge (left)", 2, 1, 1, 1, 0, 1, True], 
        ["Jump to edge (top)", 1, 2, 1, 1, 1, 0, True],
        ["Jump to edge (bottom)", 1, 0, 1, 1, 1, 2, True],
        
        # Test jumping over different object types
        ["Jump over container", 0, 1, 1, 1, 2, 1, True, "container"],
        ["Jump over furniture", 0, 1, 1, 1, 2, 1, True, "furniture"],
        ["Jump over door", 0, 1, 1, 1, 2, 1, True, "door"],
    ]
    
    for test in tests:
        if len(test) >= 8:
            desc, player_x, player_y, middle_obj_x, middle_obj_y, jump_x, jump_y, make_jumpable, obj_type = test
        else:
            desc, player_x, player_y, middle_obj_x, middle_obj_y, jump_x, jump_y, make_jumpable = test
            obj_type = "furniture"
        
        print(f"\n=== Test Edge Case: {desc} ===")
        
        # Position the player
        engine.move_entity(engine.player["id"], player_x, player_y)
        
        # Create or update middle object
        middle_obj_id = f"jumpable_{obj_type}"
        
        if middle_obj_id in engine.entities:
            # Update existing object
            engine.move_entity(middle_obj_id, middle_obj_x, middle_obj_y)
            engine.entities[middle_obj_id]["is_jumpable"] = make_jumpable
        else:
            # Create new object
            middle_obj = {
                "id": middle_obj_id,
                "type": obj_type,
                "name": f"Jumpable {obj_type.capitalize()}",
                "position": {"x": middle_obj_x, "y": middle_obj_y},
                "is_movable": False,
                "is_jumpable": make_jumpable
            }
            engine.entities[middle_obj_id] = middle_obj
            engine.board[middle_obj_y][middle_obj_x] = obj_type
            engine.entity_positions[(middle_obj_x, middle_obj_y)] = middle_obj_id
        
        print(f"Setup: Player at ({player_x}, {player_y}), {obj_type} at ({middle_obj_x}, {middle_obj_y})")
        print("Initial board state:")
        engine.print_board()
        
        # Attempt to jump
        result = engine.move_entity(engine.player["id"], jump_x, jump_y)
        
        # Verify the position
        player_pos = engine.player["position"]
        
        expected_success = (0 <= jump_x < engine.width and 0 <= jump_y < engine.height and make_jumpable)
        actual_success = result and player_pos["x"] == jump_x and player_pos["y"] == jump_y
        
        print(f"Jump expected result: {'Success' if expected_success else 'Failure'}")
        print(f"Jump actual result: {'Success' if actual_success else 'Failure'}")
        print(f"Player: ({player_pos['x']}, {player_pos['y']})")
        
        # Show the board
        print("Final board state:")
        engine.print_board()

def run_jump_tests(engine):
    """Run all jump tests"""
    print("\n==== JUMP ACTION TESTS ====")
    
    # Only run if board is at least 3x3
    if engine.width < 3 or engine.height < 3:
        print("Board too small for jump tests (need at least 3x3)")
        return
    
    test_jump_successful(engine)
    test_jump_failures(engine)
    test_jump_edge_cases(engine)

def main():
    """Run all action tests"""
    print("=== ACTION TEST SUITE ===")
    
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
    
    # Run the test suites
    if engine.width >= 3 and engine.height >= 3:
        test_push_successful(engine)
        test_push_failures(engine)
        test_blocked_push(engine)
        run_jump_tests(engine)  # Add jump tests
    else:
        print("Board too small for tests (need at least 3x3)")