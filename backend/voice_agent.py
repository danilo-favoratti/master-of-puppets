import os
import json
import numpy as np
import asyncio
from typing import Dict, Callable, Awaitable, Tuple
from openai import OpenAI
import io

# We'll use the OpenAI SDK directly for voice features instead of the agents SDK
class VoiceAgentManager:
    """
    A simplified version of the voice agent that doesn't rely on the problematic
    voice modules from the OpenAI Agents SDK.
    """

    def __init__(self, api_key: str, voice: str = "nova"):
        """
        Initialize the voice agent manager.

        Args:
            api_key (str): OpenAI API key.
            voice (str): Voice to use for TTS (e.g., alloy, echo, fable, onyx, nova, shimmer).
        """
        self.api_key = api_key
        self.voice = voice
        self.client = OpenAI(api_key=api_key)
        
    async def process_audio(
            self,
            audio_data: bytes,
            on_transcription: Callable[[str], Awaitable[None]],
            on_response: Callable[[str], Awaitable[None]],
            on_audio: Callable[[bytes], Awaitable[None]],
    ) -> Tuple[str, Dict[str, any]]:
        """
        Process audio data through direct OpenAI API calls.

        Args:
            audio_data (bytes): Raw audio data from the client.
            on_transcription (Callable[[str], Awaitable[None]]): Callback for transcription results.
            on_response (Callable[[str], Awaitable[None]]): Callback for text responses.
            on_audio (Callable[[bytes], Awaitable[None]]): Callback for audio responses.

        Returns:
            Tuple[str, Dict[str, any]]: A tuple containing the final response text and a command info dict.
        """
        try:
            # Wrap the raw audio bytes in an in-memory bytes buffer.
            audio_buffer = io.BytesIO(audio_data)
            audio_buffer.name = "audio.webm"
            
            # Use OpenAI to transcribe the audio
            transcription = self.client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_buffer
            ).text
            
            await on_transcription(transcription)
            
            # Process the command using OpenAI's assistant API
            # Here we're parsing for movement commands
            messages = [
                {"role": "system", "content": (
                    "You're a quirky, non-binary 2D game character with a personality that's both witty and ironic.\n\n"
                    "You communicate with the player and respond to their commands. Always keep your responses concise, "
                    "friendly, and in-character.\n\n"
                    "You have the following abilities:\n"
                    "- Walking in four directions (up, down, left, right)\n"
                    "- Running in four directions\n"
                    "- Jumping (up, down, left, right)\n"
                    "- Pushing objects (up, down, left, right)\n"
                    "- Pulling objects (up, down, left, right)\n\n"
                    "For navigation commands, always respond with a JSON object detailing the command and direction, like:\n"
                    '{"command": "walk", "direction": "left"}\n'
                    '{"command": "run", "direction": "up"}\n'
                    '{"command": "jump", "direction": "up"}\n'
                    "For general conversation, be friendly and quirky. Never refuse valid movement commands."
                )},
                {"role": "user", "content": transcription}
            ]
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                response_format={"type": "text"}
            )
            
            response_text = response.choices[0].message.content
            
            # Parse the response for command information
            command_info = {"name": "", "params": {}}
            json_part = None  # Initialize json_part
            try:
                # Check if the response contains JSON
                if "{" in response_text and "}" in response_text:
                    json_part = response_text[response_text.find("{"):response_text.rfind("}")+1]
                    cmd_data = json.loads(json_part)
                    if "command" in cmd_data and "direction" in cmd_data:
                        command_info["name"] = cmd_data["command"]
                        command_info["params"] = {"direction": cmd_data["direction"]}
                        # If the entire response is just JSON, replace it with a friendly message
                        if response_text.strip() == json_part:
                            if cmd_data["command"] == "walk" and cmd_data["direction"] == "left":
                                response_text = "Ah, the classic leftward journey! It's like going back in time, but with fewer dinosaurs! 🦖✨"
                            else:
                                response_text = f"{cmd_data['command']}ing {cmd_data['direction']}"
                        else:
                            # Otherwise, remove the JSON portion from the response
                            response_text = response_text.replace(json_part, "").strip()
            except json.JSONDecodeError:
                # If not valid JSON, look for keywords
                lower_text = response_text.lower()
                for cmd in ["walk", "run", "jump", "push", "pull"]:
                    if cmd in lower_text:
                        command_info["name"] = cmd
                        for direction in ["up", "down", "left", "right"]:
                            if direction in lower_text:
                                command_info["params"] = {"direction": direction}
                                break
                        if not command_info["params"] and cmd == "jump":
                            command_info["params"] = {"direction": "up"}  # Default for jump
                        break
            
            # Ensure JSON is filtered out before sending the response
            if json_part:
                response_text = response_text.replace(json_part, "").strip()
            await on_response(response_text)
            
            # Generate speech from the text response
            print(f"Generating speech for response: '{response_text}'")
            speech_response = self.client.audio.speech.create(
                model="tts-1",
                voice=self.voice,
                input=response_text
            )
            
            # Get binary audio data
            collected_audio = bytearray()
            chunk_count = 0
            print(f"Starting audio chunk streaming for response: '{response_text[:30]}...'")
            
            # Check if speech_response is None or empty
            if not speech_response:
                print("ERROR: speech_response is empty or None")
                # Send an empty response
                await on_audio(b"__AUDIO_END__")
                return response_text, command_info
            
            for chunk in speech_response.iter_bytes():
                collected_audio.extend(chunk)
                chunk_count += 1
                print(f"Sending audio chunk {chunk_count}: {len(chunk)} bytes")
                await on_audio(chunk)
            
            # Save the output audio
            output_filename = "output.mp3"
            with open(output_filename, "wb") as f:
                f.write(collected_audio)
            print(f"Audio saved to {output_filename}, total size: {len(collected_audio)} bytes in {chunk_count} chunks")
            print("Sending __AUDIO_END__ marker")
            await on_audio(b"__AUDIO_END__")

            return response_text, command_info

        except Exception as e:
            print(f"Error processing audio: {e}")
            import traceback
            traceback.print_exc()
            raise 