# README.md

# Vision-Based Browser Automation Agent

A deterministic, vision-based browser automation agent built in Python without using any agent frameworks like LangChain.

## Architecture

The agent consists of the following components:

- **planner.py**: Uses OpenAI to convert natural language intent into a structured execution plan.
- **controller.py**: Main control loop that executes the plan step-by-step.
- **browser/playwright_browser.py**: Safe wrapper around Playwright for browser actions.
- **vlm/qwen_client.py**: Client for Qwen-VL vision-language model.
- **vlm/prompt.py**: System prompt for the VLM.
- **schemas/actions.py**: Pydantic models for allowed actions.
- **schemas/plan.py**: Pydantic models for the execution plan.
- **guardrails.py**: Validation functions for safety.
- **main.py**: CLI entry point.

## Setup

1. Install `uv` if not already installed.
2. Clone the repository.
3. Install dependencies:
   ```
   uv pip install playwright openai pydantic pillow
   ```
4. Install Playwright browsers:
   ```
   playwright install
   ```
5. Set environment variables:
   - `OPENAI_API_KEY`: Your OpenAI API key.
   - `QWEN_API_KEY`: Your Qwen-VL API key.

## Usage

Run the agent with a natural language intent:

```
uv run main.py "Send 500 Rs to Rohit"
```

## How the Agent Loop Works

1. The planner converts the intent into a structured plan with ordered steps.
2. The controller iterates through each step.
3. For each step, it captures a screenshot and sends it to the VLM along with the step description and action history.
4. The VLM returns exactly one function call (e.g., click, type_text).
5. The action is validated against guardrails.
6. If valid, the action is executed on the browser.
7. Screenshots and actions are logged to disk.
8. Repeat until the step is done or max retries reached.

## Safety Limitations

- Actions are limited to predefined safe operations.
- Coordinates must be on-screen.
- Locked values (e.g., amounts) cannot be changed by the VLM.
- No more than 3 retries per step.
- Final submit actions require confirmation (not implemented in this version).

## Design Decisions

- Deterministic control flow ensures predictability.
- Pydantic models for type safety.
- Separate concerns into modules for maintainability.
- No abstractions over the core logic to keep it explicit.
