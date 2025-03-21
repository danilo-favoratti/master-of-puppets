"""
Voice transcription using OpenAI's Real-Time API.
"""
import asyncio
import numpy as np
from typing import Dict, Any, List, Callable, Awaitable
from openai import OpenAI


class RealTimeTranscriber:
    """
    Handles real-time audio transcription using OpenAI's Real-Time API.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the transcriber with API credentials.
        
        Args:
            api_key (str): OpenAI API key
        """
        self.client = OpenAI(api_key=api_key)
        self.buffer = []
        self.is_transcribing = False
        self.on_transcription_callback = None
    
    def set_transcription_callback(self, callback: Callable[[str], Awaitable[None]]):
        """
        Set the callback function to be called when transcription is complete.
        
        Args:
            callback (Callable): Async function that receives the transcribed text
        """
        self.on_transcription_callback = callback
    
    async def add_audio_chunk(self, audio_chunk: bytes):
        """
        Add an audio chunk to the buffer for transcription.
        
        Args:
            audio_chunk (bytes): Raw audio data
        """
        # Convert audio chunk to the right format if needed
        # For WebSocket binary data, it's likely we're getting raw PCM data
        # This is a simplification - in a real implementation, we might need to 
        # handle different sample rates, bit depths, etc.
        self.buffer.append(audio_chunk)
    
    async def process_buffer(self):
        """
        Process the accumulated audio buffer and get transcription.
        """
        if not self.buffer or self.is_transcribing:
            return
        
        self.is_transcribing = True
        try:
            # Combine all audio chunks
            audio_data = b''.join(self.buffer)
            
            # Convert audio data to the right format for OpenAI API
            # This would depend on the incoming format from the browser
            # For simplicity, assuming it's already in a compatible format
            
            # Use OpenAI's Real-Time API to transcribe
            transcript = await self._transcribe_audio(audio_data)
            
            # Call the callback with the transcription result
            if self.on_transcription_callback and transcript:
                await self.on_transcription_callback(transcript)
        
        finally:
            # Clear the buffer and reset state
            self.buffer = []
            self.is_transcribing = False
    
    async def _transcribe_audio(self, audio_data: bytes) -> str:
        """
        Send audio data to OpenAI's API for transcription.
        
        Args:
            audio_data (bytes): Audio data to transcribe
            
        Returns:
            str: Transcribed text
        """
        # Note: This is a simplified example. The real implementation would 
        # need to handle the details of the OpenAI Real-Time API.
        # According to the documentation (https://platform.openai.com/docs/guides/realtime),
        # this would involve sending chunks to the API and handling streaming responses.
        
        # For this POC, we're using the regular transcription API
        import tempfile
        
        # Create a temporary file to store the audio
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_file_path = temp_file.name
        
        try:
            # Use the OpenAI API to transcribe the audio file
            with open(temp_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            
            return transcript.text
        except Exception as e:
            print(f"Transcription error: {e}")
            return ""
        finally:
            # Clean up the temporary file
            import os
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
    
    async def end_audio_stream(self):
        """
        Signal the end of the audio stream and process remaining buffer.
        """
        await self.process_buffer() 