import gradio as gr
import requests
import websocket
import threading
import base64

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
        self.logs += message + "\n\n"
    
    def on_error(self, ws, error):
        self.logs += f"Websocket Error: {error}\n\n"
        
    def on_close(self, ws, sts_code, sts_msg):
        self.logs += "Websocket connection closed.\n\n"
        
        
def update_logs():
    return ws.logs

def call_server(user_id, audio_path):
    with open(audio_path, "rb") as f:
        audio = base64.b64encode(f.read()).decode('utf-8')
    out = requests.post('http://127.0.0.1:8000/call', json = {'user_id' : user_id, 'audio': audio})
    return out
            
def gradio_ui():
    with gr.Blocks() as demo:
        gr.Markdown("# Reciperite Voice Assistant")
        with gr.Row():
            with gr.Column():
                    user_id = gr.Textbox(label="User ID")
                    audio_path = gr.Audio(type="filepath", label="Speak your request")
                    audio_output = gr.Audio(label="AI Response (audio)", type="filepath")
            with gr.Column():
                log_box = gr.Textbox(
                    label="AI logs",
                    placeholder="AI's response will be displayed here",
                    lines=20,
                    value = ws.logs,
                    interactive=False
                    ) 
                demo.load(update_logs, outputs = [log_box], every = 1)  
                     
        audio_path.change(
            fn = call_server,
            inputs = [user_id, audio_path],
            outputs = [audio_output]
            )
    return demo

if __name__ == "__main__":
    ws = WS()
    demo = gradio_ui()
    demo.launch()