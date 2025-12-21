# controller.py
# Main agent loop

from planner import Planner
from browser.playwright_browser import PlaywrightBrowser
from vlm.qwen_client import QwenClient
from guardrails import validate_coordinates, validate_text_input, validate_action_for_step, validate_locked_values
from schemas.actions import Action, ClickByTextAction, FillByLabelAction, ScrollAction, WaitAction, NavigateAction, DoneAction, AddCredentialAction, GetServiceFieldsAction, GetCredentialAction, ListServicesAction, DeleteCredentialAction, LockVaultAction, CheckIsLockedAction, UpdateCredentialAction
import json
import os

class Controller:
    def __init__(self, planner: Planner, browser: PlaywrightBrowser, vlm: QwenClient, vault_manager):
        self.planner = planner
        self.browser = browser
        self.vlm = vlm
        self.vault_manager = vault_manager
        self.current_step_index = 0
        self.current_action_index = 0
        self.history = []
        self.stepsHistory = []
        self.action_results = {}
        self.log_dir = "logs"
        os.makedirs(self.log_dir, exist_ok=True)

    def run(self, intent: str):
        plan = self.planner.create_plan(intent)
        self.stepsHistory = plan.steps
        while self.current_step_index < len(plan.steps):
            step = plan.steps[self.current_step_index]
            self.execute_step(step)
            self.current_step_index += 1

    def execute_step(self, step):
        retries = 0 # for steps
        print("Current step:",step)
        print("=================================\n")
        while retries < 3:
            screenshot_filename = f"screenshot_step_{self.current_step_index}_{retries}.png"
            self.browser.take_screenshot(screenshot_filename)
            screenshot_path = os.path.join("screenshots", screenshot_filename)
            
            history_str = "; ".join(self.history[-5:])  # last 5 actions
            step_history = "; ".join([str(s) for s in self.stepsHistory[:self.current_step_index]])

            actions_data = self.vlm.call_vlm(screenshot_path, step.description , step_history, history_str, step.locked_values, self.action_results)
            actions = self.parse_actions(actions_data)
            
            if self.validate_actions(actions, step):
                all_actions_executed = True
                for action, action_data in zip(actions, actions_data):
                    try:
                        print(f"Executing action: {action_data}, with action object: {action} of type {type(action)}")
                        action_result = self.execute_action(action)
                        if action_result is not None:
                            self.action_results[action_data['name']] = action_result
                        self.history.append(f"{action_data['name']} with {action_data.get('arguments', {})}")
                        with open(os.path.join(self.log_dir, f"step_{self.current_step_index}.log"), "a") as f:
                            f.write(f"Screenshot: {screenshot_filename}\nAction: {action_data}\n")
                    except Exception as e:
                        print(f"\nError executing action {action_data}: {e}\n")
                        all_actions_executed = False
                        break
                
                # Check if last action is done
                if actions and isinstance(actions[-1], DoneAction):
                    break
                
                # If all actions executed successfully, move to next step
                if all_actions_executed:
                    break
                
                retries = 0  # reset retries if actions executed but not done
            else:
                print(f"\n❌ Validation failed for actions: {actions_data}")
                print(f"Expected locked values: {step.locked_values}")
                print(f"Expected actions: {step.expected_actions}\n")
            
            retries += 1
        
        if retries >= 3:
            raise Exception(f"Failed to execute step after 3 retries: {step.description}")

    # changes the llm's functions to actual functions with args
    def parse_action(self, data: dict) -> Action:
        name = data["name"]
        args = data.get("arguments", {})
        if name == "click_by_text":
            return ClickByTextAction(**args)
        elif name == "fill_by_label":
            return FillByLabelAction(**args)
        elif name == "scroll":
            return ScrollAction(**args)
        elif name == "wait":
            return WaitAction(**args)
        elif name == "navigate":
            return NavigateAction(**args)
        elif name == "addCredential":
            return AddCredentialAction(**args)
        elif name == "updateCredential":
            return UpdateCredentialAction(**args)
        elif name == "getServiceFields":
            return GetServiceFieldsAction(**args)
        elif name == "getCredential":
            return GetCredentialAction(**args)
        elif name == "listServices":
            return ListServicesAction()
        elif name == "deleteCredential":
            return DeleteCredentialAction(**args)
        elif name == "lockVault":
            return LockVaultAction()
        elif name == "checkIsVaultLocked":
            return CheckIsLockedAction()
        elif name == "done":
            return DoneAction()
        else:
            raise ValueError(f"Unknown action: {name}")

    # wrapper for multiple actions
    def parse_actions(self, actions_data: list[dict]) -> list[Action]:
        """Parse a list of action dictionaries into Action objects."""
        return [self.parse_action(action_data) for action_data in actions_data]

    # validates with guardrails so that the values dont change
    def validate_action(self, action: Action, step) -> bool:
        # disabled gaurdrail
        # if isinstance(action, FillByLabelAction):
        #     if not validate_locked_values(action, step):
        #         return False
        # return validate_action_for_step(action, step)
        return True

    # wrapper for multiple actions
    def validate_actions(self, actions: list[Action], step) -> bool:
        """Validate all actions in the list."""
        if not actions:
            return False
        
        for action in actions:
            if not self.validate_action(action, step):
                return False
        
        return True

    # executes a single action
    def execute_action(self, action: Action):
        print(f"Executing action: {action}")
        if isinstance(action, ClickByTextAction):
            print(f"[DEBUG] Clicking by text: {action.text}")
            self.browser.click_by_text(action.text)
        elif isinstance(action, FillByLabelAction):
            print(f"[DEBUG] Filling label '{action.label}' with text '{action.text}'")
            self.browser.fill_by_label(action.label, action.text)
        elif isinstance(action, ScrollAction):
            print(f"[DEBUG] Scrolling by delta: {action.delta}")
            self.browser.scroll(action.delta)
        elif isinstance(action, WaitAction):
            print(f"[DEBUG] Waiting for ms: {action.ms}")
            self.browser.wait(action.ms)
        elif isinstance(action, NavigateAction):
            print(f"[DEBUG] Navigating to URL: {action.url}")
            self.browser.navigate(action.url)
        elif isinstance(action, DoneAction):
            print(f"[DEBUG] Done action encountered.")
            pass  # Do nothing
        elif isinstance(action, AddCredentialAction):
            print(f"[DEBUG] Adding credential: {action.data}")
            self.vault_manager.add_credential(action.data)
        elif isinstance(action, UpdateCredentialAction):
            print(f"[DEBUG] Updating credential for service '{action.service}' with data: {action.data}")
            self.vault_manager.update_credential(action.service, action.data)
        elif isinstance(action, GetServiceFieldsAction):
            fields = self.vault_manager.get_service_fields(action.service)
            print(f"[DEBUG] Service fields for '{action.service}': {fields}")
            return fields
        elif isinstance(action, GetCredentialAction):
            cred = self.vault_manager.get_credential(action.service)
            print(f"[DEBUG] Credential for service '{action.service}': {cred}")
            return cred
        elif isinstance(action, ListServicesAction):
            services = self.vault_manager.list_services()
            print(f"[DEBUG] List of services in vault: {services}")
            return services
        elif isinstance(action, DeleteCredentialAction):    
            print(f"[DEBUG] Deleting credential for service '{action.service}'")
            self.vault_manager.delete_credential(action.service)
        elif isinstance(action, LockVaultAction):
            print(f"[DEBUG] Locking vault.")
            self.vault_manager.lock_vault()
        elif isinstance(action, CheckIsLockedAction):
            locked = self.vault_manager.check_is_vault_locked()
            print(f"[DEBUG] Vault locked: {locked}")
            return locked
        else:
            raise ValueError(f"Unknown action type: {type(action)}")
