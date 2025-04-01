import json
import logging
import os
import traceback
from prompt.storyteller_prompts import get_storyteller_system_prompt, get_game_mechanics_reference
from agent_copywriter_direct import Environment, Entity, Position

from typing import Dict, Any, Tuple, Awaitable, Callable, List, Optional

# Added for schema debugging
from pydantic.json_schema import models_json_schema

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


def setup_agent(self, story_context: CompleteStoryResult) -> Dict[str, Agent]:
    logger.debug("Setting up Storyteller agent persona and tools.")
    theme = getattr(story_context, 'theme', 'Unknown Theme')
    quest_title = "the main quest"
    if isinstance(story_context.narrative_components, dict):
        quest_data = story_context.narrative_components.get('quest', {})
        if isinstance(quest_data, dict):
            quest_title = quest_data.get('title', quest_title)

    system_prompt = get_storyteller_system_prompt(
        theme=theme,
        quest_title=quest_title,
        game_mechanics_reference=get_game_mechanics_reference()
    )

    try:
        storyteller_agent = Agent(
            name="Jan_The_Man_Storyteller",
            instructions=system_prompt,
            tools=[
                self.puppet_master_agent.as_tool(
                    tool_name="interact_char",
                    tool_description="Performs player actions in the game world (e.g., move, jump, push, pull, get_from_container, put_in_container, use_object_with, look, say, check_inventory, examine_object, execute_movement_sequence)."
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


# --- Storyteller Agent Class ---

class StorytellerAgent:
    # __init__ and other methods remain largely the same as previous correct version
    def __init__(
            self,
            puppet_master_agent: Agent,
            complete_story_result: CompleteStoryResult,
            openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY"),
            deepgram_api_key: Optional[str] = os.getenv("DEEPGRAM_API_KEY"),
            voice: str = "nova"
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
            env_error_state = Environment(width=0, height=0, grid=[])
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

        self.agent_data = setup_agent(self, self.game_context)
        logger.debug("Storyteller agent setup completed.")

    # ***** Debugging: Method to log Pydantic schema locally *****
    def _log_pydantic_schema(self):
        """Logs the schema generated by Pydantic for AnswerSet."""
        try:
            # Pydantic V2 preferred way for a single model, includes referenced definitions
            generated_schema = AnswerSet.model_json_schema(ref_template="{model}")
            generated_schema_json = json.dumps(generated_schema, indent=2)
            logger.debug(f"--- Pydantic Generated Schema for Storyteller Output ---\n{generated_schema_json}")

            # Check the 'type' property within 'Answer' definition in '$defs'
            # Definitions are usually under '$defs' in Pydantic v2 JSON Schema output
            answer_def = generated_schema.get('$defs', {}).get('Answer', {})
            answer_type_def = answer_def.get('properties', {}).get('type', {})

            logger.debug(f"Generated 'Answer.type' definition: {answer_type_def}")
            if 'default' in answer_type_def:
                logger.error(
                    "###### SCHEMA ISSUE: Local Pydantic schema STILL includes 'default' for Answer.type! ######")
            else:
                # This part was accidentally removed in the diff, let's make sure it's here
                logger.info("Schema Check: Local Pydantic schema correctly excludes 'default' for Answer.type.")
            # This part was also accidentally removed
            logger.debug("--- End Pydantic Schema Log ---")

        except Exception as schema_err:
            logger.error(f"Error generating local schema for debugging: {schema_err}", exc_info=True)

    # ***** End Debugging Method *****

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
        logger.info("🎙️ AUDIO PROCESSING START 🎙️")
        logger.info(f"🎙️ Received audio data: {len(audio_data)} bytes")

        if conversation_history is None:
            conversation_history = []
        command_info = {"name": "", "params": {}}
        response_text_for_tts = ""

        try:
            # 1. Transcribe Audio
            logger.info("🎙️ Starting transcription...")
            transcription = await self.transcribe_audio(audio_data)

            if transcription:
                logger.info(f"🎙️ Transcription success: '{transcription}'")
                await on_transcription(transcription)
                logger.info("🎙️ on_transcription callback completed")
            else:
                logger.warning("🎙️ Transcription failed or produced empty result.")
                error_response, conversation_history = self._create_error_response(
                    "I couldn't understand that. Could you repeat?", conversation_history
                )
                logger.info("🎙️ Sending error response to client")
                await on_response(error_response["content"])
                await on_audio(b"__AUDIO_END__")
                logger.info("🎙️ AUDIO PROCESSING COMPLETE (transcription failed) 🎙️")
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
                    if not response_text_for_tts:
                        logger.warning("No text extracted for TTS - check JSON structure: " + json_string[:200])
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
                logger.debug(f"Generating speech for: '{response_text_for_tts}' using voice '{self.voice}'")
                try:
                    # Log TTS request details
                    logger.info("🔊 TTS GENERATION LOG 🔊")
                    logger.info(f"🗣️ VOICE: {self.voice}")
                    logger.info(f"📝 TEXT LENGTH: {len(response_text_for_tts)} characters")
                    logger.info(f"📝 TEXT SAMPLE: {response_text_for_tts[:50]}...")

                    speech_response = await self.openai_client.audio.speech.create(
                        model="tts-1", voice=self.voice, input=response_text_for_tts, response_format="mp3"
                    )

                    # Stream the audio in chunks directly to the client
                    logger.debug("Streaming TTS audio chunks...")
                    collected_audio = bytearray()

                    # Check if openai response changed behavior between versions
                    if hasattr(speech_response, 'iter_bytes'):
                        logger.info("🔊 Using iter_bytes() method for audio streaming")
                        chunk_count = 0
                        total_bytes = 0

                        for chunk in speech_response.iter_bytes(chunk_size=4096):
                            if chunk:
                                chunk_count += 1
                                total_bytes += len(chunk)
                                collected_audio.extend(chunk)
                                await on_audio(chunk)
                                if chunk_count <= 2 or chunk_count % 10 == 0:  # Log first few chunks and every 10th
                                    logger.debug(f"Sent audio chunk #{chunk_count} ({len(chunk)} bytes)")

                        logger.info(f"🔊 AUDIO STREAMING COMPLETE: {chunk_count} chunks, {total_bytes} bytes total")
                    elif hasattr(speech_response, 'content'):
                        # Handle single content response
                        logger.info(f"🔊 Using content attribute for audio: {len(speech_response.content)} bytes")
                        await on_audio(speech_response.content)
                        logger.info("Sent entire audio content in one chunk.")
                    else:
                        # Try to read as a file-like object
                        logger.info("🔊 Attempting to read audio as file-like object")
                        audio_bytes = speech_response.read()
                        if audio_bytes:
                            logger.info(f"🔊 Read {len(audio_bytes)} bytes from file-like object")
                            await on_audio(audio_bytes)

                    logger.info("🔊 END TTS LOG 🔊")
                except OpenAIError as tts_err:
                    logger.error(f"OpenAI TTS Error: {tts_err}", exc_info=True)
                except Exception as e:
                    logger.error(f"Failed to generate or stream TTS: {e}", exc_info=True)
            else:
                logger.warning("No text extracted for TTS generation.")

            # Always send the audio end marker
            logger.debug("Sending __AUDIO_END__ marker")
            await on_audio(b"__AUDIO_END__")  # Ensure marker is sent
            logger.info("🎙️ Sent __AUDIO_END__ marker to client")

            display_text = response_text_for_tts or "No text content in response."
            logger.info(
                f"🎙️ AUDIO PROCESSING COMPLETE: {len(display_text)} chars in response, command: {command_info['name']} 🎙️")
            return display_text, command_info, conversation_history

        except Exception as e:
            # ... (critical error handling as before) ...
            logger.error(f"Critical error in process_audio: {e}", exc_info=True)
            try:
                error_response, conversation_history = self._create_error_response(
                    f"Sorry, a critical error occurred.",
                    conversation_history
                )
                logger.error("🎙️ Sending critical error response to client")
                await on_response(error_response["content"])
                await on_audio(b"__AUDIO_END__")
                logger.info("🎙️ AUDIO PROCESSING COMPLETE (with critical error) 🎙️")
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

        # Log comprehensive agent context for debugging
        logger.info("🔍 AGENT CONTEXT LOG 🔍")
        logger.info(f"🗣️ INPUT: '{user_input}'")
        logger.info(f"🎮 THEME: '{getattr(current_context, 'theme', 'Unknown')}'")

        # Log quest info if available
        quest_info = {}
        if hasattr(current_context, 'narrative_components') and current_context.narrative_components:
            if isinstance(current_context.narrative_components,
                          dict) and 'quest' in current_context.narrative_components:
                quest_info = current_context.narrative_components['quest']
                logger.info(f"📜 QUEST: {quest_info.get('title', 'Unknown Quest')}")
                logger.info(f"🎯 OBJECTIVES: {quest_info.get('objectives', [])}")

        # Log environment details
        env_info = getattr(current_context, 'environment', None)
        if env_info:
            logger.info(f"🗺️ MAP: {getattr(env_info, 'width', '?')}x{getattr(env_info, 'height', '?')}")

        # Log conversation history length
        if conversation_history:
            logger.info(f"💬 HISTORY: {len(conversation_history)} previous messages")

        # Log entity count in the world
        entity_count = len(getattr(current_context, 'entities', []))
        logger.info(f"🧩 ENTITIES: {entity_count} in game world")

        # End context log
        logger.info("🔍 END CONTEXT LOG 🔍")

        # ***** Debugging: Log the schema Pydantic generates locally *****
        try:
            # Pydantic V2 preferred way for a single model, includes referenced definitions
            generated_schema = AnswerSet.model_json_schema(ref_template="{model}")
            generated_schema_json = json.dumps(generated_schema, indent=2)
            logger.debug(f"Locally generated schema definitions by Pydantic:\n{generated_schema_json}")

            # Check the 'type' property within 'Answer' definition in '$defs'
            answer_def = generated_schema.get('$defs', {}).get('Answer', {})
            answer_type_def = answer_def.get('properties', {}).get('type', {})

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

                    # Log command execution for debugging
                    logger.info("🔍 COMMAND EXECUTION LOG 🔍")
                    logger.info(f"⚙️ COMMAND: {command_executed}")
                    logger.info(f"📊 PARAMS: {json.dumps(tool_input, indent=2)[:100]}...")
                    logger.info(f"📋 RESULT: {tool_output_str[:100]}...")

                    # Log command response content
                    try:
                        cmd_response_obj = json.loads(response_content)
                        answers = cmd_response_obj.get("answers", [])
                        if answers:
                            logger.info(f"💬 RESPONSE ANSWERS: {len(answers)} messages")
                            # Show first answer text
                            if answers:
                                logger.info(f"💬 FIRST ANSWER: {answers[0].get('description', '')[:50]}...")
                    except Exception as e:
                        logger.error(f"Error parsing command response: {e}")

                    logger.info("🔍 END COMMAND LOG 🔍")

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

            # Log agent response summary for debugging
            logger.info("🔍 AGENT RESPONSE LOG 🔍")
            logger.info(f"📤 TYPE: {response_type}")

            # Attempt to extract and log the first few answers for context
            try:
                if response_type == "json":
                    response_obj = json.loads(response_content)
                    answers = response_obj.get("answers", [])
                    if answers:
                        for i, answer in enumerate(answers[:2]):  # Log up to first 2 answers
                            logger.info(f"📝 ANSWER {i + 1}: {answer.get('description', '')[:50]}...")
                        if len(answers) > 2:
                            logger.info(f"... and {len(answers) - 2} more answers")

                        # Log options from the last answer if any
                        last_answer = answers[-1]
                        if last_answer.get("options"):
                            logger.info(f"🔘 OPTIONS: {last_answer.get('options')}")
            except Exception as e:
                logger.error(f"Error logging response content: {e}")

            logger.info("🔍 END RESPONSE LOG 🔍")

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
    logger.info("🎮 Starting example run")

    # Log environment setup
    logger.info("🔑 Checking API keys...")
    openai_key = os.getenv("OPENAI_API_KEY")
    deepgram_key = os.getenv("DEEPGRAM_API_KEY")

    if not all([openai_key, deepgram_key]):
        logger.error("❌ Missing required API keys")
        missing = []
        if not openai_key: missing.append("OPENAI_API_KEY")
        if not deepgram_key: missing.append("DEEPGRAM_API_KEY")
        logger.error(f"Missing keys: {', '.join(missing)}")
        return

    # Log mock world creation
    logger.info("🌍 Creating mock world...")
    try:
        # Environment Grid (0=Water, 1=Land) - Player starts implicitly at (2,2) facing right?
        mock_grid = [
            # 0  1  2  3  4  5  6  7  8  9  X
            [0, 1, 1, 0, 0, 0, 0, 0, 0, 0],  # 0 Y
            [0, 1, 1, 1, 1, 1, 1, 0, 0, 0],  # 1
            [0, 1, 1, 1, 1, 1, 1, 1, 0, 0],  # 2 Player @ 2,2 | Box @ 3,2
            [0, 1, 1, 1, 1, 1, 1, 1, 1, 0],  # 3 Chest @ 4,3 | Log @ 2,3
            [0, 0, 1, 1, 1, 1, 1, 1, 1, 0],  # 4 Campfire @ 5,4
            [0, 0, 0, 1, 1, 1, 1, 0, 0, 0],  # 5 Firewood @ 6,5 | Door @ 4,5
            [0, 0, 0, 0, 1, 1, 0, 0, 0, 0],  # 6
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # 7
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # 8
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  # 9
        ]
        mock_env_obj = Environment(width=10, height=10, grid=mock_grid)

        # Entities
        mock_entities = [
            Entity(id="box_1", type="box", name="Wooden Box", position=Position(x=3, y=2), description="A crate.",
                   weight=15, is_movable=True),
            Entity(id="chest_1", type="chest", name="Old Chest", position=Position(x=4, y=3),
                   description="Maybe treasure?", weight=20, is_container=True,
                   contents=[{"id": "key_1", "type": "key", "name": "Rusty Key", "weight": 1}]),
            # Container needs proper model if using puppet master directly
            Entity(id="log_1", type="log", name="Fallen Log", position=Position(x=2, y=3), description="An obstacle.",
                   weight=30, is_jumpable=True),
            Entity(id="door_1", type="door", name="Locked Door", position=Position(x=4, y=5),
                   description="Seems locked.", weight=100, state="locked", possible_actions=["unlock", "examine"]),
            Entity(id="firewood_1", type="firewood", name="Dry Firewood", position=Position(x=6, y=5),
                   description="Good for burning.", weight=5, is_collectable=True),
            Entity(id="campfire_1", type="campfire", name="Stone Campfire", position=Position(x=5, y=4),
                   description="Needs fuel.", weight=50, state="unlit", possible_actions=["light", "add_fuel"]),
            # Player inventory items are conceptual here, managed by puppet master state
            # Entity(id="torch_1", type="torch", name="Torch", description="Provides light.", weight=2), # Example if needed for use_with tests
            Entity(id="key_1", type="key", name="Rusty Key", description="An old key.", weight=1, is_collectable=True)
            # Also exists in chest initially for get/put test
        ]

        # Player conceptual inventory for context
        player_inventory_ids = ["torch_1"]  # Let's assume player starts with a torch

        mock_story_result = CompleteStoryResult(
            theme="Cave Exploration", environment=mock_env_obj,
            terrain_description="A damp, echoing cave passage.",
            entity_descriptions={
                "box_wooden_default": "A simple wooden box.",
                "chest_old_default": "An old, weathered chest.",
                "log_fallen_default": "A rough fallen log.",
                "door_locked_default": "A heavy, locked door.",
                "firewood_dry_default": "A bundle of dry firewood.",
                "campfire_stone_unlit": "A cold stone campfire pit.",
                "key_rusty_default": "A small, rusty key.",
                "torch_default_default": "A simple wooden torch."
            },
            narrative_components={
                "intro": {"intro_text": "You stand in a dark cave. A faint dripping sound echoes."},
                "quest": {"title": "Find the Exit", "objectives": ["Navigate the cave", "Find a way past the door"],
                          "reward": "Freedom!"}
            },
            entities=mock_entities,  # Use the detailed list
            complete_narrative="A cave...",
            # We might need a way to represent player's starting inventory if storyteller needs it
            # custom_context={"player_inventory": player_inventory_ids} # Example, not standard field
        )
        logger.info(f"Created mock world with {len(mock_entities)} entities")
        logger.debug(f"Entity IDs: {[e.id for e in mock_entities]}")
    except Exception as e:
        logger.error(f"❌ Error creating mock world: {str(e)}", exc_info=True)
        return

    # Initialize agents
    logger.info("🤖 Initializing agents...")
    try:
        storyteller = StorytellerAgent(
            puppet_master_agent=mock_puppet,
            complete_story_result=mock_story_result,
            voice="nova"  # Example voice
        )
        logger.info("✅ Agents initialized successfully")
    except ValueError as e:
        logger.error(f"❌ Error initializing Storyteller: {e}")
        return
    except Exception as e:
        logger.error(f"❌ Unexpected error during Storyteller initialization: {e}")
        traceback.print_exc()
        return

    # Test interactions
    logger.info("🎯 Starting interaction tests...")
    history = []  # Conversation history for the storyteller
    # Display initial message from the mock story
    intro_text = mock_story_result.narrative_components.get('intro', {}).get('intro_text', 'The game begins!')
    initial_response_content = storyteller._create_basic_answer_json(intro_text,
                                                                     options=["Look around", "Check inventory"])
    initial_response = {"type": "json", "content": initial_response_content}
    logger.info("Initial Response (JSON):")
    try:
        logger.info(json.dumps(json.loads(initial_response['content']), indent=2))
    except:
        logger.info(initial_response['content'])

    # User inputs designed to trigger puppet master tools via storyteller
    user_inputs = [
        "Look around",  # --> look
        "Check my inventory",  # --> check_inventory
        "examine the box",  # --> examine_object (box_1)
        "move right",  # --> move (walk)
        "push the box right",  # --> push (box_1)
        "move right",  # --> move (to align for pull)
        "pull the box left",  # --> pull (box_1)
        "run down",  # --> move (run)
        "jump over the log",  # --> jump (log_1) -> map coords (2,4)
        "move right",  # --> move
        "move right",  # --> move (reach chest @ 4,3)
        "examine chest_1",  # --> examine_object (chest_1)
        "get key_1 from chest_1",  # --> get_from_container
        "check inventory",  # --> check_inventory (should include key_1 now)
        "put key_1 in chest_1",  # --> put_in_container
        "check inventory",  # --> check_inventory (key_1 should be gone)
        "get the key from the chest",  # --> get_from_container (get key_1 again)
        "move down",  # --> move
        "move down",  # --> move (reach door @ 4,5)
        "examine door_1",  # --> examine_object (door_1)
        "use the key on the door",  # --> use_object_with (key_1, door_1)
        "examine door_1",  # --> examine_object (should be unlocked now conceptually)
        "move right",  # --> move
        "move right",  # --> move (reach firewood @ 6,5)
        "examine firewood_1",  # --> examine_object (firewood_1)
        "pick up the firewood",
        # --> (Implicitly handled by Storyteller/PuppetMaster? Needs get/collect logic) -> Let's assume 'get firewood_1' works conceptually like get_from_container for loose items
        "get firewood_1",  # --> Simulate pickup (maybe maps to get_item)
        "check inventory",  # --> check_inventory (should have firewood)
        "move left",  # --> move
        "move up",  # --> move (reach campfire @ 5,4)
        "examine campfire_1",  # --> examine_object (campfire_1)
        "use firewood_1 with campfire_1",  # --> use_object_with
        "examine campfire_1",  # --> examine_object (should be lit/fueled now conceptually)
        "say This cave is tricky!",  # --> say
        "move left continuous"  # --> move (continuous) - New test case
    ]

    for user_input in user_inputs:
        logger.info(f"\n👤 User input: '{user_input}'")
        try:
            response_data, history = await storyteller.process_text_input(user_input, history)
            logger.info(f"🤖 Response type: {response_data.get('type')}")
            logger.debug(f"Response content: {response_data.get('content')[:200]}...")
        except Exception as e:
            logger.error(f"❌ Error processing input: {str(e)}", exc_info=True)

        # Pretty print the JSON response
        response_content = response_data.get('content', 'Error: No content')
        logger.info("<<< Jan (JSON):")
        try:
            parsed_json = json.loads(response_content)
            logger.info(json.dumps(parsed_json, indent=2))
        except json.JSONDecodeError:
            logger.info(response_content)  # Print as is if not valid JSON

        # Print command details if a tool was called
        if response_data.get("type") == "command":
            # The 'result' here comes from the MOCK puppet master, which is likely None or a default string.
            # A real puppet master would return actual success/failure messages.
            tool_name = response_data.get('name')
            tool_params = response_data.get('params')
            mock_result = response_data.get('result')

            # Pretty-print parameters for readability
            params_str = json.dumps(tool_params, indent=4) if tool_params else "{}"

            logger.info(f"    🛠️ Tool Call Detected:")
            logger.info(f"       - Tool Name: {tool_name}")
            logger.info(f"       - Parameters:\n{params_str}")
            logger.info(f"       - Mock Result: {mock_result}")
        elif response_data.get('content'):
            # Check for specific narrative cues if needed
            if "Wanna start over? Just refresh!" in response_content:  # Example check
                logger.info("    (Restart instruction received)")

        # Add a visual separator for clarity
        logger.info("\n" + "=" * 50 + "\n")

    logger.info("\n--- Simulating Audio Interaction (Conceptual) ---")

    # (Audio part remains unchanged conceptually)
    async def mock_on_transcription(text):
        logger.info(f"   [Callback] Transcription: {text}")

    async def mock_on_response(json_str):
        logger.info(f"   [Callback] Response JSON: {json_str}")

    async def mock_on_audio(chunk):
        if chunk != b"__AUDIO_END__":
            logger.info(f"   [Callback] Audio Chunk Received ({len(chunk)} bytes)")
        else:
            logger.info(f"   [Callback] __AUDIO_END__ Received")

    dummy_audio_data = b'\x00' * 16000  # Example dummy data
    logger.info("\nProcessing dummy audio for 'look around'...")
    # NOTE: Skipping actual audio processing call as it relies on external services and previous setup.
    # text_result, cmd_info, history = await storyteller.process_audio(
    #     dummy_audio_data, mock_on_transcription, mock_on_response, mock_on_audio, history
    # )
    # print(f"   Audio Processing Result Text: {text_result}")
    # print(f"   Audio Processing Command Info: {cmd_info}")
    logger.info("   (Skipping actual audio processing in example run)")


if __name__ == "__main__":
    try:
        import asyncio

        # Ensure asyncio uses the correct event loop policy if needed, e.g. on Windows
        # if os.name == 'nt':
        #      asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(example_run())
    except KeyboardInterrupt:
        logger.info("\n🛑 Execution cancelled by user.")
    except Exception as startup_err:
        logger.error(f"\n❌ FATAL STARTUP ERROR: {startup_err}")
        traceback.print_exc()
