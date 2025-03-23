from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set, Tuple
from model.entity import Entity, Position
from model.game_object import GameObject, Container

@dataclass
class Person(Entity):
    """A person/character that can perform actions in the game."""
    inventory: Container = None
    strength: int = 5  # Determines ability to move heavy objects
    
    def __post_init__(self):
        super().__post_init__()
        if self.inventory is None:
            self.inventory = Container(id=f"{self.id}_inventory", name=f"{self.name}'s Inventory")
    
    def move(self, game_board, target_position: Position, is_running: bool = False) -> Dict[str, Any]:
        """Move to an adjacent square (walking or running).
        
        Args:
            game_board: The game board to move on
            target_position: The position to move to
            is_running: Whether to run (move up to 2 tiles) or walk (move 1 tile)
            
        Returns:
            Dict containing:
                success: Whether the move was successful
                message: Description of what happened
                old_position: The position before moving (if successful)
                new_position: The position after moving (if successful)
        """
        # Validate inputs
        if not game_board or not target_position:
            return {"success": False, "message": "Invalid movement parameters"}
            
        if not self.position:
            return {"success": False, "message": "Person is not on the board"}
            
        # Validate target position is within board
        if not game_board.is_valid_position(target_position):
            return {"success": False, "message": "Target position is outside the board"}
            
        # Calculate distance
        current_x, current_y = self.position
        target_x, target_y = target_position
        dx, dy = abs(target_x - current_x), abs(target_y - current_y)
        
        # Check if target is adjacent (or two tiles away if running)
        max_distance = 2 if is_running else 1
        if dx > max_distance or dy > max_distance:
            return {"success": False, "message": f"Target position too far (max distance is {max_distance})"}
            
        # Prevent diagonal movement
        if dx > 0 and dy > 0:
            return {"success": False, "message": "Diagonal movement not allowed"}
            
        # Store old position for return value
        old_position = self.position
        
        # Check if target is occupied or blocked
        if not game_board.can_move_to(target_position):
            # Get what's blocking the way
            blocking_entities = game_board.get_entities_at(target_position)
            if blocking_entities:
                blocker = blocking_entities[0]
                return {
                    "success": False, 
                    "message": f"Cannot move to {target_position} - blocked by {blocker.name}"
                }
            return {"success": False, "message": "Target position is occupied or not walkable"}
            
        # Perform the move
        if not game_board.move_entity(self, target_position):
            return {"success": False, "message": "Failed to move to target position"}
            
        action = "ran to" if is_running else "walked to"
        return {
            "success": True, 
            "message": f"{self.name} {action} {target_position}",
            "old_position": old_position,
            "new_position": target_position
        }
    
    def jump(self, game_board, target_position: Position) -> Dict[str, Any]:
        """Jump over one square to land two squares away."""
        if not self.position:
            return {"success": False, "message": "Person is not on the board"}
            
        # Calculate distance and middle position
        current_x, current_y = self.position
        target_x, target_y = target_position
        
        # Must be exactly 2 squares away in one direction
        if not ((abs(target_x - current_x) == 2 and target_y == current_y) or 
                (abs(target_y - current_y) == 2 and target_x == current_x)):
            return {"success": False, "message": "Can only jump exactly 2 squares in a straight line"}
            
        # Calculate middle position
        middle_x = (current_x + target_x) // 2
        middle_y = (current_y + target_y) // 2
        middle_position = (middle_x, middle_y)
        
        # Check if middle position has a jumpable object
        middle_obj = game_board.get_object_at(middle_position)
        if not middle_obj or not middle_obj.is_jumpable:
            return {"success": False, "message": "Cannot jump over this object"}
            
        # Check if target position is free
        if not game_board.can_move_to(target_position):
            return {"success": False, "message": "Target position is occupied"}
            
        # Perform the jump
        game_board.move_entity(self, target_position)
        return {"success": True, "message": f"{self.name} jumped to {target_position}"}
    
    def push(self, game_board, object_position: Position, direction: Tuple[int, int]) -> Dict[str, Any]:
        """Push an object to an adjacent square.
        Only allows pushing in cardinal directions (up, down, left, right).
        After pushing, the person moves to the object's previous position."""
        if not self.position:
            return {"success": False, "message": "Person is not on the board"}
            
        # Check if object is adjacent in a cardinal direction (not diagonal)
        current_x, current_y = self.position
        obj_x, obj_y = object_position
        
        # Stricter adjacency check - must be exactly one step in only one direction
        is_cardinal_adjacent = (
            (abs(obj_x - current_x) == 1 and obj_y == current_y) or  # Horizontal adjacency
            (abs(obj_y - current_y) == 1 and obj_x == current_x)     # Vertical adjacency
        )
        
        if not is_cardinal_adjacent:
            return {"success": False, "message": "Can only push objects in cardinal directions (up, down, left, right)"}
            
        # Get the object and check if it's movable
        obj = game_board.get_object_at(object_position)
        if not obj or not obj.is_movable:
            return {"success": False, "message": "Object is not movable"}
            
        # Check if object is too heavy
        if obj.weight > self.strength:
            return {"success": False, "message": f"{obj.name} is too heavy to push"}
            
        # Use the provided direction to calculate target position
        dir_x, dir_y = direction
        target_x = obj_x + dir_x
        target_y = obj_y + dir_y
        target_position = (target_x, target_y)
        
        # Check if target position is within board bounds and free
        if not game_board.is_valid_position(target_position):
            return {"success": False, "message": "Cannot push object off the board"}
            
        if not game_board.can_move_to(target_position):
            return {"success": False, "message": "Cannot push object there - position is occupied"}
            
        # Store the object's original position
        original_obj_pos = obj.position
        
        # Temporarily remove object from its position
        game_board.remove_entity(obj)
        
        # Check if person can move to object's position
        if not game_board.can_move_to(original_obj_pos):
            # Put object back and fail
            game_board.add_entity(obj, original_obj_pos)
            return {"success": False, "message": "Cannot move to object's position"}
            
        # Move the object to new position
        if not game_board.add_entity(obj, target_position):
            # If failed, put object back and fail
            game_board.add_entity(obj, original_obj_pos)
            return {"success": False, "message": "Failed to move object to new position"}
            
        # Move person to object's original position
        old_person_pos = self.position
        if not game_board.move_entity(self, original_obj_pos):
            # If failed, put everything back
            game_board.move_entity(obj, original_obj_pos)
            return {"success": False, "message": "Failed to move to object's position"}
            
        return {
            "success": True, 
            "message": f"{self.name} pushed {obj.name} to {target_position} and moved to {original_obj_pos}",
            "old_position": old_person_pos,
            "new_position": original_obj_pos,
            "object_position": target_position
        }
    
    def pull(self, game_board, object_position: Position) -> Dict[str, Any]:
        """Pull an object into the person's current position.
        Person must be adjacent to object in a cardinal direction.
        Person moves away from object, object moves to person's previous position.
        
        Args:
            game_board: The game board to operate on
            object_position: The position of the object to pull
            
        Returns:
            Dict containing:
                success: Whether the pull was successful
                message: Description of what happened
                old_position: The person's position before moving (if successful)
                new_position: The person's position after moving (if successful)
                object_old_position: The object's original position (if successful)
                object_new_position: The object's new position (if successful)
        """
        # Validate inputs
        if not game_board or not object_position:
            return {"success": False, "message": "Invalid pull parameters"}
            
        if not self.position:
            return {"success": False, "message": "Person is not on the board"}
            
        if not game_board.is_valid_position(object_position):
            return {"success": False, "message": "Object position is outside the board"}
            
        # Check if object is adjacent in a cardinal direction (not diagonal)
        current_x, current_y = self.position
        obj_x, obj_y = object_position
        
        # Stricter adjacency check - must be exactly one step in only one direction
        is_cardinal_adjacent = (
            (abs(obj_x - current_x) == 1 and obj_y == current_y) or  # Horizontal adjacency
            (abs(obj_y - current_y) == 1 and obj_x == current_x)     # Vertical adjacency
        )
        
        if not is_cardinal_adjacent:
            return {"success": False, "message": "Can only pull objects in cardinal directions (up, down, left, right)"}
            
        # Get the object and check if it's movable
        obj = game_board.get_object_at(object_position)
        if not obj:
            return {"success": False, "message": "No object found at that position"}
            
        if not obj.is_movable:
            return {"success": False, "message": f"{obj.name} is not movable"}
            
        # Check if object is too heavy
        if obj.weight > self.strength:
            return {"success": False, "message": f"{obj.name} is too heavy to pull"}
            
        # Calculate direction and person's new position (away from object)
        dir_x = current_x - obj_x
        dir_y = current_y - obj_y
        person_new_x = current_x + dir_x
        person_new_y = current_y + dir_y
        person_new_pos = (person_new_x, person_new_y)
        
        # Check if new position is within board bounds
        if not game_board.is_valid_position(person_new_pos):
            return {"success": False, "message": "Cannot pull - would move person off the board"}
            
        # Check if person can move to new position
        if not game_board.can_move_to(person_new_pos):
            blocking_entities = game_board.get_entities_at(person_new_pos)
            if blocking_entities:
                blocker = blocking_entities[0]
                return {"success": False, "message": f"Cannot pull - blocked by {blocker.name}"}
            return {"success": False, "message": "Cannot pull - no room to move backward"}
            
        # Store original positions
        old_person_pos = self.position
        old_obj_pos = obj.position
        
        # Temporarily remove object from board
        game_board.remove_entity(obj)
        
        # Try to move person first
        if not game_board.move_entity(self, person_new_pos):
            # If failed, restore object and fail
            game_board.add_entity(obj, old_obj_pos)
            return {"success": False, "message": "Failed to move to new position"}
            
        # Now move object to person's old position
        if not game_board.add_entity(obj, old_person_pos):
            # If failed, move person back and restore object
            game_board.move_entity(self, old_person_pos)
            game_board.add_entity(obj, old_obj_pos)
            return {"success": False, "message": "Failed to move object"}
            
        return {
            "success": True, 
            "message": f"{self.name} pulled {obj.name} to {old_person_pos}",
            "old_position": old_person_pos,
            "new_position": person_new_pos,
            "object_old_position": old_obj_pos,
            "object_new_position": old_person_pos
        }
    
    def get_from_container(self, container: Container, item_id: str) -> Dict[str, Any]:
        """Get an item from a container and put it in inventory."""
        # Check if container is adjacent or in inventory
        if (container.position and self.position and 
            abs(container.position[0] - self.position[0]) + 
            abs(container.position[1] - self.position[1]) > 1 and
            container not in self.inventory.contents):
            return {"success": False, "message": "Container is not adjacent or in inventory"}
            
        # Try to remove the item from container
        result = container.remove_item(item_id)
        if not result["success"]:
            return result
            
        # Add item to inventory
        item = result["item"]
        self.inventory.add_item(item)
        
        return {"success": True, "message": f"{self.name} got {item.name} from {container.name}"}
    
    def put_in_container(self, item_id: str, container: Container) -> Dict[str, Any]:
        """Put an item from inventory into a container."""
        # Check if container is adjacent or in inventory
        if (container.position and self.position and 
            abs(container.position[0] - self.position[0]) + 
            abs(container.position[1] - self.position[1]) > 1 and
            container not in self.inventory.contents):
            return {"success": False, "message": "Container is not adjacent or in inventory"}
            
        # Try to remove the item from inventory
        result = self.inventory.remove_item(item_id)
        if not result["success"]:
            return result
            
        # Add item to container
        item = result["item"]
        result = container.add_item(item)
        
        if not result["success"]:
            # If container cannot accept item, put it back in inventory
            self.inventory.add_item(item)
            
        return result
    
    def use_object_with(self, item1_id: str, item2_id: str) -> Dict[str, Any]:
        """Use one object with another."""
        # Find item1 in inventory
        item1 = None
        for item in self.inventory.contents:
            if item.id == item1_id:
                item1 = item
                break
                
        if not item1:
            return {"success": False, "message": f"Item {item1_id} not found in inventory"}
            
        # Check if item2 is in inventory or adjacent
        item2 = None
        for item in self.inventory.contents:
            if item.id == item2_id:
                item2 = item
                break
                
        # If item2 not in inventory, it must be adjacent on the board
        # (This logic would require access to the game board to check adjacency)
        
        if not item2:
            return {"success": False, "message": f"Item {item2_id} not found in inventory or not adjacent"}
            
        # Use the items together
        return item1.use_with(item2_id)
    
    def look(self, game_board, direction: Optional[Tuple[int, int]] = None) -> Dict[str, Any]:
        """Look around or in a specific direction to find objects."""
        if not self.position:
            return {"success": False, "message": "Person is not on the board"}
            
        if direction:
            # Look in a specific direction
            dir_x, dir_y = direction
            x, y = self.position
            visible_positions = [(x + dir_x, y + dir_y)]
        else:
            # Look in all directions (including diagonals)
            x, y = self.position
            visible_positions = [
                (x+1, y), (x-1, y), (x, y+1), (x, y-1),
                (x+1, y+1), (x+1, y-1), (x-1, y+1), (x-1, y-1)
            ]
            
        # Find visible objects
        visible_objects = []
        for pos in visible_positions:
            if game_board.is_valid_position(pos):
                objects = game_board.get_entities_at(pos)
                visible_objects.extend(objects)
                
        return {
            "success": True,
            "message": f"{self.name} looked around and saw {len(visible_objects)} objects",
            "objects": visible_objects
        }
        
    def say(self, message: str) -> Dict[str, Any]:
        """Say something."""
        return {
            "success": True,
            "message": f"{self.name} says: {message}"
        } 