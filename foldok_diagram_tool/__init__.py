"""Foldok diagram tool — the call path behind the diagram capability.

    from foldok_diagram_tool import TOOL_SCHEMA, run
    result = run(spec)          # -> SVG figure for the document

Exists because fixing the capability manifest lets the assistant claim it can
draw; this makes the claim true.
"""

from .symbols import module_symbol, register
from .tool import TOOL_SCHEMA, DiagramToolError, ToolResult, build, run, vocabulary

__all__ = [
    "DiagramToolError", "TOOL_SCHEMA", "ToolResult", "build", "module_symbol",
    "register", "run", "vocabulary",
]

__version__ = "0.84.0"
