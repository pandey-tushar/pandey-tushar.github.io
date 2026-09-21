"""Output directory for schedules and models.

Override with the CPRI_OUT environment variable; default is ./out next to
these sources.
"""
import os

def out_path(name):
    d = os.environ.get('CPRI_OUT')
    if not d:
        d = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, name)
