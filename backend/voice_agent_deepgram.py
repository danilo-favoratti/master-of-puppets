"""
Voice transcription and processing using Deepgram API with intent detection.
"""
import os
import json
import numpy as np
import asyncio
from typing import Dict, Callable, Awaitable, Tuple
from deepgram import DeepgramClient, PrerecordedOptions, FileSource
from openai import OpenAI
import io

class VoiceAgentManager:
    """
    A voice agent manager implementation that uses Deepgram for transcription and intent detection
    and OpenAI for response generation and text-to-speech.
    """

    def __init__(self, api_key: str, voice: str = "nova", deepgram_api_key: str = os.getenv("DEEPGRAM_API_KEY")):
        """
        Initialize the voice agent manager.

        Args:
            api_key (str): OpenAI API key.
            voice (str): Voice to use for TTS (e.g., alloy, echo, fable, onyx, nova, shimmer).
            deepgram_api_key (str): Deepgram API key (defaults to DEEPGRAM_API_KEY environment variable).
        """
        self.openai_key = api_key
        self.voice = voice
        self.openai_client = OpenAI(api_key=api_key)
        
        # Initialize Deepgram client
        try:
            # Try with explicit API key parameter (v2+ style)
            self.deepgram_client = DeepgramClient(api_key=deepgram_api_key)
            print("Initialized Deepgram client with explicit api_key parameter")
        except Exception as e:
            print(f"Failed to initialize Deepgram client with api_key parameter: {e}")
            try:
                # Try with positional parameter (v3+ style)
                self.deepgram_client = DeepgramClient(deepgram_api_key)
                print("Initialized Deepgram client with positional parameter")
            except Exception as e:
                print(f"Failed to initialize Deepgram client with positional parameter: {e}")
                # Last resort: follow documentation exactly
                from deepgram import DeepgramClientOptions
                self.deepgram_client = DeepgramClient(deepgram_api_key, DeepgramClientOptions())
                print("Initialized Deepgram client with DeepgramClientOptions")
        
    async def process_audio(
            self,
            audio_data: bytes,
            on_transcription: Callable[[str], Awaitable[None]],
            on_response: Callable[[str], Awaitable[None]],
            on_audio: Callable[[bytes], Awaitable[None]],
    ) -> Tuple[str, Dict[str, any]]:
        """
        Process audio data through Deepgram for transcription and intent detection, then OpenAI for response.

        Args:
            audio_data (bytes): Raw audio data from the client.
            on_transcription (Callable[[str], Awaitable[None]]): Callback for transcription results.
            on_response (Callable[[str], Awaitable[None]]): Callback for text responses.
            on_audio (Callable[[bytes], Awaitable[None]]): Callback for audio responses.

        Returns:
            Tuple[str, Dict[str, any]]: A tuple containing the final response text and a command info dict.
        """
        try:
            # Set up audio data for Deepgram processing
            print(f"Received audio data of size: {len(audio_data)} bytes")
            # Print first few bytes to verify content
            print(f"First 20 bytes of audio: {audio_data[:20]}")
            
            # Create payload with buffer
            payload: FileSource = {
                "buffer": audio_data,
            }
            
            # Configure Deepgram transcription options with intent detection enabled
            options = PrerecordedOptions(
                model="nova-3",
                smart_format=True,
                punctuate=True,
                intents=True,  # Enable intent detection
                utterances=False,
                language="en",  # Specify English language
                keyterm=["walk", "run", "jump", "push", "pull", "left", "right", "up", "down"]  # Add keywords boost for commands
            )
            
            # Process audio with Deepgram
            print(f"Sending audio to Deepgram for transcription and intent detection")
            
            try:
                # First try with the REST API (normal approach)
                response = self.deepgram_client.listen.rest.v("1").transcribe_file(payload, options)
                print("Successfully used listen.rest.v(1).transcribe_file method")
            except Exception as e:
                print(f"Error using transcribe_file: {e}")
                # Fallback approach - try different API styles that might be in different SDK versions
                try:
                    # Try alternative API structure
                    response = self.deepgram_client.listen.prerecorded.v("1").transcribe_file(payload, options)
                    print("Successfully used listen.prerecorded.v(1).transcribe_file method")
                except Exception as e2:
                    print(f"Error using prerecorded.transcribe_file: {e2}")
                    # Create a temporary file as a last resort
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
                        temp_file.write(audio_data)
                        temp_file_path = temp_file.name
                    
                    try:
                        # Try with a real file
                        with open(temp_file_path, 'rb') as audio_file:
                            file_payload = {"file": audio_file}
                            response = self.deepgram_client.listen.rest.v("1").transcribe_file(file_payload, options)
                        print("Successfully used temporary file method")
                    except Exception as e3:
                        print(f"All transcription methods failed: {e3}")
                        raise Exception(f"Could not transcribe audio: {e}, {e2}, {e3}")
                    finally:
                        # Clean up temp file
                        import os
                        os.unlink(temp_file_path)
            
            # Extract the transcription
            if not response.results:
                print("No transcription results from Deepgram")
                return "", {"name": "", "params": {}}
                
            transcription = response.results.channels[0].alternatives[0].transcript
            print(f"Deepgram transcription: '{transcription}'")
            
            # Send transcription to callback
            if transcription:
                await on_transcription(transcription)
            
            # Extract intent information if available
            command_info = {"name": "", "params": {}}
            if hasattr(response.results, 'intents') and response.results.intents:
                # Parse the intents from Deepgram
                try:
                    for segment in response.results.intents.segments:
                        if segment.intents and len(segment.intents) > 0:
                            # Take the intent with highest confidence
                            primary_intent = segment.intents[0]
                            intent_text = primary_intent.intent.lower()
                            confidence = primary_intent.confidence_score
                            
                            print(f"Detected intent: {intent_text} (confidence: {confidence})")
                            
                            # Map detected intents to game commands
                            # This mapping is based on expected Deepgram intent outputs
                            if any(cmd in intent_text for cmd in ["walk", "move", "go"]):
                                command_info["name"] = "walk"
                                for direction in ["up", "down", "left", "right"]:
                                    if direction in intent_text:
                                        command_info["params"] = {"direction": direction}
                                        break
                            
                            elif any(cmd in intent_text for cmd in ["run", "sprint", "hurry"]):
                                command_info["name"] = "run"
                                for direction in ["up", "down", "left", "right"]:
                                    if direction in intent_text:
                                        command_info["params"] = {"direction": direction}
                                        break
                            
                            elif any(cmd in intent_text for cmd in ["jump", "leap", "hop"]):
                                command_info["name"] = "jump"
                                for direction in ["up", "down", "left", "right"]:
                                    if direction in intent_text:
                                        command_info["params"] = {"direction": direction}
                                        break
                                # Set default direction for jump if none specified
                                if not command_info["params"]:
                                    command_info["params"] = {"direction": "up"}
                            
                            elif any(cmd in intent_text for cmd in ["push", "shove", "move"]):
                                command_info["name"] = "push"
                                for direction in ["up", "down", "left", "right"]:
                                    if direction in intent_text:
                                        command_info["params"] = {"direction": direction}
                                        break
                            
                            elif any(cmd in intent_text for cmd in ["pull", "drag", "tug"]):
                                command_info["name"] = "pull"
                                for direction in ["up", "down", "left", "right"]:
                                    if direction in intent_text:
                                        command_info["params"] = {"direction": direction}
                                        break
                            
                            # Only use the first detected intent with a command
                            if command_info["name"]:
                                break
                
                except (AttributeError, IndexError) as e:
                    print(f"Error parsing Deepgram intents: {e}")
            
            # If no intent was detected from Deepgram, use a fallback approach
            # to check for command words directly in the transcript
            if not command_info["name"] and transcription:
                lower_text = transcription.lower()
                print(f"Using fallback intent detection for: '{lower_text}'")
                
                # Check for common transcription errors and known substitutions
                transcription_fixes = {
                    "wall": "walk",
                    "class": "left",
                    "write": "right",
                    "up word": "upward",
                    "don": "down",
                    "let": "left",
                    "laughed": "left",
                    "jumped": "jump",
                    "walking": "walk",
                    "running": "run",
                    "jumping": "jump",
                    "pushing": "push",
                    "pulling": "pull"
                }
                
                # Apply fixes to the text
                for error, fix in transcription_fixes.items():
                    if error in lower_text:
                        print(f"Fixing transcription: '{error}' -> '{fix}'")
                        lower_text = lower_text.replace(error, fix)
                
                print(f"After fixes: '{lower_text}'")
                
                # Fuzzy detection for commands
                for cmd in ["walk", "run", "jump", "push", "pull"]:
                    # Direct word match
                    if cmd in lower_text:
                        command_info["name"] = cmd
                        print(f"Detected command: {cmd}")
                
                # If we found a command, look for directions
                if command_info["name"]:
                    for direction in ["up", "down", "left", "right"]:
                        if direction in lower_text:
                            command_info["params"] = {"direction": direction}
                            print(f"Detected direction: {direction}")
                            break
                    
                    # Special handling for directional phrases
                    if "go up" in lower_text or "upward" in lower_text:
                        command_info["params"] = {"direction": "up"}
                    elif "go down" in lower_text or "downward" in lower_text:
                        command_info["params"] = {"direction": "down"}
                    elif "go left" in lower_text or "leftward" in lower_text:
                        command_info["params"] = {"direction": "left"}
                    elif "go right" in lower_text or "rightward" in lower_text:
                        command_info["params"] = {"direction": "right"}
                    
                    # Default directions if none detected
                    if not command_info["params"] and command_info["name"] == "jump":
                        command_info["params"] = {"direction": "up"}  # Default for jump
                    elif not command_info["params"]:
                        # Try to guess direction from context
                        if "forward" in lower_text:
                            command_info["params"] = {"direction": "up"}
                        elif "backward" in lower_text or "back" in lower_text:
                            command_info["params"] = {"direction": "down"}
                        else:
                            command_info["params"] = {"direction": "right"}  # Default direction
                
                print(f"Final command: {command_info['name']} {command_info['params']}")
            
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
            
         
            # If we already detected a command, let the AI know directly instead of having it guess
            if command_info["name"]:
                direction = command_info["params"].get("direction", "")
                messages[0]["content"] += f"\nThe user has requested the '{command_info['name']}' command in the '{direction}' direction. Acknowledge this in your response."
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.7,
                response_format={"type": "text"}
            )
            
            response_text = response.choices[0].message.content
            
            # If a command was detected, create special responses
            if command_info["name"] and command_info["params"].get("direction"):
                cmd = command_info["name"]
                direction = command_info["params"]["direction"]
                
                response_text = f"{cmd.capitalize()}ing {direction}? You got it! Let's go!"
            
            await on_response(response_text)
            
            # Generate speech from the text response
            print(f"Generating speech for response: '{response_text}'")
            speech_response = self.openai_client.audio.speech.create(
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
            
            # Check for the response object type - debug
            print(f"Speech response type: {type(speech_response)}")
            
            try:
                # Get detailed info on the speech response
                print(f"Speech response object attributes: {dir(speech_response)}")
            except Exception as e:
                print(f"Cannot inspect speech response object: {e}")
            
            try:
                # First read all chunks into memory to get total size
                all_chunks = []
                for chunk in speech_response.iter_bytes():
                    all_chunks.append(chunk)
                    collected_audio.extend(chunk)
                    chunk_count += 1
                
                # Wait after sending audio_start to ensure client is ready
                await asyncio.sleep(0.1)
                
                # Then send chunks with proper pacing
                for i, chunk in enumerate(all_chunks):
                    chunk_size = len(chunk)
                    print(f"Sending audio chunk {i+1}/{len(all_chunks)}: {chunk_size} bytes")
                    # Also print first few bytes of each chunk for debugging
                    if chunk_size > 0:
                        print(f"Chunk {i+1} first 10 bytes: {chunk[:10]}")
                    await on_audio(chunk)
                    # Small delay between chunks to prevent overwhelming the client
                    await asyncio.sleep(0.01)
                
                print(f"Total chunks sent: {chunk_count}")
            except Exception as e:
                print(f"Error in audio chunk streaming: {e}")
                import traceback
                traceback.print_exc()
            
            # Save the output audio
            output_filename = "output.mp3"
            with open(output_filename, "wb") as f:
                f.write(collected_audio)
            print(f"Audio saved to {output_filename}, total size: {len(collected_audio)} bytes in {chunk_count} chunks")
            
            # Allow some time before sending the end marker
            await asyncio.sleep(0.1)
            
            # Make sure we send the audio end marker
            print("Sending __AUDIO_END__ marker")
            try:
                await on_audio(b"__AUDIO_END__")
                print("__AUDIO_END__ marker sent successfully")
            except Exception as e:
                print(f"Error sending __AUDIO_END__ marker: {e}")
                traceback.print_exc()

            return response_text, command_info

        except Exception as e:
            print(f"Error processing audio: {e}")
            import traceback
            traceback.print_exc()
            raise 