from pydantic import BaseModel


class StreamControl(BaseModel):
    enabled: bool


class MealFeedback(BaseModel):
    """A diner response for the dish served today."""

    dish: str
    reaction: str
