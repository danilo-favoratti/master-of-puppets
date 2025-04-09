import React, { useEffect, useRef, useState, useCallback, forwardRef, useImperativeHandle } from "react";
import './Chat.css';  // Import the CSS file

// Global music player singleton - outside component to prevent re-renders from affecting it
class BackgroundMusicPlayer {
  private static instance: BackgroundMusicPlayer;
  private _audio: HTMLAudioElement | null = null;
  private isPlaying: boolean = false;

  private constructor() {
    // Private constructor to enforce singleton
  }

  public static getInstance(): BackgroundMusicPlayer {
    if (!BackgroundMusicPlayer.instance) {
      BackgroundMusicPlayer.instance = new BackgroundMusicPlayer();
    }
    return BackgroundMusicPlayer.instance;
  }

  public initialize(): void {
    // Empty function - implementation moved outside React lifecycle
  }

  public getAudioElement(): HTMLAudioElement | null {
    return this._audio;
  }

  public setAudioElement(audio: HTMLAudioElement): void {
    this._audio = audio;
  }

  public play(): void {
    // Empty function - implementation moved outside React lifecycle
  }

  public pause(): void {
    // Empty function - implementation moved outside React lifecycle
  }

  public getIsPlaying(): boolean {
    return this.isPlaying;
  }
}

// Get the singleton instance
const globalMusicPlayer = BackgroundMusicPlayer.getInstance();

// Define methods exposed by the Chat component ref
export interface ChatRefMethods {
  initializeMusic: () => void;
}

interface ChatProps {
  messages: Array<{ content: string; sender: string; isError?: boolean; options?: string[]; messageId?: string}>;
  sendTextMessage: (message: string) => void;
  isThinking: boolean;
  isConnected: boolean;
  websocket: WebSocket | null; // Add WebSocket prop for direct access
}

// Use forwardRef to allow parent components (like App) to call methods on Chat
const Chat = forwardRef<ChatRefMethods, ChatProps>(({
  messages,
  sendTextMessage,
  isThinking,
  isConnected,
  websocket,
}, ref) => {
  const [message, setMessage] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [voiceLevel, setVoiceLevel] = useState(0);
  
  // State for audio controls but using global player under the hood
  const [isMusicPlaying, setIsMusicPlaying] = useState(true);
  const [isMuted, setIsMuted] = useState(false);
  
  // Audio recording refs
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const microphoneRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  // Audio playback
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);
  const hasPlayedAudioRef = useRef(false);
  const [isPlaying, setIsPlaying] = useState(false);
  // Add a ref to store audio chunks
  const audioChunksRef = useRef<Uint8Array[]>([]);

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

  // Add new state for initial wait
  const [showInitialWait, setShowInitialWait] = useState(true);
  const initialWaitDismissedRef = useRef(false); // Ref to ensure dismissal happens only once

  // Add state for help panel visibility
  const [isHelpVisible, setIsHelpVisible] = useState(false);

  // Keep error handling state
  const [serverError, setServerError] = useState<string | null>(null);
  const errorTimeoutRef = useRef<number | null>(null);

  // Reset all UI state indicators on component mount
  useEffect(() => {
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

    // Reset initial wait state ONLY IF it hasn't been dismissed yet
    if (!initialWaitDismissedRef.current) {
      setShowInitialWait(true);
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
          behavior: "smooth",
          block: "end", // Align to bottom
        });
      }, 100);
    }
  }, [
    messages,
    isThinking,
    isRecording,
    isProcessingAudio,
    isWaitingForResponse,
    isPlaying,
  ]); // Add all state variables that affect rendering

  // First, add a function to handle parsing string messages to check for JSON-in-string formatted messages
  const tryParseJsonInString = (text: string) => {
    try {
      // Safety check for null/undefined
      if (!text) return null;
      
      const cleanText = text.replace(/[\u0000-\u001F\u007F-\u009F]/g, '');
      
      if ((cleanText.trim().startsWith('{') || cleanText.trim().startsWith('[')) && 
          (cleanText.trim().endsWith('}') || cleanText.trim().endsWith(']'))) {
        
        try {
          const parsed = JSON.parse(cleanText);
          
          if (parsed.answers && Array.isArray(parsed.answers)) {
            return parsed;
          }
          
          return parsed;
        } catch (parseError) {
          console.error("⚠️ Error parsing what looks like JSON:", parseError);
          // Try a more lenient approach
          try {
            const sanitized = cleanText
              .replace(/\\"/g, '"')      // Fix escaped quotes
              .replace(/"{/g, '{')       // Fix starting brackets
              .replace(/}"/g, '}')       // Fix ending brackets
              .replace(/\\n/g, '')       // Remove newlines
              .replace(/\\/g, '\\\\');   // Escape backslashes
              
            const reparsed = JSON.parse(sanitized);
            return reparsed;
          } catch (e) {
            console.error("❌ Even sanitized parse failed:", e);
          }
        }
      }
    } catch (e) {
      console.error("❌ Error in tryParseJsonInString:", e);
    }
    return null;
  };

  // Update the WebSocket message handler
  useEffect(() => {
    if (!websocket) return;
    websocket.binaryType = "arraybuffer";

    let isReceivingAudio = false;
    let audioStartReceived = false;

    // Reset UI states when WebSocket changes
    setIsProcessingAudio(false);
    setIsWaitingForResponse(false);

    const handleMessage = (event: MessageEvent) => {
      try {
        // Handle text messages (JSON)
        if (typeof event.data === "string") {
          try {
            const data = JSON.parse(event.data);
            
            // Handle errors
            if (data.type === "error") {
              console.error("WebSocket error message:", data.content);
              setServerError(data.content);
              setIsWaitingForResponse(false);
              
              // Clear error after 5 seconds
              if (errorTimeoutRef.current) {
                clearTimeout(errorTimeoutRef.current);
              }
              errorTimeoutRef.current = setTimeout(() => {
                setServerError(null);
              }, 5000);

              return;
            }

            // Skip audio-related messages
            if (data.type === "audio_start" || data.type === "audio_end" || data.type === "audio_data") {
              // Handle internally without passing up
              switch (data.type) {
                case "audio_start":
                  audioChunksRef.current = [];
                  isReceivingAudio = true;
                  audioStartReceived = true;
                  hasPlayedAudioRef.current = false;
                  break;
                case "audio_end":
                  handleAudioEnd();
                  break;
                default: // audio_data or others handled by binary handler
                  break;
              }
              return; // Don't process further up the chain
            }

            // Handle non-audio JSON messages (errors, commands etc.)
            switch (data.type) {
              // Let App.tsx handle other message types if needed, but filter here
              default:
                // If other message types need handling in Chat.tsx, add cases here
                break;
            }
          } catch (jsonError) {
            console.error("Error parsing JSON from WebSocket:", jsonError, "Raw data:", event.data);
          }
        }
        // Handle binary data (audio chunks)
        else if (event.data instanceof ArrayBuffer) {
          handleBinaryData(event.data);
        }
      } catch (err) {
        console.error("Error in WebSocket message handler:", err);
      }
    };

    // Helper function to handle audio end
    const handleAudioEnd = () => {
      isReceivingAudio = false;
      if (audioChunksRef.current.length > 0) {
        analyzeAudioData(audioChunksRef.current);
        emergencyPlayAudio();
      } else {
        console.error("❌ No audio chunks to play after receiving audio_end");
      }
      setIsProcessingAudio(false);
      setIsWaitingForResponse(false);
    };

    // Emergency direct audio playback method
    const emergencyPlayAudio = () => {
      try {
        if (!audioChunksRef.current || audioChunksRef.current.length === 0) {
          console.error("❌ No audio chunks available for emergency playback");
          return;
        }
        
        const totalBytes = audioChunksRef.current.reduce((total, chunk) => total + chunk.length, 0);
        const combinedArray = new Uint8Array(totalBytes);
        let offset = 0;
        for (const chunk of audioChunksRef.current) {
          combinedArray.set(chunk, offset);
          offset += chunk.length;
        }
        
        const blob = new Blob([combinedArray], { type: "audio/mpeg" });
        const url = URL.createObjectURL(blob);
        const audio = new Audio();
        audio.src = url;
        audio.volume = 1.0;
        audio.muted = isMuted;
        
        audioPlayerRef.current = audio;
        document.body.appendChild(audio);
        
        const playPromise = audio.play();
        if (playPromise) {
          playPromise
            .then(() => { /* Play started */ })
            .catch(error => {
              console.error("🚨 Emergency audio play failed:", error);
              
              // Create manual play button on failure
              const playButton = document.createElement('button');
              playButton.innerText = '▶️ Play Audio';
              playButton.style.position = 'fixed';
              playButton.style.bottom = '10px';
              playButton.style.right = '10px';
              playButton.style.zIndex = '9999';
              playButton.style.padding = '10px';
              playButton.style.backgroundColor = '#ff0000';
              playButton.style.color = 'white';
              playButton.style.border = 'none';
              playButton.style.borderRadius = '5px';
              playButton.style.cursor = 'pointer';
              
              playButton.onclick = () => {
                audio.play().catch(e => console.error("🚨 Manual play failed:", e));
                playButton.remove();
              };
              document.body.appendChild(playButton);
              setTimeout(() => {
                if (document.body.contains(playButton)) {
                  playButton.remove();
                }
              }, 10000);
            });
        }
        // Setup cleanup on end
        audio.onended = () => {
            URL.revokeObjectURL(url);
            if (document.body.contains(audio)) {
                document.body.removeChild(audio);
            }
        };
        audio.onerror = (e) => {
            console.error("🚨 Emergency audio error:", e, audio.error);
            URL.revokeObjectURL(url); // Cleanup URL on error too
            if (document.body.contains(audio)) {
                document.body.removeChild(audio);
            }
        };

      } catch (error) {
        console.error("🚨 Critical error in emergency audio playback:", error);
      }
    };

    // Function to handle binary data (audio chunks)
    const handleBinaryData = (data: ArrayBuffer) => {
      const chunk = new Uint8Array(data);
      if (chunk.length === 12) { // Check for marker
        try {
          let endMarkerString = "";
          for (let i = 0; i < chunk.length; i++) {
            endMarkerString += String.fromCharCode(chunk[i]);
          }
          if (endMarkerString === "__AUDIO_END__") {
            handleAudioEnd();
            return;
          }
        } catch (error) {
          console.error("Error checking for end marker:", error);
        }
      }
      audioChunksRef.current.push(chunk);
    };

    websocket.addEventListener("message", handleMessage);
    return () => {
      websocket.removeEventListener("message", handleMessage);
      if (errorTimeoutRef.current) {
        clearTimeout(errorTimeoutRef.current);
      }
    };
  }, [websocket]);

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
      const audioContext = new (window.AudioContext ||
        (window as any).webkitAudioContext)();
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
        mimeType: "audio/webm", // Specify webm format
        audioBitsPerSecond: 128000, // 128 kbps audio
      });
      mediaRecorderRef.current = mediaRecorder;

      // Accumulate chunks locally before sending to avoid data loss
      let localChunks: Blob[] = [];

      mediaRecorder.addEventListener("dataavailable", (event) => {
        if (event.data.size > 0) {
          localChunks.push(event.data);
        }
      });

      mediaRecorder.addEventListener("stop", () => {
        // Combine all chunks into a single blob
        const completeBlob = new Blob(localChunks, { type: "audio/webm" });

        if (websocket && websocket.readyState === WebSocket.OPEN) {
          // Convert Blob to ArrayBuffer and send to server
          const reader = new FileReader();
          reader.onload = () => {
            if (
              reader.result instanceof ArrayBuffer &&
              websocket.readyState === WebSocket.OPEN
            ) {
              const buffer = reader.result;

              // Send the binary data first
              websocket.send(buffer);

              // Then signal the end of audio after a small delay to ensure the binary data is processed
              setTimeout(() => {
                if (websocket.readyState === WebSocket.OPEN) {
                  websocket.send(
                    JSON.stringify({
                      type: "audio_end",
                    })
                  );

                  // Only show processing immediately after recording, before transcription
                  startProcessingWithTimeout();
                }
              }, 200);
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
      console.error("Error accessing microphone:", err);
      alert(
        "Could not access microphone. Please check your browser permissions."
      );
    }
  };

  // Stop voice recording
  const stopRecording = () => {
    // Stop MediaRecorder
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state !== "inactive"
    ) {
      mediaRecorderRef.current.stop();
    }

    // Stop audio tracks
    if (mediaRecorderRef.current && mediaRecorderRef.current.stream) {
      mediaRecorderRef.current.stream
        .getTracks()
        .forEach((track) => track.stop());
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
      // Stop any currently playing audio before starting recording
      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause();
        audioPlayerRef.current.currentTime = 0;
        setIsPlaying(false);
      }
      startRecording();
    }
  };

  // Updated playBufferedAudio function:
  const playBufferedAudio = (chunks: Uint8Array[]) => {
    try {
      if (!chunks || chunks.length === 0) {
        console.error("❌ No audio chunks to play");
        return;
      }

      // Create a single buffer from all chunks
      const totalLength = chunks.reduce((acc, chunk) => acc + chunk.length, 0);
      
      if (totalLength === 0) {
        console.error("❌ Total audio size is 0 bytes");
        return;
      }
      
      const combined = new Uint8Array(totalLength);
      
      let offset = 0;
      for (const chunk of chunks) {
        combined.set(chunk, offset);
        offset += chunk.length;
      }
      
      // Determine content type based on header analysis
      let contentType = "audio/mpeg"; // Default to MP3
      
      // Check for MP3 header
      if (combined.length >= 3) {
        const hasId3Header = combined[0] === 0x49 && combined[1] === 0x44 && combined[2] === 0x33; // "ID3"
        const hasMp3FrameHeader = combined[0] === 0xFF && (combined[1] & 0xE0) === 0xE0;
        
        if (hasId3Header || hasMp3FrameHeader) {
          contentType = "audio/mpeg";
        }
      }
      
      // Create blob with detected content type
      const blob = new Blob([combined], { type: contentType });
      const url = URL.createObjectURL(blob);
      
      // Create audio element
      const audio = new Audio();
      
      // Set up more comprehensive event handlers
      audio.addEventListener("canplaythrough", () => {
        audio.play()
          .then(() => { /* Playback started */ })
          .catch(e => {
            console.error("❌ Play failed:", e);
            
            // Try alternative approach with user interaction
            const playOnNextClick = () => {
              audio.play().catch(err => console.error("❌ Play on click failed:", err));
              document.removeEventListener("click", playOnNextClick);
            };
            
            document.addEventListener("click", playOnNextClick, { once: true });
          });
      });
      
      audio.addEventListener("ended", () => {
        URL.revokeObjectURL(url);
      });
      
      audio.addEventListener("error", (e) => {
        console.error("❌ Audio error:", e);
        // Log the error code for debugging
        const errorCodes = ["MEDIA_ERR_ABORTED", "MEDIA_ERR_NETWORK", "MEDIA_ERR_DECODE", "MEDIA_ERR_SRC_NOT_SUPPORTED"];
        if (audio.error) {
          console.error(`❌ Error code: ${errorCodes[audio.error.code - 1] || "Unknown"}`);
        }
        
        // Try alternative format as fallback
        if (contentType === "audio/mpeg") {
          console.log("🎵 Trying fallback format: audio/mp3");
          const fallbackBlob = new Blob([combined], { type: "audio/mp3" });
          audio.src = URL.createObjectURL(fallbackBlob);
          audio.load();
        }
      });
      
      // Store reference for access elsewhere
      audioPlayerRef.current = audio;
      
      // Set source and load
      audio.src = url;
      audio.volume = 0.8; // Higher volume for TTS
      audio.load();
    } catch (e) {
      console.error("❌ Critical error playing audio:", e);
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

    // Clear any existing timer
    if (processingTimerRef.current) {
      window.clearTimeout(processingTimerRef.current);
    }

    // Set a timeout to clear the processing state after 20 seconds
    processingTimerRef.current = window.setTimeout(() => {
      if (isProcessingAudio) {
        setIsProcessingAudio(false);
      }
    }, 20000);
  };

  // Set waiting state with timeout
  const startWaitingWithTimeout = () => {
    setIsWaitingForResponse(true);

    // Clear any existing waiting timer
    if (waitingTimerRef.current) {
      window.clearTimeout(waitingTimerRef.current);
    }

    // Set a timeout to clear the waiting state after 30 seconds
    waitingTimerRef.current = window.setTimeout(() => {
      if (isWaitingForResponse) {
        setIsWaitingForResponse(false);
      }
    }, 30000);
  };

  // Function to ensure active audio playback respects the current mute setting
  const applyMuteStateToAudio = () => {
    if (audioPlayerRef.current) {
      // Check if the current mute state matches what we expect
      if (audioPlayerRef.current.muted !== isMuted) {
        audioPlayerRef.current.muted = isMuted;
      }
    }
  };

  // Update audio player mute state when isMuted changes
  useEffect(() => {
    applyMuteStateToAudio();
  }, [isMuted]);

  // Add this useEffect near the other effects inside the Chat component
  useEffect(() => {
    // If there's any message not from the user, clear the waiting state.
    if (messages.some((msg) => msg.sender !== "user")) {
      setIsWaitingForResponse(false);
    }
  }, [messages]);

  // Add Effect to dismiss initial wait
  useEffect(() => {
    // Check if wait state is active and hasn't been dismissed before
    if (showInitialWait && !initialWaitDismissedRef.current) {
      // Check if there's at least one non-user message
      const hasAssistantMessage = messages.some(msg => msg.sender !== 'user');

      if (hasAssistantMessage) {
        setShowInitialWait(false);
        initialWaitDismissedRef.current = true; // Mark as dismissed
      }
    }
  }, [messages, showInitialWait]); // Depend on messages and the wait state

  // Determine container class based on sender
  const getContainerClass = (sender: string) => {
    if (sender === 'user') return 'user-container';
    if (sender === 'character' || sender === 'assistant') return 'character-container'; 
    return 'system-container';
  };

  // Determine message class based on sender
  const getMessageClass = (sender: string) => {
    if (sender === 'user') return 'user-message';
    if (sender === 'character' || sender === 'assistant') return 'character-message';
    return 'system-message';
  };

  // --- Music Initialization Logic (moved into a function) ---
  const initializeMusic = useCallback(() => {
    try {
      let musicElement = document.getElementById('background-music-element') as HTMLAudioElement | null;
      
      if (musicElement) {
        musicElement.volume = 0.03;
        if (musicElement.paused) {
          musicElement.play().then(() => setIsMusicPlaying(true)).catch(e => console.error("[Music Init] Error re-playing existing element:", e));
        } else {
           setIsMusicPlaying(true); // Already playing
        }
        return; // Already initialized
      }
      
      const audio = new Audio();
      audio.id = 'background-music-element';
      audio.loop = true;
      audio.volume = 0.03;
      audio.src = "/audio/music.ogg";
      
      audio.oncanplaythrough = () => {
        try {
          audio.volume = 0.03;
          const playPromise = audio.play();
          if (playPromise) {
            playPromise.then(() => {
              setIsMusicPlaying(true);
            }).catch((e) => {
              console.error("❌ [Music Init] Music autoplay error:", e);
              setIsMusicPlaying(false);
            });
          }
        } catch (err) {
          console.error("❌ [Music Init] Music setup error during play attempt:", err);
          setIsMusicPlaying(false);
        }
      };
      
      audio.onerror = (e) => {
        console.error("❌ [Music Init] Audio Element Error Event:", e, audio.error);
        setIsMusicPlaying(false);
      };

      console.log("▶️ [Music Init] Attempting to append element to document.body...");
      document.body.appendChild(audio);
      console.log("✅ [Music Init] Appended new audio element to body.");
      globalMusicPlayer.setAudioElement(audio);

    } catch (err) {
      console.error("❌ [Music Init] CRITICAL error in initializeMusic try block:", err);
      setIsMusicPlaying(false); // Ensure state reflects failure
    }
  }, []); // useCallback dependency array is empty as it doesn't depend on component state/props directly
  // --- End Music Initialization Logic ---

  // Expose the initializeMusic function via the ref
  useImperativeHandle(ref, () => ({
    initializeMusic,
  }));

  // Music toggle function using the global player - completely decoupled
  const toggleMusic = useCallback(() => {
    try {
      const audioEl = document.getElementById('background-music-element') as HTMLAudioElement;
      if (!audioEl) {
        console.error("[Music Toggle] Audio element not found in DOM!");
        setIsMusicPlaying(false); // Ensure state is false if element missing
        return;
      }
      
      audioEl.volume = 0.03;
      
      if (!audioEl.paused) {
        audioEl.pause();
        setIsMusicPlaying(false); // Update state
      } else {
        audioEl.volume = 0.03;
        audioEl.play().then(() => {
          setIsMusicPlaying(true); // Update state
          setTimeout(() => { if (audioEl) audioEl.volume = 0.03; }, 100);
        }).catch(err => {
          console.error("[Music Toggle] Play error:", err);
          setIsMusicPlaying(false); // Update state on error
        });
      }
    } catch (err) {
      console.error("[Music Toggle] Error in toggle function:", err);
      setIsMusicPlaying(false); // Ensure state reflects error
    }
  }, []); // Dependency array empty

  // Add this to the Chat component to force play audio - using enhanced emergency playback
  const forcePlayAudio = (chunks: Uint8Array[]) => {
    
    try {
      // Create combined buffer
      const totalLength = chunks.reduce((acc, chunk) => acc + chunk.length, 0);
      
      if (totalLength === 0) {
        console.error("⚠️ No audio data to play!");
        return;
      }
      
      const combined = new Uint8Array(totalLength);
      
      let offset = 0;
      for (const chunk of chunks) {
        combined.set(chunk, offset);
        offset += chunk.length;
      }
      
      // Try all possible formats
      const mimeTypes = ["audio/mpeg", "audio/mp3", "audio/ogg", "audio/webm", "audio/wav"];
      
      // Create direct audio element
      const blob = new Blob([combined], { type: "audio/mpeg" });
      const url = URL.createObjectURL(blob);
      
      // Create and force-play the audio
      const audio = new Audio();
      audio.src = url;
      audio.volume = 1.0;  // Maximum volume
      audio.muted = isMuted; // Respect the component's mute state
      
      audio.onerror = (e) => console.error("🔊 Force Play error:", e, audio.error);
      
      // Add to DOM to help with playback
      document.body.appendChild(audio);
      
      // Force play
      const playPromise = audio.play();
      if (playPromise) {
        playPromise.then(() => {
          
          // Store reference to control
          audioPlayerRef.current = audio;
          
          // Clean up after playing
          audio.onended = () => {
            URL.revokeObjectURL(url);
            if (document.body.contains(audio)) {
              document.body.removeChild(audio);
            }
          };
        }).catch(e => {
          console.error("🔊 Force Play failed:", e);
          
          // Try browser interaction trick
          const playButton = document.createElement('button');
          playButton.innerText = '▶️ Play Audio';
          playButton.style.position = 'fixed';
          playButton.style.bottom = '10px';
          playButton.style.left = '10px';
          playButton.style.zIndex = '9999';
          playButton.style.padding = '10px';
          playButton.style.backgroundColor = '#ff0000';
          playButton.style.color = 'white';
          playButton.style.border = 'none';
          playButton.style.borderRadius = '5px';
          playButton.style.cursor = 'pointer';
          
          playButton.onclick = () => {
            audio.play().catch(e => console.error("🔊 Manual play failed:", e));
            playButton.remove();
          };
          
          document.body.appendChild(playButton);
          
          // Auto-remove after 10 seconds
          setTimeout(() => {
            if (document.body.contains(playButton)) {
              playButton.remove();
            }
          }, 10000);
          
          URL.revokeObjectURL(url);
        });
      }
    } catch (e) {
      console.error("❌ Critical audio play error:", e);
    }
  };

  // Helper function to analyze audio data and log diagnostic information
  const analyzeAudioData = (chunks: Uint8Array[]) => {
    if (!chunks || chunks.length === 0) {
      return false;
    }
    
    // Log total size
    const totalLength = chunks.reduce((acc, chunk) => acc + chunk.length, 0);
    
    // Combine all chunks for analysis
    const combined = new Uint8Array(totalLength);
    let offset = 0;
    for (const chunk of chunks) {
      combined.set(chunk, offset);
      offset += chunk.length;
    }
    
    // Check for common audio file headers
    const checkMp3Header = () => {
      // MP3 files start with ID3 or with an MP3 frame header (first byte 0xFF)
      if (combined.length < 3) return false;
      
      const hasId3Header = combined[0] === 0x49 && combined[1] === 0x44 && combined[2] === 0x33; // "ID3"
      const hasMp3FrameHeader = combined[0] === 0xFF && (combined[1] & 0xE0) === 0xE0;
      
      if (hasId3Header) {
        return true;
      } else if (hasMp3FrameHeader) {
        return true;
      }
      
      return false;
    };
    
    // Check for specific formats
    const isMp3 = checkMp3Header();
    
    return isMp3;
  };

  // REVERT handleSubmit function to original logic
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() === "") return;
    sendTextMessage(message);
    setMessage("");
    // Start waiting for response after sending a text message
    startWaitingWithTimeout(); 
  };

  return (
    <div className="chat-container">
      <div className="chat-header" style={{ position: 'relative' }}>
        <h2>Chat</h2>
        <span 
          style={{
            cursor: 'pointer', 
            fontSize: '1.0rem',
            backgroundColor: 'rgba(0,0,0,0.5)', 
            color: 'white', 
            borderRadius: '50%', 
            width: '20px',
            height: '20px', 
            display: 'inline-flex',
            alignItems: 'center', 
            justifyContent: 'center',
            userSelect: 'none',
            marginLeft: '8px',
            verticalAlign: 'middle'
          }}
          onMouseEnter={() => setIsHelpVisible(true)}
          onMouseLeave={() => setIsHelpVisible(false)}
        >
          ?
        </span>
        {isHelpVisible && (
          <div style={{
            position: 'absolute',
            top: '25px',
            left: '40px',
            zIndex: 11,
            backgroundColor: 'rgba(0,0,0,0.8)', 
            color: 'white', 
            padding: '10px',
            borderRadius: '5px',
            fontSize: '0.9rem',
            width: '200px',
            boxShadow: '0 2px 5px rgba(0,0,0,0.3)'
          }}>
            <strong>How to Play:</strong>
            <ul style={{ margin: '5px 0 0 15px', padding: 0, listStyleType: 'disc' }}>
              <li>Type commands like:</li>
                <ul style={{ margin: '2px 0 0 15px', padding: 0, listStyleType: 'circle' }}>
                  <li>"walk left 3 steps"</li>
                  <li>"run all the way right"</li>
                  <li>"go south" or "move down"</li>
                  <li>"what can you see around?"</li>
                  <li>"examine the chest"</li>
                  <li>"pick up the key"</li>
                  <li>"use key with chest"</li>
                </ul>
              <li>Click the 🎤 icon to speak commands.</li>
              <li>Explore and interact!</li>
            </ul>
          </div>
        )}
        <div
          className={`connection-status ${
            isConnected ? "connected" : "disconnected"
          }`}
        >
          {isConnected ? "Connected" : "Disconnected"}
        </div>
      </div>

      <div className="messages-container">
        {showInitialWait && (
          <div className="message-container system-container">
            <div className="message system-message wait-message">
              Send a message to start the conversation!
            </div>
          </div>
        )}

        {messages
          .filter(msg => !msg.content.trim().startsWith('```'))
          // Add filter to remove Json_response messages
          .filter(msg => !msg.content.trim().startsWith('Json_response'))
          .map((msg, index) => {
          
          // Try to parse JSON in content string
          const jsonContent = tryParseJsonInString(msg.content);
          
          // If message contains JSON with answers array, render those instead
          if (jsonContent && jsonContent.answers && Array.isArray(jsonContent.answers)) {
            // Filter out any answers with empty descriptions before rendering
            const validAnswers = jsonContent.answers.filter(answer => 
              answer && answer.description && answer.description.trim().length > 0
            );
            
            return (
              <React.Fragment key={index}>
                {validAnswers.map((answer: any, answerIndex: number) => (
                  <div key={`${index}-${answerIndex}-${answer.description?.substring(0, 10)}`} className={`message-container ${getContainerClass(msg.sender)}`}>
                    <div className={`message ${getMessageClass(msg.sender)} ${answer.isError ? 'error' : ''}`} data-sender={msg.sender}>
                      {answer.description}
                    </div>
                    {/* Only show options on the last answer */}
                    {answerIndex === validAnswers.length - 1 && answer.options && answer.options.length > 0 && (
                      <div className="options-container">
                        {answer.options.map((option: string, optIndex: number) => (
                          <button
                            key={optIndex}
                            className="option-button"
                            onClick={() => {
                              sendTextMessage(option);
                            }}
                          >
                            {option}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </React.Fragment>
            );
          }
          
          // For assistant messages, split by NEWLINES and render each in its own balloon
          if (msg.sender !== 'user') {
            // Split the message content by newline characters
            const paragraphs = msg.content.split('\n').filter(paragraph => paragraph.trim().length > 0);
            
            return (
              <React.Fragment key={`${index}-${msg.sender}-multi-newline`}>
                {paragraphs.map((paragraph, paragraphIndex) => (
                  <React.Fragment key={`${index}-${msg.sender}-${paragraphIndex}-frag`}>
                    <div 
                      className={`message-container ${getContainerClass(msg.sender)}`}
                    >
                      <div className={`message ${getMessageClass(msg.sender)} ${msg.isError ? 'error' : ''}`} data-sender={msg.sender}>
                        {paragraph}
                      </div>
                      {/* Only show options on the LAST paragraph of the message */} 
                      {paragraphIndex === paragraphs.length - 1 && msg.options && msg.options.length > 0 && (
                        <div className="options-container">
                          {msg.options.map((option, optIndex) => (
                            <button
                              key={optIndex}
                              className="option-button"
                              onClick={() => sendTextMessage(option)}
                            >
                              {option}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                    {/* Add a horizontal rule between paragraphs, except for the last one */}
                    {paragraphIndex < paragraphs.length - 1 && <hr className="paragraph-separator" />}
                  </React.Fragment>
                ))}
              </React.Fragment>
            );
          }
          
          // Regular user message rendering (no splitting for user messages)
          return (
            <div key={`${index}-${msg.sender}-${msg.content.substring(0, 10)}`} className={`message-container ${getContainerClass(msg.sender)}`}>
              <div className={`message ${getMessageClass(msg.sender)} ${msg.isError ? 'error' : ''}`} data-sender={msg.sender}>
                {msg.content}
              </div>
              {msg.options && msg.options.length > 0 && (
                <div className="options-container">
                  {msg.options.map((option, optIndex) => (
                    <button
                      key={optIndex}
                      className="option-button"
                      onClick={() => {
                        sendTextMessage(option);
                      }}
                    >
                      {option}
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })}

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

        {isProcessingAudio &&
          !isThinking &&
          !isRecording &&
          !isInitialMount &&
          hasStartedProcessingRef.current &&
          !messages.some(
            (m) => m.sender === "user" && m.content.length > 0
          ) && (
            <div className="thinking-indicator processing-audio">
              <div className="dot"></div>
              <div className="dot"></div>
              <div className="dot"></div>
              <span>Processing Voice</span>
            </div>
          )}

        {isWaitingForResponse &&
          !isThinking &&
          !isRecording &&
          !isProcessingAudio && (
            <div className="thinking-indicator waiting-response">
              <div className="dot"></div>
              <div className="dot"></div>
              <div className="dot"></div>
              <span>Waiting for response...</span>
            </div>
          )}
        
        {serverError && (
          <div className="message-container system-container">
            <div className="message system-message error">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '1.2em' }}>⚠️</span>
                <span>Server Error: {
                  serverError.includes('error_msg') 
                    ? 'The server encountered an error. Please try again.' 
                    : serverError
                }</span>
              </div>
            </div>
          </div>
        )}

        {/* Empty spacer div to ensure padding at bottom */}
        <div className="messages-end-spacer"></div>

        {/* Ref for scroll target */}
        <div ref={messagesEndRef} />
      </div>

      <div className={`input-area ${!showInitialWait ? 'visible' : ''}`}>
        <form onSubmit={handleSubmit}>
          <button
            type="button"
            className={`mute-button ${isMuted ? "muted" : "unmuted"}`}
            onClick={() => {
              const newMutedState = !isMuted;

              // Update React state
              setIsMuted(newMutedState);
              if (audioPlayerRef.current) {
                // Force mute state change
                audioPlayerRef.current.muted = newMutedState;

                // Force browser to recognize the mute state change by manipulating volume slightly
                const currentVolume = audioPlayerRef.current.volume;
                // Ensure volume is mutable (not 0 or 1)
                if (currentVolume > 0 && currentVolume < 1) {
                    audioPlayerRef.current.volume =
                      currentVolume > 0.5
                        ? currentVolume - 0.01
                        : currentVolume + 0.01;
                    audioPlayerRef.current.volume = currentVolume; // Restore original volume immediately
                } else if (currentVolume === 0) {
                    audioPlayerRef.current.volume = 0.01;
                    audioPlayerRef.current.volume = 0;
                } else { // volume === 1
                    audioPlayerRef.current.volume = 0.99;
                    audioPlayerRef.current.volume = 1;
                }
                
                // Force a check of the player state after a short delay
                setTimeout(() => {
                  if (audioPlayerRef.current) { // Check again inside timeout
                    if (audioPlayerRef.current.muted !== newMutedState) {
                      // Force it again if the state didn't stick
                      audioPlayerRef.current.muted = newMutedState;
                      // Try toggling pause/play to refresh audio state if it was playing
                      if (!audioPlayerRef.current.paused) {
                          const currentTime = audioPlayerRef.current.currentTime;
                          audioPlayerRef.current.pause();
                          // Use another timeout to resume play after pause
                          setTimeout(() => {
                              if (audioPlayerRef.current) {
                                  audioPlayerRef.current.currentTime = currentTime;
                                  audioPlayerRef.current.play()
                                      .catch((e) => console.error("Error resuming after mute toggle:", e)); // Keep essential error
                              }
                          }, 50); // Delay before resuming play
                      } // End if !paused
                    } // End if muted state mismatch
                  } // End if audioPlayerRef check inside timeout
                }, 50); // Delay for state check
              } // End if audioPlayerRef check
            }}
            disabled={!isConnected}
            style={{
              position: 'relative',
              ...(isMuted ? {
                border: '2px solid #ff0000',
                overflow: 'visible'
              } : {})
            }}
          >
            <span>🔊</span>
            {isMuted && (
              <div style={{
                position: 'absolute',
                top: '0',
                left: '0',
                width: '100%',
                height: '100%',
                pointerEvents: 'none',
                overflow: 'hidden',
                borderRadius: '50%' // Match the button's circular shape
              }}>
                <div style={{
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  width: '100%', // Exactly match the button's width
                  height: '2px',
                  backgroundColor: '#ff0000',
                  transform: 'translateX(-50%) rotate(-45deg)',
                  transformOrigin: 'center', // Rotate around center
                }}></div>
              </div>
            )}
          </button>
          
          
          {/* Music toggle button - updated styling */}
          <button
            type="button"
            className={`mute-button ${isMusicPlaying ? "unmuted" : "muted"}`}
            onClick={toggleMusic}
            title={isMusicPlaying ? "Turn off music" : "Turn on music"}
            disabled={!isConnected}
            style={{
              position: 'relative',
              backgroundColor: isMusicPlaying ? '#4CAF50' : '',
              color: isMusicPlaying ? 'white' : '',
              ...(!isMusicPlaying ? {
                border: '2px solid #ff0000',
                overflow: 'visible'
              } : {})
            }}
          >
            <span>🎵</span>
            {!isMusicPlaying && (
              <div style={{
                position: 'absolute',
                top: '0',
                left: '0',
                width: '100%',
                height: '100%',
                pointerEvents: 'none',
                overflow: 'hidden',
                borderRadius: '50%' // Match the button's circular shape
              }}>
                <div style={{
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  width: '100%', // Exactly match the button's width
                  height: '2px',
                  backgroundColor: '#ff0000',
                  transform: 'translateX(-50%) rotate(-45deg)',
                  transformOrigin: 'center', // Rotate around center
                }}></div>
              </div>
            )}
          </button>
          
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder={serverError ? "Please wait a moment before trying again..." : "Type your message..."}
            disabled={!isConnected || !!serverError}
          />
          <button 
            type="submit" 
            className="send-button" 
            disabled={!isConnected || !!serverError}
          >
            Send
          </button>
          <button
            type="button"
            className={`voice-button ${isRecording ? "recording" : ""}`}
            onClick={handleVoiceClick}
            disabled={!isConnected}
          >
            <span className="voice-icon">🎤</span>
          </button>
        </form>
      </div>
    </div>
  );
});

export default Chat;
