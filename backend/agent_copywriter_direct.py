import json
import logging
import os
import random
import numpy as np
import time
import traceback
from typing import Dict, Any, List, Optional, Tuple
import asyncio
import inspect
from functools import wraps

from agents import Agent, Runner, function_tool, RunContextWrapper
from openai import OpenAI
from pydantic import BaseModel, Field

# Import factory_game components for direct usage
from factory_game import (
    GameFactory, MAP_SIZE, BORDER_SIZE, WATER_SYMBOL, LAND_SYMBOL,
    generate_island_map, BackpackFactory, BedrollFactory, CampfireFactory, 
    CampfirePotFactory, CampfireSpitFactory, ChestFactory, FirewoodFactory, 
    LogStoolFactory, PotFactory, TentFactory, create_chest, create_land_obstacle
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a decorator for logging tool execution
def log_tool_execution(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Get function name
        func_name = func.__name__
        
        # Extract and format parameters for logging
        # Skip the first parameter (context) to avoid logging entire context object
        sig = inspect.signature(func)
        param_names = list(sig.parameters.keys())[1:]  # Skip first param (ctx)
        
        # Get actual parameter values (excluding ctx)
        if len(args) > 1:
            param_values = args[1:]
        else:
            param_values = []
            
        # Add kwargs
        param_dict = dict(zip(param_names, param_values))
        param_dict.update(kwargs)
        
        # Format parameters for logging (limit size for readability)
        formatted_params = {}
        for k, v in param_dict.items():
            if isinstance(v, str) and len(v) > 100:
                formatted_params[k] = f"{v[:100]}... (truncated)"
            elif isinstance(v, list) and len(v) > 5:
                formatted_params[k] = f"{v[:5]}... ({len(v)} items)"
            else:
                formatted_params[k] = v
        
        # Log function call
        logger.info(f"🔧 EXECUTING TOOL: {func_name}")
        logger.info(f"📥 PARAMETERS: {formatted_params}")
        
        # Execute the function
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Format result for logging
            if isinstance(result, dict):
                if len(result) > 5:
                    result_preview = {k: result[k] for k in list(result.keys())[:5]}
                    result_preview["..."] = f"({len(result)} total keys)"
                else:
                    result_preview = result
            elif isinstance(result, list):
                if len(result) > 5:
                    result_preview = f"{result[:5]}... ({len(result)} items)"
                else:
                    result_preview = result
            elif isinstance(result, str) and len(result) > 200:
                result_preview = f"{result[:200]}... (truncated)"
            else:
                result_preview = result
                
            logger.info(f"📤 RESULT: {result_preview}")
            logger.info(f"⏱️ EXECUTION TIME: {execution_time:.2f} seconds")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ ERROR in {func_name}: {str(e)}")
            logger.error(traceback.format_exc())
            logger.info(f"⏱️ EXECUTION TIME: {execution_time:.2f} seconds")
            raise
            
    return wrapper

# Models for data structures
class Position(BaseModel):
    x: int
    y: int

class Environment(BaseModel):
    width: int
    height: int
    grid: List[List[int]]

class EntityModel(BaseModel):
    type: str
    possible_states: List[str] = Field(default_factory=list)
    possible_actions: List[str] = Field(default_factory=list)
    variants: List[str] = Field(default_factory=list)
    can_be_at_water: bool = False
    can_be_at_land: bool = True
    might_be_movable: bool = False
    might_be_jumpable: bool = False
    might_be_used_alone: bool = False
    is_container: bool = False
    is_collectable: bool = False
    is_wearable: bool = False

class Entity(BaseModel):
    id: Optional[str] = None
    type: str
    name: str
    position: Optional[Position] = None
    state: Optional[str] = None
    variant: Optional[str] = None
    is_movable: bool = Field(alias="isMovable", default=False)
    is_jumpable: bool = Field(alias="isJumpable", default=False)
    is_usable_alone: bool = Field(alias="isUsableAlone", default=False)
    is_collectable: bool = Field(alias="isCollectable", default=False)
    is_wearable: bool = Field(alias="isWearable", default=False)
    weight: int = 1
    description: Optional[str] = None
    possible_actions: List[str] = Field(alias="possibleActions", default_factory=list)
    contents: Optional[List[Dict[str, Any]]] = None
    
    class Config:
        populate_by_name = True
        allow_population_by_field_name = True

class GameData(BaseModel):
    theme: str
    environment: Environment
    entities_library: List[EntityModel] = Field(default_factory=list)
    entities: List[Entity] = Field(default_factory=list)
    map_size: int
    border_size: int

class CopywriterContext(BaseModel):
    """Context for the copywriter agent to use"""
    theme: Optional[str] = None
    environment: Optional[Dict[str, Any]] = None
    entities: Optional[List[Dict[str, Any]]] = None
    story: Optional[str] = None
    entity_descriptions: Optional[Dict[str, str]] = None
    story_components: Optional[Dict[str, Any]] = None
    map_data: Optional[Dict[str, Any]] = None

class SaveEntitiesInput(BaseModel):
    entities: List[Dict[str, Any]]

# Define function tools for the agent
@function_tool
@log_tool_execution
async def generate_game_world(
    ctx: RunContextWrapper[CopywriterContext],
    theme: str,
    map_size: int,
    border_size: int,
    object_counts: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """Generate a game world with terrain and objects based on the theme."""
    try:
        # Ensure context exists
        if not hasattr(ctx, 'context') or ctx.context is None:
            logger.warning("Context is None in generate_game_world, initializing new context")
            ctx.context = CopywriterContext()
            
        # Store theme in context
        ctx.context.theme = theme
        
        # Use MAP_SIZE and BORDER_SIZE if not provided
        actual_map_size = map_size if map_size > 0 else MAP_SIZE
        actual_border_size = border_size if border_size > 0 else BORDER_SIZE
        
        # Set default object counts if not provided
        if not object_counts:
            object_counts = {
                "chest": 5,
                "obstacle": 10,
                "campfire": 4,
                "backpack": 3,
                "firewood": 6,
                "tent": 2,
                "bedroll": 3, 
                "log_stool": 4,
                "campfire_spit": 2,
                "campfire_pot": 2,
                "pot": 5
            }
        
        # Generate the island map using the factory function
        symbol_grid = generate_island_map(size=actual_map_size, border_size=actual_border_size)
        
        # Convert symbol grid to binary grid (0 for water, 1 for land)
        binary_grid = []
        for row in symbol_grid:
            binary_row = []
            for cell in row:
                binary_row.append(1 if cell == LAND_SYMBOL else 0)
            binary_grid.append(binary_row)
        
        # Store entities and their positions
        entities = []
        entity_positions = set()
        
        # Find all valid land and water positions
        land_positions = []
        water_positions = []
        
        for y in range(actual_map_size):
            for x in range(actual_map_size):
                if binary_grid[y][x] == 1:  # Land
                    land_positions.append((x, y))
                else:  # Water
                    water_positions.append((x, y))
        
        # Shuffle positions for randomness
        random.shuffle(land_positions)
        random.shuffle(water_positions)
        
        # Function to generate a unique ID
        def generate_id(prefix):
            return f"{prefix}_{random.randint(1000, 9999)}"
        
        # Helper function to safely convert to dictionary
        def safe_to_dict(obj):
            if isinstance(obj, dict):
                return obj  # Already a dictionary
            elif hasattr(obj, 'to_dict') and callable(obj.to_dict):
                return obj.to_dict()  # Call to_dict() method if available
            else:
                # Fallback conversion methods
                return vars(obj) if hasattr(obj, '__dict__') else {"error": "Cannot convert"}
        
        # Modified entity creation function that returns entities and their positions
        async def create_entity(entity_type, factory_func, water_compatible=False, **kwargs):
            # Choose positions based on water compatibility
            positions = water_positions if water_compatible else land_positions
            
            # Skip if no valid positions
            if not positions:
                return None
            
            # Thread-safe position selection
            with asyncio.Lock():
                if not positions:  # Double-check after acquiring lock
                    return None
                x, y = positions.pop(0)
            
            # Create the entity using the factory function and convert to dict if needed
            entity = safe_to_dict(factory_func(**kwargs))
            
            # Add position and ID if not present
            if "id" not in entity:
                entity["id"] = generate_id(entity_type)
            
            entity["position"] = {"x": x, "y": y}
            
            return entity
            
        # Create entity creation tasks for each object type
        entity_tasks = []
        
        # Chests
        for _ in range(object_counts.get("chest", 0)):
            chest_task = create_entity("chest", lambda: ChestFactory.create_chest(
                random.choice(["basic_wooden", "forestwood", "bronze_banded"]))
            )
            entity_tasks.append(chest_task)
        
        # Obstacles
        for _ in range(object_counts.get("obstacle", 0)):
            obstacle_type = random.choice(["rock", "plant", "log", "stump", "hole", "tree"])
            water_compatible = obstacle_type in ["rock"]
            obstacle_task = create_entity(
                "obstacle", 
                lambda: create_land_obstacle(obstacle_type), 
                water_compatible
            )
            entity_tasks.append(obstacle_task)
        
        # Backpacks
        for _ in range(object_counts.get("backpack", 0)):
            backpack_task = create_entity("backpack", lambda: BackpackFactory.create_backpack())
            entity_tasks.append(backpack_task)
        
        # Firewood
        for _ in range(object_counts.get("firewood", 0)):
            firewood_task = create_entity("firewood", lambda: FirewoodFactory.create_firewood())
            entity_tasks.append(firewood_task)
        
        # Tents
        for _ in range(object_counts.get("tent", 0)):
            tent_task = create_entity("tent", lambda: TentFactory.create_tent())
            entity_tasks.append(tent_task)
        
        # Bedrolls
        for _ in range(object_counts.get("bedroll", 0)):
            bedroll_task = create_entity("bedroll", lambda: BedrollFactory.create_bedroll())
            entity_tasks.append(bedroll_task)
        
        # Log stools
        for _ in range(object_counts.get("log_stool", 0)):
            log_stool_task = create_entity("log_stool", lambda: LogStoolFactory.create_stool())
            entity_tasks.append(log_stool_task)
        
        # Campfire spits
        for _ in range(object_counts.get("campfire_spit", 0)):
            campfire_spit_task = create_entity("campfire_spit", lambda: CampfireSpitFactory.create_campfire_spit())
            entity_tasks.append(campfire_spit_task)
        
        # Campfire pots
        for _ in range(object_counts.get("campfire_pot", 0)):
            campfire_pot_task = create_entity("campfire_pot", lambda: CampfirePotFactory.create_pot("tripod"))
            entity_tasks.append(campfire_pot_task)
        
        # Pots
        for _ in range(object_counts.get("pot", 0)):
            size = random.choice(["small", "medium", "big"])
            # Big pots can go in water
            water_compatible = size == "big"
            pot_task = create_entity("pot", lambda: PotFactory.create_pot(size), water_compatible)
            entity_tasks.append(pot_task)
        
        # Campfires
        for _ in range(object_counts.get("campfire", 0)):
            campfire_task = create_entity("campfire", lambda: CampfireFactory.create_campfire())
            entity_tasks.append(campfire_task)
        
        # Execute all entity creation tasks concurrently
        entity_results = await asyncio.gather(*entity_tasks)
        
        # Filter out None results and add to entities list
        entities = [entity for entity in entity_results if entity is not None]
        
        # Create the environment object
        environment = {
            "width": actual_map_size,
            "height": actual_map_size,
            "grid": binary_grid
        }
        
        # Store in context
        ctx.context.environment = environment
        ctx.context.entities = entities
        ctx.context.map_data = {
            "map": {
                "size": actual_map_size,
                "borderSize": actual_border_size,
                "grid": binary_grid
            },
            "entities": entities
        }
        
        # Calculate land percentage
        land_count = sum(row.count(1) for row in binary_grid)
        land_percentage = (land_count / (actual_map_size * actual_map_size)) * 100
        
        # Build the result
        result = {
            "theme": theme,
            "map_size": actual_map_size,
            "entity_count": len(entities),
            "land_percentage": land_percentage,
            "object_types": list(set(entity.get("type", "unknown") for entity in entities)),
            "environment": environment,
            "entities": entities
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error generating game world: {str(e)}")
        return {"error": str(e)}

@function_tool
async def get_entity_library(
    ctx: RunContextWrapper[CopywriterContext]
) -> Dict[str, Any]:
    """Return a predefined library of entity types and their properties."""
    try:
        # Predefined entity definitions
        entity_definitions = {
            "chest": {
                "possible_states": ["locked", "unlocked", "open", "closed"],
                "possible_actions": ["open", "close", "unlock", "destroy", "examine"],
                "variants": ["wooden", "silver", "golden", "magical"],
                "can_be_at_water": False,
                "can_be_at_land": True,
                "might_be_movable": True,
                "might_be_jumpable": False,
                "might_be_used_alone": True,
                "is_container": True,
                "is_collectable": False,
                "is_wearable": False
            },
            "rock": {
                "possible_states": ["broken", "unbroken"],
                "possible_actions": ["break", "throw", "examine"],
                "variants": ["small", "medium", "big"],
                "can_be_at_water": True,
                "can_be_at_land": True,
                "might_be_movable": True,
                "might_be_jumpable": True,
                "might_be_used_alone": True,
                "is_container": False,
                "is_collectable": True,
                "is_wearable": False
            },
            "campfire": {
                "possible_states": ["unlit", "burning", "dying", "extinguished"],
                "possible_actions": ["light", "extinguish", "cook", "warm"],
                "variants": ["small", "medium", "large"],
                "can_be_at_water": False,
                "can_be_at_land": True,
                "might_be_movable": False,
                "might_be_jumpable": True,
                "might_be_used_alone": True,
                "is_container": False,
                "is_collectable": False,
                "is_wearable": False
            },
            "tent": {
                "possible_states": ["folded", "setup", "damaged"],
                "possible_actions": ["enter", "exit", "setup", "pack"],
                "variants": ["small", "medium", "large"],
                "can_be_at_water": False,
                "can_be_at_land": True,
                "might_be_movable": True,
                "might_be_jumpable": False,
                "might_be_used_alone": True,
                "is_container": True,
                "is_collectable": False,
                "is_wearable": False
            },
            "pot": {
                "possible_states": ["default", "breaking", "broken"],
                "possible_actions": ["fill", "empty", "cook", "examine"],
                "variants": ["small", "medium", "big"],
                "can_be_at_water": True,
                "can_be_at_land": True,
                "might_be_movable": True,
                "might_be_jumpable": False,
                "might_be_used_alone": True,
                "is_container": True,
                "is_collectable": False,
                "is_wearable": False
            },
            "backpack": {
                "possible_states": ["empty", "filled"],
                "possible_actions": ["open", "close", "wear", "remove"],
                "variants": ["small", "medium", "large"],
                "can_be_at_water": False,
                "can_be_at_land": True,
                "might_be_movable": True,
                "might_be_jumpable": False,
                "might_be_used_alone": True,
                "is_container": True,
                "is_collectable": True,
                "is_wearable": True
            },
            "bedroll": {
                "possible_states": ["rolled", "unrolled"],
                "possible_actions": ["sleep", "roll", "unroll"],
                "variants": ["basic", "comfort", "luxury"],
                "can_be_at_water": False,
                "can_be_at_land": True,
                "might_be_movable": True,
                "might_be_jumpable": False,
                "might_be_used_alone": True,
                "is_container": False,
                "is_collectable": True,
                "is_wearable": False
            },
            "firewood": {
                "possible_states": ["dry", "wet", "burning"],
                "possible_actions": ["collect", "burn", "stack"],
                "variants": ["branch", "log", "kindling"],
                "can_be_at_water": False,
                "can_be_at_land": True,
                "might_be_movable": True,
                "might_be_jumpable": False,
                "might_be_used_alone": True,
                "is_container": False,
                "is_collectable": True,
                "is_wearable": False
            },
            "log_stool": {
                "possible_states": ["default", "occupied"],
                "possible_actions": ["sit", "stand", "move"],
                "variants": ["small", "medium", "large"],
                "can_be_at_water": False,
                "can_be_at_land": True,
                "might_be_movable": True,
                "might_be_jumpable": False,
                "might_be_used_alone": True,
                "is_container": False,
                "is_collectable": False,
                "is_wearable": False
            },
            "obstacle": {
                "possible_states": ["default", "broken", "moved"],
                "possible_actions": ["examine", "break", "climb", "jump"],
                "variants": ["rock", "plant", "log", "stump", "hole", "tree"],
                "can_be_at_water": True,
                "can_be_at_land": True,
                "might_be_movable": True,
                "might_be_jumpable": True,
                "might_be_used_alone": True,
                "is_container": False,
                "is_collectable": False,
                "is_wearable": False
            }
        }
        
        logger.info(f"Returning entity library with {len(entity_definitions)} types")
        return {
            "entity_library": entity_definitions
        }
        
    except Exception as e:
        logger.error(f"Error getting entity library: {str(e)}")
        return {"error": str(e)}

@function_tool
@log_tool_execution
async def describe_entity(
    ctx: RunContextWrapper[CopywriterContext],
    entity_type: str,
    variant: str,
    state: str,
    description: str
) -> Dict[str, Any]:
    """Create a compelling description for an entity in the game."""
    try:
        # Ensure context exists
        if not hasattr(ctx, 'context') or ctx.context is None:
            logger.warning("Context is None in describe_entity, initializing new context")
            ctx.context = CopywriterContext()
            
        # Initialize entity_descriptions if it doesn't exist
        if not ctx.context.entity_descriptions:
            ctx.context.entity_descriptions = {}
        
        # Create a key for the entity by combining type, variant, and state
        entity_key = f"{entity_type}_{variant}_{state}"
        
        # Store the description
        ctx.context.entity_descriptions[entity_key] = description
        
        return {
            "entity_type": entity_type,
            "variant": variant,
            "state": state,
            "description": description
        }
    except Exception as e:
        logger.error(f"Error describing entity: {str(e)}")
        return {"error": str(e)}

@function_tool
@log_tool_execution
async def craft_entity_interaction(
    ctx: RunContextWrapper[CopywriterContext],
    entity_type: str,
    action: str,
    narration: str,
    consequences: List[str]
) -> Dict[str, Any]:
    """Create narrative text for player interactions with entities."""
    try:
        # Ensure context exists
        if not hasattr(ctx, 'context') or ctx.context is None:
            logger.warning("Context is None in craft_entity_interaction, initializing new context")
            ctx.context = CopywriterContext()
            
        interaction = {
            "entity_type": entity_type,
            "action": action,
            "narration": narration,
            "consequences": consequences
        }
        
        # Store the interaction in context
        if not ctx.context.story_components:
            ctx.context.story_components = {}
        
        if "interactions" not in ctx.context.story_components:
            ctx.context.story_components["interactions"] = []
            
        ctx.context.story_components["interactions"].append(interaction)
        
        return interaction
    except Exception as e:
        logger.error(f"Error crafting entity interaction: {str(e)}")
        return {"error": str(e)}

@function_tool
@log_tool_execution
async def create_story_intro(
    ctx: RunContextWrapper[CopywriterContext],
    theme: str,
    location_description: str,
    mood: str
) -> Dict[str, Any]:
    """Create an introduction for the game story based on the theme and environment."""
    try:
        # Ensure context exists
        if not hasattr(ctx, 'context') or ctx.context is None:
            logger.warning("Context is None in create_story_intro, initializing new context")
            ctx.context = CopywriterContext()
        
        # Store the theme in context
        ctx.context.theme = theme
        
        # Generate an intro story that will be retained in context
        intro = {
            "theme": theme,
            "location": location_description,
            "mood": mood,
            "intro_text": f"The player finds themselves in a {mood} atmosphere, {location_description}. The theme of '{theme}' permeates the environment."
        }
        
        # Store the intro in context
        if not ctx.context.story_components:
            ctx.context.story_components = {}
        ctx.context.story_components["intro"] = intro
        
        logger.info(f"Created story intro for theme: {theme}")
        return intro
    except Exception as e:
        logger.error(f"Error creating story intro: {str(e)}")
        return {"error": str(e)}

@function_tool
@log_tool_execution
async def generate_quest(
    ctx: RunContextWrapper[CopywriterContext],
    title: str,
    description: str,
    objectives: List[str],
    required_entities: List[str],
    reward_description: str
) -> Dict[str, Any]:
    """Generate a quest with objectives based on the map and entities."""
    try:
        # Ensure context exists
        if not hasattr(ctx, 'context') or ctx.context is None:
            logger.warning("Context is None in generate_quest, initializing new context")
            ctx.context = CopywriterContext()
            
        quest = {
            "title": title,
            "description": description,
            "objectives": objectives,
            "required_entities": required_entities,
            "reward": reward_description
        }
        
        # Store the quest in context
        if not ctx.context.story_components:
            ctx.context.story_components = {}
        ctx.context.story_components["quest"] = quest
        
        return quest
    except Exception as e:
        logger.error(f"Error generating quest: {str(e)}")
        return {"error": str(e)}

@function_tool
@log_tool_execution
async def complete_story(
    ctx: RunContextWrapper[CopywriterContext]
) -> Dict[str, Any]:
    """Compile all story components into a complete narrative."""
    try:
        # Ensure context exists
        if not hasattr(ctx, 'context') or ctx.context is None:
            logger.warning("Context is None in complete_story, initializing new context")
            ctx.context = CopywriterContext()
            return {"error": "Context was missing, unable to complete story"}
            
        # Get all stored components
        components = ctx.context.story_components if ctx.context.story_components else {}
        descriptions = ctx.context.entity_descriptions if ctx.context.entity_descriptions else {}
        
        # Extract map data and entities
        map_data = ctx.context.map_data if ctx.context.map_data else {}
        entities = ctx.context.entities if ctx.context.entities else []
        
        # Log the context state for debugging
        logger.info(f"Context state in complete_story: theme={ctx.context.theme}, " 
                   f"has_components={bool(components)}, has_descriptions={bool(descriptions)}, "
                   f"has_map_data={bool(map_data)}, entity_count={len(entities)}")
        
        # Create terrain description
        terrain_description = generate_terrain_description(ctx.context.environment)
        
        # Combine everything into a complete story structure
        complete_story = {
            "theme": ctx.context.theme,
            "environment": ctx.context.environment,
            "terrain_description": terrain_description,
            "entity_descriptions": descriptions,
            "narrative_components": components,
            "game_data": {
                "map": map_data.get("map", {}),
                "entities": entities
            },
            "complete_narrative": "The complete game story narrative compiled from all components."
        }
        print(f"complete_story: {complete_story}")
        
        # Add quest information if available
        if "quest" in components:
            complete_story["quest"] = components["quest"]
        
        # Store the complete story
        ctx.context.story = complete_story
        
        logger.info("Successfully completed story compilation")
        return complete_story
    except Exception as e:
        logger.error(f"Error completing story: {str(e)}")
        # Print traceback for better debugging
        logger.error(traceback.format_exc())
        return {"error": str(e)}

def generate_terrain_description(environment):
    """Generate a description of the terrain based on the environment data."""
    if not environment or "grid" not in environment:
        return "A mysterious landscape of unknown features."
    
    grid = environment.get("grid", [])
    if not grid:
        return "A blank canvas of a world, waiting to be shaped."
    
    # Calculate land and water percentages
    total_cells = sum(len(row) for row in grid)
    land_count = sum(sum(row) for row in grid)
    water_count = total_cells - land_count
    
    land_percentage = (land_count / total_cells) * 100 if total_cells > 0 else 0
    water_percentage = (water_count / total_cells) * 100 if total_cells > 0 else 0
    
    # Describe based on percentages
    if land_percentage > 80:
        terrain = "A vast continent with small lakes and streams scattered throughout."
    elif land_percentage > 60:
        terrain = "A large landmass with significant bodies of water."
    elif land_percentage > 40:
        terrain = "An archipelago of medium-sized islands connected by shallow waters."
    elif land_percentage > 20:
        terrain = "A scattering of small islands in a vast ocean."
    else:
        terrain = "A few tiny islands barely rising above a seemingly endless ocean."
    
    # Additional details about land formations
    # This would require more complex analysis of the grid pattern
    
    return terrain

@function_tool
@log_tool_execution
async def save_entities(
    ctx: RunContextWrapper[CopywriterContext],
    entities_json: str
) -> Dict[str, Any]:
    """Save a list of created entities to the context.
    
    Args:
        entities_json: A JSON string containing an array of entity objects
    """
    try:
        # Ensure context exists
        if not hasattr(ctx, 'context') or ctx.context is None:
            logger.warning("Context is None in save_entities, initializing new context")
            ctx.context = CopywriterContext()
        
        # Parse entities from JSON string
        try:
            entities = json.loads(entities_json)
            if not isinstance(entities, list):
                return {"error": "Entities must be a list/array"}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse entities JSON: {str(e)}")
            return {"error": f"Invalid JSON: {str(e)}"}
        
        # Store entities in context
        ctx.context.entities = entities
        
        # Store descriptions if available
        if not ctx.context.entity_descriptions:
            ctx.context.entity_descriptions = {}
            
        for entity in entities:
            if "description" in entity and "type" in entity:
                key = f"{entity['type']}_{entity.get('variant', 'default')}_{entity.get('state', 'default')}"
                ctx.context.entity_descriptions[key] = entity["description"]
        
        logger.info(f"Saved {len(entities)} entities to context")
        return {
            "success": True,
            "entity_count": len(entities)
        }
        
    except Exception as e:
        logger.error(f"Error saving entities: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": str(e)}

@function_tool
@log_tool_execution
async def describe_entities_batch(
    ctx: RunContextWrapper[CopywriterContext],
    entities_batch: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Create compelling descriptions for a batch of entities in parallel.
    
    Args:
        entities_batch: A list of entity objects to describe in parallel
        
    Returns:
        Dict with success status and count of described entities
    """
    try:
        # Ensure context exists
        if not hasattr(ctx, 'context') or ctx.context is None:
            logger.warning("Context is None in describe_entities_batch, initializing new context")
            ctx.context = CopywriterContext()
        
        # Initialize entity_descriptions if it doesn't exist
        if not ctx.context.entity_descriptions:
            ctx.context.entity_descriptions = {}
        
        async def process_entity(entity):
            try:
                # Extract entity properties
                entity_type = entity.get("type", "unknown")
                variant = entity.get("variant", "default")
                state = entity.get("state", "default")
                
                # Generate a description based on entity properties
                description = f"A {variant} {entity_type} in {state} state."
                
                # Create a key for the entity
                entity_key = f"{entity_type}_{variant}_{state}"
                
                # Store the description
                ctx.context.entity_descriptions[entity_key] = description
                
                # Add description to the entity
                entity["description"] = description
                
                return {
                    "entity_type": entity_type,
                    "variant": variant,
                    "state": state,
                    "description": description
                }
            except Exception as e:
                logger.error(f"Error processing entity: {str(e)}")
                return {"error": str(e)}
        
        # Process entities in parallel
        tasks = [process_entity(entity) for entity in entities_batch]
        results = await asyncio.gather(*tasks)
        
        # Count successful descriptions
        success_count = sum(1 for result in results if "error" not in result)
        
        return {
            "success": True,
            "described_count": success_count,
            "total_count": len(entities_batch),
            "results": results
        }
    except Exception as e:
        logger.error(f"Error describing entities batch: {str(e)}")
        return {"error": str(e)}

class GameCopywriterAgent:
    """Agent for creating game story copy based on provided game data."""
    
    def __init__(self, openai_api_key: str = None):
        logger.info("Initializing GameCopywriterAgent")
        
        # Check for API key in parameter or environment
        self.openai_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        
        # Validate API key exists
        if not self.openai_key:
            logger.error("No OpenAI API key provided. Set OPENAI_API_KEY environment variable or pass key directly.")
            raise ValueError("OpenAI API key is required. Please provide it as a parameter or set the OPENAI_API_KEY environment variable.")
        
        # Initialize OpenAI client with validated key
        self.openai_client = OpenAI(api_key=self.openai_key)
        logger.info("OpenAI client initialized successfully")
        
        # Initialize context
        self.context = CopywriterContext()
        
        # Setup agent data
        self.agent_data = self.setup_agent()
        logger.info("Agent data setup completed")
        
    def setup_agent(self) -> Dict:
        """Set up the OpenAI agent with system prompt and tools."""
        system_prompt = """
        # MISSION
You are a creative copywriter tasked with crafting the core of an RPG game story. Your goal is to design a rich narrative structure with all necessary game parameters.

## YOUR ROLE

1. Analyze the input Theme and Be Creative

2. Generate creative, immersive copy for:
   - Introductory story text
   - Entity descriptions
   - Interaction narratives
   - Quest objectives
   - Overall game story arc

## PROCESS

1. First, use the `generate_game_world` function to generate a game world with terrain and objects. Map size between 40 and 60.
2. Then, use `get_entity_library` to retrieve the predefined entity types
3. Create entity instances using the library data (this happens in the agent's reasoning)
4. Use `save_entities` to store the created entities in the context
5. Use `describe_entities_batch` to efficiently describe entities in parallel batches
6. Develop a compelling introduction with `create_story_intro`
7. Create detailed descriptions for key entities with `describe_entity`
8. Design interesting interactions with `craft_entity_interaction` 
9. Build a quest with clear objectives using `generate_quest`
10. Finally, compile everything with `complete_story`

## TERRAIN AWARENESS

Pay special attention to the terrain:
- Objects in water should be described accordingly (floating, partially submerged)
- Land objects should be described in context of their surroundings
- Consider how water and land interact in your narrative

## GUIDELINES

- Maintain a consistent tone that matches the game theme
- Create vivid, evocative descriptions that bring the world to life
- Develop logical interactions between entities
- Establish clear narrative progression
- Balance detail with brevity for game text

Your writing should be cohesive, engaging, and appropriate for the game environment.
"""

        tools = [
            generate_game_world,
            get_entity_library,
            save_entities,
            describe_entities_batch,
            describe_entity,
            craft_entity_interaction,
            create_story_intro,
            generate_quest,
            complete_story
        ]
        
        return {
            "system_prompt": system_prompt,
            "tools": tools
        }
    
    async def process_game_data(self, theme: str = "Scary Place") -> Dict[str, Any]:
        """Process the game data and generate story copy."""
        logger.info("Processing game data to generate story")
        
        try:
            # Initialize context with theme if possible
            if not hasattr(self, 'context') or self.context is None:
                logger.warning("Agent context was None, initializing new context")
                self.context = CopywriterContext()

            self.context.theme = theme
            
            logger.info(f"Context initialized with theme: {self.context.theme}")
            
            # Create an agent first
            agent = Agent(
                name="game_story_copywriter",
                instructions=self.agent_data["system_prompt"],
                tools=self.agent_data["tools"]
            )
            
            # Initialize the runner without arguments
            runner = Runner()
            
            # Configure the runner after initialization
            runner.agent = agent
            runner.client = self.openai_client
            runner.context = self.context
            
            # Prepare the input message
            input_message = f"""Please create a complete game story based on theme: {theme}
            
When processing entities, use the describe_entities_batch function to process them in parallel for better performance."""
            
            # Run the agent with the required parameters and timeout handling
            try:
                logger.info("Starting OpenAI agent run - this may take some time...")
                
                # Set up async tasks to process in parallel where possible
                async def process_with_agent():
                    return await runner.run(input=input_message, starting_agent=agent)
                
                # Create a task for the agent processing
                agent_task = asyncio.create_task(process_with_agent())
                
                # Wait for the task with timeout
                result = await asyncio.wait_for(agent_task, timeout=120)  # 2 minute timeout
                
                logger.info("OpenAI agent run completed successfully")
            except asyncio.TimeoutError:
                logger.error("OpenAI API request timed out after 120 seconds")
                return {"error": "Request to OpenAI API timed out. Please try again or use a smaller world size."}
            except Exception as api_error:
                logger.error(f"Error during OpenAI API call: {str(api_error)}")
                return {"error": f"OpenAI API error: {str(api_error)}"}
            
            # Extract the final result
            if hasattr(result, 'final_output'):
                logger.info("Extracted final output from result")
                narrative_content = result.final_output
            else:
                logger.info("Using context story as final result")
                narrative_content = self.context.story
            
            if not narrative_content:
                logger.warning("No narrative content was generated")
                return {"error": "Failed to generate narrative content", "raw_result": str(result)}
                
            logger.info(f"Successfully generated story with theme: {theme}")
            return narrative_content
            
        except Exception as e:
            error_message = f"Error processing game data: {str(e)}"
            logger.error(error_message)
            return {"error": error_message}

# Example usage:
async def main():
    """Example usage of the GameCopywriterAgent."""
    # Get API key from command line if provided
    import sys
    api_key = sys.argv[1] if len(sys.argv) > 1 else None
    
    try:
        print("🚀 Initializing Game Copywriter Agent")
        
        # Create an instance of the agent with optional API key
        agent = GameCopywriterAgent(openai_api_key=api_key)
        
        print("📊 Setting up example game data")
        
        # Example game data
        game_data = { }
        #     "theme": "Abandoned at Sea",
        #     "environment": {
        #         "width": 20,  # Set a reasonable default size
        #         "height": 20,
        #         "grid": [
        #             [0, 0, 0, 0],
        #             [0, 1, 1, 0],
        #             [0, 1, 1, 0],
        #             [0, 0, 0, 0]
        #         ]
        #     },
        #     "map_size": 20,  # Add required map_size parameter
        #     "border_size": 5,  # Add required border_size parameter
        #     "entities_library": [
        #         {
        #             "type": "chest",
        #             "possible_states": ["locked", "unlocked"],
        #             "possible_actions": ["open", "close", "destroy"],
        #             "variants": ["wooden", "metal", "stone"],
        #             "can_be_at_water": False,
        #             "can_be_at_land": True,
        #             "might_be_movable": True,
        #             "might_be_jumpable": True,
        #             "might_be_used_alone": True,
        #             "is_container": True,
        #             "is_collectable": True,
        #             "is_wearable": False
        #         },
        #         {
        #             "type": "rock",
        #             "possible_states": ["broken", "unbroken"],
        #             "possible_actions": ["break"],
        #             "variants": ["small", "medium", "big"],
        #             "can_be_at_water": True,
        #             "can_be_at_land": True,
        #             "might_be_movable": True,
        #             "might_be_jumpable": True,
        #             "might_be_used_alone": True,
        #             "is_container": False,
        #             "is_collectable": True,
        #             "is_wearable": False
        #         }
        #     ]
        # }
        
        print("🤖 Generating game story (this may take a minute)...")
        start_time = time.time()
        
        # Create a progress indicator
        progress_task = None
        if sys.stdout.isatty():  # Only show spinner in interactive terminal
            async def show_progress():
                spinner = "|/-\\"
                idx = 0
                while True:
                    print(f"\rProcessing {spinner[idx % len(spinner)]}", end="")
                    idx += 1
                    await asyncio.sleep(0.1)
            
            progress_task = asyncio.create_task(show_progress())
        
        try:
            # Process the game data and get a story
            result = await agent.process_game_data()
            
            # Stop the progress indicator
            if progress_task:
                progress_task.cancel()
                try:
                    await progress_task
                except asyncio.CancelledError:
                    pass
                print("\r" + " " * 20 + "\r", end="")  # Clear the spinner line
            
            elapsed_time = time.time() - start_time
            print(f"✅ Story generated in {elapsed_time:.2f} seconds")
            
            # Check for error
            if isinstance(result, dict) and "error" in result:
                print(f"❌ Error: {result['error']}")
                sys.exit(1)
            
            # Print truncated result in color
            try:
                if isinstance(result, dict):
                    print("📝 Story Result:")
                    if "theme" in result:
                        print(f"\n🏝️ Theme: {result['theme']}")
                    if "terrain_description" in result:
                        print(f"\n🗺️ Terrain: {result['terrain_description']}")
                    if "narrative_components" in result and "intro" in result["narrative_components"]:
                        intro = result["narrative_components"]["intro"]
                        print(f"\n📖 Introduction: {intro.get('intro_text', 'No intro text available')}")
                    if "quest" in result:
                        quest = result["quest"]
                        print(f"\n🎯 Quest: {quest.get('title', 'Unnamed Quest')}")
                        print(f"   - {quest.get('description', 'No description available')}")
                    
                    # Save full result to file
                    with open("game_story_result.json", "w") as f:
                        json.dump(result, f, indent=2)
                    print(f"\n💾 Full story saved to game_story_result.json")
                else:
                    # Truncate if too long
                    result_str = str(result)
                    print(result_str)
                    
                    # Save to file
                    with open("game_story_result.txt", "w") as f:
                        f.write(str(result))
                    print(f"💾 Full story saved to game_story_result.txt")
            except Exception as e:
                print(f"Error displaying result: {str(e)}")
                print("Raw result:", result)
        
        except asyncio.CancelledError:
            if progress_task:
                progress_task.cancel()
            print("\r" + " " * 20 + "\r", end="")  # Clear the spinner line
            print("❌ Operation cancelled")
            sys.exit(1)
    
    except ValueError as e:
        print(f"❌ Error: {e}")
        print("\nUsage: python agent_copywriter_direct.py [OPENAI_API_KEY]")
        print("       You can also set the OPENAI_API_KEY environment variable")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 