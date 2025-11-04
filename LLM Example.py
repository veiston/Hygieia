import ollama  # Please install ollama beforehand. After that download the model with: ollama run qwen3:0.6b
import re

# A really small & lobotomized version of Alibabas Qwen3. Size on drive: 523MB
MODEL_NAME = "qwen3:0.6b"

# Load the system prompt from an external file (It got so long)
with open("system_prompt.txt", "rb") as file:
    SYSTEM_PROMPT = str(
        file.read()
    )  # Let's open the text in bytes to avoid issues with the character decoder.

USER_PROMPT = input("Let's test this thing out! Please write here :'): ")
prompt = [{"role": "system", "content": SYSTEM_PROMPT + USER_PROMPT}]
response = ""  # Let's declare this here for global scope
try:
    stream = ollama.chat(
        model=MODEL_NAME, messages=prompt, stream=True
    )  # Call LLM API with specified model and prompt.
    for chunk in stream:  # Add generated chunks to final message
        content = chunk.get("message", {}).get("content", "")
        print(content, flush=True, end="")  # UNCOMMENT to view thinking process.
        response += content

    # Regex final message intended for user.
    cleaned_response = re.sub(r"<think>.*?</think>\n?", "", response, flags=re.DOTALL)

except Exception as e:
    print(f"An fatal error has occured while generating LLM response: {e}")

print(cleaned_response)  # Not sure why PyLance is throwing a fit here. Shit works.
