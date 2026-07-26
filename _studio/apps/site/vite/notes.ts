/* Markdown to Note, at build time. A note is one file in content/notes; the
   section, the feed, the sitemap and the card all come from that file.

   The subset is deliberate: headings, paragraphs, lists, quotes, fenced code,
   links, bold, italic, inline code. Anything a short post needs and nothing
   that would justify pulling a parser into the bundle. */

import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import type { Note } from '../src/content/types.ts';

const esc = (s: string): string =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

function inline(s: string): string {
  return esc(s)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, '<a href="$2">$1</a>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>');
}

function markdown(src: string): string {
  const out: string[] = [];
  const lines = src.split(/\r?\n/);
  let list: string[] | null = null;
  const flush = (): void => {
    if (list) { out.push('<ul>' + list.map((l) => '<li>' + inline(l) + '</li>').join('') + '</ul>'); list = null; }
  };
  for (let i = 0; i < lines.length; i++) {
    const l = lines[i];
    if (l.startsWith('```')) {
      flush();
      const body: string[] = [];
      while (++i < lines.length && !lines[i].startsWith('```')) body.push(lines[i]);
      out.push('<pre><code>' + esc(body.join('\n')) + '</code></pre>');
      continue;
    }
    const h = /^(#{2,4})\s+(.*)$/.exec(l);
    if (h) { flush(); out.push('<h' + h[1].length + '>' + inline(h[2]) + '</h' + h[1].length + '>'); continue; }
    if (/^[-*]\s+/.test(l)) { (list ??= []).push(l.replace(/^[-*]\s+/, '')); continue; }
    if (/^>\s?/.test(l)) { flush(); out.push('<blockquote><p>' + inline(l.replace(/^>\s?/, '')) + '</p></blockquote>'); continue; }
    if (!l.trim()) { flush(); continue; }
    flush();
    out.push('<p>' + inline(l) + '</p>');
  }
  flush();
  return out.join('\n');
}

/** `--- key: value ---` at the top of the file, nothing cleverer */
function frontmatter(src: string): [Record<string, string>, string] {
  const m = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?/.exec(src);
  if (!m) return [{}, src];
  const meta: Record<string, string> = {};
  for (const line of m[1].split(/\r?\n/)) {
    const kv = /^([a-z]+):\s*(.*)$/.exec(line.trim());
    if (kv) meta[kv[1]] = kv[2].replace(/^["']|["']$/g, '');
  }
  return [meta, src.slice(m[0].length)];
}

export function readNotes(dir: string): Note[] {
  if (!existsSync(dir)) return [];
  const notes: Note[] = [];
  /* a leading underscore is how this folder keeps its own notes to itself */
  for (const file of readdirSync(dir).filter((f) => f.endsWith('.md') && !f.startsWith('_'))) {
    const [meta, rest] = frontmatter(readFileSync(join(dir, file), 'utf8'));
    if (meta.draft === 'true') continue;
    if (!meta.title || !meta.date) throw new Error('notes: ' + file + ' needs a title and a date');
    const words = rest.trim().split(/\s+/).length;
    notes.push({
      slug: meta.slug || file.replace(/\.md$/, ''),
      title: meta.title,
      date: meta.date,
      summary: meta.summary || '',
      html: markdown(rest),
      minutes: Math.max(1, Math.round(words / 220)),
    });
  }
  /* newest first, which is also the order the feed wants */
  return notes.sort((a, b) => (a.date < b.date ? 1 : -1));
}
