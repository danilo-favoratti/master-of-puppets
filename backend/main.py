"""
FastAPI WebSocket server for the game character control system.
"""
import os
import json
import asyncio
from typing import Dict, Any, List
from dotenv import load_dotenv

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from openai import OpenAI
# Change relative imports to absolute imports
from agent import setup_agent, process_user_input
from transcription import RealTimeTranscriber

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

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


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint that handles incoming connections and messages.
    
    Args:
        websocket (WebSocket): The WebSocket connection
    """
    # Accept the connection
    await websocket.accept()
    
    # Initialize session data
    session_data = {
        "agent": setup_agent(OPENAI_API_KEY),
        "transcriber": RealTimeTranscriber(OPENAI_API_KEY),
        "conversation_history": [],
        "is_receiving_audio": False
    }
    
    # Set up transcription callback
    async def on_transcription(text: str):
        """Handle transcribed text from the voice input."""
        await process_message(websocket, text)
    
    session_data["transcriber"].set_transcription_callback(on_transcription)
    
    # Store the connection and session data
    active_connections[websocket] = session_data
    
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
                    session_data["is_receiving_audio"] = True
                    await session_data["transcriber"].add_audio_chunk(audio_data)
            
            elif "text" in message:
                # Parse the JSON message
                try:
                    data = json.loads(message["text"])
                    
                    # Check message type
                    if data.get("type") == "text":
                        # Text message from user
                        await process_message(websocket, data["content"])
                    
                    elif data.get("type") == "audio_end":
                        # End of audio stream
                        if session_data["is_receiving_audio"]:
                            session_data["is_receiving_audio"] = False
                            await session_data["transcriber"].end_audio_stream()
                
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


async def process_message(websocket: WebSocket, message: str):
    """
    Process a user message through the agent and send back the response.
    
    Args:
        websocket (WebSocket): The client connection
        message (str): The user's message
    """
    # Get session data
    session_data = active_connections.get(websocket)
    if not session_data:
        return
    
    # Process the message through the agent
    response, conversation_history = process_user_input(
        session_data["agent"],
        message,
        session_data["conversation_history"]
    )
    
    # Update conversation history
    session_data["conversation_history"] = conversation_history
    
    # Send the response to the client
    await websocket.send_text(json.dumps(response))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 