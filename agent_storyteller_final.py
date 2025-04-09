async def generate_and_stream_tts(websocket: WebSocket, text: str):
    """Generates TTS audio using ElevenLabs and streams it chunk by chunk."""
    global elevenlabs_client, ELEVENLABS_VOICE_ID
    print("🎙️ [TTS] Attempting to generate TTS for text:", text[:50] + ("..." if len(text) > 50 else ""))
    if not elevenlabs_client or not ELEVENLABS_VOICE_ID:
        print("❌ [TTS] ElevenLabs client or Voice ID not configured. Skipping TTS.")
        return

    try:
        # Send audio_start message
        print("▶️ [TTS] Sending audio_start message...")
        await websocket.send_json({"type": "audio_start"})
        print("✅ [TTS] audio_start message sent.")

        # Stream audio from ElevenLabs
        print("⏳ [TTS] Calling ElevenLabs API...")
        audio_stream = await elevenlabs_client.generate(
            text=text,
            voice=Voice(voice_id=ELEVENLABS_VOICE_ID),
            model="eleven_multilingual_v2", # Or your preferred model
            stream=True
        )
        print("✅ [TTS] ElevenLabs API call successful, streaming started.")

        chunks_sent = 0
        async for chunk in audio_stream:
            if chunk:
                # print(f"➡️ [TTS] Sending audio chunk {chunks_sent + 1} (size: {len(chunk)} bytes)") # Verbose
                await websocket.send_bytes(chunk)
                chunks_sent += 1
            else:
                print("⚠️ [TTS] Received empty chunk from ElevenLabs.")
        print(f"✅ [TTS] Finished streaming {chunks_sent} audio chunks.")

        # Send audio_end message
        print("▶️ [TTS] Sending audio_end message...")
        await websocket.send_json({"type": "audio_end"})
        print("✅ [TTS] audio_end message sent.")

    except Exception as e:
        print(f"❌ [TTS] CRITICAL ERROR during generation or streaming: {e}")
        # Optionally send an error message back to the client
        try:
            await websocket.send_json({"type": "error", "content": f"TTS Error: {e}"})
        except Exception as e:
            print(f"Error sending error message: {e}") 