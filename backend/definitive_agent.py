"""
Definitive agent that combines Deepgram for transcription with OpenAI for agent-based responses.
This agent handles both text and audio inputs and processes them through OpenAI's assistant API.
"""
import os
import asyncio
from typing import Dict, Any, List, Callable, Awaitable, Tuple, Optional
import tempfile
import json
import traceback

from openai import OpenAI
from deepgram import DeepgramClient, PrerecordedOptions, FileSource

from tools import jump, walk, run as run_action, push, pull


class DefinitiveAgent:
    """
    A unified agent that handles both text and voice inputs.
    Uses Deepgram for fast speech-to-text and OpenAI for agent-based decisions.
    """

    def __init__(
        self, 
        openai_api_key: str, 
        deepgram_api_key: str = os.getenv("DEEPGRAM_API_KEY"),
        voice: str = "nova"
    ):
        """
        Initialize the definitive agent.

        Args:
            openai_api_key (str): OpenAI API key
            deepgram_api_key (str): Deepgram API key, defaults to environment variable
            voice (str): Voice to use for TTS (e.g., alloy, echo, fable, onyx, nova, shimmer)
        """
        self.openai_key = openai_api_key
        self.voice = voice
        self.openai_client = OpenAI(api_key=openai_api_key)
        
        # Initialize the agent data with the OpenAI client and assistant
        self.agent_data = self.setup_agent(openai_api_key)
        
        # Initialize Deepgram client with fallback options
        try:
            self.deepgram_client = DeepgramClient(api_key=deepgram_api_key)
            print("Initialized Deepgram client with explicit api_key parameter")
        except Exception as e:
            print(f"Failed to initialize Deepgram client with api_key parameter: {e}")
            try:
                self.deepgram_client = DeepgramClient(deepgram_api_key)
                print("Initialized Deepgram client with positional parameter")
            except Exception as e:
                print(f"Failed to initialize Deepgram client with positional parameter: {e}")
                from deepgram import DeepgramClientOptions
                self.deepgram_client = DeepgramClient(deepgram_api_key, DeepgramClientOptions())
                print("Initialized Deepgram client with DeepgramClientOptions")

    def setup_agent(self, api_key: str) -> Dict:
        """
        Set up the OpenAI agent with the character's personality and tools.
        
        Args:
            api_key (str): OpenAI API key
            
        Returns:
            Dict: Agent data containing client and assistant
        """
        # Create OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Define the character's personality in the system prompt
        system_prompt = """
        You are a funny, ironic, non-binary videogame character called Jan "The Man" with a witty personality. 
        Your responses should be concise, entertaining, and reflect your unique personality.
        When users give you commands or ask questions, you can respond in two ways:
        1. With a simple text response when having a conversation
        2. By using one of your available tools/actions when asked to perform specific tasks
        
        You can perform various movement actions in different directions (left, right, up, down).
        For example, if someone asks you to "jump up" or "walk to the left", use the appropriate
        directional action.

        Always prefer to execute the action instead of talking.

        If they ask you to perform an action and no direction is specified, you should perform it
        in the direction you are facing. If you are not facing any direction, you should perform 
        the action with direction "down".

        The chat is at a panel on your right side.
        The commands and buttons for animation are at a panel on your left side.
        The browser navigation buttons are at the top of the screen.

        Also, when someone asks you what can you do, you should respond with a simple list of your 
        available tools.
        
        Keep your responses brief and entertaining!
        """
        
        # Create a new assistant with the tools
        assistant = client.beta.assistants.create(
            name="Game Character",
            instructions=system_prompt,
            tools=[
                {"type": "function", "function": {"name": "jump", "description": "Makes the character jump", 
                                                "parameters": {"type": "object", "properties": {"direction": {"type": "string", "enum": ["left", "right", "up", "down"]}}, 
                                                            "required": []}}},
                {"type": "function", "function": {"name": "walk", "description": "Makes the character walk in a specific direction", 
                                                "parameters": {"type": "object", "properties": {"direction": {"type": "string", "enum": ["left", "right", "up", "down"]}}, 
                                                            "required": ["direction"]}}},
                {"type": "function", "function": {"name": "run", "description": "Makes the character run in a specific direction", 
                                                "parameters": {"type": "object", "properties": {"direction": {"type": "string", "enum": ["left", "right", "up", "down"]}}, 
                                                            "required": ["direction"]}}},
                {"type": "function", "function": {"name": "push", "description": "Makes the character push in a specific direction", 
                                                "parameters": {"type": "object", "properties": {"direction": {"type": "string", "enum": ["left", "right", "up", "down"]}}, 
                                                            "required": ["direction"]}}},
                {"type": "function", "function": {"name": "pull", "description": "Makes the character pull in a specific direction", 
                                                "parameters": {"type": "object", "properties": {"direction": {"type": "string", "enum": ["left", "right", "up", "down"]}}, 
                                                            "required": ["direction"]}}}
            ],
            model="gpt-4o"
        )
        
        return {"client": client, "assistant": assistant}

    async def transcribe_audio(self, audio_data: bytes) -> str:
        """
        Transcribe audio data using Deepgram with optimized settings for speed.
        
        Args:
            audio_data (bytes): Raw audio data to transcribe
            
        Returns:
            str: The transcribed text
        """
        try:
            print(f"Transcribing audio data of size: {len(audio_data)} bytes")
            
            # Create payload with buffer
            payload: FileSource = {
                "buffer": audio_data,
            }
            
            # Configure Deepgram transcription options optimized for speed
            # No intents detection to keep it fast
            options = PrerecordedOptions(
                model="nova-2",  # nova-2 is faster
                smart_format=True,
                punctuate=False,
                intents=False,  # Disable intent detection for speed
                utterances=False,
                language="en"
            )
            
            try:
                # First attempt with direct buffer transcription
                response = self.deepgram_client.listen.rest.v("1").transcribe_file(payload, options)
                print("Successfully transcribed using listen.rest.v(1).transcribe_file")
            except Exception as e:
                print(f"Error using transcribe_file: {e}")
                
                # Fallback to alternative API structure
                try:
                    response = self.deepgram_client.listen.prerecorded.v("1").transcribe_file(payload, options)
                    print("Successfully used listen.prerecorded.v(1).transcribe_file method")
                except Exception as e2:
                    print(f"Error using prerecorded.transcribe_file: {e2}")
                    
                    # Last resort: Use a temporary file
                    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
                        temp_file.write(audio_data)
                        temp_file_path = temp_file.name
                    
                    try:
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
                return ""
                
            transcription = response.results.channels[0].alternatives[0].transcript
            print(f"Deepgram transcription: '{transcription}'")
            
            return transcription
            
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            traceback.print_exc()
            return ""

    async def process_text_input(
        self, 
        user_input: str, 
        conversation_history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process text input through the OpenAI agent.
        
        Args:
            user_input (str): User message to process
            conversation_history (List[Dict[str, Any]], optional): Previous conversation history
            
        Returns:
            Dict[str, Any]: Response containing text and/or command information
        """
        return await self.process_user_input(self.agent_data, user_input, conversation_history)

    async def process_audio(
        self,
        audio_data: bytes,
        on_transcription: Callable[[str], Awaitable[None]],
        on_response: Callable[[str], Awaitable[None]],
        on_audio: Callable[[bytes], Awaitable[None]],
        conversation_history: List[Dict[str, Any]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Process audio data: transcribe with Deepgram and then process through OpenAI agent.

        Args:
            audio_data (bytes): Raw audio data from the client
            on_transcription (Callable[[str], Awaitable[None]]): Callback for transcription results
            on_response (Callable[[str], Awaitable[None]]): Callback for text responses
            on_audio (Callable[[bytes], Awaitable[None]]): Callback for audio responses
            conversation_history (List[Dict[str, Any]], optional): Previous conversation history

        Returns:
            Tuple[str, Dict[str, Any]]: A tuple containing the final response text and a command info dict
        """
        try:
            # Transcribe the audio with Deepgram
            transcription = await self.transcribe_audio(audio_data)
            
            # Notify about the transcription
            if transcription:
                await on_transcription(transcription)
            else:
                print("No transcription was produced")
                await on_response("I couldn't understand what you said. Can you try again?")
                return "I couldn't understand what you said. Can you try again?", {"name": "", "params": {}}
            
            # Process the transcription with the OpenAI agent
            response_data, conversation_history = await self.process_user_input(
                self.agent_data, 
                transcription, 
                conversation_history
            )
            
            # Extract text content and command info
            response_text = ""
            command_info = {"name": "", "params": {}}
            
            if response_data["type"] == "text":
                voice = self.voice
                response_text = response_data["content"]
                await on_response(response_text)
            elif response_data["type"] == "command":
                voice = "shimmer"
                response_text = response_data["result"]
                command_info = {
                    "name": response_data["name"],
                    "params": response_data.get("params", {})
                }

            # Generate speech from the text response
            print(f"Generating speech for response: '{response_text}'")
            speech_response = self.openai_client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=response_text
            )
            
            # Send audio chunks to client
            collected_audio = bytearray()
            for chunk in speech_response.iter_bytes():
                collected_audio.extend(chunk)
                await on_audio(chunk)
            
            # Save the output audio for debugging
            # output_filename = "output.mp3"
            # with open(output_filename, "wb") as f:
            #     f.write(collected_audio)
            # print(f"Audio saved to {output_filename}, total size: {len(collected_audio)} bytes")
            
            # Send the audio end marker
            print("Sending __AUDIO_END__ marker")
            await on_audio(b"__AUDIO_END__")
            
            return response_text, command_info
            
        except Exception as e:
            print(f"Error processing audio: {e}")
            traceback.print_exc()
            await on_response(f"Sorry, I had trouble processing that. {str(e)}")
            return f"Error: {str(e)}", {"name": "", "params": {}}

    async def process_user_input(
        self, 
        agent_data: Dict, 
        user_input: str, 
        conversation_history: List[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Process user input through the agent, invoking tools if needed.
        
        Args:
            agent_data (Dict): The configured agent data (client and assistant)
            user_input (str): User message to process
            conversation_history (List[Dict[str, Any]], optional): Previous conversation history
            
        Returns:
            Tuple[Dict[str, Any], List[Dict[str, Any]]]: Response containing text/command info and updated conversation history
        """
        client = agent_data["client"]
        assistant = agent_data["assistant"]
        
        if conversation_history is None:
            conversation_history = []
        
        # Create a new thread if we don't have one yet
        if "thread_id" not in agent_data:
            thread = client.beta.threads.create()
            agent_data["thread_id"] = thread.id
        
        # Add the user message to the thread
        client.beta.threads.messages.create(
            thread_id=agent_data["thread_id"],
            role="user",
            content=user_input
        )
        
        # Run the assistant on the thread
        run_response = client.beta.threads.runs.create(
            thread_id=agent_data["thread_id"],
            assistant_id=assistant.id
        )
        
        # Wait for the run to complete
        while run_response.status in ["queued", "in_progress"]:
            run_response = client.beta.threads.runs.retrieve(
                thread_id=agent_data["thread_id"],
                run_id=run_response.id
            )
            if run_response.status in ["queued", "in_progress"]:
                await asyncio.sleep(0.5)
        
        # Handle tool calls if any
        if run_response.status == "requires_action":
            tool_outputs = []
            response = None
            
            for tool_call in run_response.required_action.submit_tool_outputs.tool_calls:
                function_name = tool_call.function.name
                arguments = tool_call.function.arguments
                args = json.loads(arguments)
                
                # Execute the appropriate tool
                if function_name == "jump":
                    direction = args.get("direction")
                    result = jump(direction)
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": result
                    })
                    
                    # Prepare response for the client
                    response = {
                        "type": "command",
                        "name": "jump",
                        "result": result,
                        "params": {"direction": direction}
                    }
                    
                elif function_name == "walk":
                    direction = args.get("direction")
                    result = walk(direction)
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": result
                    })
                    
                    # Prepare response for the client
                    response = {
                        "type": "command",
                        "name": "walk",
                        "result": result,
                        "params": {"direction": direction}
                    }
                    
                elif function_name == "run":
                    direction = args.get("direction")
                    result = run_action(direction)
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": result
                    })
                    
                    # Prepare response for the client
                    response = {
                        "type": "command",
                        "name": "run",
                        "result": result,
                        "params": {"direction": direction}
                    }
                    
                elif function_name == "push":
                    direction = args.get("direction")
                    result = push(direction)
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": result
                    })
                    
                    # Prepare response for the client
                    response = {
                        "type": "command",
                        "name": "push",
                        "result": result,
                        "params": {"direction": direction}
                    }
                    
                elif function_name == "pull":
                    direction = args.get("direction")
                    result = pull(direction)
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": result
                    })
                    
                    # Prepare response for the client
                    response = {
                        "type": "command",
                        "name": "pull",
                        "result": result,
                        "params": {"direction": direction}
                    }
            
            # Submit the tool outputs back to the assistant
            if tool_outputs:
                run_response = client.beta.threads.runs.submit_tool_outputs(
                    thread_id=agent_data["thread_id"],
                    run_id=run_response.id,
                    tool_outputs=tool_outputs
                )
                
                # Wait for processing to complete
                while run_response.status in ["queued", "in_progress"]:
                    run_response = client.beta.threads.runs.retrieve(
                        thread_id=agent_data["thread_id"],
                        run_id=run_response.id
                    )
                    if run_response.status in ["queued", "in_progress"]:
                        await asyncio.sleep(0.5)
            
            if response:
                return response, conversation_history
        
        # Get the assistant's response
        messages = client.beta.threads.messages.list(
            thread_id=agent_data["thread_id"]
        )
        
        # Get the most recent assistant message
        assistant_messages = [msg for msg in messages.data if msg.role == "assistant"]
        if assistant_messages:
            latest_message = assistant_messages[0].content[0].text.value
            response = {
                "type": "text",
                "content": latest_message
            }
        else:
            response = {
                "type": "text",
                "content": "I'm not sure what to say. Can you try again?"
            }
        
        # Update conversation history
        # This is a simplified version that could be expanded as needed
        
        return response, conversation_history 