import { OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { Suspense, useEffect, useState, useRef, useCallback } from "react";
import "./App.css";
import Game from "./components/Game";
import GameUI from "./components/GameUI";
import Chat from "./components/Chat";

// WebSocket configuration
const WS_URL = 'ws://localhost:8080/ws';

function App() {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [messages, setMessages] = useState<Array<{content: string, sender: string, isError?: boolean}>>([{
    content: "Hey there, I'm your quirky game character! Try telling me to jump or say something funny!",
    sender: "character"
  }]);
  
  // Create a ref to store the real executeCommand implementation from Game
  const gameCommandHandlerRef = useRef<null | ((cmd: string, result: string, params: any) => void)>(null);

  // Function to register the game command handler
  const registerGameCommandHandler = useCallback((handler: (cmd: string, result: string, params: any) => void) => {
    gameCommandHandlerRef.current = handler;
  }, []);

  // Connect to WebSocket
  useEffect(() => {
    const connectWebSocket = () => {
      const ws = new WebSocket(WS_URL);
      
      ws.addEventListener('open', () => {
        console.log('WebSocket connection established');
        setIsConnected(true);
      });
      
      ws.addEventListener('close', () => {
        console.log('WebSocket connection closed');
        setIsConnected(false);
        setIsThinking(false);
        
        // Try to reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
      });
      
      ws.addEventListener('error', (error) => {
        console.error('WebSocket error:', error);
        setIsConnected(false);
        setIsThinking(false);
      });
      
      ws.addEventListener('message', (event) => {
        setIsThinking(false);
        const data = JSON.parse(event.data);
        handleServerMessage(data);
      });
      
      setSocket(ws);
    };
    
    connectWebSocket();
    
    // Cleanup on unmount
    return () => {
      if (socket) {
        socket.close();
      }
    };
  }, []);

  // Handle messages from the server
  const handleServerMessage = (data: any) => {
    switch (data.type) {
      case 'text':
        addMessage(data.content, 'character');
        break;
        
      case 'command':
        executeCommand(data.name, data.result, data.params);
        break;
        
      case 'error':
        console.error('Server error:', data.content);
        addMessage(`Error: ${data.content}`, 'character', true);
        break;
        
      default:
        console.warn('Unknown message type:', data.type);
    }
  };

  // Add a message to the chat
  const addMessage = (content: string, sender: string, isError = false) => {
    setMessages(prev => [...prev, { content, sender, isError }]);
  };

  // Send a text message to the server
  const sendTextMessage = (message: string) => {
    if (!isConnected || !socket) {
      console.error('Not connected to WebSocket server');
      return;
    }
    
    setIsThinking(true);
    
    const data = {
      type: 'text',
      content: message
    };
    
    socket.send(JSON.stringify(data));
    addMessage(message, 'user');
  };

  // Execute a command from the character
  const executeCommand = (commandName: string, result: string, params: any) => {
    // Add the command result to chat
    addMessage(result, 'command');
    
    // Forward to the game component if the handler is registered
    if (gameCommandHandlerRef.current) {
      gameCommandHandlerRef.current(commandName, result, params);
    }
  };

  return (
    <div className="game-container">
      <Canvas
        camera={{ position: [0, 0, 5], fov: 40 }}
        style={{ width: "100vw", height: "100vh" }}
      >
        <Suspense fallback={null}>
          <ambientLight intensity={0.5} />
          <directionalLight position={[10, 10, 5]} intensity={1} />
          <OrbitControls 
            enableRotate={false} 
            enableZoom={true}
            maxZoom={20}
            minZoom={5}
            zoomSpeed={0.5}
            enablePan={true}
            panSpeed={0.5}
          />
          <Game 
            executeCommand={executeCommand} 
            registerCommandHandler={registerGameCommandHandler}
          />
        </Suspense>
      </Canvas>

      <GameUI />
      
      <Chat 
        messages={messages}
        sendTextMessage={sendTextMessage}
        isThinking={isThinking}
        isConnected={isConnected}
      />
    </div>
  );
}

export default App; 