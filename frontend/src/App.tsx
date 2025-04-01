import React, {useCallback, useEffect, useRef, useState, useLayoutEffect} from "react";
import "./App.css";
import Chat from "./components/Chat";
import GameContainer from "./components/GameContainer";
import HomeScreen from "./ui/HomeScreen";
import {GameData, Position} from "./types/game";
import ToolsMenu from "./components/ToolsMenu";  // Import the ToolsMenu component
import {CharacterRefMethods} from "./components/character/CharacterBody";

// Define interface for tool calls
export interface ToolCall {
  id: string;
  name: string;
  params: Record<string, any>;
  timestamp: number;
  result?: string;
}

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

interface QueuedCommand {
    id: string;
    name: string;
    result: string;
    params: any;
}

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
    // Add state for tool calls
    const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
    const [isMapCreated, setIsMapCreated] = useState(false);
    const [mapData, setMapData] = useState<GameData | null>(null);
    const [isMapReady, setIsMapReady] = useState(false);
    const [gameStarted, setGameStarted] = useState(false);
    const [loadingMap, setLoadingMap] = useState(false);
    const [socketMessage, setSocketMessage] = useState<string | null>(null);

    // --- Command Queue State ---
    const [commandQueue, setCommandQueue] = useState<QueuedCommand[]>([]);
    const [isProcessingAnimation, setIsProcessingAnimation] = useState(false);
    const processingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const ANIMATION_TIMEOUT = 5000; // 5 seconds timeout for animations
    // -------------------------

    // Create a ref to store the real executeCommand implementation from Game
    const gameCommandHandlerRef = useRef<
        null | ((cmd: string, result: string, params: any, onComplete: () => void) => void)
    >(null);

    // Function to register the game command handler
    const registerGameCommandHandler = useCallback(
        (handler: (cmd: string, result: string, params: any, onComplete: () => void) => void) => {
            gameCommandHandlerRef.current = handler;
        },
        []
    );
    
    // Fix the ref type here to match the expected signature in GameContainer
    const characterRef = useRef<CharacterRefMethods | null>(null);

    // Connect to backend WebSocket
    useEffect(() => {
        const connectWebSocket = () => {
            console.log("WEBSOCKET: Connecting at:", WS_URL);
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
                // Reset command queue on disconnect
                setCommandQueue([]);
                setIsProcessingAnimation(false);
                if (processingTimeoutRef.current) {
                    clearTimeout(processingTimeoutRef.current);
                }
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
                    // Try to parse JSON message
                    const data = JSON.parse(event.data);
                    console.log("WEBSOCKET: Received message:", data);

                    // Check for tool call and track it
                    if (data.type === "command" && data.name && data.params) {
                      // Create a new tool call object
                      const newToolCall: ToolCall = {
                        id: Date.now().toString(),
                        name: data.name, // Keep original name (move or move_step)
                        params: data.params || {},
                        timestamp: Date.now(),
                        // Only include result if it exists and is not null/empty
                        result: (data.result && data.result.trim()) ? data.result : undefined
                      };

                      // Add to tool calls state
                      setToolCalls(prev => [newToolCall, ...prev].slice(0, 50)); // Keep only most recent 50

                      console.log("Tool call tracked:", newToolCall);
                    }

                    // Handle different message types
                    if (data.type === "text") {
                        // Simple text message
                        setMessages((prevMessages) => [
                            ...prevMessages,
                            {content: data.content, sender: data.sender || "character"},
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
                                        .concat([{content: data.content, sender: data.sender || "character"}])
                                );
                            } else {
                                // Regular handling for thinking messages - add them to the messages
                                setMessages((prevMessages) => [
                                    ...prevMessages,
                                    {content: data.content, sender: data.sender || "character"},
                                ]);
                            }
                        } catch (e) {
                            console.error("Error parsing JSON content:", e);
                            setMessages((prevMessages) => [
                                ...prevMessages,
                                {content: data.content, sender: data.sender || "character"},
                            ]);
                        }
                    } else if (data.type === "error") {
                        // Error message
                        setMessages((prevMessages) => [
                            ...prevMessages,
                            {content: data.content, sender: data.sender || "system", isError: true},
                        ]);
                        setIsThinking(false);
                        setLoadingMap(false);
                        // Clear animation state on error
                        setIsProcessingAnimation(false);
                        if (processingTimeoutRef.current) {
                            clearTimeout(processingTimeoutRef.current);
                        }
                    } else if (data.type === "command") {
                        // --- Command Queue Logic ---
                        // Add animation commands to the queue instead of executing directly
                        if (["move", "move_step", "jump"].includes(data.name)) {
                            console.log(`📬 Queuing command: ${data.name}`);
                            const newCommand: QueuedCommand = {
                                id: `${data.name}-${Date.now()}`,
                                name: data.name,
                                result: data.result || "",
                                params: data.params || {},
                            };
                            setCommandQueue((prev) => [...prev, newCommand]);

                            // If it's a move command with a result, add result to chat immediately
                            if (data.name === "move" && data.result) {
                                addMessage(data.result, data.sender || "system");
                            }
                        } else if (data.name === "create_map") {
                            // Handle map creation immediately (not an animation)
                            if (data.map_data && data.map_data.grid) {
                                console.log("Processing create_map command with map_data:", data.map_data);
                                const newMapData: GameData = {
                                    map: {
                                        width: data.map_data.width,
                                        height: data.map_data.height,
                                        grid: data.map_data.grid
                                    },
                                    entities: data.entities || []
                                };
                                setMapData(newMapData);
                                setIsMapReady(true);
                                setIsMapCreated(true);
                                setGameStarted(true);
                                setLoadingMap(false);
                                if (data.result) {
                                    addMessage(data.result, data.sender || "system");
                                }
                            } else {
                                console.error("Received create_map command but map_data is missing or invalid:", data);
                                setLoadingMap(false);
                                addMessage("Error: Failed to process map data from server.", "system", true);
                            }
                        } else {
                            // Execute other non-animation commands directly
                            console.log(`🚀 Executing non-animation command directly: ${data.name}`);
                            if (data.result) {
                                addMessage(data.result, data.sender || "system");
                            }
                            // Pass a dummy onComplete for non-animation commands
                            executeCommand(data.name, data.result || "", data.params || {}, () => {});
                        }
                        // --- End Command Queue Logic ---
                    } else if (data.type === "user_message") {
                        // This is a user message from transcription
                        setMessages((prevMessages) => [
                            ...prevMessages,
                            {content: data.content, sender: "user"},
                        ]);
                    } else if (data.type === "info") {
                        // System info message
                        setMessages((prevMessages) => [
                            ...prevMessages,
                            {content: data.content, sender: data.sender || "system"},
                        ]);
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
                    // Clear animation state on error
                    setIsProcessingAnimation(false);
                    if (processingTimeoutRef.current) {
                        clearTimeout(processingTimeoutRef.current);
                    }
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
    }, []); // Empty dependency array ensures this runs only once

    // --- Command Queue Processing Effect ---
    useEffect(() => {
        const processNextCommand = () => {
            if (isProcessingAnimation || commandQueue.length === 0) {
                return;
            }

            const commandToProcess = commandQueue[0];
            console.log(`⚙️ Dequeuing command: ${commandToProcess.name} (ID: ${commandToProcess.id})`);
            setIsProcessingAnimation(true);
            // Remove command immediately visually? Or wait until onComplete?
            // Let's wait until onComplete to be safer in case of immediate errors.
            // setCommandQueue((prev) => prev.slice(1)); // Moved to onComplete

            // Define the completion callback
            const onComplete = () => {
                console.log(`✅ Animation complete for command: ${commandToProcess.name} (ID: ${commandToProcess.id})`);
                
                // --- Remove the completed command from the queue --- 
                setCommandQueue((prevQueue) => 
                    prevQueue.filter((cmd) => cmd.id !== commandToProcess.id)
                );
                // Use filter by ID for robustness in case queue order changes unexpectedly
                // Or simply: setCommandQueue((prevQueue) => prevQueue.slice(1)); if order is guaranteed.
                // Let's use slice(1) assuming order is maintained for simplicity.
                // setCommandQueue((prevQueue) => prevQueue.slice(1)); 
                // --- End Command Removal --- 
                
                setIsProcessingAnimation(false);
                if (processingTimeoutRef.current) {
                    clearTimeout(processingTimeoutRef.current);
                    processingTimeoutRef.current = null;
                }
                // Trigger processing the next command *after* state updates
                // Using setTimeout ensures state has time to update - this is generally okay
                // setTimeout(processNextCommand, 0); // Replaced by direct call below
            };
            
            // Set a timeout for the animation
            processingTimeoutRef.current = setTimeout(() => {
                console.warn(`⌛ Animation timeout for command: ${commandToProcess.name} (ID: ${commandToProcess.id}). Forcing completion.`);
                onComplete(); // Force completion on timeout
            }, ANIMATION_TIMEOUT);

            // Execute the command via the registered handler
            try {
                executeCommand(
                    commandToProcess.name,
                    commandToProcess.result,
                    commandToProcess.params,
                    onComplete // Pass the callback
                );
            } catch (error) {
                console.error(`🔴 Error executing command ${commandToProcess.name} from queue:`, error);
                onComplete(); // Ensure we always complete, even on error
            }
        };

        // Trigger processing if not busy and queue has items
        // This structure means processNextCommand is called whenever 
        // isProcessingAnimation becomes false AND commandQueue.length > 0
        if (!isProcessingAnimation && commandQueue.length > 0) {
            processNextCommand();
        }

        // Cleanup timeout on unmount or if queue state changes
        return () => {
            if (processingTimeoutRef.current) {
                clearTimeout(processingTimeoutRef.current);
            }
        };
    }, [commandQueue, isProcessingAnimation]);
    // -------------------------------------

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
                                addMessage(answer.description, "assistant", false, answer.options || []);
                            }
                        });
                    } else {
                        addMessage(data.content, "assistant");
                    }
                    break;

                case "command":
                    // Commands are now handled by the WebSocket onmessage handler
                    // executeCommand(data.name, data.result, data.params);
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

            // Check if this contains thinking messages
            const hasThinkingMessages = jsonContent.answers?.some(
                (answer: any) => answer.isThinking === true
            );

            // If this has thinking messages, handle specially
            if (hasThinkingMessages) {
                // Direct add for thinking messages
                setMessages((prevMessages) => [...prevMessages, { content: JSON.stringify(jsonContent), sender: "assistant" }]);
            } else {
                // If not thinking messages, filter out any previous thinking messages
                setMessages((prevMessages) =>
                    prevMessages
                        .filter(msg => {
                            // Keep messages that aren't thinking messages
                            const msgJson = tryParseJsonInString(msg.content);
                            return !(msgJson?.answers?.some((a: any) => a.isThinking === true));
                        })
                        .concat([{ content: typeof data.content === 'string' ? data.content : JSON.stringify(jsonContent), sender: "assistant" }])
                );
            }

            // Update thinking state
            const isStillThinking = hasThinkingMessages;
            if (!isStillThinking) {
                setIsThinking(false);
            }
        } catch (err) {
            console.error("Error parsing JSON message:", err);
            addMessage(data.content, "assistant");
            setIsThinking(false); // Make sure to clear thinking state on error
        }
    };

    // Add a message to the chat
    const addMessage = (
        content: string,
        sender: string,
        isError: boolean = false,
        options?: string[]
    ) => {
        // Filter out tool-related messages to keep them from the chat
        if (sender === "system" &&
            (content.includes("Successfully") &&
             (content.includes("moved") ||
              content.includes("walked") ||
              content.includes("ran") ||
              content.includes("jumped") ||
              content.includes("pushed") ||
              content.includes("pulled")))) {
            console.log("Filtered out tool message from chat:", content);
            return; // Skip adding this message to the chat
        }

        setMessages((prev) => [...prev, {content, sender, isError, options}]);
    };

    // Update sendTextMessage to use the correct message format
    const sendTextMessage = (message: string) => {
        if (!isConnected || !socket) {
            console.error("Not connected to WebSocket server");
            return;
        }

        // Add the user's message to the messages array first
        addMessage(message, "user");

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

    // Execute a command (NOW ACCEPTS onComplete callback)
    // Ensure this function signature matches where it's called
    const executeCommand = useCallback((commandName: string, result: string, params: any, onComplete: () => void) => {
        console.log(`🚀 executeCommand called with:`, {
            commandName,
            params,
            hasCharacterRef: !!characterRef.current,
            hasHandler: !!gameCommandHandlerRef.current
        });
        
        if (gameCommandHandlerRef.current) {
            try {
                console.log(`🚀 Forwarding command to gameCommandHandler: ${commandName}`);
                gameCommandHandlerRef.current(commandName, result, params, onComplete);
                console.log(`🚀 Command forwarded successfully to Game.tsx`);
            } catch (error) {
                console.error(`Error forwarding command ${commandName}:`, error);
                onComplete();
            }
        } else {
            console.warn(`No gameCommandHandler registered for command: ${commandName}. Calling onComplete immediately.`);
            onComplete();
        }
    }, [gameCommandHandlerRef]);

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

    // Log toolCalls state before rendering
    console.log("🔧 Rendering App, toolCalls state:", toolCalls);

    return (
        <div className="flex flex-col h-screen">
            <GameContainer
                executeCommand={executeCommand}
                registerCommandHandler={registerGameCommandHandler}
                mapData={mapData}
                isMapReady={isMapReady}
                characterRef={characterRef}
                websocket={socket}
                toolCalls={toolCalls}
            />
            <Chat
                messages={messages}
                sendTextMessage={sendTextMessage}
                isThinking={isThinking}
                isConnected={isConnected}
                websocket={socket}
            />
            <ToolsMenu toolCalls={toolCalls} />
        </div>
    );
}

export default App;
