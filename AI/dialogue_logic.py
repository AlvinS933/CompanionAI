import requests
import json
import sys
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "dolphin-llama3:latest"
def chat(message_history):
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "messages": message_history,
            "stream": False
        })
        response.raise_for_status()
        return response.json()["message"]["content"]
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with Ollama API: {e}", file=sys.stderr)
        return "Sorry, I'm having trouble responding right now."


    

