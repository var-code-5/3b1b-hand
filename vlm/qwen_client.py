# vlm/qwen_client.py
# Client for Qwen-VL API

import requests
import base64
from PIL import Image
import io
from vlm.prompt import SYSTEM_PROMPT
import json

class QwenClient:
    def __init__(self, api_key: str, base_url: str = "https://api.qwen.ai/v1"):
        self.api_key = api_key
        self.base_url = base_url

    def call_vlm(self, image_path: str, step_description: str, history: str, locked_values: dict = None) -> list[dict]:
        with open(image_path, "rb") as img_file:
            img_data = base64.b64encode(img_file.read()).decode()

        # Format locked values instruction
        locked_values_instruction = ""
        if locked_values:
            locked_values_str = ", ".join([f"{k}: {v}" for k, v in locked_values.items()])
            locked_values_instruction = f"CRITICAL - You MUST use these exact values (DO NOT CHANGE): {locked_values_str}"
        
        prompt = SYSTEM_PROMPT.format(
            step_description=step_description, 
            history=history,
            locked_values_instruction=locked_values_instruction
        )

        payload = {
            "model": "qwen-vl-max",  # Assuming model name
            "messages": [
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_data}"}}
                ]}
            ]
        }

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        response = requests.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        print(content)
        actions = json.loads(content)
        
        # Ensure we always return a list
        if isinstance(actions, dict):
            # If single action dict is returned, wrap it in a list
            return [actions]
        elif isinstance(actions, list):
            return actions
        else:
            raise ValueError(f"Unexpected response format: {actions}")
