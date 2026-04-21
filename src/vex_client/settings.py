from pydantic import BaseModel, Field


class Settings(BaseModel):
    navigation_position: str = Field(default="top")
    """Navigation bar position."""

    # atom-one-dark
    theme: str = Field(default="nightfly")
    """The name of the theme to use."""
