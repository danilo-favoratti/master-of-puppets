# Game Character Control System

A WebSocket-based system that allows controlling a funny, ironic, non-binary videogame character using text and voice commands. The character can "jump" and "talk" in response to user input.

## Project Structure

```
/
├── backend/               # Python WebSocket server
│   ├── __init__.py        # Package initialization
│   ├── main.py            # FastAPI server implementation
│   ├── agent.py           # OpenAI agent setup and management
│   ├── tools.py           # Character action tools
│   ├── transcription.py   # Voice transcription handling
│   └── requirements.txt   # Python dependencies
├── frontend/              # Web client
│   ├── index.html         # HTML structure
│   ├── script.js          # JavaScript logic
│   └── styles.css         # CSS styling
└── README.md              # This file
```

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- An OpenAI API key with access to the Assistants API and Audio API

### Backend Setup

1. Navigate to the backend directory:
   ```
   cd backend
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   ```

3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`

4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

5. Create a `.env` file in the backend directory with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

6. Run the server:
   ```
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Frontend Setup

1. Open the frontend directory in a separate terminal window.

2. You can serve the frontend using any simple HTTP server. For example, with Python:
   ```
   python -m http.server 8080
   ```

3. Open your browser and go to http://localhost:8080 to access the application.

## Usage

- Type messages in the text input and press "Send" to communicate with the character.
- Click the "Voice" button to start voice recording, and click it again to stop and send the audio.
- The character will respond to your messages and may perform actions like jumping or talking.

## Extending the System

### Adding New Tools (Actions)

To add new tools/actions for the character:

1. Add a new function in `backend/tools.py`:
```python
def dance() -> str:
    """
    Makes the character dance.
    
    Returns:
        str: A description of the dance action
    """
    print("Dancing!")
    return "*(The character busts out some amazing dance moves.)*"
```

2. Register the tool in `backend/agent.py`:
```python
# In the setup_agent function, modify the tools list:
agent = agents.Agent(
    client=client,
    tools=[
        agents.tool(jump),
        agents.tool(talk),
        agents.tool(dance)  # Add your new tool here
    ],
    system=system_prompt
)
```

3. Add UI handling for the new command in `frontend/script.js`:
```javascript
// In the executeCommand function, add a new case:
case 'dance':
    // Animate the character dancing
    characterSprite.classList.add('dancing');
    setTimeout(() => {
        characterSprite.classList.remove('dancing');
    }, 2000);
    break;
```

4. Optionally, add CSS for any new animations in `frontend/styles.css`:
```css
/* Dance animation */
@keyframes dance {
    0%, 100% { transform: translateY(0) rotate(0); }
    25% { transform: translateY(-10px) rotate(10deg); }
    50% { transform: translateY(0) rotate(-10deg); }
    75% { transform: translateY(-10px) rotate(10deg); }
}

.dancing {
    animation: dance 0.8s ease infinite;
}
```

### Customizing the Character

To modify the character's personality:

1. Edit the system prompt in `backend/agent.py`.
2. Customize the appearance in `frontend/styles.css`.

## Technical Notes

- The WebSocket server handles both text messages and binary audio data.
- Voice input is processed using OpenAI's transcription API.
- Each browser connection is treated as a unique session with its own conversation history.
- The frontend uses standard Web APIs without external dependencies. 