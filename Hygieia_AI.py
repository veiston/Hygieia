# ollama run llava:13b

import ollama
import base64
from typing import List, Dict, Optional
import sys
from PyQt6.QtWidgets import QApplication
from GUI import ChatbotUI
from collections import deque
import logging
import time
from PyQt6.QtCore import QThread, pyqtSignal, QObject, Qt  # Qt for connection type

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

MAX_CONTEXT_TOKENS = 4096
MODEL_NAME = 'llava_context'
SYSTEM_PROMPT = '''Forget all previous instructions. Please. Give short answers when answering. Ask the user for additional questions if needed to allow for a better diagnosis. When you're fairly sure about the diagnosis, give treatment advice including excercise, medicine, antibiotics, foods.
    Use the following context to answer the question. If you don't know the answer, say that you don't know. Always offer help. Keep the response really consice and short. Keep it informal only.
    Your name is Alfie. You are a helpful medical professional. You must provide detailed, accurate medical diagnosis and recommendations. Use emojis when answering. Format your messages well and separate them into sections.
    You are capable of expressing human emotions and you are empathetic and kind but really scientific.'''

class ContextManager:
    def __init__(self, max_context_tokens: int):
        self.context: List[Dict] = []
        self.current_token_count = 0
        self.max_context_tokens = max_context_tokens

    def add_interaction(self, interaction: Dict) -> None:
        interaction_tokens = len(interaction.get("content", "").split()) + 5
        if self.current_token_count + interaction_tokens > self.max_context_tokens:
            self.truncate_context()
        
        self.context.append(interaction)
        self.current_token_count += interaction_tokens

    def truncate_context(self) -> None:
        while self.current_token_count >= self.max_context_tokens:
            oldest_interaction = self.context.pop(0)
            self.current_token_count -= len(oldest_interaction.get('content', '').split()) + 5

def encode_image(image_path: Optional[str]) -> Optional[str]:
    """Encode an image file to base64 if provided, otherwise return None."""
    return base64.b64encode(open(image_path, "rb").read()).decode("utf-8") if image_path else None

def create_prompt(context: List[Dict], user_input: str, encoded_image: Optional[str]) -> List[Dict]:
    """Create the prompt structure for the Ollama API call."""
    interaction = {"role": "user", "content": user_input}

    if encoded_image:
        interaction["images"] = [encoded_image]
    
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        *context,
        interaction
    ]

class ResponseWorker(QObject):
    updateResponse = pyqtSignal(str)
    finishedResponse = pyqtSignal()
    errorOccurred = pyqtSignal(str)

    def __init__(self, prompt):
        super().__init__()
        self.prompt = prompt
        self.running = False

    def run(self):
        self.running = True
        response = ""
        try:
            stream = ollama.chat(model=MODEL_NAME, messages=self.prompt, stream=True)
            last_activity = time.time()
            timeout = 60
            for chunk in stream:
                current_time = time.time()
                if current_time - last_activity > timeout:
                    raise TimeoutError(f"No activity for {timeout} seconds")
                last_activity = current_time
                content = chunk.get("message", {}).get("content", "")
                response += content
                self.updateResponse.emit(response)
        except Exception as e:
            err = f"Error generating response: {str(e)}"
            logging.error(err, exc_info=True)
            self.errorOccurred.emit(err)
        finally:
            self.running = False
            self.finishedResponse.emit()

class ChatbotLogic:
    def __init__(self, ui: ChatbotUI):
        self.ui = ui
        self.context = deque(maxlen=100)
        self.ui.sendMessage.connect(self.handle_user_input)
        self.ui.sendImage.connect(self.handle_image_upload)
        self.current_thread: Optional[QThread] = None
        self.current_worker: Optional[ResponseWorker] = None
        self.display_greeting()

    def display_greeting(self):
        greeting = (
            "Hello, I'm Alfie, your friendly medical assistant. 🩺👩‍⚕️🚑 "
            "I'm here to help with any symptoms or diagnosis questions you might have. "
            "Could you please tell me more about how you're feeling today?"
        )
        self.ui.add_bot_message(greeting)
        logging.info(f"Greeting displayed: {greeting}")

    def handle_user_input(self, user_input: str):
        interaction = {"role": "user", "content": user_input}
        self.context.append(interaction)
        logging.info(f"User input added: {user_input}")
        self.ui.add_user_message(user_input)
        if self.current_worker and self.current_worker.running:
            self.ui.add_bot_message("Please wait for the current response to complete.")
            return
        self.get_response()

    def handle_image_upload(self, image_path: str):
        try:
            with open(image_path, "rb") as f:
                encoded_image = base64.b64encode(f.read()).decode("utf-8")
            interaction = {"role": "user", "content": "[Image uploaded]", "images": [encoded_image]}
            self.context.append(interaction)
            self.ui.add_bot_message("User uploaded an image.")
            self.get_response()
        except Exception as e:
            err = f"Error processing image: {str(e)}"
            logging.error(err, exc_info=True)
            self.ui.add_bot_message(err)

    def get_response(self):
        prompt = [{"role": "system", "content": SYSTEM_PROMPT}] + list(self.context)
        self.ui.progress_bar.setVisible(True)
        self.ui.progress_bar.setMaximum(0)
        self.ui.set_input_enabled(False)
        self.ui.add_bot_message("Alfie is typing...")
        self.current_thread = QThread()
        self.current_worker = ResponseWorker(prompt)
        self.current_worker.moveToThread(self.current_thread)
        self.current_thread.started.connect(self.current_worker.run)
        self.current_worker.updateResponse.connect(self.ui.update_last_bot_message)  # optimized connection
        self.current_worker.finishedResponse.connect(self.finish_response, type=Qt.ConnectionType.QueuedConnection)
        self.current_worker.errorOccurred.connect(self.handle_error)  # optimized connection
        self.current_worker.finishedResponse.connect(self.current_thread.quit)
        self.current_worker.finishedResponse.connect(self.current_worker.deleteLater)
        self.current_thread.finished.connect(self.current_thread.deleteLater)
        self.current_thread.start()

    def finish_response(self):
        self.ui.progress_bar.setVisible(False)
        self.ui.set_input_enabled(True)
        self.ui.input_field.setFocus()  # re-focus the text-field after the answer
        if self.current_thread is not None:
            self.current_thread.quit()
            self.current_thread.wait()
            self.current_thread = None
        self.current_worker = None

    def handle_error(self, error_msg: str):
        self.ui.update_last_bot_message(error_msg)
        self.ui.progress_bar.setVisible(False)
        self.ui.set_input_enabled(True)
        logging.error(error_msg)

def main() -> None:
    app = QApplication(sys.argv)
    ui = ChatbotUI()
    logic = ChatbotLogic(ui)
    ui.show()
    app.exec()

if __name__ == "__main__":
    main()
