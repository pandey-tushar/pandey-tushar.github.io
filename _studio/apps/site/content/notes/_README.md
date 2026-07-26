# Notes

One file per note. The build compiles every `.md` in this folder into the
Writing section, a page at `/notes/<slug>/`, an item in `/feed.xml`, an entry in
`/sitemap.xml`, and a share card at `/og/notes-<slug>.png`. No markup to edit.

```md
---
title: What a syndrome actually measures
date: 2026-07-19
summary: One paragraph, used by the section, the feed and the card.
slug: what-a-syndrome-measures
draft: false
---

Body starts here. Headings from `##` down, lists, quotes, fenced code,
links, **bold**, *italic*, `code`.
```

`title` and `date` are required. `slug` defaults to the filename. `draft: true`
keeps a file out of the build entirely.
