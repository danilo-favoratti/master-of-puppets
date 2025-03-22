"""
Example script for using the RealtimeAgent with Deepgram's Voice Agent API.
This demonstrates how to set up and use the realtime agent with audio streaming.
"""
import os
import asyncio
import argparse
from dotenv import load_dotenv

# Import the RealtimeAgent class
from realtime_agent import RealtimeAgent

# Load environment variables from .env file
load_dotenv()

async def on_transcription(text: str):
    """Callback for when user speech is transcribed."""
    print(f"\nTranscription: {text}")

async def on_response(text: str):
    """Callback for when the agent produces a text response."""
    print(f"\nAgent: {text}")

async def on_audio(audio_data: bytes):
    """Callback for when the agent produces audio."""
    # This would normally send audio to a player
    # For this example, we'll just log the size
    if audio_data == b"__AUDIO_END__":
        print("\nAudio playback complete")
    else:
        print(f"Received audio chunk: {len(audio_data)} bytes")

async def on_command(command_info: dict):
    """Callback for when the agent executes a command."""
    name = command_info.get("name", "")
    params = command_info.get("params", {})
    direction = params.get("direction", "")
    
    if name:
        if direction:
            print(f"\nExecuting command: {name} {direction}")
        else:
            print(f"\nExecuting command: {name}")

async def main():
    """Main function that sets up and runs the realtime agent."""
    parser = argparse.ArgumentParser(description="Run the RealtimeAgent demo")
    parser.add_argument("--api-key", type=str, help="Deepgram API Key", 
                        default=os.environ.get("DEEPGRAM_API_KEY"))
    parser.add_argument("--voice-id", type=str, 
                        help="ElevenLabs Voice ID", 
                        default="cgSgspJ2msm6clMCkdW9")
    parser.add_argument("--model", type=str, 
                        help="LLM model to use", 
                        default="gpt-4o-mini")
    args = parser.parse_args()
    
    if not args.api_key:
        print("Error: Deepgram API Key is required. Provide it with --api-key or set DEEPGRAM_API_KEY environment variable.")
        return
    
    # Create the realtime agent
    agent = RealtimeAgent(
        deepgram_api_key=args.api_key,
        voice_id=args.voice_id,
        llm_model=args.model
    )
    
    # Set up callbacks
    agent.set_callbacks(
        on_transcription=on_transcription,
        on_response=on_response,
        on_audio=on_audio,
        on_command=on_command
    )
    
    # Connect to the Deepgram Voice Agent API
    connected = await agent.connect()
    if not connected:
        print("Failed to connect to Deepgram Voice Agent API")
        return
    
    print("\n=== RealtimeAgent Demo ===")
    print("The agent is now listening. Speak into your microphone.")
    print("Press Ctrl+C to exit.")
    
    try:
        # In a real application, you would capture audio from a microphone
        # and send it to the agent using agent.send_audio(audio_data)
        
        # For this demo, we'll just keep the connection open
        # and use an example message
        await agent.inject_message("Hello, what can you do?")
        
        # Keep the connection alive until interrupted
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        # Disconnect from the Deepgram Voice Agent API
        await agent.disconnect()
        print("Disconnected from Deepgram Voice Agent API")

if __name__ == "__main__":
    asyncio.run(main()) 