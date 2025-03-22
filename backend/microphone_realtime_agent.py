"""
Real-time microphone capture and streaming to the RealtimeAgent.
This script demonstrates capturing audio from a microphone and streaming it to
the RealtimeAgent for real-time voice interaction.
"""
import os
import asyncio
import argparse
import queue
import threading
import time
import pyaudio
from dotenv import load_dotenv

# Import the RealtimeAgent class
from realtime_agent import RealtimeAgent

# Load environment variables from .env file
load_dotenv()

# Audio parameters
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 48000  # Sample rate expected by Deepgram
CHUNK = 4096  # Number of frames per buffer
RECORD_SECONDS = 300  # Max recording time

class MicrophoneCapture:
    """
    Class to handle microphone audio capture and streaming to the RealtimeAgent.
    """
    def __init__(self, agent: RealtimeAgent):
        self.agent = agent
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.audio = pyaudio.PyAudio()
        self.stream = None
        
    def audio_callback(self, in_data, frame_count, time_info, status):
        """
        Callback function for PyAudio, called when new audio data is available.
        """
        self.audio_queue.put(in_data)
        return (in_data, pyaudio.paContinue)
    
    def start_recording(self):
        """
        Start recording audio from the microphone.
        """
        if self.is_recording:
            print("Already recording.")
            return
        
        self.is_recording = True
        
        # Initialize PyAudio stream
        self.stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            stream_callback=self.audio_callback
        )
        
        print("Recording started...")
        
        # Start a thread to process the audio queue
        threading.Thread(target=self._process_audio_queue, daemon=True).start()
    
    def stop_recording(self):
        """
        Stop recording audio from the microphone.
        """
        if not self.is_recording:
            return
        
        self.is_recording = False
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        
        print("Recording stopped.")
    
    def _process_audio_queue(self):
        """
        Process audio data from the queue and send it to the agent.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while self.is_recording:
            try:
                # Get audio data from the queue
                if not self.audio_queue.empty():
                    audio_data = self.audio_queue.get(timeout=0.1)
                    
                    # Send audio data to the agent
                    loop.run_until_complete(self.agent.send_audio(audio_data))
                else:
                    time.sleep(0.01)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error processing audio: {e}")
                continue
        
        loop.close()
    
    def cleanup(self):
        """
        Clean up resources.
        """
        self.stop_recording()
        self.audio.terminate()

async def on_transcription(text: str):
    """Callback for when user speech is transcribed."""
    print(f"\nYou said: {text}")

async def on_response(text: str):
    """Callback for when the agent produces a text response."""
    print(f"\nJan: {text}")

async def on_audio(audio_data: bytes):
    """Callback for when the agent produces audio."""
    # This would normally play the audio through speakers
    # For this example, we'll just log the size
    if audio_data == b"__AUDIO_END__":
        print("(Audio playback complete)")
    else:
        # Print only for the first chunk to avoid cluttering the console
        if not hasattr(on_audio, "first_chunk_logged"):
            print(f"(Received audio: {len(audio_data)} bytes)")
            on_audio.first_chunk_logged = True
        
        # Every 10 chunks, print a '.' to show activity
        if not hasattr(on_audio, "chunk_count"):
            on_audio.chunk_count = 0
        on_audio.chunk_count += 1
        
        if on_audio.chunk_count % 10 == 0:
            print(".", end="", flush=True)
        
        # Reset for next response
        if audio_data == b"__AUDIO_END__":
            on_audio.first_chunk_logged = False
            on_audio.chunk_count = 0
            print("")  # New line after audio is complete

async def on_command(command_info: dict):
    """Callback for when the agent executes a command."""
    name = command_info.get("name", "")
    params = command_info.get("params", {})
    
    if name == "jump":
        direction = params.get("direction", "")
        if direction:
            print(f"\n(Jan jumps {direction})")
        else:
            print("\n(Jan jumps)")
    elif name == "walk":
        direction = params.get("direction", "")
        print(f"\n(Jan walks {direction})")
    elif name == "run":
        direction = params.get("direction", "")
        print(f"\n(Jan runs {direction})")
    elif name == "push":
        direction = params.get("direction", "")
        print(f"\n(Jan pushes {direction})")
    elif name == "pull":
        direction = params.get("direction", "")
        print(f"\n(Jan pulls {direction})")
    elif name == "talk":
        message = params.get("message", "")
        print(f"\n(Jan says: '{message}')")

async def main():
    """Main function that sets up and runs the microphone-enabled realtime agent."""
    parser = argparse.ArgumentParser(description="Run the RealtimeAgent with microphone input")
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
    
    # Create and start the microphone capture
    mic_capture = MicrophoneCapture(agent)
    
    print("\n=== RealtimeAgent Microphone Demo ===")
    print("The agent is now listening. Speak into your microphone.")
    print("Say 'hello' to get started.")
    print("Press Ctrl+C to exit.")
    
    try:
        # Start recording from the microphone
        mic_capture.start_recording()
        
        # Keep the connection alive until interrupted
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        # Clean up
        mic_capture.cleanup()
        await agent.disconnect()
        print("Disconnected from Deepgram Voice Agent API")

if __name__ == "__main__":
    asyncio.run(main()) 