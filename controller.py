# controller.py
# Main agent loop

from planner import Planner
from browser.playwright_browser import PlaywrightBrowser
from vlm.qwen_client import QwenClient
from guardrails import validate_coordinates, validate_text_input, validate_action_for_step, validate_locked_values
from schemas.actions import Action, ClickAction, TypeTextAction, ScrollAction, WaitAction, NavigateAction, DoneAction
import json
import os

class Controller:
    def __init__(self, planner: Planner, browser: PlaywrightBrowser, vlm: QwenClient):
        self.planner = planner
        self.browser = browser
        self.vlm = vlm
        self.current_step_index = 0
        self.history = []
        self.log_dir = "logs"
        os.makedirs(self.log_dir, exist_ok=True)

    def run(self, intent: str):
        plan = self.planner.create_plan(intent)
        while self.current_step_index < len(plan.steps):
            step = plan.steps[self.current_step_index]
            self.execute_step(step)
            self.current_step_index += 1

    def execute_step(self, step):
        retries = 0
        while retries < 3:
            screenshot_filename = f"screenshot_step_{self.current_step_index}_{retries}.png"
            self.browser.take_screenshot(screenshot_filename)
            screenshot_path = os.path.join("screenshots", screenshot_filename)
            history_str = "; ".join(self.history[-5:])  # last 5 actions
            action_data = self.vlm.call_vlm(screenshot_path, step.description, history_str)
            action = self.parse_action(action_data)
            if self.validate_action(action, step):
                self.execute_action(action)
                self.history.append(f"{action_data['name']} with {action_data.get('arguments', {})}")
                with open(os.path.join(self.log_dir, f"step_{self.current_step_index}.log"), "a") as f:
                    f.write(f"Screenshot: {screenshot_filename}\nAction: {action_data}\n")
                if isinstance(action, DoneAction):
                    break
                # Continue to next iteration for the same step
            retries += 1
        if retries >= 3:
            raise Exception(f"Failed to execute step after 3 retries: {step.description}")

    def parse_action(self, data: dict) -> Action:
        name = data["name"]
        args = data.get("arguments", {})
        if name == "click":
            return ClickAction(**args)
        elif name == "type_text":
            return TypeTextAction(**args)
        elif name == "scroll":
            return ScrollAction(**args)
        elif name == "wait":
            return WaitAction(**args)
        elif name == "navigate":
            return NavigateAction(**args)
        elif name == "done":
            return DoneAction()
        else:
            raise ValueError(f"Unknown action: {name}")

    def validate_action(self, action: Action, step) -> bool:
        if isinstance(action, ClickAction):
            if not validate_coordinates(action.x, action.y):
                return False
        elif isinstance(action, TypeTextAction):
            if not validate_locked_values(action, step):
                return False
        return validate_action_for_step(action, step)

    def execute_action(self, action: Action):
        if isinstance(action, ClickAction):
            self.browser.click(action.x, action.y)
        elif isinstance(action, TypeTextAction):
            self.browser.type_text(action.text)
        elif isinstance(action, ScrollAction):
            self.browser.scroll(action.delta)
        elif isinstance(action, WaitAction):
            self.browser.wait(action.ms)
        elif isinstance(action, NavigateAction):
            self.browser.navigate(action.url)
        elif isinstance(action, DoneAction):
            pass  # Do nothing
