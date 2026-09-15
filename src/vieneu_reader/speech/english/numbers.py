"""English numbers as words, for the voice.

`num2words` did this job in the library this G2P was taken from; it is LGPL
and is not shipped. What the lexicon's number reader actually asks for is
small: a cardinal, an ordinal, a year, and a decimal. The wording follows
what `num2words` produced for those, minus the "and" - the caller strips it
anyway unless the text asked for it.
"""

from __future__ import annotations

_ONES = (
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen",
)
_TENS = (
    "", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
    "eighty", "ninety",
)
_SCALES = (
    (10**15, "quadrillion"),
    (10**12, "trillion"),
    (10**9, "billion"),
    (10**6, "million"),
    (10**3, "thousand"),
)
_ORDINAL_IRREGULAR = {
    "one": "first", "two": "second", "three": "third", "five": "fifth",
    "eight": "eighth", "nine": "ninth", "twelve": "twelfth",
}


def _below_thousand(n: int) -> str:
    words: list[str] = []
    if n >= 100:
        words.append(f"{_ONES[n // 100]} hundred")
        n %= 100
    if n >= 20:
        words.append(_TENS[n // 10] + (f"-{_ONES[n % 10]}" if n % 10 else ""))
    elif n or not words:
        words.append(_ONES[n])
    return " ".join(words)


def cardinal(n: int) -> str:
    """0 → "zero", 1975 → "one thousand nine hundred seventy-five"."""

    if n < 0:
        return f"minus {cardinal(-n)}"
    if n < 1000:
        return _below_thousand(n)
    words: list[str] = []
    for scale, name in _SCALES:
        if n >= scale:
            words.append(f"{_below_thousand(n // scale)} {name}")
            n %= scale
    if n:
        words.append(_below_thousand(n))
    return " ".join(words)


def ordinal(n: int) -> str:
    """1 → "first", 22 → "twenty-second", 100 → "hundredth"."""

    words = cardinal(n)
    head, _, last = words.rpartition(" ")
    stem, dash, unit = last.rpartition("-")
    tail = unit if dash else last
    if tail in _ORDINAL_IRREGULAR:
        tail = _ORDINAL_IRREGULAR[tail]
    elif tail.endswith("y"):
        tail = tail[:-1] + "ieth"
    else:
        tail = tail + "th"
    last = f"{stem}-{tail}" if dash else tail
    return f"{head} {last}" if head else last


def year(n: int) -> str:
    """The way a year is read: 1975 → "nineteen seventy-five", 2005 →
    "two thousand five", 1905 → "nineteen oh five", 2000 → "two thousand"."""

    if n < 1000 or n > 9999:
        return cardinal(n)
    high, low = divmod(n, 100)
    if low == 0:
        return f"{cardinal(high)} hundred" if high % 10 else cardinal(n)
    if low < 10:
        # 2005, 3001: said as the full number, "two thousand five"; 1905 is
        # "nineteen oh five".
        return cardinal(n) if high % 10 == 0 else f"{_below_thousand(high)} oh {_ONES[low]}"
    return f"{_below_thousand(high)} {_below_thousand(low)}"


def decimal(text: str) -> str:
    """"3.14" → "three point one four"; the digits after the point are
    read one by one, which is how a decimal is said aloud."""

    whole, _, fraction = text.partition(".")
    words = cardinal(int(whole)) if whole else ""
    # "2.0" is "two" and "3.50" is "three point five": a trailing zero is
    # written, not said.
    fraction = fraction.rstrip("0")
    if fraction:
        digits = " ".join(_ONES[int(digit)] for digit in fraction)
        words = f"{words} point {digits}" if words else f"point {digits}"
    return words
