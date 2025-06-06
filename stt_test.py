# Example filename: main.py

import httpx
import logging
from deepgram.utils import verboselogs
import threading
import asyncio
import pyaudio

from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)
CHANNEL = 1
FORMAT = pyaudio.paInt16
IN_RATE = 24000
OUT_RATE = 16000
CHUNK = 1024

# URL for the realtime streaming audio you would like to transcribe
URL = "http://stream.live.vc.bbcmedia.co.uk/bbc_world_service"

def on_message(self, result, **kwargs):
        sentence = result.channel.alternatives[0].transcript
        if len(sentence) == 0:
            return
        print(f"speaker: {sentence}")
        
class server:
    async def listen_audio(self):
        mic = await asyncio.to_thread(self.pya.open,
                format=FORMAT,
                channels=CHANNEL,
                rate=IN_RATE,
                input=True,
                frames_per_buffer=CHUNK
            )
        try:
            if __debug__:
                kwargs = {"exception_on_overflow": False}
            else:
                kwargs = {}
            while True:
                chunk = await asyncio.to_thread(mic.read, CHUNK, **kwargs)
                if chunk:
                    await self.audio_out_queue.put(chunk)
                
        except Exception as e:
            print(f"An error occurred while listening audio: {e}")
            
        finally:
            mic.close()
def main():
    try:
        # use default config
        deepgram: DeepgramClient = DeepgramClient()

        # Create a websocket connection to Deepgram
        dg_connection = deepgram.listen.websocket.v("1")

        

        dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)

        # connect to websocket
        options = LiveOptions(model="nova-3")

        print("\n\nPress Enter to stop recording...\n\n")
        if dg_connection.start(options) is False:
            print("Failed to start connection")
            return


        dg_connection.send(data)

        print("Finished")

    except Exception as e:
        print(f"Could not open socket: {e}")
        return

if __name__ == "__main__":
    main()
