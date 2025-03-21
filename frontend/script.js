/**
 * Game Character Control - Frontend Script
 * Handles WebSocket communication, voice recording, and UI interactions
 */

// Configuration
const WS_URL = 'ws://localhost:8080/ws'; // WebSocket server URL

// DOM Elements
const messageForm = document.getElementById('message-form');
const messageInput = document.getElementById('message-input');
const messagesContainer = document.getElementById('messages');
const connectionStatus = document.getElementById('connection-status');
const voiceButton = document.getElementById('voice-button');
const recordingIndicator = document.getElementById('recording-indicator');
const characterSprite = document.getElementById('character-sprite');

// State variables
let socket;
let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let isConnected = false;

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
        
        // Try to reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
    });
    
    // Connection error
    socket.addEventListener('error', (error) => {
        console.error('WebSocket error:', error);
        isConnected = false;
        updateConnectionStatus('Connection Error');
    });
    
    // Listen for messages from the server
    socket.addEventListener('message', (event) => {
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
            executeCommand(data.name, data.result);
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

// Execute a command from the character
function executeCommand(commandName, result) {
    console.log(`Executing command: ${commandName}`);
    
    switch (commandName) {
        case 'jump':
            // Animate the character jumping
            characterSprite.classList.add('jumping');
            setTimeout(() => {
                characterSprite.classList.remove('jumping');
            }, 500);
            break;
            
        case 'talk':
            // Animate the character talking
            characterSprite.classList.add('talking');
            setTimeout(() => {
                characterSprite.classList.remove('talking');
            }, 2000);
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

// Setup voice recording
async function setupVoiceRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        mediaRecorder = new MediaRecorder(stream);
        
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
            // Signal the end of the audio stream
            if (isConnected) {
                const data = {
                    type: 'audio_end'
                };
                socket.send(JSON.stringify(data));
            }
            
            // Reset audio chunks
            audioChunks = [];
        });
        
        return true;
    } catch (error) {
        console.error('Error accessing microphone:', error);
        return false;
    }
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