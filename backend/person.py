from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple, TYPE_CHECKING
import logging

from entity import Entity, Position
from game_object import GameObject, Container

if TYPE_CHECKING:
    from agent_copywriter_direct import Environment


@dataclass
class Person(Entity):
    """A person/character that can perform actions in the game."""
    inventory: Container = None
    wearable_items: List[GameObject] = field(default_factory=list)  # Items currently being worn
    strength: int = 5  # Determines ability to move heavy objects
    
    def __post_init__(self):
        super().__post_init__()
        if self.inventory is None:
            self.inventory = Container(id=f"{self.id}_inventory", name=f"{self.name}'s Inventory")
    
    def look(self, environment: 'Environment', radius: int = 3) -> Dict[str, Any]:
        """Get nearby objects and entities within a specified radius.
        
        Args:
            environment: The environment to look in
            radius: How far to look in all directions (creates a square area)
            
        Returns:
            Dict containing:
                success: Whether the look was successful
                message: Description of what was seen
                nearby_objects: Dictionary of nearby objects with id as key
                nearby_entities: Dictionary of nearby entities with id as key
        """
        if not self.position or not environment:
            return {"success": False, "message": "Cannot look - no position or environment"}
            
        # Safely extract current x, y coordinates
        current_x: int
        current_y: int
        # Use hasattr check instead of isinstance to avoid issues with generics/type resolution
        if hasattr(self.position, 'x') and hasattr(self.position, 'y'): 
            current_x = self.position.x
            current_y = self.position.y
        elif isinstance(self.position, (tuple, list)) and len(self.position) >= 2:
            current_x = self.position[0]
            current_y = self.position[1]
        else:
            logger = logging.getLogger(__name__) # Get logger instance if needed
            logger.error(f"Invalid position type in Person.look: {type(self.position)}")
            return {"success": False, "message": f"Cannot look - invalid position format {type(self.position)}"}

        nearby_objects = {}
        nearby_entities = {}
        
        # Ensure radius is non-negative
        radius = max(0, radius)
        
        for y in range(current_y - radius, current_y + radius + 1):
            for x in range(current_x - radius, current_x + radius + 1):
                pos_tuple = (x, y)
                if pos_tuple == (current_x, current_y):
                    continue # Skip self's exact position
                    
                if not environment.is_valid_position(pos_tuple):
                    continue
                    
                entities_at_pos = environment.get_entities_at(pos_tuple)
                for entity in entities_at_pos:
                    if entity.id != self.id: # Don't list self
                        try:
                            from game_object import GameObject # Lazy import for type check
                            if isinstance(entity, GameObject):
                                nearby_objects[entity.id] = entity
                            else: # Assume it's another entity (like another Person)
                                nearby_entities[entity.id] = entity
                        except ImportError:
                             if hasattr(entity, 'is_collectable') or hasattr(entity, 'is_container'):
                                 nearby_objects[entity.id] = entity
                             else:
                                 nearby_entities[entity.id] = entity
        
        return {
            "success": True,
            "message": f"Found {len(nearby_objects)} objects and {len(nearby_entities)} entities nearby",
            "nearby_objects": nearby_objects,
            "nearby_entities": nearby_entities
        }
    
    def move(self, environment: 'Environment', target_position: Position, is_running: bool = False) -> Dict[str, Any]:
        """Move to an adjacent square (walking or running).
        
        Args:
            environment: The environment to move on
            target_position: The position to move to (can be a Position object or (x, y) tuple)
            is_running: Whether to run (move 2 tiles) or walk (move 1 tile)
            
        Returns:
            Dict containing:
                success: Whether the move was successful
                message: Description of what happened
                old_position: The position before moving (if successful)
                new_position: The position after moving (if successful)
        """
        logger = logging.getLogger(__name__) # Ensure logger is available
        # ---> LOG ENV ID <---
        logger.info(f"SYNC CHECK: Environment ID in Person.move: {id(environment)}")

        if not environment:
            return {"success": False, "message": "Environment not provided for move action."}
        if not self.position:
            return {"success": False, "message": f"{self.name} has no current position."}
        if not target_position:
             return {"success": False, "message": "Target position not provided."}

        # --- Normalize current position ---
        current_x, current_y = None, None
        if hasattr(self.position, 'x') and hasattr(self.position, 'y'):
            current_x, current_y = self.position.x, self.position.y
        elif isinstance(self.position, (tuple, list)) and len(self.position) == 2:
            current_x, current_y = self.position[0], self.position[1]
        else:
             logger.error(f"Invalid current position format for {self.name}: {self.position}")
             return {"success": False, "message": f"Invalid current position format: {self.position}"}
        current_pos_tuple = (current_x, current_y)

        # --- Normalize target position ---
        target_x, target_y = None, None
        if hasattr(target_position, 'x') and hasattr(target_position, 'y'):
            target_x, target_y = target_position.x, target_position.y
        elif isinstance(target_position, (tuple, list)) and len(target_position) == 2:
            target_x, target_y = target_position[0], target_position[1]
        else:
            logger.error(f"Invalid target position format: {target_position}")
            return {"success": False, "message": f"Invalid target position format: {target_position}"}
        target_pos_tuple = (target_x, target_y)

        # --- Validate target position ---
        if not environment.is_valid_position(target_pos_tuple):
            return {"success": False, "message": f"Target position {target_pos_tuple} is outside the environment bounds."}

        # --- Validate distance and direction ---
        dx, dy = abs(target_x - current_x), abs(target_y - current_y)
        max_distance = 2 if is_running else 1

        if dx == 0 and dy == 0:
             return {"success": False, "message": "Target position is the same as current position."}
        if dx > max_distance or dy > max_distance:
            return {"success": False, "message": f"Target position {target_pos_tuple} is too far. Max distance: {max_distance}."}
        if dx > 0 and dy > 0:
            return {"success": False, "message": "Diagonal movement is not allowed."}

        # --- Check if target is walkable/movable ---
        if not environment.can_move_to(target_pos_tuple):
            blocking_entities = environment.get_entities_at(target_pos_tuple)
            blocker_name = "an obstacle"
            if blocking_entities:
                 # Use the name of the first blocking entity found
                 blocker_name = blocking_entities[0].name if hasattr(blocking_entities[0], 'name') else "an entity"
            return {
                "success": False,
                "message": f"Cannot move to {target_pos_tuple} - blocked by {blocker_name}."
            }

        # --- Perform the move using Environment method ---
        old_position_repr = self.position # Keep original format for return
        move_success = environment.move_entity(self, target_pos_tuple)

        if not move_success:
            # Environment.move_entity should ideally log specifics if it fails
            logger.error(f"Environment.move_entity failed for {self.name} moving to {target_pos_tuple}")
            return {"success": False, "message": f"Failed to move {self.name} to {target_pos_tuple}."}

        action = "ran" if is_running else "walked"
        new_position_repr = self.position # Position should be updated by move_entity
        return {
            "success": True,
            "message": f"{self.name} {action} from {old_position_repr} to {new_position_repr}.",
            "old_position": old_position_repr,
            "new_position": new_position_repr # Return the updated position object/tuple
        }
    
    def jump(self, environment: 'Environment', target_position: Position) -> Dict[str, Any]:
        """Jump over one square to land two squares away."""
        logger = logging.getLogger(__name__)

        if not environment:
            return {"success": False, "message": "Environment not provided for jump action."}
        if not self.position:
            return {"success": False, "message": f"{self.name} has no current position."}
        if not target_position:
             return {"success": False, "message": "Target position not provided."}

        # --- Normalize current position ---
        current_x, current_y = None, None
        if hasattr(self.position, 'x') and hasattr(self.position, 'y'):
            current_x, current_y = self.position.x, self.position.y
        elif isinstance(self.position, (tuple, list)) and len(self.position) == 2:
            current_x, current_y = self.position[0], self.position[1]
        else:
             logger.error(f"Invalid current position format for {self.name}: {self.position}")
             return {"success": False, "message": f"Invalid current position format: {self.position}"}
        current_pos_tuple = (current_x, current_y)

        # --- Normalize target position ---
        target_x, target_y = None, None
        if hasattr(target_position, 'x') and hasattr(target_position, 'y'):
            target_x, target_y = target_position.x, target_position.y
        elif isinstance(target_position, (tuple, list)) and len(target_position) == 2:
            target_x, target_y = target_position[0], target_position[1]
        else:
            logger.error(f"Invalid target position format: {target_position}")
            return {"success": False, "message": f"Invalid target position format: {target_position}"}
        target_pos_tuple = (target_x, target_y)

        # --- Validate target position ---
        if not environment.is_valid_position(target_pos_tuple):
            return {"success": False, "message": f"Target position {target_pos_tuple} is outside the environment bounds."}

        # --- Validate jump distance and direction ---
        dx, dy = abs(target_x - current_x), abs(target_y - current_y)
        is_valid_jump_distance = (dx == 2 and dy == 0) or (dx == 0 and dy == 2)
        if not is_valid_jump_distance:
            return {"success": False, "message": f"Cannot jump to {target_pos_tuple}. Must jump exactly 2 squares horizontally or vertically."}

        # --- Check the middle square ---
        middle_x = (current_x + target_x) // 2
        middle_y = (current_y + target_y) // 2
        middle_pos_tuple = (middle_x, middle_y)

        # Check if middle position is valid (should be, given start/end are valid)
        if not environment.is_valid_position(middle_pos_tuple):
             logger.error(f"Calculated middle position {middle_pos_tuple} invalid for jump from {current_pos_tuple} to {target_pos_tuple}")
             return {"success": False, "message": "Cannot jump - path is invalid."} # Should not happen

        # Check what's in the middle square
        middle_entities = environment.get_entities_at(middle_pos_tuple)
        can_jump_over = False
        jump_over_name = "something"
        if not middle_entities:
            # Can jump over empty space? Maybe allow this.
            # can_jump_over = True # Uncomment if jumping over empty space is allowed
            # jump_over_name = "empty space"
             return {"success": False, "message": f"Cannot jump over empty space at {middle_pos_tuple}."}
        else:
            # Assume we check the first entity found. Add logic if multiple entities matter.
            middle_obj = middle_entities[0]
            jump_over_name = middle_obj.name if hasattr(middle_obj, 'name') else "an object"
            # Check if the object has an 'is_jumpable' attribute and it's True
            if hasattr(middle_obj, 'is_jumpable') and middle_obj.is_jumpable:
                 can_jump_over = True
            # Add other conditions? E.g., jumpable if it's not a wall, or below a certain height?

        if not can_jump_over:
            return {"success": False, "message": f"Cannot jump over {jump_over_name} at {middle_pos_tuple}."}

        # --- Check if landing spot is clear ---
        if not environment.can_move_to(target_pos_tuple):
            blocking_entities = environment.get_entities_at(target_pos_tuple)
            blocker_name = "an obstacle"
            if blocking_entities:
                 blocker_name = blocking_entities[0].name if hasattr(blocking_entities[0], 'name') else "an entity"
            return {"success": False, "message": f"Cannot land at {target_pos_tuple} - blocked by {blocker_name}."}

        # --- Perform the jump using Environment method ---
        old_position_repr = self.position # Keep original format for return
        jump_success = environment.move_entity(self, target_pos_tuple)

        if not jump_success:
            logger.error(f"Environment.move_entity failed for {self.name} jumping to {target_pos_tuple}")
            return {"success": False, "message": f"Failed to jump {self.name} to {target_pos_tuple}."}

        new_position_repr = self.position # Position should be updated by move_entity
        return {
            "success": True,
            "message": f"{self.name} jumped over {jump_over_name} from {old_position_repr} to {new_position_repr}.",
            "old_position": old_position_repr,
            "new_position": new_position_repr
        }
    
    def push(self, environment: 'Environment', object_position: Position, direction: Tuple[int, int]) -> Dict[str, Any]:
        """Push an object to an adjacent square.
        Only allows pushing in cardinal directions (up, down, left, right).
        After pushing, the person moves to the object's previous position."""
        if not self.position:
            return {"success": False, "message": "Person is not on the environment"}
            
        current_x, current_y = self.position
        obj_x, obj_y = object_position
        
        is_cardinal_adjacent = (
            (abs(obj_x - current_x) == 1 and obj_y == current_y) or  # Horizontal adjacency
            (abs(obj_y - current_y) == 1 and obj_x == current_x)     # Vertical adjacency
        )
        
        if not is_cardinal_adjacent:
            return {"success": False, "message": "Can only push objects in cardinal directions (up, down, left, right)"}
            
        obj = environment.get_object_at(object_position)
        if not obj or not obj.is_movable:
            return {"success": False, "message": "Object is not movable"}
            
        if obj.weight > self.strength:
            return {"success": False, "message": f"{obj.name} is too heavy to push"}
            
        dir_x, dir_y = direction
        target_x = obj_x + dir_x
        target_y = obj_y + dir_y
        target_position = (target_x, target_y)
        
        if not environment.is_valid_position(target_position):
            return {"success": False, "message": "Cannot push object off the environment"}
            
        if not environment.can_move_to(target_position):
            return {"success": False, "message": "Cannot push object there - position is occupied"}
            
        original_obj_pos = obj.position
        
        obj_removed = environment.remove_entity(obj)
            
        if not obj_removed:
            return {"success": False, "message": "Failed to move object from its position"}
        
        if not environment.can_move_to(original_obj_pos):
            environment.add_entity(obj, original_obj_pos)
            return {"success": False, "message": "Cannot move to object's position"}
            
        obj_moved = environment.add_entity(obj, target_position)
            
        if not obj_moved:
            environment.add_entity(obj, original_obj_pos)
            return {"success": False, "message": "Failed to move object to new position"}
            
        old_person_pos = self.position
        person_moved = environment.move_entity(self, original_obj_pos)
            
        if not person_moved:
            environment.remove_entity(obj)
            environment.add_entity(obj, original_obj_pos)
                
            return {"success": False, "message": "Failed to move to object's position"}
            
        return {
            "success": True, 
            "message": f"{self.name} pushed {obj.name} to {target_position} and moved to {original_obj_pos}",
            "old_position": old_person_pos,
            "new_position": original_obj_pos,
            "object_position": target_position
        }
    
    def pull(self, environment: 'Environment', object_position: Position) -> Dict[str, Any]:
        """Pull an object into the person's current position.
        Person must be adjacent to object in a cardinal direction.
        Person moves away from object, object moves to person's previous position.
        
        Args:
            environment: The environment to operate on
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
        if not environment or not object_position:
            return {"success": False, "message": "Invalid pull parameters"}
            
        if not self.position:
            return {"success": False, "message": "Person is not on the environment"}
            
        if not environment.is_valid_position(object_position):
            return {"success": False, "message": "Object position is outside the environment"}
            
        current_x, current_y = self.position
        obj_x, obj_y = object_position
        
        is_cardinal_adjacent = (
            (abs(obj_x - current_x) == 1 and obj_y == current_y) or  # Horizontal adjacency
            (abs(obj_y - current_y) == 1 and obj_x == current_x)     # Vertical adjacency
        )
        
        if not is_cardinal_adjacent:
            return {"success": False, "message": "Can only pull objects in cardinal directions (up, down, left, right)"}
            
        obj = environment.get_object_at(object_position)
        if not obj:
            return {"success": False, "message": "No object found at that position"}
            
        if not obj.is_movable:
            return {"success": False, "message": f"{obj.name} is not movable"}
            
        if obj.weight > self.strength:
            return {"success": False, "message": f"{obj.name} is too heavy to pull"}
            
        dir_x = current_x - obj_x
        dir_y = current_y - obj_y
        person_new_x = current_x + dir_x
        person_new_y = current_y + dir_y
        person_new_pos = (person_new_x, person_new_y)
        
        if not environment.is_valid_position(person_new_pos):
            return {"success": False, "message": "Cannot pull - would move person off the environment"}
            
        if not environment.can_move_to(person_new_pos):
            blocking_entities = environment.get_entities_at(person_new_pos)
            if blocking_entities:
                blocker = blocking_entities[0]
                return {"success": False, "message": f"Cannot pull - blocked by {blocker.name}"}
            return {"success": False, "message": "Cannot pull - no room to move backward"}
            
        old_person_pos = self.position
        old_obj_pos = obj.position
        
        obj_removed = environment.remove_entity(obj)
            
        if not obj_removed:
            return {"success": False, "message": "Failed to remove object for pull action"}
        
        person_moved = environment.move_entity(self, person_new_pos)
            
        if not person_moved:
            environment.add_entity(obj, old_obj_pos)
            return {"success": False, "message": "Failed to move to new position"}
            
        obj_moved = environment.add_entity(obj, old_person_pos)
            
        if not obj_moved:
            environment.move_entity(self, old_person_pos)
            environment.add_entity(obj, old_obj_pos)
                
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
        if (container.position and self.position and 
            abs(container.position[0] - self.position[0]) + 
            abs(container.position[1] - self.position[1]) > 1 and
            container not in self.inventory.contents):
            return {"success": False, "message": "Container is not adjacent or in inventory"}
            
        result = container.remove_item(item_id)
        if not result["success"]:
            return result
            
        item = result["item"]
        self.inventory.add_item(item)
        
        return {"success": True, "message": f"{self.name} got {item.name} from {container.name}"}
    
    def put_in_container(self, item_id: str, container: Container) -> Dict[str, Any]:
        """Put an item from inventory into a container."""
        if (container.position and self.position and 
            abs(container.position[0] - self.position[0]) + 
            abs(container.position[1] - self.position[1]) > 1 and
            container not in self.inventory.contents):
            return {"success": False, "message": "Container is not adjacent or in inventory"}
            
        result = self.inventory.remove_item(item_id)
        if not result["success"]:
            return result
            
        item = result["item"]
        result = container.add_item(item)
        
        if not result["success"]:
            self.inventory.add_item(item)
            
        return result
    
    def use_object_with(self, item1_id: str, item2_id: str, environment: 'Environment', nearby_objects: Dict[str, Entity]) -> Dict[str, Any]:
        """Use one object (item1 from inventory) with another object (item2 in inventory or nearby)."""
        item1 = self.inventory.get_item(item1_id) if hasattr(self.inventory, 'get_item') else next((i for i in self.inventory.contents if i.id == item1_id), None)
        if not item1:
            return {"success": False, "message": f"Item '{item1_id}' not found in inventory."}

        item2 = self.inventory.get_item(item2_id) if hasattr(self.inventory, 'get_item') else next((i for i in self.inventory.contents if i.id == item2_id), None)
        source = "inventory"
        if not item2:
            if item2_id in nearby_objects:
                item2 = nearby_objects[item2_id]
                source = "nearby environment"
            else:
                 if hasattr(environment, '_entity_map') and item2_id in environment._entity_map:
                      item2 = environment._entity_map[item2_id]
                      source = "world"
                 else:
                    return {"success": False, "message": f"Target object '{item2_id}' not found in inventory or nearby."}

        if not hasattr(item1, 'use_with') or not callable(item1.use_with):
             return {"success": False, "message": f"'{item1.name}' cannot be used with anything."}

        try:
             result = item1.use_with(item2) 
        except Exception as e:
             return {"success": False, "message": f"Error using '{item1.name}' with '{item2.name}': {e}"}

        if isinstance(result, dict) and result.get("success"):
            result["message"] = result.get("message", f"Used '{item1.name}' with '{item2.name}' (found in {source}).")
        elif isinstance(result, bool) and result:
             result = {"success": True, "message": f"Used '{item1.name}' with '{item2.name}' (found in {source})."}
        elif result is None: # Assume success if None is returned, provide generic message
             result = {"success": True, "message": f"Used '{item1.name}' with '{item2.name}' (found in {source}). Action completed."}
        elif isinstance(result, bool) and not result:
             result = {"success": False, "message": f"Failed to use '{item1.name}' with '{item2.name}'."}
        elif not isinstance(result, dict):
            result = {"success": False, "message": f"Unexpected result from use_with: {result}"}

        return result
    
    def say(self, message: str) -> Dict[str, Any]:
        """Say something."""
        return {
            "success": True,
            "message": f"{self.name} says: {message}"
        }
    
    def wear_item(self, item_id: str) -> Dict[str, Any]:
        """Put on a wearable item from inventory.
        
        Args:
            item_id: The ID of the item to wear
            
        Returns:
            Dict containing:
                success: Whether the action was successful
                message: Description of what happened
        """
        item = None
        for inventory_item in self.inventory.contents:
            if inventory_item.id == item_id:
                item = inventory_item
                break

        if not item:
            return {"success": False, "message": f"Item {item_id} not found in inventory"}

        if not item.is_wearable:
            return {"success": False, "message": f"{item.name} is not wearable"}

        result = self.inventory.remove_item(item_id)
        if not result["success"]:
            return result

        self.wearable_items.append(item)

        return {"success": True, "message": f"{self.name} put on {item.name}"}

    def remove_item(self, item_id: str) -> Dict[str, Any]:
        """Remove a wearable item and put it back in inventory.
        
        Args:
            item_id: The ID of the item to remove
            
        Returns:
            Dict containing:
                success: Whether the action was successful
                message: Description of what happened
        """
        item = None
        for wearable_item in self.wearable_items:
            if wearable_item.id == item_id:
                item = wearable_item
                break

        if not item:
            return {"success": False, "message": f"Item {item_id} is not being worn"}

        self.wearable_items.remove(item)

        self.inventory.add_item(item)

        return {"success": True, "message": f"{self.name} removed {item.name}"}

    def get_worn_items(self) -> List[GameObject]:
        """Get a list of all items currently being worn.
        
        Returns:
            List of wearable items
        """
        return self.wearable_items.copy()

    def is_wearing(self, item_id: str) -> bool:
        """Check if a specific item is being worn.
        
        Args:
            item_id: The ID of the item to check
            
        Returns:
            bool: Whether the item is being worn
        """
        return any(item.id == item_id for item in self.wearable_items)