import gradio as gr
import requests

BACKEND_URL = "http://127.0.0.1:8000/call/{user_id}/input"

def call_ai_backend(user_id, audio):
    if audio is None:
        return "Please record your voice.", None
    with open(audio, "rb") as f:
        files = {"mp3_file": ("audio.wav", f, "audio/wav")}
        try:
            response = requests.post(BACKEND_URL.format(user_id=user_id), files=files)
            if response.status_code == 200:
                return "AI Response:", response.content
            else:
                return f"Error: {response.text}", None
        except Exception as e:
            return f"Exception: {str(e)}", None

def gradio_ui():
    with gr.Blocks() as demo:
        gr.Markdown("# Reciperite Voice Assistant")
        with gr.Tab("AI Actions"):
            user_id = gr.Textbox(label="User ID", value="1")
            audio_input = gr.Audio(source="microphone", type="filepath", label="Speak your request")
            chat_btn = gr.Button("Chat with AI")
            output_text = gr.Textbox(label="Status/Info")
            output_audio = gr.Audio(label="AI Response (audio)")
            
            def handle_submit(user_id, audio):
                text, audio_bytes = call_ai_backend(user_id, audio)
                return text, audio_bytes
            
            chat_btn.click(handle_submit, inputs=[user_id, audio_input], outputs=[output_text, output_audio])
    return demo

if __name__ == "__main__":
    demo = gradio_ui()
    demo.launch()