"""
FastAPI WebSocket server for the game character control system using OpenAI Agents SDK.
Initial text messages are routed to the CopywriterAgent for map/story setup. Once complete,
subsequent messages (including audio) are handled by the StorytellerAgent with enhanced audio processing.
"""

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Dict, Any
import traceback

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from agent_copywriter_direct import CompleteStoryResult
from agent_puppet_master import create_puppet_master
from agent_storyteller_final import StorytellerAgentFinal

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
CHARACTER_VOICE = os.getenv("CHARACTER_VOICE", "nova")  # Default voice: nova

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware (for development, allow all origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dictionary to store active WebSocket connections and their session data.
active_connections: Dict[WebSocket, Dict[str, Any]] = {}


@app.on_event("startup")
async def startup_event():
    """Initialize resources on server startup."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    if not DEEPGRAM_API_KEY:
        raise ValueError("DEEPGRAM_API_KEY environment variable is not set")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint:
      - First, text messages are sent to the CopywriterAgent to set up the game context.
      - When that stage is complete, further messages (text or audio) are handled by the StorytellerAgent.
    """
    await websocket.accept()

    # Initialize agents:
    # Copywriter is only used initially if we implement the map generation phase
    # copywriter_agent = GameCopywriterAgent(OPENAI_API_KEY)

    session_data = {
        # "copywriter_agent": copywriter_agent, # Keep commented if not used initially
        "storyteller_agent": None,
        "char_controller_agent": None,
        "audio_buffer": bytearray(),
        "is_receiving_audio": False,
        "audio_sent_metadata": False,
        "conversation_history": [],
        # Flag indicating whether the copywriter stage is complete (now means theme loaded).
        "copywriter_done": False,
        "game_context": None  # Holds the CompleteStoryResult object after loading
    }

    active_connections[websocket] = session_data

    # Define callback functions
    async def on_transcription(text: str):
        await websocket.send_text(json.dumps({
            "type": "user_message",
            "content": text,
            "sender": "user"  # Specify this is from the user
        }))

    async def on_response(text: str):
        await websocket.send_text(json.dumps({
            "type": "text",
            "content": text,
            "sender": "character"  # Specify this is from the character/assistant
        }))

    async def on_audio(audio_chunk: bytes):
        """
        Handle audio chunks from the agent:
          - Sends an audio_start metadata message on the first chunk.
          - Logs chunk information and ensures proper sending.
          - Sends a final audio_end signal when done.
        """
        if audio_chunk == b"__AUDIO_END__":
            await websocket.send_text(json.dumps({"type": "audio_end"}))
            return

        try:
            # Send metadata on first audio chunk
            if not session_data.get("audio_sent_metadata"):
                # Debug print (can be removed in production)
                print("First audio chunk received, sending audio_start metadata")
                await websocket.send_text(json.dumps({
                    "type": "audio_start",
                    "format": "mp3",
                    "timestamp": time.time()
                }))
                session_data["audio_sent_metadata"] = True
                # Delay to allow client to prepare for audio chunks
                await asyncio.sleep(0.2)

            # Ensure audio_chunk is bytes
            if not isinstance(audio_chunk, bytes):
                print(f"Warning: audio_chunk is not bytes, it's {type(audio_chunk)}. Converting...")
                audio_chunk = bytes(audio_chunk)

            if len(audio_chunk) > 0:
                await websocket.send_bytes(audio_chunk)
                await asyncio.sleep(0.02)
            else:
                print("Warning: Empty audio chunk, not sending")
        except Exception as e:
            print(f"Error in on_audio: {e}")

    async def send_command(name: str, params: Dict[str, Any]):
        direction = params.get("direction", "")
        result = f"{name.capitalize()} {direction}"
        cmd_data = {
            "type": "command",
            "name": name,
            "result": result,
            "params": params,
            "sender": "system"  # Commands are system messages
        }
        print(f"🎮 Sending command to frontend: {name}, params: {params}")
        print(f"FULL COMMAND JSON: {json.dumps(cmd_data)}")
        await websocket.send_text(json.dumps(cmd_data))
        print(f"✅ Command sent successfully: {name}")

    # Send a welcome message
    """ await websocket.send_text(json.dumps({
        "type": "text",
        "content": "Loading game...",
        "sender": "system"  # Welcome message is from the character/assistant
    })) """

    try:
        while True:
            try:
                message = await websocket.receive()
            except Exception as recv_error:
                print(f"WebSocket receive error, terminating loop: {recv_error}")
                break

            if "bytes" in message:
                # Handle incoming binary audio data
                audio_data = message["bytes"]
                # Debug logging for audio chunk sizes and header check
                print(f"Received binary data: {len(audio_data)} bytes")
                if len(audio_data) < 10:
                    print("Warning: Received very small audio chunk, possibly invalid")
                else:
                    print(f"Audio data header check: {audio_data[:10]}")

                if audio_data:
                    if not session_data["is_receiving_audio"]:
                        # Start new audio session: reset buffer and metadata flag
                        session_data["audio_buffer"] = bytearray()
                        session_data["audio_sent_metadata"] = False
                        session_data["is_receiving_audio"] = True
                        print("Started new audio recording session")
                    session_data["audio_buffer"].extend(audio_data)
                    print(f"Audio buffer size now: {len(session_data['audio_buffer'])} bytes")
            elif "text" in message:
                try:
                    data = json.loads(message["text"])
                    print(f"Received message: {data} | Theme Loaded? {session_data['copywriter_done']}")

                    # Handle theme selection before copywriter is done
                    if data.get("type") == "set_theme" and not session_data["copywriter_done"]:
                        theme_name = data.get("theme")

                        if not theme_name or not isinstance(theme_name, str):
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "content": "Invalid theme name provided.",
                                "sender": "system"
                            }))
                            continue  # Wait for a valid theme

                        # Sanitize theme name slightly just in case (prevent directory traversal)
                        safe_theme_name = Path(theme_name).name
                        # map_file_path = Path("backend/map") / f"{safe_theme_name}.json" # Old path

                        # --- Construct path relative to this script file --- 
                        script_dir = Path(__file__).resolve().parent
                        map_file_path = script_dir / "map" / f"{safe_theme_name}.json"
                        print(f"[DEBUG] Attempting to load map file from: {map_file_path}")  # Debug print
                        # --- End path fix ---

                        if not map_file_path.is_file():
                            print(f"Error: Map file not found at {map_file_path}")
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "content": f"Theme file '{safe_theme_name}.json' not found.",
                                "sender": "system"
                            }))
                            continue  # Wait for a valid theme

                        try:
                            with open(map_file_path, "r") as f:
                                game_data = json.load(f)
                        except json.JSONDecodeError:
                            print(f"Error: Could not decode JSON from {map_file_path}")
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "content": f"Error reading theme file '{safe_theme_name}.json'.",
                                "sender": "system"
                            }))
                            continue  # Wait for a valid theme
                        except Exception as e:
                            print(f"Error reading map file {map_file_path}: {e}")
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "content": "An error occurred while loading the theme.",
                                "sender": "system"
                            }))
                            continue  # Wait for a valid theme

                        try:
                            # Use Pydantic's model_validate for robust parsing
                            complete_story_result = CompleteStoryResult.model_validate(game_data)
                            session_data["game_context"] = complete_story_result  # Store the validated object
                            print(
                                f"Successfully validated and created CompleteStoryResult for theme: {complete_story_result.theme}")
                        except Exception as validation_error:
                            print(
                                f"Error: Failed to validate game data against CompleteStoryResult: {validation_error}")
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "content": f"Error validating data structure in theme file '{safe_theme_name}.json'.",
                                "sender": "system"
                            }))
                            continue  # Wait for a valid theme

                        # --- Initialize StorytellerAgent with the context ---
                        try:
                            # Create a character controller agent
                            char_controller_agent = create_puppet_master(person_name="Jan Character",
                                                                         story_result=complete_story_result)
                            session_data["char_controller_agent"] = char_controller_agent

                            storyteller_agent = StorytellerAgentFinal(
                                complete_story_result=complete_story_result,  # Pass the validated object
                                websocket=websocket  # Pass the websocket connection
                            )
                            session_data["storyteller_agent"] = storyteller_agent
                            session_data["copywriter_done"] = True  # Mark theme loading as complete
                            print("StorytellerAgent initialized successfully with loaded game context.")
                        except Exception as agent_init_error:
                            print(f"Error initializing StorytellerAgent: {agent_init_error}")
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "content": "Failed to initialize the character agent after loading theme.",
                                "sender": "system"
                            }))
                            # Reset state if agent init fails
                            session_data["game_context"] = None
                            session_data["copywriter_done"] = False
                            continue

                        # --- REMOVED storyteller_agent.set_result(...) ---

                        # Send map creation command to frontend
                        map_create_command = {
                            "type": "command",
                            "name": "create_map",
                            "map_data": game_data.get("environment", {}),  # Send raw dict for compatibility if needed
                            "entities": game_data.get("entities", []),  # Send raw dict for compatibility if needed
                            "narrative": game_data.get("complete_narrative", ""),
                            "result": f"`{safe_theme_name.replace('_', ' ')}` loaded. \nWait...",
                            "params": {
                                "map_name": game_data.get("theme", safe_theme_name),
                                "map_description": game_data.get("terrain_description", "No description available.")
                            },
                            "sender": "system"
                        }
                        await websocket.send_text(json.dumps(map_create_command))

                    elif data.get("type") == "text":
                        text_message = data["content"]
                        # Echo the user's text message
                        await websocket.send_text(json.dumps({
                            "type": "user_message",
                            "content": text_message,
                            "sender": "user"
                        }))

                        if not session_data["copywriter_done"] or not session_data["storyteller_agent"]:
                            # Prompt user to select a theme if not done
                            await websocket.send_text(json.dumps({
                                "type": "info",
                                "content": "Please select a theme first to start the game.",
                                "sender": "system"
                            }))
                        else:
                            # Process subsequent text with StorytellerAgent
                            try:
                                # Get the storyteller agent
                                storyteller_agent = session_data["storyteller_agent"]
                                
                                print(f"⌨️ Processing text input: '{text_message}'")
                                # Process the text input
                                response_data, session_data[
                                    "conversation_history"] = await storyteller_agent.process_text_input(
                                    text_message,
                                    conversation_history=session_data["conversation_history"]
                                    # Context is now internal to the storyteller_agent instance
                                )
                                
                                print(f"📩 Received response data type: {response_data['type']}")

                                # --- Handle response types (JSON, Command, Text with TTS) ---
                                if response_data["type"] == "json":
                                    print(f"📄 Processing JSON response")
                                    # Extract text from answers for TTS
                                    try:
                                        json_content = json.loads(response_data["content"])
                                        # Ensure we handle potential list/dict structure correctly
                                        answers_list = json_content.get("answers", [])
                                        tts_text = " ".join([answer.get("description", "")
                                                         for answer in answers_list if isinstance(answer, dict)])

                                        # Generate TTS audio for the response
                                        if tts_text.strip() and storyteller_agent.openai_client:  # Check if client exists
                                            print(f"Generating TTS for: '{tts_text[:50]}...'")  # Log TTS text
                                            try:
                                                speech_response = storyteller_agent.openai_client.audio.speech.create(
                                                    model="tts-1",
                                                    voice=storyteller_agent.voice,
                                                    input=tts_text
                                                )
                                                session_data["audio_sent_metadata"] = False

                                                # Send the JSON content directly to the client
                                                await on_response(response_data["content"])

                                                for chunk in speech_response.iter_bytes():
                                                    await on_audio(chunk)

                                                await on_audio(b"__AUDIO_END__")
                                            except Exception as tts_error:
                                                print(f"Error during TTS generation/streaming: {tts_error}")
                                    except json.JSONDecodeError as e:
                                        print(f"Error decoding JSON for TTS: {e}")
                                    except Exception as tts_prep_error:
                                        print(f"Error preparing text for TTS: {tts_prep_error}")

                                elif response_data["type"] == "command":
                                    print(f"🎮 Processing COMMAND response: {response_data['name']}")
                                    print(f"🎮 Command details: {response_data}")
                                    # Send the command details first
                                    await send_command(response_data["name"], response_data.get("params", {}))
                                    # Log specifics for movement commands
                                    if response_data["name"] == "move":
                                        print(f"🚶 Movement command sent to frontend: {response_data['name']} with params: {response_data.get('params', {})}")
                                    # Then send the narrative/text part of the command response
                                    if "content" in response_data and response_data["content"]:
                                        await on_response(response_data["content"])
                                        # Optionally generate TTS for the command response text
                                        try:
                                            json_content = json.loads(response_data["content"])
                                            answers_list = json_content.get("answers", [])
                                            tts_text = " ".join([answer.get("description", "")
                                                             for answer in answers_list if isinstance(answer, dict)])
                                            if tts_text.strip() and storyteller_agent.openai_client:
                                                print(f"Generating TTS for command response: '{tts_text[:50]}...'")
                                                try:
                                                    speech_response = await storyteller_agent.openai_client.audio.speech.create(
                                                        model="tts-1", voice=storyteller_agent.voice,
                                                        input=tts_text.strip(), response_format="mp3"
                                                    )
                                                    session_data["audio_sent_metadata"] = False
                                                    if hasattr(speech_response, 'iter_bytes'):
                                                        async for chunk in speech_response.aiter_bytes(chunk_size=4096):
                                                            if chunk: await on_audio(chunk)
                                                    elif hasattr(speech_response, 'content'):
                                                        await on_audio(speech_response.content)
                                                    else:
                                                        audio_bytes = speech_response.read()
                                                        if audio_bytes: await on_audio(audio_bytes)
                                                    await on_audio(b"__AUDIO_END__")
                                                except Exception as tts_error:
                                                    print(f"Error during TTS generation/streaming for command: {tts_error}")
                                        except Exception as cmd_tts_err:
                                            print(f"Error preparing command response for TTS: {cmd_tts_err}")
                                else:
                                    print(f"⚠️ Unknown response type: {response_data['type']}")
                            except Exception as process_error:
                                print(f"Error processing text input: {process_error}")
                                traceback.print_exc()
                                await websocket.send_text(json.dumps({
                                    "type": "error",
                                    "content": f"Server error: {str(process_error)}",
                                    "sender": "system"
                                }))

                    elif data.get("type") == "audio_end":
                        # Process the complete audio buffer when audio_end is received
                        if session_data["is_receiving_audio"] and session_data["audio_buffer"]:
                            audio_data = bytes(session_data["audio_buffer"])
                            try:
                                print(f"Processing audio buffer ({len(audio_data)} bytes)")
                                # Ensure theme is loaded and agent exists
                                if not session_data["copywriter_done"] or not session_data["storyteller_agent"]:
                                    await websocket.send_text(json.dumps({
                                        "type": "info",
                                        "content": "Please select a theme first to start the game.",
                                        "sender": "system"
                                    }))
                                else:
                                    storyteller_agent = session_data["storyteller_agent"]
                                    # Process audio using the agent instance
                                    response_text, command_info, session_data[
                                        "conversation_history"] = await storyteller_agent.process_audio(
                                        audio_data, on_transcription, on_response, on_audio,
                                        session_data["conversation_history"]
                                        # Context is internal to the agent instance now
                                    )
                                    # Send command if returned by audio processing
                                    if command_info and command_info.get("name") and command_info[
                                        "name"] != "json_response":
                                        await send_command(command_info["name"], command_info.get("params", {}))
                            except Exception as e:
                                print(f"Error processing audio: {e}")
                                await websocket.send_text(json.dumps({
                                    "type": "error",
                                    "content": f"Error processing voice: {str(e)}",
                                    "sender": "system"
                                }))
                        else:
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "content": "No audio data received. Please try recording again.",
                                "sender": "system"
                            }))
                        # Reset audio state regardless
                        session_data["audio_buffer"] = bytearray()
                        session_data["audio_sent_metadata"] = False
                        session_data["is_receiving_audio"] = False
                    else:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "content": "Unrecognized message type.",
                            "sender": "system"
                        }))
                except json.JSONDecodeError:
                    try:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "content": "Invalid message format.",
                            "sender": "system"
                        }))
                    except Exception as sendError:
                        print(f"Error sending invalid format message: {sendError}")
    except WebSocketDisconnect:
        if websocket in active_connections:
            del active_connections[websocket]
    except Exception as e:
        print(f"Unexpected error in websocket_endpoint: {e}")
        traceback.print_exc()  # Add traceback to see the full error stack
        # Try to notify client if connection is still open
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "content": f"Server error: {str(e)}",
                "sender": "system"
            }))
        except Exception:
            pass  # Connection might be closed
        if websocket in active_connections:
            del active_connections[websocket]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
