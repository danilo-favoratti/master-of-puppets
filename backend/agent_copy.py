import json
import os
import asyncio
from typing import List, Dict, Any, Tuple, Optional

# Use typing_extensions for TypedDict if Python < 3.12 for Pydantic v2
from typing_extensions import TypedDict

# Pydantic is highly recommended for defining input/output schemas
from pydantic import BaseModel, Field, RootModel, create_model, ValidationError


# Placeholder for OpenAI Client - Replace with actual import
# from openai import AsyncOpenAI # Or OpenAI for synchronous
# client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# --- Placeholder OpenAI Client and Structures ---
# Replace these with actual OpenAI SDK components when available/used
class PlaceholderClient:
    def __init__(self):
        self.beta = self._Beta()

    class _Beta:
        def __init__(self):
            self.threads = self._Threads()
            self.assistants = self._Assistants()

    class _Assistants:
        async def create(self, *, name, instructions, model, response_format=None, tools=None):
            print(f"--- MOCK ASSISTANT CREATE ---")
            print(f"Name: {name}")
            print(f"Model: {model}")
            print(f"Instructions (preview): {instructions[:200]}...")
            print(f"Response Format: {response_format}")
            print(f"-----------------------------")
            # Return a mock assistant object with an ID
            return type('MockAssistant', (object,), {'id': 'asst_mock_123'})()

    class _Threads:
        async def create_and_run(self, *, assistant_id, thread, model=None):
            print(f"--- MOCK THREAD CREATE & RUN ---")
            print(f"Assistant ID: {assistant_id}")
            # In a real scenario, 'thread' would contain user messages
            user_message = thread.get("messages", [{}])[0].get("content", "No user message provided")
            print(f"User Message (part of thread): {user_message}")
            print(f"-------------------------------")

            # --- MOCK LLM RESPONSE GENERATION ---
            # Simulate the LLM generating JSON based on the assistant's instructions
            # THIS IS WHERE THE ACTUAL LLM MAGIC HAPPENS IN THE REAL SDK
            # We'll generate placeholder valid JSON matching the requested schema
            mock_response_json = self._generate_mock_story_output()
            # ------------------------------------

            # Return a mock run object that includes the simulated response
            # In the real SDK, you'd poll the run status and then retrieve messages
            mock_run = type('MockRun', (object,), {
                'id': 'run_mock_456',
                'status': 'completed',  # Assume immediate completion for mock
                # Simulate storing the result accessible later
                '_mock_result_json': json.dumps(mock_response_json)
            })()
            return mock_run

        async def retrieve(self, *, thread_id, run_id):
            # Allows fetching the mock run object created above
            print(f"--- MOCK THREAD RETRIEVE (Run) ---")
            print(f"Thread ID: {thread_id}, Run ID: {run_id}")
            # In this mock, we just return a completed run object immediately
            # Normally you'd poll until status is 'completed'
            print(f"----------------------------------")
            # Return a dummy object with status, assuming we don't need the _mock_result_json here
            # In a real flow you might retrieve *messages* added by the run instead
            return type('MockRunStatus', (object,), {'id': run_id, 'status': 'completed'})()

        async def list_messages(self, thread_id, *, limit=1, order='desc'):
            print(f"--- MOCK THREAD LIST MESSAGES ---")
            print(f"Thread ID: {thread_id}")
            # Simulate retrieving the *last* message added by the assistant run
            # In the real SDK, this message contains the LLM's response
            mock_run_result = self._get_mock_run_result()  # Helper to get the stored JSON
            print(f"---------------------------------")
            mock_message = type('MockMessage', (object,), {
                'id': 'msg_mock_789',
                'role': 'assistant',
                'content': [
                    type('MockTextContent', (object,), {
                        'type': 'text',
                        'text': type('MockTextValue', (object,), {'value': mock_run_result})()
                    })()
                ]
            })()
            return type('MockMessageList', (object,), {'data': [mock_message]})()

        # Helper methods for mock response generation/retrieval
        _MOCK_RUN_RESULT_JSON = None

        def _generate_mock_story_output(self):
            # Generate data matching GeneratedStoryOutput structure
            output = {
                "creative_environment_description": "Mock description: The salty air hangs heavy around the creaking, half-submerged wreckage.",
                "entity_instances": [
                    {
                        "id": "chest-1",  # Assembler might regenerate this later
                        "type": "chest",
                        "name": "Waterlogged Chest",
                        "description": "A barnacle-encrusted wooden chest, half-stuck in the sand.",
                        "position": [1, 1],  # Example valid land position from input grid
                        "state": "locked",
                        "variant": "wooden",
                        # Add other required fields from EntityInstance Pydantic model
                        "weight": 50,
                        "possible_actions": ["examine", "unlock", "destroy"]  # Subset based on library
                    },
                    {
                        "id": "rock-1",
                        "type": "rock",
                        "name": "Jagged Rock",
                        "description": "A sharp rock sticking out of the water.",
                        "position": [0, 3],  # Example valid water/edge position
                        "state": "unbroken",
                        "variant": "medium",
                        "weight": 100,
                        "possible_actions": ["examine", "climb_on"]  # LLM creatively adds/chooses actions
                    }
                    # Add more mock entities (20-30 total)
                ],
                "quest": {
                    "title": "Mock Quest: Escape the Wreckage",
                    "description": "Find a way off this makeshift island.",
                    "objectives": [
                        {
                            "id": "obj-1",  # Assembler might regenerate later
                            "description": "Find the key to the Waterlogged Chest.",
                            "related_entity_ids": ["chest-1"],  # Refers to instance IDs above
                            "completion_state_description": "Player obtains 'key-1' (assuming key is another entity)"
                        },
                        {
                            "id": "obj-2",
                            "description": "Open the Waterlogged Chest.",
                            "related_entity_ids": ["chest-1"],
                            "completion_state_description": "'chest-1' state is 'unlocked' or 'open'"
                        }
                        # Add more mock objectives (4-9 total)
                    ]
                }
            }
            # Store it for retrieval by list_messages mock
            self._MOCK_RUN_RESULT_JSON = json.dumps(output)
            return output  # create_and_run expects the object, list_messages the string

        def _get_mock_run_result(self):
            return self._MOCK_RUN_RESULT_JSON or "{}"  # Return stored JSON string


# Instantiate the Mock Client
client = PlaceholderClient()


# -----------------------------------------------------


# --- Input Data Structures (Pydantic Models) ---
class EnvironmentInput(BaseModel):
    width: int
    height: int
    grid: List[List[int]]  # 0=?, 1=Land, 2=Water


class EntityLibraryItem(BaseModel):
    type: str
    possible_states: Optional[List[str]] = None
    possible_actions: Optional[List[str]] = None
    variants: Optional[List[str]] = None
    can_be_at_water: bool = False
    can_be_at_land: bool = True
    might_be_movable: bool = False
    might_be_jumpable: bool = False
    might_be_used_alone: bool = False
    is_container: bool = False
    is_collectable: bool = False
    is_wearable: bool = False
    # Add weight ranges or default weights if needed?


class GameInputData(BaseModel):
    theme: str
    environment: EnvironmentInput
    entities_library: List[EntityLibraryItem]


# --- Output Data Structures (Pydantic Models) ---
# Defines the structure the AI Agent should generate

class EntityInstance(BaseModel):
    # Note: The AI generates instance data. Final ID might be reassigned later if needed.
    id: str = Field(...,
                    description="Unique identifier for this specific entity instance (e.g., 'chest-1', 'rock-area-3').")
    type: str = Field(..., description="Entity type, must exist in the provided entities_library.")
    name: str = Field(..., description="Creative name for this specific instance, fitting the theme.")
    description: str = Field(..., description="Creative description for this specific instance, fitting the theme.")
    position: Tuple[int, int] = Field(...,
                                      description="Coordinates [x, y] where the entity is placed. Must be valid based on environment grid and entity's land/water capability.")
    state: Optional[str] = Field(None,
                                 description="Initial state of the entity instance (e.g., 'locked', 'unbroken'). Must be one of the 'possible_states' from the library for this type.")
    variant: Optional[str] = Field(None,
                                   description="Specific variant chosen for this instance (e.g., 'wooden', 'metal', 'small'). Must be one of the 'variants' from the library for this type.")
    weight: Optional[int] = Field(None,
                                  description="Specific weight for this instance (optional, can be estimated based on type/variant).")
    possible_actions: Optional[List[str]] = Field(None,
                                                  description="Specific actions applicable to this instance, likely a subset of library actions or potentially new creative ones.")
    # Add other relevant instance properties if needed (e.g., contained items for containers)


class ObjectiveOutput(BaseModel):
    # Note: The AI generates objective data. Final ID might be reassigned later.
    id: str = Field(..., description="Unique identifier for this objective (e.g., 'obj-1', 'find-key').")
    description: str = Field(..., description="Clear description of what the player needs to achieve.")
    related_entity_ids: List[str] = Field(...,
                                          description="List of entity instance 'id' values involved in this objective.")
    completion_state_description: str = Field(...,
                                              description="Describes the condition that marks this objective as complete (e.g., 'Player has item key-1', 'chest-1 state is open').")


class QuestOutput(BaseModel):
    title: str = Field(..., description="Creative title for the overall quest, fitting the theme.")
    description: str = Field(..., description="Brief overall description of the quest.")
    objectives: List[ObjectiveOutput] = Field(..., min_length=4, max_length=9, description="List of 4 to 9 objectives.")


class GeneratedStoryOutput(BaseModel):
    """
    The complete structured output expected from the AI copywriter agent.
    """
    creative_environment_description: str = Field(...,
                                                  description="A paragraph describing the environment creatively, based on the theme and grid.")
    entity_instances: List[EntityInstance] = Field(..., min_length=20, max_length=30,
                                                   description="List of 20 to 30 specific entity instances placed in the environment.")
    quest: QuestOutput = Field(..., description="The generated quest structure.")


# --- Helper to Format Input for Prompt ---
def format_input_for_prompt(data: GameInputData) -> str:
    """Formats the input data into a string suitable for the LLM prompt."""

    # Summarize grid concisely
    land_coords = []
    water_coords = []
    for y, row in enumerate(data.environment.grid):
        for x, cell in enumerate(row):
            if cell == 1:
                land_coords.append(f"({x},{y})")
            elif cell == 2:
                water_coords.append(f"({x},{y})")

    grid_summary = f"Environment Grid ({data.environment.width}x{data.environment.height}):\n"
    grid_summary += f"  Land at: {', '.join(land_coords) if land_coords else 'None'}\n"
    grid_summary += f"  Water at: {', '.join(water_coords) if water_coords else 'None'}\n"
    # Could add more sophisticated summary (e.g., contiguous areas) if needed

    library_summary = "Available Entity Types (Library):\n"
    for item in data.entities_library:
        library_summary += f"- Type: {item.type}\n"
        library_summary += f"  - States: {item.possible_states}\n"
        library_summary += f"  - Actions: {item.possible_actions}\n"
        library_summary += f"  - Variants: {item.variants}\n"
        library_summary += f"  - Placement: {'Land' if item.can_be_at_land else ''}{'/' if item.can_be_at_land and item.can_be_at_water else ''}{'Water' if item.can_be_at_water else ''}\n"
        # Add other flags concisely if important context
        library_summary += f"  - Properties: {'Movable ' if item.might_be_movable else ''}{'Jumpable ' if item.might_be_jumpable else ''}{'UsableAlone ' if item.might_be_used_alone else ''}{'Container ' if item.is_container else ''}{'Collectable ' if item.is_collectable else ''}{'Wearable ' if item.is_wearable else ''}\n"

    prompt_context = f"""
Theme: {data.theme}

{grid_summary}
{library_summary}
"""
    return prompt_context


# --- Main Agent Function ---
async def generate_story_from_input(input_data: GameInputData, llm_model: str = "gpt-4-turbo") -> GeneratedStoryOutput:
    """
    Uses an AI Agent (conceptual OpenAI Assistant) to generate game story elements.
    """
    print("Step 1: Formatting input data for the agent prompt...")
    prompt_context = format_input_for_prompt(input_data)

    print("Step 2: Defining the system prompt and desired output structure...")
    system_prompt = f"""You are a creative game story copywriter AI. Your task is to generate key story elements for a game based on the provided theme, environment layout, and available entity types.

You MUST follow these instructions:
1.  Read the provided Theme, Environment Grid Summary, and Available Entity Types (Library) context carefully.
2.  Generate a creative, engaging paragraph describing the environment based on the Theme and grid layout.
3.  Generate a list of exactly 20 to 30 specific `entity_instances`.
    - Each instance must have a unique `id` (you can create temporary ones like 'chest-1', 'rock-area-3').
    - Each instance must have a `type` from the provided Library.
    - Give each instance a creative `name` and `description` fitting the Theme.
    - Choose a valid `position` [x, y] based on the Environment Grid and the entity type's `can_be_at_land`/`can_be_at_water` properties from the Library. Coordinates must be within the grid dimensions (0 to width-1, 0 to height-1).
    - Choose an appropriate initial `state` and `variant` for each instance from the possibilities listed in the Library for its type.
    - Assign reasonable `weight` and `possible_actions` (can be a subset from the library or creative additions).
4.  Generate a `quest` structure containing:
    - A creative `title` and `description` fitting the Theme.
    - A list of exactly 4 to 9 `objectives`.
    - Each objective must have a unique `id` (e.g., 'obj-1'), a clear `description`, a list of `related_entity_ids` (referencing the `id`s of the entity instances you generated), and a `completion_state_description`.
5.  You MUST output ONLY a single JSON object adhering strictly to the specified format. Do not include any explanatory text before or after the JSON.

Context:
{prompt_context}

Output Format (JSON Schema derived from Pydantic model):
{GeneratedStoryOutput.model_json_schema(indent=2)}
"""

    # Define the response format using the Pydantic model's schema
    # This tells the OpenAI API to *try* and return JSON matching this structure
    # Requires a compatible model like gpt-4-turbo, gpt-3.5-turbo-0125+
    response_format_spec = {
        "type": "json_object",
        "schema": GeneratedStoryOutput.model_json_schema()
    }

    try:
        print(f"Step 3: Creating/Configuring the AI Assistant (Using Model: {llm_model})...")
        # In a real app, you might retrieve an existing assistant ID
        assistant = await client.beta.assistants.create(
            name="Game Story Copywriter Agent",
            instructions=system_prompt,
            model=llm_model,
            # Use the Tool/Function calling equivalent if directly calling ChatCompletions
            # For Assistants API v2+, response_format is top-level during run creation/modification
            # For older versions or direct ChatCompletions, it might be elsewhere.
            # This mock assumes it's part of assistant creation for simplicity.
            response_format=response_format_spec
        )
        assistant_id = assistant.id
        print(f"Assistant created/configured with ID: {assistant_id}")

        print("Step 4: Creating a thread and running the assistant...")
        # The user message could be simple, as context is in the system prompt
        user_message_content = f"Generate the game story elements based on the provided context for the theme: '{input_data.theme}'."

        # Assistants API v2 uses `create_and_run`
        run = await client.beta.threads.create_and_run(
            assistant_id=assistant_id,
            thread={  # Thread creation parameters
                "messages": [
                    {"role": "user", "content": user_message_content}
                ]
            },
            # Model override if needed, response_format can also be specified here in v2+
            # model=llm_model,
            # response_format=response_format_spec # Specify here for v2+
        )
        thread_id = run.thread_id  # Assuming create_and_run returns this in v2+
        run_id = run.id
        print(f"Run initiated with ID: {run_id} in Thread: {thread_id}")

        # Step 5: Poll for Run completion (Conceptual - Mock completes instantly)
        # while run.status in ['queued', 'in_progress', 'cancelling']:
        #     await asyncio.sleep(1) # Wait 1 second
        #     run = await client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        #     print(f"Run status: {run.status}")
        # This mock skips polling as status is set to 'completed' immediately

        # Check final run status (using retrieve for the mock)
        run_status_check = await client.beta.threads.retrieve(thread_id=thread_id, run_id=run_id)
        if run_status_check.status == 'completed':
            print("Step 6: Run completed. Retrieving the assistant's response...")
            messages = await client.beta.threads.list_messages(
                thread_id=thread_id, limit=1, order='desc'  # Get the latest message
            )

            if messages.data and messages.data[0].role == 'assistant':
                assistant_response_content = messages.data[0].content[0].text.value
                print("Step 7: Parsing and validating the response...")
                try:
                    # Parse the JSON string response
                    parsed_json = json.loads(assistant_response_content)
                    # Validate against the Pydantic model
                    validated_output = GeneratedStoryOutput.model_validate(parsed_json)
                    print("Response successfully parsed and validated.")
                    return validated_output
                except json.JSONDecodeError as e:
                    print(f"ERROR: Failed to decode JSON response: {e}")
                    print(f"Raw Response: {assistant_response_content}")
                    raise ValueError("AI response was not valid JSON.") from e
                except ValidationError as e:
                    print(f"ERROR: Response JSON does not match the expected structure: {e}")
                    print(f"Raw Response: {assistant_response_content}")
                    raise ValueError("AI response structure validation failed.") from e
            else:
                raise ValueError("Could not retrieve a valid assistant message.")

        else:
            print(f"ERROR: Run failed or was cancelled. Status: {run.status}")
            # You might want to check run.last_error here in a real scenario
            raise RuntimeError(f"Assistant run failed with status: {run.status}")

    except Exception as e:
        print(f"An error occurred during AI agent execution: {e}")
        raise  # Re-raise the exception


# --- Example Usage ---
async def main():
    # Load input data from JSON example
    input_json_str = """
{
    "theme": "Abandoned Shipwreck on a Tiny Island",
    "environment": {
        "width": 5,
        "height": 5,
        "grid": [
            [2, 2, 2, 2, 2],
            [2, 2, 1, 2, 2],
            [2, 1, 1, 1, 2],
            [2, 2, 1, 2, 2],
            [2, 2, 2, 2, 2]
        ]
    },
    "entities_library": [
        {
            "type": "chest",
            "possible_states": ["locked", "unlocked", "empty", "broken"],
            "possible_actions": ["examine", "unlock", "open", "close", "kick", "destroy"],
            "variants": ["wooden", "metal", "ornate"],
            "can_be_at_water": false,
            "can_be_at_land": true,
            "might_be_movable": true,
            "might_be_jumpable": false,
            "might_be_used_alone": false,
            "is_container": true,
            "is_collectable": false,
            "is_wearable": false
        },
        {
            "type": "rock",
            "possible_states": ["normal", "cracked", "mossy"],
            "possible_actions": ["examine", "climb", "push", "break"],
            "variants": ["small", "medium", "large", "sharp"],
            "can_be_at_water": true,
            "can_be_at_land": true,
            "might_be_movable": true,
            "might_be_jumpable": true,
            "might_be_used_alone": true,
            "is_container": false,
            "is_collectable": true,
            "is_wearable": false
        },
        {
            "type": "driftwood",
            "possible_states": ["whole", "broken"],
            "possible_actions": ["examine", "take", "break", "use"],
            "variants": ["log", "plank", "branch"],
            "can_be_at_water": true,
            "can_be_at_land": true,
            "might_be_movable": true,
            "might_be_jumpable": false,
            "might_be_used_alone": true,
            "is_container": false,
            "is_collectable": true,
            "is_wearable": false
        }
        // Add more library items...
    ]
}
"""
    try:
        input_data_dict = json.loads(input_json_str)
        input_data_model = GameInputData.model_validate(input_data_dict)

        print("Input data loaded and validated.")
        print("-" * 30)

        # Set the desired LLM model (needs to support JSON mode / function calling / response_format)
        # model = "gpt-4-turbo-preview" # Or gpt-4-turbo, gpt-3.5-turbo-0125+
        model = "gpt-4o"  # Use latest compatible model

        generated_story = await generate_story_from_input(input_data_model, llm_model=model)

        print("-" * 30)
        print("Successfully generated story elements:")
        print("-" * 30)
        # Output the result (Pydantic model can be easily converted to dict/JSON)
        print(json.dumps(generated_story.model_dump(), indent=2))

    except (json.JSONDecodeError, ValidationError) as e:
        print(f"Error processing input JSON: {e}")
    except Exception as e:
        print(f"An error occurred in the main execution: {e}")


if __name__ == "__main__":
    # Ensure OPENAI_API_KEY environment variable is set for real execution
    # if not os.environ.get("OPENAI_API_KEY"):
    #     print("Warning: OPENAI_API_KEY environment variable not set. Using mock client.")
    # else:
    #     print("OPENAI_API_KEY found. Replace mock client with actual OpenAI client.")

    # Replace PlaceholderClient with actual OpenAI client if needed:
    # client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    asyncio.run(main())