from typing import Dict, List, Set, Tuple, Optional, Any
from entity import Entity, Position
from game_object import GameObject
from collections import defaultdict

class Board:
    """The game board representing the 2D world."""
    
    def __init__(self, width: int, height: int):
        """Initialize a board with given dimensions."""
        self.width = width
        self.height = height
        self._position_map = defaultdict(list)  # Maps positions to entities
        self._entity_map = {}  # Maps entity IDs to their entities
    
    def is_valid_position(self, position: Position) -> bool:
        """Check if position is within board boundaries."""
        x, y = position
        return 0 <= x < self.width and 0 <= y < self.height
    
    def add_entity(self, entity: Entity, position: Position) -> bool:
        """Add an entity to the board at the specified position."""
        if not self.is_valid_position(position):
            return False
            
        # Update entity's position
        entity.set_position(position)
        
        # Add to position and entity maps
        self._position_map[position].append(entity)
        self._entity_map[entity.id] = entity
        
        return True
    
    def remove_entity(self, entity: Entity) -> bool:
        """Remove an entity from the board."""
        if entity.id not in self._entity_map:
            return False
            
        # Remove from position map
        if entity.position:
            position_entities = self._position_map[entity.position]
            if entity in position_entities:
                position_entities.remove(entity)
                
            # Clean up empty positions
            if not position_entities:
                del self._position_map[entity.position]
        
        # Remove from entity map
        del self._entity_map[entity.id]
        
        # Clear entity's position
        entity.set_position(None)
        
        return True
    
    def move_entity(self, entity: Entity, new_position: Position) -> bool:
        """Move an entity to a new position on the board.
        
        Returns:
            bool: True if move was successful, False otherwise
        """
        # Validate inputs
        if not entity or not new_position:
            return False
            
        # Check if position is valid and can be moved to
        if not self.is_valid_position(new_position):
            return False
            
        # Special case: if the entity is already at this position, consider it a success
        if entity.position == new_position:
            return True
            
        # Store old position for rollback
        old_position = entity.position
        
        # Check if we can move to the new position
        # Skip the check if the entity is already at that position (moving in place)
        if not self.can_move_to(new_position):
            return False
            
        try:
            # Remove from old position if it exists
            if old_position:
                position_entities = self._position_map[old_position]
                if entity in position_entities:
                    position_entities.remove(entity)
                    
                # Clean up empty positions
                if not position_entities:
                    del self._position_map[old_position]
            
            # Update entity's position
            entity.set_position(new_position)
            
            # Add to new position
            self._position_map[new_position].append(entity)
            
            # Update entity map
            self._entity_map[entity.id] = entity
            
            return True
            
        except Exception as e:
            # If anything goes wrong, try to restore the original state
            if old_position:
                # Restore entity to old position
                entity.set_position(old_position)
                self._position_map[old_position].append(entity)
            if new_position in self._position_map and not self._position_map[new_position]:
                del self._position_map[new_position]
            return False
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by its ID."""
        return self._entity_map.get(entity_id)
    
    def get_entities_at(self, position: Position) -> List[Entity]:
        """Get all entities at a specific position."""
        if not self.is_valid_position(position):
            return []
            
        return self._position_map.get(position, [])
    
    def get_object_at(self, position: Position) -> Optional[GameObject]:
        """Get the first GameObject at a position, if any."""
        entities = self.get_entities_at(position)
        for entity in entities:
            if isinstance(entity, GameObject):
                return entity
        return None
    
    def can_move_to(self, position: Position) -> bool:
        """Check if an entity can move to this position.
        
        A position is movable if:
        1. It is within board boundaries
        2. It is either empty or only contains entities that can share space
        """
        # Check if position is valid
        if not self.is_valid_position(position):
            return False
            
        # Get all entities at the position
        entities = self.get_entities_at(position)
        if not entities:
            return True  # Empty position is always movable
            
        # Check each entity at the position
        for entity in entities:
            # GameObjects always block movement
            if isinstance(entity, GameObject):
                return False
                
            # Add other blocking conditions here if needed
            # For example: walls, barriers, etc.
            
        return True  # Position only contains non-blocking entities
    
    def get_all_entities(self) -> List[Entity]:
        """Get all entities on the board."""
        return list(self._entity_map.values())
        
    def find_entities_by_name(self, name: str) -> List[Entity]:
        """Find entities by name (partial match)."""
        return [entity for entity in self._entity_map.values() 
                if name.lower() in entity.name.lower()]
                
    def find_entities_by_type(self, entity_type: type) -> List[Entity]:
        """Find entities by type."""
        return [entity for entity in self._entity_map.values() 
                if isinstance(entity, entity_type)] 