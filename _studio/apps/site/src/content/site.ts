/* The site, as data. Every string a visitor reads lives here.
   Copy is carried over from the shipped index.html unchanged; the only new
   strings are the writing section and the theme chip, which are new content. */

import type { Chapter, ContactLink, Hero, NavLink, PageMeta } from './types.ts';

export const ORIGIN = 'https://pandey-tushar.com';

/* Kept byte-identical to the live page. og-home.png is a real file at the
   deploy root and stays the home card; people have shared that URL. */
export const meta: PageMeta = {
  title: 'Tushar Pandey · Quantum × AI',
  description:
    'Dr. Tushar Pandey. Quantum error correction, machine intelligence, and systems that ship. Trained on proofs; builds the improbable.',
  canonical: ORIGIN + '/',
  ogTitle: 'Tushar Pandey',
  ogDescription: "Error, corrected. Reasoning that grows. Let's build the improbable.",
  ogImage: ORIGIN + '/og-home.png',
};

export const GA4_ID = 'G-DVPGC1C44Z';

export const brand = { first: 'Tushar', last: 'Pandey' };

export const nav: NavLink[] = [
  { label: 'Quantum', href: '#quantum' },
  { label: 'AI', href: '#ai' },
  { label: 'Research', href: 'https://sites.google.com/view/tusharpandey', external: true },
  { label: 'Book', href: 'qubit-dialogues.html' },
  { label: 'CV', href: 'cv.html' },
  { label: 'Contact', href: '#contact' },
];

export const intro = {
  name: 'Tushar Pandey',
  /* the first six letters are plain, the last six take the gradient */
  plain: 6,
  sub: 'Quantum · Intelligence · Systems',
};

export const hero: Hero = {
  eyebrow: 'Ph.D. Mathematics · Quantum × AI',
  name: ['Tushar', 'Pandey'],
  lede: 'I turn ideas into systems that ship.',
  whisper: { text: 'Trained on proofs:', strong: 'one conjecture, solved alone, 2023.' },
  facts: [
    { key: 'Now', value: 'Senior Software Engineer @ DataRobot' },
    { key: 'Based in', value: 'Dallas, TX' },
  ],
  ctas: [
    { label: 'Curriculum Vitae →', href: 'cv.html', primary: true },
    { label: 'GitHub', href: 'https://github.com/pandey-tushar', external: true },
    { label: 'Email', href: 'mailto:wtatushar@gmail.com' },
  ],
  hint: 'drag to spin · click to pulse',
  scrollCue: 'scroll',
};

export const chapters: Chapter[] = [
  {
    id: 'quantum',
    ghost: '01',
    side: 'right',
    eyebrow: 'Can you compute with broken parts?',
    heading: ['Error, ', 'corrected.'],
    lede:
      'Two summers at Oak Ridge building <b>fault tolerance for a non-abelian code</b>; ' +
      'lead author, APL Quantum, 2025. The newest work reaches the qLDPC frontier.',
    more: { label: 'the record →', href: 'https://sites.google.com/view/tusharpandey', external: true },
    act: "some questions don't have edges",
    actAt: 0.3,
  },
  {
    id: 'ai',
    ghost: '02',
    side: 'left',
    eyebrow: 'Can a machine think harder, mid-thought?',
    heading: ['Reasoning that ', 'grows.'],
    lede:
      '<b>AGoT</b> grows chains, trees and graphs as it runs: 19 citations in year one, ' +
      'running in production.',
    more: { label: 'the code, open source →', href: 'https://github.com/AgnostiqHQ/multi-agent-llm', external: true },
    act: 'then it learns to think',
    actAt: 0.45,
  },
];

/* New section. Notes are compiled from apps/site/content/notes/*.md at build
   time; with none written the section says so rather than pretending. */
export const writing = {
  id: 'writing',
  ghost: '03',
  eyebrow: 'Where does a thought go before it is a paper?',
  heading: ['Notes, ', 'in the open.'] as [string, string],
  lede: 'Short pieces on error correction, inference, and the arithmetic underneath both.',
  empty: 'Nothing published yet. The first note lands here and in the feed on the same day.',
  feed: { label: 'RSS feed →', href: '/feed.xml' },
};

export const names: string[] = [
  'Oak Ridge National Laboratory',
  'APL Quantum',
  'IBM Quantum',
  'MIT',
  'Texas A&M',
  'IIT Kanpur',
];

export const contact = {
  id: 'contact',
  eyebrow: 'What’s left to prove?',
  heading: ["Let’s build the ", 'improbable.'] as [string, string],
  receipt:
    'Multi-tenant LLM inference at DataRobot: deploys <b>30 to 40 percent faster</b>, ' +
    'throughput <b>tripled</b>. Three first-place titles since 2024.',
  act: 'and decides to build',
  actAt: 0.55,
};

export const contactLinks: ContactLink[] = [
  { label: 'Email', text: 'wtatushar [at] gmail [dot] com', href: 'mailto:wtatushar@gmail.com' },
  { label: 'LinkedIn', text: 'linkedin.com/in/tpmath', href: 'https://www.linkedin.com/in/tpmath/', external: true },
  { label: 'GitHub', text: 'github.com/pandey-tushar', href: 'https://github.com/pandey-tushar', external: true },
  { label: 'Scholar', text: 'Google Scholar →', href: 'https://scholar.google.com/citations?user=_ivaRgIAAAAJ', external: true },
  { label: 'CV', text: 'Curriculum Vitae →', href: 'cv.html' },
];

export const footer = { colophon: 'One canvas · three thousand qubits · zero page builders.' };

export const theme = { toLight: 'paper', toDark: 'night' };

/* Routes the sitemap advertises. Only what is already public: the three new
   book editions stay off this list until they are published deliberately. */
export const routes = ['/', '/cv.html', '/qubit-dialogues.html'];

export const fonts =
  'https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;' +
  '0,9..144,600;1,9..144,400;1,9..144,500&family=Inter:wght@400;500;600&' +
  'family=JetBrains+Mono:wght@400;500&display=swap';
