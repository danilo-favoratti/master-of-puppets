import React, { useState, useEffect, useRef } from 'react';
import './Chat.css';

interface ChatProps {
  messages: Array<{content: string, sender: string, isError?: boolean}>;
  sendTextMessage: (message: string) => void;
  isThinking: boolean;
  isConnected: boolean;
  websocket: WebSocket | null; // Add WebSocket prop for direct access
}

const Chat = ({ messages, sendTextMessage, isThinking, isConnected, websocket }: ChatProps) => {
  const [message, setMessage] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [voiceLevel, setVoiceLevel] = useState(0);
  
  // Audio recording refs
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const microphoneRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  
  // Audio playback
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  
  // Add a debug flag near the top
  const DEBUG = true;
  
  // Add state for audio processing
  const [isProcessingAudio, setIsProcessingAudio] = useState(false);
  
  // Add state for waiting for agent response
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);
  
  // Add state to track initial mount
  const [isInitialMount, setIsInitialMount] = useState(true);
  
  // Add a timer ref to handle timeouts
  const processingTimerRef = useRef<number | null>(null);
  
  // Add an additional timer ref for waiting state timeout
  const waitingTimerRef = useRef<number | null>(null);
  
  // Add a ref to track if we've explicitly started processing
  const hasStartedProcessingRef = useRef<boolean>(false);
  
  // Initialize audio player
  useEffect(() => {
    console.log("Initializing audio player");
    
    // Create audio element if not exists
    if (!audioPlayerRef.current) {
      const audio = new Audio();
      
      // Prevent automatic loading/playing which can cause errors
      audio.autoplay = false;
      audio.preload = "auto"; // Change to auto for better initialization
      
      // Set an empty audio source to prevent errors
      // Use a tiny silent MP3 or a data URL with a valid audio format
      audio.src = 'data:audio/mp3;base64,SUQzBAAAAAABEVRYWFgAAAAtAAADY29tbWVudABCaWdTb3VuZEJhbmsuY29tIC8gTGFTb25vdGhlcXVlLm9yZwBURU5DAAAAHQAAA1N3aXRjaCBQbHVzIMKpIE5DSCBTb2Z0d2FyZQBUSVQyAAAABgAAAzIyMzUAVFNTRQAAAA8AAANMYXZmNTcuODMuMTAwAAAAAAAAAAAAAAD/80DEAAAAA0gAAAAATEFNRTMuMTAwVVVVVVVVVVVVVUxBTUUzLjEwMFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVf/zQsRbAAADSAAAAABVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVf/zQMSkAAADSAAAAABVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV';
      
      // Initialize volume
      audio.volume = 1.0;
      audio.muted = false;
      
      audioPlayerRef.current = audio;
      console.log("Created new Audio element with autoplay=false and preload=auto");
      
      // Try to unlock audio on first user interaction
      const unlockAudio = () => {
        if (audioPlayerRef.current) {
          // Play a silent sound
          audioPlayerRef.current.play()
            .then(() => {
              console.log("Audio unlocked successfully");
              // Stop playing the silent audio immediately
              audioPlayerRef.current?.pause();
              audioPlayerRef.current!.currentTime = 0;
            })
            .catch(err => {
              console.log("Could not unlock audio:", err);
            });
        }
        
        // Remove the listener once we've tried to unlock
        document.removeEventListener('click', unlockAudio);
        document.removeEventListener('touchstart', unlockAudio);
      };
      
      // Add listeners to unlock audio on first interaction
      document.addEventListener('click', unlockAudio, { once: true });
      document.addEventListener('touchstart', unlockAudio, { once: true });
    }
    
    // Set up event listeners
    const onPlay = () => {
      console.log("Audio playback started");
      setIsPlaying(true);
    };
    
    const onEnded = () => {
      console.log("Audio playback ended");
      setIsPlaying(false);
    };
    
    const onPause = () => {
      console.log("Audio playback paused");
      setIsPlaying(false);
    };
    
    const onError = (e: Event) => {
      // Only log real errors, not initialization ones
      const element = e.target as HTMLAudioElement;
      if (element && element.error && element.error.code !== MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED) {
        console.error("Audio playback error:", e);
        // Try to get more information about the error
        if (audioPlayerRef.current && audioPlayerRef.current.error) {
          console.error("Error code:", audioPlayerRef.current.error.code);
          console.error("Error message:", audioPlayerRef.current.error.message);
        }
        setIsPlaying(false);
        
        // Show a message to the user about enabling sound
        if (element.error.code === MediaError.MEDIA_ERR_ABORTED || 
            element.error.code === MediaError.MEDIA_ERR_NETWORK) {
          alert("Please ensure your browser allows audio playback for this site.");
        }
      }
    };
    
    // Attach listeners
    if (audioPlayerRef.current) {
      audioPlayerRef.current.addEventListener('play', onPlay);
      audioPlayerRef.current.addEventListener('ended', onEnded);
      audioPlayerRef.current.addEventListener('pause', onPause);
      audioPlayerRef.current.addEventListener('error', onError);
    }
    
    // Clean up
    return () => {
      console.log("Cleaning up audio player");
      if (audioPlayerRef.current) {
        audioPlayerRef.current.removeEventListener('play', onPlay);
        audioPlayerRef.current.removeEventListener('ended', onEnded);
        audioPlayerRef.current.removeEventListener('pause', onPause);
        audioPlayerRef.current.removeEventListener('error', onError);
        audioPlayerRef.current.pause();
        audioPlayerRef.current.src = '';
      }
    };
  }, []);
  
  // Reset all UI state indicators on component mount
  useEffect(() => {
    console.log("Resetting all UI state indicators on component mount");
    // Reset recording state
    setIsRecording(false);
    // Reset audio processing state
    setIsProcessingAudio(false);
    // Reset waiting for response state
    setIsWaitingForResponse(false);
    // Reset voice level
    setVoiceLevel(0);
    // Reset processing flag
    hasStartedProcessingRef.current = false;
    // Clear any existing timers
    if (processingTimerRef.current) {
      window.clearTimeout(processingTimerRef.current);
      processingTimerRef.current = null;
    }
    if (waitingTimerRef.current) {
      window.clearTimeout(waitingTimerRef.current);
      waitingTimerRef.current = null;
    }
    
    // Mark that we're no longer in initial mount after a short delay
    setTimeout(() => {
      setIsInitialMount(false);
    }, 500);
  }, []);
  
  // Scroll to bottom of messages - improved to ensure visibility
  useEffect(() => {
    if (messagesEndRef.current) {
      // Use a small timeout to ensure DOM updates are complete
      setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({ 
          behavior: 'smooth',
          block: 'end' // Align to bottom
        });
      }, 100);
    }
  }, [
    messages, 
    isThinking, 
    isRecording, 
    isProcessingAudio, 
    isWaitingForResponse, 
    isPlaying
  ]); // Add all state variables that affect rendering
  
  // Set up WebSocket listeners for audio
  useEffect(() => {
    if (!websocket) return;
    
    let audioChunks: Uint8Array[] = [];
    let isReceivingAudio = false;
    let audioStartReceived = false;
    
    console.log("Setting up WebSocket listeners for audio");
    
    // Reset UI states when WebSocket changes
    setIsProcessingAudio(false);
    setIsWaitingForResponse(false);
    
    const handleMessage = (event: MessageEvent) => {
      try {
        // Handle text messages (JSON)
        if (typeof event.data === 'string') {
          try {
            const data = JSON.parse(event.data);
            console.log("WebSocket received JSON message:", data.type);
            
            // When we receive a text or transcription response, audio processing is complete
            if (data.type === 'text' || data.type === 'user_message') {
              if (data.type === 'user_message') {
                // When we get a transcription, end processing state and start waiting
                if (isProcessingAudio) {
                  console.log("Audio transcription received, ending processing state and starting waiting state");
                  setIsProcessingAudio(false);
                  startWaitingWithTimeout();
                }
              } else if (data.type === 'text') {
                // When we get a text response from the agent, end waiting
                console.log("Got response from agent");
                setIsWaitingForResponse(false);
              }
            }
            
            // Handle audio metadata
            if (data.type === 'audio_start') {
              console.log("WebSocket: Received audio_start signal");
              isReceivingAudio = true;
              audioStartReceived = true;
              audioChunks = [];
            } 
            else if (data.type === 'audio_end') {
              console.log(`WebSocket: Received audio_end JSON signal, chunks: ${audioChunks.length}, audioStartReceived: ${audioStartReceived}`);
              
              // Only try to play if we have both audio_start and chunks
              if (audioStartReceived && audioChunks.length > 0) {
                console.log(`Playing audio: ${audioChunks.length} chunks totaling ${audioChunks.reduce((acc, chunk) => acc + chunk.length, 0)} bytes`);
                playBufferedAudio(audioChunks);
              } else {
                if (!audioStartReceived) {
                  console.warn("Received audio_end but no audio_start was received");
                }
                if (audioChunks.length === 0) {
                  console.warn("No audio chunks to play after audio_end", new Error().stack);
                }
              }
              
              // Reset state
              isReceivingAudio = false;
              audioStartReceived = false;
              // Clear chunks after failed attempt
              audioChunks = [];
            }
            // Handle error messages - also end processing state
            else if (data.type === 'error') {
              console.error("Received error from server:", data.content);
              setIsProcessingAudio(false);
              setIsWaitingForResponse(false);
            }
          } catch (jsonError) {
            console.error("Error parsing JSON from WebSocket:", jsonError);
          }
        } 
        // Handle binary data (audio chunks)
        else if (event.data instanceof ArrayBuffer) {
          console.log(`WebSocket: Received binary data, size: ${event.data.byteLength} bytes, isReceiving: ${isReceivingAudio}, audioStartReceived: ${audioStartReceived}`);
          
          // Only process binary data if we've received an audio_start
          if (isReceivingAudio && audioStartReceived) {
            try {
              const arrayBuf = new Uint8Array(event.data);
              
              // Check if it's the audio end marker
              const isEndMarker = arrayBuf.length === 12;
              if (isEndMarker) {
                // Convert to string for comparison
                let endMarkerString = '';
                for (let i = 0; i < arrayBuf.length; i++) {
                  endMarkerString += String.fromCharCode(arrayBuf[i]);
                }
                
                if (endMarkerString === '__AUDIO_END__') {
                  console.log(`WebSocket: Received __AUDIO_END__ binary marker, chunks: ${audioChunks.length}`);
                  isReceivingAudio = false;
                  
                  if (audioChunks.length > 0) {
                    console.log(`Playing audio from binary __AUDIO_END__: ${audioChunks.length} chunks totaling ${audioChunks.reduce((acc, chunk) => acc + chunk.length, 0)} bytes`);
                    playBufferedAudio(audioChunks);
                  } else {
                    console.warn("No audio chunks to play after __AUDIO_END__", new Error().stack);
                  }
                  
                  // Reset state
                  audioStartReceived = false;
                  // Clear chunks after attempt
                  audioChunks = [];
                } else {
                  // Regular audio chunk
                  audioChunks.push(arrayBuf);
                  console.log(`Added audio chunk: ${arrayBuf.length} bytes, total chunks: ${audioChunks.length}`);
                }
              } else {
                // Regular audio chunk - perform a detailed log of the first chunk
                if (audioChunks.length === 0) {
                  console.log(`Added FIRST audio chunk: ${arrayBuf.length} bytes, first 30 bytes:`, 
                             Array.from(arrayBuf.slice(0, 30)).map(b => b.toString(16).padStart(2, '0')).join(' '));
                  
                  // Verify this looks like an MP3 header (most MP3s start with ID3 or FF FB)
                  const potentialHeader = Array.from(arrayBuf.slice(0, 3)).map(b => b.toString(16).padStart(2, '0')).join(' ');
                  console.log(`MP3 header check: ${potentialHeader}`);
                  
                  // For safety, check the chunk isn't suspiciously small
                  if (arrayBuf.length < 100) {
                    console.warn(`Suspiciously small first audio chunk: ${arrayBuf.length} bytes`);
                  }
                } else {
                  console.log(`Added audio chunk: ${arrayBuf.length} bytes, total chunks: ${audioChunks.length + 1}`);
                }
                
                // Add the chunk to our collection
                audioChunks.push(arrayBuf);
                
                // Log the accumulated size periodically
                if (audioChunks.length % 5 === 0) {
                  const totalSize = audioChunks.reduce((acc, chunk) => acc + chunk.length, 0);
                  console.log(`Accumulated ${audioChunks.length} chunks, total size: ${totalSize} bytes`);
                }
              }
            } catch (binaryError) {
              console.error("Error processing binary data:", binaryError);
            }
          } else {
            if (!isReceivingAudio) {
              console.warn("Received binary data but isReceivingAudio is false");
            }
            if (!audioStartReceived) {
              console.warn("Received binary data but no audio_start was received");
            }
          }
        }
      } catch (err) {
        console.error('Error in WebSocket message handler:', err);
      }
    };
    
    websocket.addEventListener('message', handleMessage);
    
    return () => {
      console.log("Cleaning up WebSocket audio listeners");
      websocket.removeEventListener('message', handleMessage);
    };
  }, [websocket]);
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (message.trim() === '') return;
    
    sendTextMessage(message);
    setMessage('');
    
    // Start waiting for response after sending a text message
    startWaitingWithTimeout();
  };
  
  // Setup audio visualization
  const visualizeAudio = () => {
    if (!analyserRef.current) return;
    
    const bufferLength = analyserRef.current.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    
    const updateVoiceLevel = () => {
      if (!analyserRef.current) return;
      
      analyserRef.current.getByteFrequencyData(dataArray);
      
      // Calculate average volume level
      let sum = 0;
      for (let i = 0; i < bufferLength; i++) {
        sum += dataArray[i];
      }
      const average = sum / bufferLength;
      
      // Scale to percentage (0-100%)
      let percentage = (average / 128) * 100;
      percentage = Math.min(100, percentage);
      
      setVoiceLevel(percentage);
      
      if (isRecording) {
        animationFrameRef.current = requestAnimationFrame(updateVoiceLevel);
      }
    };
    
    updateVoiceLevel();
  };
  
  // Start voice recording
  const startRecording = async () => {
    try {
      // Clear any previous state to ensure clean recording
      if (isProcessingAudio || isWaitingForResponse) {
        console.log("Clearing previous states before starting new recording");
        setIsProcessingAudio(false);
        setIsWaitingForResponse(false);
        
        if (processingTimerRef.current) {
          window.clearTimeout(processingTimerRef.current);
          processingTimerRef.current = null;
        }
        if (waitingTimerRef.current) {
          window.clearTimeout(waitingTimerRef.current);
          waitingTimerRef.current = null;
        }
      }
      
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      // Set up AudioContext for visualization
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      const microphone = audioContext.createMediaStreamSource(stream);
      microphone.connect(analyser);
      
      // Store refs
      audioContextRef.current = audioContext;
      analyserRef.current = analyser;
      microphoneRef.current = microphone;
      
      // Setup MediaRecorder with specific options for better audio quality
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm',  // Specify webm format
        audioBitsPerSecond: 128000  // 128 kbps audio
      });
      mediaRecorderRef.current = mediaRecorder;
      
      // Accumulate chunks locally before sending to avoid data loss
      let localChunks: Blob[] = [];
      
      mediaRecorder.addEventListener('dataavailable', (event) => {
        if (event.data.size > 0) {
          console.log(`Recording data available: ${event.data.size} bytes`);
          localChunks.push(event.data);
        }
      });
      
      mediaRecorder.addEventListener('stop', () => {
        console.log('MediaRecorder stopped, sending accumulated data');
        
        // Combine all chunks into a single blob
        const completeBlob = new Blob(localChunks, { type: 'audio/webm' });
        console.log(`Complete recording size: ${completeBlob.size} bytes`);
        
        if (websocket && websocket.readyState === WebSocket.OPEN) {
          // Convert Blob to ArrayBuffer and send to server
          const reader = new FileReader();
          reader.onload = () => {
            if (reader.result instanceof ArrayBuffer && websocket.readyState === WebSocket.OPEN) {
              const buffer = reader.result;
              console.log(`Sending complete audio data to server: ${buffer.byteLength} bytes`);
              
              // Verify buffer has content
              if (buffer.byteLength > 0) {
                // Log first 10 bytes for debugging
                const view = new Uint8Array(buffer);
                console.log(`First 10 bytes of audio data: [${Array.from(view.slice(0, 10)).join(', ')}]`);
                
                // Send the binary data first
                websocket.send(buffer);
                
                // Then signal the end of audio after a small delay to ensure the binary data is processed
                setTimeout(() => {
                  if (websocket.readyState === WebSocket.OPEN) {
                    console.log("Sending audio_end signal");
                    websocket.send(JSON.stringify({
                      type: 'audio_end'
                    }));
                    
                    // Only show processing immediately after recording, before transcription
                    startProcessingWithTimeout();
                  }
                }, 200);
              } else {
                console.warn("Empty audio buffer, not sending");
                // Notify user of empty recording
                alert("No audio was recorded. Please try again and speak into your microphone.");
              }
            }
          };
          reader.readAsArrayBuffer(completeBlob);
        }
      });
      
      // Start recording
      mediaRecorder.start();
      setIsRecording(true);
      
      // Start visualizing audio
      visualizeAudio();
      
    } catch (err) {
      console.error('Error accessing microphone:', err);
      alert('Could not access microphone. Please check your browser permissions.');
    }
  };
  
  // Stop voice recording
  const stopRecording = () => {
    // Stop MediaRecorder
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      console.log("Stopping MediaRecorder - chunks will be processed in the stop event handler");
      mediaRecorderRef.current.stop();
    }
    
    // Stop audio tracks
    if (mediaRecorderRef.current && mediaRecorderRef.current.stream) {
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
    }
    
    // Cancel animation frame
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    
    // Clean up AudioContext and related nodes
    if (microphoneRef.current) {
      microphoneRef.current.disconnect();
      microphoneRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (analyserRef.current) {
      analyserRef.current.disconnect && analyserRef.current.disconnect();
      analyserRef.current = null;
    }
    
    // Reset MediaRecorder ref (will be cleaned up after stop event)
    // Don't set to null yet as we need it for the stop event
    
    // Reset UI state
    setIsRecording(false);
    setVoiceLevel(0);
    
    // Note: We don't start processing or send audio_end here anymore
    // That's handled in the MediaRecorder's stop event listener
  };
  
  // Handle voice button click
  const handleVoiceClick = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };
  
  // Helper function to detect audio format from header bytes
  const detectAudioFormat = (firstChunk: Uint8Array): string => {
    if (!firstChunk || firstChunk.length < 4) {
      console.log("Not enough data to detect audio format, defaulting to audio/mpeg");
      return 'audio/mpeg';
    }

    // Check for MP3 header (usually starts with ID3 or first byte is 0xFF)
    if (
      (firstChunk[0] === 0x49 && firstChunk[1] === 0x44 && firstChunk[2] === 0x33) || // ID3
      (firstChunk[0] === 0xFF && (firstChunk[1] & 0xE0) === 0xE0) // MPEG sync word
    ) {
      console.log("Detected MP3 format");
      return 'audio/mpeg';
    }
    
    // Check for WAV header
    if (
      firstChunk[0] === 0x52 && firstChunk[1] === 0x49 && 
      firstChunk[2] === 0x46 && firstChunk[3] === 0x46
    ) {
      console.log("Detected WAV format");
      return 'audio/wav';
    }
    
    // Check for Ogg/Opus/Vorbis header
    if (
      firstChunk[0] === 0x4F && firstChunk[1] === 0x67 && 
      firstChunk[2] === 0x67 && firstChunk[3] === 0x53
    ) {
      console.log("Detected Ogg format");
      return 'audio/ogg';
    }
    
    // Default to MP3 if format is unknown
    console.log("Unknown audio format, defaulting to audio/mpeg");
    return 'audio/mpeg';
  };

  // Add a function to play buffered audio
  const playBufferedAudio = (chunks: Uint8Array[]) => {
    if (DEBUG) console.log("Playing buffered audio, chunks:", chunks.length);
    
    if (chunks.length === 0) {
      console.error("No audio chunks to play");
      return;
    }
    
    try {
      // Log first few bytes for debugging
      let mimeType = 'audio/mpeg';
      if (chunks.length > 0 && chunks[0].length > 0) {
        const firstChunk = chunks[0];
        const headerBytes = Array.from(firstChunk.slice(0, 16)).map(b => b.toString(16).padStart(2, '0')).join(' ');
        console.log(`First 16 bytes of audio data: ${headerBytes}`);
        
        // Auto-detect audio format
        mimeType = detectAudioFormat(firstChunk);
      }
      
      // Create a new Blob from the audio chunks with detected MIME type
      const blob = new Blob(chunks, { type: mimeType });
      console.log(`Created audio blob with type ${mimeType}, size: ${blob.size}`);
      
      // Create a URL for the blob
      const url = URL.createObjectURL(blob);
      console.log("Created URL for audio blob:", url);
      
      // Save blob to file (for debugging)
      if (DEBUG) {
        try {
          const debugLink = document.createElement('a');
          debugLink.href = url;
          debugLink.download = `audio_debug_${Date.now()}.mp3`;
          document.body.appendChild(debugLink);
          debugLink.click();
          document.body.removeChild(debugLink);
          console.log("Saved debug audio file");
        } catch (e) {
          console.error("Error saving debug audio:", e);
        }
      }
      
      // Try with main audio player first for more reliable playback
      tryPlayWithMainAudio(url);
      
      // Also try with an invisible audio element as backup
      const invisibleAudio = document.createElement('audio');
      invisibleAudio.setAttribute('playsinline', '');
      invisibleAudio.setAttribute('controls', '');
      invisibleAudio.style.display = 'none';
      invisibleAudio.src = url;
      document.body.appendChild(invisibleAudio);
      
      // Add event listeners for debugging
      invisibleAudio.addEventListener('play', () => {
        console.log('Invisible audio started playing');
        setIsPlaying(true);
      });
      
      invisibleAudio.addEventListener('ended', () => {
        console.log('Invisible audio finished playing');
        setIsPlaying(false);
        document.body.removeChild(invisibleAudio);
      });
      
      invisibleAudio.addEventListener('error', (e) => {
        console.error('Invisible audio error:', e);
        
        if (invisibleAudio.error) {
          console.error(`Error code: ${invisibleAudio.error.code}, Message: ${invisibleAudio.error.message}`);
        }
        
        setIsPlaying(false);
        document.body.removeChild(invisibleAudio);
      });
      
      // Try to play the backup audio element
      setTimeout(() => {
        try {
          invisibleAudio.play()
            .catch(err => {
              console.log('Invisible audio play failed:', err);
            });
        } catch (e) {
          console.log('Auto-play attempt failed:', e);
        }
      }, 500);
    } catch (error) {
      console.error("Error in playBufferedAudio:", error);
    }
  };
  
  // Helper function to try playing with the main audio player
  const tryPlayWithMainAudio = (url: string) => {
    try {
      console.log("Trying with main audio player");
      if (!audioPlayerRef.current) {
        console.error("Audio player not initialized yet");
        const audio = new Audio();
        audio.autoplay = false;
        audio.preload = "auto";
        audioPlayerRef.current = audio;
        console.log("Created new Audio element on-the-fly");
      }
      
      // Reset the audio element
      try {
        audioPlayerRef.current.pause();
        audioPlayerRef.current.currentTime = 0;
      } catch (e) {
        console.warn("Error resetting audio element:", e);
      }
      
      // Set up audio for playback
      audioPlayerRef.current.src = url;
      audioPlayerRef.current.preload = "auto";
      
      // Force unmute the audio element
      audioPlayerRef.current.muted = false;
      audioPlayerRef.current.volume = 1.0;
      
      // Let the browser know we want to play audio
      audioPlayerRef.current.load();
      
      console.log("Attempting to play with main audio player...");
      
      // Add a retry mechanism
      let retryCount = 0;
      const maxRetries = 3;
      
      const attemptPlay = () => {
        audioPlayerRef.current!.play()
          .then(() => {
            console.log("Main audio player playback started successfully");
          })
          .catch(err => {
            console.error(`Error playing with main audio player (attempt ${retryCount + 1}/${maxRetries}):`, err);
            
            if (retryCount < maxRetries) {
              retryCount++;
              console.log(`Retrying playback in ${retryCount * 500}ms...`);
              
              // Try again with a delay
              setTimeout(attemptPlay, retryCount * 500);
            } else {
              console.error("Failed to play audio after multiple attempts");
              
              // Show alert to user only on the final failure
              if (err.name === 'NotAllowedError') {
                alert("Audio playback was blocked. Please enable autoplay in your browser settings for this site.");
              } else if (err.name === 'AbortError' || err.name === 'NotSupportedError') {
                alert("The audio format is not supported by your browser. You may not hear responses.");
              }
            }
          });
      };
      
      attemptPlay();
    } catch (error) {
      console.error("Error in tryPlayWithMainAudio:", error);
    }
  };
  
  // Clear the processing timer when component unmounts
  useEffect(() => {
    return () => {
      if (processingTimerRef.current) {
        window.clearTimeout(processingTimerRef.current);
      }
      if (waitingTimerRef.current) {
        window.clearTimeout(waitingTimerRef.current);
      }
    };
  }, []);
  
  // Set processing state with timeout
  const startProcessingWithTimeout = () => {
    setIsProcessingAudio(true);
    hasStartedProcessingRef.current = true;
    console.log("Audio processing started");
    
    // Clear any existing timer
    if (processingTimerRef.current) {
      window.clearTimeout(processingTimerRef.current);
    }
    
    // Set a timeout to clear the processing state after 20 seconds
    processingTimerRef.current = window.setTimeout(() => {
      if (isProcessingAudio) {
        console.log("Audio processing timed out after 20 seconds");
        setIsProcessingAudio(false);
      }
    }, 20000);
  };
  
  // Set waiting state with timeout
  const startWaitingWithTimeout = () => {
    setIsWaitingForResponse(true);
    console.log("Waiting for agent response");
    
    // Clear any existing waiting timer
    if (waitingTimerRef.current) {
      window.clearTimeout(waitingTimerRef.current);
    }
    
    // Set a timeout to clear the waiting state after 30 seconds
    waitingTimerRef.current = window.setTimeout(() => {
      if (isWaitingForResponse) {
        console.log("Waiting for response timed out after 30 seconds");
        setIsWaitingForResponse(false);
      }
    }, 30000);
  };
  
  // Add a useEffect to log state changes
  useEffect(() => {
    console.log(`State change - isRecording: ${isRecording}, isProcessingAudio: ${isProcessingAudio}, isWaitingForResponse: ${isWaitingForResponse}, isThinking: ${isThinking}, isPlaying: ${isPlaying}`);
  }, [isRecording, isProcessingAudio, isWaitingForResponse, isThinking, isPlaying]);
  
  // Force reset all states on initial render with a delay - this should fix any "stuck" states
  useEffect(() => {
    const forceResetTimer = setTimeout(() => {
      console.log("FORCE RESET: Resetting all UI state indicators after timeout");
      setIsRecording(false);
      setIsProcessingAudio(false);
      setIsWaitingForResponse(false);
      setIsPlaying(false);
      hasStartedProcessingRef.current = false;
    }, 300);
    
    return () => clearTimeout(forceResetTimer);
  }, []);
  
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
        
        {isRecording && !isThinking && (
          <div className="thinking-indicator recording-indicator-chat">
            <div className="dot"></div>
            <div className="dot"></div>
            <div className="dot"></div>
            <span>Recording...</span>
          </div>
        )}
        
        {/* Only show processing before we get transcription */}
        {isProcessingAudio && !isThinking && !isRecording && !isInitialMount && hasStartedProcessingRef.current && !messages.some(m => m.sender === 'user' && m.content.length > 0) && (
          <div className="thinking-indicator processing-audio">
            <div className="dot"></div>
            <div className="dot"></div>
            <div className="dot"></div>
            <span>Processing Voice</span>
          </div>
        )}
        
        {/* Show waiting response indicator when appropriate */}
        {isWaitingForResponse && !isThinking && !isRecording && !isProcessingAudio && (
          <div className="thinking-indicator waiting-response">
            <div className="dot"></div>
            <div className="dot"></div>
            <div className="dot"></div>
            <span>Waiting for response...</span>
          </div>
        )}
        
        {isPlaying && (
          <div className="audio-indicator">
            <div className="audio-wave"></div>
            <span>Speaking</span>
          </div>
        )}
        
        {/* Empty spacer div to ensure padding at bottom */}
        <div className="messages-end-spacer"></div>
        
        {/* Ref for scroll target */}
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
      </div>
    </div>
  );
};

export default Chat;