"""The notation rules of stateHTML in qec-in-practice/js/patch.js, for text
written into the page at build time. Keep the two in step."""
import re


def state_html(s):
    s = s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    s = re.sub(r'\|([^|&\s]*?)&gt;', r'|\1&#10217;', s)
    s = re.sub(r'_L\b', '&#8203;<sub>L</sub>', s)
    return s.replace('sqrt2', '&radic;2')


def plain(s):
    """The same text for attributes: kets closed with the real character, no markup."""
    s = re.sub(r'\|([^|&\s]*?)>', r'|\1⟩', s)
    return s.replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
