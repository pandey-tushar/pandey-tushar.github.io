# Tushar Pandey — personal site

Two self-contained pages (HTML + CSS + JS, no build step, no dependencies):

- `index.html` — portfolio (WebGL hero, research, projects, teaching, conferences, service)
- `cv.html` — academic CV (dark on screen, prints to a clean PDF via the in-page button)

## Preview locally
Double-click `index.html`, or:
```
python3 -m http.server 8000
# open http://localhost:8000
```

## Deploy to GitHub Pages
This repo is named `pandey-tushar.github.io`, so it publishes as a **user site** at
`https://pandey-tushar.github.io`.

1. Push `index.html`, `cv.html`, and this `README.md` to the repo root on the `main` branch.
2. Repo → Settings → Pages → Source: `main` / `/ (root)` → Save.
3. Live in ~1 min at `https://pandey-tushar.github.io`. The CV is at `/cv.html`.

## Custom domain (optional)
Settings → Pages → Custom domain, then point a CNAME at GitHub Pages. A `CNAME`
file is created automatically.

## Editing content
All content lives in the `<script>` block near the bottom of each file:
`papers`, `talks`, `projects`, `surveys`, `teaching`, `conferences`, `leadership`,
`prizes` (index), plus `education`, `employment`, `interests`, `skills` (cv).
Add an entry to the relevant array and it renders automatically. The two files keep
their own copies of the shared arrays.
