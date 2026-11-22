"""The notation rules of stateHTML in qec-in-practice/js/patch.js, for text
written into the page at build time. Keep the two in step. Also the course
order, read from qec-in-practice/data/course.json."""
import io, json, re

SITE = 'https://pandey-tushar.com/qec-in-practice/'


def course(qec):
    """The course pages in order: page, title, url, part, card, and lesson (1..4) or picture."""
    load = lambda name: json.loads(io.open(qec / 'data' / name, encoding='utf-8').read())
    lessons = load('lessons.json')
    out = []
    for part in load('course.json')['parts']:
        for e in part['pages']:
            e = dict(e, part=part['name'], url=SITE + e['page'])
            if 'lesson' in e:
                e['title'] = f"Lesson {e['lesson']}: {lessons[str(e['lesson'])]['title']}"
            out.append(e)
    return out


def state_html(s):
    s = s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    s = re.sub(r'\|([^|&\s]*?)&gt;', r'|\1&#10217;', s)
    s = re.sub(r'_L\b', '&#8288;<sub>L</sub>', s)  # a word joiner: the L never wraps away from its letter
    return s.replace('sqrt2', '&radic;2')


def phase_label(name):
    """The page name of a phase, as phaseLabel in qec-in-practice/js/strip.js: the readout rotation is H on the patch."""
    return re.sub(r'^readout rotation (\S+) \(\w\)$', r'H on \1', name)


def plain(s):
    """The same text for attributes: kets closed with the real character, no markup."""
    s = re.sub(r'\|([^|&\s]*?)>', r'|\1⟩', s)
    return s.replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
