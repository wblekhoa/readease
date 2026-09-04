"""Re-export so this package does not reach back up into its parent's parent.

`SynthesisSettings` belongs to the local model, and an external engine has to
accept one to satisfy the same protocol. Importing it through one name here
keeps that dependency visible in a single line.
"""

from vieneu_reader.speech.contracts import SynthesisSettings

__all__ = ["SynthesisSettings"]
