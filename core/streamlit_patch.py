"""
TypedDict compatibility patch for Python 3.14.

Streamlit≥1.51 uses typing.TypedDict with the keyword argument ``closed``,
but Python 3.14.0's stdlib implementation doesn't yet accept that keyword.
This module simply re-exports ``typing_extensions.TypedDict`` as
``typing.TypedDict`` so every dependency (Streamlit, SQLAlchemy, etc.)
gets the modern behavior without source edits.
"""

from __future__ import annotations

import typing

try:
    import typing_extensions
except ImportError:  # pragma: no cover
    typing_extensions = None  # type: ignore


def patch_typeddict() -> None:
    """Replace typing.TypedDict with typing_extensions backport where available."""
    if typing_extensions is None:
        return

    stdlib_td = typing.TypedDict
    backport_td = typing_extensions.TypedDict  # type: ignore[attr-defined]
    if stdlib_td is backport_td:
        return

    typing.TypedDict = backport_td  # type: ignore[assignment]


patch_typeddict()

