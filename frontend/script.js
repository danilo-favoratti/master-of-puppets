/**
 * Game Character Control - Frontend Script
 * Handles WebSocket communication, voice recording, and UI interactions
 */

// Configuration
const WS_URL = 'wss://masterofpuppets-ws.favoratti.com/ws'; // Updated WebSocket server URL

// DOM Elements
const messageForm = document.getElementById('message-form');
const messageInput = document.getElementById('message-input');
const messagesContainer = document.getElementById('messages');
const connectionStatus = document.getElementById('connection-status');
const voiceButton = document.getElementById('voice-button');
const recordingIndicator = document.getElementById('recording-indicator');
const characterSprite = document.getElementById('character-sprite');
const thinkingIndicator = document.getElementById('thinking-indicator');
const voiceLevelElement = document.getElementById('voice-level');

// State variables
let socket;
let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let isConnected = false;
let isThinking = false;
let audioContext;
let analyser;
let microphone;
let animationFrame;

// Show or hide the thinking indicator
function setThinking(thinking) {
    isThinking = thinking;
    if (thinking) {
        thinkingIndicator.classList.add('active');
    } else {
        thinkingIndicator.classList.remove('active');
    }
}

// Connect to WebSocket server
function connectWebSocket() {
    socket = new WebSocket(WS_URL);
    
    // Connection opened
    socket.addEventListener('open', () => {
        console.log('WebSocket connection established');
        isConnected = true;
        updateConnectionStatus('Connected');
    });
    
    // Connection closed
    socket.addEventListener('close', () => {
        console.log('WebSocket connection closed');
        isConnected = false;
        updateConnectionStatus('Disconnected');
        setThinking(false); // Make sure to clear thinking state on disconnect
        
        // Try to reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
    });
    
    // Connection error
    socket.addEventListener('error', (error) => {
        console.error('WebSocket error:', error);
        isConnected = false;
        updateConnectionStatus('Connection Error');
        setThinking(false); // Make sure to clear thinking state on error
    });
    
    // Listen for messages from the server
    socket.addEventListener('message', (event) => {
        // Hide thinking indicator when we get a response
        setThinking(false);
        
        const data = JSON.parse(event.data);
        handleServerMessage(data);
    });
}

// Update connection status display
function updateConnectionStatus(status) {
    connectionStatus.textContent = status;
    connectionStatus.className = 'connection-status';
    
    if (status === 'Connected') {
        connectionStatus.classList.add('connected');
    } else {
        connectionStatus.classList.add('disconnected');
    }
}

// Handle incoming messages from the server
function handleServerMessage(data) {
    console.log('Received message:', data);
    
    switch (data.type) {
        case 'text':
            // Display regular text message
            addMessage(data.content, 'character');
            break;
            
        case 'command':
            // Execute a command and display the result
            executeCommand(data.name, data.result, data.params);
            break;
            
        case 'error':
            // Display error message
            console.error('Server error:', data.content);
            addMessage(`Error: ${data.content}`, 'character', true);
            break;
            
        default:
            console.warn('Unknown message type:', data.type);
    }
}

// Add a message to the chat display
function addMessage(content, sender, isError = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    
    if (isError) {
        messageDiv.classList.add('error');
    }
    
    messageDiv.textContent = content;
    messagesContainer.appendChild(messageDiv);
    
    // Scroll to the bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Add a voice message indicator to chat
function addVoiceMessageIndicator() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message user-message voice-message';
    messageDiv.innerHTML = '🎤 <em>Voice message sent</em>';
    messagesContainer.appendChild(messageDiv);
    
    // Scroll to the bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Execute a command from the character
function executeCommand(commandName, result, params) {
    console.log(`Executing command: ${commandName}`, params);
    
    const direction = params?.direction || null;
    
    switch (commandName) {
        case 'jump':
            // Animate the character jumping in the specified direction
            if (direction) {
                characterSprite.classList.add(`jumping-${direction}`);
                setTimeout(() => {
                    characterSprite.classList.remove(`jumping-${direction}`);
                }, 500);
            } else {
                characterSprite.classList.add('jumping');
                setTimeout(() => {
                    characterSprite.classList.remove('jumping');
                }, 500);
            }
            break;
            
        case 'talk':
            // Animate the character talking
            characterSprite.classList.add('talking');
            setTimeout(() => {
                characterSprite.classList.remove('talking');
            }, 2000);
            break;
            
        case 'walk':
            // Animate the character walking in the specified direction
            characterSprite.classList.add(`walking-${direction}`);
            setTimeout(() => {
                characterSprite.classList.remove(`walking-${direction}`);
            }, 1000);
            break;
            
        case 'run':
            // Animate the character running in the specified direction
            characterSprite.classList.add(`running-${direction}`);
            setTimeout(() => {
                characterSprite.classList.remove(`running-${direction}`);
            }, 600);
            break;
            
        case 'push':
            // Animate the character pushing in the specified direction
            characterSprite.classList.add(`pushing-${direction}`);
            setTimeout(() => {
                characterSprite.classList.remove(`pushing-${direction}`);
            }, 800);
            break;
            
        case 'pull':
            // Animate the character pulling in the specified direction
            characterSprite.classList.add(`pulling-${direction}`);
            setTimeout(() => {
                characterSprite.classList.remove(`pulling-${direction}`);
            }, 800);
            break;
            
        default:
            console.warn('Unknown command:', commandName);
    }
    
    // Display the command result
    addCommandMessage(result);
}

// Add a command message to the chat
function addCommandMessage(content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'command-message';
    messageDiv.textContent = content;
    messagesContainer.appendChild(messageDiv);
    
    // Scroll to the bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Send a text message to the server
function sendTextMessage(message) {
    if (!isConnected) {
        console.error('Not connected to WebSocket server');
        return;
    }
    
    // Show thinking indicator
    setThinking(true);
    
    const data = {
        type: 'text',
        content: message
    };
    
    socket.send(JSON.stringify(data));
    
    // Display the user's message
    addMessage(message, 'user');
    
    // Clear the input field
    messageInput.value = '';
}

// Setup voice recording and audio analysis
async function setupVoiceRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        mediaRecorder = new MediaRecorder(stream);
        
        // Set up audio analysis
        if (!audioContext) {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
        
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        microphone = audioContext.createMediaStreamSource(stream);
        microphone.connect(analyser);
        
        // Handle audio data
        mediaRecorder.addEventListener('dataavailable', (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
                
                // Send the audio chunk to the server
                if (isConnected) {
                    const reader = new FileReader();
                    reader.onload = () => {
                        socket.send(reader.result);
                    };
                    reader.readAsArrayBuffer(event.data);
                }
            }
        });
        
        // Handle recording stop
        mediaRecorder.addEventListener('stop', () => {
            // Show voice message indicator in chat
            if (audioChunks.length > 0) {
                addVoiceMessageIndicator();
            }
            
            // Signal the end of the audio stream
            if (isConnected) {
                // Show thinking indicator when sending audio
                setThinking(true);
                
                const data = {
                    type: 'audio_end'
                };
                socket.send(JSON.stringify(data));
            }
            
            // Stop visualizing audio
            if (animationFrame) {
                cancelAnimationFrame(animationFrame);
                animationFrame = null;
            }
            
            // Reset the voice level display
            voiceLevelElement.style.width = '0%';
            
            // Reset audio chunks
            audioChunks = [];
        });
        
        return true;
    } catch (error) {
        console.error('Error accessing microphone:', error);
        return false;
    }
}

// Visualize audio levels
function visualizeAudio() {
    if (!analyser) return;
    
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    
    function updateVoiceLevel() {
        analyser.getByteFrequencyData(dataArray);
        
        // Calculate average volume level
        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
            sum += dataArray[i];
        }
        const average = sum / bufferLength;
        
        // Scale to percentage (0-100%)
        // Adjust the divider (128) to make the meter more or less sensitive
        let percentage = (average / 128) * 100;
        percentage = Math.min(100, percentage); // Cap at 100%
        
        // Update the voice level display
        voiceLevelElement.style.width = percentage + '%';
        
        // Continue the animation loop if still recording
        if (isRecording) {
            animationFrame = requestAnimationFrame(updateVoiceLevel);
        }
    }
    
    // Start the animation loop
    animationFrame = requestAnimationFrame(updateVoiceLevel);
}

// Toggle voice recording
async function toggleVoiceRecording() {
    if (!mediaRecorder) {
        const setup = await setupVoiceRecording();
        if (!setup) {
            alert('Could not access microphone. Please check your browser permissions.');
            return;
        }
    }
    
    if (isRecording) {
        // Stop recording
        mediaRecorder.stop();
        isRecording = false;
        voiceButton.classList.remove('recording');
        recordingIndicator.classList.remove('active');
    } else {
        // Start recording
        audioChunks = [];
        mediaRecorder.start(100); // Collect audio in 100ms chunks
        isRecording = true;
        voiceButton.classList.add('recording');
        recordingIndicator.classList.add('active');
        
        // Start visualizing audio
        visualizeAudio();
    }
}

// Event Listeners
messageForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const message = messageInput.value.trim();
    if (message) {
        sendTextMessage(message);
    }
});

voiceButton.addEventListener('click', () => {
    toggleVoiceRecording();
});

// Initialize the application
function init() {
    // Connect to WebSocket server
    connectWebSocket();
}

// Start the app
init(); 