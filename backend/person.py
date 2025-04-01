from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, TYPE_CHECKING

from entity import Entity, Position
from game_object import GameObject, Container

# Conditionally import Environment only for type checking to avoid circular import
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
            
        current_x, current_y = self.position
        nearby_objects = {}
        nearby_entities = {}
        
        # Scan the area around the person
        for y in range(current_y - radius, current_y + radius + 1):
            for x in range(current_x - radius, current_x + radius + 1):
                # Skip the person's own position
                if (x, y) == self.position:
                    continue
                    
                # Check if position is valid
                if not environment.is_valid_position((x, y)):
                    continue
                    
                # Get objects at this position
                obj = environment.get_object_at((x, y))
                if obj:
                    nearby_objects[obj.id] = obj
                    
                # Get entities at this position
                entities = environment.get_entities_at((x, y))
                for entity in entities:
                    if entity.id != self.id:  # Skip self
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
            target_position: The position to move to
            is_running: Whether to run (move 2 tiles) or walk (move 1 tile)
            
        Returns:
            Dict containing:
                success: Whether the move was successful
                message: Description of what happened
                old_position: The position before moving (if successful)
                new_position: The position after moving (if successful)
        """
        # Validate inputs
        if not environment or not target_position:
            return {"success": False, "message": "Invalid movement parameters"}
            
        if not self.position:
            return {"success": False, "message": "Person is not on the environment"}
            
        # Validate target position is within environment
        if not environment.is_valid_position(target_position):
            return {"success": False, "message": "Target position is outside the environment"}
            
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
        if not environment.can_move_to(target_position):
            # Get what's blocking the way
            blocking_entities = environment.get_entities_at(target_position)
            if blocking_entities:
                blocker = blocking_entities[0]
                return {
                    "success": False, 
                    "message": f"Cannot move to {target_position} - blocked by {blocker.name}"
                }
            return {"success": False, "message": "Target position is occupied or not walkable"}
            
        # Perform the move - try to use move_entity if available, otherwise update position directly
        move_success = False
        
        # Try the Board/Environment move_entity method first if it exists
        if hasattr(environment, 'move_entity') and callable(environment.move_entity):
            move_success = environment.move_entity(self, target_position)
        else:
            # Direct position update if environment doesn't have move_entity
            # Update position maps if they exist
            if hasattr(environment, '_position_map'):
                # Remove from old position in the map
                if old_position in environment._position_map:
                    position_entities = environment._position_map[old_position]
                    if self in position_entities:
                        position_entities.remove(self)
                    
                    # Clean up empty positions
                    if not position_entities:
                        del environment._position_map[old_position]
                
                # Add to new position in the map
                if target_position not in environment._position_map:
                    environment._position_map[target_position] = []
                environment._position_map[target_position].append(self)
            
            # Update entity_map if it exists
            if hasattr(environment, '_entity_map') and hasattr(self, 'id'):
                environment._entity_map[self.id] = self
            
            # Update the entity's own position
            self.position = target_position
            move_success = True
        
        if not move_success:
            return {"success": False, "message": "Failed to move to target position"}
            
        action = "ran to" if is_running else "walked to"
        return {
            "success": True, 
            "message": f"{self.name} {action} {target_position}",
            "old_position": old_position,
            "new_position": target_position
        }
    
    def jump(self, environment: 'Environment', target_position: Position) -> Dict[str, Any]:
        """Jump over one square to land two squares away."""
        if not self.position:
            return {"success": False, "message": "Person is not on the environment"}
            
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
        middle_obj = environment.get_object_at(middle_position)
        if not middle_obj or not middle_obj.is_jumpable:
            return {"success": False, "message": "Cannot jump over this object"}
            
        # Check if target position is free
        if not environment.can_move_to(target_position):
            return {"success": False, "message": "Target position is occupied"}
        
        # Store old position    
        old_position = self.position
            
        # Perform the jump - using move_entity if available, otherwise direct update
        jump_success = False
        
        if hasattr(environment, 'move_entity') and callable(environment.move_entity):
            jump_success = environment.move_entity(self, target_position)
        else:
            # Direct position update if environment doesn't have move_entity
            # Update position maps if they exist
            if hasattr(environment, '_position_map'):
                # Remove from old position in the map
                if old_position in environment._position_map:
                    position_entities = environment._position_map[old_position]
                    if self in position_entities:
                        position_entities.remove(self)
                    
                    # Clean up empty positions
                    if not position_entities:
                        del environment._position_map[old_position]
                
                # Add to new position in the map
                if target_position not in environment._position_map:
                    environment._position_map[target_position] = []
                environment._position_map[target_position].append(self)
            
            # Update entity_map if it exists
            if hasattr(environment, '_entity_map') and hasattr(self, 'id'):
                environment._entity_map[self.id] = self
            
            # Update the entity's own position
            self.position = target_position
            jump_success = True
        
        if not jump_success:
            return {"success": False, "message": "Failed to jump to target position"}
            
        return {"success": True, "message": f"{self.name} jumped to {target_position}"}
    
    def push(self, environment: 'Environment', object_position: Position, direction: Tuple[int, int]) -> Dict[str, Any]:
        """Push an object to an adjacent square.
        Only allows pushing in cardinal directions (up, down, left, right).
        After pushing, the person moves to the object's previous position."""
        if not self.position:
            return {"success": False, "message": "Person is not on the environment"}
            
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
        obj = environment.get_object_at(object_position)
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
        
        # Check if target position is within environment bounds and free
        if not environment.is_valid_position(target_position):
            return {"success": False, "message": "Cannot push object off the environment"}
            
        if not environment.can_move_to(target_position):
            return {"success": False, "message": "Cannot push object there - position is occupied"}
            
        # Store the object's original position
        original_obj_pos = obj.position
        
        # Helper function for direct entity removal without remove_entity method
        def direct_remove_entity(entity):
            if hasattr(environment, '_position_map') and entity.position:
                position_entities = environment._position_map.get(entity.position, [])
                if entity in position_entities:
                    position_entities.remove(entity)
                    
                # Clean up empty positions
                if not position_entities and entity.position in environment._position_map:
                    del environment._position_map[entity.position]
            
            # Remove from entity map but don't change entity's position yet
            if hasattr(environment, '_entity_map') and hasattr(entity, 'id'):
                if entity.id in environment._entity_map:
                    del environment._entity_map[entity.id]
            
            return True
            
        # Helper function for direct entity addition without add_entity method
        def direct_add_entity(entity, position):
            # Update entity's position
            old_pos = entity.position
            entity.position = position
            
            # Add to position map
            if hasattr(environment, '_position_map'):
                if position not in environment._position_map:
                    environment._position_map[position] = []
                environment._position_map[position].append(entity)
            
            # Add to entity map
            if hasattr(environment, '_entity_map') and hasattr(entity, 'id'):
                environment._entity_map[entity.id] = entity
                
            return True
        
        # Temporarily remove object from its position
        obj_removed = False
        if hasattr(environment, 'remove_entity') and callable(environment.remove_entity):
            obj_removed = environment.remove_entity(obj)
        else:
            obj_removed = direct_remove_entity(obj)
            
        if not obj_removed:
            return {"success": False, "message": "Failed to move object from its position"}
        
        # Check if person can move to object's position
        if not environment.can_move_to(original_obj_pos):
            # Put object back and fail - using add_entity if available
            if hasattr(environment, 'add_entity') and callable(environment.add_entity):
                environment.add_entity(obj, original_obj_pos)
            else:
                direct_add_entity(obj, original_obj_pos)
            return {"success": False, "message": "Cannot move to object's position"}
            
        # Move the object to new position - using add_entity if available
        obj_moved = False
        if hasattr(environment, 'add_entity') and callable(environment.add_entity):
            obj_moved = environment.add_entity(obj, target_position)
        else:
            obj_moved = direct_add_entity(obj, target_position)
            
        if not obj_moved:
            # If failed, put object back and fail
            if hasattr(environment, 'add_entity') and callable(environment.add_entity):
                environment.add_entity(obj, original_obj_pos)
            else:
                direct_add_entity(obj, original_obj_pos)
            return {"success": False, "message": "Failed to move object to new position"}
            
        # Move person to object's original position
        old_person_pos = self.position
        person_moved = False
        
        if hasattr(environment, 'move_entity') and callable(environment.move_entity):
            person_moved = environment.move_entity(self, original_obj_pos)
        else:
            # Remove person from current position
            direct_remove_entity(self)
            # Add to new position
            person_moved = direct_add_entity(self, original_obj_pos)
            
        if not person_moved:
            # If failed, put everything back
            if hasattr(environment, 'move_entity') and callable(environment.move_entity):
                # Remove object from target
                if hasattr(environment, 'remove_entity') and callable(environment.remove_entity):
                    environment.remove_entity(obj)
                else:
                    direct_remove_entity(obj)
                # Put object back
                if hasattr(environment, 'add_entity') and callable(environment.add_entity):
                    environment.add_entity(obj, original_obj_pos)
                else:
                    direct_add_entity(obj, original_obj_pos)
            else:
                # Direct updates for rollback
                direct_remove_entity(obj)
                direct_add_entity(obj, original_obj_pos)
                # Restore person's position
                self.position = old_person_pos
                
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
        # Validate inputs
        if not environment or not object_position:
            return {"success": False, "message": "Invalid pull parameters"}
            
        if not self.position:
            return {"success": False, "message": "Person is not on the environment"}
            
        if not environment.is_valid_position(object_position):
            return {"success": False, "message": "Object position is outside the environment"}
            
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
        obj = environment.get_object_at(object_position)
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
        
        # Check if new position is within environment bounds
        if not environment.is_valid_position(person_new_pos):
            return {"success": False, "message": "Cannot pull - would move person off the environment"}
            
        # Check if person can move to new position
        if not environment.can_move_to(person_new_pos):
            blocking_entities = environment.get_entities_at(person_new_pos)
            if blocking_entities:
                blocker = blocking_entities[0]
                return {"success": False, "message": f"Cannot pull - blocked by {blocker.name}"}
            return {"success": False, "message": "Cannot pull - no room to move backward"}
            
        # Store original positions
        old_person_pos = self.position
        old_obj_pos = obj.position
        
        # Helper function for direct entity removal without remove_entity method
        def direct_remove_entity(entity):
            if hasattr(environment, '_position_map') and entity.position:
                position_entities = environment._position_map.get(entity.position, [])
                if entity in position_entities:
                    position_entities.remove(entity)
                    
                # Clean up empty positions
                if not position_entities and entity.position in environment._position_map:
                    del environment._position_map[entity.position]
            
            # Remove from entity map but don't change entity's position yet
            if hasattr(environment, '_entity_map') and hasattr(entity, 'id'):
                if entity.id in environment._entity_map:
                    del environment._entity_map[entity.id]
            
            return True
            
        # Helper function for direct entity addition without add_entity method
        def direct_add_entity(entity, position):
            # Update entity's position
            entity.position = position
            
            # Add to position map
            if hasattr(environment, '_position_map'):
                if position not in environment._position_map:
                    environment._position_map[position] = []
                environment._position_map[position].append(entity)
            
            # Add to entity map
            if hasattr(environment, '_entity_map') and hasattr(entity, 'id'):
                environment._entity_map[entity.id] = entity
                
            return True
            
        # Temporarily remove object from environment
        obj_removed = False
        if hasattr(environment, 'remove_entity') and callable(environment.remove_entity):
            obj_removed = environment.remove_entity(obj)
        else:
            obj_removed = direct_remove_entity(obj)
            
        if not obj_removed:
            return {"success": False, "message": "Failed to remove object for pull action"}
        
        # Try to move person first
        person_moved = False
        if hasattr(environment, 'move_entity') and callable(environment.move_entity):
            person_moved = environment.move_entity(self, person_new_pos)
        else:
            # Remove person from current position using direct update
            direct_remove_entity(self)
            # Add person to new position
            person_moved = direct_add_entity(self, person_new_pos)
            
        if not person_moved:
            # If failed, restore object and fail
            if hasattr(environment, 'add_entity') and callable(environment.add_entity):
                environment.add_entity(obj, old_obj_pos)
            else:
                direct_add_entity(obj, old_obj_pos)
            return {"success": False, "message": "Failed to move to new position"}
            
        # Now move object to person's old position
        obj_moved = False
        if hasattr(environment, 'add_entity') and callable(environment.add_entity): 
            obj_moved = environment.add_entity(obj, old_person_pos)
        else:
            obj_moved = direct_add_entity(obj, old_person_pos)
            
        if not obj_moved:
            # If failed, move person back and restore object
            if hasattr(environment, 'move_entity') and callable(environment.move_entity):
                environment.move_entity(self, old_person_pos)
                if hasattr(environment, 'add_entity') and callable(environment.add_entity):
                    environment.add_entity(obj, old_obj_pos)
                else:
                    direct_add_entity(obj, old_obj_pos) 
            else:
                # Direct updates for rollback
                direct_remove_entity(self)
                direct_add_entity(self, old_person_pos)
                direct_add_entity(obj, old_obj_pos)
                
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
    
    def use_object_with(self, item1_id: str, item2_id: str, environment: 'Environment', nearby_objects: Dict[str, Entity]) -> Dict[str, Any]:
        """Use one object (item1 from inventory) with another object (item2 in inventory or nearby)."""
        # Find item1 in inventory
        # Assuming Container has a method like get_item(item_id)
        item1 = self.inventory.get_item(item1_id) if hasattr(self.inventory, 'get_item') else next((i for i in self.inventory.contents if i.id == item1_id), None)
        if not item1:
            return {"success": False, "message": f"Item '{item1_id}' not found in inventory."}

        # Find item2 (first check inventory, then nearby objects)
        item2 = self.inventory.get_item(item2_id) if hasattr(self.inventory, 'get_item') else next((i for i in self.inventory.contents if i.id == item2_id), None)
        source = "inventory"
        if not item2:
            if item2_id in nearby_objects:
                item2 = nearby_objects[item2_id]
                source = "nearby environment"
            else:
                 # Last check: search the whole environment map if nearby failed
                 if hasattr(environment, '_entity_map') and item2_id in environment._entity_map:
                      item2 = environment._entity_map[item2_id]
                      source = "world"
                 else:
                    return {"success": False, "message": f"Target object '{item2_id}' not found in inventory or nearby."}

        # Check if item1 can be used with item2
        if not hasattr(item1, 'use_with') or not callable(item1.use_with):
             return {"success": False, "message": f"'{item1.name}' cannot be used with anything."}

        # Call the item's specific use_with logic
        # Pass necessary context if the item's use_with needs it (e.g., environment, target object)
        # Assuming item1.use_with might need the target object itself
        # Modify based on what item1.use_with actually needs. 
        # Simplest case: pass target object.
        try:
             result = item1.use_with(item2) 
        except Exception as e:
             # Catch potential errors if use_with signature is wrong or logic fails
             return {"success": False, "message": f"Error using '{item1.name}' with '{item2.name}': {e}"}

        # Update success message to include source if result is a dict
        if isinstance(result, dict) and result.get("success"):
            result["message"] = result.get("message", f"Used '{item1.name}' with '{item2.name}' (found in {source}).")
        # Handle cases where use_with might return bool or None
        elif isinstance(result, bool) and result:
             result = {"success": True, "message": f"Used '{item1.name}' with '{item2.name}' (found in {source})."}
        elif result is None: # Assume success if None is returned, provide generic message
             result = {"success": True, "message": f"Used '{item1.name}' with '{item2.name}' (found in {source}). Action completed."}
        elif isinstance(result, bool) and not result:
             result = {"success": False, "message": f"Failed to use '{item1.name}' with '{item2.name}'."}
        # Ensure result is always a dict for consistency
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
        # Find item in inventory
        item = None
        for inventory_item in self.inventory.contents:
            if inventory_item.id == item_id:
                item = inventory_item
                break
                
        if not item:
            return {"success": False, "message": f"Item {item_id} not found in inventory"}
            
        # Check if item is wearable
        if not item.is_wearable:
            return {"success": False, "message": f"{item.name} is not wearable"}
            
        # Remove item from inventory
        result = self.inventory.remove_item(item_id)
        if not result["success"]:
            return result
            
        # Add to wearable items
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
        # Find item in wearable items
        item = None
        for wearable_item in self.wearable_items:
            if wearable_item.id == item_id:
                item = wearable_item
                break
                
        if not item:
            return {"success": False, "message": f"Item {item_id} is not being worn"}
            
        # Remove from wearable items
        self.wearable_items.remove(item)
        
        # Add back to inventory
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