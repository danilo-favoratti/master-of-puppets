import React, {useCallback, useEffect, useRef, useState, useLayoutEffect} from "react";
import * as THREE from 'three'; // <-- Import Three.js
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
    const [themeIsSelected, setThemeIsSelected] = useState(false);
    const [messages, setMessages] = useState<
        Array<{
            content: string;
            sender: string;
            isError?: boolean;
            options?: string[];
        }>
    >([]);
    const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
    const [isMapCreated, setIsMapCreated] = useState(false);
    const [mapData, setMapData] = useState<GameData | null>(null);
    const [isMapReady, setIsMapReady] = useState(false);
    const [gameStarted, setGameStarted] = useState(false);
    const [loadingMap, setLoadingMap] = useState(false);
    const [socketMessage, setSocketMessage] = useState<string | null>(null);
    const [commandQueue, setCommandQueue] = useState<QueuedCommand[]>([]);
    const [isProcessingAnimation, setIsProcessingAnimation] = useState(false);
    const [isShowingIntroPortal, setIsShowingIntroPortal] = useState(false);
    const processingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const ANIMATION_TIMEOUT = 5000; // 5 seconds timeout for animations
    const gameCommandHandlerRef = useRef<
        null | ((cmd: string, result: string, params: any, onComplete: () => void) => void)
    >(null);
    const characterRef = useRef<CharacterRefMethods | null>(null);

    // --- Three.js Refs for Portal --- 
    const portalMountRef = useRef<HTMLDivElement>(null); 
    const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
    const sceneRef = useRef<THREE.Scene | null>(null);
    const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
    const portalGroupRef = useRef<THREE.Group | null>(null);
    const portalParticlesRef = useRef<THREE.BufferGeometry | null>(null);
    const animationFrameIdRef = useRef<number | null>(null);
    // --- End Three.js Refs ---

    const registerGameCommandHandler = useCallback(
        (handler: (cmd: string, result: string, params: any, onComplete: () => void) => void) => {
            gameCommandHandlerRef.current = handler;
        },
        []
    );

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
                setSocketMessage("Error: " + JSON.stringify(error)); // Stringify error for display
            };

            // Process incoming messages
            newSocket.onmessage = (event) => {
                if (event.data instanceof ArrayBuffer || event.data instanceof Blob) {
                    logWebSocketMessage(event.data, "BINARY"); // Log binary slightly differently
                    // Audio handled in Chat
                    return;
                }

                try {
                    const data = JSON.parse(event.data);
                    logWebSocketMessage(data, "JSON");
                    handleServerMessage(data); // Centralized message handler

                } catch (error) {
                    logWebSocketMessage(event.data, "TEXT/ERROR"); // Log raw text if JSON fails
                    console.error("Error processing message:", error);
                    addMessage(`Received unparseable message: ${event.data}`, "system", true);
                    setIsThinking(false);
                    setLoadingMap(false);
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

            const onComplete = () => {
                log(`✅ Animation complete for command: ${commandToProcess.name} (ID: ${commandToProcess.id})`);
                setCommandQueue((prevQueue) => 
                    prevQueue.filter((cmd) => cmd.id !== commandToProcess.id)
                );
                setIsProcessingAnimation(false);
                if (processingTimeoutRef.current) {
                    clearTimeout(processingTimeoutRef.current);
                    processingTimeoutRef.current = null;
                }
            };
            
            processingTimeoutRef.current = setTimeout(() => {
                console.warn(`⌛ Animation timeout for command: ${commandToProcess.name} (ID: ${commandToProcess.id}). Forcing completion.`);
                onComplete();
            }, ANIMATION_TIMEOUT);

            try {
                executeCommand(
                    commandToProcess.name,
                    commandToProcess.result,
                    commandToProcess.params,
                    onComplete
                );
            } catch (error) {
                console.error(`🔴 Error executing command ${commandToProcess.name} from queue:`, error);
                onComplete();
            }
        };

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
                    // ---> Log ALL commands received
                    log(`Received command: ${data.name}`, data);
                    setToolCalls(prev => [{ id: Date.now().toString(), name: data.name, params: data.params || {}, timestamp: Date.now(), result: (data.result && data.result.trim()) ? data.result : undefined }, ...prev].slice(0, 50));
                    if (["move", "move_step", "jump"].includes(data.name)) {
                        log(`📬 Queuing command: ${data.name}`);
                        const newCommand: QueuedCommand = { id: `${data.name}-${Date.now()}`, name: data.name, result: data.result || "", params: data.params || {} };
                        setCommandQueue((prev) => [...prev, newCommand]);
                        if (data.name === "move" && data.result && !data.params?.continuous) addMessage(data.result, data.sender || "system");
                    } else if (data.name === "create_map") {
                         // ---> Log specific create_map command
                         log("Received create_map command data:", data);
                        if (data.map_data?.grid) {
                            // ---> Log that grid exists
                            log("Processing create_map: Found valid grid data.");
                            const newMapData: GameData = { map: { width: data.map_data.width, height: data.map_data.height, grid: data.map_data.grid }, entities: data.entities || [] };
                            // ---> Log map data before setting state
                            log("Setting mapData state with:", newMapData);
                            setMapData(newMapData);
                            setIsMapReady(true);
                            setIsMapCreated(true);
                            setGameStarted(true);
                            setLoadingMap(false);
                            // ---> Show intro portal AFTER map data is set
                            setIsShowingIntroPortal(true); 
                            if (data.result) addMessage(data.result, data.sender || "system");
                        } else {
                            // ---> Log if grid is missing
                            log("Processing create_map: Invalid or missing grid data."); 
                            console.error("Invalid create_map data:", data);
                            setLoadingMap(false);
                            // Don't show portal on error
                            setIsShowingIntroPortal(false); 
                            addMessage("Error: Failed processing map data.", "system", true);
                        }
                    } else {
                        log(`🚀 Executing non-animation command: ${data.name}`);
                        if (data.result) addMessage(data.result, data.sender || "system");
                        executeCommand(data.name, data.result || "", data.params || {}, () => {});
                    }
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
            setIsShowingIntroPortal(false); // Ensure portal is hidden on general error
        } finally {
            const jsonContent = data.type === 'json' ? tryParseJsonInString(data.content) : null;
            const isStillThinking = jsonContent?.answers?.some((a: any) => a.isThinking === true);
            if (!isStillThinking) {
                 setIsThinking(false);
                 // Consider hiding portal here too if thinking stops before map arrives?
                 // For now, let create_map handle hiding it.
            }
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
              content.includes("pulled"))) || 
              content.includes("Could not move")) { // Filter move failures too
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
                log(`🚀 Command forwarded successfully`);
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
        log("Toggle Chat called");
    };

    // Send theme selection
    const sendThemeSelection = (theme: string) => {
        if (!socket || socket.readyState !== WebSocket.OPEN) { console.error('Socket not ready'); addMessage("Error: Not connected.", "system", true); setIsThinking(false); setThemeIsSelected(false); return; }
        console.log('Sending theme:', theme);
        setIsThinking(true); 
        setLoadingMap(true); 
        // ---> REMOVED showing portal here
        // setIsShowingIntroPortal(true); 
        const message = { type: 'set_theme', theme: theme };
        try { socket.send(JSON.stringify(message)); } 
        catch (err) { 
            console.error('Send theme error:', err); 
            setIsThinking(false); 
            setLoadingMap(false); 
            setThemeIsSelected(false); 
            setIsShowingIntroPortal(false); // Ensure portal hidden on error
            addMessage("Error sending theme.", "system", true); 
        }
    };

    // Handle theme selection
    const handleThemeSelection = (theme: string) => {
        setThemeIsSelected(true); 
        if (!socket) { 
            console.error("Socket null"); 
            addMessage("Connecting... Try again.", "system", true); 
            setThemeIsSelected(false); 
            return; 
        }
        if (socket.readyState !== WebSocket.OPEN) {
            console.log(`Waiting for socket (state: ${socket.readyState})...`);
            addMessage("Connecting...", "system"); 
            setIsThinking(true);
            const timer = setTimeout(() => {
                if (socket?.readyState === WebSocket.OPEN) { 
                    sendThemeSelection(theme); 
                } else { 
                    console.error("Connect failed"); 
                    setIsThinking(false); 
                    addMessage("Connection failed.", "system", true); 
                    setThemeIsSelected(false); 
                    setIsShowingIntroPortal(false); // Ensure portal hidden on error
                }
            }, 2000);
            return () => clearTimeout(timer);
        }
        sendThemeSelection(theme);
    };

    // --- Three.js Portal Effect --- 
    useEffect(() => {
        let portalGroup: THREE.Group | null = null;
        let portalParticles: THREE.BufferGeometry | null = null;
        let particleSystem: THREE.Points | null = null;

        const initThreeJS = () => {
            // Initialize only when the flag is true
            if (!portalMountRef.current || !isShowingIntroPortal) return;
            log("Initializing Three.js for Intro Portal"); // Log message updated
            const mount = portalMountRef.current;
            const scene = new THREE.Scene();
            sceneRef.current = scene;
            const camera = new THREE.PerspectiveCamera(75, mount.clientWidth / mount.clientHeight, 0.1, 1000);
            // Move camera closer for the smaller portal
            camera.position.z = 25; 
            cameraRef.current = camera;
            const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
            renderer.setSize(mount.clientWidth, mount.clientHeight);
            renderer.setPixelRatio(window.devicePixelRatio);
            rendererRef.current = renderer;
            mount.appendChild(renderer.domElement);
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
            scene.add(ambientLight);
            const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
            directionalLight.position.set(5, 10, 7.5);
            scene.add(directionalLight);

            // Create Portal 
            portalGroup = new THREE.Group();
            // Shift position within the container towards top-left and slightly forward
            portalGroup.position.set(-10, 5, 0.5); 
            // Scale the portal down
            portalGroup.scale.set(0.25, 0.25, 0.25);
            // Set rotation back to 0 on X-axis to face forward
            portalGroup.rotation.x = 0;
            portalGroupRef.current = portalGroup;
            const portalGeometry = new THREE.TorusGeometry(15, 2, 16, 100);
            const portalMaterial = new THREE.MeshPhongMaterial({ color: 0x00ff00, emissive: 0x00aa00, transparent: true, opacity: 0.8, shininess: 80 });
            const portal = new THREE.Mesh(portalGeometry, portalMaterial);
            portalGroup.add(portal);

            // Inner surface
            const portalInnerGeometry = new THREE.CircleGeometry(13, 32);
            const portalInnerMaterial = new THREE.MeshBasicMaterial({
                color: 0x00ff00,
                transparent: true,
                opacity: 0.3,
                side: THREE.DoubleSide
            });
            const portalInner = new THREE.Mesh(portalInnerGeometry, portalInnerMaterial);
            portalGroup.add(portalInner);

            // Particle system
            const portalParticleCount = 1000;
            portalParticles = new THREE.BufferGeometry();
            const portalPositions = new Float32Array(portalParticleCount * 3);
            const portalColors = new Float32Array(portalParticleCount * 3);

            for (let i = 0; i < portalParticleCount * 3; i += 3) {
                const angle = Math.random() * Math.PI * 2;
                const radius = 15 + (Math.random() - 0.5) * 4;
                portalPositions[i] = Math.cos(angle) * radius; // x
                portalPositions[i + 1] = Math.sin(angle) * radius; // y
                portalPositions[i + 2] = (Math.random() - 0.5) * 5; // z - spread out a bit

                // Green color
                portalColors[i] = 0;
                portalColors[i + 1] = 0.6 + Math.random() * 0.4; // Random green intensity
                portalColors[i + 2] = 0;
            }

            portalParticles.setAttribute('position', new THREE.BufferAttribute(portalPositions, 3));
            portalParticles.setAttribute('color', new THREE.BufferAttribute(portalColors, 3));
            portalParticlesRef.current = portalParticles;

            const portalParticleMaterial = new THREE.PointsMaterial({
                size: 0.2,
                vertexColors: true,
                transparent: true,
                opacity: 0.7,
                sizeAttenuation: true
            });

            particleSystem = new THREE.Points(portalParticles, portalParticleMaterial);
            portalGroup.add(particleSystem);

            scene.add(portalGroup);

            // Handle Resize
            const handleResize = () => {
                if (!portalMountRef.current || !cameraRef.current || !rendererRef.current) return;
                const width = portalMountRef.current.clientWidth;
                const height = portalMountRef.current.clientHeight;
                cameraRef.current.aspect = width / height;
                cameraRef.current.updateProjectionMatrix();
                rendererRef.current.setSize(width, height);
            };
            window.addEventListener('resize', handleResize);

            // Animation Loop
            const animate = () => {
                if (!portalParticlesRef.current || !portalGroupRef.current || !sceneRef.current || !cameraRef.current || !rendererRef.current) {
                    log("Stopping portal animation - refs missing");
                    return; 
                }
                
                animationFrameIdRef.current = requestAnimationFrame(animate);

                // Animate particles
                const positions = portalParticlesRef.current.attributes.position.array as Float32Array;
                for (let i = 0; i < positions.length; i += 3) {
                    // Simple up/down float + slight radial movement
                    positions[i + 1] += 0.02 * Math.sin(Date.now() * 0.001 + i);
                    positions[i + 2] += 0.01 * Math.cos(Date.now() * 0.002 + i);
                }
                portalParticlesRef.current.attributes.position.needsUpdate = true;

                // Rotate portal group
                portalGroupRef.current.rotation.y += 0.003;
                // portalGroupRef.current.rotation.x += 0.001; // Removed continuous X rotation

                rendererRef.current.render(sceneRef.current, cameraRef.current);
            };
            
            animate();
            return () => { window.removeEventListener('resize', handleResize); };
        };

        const cleanupThreeJS = () => {
            log("Cleaning up Three.js Portal");
            // Stop animation loop
            if (animationFrameIdRef.current) {
                cancelAnimationFrame(animationFrameIdRef.current);
                animationFrameIdRef.current = null;
            }

            // Dispose geometries, materials, textures
            if (portalGroupRef.current) {
                portalGroupRef.current.traverse((object) => {
                    if (object instanceof THREE.Mesh || object instanceof THREE.Points) {
                        object.geometry?.dispose();
                         if (object.material) {
                             if (Array.isArray(object.material)) {
                                object.material.forEach(material => material.dispose());
                            } else {
                                object.material.dispose();
                            }
                         }
                    }
                });
                sceneRef.current?.remove(portalGroupRef.current);
                portalGroupRef.current = null;
            }
            portalParticlesRef.current?.dispose(); // Dispose buffer geometry
            portalParticlesRef.current = null;

            // Remove renderer DOM element
            if (rendererRef.current && portalMountRef.current?.contains(rendererRef.current.domElement)) {
                 portalMountRef.current.removeChild(rendererRef.current.domElement);
            }
            
            // Dispose renderer
            rendererRef.current?.dispose();
            rendererRef.current = null;

            sceneRef.current = null;
            cameraRef.current = null;
        };

        let resizeCleanup: (() => void) | undefined;
        // Condition uses the renamed state
        if (isShowingIntroPortal) {
            resizeCleanup = initThreeJS();
        } else {
            cleanupThreeJS();
        }

        return () => {
            if (resizeCleanup) resizeCleanup();
            cleanupThreeJS();
        };
    }, [isShowingIntroPortal]);
    // --- End Three.js Portal Effect ---

    // --- Effect to auto-hide intro portal ---
    useEffect(() => {
        let hideTimeoutId: ReturnType<typeof setTimeout> | null = null;
        if (isShowingIntroPortal) {
            log("Intro portal is visible, starting hide timer...");
            hideTimeoutId = setTimeout(() => {
                log("Hiding intro portal after delay.");
                setIsShowingIntroPortal(false);
            }, 5000); // Hide after 5 seconds
        }

        // Cleanup the timeout if the component unmounts or the state changes before timeout completes
        return () => {
            if (hideTimeoutId) {
                clearTimeout(hideTimeoutId);
            }
        };
    }, [isShowingIntroPortal]);
    // --- End auto-hide effect ---

    // Theme selection function passed to HomeScreen
    const themeSelect = (theme: string) => {
        log(`Selected theme: ${theme}`);
        handleThemeSelection(theme); // Call the existing handler
    };

    return (
        <div className="App">
            {/* Conditionally render Three.js portal canvas based on intro state */} 
            {isShowingIntroPortal && (
                <div 
                    ref={portalMountRef}
                    className="portal-canvas-container"
                    style={{ position: 'absolute', top: 0, left: 0, width: '50vw', height: '50vh', zIndex: 1 }}
                ></div>
            )}

            {/* Render GameContainer if map data exists and theme selected */} 
            {mapData && themeIsSelected ? (
                <GameContainer
                    mapData={mapData}
                    isMapReady={isMapReady}
                    registerCommandHandler={registerGameCommandHandler}
                    executeCommand={executeCommand}
                    characterRef={characterRef}    
                    toolCalls={toolCalls}          
                    websocket={socket}             
                />
            /* Render HomeScreen if theme is NOT selected */
            ) : !themeIsSelected ? (
                <HomeScreen 
                  themeSelect={themeSelect} 
                  themeIsSelected={themeIsSelected} 
                  isConnected={isConnected}         
                  socketMessage={socketMessage}   
                />
            /* Render loading indicator if theme selected but no map yet */
            ) : themeIsSelected && !mapData ? (
                 <div className="loading-container" style={{zIndex: 0}}> {/* Basic Loading text */}
                   <p>Loading Map Data...</p>
                   <div className="loading-spinner"></div>
                 </div>
            ) : null }

            {/* Render Chat and ToolsMenu only when game has started (mapData exists) */}
            {mapData && (
                <>
                    <Chat
                        messages={messages}
                        sendTextMessage={sendTextMessage}
                        isThinking={isThinking}
                        websocket={socket} 
                        isConnected={isConnected}
                    />
                    <ToolsMenu toolCalls={toolCalls} />
                </>
            )}
        </div>
    );
}

export default App;
