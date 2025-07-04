from dataclasses import dataclass

from deepgram import (
    DeepgramClientOptions,
    LiveOptions,
)

from google.genai import types

import data.prompts as prompt


@dataclass
class STT_CONFIG:
    CONFIG: DeepgramClientOptions = DeepgramClientOptions(options={"keepalive": "true"})
    OPTIONS = LiveOptions(model="nova-3", language="en-US", smart_format=True, encoding="linear16", channels=1, 
        sample_rate=16000, vad_events=True, endpointing=5)#interim_results = True, utterance_end_ms = 1000, endpointing=300)
    ADDONS = {"no_delay": "true"}
    
    
    
    
    
@dataclass
class TTT_CONFIG:
    MODEL =  "gemini-2.5-flash-preview-05-20"  
    
    
    
    
@dataclass
class TTS_CONFIG:
    model_id = "sonic-2"
    voice = {"id": "f9836c6e-a0bd-460e-9d3c-f7299fa60f94"}
    output_format = {
        "container": "raw",
        "encoding": "pcm_s16le",
        "sample_rate": 16000
    }
    stream = True
    

    
    
    
STT = STT_CONFIG()
TTT = TTT_CONFIG()
TTS = TTS_CONFIG()


user_details = "name is ajay"