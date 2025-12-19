# schemas/plan.py
# Pydantic models for planner output

from pydantic import BaseModel
from typing import List

class PlanStep(BaseModel):
    description: str
    expected_actions: List[str]  # e.g., ["click", "type_text"]
    locked_values: dict  # e.g., {"amount": "500 Rs", "recipient": "Rohit"}

class ExecutionPlan(BaseModel):
    steps: List[PlanStep]
