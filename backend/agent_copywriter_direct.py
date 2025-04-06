import asyncio
import inspect
import json
import logging
import os
import random
import time
import traceback
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union, Tuple

from person import Person
from entity import Entity

try:
    from agents import Agent, Runner, function_tool, RunContextWrapper
except ImportError:
    print("\nERROR: Could not import 'agents'.")
    print("Please ensure the OpenAI Agents SDK is installed correctly.")
    print("Installation might be like: pip install openai-agents (check the actual package name)")
    raise
try:
    from openai import AsyncOpenAI, OpenAI, OpenAIError, BadRequestError  # Import specific error
    from pydantic import BaseModel, Field, ValidationError
except ImportError:
    print("\nERROR: Could not import 'openai' or 'pydantic'.")
    print("Please install them (`pip install openai pydantic`).")
    raise

try:
    from factory_game import (
        MAP_SIZE as DEFAULT_MAP_SIZE,
        BORDER_SIZE as DEFAULT_BORDER_SIZE,
        LAND_SYMBOL,
        generate_island_map,
        BackpackFactory, BedrollFactory, CampfireFactory,
        CampfirePotFactory, CampfireSpitFactory, ChestFactory, FirewoodFactory,
        LogStoolFactory, PotFactory, TentFactory, create_land_obstacle
    )

    FACTORY_GAME_AVAILABLE = True
except ImportError:
    print("\nWARNING: Could not import 'factory_game'. World generation tools will fail.")
    print("Ensure 'factory_game.py' is in the same directory or your PYTHONPATH,")
    print("or that the 'factory_game' package is installed.")
    FACTORY_GAME_AVAILABLE = False
    DEFAULT_MAP_SIZE = 50
    DEFAULT_BORDER_SIZE = 5
    LAND_SYMBOL = '#'


    def generate_island_map(size, border_size):
        raise NotImplementedError("factory_game not available")


    class DummyFactory:
        @staticmethod
        def create_chest(*args, **kwargs): raise NotImplementedError("factory_game not available")

        @staticmethod
        def create_backpack(*args, **kwargs): raise NotImplementedError("factory_game not available")


    ChestFactory = BackpackFactory = BedrollFactory = CampfireFactory = DummyFactory
    CampfirePotFactory = CampfireSpitFactory = FirewoodFactory = LogStoolFactory = DummyFactory
    PotFactory = TentFactory = DummyFactory


    def create_land_obstacle(*args, **kwargs):
        raise NotImplementedError("factory_game not available")

LOG_LEVEL = logging.DEBUG  # Keep DEBUG for now
AGENT_TIMEOUT_SECONDS = 180
OUTPUT_DIR = Path("./game_output")
DEFAULT_THEME = "Mysterious Island Survival"
MAP_SIZE_RANGE = (30, 50)
AGENT_MODEL = "gpt-4o"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

root_logger = logging.getLogger()
if root_logger.hasHandlers():
    root_logger.handlers.clear()

logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(OUTPUT_DIR / "agent_run.log", mode='a')
    ]
)
logger = logging.getLogger(__name__)


class Position(BaseModel):
    x: int
    y: int
    model_config = {"json_schema_extra": {"example": {"x": 10, "y": 15}}}

    def to_tuple(self) -> Tuple[int, int]:
        return (self.x, self.y)

    @classmethod
    def from_tuple(cls, pos_tuple: Tuple[int, int]) -> 'Position':
        return cls(x=pos_tuple[0], y=pos_tuple[1])


class Environment(BaseModel):
    width: int
    height: int
    grid: List[List[int]]
    entity_map: Dict[str, 'Entity'] = Field(default_factory=dict, exclude=True) # Map entity ID to entity
    position_map: Dict[tuple[int, int], List['Entity']] = Field(default_factory=dict, exclude=True) # Map (x, y) to list of entities
    model_config = {"json_schema_extra": {"example": {"width": 10, "height": 10, "grid": [[0, 1], [1, 0]]}}}
    
    def is_valid_position(self, position) -> bool:
        """Check if a position is within the bounds of the environment.
        
        Args:
            position: A tuple or list with (x, y) coordinates, or an object with x and y attributes
            
        Returns:
            bool: True if the position is valid, False otherwise
        """
        if hasattr(position, 'x') and hasattr(position, 'y'):
            x, y = position.x, position.y
        elif isinstance(position, (tuple, list)) and len(position) >= 2:
            x, y = position[0], position[1]
        else:
            return False
            
        return 0 <= x < self.width and 0 <= y < self.height
    
    def can_move_to(self, position) -> bool:
        """Check if a position is valid and traversable (value = 1 in grid).
        
        Args:
            position: A tuple or list with (x, y) coordinates, or an object with x and y attributes
            
        Returns:
            bool: True if the position is valid and traversable, False otherwise
        """
        if not self.is_valid_position(position):
            return False
            
        if hasattr(position, 'x') and hasattr(position, 'y'):
            x, y = position.x, position.y
        else:
            x, y = position[0], position[1]
            
        try:
            return self.grid[x][y] == 1  # Assuming 1 means traversable
        except IndexError:
            return False
    
    def get_entities_at(self, position) -> List['Entity']:
        """Get all entities at a specific position.
        
        Args:
            position: A tuple or list with (x, y) coordinates, or an object with x and y attributes
            
        Returns:
            List['Entity'] at the position (empty list if none found)
        """
        pos_tuple = self._normalize_position(position)
        if pos_tuple is None:
            return []
        return list(self.position_map.get(pos_tuple, []))

    def get_object_at(self, position) -> Optional['GameObject']:
        """Get the first GameObject at a position, if any.
        
        Args:
            position: A tuple or list with (x, y) coordinates, or an object with x and y attributes
            
        Returns:
            Optional['GameObject'] at the position or None if not found
        """
        entities = self.get_entities_at(position)
        for entity in entities:
            try:
                from game_object import GameObject # Lazy import for type check if needed
                if isinstance(entity, GameObject):
                    return entity
            except ImportError:
                if 'GameObject' in str(type(entity)): # Less reliable check
                     return entity # type: ignore
        return None

    def _normalize_position(self, position: Any) -> Optional[tuple[int, int]]:
        """Converts various position inputs to a standard (x, y) tuple."""
        if hasattr(position, 'x') and hasattr(position, 'y'):
            return (position.x, position.y)
        elif isinstance(position, (tuple, list)) and len(position) >= 2:
            return (position[0], position[1])
        else:
            logger.warning(f"Invalid position format received: {position!r}")
            return None

    def add_entity(self, entity: 'Entity', position: Optional[Union[Position, tuple[int, int]]] = None) -> bool:
        """Adds an entity to the environment at the specified position."""
        if not hasattr(entity, 'id'):
             logger.error(f"Cannot add entity without id: {entity!r}")
             return False

        pos_to_set = position or getattr(entity, 'position', None)
        pos_tuple = self._normalize_position(pos_to_set)

        if pos_tuple is None:
             logger.warning(f"Cannot add entity '{entity.id}' without a valid position.")
             return False # Or add to entity_map only?

        if not self.is_valid_position(pos_tuple):
             logger.error(f"Cannot add entity '{entity.id}' at invalid position {pos_tuple}.")
             return False

        if hasattr(entity, 'position'):
             if not isinstance(entity.position, Position) or (entity.position.x, entity.position.y) != pos_tuple:
                 try:
                    entity.position = Position(x=pos_tuple[0], y=pos_tuple[1])
                 except Exception as e:
                    logger.error(f"Failed to update entity position object for {entity.id}: {e}")

        self.entity_map[entity.id] = entity
        if pos_tuple not in self.position_map:
             self.position_map[pos_tuple] = []
        if entity not in self.position_map[pos_tuple]:
            self.position_map[pos_tuple].append(entity)
        return True

    def remove_entity(self, entity: 'Entity') -> bool:
        """Removes an entity from the environment."""
        if not hasattr(entity, 'id') or entity.id not in self.entity_map:
            logger.warning(f"Cannot remove entity: Not found or invalid ID. Entity: {entity!r}")
            return False

        entity_id = entity.id
        found_entity = self.entity_map[entity_id]

        pos_tuple = self._normalize_position(getattr(found_entity, 'position', None))
        if pos_tuple and pos_tuple in self.position_map:
            if found_entity in self.position_map[pos_tuple]:
                self.position_map[pos_tuple].remove(found_entity)
                if not self.position_map[pos_tuple]:
                    del self.position_map[pos_tuple]

        del self.entity_map[entity_id]
        return True

    def move_entity(self, entity: 'Entity', new_position: Union[Position, tuple[int, int]]) -> bool:
        """Moves an entity from its current position to a new position."""
        logger.info(f"SYNC CHECK: Environment ID in Environment.move_entity: {id(self)}")
        if not hasattr(entity, 'id') or entity.id not in self.entity_map:
            logger.error(f"Cannot move entity: Not found or invalid ID. Entity: {entity!r}")
            return False

        new_pos_tuple = self._normalize_position(new_position)
        if new_pos_tuple is None or not self.is_valid_position(new_pos_tuple):
            logger.error(f"Cannot move entity {entity.id}: Invalid target position {new_position}.")
            return False


        old_pos_tuple = self._normalize_position(getattr(entity, 'position', None))

        if old_pos_tuple and old_pos_tuple in self.position_map:
             if entity in self.position_map[old_pos_tuple]:
                 self.position_map[old_pos_tuple].remove(entity)
                 if not self.position_map[old_pos_tuple]:
                      del self.position_map[old_pos_tuple]

        if hasattr(entity, 'position'):
             try:
                 entity.position = Position(x=new_pos_tuple[0], y=new_pos_tuple[1])
             except Exception as e:
                 logger.error(f"Failed to update entity position object for {entity.id} during move: {e}")


        if new_pos_tuple not in self.position_map:
             self.position_map[new_pos_tuple] = []
        if entity not in self.position_map[new_pos_tuple]:
            self.position_map[new_pos_tuple].append(entity)

        self.entity_map[entity.id] = entity

        return True


# Re-inserted EntityModel definition
class EntityModel(BaseModel):
    type: str
    possible_states: Optional[List[str]] = None
    possible_actions: Optional[List[str]] = None
    variants: Optional[List[str]] = None
    is_container: Optional[bool] = None
    might_be_movable: Optional[bool] = None
    can_be_at_water: Optional[bool] = None
    might_be_jumpable: Optional[bool] = None
    is_collectable: Optional[bool] = None
    is_wearable: Optional[bool] = None


class GameData(BaseModel):
    theme: str
    environment: Environment
    entities_library: List[EntityModel] = Field(default_factory=list)
    entities: List[Entity] = Field(default_factory=list)
    map_size: int
    border_size: int


class CopywriterContext(BaseModel):
    theme: Optional[str] = None
    environment: Optional[Environment] = None
    entities: Optional[List[Entity]] = None
    entity_library: Optional[List[EntityModel]] = None
    entity_descriptions: Dict[str, str] = Field(default_factory=dict)
    story_components: Dict[str, Any] = Field(default_factory=dict)


class ObjectCounts(BaseModel):
    chest: Optional[int] = Field(None)
    obstacle: Optional[int] = Field(None)
    campfire: Optional[int] = Field(None)
    backpack: Optional[int] = Field(None)
    firewood: Optional[int] = Field(None)
    tent: Optional[int] = Field(None)
    bedroll: Optional[int] = Field(None)
    log_stool: Optional[int] = Field(None)
    campfire_spit: Optional[int] = Field(None)
    campfire_pot: Optional[int] = Field(None)
    pot: Optional[int] = Field(None)
    model_config = {"json_schema_extra": {"example": {"chest": 5, "obstacle": 10, "campfire": 4}}}


class GameWorldResultBase(BaseModel):
    theme: str
    map_size: int
    entity_count: int
    land_percentage: float
    object_types: List[str]
    environment: Environment
    entities: List[Entity]
    error: Optional[str] = None


class GameWorldResult(GameWorldResultBase): pass


class CompleteGameWorldResult(GameWorldResultBase):
    entity_descriptions: Dict[str, str] = Field(default_factory=dict)


class EntityLibraryResult(BaseModel):
    entity_library: List[EntityModel]
    error: Optional[str] = None


class EntityDescription(BaseModel):
    type: str
    variant: Optional[str] = Field(None)
    state: Optional[str] = Field(None)
    description: str
    model_config = {"json_schema_extra": {
        "example": {"type": "chest", "variant": "wooden", "state": "locked", "description": "Sturdy wooden chest."}}}


class EntityBatchDescriptionResult(BaseModel):
    success: bool
    processed_count: int
    descriptions_added: Dict[str, str]
    error: Optional[str] = None


class Interaction(BaseModel):
    entity_type: str
    action: str
    narration: str
    consequences: List[str] = Field(default_factory=list)


class InteractionBatchResult(BaseModel):
    success: bool
    processed_count: int
    interactions_added: List[Interaction]
    error: Optional[str] = None


class StoryIntroResult(BaseModel):
    theme: str
    location: str
    mood: str
    intro_text: str
    error: Optional[str] = None


class QuestResult(BaseModel):
    title: str
    description: str
    objectives: List[str]
    required_entities: List[str] = Field(default_factory=list)
    reward: str
    error: Optional[str] = None


class StoryComponentsResult(BaseModel):
    intro: Optional[StoryIntroResult] = None
    quest: Optional[QuestResult] = None
    error: Optional[str] = None


class CompleteStoryResult(BaseModel):
    person: Person
    theme: str
    environment: Environment
    terrain_description: str
    entity_descriptions: Dict[str, str] = Field(default_factory=dict)
    narrative_components: Dict[str, Any] = Field(default_factory=dict)
    entities: List[Entity]
    complete_narrative: str
    error: Optional[str] = None
    nearby_objects: Dict[str, Entity] = Field(default_factory=dict)
    
    model_config = {
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "theme": "Fantasy Adventure",
                "environment": {"width": 10, "height": 10, "grid": [[0, 1], [1, 0]]},
                "terrain_description": "A mystical forest",
                "entity_descriptions": {"chest": "An ornate wooden chest"},
                "narrative_components": {"quest": {"title": "The Lost Artifact"}},
                "entities": [],
                "complete_narrative": "A tale of adventure...",
                "nearby_objects": {},
                "error": None
            }
        }
    }


def _get_default_object_counts() -> Dict[str, int]:
    return {"chest": 5, "obstacle": 10, "campfire": 4, "backpack": 3, "firewood": 6, "tent": 2, "bedroll": 3,
            "log_stool": 4, "campfire_spit": 2, "campfire_pot": 2, "pot": 5}


def _generate_entity_id(prefix: str) -> str:
    return f"{prefix}_{random.randint(10000, 99999)}_{int(time.time() * 1000)}"


def _safe_entity_factory_call(factory_func: Callable, **kwargs) -> Optional[Dict[str, Any]]:
    try:
        obj = factory_func(**kwargs)
        if isinstance(obj, BaseModel):
            return obj.model_dump(exclude_none=True, by_alias=True)
        elif isinstance(obj, dict):
            return obj
        elif hasattr(obj, 'to_dict'):
            logger.warning(f"Using legacy 'to_dict' for {type(obj)}")
            return obj.to_dict()
        elif hasattr(obj, '__dict__'):
            logger.warning(f"Using vars() for {type(obj)}")
            return vars(obj)
        else:
            logger.warning(f"Cannot convert factory result {type(obj)}")
            return None
    except NotImplementedError as nie:
        logger.error(f"Factory missing impl: {nie}")
        return None
    except Exception as e:
        logger.error(f"Factory call error {getattr(factory_func, '__name__', '?')}: {e}", exc_info=True)
        return None


async def _create_entity_instance(
        type: str,
        factory: Callable,
        positions: List[tuple[int, int]],
        lock: asyncio.Lock,
        **kwargs
) -> Optional[Entity]:
    pos = None
    async with lock:
        if positions:
            pos = positions.pop(random.randrange(len(positions)))
            logger.debug(f"Pos {pos} for {type} ({len(positions)} left).")
        else:
            logger.warning(f"No positions left for {type}.")
            return None
    if pos is None:
        return None  # Should not happen if lock logic is correct, but safeguard

    x, y = pos
    data = _safe_entity_factory_call(factory, **kwargs)
    if data:
        try:
            data["type"] = data.get("type", type)
            data["id"] = data.get("id", _generate_entity_id(type))
            data["position"] = (x, y)
            if "name" not in data:
                data["name"] = f"{data.get('variant', 'Std')} {type.replace('_', ' ').title()}"
            logger.debug(f"Validating {type}: {data}")
            validated = Entity.model_validate(data)
            logger.debug(f"Validated {type} id {validated.id}")
            return validated
        except ValidationError as e:
            logger.error(f"Validation fail {type} @({x},{y}): {e}", exc_info=False)
            logger.error(f"--> Data: {json.dumps(data, default=str)}")
            return None
        except Exception as e:
            logger.error(f"Finalizing error {type}: {e}", exc_info=True)
            return None
    else:  # data is None
        logger.warning(f"Factory call for {type} returned None.")
        return None


def generate_terrain_description(env: Optional[Environment]) -> str:
    if not env or not env.grid:
        return "Mysterious landscape."
    total = getattr(env, 'width', 0) * getattr(env, 'height', 0)
    land_c = sum(sum(r) for r in env.grid)
    if total == 0:
        return "Empty void."
    perc = (land_c / total) * 100
    if perc > 95:
        t = "Vast continent"
    elif perc > 75:
        t = "Large landmass, water features"
    elif perc > 50:
        t = "Balanced land/water"
    elif perc > 25:
        t = "Archipelago"
    elif perc > 5:
        t = "Ocean, small islands"
    else:
        t = "Aquatic world, specks of land"
    return t + f" (~{perc:.0f}% land)"



@function_tool()
async def generate_complete_game_world(
        ctx: RunContextWrapper[CopywriterContext],
        theme: str,
        map_size: int = Field(..., ge=MAP_SIZE_RANGE[0], le=MAP_SIZE_RANGE[1]),
        border_size: int = Field(DEFAULT_BORDER_SIZE, ge=1, le=15),
        object_counts: Optional[ObjectCounts] = None
) -> Union[CompleteGameWorldResult, str]:  # Return str on success
    """
    Generates a complete game world including terrain (island map), entities based on counts,
    and basic placeholder descriptions. This is the preferred tool for initial world creation.
    Map size should typically be between {MAP_SIZE_RANGE[0]} and {MAP_SIZE_RANGE[1]}.
    """
    if not FACTORY_GAME_AVAILABLE:
        logger.error("Tool fail: 'factory_game' unavailable.")
        return CompleteGameWorldResult(
            theme=theme, map_size=map_size, entity_count=0, land_percentage=0,
            object_types=[], environment=Environment(width=map_size, height=map_size, grid=[]),
            entities=[], entity_descriptions={}, error="factory_game missing."
        )

    if not ctx.context:
        ctx.context = CopywriterContext()
    context = ctx.context
    context.theme = theme
    actual_map_size = map_size
    actual_border_size = border_size
    logger.info(f"Starting generation: Map={actual_map_size}x{actual_map_size}, Theme='{theme}'")

    try:
        logger.debug("Generating map...")
        symbol_grid = generate_island_map(size=actual_map_size, border_size=actual_border_size)
        binary_grid = [[1 if cell == LAND_SYMBOL else 0 for cell in row] for row in symbol_grid]
        logger.debug(f"Map {len(binary_grid)}x{len(binary_grid[0]) if binary_grid else 0}. Validating Env.")
        environment = Environment(width=actual_map_size, height=actual_map_size, grid=binary_grid)
        context.environment = environment
        logger.debug("Environment stored.")

        counts_dict = _get_default_object_counts()
        if object_counts:
            counts_dict.update(object_counts.model_dump(exclude_none=True))
            logger.info(f"Using counts (merged): {counts_dict}")
        else:
            logger.info(f"Using default counts: {counts_dict}")

        land_pos = [(x, y) for y, r in enumerate(binary_grid) for x, c in enumerate(r) if c == 1]
        water_pos = [(x, y) for y, r in enumerate(binary_grid) for x, c in enumerate(r) if c == 0]
        logger.debug(f"Positions: {len(land_pos)} land, {len(water_pos)} water.")

        lock = asyncio.Lock()
        tasks = []
        total_scheduled = 0

        def _obstacle_factory():
            obstacle_type = random.choice(["rock", "plant", "log", "stump", "hole", "tree"])
            return create_land_obstacle(obstacle_type)  # Pass the chosen type

        factories = {  # Ensure factories exist & return valid data/models
            "chest": (lambda: ChestFactory.create_chest(
                chest_type=random.choice(["basic_wooden", "forestwood", "bronze_banded"])), False),
            "obstacle": (_obstacle_factory, True),
            "backpack": (BackpackFactory.create_backpack, False),
            "firewood": (FirewoodFactory.create_firewood, False),
            "tent": (TentFactory.create_tent, False),
            "bedroll": (BedrollFactory.create_bedroll, False),
            "log_stool": (LogStoolFactory.create_stool, False),
            "campfire_spit": (CampfireSpitFactory.create_campfire_spit, False),
            "campfire_pot": (lambda: CampfirePotFactory.create_pot("tripod"), False),
            "pot": (lambda size=random.choice(["small", "medium", "big"]): PotFactory.create_pot(size), True),
            "campfire": (CampfireFactory.create_campfire, False),
        }
        logger.debug("Setting up entity tasks...")
        for type, count in counts_dict.items():
            if count <= 0:
                continue
            factory_tuple = factories.get(type)
            if not factory_tuple:
                logger.warning(f"Skip {type}: No factory.")
                continue

            factory, water_ok = factory_tuple
            available_positions = list(land_pos)  # Copy land positions
            if water_ok:
                available_positions.extend(list(water_pos))  # Add copy of water positions

            if not available_positions:
                logger.warning(f"Skip {type}: No valid positions available.")
                continue

            random.shuffle(available_positions)

            actual_cnt = min(count, len(available_positions))
            if actual_cnt < count:
                logger.warning(
                    f"Position shortage for {type}: Need={count}, Have={len(available_positions)}. Making {actual_cnt}.")

            logger.debug(f"Creating {actual_cnt} task(s) for {type}...")
            positions_for_tasks = available_positions[:actual_cnt]
            for _ in range(actual_cnt):
                tasks.append(_create_entity_instance(type, factory, positions_for_tasks, lock))
                total_scheduled += 1
        logger.info(f"Total tasks scheduled: {total_scheduled}")

        valid_entities: List[Entity] = []
        exceptions = []
        if tasks:
            logger.debug(f"Gathering results from {len(tasks)} tasks...")
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                logger.debug("Gather complete.")
                for res in results:
                    if isinstance(res, Entity):
                        valid_entities.append(res)
                    elif isinstance(res, Exception):
                        exceptions.append(res)
            except Exception as e:
                logger.error(f"Gather error: {e}", exc_info=True)
        else:
            logger.warning("No tasks scheduled.")

        failed_count = total_scheduled - len(valid_entities)
        logger.info(f"Entity creation: {len(valid_entities)} valid, {failed_count} failed/None.")
        for i, exc in enumerate(exceptions):
            logger.error(f"  Task exception {i + 1}: {exc}",
                         exc_info=False)  # Keep exc_info False for cleaner logs unless debugging
        if not valid_entities and total_scheduled > 0:
            logger.error("All entity tasks failed or returned None.")

        context.entities = valid_entities
        if context.environment:
            logger.debug(f"Populating environment with {len(valid_entities)} valid entities...")
            added_to_env = 0
            for entity in valid_entities:
                if context.environment.add_entity(entity): # Uses entity's position
                     added_to_env += 1
                else:
                     logger.warning(f"Failed to add entity {entity.id} to environment map.")
            logger.debug(f"Successfully added {added_to_env} entities to environment state.")
        else:
             logger.error("Cannot populate environment: Environment object is missing in context.")

        logger.debug("Generating placeholder descriptions...")
        entity_descriptions = {}
        for e in valid_entities:
            key = f"{e.type}_{e.variant or 'default'}_{e.state or 'default'}"
            if key not in entity_descriptions:
                entity_descriptions[key] = f"A {e.name or e.type}{f' ({e.state})' if e.state else ''}."
        context.entity_descriptions = entity_descriptions
        logger.debug(f"Generated/updated {len(entity_descriptions)} placeholders.")

        land_c = sum(sum(r) for r in binary_grid)
        total_c = actual_map_size * actual_map_size
        land_p = (land_c / total_c) * 100 if total_c > 0 else 0
        obj_types = sorted(list(set(e.type for e in valid_entities)))
        logger.info(f"Finalizing world gen: Entities={len(valid_entities)}, Types={obj_types}, Land={land_p:.1f}%")

        return f"Success: Generated world. Map={actual_map_size}x{actual_map_size}, Land={land_p:.1f}%, Entities={len(valid_entities)} ({failed_count} failed)."

    except NotImplementedError as nie:  # Specific known failure
        logger.error(f"Tool fail: Missing implementation: {nie}", exc_info=False)
        return CompleteGameWorldResult(
            theme=theme, map_size=map_size, entity_count=0, land_percentage=0, object_types=[],
            environment=Environment(width=map_size, height=map_size, grid=[]), entities=[],
            entity_descriptions={}, error=f"Missing implementation: {nie}"
        )
    except Exception as e:  # Unexpected failure
        logger.error(f"CRITICAL ERROR in generate_complete_game_world: {e}", exc_info=True)
        return CompleteGameWorldResult(
            theme=theme, map_size=map_size, entity_count=0, land_percentage=0, object_types=[],
            environment=Environment(width=map_size, height=map_size, grid=[]), entities=[],
            entity_descriptions={}, error=f"Tool error: {type(e).__name__} - {e}"
        )


@function_tool()
async def get_entity_library(ctx: RunContextWrapper[CopywriterContext]) -> EntityLibraryResult:
    """Returns a predefined library of known entity types and their potential properties."""
    definitions = [EntityModel(type="chest", possible_states=["locked", "unlocked", "open", "closed", "empty", "full"],
                               possible_actions=["open", "close", "lock", "unlock", "examine", "empty"],
                               variants=["wooden", "iron", "ornate"], is_container=True, might_be_movable=True),
                   EntityModel(type="rock", possible_states=["whole", "cracked", "broken"],
                               possible_actions=["examine", "throw", "break", "gather"],
                               variants=["small", "medium", "large", "mossy"], can_be_at_water=True,
                               might_be_movable=True,
                               might_be_jumpable=True, is_collectable=True),
                   EntityModel(type="campfire",
                               possible_states=["unlit", "smoldering", "burning", "dying", "extinguished"],
                               possible_actions=["light", "extinguish", "add_fuel", "cook", "warm_up"],
                               variants=["simple_pit", "stone_ring"], might_be_jumpable=True),
                   EntityModel(type="tent", possible_states=["packed", "setup", "damaged"],
                               possible_actions=["setup", "pack", "enter", "exit", "repair", "sleep"],
                               variants=["small_canvas", "large_leather"], is_container=True),
                   EntityModel(type="pot", possible_states=["empty", "full_water", "full_soup", "boiling", "dirty"],
                               possible_actions=["fill", "empty", "cook", "drink", "clean", "examine"],
                               variants=["clay", "iron", "copper"], can_be_at_water=True, might_be_movable=True,
                               is_container=True),
                   EntityModel(type="backpack", possible_states=["empty", "partially_full", "full"],
                               possible_actions=["open", "close", "wear", "remove", "drop"],
                               variants=["small_satchel", "medium_rucksack", "large_framepack"], is_container=True,
                               is_collectable=True, is_wearable=True),
                   EntityModel(type="bedroll", possible_states=["rolled", "unrolled"],
                               possible_actions=["unroll", "roll", "sleep", "pickup"],
                               variants=["straw", "wool", "fur"], might_be_movable=True, is_collectable=True),
                   EntityModel(type="firewood", possible_states=["dry", "wet", "charred"],
                               possible_actions=["gather", "add_to_fire", "drop"],
                               variants=["kindling", "branch", "log"], might_be_movable=True, is_collectable=True),
                   EntityModel(type="log_stool", possible_states=["default", "occupied"],
                               possible_actions=["sit", "stand_up", "move"], variants=["short", "tall"],
                               might_be_movable=True),
                   EntityModel(type="obstacle", possible_states=["default", "cleared", "broken"],
                               possible_actions=["examine", "climb", "jump_over", "destroy", "move"],
                               variants=["boulder", "thorny_bush", "fallen_log", "deep_mud", "rubble"],
                               can_be_at_water=True, might_be_jumpable=True),
                   EntityModel(type="campfire_spit", possible_states=["empty", "cooking"],
                               possible_actions=["attach_food", "remove_food", "examine"],
                               variants=["wooden", "metal"], might_be_movable=True),
                   EntityModel(type="campfire_pot", possible_states=["empty", "full_water", "cooking"],
                               possible_actions=["fill", "empty", "cook", "serve"], variants=["tripod", "hanging"],
                               might_be_movable=True, is_container=True)
                   ]
    if not ctx.context:
        ctx.context = CopywriterContext()
    ctx.context.entity_library = definitions
    return EntityLibraryResult(entity_library=definitions)


@function_tool()
async def describe_entities_batch(
        ctx: RunContextWrapper[CopywriterContext], descriptions: List[EntityDescription]
) -> Union[EntityBatchDescriptionResult, str]:  # Return str on success
    """Adds/updates descriptions for multiple entity type/variant/state combinations."""
    if not ctx.context:
        ctx.context = CopywriterContext()
    if not hasattr(ctx.context, 'entity_descriptions') or ctx.context.entity_descriptions is None:
        ctx.context.entity_descriptions = {}

    added: Dict[str, str] = {}
    processed = 0
    try:
        if not isinstance(descriptions, list):
            raise TypeError("Input must be a list of EntityDescription objects.")

        for item in descriptions:
            desc_data = item
            if not isinstance(item, EntityDescription):
                try:
                    desc_data = EntityDescription.model_validate(item)
                except (ValidationError, TypeError) as e:
                    logger.warning(f"Skipping invalid description item: {e} - {item!r}")
                    continue

            key = f"{desc_data.type}_{desc_data.variant or 'default'}_{desc_data.state or 'default'}"
            ctx.context.entity_descriptions[key] = desc_data.description
            added[key] = desc_data.description
            processed += 1

        logger.info(f"Added/updated {processed} descriptions.")
        return f"Success: Processed {processed} entity descriptions."
    except Exception as e:
        logger.error(f"Error in describe_entities_batch: {e}", exc_info=True)
        return EntityBatchDescriptionResult(
            success=False, processed_count=processed, descriptions_added=added,
            error=f"{type(e).__name__}: {e}"
        )


@function_tool()
async def craft_entity_interactions_batch(
        ctx: RunContextWrapper[CopywriterContext], interactions: List[Interaction]
) -> Union[InteractionBatchResult, str]:  # Return str on success
    """Adds multiple entity interaction narratives to the story components."""
    if not ctx.context:
        ctx.context = CopywriterContext()
    if 'interactions' not in ctx.context.story_components or not isinstance(
            ctx.context.story_components.get("interactions"), list):
        ctx.context.story_components["interactions"] = []

    added: List[Interaction] = []
    processed = 0
    try:
        if not isinstance(interactions, list):
            raise TypeError("Input must be a list of Interaction objects.")

        for item in interactions:
            interact_data = item
            if not isinstance(item, Interaction):
                try:
                    interact_data = Interaction.model_validate(item)
                except (ValidationError, TypeError) as e:
                    logger.warning(f"Skipping invalid interaction item: {e} - {item!r}")
                    continue

            ctx.context.story_components["interactions"].append(interact_data.model_dump(mode='json'))
            added.append(interact_data)  # Keep original model for the result
            processed += 1

        logger.info(f"Added {processed} interactions.")
        return f"Success: Added {processed} entity interactions."
    except Exception as e:
        logger.error(f"Error in craft_entity_interactions_batch: {e}", exc_info=True)
        return InteractionBatchResult(
            success=False, processed_count=processed, interactions_added=added,
            error=f"{type(e).__name__}: {e}"
        )


@function_tool()
async def generate_story_components(
        ctx: RunContextWrapper[CopywriterContext], theme: str, location_description: str, mood: str,
        quest_title: str, quest_description: str, quest_objectives: List[str],
        quest_reward: str, quest_required_entities: Optional[List[str]] = None
) -> Union[StoryComponentsResult, str]:  # Return str on success
    """Generates and adds the story introduction and main quest."""
    if not ctx.context:
        ctx.context = CopywriterContext()
    context = ctx.context
    context.theme = theme  # Update theme in context if provided
    try:
        intro_text = f"You find yourself in '{location_description}'. The air holds a sense of {mood}. Theme: '{theme}'..."
        intro = StoryIntroResult(theme=theme, location=location_description, mood=mood, intro_text=intro_text)
        context.story_components["intro"] = intro.model_dump(mode='json')  # Store dict

        quest = QuestResult(
            title=quest_title,
            description=quest_description,
            objectives=quest_objectives,
            required_entities=quest_required_entities or [],  # Ensure list even if None
            reward=quest_reward
        )
        context.story_components["quest"] = quest.model_dump(mode='json')  # Store dict

        logger.info(f"Generated intro and quest '{quest_title}'.")
        return f"Success: Generated story intro and quest '{quest_title}'."
    except Exception as e:
        logger.error(f"Error generating story components: {e}", exc_info=True)
        intro_res = context.story_components.get("intro")
        quest_res = context.story_components.get("quest")
        try:
            intro_res = StoryIntroResult.model_validate(intro_res) if isinstance(intro_res, dict) else None
        except:
            intro_res = None
        try:
            quest_res = QuestResult.model_validate(quest_res) if isinstance(quest_res, dict) else None
        except:
            quest_res = None

        return StoryComponentsResult(
            intro=intro_res,
            quest=quest_res,
            error=f"{type(e).__name__}: {e}"
        )


@function_tool()
async def complete_story(ctx: RunContextWrapper[CopywriterContext]) -> CompleteStoryResult:
    """Compiles all generated components into a final, structured story result."""
    if not ctx.context:
        logger.error("Cannot complete story: Context is missing.")
        return CompleteStoryResult(
            theme="Unknown",
            environment=Environment(width=0, height=0, grid=[]),
            terrain_description="Error: Context missing",
            entity_descriptions={},
            narrative_components={},
            entities=[],
            complete_narrative="",
            error="Context missing during final compilation.",
            nearby_objects={}
        )

    context = ctx.context
    logger.info("Compiling final story...")
    try:
        theme = getattr(context, 'theme', DEFAULT_THEME)
        env = getattr(context, 'environment', None)
        ents = getattr(context, 'entities', []) or []
        descs = getattr(context, 'entity_descriptions', {}) or {}
        comps = getattr(context, 'story_components', {}) or {}

        if not isinstance(env, Environment) or not env.grid or env.width <= 0 or env.height <= 0:
            logger.error("Environment missing or invalid in context.")
            return CompleteStoryResult(
                theme=theme,
                environment=env or Environment(width=0, height=0, grid=[]),  # Return invalid env if present, else empty
                terrain_description="Error: Environment missing or invalid",
                entity_descriptions=descs,
                narrative_components=comps,
                entities=ents,
                complete_narrative="",
                error="Environment missing or invalid during final compilation.",
                nearby_objects={}
            )

        terrain = generate_terrain_description(env)

        intro_data = comps.get("intro", {})
        intro_text = intro_data.get("intro_text", "The story begins...") if isinstance(intro_data,
                                                                                       dict) else "Introduction missing."

        quest_data = comps.get("quest", {})
        interaction_data = comps.get("interactions", [])

        parts = [intro_text, f"\n**World:**\n{terrain}"]

        if isinstance(quest_data, dict) and quest_data:
            parts.append(f"\n**Quest: {quest_data.get('title', 'Untitled Quest')}**")
            parts.append(quest_data.get('description', 'No description provided.'))
            objectives = quest_data.get('objectives', [])
            if objectives:
                parts.extend([f"- {o}" for o in objectives])
            else:
                parts.append("- No objectives defined.")
                parts.append(f"Reward: {quest_data.get('reward', 'An unknown reward.')}")

        if descs:
            parts.append("\n**Notable Features:**")
            shown_count = 0
            for key, desc_text in descs.items():
                if shown_count < 5:
                    name_parts = key.split('_')
                    name = name_parts[0].replace('_', ' ').title()
                    if len(name_parts) > 1 and name_parts[1] != 'default': name += f" ({name_parts[1]})"
                    if len(name_parts) > 2 and name_parts[2] != 'default': name += f" [{name_parts[2]}]"
                    parts.append(f"- {name}: {desc_text}")
                    shown_count += 1
                else:
                    parts.append(f"- ...and {len(descs) - shown_count} more descriptions.")
                    break
        else:
            parts.append("\n**Notable Features:**\n- None described.")

        if isinstance(interaction_data, list) and interaction_data:
            parts.append("\n**Possible Interactions:**")
            shown_count = 0
            for interaction in interaction_data:
                if isinstance(interaction, dict):  # Interactions stored as dicts
                    if shown_count < 5:
                        action = interaction.get('action', 'interact').title()
                        entity_type = interaction.get('entity_type', 'something')
                        narration = interaction.get('narration', '...')
                        parts.append(f"- {action} with {entity_type}: {narration}")
                        shown_count += 1
                    else:
                        parts.append(f"- ...and {len(interaction_data) - shown_count} more interactions.")
                        break
                else:
                    logger.warning(f"Skipping non-dictionary interaction item: {interaction!r}")
        else:
            parts.append("\n**Possible Interactions:**\n- None defined.")

        complete_narrative = "\n".join(filter(None, parts))

        result = CompleteStoryResult(
            theme=theme,
            environment=env,
            terrain_description=terrain,
            entity_descriptions=descs,
            narrative_components=comps,
            entities=ents,
            complete_narrative=complete_narrative,
            nearby_objects={}
        )

        try:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            sanitized_theme = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in theme)
            filename = f"{timestamp}-{sanitized_theme}.json"
            output_path = OUTPUT_DIR / filename
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result.model_dump(mode='json', exclude_none=True), f, indent=2, ensure_ascii=False)
            logger.info(f"✅ Intermediate story result saved by complete_story: {output_path}")
        except Exception as save_err:
            logger.error(f"❌ Failed to save intermediate story result in complete_story: {save_err}", exc_info=True)

        logger.info("Successfully compiled final story.")
        return result

    except Exception as e:
        logger.error(f"Error compiling final story: {e}", exc_info=True)
        env_fallback = getattr(context, 'environment', Environment(width=0, height=0, grid=[]))
        theme_fallback = getattr(context, 'theme', "Unknown")
        descs_fallback = getattr(context, 'entity_descriptions', {}) or {}
        comps_fallback = getattr(context, 'story_components', {}) or {}
        ents_fallback = getattr(context, 'entities', []) or []

        return CompleteStoryResult(
            theme=theme_fallback,
            environment=env_fallback,
            terrain_description="Error during compilation",
            entity_descriptions=descs_fallback,
            narrative_components=comps_fallback,
            entities=ents_fallback,
            complete_narrative="",
            error=f"Compilation failed: {type(e).__name__} - {e}",
            nearby_objects={}
        )


class GameCopywriterAgent:
    def __init__(self, openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")):
        logger.info("Initializing GameCopywriterAgent...")
        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key is required (pass as argument or set OPENAI_API_KEY environment variable).")
        try:
            self.sync_openai_client = OpenAI(api_key=self.api_key)
            logger.info("OpenAI client initialized.")
        except Exception as e:
            logger.critical(f"Failed to initialize OpenAI client: {e}", exc_info=True)
            raise  # Cannot proceed without a client
        self.agent = self._setup_agent()
        logger.info(f"Agent '{self.agent.name}' setup complete (model: {getattr(self.agent, 'model', 'N/A')}).")

    def _setup_agent(self) -> Agent:
        system_prompt = f"""
1. World Gen: Call `generate_complete_game_world` ONCE (map size {MAP_SIZE_RANGE[0]}-{MAP_SIZE_RANGE[1]}). If this tool returns an error object, STOP immediately and return that error. If it returns a success string, continue.
2. Descriptions: Call `describe_entities_batch` ONCE using world gen results stored in context. If this tool returns an error object, STOP and return it. If it returns a success string, continue.
3. Story Core: Call `generate_story_components` ONCE (intro + quest). If this tool returns an error object, STOP and return it. If it returns a success string, continue.
4. Interactions: Call `craft_entity_interactions_batch` ONCE for key interactions. If this tool returns an error object, STOP and return it. If it returns a success string, continue.
5. Final Compile: Call `complete_story` ONCE as the very last step. This tool *always* returns a `CompleteStoryResult` object (either success or containing an error field). Return this object directly.
"""
        tools = [
            generate_complete_game_world,
            get_entity_library,  # Keep for potential context/reference, though not in main workflow
            describe_entities_batch,
            craft_entity_interactions_batch,
            generate_story_components,
            complete_story
        ]
        if not FACTORY_GAME_AVAILABLE:
            logger.warning("Excluding 'generate_complete_game_world' tool because 'factory_game' is missing.")
            tools = [t for t in tools if t.__name__ != 'generate_complete_game_world']
            if not tools:
                raise RuntimeError("No tools available for agent after excluding world generation.")
            system_prompt = f"""
1. Descriptions: Call `describe_entities_batch` ONCE based on a hypothetical world concept.
2. Story Core: Call `generate_story_components` ONCE (intro + quest).
3. Interactions: Call `craft_entity_interactions_batch` ONCE for key interactions.
4. Final Compile: Call `complete_story` ONCE last. This returns the final object.
"""

        return Agent[CopywriterContext](
            name="Narrativa_Game_Writer",
            instructions=system_prompt,
            tools=tools,
            model=AGENT_MODEL
        )

    async def process_game_data(self, theme: str = DEFAULT_THEME) -> str:
        """Runs the agent workflow to generate game narrative data."""
        if not self.agent.tools:
            logger.error("Agent has no tools configured.")
            return {"error": "Agent initialization failed: No tools available."}

        logger.info(f"Starting agent processing for theme: '{theme}'")
        initial_context = CopywriterContext(theme=theme)

        runner = Runner()
        runner.client = self.sync_openai_client  # Use the initialized synchronous client
        runner.agent = self.agent
        runner.context = initial_context

        input_msg = f"Generate the complete game narrative skeleton for the theme: '{theme}'. Adhere strictly to the defined workflow."
        if not FACTORY_GAME_AVAILABLE:
            input_msg += " Note: World generation is unavailable; proceed with the alternative workflow."

        try:
            logger.info(
                f"Running agent '{self.agent.name}' with model '{self.agent.model}'. Timeout: {AGENT_TIMEOUT_SECONDS}s")
            run_result = await asyncio.wait_for(
                runner.run(starting_agent=self.agent, input=input_msg),
                timeout=AGENT_TIMEOUT_SECONDS
            )
            logger.info("Agent run finished.")

            final_output = getattr(run_result, 'final_output', None)
            return final_output
        except Exception as e:
            return "error, please restart it"

    async def _reconstruct_result_from_context(self, context: Optional[CopywriterContext]) -> Optional[
        CompleteStoryResult]:
        """Attempts to build a CompleteStoryResult by calling the `complete_story` tool's underlying function with the final context."""
        if not context:
            logger.error("Cannot reconstruct result: Context is None.")
            return None

        logger.info("Reconstructing final result object from the last known context state...")
        try:
            class DummyContextWrapper:
                def __init__(self, context_data: CopywriterContext):
                    self.context = context_data

            dummy_wrapper = DummyContextWrapper(context)

            original_complete_story_func = complete_story
            while hasattr(original_complete_story_func, '__wrapped__'):
                original_complete_story_func = getattr(original_complete_story_func, '__wrapped__')

            if not inspect.iscoroutinefunction(original_complete_story_func):
                logger.error("Reconstruction failed: Could not find the original async function for complete_story.")
                return None

            reconstructed_result: CompleteStoryResult = await original_complete_story_func(dummy_wrapper)

            if reconstructed_result and isinstance(reconstructed_result, CompleteStoryResult):
                log_msg = "Reconstruction successful"
                if reconstructed_result.error:
                    log_msg += f" (result contains error: {reconstructed_result.error})"
                else:
                    log_msg += "."
                logger.info(log_msg)
                return reconstructed_result
            else:
                logger.error(f"Reconstruction call returned an unexpected type: {type(reconstructed_result)}")
                return None

        except Exception as e:
            logger.error(f"Error during result reconstruction: {e}", exc_info=True)
            return None

    def save_results(self, final_result: Union[CompleteStoryResult, Dict, str], context: Optional[CopywriterContext],
                     run_info: Optional[Any]):
        """Saves the final generated result, the final context state, and basic run info."""
        ts = time.strftime("%Y%m%d_%H%M%S")
        try:
            result_content: Optional[Union[Dict, str]] = None
            result_filename = f"game_story_{ts}.json"  # Default

            if isinstance(final_result, CompleteStoryResult):
                try:
                    result_content = final_result.model_dump(mode='json', exclude_none=True)
                except Exception as dump_err:
                    logger.error(f"Failed to dump CompleteStoryResult model: {dump_err}")
                    result_content = {"error": "Failed to serialize CompleteStoryResult", "repr": repr(final_result)}
            elif isinstance(final_result, dict):
                result_content = final_result
            elif isinstance(final_result, str):
                result_filename = f"game_output_string_{ts}.txt"
                result_content = final_result
                logger.warning(f"Final result was a string; saving as text: {result_filename}")
            else:
                logger.error(f"Cannot save final result: Unsupported type {type(final_result)}")
                result_content = {"error": f"Unsupported result type: {type(final_result)}", "repr": repr(final_result)}

            output_path = OUTPUT_DIR / result_filename
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    if isinstance(result_content, dict):
                        json.dump(result_content, f, indent=2, ensure_ascii=False)
                    elif isinstance(result_content, str):  # Handles the string case
                        f.write(result_content)
                logger.info(f"✅ Final result saved: {output_path}")
            except TypeError as json_err:
                logger.error(f"JSON serialization error saving result: {json_err}")
                repr_path = OUTPUT_DIR / f"{output_path.stem}.repr.txt"
                try:
                    with open(repr_path, "w", encoding="utf-8") as f_repr:
                        f_repr.write(repr(result_content))
                    logger.warning(f"Saved result representation due to JSON error: {repr_path}")
                except Exception as repr_err:
                    logger.error(f"Failed to save result representation: {repr_err}")
            except Exception as file_err:
                logger.error(f"Failed to write result file {output_path}: {file_err}")

            if context and isinstance(context, CopywriterContext):
                context_path = OUTPUT_DIR / f"final_context_{ts}.json"
                try:
                    with open(context_path, "w", encoding="utf-8") as f_ctx:
                        json.dump(context.model_dump(mode='json', exclude_none=True), f_ctx, indent=2,
                                  ensure_ascii=False)
                    logger.info(f"💾 Final context saved: {context_path}")
                except Exception as e:
                    logger.error(f"Failed to save final context: {e}", exc_info=True)
            elif context:
                logger.warning(f"Final context was not a CopywriterContext object (type: {type(context)}), not saving.")
            else:
                logger.warning("Final context was None, not saving.")

            if run_info:
                run_info_path = OUTPUT_DIR / f"run_info_{ts}.json"
                try:
                    info_dict = {
                        "run_object_type": type(run_info).__name__,
                        "final_output_type": type(getattr(run_info, 'final_output', None)).__name__,
                    }
                    with open(run_info_path, "w", encoding="utf-8") as f_info:
                        json.dump(info_dict, f_info, indent=2, default=str)  # Use default=str for safety
                    logger.info(f"📜 Basic run info saved: {run_info_path}")
                except Exception as e:
                    logger.error(f"Failed to save run info: {e}")

        except Exception as e:
            logger.error(f"❌ Unexpected error during saving results: {e}", exc_info=True)

    def save_story_result(self, result: CompleteStoryResult) -> str:
        """Save the story result to a JSON file with timestamped filename."""
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"{timestamp}-{result.theme}.json"
        output_path = OUTPUT_DIR / filename
        
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result.model_dump(mode='json', exclude_none=True), f, indent=2, ensure_ascii=False)
            logger.info(f"✅ Story result saved: {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Failed to save story result: {e}")
            raise


async def main():
    print("--- Game Copywriter Agent ---")
    
    agent = GameCopywriterAgent()
    
    result = await agent.process_game_data()
    
    if isinstance(result, CompleteStoryResult):
        print("\n--- Generation Summary ---")
        print(f"Theme: {result.theme}")
        
        story_path = agent.save_story_result(result)
        print(f"\nℹ️ Full story saved in: {story_path}")
        
        env_width = getattr(result.environment, 'width', 0)
        env_height = getattr(result.environment, 'height', 0)
        land_perc = getattr(result, 'land_percentage', 0.0)  # Use attribute from result if available
        if env_width > 0 and env_height > 0:
            print(f"Map: {env_width}x{env_height} ({land_perc:.1f}% land)")
        else:
            map_status = "(Invalid Data)" if FACTORY_GAME_AVAILABLE else "(Not Generated)"
            print(f"Map: {map_status}")

        print(f"Entities Generated: {len(result.entities)}")
        print(f"Entity Descriptions: {len(result.entity_descriptions)}")

        narr_comps = result.narrative_components or {}
        interactions_list = narr_comps.get("interactions", [])
        print(f"Interaction Snippets: {len(interactions_list) if isinstance(interactions_list, list) else 0}")

        quest_info = narr_comps.get("quest", {})
        quest_title = quest_info.get("title", "N/A") if isinstance(quest_info, dict) else "N/A"
        print(f"Quest Title: {quest_title}")

        if result.error:
            print(f"\n⚠️ WARNING: The final result contains an error message: {result.error}")
        else:
            print("\n📜 Narrative Preview:")
            print("-" * 20)
            narrative = result.complete_narrative or "(Narrative is empty)"
            preview_len = 600
            print(narrative[:preview_len] + ("..." if len(narrative) > preview_len else ""))
            print("-" * 20)

        print(f"\nℹ️ Full details saved in the '{OUTPUT_DIR}' directory.")
        print(f"   Check 'game_story_*.json' and 'agent_run.log'.")

    elif isinstance(result, dict) and "error" in result:
        print(f"\n❌ ERROR during processing: {result['error']}")
        print(f"ℹ️ Check logs in '{OUTPUT_DIR}/agent_run.log' for more details.")
    else:
        print(f"\n⚠️ Unexpected result type received: {type(result)}")
        print(f"   Result: {repr(result)[:500]}")
        print(f"ℹ️ Check logs and files in '{OUTPUT_DIR}' for details.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Execution cancelled by user.")
    except Exception as startup_err:
        print(f"\n❌ FATAL STARTUP ERROR: {startup_err}")
        traceback.print_exc()
