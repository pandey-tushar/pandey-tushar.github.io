/* The OG card template. One function, called once per route that needs a card,
   so a new note gets a share image without anyone opening a design tool.
   Colours and type come from @qubit/tokens. */

import { site, type } from '@qubit/tokens';

const esc = (s: string): string =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

/** greedy wrap on a rough character budget for the display size */
function wrap(s: string, per: number, max: number): string[] {
  const out: string[] = []; let line = '';
  for (const w of s.split(/\s+/)) {
    if (line && (line + ' ' + w).length > per) { out.push(line); line = w; } else line = line ? line + ' ' + w : w;
    if (out.length === max) break;
  }
  if (line && out.length < max) out.push(line);
  return out;
}

export interface Card { kicker: string; title: string; footer: string }

export function ogCard(c: Card): string {
  const lines = wrap(c.title, 26, 4);
  const size = lines.length > 3 ? 62 : lines.length > 2 ? 72 : 84;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
<defs>
<linearGradient id="g" x1="0" y1="0" x2="1" y2="0">
<stop offset="0" stop-color="${site.cyan}"/><stop offset=".58" stop-color="${site.violet}"/><stop offset="1" stop-color="${site.magenta}"/>
</linearGradient>
<radialGradient id="n" cx="78%" cy="18%" r="70%">
<stop offset="0" stop-color="${site.violet}" stop-opacity=".38"/><stop offset="1" stop-color="${site.violet}" stop-opacity="0"/>
</radialGradient>
</defs>
<rect width="1200" height="630" fill="${site.ink}"/>
<rect width="1200" height="630" fill="url(#n)"/>
<rect width="1200" height="6" fill="url(#g)"/>
<text x="84" y="132" font-family=${JSON.stringify(type.siteMono)} font-size="24" letter-spacing="5" fill="${site.cyan}">${esc(c.kicker.toUpperCase())}</text>
<g font-family=${JSON.stringify(type.siteSerif)} font-size="${size}" fill="${site.text}">
${lines.map((l, i) => `<text x="84" y="${250 + i * (size + 14)}">${esc(l)}</text>`).join('\n')}
</g>
<text x="84" y="556" font-family=${JSON.stringify(type.siteMono)} font-size="24" fill="${site.text2}">${esc(c.footer)}</text>
<rect x="84" y="580" width="140" height="3" fill="url(#g)"/>
</svg>
`;
}
