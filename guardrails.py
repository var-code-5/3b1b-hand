# guardrails.py
# Validation functions for safety

from schemas.actions import Action, FillByLabelAction
from schemas.plan import PlanStep
import re

def validate_coordinates(x: int, y: int, screen_width: int = 1024, screen_height: int = 768) -> bool:
    """Check if coordinates are on screen bounds."""
    return 0 <= x < screen_width and 0 <= y < screen_height

def validate_text_input(text: str, expected: str) -> bool:
    """Check if text matches expected value (e.g., amount)."""
    # Simple exact match or regex if needed
    return text == expected

def validate_action_for_step(action: Action, step: PlanStep) -> bool:
    """Check if action is allowed for the current step."""
    action_name = type(action).__name__.replace('Action', '').lower()
    return action_name in step.expected_actions

def validate_locked_values(action: Action, step: PlanStep) -> bool:
    """Ensure VLM doesn't change locked values like amount."""
    if isinstance(action, FillByLabelAction):
        # Check if any locked value should be used in this action
        for key, value in step.locked_values.items():
            # If the locked key is 'text' or matches a field name, enforce exact match
            if key == 'text' and action.text != value:
                print(f"❌ Locked value violation: expected '{value}', got '{action.text}'")
                return False
    return True
