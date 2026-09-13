import type {CSSProperties} from 'react';
import type {EditSpec, ReelThemeName} from '../types';

export type {ReelThemeName} from '../types';

export type ReelTheme = {
  name: ReelThemeName;
  displayFont: string;
  bodyFont: string;
  textTransform: CSSProperties['textTransform'];
  titleTracking: number;
  eyebrowTracking: number;
  radius: number;
  borderWidth: number;
  panelOpacity: number;
  scrimOpacity: number;
  shadow: string;
  titleScale: number;
  accentScale: number;
};

const THEMES: Record<ReelThemeName, ReelTheme> = {
  classic: {
    name: 'classic',
    displayFont: 'Display',
    bodyFont: 'Body',
    textTransform: 'uppercase',
    titleTracking: 0,
    eyebrowTracking: 5,
    radius: 0,
    borderWidth: 1,
    panelOpacity: 0.9,
    scrimOpacity: 0.68,
    shadow: '0 22px 48px rgba(0,0,0,.36)',
    titleScale: 1,
    accentScale: 1,
  },
  cinematic: {
    name: 'cinematic',
    displayFont: 'Display',
    bodyFont: 'Body',
    textTransform: 'uppercase',
    titleTracking: 1,
    eyebrowTracking: 7,
    radius: 4,
    borderWidth: 1,
    panelOpacity: 0.78,
    scrimOpacity: 0.82,
    shadow: '0 30px 80px rgba(0,0,0,.52)',
    titleScale: 1.02,
    accentScale: 0.8,
  },
  match_day: {
    name: 'match_day',
    displayFont: 'Display',
    bodyFont: 'Body',
    textTransform: 'uppercase',
    titleTracking: -1,
    eyebrowTracking: 5,
    radius: 10,
    borderWidth: 3,
    panelOpacity: 0.92,
    scrimOpacity: 0.58,
    shadow: '0 18px 0 rgba(0,0,0,.34)',
    titleScale: 1.08,
    accentScale: 1.2,
  },
  kinetic: {
    name: 'kinetic',
    displayFont: 'Display',
    bodyFont: 'Body',
    textTransform: 'uppercase',
    titleTracking: -2,
    eyebrowTracking: 3,
    radius: 2,
    borderWidth: 4,
    panelOpacity: 0.94,
    scrimOpacity: 0.48,
    shadow: '12px 14px 0 rgba(0,0,0,.55)',
    titleScale: 1.14,
    accentScale: 1.35,
  },
  minimal: {
    name: 'minimal',
    displayFont: 'Body',
    bodyFont: 'Body',
    textTransform: 'none',
    titleTracking: -1,
    eyebrowTracking: 3,
    radius: 22,
    borderWidth: 1,
    panelOpacity: 0.84,
    scrimOpacity: 0.42,
    shadow: '0 16px 50px rgba(0,0,0,.24)',
    titleScale: 0.9,
    accentScale: 0.65,
  },
  youth_energy: {
    name: 'youth_energy',
    displayFont: 'Display',
    bodyFont: 'Body',
    textTransform: 'uppercase',
    titleTracking: 0,
    eyebrowTracking: 3,
    radius: 28,
    borderWidth: 3,
    panelOpacity: 0.9,
    scrimOpacity: 0.5,
    shadow: '0 22px 0 rgba(0,0,0,.3)',
    titleScale: 1.06,
    accentScale: 1.3,
  },
  premium: {
    name: 'premium',
    displayFont: 'Display',
    bodyFont: 'Body',
    textTransform: 'uppercase',
    titleTracking: 2,
    eyebrowTracking: 9,
    radius: 0,
    borderWidth: 1,
    panelOpacity: 0.82,
    scrimOpacity: 0.76,
    shadow: '0 28px 70px rgba(0,0,0,.46)',
    titleScale: 0.94,
    accentScale: 0.72,
  },
  testimonial: {
    name: 'testimonial',
    displayFont: 'Body',
    bodyFont: 'Body',
    textTransform: 'none',
    titleTracking: -1,
    eyebrowTracking: 3,
    radius: 26,
    borderWidth: 1,
    panelOpacity: 0.9,
    scrimOpacity: 0.6,
    shadow: '0 24px 64px rgba(0,0,0,.34)',
    titleScale: 0.88,
    accentScale: 0.75,
  },
};

export const reelThemeNames = Object.keys(THEMES) as ReelThemeName[];

export const getReelTheme = (name: ReelThemeName | undefined): ReelTheme =>
  THEMES[name ?? 'classic'];

export type ReelPalette = {
  primary: string;
  accent: string;
  ink: string;
  text: string;
  mutedText: string;
  panel: string;
};

export const getReelPalette = (brand: EditSpec['brand']): ReelPalette => ({
  primary: brand.primary,
  accent: brand.accent,
  ink: brand.ink,
  text: '#FFFFFF',
  mutedText: 'rgba(255,255,255,.76)',
  panel: brand.ink,
});
