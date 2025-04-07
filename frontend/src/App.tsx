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
const DEBUG_WEBSOCKET = true; // Keep this true for now if you still want basic WS message logs, or set to false

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
                setCommandQueue([]);
                setIsProcessingAnimation(false);
                if (processingTimeoutRef.current) {
                    clearTimeout(processingTimeoutRef.current);
                }
                setTimeout(connectWebSocket, 3000);
            };

            newSocket.onerror = (error) => {
                console.error("WEBSOCKET: Error:", error);
                setSocketMessage("Error: " + JSON.stringify(error));
            };

            newSocket.onmessage = (event) => {
                if (event.data instanceof ArrayBuffer || event.data instanceof Blob) {
                    return;
                }
                try {
                    const data = JSON.parse(event.data);
                    handleServerMessage(data);
                } catch (error) {
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
            return () => { newSocket.close(); };
        };
        connectWebSocket();
    }, []);

    // --- Command Queue Processing Effect ---
    useEffect(() => {
        const processNextCommand = () => {
            if (isProcessingAnimation || commandQueue.length === 0) return;
            const commandToProcess = commandQueue[0];
            setIsProcessingAnimation(true);
            const onComplete = () => {
                setCommandQueue((prevQueue) => prevQueue.filter((cmd) => cmd.id !== commandToProcess.id));
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
                executeCommand(commandToProcess.name, commandToProcess.result, commandToProcess.params, onComplete);
            } catch (error) {
                console.error(`🔴 Error executing command ${commandToProcess.name} from queue:`, error);
                onComplete();
            }
        };
        if (!isProcessingAnimation && commandQueue.length > 0) {
            processNextCommand();
        }
        return () => {
            if (processingTimeoutRef.current) clearTimeout(processingTimeoutRef.current);
        };
    }, [commandQueue, isProcessingAnimation]);

    // Reset thinking state on component mount
    useEffect(() => {
        setIsThinking(false);
    }, []);

    // Update the handleServerMessage function to handle 'info' message type
    const handleServerMessage = (data: any) => {
        setIsWaitingForResponse(false);

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
                    setToolCalls(prev => [{ id: Date.now().toString(), name: data.name, params: data.params || {}, timestamp: Date.now(), result: (data.result && data.result.trim()) ? data.result : undefined }, ...prev].slice(0, 50));
                    if (["move", "move_step", "jump"].includes(data.name)) {
                        const newCommand: QueuedCommand = { id: `${data.name}-${Date.now()}`, name: data.name, result: data.result || "", params: data.params || {} };
                        setCommandQueue((prev) => [...prev, newCommand]);
                        if (data.name === "move" && data.result && !data.params?.continuous) addMessage(data.result, data.sender || "system");
                    } else if (data.name === "create_map") {
                        if (data.map_data?.grid) {
                            const newMapData: GameData = { map: { width: data.map_data.width, height: data.map_data.height, grid: data.map_data.grid }, entities: data.entities || [] };
                            setMapData(newMapData);
                            setIsMapReady(true);
                            setIsMapCreated(true);
                            setGameStarted(true);
                            setLoadingMap(false);
                            setIsShowingIntroPortal(true); 
                            if (data.result) addMessage(data.result, data.sender || "system");
                        } else {
                            console.error("Invalid create_map data:", data);
                            setLoadingMap(false);
                            setIsShowingIntroPortal(false); 
                            addMessage("Error: Failed processing map data.", "system", true);
                        }
                    } else {
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
                    addMessage(data.content, "user");
                    setIsWaitingForResponse(false);
                    break;

                case "info":
                    if (data.content?.includes("Map created")) addMessage("Map created!", "system");
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
            setIsShowingIntroPortal(false);
        } finally {
            const jsonContent = data.type === 'json' ? tryParseJsonInString(data.content) : null;
            const isStillThinking = jsonContent?.answers?.some((a: any) => a.isThinking === true);
            if (!isStillThinking) {
            setIsThinking(false);
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
            return; // Skip adding this message to the chat
        }

        setMessages((prev) => [...prev, {content, sender, isError, options}]);
    };

    // Update sendTextMessage to use the correct message format
    const sendTextMessage = (message: string) => {
        if (!isConnected || !socket) { console.error("Not connected"); return; }
        // addMessage(message, "user"); // REMOVE/COMMENT OUT THIS LINE - prevents double message
        setIsThinking(true);
        const data = { type: "text", content: message };
        try { socket.send(JSON.stringify(data)); } 
        catch (err) { 
            console.error("Send error:", err);
            setIsThinking(false);
            addMessage("Send failed.", "system", true); 
        }
    };

    // Execute a command
    const executeCommand = useCallback((commandName: string, result: string, params: any, onComplete: () => void) => {
        if (gameCommandHandlerRef.current) {
            try {
                gameCommandHandlerRef.current(commandName, result, params, onComplete);
            } catch (error) {
                console.error(`Forwarding error ${commandName}:`, error);
                onComplete();
            }
        } else {
            console.warn(`No handler for: ${commandName}. Completing.`);
            onComplete();
        }
    }, []);

    // Toggle chat visibility
    const toggleChat = () => {
    };

    // Send theme selection
    const sendThemeSelection = (theme: string) => {
        if (!socket || socket.readyState !== WebSocket.OPEN) { console.error('Socket not ready'); addMessage("Error: Not connected.", "system", true); setIsThinking(false); setThemeIsSelected(false); return; }
        setIsThinking(true); 
        setLoadingMap(true); 
        setIsShowingIntroPortal(true); 
        const message = { type: 'set_theme', theme: theme };
        try { socket.send(JSON.stringify(message)); } 
        catch (err) { 
            console.error('Send theme error:', err); 
            setIsThinking(false);
            setLoadingMap(false);
            setThemeIsSelected(false); 
            setIsShowingIntroPortal(false); 
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
                    setIsShowingIntroPortal(false); 
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
            if (!portalMountRef.current || !isShowingIntroPortal) return;
            const mount = portalMountRef.current;
            const scene = new THREE.Scene();
            sceneRef.current = scene;
            const camera = new THREE.PerspectiveCamera(75, mount.clientWidth / mount.clientHeight, 0.1, 1000);
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
            portalGroup.position.set(-10, 5, 0.5); 
            portalGroup.scale.set(0.25, 0.25, 0.25);
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

                rendererRef.current.render(sceneRef.current, cameraRef.current);
            };
            
            animate();
            return () => { window.removeEventListener('resize', handleResize); };
        };

        const cleanupThreeJS = () => {
            if (animationFrameIdRef.current) {
                cancelAnimationFrame(animationFrameIdRef.current);
                animationFrameIdRef.current = null;
            }

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
            portalParticlesRef.current?.dispose();
            portalParticlesRef.current = null;

            if (rendererRef.current && portalMountRef.current?.contains(rendererRef.current.domElement)) {
                 portalMountRef.current.removeChild(rendererRef.current.domElement);
            }
            
            rendererRef.current?.dispose();
            rendererRef.current = null;

            sceneRef.current = null;
            cameraRef.current = null;
        };

        let resizeCleanup: (() => void) | undefined;
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
            hideTimeoutId = setTimeout(() => {
                setIsShowingIntroPortal(false);
            }, 5000);
        }

        return () => {
            if (hideTimeoutId) {
                clearTimeout(hideTimeoutId);
            }
        };
    }, [isShowingIntroPortal]);
    // --- End auto-hide effect ---

    // Theme selection function passed to HomeScreen
    const themeSelect = (theme: string) => {
        handleThemeSelection(theme);
    };

    return (
        <div className="App">
            {isShowingIntroPortal && (
                <div 
                    ref={portalMountRef}
                    className="portal-canvas-container"
                    style={{ position: 'absolute', top: 0, left: 0, width: '50vw', height: '50vh', zIndex: 1 }}
                ></div>
            )}

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
            ) : !themeIsSelected ? (
                <HomeScreen 
                  themeSelect={themeSelect} 
                  themeIsSelected={themeIsSelected} 
                  isConnected={isConnected}         
                  socketMessage={socketMessage}   
                />
            ) : themeIsSelected && !mapData ? (
                 <div className="loading-container" style={{zIndex: 0}}>
                   <p>Loading Map Data...</p>
                   <div className="loading-spinner"></div>
                 </div>
            ) : null }

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
