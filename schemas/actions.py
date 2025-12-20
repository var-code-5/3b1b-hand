# schemas/actions.py
# Pydantic models for allowed browser actions

from pydantic import BaseModel
from typing import Optional, List

class ClickByTextAction(BaseModel):
    text: str

class FillByLabelAction(BaseModel):
    label: str
    text: str

class ScrollAction(BaseModel):
    delta: int

class WaitAction(BaseModel):
    ms: int

class NavigateAction(BaseModel):
    url: str

class DoneAction(BaseModel):
    pass

# Union of all actions
from typing import Union
Action = Union[ClickByTextAction, FillByLabelAction, ScrollAction, WaitAction, NavigateAction, DoneAction]

class ActionList(BaseModel):
    """Container for a list of actions to be executed for a step."""
    actions: List[Action]
