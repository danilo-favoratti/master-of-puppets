from dataclasses import dataclass, field
from typing import Set, Dict, Any, List, Optional
from model.entity import Entity, Position

@dataclass
class GameObject(Entity):
    """Game object that can exist on the board."""
    is_movable: bool = False  # Can be pushed/pulled
    is_jumpable: bool = False  # Can be jumped over
    weight: int = 1  # Weight affects movement mechanics
    usable_with: Set[str] = field(default_factory=set)  # IDs of objects this can be used with
    
    def can_use_with(self, obj_id: str) -> bool:
        """Check if this object can be used with another object."""
        return obj_id in self.usable_with
    
    def use_with(self, obj_id: str) -> Dict[str, Any]:
        """Use this object with another object."""
        if self.can_use_with(obj_id):
            return {"success": True, "message": f"{self.name} used successfully"}
        return {"success": False, "message": f"{self.name} cannot be used with that"}

@dataclass
class Container(GameObject):
    """A game object that can contain other objects."""
    contents: List[GameObject] = field(default_factory=list)
    capacity: int = 10  # Maximum number of items it can hold
    is_open: bool = True  # Whether items can be added/removed
    
    def add_item(self, item: GameObject) -> Dict[str, Any]:
        """Add an item to this container."""
        if not self.is_open:
            return {"success": False, "message": f"{self.name} is closed"}
        
        if len(self.contents) >= self.capacity:
            return {"success": False, "message": f"{self.name} is full"}
        
        self.contents.append(item)
        item.set_position(None)  # Item is now in container, not on board
        return {"success": True, "message": f"{item.name} added to {self.name}"}
    
    def remove_item(self, item_or_id) -> Dict[str, Any]:
        """Remove an item from this container.
        
        Args:
            item_or_id: Either an item ID (str) or a GameObject instance
        """
        if not self.is_open:
            return {"success": False, "message": f"{self.name} is closed"}
        
        # Handle different input types
        item_id = item_or_id.id if hasattr(item_or_id, 'id') else item_or_id
            
        for i, item in enumerate(self.contents):
            if item.id == item_id:
                removed = self.contents.pop(i)
                return {"success": True, "message": f"{removed.name} removed from {self.name}", "item": removed}
                
        return {"success": False, "message": f"Item not found in {self.name}"}
    
    def get_contents(self) -> List[GameObject]:
        """Get all items in this container."""
        return self.contents 