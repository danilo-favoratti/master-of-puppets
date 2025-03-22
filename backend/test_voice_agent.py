"""
Test script for the fixed voice agent implementation.
"""
import asyncio
import os
from dotenv import load_dotenv
from voice_agent import VoiceAgentManager
from openai import OpenAI

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHARACTER_VOICE = os.getenv("CHARACTER_VOICE", "nova") 

async def main():
    # Initialize the voice agent
    voice_agent = VoiceAgentManager(OPENAI_API_KEY, CHARACTER_VOICE)
    
    # Define callback functions
    async def on_transcription(text: str):
        print(f"Transcription: {text}")
    
    async def on_response(text: str):
        print(f"Response: {text}")
    
    async def on_audio(audio_chunk: bytes):
        # In a real implementation, you'd send this over WebSocket
        print(f"Received audio chunk: {len(audio_chunk)} bytes")
    
    # Test the voice pipeline with generated audio
    print("Testing voice agent with test audio...")
    
    # Create test audio by converting a text command to speech
    print("Creating test audio from command 'walk left'...")
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    # Convert text to speech
    response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input="Hey character, please walk left"
    )
    
    # Get binary audio data
    buffer = bytearray()
    for chunk in response.iter_bytes():
        buffer.extend(chunk)
    
    print(f"Generated {len(buffer)} bytes of audio data")

    # Process the audio through the voice pipeline
    print("\nProcessing audio through voice agent...")
    response_text, command_info = await voice_agent.process_audio(
        bytes(buffer),
        on_transcription,
        on_response,
        on_audio
    )
    
    # Check for command detection
    if command_info["name"]:
        print(f"\nDetected command: {command_info['name']} with params: {command_info['params']}")
    else:
        print("\nNo command detected in the response")
    
    print("\nTest completed!")

if __name__ == "__main__":
    asyncio.run(main()) 