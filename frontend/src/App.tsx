import React, {useCallback, useEffect, useRef, useState, useLayoutEffect} from "react";
import "./App.css";
import Chat from "./components/Chat";
import GameContainer from "./components/GameContainer";
import { GameData } from "./types/game";

// Fix the WebSocket URL declaration - Add type assertion
const WS_URL = (import.meta as any).env.VITE_WS_URL ||
    ((import.meta as any).env.DEV ? `ws://localhost:8080/ws` : `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws`);

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
    const [mapData, setMapData] = useState<GameData | null>(null);
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
            // If we already have a global socket, use it
            if (globalSocket && globalSocket.readyState === WebSocket.OPEN) {
                console.log("Using existing WebSocket connection");
                setSocket(globalSocket);
                setIsConnected(true);
                return;
            }

            // Use port 8080 for WebSocket in development - Add type assertion
            const wsUrl = (import.meta as any).env.DEV
                ? `ws://localhost:8080/ws`
                : `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws`;

            console.log("Connecting to WebSocket at:", wsUrl);

            const newSocket = new WebSocket(wsUrl);

            newSocket.onopen = () => {
                console.log("WebSocket connection established");
                setIsConnected(true);
                // Store the socket globally
                globalSocket = newSocket;
            };

            newSocket.onclose = () => {
                console.log("WebSocket connection closed");
                setIsConnected(false);
                globalSocket = null;
                // Try to reconnect after a delay
                setTimeout(connectWebSocket, 3000);
            };

            newSocket.onerror = (error) => {
                console.error("WebSocket error:", error);
                globalSocket = null;
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
                            {content: data.content, sender: "assistant"},
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
                                        .concat([{content: data.content, sender: "assistant"}])
                                );
                            } else {
                                // Regular handling for thinking messages - add them to the messages
                                setMessages((prevMessages) => [
                                    ...prevMessages,
                                    {content: data.content, sender: "assistant"},
                                ]);
                            }
                        } catch (e) {
                            console.error("Error parsing JSON content:", e);
                            setMessages((prevMessages) => [
                                ...prevMessages,
                                {content: data.content, sender: "assistant"},
                            ]);
                        }
                    } else if (data.type === "error") {
                        // Error message
                        setMessages((prevMessages) => [
                            ...prevMessages,
                            {content: data.content, sender: "assistant", isError: true},
                        ]);
                        setIsThinking(false);
                        setLoadingMap(false);
                    } else if (data.type === "command") {
                        if (data.name === "create_map") {
                            // Check if map_data exists in the message
                            if (data.map_data && data.map_data.grid) {
                                console.log("Processing create_map command with map_data:", data.map_data);
                                
                                // Construct the internal GameData structure from map_data
                                const newMapData: GameData = {
                                    map: {
                                        width: data.map_data.width,
                                        height: data.map_data.height,
                                        grid: data.map_data.grid
                                    },
                                    // Use top-level entities if they exist, otherwise default to empty array
                                    entities: data.entities || [] 
                                };

                                setMapData(newMapData);
                                setIsMapReady(true); // Mark map as ready
                                setIsMapCreated(true); // Also set this flag
                                setGameStarted(true);
                                setLoadingMap(false);

                                // Add the result message to the chat if it exists
                                if (data.result) {
                                    addMessage(data.result, "assistant"); // Use addMessage helper
                                }

                            } else {
                                console.error("Received create_map command but map_data is missing or invalid:", data);
                                setLoadingMap(false);
                                // Optionally, add an error message to the chat
                                addMessage("Error: Failed to process map data from server.", "system", true);
                            }
                        } else {
                            // Other command, just show the result as a message
                            // Using addMessage ensures consistent handling
                            if (data.result) {
                                addMessage(data.result, "assistant");
                            }
                        }
                    }

                    // Clear thinking state (might need adjustment based on message flow)
                    // Check if the message indicates thinking should stop
                    const jsonContent = data.type === 'json' ? tryParseJsonInString(data.content) : null;
                    const isStillThinking = jsonContent?.answers?.some((a: any) => a.isThinking === true);
                    if (!isStillThinking) {
                        setIsThinking(false);
                    }
                } catch (error) {
                    console.error("Error processing message:", error);
                    setIsThinking(false);
                    setLoadingMap(false);
                }
            };

            setSocket(newSocket);

            // Cleanup on unmount
            return () => {
                if (newSocket === globalSocket) {
                    globalSocket = null;
                }
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
        setMessages((prev) => [...prev, {content, sender, isError, options}]);
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
        if (commandName === "create_map" && params.environment) {
            // Send the map data to the game container
            if (gameCommandHandlerRef.current) {
                gameCommandHandlerRef.current(
                    "update_map",
                    "Map updated",
                    params.environment
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
    // THIS FUNCTION IS NO LONGER NEEDED FOR MAP GEN - THEME SELECTION HANDLES IT.
    // const requestMapGeneration = (theme: string) => {
    //     // ... existing implementation ...
    // };

    // Helper function to actually send the map request - NOW SENDS THEME
    // Renamed for clarity
    const sendThemeSelection = (theme: string) => {
        // Safety check again to make sure socket exists
        if (!socket || socket.readyState !== WebSocket.OPEN) {
            console.error('Socket not connected or null, cannot send theme');
            addMessage("Error: Not connected to server. Please wait or refresh.", "system", true);
            setIsThinking(false); // Stop thinking indicator
            setThemeIsSelected(false); // Allow re-selection
            return;
        }

        console.log('Sending theme selection request for theme:', theme);
        setIsThinking(true); // Indicate processing
        setLoadingMap(true); // Indicate map loading specifically

        // Use the NEW format the server expects
        const message = {
            type: 'set_theme', // <--- Use set_theme type
            theme: theme      // <--- Send theme name
        };

        try {
            socket.send(JSON.stringify(message));
            console.log('Theme selection request sent successfully');
            // Backend will respond with create_map or error
        } catch (err) {
            console.error('Error sending theme selection request:', err);
            setIsThinking(false);
            setLoadingMap(false);
            setThemeIsSelected(false); // Allow re-selection on error
            addMessage("Error sending theme choice. Please try again.", "system", true);
        }
    };

    // Update the handleThemeSelection function to directly call sendThemeSelection
    const handleThemeSelection = (theme: string) => {
        setThemeIsSelected(true); // Mark theme as selected immediately for UI

        // Check if socket exists but isn't connected yet
        if (!socket) {
            console.error("Socket not initialized, cannot send theme");
            addMessage("Connecting to server... Please try again in a moment.", "system", true);
            setThemeIsSelected(false); // Revert selection on error
            return;
        }

        if (socket.readyState !== WebSocket.OPEN) {
            console.log(`WebSocket not ready yet (state: ${socket.readyState}). Waiting...`);
            addMessage("Connecting to server... Please wait.", "system");
            setIsThinking(true); // Show thinking while waiting

            // Try again after a delay
            const connectionTimer = setTimeout(() => {
                if (socket && socket.readyState === WebSocket.OPEN) {
                    console.log("WebSocket now connected, sending theme");
                    sendThemeSelection(theme);
                    // setThemeIsSelected is already true
                } else {
                    console.error("WebSocket connection failed after waiting");
                    setIsThinking(false);
                    addMessage("Could not connect to server. Please refresh the page and try again.", "system", true);
                    setThemeIsSelected(false); // Revert selection on error
                }
            }, 2000); // Wait 2 seconds

            // Cleanup timer if component unmounts or socket connects sooner elsewhere
            return () => clearTimeout(connectionTimer);
        }

        // If we get here, the socket is connected and ready
        sendThemeSelection(theme);
    };

    // This function remains the same, just calls the updated handleThemeSelection
    const themeSelect = (theme: string) => {
        // Prevent selecting another theme if one is already loading/selected
        if (themeIsSelected || loadingMap) {
             console.warn("Theme already selected or loading.");
             return;
        }
        handleThemeSelection(theme);
    };

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
                    <div style={{flex: 1, position: "relative"}}>
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
                                onClick={() => themeSelect("Abandoned_Prisioner")}
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
                                onClick={() => themeSelect("Crash_in_the_Sea")}
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
                                onClick={() => themeSelect("Lost_Memory")}
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
