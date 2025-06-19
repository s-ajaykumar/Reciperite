from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)
from dotenv import load_dotenv
load_dotenv()
import asyncio
import pyaudio
import os
import json

DEEPGRAM_CONFIG: DeepgramClientOptions = DeepgramClientOptions(options={"keepalive": "true"})
deepgram_client: DeepgramClient = DeepgramClient(os.getenv("DEEPGRAM_API_KEY"), DEEPGRAM_CONFIG)

class DeepgramSTT:
    def __init__(self):
        self.client_id = None
        self.is_finals = []
        self.text_in_queue = None
        self.stt_connection = None
        self.audio_stream = None
        self.audio = None
        
    async def receive_stt_text(self, deepgram_self, result, **kwargs):
        try:
            # Handle case where result might be a string
            if isinstance(result, str):
                result = json.loads(result)
            
            # Check if this is a speech started event
            if result.get("type") == "SpeechStarted":
                print(f"Client {self.client_id} New Speech Started\n")
                return
                
            # Get the transcript
            if "channel" in result and "alternatives" in result["channel"]:
                sentence = result["channel"]["alternatives"][0]["transcript"]
            else:
                return
            
            if len(sentence) == 0:
                return
            
            print(f"Interim: {sentence}")
            
            # Check if this is a final result
            is_final = result.get("is_final", False)
            speech_final = result.get("speech_final", False)
            
            if is_final:
                self.is_finals.append(sentence)
                
                if speech_final:
                    utterance = " ".join(self.is_finals)
                    await self.text_in_queue.put(utterance)
                    print(f"Client {self.client_id}\nFinal STT: {utterance}\n")
                    self.is_finals = []
                    
        except Exception as e:
            print(f"Error processing STT result: {e}")
            print(f"Result type: {type(result)}")
            print(f"Result content: {result}")
                
    def setup_audio(self):
        """Setup PyAudio for microphone input"""
        self.audio = pyaudio.PyAudio()
        
        # Audio configuration
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk = 1024
        
        # Open audio stream
        self.audio_stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )
        
        print("Microphone setup complete")
                
    async def start_connections(self):          
        try:
            self.stt_connection = deepgram_client.listen.asyncwebsocket.v("1")
            
            # Set up event handlers
            self.stt_connection.on(LiveTranscriptionEvents.Transcript, self.receive_stt_text)
            
            stt_options = LiveOptions(
                model="nova-2", 
                language="en-US", 
                smart_format=True, 
                encoding="linear16", 
                channels=1, 
                sample_rate=16000, 
                vad_events=True, 
                interim_results=True, 
                utterance_end_ms=1000, 
                endpointing=300
            )
            
            await self.stt_connection.start(stt_options)
            print("STT connection started successfully")
            return True
            
        except Exception as e:
            print(f"Failed to start STT connection: {e}")
            return False
            
    async def send_audio(self):
        """Continuously capture audio from microphone and send to Deepgram"""
        try:
            while True:
                # Read audio data from microphone
                audio_data = self.audio_stream.read(self.chunk, exception_on_overflow=False)
                
                # Send audio data to Deepgram
                if self.stt_connection:
                    await self.stt_connection.send(audio_data)
                    
                # Small delay to prevent overwhelming the connection
                await asyncio.sleep(0.01)
                
        except Exception as e:
            print(f"Error in audio capture: {e}")
        finally:
            self.cleanup_audio()
            
    def cleanup_audio(self):
        """Clean up audio resources"""
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
        if self.audio:
            self.audio.terminate()
        print("Audio resources cleaned up")
                
    async def main(self):
        self.client_id = "test_client"
        self.is_finals = []
        self.text_in_queue = asyncio.Queue()

        try:
            # Setup audio capture
            self.setup_audio()
            
            # Start the STT connection
            if await self.start_connections():
                print("Starting audio capture... Press Ctrl+C to stop")
                
                # Start sending audio data
                await self.send_audio()
            else:
                print("Failed to establish connection")
                
        except KeyboardInterrupt:
            print("\nStopping audio capture...")
        except Exception as e:
            print(f"Error in main: {e}")
        finally:
            # Cleanup
            if self.stt_connection:
                await self.stt_connection.finish()
            self.cleanup_audio()
         
obj = DeepgramSTT()        
         
if __name__ == "__main__":
    asyncio.run(obj.main())