from dataclasses import dataclass, field
from typing import Set, Dict, Any, List

from entity import Entity


@dataclass
class GameObject(Entity):
    """Game object that can exist on the board."""
    is_movable: bool = False  # Can be pushed/pulled
    is_jumpable: bool = False  # Whether can be jumped over
    is_usable_alone: bool = False  # Whether object can be used by itself
    is_collectable: bool = False  # Whether object can be collected
    is_wearable: bool = False  # Whether object can be worn
    weight: int = 1  # Weight affects movement mechanics
    usable_with: Set[str] = field(default_factory=set)  # IDs of objects this can be used with
    possible_alone_actions: List[str] = field(default_factory=list)  # List of possible actions when used alone

    def can_use_with(self, obj_id: str) -> bool:
        """Check if this object can be used with another object."""
        return obj_id in self.usable_with
    
    def use_with(self, obj_id: str) -> Dict[str, Any]:
        """Use this object with another object."""
        if self.can_use_with(obj_id):
            return {"success": True, "message": f"{self.name} used successfully"}
        return {"success": False, "message": f"{self.name} cannot be used with that"}
        
    def use(self) -> Dict[str, Any]:
        """Use this object by itself."""
        if self.is_usable_alone:
            return {"success": True, "message": f"{self.name} used successfully"}
        return {"success": False, "message": f"{self.name} cannot be used alone"}

    def on_action_start(self, action: str) -> bool:
        """Called when an alone action starts. Override in subclasses.
        
        Args:
            action: The action being started
            
        Returns:
            bool: Whether the action can start
        """
        return action in self.possible_alone_actions

    def on_action_complete(self, action: str) -> bool:
        """Called when an alone action completes. Override in subclasses.
        
        Args:
            action: The action being completed
            
        Returns:
            bool: Whether the action completed successfully
        """
        return action in self.possible_alone_actions
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the game object to a dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description if hasattr(self, "description") else "",
            "is_movable": self.is_movable,
            "is_jumpable": self.is_jumpable,
            "is_usable_alone": self.is_usable_alone,
            "is_collectable": self.is_collectable,
            "is_wearable": self.is_wearable,
            "weight": self.weight,
            "possible_actions": list(self.possible_alone_actions),
            "usable_with": list(self.usable_with)
        }

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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the container object to a dictionary representation."""
        base_dict = super().to_dict()
        base_dict.update({
            "contents": [item.to_dict() for item in self.contents],
            "capacity": self.capacity,
            "is_open": self.is_open
        })
        return base_dict 