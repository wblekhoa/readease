"""Paid voices from an outside API, on the reader's own key.

The local VieNeu model is the product; these are an option for someone who
wants a particular voice badly enough to pay a provider by the character. The
rules that make it safe to offer are in this package rather than in each
provider: the key never leaves this machine, never reaches the webview, and
never appears in an error message.
"""

from .secrets import redacted

__all__ = ["redacted"]
