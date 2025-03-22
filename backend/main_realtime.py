"""
FastAPI WebSocket server for the game character control system using Deepgram's Voice Agent API.
"""
import os
import json
import asyncio
from typing import Dict, Any, List
from dotenv import load_dotenv

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Import the real-time agent
from realtime_agent import RealtimeAgent

# Load environment variables
load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
CHARACTER_VOICE_ID = os.getenv("CHARACTER_VOICE_ID", "cgSgspJ2msm6clMCkdW9")  # Default ElevenLabs voice ID
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")  # Default model

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
    
    # Initialize the RealtimeAgent with Deepgram API key
    agent = RealtimeAgent(
        deepgram_api_key=DEEPGRAM_API_KEY,
        voice_id=CHARACTER_VOICE_ID,
        llm_model=LLM_MODEL
    )
    
    # Initialize session data
    session_data = {
        "agent": agent,
        "is_receiving_audio": False,
        "websocket_open": True,
        "audio_chunks_count": 0,  # Track the number of audio chunks
        "audio_sent_metadata": False  # Flag to track if we've sent the audio_start signal
    }
    
    # Store the connection and session data
    active_connections[websocket] = session_data
    
    # Define callbacks for agent
    async def on_transcription(text: str):
        """Handle transcribed text from the voice input."""
        if not session_data["websocket_open"]:
            return
            
        # Send the transcription as a normal user message
        await websocket.send_text(json.dumps({
            "type": "user_message",
            "content": text
        }))
    
    async def on_response(text: str):
        """Handle text response from the agent."""
        if not session_data["websocket_open"]:
            return
            
        await websocket.send_text(json.dumps({
            "type": "text",
            "content": text
        }))
    
    async def on_audio(audio_chunk: bytes):
        """Handle audio response from the agent."""
        if not session_data["websocket_open"]:
            return
            
        try:
            # Check if this is the end marker
            if audio_chunk == b"__AUDIO_END__":
                print(f"Received __AUDIO_END__ marker, sent {session_data['audio_chunks_count']} chunks before")
                
                # Only send audio_end if we've sent at least one chunk
                if session_data['audio_chunks_count'] > 0:
                    await websocket.send_text(json.dumps({
                        "type": "audio_end"
                    }))
                    print("Sent audio_end signal to client")
                else:
                    print("WARNING: No audio chunks were sent, not sending audio_end")
                
                # Reset counters for next audio
                session_data['audio_chunks_count'] = 0
                session_data["audio_sent_metadata"] = False
                return
            
            # Verify this is valid audio data (should be non-empty)
            if len(audio_chunk) == 0:
                print("WARNING: Received empty audio chunk, skipping")
                return
                
            # Log first few bytes of the first chunk for debugging
            if session_data['audio_chunks_count'] == 0:
                first_bytes = ', '.join([f"{b:02x}" for b in audio_chunk[:20]])
                print(f"First 20 bytes of first audio chunk: [{first_bytes}]")
            
            # Send audio metadata if this is the first chunk
            if not session_data.get("audio_sent_metadata"):
                print("First audio chunk received, sending audio_start metadata")
                await websocket.send_text(json.dumps({
                    "type": "audio_start",
                    "format": "mp3",  # ElevenLabs typically returns MP3
                }))
                session_data["audio_sent_metadata"] = True
                # Small delay for client to prepare for audio
                await asyncio.sleep(0.2)
            
            # Send the audio chunk
            await websocket.send_bytes(audio_chunk)
            session_data['audio_chunks_count'] += 1
            
            # Log progress periodically
            if session_data['audio_chunks_count'] % 5 == 0 or session_data['audio_chunks_count'] == 1:
                print(f"Sent {session_data['audio_chunks_count']} audio chunks so far, last chunk size: {len(audio_chunk)} bytes")
            
            # Small delay between chunks
            await asyncio.sleep(0.02)
            
        except Exception as e:
            print(f"Error in on_audio: {e}")
            import traceback
            traceback.print_exc()
    
    async def on_command(command_info: Dict[str, Any]):
        """Handle command execution from the agent."""
        if not session_data["websocket_open"]:
            return
            
        name = command_info.get("name", "")
        params = command_info.get("params", {})
        
        # Format a friendly result message
        if name == "jump":
            direction = params.get("direction", "")
            result = f"Jump {direction}" if direction else "Jump"
        elif name == "walk":
            direction = params.get("direction", "")
            result = f"Walk {direction}"
        elif name == "run":
            direction = params.get("direction", "")
            result = f"Run {direction}"
        elif name == "push":
            direction = params.get("direction", "")
            result = f"Push {direction}"
        elif name == "pull":
            direction = params.get("direction", "")
            result = f"Pull {direction}"
        elif name == "talk":
            message = params.get("message", "")
            result = f"Say: '{message}'"
        else:
            result = f"Unknown command: {name}"
        
        # Send the command to the client
        await websocket.send_text(json.dumps({
            "type": "command",
            "name": name,
            "result": result,
            "params": params
        }))
    
    # Set up the agent callbacks
    agent.set_callbacks(
        on_transcription=on_transcription,
        on_response=on_response,
        on_audio=on_audio,
        on_command=on_command
    )
    
    # Connect to the Deepgram Voice Agent API
    connected = await agent.connect()
    if not connected:
        await websocket.send_text(json.dumps({
            "type": "error",
            "content": "Failed to connect to Deepgram Voice Agent API. Please check your API key."
        }))
        await websocket.close()
        return
    
    # Send a welcome message to the client
    await websocket.send_text(json.dumps({
        "type": "text",
        "content": "Hey there, I'm Jan! Speak to me or send me a text message."
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
                
                if audio_data:
                    # Log the start of a new audio segment if needed
                    print(f"Received audio data from client: {len(audio_data)} bytes")
                    # Send audio data directly to the agent
                    await agent.send_audio(audio_data)
            
            elif "text" in message:
                # Parse the JSON message
                try:
                    data = json.loads(message["text"])
                    
                    # Check message type
                    if data.get("type") == "text":
                        text_message = data["content"]
                        
                        # Send the user's text message to UI
                        await websocket.send_text(json.dumps({
                            "type": "user_message",
                            "content": text_message
                        }))
                        
                        # Process the text message by injecting it into the conversation
                        await agent.inject_message(text_message)
                    
                    elif data.get("type") == "audio_end":
                        # Client is signaling that audio recording has ended
                        # Our agent handles this internally, so we don't need to do anything here
                        print("Received audio_end signal from client")
                    
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "content": "Invalid JSON message received"
                    }))
            
    except WebSocketDisconnect:
        print(f"WebSocket client disconnected")
    except Exception as e:
        print(f"Error in WebSocket communication: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to send error message to client
        try:
            if websocket.client_state.CONNECTED:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "content": f"Server error: {str(e)}"
                }))
        except:
            pass
    finally:
        # Clean up connections and resources
        session_data["websocket_open"] = False
        
        # Disconnect the agent
        await agent.disconnect()
        
        # Remove from active connections
        if websocket in active_connections:
            del active_connections[websocket]
        
        # Close websocket if still open
        try:
            await websocket.close()
        except:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 