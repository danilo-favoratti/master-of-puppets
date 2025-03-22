# Deepgram Voice Agent Integration

This integration allows Jan "The Man" to use Deepgram's Voice Agent API for real-time, streaming voice interactions with much lower latency and better barge-in capabilities than the previous implementation.

## Features

- Real-time voice streaming with Deepgram's Voice Agent API
- Voice-based tool execution (jump, walk, run, push, pull, talk)
- Text-to-speech using ElevenLabs voices
- Barge-in capability (interrupt the agent while it's speaking)
- Persistent conversation context

## Prerequisites

- [Deepgram API Key](https://console.deepgram.com/signup)
- Python 3.8+
- Node.js and npm (for the frontend)

## Setup

1. Clone this repository:
```bash
git clone https://github.com/your-username/master-of-puppets.git
cd master-of-puppets
```

2. Install backend dependencies:
```bash
cd backend
pip install -r requirements.txt
```

3. Set up your environment variables:
    - Copy `backend/.env.example` to `backend/.env`
    - Add your Deepgram API key to the `.env` file

4. Install frontend dependencies:
```bash
cd frontend
npm install
```

## Running the Application

### Start the Backend

#### On Linux/macOS:
```bash
cd master-of-puppets
./backend/start_realtime_server.sh
```

#### On Windows:
```bash
cd master-of-puppets
backend\start_realtime_server.bat
```

### Start the Frontend

```bash
cd frontend
npm run dev
```

Then open your browser to the URL displayed in the terminal (typically http://localhost:5173).

## Usage

1. Click the microphone button in the chat interface to start recording
2. Speak your commands or questions
3. Jan will respond with voice and text
4. You can interrupt Jan by clicking the microphone button and speaking again

## Available Commands

Jan "The Man" can perform the following actions:
- **jump** [direction]: Makes the character jump (optional direction: left/right/up/down)
- **walk** [direction]: Makes the character walk in a specific direction (left/right/up/down)
- **run** [direction]: Makes the character run in a specific direction (left/right/up/down)
- **push** [direction]: Makes the character push in a specific direction (left/right/up/down)
- **pull** [direction]: Makes the character pull in a specific direction (left/right/up/down)
- **talk** [message]: Makes the character say something

## Troubleshooting

- **"Failed to connect to Deepgram Voice Agent API"**: Check that your Deepgram API key is correctly set in the `.env` file
- **No audio playback**: Make sure your browser allows audio playback for the site
- **Microphone not working**: Ensure your browser has permission to access the microphone
- **"WebSocket connection closed"**: The backend server might be down, check that it's running

## How It Works

1. The frontend React application establishes a WebSocket connection to the backend
2. When you click the microphone button, audio is captured from your microphone and streamed to the backend
3. The backend forwards this audio to Deepgram's Voice Agent API
4. Deepgram processes the audio, transcribes it, and generates a response using the specified LLM (gpt-4o-mini by default)
5. The response is converted to speech using ElevenLabs TTS
6. Both the text and audio are streamed back to the frontend
7. The frontend displays the text and plays the audio

## Advanced Configuration

You can customize the following environment variables in your `.env` file:

- `DEEPGRAM_API_KEY`: Your Deepgram API key (required)
- `CHARACTER_VOICE_ID`: ElevenLabs voice ID (default: "cgSgspJ2msm6clMCkdW9")
- `LLM_MODEL`: LLM model to use (default: "gpt-4o-mini")

## License

This project is licensed under the MIT License. 