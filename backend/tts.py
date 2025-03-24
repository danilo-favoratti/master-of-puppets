"""
Text-to-speech synthesis using OpenAI's API.
"""
from io import BytesIO
from typing import Optional

from openai import OpenAI


class TextToSpeech:
    """
    Handles text-to-speech synthesis using OpenAI's API.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the TTS engine with API credentials.
        
        Args:
            api_key (str): OpenAI API key
        """
        self.client = OpenAI(api_key=api_key)
    
    async def synthesize_speech(self, text: str, voice: str = "alloy") -> Optional[bytes]:
        """
        Convert text to speech using OpenAI's API.
        
        Args:
            text (str): The text to convert to speech
            voice (str): The voice to use (alloy, echo, fable, onyx, nova, shimmer)
            
        Returns:
            bytes: Audio data in MP3 format
        """
        try:
            # Limit text length to avoid errors
            if len(text) > 4000:
                text = text[:4000]
            
            # Use OpenAI's API to convert text to speech
            response = self.client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text
            )
            
            # Get the audio data
            buffer = BytesIO()
            response.stream_to_file(buffer)
            buffer.seek(0)
            return buffer.read()
            
        except Exception as e:
            print(f"TTS error: {e}")
            return None
    
    async def generate_audio_chunks(self, text: str, voice: str = "alloy", chunk_size: int = 200):
        """
        Generate audio chunks for longer text by splitting it into sentences.
        
        Args:
            text (str): The text to convert to speech
            voice (str): The voice to use
            chunk_size (int): Maximum size of each text chunk
            
        Yields:
            bytes: Audio data chunks in MP3 format
        """
        # Split text into sentences
        sentences = text.replace(".", ". ").replace("!", "! ").replace("?", "? ").split()
        
        # Create chunks of sentences that don't exceed chunk_size
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= chunk_size:
                current_chunk += " " + sentence
            else:
                # Add current chunk to the list if it's not empty
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        # Add the last chunk if there is one
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # Generate audio for each chunk
        for chunk in chunks:
            audio_data = await self.synthesize_speech(chunk, voice)
            if audio_data:
                yield audio_data 