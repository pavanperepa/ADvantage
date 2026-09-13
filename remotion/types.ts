export type ReelThemeName =
  | 'classic'
  | 'cinematic'
  | 'match_day'
  | 'kinetic'
  | 'minimal'
  | 'youth_energy'
  | 'premium'
  | 'testimonial';

export type Motion =
  | 'none'
  | 'slow_push'
  | 'hero_push'
  | 'zoom_out'
  | 'gentle_drift_left'
  | 'gentle_drift_right'
  | 'pan_up'
  | 'pan_down'
  | 'handheld';

export type Transition =
  | 'none'
  | 'soft_dissolve'
  | 'brand_wipe'
  | 'impact_cut'
  | 'wipe_left'
  | 'wipe_right'
  | 'wipe_up'
  | 'wipe_down'
  | 'slide_left'
  | 'slide_right'
  | 'push_left'
  | 'push_right'
  | 'zoom'
  | 'flash'
  | 'glitch'
  | 'shutter'
  | 'bars'
  | 'iris';

export type OverlayPosition = 'top' | 'center' | 'bottom';
export type OverlayAnimation =
  | 'fade'
  | 'slide_up'
  | 'slide_left'
  | 'slide_right'
  | 'pop'
  | 'spring'
  | 'mask'
  | 'blur'
  | 'impact';

export type Shot = {
  id: string;
  media: string;
  timelineStart: number;
  duration: number;
  motion: Motion;
  transition: Transition;
  audio: number;
  focusX?: number;
  speed?: number;
  freeze?: number;
};

type OverlayBase = {
  start: number;
  duration: number;
  variant?: string;
  animation?: OverlayAnimation;
  position?: OverlayPosition;
};

export type HeroOverlay = OverlayBase & {
  type: 'hero_title';
  eyebrow: string;
  line1: string;
  line2: string;
};

export type ChapterOverlay = OverlayBase & {
  type: 'chapter';
  number: string;
  label?: string;
  title: string;
  detail: string;
};

export type ClosingOverlay = OverlayBase & {
  type: 'closing';
  headline: string;
  action: string;
  deadlineMonth?: string;
  deadlineDay?: string;
};

export type DeadlineOverlay = OverlayBase & {
  type: 'deadline';
  label: string;
  date: string;
};

export type LowerThirdOverlay = OverlayBase & {
  type: 'lower_third';
  eyebrow?: string;
  title: string;
  subtitle?: string;
};

export type StatOverlay = OverlayBase & {
  type: 'stat';
  value: string;
  label: string;
  detail?: string;
  items?: Array<{value: string; label: string}>;
  heading?: string;
  columns?: 1 | 2 | 3;
};

export type QuoteOverlay = OverlayBase & {
  type: 'quote';
  quote: string;
  attribution?: string;
  role?: string;
};

export type ChecklistOverlay = OverlayBase & {
  type: 'checklist';
  title?: string;
  items: string[];
};

export type CaptionOverlay = OverlayBase & {
  type: 'caption';
  text: string;
  speaker?: string;
  emphasis?: string[];
};

export type LocationOverlay = OverlayBase & {
  type: 'location';
  label?: string;
  location: string;
  detail?: string;
};

export type BadgeOverlay = OverlayBase & {
  type: 'badge';
  text: string;
  detail?: string;
};

export type MatchupOverlay = OverlayBase & {
  type: 'matchup';
  label?: string;
  sideA: string;
  sideB: string;
  detail?: string;
};

export type ScoreboardOverlay = OverlayBase & {
  type: 'scoreboard';
  homeName: string;
  awayName: string;
  homeScore: string;
  awayScore: string;
  status?: string;
};

export type TickerOverlay = OverlayBase & {
  type: 'ticker';
  items: string[];
  label?: string;
};

export type SplitHeadlineOverlay = OverlayBase & {
  type: 'split_headline';
  left: string;
  right: string;
  dividerText?: string;
  topLabel?: string;
};

export type InfoChipsOverlay = OverlayBase & {
  type: 'info_chips';
  items: Array<{icon?: string; label: string; value: string}>;
  direction?: 'row' | 'column';
};

export type ReelOverlay =
  | HeroOverlay
  | ChapterOverlay
  | ClosingOverlay
  | DeadlineOverlay
  | LowerThirdOverlay
  | StatOverlay
  | QuoteOverlay
  | ChecklistOverlay
  | CaptionOverlay
  | LocationOverlay
  | BadgeOverlay
  | MatchupOverlay
  | ScoreboardOverlay
  | TickerOverlay
  | SplitHeadlineOverlay
  | InfoChipsOverlay;

export type EditSpec = {
  canvas: {width: number; height: number; fps: number};
  style?: {
    theme?: ReelThemeName;
    showBrandRail?: boolean;
    transitionColor?: string;
    defaultOverlayAnimation?: OverlayAnimation;
  };
  brand: {
    academy: string;
    location: string;
    phone: string;
    registrationUrl: string;
    primary: string;
    accent: string;
    ink: string;
  };
  music: {
    source: string;
    file: string;
    title: string;
    artist: string;
    sourceUrl: string;
    license: string;
    baseVolume: number;
    duckVolume: number;
    duckStart: number;
    duckEnd: number;
    fadeIn: number;
    fadeOut: number;
  };
  shots: Shot[];
  overlays: ReelOverlay[];
};
