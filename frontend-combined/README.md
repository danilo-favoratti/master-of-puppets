# Game Character Control - Combined Frontend

This project combines the best features of both the original game character control frontends:
- 3D character rendering and animation from the React/Three.js version
- WebSocket communication and chat interface from the vanilla JS version

## Features

- Interactive 3D game character with animations (walk, run, jump, push, pull)
- Floating chat interface for communicating with the character
- WebSocket connectivity to send commands to the character
- Voice command support (simulated in this version)
- Real-time animation controls and game stats display

## Setup

1. Install dependencies:
```
npm install
```

2. Start the development server:
```
npm run dev
```

3. Make sure the WebSocket server is running (default: ws://localhost:8080/ws)

## Technical Details

This project is built with:
- React + TypeScript
- Three.js (via @react-three/fiber and @react-three/drei)
- Zustand for state management
- Vite for build tooling

## Project Structure

- `/src/components/` - React components including Game, Chat, and CharacterSprite
- `/src/store/` - State management with Zustand
- `/src/hooks/` - Custom React hooks for keyboard control
- `/src/assets/` - Game assets like character sprite sheets

## WebSocket Communication

The application communicates with a WebSocket server to:
- Send text messages
- Send voice commands (simulated)
- Receive text responses
- Receive command instructions that control the character

## Commands

The character can execute the following commands:
- `jump` - Make the character jump
- `walk` - Make the character walk in a direction
- `run` - Make the character run in a direction
- `push` - Make the character push in a direction
- `pull` - Make the character pull in a direction

Each command can include a direction parameter (up, down, left, right). 