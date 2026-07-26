/* Every piece of the site is one of these. Adding a paper, a talk, a project or
   a link is adding an object to an array in src/content, never editing markup. */

export interface NavLink {
  label: string;
  href: string;
  /** external links get target/rel; internal ones must not */
  external?: boolean;
}

export interface Cta {
  label: string;
  href: string;
  primary?: boolean;
  external?: boolean;
}

export interface MetaFact {
  /** the bold lead-in, e.g. "Now" */
  key: string;
  value: string;
}

export interface Hero {
  eyebrow: string;
  /** rendered as two lines; the second is the gradient italic */
  name: [string, string];
  lede: string;
  whisper: { text: string; strong: string };
  facts: MetaFact[];
  ctas: Cta[];
  hint: string;
  scrollCue: string;
}

export interface Chapter {
  id: string;
  /** the outlined numeral behind the box */
  ghost: string;
  /** the question the chapter answers */
  eyebrow: string;
  /** heading, split so the second half takes the gradient italic */
  heading: [string, string];
  /** allows <b> only; written as data, not markup */
  lede: string;
  more?: Cta;
  /** which side of the viewport the box sits on */
  side?: 'left' | 'right';
  /** the line the scene caption shows while this chapter is in view */
  act?: string;
  /** how far into the section the caption switches, 0 to 1 */
  actAt?: number;
}

export interface ContactLink {
  label: string;
  text: string;
  href: string;
  external?: boolean;
}

/** A paper, a talk or a project. One object, one line of provenance. */
export interface Entry {
  title: string;
  venue: string;
  year: number;
  href?: string;
  blurb?: string;
  tags?: string[];
}

/** A compiled markdown note. Produced by the build, never written by hand. */
export interface Note {
  slug: string;
  title: string;
  date: string;
  summary: string;
  html: string;
  minutes: number;
}

export interface PageMeta {
  title: string;
  description: string;
  canonical: string;
  ogTitle: string;
  ogDescription: string;
  ogImage: string;
}
