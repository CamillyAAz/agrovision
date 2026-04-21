import requests
import json
from typing import Dict, Any, Optional, List

from .config import OLLAMA_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT, OLLAMA_KEEP_ALIVE

class OllamaClient:
    def __init__(self):
        self.base_url = OLLAMA_URL.rstrip('/api/chat')
        self.model = OLLAMA_MODEL
        self.timeout = OLLAMA_TIMEOUT
        self.keep_alive = OLLAMA_KEEP_ALIVE

    def warmup_model(self) -> bool:
        """Warm up the model by sending a simple request."""
        try:
            payload = {
                "model": self.model,
                "prompt": "Hello",
                "stream": False,
                "keep_alive": self.keep_alive
            }
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=30
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to warmup Ollama model: {e}")
            return False

    def chat_completion(self, messages: List[Dict[str, str]], stream: bool = False) -> Optional[str]:
        """Send a chat completion request to Ollama."""
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": stream,
                "keep_alive": self.keep_alive
            }
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout,
                stream=stream
            )

            if response.status_code != 200:
                print(f"Ollama API error: {response.status_code} - {response.text}")
                return None

            if stream:
                # For streaming, we'd need to handle the stream
                # For now, return the full response
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line.decode('utf-8'))
                        if 'message' in chunk and 'content' in chunk['message']:
                            full_response += chunk['message']['content']
                        if chunk.get('done', False):
                            break
                return full_response
            else:
                result = response.json()
                return result.get('message', {}).get('content', '')

        except requests.exceptions.RequestException as e:
            print(f"Ollama request failed: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error in Ollama chat: {e}")
            return None

# Global client instance
ollama_client = OllamaClient()