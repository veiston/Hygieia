import base64
import logging
from typing import List, Dict, Optional
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
        {"role": "system", "content": "You are a helpful assistant. Summarize  following conversation context into  most important key points:"},
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