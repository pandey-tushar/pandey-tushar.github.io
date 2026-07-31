# Promote built output from _studio up into the site root.
#
# Source and site now live in one repo. The source sits in _studio, which Jekyll
# never copies into the built site, so nothing in there is reachable by URL.
# This script only copies; it never deletes, and it never commits or pushes, so
# the diff can be read before anything leaves the machine.
#
#   powershell -File _studio/tools/deploy.ps1

$ErrorActionPreference = 'Stop'
$studio = Split-Path -Parent $PSScriptRoot   # ...\_studio
$repo   = Split-Path -Parent $studio         # the site root

function Copy-Tree($src, $dst) {
  if (-not (Test-Path $src)) { throw "missing source: $src" }
  New-Item -ItemType Directory -Force -Path $dst | Out-Null
  Copy-Item "$src\*" -Destination $dst -Recurse -Force
}

# 1. the site at the root.
# books.html used to be promoted from prototypes\books-hub. That prototype has
# been deleted, so the copy at the root is now the only one and is edited in
# place; it is checked below like everything else the site links to.
Copy-Item "$studio\prototypes\site-full\index.html" "$repo\index.html" -Force

# 2. the two published editions, each in its own directory
Copy-Tree "$studio\apps\unpolarized\dist" "$repo\life"
Copy-Tree "$studio\apps\illustrated\dist" "$repo\illustrated"

# 3. the Hindi edition is deliberately unpublished; fail loudly if it appears
if (Test-Path "$repo\hindi") { throw 'the Hindi edition must not be deployed' }

# 4. everything the site links to must survive
$must = @('CNAME','index.html','books.html','cv.html','qubit-dialogues.html',
          'og-home.png','og-book.png',
          'qubit-dialogues.pdf','an-unpolarized-life.pdf','illustrated.pdf',
          'Tushar_Pandey_Resume_AI.pdf','Tushar_Pandey_Resume_Quantum.pdf')
$missing = $must | Where-Object { -not (Test-Path (Join-Path $repo $_)) }
if ($missing) { throw "deploy would break existing links: $($missing -join ', ')" }

Write-Output 'staged. review with git status and git diff, then commit and push.'
