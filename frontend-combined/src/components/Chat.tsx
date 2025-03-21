import { useState, useEffect, useRef } from 'react';
import './Chat.css';

interface ChatProps {
  messages: Array<{content: string, sender: string, isError?: boolean}>;
  sendTextMessage: (message: string) => void;
  isThinking: boolean;
  isConnected: boolean;
}

const Chat = ({ messages, sendTextMessage, isThinking, isConnected }: ChatProps) => {
  const [message, setMessage] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [voiceLevel, setVoiceLevel] = useState(0);
  
  // Scroll to bottom of messages
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (message.trim() === '') return;
    
    sendTextMessage(message);
    setMessage('');
  };
  
  // Start voice recording (this is a placeholder, would need actual implementation)
  const handleVoiceClick = () => {
    if (isRecording) {
      // Stop recording
      setIsRecording(false);
      setVoiceLevel(0);
      
      // For demo purposes, just simulate receiving some voice
      sendTextMessage("Voice message");
    } else {
      // Start recording
      setIsRecording(true);
      
      // Animate the voice level indicator (for demo)
      const voiceLevelInterval = setInterval(() => {
        setVoiceLevel(Math.random() * 100);
      }, 100);
      
      // Stop after 3 seconds (demo)
      setTimeout(() => {
        clearInterval(voiceLevelInterval);
        setIsRecording(false);
        setVoiceLevel(0);
        
        // For demo purposes, send a message
        sendTextMessage("Voice command: make the character jump");
      }, 3000);
    }
  };
  
  return (
    <div className="chat-container">
      <div className="chat-header">
        <h2>Chat</h2>
        <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
          {isConnected ? 'Connected' : 'Disconnected'}
        </div>
      </div>
      
      <div className="messages-container">
        {messages.map((msg, index) => (
          <div 
            key={index} 
            className={`message ${msg.sender}-message ${msg.isError ? 'error' : ''}`}
          >
            {msg.content}
          </div>
        ))}
        
        {isThinking && (
          <div className="thinking-indicator">
            <div className="dot"></div>
            <div className="dot"></div>
            <div className="dot"></div>
            <span>Thinking</span>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      <div className="input-area">
        <form onSubmit={handleSubmit}>
          <input 
            type="text" 
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Type your message..." 
            disabled={!isConnected}
          />
          <button type="submit" disabled={!isConnected}>Send</button>
          <button 
            type="button" 
            className={`voice-button ${isRecording ? 'recording' : ''}`}
            onClick={handleVoiceClick}
            disabled={!isConnected}
          >
            <span className="voice-icon">🎤</span>
          </button>
        </form>
        
        {isRecording && (
          <div className="recording-indicator">
            Recording...
            <div className="voice-level-container">
              <div 
                className="voice-level" 
                style={{ width: `${voiceLevel}%` }}
              ></div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Chat; 