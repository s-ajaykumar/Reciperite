import gradio as gr
import requests
import websocket
import threading
import base64
import tempfile
import json

#BACKEND_URL = "http://127.0.0.1:8000/call/{user_id}/input"


class WS:
    def __init__(self):
        self.logs = ""
        try:
            self.ws = websocket.WebSocketApp(
                "ws://localhost:8000/ws",
                on_message = self.on_message,
                on_error = self.on_error,
                on_close = self.on_close
            )
            threading.Thread(target = self.run_ws, daemon = True).start()
            self.logs += "WebSocket connection established.\n\n"
        except Exception as e:
            print(f"Error connecting to WebSocket: {e}")
        
    def run_ws(self):
        self.ws.run_forever()
        
    def on_message(self, ws, message):
        message = json.loads(message)
        self.logs += message['log'] + "\n\n"
    
    def on_error(self, ws, error):
        self.logs += f"Websocket Error: {error}\n\n"
        
    def on_close(self, ws, sts_code, sts_msg):
        self.logs += "Websocket connection closed.\n\n"
        
        
def update_logs():
    return ws.logs


def call_server(user_id, audio_input):
    with open(audio_input, "rb") as f:
        audio = base64.b64encode(f.read()).decode('utf-8')
    out = requests.post('http://127.0.0.1:8000/call', json = {'user_id' : user_id, 'audio': audio})
    out = out.json()
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=f'.wav') as temp_file:
            temp_file.write(base64.b64decode(out['response_audio']))
            temp_file_path = temp_file.name
    return out['response_text'], temp_file_path
       
            
def gradio_ui():
    with gr.Blocks() as demo:
        gr.Markdown("# Reciperite Voice Assistant")
        with gr.Row():
            with gr.Column():
                    user_id = gr.Textbox(label="User ID")
                    audio_input = gr.Audio(type="filepath", label="Speak your request")
                    text_output = gr.Textbox(
                        label="AI Response",
                        placeholder="AI's response will be displayed here",
                        lines=5,
                        interactive=False
                    )
                    audio_output = gr.Audio(label="AI Response (audio)", type="filepath")
            with gr.Column():
                log_box = gr.Textbox(
                    label="AI logs",
                    placeholder="AI's response will be displayed here",
                    lines=20,
                    value = ws.logs,
                    interactive=False
                    ) 
        timer = gr.Timer(0.1)  # Update every 1 second
        timer.tick(update_logs, outputs=[log_box])
                
                     
        audio_input.change(
            fn = call_server,
            inputs = [user_id, audio_input],
            outputs = [text_output, audio_output]
            )
    return demo


if __name__ == "__main__":
    ws = WS()
    demo = gradio_ui()
    demo.launch()