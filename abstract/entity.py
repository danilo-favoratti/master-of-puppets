from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, List

Position = Tuple[int, int]  # (x, y) coordinates

@dataclass
class Entity:
    """Base class for any entity that can exist on the board."""
    id: str
    name: str
    position: Optional[Position] = None
    description: str = ""
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}
    
    def set_position(self, position: Position) -> None:
        """Set the position of this entity on the board."""
        self.position = position
    
    def get_position(self) -> Optional[Position]:
        """Get the current position of this entity."""
        return self.position 