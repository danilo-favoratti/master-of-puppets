import React, {useCallback, useEffect, useRef, useState} from "react";
import "./App.css";
import Chat from "./components/Chat";
import GameContainer from "./components/GameContainer";
import {WebSocket} from "vite";

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

// Helper function to parse JSON from string
const tryParseJsonInString = (text: string) => {
  try {
    // Check if the string might be JSON (starts with '{' or '[')
    if ((text.trim().startsWith('{') || text.trim().startsWith('[')) && 
        (text.trim().endsWith('}') || text.trim().endsWith(']'))) {
      return JSON.parse(text);
    }
  } catch (e) {
    // If parsing fails, it's not valid JSON
    console.log("Not valid JSON in message:", e);
  }
  return null;
};

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
  const [gameStarted, setGameStarted] = useState(false);
  const [loadingMap, setLoadingMap] = useState(false);

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

  // Connect to backend WebSocket
  useEffect(() => {
    const connectWebSocket = () => {
      const wsUrl = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${
        window.location.host
      }/ws`;
      console.log("Connecting to WebSocket at:", wsUrl);
      
      const newSocket = new WebSocket(wsUrl);
      
      newSocket.onopen = () => {
        console.log("WebSocket connection established");
        setIsConnected(true);
      };
      
      newSocket.onclose = () => {
        console.log("WebSocket connection closed");
        setIsConnected(false);
        // Try to reconnect after a delay
        setTimeout(connectWebSocket, 3000);
      };
      
      newSocket.onerror = (error) => {
        console.error("WebSocket error:", error);
      };
      
      // Process incoming messages directly inline for simplicity
      newSocket.onmessage = (event) => {
        // Check if binary data (audio chunks) - already handled in Chat component
        if (event.data instanceof ArrayBuffer) {
          return;
        }

        try {
          // Parse JSON message
          const data = JSON.parse(event.data);
          console.log("Received message:", data);

          // Handle different message types
          if (data.type === "text") {
            // Simple text message
            setMessages((prevMessages) => [
              ...prevMessages,
              { content: data.content, sender: "assistant" },
            ]);
            setLoadingMap(false);
          } else if (data.type === "json") {
            // JSON content with answers array
            try {
              const jsonContent = JSON.parse(data.content);
              
              // Check if this contains thinking messages
              const hasThinkingMessages = jsonContent.answers?.some(
                (answer: any) => answer.isThinking === true
              );
              
              // If we previously had thinking messages and this isn't a thinking message,
              // we should clear the thinking messages
              if (!hasThinkingMessages) {
                // Filter out any thinking messages before adding new content
                setMessages((prevMessages) => 
                  prevMessages
                    .filter(msg => {
                      // Keep messages that aren't thinking messages
                      const msgJson = tryParseJsonInString(msg.content);
                      return !(msgJson?.answers?.some((a: any) => a.isThinking === true));
                    })
                    .concat([{ content: data.content, sender: "assistant" }])
                );
              } else {
                // Regular handling for thinking messages - add them to the messages
                setMessages((prevMessages) => [
                  ...prevMessages,
                  { content: data.content, sender: "assistant" },
                ]);
              }
            } catch (e) {
              console.error("Error parsing JSON content:", e);
              setMessages((prevMessages) => [
                ...prevMessages,
                { content: data.content, sender: "assistant" },
              ]);
            }
          } else if (data.type === "error") {
            // Error message
            setMessages((prevMessages) => [
              ...prevMessages,
              { content: data.content, sender: "assistant", isError: true },
            ]);
            setIsThinking(false);
            setLoadingMap(false);
          } else if (data.type === "command") {
            if (data.name === "create_map") {
              console.log("Creating map with data:", data.params.map_data);
              setMapData(data.params.map_data);
              setGameStarted(true);
              setLoadingMap(false);

              // Also add the map creation message to the chat
              if (data.content) {
                // Filter out any thinking messages
                setMessages((prevMessages) => 
                  prevMessages
                    .filter(msg => {
                      const msgJson = tryParseJsonInString(msg.content);
                      return !(msgJson?.answers?.some((a: any) => a.isThinking === true));
                    })
                    .concat([{ content: data.content, sender: "assistant" }])
                );
              }
            } else {
              // Other command, just show the result as a message
              setMessages((prevMessages) => [
                ...prevMessages,
                { content: data.result, sender: "assistant" },
              ]);
            }
          }

          // Clear thinking state
          setIsThinking(false);
        } catch (error) {
          console.error("Error processing message:", error);
          setIsThinking(false);
          setLoadingMap(false);
        }
      };
      
      setSocket(newSocket);
      
      // Cleanup on unmount
      return () => {
        newSocket.close();
      };
    };
    
    connectWebSocket();
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
    // Check if socket exists but isn't connected yet
    if (!socket) {
      console.error("Socket not initialized, cannot send theme");
      // Show a message to the user
      addMessage("Connecting to server... Please try again in a moment.", "system", true);
      return;
    }

    if (socket.readyState !== WebSocket.OPEN) {
      console.log(`WebSocket not ready yet (state: ${socket.readyState}). Waiting...`);
      addMessage("Connecting to server... Please wait.", "system");
      
      // Set a loading indicator
      setIsThinking(true);
      
      // Try again after a delay
      const connectionTimer = setTimeout(() => {
        if (socket && socket.readyState === WebSocket.OPEN) {
          console.log("WebSocket now connected, sending theme");
          setIsThinking(true);
          requestMapGeneration(theme);
          setThemeIsSelected(true);
        } else {
          console.error("WebSocket connection failed after waiting");
          setIsThinking(false);
          addMessage("Could not connect to server. Please refresh the page and try again.", "system", true);
        }
      }, 2000); // Wait 2 seconds before retrying
      
      return;
    }

    // If we get here, the socket is connected and ready
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
      <div className="flex flex-col h-screen">
        {!themeIsSelected ? (
          // Theme selection screen
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
                  <div style={{ 
                    textAlign: "center", 
                    margin: "10px 0", 
                    color: isConnected ? "green" : "red",
                    fontSize: "14px"
                  }}>
                    {isConnected ? "✓ Connected to server" : "⚠ Connecting to server..."}
                  </div>
                </div>
                <button
                  onClick={() => themeSelect("theme: Abandoned Prisioner")}
                  style={{
                    backgroundColor: "#3B82F6",
                    color: "white",
                    padding: "0.5rem 1rem",
                    borderRadius: "0.375rem",
                    border: "none",
                    cursor: "pointer",
                    marginBottom: "1rem",
                    fontSize: "1.2rem",
                    opacity: isConnected ? 1 : 0.6
                  }}
                  disabled={!isConnected}
                >
                  Abandoned Prisioner
                </button>
                <button
                  onClick={() => themeSelect("theme: Crash in the Sea")}
                  style={{
                    backgroundColor: "#3B82F6",
                    color: "white",
                    padding: "0.5rem 1rem",
                    borderRadius: "0.375rem",
                    border: "none",
                    cursor: "pointer",
                    marginBottom: "1rem",
                    fontSize: "1.2rem",
                    opacity: isConnected ? 1 : 0.6
                  }}
                  disabled={!isConnected}
                >
                  Crash in the Sea
                </button>
                <button
                  onClick={() => themeSelect("theme: Lost Memory")}
                  style={{
                    backgroundColor: "#3B82F6",
                    color: "white",
                    padding: "0.5rem 1rem",
                    borderRadius: "0.375rem",
                    border: "none",
                    cursor: "pointer",
                    marginBottom: "1rem",
                    fontSize: "1.2rem",
                    opacity: isConnected ? 1 : 0.6
                  }}
                  disabled={!isConnected}
                >
                  Lost Memory
                </button>
              </div>
            </div>
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

  return (
    <div className="flex flex-col h-screen">
      {!themeIsSelected ? (
        // Theme selection screen
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
                <div style={{ 
                  textAlign: "center", 
                  margin: "10px 0", 
                  color: isConnected ? "green" : "red",
                  fontSize: "14px"
                }}>
                  {isConnected ? "✓ Connected to server" : "⚠ Connecting to server..."}
                </div>
              </div>
              <button
                onClick={() => themeSelect("theme: Abandoned Prisioner")}
                style={{
                  backgroundColor: "#3B82F6",
                  color: "white",
                  padding: "0.5rem 1rem",
                  borderRadius: "0.375rem",
                  border: "none",
                  cursor: "pointer",
                  marginBottom: "1rem",
                  fontSize: "1.2rem",
                  opacity: isConnected ? 1 : 0.6
                }}
                disabled={!isConnected}
              >
                Abandoned Prisioner
              </button>
              <button
                onClick={() => themeSelect("theme: Crash in the Sea")}
                style={{
                  backgroundColor: "#3B82F6",
                  color: "white",
                  padding: "0.5rem 1rem",
                  borderRadius: "0.375rem",
                  border: "none",
                  cursor: "pointer",
                  marginBottom: "1rem",
                  fontSize: "1.2rem",
                  opacity: isConnected ? 1 : 0.6
                }}
                disabled={!isConnected}
              >
                Crash in the Sea
              </button>
              <button
                onClick={() => themeSelect("theme: Lost Memory")}
                style={{
                  backgroundColor: "#3B82F6",
                  color: "white",
                  padding: "0.5rem 1rem",
                  borderRadius: "0.375rem",
                  border: "none",
                  cursor: "pointer",
                  marginBottom: "1rem",
                  fontSize: "1.2rem",
                  opacity: isConnected ? 1 : 0.6
                }}
                disabled={!isConnected}
              >
                Lost Memory
              </button>
            </div>
          </div>
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
