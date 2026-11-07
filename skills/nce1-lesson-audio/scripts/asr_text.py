"""Conservative spelling alignment for spoken-content comparison."""
import re

DIGITS = dict(zip('zero one two three four five six seven eight nine'.split(), '0123456789'))
WORD = '(?:' + '|'.join(DIGITS) + ')'
SEQUENCE = re.compile(r'\b' + WORD + r'(?:[,\s]+' + WORD + r'){2,}\b', re.I)

def align_digit_sequences(expected, heard):
    """Expand only numerals that exactly match an explicit spoken digit sequence."""
    for match in SEQUENCE.finditer(expected):
        digits = [DIGITS[w.lower()] for w in re.findall(r'[a-z]+', match[0], re.I)]
        pattern = r'(?<!\d)' + r'[\s,-]*'.join(digits) + r'(?!\d)'
        heard = re.sub(pattern, lambda _: match[0], heard)
    return heard
