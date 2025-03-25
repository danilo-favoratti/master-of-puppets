import React, { useCallback, useEffect, useRef, useState } from "react";
import Chat from "./components/Chat";
import GameContainer from "./components/GameContainer";

// Fix the WebSocket URL declaration to avoid TypeScript error
const WS_URL =
  (import.meta as any).env?.VITE_WS_URL ||
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
  const [isChatVisible, setIsChatVisible] = useState(false);
  const [themeIsSelected, setThemeIsSelected] = useState(false);
  const [messages, setMessages] = useState<
    Array<{
      content: string;
      sender: string;
      isError?: boolean;
      options?: string[];
    }>
  >([]);
  const [isMapCreated, setIsMapCreated] = useState(false);
  const [mapData, setMapData] = useState(null);
  const [isMapReady, setIsMapReady] = useState(false);

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

  // Update the handleServerMessage function to handle 'info' message type
  const handleServerMessage = (data: any) => {
    setIsWaitingForResponse(false);
    console.log("Received server message:", data);

    try {
      // Handle different message types
      switch (data.type) {
        case "user_input":
        case "text":
        case "response":
          if (Array.isArray(data.answers)) {
            data.answers.forEach((answer: any) => {
              if (answer.type === "text") {
                addMessage(answer.description, "character", false, answer.options || []);
              }
            });
          } else {
            addMessage(data.content, "character");
          }
          break;

        case "command":
          console.info("Command", data);
          executeCommand(data.name, data.result, data.params);
          break;

        case "error":
          console.error("Server error:", data.content);
          addMessage(`Error: ${data.content}`, "system", true);
          break;

        case "transcription":
          addMessage(data.content, "user");
          break;

        case "user_message":
          // Handle the new user_message type (for voice input)
          addMessage(data.content, "user");
          setIsWaitingForResponse(false);
          break;

        case "map_created":
          console.log("Map Created", data.content);
          handleMapCreated(data);
          break;

        case "info":
          console.log("Info message received:", data.content);
          // Add to messages if it's informative to the user
          if (data.content && data.content.includes("Map created")) {
            addMessage("Map created and ready for exploration!", "system");
          }
          break;

        case "json":
          handleJsonMessage(data);
          break;

        case "audio_start":
        case "audio_end":
        case "audio_data":
          // These are handled by the Chat component
          break;

        default:
          console.log(`Received unhandled message type: ${data.type}`);
          break;
      }
    } catch (err) {
      console.error("Error processing server message:", err);
    } finally {
      setIsThinking(false);
    }
  };

  // Helper function to handle map creation messages
  const handleMapCreated = (data: any) => {
    console.log('Map created in App:', data);
    
    if (data.map_data) {
      if (data.map_data.error) {
        console.error('Map data contains error:', data.map_data.error);
        // Simply retry the map generation with the correct text format
        if (!isMapCreated) {
          console.log('Retrying map generation with theme message');
          setIsMapCreated(true); // Set this first to prevent multiple retries
          
          // Short delay before retry
          setTimeout(() => {
            requestMapGeneration('abandoned prisioner');
          }, 500);
        }
      } else {
        console.log('Valid map data received, updating state');
        setMapData(data.map_data);
        setIsMapReady(true);
        setIsMapCreated(true);
        addMessage("Map created successfully! Wanna know more about this world?", "character");
      }
    } else {
      console.error('Received map_created event but data is missing map_data property');
      if (!isMapCreated) {
        setIsMapCreated(true);
        setTimeout(() => {
          requestMapGeneration('abandoned prisioner');
        }, 500);
      }
    }
  };

  // Helper function to handle JSON messages
  const handleJsonMessage = (data: any) => {
    try {
      const jsonContent = typeof data.content === 'string' ? JSON.parse(data.content) : data.content;
      addMessage(JSON.stringify(jsonContent), "agent");
    } catch (err) {
      console.error("Error parsing JSON message:", err);
      addMessage(data.content, "agent");
    }
  };

  // Add a message to the chat
  const addMessage = (
    content: string,
    sender: string,
    isError: boolean = false,
    options?: string[]
  ) => {
    setMessages((prev) => [...prev, { content, sender, isError, options }]);
  };

  // Update sendTextMessage to use the correct message format
  const sendTextMessage = (message: string) => {
    if (!isConnected || !socket) {
      console.error("Not connected to WebSocket server");
      return;
    }

    setIsThinking(true);

    // Use the format the backend expects
    const data = {
      type: "text",
      content: message
    };

    try {
      socket.send(JSON.stringify(data));
    } catch (err) {
      console.error("Error sending message:", err);
      setIsThinking(false);
      addMessage("Failed to send message. Please try again.", "system", true);
    }
  };

  // Execute a command from the character
  const executeCommand = (commandName: string, result: string, params: any) => {
    // Add the command result to chat
    addMessage(result, "command");

    // Handle create_map command
    if (commandName === "create_map" && params.map_data) {
      // Send the map data to the game container
      if (gameCommandHandlerRef.current) {
        gameCommandHandlerRef.current(
          "update_map",
          "Map updated",
          params.map_data
        );
      }
    }
    // Forward other commands to the game component if the handler is registered
    else if (gameCommandHandlerRef.current) {
      gameCommandHandlerRef.current(commandName, result, params);
    }
  };

  // Toggle chat visibility
  const toggleChat = () => {
    setIsChatVisible(!isChatVisible);
  };

  // Fix the map generation function to use the correct format "generate_world"
  const requestMapGeneration = (theme: string) => {
    // First check if socket exists and is connected
    if (!socket) {
      console.error('Socket not initialized, cannot generate map');
      return;
    }

    if (socket.readyState !== WebSocket.OPEN) {
      console.error('WebSocket not connected (state:', socket.readyState, ')');
      
      // Retry after a short delay if socket exists but not in OPEN state
      setTimeout(() => {
        if (socket && socket.readyState === WebSocket.OPEN) {
          console.log('Retrying map generation after connection delay');
          doSendMapRequest(theme);
        } else {
          console.error('Still not connected, cannot generate map');
        }
      }, 1000);
      return;
    }

    doSendMapRequest(theme);
  };

  // Helper function to actually send the map request
  const doSendMapRequest = (theme: string) => {
    // Safety check again to make sure socket exists
    if (!socket) {
      console.error('Socket became null before sending request');
      return;
    }
    
    console.log('Sending map generation request for theme:', theme);
    setIsThinking(true);

    // Use the text format with theme prefix - the format the server actually accepts
    const message = {
      type: 'text',
      content: `${theme}`
    };

    try {
      socket.send(JSON.stringify(message));
      console.log('Map generation request sent successfully');
    } catch (err) {
      console.error('Error sending map generation request:', err);
      setIsThinking(false);
    }
  };

  // Update the handleThemeSelection function
  const handleThemeSelection = (theme: string) => {
    if (!isConnected || !socket) {
      console.error("Not connected to WebSocket server");
      return;
    }

    setIsThinking(true);
    requestMapGeneration(theme);
    setThemeIsSelected(true);
  };

  // Update the themeSelect function to use handleThemeSelection
  const themeSelect = (theme) => {
    setThemeIsSelected(true);
    handleThemeSelection(theme);
  };

  // Add a useEffect to listen to WebSocket messages for map creation
  useEffect(() => {
    if (socket) {
      const handleWebSocketMessage = (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'map_created') {
            console.log('Map created in App:', data);
            setMapData(data.map_data);
            setIsMapReady(true);
          }
        } catch (err) {
          console.error('Error processing websocket message in App:', err);
        }
      };

      socket.addEventListener('message', handleWebSocketMessage);

      return () => {
        socket.removeEventListener('message', handleWebSocketMessage);
      };
    }
  }, [socket]);

  if (!themeIsSelected) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          height: "100vh",
          width: "100vw",
        }}
      >
        <div style={{ flex: 1, position: "relative" }}>
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              height: "100%",
              opacity: 0.5,
              zIndex: 10,
            }}
          ></div>
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              height: "100%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexDirection: "column",
              zIndex: 20,
            }}
          >
            <div>
              <h2>Select a Game Theme</h2>
            </div>
            <button
              onClick={() => themeSelect("Abandoned Prisioner")}
              style={{
                backgroundColor: "#3B82F6",
                color: "white",
                padding: "0.5rem 1rem",
                borderRadius: "0.375rem",
                border: "none",
                cursor: "pointer",
                marginBottom: "1rem",
                fontSize: "1.2rem",
              }}
            >
              Abandoned Prisioner
            </button>
            <button
              onClick={() => themeSelect("Crash in the Sea")}
              style={{
                backgroundColor: "#3B82F6",
                color: "white",
                padding: "0.5rem 1rem",
                borderRadius: "0.375rem",
                border: "none",
                cursor: "pointer",
                marginBottom: "1rem",
                fontSize: "1.2rem",
              }}
            >
              Crash in the Sea
            </button>
            <button
              onClick={() => themeSelect("Lost Memory")}
              style={{
                backgroundColor: "#3B82F6",
                color: "white",
                padding: "0.5rem 1rem",
                borderRadius: "0.375rem",
                border: "none",
                cursor: "pointer",
                marginBottom: "1rem",
                fontSize: "1.2rem",
              }}
            >
              Lost Memory
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen">
      {!themeIsSelected ? (
        // Theme selection screen (unchanged)
        <div style={{ /* unchanged */ }}>
          {/* ... unchanged ... */}
        </div>
      ) : (
        // Game screen with map data
        <div className="flex-1 relative">
          <GameContainer
            executeCommand={executeCommand}
            registerCommandHandler={registerGameCommandHandler}
            mapData={mapData}
            isMapReady={isMapReady}
            characterRef={characterRef}
            websocket={socket}
          />
          
          <Chat
            messages={messages}
            sendTextMessage={sendTextMessage}
            isThinking={isThinking}
            isConnected={isConnected}
            websocket={socket}
          />
        </div>
      )}
    </div>
  );
}

export default App;
