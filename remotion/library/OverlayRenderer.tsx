import React from 'react';
import {staticFile} from 'remotion';
import type {EditSpec, OverlayAnimation, ReelOverlay, ReelThemeName} from '../types';
import {Ticker} from './decorations';
import {BlurReveal, Fade, Impact, MaskReveal, Pop, Slide, SpringReveal} from './motion';
import {
  Badge,
  CaptionPanel,
  ChapterCard,
  Checklist,
  CountdownCard,
  CTAEndCard,
  HookTitle,
  InfoChips,
  LowerThird,
  Scoreboard,
  SplitHeadline,
  StatCards,
  TestimonialCard,
  VersusCard,
  type OverlayFonts,
  type OverlayPalette,
} from './overlays';
import {getReelTheme} from './themes';

export type OverlayRendererProps = {
  overlay: ReelOverlay;
  brand: EditSpec['brand'];
  durationInFrames: number;
  themeName?: ReelThemeName;
  animation?: OverlayAnimation;
};

const rgba = (hex: string, alpha: number): string => {
  const value = hex.replace('#', '');
  if (!/^[0-9a-f]{6}$/iu.test(value)) {
    return `rgba(3,11,8,${alpha})`;
  }
  const red = Number.parseInt(value.slice(0, 2), 16);
  const green = Number.parseInt(value.slice(2, 4), 16);
  const blue = Number.parseInt(value.slice(4, 6), 16);
  return `rgba(${red},${green},${blue},${alpha})`;
};

const pickVariant = <const T extends readonly string[]>(
  value: string | undefined,
  choices: T,
  fallback: T[number],
): T[number] => choices.includes(value as T[number]) ? (value as T[number]) : fallback;

const themeDefaults = (themeName: NonNullable<EditSpec['style']>['theme']) => {
  switch (themeName) {
    case 'match_day':
      return {hook: 'highlight' as const, chapter: 'numbered' as const, stat: 'solid' as const, closing: 'banner' as const};
    case 'kinetic':
      return {hook: 'highlight' as const, chapter: 'rail' as const, stat: 'outline' as const, closing: 'banner' as const};
    case 'minimal':
      return {hook: 'stacked' as const, chapter: 'minimal' as const, stat: 'glass' as const, closing: 'minimal' as const};
    case 'premium':
      return {hook: 'outline' as const, chapter: 'minimal' as const, stat: 'outline' as const, closing: 'centered' as const};
    case 'testimonial':
      return {hook: 'boxed' as const, chapter: 'minimal' as const, stat: 'glass' as const, closing: 'minimal' as const};
    case 'youth_energy':
      return {hook: 'highlight' as const, chapter: 'numbered' as const, stat: 'solid' as const, closing: 'banner' as const};
    case 'cinematic':
      return {hook: 'boxed' as const, chapter: 'rail' as const, stat: 'glass' as const, closing: 'centered' as const};
    case 'classic':
    default:
      return {hook: 'boxed' as const, chapter: 'rail' as const, stat: 'glass' as const, closing: 'centered' as const};
  }
};

const OverlayRendererBody: React.FC<OverlayRendererProps> = ({
  overlay,
  brand,
  durationInFrames,
  themeName = 'classic',
}) => {
  const theme = getReelTheme(themeName);
  const palette: OverlayPalette = {
    primary: brand.primary,
    accent: brand.accent,
    ink: brand.ink,
    surface: rgba(brand.ink, theme.panelOpacity),
    text: '#FFFFFF',
    muted: 'rgba(255,255,255,.76)',
  };
  const fonts: OverlayFonts = {display: theme.displayFont, body: theme.bodyFont};
  const common = {palette, fonts, placement: overlay.position, durationInFrames};
  const defaults = themeDefaults(themeName);

  switch (overlay.type) {
    case 'hero_title':
      return (
        <HookTitle
          {...common}
          eyebrow={overlay.eyebrow}
          line1={overlay.line1}
          line2={overlay.line2}
          variant={pickVariant(overlay.variant, ['stacked', 'boxed', 'highlight', 'outline'], defaults.hook)}
        />
      );
    case 'chapter':
      return (
        <ChapterCard
          {...common}
          number={overlay.number}
          label={overlay.label}
          title={overlay.title}
          detail={overlay.detail}
          variant={pickVariant(overlay.variant, ['rail', 'numbered', 'minimal'], defaults.chapter)}
        />
      );
    case 'closing':
      return (
        <CTAEndCard
          {...common}
          headline={overlay.headline}
          action={overlay.action}
          urgency={overlay.deadlineMonth && overlay.deadlineDay ? `${overlay.deadlineMonth} ${overlay.deadlineDay}` : undefined}
          logoSrc={staticFile('brand/logo.png')}
          phone={brand.phone}
          url={brand.registrationUrl}
          location={brand.location}
          variant={pickVariant(overlay.variant, ['centered', 'banner', 'minimal'], defaults.closing)}
        />
      );
    case 'deadline':
      return (
        <CountdownCard
          {...common}
          label={overlay.label}
          value={overlay.date}
          variant={pickVariant(overlay.variant, ['counter', 'calendar', 'urgent'], 'urgent')}
        />
      );
    case 'lower_third':
      return (
        <LowerThird
          {...common}
          kicker={overlay.eyebrow}
          name={overlay.title}
          role={overlay.subtitle}
          side={overlay.variant === 'right' ? 'right' : 'left'}
        />
      );
    case 'stat':
      return (
        <StatCards
          {...common}
          heading={overlay.heading ?? overlay.detail}
          items={overlay.items ?? [{value: overlay.value, label: overlay.label}]}
          columns={overlay.columns ?? (overlay.items && overlay.items.length >= 3 ? 3 : overlay.items?.length === 1 ? 1 : 2)}
          variant={pickVariant(overlay.variant, ['solid', 'glass', 'outline'], defaults.stat)}
        />
      );
    case 'quote':
      return (
        <TestimonialCard
          {...common}
          quote={overlay.quote}
          author={overlay.attribution ?? brand.academy}
          role={overlay.role}
          rating={overlay.variant === 'five_star' ? 5 : undefined}
        />
      );
    case 'checklist':
      return <Checklist {...common} heading={overlay.title} items={overlay.items} />;
    case 'caption':
      return (
        <CaptionPanel
          {...common}
          text={overlay.text}
          speaker={overlay.speaker}
          activeWords={overlay.emphasis}
          variant={pickVariant(overlay.variant, ['panel', 'floating', 'karaoke'], 'panel')}
        />
      );
    case 'location':
      return (
        <InfoChips
          {...common}
          items={[{label: overlay.label ?? 'Location', value: overlay.location}, ...(overlay.detail ? [{label: 'Details', value: overlay.detail}] : [])]}
        />
      );
    case 'badge':
      return (
        <Badge
          {...common}
          text={overlay.text}
          subtext={overlay.detail}
          shape={pickVariant(overlay.variant, ['pill', 'stamp', 'burst'], 'pill')}
        />
      );
    case 'matchup':
      return (
        <VersusCard
          {...common}
          label={overlay.label}
          left={overlay.sideA}
          right={overlay.sideB}
          leftMeta={overlay.detail}
        />
      );
    case 'scoreboard':
      return (
        <Scoreboard
          {...common}
          home={overlay.homeName}
          away={overlay.awayName}
          homeScore={overlay.homeScore}
          awayScore={overlay.awayScore}
          status={overlay.status}
        />
      );
    case 'ticker':
      return <Ticker items={overlay.label ? [overlay.label, ...overlay.items] : overlay.items} color={brand.ink} backgroundColor={brand.accent} />;
    case 'split_headline':
      return (
        <SplitHeadline
          {...common}
          left={overlay.left}
          right={overlay.right}
          dividerText={overlay.dividerText}
          topLabel={overlay.topLabel}
        />
      );
    case 'info_chips':
      return <InfoChips {...common} items={overlay.items} direction={overlay.direction} />;
    default: {
      const exhaustive: never = overlay;
      throw new Error(`Unsupported overlay: ${JSON.stringify(exhaustive)}`);
    }
  }
};

export const OverlayRenderer: React.FC<OverlayRendererProps> = (props) => {
  const animation = props.animation ?? props.overlay.animation;
  const content = <OverlayRendererBody {...props} />;
  const style: React.CSSProperties = {position: 'absolute', inset: 0};

  switch (animation) {
    case 'fade':
      return <Fade style={style}>{content}</Fade>;
    case 'slide_up':
      return <Slide style={style} direction="up">{content}</Slide>;
    case 'slide_left':
      return <Slide style={style} direction="left">{content}</Slide>;
    case 'slide_right':
      return <Slide style={style} direction="right">{content}</Slide>;
    case 'pop':
      return <Pop style={style}>{content}</Pop>;
    case 'spring':
      return <SpringReveal style={style}>{content}</SpringReveal>;
    case 'mask':
      return <MaskReveal style={style}>{content}</MaskReveal>;
    case 'blur':
      return <BlurReveal style={style}>{content}</BlurReveal>;
    case 'impact':
      return <Impact style={style}>{content}</Impact>;
    default:
      return content;
  }
};
