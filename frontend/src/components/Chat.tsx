import React, { useEffect, useRef, useState, useCallback } from "react";
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

// Add near the top, after imports
// Enable or disable verbose logging
const VERBOSE_LOGGING = false;

// Helper function for conditional logging
const log = (message: string, ...args: any[]) => {
  if (VERBOSE_LOGGING) {
    console.log(message, ...args);
  }
};

interface ChatProps {
  messages: Array<{ content: string; sender: string; isError?: boolean; options?: string[]; messageId?: string}>;
  sendTextMessage: (message: string) => void;
  isThinking: boolean;
  isConnected: boolean;
  websocket: WebSocket | null; // Add WebSocket prop for direct access
  isMapReady?: boolean; // Optional prop to know when map is ready
}

const Chat = ({
  messages,
  sendTextMessage,
  isThinking,
  isConnected,
  websocket,
  isMapReady = false,
}: ChatProps) => {
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

  // Reset all UI state indicators on component mount
  useEffect(() => {
    log("Resetting all UI state indicators on component mount");
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
      // Check if the string might be JSON (starts with '{' or '[')
      if ((text.trim().startsWith('{') || text.trim().startsWith('[')) && 
          (text.trim().endsWith('}') || text.trim().endsWith(']'))) {
        return JSON.parse(text);
      }
    } catch (e) {
      // If parsing fails, it's not valid JSON
      log("Not valid JSON in message:", e);
    }
    return null;
  };

  // Update the WebSocket message handler
  useEffect(() => {
    if (!websocket) return;
    websocket.binaryType = "arraybuffer";

    let audioChunks: Uint8Array[] = [];
    let isReceivingAudio = false;
    let audioStartReceived = false;

    log("Setting up WebSocket listeners for audio");

    // Reset UI states when WebSocket changes
    setIsProcessingAudio(false);
    setIsWaitingForResponse(false);

    const handleMessage = (event: MessageEvent) => {
      try {
        // Handle text messages (JSON)
        if (typeof event.data === "string") {
          try {
            const data = JSON.parse(event.data);
            log("WebSocket received JSON message:", data.type);

            switch (data.type) {
              case "audio_start":
                log("WebSocket: Received audio_start signal");
                isReceivingAudio = true;
                audioStartReceived = true;
                hasPlayedAudioRef.current = false;
                audioChunks = [];
                break;

              case "audio_end":
                handleAudioEnd();
                break;

              case "error":
                log("Received error from server:", data.content);
                setIsProcessingAudio(false);
                setIsWaitingForResponse(false);
                break;

              // Let App.tsx handle other message types
              default:
                break;
            }
          } catch (jsonError) {
            log("Error parsing JSON from WebSocket:", jsonError);
          }
        }
        // Handle binary data (audio chunks)
        else if (event.data instanceof ArrayBuffer) {
          handleBinaryData(event.data);
        }
      } catch (err) {
        log("Error in WebSocket message handler:", err);
      }
    };

    // Helper function to handle audio end
    const handleAudioEnd = () => {
      log(
        `WebSocket: Received audio_end signal, chunks: ${audioChunks.length}, audioStartReceived: ${audioStartReceived}`
      );

      if (audioStartReceived && audioChunks.length > 0 && !hasPlayedAudioRef.current) {
        log(
          `Playing audio: ${audioChunks.length} chunks totaling ${audioChunks.reduce(
            (acc, chunk) => acc + chunk.length,
            0
          )} bytes`
        );
        playBufferedAudio(audioChunks);
        hasPlayedAudioRef.current = true;
      } else {
        if (!audioStartReceived) {
          log("Received audio_end but no audio_start was received");
        }
        if (audioChunks.length === 0) {
          log("No audio chunks to play after audio_end");
        }
      }

      // Reset state
      isReceivingAudio = false;
      audioStartReceived = false;
      audioChunks = [];
    };

    // Helper function to handle binary data
    const handleBinaryData = (data: ArrayBuffer) => {
      log(
        `WebSocket: Received binary data, size: ${data.byteLength} bytes, isReceiving: ${isReceivingAudio}, audioStartReceived: ${audioStartReceived}`
      );

      if (isReceivingAudio && audioStartReceived) {
        try {
          const arrayBuf = new Uint8Array(data);
          const isEndMarker = arrayBuf.length === 12;

          if (isEndMarker) {
            let endMarkerString = "";
            for (let i = 0; i < arrayBuf.length; i++) {
              endMarkerString += String.fromCharCode(arrayBuf[i]);
            }
            if (endMarkerString === "__AUDIO_END__") {
              handleAudioEnd();
            } else {
              audioChunks.push(arrayBuf);
            }
          } else {
            if (audioChunks.length === 0) {
              logFirstChunk(arrayBuf);
            }
            audioChunks.push(arrayBuf);
            logChunkProgress();
          }
        } catch (binaryError) {
          log("Error processing binary data:", binaryError);
        }
      } else {
        logAudioStateWarnings();
      }
    };

    // Helper function to log first chunk details
    const logFirstChunk = (arrayBuf: Uint8Array) => {
      log(
        `Added FIRST audio chunk: ${arrayBuf.length} bytes, first 30 bytes:`,
        Array.from(arrayBuf.slice(0, 30))
          .map((b) => b.toString(16).padStart(2, "0"))
          .join(" ")
      );
      const potentialHeader = Array.from(arrayBuf.slice(0, 3))
        .map((b) => b.toString(16).padStart(2, "0"))
        .join(" ");
      log(`MP3 header check: ${potentialHeader}`);
      if (arrayBuf.length < 100) {
        log(`Suspiciously small first audio chunk: ${arrayBuf.length} bytes`);
      }
    };

    // Helper function to log chunk progress
    const logChunkProgress = () => {
      if (audioChunks.length % 5 === 0) {
        const totalSize = audioChunks.reduce((acc, chunk) => acc + chunk.length, 0);
        log(
          `Accumulated ${audioChunks.length} chunks, total size: ${totalSize} bytes`
        );
      }
    };

    // Helper function to log audio state warnings
    const logAudioStateWarnings = () => {
      if (!isReceivingAudio) {
        log("Received binary data but isReceivingAudio is false");
      }
      if (!audioStartReceived) {
        log("Received binary data but no audio_start was received");
      }
    };

    websocket.addEventListener("message", handleMessage);

    return () => {
      log("Cleaning up WebSocket audio listeners");
      websocket.removeEventListener("message", handleMessage);
    };
  }, [websocket]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (message.trim() === "") return;

    sendTextMessage(message);
    setMessage("");

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
        log("Clearing previous states before starting new recording");
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
          log(`Recording data available: ${event.data.size} bytes`);
          localChunks.push(event.data);
        }
      });

      mediaRecorder.addEventListener("stop", () => {
        log("MediaRecorder stopped, sending accumulated data");

        // Combine all chunks into a single blob
        const completeBlob = new Blob(localChunks, { type: "audio/webm" });
        log(`Complete recording size: ${completeBlob.size} bytes`);

        if (websocket && websocket.readyState === WebSocket.OPEN) {
          // Convert Blob to ArrayBuffer and send to server
          const reader = new FileReader();
          reader.onload = () => {
            if (
              reader.result instanceof ArrayBuffer &&
              websocket.readyState === WebSocket.OPEN
            ) {
              const buffer = reader.result;
              log(
                `Sending complete audio data to server: ${buffer.byteLength} bytes`
              );

              // Verify buffer has content
              if (buffer.byteLength > 0) {
                // Log first 10 bytes for debugging
                const view = new Uint8Array(buffer);
                log(
                  `First 10 bytes of audio data: [${Array.from(
                    view.slice(0, 10)
                  ).join(", ")}]`
                );

                // Send the binary data first
                websocket.send(buffer);

                // Then signal the end of audio after a small delay to ensure the binary data is processed
                setTimeout(() => {
                  if (websocket.readyState === WebSocket.OPEN) {
                    log("Sending audio_end signal");
                    websocket.send(
                      JSON.stringify({
                        type: "audio_end",
                      })
                    );

                    // Only show processing immediately after recording, before transcription
                    startProcessingWithTimeout();
                  }
                }, 200);
              } else {
                log("Empty audio buffer, not sending");
                // Notify user of empty recording
                alert(
                  "No audio was recorded. Please try again and speak into your microphone."
                );
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
      log("Error accessing microphone:", err);
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
      log(
        "Stopping MediaRecorder - chunks will be processed in the stop event handler"
      );
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
        log("Stopping audio playback before recording");
        audioPlayerRef.current.pause();
        audioPlayerRef.current.currentTime = 0;
        setIsPlaying(false);
      }
      startRecording();
    }
  };

  // Helper function to detect audio format from header bytes
  const detectAudioFormat = (firstChunk: Uint8Array): string => {
    if (!firstChunk || firstChunk.length < 4) {
      log(
        "Not enough data to detect audio format, defaulting to audio/mpeg"
      );
      return "audio/mpeg";
    }

    // Check for MP3 header (usually starts with ID3 or first byte is 0xFF)
    if (
      (firstChunk[0] === 0x49 &&
        firstChunk[1] === 0x44 &&
        firstChunk[2] === 0x33) || // ID3
      (firstChunk[0] === 0xff && (firstChunk[1] & 0xe0) === 0xe0) // MPEG sync word
    ) {
      log("Detected MP3 format");
      return "audio/mpeg";
    }

    // Check for WAV header
    if (
      firstChunk[0] === 0x52 &&
      firstChunk[1] === 0x49 &&
      firstChunk[2] === 0x46 &&
      firstChunk[3] === 0x46
    ) {
      log("Detected WAV format");
      return "audio/wav";
    }

    // Check for Ogg/Opus/Vorbis header
    if (
      firstChunk[0] === 0x4f &&
      firstChunk[1] === 0x67 &&
      firstChunk[2] === 0x67 &&
      firstChunk[3] === 0x53
    ) {
      log("Detected Ogg format");
      return "audio/ogg";
    }

    // Default to MP3 if format is unknown
    log("Unknown audio format, defaulting to audio/mpeg");
    return "audio/mpeg";
  };

  // New playBufferedAudio function:
  const playBufferedAudio = (chunks: Uint8Array[]) => {
    if (DEBUG) log("Playing buffered audio, chunks:", chunks.length);

    if (chunks.length === 0) {
      log("No audio chunks to play");
      return;
    }

    try {
      let mimeType = "audio/mpeg";
      if (chunks.length > 0 && chunks[0].length > 0) {
        mimeType = detectAudioFormat(chunks[0]);
      }

      const blob = new Blob(chunks, { type: mimeType });
      if (DEBUG)
        log(
          `Created audio blob with type ${mimeType}, size: ${blob.size}`
        );

      const url = URL.createObjectURL(blob);
      if (DEBUG) log("Created URL for audio blob:", url);

      // Use only the main audio player for playback
      tryPlayWithMainAudio(url);
    } catch (error) {
      log("Error in playBufferedAudio:", error);
    }
  };

  // Helper function to try playing with the main audio player
  const tryPlayWithMainAudio = (url: string) => {
    try {
      log(
        `Trying with main audio player (current mute state: ${isMuted})`
      );
      if (!audioPlayerRef.current) {
        log("Audio player not initialized yet");
        const audio = new Audio();
        audio.autoplay = false;
        audio.preload = "auto";

        // Important: Apply the mute setting immediately to the new audio element
        audio.muted = isMuted;
        log(`Created new Audio element with muted=${isMuted}`);

        audioPlayerRef.current = audio;
      }

      // Reset the audio element
      try {
        audioPlayerRef.current.pause();
        audioPlayerRef.current.currentTime = 0;
      } catch (e) {
        log("Error resetting audio element:", e);
      }

      // Set up audio for playback
      audioPlayerRef.current.src = url;
      audioPlayerRef.current.preload = "auto";

      // Forcefully apply the mute state before trying to play
      audioPlayerRef.current.muted = isMuted;
      audioPlayerRef.current.volume = 0.5;

      log(
        `Audio player setup complete: src=${url}, muted=${audioPlayerRef.current.muted}, volume=${audioPlayerRef.current.volume}`
      );

      // Let the browser know we want to play audio
      audioPlayerRef.current.load();

      log(
        `Attempting to play with main audio player... (muted: ${isMuted}, audioPlayer.muted: ${audioPlayerRef.current.muted})`
      );

      // Add a retry mechanism
      let retryCount = 0;
      const maxRetries = 3;

      const attemptPlay = () => {
        // Double-check mute state right before playing
        if (
          audioPlayerRef.current &&
          audioPlayerRef.current.muted !== isMuted
        ) {
          log(
            `Fixing mute state discrepancy right before playing: ${isMuted} vs ${audioPlayerRef.current.muted}`
          );
          audioPlayerRef.current.muted = isMuted;
        }

        audioPlayerRef
          .current!.play()
          .then(() => {
            log("Main audio player playback started successfully");

            // One last check after play starts
            setTimeout(() => {
              if (
                audioPlayerRef.current &&
                audioPlayerRef.current.muted !== isMuted
              ) {
                log(
                  `Post-playback mute correction: setting to ${isMuted}`
                );
                audioPlayerRef.current.muted = isMuted;
              }
            }, 100);
          })
          .catch((err) => {
            log(
              `Error playing with main audio player (attempt ${
                retryCount + 1
              }/${maxRetries}):`,
              err
            );

            if (retryCount < maxRetries) {
              retryCount++;
              log(`Retrying playback in ${retryCount * 500}ms...`);

              // Try again with a delay
              setTimeout(attemptPlay, retryCount * 500);
            } else {
              log("Failed to play audio after multiple attempts");

              // Show alert to user only on the final failure
              if (err.name === "NotAllowedError") {
                alert(
                  "Audio playback was blocked. Please enable autoplay in your browser settings for this site."
                );
              } else if (
                err.name === "AbortError" ||
                err.name === "NotSupportedError"
              ) {
                alert(
                  "The audio format is not supported by your browser. You may not hear responses."
                );
              }
            }
          });
      };

      attemptPlay();
    } catch (error) {
      log("Error in tryPlayWithMainAudio:", error);
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
    log("Audio processing started");

    // Clear any existing timer
    if (processingTimerRef.current) {
      window.clearTimeout(processingTimerRef.current);
    }

    // Set a timeout to clear the processing state after 20 seconds
    processingTimerRef.current = window.setTimeout(() => {
      if (isProcessingAudio) {
        log("Audio processing timed out after 20 seconds");
        setIsProcessingAudio(false);
      }
    }, 20000);
  };

  // Set waiting state with timeout
  const startWaitingWithTimeout = () => {
    setIsWaitingForResponse(true);
    log("Waiting for agent response");

    // Clear any existing waiting timer
    if (waitingTimerRef.current) {
      window.clearTimeout(waitingTimerRef.current);
    }

    // Set a timeout to clear the waiting state after 30 seconds
    waitingTimerRef.current = window.setTimeout(() => {
      if (isWaitingForResponse) {
        log("Waiting for response timed out after 30 seconds");
        setIsWaitingForResponse(false);
      }
    }, 30000);
  };

  // Add a useEffect to log state changes
  useEffect(() => {
    log(
      `State change - isRecording: ${isRecording}, isProcessingAudio: ${isProcessingAudio}, isWaitingForResponse: ${isWaitingForResponse}, isThinking: ${isThinking}, isPlaying: ${isPlaying}`
    );
  }, [
    isRecording,
    isProcessingAudio,
    isWaitingForResponse,
    isThinking,
    isPlaying,
  ]);

  // Force reset all states on initial render with a delay - this should fix any "stuck" states
  useEffect(() => {
    const forceResetTimer = setTimeout(() => {
      log(
        "FORCE RESET: Resetting all UI state indicators after timeout"
      );
      setIsRecording(false);
      setIsProcessingAudio(false);
      setIsWaitingForResponse(false);
      setIsPlaying(false);
      hasStartedProcessingRef.current = false;
    }, 300);

    return () => clearTimeout(forceResetTimer);
  }, []);

  // Function to ensure active audio playback respects the current mute setting
  const applyMuteStateToAudio = () => {
    if (audioPlayerRef.current) {
      // Check if the current mute state matches what we expect
      if (audioPlayerRef.current.muted !== isMuted) {
        log(
          `Audio player mute state (${audioPlayerRef.current.muted}) doesn't match expected state (${isMuted}), correcting...`
        );
        audioPlayerRef.current.muted = isMuted;
      } else {
        log(
          `Audio player mute state already matches expected state (${isMuted})`
        );
      }
    }
  };

  // Update audio player mute state when isMuted changes
  useEffect(() => {
    log(
      `isMuted state changed to: ${isMuted} - updating audio player state`
    );
    applyMuteStateToAudio();
  }, [isMuted]);

  // Add this useEffect near the other effects inside the Chat component
  useEffect(() => {
    // If there's any message not from the user, clear the waiting state.
    if (messages.some((msg) => msg.sender !== "user")) {
      log("Received response. Clearing waiting state.");
      setIsWaitingForResponse(false);
    }
  }, [messages]);

  // Determine container class based on sender
  const getContainerClass = (sender: string) => {
    if (sender === 'user') return 'user-container';
    if (sender === 'character') return 'character-container'; 
    return 'system-container';
  };

  // Determine message class based on sender
  const getMessageClass = (sender: string) => {
    if (sender === 'user') return 'user-message';
    if (sender === 'character') return 'character-message';
    return 'system-message';
  };

  // Initialize the music player when map is ready (once)
  useEffect(() => {
    if (isMapReady) {
      // Create audio element once - not tied to React state
      try {
        // Check if we should initialize
        const musicElement = document.getElementById('background-music-element') as HTMLAudioElement;
        if (musicElement) {
          // Element already exists, just update volume
          musicElement.volume = 0.03; // Lowered volume
          log("Found existing music element, set volume to 0.03");
          return;
        }
        
        // Limit console logging
        log("🎵 Initializing background music (once-only)");
        
        // Create a stable element outside React
        const audio = new Audio();
        audio.id = 'background-music-element';
        audio.loop = true;
        audio.volume = 0.03;
        audio.src = "/audio/music.ogg";
        
        // Force volume setting
        console.log("🎵 Setting music volume to 0.03 (3%)"); // Updated log message
        
        // Set a play handler that won't trigger re-renders
        audio.oncanplaythrough = () => {
          // Try to play without updating state
          try {
            // Force volume setting again just before playing
            audio.volume = 0.03; // Lowered volume
            const playPromise = audio.play();
            if (playPromise) {
              playPromise.catch((e) => {
                log("Music autoplay error:", e);
                // Don't update state here
              });
            }
          } catch (err) {
            log("Music setup error:", err);
          }
        };
        
        // Store in document to keep it outside React lifecycle
        document.body.appendChild(audio);
        
        // Store reference in global player using the proper accessor
        globalMusicPlayer.setAudioElement(audio);
      } catch (err) {
        log("Fatal music init error:", err);
      }
    }
  }, [isMapReady]); 

  // Music toggle function using the global player - completely decoupled
  const toggleMusic = useCallback(() => {
    try {
      // Get actual audio element from document
      const audioEl = document.getElementById('background-music-element') as HTMLAudioElement;
      if (!audioEl) return;
      
      // Ensure volume is correct every time we interact with the element
      audioEl.volume = 0.03; // Lowered volume
      
      if (!audioEl.paused) {
        audioEl.pause();
        setIsMusicPlaying(false);
      } else {
        // Force volume before playing
        audioEl.volume = 0.03; // Lowered volume
        audioEl.play().then(() => {
          setIsMusicPlaying(true);
          // Double-check volume after successful play
          setTimeout(() => {
            if (audioEl) audioEl.volume = 0.03; // Lowered volume
          }, 100);
        }).catch(err => {
          log("Music toggle error:", err);
        });
      }
    } catch (err) {
      log("Music toggle error:", err);
    }
  }, []);

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h2>Chat</h2>
        <div
          className={`connection-status ${
            isConnected ? "connected" : "disconnected"
          }`}
        >
          {isConnected ? "Connected" : "Disconnected"}
        </div>
      </div>

      <div className="messages-container">
        {messages
          .filter(msg => !msg.content.trim().startsWith('```'))
          // Add filter to remove Json_response messages
          .filter(msg => !msg.content.trim().startsWith('Json_response'))
          // Create a more robust deduplication algorithm
          .filter((msg, index, self) => {
            // First level: Use messageId for deduplication if available
            if (msg.messageId) {
              return self.findIndex(m => m.messageId === msg.messageId) === index;
            }
            
            // Second level: For theme selections, handle case and format variations
            const normalizedMsgContent = msg.content.toLowerCase().replace(/_/g, ' ');
            const isThemeSelectionMsg = 
              msg.sender === 'user' && 
              (normalizedMsgContent.includes('abandoned prisioner') || 
               normalizedMsgContent.includes('crash in the sea') ||
               normalizedMsgContent.includes('lost memory'));
            
            if (isThemeSelectionMsg) {
              // Find all theme selection messages and check if this is the first
              // Check against other normalized theme messages
              return false;
            }
            
            // Third level: For messages without messageId, use content+sender combination
            return self.findIndex(m => 
              m.content === msg.content && m.sender === msg.sender
            ) === index;
          })
          .map((msg, index) => {
          // Enhanced logging to debug message rendering
          log(`Rendering message ${index}:`, { 
            sender: msg.sender, 
            content: msg.content.substring(0, 30),
            containerClass: getContainerClass(msg.sender),
            messageClass: getMessageClass(msg.sender)
          });
          
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
                              // Only send the message, don't update the input field
                              // setMessage(option);
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
          
          // Regular message rendering with explicit classes
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
                        // Only send the message, don't update the input field
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

        {/* Only show processing before we get transcription */}
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

        {/* Show waiting response indicator when appropriate */}
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

        {/* Empty spacer div to ensure padding at bottom */}
        <div className="messages-end-spacer"></div>

        {/* Ref for scroll target */}
        <div ref={messagesEndRef} />
      </div>

      <div className="input-area">
        <form onSubmit={handleSubmit}>
          <button
            type="button"
            className={`mute-button ${isMuted ? "muted" : "unmuted"}`}
            onClick={() => {
              const newMutedState = !isMuted;
              log(
                `Mute button clicked: changing from ${
                  isMuted ? "muted" : "unmuted"
                } to ${newMutedState ? "muted" : "unmuted"}`
              );

              // Update React state
              setIsMuted(newMutedState);

              // Immediately apply mute setting to currently playing audio
              if (audioPlayerRef.current) {
                // Force mute state change
                audioPlayerRef.current.muted = newMutedState;
                log(
                  `Applied mute setting to audio player: ${newMutedState} (actual: ${audioPlayerRef.current.muted})`
                );

                // Force browser to recognize the mute state change by manipulating volume slightly
                const currentVolume = audioPlayerRef.current.volume;
                audioPlayerRef.current.volume =
                  currentVolume > 0.5
                    ? currentVolume - 0.01
                    : currentVolume + 0.01;
                audioPlayerRef.current.volume = currentVolume;

                // Force a check of the player state
                setTimeout(() => {
                  if (audioPlayerRef.current) {
                    if (audioPlayerRef.current.muted !== newMutedState) {
                      log(
                        `Mute state mismatch after click: expected ${newMutedState}, got ${audioPlayerRef.current.muted}`
                      );
                      // Force it again with a different approach
                      audioPlayerRef.current.muted = newMutedState;
                      // Try toggling pause/play to refresh audio state if currently playing
                      if (!audioPlayerRef.current.paused) {
                        const currentTime = audioPlayerRef.current.currentTime;
                        audioPlayerRef.current.pause();
                        setTimeout(() => {
                          if (audioPlayerRef.current) {
                            audioPlayerRef.current.currentTime = currentTime;
                            audioPlayerRef
                              .current
                              .play()
                              .catch((e) =>
                                log(
                                  "Error resuming after mute toggle:",
                                  e
                                )
                              );
                          }
                        }, 50);
                      }
                    } else {
                      log(
                        `Mute state confirmed after click: ${audioPlayerRef.current.muted}`
                      );
                    }
                  }
                }, 50);
              } else {
                log("No audio player available to mute/unmute");
              }
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
          {isMapReady && (
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
          )}
          
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Type your message..."
            disabled={!isConnected}
          />
          <button type="submit" className="send-button" disabled={!isConnected}>
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
};

export default Chat;
