from tree_sitter_language_pack import (
    get_language,
    DownloadError,
    has_language,
    init,
)

from vex_cli.locations import vex_tree_sitter_directory


def init_http() -> bool:
    try:
        init(
            {
                "config_dir": str(vex_tree_sitter_directory() / "http-lang"),
                "languages": ["http"],
            }
        )
        return has_language("http")
    except DownloadError:
        return False


def get_http_lang():
    return get_language("http")  # type: ignore


def get_highlight_query() -> str:
    return """
    (method) @method
    (http_version) @version
    (header name: (_) @header)
    (header value: (_) @value)
    (status_code) @status
    (status_text) @status
    """
