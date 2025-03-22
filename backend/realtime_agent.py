"""
Real-time voice agent using Deepgram's Voice Agent API with OpenAI tools.
This agent handles streaming audio interactions with voice-only inputs and outputs.
"""
import os
import json
import asyncio
import websockets
from typing import Dict, List, Any, Callable, Awaitable, Optional
import traceback
import logging

# Import tools for the character's actions
from tools import jump, talk, walk, run, push, pull

# Configure logging with more detail
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RealtimeAgent:
    """
    A voice-only agent that uses Deepgram's Voice Agent API for real-time interactions.
    Enables persistent conversational context and tool usage through voice commands.
    """

    def __init__(
        self,
        deepgram_api_key: str,
        voice_id: str = "cgSgspJ2msm6clMCkdW9",  # ElevenLabs voice ID
        llm_model: str = "gpt-4o-mini"
    ):
        """
        Initialize the realtime agent.
        
        Args:
            deepgram_api_key (str): Deepgram API key
            voice_id (str): Voice ID for ElevenLabs TTS
            llm_model (str): Model to use for thinking (gpt-4o, gpt-4o-mini, etc.)
        """
        self.deepgram_api_key = deepgram_api_key
        self.voice_id = voice_id
        self.llm_model = llm_model
        self.websocket = None
        self.is_connected = False
        self.audio_buffer = b""
        self.last_transcription = ""
        
        # Flags to track audio state
        self.received_audio_data = False
        self.audio_chunks_count = 0
        
        # The system instructions for the agent persona
        self.system_instructions = """
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
        
        # Define callbacks
        self.on_transcription_callback = None
        self.on_response_callback = None
        self.on_audio_callback = None
        self.on_command_callback = None

    def set_callbacks(
        self,
        on_transcription: Optional[Callable[[str], Awaitable[None]]] = None,
        on_response: Optional[Callable[[str], Awaitable[None]]] = None,
        on_audio: Optional[Callable[[bytes], Awaitable[None]]] = None,
        on_command: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
    ):
        """
        Set callbacks for various events.
        
        Args:
            on_transcription: Called when user speech is transcribed
            on_response: Called when a text response is generated
            on_audio: Called when audio response is generated
            on_command: Called when a command is detected
        """
        self.on_transcription_callback = on_transcription
        self.on_response_callback = on_response
        self.on_audio_callback = on_audio
        self.on_command_callback = on_command

    async def connect(self):
        """
        Connect to the Deepgram Voice Agent API via WebSocket.
        """
        if self.is_connected:
            logger.info("Already connected to Deepgram Voice Agent API")
            return
        
        try:
            logger.info("Connecting to Deepgram Voice Agent API...")
            # Create WebSocket connection
            self.websocket = await websockets.connect(
                "wss://agent.deepgram.com/agent",
                extra_headers={"Authorization": f"Token {self.deepgram_api_key}"}
            )
            
            # Send initial configuration
            settings_config = {
                "type": "SettingsConfiguration",
                "audio": {
                    "input": {
                        "encoding": "linear16",
                        "sample_rate": 48000
                    },
                    "output": {
                        "encoding": "linear16",
                        "sample_rate": 24000,
                        "container": "none"
                    }
                },
                "agent": {
                    "listen": {
                        "model": "nova-3"
                    },
                    "speak": {
                        "provider": "eleven_labs",
                        "voice_id": self.voice_id
                    },
                    "think": {
                        "model": self.llm_model,
                        "provider": {
                            "type": "open_ai"
                        },
                        "instructions": self.system_instructions,
                        "tools": [
                            {"name": "jump", "description": "Makes the character jump", 
                             "parameters": {"type": "object", "properties": {"direction": {"type": "string", "enum": ["left", "right", "up", "down"]}}, 
                                          "required": []}},
                            {"name": "talk", "description": "Makes the character say something", 
                             "parameters": {"type": "object", "properties": {"message": {"type": "string"}}, 
                                          "required": ["message"]}},
                            {"name": "walk", "description": "Makes the character walk in a specific direction", 
                             "parameters": {"type": "object", "properties": {"direction": {"type": "string", "enum": ["left", "right", "up", "down"]}}, 
                                          "required": ["direction"]}},
                            {"name": "run", "description": "Makes the character run in a specific direction", 
                             "parameters": {"type": "object", "properties": {"direction": {"type": "string", "enum": ["left", "right", "up", "down"]}}, 
                                          "required": ["direction"]}},
                            {"name": "push", "description": "Makes the character push in a specific direction", 
                             "parameters": {"type": "object", "properties": {"direction": {"type": "string", "enum": ["left", "right", "up", "down"]}}, 
                                          "required": ["direction"]}},
                            {"name": "pull", "description": "Makes the character pull in a specific direction", 
                             "parameters": {"type": "object", "properties": {"direction": {"type": "string", "enum": ["left", "right", "up", "down"]}}, 
                                          "required": ["direction"]}}
                        ]
                    }
                },
                "context": {
                    "messages": [
                        {
                            "content": "Hello, how can I help you?",
                            "role": "assistant"
                        }
                    ],
                    "replay": True
                }
            }
            
            await self.websocket.send(json.dumps(settings_config))
            logger.info("Configuration sent to Deepgram Voice Agent API")
            self.is_connected = True
            
            # Start listening for messages from the server
            asyncio.create_task(self._listen_for_server_messages())
            
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to Deepgram Voice Agent API: {e}")
            traceback.print_exc()
            return False

    async def disconnect(self):
        """
        Disconnect from the Deepgram Voice Agent API.
        """
        if self.websocket and self.is_connected:
            try:
                await self.websocket.close()
                logger.info("Disconnected from Deepgram Voice Agent API")
            except Exception as e:
                logger.error(f"Error disconnecting from Deepgram Voice Agent API: {e}")
            finally:
                self.is_connected = False
                self.websocket = None

    async def send_audio(self, audio_data: bytes):
        """
        Send audio data to the Deepgram Voice Agent API.
        
        Args:
            audio_data (bytes): Raw audio data to be sent
        """
        if not self.is_connected or not self.websocket:
            logger.warning("Not connected to Deepgram Voice Agent API. Cannot send audio.")
            return False
        
        try:
            # Send binary audio data
            logger.info(f"Sending {len(audio_data)} bytes of audio data to Deepgram")
            await self.websocket.send(audio_data)
            return True
        except Exception as e:
            logger.error(f"Error sending audio to Deepgram Voice Agent API: {e}")
            return False

    async def _listen_for_server_messages(self):
        """
        Listen for messages from the Deepgram Voice Agent API.
        """
        if not self.websocket:
            logger.error("WebSocket connection not established.")
            return
        
        try:
            while self.is_connected:
                message = await self.websocket.recv()
                
                # Check if the message is binary (audio) or text (JSON)
                if isinstance(message, bytes):
                    # This is audio data from TTS
                    if len(message) > 0:
                        self.audio_chunks_count += 1
                        self.received_audio_data = True
                        # Log first audio chunk and periodic updates
                        if self.audio_chunks_count == 1:
                            logger.info(f"Received first audio chunk: {len(message)} bytes")
                            # Log the first few bytes for debugging
                            first_bytes = ", ".join([f"{b:02x}" for b in message[:20]])
                            logger.info(f"First 20 bytes: {first_bytes}")
                        elif self.audio_chunks_count % 10 == 0:
                            logger.info(f"Received {self.audio_chunks_count} audio chunks so far")
                        
                        # Forward audio data to the callback
                        if self.on_audio_callback:
                            await self.on_audio_callback(message)
                    else:
                        logger.warning("Received empty binary message, ignoring")
                        
                # Special checking for audio end marker - this is a binary representation
                # of the string "__AUDIO_END__" which is 12 bytes long
                elif isinstance(message, bytes) and len(message) == 12:
                    try:
                        text_value = message.decode('utf-8')
                        if text_value == "__AUDIO_END__":
                            logger.info(f"Received __AUDIO_END__ marker after {self.audio_chunks_count} chunks")
                            
                            # Only send the end marker if we actually received audio chunks
                            if self.received_audio_data and self.audio_chunks_count > 0:
                                if self.on_audio_callback:
                                    await self.on_audio_callback(b"__AUDIO_END__")
                            else:
                                logger.warning("No audio chunks received before __AUDIO_END__ marker")
                                
                            # Reset counters
                            self.audio_chunks_count = 0
                            self.received_audio_data = False
                    except:
                        # Not a UTF-8 string, just a binary audio chunk
                        if self.on_audio_callback:
                            await self.on_audio_callback(message)
                else:
                    # This is a JSON message
                    await self._handle_server_message(message)
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Error in WebSocket message listener: {e}")
            traceback.print_exc()
            self.is_connected = False

    async def _handle_server_message(self, message_json: str):
        """
        Handle JSON messages from the Deepgram Voice Agent API.
        
        Args:
            message_json (str): JSON message from the server
        """
        try:
            message = json.loads(message_json)
            message_type = message.get("type")
            
            # Log all received message types
            logger.info(f"Received message of type: {message_type}")
            
            if message_type == "ConversationText":
                # This is the transcription of what the user said
                transcription = message.get("text", "")
                logger.info(f"Transcription: {transcription}")
                self.last_transcription = transcription
                
                if self.on_transcription_callback:
                    await self.on_transcription_callback(transcription)
                    
            elif message_type == "AgentText":
                # This is the response from the agent
                response_text = message.get("text", "")
                logger.info(f"Agent response: {response_text}")
                
                if self.on_response_callback:
                    await self.on_response_callback(response_text)
                    
            elif message_type == "ToolCall":
                # The agent is calling a tool
                tool_name = message.get("name", "")
                tool_params = message.get("parameters", {})
                logger.info(f"Tool call: {tool_name} with parameters {tool_params}")
                
                # Execute the tool and get result
                result = await self._execute_tool(tool_name, tool_params)
                
                # Send the tool result back to the agent
                tool_result = {
                    "type": "ToolCallResult",
                    "id": message.get("id", ""),
                    "result": result
                }
                
                await self.websocket.send(json.dumps(tool_result))
                
                # Call the command callback
                if self.on_command_callback:
                    command_info = {
                        "name": tool_name,
                        "params": tool_params
                    }
                    await self.on_command_callback(command_info)
                    
            elif message_type == "UserStartedSpeaking":
                # User started speaking - we should cancel any queued responses
                logger.info("User started speaking")
                # If we're currently receiving audio, we might want to implement
                # barge-in by sending a special message to stop the current audio
                # Reset audio tracking counters
                self.audio_chunks_count = 0
                self.received_audio_data = False
                
            elif message_type == "UserFinishedSpeaking":
                # User finished speaking
                logger.info("User finished speaking")
                
            elif message_type == "AgentStartedSpeaking":
                # Agent is about to send audio
                logger.info("Agent started speaking, expecting audio data next")
                # Reset audio tracking
                self.audio_chunks_count = 0
                self.received_audio_data = False
                
            elif message_type == "AgentAudioDone":
                # Agent has finished sending audio
                logger.info(f"Agent finished sending audio, received {self.audio_chunks_count} chunks")
                # If we have the callback and received audio, send the end marker
                if self.on_audio_callback and self.received_audio_data and self.audio_chunks_count > 0:
                    await self.on_audio_callback(b"__AUDIO_END__")
                # Reset audio tracking
                self.audio_chunks_count = 0
                self.received_audio_data = False
                
            elif message_type == "Error":
                # Error from the server
                error_message = message.get("message", "Unknown error")
                logger.error(f"Error from Voice Agent API: {error_message}")
                
            elif message_type == "Welcome":
                # Welcome message
                logger.info("Received welcome message from Deepgram Voice Agent API")
                
            elif message_type == "SettingsApplied":
                # Settings applied successfully
                logger.info("Settings applied successfully on Deepgram Voice Agent API")
                
            else:
                # Other messages
                logger.info(f"Received message of type {message_type}: {message_json}")
                
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON message: {message_json}")
        except Exception as e:
            logger.error(f"Error handling server message: {e}")
            traceback.print_exc()

    async def _execute_tool(self, tool_name: str, params: Dict[str, Any]) -> str:
        """
        Execute a tool based on the tool name and parameters.
        
        Args:
            tool_name (str): Name of the tool to execute
            params (Dict[str, Any]): Parameters for the tool
            
        Returns:
            str: Result of the tool execution
        """
        try:
            result = ""
            
            if tool_name == "jump":
                direction = params.get("direction")
                result = jump(direction)
                
            elif tool_name == "talk":
                message = params.get("message", "")
                result = talk(message)
                
            elif tool_name == "walk":
                direction = params.get("direction")
                result = walk(direction)
                
            elif tool_name == "run":
                direction = params.get("direction")
                result = run(direction)
                
            elif tool_name == "push":
                direction = params.get("direction")
                result = push(direction)
                
            elif tool_name == "pull":
                direction = params.get("direction")
                result = pull(direction)
                
            return result
        except Exception as e:
            error_msg = f"Error executing tool {tool_name}: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    async def inject_message(self, message: str):
        """
        Inject a message into the conversation, as if the user had said it.
        
        Args:
            message (str): Message to inject
        """
        if not self.is_connected or not self.websocket:
            logger.warning("Not connected to Deepgram Voice Agent API. Cannot inject message.")
            return False
        
        try:
            inject_message = {
                "type": "InjectConversationMessage",
                "text": message
            }
            
            await self.websocket.send(json.dumps(inject_message))
            logger.info(f"Injected message: {message}")
            return True
        except Exception as e:
            logger.error(f"Error injecting message: {e}")
            return False

    async def update_instructions(self, new_instructions: str):
        """
        Update the agent's instructions.
        
        Args:
            new_instructions (str): New instructions for the agent
        """
        if not self.is_connected or not self.websocket:
            logger.warning("Not connected to Deepgram Voice Agent API. Cannot update instructions.")
            return False
        
        try:
            update_message = {
                "type": "UpdateInstructions",
                "instructions": new_instructions
            }
            
            await self.websocket.send(json.dumps(update_message))
            self.system_instructions = new_instructions
            logger.info("Agent instructions updated")
            return True
        except Exception as e:
            logger.error(f"Error updating instructions: {e}")
            return False 