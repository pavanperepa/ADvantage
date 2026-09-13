import type {Motion, OverlayAnimation, ReelThemeName, Transition} from '../types';

export type ReelLibraryEntry = {
  id: string;
  purpose: string;
  variants?: readonly string[];
};

export const themeCatalog: readonly ReelThemeName[] = [
  'classic',
  'cinematic',
  'match_day',
  'kinetic',
  'minimal',
  'youth_energy',
  'premium',
  'testimonial',
];

export const overlayCatalog: readonly ReelLibraryEntry[] = [
  {id: 'hero_title', purpose: 'Opening hook or campaign promise', variants: ['stacked', 'boxed', 'highlight', 'outline']},
  {id: 'chapter', purpose: 'Story beat or section marker', variants: ['rail', 'numbered', 'minimal']},
  {id: 'lower_third', purpose: 'Coach, player, speaker, or venue identification', variants: ['left', 'right']},
  {id: 'stat', purpose: 'One to three results, facts, or program metrics', variants: ['solid', 'glass', 'outline']},
  {id: 'quote', purpose: 'Parent testimonial or coach quote', variants: ['standard', 'five_star']},
  {id: 'checklist', purpose: 'Benefits, features, or learning outcomes'},
  {id: 'split_headline', purpose: 'Before/after, problem/solution, or two-part message'},
  {id: 'info_chips', purpose: 'Location, age group, contact, or event information'},
  {id: 'location', purpose: 'Compact location and detail card'},
  {id: 'badge', purpose: 'Offer, urgency, win, or announcement badge', variants: ['pill', 'stamp', 'burst']},
  {id: 'caption', purpose: 'Dialogue subtitle or emphasized quote', variants: ['panel', 'floating', 'karaoke']},
  {id: 'matchup', purpose: 'Team-versus-team or option comparison'},
  {id: 'scoreboard', purpose: 'Match score, result, or live status'},
  {id: 'deadline', purpose: 'Date or countdown emphasis', variants: ['counter', 'calendar', 'urgent']},
  {id: 'ticker', purpose: 'Continuous announcements or supporting benefits'},
  {id: 'closing', purpose: 'Logo, action, phone, URL, and final CTA', variants: ['centered', 'banner', 'minimal']},
];

export const shotMotionCatalog: readonly Motion[] = [
  'none', 'slow_push', 'hero_push', 'zoom_out', 'gentle_drift_left', 'gentle_drift_right', 'pan_up', 'pan_down', 'handheld',
];

export const overlayAnimationCatalog: readonly OverlayAnimation[] = [
  'fade', 'slide_up', 'slide_left', 'slide_right', 'pop', 'spring', 'mask', 'blur', 'impact',
];

export const transitionCatalog: readonly Transition[] = [
  'none', 'soft_dissolve', 'brand_wipe', 'impact_cut', 'wipe_left', 'wipe_right', 'wipe_up', 'wipe_down',
  'slide_left', 'slide_right', 'push_left', 'push_right', 'zoom', 'flash', 'glitch', 'shutter', 'bars', 'iris',
];

export const decorationCatalog: readonly string[] = [
  'gradient_scrim', 'vignette', 'progress_rail', 'corner_brackets', 'accent_bars', 'grid_pattern',
  'dot_pattern', 'ticker', 'floating_particles', 'confetti', 'focus_circle', 'pointer_arrow', 'film_grain',
];
