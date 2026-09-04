"""Keep an API key out of every string that could be read by a person.

The owner's one hard condition for this feature: the key stays local. That is
not only about where it is STORED. A key leaks by being quoted back - a 401
body that echoes the Authorization header, a stack trace that formats the
request, a log line written while debugging - and this app now shows the
engine's own words on screen when something fails (docs/readease-hig.md
§3.11, §3.14). So the words that reach a person are filtered at the seam
where they are made, not where they are displayed.
"""

from __future__ import annotations

MARKER = "***"

# Below this, a "secret" is more likely to be a word that appears in ordinary
# prose than an actual credential - redacting "" or "sk" would blank out text
# for no gain.
_MINIMUM_SECRET_LENGTH = 8


def redacted(text: object, *secrets: str | None) -> str:
    """`text` with every secret replaced, in the order given.

    Takes `object` because the usual caller is `str(error)` on something that
    may not be a string at all.
    """

    result = str(text)
    for secret in secrets:
        if not secret:
            continue
        secret = secret.strip()
        if len(secret) < _MINIMUM_SECRET_LENGTH:
            continue
        result = result.replace(secret, MARKER)
    return result
