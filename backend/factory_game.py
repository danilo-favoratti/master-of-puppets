import math
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Set, Dict, Any, Literal, Tuple

import random
import numpy as np
from colorama import Fore, Back, Style, init

from game_constants import *
from game_object import GameObject, Container

# Initialize colorama for Windows
init()

# Map configuration
MAP_SIZE = 60
BORDER_SIZE = 15
WATER_LEVEL = 0.5  # Values below this are water, above are land
WATER_SYMBOL = "~~~"
LAND_SYMBOL = "$$$"

# Version information
VERSION = "2.0"  # Removed landmark and NPC functionality

def create_game(map_size: int = MAP_SIZE, 
                border_size: int = BORDER_SIZE,
                chest_count: int = 5,
                camp_count: int = 3,
                obstacle_count: int = 10,
                campfire_count: int = 4,
                backpack_count: int = 3,
                firewood_count: int = 6,
                tent_count: int = 2,
                bedroll_count: int = 3,
                log_stool_count: int = 4,
                campfire_spit_count: int = 2,
                campfire_pot_count: int = 2,
                pot_count: int = 5) -> Dict[str, Any]:
    """
    Create a complete game world.
    
    Args:
        map_size: Size of the map (square)
        border_size: Size of the water border
        chest_count: Number of chests to place
        camp_count: Number of camps to place
        obstacle_count: Number of land obstacles to place
        campfire_count: Number of campfires to place
        backpack_count: Number of backpacks to place
        firewood_count: Number of firewood to place
        tent_count: Number of tents to place
        bedroll_count: Number of bedrolls to place
        log_stool_count: Number of log stools to place
        campfire_spit_count: Number of campfire spits to place
        campfire_pot_count: Number of campfire pots to place
        pot_count: Number of pots to place
        
    Returns:
        Dict containing the map and placed objects
    """
    factory = GameFactory(map_size, border_size)
    world = factory.generate_world(
        chest_count=chest_count, 
        camp_count=camp_count,
        obstacle_count=obstacle_count,
        campfire_count=campfire_count,
        backpack_count=backpack_count,
        firewood_count=firewood_count,
        tent_count=tent_count,
        bedroll_count=bedroll_count,
        log_stool_count=log_stool_count,
        campfire_spit_count=campfire_spit_count,
        campfire_pot_count=campfire_pot_count,
        pot_count=pot_count
    )
    return world

def generate_perlin_noise(width: int, height: int, scale: float = 10.0, octaves: int = 6, 
                          persistence: float = 0.5, lacunarity: float = 2.0) -> np.ndarray:
    """
    Generate a 2D Perlin noise map.
    
    Args:
        width: Width of the map
        height: Height of the map
        scale: Scale of the noise (higher = more zoomed out)
        octaves: Number of layers of noise
        persistence: How much each octave contributes
        lacunarity: How much detail is added per octave
        
    Returns:
        2D numpy array of noise values between 0 and 1
    """
    # Initialize empty noise array
    noise_map = np.zeros((height, width))
    
    # Use numpy's random function as a simple noise source
    # In a real implementation, you'd use a proper Perlin noise library
    random_grid = np.random.rand(height, width)
    
    # Simple approximation of noise for demonstration
    # For each coordinate, calculate a weighted sum of surrounding random values
    for y in range(height):
        for x in range(width):
            # Get normalized coordinates
            nx = x / width
            ny = y / height
            
            # Use a weighted average of surrounding points as "noise"
            # This is a very simplified version of noise and not true Perlin noise
            frequency = 1
            amplitude = 1
            noise_value = 0
            
            # Sample points at different frequencies and amplitudes
            for i in range(octaves):
                # Sample index calculation
                sample_x = int((nx * frequency * scale) % width)
                sample_y = int((ny * frequency * scale) % height)
                
                # Get noise value
                noise_value += random_grid[sample_y, sample_x] * amplitude
                
                # Update frequency and amplitude for next octave
                amplitude *= persistence
                frequency *= lacunarity
            
            noise_map[y, x] = noise_value
    
    # Normalize the noise values to [0, 1]
    min_val = np.min(noise_map)
    max_val = np.max(noise_map)
    noise_map = (noise_map - min_val) / (max_val - min_val)
    
    return noise_map

def create_distance_map(width: int, height: int, method: Literal["square_bump", "euclidean"] = "square_bump") -> np.ndarray:
    """
    Create a distance map where the center is 0 and the edges are 1.
    
    Args:
        width: Width of the map
        height: Height of the map
        method: Distance function to use ("square_bump" or "euclidean")
        
    Returns:
        2D numpy array of distance values between 0 and 1
    """
    distance_map = np.zeros((height, width))
    
    for y in range(height):
        for x in range(width):
            # Normalize coordinates to range from -1 to 1
            nx = 2 * x / width - 1
            ny = 2 * y / height - 1
            
            if method == "square_bump":
                # Square bump distance: d = 1 - (1-nx²) * (1-ny²)
                distance_map[y, x] = 1 - (1 - nx**2) * (1 - ny**2)
            else:
                # Euclidean² distance: d = min(1, (nx² + ny²) / sqrt(2))
                distance_map[y, x] = min(1, (nx**2 + ny**2) / math.sqrt(2))
    
    return distance_map

def generate_island_map(size: int = MAP_SIZE, border_size: int = BORDER_SIZE) -> List[List[str]]:
    """
    Generate a map with islands surrounded by water.
    
    Args:
        size: Size of the map (square)
        border_size: Size of the water border
        
    Returns:
        2D list of strings representing the map
    """
    # Generate base noise
    inner_size = size - 2 * border_size
    noise = generate_perlin_noise(inner_size, inner_size)
    
    # Create distance map
    distance = create_distance_map(inner_size, inner_size, "square_bump")
    
    # Apply shaping function (linear interpolation)
    mix = 0.65  # Control how much of the distance affects the final value
    shaped_elevation = np.zeros_like(noise)
    for y in range(inner_size):
        for x in range(inner_size):
            d = distance[y, x]
            e = noise[y, x]
            # Linear interpolation: e = lerp(e, 1-d, mix)
            shaped_elevation[y, x] = e * (1 - mix) + (1 - d) * mix
    
    # Create the final map with water border
    map_grid = []
    for y in range(size):
        row = []
        for x in range(size):
            # If in the border area, it's water
            if (y < border_size or y >= size - border_size or 
                x < border_size or x >= size - border_size):
                row.append(WATER_SYMBOL)
            else:
                # Otherwise, use the shaped elevation
                inner_x = x - border_size
                inner_y = y - border_size
                if shaped_elevation[inner_y, inner_x] >= WATER_LEVEL:
                    row.append(LAND_SYMBOL)
                else:
                    row.append(WATER_SYMBOL)
        map_grid.append(row)
    
    return map_grid

def print_map(map_grid: List[List[str]]) -> None:
    """
    Print the map to the console.
    
    Args:
        map_grid: 2D list of strings representing the map
    """
    for row in map_grid:
        print(" ".join(row))

def generate_map() -> List[List[str]]:
    """
    Generate and return a map with islands surrounded by water.
    
    Returns:
        2D list of strings representing the map
    """
    return generate_island_map()

if __name__ == "__main__":
    # Generate and print a map
    map_grid = generate_map()
    print_map(map_grid) 

@dataclass
class Backpack(GameObject):
    """
    A small backpack that can hold items.
    """
    description: str = ""
    max_capacity: int = 5  # Maximum number of items the backpack can hold
    contained_items: List[str] = field(default_factory=list)  # Items currently in the backpack
    possible_alone_actions: Set[str] = field(default_factory=set)  # Actions available when used alone

    def __post_init__(self):
        # Backpacks are movable and can be interacted with
        self.is_movable = True
        self.is_jumpable = False
        self.is_usable_alone = True
        self.is_wearable = True  # Backpacks can be worn
        self.weight = 2  # Backpacks are moderately heavy
        self.usable_with = set()
        super().__post_init__()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the backpack object to a dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "max_capacity": self.max_capacity,
            "contained_items": self.contained_items,
            "is_movable": self.is_movable,
            "is_jumpable": self.is_jumpable,
            "is_usable_alone": self.is_usable_alone,
            "is_wearable": self.is_wearable,
            "weight": self.weight,
            "possible_actions": list(self.possible_alone_actions),
            "usable_with": list(self.usable_with)
        }


class BackpackFactory:
    """
    Factory to create backpack objects.
    """
    _backpack_data: Dict[str, Dict[str, Any]] = {
        "small": {
            "name": "Small Backpack",
            "description": "A small backpack that can hold a few items.",
            "max_capacity": 5
        }
    }
    
    @classmethod
    def create_backpack(cls, variant: str = "small", id: str = None) -> Dict[str, Any]:
        """
        Create a backpack object.
        
        Args:
            variant (str): The variant of backpack to create (currently only "small").
            id (str, optional): An optional id for the backpack. If not provided, a default is generated.
            
        Returns:
            Dict[str, Any]: A dictionary representation of the backpack.
        
        Raises:
            ValueError: If an invalid variant is provided.
        """
        data = cls._backpack_data.get(variant)
        if data is None:
            valid_variants = ", ".join(cls._backpack_data.keys())
            raise ValueError(f"Invalid backpack variant: {variant}. Valid variants are: {valid_variants}")
            
        # If no id is provided, generate a default id.
        if id is None:
            id = f"backpack_{variant}_{random.randint(1000, 9999)}"
            
        backpack = Backpack(
            id=id,
            name=data["name"],
            description=data["description"],
            max_capacity=data["max_capacity"],
            is_movable=True,
            is_jumpable=False,
            is_usable_alone=True,
            is_wearable=True,  # Backpacks can be worn
            weight=2,
            usable_with=set()
        )
        
        return backpack.to_dict()

# Action constants
ACTION_SLEEP = "sleep"

@dataclass
class Bedroll(GameObject):
    """
    A bedroll that can be used for sleeping.
    """
    description: str = ""
    max_capacity: int = 1  # Maximum number of people that can sleep in the bedroll
    contained_items: List[str] = field(default_factory=list)  # People currently in the bedroll
    possible_alone_actions: Set[str] = field(default_factory=set)  # Actions available when used alone

    def __post_init__(self):
        # Bedrolls are movable but become immovable when in use
        self.is_movable = True
        self.is_jumpable = False
        self.is_usable_alone = True
        self.weight = 2  # Bedrolls are moderately heavy
        self.usable_with = set()
        self.possible_alone_actions = {ACTION_SLEEP}
        super().__post_init__()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the bedroll object to a dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "max_capacity": self.max_capacity,
            "contained_items": self.contained_items,
            "is_movable": self.is_movable,
            "is_jumpable": self.is_jumpable,
            "is_usable_alone": self.is_usable_alone,
            "weight": self.weight,
            "possible_actions": list(self.possible_alone_actions),
            "usable_with": list(self.usable_with)
        }


class BedrollFactory:
    """
    Factory to create bedroll objects.
    """
    _bedroll_data: Dict[str, Dict[str, Any]] = {
        "standard": {
            "name": "Bedroll",
            "description": "A comfortable bedroll for sleeping."
        }
    }
    
    @classmethod
    def create_bedroll(cls, variant: str = "standard", id: str = None) -> Dict[str, Any]:
        """
        Create a bedroll object.
        
        Args:
            variant (str): The variant of bedroll to create (currently only "standard").
            id (str, optional): An optional id for the bedroll. If not provided, a default is generated.
            
        Returns:
            Dict[str, Any]: A dictionary representation of the bedroll.
        
        Raises:
            ValueError: If an invalid variant is provided.
        """
        data = cls._bedroll_data.get(variant)
        if data is None:
            valid_variants = ", ".join(cls._bedroll_data.keys())
            raise ValueError(f"Invalid bedroll variant: {variant}. Valid variants are: {valid_variants}")
            
        # If no id is provided, generate a default id.
        if id is None:
            id = f"bedroll_{variant}_{random.randint(1000, 9999)}"
            
        bedroll = Bedroll(
            id=id,
            name=data["name"],
            description=data["description"],
            max_capacity=1,
            is_movable=True,
            is_jumpable=True,
            is_usable_alone=False,
            weight=2,
            usable_with=set()
        )
        
        return bedroll.to_dict()


# Camp types
CAMP_TYPES = {
    "bandit": {
        "description": "A hostile camp of bandits that will attack on sight",
        "hostility": "aggressive",
        "sizes": ["small", "medium", "large"],
        "npcs": ["bandit_scout", "bandit_thug", "bandit_archer", "bandit_leader"]
    },
    "traveler": {
        "description": "A peaceful camp of travelers resting or trading goods",
        "hostility": "friendly",
        "sizes": ["small", "medium"],
        "npcs": ["merchant", "guard", "wanderer", "storyteller"]
    },
    "merchant": {
        "description": "A well-established trading post with valuable goods",
        "hostility": "neutral",
        "sizes": ["medium", "large"],
        "npcs": ["trader", "guard", "craftsman", "collector"]
    },
    "abandoned": {
        "description": "A deserted camp with possible loot but also possible danger",
        "hostility": "neutral",
        "sizes": ["small", "medium", "large"],
        "npcs": ["wildlife", "scavenger", "ghost"]
    },
    "military": {
        "description": "A well-organized camp of soldiers or guards",
        "hostility": "neutral",
        "sizes": ["medium", "large"],
        "npcs": ["soldier", "commander", "scout", "archer"]
    }
}

# Size configurations
CAMP_SIZES = {
    "small": {
        "radius": 1,
        "occupants": (1, 3),
        "structures": (1, 2)
    },
    "medium": {
        "radius": 2,
        "occupants": (3, 6),
        "structures": (2, 4)
    },
    "large": {
        "radius": 3,
        "occupants": (5, 10),
        "structures": (4, 7)
    }
}

# Structure types that can appear in camps
STRUCTURES = {
    "bandit": ["tent", "campfire", "weapon_rack", "cage", "lookout"],
    "traveler": ["tent", "campfire", "cart", "animal_pen"],
    "merchant": ["shop", "storage", "tent", "campfire", "animal_pen", "forge"],
    "abandoned": ["ruined_tent", "cold_campfire", "broken_cart", "debris"],
    "military": ["barracks", "armory", "watchtower", "command_tent", "training_area"]
}

def create_camp(camp_type: str = None, size: str = None) -> Dict[str, Any]:
    """
    Create a random camp or one of a specific type and size.
    
    Args:
        camp_type (str, optional): Type of camp to create. If None, a random type is chosen.
        size (str, optional): Size of the camp. If None, a random appropriate size is chosen.
        
    Returns:
        Dict: A camp object with properties
    """
    # Choose a random camp type if none specified
    if camp_type is None:
        camp_type = random.choice(list(CAMP_TYPES.keys()))
    
    # Get camp type data
    camp_data = CAMP_TYPES[camp_type]
    
    # Choose a random appropriate size if none specified
    if size is None:
        size = random.choice(camp_data["sizes"])
    
    # Get size configuration
    size_config = CAMP_SIZES[size]
    
    # Determine number of occupants and structures
    num_occupants = random.randint(*size_config["occupants"])
    num_structures = random.randint(*size_config["structures"])
    
    # Select occupants
    occupants = []
    for _ in range(num_occupants):
        npc_type = random.choice(camp_data["npcs"])
        occupants.append({
            "type": npc_type,
            "level": random.randint(1, 5),
            "hostile": camp_data["hostility"] == "aggressive"
        })
    
    # Select structures
    structures = []
    available_structures = STRUCTURES.get(camp_type, ["tent", "campfire"])
    for _ in range(num_structures):
        structure_type = random.choice(available_structures)
        structures.append({
            "type": structure_type,
            "condition": random.choice(["poor", "fair", "good"]) if camp_type != "abandoned" else "poor"
        })
    
    # Create the camp object
    camp = {
        "type": camp_type,
        "size": size,
        "radius": size_config["radius"],
        "description": camp_data["description"],
        "hostility": camp_data["hostility"],
        "occupants": occupants,
        "structures": structures
    }
    
    return camp


@dataclass
class CampfirePot(GameObject):
    """
    A container that can be placed over a campfire for cooking.
    Can be either a tripod or a spit, and can hold items for cooking.
    """
    description: str = ""
    pot_type: str = POT_TRIPOD  # Type of pot (tripod or spit)
    state: str = POT_EMPTY  # Current state of the pot
    possible_alone_actions: Set[str] = field(default_factory=set)  # Actions available when used alone
    contained_items: List[str] = field(default_factory=list)  # Items currently in the pot
    max_items: int = 1  # Maximum number of items the pot can hold

    def __post_init__(self):
        # Pots are movable and can be interacted with
        self.is_movable = True
        self.is_jumpable = False
        self.is_usable_alone = True
        self.weight = 3  # Pots are moderately heavy
        self.usable_with = {CAMPFIRE_BURNING, CAMPFIRE_DYING}  # Can be used with burning/dying fires
        
        # Set possible actions based on state
        if self.state == POT_EMPTY:
            self.possible_alone_actions = {ACTION_PLACE}
        elif self.state == POT_COOKING:
            self.possible_alone_actions = {ACTION_REMOVE}
        elif self.state == POT_BURNING:
            self.possible_alone_actions = {ACTION_REMOVE}
        elif self.state == POT_COOKED:
            self.possible_alone_actions = {ACTION_REMOVE, ACTION_EMPTY}
            
        super().__post_init__()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the campfire pot object to a dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "pot_type": self.pot_type,
            "state": self.state,
            "max_items": self.max_items,
            "contained_items": self.contained_items,
            "is_movable": self.is_movable,
            "is_jumpable": self.is_jumpable,
            "is_usable_alone": self.is_usable_alone,
            "weight": self.weight,
            "possible_actions": list(self.possible_alone_actions),
            "usable_with": list(self.usable_with)
        }


class CampfirePotFactory:
    """
    Factory to create various campfire pot objects.
    """
    _pot_data: Dict[str, Dict[str, Any]] = {
        POT_TRIPOD: {
            "name": "Cooking Tripod",
            "description": "A sturdy metal tripod designed to hold cooking pots over a fire.",
            "pot_type": POT_TRIPOD,
            "state": POT_EMPTY,
            "max_items": 1
        },
        POT_SPIT: {
            "name": "Roasting Spit",
            "description": "A long metal spit perfect for roasting meat over a fire.",
            "pot_type": POT_SPIT,
            "state": POT_EMPTY,
            "max_items": 1
        }
    }
    
    @classmethod
    def create_pot(cls, pot_type: str, id: str = None) -> Dict[str, Any]:
        """
        Create a campfire pot object based on the type provided.
        
        Args:
            pot_type (str): The type of pot (tripod or spit).
            id (str, optional): An optional id for the pot. If not provided, a default is generated.
            
        Returns:
            Dict[str, Any]: A dictionary representation of the pot.
        
        Raises:
            ValueError: If an invalid pot type is provided.
        """
        data = cls._pot_data.get(pot_type)
        if data is None:
            valid_types = ", ".join(cls._pot_data.keys())
            raise ValueError(f"Invalid pot type: {pot_type}. Valid types are: {valid_types}")
            
        # If no id is provided, generate a default id.
        if id is None:
            id = f"pot_{pot_type}_{random.randint(1000, 9999)}"
            
        pot = CampfirePot(
            id=id,
            name=data["name"],
            description=data["description"],
            pot_type=data["pot_type"],
            state=data["state"],
            max_items=data["max_items"],
            is_movable=True,
            is_jumpable=False,
            is_usable_alone=True,
            weight=3,
            usable_with={CAMPFIRE_BURNING, CAMPFIRE_DYING}
        )
        
        return pot.to_dict()




@dataclass
class SpitItem(GameObject):
    """
    An item that can be cooked on a spit over a campfire.
    Can be various types of meat, fish, or other food items.
    """
    description: str = ""
    item_type: str = SPIT_BIRD  # Type of item (bird, fish, meat)
    state: str = SPIT_ITEM_RAW  # Current state of the item
    possible_alone_actions: Set[str] = field(default_factory=set)  # Actions available when used alone
    cooking_time: int = 5  # Time in turns to cook the item
    is_edible: bool = True  # Whether the item can be eaten

    def __post_init__(self):
        # Spit items are movable and can be interacted with
        self.is_movable = True
        self.is_jumpable = False
        self.is_usable_alone = True
        self.weight = 1  # Food items are relatively light
        self.usable_with = {POT_SPIT}  # Can be used with a spit
        
        # Set possible actions based on state
        if self.state == SPIT_ITEM_RAW:
            self.possible_alone_actions = {ACTION_PLACE_ON_SPIT}
        elif self.state == SPIT_ITEM_COOKING:
            self.possible_alone_actions = {ACTION_REMOVE_FROM_SPIT}
        elif self.state == SPIT_ITEM_BURNING:
            self.possible_alone_actions = {ACTION_REMOVE_FROM_SPIT}
        elif self.state == SPIT_ITEM_COOKED:
            self.possible_alone_actions = {ACTION_REMOVE_FROM_SPIT, ACTION_EAT}
            
        super().__post_init__()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the spit item object to a dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "item_type": self.item_type,
            "state": self.state,
            "cooking_time": self.cooking_time,
            "is_edible": self.is_edible,
            "is_movable": self.is_movable,
            "is_jumpable": self.is_jumpable,
            "is_usable_alone": self.is_usable_alone,
            "weight": self.weight,
            "possible_actions": list(self.possible_alone_actions),
            "usable_with": list(self.usable_with)
        }


class SpitItemFactory:
    """
    Factory to create various items that can be cooked on a spit.
    """
    _item_data: Dict[str, Dict[str, Any]] = {
        SPIT_BIRD: {
            "name": "Raw Bird",
            "description": "A plucked bird ready for roasting.",
            "item_type": SPIT_BIRD,
            "state": SPIT_ITEM_RAW,
            "cooking_time": 5,
            "is_edible": True
        },
        SPIT_FISH: {
            "name": "Raw Fish",
            "description": "A cleaned fish ready for grilling.",
            "item_type": SPIT_FISH,
            "state": SPIT_ITEM_RAW,
            "cooking_time": 3,
            "is_edible": True
        },
        SPIT_MEAT: {
            "name": "Raw Meat",
            "description": "A piece of meat ready for roasting.",
            "item_type": SPIT_MEAT,
            "state": SPIT_ITEM_RAW,
            "cooking_time": 7,
            "is_edible": True
        }
    }
    
    @classmethod
    def create_item(cls, item_type: str, id: str = None) -> Dict[str, Any]:
        """
        Create a spit item object based on the type provided.
        
        Args:
            item_type (str): The type of item (bird, fish, or meat).
            id (str, optional): An optional id for the item. If not provided, a default is generated.
            
        Returns:
            Dict[str, Any]: A dictionary representation of the item.
        
        Raises:
            ValueError: If an invalid item type is provided.
        """
        data = cls._item_data.get(item_type)
        if data is None:
            valid_types = ", ".join(cls._item_data.keys())
            raise ValueError(f"Invalid item type: {item_type}. Valid types are: {valid_types}")
            
        # If no id is provided, generate a default id.
        if id is None:
            id = f"spit_item_{item_type}_{random.randint(1000, 9999)}"
            
        item = SpitItem(
            id=id,
            name=data["name"],
            description=data["description"],
            item_type=data["item_type"],
            state=data["state"],
            cooking_time=data["cooking_time"],
            is_edible=data["is_edible"],
            is_movable=True,
            is_jumpable=False,
            is_usable_alone=True,
            weight=1,
            usable_with={POT_SPIT}
        )
        
        return item.to_dict()


@dataclass
class CampfireSpit(GameObject):
    """
    A spit that can be placed over a campfire for cooking food.
    """
    description: str = ""
    quality: str = SPIT_QUALITY_BASIC  # Quality level of the spit
    durability: int = 100  # Current durability
    max_durability: int = 100  # Maximum durability
    cooking_bonus: int = 0  # Bonus to cooking speed/quality
    possible_alone_actions: Set[str] = field(default_factory=set)

    def __post_init__(self):
        # Spits are movable but not jumpable
        self.is_movable = True
        self.is_jumpable = False
        self.is_usable_alone = True
        self.weight = 2  # Spits are moderately heavy
        self.usable_with = {POT_SPIT}  # Can be used with pots
        super().__post_init__()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the campfire spit object to a dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "quality": self.quality,
            "durability": self.durability,
            "max_durability": self.max_durability,
            "cooking_bonus": self.cooking_bonus,
            "is_movable": self.is_movable,
            "is_jumpable": self.is_jumpable,
            "is_usable_alone": self.is_usable_alone,
            "weight": self.weight,
            "possible_actions": list(self.possible_alone_actions),
            "usable_with": list(self.usable_with)
        }


class CampfireSpitFactory:
    """
    Factory to create campfire spits of various qualities.
    """
    _spit_data: Dict[str, Dict[str, Any]] = {
        SPIT_QUALITY_BASIC: {
            "name": "Basic Campfire Spit",
            "description": "A simple wooden spit for cooking over a campfire.",
            "quality": SPIT_QUALITY_BASIC,
            "durability": 100,
            "max_durability": 100,
            "cooking_bonus": 0
        },
        SPIT_QUALITY_STURDY: {
            "name": "Sturdy Campfire Spit",
            "description": "A well-crafted spit made from hardwood.",
            "quality": SPIT_QUALITY_STURDY,
            "durability": 150,
            "max_durability": 150,
            "cooking_bonus": 1
        },
        SPIT_QUALITY_REINFORCED: {
            "name": "Reinforced Campfire Spit",
            "description": "A reinforced spit with metal supports.",
            "quality": SPIT_QUALITY_REINFORCED,
            "durability": 200,
            "max_durability": 200,
            "cooking_bonus": 2
        }
    }
    
    @classmethod
    def create_campfire_spit(cls, quality: str = SPIT_QUALITY_BASIC, id: str = None) -> Dict[str, Any]:
        """
        Create a campfire spit object.
        
        Args:
            quality (str): The quality level of the spit (basic, sturdy, or reinforced)
            id (str, optional): An optional id for the spit. If not provided, a default is generated.
            
        Returns:
            Dict[str, Any]: A dictionary representation of the campfire spit
            
        Raises:
            ValueError: If an invalid quality level is provided
        """
        data = cls._spit_data.get(quality)
        if data is None:
            valid_qualities = ", ".join(cls._spit_data.keys())
            raise ValueError(f"Invalid quality level: {quality}. Valid qualities are: {valid_qualities}")
            
        # If no id is provided, generate a default id
        if id is None:
            id = f"campfire_spit_{quality}_{random.randint(1000, 9999)}"
            
        spit = CampfireSpit(
            id=id,
            name=data["name"],
            description=data["description"],
            quality=data["quality"],
            durability=data["durability"],
            max_durability=data["max_durability"],
            cooking_bonus=data["cooking_bonus"],
            is_movable=False,
            is_jumpable=False,
            is_usable_alone=True,
            weight=2,
            usable_with={POT_SPIT}
        )
        
        return spit.to_dict()


@dataclass
class Campfire(GameObject):
    """
    A campfire game object with different states.
    The campfire can be unlit, burning, dying, or extinguished.
    """
    description: str = ""
    state: str = CAMPFIRE_UNLIT  # Current state of the campfire
    possible_alone_actions: Set[str] = field(default_factory=set)  # Actions available when used alone

    def __post_init__(self):
        # Campfires are immovable and can be interacted with
        self.is_movable = False
        self.is_jumpable = True
        self.is_usable_alone = True
        self.weight = 5  # Campfires are heavier than candles
        self.usable_with = set()  # Can be used with items like wood, water, etc.
        
        # Set possible actions based on state
        if self.state == CAMPFIRE_UNLIT:
            self.possible_alone_actions = {ACTION_LIGHT}
        elif self.state in [CAMPFIRE_BURNING, CAMPFIRE_DYING]:
            self.possible_alone_actions = {ACTION_EXTINGUISH}
        else:  # CAMPFIRE_EXTINGUISHED
            self.possible_alone_actions = {ACTION_LIGHT}
            
        super().__post_init__()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the campfire object to a dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "state": self.state,
            "is_movable": self.is_movable,
            "is_jumpable": self.is_jumpable,
            "is_usable_alone": self.is_usable_alone,
            "weight": self.weight,
            "possible_actions": list(self.possible_alone_actions),
            "usable_with": list(self.usable_with)
        }

class CampfireFactory:
    """
    Factory to create various campfire objects with different states.
    """
    _campfire_data: Dict[str, Dict[str, Any]] = {
        CAMPFIRE_UNLIT: {
            "name": "Unlit Campfire",
            "description": "A pile of dry wood ready to be lit.",
            "state": CAMPFIRE_UNLIT
        },
        CAMPFIRE_BURNING: {
            "name": "Burning Campfire",
            "description": "A roaring campfire with dancing flames.",
            "state": CAMPFIRE_BURNING
        },
        CAMPFIRE_DYING: {
            "name": "Dying Campfire",
            "description": "A campfire that's slowly dying out.",
            "state": CAMPFIRE_DYING
        },
        CAMPFIRE_EXTINGUISHED: {
            "name": "Extinguished Campfire",
            "description": "A cold pile of ashes and charred wood.",
            "state": CAMPFIRE_EXTINGUISHED
        }
    }
    
    @classmethod
    def create_campfire(cls, state: str = CAMPFIRE_UNLIT, id: str = None) -> Dict[str, Any]:
        """
        Create a campfire object based on the state provided.
        
        Args:
            state (str): The state of the campfire (unlit, burning, dying, or extinguished).
            id (str, optional): An optional id for the campfire. If not provided, a default is generated.
            
        Returns:
            Dict[str, Any]: A dictionary representation of the campfire.
        
        Raises:
            ValueError: If an invalid state is provided.
        """
        data = cls._campfire_data.get(state)
        if data is None:
            valid_states = ", ".join(cls._campfire_data.keys())
            raise ValueError(f"Invalid campfire state: {state}. Valid states are: {valid_states}")
            
        # If no id is provided, generate a default id.
        if id is None:
            id = f"campfire_{state}_{random.randint(1000, 9999)}"
            
        campfire = Campfire(
            id=id,
            name=data["name"],
            description=data["description"],
            state=data["state"],
            is_movable=False,
            is_jumpable=False,
            is_usable_alone=True,
            weight=5,
            usable_with=set()
        )
        
        return campfire.to_dict()

# Chest type constants
CHEST_BASIC_WOODEN = "basic_wooden"
CHEST_FORESTWOOD = "forestwood"
CHEST_BRONZE_BANDED = "bronze_banded"
CHEST_BEASTS_MAW = "beasts_maw"
CHEST_DARK_IRON = "dark_iron"
CHEST_STEELBOUND = "steelbound"
CHEST_ROYAL_AZURE = "royal_azure"
CHEST_CELESTIAL = "celestial"
CHEST_SHADOWFANG = "shadowfang"
CHEST_ABYSSAL = "abyssal"
CHEST_BANDITS = "bandits"
CHEST_ARCANIST = "arcanist"
CHEST_CRIMSON = "crimson"
CHEST_VIOLET = "violet"
CHEST_STONE_TITAN = "stone_titan"

# Chest rarity types
CHEST_TYPES = [
    "wooden",    # Common
    "silver",    # Uncommon
    "golden",    # Rare
    "magical"    # Epic
]

# Items that can be found in chests
CHEST_ITEMS = {
    "wooden": [
        "apple", "bread", "rope", "torch", "flint", "small_coin_pouch"
    ],
    "silver": [
        "health_potion", "mana_potion", "bronze_dagger", "leather_armor",
        "silver_coin_pouch", "basic_scroll", "key"
    ],
    "golden": [
        "magic_wand", "enchanted_bow", "steel_sword", "chainmail_armor",
        "gold_coin_pouch", "enchantment_scroll", "key"
    ],
    "magical": [
        "legendary_weapon", "enchanted_armor", "powerful_artifact",
        "teleportation_scroll", "large_gold_chest", "rare_gem", "key", "master key"
    ]
}

# Lock types for chests
LOCK_TYPES = {
    "wooden": ["simple", "broken", None],
    "silver": ["standard", "tricky", "simple", None],
    "golden": ["complex", "magic", "standard"],
    "magical": ["enchanted", "puzzle", "trapped"]
}

@dataclass
class Chest(Container):
    """A chest that can hold items."""
    chest_type: str = ""  # Type of chest
    is_locked: bool = False  # Whether the chest is locked
    lock_difficulty: int = 0  # Difficulty to pick the lock (0-10)
    durability: int = 100  # Chest's durability (0-100)
    
    def __post_init__(self):
        # All chests are movable containers
        self.is_movable = True
        self.is_jumpable = False
        self.is_usable_alone = True
        self.weight = 10  # Base weight for chests
        super().__post_init__()

class ChestFactory:
    """Factory to create chest objects."""
    
    _chest_data: Dict[str, Dict[str, Any]] = {
        CHEST_BASIC_WOODEN: {
            "name": "Basic Wooden Chest",
            "description": "A simple wooden chest with basic craftsmanship.",
            "capacity": 5,
            "is_locked": False,
            "lock_difficulty": 0,
            "durability": 50,
            "weight": 10
        },
        CHEST_FORESTWOOD: {
            "name": "Forestwood Chest",
            "description": "A chest crafted from ancient forest wood, naturally resistant to decay.",
            "capacity": 6,
            "is_locked": False,
            "lock_difficulty": 0,
            "durability": 70,
            "weight": 12
        },
        CHEST_BRONZE_BANDED: {
            "name": "Bronze Banded Chest",
            "description": "A sturdy chest reinforced with bronze bands for extra protection.",
            "capacity": 7,
            "is_locked": True,
            "lock_difficulty": 2,
            "durability": 80,
            "weight": 15
        },
        CHEST_BEASTS_MAW: {
            "name": "Beast's Maw Chest",
            "description": "A fearsome chest carved to resemble a beast's open maw.",
            "capacity": 8,
            "is_locked": True,
            "lock_difficulty": 3,
            "durability": 85,
            "weight": 18
        },
        CHEST_DARK_IRON: {
            "name": "Dark Iron Chest",
            "description": "A heavy chest forged from dark iron, resistant to corrosion.",
            "capacity": 8,
            "is_locked": True,
            "lock_difficulty": 4,
            "durability": 90,
            "weight": 20
        },
        CHEST_STEELBOUND: {
            "name": "Steelbound Strongbox",
            "description": "A reinforced chest bound with steel bands and complex locks.",
            "capacity": 9,
            "is_locked": True,
            "lock_difficulty": 5,
            "durability": 95,
            "weight": 22
        },
        CHEST_ROYAL_AZURE: {
            "name": "Royal Azure Chest",
            "description": "An ornate chest adorned with azure gems and gold trim.",
            "capacity": 10,
            "is_locked": True,
            "lock_difficulty": 6,
            "durability": 100,
            "weight": 25
        },
        CHEST_CELESTIAL: {
            "name": "Celestial Guardian Chest",
            "description": "A mystical chest that seems to glow with celestial energy.",
            "capacity": 12,
            "is_locked": True,
            "lock_difficulty": 7,
            "durability": 100,
            "weight": 28
        },
        CHEST_SHADOWFANG: {
            "name": "Shadowfang Chest",
            "description": "A dark chest that seems to absorb light around it.",
            "capacity": 12,
            "is_locked": True,
            "lock_difficulty": 7,
            "durability": 100,
            "weight": 30
        },
        CHEST_ABYSSAL: {
            "name": "Abyssal Obsidian Chest",
            "description": "A chest crafted from pure obsidian, emanating dark energy.",
            "capacity": 15,
            "is_locked": True,
            "lock_difficulty": 8,
            "durability": 100,
            "weight": 35
        },
        CHEST_BANDITS: {
            "name": "Bandit's Booty Box",
            "description": "A chest designed for quick access and easy transport.",
            "capacity": 8,
            "is_locked": True,
            "lock_difficulty": 4,
            "durability": 75,
            "weight": 15
        },
        CHEST_ARCANIST: {
            "name": "Arcanist's Reliquary",
            "description": "A chest enchanted with protective magical wards.",
            "capacity": 10,
            "is_locked": True,
            "lock_difficulty": 6,
            "durability": 90,
            "weight": 20
        },
        CHEST_CRIMSON: {
            "name": "Crimson Command Chest",
            "description": "A military-grade chest with reinforced security measures.",
            "capacity": 12,
            "is_locked": True,
            "lock_difficulty": 7,
            "durability": 95,
            "weight": 25
        },
        CHEST_VIOLET: {
            "name": "Violet Vault",
            "description": "A mysterious chest that seems to shift and change.",
            "capacity": 15,
            "is_locked": True,
            "lock_difficulty": 8,
            "durability": 100,
            "weight": 30
        },
        CHEST_STONE_TITAN: {
            "name": "Stone Titan's Locker",
            "description": "A massive chest carved from living stone.",
            "capacity": 20,
            "is_locked": True,
            "lock_difficulty": 9,
            "durability": 100,
            "weight": 40
        }
    }
    
    @classmethod
    def create_chest(cls, chest_type: str, id: str = None) -> Chest:
        """Create a chest object.
        
        Args:
            chest_type: The type of chest to create
            id: Optional ID for the chest. If not provided, a default is generated.
            
        Returns:
            Chest: A new chest instance.
            
        Raises:
            ValueError: If an invalid chest type is provided.
        """
        data = cls._chest_data.get(chest_type)
        if data is None:
            valid_types = ", ".join(cls._chest_data.keys())
            raise ValueError(f"Invalid chest type: {chest_type}. Valid types are: {valid_types}")
            
        # If no id is provided, generate a default id
        if id is None:
            id = f"chest_{chest_type}"
            
        return Chest(
            id=id,
            name=data["name"],
            description=data["description"],
            capacity=data["capacity"],
            chest_type=chest_type,
            is_locked=data["is_locked"],
            lock_difficulty=data["lock_difficulty"],
            durability=data["durability"],
            weight=data["weight"]
        )

def create_chest(chest_type: str = None) -> Dict[str, Any]:
    """
    Create a random chest or one of a specific type.
    
    Args:
        chest_type (str, optional): Type of chest to create. If None, a random type is chosen.
        
    Returns:
        Dict: A chest object with properties
    """
    # Choose a random chest type if none specified
    if chest_type is None:
        chest_type = random.choice(CHEST_TYPES)
    
    # Determine rarity weights based on chest type
    if chest_type == "wooden":
        rarity_weights = [0.7, 0.25, 0.05, 0]  # Common, uncommon, rare, epic
    elif chest_type == "silver":
        rarity_weights = [0.4, 0.4, 0.15, 0.05]
    elif chest_type == "golden":
        rarity_weights = [0.1, 0.3, 0.4, 0.2]
    else:  # magical
        rarity_weights = [0, 0.1, 0.3, 0.6]
    
    # Select items based on rarity weights
    num_items = random.randint(1, 3) if chest_type == "wooden" else \
               random.randint(2, 4) if chest_type == "silver" else \
               random.randint(3, 5) if chest_type == "golden" else \
               random.randint(4, 6)  # magical
    
    # Select items for the chest
    chest_contents = []
    
    for _ in range(num_items):
        # Choose an item tier based on rarity weights
        tier = random.choices(range(4), weights=rarity_weights)[0]
        
        # Get items from appropriate tier
        item_tier = CHEST_TYPES[tier]
        item = random.choice(CHEST_ITEMS[item_tier])
        
        chest_contents.append({
            "name": item,
            "tier": item_tier,
            "quantity": random.randint(1, 3) if tier < 2 else random.randint(1, 2)
        })
    
    # Determine lock type
    lock_type = random.choice(LOCK_TYPES[chest_type])
    
    # Create the chest object
    chest = {
        "type": chest_type,
        "contents": chest_contents,
        "locked": lock_type is not None,
        "lock_type": lock_type
    }
    
    return chest

# Action constants
ACTION_COLLECT = "collect"

@dataclass
class Firewood(GameObject):
    """
    A fallen branch that can be collected for firewood.
    """
    description: str = ""
    possible_alone_actions: Set[str] = field(default_factory=set)  # Actions available when used alone

    def __post_init__(self):
        # Firewood is movable and can be collected
        self.is_movable = True
        self.is_jumpable = False
        self.is_usable_alone = True
        self.is_collectable = True  # Firewood can be collected
        self.weight = 1  # Firewood is relatively light
        self.usable_with = set()
        self.possible_alone_actions = {ACTION_COLLECT}
        super().__post_init__()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the firewood object to a dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_movable": self.is_movable,
            "is_jumpable": self.is_jumpable,
            "is_usable_alone": self.is_usable_alone,
            "is_collectable": self.is_collectable,
            "weight": self.weight,
            "possible_actions": list(self.possible_alone_actions),
            "usable_with": list(self.usable_with)
        }


class FirewoodFactory:
    """
    Factory to create firewood objects.
    """
    _firewood_data: Dict[str, Dict[str, Any]] = {
        "branch": {
            "name": "Fallen Branch",
            "description": "A dry branch that can be collected for firewood."
        }
    }
    
    @classmethod
    def create_firewood(cls, variant: str = "branch", id: str = None) -> Dict[str, Any]:
        """
        Create a firewood object.
        
        Args:
            variant (str): The variant of firewood to create (currently only "branch").
            id (str, optional): An optional id for the firewood. If not provided, a default is generated.
            
        Returns:
            Dict[str, Any]: A dictionary representation of the firewood.
        
        Raises:
            ValueError: If an invalid variant is provided.
        """
        data = cls._firewood_data.get(variant)
        if data is None:
            valid_variants = ", ".join(cls._firewood_data.keys())
            raise ValueError(f"Invalid firewood variant: {variant}. Valid variants are: {valid_variants}")
            
        # If no id is provided, generate a default id.
        if id is None:
            id = f"firewood_{variant}_{random.randint(1000, 9999)}"
            
        firewood = Firewood(
            id=id,
            name=data["name"],
            description=data["description"],
            is_movable=True,
            is_jumpable=False,
            is_usable_alone=True,
            is_collectable=True,  # Firewood can be collected
            weight=1,
            usable_with=set()
        )
        
        return firewood.to_dict()


# Example usage:
if __name__ == "__main__":
    # Create a fallen branch
    firewood = FirewoodFactory.create_firewood()
    print(f"Created Firewood: {firewood['name']}")
    print(f"Description: {firewood['description']}")
    print(f"Possible actions: {firewood['possible_actions']}")
    print(f"Movable: {firewood['is_movable']}")
    print(f"Collectable: {firewood['is_collectable']}")
    print(f"Weight: {firewood['weight']}") 

    import random

class LandObstacleFactory:
    @staticmethod
    def create_hole(name: str = "Hole", **props) -> GameObject:
        from game_object import GameObject
        return GameObject(
            id=str(uuid.uuid4()),
            name=name,
            description="A hole in the ground",
            is_movable=False,
            is_jumpable=True,
            is_usable_alone=False,
            weight=0,
            **props
        )

    @staticmethod
    def create_fallen_log(size: str = "medium", **props) -> GameObject:
        from game_object import GameObject
        return GameObject(
            id=str(uuid.uuid4()),
            name=f"{size.capitalize()} Fallen Log",
            description=f"A {size} fallen log",
            is_movable=True,
            is_jumpable=True,
            is_usable_alone=True,
            weight=5,
            **props
        )

    @staticmethod
    def create_tree_stump(height: int = 1, **props) -> GameObject:
        from game_object import GameObject
        return GameObject(
            id=str(uuid.uuid4()),
            name=f"Tree Stump ({height}m)",
            description=f"A tree stump {height} meters high",
            is_movable=False,
            is_jumpable=True,
            is_usable_alone=True,
            weight=10,
            **props
        )

    @staticmethod
    def create_rock(rock_type: str = "boulder", **props) -> GameObject:
        """Create a rock obstacle.
        
        Args:
            rock_type: Type of rock ("pebble", "stone", or "boulder")
        """
        rock_properties = {
            "pebble": {
                "name": "Small Pebble", 
                "weight": 1, 
                "is_movable": True,
                "is_collectable": True
            },
            "stone": {
                "name": "Stone", 
                "weight": 3, 
                "is_movable": True,
                "is_collectable": False
            },
            "boulder": {
                "name": "Large Boulder", 
                "weight": 15, 
                "is_movable": False,
                "is_collectable": False
            }
        }
        
        rock_props = rock_properties.get(rock_type, rock_properties["boulder"])
        
        return GameObject(
            id=f"{rock_type}_{random.randint(1000, 9999)}",
            is_jumpable=True,
            **rock_props,
            **props
        )
    
    @staticmethod
    def create_plant(plant_type: str, **props) -> GameObject:
        """Create a plant or flower obstacle.
        
        Args:
            plant_type: Type of plant ("bush", "wild-bush", "leafs", "soft-grass", "tall-grass", "dense-bush", "grass")
        """
        plant_properties = {
            "bush": {
                "name": "Bush",
                "weight": 1,
                "is_collectable": True,
                "is_movable": True
            },
            "wild-bush": {
                "name": "Wild Bush",
                "weight": 1,
                "is_collectable": True,
                "is_movable": True
            },
            "leafs": {
                "name": "Leafs",
                "weight": 1,
                "is_collectable": True,
                "is_movable": True
            },
            "soft-grass": {
                "name": "Soft Grass",
                "weight": 2,
                "is_collectable": True,
                "is_movable": True
            },
            "tall-grass": {
                "name": "Tall Grass",
                "weight": 1,
                "is_collectable": True,
                "is_movable": True
            },
            "dense-bush": {
                "name": "Dense Bush",
                "weight": 4,
                "is_collectable": False,
                "is_movable": False
            },
            "grass": {
                "name": "Grass",
                "weight": 3,
                "is_collectable": False,
                "is_movable": True
            }
        }
        
        if plant_type not in plant_properties:
            plant_type = random.choice(list(plant_properties.keys()))
            
        plant_props = plant_properties[plant_type]
        
        # Create a copy of props to avoid modifying the original
        final_props = props.copy()
        
        # Update final_props with plant_props, but don't override existing props
        for key, value in plant_props.items():
            if key not in final_props:
                final_props[key] = value
        
        return GameObject(
            id=f"{plant_type}_{random.randint(1000, 9999)}",
            is_jumpable=True,
            **final_props
        )
    
    @staticmethod
    def create_chestnut_tree(**props) -> GameObject:
        """Create a chestnut tree obstacle that cannot be jumped over."""
        return GameObject(
            id=f"chestnut_tree_{random.randint(1000, 9999)}",
            name="Chestnut Tree",
            is_jumpable=False,  # Explicitly not jumpable as requested
            is_movable=False,
            is_collectable=False,
            weight=50,
            **props
        )
    
    @staticmethod
    def create_random_obstacle(**props) -> GameObject:
        """Create a random land obstacle."""
        factories = [
            LandObstacleFactory.create_hole,
            lambda **p: LandObstacleFactory.create_fallen_log(random.choice(["small", "medium", "large"]), **p),
            lambda **p: LandObstacleFactory.create_tree_stump(random.randint(1, 3), **p),
            lambda **p: LandObstacleFactory.create_rock(random.choice(["pebble", "stone", "boulder"]), **p),
            lambda **p: LandObstacleFactory.create_plant(random.choice([
                "bush", "wild-bush", "leafs", "soft-grass", "tall-grass", "dense-bush", "grass"
            ]), **p),
            LandObstacleFactory.create_chestnut_tree
        ]
        
        factory = random.choice(factories)
        return factory(**props)


def create_land_obstacle(obstacle_type: str = None, **props) -> dict:
    """
    Create a land obstacle object.
    
    Args:
        obstacle_type (str, optional): Specific type of obstacle to create. If None, creates a random obstacle.
        **props: Additional properties to pass to the obstacle creation method.
        
    Returns:
        dict: A dictionary representation of the land obstacle with position and other metadata.
    """
    # Use specific factory method if obstacle_type is provided
    if obstacle_type == "hole":
        game_obj = LandObstacleFactory.create_hole(**props)
    elif obstacle_type == "log":
        size = props.pop("size", "medium")
        game_obj = LandObstacleFactory.create_fallen_log(size, **props)
    elif obstacle_type == "stump":
        height = props.pop("height", 1)
        game_obj = LandObstacleFactory.create_tree_stump(height, **props)
    elif obstacle_type == "rock":
        rock_type = props.pop("rock_type", "boulder")
        game_obj = LandObstacleFactory.create_rock(rock_type, **props)
    elif obstacle_type == "plant":
        plant_type = props.pop("plant_type", random.choice(["bush", "wild-bush", "leafs", "soft-grass", "tall-grass", "dense-bush", "grass"]))
        game_obj = LandObstacleFactory.create_plant(plant_type, **props)
    elif obstacle_type == "tree":
        game_obj = LandObstacleFactory.create_chestnut_tree(**props)
    else:
        # Create a random obstacle
        game_obj = LandObstacleFactory.create_random_obstacle(**props)
    
    # Convert GameObject to a dictionary representation
    obstacle_data = game_obj.to_dict()
    obstacle_data["type"] = obstacle_type or "random"
    
    # Add any additional properties
    for key, value in props.items():
        if key not in obstacle_data:
            obstacle_data[key] = value
    
    return obstacle_data 

from dataclasses import dataclass, field
from typing import Dict, Any, Set
import random

from game_object import GameObject

# Action constants
ACTION_SIT = "sit"


@dataclass
class LogStool(GameObject):
    """
    A squat log that can be used as a stool for sitting.
    """
    description: str = ""
    possible_alone_actions: Set[str] = field(default_factory=set)  # Actions available when used alone

    def __post_init__(self):
        # Log stools are movable and can be interacted with
        self.is_movable = True
        self.is_jumpable = False
        self.is_usable_alone = True
        self.weight = 3  # Logs are moderately heavy
        self.usable_with = set()
        self.possible_alone_actions = {ACTION_SIT}
        super().__post_init__()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the log stool object to a dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_movable": self.is_movable,
            "is_jumpable": self.is_jumpable,
            "is_usable_alone": self.is_usable_alone,
            "weight": self.weight,
            "possible_actions": list(self.possible_alone_actions),
            "usable_with": list(self.usable_with)
        }


class LogStoolFactory:
    """
    Factory to create log stool objects.
    """
    _stool_data: Dict[str, Dict[str, Any]] = {
        "squat": {
            "name": "Squat Log",
            "description": "A short, sturdy log that can be used as a stool."
        }
    }
    
    @classmethod
    def create_stool(cls, variant: str = "squat", id: str = None) -> Dict[str, Any]:
        data = cls._stool_data.get(variant)
        if data is None:
            valid_variants = ", ".join(cls._stool_data.keys())
            raise ValueError(f"Invalid stool variant: {variant}. Valid variants are: {valid_variants}")
            
        # If no id is provided, generate a default id.
        if id is None:
            id = f"stool_{variant}_{random.randint(1000, 9999)}"
            
        stool = LogStool(
            id=id,
            name=data["name"],
            description=data["description"],
            is_movable=True,
            is_jumpable=False,
            is_usable_alone=True,
            weight=3,
            usable_with=set()
        )
        
        return stool.to_dict()

# Pot size constants
POT_SIZE_SMALL = "small"
POT_SIZE_MEDIUM = "medium"
POT_SIZE_BIG = "big"

# Pot state constants
POT_STATE_DEFAULT = "default"
POT_STATE_BREAKING = "breaking"
POT_STATE_BROKEN = "broken"

@dataclass
class Pot(Container):
    """A pot that can contain items and has different states."""
    pot_size: str = POT_SIZE_MEDIUM  # Size of the pot
    state: str = POT_STATE_DEFAULT  # Current state of the pot
    max_durability: int = 100  # Maximum durability
    current_durability: int = 100  # Current durability
    
    def __post_init__(self):
        # Set basic properties based on pot size
        if self.pot_size == POT_SIZE_SMALL:
            self.is_movable = True
            self.is_jumpable = True
            self.capacity = 3
            self.weight = 5
            self.max_durability = 50
            self.current_durability = 50
        elif self.pot_size == POT_SIZE_MEDIUM:
            self.is_movable = True
            self.is_jumpable = False
            self.capacity = 5
            self.weight = 10
            self.max_durability = 75
            self.current_durability = 75
        else:  # POT_SIZE_BIG
            self.is_movable = False
            self.is_jumpable = False
            self.capacity = 8
            self.weight = 20
            self.max_durability = 100
            self.current_durability = 100
            
        self.is_usable_alone = True
        self.is_collectable = False
        super().__post_init__()
    
    def damage(self, amount: int) -> Dict[str, Any]:
        """Apply damage to the pot, potentially changing its state."""
        if self.state == POT_STATE_BROKEN:
            return {"success": False, "message": f"The {self.name} is already broken"}
            
        self.current_durability = max(0, self.current_durability - amount)
        
        # Update state based on durability percentage
        durability_percentage = (self.current_durability / self.max_durability) * 100
        
        if durability_percentage <= 0:
            old_state = self.state
            self.state = POT_STATE_BROKEN
            # If broken, reduce capacity and empty contents if any
            self.capacity = 0
            self.contents = []
            return {
                "success": True,
                "message": f"The {self.name} has been broken!",
                "old_state": old_state,
                "new_state": self.state
            }
        elif durability_percentage <= 30:
            old_state = self.state
            self.state = POT_STATE_BREAKING
            return {
                "success": True,
                "message": f"The {self.name} is starting to crack!",
                "old_state": old_state,
                "new_state": self.state
            }
        
        return {
            "success": True,
            "message": f"The {self.name} took {amount} damage.",
            "current_durability": self.current_durability,
            "max_durability": self.max_durability
        }
        
    def add_item(self, item: GameObject) -> Dict[str, Any]:
        """Override to prevent adding items to broken pots."""
        if self.state == POT_STATE_BROKEN:
            return {"success": False, "message": f"Cannot add items to a broken {self.name}"}
        return super().add_item(item)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the pot object to a dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description if hasattr(self, "description") else "",
            "size": self.pot_size,
            "state": self.state,
            "capacity": self.capacity,
            "weight": self.weight,
            "is_movable": self.is_movable,
            "is_jumpable": self.is_jumpable,
            "is_usable_alone": self.is_usable_alone,
            "is_collectable": self.is_collectable,
            "durability": self.current_durability,
            "max_durability": self.max_durability,
            "contents": self.contents,
            "possible_actions": list(self.possible_alone_actions),
            "usable_with": list(self.usable_with)
        }


class PotFactory:
    """Factory to create pot objects with different sizes and states."""
    
    _pot_data: Dict[str, Dict[str, Any]] = {
        POT_SIZE_SMALL: {
            "name": "Small Vase",
            "description": "A small decorative vase that can hold a few small items.",
            "capacity": 3,
            "weight": 5,
            "max_durability": 50
        },
        POT_SIZE_MEDIUM: {
            "name": "Medium Vase",
            "description": "A medium-sized vase that can hold several items.",
            "capacity": 5,
            "weight": 10,
            "max_durability": 75
        },
        POT_SIZE_BIG: {
            "name": "Large Vase",
            "description": "A large ornate vase with significant storage capacity.",
            "capacity": 8,
            "weight": 20,
            "max_durability": 100
        }
    }
    
    @classmethod
    def create_pot(cls, size: str = POT_SIZE_MEDIUM, state: str = POT_STATE_DEFAULT, id: str = None) -> Dict[str, Any]:
        """
        Create a pot object.
        
        Args:
            size (str): Size of the pot (small, medium, or big)
            state (str): Initial state of the pot (default, breaking, or broken)
            id (str, optional): An optional id for the pot. If not provided, a default is generated.
            
        Returns:
            Dict[str, Any]: A dictionary representation of the pot.
        
        Raises:
            ValueError: If an invalid size or state is provided.
        """
        # Validate size
        if size not in cls._pot_data:
            valid_sizes = ", ".join(cls._pot_data.keys())
            raise ValueError(f"Invalid pot size: {size}. Valid sizes are: {valid_sizes}")
        
        # Validate state
        valid_states = [POT_STATE_DEFAULT, POT_STATE_BREAKING, POT_STATE_BROKEN]
        if state not in valid_states:
            valid_states_str = ", ".join(valid_states)
            raise ValueError(f"Invalid pot state: {state}. Valid states are: {valid_states_str}")
            
        # If no id is provided, generate a default id.
        if id is None:
            id = f"pot_{size}_{random.randint(1000, 9999)}"
        
        # Create the pot with basic properties
        data = cls._pot_data[size]
        pot = Pot(
            id=id,
            name=data["name"],
            pot_size=size,
            state=state,
            max_durability=data["max_durability"],
            current_durability=data["max_durability"] if state == POT_STATE_DEFAULT else
                              data["max_durability"] * 0.3 if state == POT_STATE_BREAKING else 0,
            capacity=data["capacity"] if state != POT_STATE_BROKEN else 0,
            weight=data["weight"]
        )
        
        # Adjust properties based on state
        if state == POT_STATE_BROKEN:
            pot.capacity = 0
            pot.contents = []
            
        return pot.to_dict()


def create_pot(size: str = None, state: str = None) -> Dict[str, Any]:
    """
    Create a pot object for use in the game world.
    
    Args:
        size (str, optional): Size of the pot. If None, a random size is chosen.
        state (str, optional): State of the pot. If None, defaults to "default".
        
    Returns:
        Dict: A dictionary representation of the pot object.
    """
    # Choose random size if not specified
    if size is None:
        size = random.choice([POT_SIZE_SMALL, POT_SIZE_MEDIUM, POT_SIZE_BIG])
    
    # Default state if not specified
    if state is None:
        state = POT_STATE_DEFAULT
        
    # Create a pot using the factory
    return PotFactory.create_pot(size=size, state=state)

# Action constants
ACTION_ENTER = "enter"
ACTION_EXIT = "exit"


@dataclass
class Tent(GameObject):
    """
    A tent that can shelter people.
    """
    description: str = ""
    max_capacity: int = 1  # Maximum number of people that can fit in the tent
    contained_items: List[str] = field(default_factory=list)  # People currently in the tent
    possible_alone_actions: Set[str] = field(default_factory=set)  # Actions available when used alone

    def __post_init__(self):
        # Tents are movable but become immovable when set up
        self.is_movable = True
        self.is_jumpable = False
        self.is_usable_alone = True
        self.weight = 5  # Tents are heavy
        self.usable_with = set()
        self.possible_alone_actions = {ACTION_ENTER, ACTION_EXIT}
        super().__post_init__()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the tent object to a dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "max_capacity": self.max_capacity,
            "contained_items": self.contained_items,
            "is_movable": self.is_movable,
            "is_jumpable": self.is_jumpable,
            "is_usable_alone": self.is_usable_alone,
            "weight": self.weight,
            "possible_actions": list(self.possible_alone_actions),
            "usable_with": list(self.usable_with)
        }


class TentFactory:
    """
    Factory to create tent objects.
    """
    _tent_data: Dict[str, Dict[str, Any]] = {
        "small": {
            "name": "Tent",
            "description": "A small tent that can shelter one person."
        }
    }
    
    @classmethod
    def create_tent(cls, variant: str = "small", id: str = None) -> Dict[str, Any]:
        """
        Create a tent object.
        
        Args:
            variant (str): The variant of tent to create (currently only "small").
            id (str, optional): An optional id for the tent. If not provided, a default is generated.
            
        Returns:
            Dict[str, Any]: A dictionary representation of the tent.
        
        Raises:
            ValueError: If an invalid variant is provided.
        """
        data = cls._tent_data.get(variant)
        if data is None:
            valid_variants = ", ".join(cls._tent_data.keys())
            raise ValueError(f"Invalid tent variant: {variant}. Valid variants are: {valid_variants}")
            
        # If no id is provided, generate a default id.
        if id is None:
            id = f"tent_{variant}_{random.randint(1000, 9999)}"
            
        tent = Tent(
            id=id,
            name=data["name"],
            description=data["description"],
            max_capacity=1,
            is_movable=True,
            is_jumpable=False,
            is_usable_alone=True,
            weight=5,
            usable_with=set()
        )
        
        return tent.to_dict()

class WeatherType(Enum):
    """Enum defining different types of weather conditions."""
    CLOUD_COVER = auto()
    RAINFALL = auto()
    SNOWFALL = auto()
    LIGHTNING_STRIKES = auto()
    SNOW_COVER = auto()
    CLEAR = auto()


@dataclass
class WeatherParameters:
    """Parameters that define a weather condition's properties."""
    intensity: float = 0.5  # 0.0 to 1.0, how intense the weather is
    duration: int = 100     # How many turns/time units the weather lasts
    coverage: float = 0.8   # 0.0 to 1.0, how much of the map is affected


class Weather:
    """Base class for all weather conditions."""
    
    def __init__(self, params: WeatherParameters):
        self.params = params
        self.remaining_duration = params.duration
        
    def update(self, delta_time: float = 1.0) -> None:
        """Update the weather state."""
        self.remaining_duration -= delta_time
        
    def is_active(self) -> bool:
        """Check if the weather is still active."""
        return self.remaining_duration > 0
        
    def get_effects(self) -> Dict[str, Any]:
        """Get the game effects of this weather."""
        return {}


class CloudCover(Weather):
    """Cloud cover reduces visibility and affects mood."""
    
    def get_effects(self) -> Dict[str, Any]:
        return {
            "visibility_reduction": self.params.intensity * 0.3,
            "mood_modifier": -0.2 * self.params.intensity,
            "temperature_modifier": -1 * self.params.intensity
        }


class Rainfall(Weather):
    """Rainfall affects movement speed, visibility, and can extinguish fires."""
    
    def get_effects(self) -> Dict[str, Any]:
        return {
            "movement_speed_modifier": -0.2 * self.params.intensity,
            "visibility_reduction": self.params.intensity * 0.5,
            "fire_extinguish_chance": 0.1 * self.params.intensity,
            "temperature_modifier": -2 * self.params.intensity,
            "mood_modifier": -0.3 * self.params.intensity
        }


class Snowfall(Weather):
    """Snowfall heavily affects movement and visibility, and causes snow cover to build up."""
    
    def get_effects(self) -> Dict[str, Any]:
        return {
            "movement_speed_modifier": -0.4 * self.params.intensity,
            "visibility_reduction": self.params.intensity * 0.7,
            "temperature_modifier": -5 * self.params.intensity,
            "mood_modifier": 0.1 - (0.4 * self.params.intensity)  # Light snow is pleasant, heavy snow is not
        }


class LightningStrikes(Weather):
    """Lightning can damage entities, start fires, and affect visibility."""
    
    def get_effects(self) -> Dict[str, Any]:
        return {
            "lightning_strike_chance": 0.05 * self.params.intensity,
            "damage_on_strike": 5 + (10 * self.params.intensity),
            "fire_start_chance": 0.2 * self.params.intensity,
            "visibility_flash": 1.0,  # Momentary full visibility during lightning
            "mood_modifier": -0.5 * self.params.intensity
        }


class SnowCover(Weather):
    """Snow accumulated on the ground, affecting movement and game mechanics."""
    
    def get_effects(self) -> Dict[str, Any]:
        return {
            "movement_speed_modifier": -0.3 * self.params.intensity,
            "tracking_bonus": 0.5 * self.params.intensity,  # Easier to track in snow
            "temperature_modifier": -3 * self.params.intensity,
            "concealment_penalty": 0.4 * self.params.intensity  # Harder to hide in snow
        }


class Clear(Weather):
    """Clear weather has positive effects on mood and visibility."""
    
    def get_effects(self) -> Dict[str, Any]:
        return {
            "visibility_bonus": 0.2,
            "mood_modifier": 0.3,
            "temperature_modifier": 2 * self.params.intensity
        }


class WeatherFactory:
    """Factory for creating weather objects based on type."""
    
    @classmethod
    def create_weather(cls, weather_type: WeatherType, params: WeatherParameters) -> Weather:
        """Create a weather object of the specified type."""
        weather_map = {
            WeatherType.CLOUD_COVER: CloudCover,
            WeatherType.RAINFALL: Rainfall,
            WeatherType.SNOWFALL: Snowfall,
            WeatherType.LIGHTNING_STRIKES: LightningStrikes,
            WeatherType.SNOW_COVER: SnowCover,
            WeatherType.CLEAR: Clear,
        }
        
        weather_class = weather_map.get(weather_type)
        if not weather_class:
            raise ValueError(f"Unknown weather type: {weather_type}")
            
        return weather_class(params)


class WeatherSystem:
    """System that manages weather conditions in the game."""
    
    def __init__(self):
        self.current_weather = []
        
    def add_weather(self, weather: Weather) -> None:
        """Add a weather condition to the system."""
        self.current_weather.append(weather)
        
    def update(self, delta_time: float = 1.0) -> None:
        """Update all weather conditions and remove inactive ones."""
        self.current_weather = [w for w in self.current_weather if w.is_active()]
        
        for weather in self.current_weather:
            weather.update(delta_time)
            
    def get_combined_effects(self) -> Dict[str, float]:
        """Combine the effects of all active weather conditions."""
        combined_effects = {}
        
        for weather in self.current_weather:
            effects = weather.get_effects()
            
            for effect, value in effects.items():
                if effect in combined_effects:
                    # For most effects, we take the most extreme value
                    if "modifier" in effect or "reduction" in effect:
                        combined_effects[effect] = min(combined_effects[effect], value) if value < 0 else max(combined_effects[effect], value)
                    # For chances, we add them up to a max of 1.0
                    elif "chance" in effect:
                        combined_effects[effect] = min(combined_effects[effect] + value, 1.0)
                    # For other effects, we take the max
                    else:
                        combined_effects[effect] = max(combined_effects[effect], value)
                else:
                    combined_effects[effect] = value
                    
        return combined_effects
        
    def get_game_state(self) -> Dict[str, Any]:
        """Get the current weather state for the game."""
        active_weather = []
        for weather in self.current_weather:
            weather_type = type(weather).__name__
            active_weather.append({
                "type": weather_type,
                "intensity": weather.params.intensity,
                "remaining_duration": weather.remaining_duration,
                "coverage": weather.params.coverage
            })
            
        return {
            "active_weather": active_weather,
            "combined_effects": self.get_combined_effects()
        }
        
    def get_random_weather(self, exclude_types: List[WeatherType] = None) -> Weather:
        """Generate a random weather condition."""
        exclude_types = exclude_types or []
        available_types = [w for w in WeatherType if w not in exclude_types]
        
        if not available_types:
            return None
            
        weather_type = random.choice(available_types)
        
        # Generate random parameters
        params = WeatherParameters(
            intensity=random.uniform(0.2, 1.0),
            duration=random.randint(50, 200),
            coverage=random.uniform(0.5, 1.0)
        )
        
        return WeatherFactory.create_weather(weather_type, params)
    
    
class GameFactory:
    """Factory for generating complete game worlds with maps and objects."""
    
    def __init__(self, map_size: int = MAP_SIZE, border_size: int = BORDER_SIZE):
        """
        Initialize the game factory.
        
        Args:
            map_size: Size of the map (square)
            border_size: Size of the water border
        """
        self.map_size = map_size
        self.border_size = border_size
        self.map_grid = None
        self.objects = {
            "chests": [],
            "camps": [],
            "obstacles": [],
            "campfires": [],
            "backpacks": [],
            "firewood": [],
            "tents": [],
            "bedrolls": [],
            "log_stools": [],
            "campfire_spits": [],
            "campfire_pots": [],
            "pots": []
        }

    def find_valid_player_position(self) -> Tuple[int, int]:
        """
        Find a valid starting position for the player that:
        1. Is on land
        2. Is not occupied by any object
        3. Has at least 5 free adjacent positions for movement
        
        Returns:
            Tuple[int, int]: A valid (x, y) position for the player
        """
        # Get all land tiles
        land_tiles = []
        for y in range(self.map_size):
            for x in range(self.map_size):
                if y < self.border_size or y >= self.map_size - self.border_size or \
                   x < self.border_size or x >= self.map_size - self.border_size:
                    continue
                
                # Check if the tile is land
                if self.map_grid[y][x] == "$$$":
                    # Check if the tile is already occupied
                    occupied = False
                    for obj_type, obj_list in self.objects.items():
                        for obj in obj_list:
                            if obj["position"] == (x, y):
                                occupied = True
                                break
                        if occupied:
                            break
                    
                    if not occupied:
                        land_tiles.append((x, y))
        
        # Shuffle the land tiles for random selection
        random.shuffle(land_tiles)
        
        # Check each tile for valid movement options
        for x, y in land_tiles:
            free_positions = 0
            
            # Check adjacent positions (including diagonals)
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                        
                    new_x = x + dx
                    new_y = y + dy
                    
                    # Check if position is valid and free
                    if (new_x >= self.border_size and new_x < self.map_size - self.border_size and
                        new_y >= self.border_size and new_y < self.map_size - self.border_size and
                        self.map_grid[new_y][new_x] == "$$$"):
                        
                        # Check if position is occupied
                        occupied = False
                        for obj_type, obj_list in self.objects.items():
                            for obj in obj_list:
                                if obj["position"] == (new_x, new_y):
                                    occupied = True
                                    break
                            if occupied:
                                break
                        
                        if not occupied:
                            free_positions += 1
            
            # If we found a position with at least 5 free adjacent tiles
            if free_positions >= 5:
                return (x, y)
        
        # If no position found, return a default position
        return (self.border_size + 1, self.border_size + 1)
        
    def generate_world(self, 
                      chest_count: int = 5, 
                      camp_count: int = 3,
                      obstacle_count: int = 10,
                      campfire_count: int = 4,
                      backpack_count: int = 3,
                      firewood_count: int = 6,
                      tent_count: int = 2,
                      bedroll_count: int = 3,
                      log_stool_count: int = 4,
                      campfire_spit_count: int = 2,
                      campfire_pot_count: int = 2,
                      pot_count: int = 5) -> Dict[str, Any]:
        """
        Generate a complete game world with map and objects.
        
        Args:
            chest_count: Number of chests to place
            camp_count: Number of camps to place
            obstacle_count: Number of land obstacles to place
            campfire_count: Number of campfires to place
            backpack_count: Number of backpacks to place
            firewood_count: Number of firewood to place
            tent_count: Number of tents to place
            bedroll_count: Number of bedrolls to place
            log_stool_count: Number of log stools to place
            campfire_spit_count: Number of campfire spits to place
            campfire_pot_count: Number of campfire pots to place
            pot_count: Number of pots to place
            
        Returns:
            Dict containing the map, placed objects, and suggested player position
        """
        # Generate the map
        self.map_grid = generate_map()
        
        # Place objects in order of importance
        self.place_objects("obstacles", obstacle_count)
        self.place_objects("camps", camp_count)
        self.place_objects("campfires", campfire_count)
        self.place_objects("tents", tent_count)
        self.place_objects("bedrolls", bedroll_count)
        self.place_objects("log_stools", log_stool_count)
        self.place_objects("campfire_spits", campfire_spit_count)
        self.place_objects("campfire_pots", campfire_pot_count)
        self.place_objects("chests", chest_count)
        self.place_objects("backpacks", backpack_count)
        self.place_objects("firewood", firewood_count)
        self.place_objects("pots", pot_count)
        
        # Find a valid starting position for the player
        player_position = self.find_valid_player_position()
        
        return {
            "map": self.map_grid,
            "objects": self.objects,
            "player_position": player_position
        }
    
    def create_landmark(self) -> Dict[str, Any]:
        """
        Create a landmark object for the game world.
        
        Returns:
            Dict: A landmark object with attributes
        """
        landmark_types = ["tower", "statue", "ruins", "cave", "shrine", "portal", "monolith"]
        landmark_type = random.choice(landmark_types)
        
        # Randomize if the landmark is special (has unique properties)
        is_special = random.random() < 0.3  # 30% chance of being special
        
        landmark = {
            "type": landmark_type,
            "name": f"{landmark_type.capitalize()}",
            "special": is_special,
            "id": f"landmark_{landmark_type}_{random.randint(1000, 9999)}"
        }
        
        # Add special properties based on type
        if landmark_type == "tower":
            landmark["height"] = random.randint(3, 8)
            landmark["description"] = f"A {landmark['height']}-story high watchtower overlooking the area."
            if is_special:
                landmark["has_treasure"] = True
                landmark["locked"] = random.random() < 0.7  # 70% chance of being locked
                
        elif landmark_type == "statue":
            statue_subjects = ["hero", "king", "queen", "deity", "beast", "ancient_one"]
            landmark["subject"] = random.choice(statue_subjects)
            landmark["description"] = f"A statue of a {landmark['subject'].replace('_', ' ')}."
            if is_special:
                landmark["has_inscription"] = True
                landmark["gives_buff"] = random.random() < 0.5  # 50% chance of giving buff
                
        elif landmark_type == "ruins":
            ruin_types = ["temple", "fortress", "village", "castle", "outpost"]
            landmark["ruin_type"] = random.choice(ruin_types)
            landmark["description"] = f"Ruins of an ancient {landmark['ruin_type']}."
            if is_special:
                landmark["has_hidden_entrance"] = True
                landmark["guarded"] = random.random() < 0.4  # 40% chance of being guarded
                
        elif landmark_type == "cave":
            cave_types = ["small", "large", "deep", "crystal", "dark"]
            landmark["cave_type"] = random.choice(cave_types)
            landmark["description"] = f"A {landmark['cave_type']} cave entrance leading underground."
            if is_special:
                landmark["has_monster"] = random.random() < 0.6  # 60% chance of having monster
                landmark["has_treasure"] = random.random() < 0.7  # 70% chance of having treasure
                
        elif landmark_type == "shrine":
            shrine_types = ["nature", "warrior", "healer", "scholar", "traveler"]
            landmark["shrine_type"] = random.choice(shrine_types)
            landmark["description"] = f"A shrine dedicated to the {landmark['shrine_type']}."
            if is_special:
                landmark["gives_blessing"] = True
                landmark["requires_offering"] = random.random() < 0.5  # 50% chance of requiring offering
                
        elif landmark_type == "portal":
            portal_states = ["active", "dormant", "broken", "unstable"]
            landmark["state"] = random.choice(portal_states)
            landmark["description"] = f"A {landmark['state']} magical portal."
            if is_special:
                landmark["destination"] = "special_location"
                landmark["requires_key"] = random.random() < 0.8  # 80% chance of requiring key
                
        else:  # monolith
            monolith_materials = ["stone", "obsidian", "crystal", "metal", "unknown"]
            landmark["material"] = random.choice(monolith_materials)
            landmark["description"] = f"A towering monolith made of {landmark['material']}."
            if is_special:
                landmark["has_inscriptions"] = True
                landmark["magical"] = random.random() < 0.9  # 90% chance of being magical
                
        return landmark
    
    def create_npc(self) -> Dict[str, Any]:
        """
        Create an NPC for the game world.
        
        Returns:
            Dict: An NPC object with attributes
        """
        npc_types = ["villager", "hero", "merchant", "guard", "wizard", "monk", "thief"]
        npc_type = random.choice(npc_types)
        
        # Basic states
        states = ["idle", "walking", "sleeping", "working", "eating"]
        
        # Type-specific states
        type_states = {
            "villager": ["farming", "chatting", "crafting"],
            "hero": ["training", "resting", "negotiating"],
            "merchant": ["selling", "bargaining", "counting_coins"],
            "guard": ["patrolling", "watching", "fighting"],
            "wizard": ["studying", "brewing", "casting"],
            "monk": ["meditating", "teaching", "healing"],
            "thief": ["sneaking", "hiding", "stealing"]
        }
        
        # Combine basic states with type-specific states
        all_states = states + type_states.get(npc_type, [])
        state = random.choice(all_states)
        
        # Determine if hostile based on type (thieves more likely to be hostile)
        hostile_chance = {
            "thief": 0.7,
            "wizard": 0.3,
            "guard": 0.2,
            "hero": 0.1,
            "monk": 0.05,
            "merchant": 0.05,
            "villager": 0.02
        }
        is_hostile = random.random() < hostile_chance.get(npc_type, 0.1)
        
        # Create the NPC
        npc = {
            "id": f"npc_{npc_type}_{random.randint(1000, 9999)}",
            "type": npc_type,
            "name": f"{npc_type.capitalize()}",  # Could be expanded with name generation
            "level": random.randint(1, 5),
            "state": state,
            "hostile": is_hostile,
            "inventory": []
        }
        
        # Add some random items to inventory
        possible_items = ["potion", "food", "coin", "tool", "weapon", "clothing"]
        inventory_size = random.randint(0, 3)
        
        for _ in range(inventory_size):
            item_type = random.choice(possible_items)
            quantity = random.randint(1, 3)
            npc["inventory"].append({
                "type": item_type,
                "quantity": quantity,
                "id": f"item_{item_type}_{random.randint(1000, 9999)}"
            })
            
        return npc
        
    def place_objects(self, object_type: str, count: int) -> None:
        """
        Place objects randomly on land tiles.
        
        Args:
            object_type: Type of object to place 
            count: Number of objects to place
        """
        # Reset the objects list for this type
        self.objects[object_type] = []
        
        # Find all land tiles
        land_tiles = []
        for y in range(self.map_size):
            for x in range(self.map_size):
                if y < self.border_size or y >= self.map_size - self.border_size or \
                   x < self.border_size or x >= self.map_size - self.border_size:
                    continue
                
                # Check if the tile is land
                if self.map_grid[y][x] == "$$$":
                    # Check if the tile is already occupied by another object
                    occupied = False
                    for obj_type, obj_list in self.objects.items():
                        for obj in obj_list:
                            if obj["position"] == (x, y):
                                occupied = True
                                break
                        if occupied:
                            break
                    
                    if not occupied:
                        land_tiles.append((x, y))
        
        # Shuffle the land tiles
        random.shuffle(land_tiles)
        
        # Place objects on the first 'count' land tiles
        for i in range(min(count, len(land_tiles))):
            x, y = land_tiles[i]
            
            # Create the object
            if object_type == "chests":
                obj = create_chest()
            elif object_type == "camps":
                obj = create_camp()
            elif object_type == "obstacles":
                obj = create_land_obstacle()
            elif object_type == "campfires":
                obj = CampfireFactory.create_campfire("unlit")
            elif object_type == "backpacks":
                obj = BackpackFactory.create_backpack()
            elif object_type == "firewood":
                obj = FirewoodFactory.create_firewood()
            elif object_type == "tents":
                obj = TentFactory.create_tent()
            elif object_type == "bedrolls":
                obj = BedrollFactory.create_bedroll()
            elif object_type == "log_stools":
                obj = LogStoolFactory.create_stool()
            elif object_type == "campfire_spits":
                obj = CampfireSpitFactory.create_campfire_spit()
            elif object_type == "campfire_pots":
                obj = CampfirePotFactory.create_pot("tripod")
            elif object_type == "pots":
                obj = create_pot()
            else:
                continue
            
            # Add position to the object
            obj["position"] = (x, y)
            
            # Add to the objects list
            self.objects[object_type].append(obj)

    def print_world(self) -> None:
        """
        Print the game world with colored text representation.
        Each tile is represented by 3 characters.
        """
        if not self.map_grid:
            print("No world generated yet. Call generate_world() first.")
            return
        
        # Create a copy of the map grid for display
        display_grid = [row[:] for row in self.map_grid]
        
        # Place objects on the display grid in order of visibility (layering)
        
        # First obstacles (lowest layer above terrain)
        for obstacle in self.objects["obstacles"]:
            x, y = obstacle["position"]
            display_grid[y][x] = "OBS"
        
        # Add pots to the display grid
        for pot in self.objects["pots"]:
            x, y = pot["position"]
            if pot["size"] == "small":
                display_grid[y][x] = "SPT"
            elif pot["size"] == "medium":
                display_grid[y][x] = "MPT"
            else:  # big
                display_grid[y][x] = "BPT"
        
        # Then camps and camp-related items
        for camp in self.objects["camps"]:
            x, y = camp["position"]
            
            if camp["type"] == "bandit":
                display_grid[y][x] = "BND"
            elif camp["type"] == "traveler":
                display_grid[y][x] = "TRV"
            elif camp["type"] == "merchant":
                display_grid[y][x] = "MRC"
            elif camp["type"] == "military":
                display_grid[y][x] = "MIL"
            else:  # abandoned
                display_grid[y][x] = "ABD"
                
        for campfire in self.objects["campfires"]:
            x, y = campfire["position"]
            display_grid[y][x] = "CFR"
            
        for tent in self.objects["tents"]:
            x, y = tent["position"]
            display_grid[y][x] = "TNT"
            
        for bedroll in self.objects["bedrolls"]:
            x, y = bedroll["position"]
            display_grid[y][x] = "BDR"
            
        for log_stool in self.objects["log_stools"]:
            x, y = log_stool["position"]
            display_grid[y][x] = "LST"
            
        for campfire_spit in self.objects["campfire_spits"]:
            x, y = campfire_spit["position"]
            display_grid[y][x] = "CSP"
            
        for campfire_pot in self.objects["campfire_pots"]:
            x, y = campfire_pot["position"]
            display_grid[y][x] = "CPT"
            
        for firewood in self.objects["firewood"]:
            x, y = firewood["position"]
            display_grid[y][x] = "FWD"
        
        # Then chests and backpacks
        for chest in self.objects["chests"]:
            x, y = chest["position"]
            
            if chest["type"] == "wooden":
                display_grid[y][x] = "CHW"
            elif chest["type"] == "silver":
                display_grid[y][x] = "CHS"
            elif chest["type"] == "golden":
                display_grid[y][x] = "CHG" 
            else:  # magical
                display_grid[y][x] = "CHM"
                
        for backpack in self.objects["backpacks"]:
            x, y = backpack["position"]
            display_grid[y][x] = "BPK"
        
        # Count land tiles
        land_count = sum(1 for row in self.map_grid for tile in row if tile == "$$$")
        water_count = self.map_size * self.map_size - land_count
        
        # Print world summary
        print("\n== WORLD SUMMARY ==")
        print(f"Size: {self.map_size}x{self.map_size}")
        print(f"Land tiles: {land_count} ({land_count / (self.map_size * self.map_size) * 100:.1f}%)")
        print(f"Water tiles: {water_count} ({water_count / (self.map_size * self.map_size) * 100:.1f}%)")
        print(f"Objects: {sum(len(obj_list) for obj_list in self.objects.values())}")
        
        # Print the legend
        print("\n== WORLD MAP LEGEND ==")
        print(f"{Fore.BLUE}{Back.CYAN}~~~{Style.RESET_ALL} Water")
        print(f"{Fore.GREEN}{Back.BLACK}$$${Style.RESET_ALL} Land")
        print(f"{Fore.YELLOW}{Back.BLACK}CHW{Style.RESET_ALL} Wooden Chest   {Fore.YELLOW}{Back.BLACK}CHS{Style.RESET_ALL} Silver Chest   "
              f"{Fore.YELLOW}{Back.BLACK}CHG{Style.RESET_ALL} Golden Chest   {Fore.YELLOW}{Back.BLACK}CHM{Style.RESET_ALL} Magical Chest")
        print(f"{Fore.YELLOW}{Back.BLACK}BPK{Style.RESET_ALL} Backpack")
        print(f"{Fore.RED}{Back.BLACK}BND{Style.RESET_ALL} Bandit Camp   {Fore.RED}{Back.BLACK}TRV{Style.RESET_ALL} Traveler Camp   "
              f"{Fore.RED}{Back.BLACK}MRC{Style.RESET_ALL} Merchant Camp   {Fore.RED}{Back.BLACK}ABD{Style.RESET_ALL} Abandoned Camp")
        print(f"{Fore.RED}{Back.BLACK}CFR{Style.RESET_ALL} Campfire   {Fore.RED}{Back.BLACK}TNT{Style.RESET_ALL} Tent   "
              f"{Fore.RED}{Back.BLACK}BDR{Style.RESET_ALL} Bedroll   {Fore.RED}{Back.BLACK}LST{Style.RESET_ALL} Log Stool")
        print(f"{Fore.RED}{Back.BLACK}CSP{Style.RESET_ALL} Campfire Spit   {Fore.RED}{Back.BLACK}CPT{Style.RESET_ALL} Campfire Pot   "
              f"{Fore.RED}{Back.BLACK}FWD{Style.RESET_ALL} Firewood")
        print(f"{Fore.MAGENTA}{Back.BLACK}OBS{Style.RESET_ALL} Obstacle")
        print(f"{Fore.GREEN}{Back.BLACK}SPT{Style.RESET_ALL} Small Pot   {Fore.GREEN}{Back.BLACK}MPT{Style.RESET_ALL} Medium Pot   "
              f"{Fore.GREEN}{Back.BLACK}BPT{Style.RESET_ALL} Big Pot")
        print("=====================\n")
        
        # Print the map with colors
        for y in range(self.map_size):
            row = ""
            for x in range(self.map_size):
                tile = display_grid[y][x]
                
                if tile == "~~~":  # Water
                    row += f"{Fore.BLUE}{Back.CYAN}~~~{Style.RESET_ALL}"
                elif tile == "$$$":  # Land
                    row += f"{Fore.GREEN}{Back.BLACK}$$$"
                
                # Chests and backpacks (yellow)
                elif tile in ["CHW", "CHS", "CHG", "CHM", "BPK"]:
                    row += f"{Fore.YELLOW}{Back.BLACK}{tile}"
                
                # Camps and camp items (red)
                elif tile in ["BND", "TRV", "MRC", "ABD", "MIL", "CFR", "TNT", "BDR", "LST", "CSP", "CPT", "FWD"]:
                    row += f"{Fore.RED}{Back.BLACK}{tile}"
                
                # Obstacles (magenta)
                elif tile in ["OBS"]:
                    row += f"{Fore.MAGENTA}{Back.BLACK}{tile}"
                
                # Pots (green)
                elif tile in ["SPT", "MPT", "BPT"]:
                    row += f"{Fore.GREEN}{Back.BLACK}{tile}"
                
                else:
                    row += f"{Style.RESET_ALL}{tile}"
                
                # Add a space between tiles for better readability
                row += " "
            
            print(row + Style.RESET_ALL)
        
        # Print object details
        print(f"\nGame World Generated:")
        
        # Print chests
        print(f"- {len(self.objects['chests'])} chests")
        for i, chest in enumerate(self.objects['chests']):
            chest_type = chest['type'].capitalize()
            contents = ', '.join([f"{item['quantity']}× {item['name']}" for item in chest['contents'][:2]])
            if len(chest['contents']) > 2:
                contents += f", and {len(chest['contents']) - 2} more items"
            print(f"  {i+1}. {chest_type} chest {Fore.YELLOW}({chest['position'][0]},{chest['position'][1]}){Style.RESET_ALL}: {contents}")
        
        # Print backpacks
        print(f"- {len(self.objects['backpacks'])} backpacks")
        for i, backpack in enumerate(self.objects['backpacks']):
            capacity = backpack.get('capacity', 'Unknown')
            color = backpack.get('color', 'Unknown')
            print(f"  {i+1}. {color} backpack {Fore.YELLOW}({backpack['position'][0]},{backpack['position'][1]}){Style.RESET_ALL}: {capacity} capacity")
        
        # Print camps
        print(f"- {len(self.objects['camps'])} camps")
        for i, camp in enumerate(self.objects['camps']):
            occupants = len(camp['occupants'])
            camp_type = camp['type'].capitalize()
            size = camp['size'].capitalize()
            print(f"  {i+1}. {size} {camp_type} camp {Fore.RED}({camp['position'][0]},{camp['position'][1]}){Style.RESET_ALL}: {occupants} occupants, {len(camp['structures'])} structures")
        
        # Print camp items
        for item_type, color_code in [
            ('campfires', Fore.RED),
            ('tents', Fore.RED),
            ('bedrolls', Fore.RED),
            ('log_stools', Fore.RED),
            ('campfire_spits', Fore.RED),
            ('campfire_pots', Fore.RED),
            ('firewood', Fore.RED)
        ]:
            if len(self.objects[item_type]) > 0:
                item_name = item_type.replace('_', ' ')
                print(f"- {len(self.objects[item_type])} {item_name}")
                for i, item in enumerate(self.objects[item_type]):
                    quality = item.get('quality', 'standard').capitalize()
                    print(f"  {i+1}. {quality} {item_name[:-1]} {color_code}({item['position'][0]},{item['position'][1]}){Style.RESET_ALL}")
        
        # Print pots
        if len(self.objects['pots']) > 0:
            print(f"- {len(self.objects['pots'])} pots")
            for i, pot in enumerate(self.objects['pots']):
                size = pot['size'].capitalize()
                state = pot['state'].capitalize()
                durability = pot.get('durability', 'Unknown')
                max_durability = pot.get('max_durability', 'Unknown')
                durability_info = f"{durability}/{max_durability}" if durability != 'Unknown' else ''
                print(f"  {i+1}. {size} Vase ({state}) {Fore.GREEN}({pot['position'][0]},{pot['position'][1]}){Style.RESET_ALL}: " +
                     f"Capacity: {pot.get('capacity', 'Unknown')}, Durability: {durability_info}")
        
        print(f"- {len(self.objects['obstacles'])} obstacles")
        for i, obstacle in enumerate(self.objects['obstacles']):
            obstacle_type = obstacle['type'].capitalize() if 'type' in obstacle else 'Generic'
            print(f"  {i+1}. {obstacle_type} obstacle {Fore.MAGENTA}({obstacle['position'][0]},{obstacle['position'][1]}){Style.RESET_ALL}")
        
        # Print NPCs
        print(f"- {len(self.objects['npcs'])} NPCs")
        for i, npc in enumerate(self.objects['npcs']):
            npc_type = npc['type'].capitalize()
            status = "Hostile" if npc.get('hostile', False) else "Friendly"
            print(f"  {i+1}. Level {npc['level']} {npc_type} {Fore.CYAN}({npc['position'][0]},{npc['position'][1]}){Style.RESET_ALL}: {status}, {npc['state'].capitalize()}")

    def export_world_json(self) -> Dict[str, Any]:
        """
        Export the game world as a JSON-serializable dictionary.
        
        Returns:
            Dict containing all map and object information.
        """
        if not self.map_grid:
            return {"error": "No world generated yet. Call generate_world() first."}
        
        # Count land and water tiles
        land_count = sum(1 for row in self.map_grid for tile in row if tile == LAND_SYMBOL)
        water_count = self.map_size * self.map_size - land_count
        
        # Convert map grid to 0s and 1s (water = 0, land = 1)
        grid = []
        for row in self.map_grid:
            grid_row = []
            for cell in row:
                grid_row.append(1 if cell == "$$$" else 0)
            grid.append(grid_row)
        
        # Create the world data dictionary
        world_data = {
            "map": {
                "size": self.map_size,
                "border_size": self.border_size,
                "grid": grid,
                "statistics": {
                    "land_tiles": land_count,
                    "water_tiles": water_count,
                    "land_percentage": land_count / (self.map_size * self.map_size) * 100
                }
            },
            "objects": self.objects,
            "total_object_count": sum(len(obj_list) for obj_list in self.objects.values())
        }
        
        return world_data

    def export_world_ui_json(self) -> Dict[str, Any]:
        """
        Export the game world in UI-friendly format.
        
        Returns:
            Dict containing map and entities in UI format
        """
        if not self.map_grid:
            return {"error": "No world generated yet. Call generate_world() first."}
            
        # Convert map grid to 0s and 1s (water = 0, land = 1)
        ui_grid = []
        for row in self.map_grid:
            grid_row = []
            for cell in row:
                grid_row.append(1 if cell == "$$$" else 0)
            ui_grid.append(grid_row)
            
        # Convert objects to entities
        entities = []
            
        # Convert campfires
        for i, campfire in enumerate(self.objects["campfires"]):
            entities.append({
                "id": f"campfire-{i+1}",
                "type": "campfire",
                "name": "Camp Fire",
                "position": {"x": campfire["position"][0], "y": campfire["position"][1]},
                "state": campfire["state"],
                "variant": "1",
                "isMovable": False,
                "isJumpable": True,
                "isUsableAlone": True,
                "isCollectable": False,
                "isWearable": False,
                "weight": 5,
                "possibleActions": ["light", "extinguish"],
                "description": campfire.get("description", "A place to cook and keep warm.")
            })
            
        # Convert pots
        for i, pot in enumerate(self.objects["pots"]):
            entities.append({
                "id": f"pot-{i+1}",
                "type": "pot",
                "name": "Pot",
                "position": {"x": pot["position"][0], "y": pot["position"][1]},
                "state": pot.get("state", "idle"),
                "variant": "1",
                "isMovable": pot.get("is_movable", True),
                "isJumpable": pot.get("is_jumpable", False),
                "isUsableAlone": True,
                "isCollectable": False,
                "isWearable": False,
                "weight": pot.get("weight", 3),
                "capacity": pot.get("capacity", 5),
                "durability": pot.get("durability", 100),
                "maxDurability": pot.get("max_durability", 100),
                "size": pot.get("size", "medium"),
                "description": pot.get("description", "A container that can hold items.")
            })

        # Convert chests
        for i, chest in enumerate(self.objects["chests"]):
            entities.append({
                "id": chest.get("id", f"chest-{i+1}"),
                "type": "chest",
                "name": f"{chest['type'].capitalize()} Chest",
                "position": {"x": chest["position"][0], "y": chest["position"][1]},
                "state": "closed" if chest.get("locked", False) else "open",
                "variant": chest["type"],
                "isMovable": False,
                "isJumpable": False,
                "isUsableAlone": True,
                "isCollectable": False,
                "isWearable": False,
                "weight": 10,
                "locked": chest.get("locked", False),
                "lockType": chest.get("lock_type", None),
                "contents": chest.get("contents", []),
                "description": chest.get("description", "A container for storing valuable items.")
            })

        # Convert camp items (tents, bedrolls, log stools, etc.)
        for item_type in ["tents", "bedrolls", "log_stools", "campfire_spits", "campfire_pots", "firewood"]:
            for i, item in enumerate(self.objects[item_type]):
                base_name = item_type[:-1].replace("_", " ").title()
                entities.append({
                    "id": item.get("id", f"{item_type[:-1]}-{i+1}"),
                    "type": item_type[:-1],
                    "name": f"{item.get('quality', 'Standard')} {base_name}",
                    "position": {"x": item["position"][0], "y": item["position"][1]},
                    "state": item.get("state", "idle"),
                    "variant": "1",
                    "isMovable": item.get("is_movable", True),
                    "isJumpable": item.get("is_jumpable", False),
                    "isUsableAlone": item.get("is_usable_alone", True),
                    "isCollectable": item.get("is_collectable", False),
                    "isWearable": item.get("is_wearable", False),
                    "weight": item.get("weight", 2),
                    "quality": item.get("quality", "standard"),
                    "durability": item.get("durability", 100),
                    "maxDurability": item.get("max_durability", 100),
                    "description": item.get("description", f"A {base_name.lower()} that can be used in camp.")
                })
            
        return {
            "map": {
                "size": self.map_size,
                "border_size": self.border_size,
                "grid": ui_grid
            },
            "entities": entities
        }
    
if __name__ == "__main__":
    # Create a game factory
    factory = GameFactory()
    
    # Generate a world with all object types
    world = factory.generate_world(
        chest_count=8, 
        camp_count=4, 
        obstacle_count=12,
        campfire_count=6,
        backpack_count=5,
        firewood_count=8,
        tent_count=4,
        bedroll_count=5,
        log_stool_count=6,
        campfire_spit_count=3,
        campfire_pot_count=3,
        pot_count=6
    )
    
    # Print the world
    factory.print_world()
    
    # Print and save JSON representations
    import json
    from datetime import datetime
    
    # Generate timestamp and filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    map_filename = f"{timestamp}-map.json"
    ui_filename = f"{timestamp}-ui.json"
    
    # Save original map JSON
    world_json = factory.export_world_json()
    print("\nJSON representation of the world:")
    print(json.dumps(world_json, indent=2))
    
    with open(map_filename, 'w') as f:
        json.dump(world_json, f, indent=2)
    print(f"\nMap saved to: {map_filename}")
    
    # Save UI JSON
    ui_json = factory.export_world_ui_json()
    print("\nUI JSON representation of the world:")
    print(json.dumps(ui_json, indent=2))
    
    with open(ui_filename, 'w') as f:
        json.dump(ui_json, f, indent=2)
    print(f"UI map saved to: {ui_filename}") 

class RainWeatherObject(GameObject):
    """Rain drop object that falls down the screen."""
    def __init__(self, x_pos, id_num):
        from game_object import GameObject  # Import updated
        super().__init__(
            id=f"rain_{id_num}",
            name="Rain Drop",
            description="A drop of rain falling from the sky",
            is_movable=False
        )
        # ... existing code ...

class CloudWeatherObject(GameObject):
    """Cloud object that moves across the screen."""
    def __init__(self, y_pos, id_num):
        from game_object import GameObject  # Import updated
        super().__init__(
            id=f"cloud_{id_num}",
            name="Cloud",
            description="A fluffy cloud floating in the sky",
            is_movable=False
        )
        # ... existing code ...

class LightningWeatherObject(GameObject):
    """Lightning bolt that briefly appears on the screen."""
    def __init__(self, x_pos, id_num):
        from game_object import GameObject  # Import updated
        super().__init__(
            id=f"lightning_{id_num}",
            name="Lightning Bolt",
            description="A bright flash of lightning",
            is_movable=False
        )
        # ... existing code ...