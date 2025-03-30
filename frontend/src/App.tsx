import React, {useCallback, useEffect, useRef, useState, useLayoutEffect} from "react";
import "./App.css";
import Chat from "./components/Chat";
import GameContainer from "./components/GameContainer";
import HomeScreen from "./ui/HomeScreen";
import {GameData} from "./types/game";

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
    const [mapData, setMapData] = useState(null);
    const [isMapReady, setIsMapReady] = useState(false);
    const [gameStarted, setGameStarted] = useState(false);
    const [loadingMap, setLoadingMap] = useState(false);
    const [socketMessage, setSocketMessage] = useState<string | null>(null);

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
            const wsUrl = `${
                window.location.protocol === "https:" ? "wss:" : "ws:"
            }//${window.location.host}/ws`;
            console.log("WEBSOCKET: Connecting at:", wsUrl);

            const newSocket = new WebSocket(WS_URL);

            newSocket.onopen = () => {
                console.log("WEBSOCKET: Connection established");
                setIsConnected(true);
                setSocketMessage(null);
            };

            newSocket.onclose = () => {
                console.log("WEBSOCKET: Connection closed");
                setIsConnected(false);
                setSocketMessage("Connection closed");
                // Try to reconnect after a delay
                setTimeout(connectWebSocket, 3000);
            };

            newSocket.onerror = (error) => {
                console.error("WEBSOCKET: Error:", error);
                setSocketMessage("Error: " + error);
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
                    console.log("WEBSOCKET: Received message:", data);

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
    // Helper function to handle map creation messages
    const handleMapCreated = (data: any) => {
        console.log("Map created in App:", data);

        if (data.map_data) {
            if (data.map_data.error) {
                console.error("Map data contains error:", data.map_data.error);
                // Simply retry the map generation with the correct text format
                if (!isMapCreated) {
                    console.log("Retrying map generation with theme message");
                    setIsMapCreated(true); // Set this first to prevent multiple retries

                    // Short delay before retry
                    setTimeout(() => {
                        requestMapGeneration("abandoned prisioner");
                    }, 500);
                }
            } else {
                console.log("Valid map data received, updating state");
                setMapData(data.map_data);
                setIsMapReady(true);
                setIsMapCreated(true);
                addMessage(
                    "Map created successfully! Wanna know more about this world?",
                    "character"
                );
            }
        } else {
            console.error(
                "Received map_created event but data is missing map_data property"
            );
            if (!isMapCreated) {
                setIsMapCreated(true);
                setTimeout(() => {
                    requestMapGeneration("abandoned prisioner");
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

    if (!themeIsSelected) {
        return (
            <HomeScreen
                themeIsSelected={themeIsSelected}
                isConnected={isConnected}
                themeSelect={themeSelect}
                socketMessage={socketMessage}
            />
        );
    }

    return (
        <div className="flex flex-col h-screen">
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
    );
}

export default App;
