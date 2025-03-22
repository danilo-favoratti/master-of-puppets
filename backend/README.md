# Voice Agent for Game Character

This project implements a voice agent that allows players to interact with a game character through voice commands.

## TensorFlow Compatibility Issue

The original implementation used `openai-agents[voice]==0.0.6`, which depends on TensorFlow with the `contrib` module. However, this module was removed in TensorFlow 2.0, causing compatibility issues:

```
AttributeError: module 'tensorflow' has no attribute 'contrib'
```

## Solution

Two approaches are provided:

### Option 1: Use TensorFlow 1.x

If you need the full feature set of the OpenAI Agents SDK voice module:

1. Install TensorFlow 1.15.0 (last version with `contrib`):
   ```
   pip install tensorflow==1.15.0
   ```

2. Then install the other requirements:
   ```
   pip install -r requirements.txt
   ```

3. Use the original `voice_agent.py` implementation.

### Option 2: Simplified Implementation (Recommended)

A simplified implementation that avoids the OpenAI Agents SDK voice module and directly uses the OpenAI API:

1. Install the requirements:
   ```
   pip install openai python-dotenv numpy
   ```

2. Use `voice_agent_fixed.py` and `test_voice_agent_fixed.py`.

This implementation provides the same functionality without the TensorFlow dependency issues.

## Voice Agent Implementation

This project includes two different implementations of the voice agent:

1. **OpenAI Whisper (voice_agent.py)**: Uses OpenAI's Whisper API for transcription and relies on OpenAI to parse intents from the text.

2. **Deepgram Implementation (voice_agent_deepgram.py)**: Uses Deepgram for transcription with built-in intent detection, providing potentially better command recognition.

### Using Deepgram Implementation

To use the Deepgram implementation:

1. Make sure you have a Deepgram API key (you can sign up at [deepgram.com](https://deepgram.com/))
2. Add your Deepgram API key to the `.env` file:
   ```
   DEEPGRAM_API_KEY=your-deepgram-api-key-here
   ```
3. The backend is now configured to use Deepgram by default.

If you want to switch back to the OpenAI implementation, simply change the import in `main.py`:
```python
# Change from
from voice_agent_deepgram import VoiceAgentManager
# To
from voice_agent import VoiceAgentManager
```

## Usage

1. Set up environment variables in a `.env` file:
   ```
   OPENAI_API_KEY=your-api-key
   CHARACTER_VOICE=nova
   ```

2. Run the test script:
   ```
   python test_voice_agent_fixed.py
   ``` 