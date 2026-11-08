"""Conservative spelling alignment for spoken-content comparison."""
import re
from num2words import num2words

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

CLOCKS = {num2words(h) + ' ' + ('oh ' if m < 10 else '') + num2words(m): (h,m)
          for h in range(1,13) for m in range(1,60)}
CLOCK_PATTERN = re.compile(r'\b(?:' + '|'.join(re.escape(x) for x in sorted(CLOCKS,key=len,reverse=True)) + r')\b',re.I)

def align_clock_sequences(expected, heard):
    """Align numeric time formatting only when both hour and minute match."""
    for match in CLOCK_PATTERN.finditer(expected):
        hour, minute = CLOCKS[match[0].lower()]
        pattern = r'(?<![\d$£])' + str(hour) + r'[:.]?' + f'{minute:02}' + r'(?!\d)'
        heard = re.sub(pattern, lambda _: match[0], heard)
    return heard

YEARS = {num2words(n,to='year'): str(n) for n in range(1800,2100)}
YEAR_PATTERN = re.compile(r'\b(?:' + '|'.join(re.escape(x) for x in sorted(YEARS,key=len,reverse=True)) + r')\b',re.I)

def normalize_year_words(text):
    return YEAR_PATTERN.sub(lambda m: YEARS[m[0].lower()], text)
