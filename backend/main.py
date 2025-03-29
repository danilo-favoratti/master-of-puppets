"""
FastAPI WebSocket server for the game character control system using OpenAI Agents SDK.
Initial text messages are routed to the CopywriterAgent for map/story setup. Once complete,
subsequent messages (including audio) are handled by the StorytellerAgent with enhanced audio processing.
"""

import asyncio
import json
import os
import time
from typing import Dict, Any
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agent_puppet_master import create_puppet_master
from agent_copywriter_direct import GameCopywriterAgent, CompleteStoryResult
from old.agent_storyteller import StorytellerAgent

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
    copywriter_agent = GameCopywriterAgent(OPENAI_API_KEY)

    # Create a character controller agent (for example purposes)
    char_controller_agent = create_puppet_master("Jan Character")

    storyteller_agent = StorytellerAgent(char_controller_agent, OPENAI_API_KEY, DEEPGRAM_API_KEY, CHARACTER_VOICE)

    session_data = {
        "copywriter_agent": copywriter_agent,
        "storyteller_agent": storyteller_agent,
        "char_controller_agent": char_controller_agent,
        "audio_buffer": bytearray(),
        "is_receiving_audio": False,
        "audio_sent_metadata": False,
        "conversation_history": [],
        # Flag indicating whether the copywriter stage is complete.
        "copywriter_done": False,
        "game_context": None  # <-- Add placeholder for loaded game data
    }

    active_connections[websocket] = session_data

    # Define callback functions
    async def on_transcription(text: str):
        await websocket.send_text(json.dumps({
            "type": "user_message",
            "content": text
        }))

    async def on_response(text: str):
        await websocket.send_text(json.dumps({
            "type": "text",
            "content": text
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
        await websocket.send_text(json.dumps({
            "type": "command",
            "name": name,
            "result": result,
            "params": params
        }))

    # Send a welcome message
    await websocket.send_text(json.dumps({
        "type": "text",
        "content": "Hey there, Let's begin your journey! Speak or send a text message."
    }))

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
                    print(f"Received message: {data} | Copywriter Done? {session_data['copywriter_done']}")

                    # Handle theme selection before copywriter is done
                    if data.get("type") == "set_theme" and not session_data["copywriter_done"]:
                        theme_name = data.get("theme")

                        if not theme_name or not isinstance(theme_name, str):
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "content": "Invalid theme name provided."
                            }))
                            continue # Wait for a valid theme

                        # Sanitize theme name slightly just in case (prevent directory traversal)
                        safe_theme_name = Path(theme_name).name
                        # map_file_path = Path("backend/map") / f"{safe_theme_name}.json" # Old path

                        # --- Construct path relative to this script file --- 
                        script_dir = Path(__file__).resolve().parent
                        map_file_path = script_dir / "map" / f"{safe_theme_name}.json"
                        print(f"[DEBUG] Attempting to load map file from: {map_file_path}") # Debug print
                        # --- End path fix ---

                        if not map_file_path.is_file():
                            print(f"Error: Map file not found at {map_file_path}")
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "content": f"Theme file '{safe_theme_name}.json' not found."
                            }))
                            continue # Wait for a valid theme

                        try:
                            with open(map_file_path, "r") as f:
                                game_data = json.load(f)
                        except json.JSONDecodeError:
                            print(f"Error: Could not decode JSON from {map_file_path}")
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "content": f"Error reading theme file '{safe_theme_name}.json'."
                            }))
                            continue # Wait for a valid theme
                        except Exception as e:
                            print(f"Error reading map file {map_file_path}: {e}")
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "content": "An error occurred while loading the theme."
                            }))
                            continue # Wait for a valid theme

                        # Store game context and mark copywriter as done
                        session_data["game_context"] = game_data
                        session_data["copywriter_done"] = True
                        copywriter_agent.game_context = game_data # Update agent context if needed

                        # Send map creation command to frontend
                        map_create_command = {
                            "type": "command",
                            "name": "create_map",
                            "map_data": game_data.get("environment", {}),
                            "entities": game_data.get("entities", []), # Send entities too
                            "narrative": game_data.get("complete_narrative", ""), # Send narrative
                            "result": f"Map loaded for theme: {safe_theme_name}",
                            "params": {
                                "map_name": game_data.get("theme", safe_theme_name),
                                "map_description": game_data.get("terrain_description", "No description available.")
                            }
                        }
                        await websocket.send_text(json.dumps(map_create_command))

                        await websocket.send_text(json.dumps({
                            "type": "info",
                            "content": f"Theme '{safe_theme_name}' loaded. You can now interact with the world."
                        }))

                    elif data.get("type") == "text":
                        text_message = data["content"]
                        # Echo the user's text message
                        await websocket.send_text(json.dumps({
                            "type": "user_message",
                            "content": text_message
                        }))

                        if not session_data["copywriter_done"]:
                            # If copywriter isn't done, prompt user to select a theme
                             await websocket.send_text(json.dumps({
                                "type": "info",
                                "content": "Please select a theme first to start the game."
                            }))
                        else:
                            # Process subsequent text with StorytellerAgent using loaded context
                            response_data, session_data[
                                "conversation_history"] = await storyteller_agent.process_text_input(
                                text_message,
                                session_data["conversation_history"],
                                game_context=session_data.get("game_context") # Pass context
                            )
                            if response_data["type"] == "text":
                                await on_response(response_data["content"])
                                # Generate TTS audio for the response
                                speech_response = storyteller_agent.openai_client.audio.speech.create(
                                    model="tts-1",
                                    voice=storyteller_agent.voice,
                                    input=response_data["content"]
                                )
                                session_data["audio_sent_metadata"] = False
                                for chunk in speech_response.iter_bytes():
                                    await on_audio(chunk)
                                await on_audio(b"__AUDIO_END__")
                            elif response_data["type"] == "command":
                                await send_command(response_data["name"], response_data.get("params", {}))

                    elif data.get("type") == "audio_end":
                        # Process the complete audio buffer when audio_end is received
                        if session_data["is_receiving_audio"] and session_data["audio_buffer"]:
                            audio_data = bytes(session_data["audio_buffer"])
                            try:
                                print(f"Processing audio buffer ({len(audio_data)} bytes)")
                                print(f"First 20 bytes of audio: {audio_data[:20]}")
                                # Ensure copywriter is done before processing audio
                                if not session_data["copywriter_done"]:
                                    await websocket.send_text(json.dumps({
                                        "type": "info",
                                        "content": "Please select a theme first to start the game."
                                    }))
                                else:
                                    response_text, command_info = await storyteller_agent.process_audio(
                                        audio_data, on_transcription, on_response, on_audio,
                                        session_data["conversation_history"],
                                        game_context=session_data.get("game_context") # Pass context
                                    )
                                    if command_info.get("name"):
                                        await send_command(command_info["name"], command_info.get("params", {}))
                            except Exception as e:
                                print(f"Error processing audio: {e}")
                                await websocket.send_text(json.dumps({
                                    "type": "error",
                                    "content": f"Error processing voice: {str(e)}"
                                }))
                        else:
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "content": "No audio data received. Please try recording again."
                            }))
                        # Reset audio state regardless
                        session_data["audio_buffer"] = bytearray()
                        session_data["audio_sent_metadata"] = False
                        session_data["is_receiving_audio"] = False
                    else:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "content": "Unrecognized message type."
                        }))
                except json.JSONDecodeError:
                    try:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "content": "Invalid message format."
                        }))
                    except Exception as sendError:
                        print(f"Error sending invalid format message: {sendError}")
    except WebSocketDisconnect:
        if websocket in active_connections:
            del active_connections[websocket]
    except Exception as e:
        print(f"Unexpected error in websocket_endpoint: {e}")
        if websocket in active_connections:
            del active_connections[websocket]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
