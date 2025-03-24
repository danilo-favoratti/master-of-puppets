import React, { useCallback, useEffect, useRef, useState } from "react";
import "./App.css";
import Chat from "./components/Chat";
import GameContainer from "./components/GameContainer";

// @ts-ignore: Property 'env' does not exist on type 'ImportMeta'.
const WS_URL =
  (import.meta.env as any).VITE_WS_URL ||
  "wss://masterofpuppets.favoratti.com/ws";

// Global variables to maintain a single WebSocket connection across component mounts
let globalSocket: WebSocket | null = null;
let globalReconnectTimeout: ReturnType<typeof setTimeout> | null = null;
let globalSocketInitialized = false;
let hasLoggedConnection = false;
let globalWelcomeReceived = false;

function App() {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);
  const [messages, setMessages] = useState<
    Array<{ content: string; sender: string; isError?: boolean; options?: string[] }>
  >([]);

  // Create a ref to store the real executeCommand implementation from Game
  const gameCommandHandlerRef = useRef<
    null | ((cmd: string, result: string, params: any) => void)
  >(null);

  // Function to register the game command handler
  const registerGameCommandHandler = useCallback(
    (handler: (cmd: string, result: string, params: any) => void) => {
      gameCommandHandlerRef.current = handler;
    },
    []
  );

  const characterRef = useRef(null);

  // Connect to WebSocket using global variables to ensure a singleton connection
  useEffect(() => {
    let isMounted = true;

    // Reset thinking state whenever WebSocket connection changes
    setIsThinking(false);

    const connectWebSocket = () => {
      if (!isMounted) return;
      const ws = new WebSocket(WS_URL);
      globalSocket = ws;
      globalSocketInitialized = true;

      ws.addEventListener("open", () => {
        if (!hasLoggedConnection) {
          console.log("WebSocket connection established");
          hasLoggedConnection = true;
        }
        setIsConnected(true);
      });

      ws.addEventListener("close", () => {
        console.log("WebSocket connection closed");
        setIsConnected(false);
        setIsThinking(false);
        if (isMounted) {
          globalReconnectTimeout = setTimeout(() => {
            connectWebSocket();
          }, 3000);
        }
      });

      ws.addEventListener("error", (error) => {
        console.error("WebSocket error:", error);
        setIsConnected(false);
        setIsThinking(false);
      });

      ws.addEventListener("message", (event) => {
        setIsThinking(false);
        try {
          const data = JSON.parse(event.data);
          handleServerMessage(data);
        } catch (e) {
          // Non-JSON message handled in Chat component
        }
      });

      setSocket(ws);
    };

    if (!globalSocketInitialized) {
      connectWebSocket();
    } else {
      setSocket(globalSocket);
    }

    // Cleanup on unmount: do not close globalSocket to preserve the connection
    return () => {
      isMounted = false;
      if (globalReconnectTimeout) clearTimeout(globalReconnectTimeout);
    };
  }, []);

  // Reset thinking state on component mount
  useEffect(() => {
    console.log("Resetting thinking state on App mount");
    setIsThinking(false);
  }, []);

  // Handle messages from the server
  const handleServerMessage = (data: any) => {
    switch (data.type) {
      case "text":
        // Check if this is the welcome message
        if (
          data.content ===
          "Hey there, I'm your quirky game character! Let's play a game together? Give me a Theme..."
        ) {
          if (!globalWelcomeReceived) {
            globalWelcomeReceived = true;
            addMessage(data.content, "character");
          }
        } else {
          // Handle text messages with options
          if (Array.isArray(data.answers)) {
            data.answers.forEach((answer: any) => {
              if (answer.type === "text") {
                addMessage(answer.description, "character", false, answer.options || []);
              }
            });
          } else {
            addMessage(data.content, "character");
          }
        }
        setIsWaitingForResponse(false);
        break;

      case "command":
        executeCommand(data.name, data.result, data.params);
        setIsWaitingForResponse(false);
        break;

      case "error":
        console.error("Server error:", data.content);
        addMessage(`Error: ${data.content}`, "character", true);
        setIsWaitingForResponse(false);
        break;

      case "transcription":
        // Add the transcribed text to the chat as a user message
        addMessage(data.content, "user");
        setIsWaitingForResponse(false);
        break;

      case "user_message":
        // Handle the new user_message type (for voice input)
        addMessage(data.content, "user");
        setIsWaitingForResponse(false);
        break;

      default:
        // Ignore other message types like audio metadata
        setIsWaitingForResponse(false);
        break;
    }
  };

  // Add a message to the chat
  const addMessage = (content: string, sender: string, isError: boolean = false, options?: string[]) => {
    setMessages(prev => [...prev, { content, sender, isError, options }]);
  };

  // Send a text message to the server
  const sendTextMessage = (message: string) => {
    if (!isConnected || !socket) {
      console.error("Not connected to WebSocket server");
      return;
    }

    setIsThinking(true);

    const data = {
      type: "text",
      content: message,
    };

    socket.send(JSON.stringify(data));
  };

  // Execute a command from the character
  const executeCommand = (commandName: string, result: string, params: any) => {
    // Add the command result to chat
    addMessage(result, "command");

    // Handle create_map command
    if (commandName === "create_map" && params.map_data) {
      // Send the map data to the game container
      if (gameCommandHandlerRef.current) {
        gameCommandHandlerRef.current("update_map", "Map updated", params.map_data);
      }
    }
    // Forward other commands to the game component if the handler is registered
    else if (gameCommandHandlerRef.current) {
      gameCommandHandlerRef.current(commandName, result, params);
    }
  };

  return (
    <div className="flex flex-col h-screen">
      <div className="flex-1 relative">
        <GameContainer
          executeCommand={executeCommand}
          registerCommandHandler={registerGameCommandHandler}
        />
      </div>
      <Chat
        messages={messages}
        sendTextMessage={sendTextMessage}
        isThinking={isThinking}
        isConnected={isConnected}
        websocket={socket}
      />
    </div>
  );
}

export default App;
