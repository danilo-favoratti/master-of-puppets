# Realtime Voice Agent with Deepgram

This module provides a real-time voice agent implementation using Deepgram's Voice Agent API. The agent allows for continuous, streaming voice interactions with a virtual character called Jan "The Man".

## Features

- Real-time voice streaming with low latency
- Voice recognition using Deepgram's Nova-3 model
- Text-to-speech using ElevenLabs voices
- Tool execution based on voice commands
- Barge-in capability (user can interrupt the agent)

## Prerequisites

- Python 3.8+
- [Deepgram API Key](https://console.deepgram.com/signup)
- (Optional) An ElevenLabs account for custom voices

## Installation

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set up your environment variables:

Create a `.env` file with your API keys:

```
DEEPGRAM_API_KEY=your_deepgram_api_key
```

## Usage

### Basic Example

Run the simple example:

```bash
python example_realtime_agent.py
```

This will:
1. Connect to Deepgram's Voice Agent API
2. Send an example message "Hello, what can you do?"
3. Return the agent's response

### Microphone Example

For a more interactive experience, run the microphone example:

```bash
python microphone_realtime_agent.py
```

This will:
1. Connect to Deepgram's Voice Agent API
2. Start recording from your microphone
3. Stream your voice in real-time to the agent
4. Play the agent's responses and execute commands

### Command-line Options

Both examples accept the following command-line arguments:

- `--api-key`: Your Deepgram API key (defaults to DEEPGRAM_API_KEY environment variable)
- `--voice-id`: ElevenLabs voice ID (defaults to "cgSgspJ2msm6clMCkdW9")
- `--model`: LLM model to use (defaults to "gpt-4o-mini")

Example:

```bash
python microphone_realtime_agent.py --voice-id "alternative_voice_id" --model "gpt-4o"
```

## Available Agent Actions

Jan "The Man" can perform the following actions:

- **jump** [direction]: Makes the character jump (optional direction: left/right/up/down)
- **walk** [direction]: Makes the character walk in a specific direction (left/right/up/down)
- **run** [direction]: Makes the character run in a specific direction (left/right/up/down)
- **push** [direction]: Makes the character push in a specific direction (left/right/up/down)
- **pull** [direction]: Makes the character pull in a specific direction (left/right/up/down)
- **talk** [message]: Makes the character say something

## Integration Guide

To use the RealtimeAgent in your own application:

1. Import the RealtimeAgent:

```python
from realtime_agent import RealtimeAgent
```

2. Create an instance with your API key:

```python
agent = RealtimeAgent(deepgram_api_key="your_api_key")
```

3. Set up callbacks for various events:

```python
agent.set_callbacks(
    on_transcription=your_transcription_handler,
    on_response=your_response_handler,
    on_audio=your_audio_handler,
    on_command=your_command_handler
)
```

4. Connect to the service:

```python
await agent.connect()
```

5. Send audio data:

```python
await agent.send_audio(audio_chunk)
```

6. When finished, disconnect:

```python
await agent.disconnect()
```

## Advanced Usage

The RealtimeAgent also supports:

- Injecting text messages with `agent.inject_message("Hello")`
- Updating system instructions with `agent.update_instructions(new_instructions)`

## Troubleshooting

- If audio capture fails, ensure you have working microphone hardware and proper permissions
- If the agent doesn't respond, check your DEEPGRAM_API_KEY is valid
- For issues with ElevenLabs voices, verify your voice_id is correct

## License

This project is licensed under the MIT License - see the LICENSE file for details. 