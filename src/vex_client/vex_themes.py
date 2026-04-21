from pydantic import BaseModel, Field
from rich.style import Style
from textual.color import Color
from textual.theme import Theme as TextualTheme
from textual.widgets.text_area import TextAreaTheme

"""
This theme code pattern was inspired by the Posting project.
Reference: https://github.com/darrenburns/posting/blob/main/src/posting/themes.py
"""


class VexTextAreaTheme(BaseModel):
    """Theme for the text area HTTP syntax highlighting and cursor."""

    cursor: str | None = Field(default=None)
    """The style to apply to the cursor."""

    cursor_line: str | None = Field(default=None)
    """The style to apply to the line the cursor is on."""

    selection: str | None = Field(default=None)
    """The style to apply to the selected text."""

    method: str | None = Field(default="#8c0260")
    """The style to apply to the HTTP method."""

    version: str | None = Field(default="#019006")
    """The style to apply to the HTTP version."""

    status: str | None = Field(default="#0E98F3")
    """The style to apply to the HTTP status code."""

    header: str | None = Field(default="#D7D012")
    """The style to apply to the HTTP headers."""

    value: str | None = Field(default="#CC4009")
    """The style to apply to the HTTP header values."""


class MethodStyles(BaseModel):
    """The style to apply to HTTP methods in the datatable."""

    get: str | None = Field(default="#0ea5e9")
    post: str | None = Field(default="#22c55e")
    put: str | None = Field(default="#f59e0b")
    delete: str | None = Field(default="#ef4444")
    patch: str | None = Field(default="#14b8a6")
    options: str | None = Field(default="#8b5cf6")
    head: str | None = Field(default="#d946ef")


class FileStyle(BaseModel):
    """The style to apply to HTTP methods in the datatable."""

    html: str | None = Field(default="#22c55e")
    css: str | None = Field(default="#ef4444")
    js: str | None = Field(default="#f5da0b")
    ts: str | None = Field(default="#0ea5e9")  # typescript
    php: str | None = Field(default="#00537a")
    json_ext: str | None = Field(default="#d58317")
    pdf: str | None = Field(default="#ff4646")
    png: str | None = Field(default="#14b8a6")
    jpg: str | None = Field(default="#8b5cf6")
    svg: str | None = Field(default="#d946ef")


class VexTheme(BaseModel):
    name: str = Field(exclude=True)
    primary: str
    secondary: str | None = None
    background: str | None = None
    # foreground: str | None = None -> automatically generated?
    surface: str | None = None
    panel: str | None = None
    warning: str | None = None
    error: str | None = None
    success: str | None = None
    accent: str | None = None
    dark: bool = True

    text_area: VexTextAreaTheme = Field(default_factory=VexTextAreaTheme)
    """Styling to apply to TextAreas."""

    method: MethodStyles | None = Field(default_factory=MethodStyles)
    """The style to apply to HTTP methods in DataTable."""

    file_extension: FileStyle | None = Field(default_factory=FileStyle)
    """The style to apply to HTTP file extensions in DataTable."""

    def to_textual_theme(self) -> TextualTheme:
        """Convert this theme to a Textual Theme.

        Returns:
            A Textual Theme instance with all properties and variables set.
        """
        theme_data = {
            "name": self.name,
            "dark": self.dark,
        }
        colors = {
            "primary": self.primary,
            "secondary": self.secondary,
            "background": self.background,
            # "foreground": self.foreground,
            "surface": self.surface,
            "panel": self.panel,
            "warning": self.warning,
            "error": self.error,
            "success": self.success,
            "accent": self.accent,
        }

        # Validate the colors before converting to a Textual theme.
        for color in colors.values():
            if color is not None:
                Color.parse(color)

        theme_data.update({k: v for k, v in colors.items() if v is not None})

        variables: dict[str, str] = {}

        if self.method:
            if self.method.get:
                variables["method-get"] = self.method.get
            if self.method.post:
                variables["method-post"] = self.method.post
            if self.method.put:
                variables["method-put"] = self.method.put
            if self.method.delete:
                variables["method-delete"] = self.method.delete
            if self.method.patch:
                variables["method-patch"] = self.method.patch
            if self.method.options:
                variables["method-options"] = self.method.options
            if self.method.head:
                variables["method-head"] = self.method.head

        if self.file_extension:
            if self.file_extension.html:
                variables["ext-html"] = self.file_extension.html
            if self.file_extension.css:
                variables["ext-css"] = self.file_extension.css
            if self.file_extension.js:
                variables["ext-js"] = self.file_extension.js
            if self.file_extension.ts:
                variables["ext-ts"] = self.file_extension.ts
            if self.file_extension.php:
                variables["ext-php"] = self.file_extension.php
            if self.file_extension.json_ext:
                variables["ext-json"] = self.file_extension.json_ext
            if self.file_extension.pdf:
                variables["ext-pdf"] = self.file_extension.pdf
            if self.file_extension.png:
                variables["ext-png"] = self.file_extension.png
            if self.file_extension.jpg:
                variables["ext-jpg"] = self.file_extension.jpg
            if self.file_extension.svg:
                variables["ext-svg"] = self.file_extension.svg
        
        if self.success:
            variables["cookies-yes"] = self.success
            variables["status-success"] = self.success
        if self.warning:
            variables["status-redirect"] = self.warning
        if self.error:
            variables["cookies-no"] = self.error
            variables["status-error"] = self.error

        theme_data = {k: v for k, v in theme_data.items() if v is not None}
        theme_data["variables"] = {k: v for k, v in variables.items() if v is not None}

        return TextualTheme(**theme_data)

    # in VexTheme
    def to_text_area_theme(self) -> TextAreaTheme:
        """Build a TextAreaTheme for HTTP syntax highlighting from this theme's colors."""
        ta = self.text_area

        # Fall back through: text_area field → method colors → sensible defaults
        syntax_styles: dict[str, Style] = {
            "method": Style.parse(ta.method or self.accent or self.primary),
            "version": Style.parse(ta.version or self.secondary or self.primary),
            "status": Style.parse(ta.status or self.success or self.primary),
            "header": Style.parse(ta.header or self.primary),
            "value": Style.parse(ta.value or self.secondary or "default"),
        }

        return TextAreaTheme(
            name=f"{self.name}-http-theme",
            syntax_styles=syntax_styles,
            cursor_style=Style.parse(ta.cursor) if ta.cursor else None,
            cursor_line_style=Style.parse(ta.cursor_line) if ta.cursor_line else None,
            selection_style=Style.parse(ta.selection) if ta.selection else None,
        )
