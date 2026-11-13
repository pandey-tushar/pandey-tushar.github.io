"""Rebuild the two resume PDFs at the repo root from the Word sources in this folder.

Needs Microsoft Word on Windows (driven through PowerShell COM) and pypdf.
Usage: python _studio/resume/build.py
"""
import os, subprocess, tempfile
from pypdf import PdfReader, PdfWriter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
JOBS = [('Tushar_AI.docx', 'Tushar_Pandey_Resume_AI.pdf', 'Tushar Pandey, PhD - Resume (AI)'),
        ('Tushar_Quantum.docx', 'Tushar_Pandey_Resume_Quantum.pdf', 'Tushar Pandey, PhD - Resume (Quantum)')]

PS = r'''
$w = New-Object -ComObject Word.Application
$w.Visible = $false
try {
  foreach ($pair in $args) {
    $src, $dst = $pair -split '\|'
    $d = $w.Documents.Open($src, $false, $true)
    $d.ExportAsFixedFormat($dst, 17, $false, 0, 0, 0, 0, 0, $true, $true, 0, $true, $true, $false)
    $d.Close($false)
  }
} finally { $w.Quit() }
'''


def main():
    tmp = tempfile.mkdtemp()
    pairs = [f'{os.path.join(HERE, s)}|{os.path.join(tmp, o)}' for s, o, _ in JOBS]
    script = os.path.join(tmp, 'export.ps1')
    with open(script, 'w') as f:
        f.write(PS)
    subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', script, *pairs], check=True)
    for _, out, title in JOBS:
        r = PdfReader(os.path.join(tmp, out))
        w = PdfWriter(clone_from=r)
        w.add_metadata({'/Title': title, '/Author': 'Tushar Pandey', '/Creator': 'Microsoft Word',
                        '/Producer': 'Microsoft Word'})
        with open(os.path.join(ROOT, out), 'wb') as f:
            w.write(f)
        print('wrote', out, len(r.pages), 'page(s)')


if __name__ == '__main__':
    main()
