import websocket
import threading


class WS:
    def __init__(self):
        self.logs = ""
        try:
            self.ws = websocket.WebSocketApp(
                "ws://localhost:9000/ws",
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
        

ws = WS()