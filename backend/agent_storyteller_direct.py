import json
import logging
import os
import traceback
from typing import Dict, Any, Tuple, Awaitable, Callable, List, Optional

# Added for schema debugging
from pydantic.json_schema import models_json_schema

from agent_puppet_master import GameState

# Third-party imports (ensure versions are compatible)
try:
    from agents import Agent, Runner, function_tool, \
        RunContextWrapper
except ImportError:
    print("\nERROR: Could not import 'agents'.")
    print("Please ensure the OpenAI Agents SDK is installed correctly.")
    raise
try:
    from openai import OpenAI, OpenAIError, BadRequestError  # Import BadRequestError explicitly
    from pydantic import BaseModel, Field, ValidationError
except ImportError:
    print("\nERROR: Could not import 'openai' or 'pydantic'.")
    print("Please install them (`pip install openai pydantic`).")
    raise
try:
    from deepgram import (
        DeepgramClient,
        PrerecordedOptions,
        FileSource
    )
except ImportError:
    print("\nERROR: Could not import 'deepgram'.")
    print("Please install it (`pip install deepgram-sdk`).")
    raise

# Local imports
try:
    from agent_copywriter_direct import CompleteStoryResult
except ImportError:
    print("\nERROR: Could not import 'CompleteStoryResult'.")
    print("Ensure the class definition is accessible (e.g., in 'agent_copywriter_direct.py').")
    raise

# --- Configuration ---
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = logging.DEBUG if DEBUG_MODE else logging.INFO
DEFAULT_VOICE = "nova"

# --- Logging Setup ---
root_logger = logging.getLogger()
if root_logger.hasHandlers():
    root_logger.handlers.clear()

logging.basicConfig(level=LOG_LEVEL,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
if DEBUG_MODE:
    logger.info("Debug mode enabled.")


# --- Pydantic Models for Storyteller Output ---

class Answer(BaseModel):
    """Represents a single piece of dialogue or interaction option."""
    # ***** FIX 2: Use Ellipsis (...) to explicitly mark as required *****
    type: str = Field(..., description="The type of answer, MUST be 'text'.")
    description: str = Field(
        ...,
        description="Text message with a maximum of 20 words."
    )
    options: List[str] = Field(
        default_factory=list,
        description="List of options, each with a maximum of 5 words."
    )
    isThinking: Optional[bool] = Field(None, description="Indicates if the agent is processing in the background.")


class AnswerSet(BaseModel):
    """The required JSON structure for all storyteller responses."""
    answers: List[Answer]
    model_config = {
        "json_schema_extra": {
            "example": {
                "answers": [
                    {"type": "text", "description": "The salty air whips around you.", "options": []},
                    {"type": "text", "description": "What will you do?", "options": ["Look around", "Check map"]}
                ]
            }
        }
    }


# --- Storyteller Agent Class ---

class StorytellerAgent:
    # __init__ and other methods remain largely the same as previous correct version
    def __init__(
            self,
            puppet_master_agent: Agent,
            complete_story_result: CompleteStoryResult,
            openai_api_key: Optional[str] = None,
            deepgram_api_key: Optional[str] = None,
            voice: Optional[str] = None
    ):
        logger.debug("Initializing StorytellerAgent.")
        self.openai_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.deepgram_key = deepgram_api_key or os.getenv("DEEPGRAM_API_KEY")
        self.voice = voice or os.getenv("CHARACTER_VOICE") or DEFAULT_VOICE

        if not self.openai_key:
            raise ValueError("OpenAI API key is required.")
        if not self.deepgram_key:
            raise ValueError("Deepgram API key is required.")

        try:
            self.openai_client = OpenAI(api_key=self.openai_key)
            logger.info("Initialized OpenAI client.")
        except Exception as e:
            logger.critical(f"Failed to initialize OpenAI client: {e}", exc_info=True)
            raise

        try:
            self.deepgram_client = DeepgramClient(api_key=self.deepgram_key)
            logger.info("Initialized Deepgram client.")
        except Exception as e:
            logger.critical(f"Failed to initialize Deepgram client: {e}", exc_info=True)
            raise

        if not isinstance(complete_story_result, CompleteStoryResult):
            logger.error(
                f"Invalid complete_story_result type: {type(complete_story_result)}. Expected CompleteStoryResult.")
            env_error_state = {"width": 0, "height": 0, "grid": []}
            self.game_context = CompleteStoryResult(
                theme="Error", environment=env_error_state,
                terrain_description="Error loading story", entity_descriptions={},
                narrative_components={}, entities=[], complete_narrative="",
                error="Invalid story data provided to StorytellerAgent."
            )
        else:
            self.game_context: CompleteStoryResult = complete_story_result
            logger.info(f"Game context loaded with theme: '{self.game_context.theme}'.")
            if self.game_context.error:
                logger.warning(f"Loaded game context contains an error: {self.game_context.error}")

        self.puppet_master_agent = puppet_master_agent
        logger.debug("Puppet master agent stored.")

        self.agent_data = self.setup_agent(self.game_context)
        logger.debug("Storyteller agent setup completed.")

    def setup_agent(self, story_context: CompleteStoryResult) -> Dict[str, Agent]:
        logger.debug("Setting up Storyteller agent persona and tools.")
        theme = getattr(story_context, 'theme', 'Unknown Theme')
        quest_title = "the main quest"
        if isinstance(story_context.narrative_components, dict):
            quest_data = story_context.narrative_components.get('quest', {})
            if isinstance(quest_data, dict):
                quest_title = quest_data.get('title', quest_title)

        system_prompt = f"""
# MISSION
You are Jan "The Man", a funny, ironic, non-binary video game character with a witty personality and deep storytelling skills. Guide the user through the game using the pre-generated story information provided in the context (a CompleteStoryResult object).

# CONTEXT
The game world is pre-defined in the `CompleteStoryResult` context object, containing:
- `theme`: "{theme}"
- `environment`: Map grid and dimensions.
- `entities`: List of all objects and their properties/positions.
- `entity_descriptions`: Descriptions for various entity types/states.
- `narrative_components`: Includes 'intro', 'quest' details (Title: '{quest_title}'), and 'interactions'.
- `complete_narrative`: An overall summary text (use for flavor, not primary state).

# INSTRUCTIONS
- **Game Interaction:** Use the provided `CompleteStoryResult` context to understand the world state and guide the player. Use the `interact_char` tool to perform player actions (move, examine, use items, etc.).
- **Dialogue:** Respond ONLY in brief, entertaining text messages (max 20 words per message). Be witty and slightly sarcastic like Jan.
- **Format:** EVERY response MUST be a JSON object conforming to the `AnswerSet` schema:
  ```json
  {{
    "answers": [
      {{ "type": "text", "description": "<TEXT MESSAGE MAX 20 WORDS>", "options": [] }},
      {{ "type": "text", "description": "<TEXT MESSAGE MAX 20 WORDS>", "options": ["<OPTION MAX 5 WORDS>"] }}
    ]
  }}
  ```
  - Ensure the 'type' field in each answer is ALWAYS the string 'text'. Do NOT omit it or use other values.
  - Provide 1-3 answers per response.
  - Include relevant action options (max 5 words each) where appropriate.
- **Gameplay Loop:**
  1. Start by using the `narrative_components.intro` from the context.
  2. Ask the user what they want to do, providing options based on the current situation and available `interact_char` actions.
  3. Use the `interact_char` tool to execute the user's chosen action. The tool will update the game state (you'll see results in subsequent turns).
  4. Describe the outcome based on the tool's result and the context.
  5. Check quest progress (using `narrative_components.quest` objectives and entity states) implicitly. Guide the player towards the quest '{quest_title}'.
  6. **Ending:** When the quest objectives seem fulfilled (based on context and interaction results), announce it was all a test! Say something darkly funny related to the theme "{theme}" will happen now. Output only `{{ "answers": [{{"type": "text", "description": "...", "options":[]}}] }}` and STOP.
- **Style:** Keep it engaging, enthusiastic but cynical, and strictly game-related. Stick to the Jan persona.
- **Restart:** If the user asks to restart, instruct them to refresh the page/app. Output: `{{ "answers": [{{"type": "text", "description": "Wanna start over? Just refresh!", "options":[]}}] }}`

# GAME MECHANICS REFERENCE (From `factory_game` - Use for understanding possibilities)
{self._get_game_mechanics_reference()}
"""
        try:
            storyteller_agent = Agent(
                name="Jan_The_Man_Storyteller",
                instructions=system_prompt,
                tools=[
                    self.puppet_master_agent.as_tool(
                        tool_name="interact_char",
                        tool_description="Performs player actions in the game world (e.g., move N, examine chest, use firewood with campfire, jump log)."
                    )
                ],
                output_type=AnswerSet,
                model="gpt-4o"
            )
            logger.debug("Storyteller agent instance created.")
            return {"agent": storyteller_agent}
        except Exception as e:
            logger.critical(f"Failed to create Storyteller agent instance: {e}", exc_info=True)
            raise

    def _get_game_mechanics_reference(self) -> str:
        # (Content unchanged)
        return """
---
## 1. Interactive Items and Their Factories
... (rest of mechanics) ...
---
"""

    async def transcribe_audio(self, audio_data: bytes) -> str:
        # (Content unchanged from previous version)
        logger.debug("Starting audio transcription process.")
        if not audio_data:
            logger.warning("Received empty audio data for transcription.")
            return ""
        try:
            logger.info(f"Transcribing audio data of size: {len(audio_data)} bytes")
            payload: FileSource = {"buffer": audio_data}
            options = PrerecordedOptions(
                model="nova-2", smart_format=True, punctuate=True,
                intents=False, utterances=False, language="en"
            )
            logger.debug("Deepgram options set for transcription.")
            try:
                response = await self.deepgram_client.listen.asyncrest.v("1").transcribe_file(payload, options,
                                                                                              timeout=30)
                logger.debug("Deepgram transcription request sent.")
            except AttributeError:
                logger.warning("`asyncrest` not found, trying synchronous `prerecorded` method (might block).")
                try:
                    # Use asyncio.to_thread to run sync code in a separate thread
                    response = await asyncio.to_thread(
                        self.deepgram_client.listen.prerecorded.v("1").transcribe_file,
                        payload, options, timeout=30
                    )
                except Exception as sync_err:
                    logger.error(f"Synchronous Deepgram transcription failed: {sync_err}", exc_info=True)
                    return ""
            if response and hasattr(response, 'results') and response.results:
                try:
                    if (hasattr(response.results, 'channels') and response.results.channels and
                            hasattr(response.results.channels[0], 'alternatives') and response.results.channels[
                                0].alternatives):
                        transcription = response.results.channels[0].alternatives[0].transcript
                        if transcription and transcription.strip():
                            logger.info(f"Deepgram transcription: '{transcription}'")
                            return transcription
                        else:
                            logger.warning("Deepgram returned an empty transcript.")
                            return ""
                    else:
                        logger.warning("Deepgram response structure missing expected channels/alternatives.")
                        logger.debug(f"Deepgram raw response results: {response.results}")
                        return ""
                except (IndexError, AttributeError, TypeError, KeyError) as parse_err:
                    logger.error(f"Error parsing Deepgram response: {parse_err}", exc_info=True)
                    logger.debug(f"Deepgram raw response: {response}")
                    return ""
            else:
                logger.warning("No transcription results received from Deepgram or response was empty.")
                logger.debug(f"Deepgram raw response: {response}")
                return ""
        except OpenAIError as api_err:
            logger.error(f"Deepgram API Error: {api_err}", exc_info=True)
            return ""
        except Exception as e:
            logger.error(f"Error during Deepgram transcription: {e}", exc_info=True)
            return ""

    async def process_text_input(
            self,
            user_input: str,
            conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        # (Content unchanged from previous version)
        logger.debug(f"Processing text input: '{user_input}'")
        if conversation_history is None:
            conversation_history = []
        return await self.process_user_input(user_input, conversation_history)

    async def process_audio(
            self,
            audio_data: bytes,
            on_transcription: Callable[[str], Awaitable[None]],
            on_response: Callable[[str], Awaitable[None]],
            on_audio: Callable[[bytes], Awaitable[None]],
            conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[str, Dict[str, Any], List[Dict[str, Any]]]:
        # (Content mostly unchanged from previous version, including error handling and TTS)
        logger.debug("Processing audio input.")
        if conversation_history is None:
            conversation_history = []
        command_info = {"name": "", "params": {}}
        response_text_for_tts = ""

        try:
            # 1. Transcribe Audio
            transcription = await self.transcribe_audio(audio_data)

            if transcription:
                await on_transcription(transcription)
            else:
                logger.warning("Transcription failed or produced empty result.")
                error_response, conversation_history = self._create_error_response(
                    "I couldn't understand that. Could you repeat?", conversation_history
                )
                await on_response(error_response["content"])
                await on_audio(b"__AUDIO_END__")
                return "Transcription failed.", command_info, conversation_history

            # 2. Process Transcription with Agent
            agent_response_data, updated_history = await self.process_user_input(transcription, conversation_history)
            conversation_history = updated_history
            logger.debug(f"Agent response data received: {agent_response_data.get('type')}")

            # 3. Handle Agent Response
            if agent_response_data["type"] == "json":
                json_string = agent_response_data["content"]
                try:
                    await on_response(json_string)
                    logger.info("Sent JSON response content via on_response callback.")
                    json_content = json.loads(json_string)
                    answers = json_content.get("answers", [])
                    response_text_for_tts = " ".join([a.get("description", "") for a in answers if isinstance(a, dict)])
                    response_text_for_tts = response_text_for_tts.strip()
                    logger.debug(f"Text extracted for TTS: '{response_text_for_tts}'")
                    command_info = {"name": "json_response", "params": {}}
                except json.JSONDecodeError:
                    # ... (error handling as before) ...
                    logger.error(f"Invalid JSON received from agent: {json_string}")
                    error_response, conversation_history = self._create_error_response(
                        "Internal error processing response.", conversation_history
                    )
                    await on_response(error_response["content"])
                    response_text_for_tts = ""
                    await on_audio(b"__AUDIO_END__")
                    return "JSON processing error.", command_info, conversation_history
                except Exception as e:
                    # ... (error handling as before) ...
                    logger.error(f"Error handling JSON response: {e}", exc_info=True)
                    error_response, conversation_history = self._create_error_response(
                        f"Error handling response: {e}", conversation_history
                    )
                    await on_response(error_response["content"])
                    response_text_for_tts = ""
                    await on_audio(b"__AUDIO_END__")
                    return "Response handling error.", command_info, conversation_history


            elif agent_response_data["type"] == "command":
                # ... (handling as before) ...
                command_info = {
                    "name": agent_response_data.get("name", "unknown_command"),
                    "params": agent_response_data.get("params", {})
                }
                if "content" in agent_response_data and agent_response_data["content"]:
                    json_string = agent_response_data["content"]
                    try:
                        await on_response(json_string)
                        logger.info(f"Sent command ({command_info['name']}) JSON via on_response.")
                        json_content = json.loads(json_string)
                        answers = json_content.get("answers", [])
                        response_text_for_tts = " ".join(
                            [a.get("description", "") for a in answers if isinstance(a, dict)])
                        response_text_for_tts = response_text_for_tts.strip()
                        logger.debug(f"Text extracted for command TTS: '{response_text_for_tts}'")
                    except json.JSONDecodeError:
                        # ... (error handling as before) ...
                        logger.error(f"Invalid JSON in command content: {json_string}")
                        response_text_for_tts = agent_response_data.get("result", "Action completed.")
                        fallback_resp, _ = self._create_text_response(response_text_for_tts, conversation_history)
                        await on_response(fallback_resp["content"])
                    except Exception as e:
                        # ... (error handling as before) ...
                        logger.error(f"Error handling command JSON: {e}", exc_info=True)
                        response_text_for_tts = agent_response_data.get("result", "Error handling command.")
                        fallback_resp, _ = self._create_text_response(response_text_for_tts, conversation_history)
                        await on_response(fallback_resp["content"])
                else:
                    # ... (handling as before) ...
                    response_text_for_tts = agent_response_data.get("result", "Action performed.")
                    logger.warning(f"Command '{command_info['name']}' missing 'content'. Sending fallback text.")
                    fallback_resp, _ = self._create_text_response(response_text_for_tts, conversation_history)
                    await on_response(fallback_resp["content"])
                logger.info(f"Command executed: {command_info['name']}")

            else:
                # ... (handling as before) ...
                logger.error(f"Unexpected agent response type: {agent_response_data.get('type')}")
                response_text_for_tts = agent_response_data.get('content', "An unexpected response occurred.")
                error_response, conversation_history = self._create_error_response(
                    response_text_for_tts, conversation_history
                )
                await on_response(error_response["content"])
                response_text_for_tts = ""

            # 4. Generate Speech (TTS)
            if response_text_for_tts:
                # ... (TTS generation as before) ...
                logger.debug(f"Generating speech for: '{response_text_for_tts}' using voice '{self.voice}'")
                try:
                    speech_response = await self.openai_client.audio.speech.create(  # Use await
                        model="tts-1", voice=self.voice, input=response_text_for_tts, response_format="mp3"
                    )
                    logger.debug("Streaming TTS audio chunks...")
                    async for chunk in speech_response.aiter_bytes(chunk_size=4096):
                        if chunk:
                            await on_audio(chunk)
                    logger.debug("Finished streaming TTS audio.")
                except OpenAIError as tts_err:
                    logger.error(f"OpenAI TTS Error: {tts_err}", exc_info=True)
                except Exception as e:
                    logger.error(f"Failed to generate or stream TTS: {e}", exc_info=True)
            else:
                logger.warning("No text extracted for TTS generation.")

            await on_audio(b"__AUDIO_END__")  # Ensure marker is sent

            display_text = response_text_for_tts or "No text content in response."
            return display_text, command_info, conversation_history

        except Exception as e:
            # ... (critical error handling as before) ...
            logger.error(f"Critical error in process_audio: {e}", exc_info=True)
            try:
                error_response, conversation_history = self._create_error_response(
                    f"Sorry, a critical error occurred.",
                    conversation_history
                )
                await on_response(error_response["content"])
                await on_audio(b"__AUDIO_END__")
            except Exception as cb_err:
                logger.error(f"Failed to send error response via callback: {cb_err}", exc_info=True)
            return f"Error: {e}", command_info, conversation_history

    async def process_user_input(
            self,
            user_input: str,
            conversation_history: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Core logic to run the user input through the Storyteller agent.
        Includes schema logging for debugging.
        """
        logger.debug(f"Running agent with input: '{user_input}'")
        agent = self.agent_data.get("agent")
        if not agent:
            logger.error("Storyteller agent instance not found in agent_data.")
            return self._create_error_response("Agent not initialized.", conversation_history)

        current_context = self.game_context

        # ***** Debugging: Log the schema Pydantic generates locally *****
        try:
            # Assuming AnswerSet is the top-level model passed as output_type
            # The models_json_schema function expects a list of model types
            schema_tuple = models_json_schema([Answer, AnswerSet], ref_template="{model}")
            generated_schema_defs = schema_tuple[1]  # The second element contains the definitions dictionary
            generated_schema_json = json.dumps(generated_schema_defs, indent=2)
            logger.debug(f"Locally generated schema definitions by Pydantic:\n{generated_schema_json}")

            # Specifically check the 'type' property within 'Answer' definition
            answer_type_def = generated_schema_defs.get('Answer', {}).get('properties', {}).get('type', {})
            logger.debug(f"Locally generated 'Answer.type' definition: {answer_type_def}")
            if 'default' in answer_type_def:
                logger.error("!!!!!! Local schema generation STILL includes 'default' for Answer.type !!!!!!")
            else:
                logger.info("Local schema generation correctly excludes 'default' for Answer.type.")
        except Exception as schema_err:
            logger.error(f"Error generating local schema for debugging: {schema_err}")
        # ***** End Debugging Section *****

        try:
            # Run the agent using the Runner
            run_result = await Runner.run(
                starting_agent=agent,
                input=user_input,
                context=current_context,
            )
            logger.debug("Runner.run completed.")

            # --- Process Agent/Tool Output --- (Same logic as before) ---
            final_output = getattr(run_result, 'final_output', None)
            tool_calls = getattr(run_result, 'tool_calls', [])

            if tool_calls:
                tool_call = tool_calls[0]
                tool_name = getattr(tool_call, 'name', '')
                tool_input = getattr(tool_call, 'input', {})
                tool_output_raw = getattr(tool_call, 'output', "Action completed.")
                tool_output_str = str(tool_output_raw)

                logger.info(f"Tool '{tool_name}' called with input: {tool_input}")
                logger.debug(f"Tool raw output: {tool_output_raw}")

                if tool_name == "interact_char":
                    command_executed = tool_input.get("command", "interaction")
                    if isinstance(final_output, AnswerSet):
                        response_content = final_output.model_dump_json()
                    elif isinstance(final_output, dict) and "answers" in final_output:
                        try:
                            validated_output = AnswerSet.model_validate(final_output)
                            response_content = validated_output.model_dump_json()
                        except (ValidationError, TypeError):
                            response_content = self._create_basic_answer_json(tool_output_str)
                    else:
                        response_content = self._create_basic_answer_json(tool_output_str)

                    response_data = {
                        "type": "command", "name": command_executed.split()[0] if command_executed else tool_name,
                        "result": tool_output_str, "content": response_content, "params": tool_input
                    }
                    return response_data, conversation_history
                else:
                    logger.warning(f"Unhandled tool call: {tool_name}.")
                    final_output = f"Tool {tool_name} executed: {tool_output_str}"

            # Handle Direct Agent Output
            if isinstance(final_output, AnswerSet):
                response_content = final_output.model_dump_json()
                response_type = "json"
            elif isinstance(final_output, dict) and "answers" in final_output:
                try:
                    validated_output = AnswerSet.model_validate(final_output)
                    response_content = validated_output.model_dump_json()
                    response_type = "json"
                except (ValidationError, TypeError):
                    response_content = self._create_basic_answer_json(str(final_output))
                    response_type = "json"
            elif isinstance(final_output, str):
                response_content = self._create_basic_answer_json(final_output)
                response_type = "json"
            elif final_output is None and not tool_calls:
                logger.error("Agent returned None and no tool calls were made.")
                return self._create_error_response("Agent did not respond.", conversation_history)
            else:
                logger.error(f"Unexpected agent final_output type: {type(final_output)}. Value: {final_output!r}")
                response_content = self._create_basic_answer_json("I'm a bit confused right now.")
                response_type = "json"

            response_data = {"type": response_type, "content": response_content}
            return response_data, conversation_history

        except BadRequestError as api_err:  # Catch specific error
            logger.error(f"OpenAI API BadRequestError during agent run: {api_err}", exc_info=True)
            error_detail = api_err.body.get('error', {}).get('message', '') if api_err.body else str(api_err)
            logger.error(f"BadRequest Details: {error_detail}")
            # Check if it's still the schema error
            if "'default' is not permitted" in error_detail:
                logger.critical(
                    "SCHEMA ERROR PERSISTS: API rejected schema containing 'default'. Check local schema log above.")
                return self._create_error_response(f"Internal schema configuration error. Please report this.",
                                                   conversation_history)
            else:
                return self._create_error_response(f"API request error: {error_detail}", conversation_history)
        except OpenAIError as api_err:
            logger.error(f"OpenAI API error during agent run: {api_err}", exc_info=True)
            return self._create_error_response(f"API Error: {api_err}", conversation_history)
        except Exception as e:
            logger.error(f"Error processing user input: {e}", exc_info=True)
            return self._create_error_response(f"Oops! An internal error occurred.", conversation_history)

    def _create_basic_answer_json(self, text: str, options: Optional[List[str]] = None) -> str:
        # (Content unchanged from previous version)
        if not text or text.strip() == "": text = "Okay, what next?"
        words = text.split()
        max_words = 20
        answers_list_text = []
        current_chunk = []
        word_count = 0
        for word in words:
            current_chunk.append(word)
            word_count += 1
            if word_count >= max_words:
                answers_list_text.append(" ".join(current_chunk))
                current_chunk = []
                word_count = 0
        if current_chunk: answers_list_text.append(" ".join(current_chunk))
        if not answers_list_text: answers_list_text.append("What should we do?")
        final_answers = []
        for i, desc in enumerate(answers_list_text):
            ans_options = options if i == len(answers_list_text) - 1 else []
            ans_options = [(opt[:25].strip() + ('...' if len(opt) > 25 else ''))
                           for opt in (ans_options or []) if opt.strip()][:3]
            # Ensure type is explicitly 'text'
            final_answers.append(Answer(type="text", description=desc.strip(), options=ans_options))
        answer_set = AnswerSet(answers=final_answers)
        return answer_set.model_dump_json()

    def _create_error_response(self, error_message: str, history: List[Dict[str, Any]]) -> Tuple[
        Dict[str, Any], List[Dict[str, Any]]]:
        # (Content unchanged from previous version)
        logger.warning(f"Creating error response: {error_message}")
        error_json_content = self._create_basic_answer_json(
            f"Jan says: Yikes! {error_message}", options=["Try again", "Help?"]
        )
        response_data = {"type": "json", "content": error_json_content}
        return response_data, history

    def _create_text_response(self, text_message: str, history: List[Dict[str, Any]]) -> Tuple[
        Dict[str, Any], List[Dict[str, Any]]]:
        # (Content unchanged from previous version)
        logger.debug(f"Creating text response: {text_message}")
        json_content = self._create_basic_answer_json(
            text_message, options=["Okay", "What else?"]
        )
        response_data = {"type": "json", "content": json_content}
        return response_data, history


# --- Example Usage (Conceptual) ---
async def example_run():
    # (Content mostly unchanged from previous version, includes Mock Agent)
    print("--- Storyteller Agent Example ---")
    openai_key = os.getenv("OPENAI_API_KEY")
    deepgram_key = os.getenv("DEEPGRAM_API_KEY")
    if not openai_key or not deepgram_key:
        print("❌ Error: OPENAI_API_KEY and DEEPGRAM_API_KEY environment variables must be set.")
        return

    mock_env_dict = {"width": 10, "height": 10, "grid": [[0, 1, 0], [1, 1, 1], [0, 1, 0]]}
    mock_env_to_use = mock_env_dict
    mock_story_result = CompleteStoryResult(
        theme="Mysterious Island Survival", environment=mock_env_to_use,
        terrain_description="A small, dense island.",
        entity_descriptions={"chest_wooden_default": "A simple wooden chest."},
        narrative_components={
            "intro": {"theme": "...", "location": "...", "mood": "...", "intro_text": "You wake up on a beach..."},
            "quest": {"title": "Find Shelter", "description": "...", "objectives": ["Find wood", "Build fire"],
                      "reward": "Safety"}
        },
        entities=[{"id": "ent_1", "type": "chest", "name": "Wooden Chest", "position": {"x": 1, "y": 1}}],
        complete_narrative="You are stranded..."
    )
    print(f"Loaded mock story with theme: {mock_story_result.theme}")

    mock_puppet = Agent[CompleteStoryResult](name="Jan 'The Man'")
    print("Initialized mock puppet master agent.")

    try:
        storyteller = StorytellerAgent(
            puppet_master_agent=mock_puppet, complete_story_result=mock_story_result,
            openai_api_key=openai_key, deepgram_api_key=deepgram_key, voice="nova"
        )
        print("Storyteller agent initialized successfully.")
    except ValueError as e:
        print(f"❌ Error initializing Storyteller: {e}")
        return
    except Exception as e:
        print(f"❌ Unexpected error during Storyteller initialization: {e}")
        traceback.print_exc()
        return

    print("\n--- Simulating Text Interaction ---")
    history = []
    intro_text = mock_story_result.narrative_components.get('intro', {}).get('intro_text', 'The game begins!')
    initial_response_content = storyteller._create_basic_answer_json(intro_text, options=["Look around", "Check map"])
    initial_response = {"type": "json", "content": initial_response_content}
    print(f"Initial Response (JSON): {initial_response['content']}")

    user_inputs = ["Look around", "move North", "examine chest", "try to fail", "restart"]
    for user_input in user_inputs:
        print(f"\n>>> User: {user_input}")
        response_data, history = await storyteller.process_text_input(user_input, history)
        print(f"<<< Jan (JSON): {response_data.get('content', 'Error: No content')}")
        if response_data.get("type") == "command":
            print(f"    (Command Executed: {response_data.get('name')} - Result: {response_data.get('result')})")
        elif response_data.get('content'):
            if "Wanna start over? Just refresh!" in response_data['content']:
                print("    (Restart instruction received)")

    print("\n--- Simulating Audio Interaction (Conceptual) ---")

    async def mock_on_transcription(text):
        print(f"   [Callback] Transcription: {text}")

    async def mock_on_response(json_str):
        print(f"   [Callback] Response JSON: {json_str}")

    async def mock_on_audio(chunk):
        if chunk != b"__AUDIO_END__":
            print(f"   [Callback] Audio Chunk Received ({len(chunk)} bytes)")
        else:
            print(f"   [Callback] __AUDIO_END__ Received")

    dummy_audio_data = b'\x00' * 16000
    print("\nProcessing dummy audio for 'move South'...")
    # text_result, cmd_info, history = await storyteller.process_audio(
    #     dummy_audio_data, mock_on_transcription, mock_on_response, mock_on_audio, history
    # )
    # print(f"   Audio Processing Result Text: {text_result}")
    # print(f"   Audio Processing Command Info: {cmd_info}")
    print("   (Skipping actual audio processing in example for brevity)")


if __name__ == "__main__":
    try:
        import asyncio

        # Ensure asyncio uses the correct event loop policy if needed, e.g. on Windows
        # if os.name == 'nt':
        #      asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(example_run())
    except KeyboardInterrupt:
        print("\n🛑 Execution cancelled by user.")
    except Exception as startup_err:
        print(f"\n❌ FATAL STARTUP ERROR: {startup_err}")
        traceback.print_exc()
