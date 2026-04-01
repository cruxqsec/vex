from pydantic import BaseModel, Field


class Settings(BaseModel):
    navigation_position: str = Field(default="top")
    """Navigation bar position."""

    theme: str = Field(default="textual-dark")
    """The name of the theme to use."""
