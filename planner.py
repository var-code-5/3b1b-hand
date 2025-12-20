# planner.py
# Converts user intent to structured plan using OpenAI

import openai
from pydantic import ValidationError
from schemas.plan import ExecutionPlan
import json
import os

class Planner:
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/") # using gemini

    def create_plan(self, intent: str) -> ExecutionPlan:
        prompt = f"""
Convert the following user intent into a structured execution plan for browser automation.
vision-based browser automation agent. Analyze the screenshot and current step.

Current step: 
Intent: {intent}

Output a JSON object with the following structure:
{{
  "steps": [
    {{
      "description": "Step description",
      "expected_actions": ["click", "type_text", "scroll", "wait", "navigate"],
      "locked_values": {{"key": "value"}}  // e.g., amount, recipient
    }}
  ]
}}

Ensure the plan is ordered and deterministic. Lock sensitive values like amounts.
You are a JSON generator.
Return ONLY valid JSON.
No markdown.
No explanation.
No code fences.
"""
        response = self.client.chat.completions.create(
            model="gemini-2.5-flash",  # or gpt-3.5-turbo
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        print(response)
        plan_json = response.choices[0].message.content
        print(plan_json)
        try:
            plan_data = json.loads(plan_json)
            return ExecutionPlan(**plan_data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise ValueError(f"Invalid plan generated: {e}")
