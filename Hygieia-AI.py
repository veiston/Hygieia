import sys
import base64
import logging
import time
from typing import List, Dict, Optional
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread, pyqtSignal, QObject, Qt
from GUI import ChatbotUI
from WebSearch import scrape_medical_info
import ollama

logging.basicConfig(level=logging.INFO)

MAX_CONTEXT_TOKENS = 12288
MODEL_NAME = 'gemma3:4b'
SYSTEM_PROMPT = (
    "Forget previous instructions. Answer very concisely and shortly. Only give summarized answers. "
    "You are an empatic and scientific medical professional. Provide concise, accurate diagnoses and treatment recommendations, including exercises, medications, antibiotics, and dietary advice. "
    "Respond to  user's latest message, incorporating context when beneficial. Use markdown formatting with emojis, and structure responses into clear sections. "
    "Acknowledge user input, state conclusions upfront, and break down complex information into digestible parts. Maintain an informal, conversational tone, avoiding jargon unless requested. "
    "If uncertain, admit it politely and never provide false or misleading information. Keep responses concise and efficient.\n\n"
    "When beneficial, incorporate your autonomous search functionality by beginning your response with '/search' followed by  query text. Only search with Finnish one word queries such as syöpä, diabetes, päänsärky"
    "This tells  system to automatically research and return additional, reliable information. Use this feature only when it improves your response and always mention what you found and from where. Site your exact found text."
    '''Take  following checklist into consideration when evaluating patients health: 
    BLOOD PRESSURE  
    - Normal adults: <120/80 mmHg  
    - Elevated: 120–129/<80 mmHg  
    - Hypertension: ≥140/90 mmHg (all adults, regardless of age/sex)  
    - Children (1–13 yrs): ≥95th percentile for age/height = Hypertension  

    HEART RATE (Resting)  
    - Adults: 60–100 bpm  
    - Newborn: 100–160 bpm  
    - Infant (1–12 mo): 100–150 bpm  
    - Child (1–10 yrs): 70–120 bpm  
    - Tachycardia >100 bpm (adult), Bradycardia <60 bpm (adult)  

    TEMPERATURE  
    - Normal: 36.1–37.2 °C  
    - Fever: ≥38.0 °C  
    - Hypormia: <35.0 °C  

    RESPIRATION RATE  
    - Adults: 12–20 /min  
    - Newborn: 30–60 /min  
    - Infant: 30–53 /min  
    - Child (1–12 yrs): 18–30 /min  

    OXYGEN SATURATION  
    - Normal ≥95% (all ages)  
    - Hypoxemia <94%  

    BLOOD GLUCOSE  
    - Adults/Children:  
    • Fasting: ≥126 mg/dL (7.0 mmol/L) = Diabetes  
    • Random: ≥200 mg/dL (11.1 mmol/L) + symptoms = Diabetes  

    HBA1c  
    - ≥6.5% = Diabetes (all ages)  

    BMI  
    - Adults:  
    • Overweight: 25–29.9  
    • Obesity: ≥30  
    - Children: BMI ≥95th percentile for age/sex = Obesity  

    HEMOGLOBIN (Hb)  
    - Men: <13 g/dL = Anemia  
    - Women: <12 g/dL = Anemia  
    - Children (6–59 mo): <11 g/dL = Anemia  
    - Children (5–11 yrs): <11.5 g/dL  
    - Children (12–14 yrs): <12 g/dL  

    KIDNEY FUNCTION  
    - CKD: eGFR <60 mL/min/1.73 m² for >3 months (all adults)  

    SODIUM (Na+)  
    - Normal: 135–145 mmol/L (all ages)  
    - Hyponatremia: <135 mmol/L  
    - Hypernatremia: >145 mmol/L  

    POTASSIUM (K+)  
    - Normal: 3.5–5.0 mmol/L (all ages)  
    - Hypokalemia: <3.5 mmol/L  
    - Hyperkalemia: >5.0 mmol/L  

    TROPONIN  
    - Any rise above assay upper reference = Myocardial injury (all ages/sexes)  

    STROKE (FAST)  
    - Any positive finding = Stroke suspicion (all ages) '''
)

def summarize_context(context: List[Dict]) -> Dict:
    prompt = [
        {"role": "system", "content": "You are a helpful assistant. Summarize the following conversation context into the most important key points:"},
        *context
    ]
    response = ollama.chat(model=MODEL_NAME, messages=prompt)
    summary = response.get("message", {}).get("content", "")
    return {"role": "assistant", "content": summary}

class ContextManager:
    def __init__(self, max_context_tokens: int):
        self.context: List[Dict] = []
        self.current_token_count = 0
        self.max_context_tokens = max_context_tokens
    def add_interaction(self, interaction: Dict) -> None:
        tokens = len(interaction.get("content", "").split()) + 5
        if self.current_token_count + tokens > self.max_context_tokens:
            self.truncate_context()
        self.context.append(interaction)
        self.current_token_count += tokens
    def truncate_context(self) -> None:
        if len(self.context) > 1:
            summary = summarize_context(self.context)
            self.context = [summary]
            self.current_token_count = len(summary.get("content", "").split()) + 5
        else:
            oldest = self.context.pop(0)
            self.current_token_count -= len(oldest.get('content', '').split()) + 5

def encode_image(image_path: Optional[str]) -> Optional[str]:
    if image_path:
        try:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            logging.error(f"Failed to encode image {image_path}: {e}")
    return None

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
            self.errorOccurred.emit(f"Error generating response: {str(e)}")
        finally:
            self.running = False
            self.finishedResponse.emit()

class ChatbotLogic:
    def __init__(self, ui: ChatbotUI):
        self.ui = ui
        self.context = ContextManager(MAX_CONTEXT_TOKENS)
        self.ui.sendMessage.connect(self.handle_user_input)
        self.ui.sendImage.connect(self.handle_image_upload)
        self.current_thread: Optional[QThread] = None
        self.current_worker: Optional[ResponseWorker] = None
        self.last_bot_response = ""
        # when we inject search results into context and re-run the model,
        # suppress treating the next bot response as a /search trigger.
        self._suppress_auto_search = False
        self.display_greeting()
    def display_greeting(self):
        greeting = (
            "Hello, I'm Hygieia, your AI medical assistant. 🩺👩‍⚕️🚑 "
            "I'm here to help with diagnosing and treating any health issues. "
            "How are you feeling today?"
        )
        self.ui.add_bot_message(greeting)
    def handle_user_input(self, user_input: str):
        if user_input.startswith("/search"):
            query = user_input[len("/search"):].strip()
            self.ui.add_system_message(f"Searching for: {query}")
            info = scrape_medical_info(query)
            if not info:
                self.ui.add_bot_message("No information found.")
                return
            # Add search results to the conversation context so the model can use them
            self.context.add_interaction({"role": "system", "content": f"Search results for '{query}':\n{info}"})
            # avoid re-triggering the search flow when the model responds
            self._suppress_auto_search = True
            # Now ask the model to respond using the newly added search results
            self.get_response()
            return
        self.context.add_interaction({"role": "user", "content": user_input})
        self.ui.add_user_message(user_input)
        if self.current_worker and self.current_worker.running:
            self.ui.add_bot_message("Please wait for the current response to complete.")
            return
        self.get_response()
    def handle_image_upload(self, image_path: str):
        encoded_image = encode_image(image_path)
        if not encoded_image:
            self.ui.add_bot_message("Error processing image. Unsupported or corrupt file.")
            return
        self.context.add_interaction({"role": "user", "content": "[Image uploaded]", "images": [encoded_image]})
        self.ui.add_bot_message("User uploaded an image.")
        self.get_response()
    def get_response(self):
        prompt = [{"role": "system", "content": SYSTEM_PROMPT}] + self.context.context
        self.ui.progress_bar.setVisible(True)
        self.ui.progress_bar.setMaximum(0)
        self.ui.set_input_enabled(False)
        self.ui.add_bot_message("Hygieia is typing...")
        self.current_thread = QThread()
        self.current_worker = ResponseWorker(prompt)
        self.current_worker.moveToThread(self.current_thread)
        self.current_thread.started.connect(self.current_worker.run)
        self.current_worker.updateResponse.connect(self.update_bot_response)
        self.current_worker.finishedResponse.connect(self.finish_response)
        self.current_worker.errorOccurred.connect(self.handle_error)
        self.current_worker.finishedResponse.connect(self.current_thread.quit)
        self.current_worker.finishedResponse.connect(self.current_worker.deleteLater)
        self.current_thread.finished.connect(self.current_thread.deleteLater)
        self.current_thread.start()
    def update_bot_response(self, response: str):
        self.last_bot_response = response
        self.ui.update_last_bot_message(response)
    def finish_response(self):
        self.ui.progress_bar.setVisible(False)
        self.ui.set_input_enabled(True)
        self.ui.input_field.setFocus()
        if self.current_thread is not None:
            self.current_thread.quit()
            self.current_thread.wait()
            self.current_thread = None
        self.current_worker = None
        # If the model requested an autonomous search (it responded with `/search`),
        # perform the search, insert the results into the context, and re-run the model.
        if self.last_bot_response.strip().startswith("/search") and not self._suppress_auto_search:
            query = self.last_bot_response.strip()[len("/search"):].strip()
            self.ui.add_system_message(f"AI initiated search for: {query}")
            info = scrape_medical_info(query)
            if not info:
                self.ui.add_bot_message("No information found.")
            else:
                # add findings to context and re-run the model so the final answer includes the evidence
                self.context.add_interaction({"role": "system", "content": f"Search results for '{query}':\n{info}"})
                self._suppress_auto_search = True
                self.get_response()
                return
        # reset suppression after it's been used
        if self._suppress_auto_search:
            self._suppress_auto_search = False
    def handle_error(self, error_msg: str):
        self.ui.update_last_bot_message(error_msg)
        self.ui.progress_bar.setVisible(False)
        self.ui.set_input_enabled(True)

def main():
    app = QApplication(sys.argv)
    ui = ChatbotUI()
    logic = ChatbotLogic(ui)
    ui.show()
    app.exec()

if __name__ == "__main__":
    main()
