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
const WS_URL = `ws://localhost:8080/ws`;

// Global variables to maintain a single WebSocket connection across component mounts
let globalSocket: WebSocket | null = null;
let globalReconnectTimeout: ReturnType<typeof setTimeout> | null = null;
let globalSocketInitialized = false;
let hasLoggedConnection = false;
let globalWelcomeReceived = false;

// In App.tsx or where WebSocket is created, add a simple connection counter
let connectionCount = 0;

// Enable or disable verbose logging
const VERBOSE_LOGGING = false;
const DEBUG_WEBSOCKET = true; // Set to true to log all WebSocket messages

// Helper function for conditional logging
const log = (message: string, ...args: any[]) => {
    if (VERBOSE_LOGGING) {
        console.log(message, ...args);
    }
};

// Helper function to parse JSON from string
const tryParseJsonInString = (text: string) => {
    try {
        // Check if the string might be JSON (starts with '{' or '[')
        if ((text.trim().startsWith('{') || text.trim().startsWith('[')) &&
            (text.trim().endsWith('}') || text.trim().endsWith(']'))) {
            return JSON.parse(text);
        }
    } catch (e) {
        // Don't log parsing errors in normal operation
        if (VERBOSE_LOGGING) {
            console.log("Not valid JSON in message:", e);
        }
    }
    return null;
};

interface QueuedCommand {
    id: string;
    name: string;
    result: string;
    params: any;
}

// Helper function for WebSocket message logging
const logWebSocketMessage = (message: any, type: string) => {
    if (DEBUG_WEBSOCKET) {
        // Skip ALL binary data and audio-related messages
        if (type === "BINARY" || 
            (typeof message === "object" && 
             (message.type === "audio_start" || 
              message.type === "audio_end" ||
              message.type === "audio_data"))) {
          return; // Skip logging audio messages completely
        }
        
        const timestamp = new Date().toISOString();
        console.log(`[${timestamp}] App WebSocket RECEIVED ${type}:`, message);
        
        // For JSON messages, log detailed content
        if (typeof message === "object") {
            try {
                // Log message type and important fields
                const msgType = message.type || "unknown-type";
                console.log(`  → Type: ${msgType}`);
                
                // Log different fields based on message type
                if (msgType === "command") {
                    console.log(`  → Command: ${message.name || "unnamed"}`);
                    console.log(`  → Params:`, message.params || {});
                    console.log(`  → Result: ${message.result?.substring(0, 100)}${message.result?.length > 100 ? "..." : ""}`);
                } else if (msgType === "text" || msgType === "user_message") {
                    console.log(`  → Content: ${message.content?.substring(0, 100)}${message.content?.length > 100 ? "..." : ""}`);
                    console.log(`  → Sender: ${message.sender || "unknown"}`);
                } else if (msgType === "error") {
                    console.error(`  → ERROR: ${message.content || "No error message"}`);
                }
            } catch (e) {
                console.error("Error parsing WebSocket message details:", e);
            }
        }
    }
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
        if (VERBOSE_LOGGING) {
            console.log(`Creating WebSocket connection #${++connectionCount}`);
        }
        
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
                    // Skip logging binary data
                    return;
                }

                try {
                    // Try to parse JSON message
                    const data = JSON.parse(event.data);
                    
                    // Skip logging audio-related messages
                    if (data.type === "audio_start" || data.type === "audio_end" || data.type === "audio_data") {
                        return;
                    }
                    
                    // Log all other WebSocket messages with details
                    logWebSocketMessage(data, "JSON");
                    
                    if (VERBOSE_LOGGING) {
                        console.log("WEBSOCKET: Received message:", data);
                    } else if (data.type === "error") {
                        // Always log errors
                        console.error("WEBSOCKET: Received error:", data);
                    }

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

                      if (VERBOSE_LOGGING) {
                        console.log("Tool call tracked:", newToolCall);
                      }
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
                        // Handle AnswerSet format - The backend now directly provides AnswerSet objects
                        // We can use the content directly or parse it if it's a string
                        try {
                            let jsonContent = data.content;
                            // Parse the content if it's a string
                            if (typeof data.content === 'string') {
                                jsonContent = JSON.parse(data.content);
                            }

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
                                        .concat([{
                                            content: typeof data.content === 'string' 
                                                ? data.content 
                                                : JSON.stringify(jsonContent),
                                            sender: data.sender || "character"
                                        }])
                                );
                            } else {
                                // Regular handling for thinking messages - add them to the messages
                                setMessages((prevMessages) => [
                                    ...prevMessages,
                                    {
                                        content: typeof data.content === 'string' 
                                            ? data.content 
                                            : JSON.stringify(jsonContent),
                                        sender: data.sender || "character"
                                    },
                                ]);
                            }
                        } catch (e) {
                            console.error("Error processing JSON content:", e);
                            setMessages((prevMessages) => [
                                ...prevMessages,
                                {content: typeof data.content === 'string' 
                                    ? data.content 
                                    : JSON.stringify(data.content),
                                sender: data.sender || "character"},
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
                            log(`📬 Queuing command: ${data.name}`);
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
                                log("Processing create_map command with map_data:", data.map_data);
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
                            log(`🚀 Executing non-animation command directly: ${data.name}`);
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
            log(`⚙️ Dequeuing command: ${commandToProcess.name} (ID: ${commandToProcess.id})`);
            setIsProcessingAnimation(true);

            // Define the completion callback
            const onComplete = () => {
                log(`✅ Animation complete for command: ${commandToProcess.name} (ID: ${commandToProcess.id})`);
                
                // --- Remove the completed command from the queue --- 
                setCommandQueue((prevQueue) => 
                    prevQueue.filter((cmd) => cmd.id !== commandToProcess.id)
                );
                
                setIsProcessingAnimation(false);
                if (processingTimeoutRef.current) {
                    clearTimeout(processingTimeoutRef.current);
                    processingTimeoutRef.current = null;
                }
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
        log("Resetting thinking state on App mount");
        setIsThinking(false);
    }, []);

    // Update the handleServerMessage function to handle 'info' message type
    const handleServerMessage = (data: any) => {
        setIsWaitingForResponse(false);
        log("Received server message:", data);

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
                    log("Info message received:", data.content);
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
                    log(`Received unhandled message type: ${data.type}`);
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
            // Handle AnswerSet format from backend
            let jsonContent: any;
            
            // Support both string content and direct object content
            if (typeof data.content === 'string') {
                jsonContent = JSON.parse(data.content);
            } else {
                // Content is already an object 
                jsonContent = data.content;
            }

            // Check if this contains thinking messages
            const hasThinkingMessages = jsonContent.answers?.some(
                (answer: any) => answer.isThinking === true
            );

            // If this has thinking messages, handle specially
            if (hasThinkingMessages) {
                // Direct add for thinking messages
                setMessages((prevMessages) => [...prevMessages, { 
                    content: typeof jsonContent === 'string' ? jsonContent : JSON.stringify(jsonContent), 
                    sender: "assistant" 
                }]);
            } else {
                // If not thinking messages, filter out any previous thinking messages
                setMessages((prevMessages) =>
                    prevMessages
                        .filter(msg => {
                            // Keep messages that aren't thinking messages
                            const msgJson = tryParseJsonInString(msg.content);
                            return !(msgJson?.answers?.some((a: any) => a.isThinking === true));
                        })
                        .concat([{ 
                            content: typeof jsonContent === 'string' ? jsonContent : JSON.stringify(jsonContent), 
                            sender: "assistant" 
                        }])
                );
            }

            // Update thinking state
            const isStillThinking = hasThinkingMessages;
            if (!isStillThinking) {
                setIsThinking(false);
            }
        } catch (err) {
            console.error("Error processing JSON message:", err);
            // Fall back to adding the raw content
            addMessage(
                typeof data.content === 'string' ? data.content : JSON.stringify(data.content), 
                "assistant"
            );
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
            log("Filtered out tool message from chat:", content);
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

    // Execute a command
    const executeCommand = useCallback((commandName: string, result: string, params: any, onComplete: () => void) => {
        log(`🚀 executeCommand called:`, { commandName, params });
        
        if (gameCommandHandlerRef.current) {
            try {
                log(`🚀 Forwarding command to gameCommandHandler: ${commandName}`);
                gameCommandHandlerRef.current(commandName, result, params, onComplete);
                log(`🚀 Command forwarded successfully to Game.tsx`);
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

    // Helper function to actually send the map request - NOW SENDS THEME
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
                toolCalls={toolCalls}
            />
            {/* Chat container with increased width */}
            <div className="relative" style={{ width: "115%", maxWidth: "115%", margin: "0 auto" }}>
                <Chat
                    messages={messages}
                    sendTextMessage={sendTextMessage}
                    isThinking={isThinking}
                    isConnected={isConnected}
                    websocket={socket}
                    isMapReady={isMapReady}
                />
            </div>
            <ToolsMenu toolCalls={toolCalls} />
        </div>
    );
}

export default App;
