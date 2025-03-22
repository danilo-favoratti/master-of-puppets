"""
FastAPI WebSocket server for the game character control system using OpenAI Agents SDK.
"""
import os
import json
import asyncio
import time
from typing import Dict, Any, List
from dotenv import load_dotenv

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Import the new DefinitiveAgent instead of VoiceAgentManager
from definitive_agent import DefinitiveAgent

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
CHARACTER_VOICE = os.getenv("CHARACTER_VOICE", "nova")  # Default voice: nova

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware to allow connections from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for development, restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active connections and their associated data
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
    WebSocket endpoint that handles incoming connections and messages.
    
    Args:
        websocket (WebSocket): The WebSocket connection
    """
    # Accept the connection
    await websocket.accept()
    
    # Initialize the DefinitiveAgent with both OpenAI and Deepgram API keys
    agent = DefinitiveAgent(OPENAI_API_KEY, DEEPGRAM_API_KEY, CHARACTER_VOICE)
    
    # Initialize session data
    session_data = {
        "agent": agent,
        "audio_buffer": bytearray(),
        "is_receiving_audio": False,
        "conversation_history": []
    }
    
    # Store the connection and session data
    active_connections[websocket] = session_data
    
    # Define callbacks for agent
    async def on_transcription(text: str):
        """Handle transcribed text from the voice input."""
        # Send the transcription as a normal user message rather than a special transcription type
        # This will make voice input look the same as typed input in the chat UI
        await websocket.send_text(json.dumps({
            "type": "user_message",
            "content": text
        }))
    
    async def on_response(text: str):
        """Handle text response from the agent."""
        await websocket.send_text(json.dumps({
            "type": "text",
            "content": text
        }))
    
    async def on_audio(audio_chunk: bytes):
        """Handle audio response from the agent."""
        # Check if this is the end marker
        if audio_chunk == b"__AUDIO_END__":
            print("Received __AUDIO_END__ marker, sending audio_end signal")
            await websocket.send_text(json.dumps({
                "type": "audio_end"
            }))
            print("Sent audio_end signal to client")
            return
        
        try:
            # Send audio metadata if this is the first chunk
            if not session_data.get("audio_sent_metadata"):
                print("First audio chunk received, sending audio_start metadata")
                await websocket.send_text(json.dumps({
                    "type": "audio_start",
                    "format": "mp3",
                    "timestamp": time.time()
                }))
                session_data["audio_sent_metadata"] = True
                # Allow time for the client to process the metadata and prepare for audio chunks
                await asyncio.sleep(0.2)  # Increased delay to ensure client is ready
                print("Sent audio_start metadata to client - waiting for client to prepare")
            
            # Ensure the chunk is properly bytes
            if not isinstance(audio_chunk, bytes):
                print(f"Warning: audio_chunk is not bytes, it's {type(audio_chunk)}. Converting...")
                audio_chunk = bytes(audio_chunk)
            
            # Send the audio chunk
            if len(audio_chunk) > 0:
                print(f"Sending {len(audio_chunk)} bytes of audio data to client")
                # Use send_bytes with proper framing
                await websocket.send_bytes(audio_chunk)
                print(f"Successfully sent {len(audio_chunk)} bytes of audio data")
                # Allow a small delay between chunks
                await asyncio.sleep(0.02)
            else:
                print("Warning: Empty audio chunk, not sending")
        except Exception as e:
            print(f"Error in on_audio: {e}")
            import traceback
            traceback.print_exc()
    
    async def send_command(name: str, params: Dict[str, Any]):
        """Send a command to the client."""
        direction = params.get("direction", "")
        result = f"{name.capitalize()} {direction}"
        
        await websocket.send_text(json.dumps({
            "type": "command",
            "name": name,
            "result": result,
            "params": params
        }))
    
    # Send a welcome message to the client
    await websocket.send_text(json.dumps({
        "type": "text",
        "content": "Hey there, I'm your quirky game character! Speak to me or send me a text message."
    }))
    
    try:
        # Main WebSocket message loop
        while True:
            # Wait for messages from the client
            message = await websocket.receive()
            
            # Check if the message is binary (audio data) or text
            if "bytes" in message:
                # Handle binary audio data
                audio_data = message["bytes"]
                print(f"Received binary data: {len(audio_data)} bytes")
                
                # Validate the audio data
                if len(audio_data) < 10:
                    print("Warning: Received very small audio chunk, possibly invalid")
                else:
                    print(f"Audio data header check: First 10 bytes: {audio_data[:10]}")
                    
                if audio_data:
                    if not session_data["is_receiving_audio"]:
                        # Reset the audio buffer and metadata flag
                        session_data["audio_buffer"] = bytearray()
                        session_data["audio_sent_metadata"] = False
                        session_data["is_receiving_audio"] = True
                        print("Started new audio recording session")
                    
                    # Append to the audio buffer
                    session_data["audio_buffer"].extend(audio_data)
                    print(f"Audio buffer size now: {len(session_data['audio_buffer'])} bytes")
            
            elif "text" in message:
                # Parse the JSON message
                try:
                    data = json.loads(message["text"])
                    
                    # Check message type
                    if data.get("type") == "text":
                        text_message = data["content"]
                        
                        # Send the user's text message
                        await websocket.send_text(json.dumps({
                            "type": "user_message",
                            "content": text_message
                        }))
                        print(f"Sent user text message: '{text_message}'")
                        
                        # Process the text message with the DefinitiveAgent
                        try:
                            response_data, session_data["conversation_history"] = await agent.process_text_input(
                                text_message,
                                session_data["conversation_history"]
                            )
                            
                            # Extract text content and command info
                            if response_data["type"] == "text":
                                response_text = response_data["content"]
                                await on_response(response_text)
                                
                                # Generate TTS for the text response
                                speech_response = agent.openai_client.audio.speech.create(
                                    model="tts-1",
                                    voice=agent.voice,
                                    input=response_text
                                )
                                
                                # Reset audio metadata state
                                session_data["audio_sent_metadata"] = False
                                
                                # Send audio to client
                                collected_audio = bytearray()
                                for chunk in speech_response.iter_bytes():
                                    collected_audio.extend(chunk)
                                    await on_audio(chunk)
                                
                                # Send audio end marker
                                await on_audio(b"__AUDIO_END__")
                                
                            elif response_data["type"] == "command":
                                response_text = response_data["result"]
                                await on_response(response_text)
                                
                                # Send the command to the frontend
                                await send_command(
                                    response_data["name"],
                                    response_data.get("params", {})
                                )
                                
                                # Generate TTS for the command response
                                speech_response = agent.openai_client.audio.speech.create(
                                    model="tts-1",
                                    voice=agent.voice,
                                    input=response_text
                                )
                                
                                # Reset audio metadata state
                                session_data["audio_sent_metadata"] = False
                                
                                # Send audio to client
                                collected_audio = bytearray()
                                for chunk in speech_response.iter_bytes():
                                    collected_audio.extend(chunk)
                                    await on_audio(chunk)
                                
                                # Send audio end marker
                                await on_audio(b"__AUDIO_END__")
                            
                        except Exception as e:
                            print(f"Error processing text input: {e}")
                            import traceback
                            traceback.print_exc()
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "content": f"Error processing text: {str(e)}"
                            }))
                    
                    # Handle audio_end signal from client
                    elif data.get("type") == "audio_end":
                        print("Received audio_end signal from client")
                        if session_data["is_receiving_audio"]:
                            if session_data["audio_buffer"]:
                                # Process the complete audio buffer
                                audio_data = bytes(session_data["audio_buffer"])
                                try:
                                    print(f"Processing audio buffer ({len(audio_data)} bytes)")
                                    
                                    # Log the first few bytes for debugging
                                    print(f"First 20 bytes of audio: {audio_data[:20]}")
                                    
                                    # Send the audio to the agent for processing
                                    response_text, command_info = await agent.process_audio(
                                        audio_data,
                                        on_transcription,
                                        on_response,
                                        on_audio,
                                        session_data["conversation_history"]
                                    )
                                    
                                    # Update conversation history
                                    # Note: process_audio already handles the TTS
                                    
                                    print(f"Audio processed successfully. Response: '{response_text[:50]}...'")

                                    # Send any command if detected
                                    if command_info["name"]:
                                        print(f"Detected command: {command_info['name']} with params: {command_info['params']}")
                                        await send_command(command_info["name"], command_info["params"])
                                        
                                except Exception as e:
                                    print(f"Error processing audio: {e}")
                                    import traceback
                                    traceback.print_exc()
                                    await websocket.send_text(json.dumps({
                                        "type": "error",
                                        "content": f"Error processing voice: {str(e)}"
                                    }))
                            else:
                                await websocket.send_text(json.dumps({
                                    "type": "error",
                                    "content": "No audio data received. Please try recording again."
                                }))
                        else:
                            print("is_receiving_audio is False during audio_end - this indicates a state mismatch")
                            # Try to process any data in the buffer anyway
                            if session_data["audio_buffer"] and len(session_data["audio_buffer"]) > 0:
                                print(f"Attempting to process buffer anyway ({len(session_data['audio_buffer'])} bytes)")
                                audio_data = bytes(session_data["audio_buffer"])
                                try:
                                    # Send the audio to the agent for processing even though state is wrong
                                    response_text, command_info = await agent.process_audio(
                                        audio_data,
                                        on_transcription,
                                        on_response,
                                        on_audio,
                                        session_data["conversation_history"]
                                    )
                                    print("Successfully processed audio despite state mismatch")
                                except Exception as e:
                                    print(f"Error in fallback processing: {e}")
                                    await websocket.send_text(json.dumps({
                                        "type": "error",
                                        "content": f"Error processing voice: {str(e)}"
                                    }))
                            else:
                                await websocket.send_text(json.dumps({
                                    "type": "error",
                                    "content": "No audio data received. Please try recording again."
                                }))
                        
                        # Reset the audio state regardless
                        session_data["audio_buffer"] = bytearray()
                        session_data["audio_sent_metadata"] = False
                        session_data["is_receiving_audio"] = False
                        print("Audio state reset")
                    
                except json.JSONDecodeError:
                    # Not a valid JSON message
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "content": "Invalid message format"
                    }))
    
    except WebSocketDisconnect:
        # Remove connection data when client disconnects
        if websocket in active_connections:
            del active_connections[websocket]
    
    except Exception as e:
        # Handle unexpected errors
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "content": f"Server error: {str(e)}"
            }))
        except:
            pass
        
        # Clean up connection
        if websocket in active_connections:
            del active_connections[websocket]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True) 