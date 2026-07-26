/* The same tokens as tokens.css, readable from JS.
   Canvas and WebGL cannot resolve CSS custom properties, so scenes take their
   colours from here. Keep both files in step: tokens.css is the source of
   truth for layout, this file is the source of truth for drawing. */

export type ThemeName = 'light' | 'dark';

export interface Palette {
  void: string;
  void2: string;
  ink: string;
  cyan: string;
  violet: string;
  gold: string;
  rose: string;
  dim: string;
  line: string;
}

export const palette: Record<ThemeName, Palette> = {
  light: {
    void: '#f5efe2',
    void2: '#ece3d1',
    ink: '#241f18',
    cyan: '#0d6e86',
    violet: '#6d28d9',
    gold: '#946213',
    rose: '#b32a5e',
    dim: '#6b6153',
    line: 'rgba(148, 98, 19, .30)',
  },
  dark: {
    void: '#05060f',
    void2: '#0a0c1c',
    ink: '#e8e6ff',
    cyan: '#5ef4ff',
    violet: '#b07bff',
    gold: '#f4d58d',
    rose: '#ff6ea9',
    dim: '#8a88b8',
    line: 'rgba(244, 213, 141, .22)',
  },
};

/* Scenes keep their night palette in both themes (a dark astronomy plate on a
   paper page), so these are the dark hues as numbers for Three.js. */
export const sceneColors = {
  cyan: 0x5ef4ff,
  violet: 0xb07bff,
  gold: 0xf4d58d,
  rose: 0xff6ea9,
  void: 0x05060f,
} as const;

export const site = {
  ink: '#070a14',
  ink2: '#0c1020',
  surface: '#121829',
  surface2: '#171e33',
  line: 'rgba(150, 170, 210, .14)',
  lineStrong: 'rgba(150, 170, 210, .28)',
  text: '#e8ecf6',
  text2: '#9aa4c0',
  text3: '#69728e',
  cyan: '#52d6e6',
  violet: '#9b7bff',
  magenta: '#f06ab0',
} as const;

export const type = {
  serif: '"Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif',
  mono: '"SF Mono", ui-monospace, "Cascadia Code", Menlo, monospace',
  siteSerif: '"Fraunces", Georgia, serif',
  siteSans: '"Inter", system-ui, sans-serif',
  siteMono: '"JetBrains Mono", ui-monospace, monospace',
} as const;

export const space = {
  1: '.25rem',
  2: '.5rem',
  3: '.75rem',
  4: '1.1rem',
  5: '1.8rem',
  6: '2.4rem',
  7: '3.6rem',
  measure: '820px',
  gutter: '22px',
} as const;

export const radius = {
  sm: '6px',
  md: '12px',
  lg: '14px',
  pill: '999px',
} as const;
