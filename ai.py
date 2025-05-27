from openai import OpenAI
import os
from datetime import datetime
from dotenv import load_dotenv
import assemblyai as aai

load_dotenv()

class AI:
    def __init__(self, openai_api_key, stt_key):
        self.client = OpenAI(api_key=openai_api_key)
        aai.settings.api_key =  stt_key
        
    def ttt(self, text):
        response = self.client.responses.create(
            model="gpt-4.1-nano",
            input = text
        )
        return response.output_text   # Response json

    def stt(self, audio = None):
        with open('/Users/outbell/Ajay/DeepLearning/GenAI/Reciperite/2024-12-19-18:29.mp3', 'rb') as audio:
            '''transcript = self.client.audio.transcriptions.create(
                model = "whisper-1",
                file = audio
            )
            
            return transcript["text"]   # Response string'''
            config = aai.TranscriptionConfig(speech_model=aai.SpeechModel.best)
            transcript = aai.Transcriber(config=config).transcribe(audio)

            if transcript.status == "error":
                raise RuntimeError(f"Transcription failed: {transcript.error}")

            return transcript.text

    def tts(self, text):
        '''response = self.client.Audio.speech.create(
            model="tts-1",
            voice="nova",  # Other options: alloy, echo, fable, onyx, shimmer
            input = text
            )'''
        file_name = datetime.now().strftime('%Y%m%dT%H%M%SZ')
        with open(f"{file_name}.mp3", "wb") as f:
            f.write(response.content)
        return f"{file_name}.mp3"
    
ai = AI(os.environ["OPENAI_API_KEY"], os.environ["ASSEMBLY_AI_API_KEY"])

print(ai.stt())