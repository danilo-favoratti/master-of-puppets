import argparse
import json
import os
import sys
import time # Added for profiling
from typing import List, Optional, Union, Tuple # Added Tuple

# Assuming openai library is installed: pip install openai
# Assuming pydantic library is installed: pip install pydantic
import openai
from pydantic import BaseModel, ValidationError

from factory_game import generate_island_map


# --- Pydantic Models ---

# Input Models (used internally for structure)
class InputMapLand(BaseModel):
    width: int
    height: int
    grid: List[List[int]]

class AbstractEntity(BaseModel):
    type: str
    possible_states: List[str]
    possible_actions: List[str]
    variants: List[str]
    can_be_at_water: bool
    can_be_at_land: bool
    might_be_movable: bool
    might_be_jumpable: bool
    might_be_used_alone: bool
    is_container: bool
    is_collectable: bool
    is_wearable: bool

# Output Models
class OutputMapLand(BaseModel):
    width: int
    height: int
    grid: List[List[int]]

class Position(BaseModel):
    x: int
    y: int

class RealObject(BaseModel):
    id: str
    type: str
    name: str
    position: Position
    state: str
    variant: str
    isMovable: bool
    isJumpable: bool
    isUsableAlone: bool
    isCollectable: bool
    isWearable: bool
    weight: Optional[Union[int, float]] = None
    possibleActions: List[str]
    description: str

# Model for parsing LLM's partial response
class LLMResponse(BaseModel):
    real_objects: List[RealObject]

# Final full output structure
class OutputData(BaseModel):
    map_land: OutputMapLand
    real_objects: List[RealObject]

# --- Hardcoded Abstract Entities Data ---
# (ABSTRACT_ENTITIES_DATA remains the same as before)
ABSTRACT_ENTITIES_DATA = [
    {
      "type": "chest", "possible_states": ["locked", "unlocked", "open", "closed"], "possible_actions": ["open", "close", "unlock", "destroy", "examine"],
      "variants": ["wooden", "silver", "golden", "magical"], "can_be_at_water": False, "can_be_at_land": True, "might_be_movable": True,
      "might_be_jumpable": False, "might_be_used_alone": True, "is_container": True, "is_collectable": False, "is_wearable": False
    },
    {
      "type": "rock", "possible_states": ["broken", "unbroken"], "possible_actions": ["break", "throw", "examine"],
      "variants": ["small", "medium", "big"], "can_be_at_water": True, "can_be_at_land": True, "might_be_movable": True,
      "might_be_jumpable": True, "might_be_used_alone": True, "is_container": False, "is_collectable": True, "is_wearable": False
    },
    {
      "type": "campfire", "possible_states": ["unlit", "burning", "dying", "extinguished"], "possible_actions": ["light", "extinguish", "cook", "warm"],
      "variants": ["small", "medium", "large"], "can_be_at_water": False, "can_be_at_land": True, "might_be_movable": False,
      "might_be_jumpable": True, "might_be_used_alone": True, "is_container": False, "is_collectable": False, "is_wearable": False
    },
    {
      "type": "tent", "possible_states": ["folded", "setup", "damaged"], "possible_actions": ["enter", "exit", "setup", "pack"],
      "variants": ["small", "medium", "large"], "can_be_at_water": False, "can_be_at_land": True, "might_be_movable": True,
      "might_be_jumpable": False, "might_be_used_alone": True, "is_container": True, "is_collectable": False, "is_wearable": False
    },
    {
      "type": "pot", "possible_states": ["default", "breaking", "broken"], "possible_actions": ["fill", "empty", "cook", "examine"],
      "variants": ["small", "medium", "big"], "can_be_at_water": True, "can_be_at_land": True, "might_be_movable": True,
      "might_be_jumpable": False, "might_be_used_alone": True, "is_container": True, "is_collectable": False, "is_wearable": False
    },
    {
      "type": "backpack", "possible_states": ["empty", "filled"], "possible_actions": ["open", "close", "wear", "remove"],
      "variants": ["small", "medium", "large"], "can_be_at_water": False, "can_be_at_land": True, "might_be_movable": True,
      "might_be_jumpable": False, "might_be_used_alone": True, "is_container": True, "is_collectable": True, "is_wearable": True
    },
    {
      "type": "bedroll", "possible_states": ["rolled", "unrolled"], "possible_actions": ["sleep", "roll", "unroll"],
      "variants": ["basic", "comfort", "luxury"], "can_be_at_water": False, "can_be_at_land": True, "might_be_movable": True,
      "might_be_jumpable": False, "might_be_used_alone": True, "is_container": False, "is_collectable": True, "is_wearable": False
    },
    {
      "type": "firewood", "possible_states": ["dry", "wet", "burning"], "possible_actions": ["collect", "burn", "stack"],
      "variants": ["branch", "log", "kindling"], "can_be_at_water": False, "can_be_at_land": True, "might_be_movable": True,
      "might_be_jumpable": False, "might_be_used_alone": True, "is_container": False, "is_collectable": True, "is_wearable": False
    },
    {
      "type": "log_stool", "possible_states": ["default", "occupied"], "possible_actions": ["sit", "stand", "move"],
      "variants": ["small", "medium", "large"], "can_be_at_water": False, "can_be_at_land": True, "might_be_movable": True,
      "might_be_jumpable": False, "might_be_used_alone": True, "is_container": False, "is_collectable": False, "is_wearable": False
    },
    {
      "type": "obstacle", "possible_states": ["default", "broken", "moved"], "possible_actions": ["examine", "break", "climb", "jump"],
      "variants": ["rock", "plant", "log", "stump", "hole", "tree"], "can_be_at_water": True, "can_be_at_land": True, "might_be_movable": True,
      "might_be_jumpable": True, "might_be_used_alone": True, "is_container": False, "is_collectable": False, "is_wearable": False
    }
]

# --- Map Creation and Helper Functions ---

def createMap() -> InputMapLand:
    """Generates the map data structure."""
    width = 60
    height = 60
    # Adjust radius for a reasonable island size within 60x60
    grid = generate_island_map(size=60, border_size=15)
    print(f"Generated map data ({width}x{height}).")
    return InputMapLand(width=width, height=height, grid=grid)

def get_land_coordinates(grid: List[List[int]]) -> List[List[int]]:
    """Extracts land coordinates ([x, y] pairs) from the grid."""
    land_coords = []
    height = len(grid)
    if height == 0:
        return []
    width = len(grid[0])
    for y in range(height):
        for x in range(width):
            if grid[y][x] == 1: # Assuming 1 is land
                land_coords.append([x, y]) # Use list format [x, y] for JSON
    return land_coords

# --- Prompt ---

# Updated Prompt: Asks for fewer objects, expects simplified map input,
# and requests ONLY the real_objects list in the output JSON.
AGENT_PROMPT = """
# INSTRUCTIONS
You are an AI assistant generating game object data based on abstract definitions and map info.
You will receive a JSON object containing:
- `map_info`: Includes `width`, `height`, and `land_coordinates` (a list of `[x, y]` pairs representing valid land spots).
- `abstract_entities`: A list of possible entity types with their properties.

Your goal is to generate a list of specific game objects (`real_objects`). Follow these steps:

1.  **Analyze Input:** Understand the `map_info` (dimensions and valid land spots) and the available `abstract_entities`. Note the survival/camping theme.
2.  **Select & Place Entities:**
    *   Choose **8-12** distinct entity types from `abstract_entities` suitable for the theme.
    *   For each chosen type, create one specific instance (`real_object`).
    *   Assign a unique `id` (e.g., "type-1").
    *   Give it a descriptive `name`.
    *   Choose a `variant` from the entity's possible variants.
    *   Select an initial `state` from the entity's possible states.
    *   Determine specific properties (`isMovable`, `isJumpable`, etc.) based on `might_be_`/`is_` flags in the abstract definition. Decide definitively (true/false).
    *   Assign a plausible `weight` (integer or float, optional).
    *   Determine `possibleActions` (usually same as abstract, minor adjustments based on state are allowed).
    *   Assign `position` (`x`, `y`) by choosing coordinates. Ensure land-only items (`can_be_at_land: true`, `can_be_at_water: false`) are placed ONLY on coordinates provided in `land_coordinates`. Respect `can_be_at_water` for water items (though no water coordinates are provided in this input version, assume 0,0 might be water if needed, but focus on land placement). Avoid placing multiple objects in the exact same coordinate.
    *   Write a brief, evocative `description`.
3.  **Construct Output:** Create a JSON object containing ONLY a single key: `"real_objects"`, whose value is the list of the specific object instances you generated.

**Output Format:**
Ensure the output is a single, valid JSON object containing ONLY the `real_objects` list, like this:
```json
{
  "real_objects": [
    {
      "id": "campfire-1",
      "type": "campfire",
      "name": "Small Camp Fire",
      "position": { "x": 25, "y": 28 }, // Example coordinates from land_coordinates
      "state": "unlit",
      "variant": "small",
      "isMovable": false,
      "isJumpable": true,
      "isUsableAlone": true,
      "isCollectable": false,
      "isWearable": false,
      "weight": 5,
      "possibleActions": ["light", "extinguish", "cook", "warm"],
      "description": "A small pile of wood and stones on the island soil, ready to be lit."
    },
    // ... other 7-11 objects ...
 ]
}
```
Do NOT include the `map_land` or `map_info` in your output. Do NOT add any text before or after the JSON object.
"""

# --- Agent Runner Class ---

class AgentRunner:
    """
    Handles interaction with the OpenAI API to generate game world data.
    Accepts the input data as a pre-formatted JSON string.
    """
    def __init__(self, openai_api_key: Optional[str] = None, input_data_str: Optional[str] = None):
        self.openai_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not self.openai_key:
            raise ValueError("OpenAI API key not provided or found in environment variables (OPENAI_API_KEY)")
        if not input_data_str:
            raise ValueError("Input data string not provided to AgentRunner.")

        self.client = openai.OpenAI(api_key=self.openai_key)
        self.input_data_str = input_data_str # Store the raw input JSON string
        self.agent_prompt = AGENT_PROMPT

    def run(self) -> List[RealObject]: # Returns only the list of objects
        """
        Sends the prompt and input data string to OpenAI and parses the response
        to extract the list of RealObject instances.
        """
        print("Sending request to OpenAI with optimized input...")
        start_time = time.time() # Start timer for API call
        try:
            # Construct the user message content including the raw input data string
            user_message_content = (
                "Here is the abstract world definition and map info:\n"
                "```json\n"
                f"{self.input_data_str}\n" # Send the provided raw string
                "```\n"
                "Please generate the `real_objects` list based on the instructions and provide the JSON output as described."
            )

            response = self.client.chat.completions.create(
                # Consider gpt-3.5-turbo if o3-mini is slow/unreliable for this
                # model="o3-mini",
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.agent_prompt},
                    {"role": "user", "content": user_message_content},
                ],
                response_format={"type": "json_object"}, # Ensures the output is a valid JSON object
            )

            api_call_time = time.time() - start_time # End timer
            print(f"OpenAI API call took: {api_call_time:.2f} seconds")

            response_content = response.choices[0].message.content

            if not response_content:
                raise ValueError("Received empty response from OpenAI.")

            print("Parsing OpenAI response (expecting {'real_objects': [...]})...")
            # Parse the JSON response expecting the structure {"real_objects": [...]}
            # Use the LLMResponse model for validation
            llm_output = LLMResponse.model_validate_json(response_content)
            print("Successfully parsed response.")
            return llm_output.real_objects # Return only the list of RealObject

        except openai.APIError as e:
            print(f"OpenAI API returned an API Error: {e}")
            raise
        except openai.APIConnectionError as e:
            print(f"Failed to connect to OpenAI API: {e}")
            raise
        except openai.RateLimitError as e:
            print(f"OpenAI API request exceeded rate limit: {e}")
            raise
        except json.JSONDecodeError as e:
            print(f"Failed to decode OpenAI response JSON: {e}")
            print(f"Raw response was: {response_content}")
            raise
        except ValidationError as e:
            # This validation is against the *LLMResponse* model now
            print(f"OpenAI response validation failed (LLMResponse structure): {e}")
            print(f"Raw response was: {response_content}")
            raise
        except Exception as e:
            print(f"An unexpected error occurred during API call or parsing: {e}")
            raise


# --- Main Execution ---

def main():
    parser = argparse.ArgumentParser(description="Run OpenAI Agent to generate game world data.")
    parser.add_argument("--openai-key", help="OpenAI API Key (optional, overrides OPENAI_API_KEY env var)")
    args = parser.parse_args()

    overall_start_time = time.time()

    # 1. Generate Map Data & Extract Land Coordinates
    print("Step 1: Generating map...")
    start_time = time.time()
    map_land_obj: InputMapLand = createMap() # Keep the original map object
    land_coordinates = get_land_coordinates(map_land_obj.grid)
    map_gen_time = time.time() - start_time
    print(f"Map generation & coordinate extraction took: {map_gen_time:.2f} seconds. Found {len(land_coordinates)} land cells.")
    if not land_coordinates:
        print("Error: No land coordinates found in the generated map. Cannot place objects.")
        sys.exit(1)

    # 2. Validate Abstract Entities (Optional but good practice)
    print("\nStep 2: Validating abstract entities...")
    try:
        validated_abstract_entities = [AbstractEntity(**entity) for entity in ABSTRACT_ENTITIES_DATA]
        print("Abstract entities structure appears valid.")
    except ValidationError as e:
         print(f"Error: Abstract entities data validation failed: {e}")
         sys.exit(1)

    # 3. Construct the input JSON string for the LLM
    print("\nStep 3: Constructing input payload for LLM...")
    # Use the simplified map info format
    input_payload_dict = {
        "map_info": {
            "width": map_land_obj.width,
            "height": map_land_obj.height,
            "land_coordinates": land_coordinates # Send coordinates, not the grid
        },
        "abstract_entities": [entity.model_dump() for entity in validated_abstract_entities] # Send validated data
    }
    try:
        # Use compact JSON for potentially smaller payload size
        input_data_string = json.dumps(input_payload_dict, separators=(',', ':'))
        # print("\n--- Input String for LLM (compact) ---")
        # print(input_data_string[:500] + "..." if len(input_data_string) > 500 else input_data_string) # Print snippet
        # print("--- End Input String ---\n")
    except Exception as e:
        print(f"Error constructing input JSON string: {e}")
        sys.exit(1)

    # 4. Run the agent
    print("\nStep 4: Running the Agent via OpenAI...")
    try:
        # Pass API key and the constructed input string to the runner
        runner = AgentRunner(
            openai_api_key=args.openai_key,
            input_data_str=input_data_string
        )
        # The run method now returns only List[RealObject]
        generated_objects: List[RealObject] = runner.run()
        print(f"Agent successfully generated {len(generated_objects)} objects.")

    except (ValueError, openai.APIError, ValidationError) as e: # Catch validation errors here too
        print(f"\nError running agent: {e}")
        sys.exit(1) # Exit on agent errors
    except Exception as e:
        print(f"\nAn unexpected critical error occurred during agent execution: {e}")
        sys.exit(1) # Exit on unexpected errors

    # 5. Construct final OutputData
    print("\nStep 5: Assembling final output...")
    final_output = OutputData(
        map_land=OutputMapLand( # Use the original map data stored earlier
             width=map_land_obj.width,
             height=map_land_obj.height,
             grid=map_land_obj.grid # Include the full grid in the final output
        ),
        real_objects=generated_objects # Use the objects generated by the LLM
    )

    print("\n--- Generated World Data ---")
    # Use model_dump_json for clean, Pydantic-aware JSON output
    print(final_output.model_dump_json(indent=2))
    print("--- End Generated World Data ---")

    overall_time = time.time() - overall_start_time
    print(f"\nTotal execution time: {overall_time:.2f} seconds")

if __name__ == "__main__":
    main()