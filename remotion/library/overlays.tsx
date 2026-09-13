import React from 'react';
import {
  AbsoluteFill,
  Easing,
  Img,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

/**
 * A dependency-free collection of social-video overlays. All components are
 * sized for a 1080 x 1920 canvas and keep important copy inside the default
 * Reels/Stories safe area. Put each component inside a Remotion Sequence.
 */

export const REEL_SAFE_AREA = {
  top: 150,
  right: 72,
  bottom: 260,
  left: 72,
} as const;

export type OverlayPalette = {
  primary: string;
  accent: string;
  ink: string;
  surface: string;
  text: string;
  muted: string;
};

export type OverlayFonts = {
  display: string;
  body: string;
};

export type OverlayPlacement = 'top' | 'center' | 'bottom';

export type ReelOverlayBaseProps = {
  palette?: Partial<OverlayPalette>;
  fonts?: Partial<OverlayFonts>;
  placement?: OverlayPlacement;
  enterDelay?: number;
  exitFrames?: number;
  durationInFrames?: number;
};

const DEFAULT_PALETTE: OverlayPalette = {
  primary: '#8CC63F',
  accent: '#FFD437',
  ink: '#061008',
  surface: 'rgba(3, 11, 8, 0.92)',
  text: '#FFFFFF',
  muted: 'rgba(255, 255, 255, 0.76)',
};

const DEFAULT_FONTS: OverlayFonts = {
  display: 'Display, Impact, sans-serif',
  body: 'Body, Arial, sans-serif',
};

const resolvePalette = (value?: Partial<OverlayPalette>): OverlayPalette => ({
  ...DEFAULT_PALETTE,
  ...value,
});

const resolveFonts = (value?: Partial<OverlayFonts>): OverlayFonts => ({
  ...DEFAULT_FONTS,
  ...value,
});

const placementStyle = (placement: OverlayPlacement = 'bottom'): React.CSSProperties => ({
  justifyContent:
    placement === 'top' ? 'flex-start' : placement === 'center' ? 'center' : 'flex-end',
});

const useOverlayMotion = ({
  enterDelay = 0,
  exitFrames = 10,
  durationInFrames,
}: Pick<ReelOverlayBaseProps, 'enterDelay' | 'exitFrames' | 'durationInFrames'>) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames: sequenceDuration} = useVideoConfig();
  const duration = durationInFrames ?? sequenceDuration;
  const reveal = spring({
    frame: Math.max(0, frame - enterDelay),
    fps,
    config: {damping: 18, stiffness: 125, mass: 0.9},
  });
  const visible = interpolate(
    frame,
    [Math.max(0, duration - exitFrames), Math.max(1, duration - 1)],
    [1, 0],
    {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.in(Easing.cubic),
    },
  );
  return {frame, fps, reveal, visible};
};

const OverlayFill: React.FC<{
  placement?: OverlayPlacement;
  opacity?: number;
  children: React.ReactNode;
  style?: React.CSSProperties;
}> = ({placement = 'bottom', opacity = 1, children, style}) => (
  <AbsoluteFill
    style={{
      ...placementStyle(placement),
      padding: `${REEL_SAFE_AREA.top}px ${REEL_SAFE_AREA.right}px ${REEL_SAFE_AREA.bottom}px ${REEL_SAFE_AREA.left}px`,
      opacity,
      pointerEvents: 'none',
      ...style,
    }}
  >
    {children}
  </AbsoluteFill>
);

const Eyebrow: React.FC<{
  children: React.ReactNode;
  color: string;
  font: string;
  dark?: boolean;
}> = ({children, color, font, dark = false}) => (
  <div
    style={{
      alignSelf: 'flex-start',
      background: dark ? color : 'transparent',
      color: dark ? '#061008' : color,
      fontFamily: font,
      fontSize: 22,
      fontWeight: 800,
      letterSpacing: 5,
      lineHeight: 1,
      padding: dark ? '11px 15px 9px' : 0,
      textTransform: 'uppercase',
    }}
  >
    {children}
  </div>
);

export type HookTitleProps = ReelOverlayBaseProps & {
  eyebrow?: string;
  line1: string;
  line2?: string;
  supportingText?: string;
  variant?: 'stacked' | 'boxed' | 'highlight' | 'outline';
  align?: 'left' | 'center';
};

/** Large opening hook with four common editorial treatments. */
export const HookTitle: React.FC<HookTitleProps> = ({
  eyebrow,
  line1,
  line2,
  supportingText,
  variant = 'stacked',
  align = 'left',
  palette: paletteInput,
  fonts: fontInput,
  placement = 'bottom',
  ...motionProps
}) => {
  const palette = resolvePalette(paletteInput);
  const fonts = resolveFonts(fontInput);
  const {reveal, visible} = useOverlayMotion(motionProps);
  const centered = align === 'center';
  const boxed = variant === 'boxed';
  const highlight = variant === 'highlight';
  const outline = variant === 'outline';

  return (
    <OverlayFill placement={placement} opacity={visible}>
      <div
        style={{
          alignItems: centered ? 'center' : 'flex-start',
          alignSelf: centered ? 'center' : 'stretch',
          background: boxed ? palette.surface : 'transparent',
          border: boxed ? `2px solid ${palette.accent}` : undefined,
          borderLeft: boxed && !centered ? `12px solid ${palette.accent}` : undefined,
          boxShadow: boxed ? '0 24px 70px rgba(0,0,0,.38)' : undefined,
          display: 'flex',
          flexDirection: 'column',
          maxWidth: 936,
          padding: boxed ? '42px 42px 46px' : 0,
          textAlign: align,
          transform: `translateY(${(1 - reveal) * 90}px) scale(${0.96 + reveal * 0.04})`,
          opacity: reveal,
        }}
      >
        {eyebrow ? <Eyebrow color={palette.accent} font={fonts.body} dark={highlight}>{eyebrow}</Eyebrow> : null}
        <div
          style={{
            color: palette.text,
            fontFamily: fonts.display,
            fontSize: line1.length > 24 ? 80 : 104,
            lineHeight: 0.92,
            marginTop: eyebrow ? 22 : 0,
            textShadow: '0 6px 22px rgba(0,0,0,.75)',
            textTransform: 'uppercase',
          }}
        >
          {line1}
        </div>
        {line2 ? (
          <div
            style={{
              WebkitTextStroke: outline ? `3px ${palette.accent}` : undefined,
              background: highlight ? palette.accent : 'transparent',
              color: outline ? 'transparent' : highlight ? palette.ink : palette.accent,
              fontFamily: fonts.display,
              fontSize: line2.length > 20 ? 82 : 120,
              lineHeight: 0.9,
              marginTop: 12,
              padding: highlight ? '8px 18px 4px' : 0,
              textShadow: outline || highlight ? undefined : '0 6px 22px rgba(0,0,0,.7)',
              textTransform: 'uppercase',
              transform: `translateX(${(1 - reveal) * (centered ? 0 : -55)}px)`,
            }}
          >
            {line2}
          </div>
        ) : null}
        {supportingText ? (
          <div style={{color: palette.muted, fontFamily: fonts.body, fontSize: 30, lineHeight: 1.25, marginTop: 24, maxWidth: 820}}>
            {supportingText}
          </div>
        ) : null}
        {!boxed ? <div style={{background: palette.accent, height: 9, marginTop: 28, width: 150 * reveal}} /> : null}
      </div>
    </OverlayFill>
  );
};

export type ChapterCardProps = ReelOverlayBaseProps & {
  number?: string;
  label?: string;
  title: string;
  detail?: string;
  variant?: 'rail' | 'numbered' | 'minimal';
};

export const ChapterCard: React.FC<ChapterCardProps> = ({
  number,
  label,
  title,
  detail,
  variant = 'rail',
  palette: paletteInput,
  fonts: fontInput,
  placement = 'bottom',
  ...motionProps
}) => {
  const palette = resolvePalette(paletteInput);
  const fonts = resolveFonts(fontInput);
  const {reveal, visible} = useOverlayMotion(motionProps);
  const minimal = variant === 'minimal';
  return (
    <OverlayFill placement={placement} opacity={visible}>
      <div
        style={{
          alignItems: 'stretch',
          display: 'flex',
          maxWidth: 900,
          opacity: reveal,
          transform: `translateX(${(1 - reveal) * -70}px)`,
        }}
      >
        {variant === 'rail' ? <div style={{background: palette.accent, boxShadow: `0 0 28px ${palette.accent}80`, width: 12}} /> : null}
        {variant === 'numbered' && number ? (
          <div
            style={{
              alignItems: 'center',
              background: palette.accent,
              color: palette.ink,
              display: 'flex',
              fontFamily: fonts.display,
              fontSize: 92,
              justifyContent: 'center',
              minWidth: 150,
            }}
          >
            {number}
          </div>
        ) : null}
        <div
          style={{
            background: minimal ? 'transparent' : palette.surface,
            border: minimal ? undefined : `1px solid ${palette.accent}66`,
            boxShadow: minimal ? undefined : '0 22px 54px rgba(0,0,0,.36)',
            padding: minimal ? 0 : '30px 36px 34px',
          }}
        >
          {label ? <Eyebrow color={palette.accent} font={fonts.body}>{label}</Eyebrow> : null}
          <div style={{color: palette.text, fontFamily: fonts.display, fontSize: title.length > 26 ? 62 : 76, lineHeight: 0.98, marginTop: label ? 12 : 0, textShadow: minimal ? '0 5px 18px rgba(0,0,0,.8)' : undefined}}>
            {title}
          </div>
          {detail ? <div style={{color: palette.muted, fontFamily: fonts.body, fontSize: 28, lineHeight: 1.25, marginTop: 14}}>{detail}</div> : null}
        </div>
      </div>
    </OverlayFill>
  );
};

export type LowerThirdProps = ReelOverlayBaseProps & {
  name: string;
  role?: string;
  kicker?: string;
  avatarSrc?: string;
  side?: 'left' | 'right';
};

export const LowerThird: React.FC<LowerThirdProps> = ({
  name,
  role,
  kicker,
  avatarSrc,
  side = 'left',
  palette: paletteInput,
  fonts: fontInput,
  placement = 'bottom',
  ...motionProps
}) => {
  const palette = resolvePalette(paletteInput);
  const fonts = resolveFonts(fontInput);
  const {reveal, visible} = useOverlayMotion(motionProps);
  return (
    <OverlayFill placement={placement} opacity={visible} style={{alignItems: side === 'right' ? 'flex-end' : 'flex-start'}}>
      <div style={{alignItems: 'stretch', display: 'flex', flexDirection: side === 'right' ? 'row-reverse' : 'row', opacity: reveal, transform: `translateX(${(1 - reveal) * (side === 'right' ? 100 : -100)}px)`}}>
        {avatarSrc ? <Img src={avatarSrc} style={{border: `5px solid ${palette.accent}`, height: 142, objectFit: 'cover', width: 142}} /> : null}
        <div style={{background: palette.surface, borderBottom: `8px solid ${palette.accent}`, minWidth: 440, padding: '24px 30px 20px'}}>
          {kicker ? <div style={{color: palette.accent, fontFamily: fonts.body, fontSize: 18, fontWeight: 800, letterSpacing: 4, textTransform: 'uppercase'}}>{kicker}</div> : null}
          <div style={{color: palette.text, fontFamily: fonts.display, fontSize: 52, lineHeight: 1, marginTop: kicker ? 7 : 0}}>{name}</div>
          {role ? <div style={{color: palette.muted, fontFamily: fonts.body, fontSize: 24, marginTop: 7}}>{role}</div> : null}
        </div>
      </div>
    </OverlayFill>
  );
};

export type StatItem = {value: string; label: string};

export type StatCardsProps = ReelOverlayBaseProps & {
  items: StatItem[];
  heading?: string;
  columns?: 1 | 2 | 3;
  variant?: 'solid' | 'glass' | 'outline';
};

export const StatCards: React.FC<StatCardsProps> = ({
  items,
  heading,
  columns = 2,
  variant = 'glass',
  palette: paletteInput,
  fonts: fontInput,
  placement = 'center',
  ...motionProps
}) => {
  const palette = resolvePalette(paletteInput);
  const fonts = resolveFonts(fontInput);
  const {reveal, visible} = useOverlayMotion(motionProps);
  return (
    <OverlayFill placement={placement} opacity={visible}>
      <div style={{width: '100%'}}>
        {heading ? <div style={{color: palette.text, fontFamily: fonts.display, fontSize: 66, marginBottom: 28, textAlign: 'center', textShadow: '0 5px 18px rgba(0,0,0,.75)'}}>{heading}</div> : null}
        <div style={{display: 'grid', gap: 18, gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))`}}>
          {items.map((item, index) => {
            const itemReveal = interpolate(reveal, [index * 0.08, 0.72 + index * 0.08], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
            const valueSize = columns === 3
              ? item.value.length > 8 ? 38 : item.value.length > 5 ? 50 : 66
              : item.value.length > 8 ? 58 : 82;
            return (
              <div
                key={`${item.label}-${index}`}
                style={{
                  background: variant === 'solid' ? palette.accent : variant === 'glass' ? palette.surface : 'rgba(0,0,0,.18)',
                  border: variant === 'outline' ? `3px solid ${palette.accent}` : `1px solid ${palette.accent}55`,
                  boxShadow: '0 16px 42px rgba(0,0,0,.32)',
                  color: variant === 'solid' ? palette.ink : palette.text,
                  minHeight: 190,
                  opacity: itemReveal,
                  minWidth: 0,
                  overflow: 'hidden',
                  padding: columns === 3 ? '30px 12px' : '30px 24px',
                  textAlign: 'center',
                  transform: `translateY(${(1 - itemReveal) * 45}px)`,
                }}
              >
                <div style={{color: variant === 'solid' ? palette.ink : palette.accent, fontFamily: fonts.display, fontSize: valueSize, lineHeight: 0.95, overflowWrap: 'anywhere'}}>{item.value}</div>
                <div style={{fontFamily: fonts.body, fontSize: 22, fontWeight: 700, letterSpacing: 2, marginTop: 14, textTransform: 'uppercase'}}>{item.label}</div>
              </div>
            );
          })}
        </div>
      </div>
    </OverlayFill>
  );
};

export type TestimonialCardProps = ReelOverlayBaseProps & {
  quote: string;
  author: string;
  role?: string;
  rating?: number;
  avatarSrc?: string;
};

export const TestimonialCard: React.FC<TestimonialCardProps> = ({
  quote,
  author,
  role,
  rating,
  avatarSrc,
  palette: paletteInput,
  fonts: fontInput,
  placement = 'center',
  ...motionProps
}) => {
  const palette = resolvePalette(paletteInput);
  const fonts = resolveFonts(fontInput);
  const {reveal, visible} = useOverlayMotion(motionProps);
  const stars = Math.max(0, Math.min(5, Math.round(rating ?? 0)));
  return (
    <OverlayFill placement={placement} opacity={visible}>
      <div style={{background: palette.surface, border: `2px solid ${palette.accent}88`, boxShadow: '0 28px 78px rgba(0,0,0,.42)', opacity: reveal, padding: '54px 48px 46px', position: 'relative', transform: `scale(${0.92 + reveal * 0.08})`, width: '100%'}}>
        <div style={{color: palette.accent, fontFamily: 'Georgia, serif', fontSize: 150, left: 28, lineHeight: 1, opacity: 0.65, position: 'absolute', top: 5}}>“</div>
        {stars > 0 ? <div style={{color: palette.accent, fontFamily: fonts.body, fontSize: 32, letterSpacing: 8, marginBottom: 22}}>{'★'.repeat(stars)}</div> : null}
        <div style={{color: palette.text, fontFamily: fonts.display, fontSize: quote.length > 130 ? 42 : 52, lineHeight: 1.14, position: 'relative'}}>{quote}</div>
        <div style={{alignItems: 'center', display: 'flex', gap: 18, marginTop: 32}}>
          {avatarSrc ? <Img src={avatarSrc} style={{border: `4px solid ${palette.accent}`, borderRadius: '50%', height: 88, objectFit: 'cover', width: 88}} /> : null}
          <div>
            <div style={{color: palette.accent, fontFamily: fonts.body, fontSize: 26, fontWeight: 800}}>{author}</div>
            {role ? <div style={{color: palette.muted, fontFamily: fonts.body, fontSize: 21, marginTop: 4}}>{role}</div> : null}
          </div>
        </div>
      </div>
    </OverlayFill>
  );
};

export type ChecklistProps = ReelOverlayBaseProps & {
  heading?: string;
  items: string[];
  checkmark?: string;
};

export const Checklist: React.FC<ChecklistProps> = ({
  heading,
  items,
  checkmark = '✓',
  palette: paletteInput,
  fonts: fontInput,
  placement = 'center',
  ...motionProps
}) => {
  const palette = resolvePalette(paletteInput);
  const fonts = resolveFonts(fontInput);
  const {reveal, visible} = useOverlayMotion(motionProps);
  return (
    <OverlayFill placement={placement} opacity={visible}>
      <div style={{background: palette.surface, borderTop: `10px solid ${palette.accent}`, boxShadow: '0 24px 64px rgba(0,0,0,.4)', padding: '40px 42px 44px', width: '100%'}}>
        {heading ? <div style={{color: palette.text, fontFamily: fonts.display, fontSize: 64, lineHeight: 1, marginBottom: 30}}>{heading}</div> : null}
        <div style={{display: 'flex', flexDirection: 'column', gap: 18}}>
          {items.map((item, index) => {
            const rowReveal = interpolate(reveal, [index * 0.09, 0.62 + index * 0.09], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
            return (
              <div key={`${item}-${index}`} style={{alignItems: 'center', display: 'flex', gap: 20, opacity: rowReveal, transform: `translateX(${(1 - rowReveal) * -44}px)`}}>
                <div style={{alignItems: 'center', background: palette.accent, borderRadius: '50%', color: palette.ink, display: 'flex', flex: '0 0 54px', fontFamily: fonts.body, fontSize: 30, fontWeight: 900, height: 54, justifyContent: 'center'}}>{checkmark}</div>
                <div style={{color: palette.text, fontFamily: fonts.body, fontSize: items.length > 5 ? 28 : 34, fontWeight: 700, lineHeight: 1.18}}>{item}</div>
              </div>
            );
          })}
        </div>
      </div>
    </OverlayFill>
  );
};

export type SplitHeadlineProps = ReelOverlayBaseProps & {
  left: string;
  right: string;
  dividerText?: string;
  topLabel?: string;
};

export const SplitHeadline: React.FC<SplitHeadlineProps> = ({
  left,
  right,
  dividerText,
  topLabel,
  palette: paletteInput,
  fonts: fontInput,
  placement = 'center',
  ...motionProps
}) => {
  const palette = resolvePalette(paletteInput);
  const fonts = resolveFonts(fontInput);
  const {reveal, visible} = useOverlayMotion(motionProps);
  return (
    <OverlayFill placement={placement} opacity={visible} style={{alignItems: 'center'}}>
      {topLabel ? <Eyebrow color={palette.accent} font={fonts.body} dark>{topLabel}</Eyebrow> : null}
      <div style={{alignItems: 'stretch', display: 'flex', marginTop: topLabel ? 26 : 0, width: '100%'}}>
        <div style={{alignItems: 'flex-end', background: palette.surface, color: palette.text, display: 'flex', flex: 1, fontFamily: fonts.display, fontSize: 70, justifyContent: 'center', lineHeight: 0.95, opacity: reveal, padding: '42px 32px', textAlign: 'right', transform: `translateX(${(1 - reveal) * -100}px)`}}>{left}</div>
        <div style={{alignItems: 'center', background: palette.accent, color: palette.ink, display: 'flex', fontFamily: fonts.display, fontSize: dividerText ? 34 : 0, justifyContent: 'center', minWidth: dividerText ? 110 : 14, padding: dividerText ? '0 12px' : 0, zIndex: 1}}>{dividerText}</div>
        <div style={{alignItems: 'flex-start', background: `${palette.ink}ED`, color: palette.accent, display: 'flex', flex: 1, fontFamily: fonts.display, fontSize: 70, justifyContent: 'center', lineHeight: 0.95, opacity: reveal, padding: '42px 32px', textAlign: 'left', transform: `translateX(${(1 - reveal) * 100}px)`}}>{right}</div>
      </div>
    </OverlayFill>
  );
};

export type InfoChipItem = {
  icon?: string;
  label: string;
  value: string;
};

export type InfoChipsProps = ReelOverlayBaseProps & {
  items: InfoChipItem[];
  direction?: 'row' | 'column';
};

/** Compact location, schedule, age, price, or contact chips. */
export const InfoChips: React.FC<InfoChipsProps> = ({
  items,
  direction = 'column',
  palette: paletteInput,
  fonts: fontInput,
  placement = 'bottom',
  ...motionProps
}) => {
  const palette = resolvePalette(paletteInput);
  const fonts = resolveFonts(fontInput);
  const {reveal, visible} = useOverlayMotion(motionProps);
  return (
    <OverlayFill placement={placement} opacity={visible}>
      <div style={{display: 'flex', flexDirection: direction, flexWrap: 'wrap', gap: 14}}>
        {items.map((item, index) => (
          <div key={`${item.label}-${index}`} style={{alignItems: 'center', background: palette.surface, border: `2px solid ${palette.accent}88`, display: 'flex', flex: direction === 'row' ? '1 1 260px' : undefined, gap: 16, opacity: reveal, padding: '17px 22px', transform: `translateY(${(1 - reveal) * (26 + index * 8)}px)`}}>
            {item.icon ? <div style={{fontSize: 35, lineHeight: 1}}>{item.icon}</div> : <div style={{background: palette.accent, height: 42, width: 7}} />}
            <div>
              <div style={{color: palette.accent, fontFamily: fonts.body, fontSize: 17, fontWeight: 800, letterSpacing: 3, textTransform: 'uppercase'}}>{item.label}</div>
              <div style={{color: palette.text, fontFamily: fonts.body, fontSize: 28, fontWeight: 700, lineHeight: 1.1, marginTop: 5}}>{item.value}</div>
            </div>
          </div>
        ))}
      </div>
    </OverlayFill>
  );
};

export type BadgeProps = ReelOverlayBaseProps & {
  text: string;
  subtext?: string;
  shape?: 'pill' | 'stamp' | 'burst';
  rotation?: number;
  side?: 'left' | 'right';
};

export const Badge: React.FC<BadgeProps> = ({
  text,
  subtext,
  shape = 'pill',
  rotation = -5,
  side = 'right',
  palette: paletteInput,
  fonts: fontInput,
  placement = 'top',
  ...motionProps
}) => {
  const palette = resolvePalette(paletteInput);
  const fonts = resolveFonts(fontInput);
  const {reveal, visible} = useOverlayMotion(motionProps);
  const burst = shape === 'burst';
  const stamp = shape === 'stamp';
  return (
    <OverlayFill placement={placement} opacity={visible} style={{alignItems: side === 'right' ? 'flex-end' : 'flex-start'}}>
      <div style={{alignItems: 'center', aspectRatio: burst || stamp ? '1' : undefined, background: burst ? palette.accent : stamp ? palette.surface : palette.accent, border: stamp ? `6px double ${palette.accent}` : `3px solid ${palette.text}`, borderRadius: shape === 'pill' ? 999 : stamp ? '50%' : 0, clipPath: burst ? 'polygon(50% 0%,61% 13%,78% 5%,83% 23%,100% 28%,89% 44%,100% 58%,82% 65%,81% 84%,62% 79%,50% 100%,39% 81%,20% 87%,18% 67%,0% 59%,11% 43%,0% 28%,18% 22%,22% 4%,40% 13%)' : undefined, color: burst || shape === 'pill' ? palette.ink : palette.text, display: 'flex', flexDirection: 'column', justifyContent: 'center', minHeight: shape === 'pill' ? 90 : 230, opacity: reveal, padding: shape === 'pill' ? '19px 32px 16px' : 30, textAlign: 'center', transform: `rotate(${rotation}deg) scale(${0.65 + reveal * 0.35})`, width: shape === 'pill' ? undefined : 230}}>
        <div style={{fontFamily: fonts.display, fontSize: shape === 'pill' ? 42 : text.length > 10 ? 39 : 50, lineHeight: 0.95, textTransform: 'uppercase'}}>{text}</div>
        {subtext ? <div style={{fontFamily: fonts.body, fontSize: 17, fontWeight: 800, letterSpacing: 2, marginTop: 8, textTransform: 'uppercase'}}>{subtext}</div> : null}
      </div>
    </OverlayFill>
  );
};

export type CaptionPanelProps = ReelOverlayBaseProps & {
  text: string;
  activeWords?: string[];
  speaker?: string;
  variant?: 'panel' | 'floating' | 'karaoke';
};

export const CaptionPanel: React.FC<CaptionPanelProps> = ({
  text,
  activeWords = [],
  speaker,
  variant = 'panel',
  palette: paletteInput,
  fonts: fontInput,
  placement = 'bottom',
  ...motionProps
}) => {
  const palette = resolvePalette(paletteInput);
  const fonts = resolveFonts(fontInput);
  const {reveal, visible} = useOverlayMotion(motionProps);
  const active = new Set(activeWords.map((word) => word.toLocaleLowerCase()));
  const words = text.split(/(\s+)/);
  return (
    <OverlayFill placement={placement} opacity={visible} style={{alignItems: variant === 'floating' ? 'center' : 'stretch'}}>
      <div style={{background: variant === 'floating' ? 'transparent' : palette.surface, borderRadius: variant === 'panel' ? 20 : 0, borderTop: variant === 'panel' ? `7px solid ${palette.accent}` : undefined, boxShadow: variant === 'panel' ? '0 18px 48px rgba(0,0,0,.4)' : undefined, maxWidth: variant === 'floating' ? 860 : undefined, opacity: reveal, padding: variant === 'panel' ? '24px 30px 28px' : 0, textAlign: 'center', transform: `translateY(${(1 - reveal) * 30}px)`}}>
        {speaker ? <div style={{color: palette.accent, fontFamily: fonts.body, fontSize: 18, fontWeight: 900, letterSpacing: 4, marginBottom: 10, textTransform: 'uppercase'}}>{speaker}</div> : null}
        <div style={{color: palette.text, fontFamily: fonts.body, fontSize: text.length > 100 ? 34 : 42, fontWeight: 800, lineHeight: 1.22, textShadow: variant === 'floating' ? '0 3px 12px #000, 0 3px 20px #000' : undefined}}>
          {words.map((word, index) => {
            const normalized = word.replace(/[^\p{L}\p{N}']/gu, '').toLocaleLowerCase();
            const isActive = normalized.length > 0 && active.has(normalized);
            return <span key={`${word}-${index}`} style={{background: isActive && variant === 'karaoke' ? palette.accent : undefined, color: isActive ? (variant === 'karaoke' ? palette.ink : palette.accent) : undefined, padding: isActive && variant === 'karaoke' ? '2px 5px' : 0}}>{word}</span>;
          })}
        </div>
      </div>
    </OverlayFill>
  );
};

export type VersusCardProps = ReelOverlayBaseProps & {
  left: string;
  right: string;
  leftMeta?: string;
  rightMeta?: string;
  label?: string;
};

export const VersusCard: React.FC<VersusCardProps> = ({
  left,
  right,
  leftMeta,
  rightMeta,
  label,
  palette: paletteInput,
  fonts: fontInput,
  placement = 'center',
  ...motionProps
}) => {
  const palette = resolvePalette(paletteInput);
  const fonts = resolveFonts(fontInput);
  const {reveal, visible} = useOverlayMotion(motionProps);
  return (
    <OverlayFill placement={placement} opacity={visible} style={{alignItems: 'center'}}>
      {label ? <Eyebrow color={palette.accent} font={fonts.body} dark>{label}</Eyebrow> : null}
      <div style={{alignItems: 'center', display: 'flex', marginTop: label ? 30 : 0, width: '100%'}}>
        {[
          {name: left, meta: leftMeta, side: -1},
          {name: right, meta: rightMeta, side: 1},
        ].map((team, index) => (
          <React.Fragment key={`${team.name}-${index}`}>
            {index === 1 ? <div style={{alignItems: 'center', background: palette.accent, border: `5px solid ${palette.text}`, borderRadius: '50%', color: palette.ink, display: 'flex', flex: '0 0 122px', fontFamily: fonts.display, fontSize: 44, height: 122, justifyContent: 'center', margin: '0 -14px', zIndex: 2}}>VS</div> : null}
            <div style={{background: index === 0 ? palette.surface : `${palette.ink}F2`, border: `3px solid ${index === 0 ? palette.text : palette.accent}`, color: index === 0 ? palette.text : palette.accent, flex: 1, opacity: reveal, padding: '52px 22px 44px', textAlign: 'center', transform: `translateX(${(1 - reveal) * team.side * 120}px)`}}>
              <div style={{fontFamily: fonts.display, fontSize: team.name.length > 14 ? 46 : 59, lineHeight: 0.95, textTransform: 'uppercase'}}>{team.name}</div>
              {team.meta ? <div style={{color: palette.muted, fontFamily: fonts.body, fontSize: 21, marginTop: 13}}>{team.meta}</div> : null}
            </div>
          </React.Fragment>
        ))}
      </div>
    </OverlayFill>
  );
};

export type ScoreboardProps = ReelOverlayBaseProps & {
  home: string;
  away: string;
  homeScore: string;
  awayScore: string;
  status?: string;
  competition?: string;
  detail?: string;
};

export const Scoreboard: React.FC<ScoreboardProps> = ({
  home,
  away,
  homeScore,
  awayScore,
  status,
  competition,
  detail,
  palette: paletteInput,
  fonts: fontInput,
  placement = 'top',
  ...motionProps
}) => {
  const palette = resolvePalette(paletteInput);
  const fonts = resolveFonts(fontInput);
  const {reveal, visible} = useOverlayMotion(motionProps);
  return (
    <OverlayFill placement={placement} opacity={visible} style={{alignItems: 'center'}}>
      <div style={{boxShadow: '0 18px 50px rgba(0,0,0,.42)', opacity: reveal, transform: `translateY(${(1 - reveal) * -70}px)`, width: '100%'}}>
        {competition ? <div style={{background: palette.accent, color: palette.ink, fontFamily: fonts.body, fontSize: 18, fontWeight: 900, letterSpacing: 4, padding: '10px 18px 8px', textAlign: 'center', textTransform: 'uppercase'}}>{competition}</div> : null}
        <div style={{alignItems: 'center', background: palette.surface, display: 'grid', gridTemplateColumns: '1fr 142px 1fr', minHeight: 150}}>
          <div style={{color: palette.text, fontFamily: fonts.display, fontSize: home.length > 14 ? 38 : 48, padding: '20px', textAlign: 'right', textTransform: 'uppercase'}}>{home}</div>
          <div style={{background: palette.text, color: palette.ink, fontFamily: fonts.display, fontSize: 46, padding: '20px 8px', textAlign: 'center'}}>{homeScore}<span style={{color: palette.primary, padding: '0 7px'}}>–</span>{awayScore}</div>
          <div style={{color: palette.text, fontFamily: fonts.display, fontSize: away.length > 14 ? 38 : 48, padding: '20px', textAlign: 'left', textTransform: 'uppercase'}}>{away}</div>
        </div>
        {status || detail ? <div style={{background: `${palette.ink}F2`, borderTop: `3px solid ${palette.accent}`, color: palette.muted, display: 'flex', fontFamily: fonts.body, fontSize: 19, fontWeight: 700, justifyContent: 'space-between', letterSpacing: 2, padding: '11px 18px'}}><span>{status}</span><span>{detail}</span></div> : null}
      </div>
    </OverlayFill>
  );
};

export type CountdownCardProps = ReelOverlayBaseProps & {
  label: string;
  value: string;
  unit?: string;
  date?: string;
  variant?: 'counter' | 'calendar' | 'urgent';
};

export const CountdownCard: React.FC<CountdownCardProps> = ({
  label,
  value,
  unit,
  date,
  variant = 'counter',
  palette: paletteInput,
  fonts: fontInput,
  placement = 'center',
  ...motionProps
}) => {
  const palette = resolvePalette(paletteInput);
  const fonts = resolveFonts(fontInput);
  const {reveal, visible} = useOverlayMotion(motionProps);
  const urgent = variant === 'urgent';
  const calendar = variant === 'calendar';
  return (
    <OverlayFill placement={placement} opacity={visible} style={{alignItems: 'center'}}>
      <div style={{alignItems: 'center', background: urgent ? palette.accent : palette.surface, border: `5px solid ${urgent ? palette.text : palette.accent}`, boxShadow: '0 26px 70px rgba(0,0,0,.45)', color: urgent ? palette.ink : palette.text, display: 'flex', flexDirection: calendar ? 'row' : 'column', gap: calendar ? 30 : 8, justifyContent: 'center', minHeight: 330, opacity: reveal, padding: '38px 48px', textAlign: 'center', transform: `scale(${0.78 + reveal * 0.22}) rotate(${(1 - reveal) * -4}deg)`, width: calendar ? 770 : 650}}>
        <div>
          <div style={{color: urgent ? palette.ink : palette.accent, fontFamily: fonts.body, fontSize: 23, fontWeight: 900, letterSpacing: 5, textTransform: 'uppercase'}}>{label}</div>
          {date ? <div style={{fontFamily: fonts.body, fontSize: 27, fontWeight: 700, marginTop: 11}}>{date}</div> : null}
        </div>
        {calendar ? <div style={{background: urgent ? palette.ink : palette.accent, height: 180, opacity: 0.35, width: 4}} /> : null}
        <div style={{fontFamily: fonts.display, fontSize: value.length > 6 ? 112 : 176, lineHeight: 0.8}}>{value}</div>
        {unit ? <div style={{fontFamily: fonts.body, fontSize: 26, fontWeight: 900, letterSpacing: 4, textTransform: 'uppercase'}}>{unit}</div> : null}
      </div>
    </OverlayFill>
  );
};

export type CTAEndCardProps = ReelOverlayBaseProps & {
  headline: string;
  action: string;
  subheadline?: string;
  logoSrc?: string;
  phone?: string;
  url?: string;
  location?: string;
  urgency?: string;
  variant?: 'centered' | 'banner' | 'minimal';
};

export const CTAEndCard: React.FC<CTAEndCardProps> = ({
  headline,
  action,
  subheadline,
  logoSrc,
  phone,
  url,
  location,
  urgency,
  variant = 'centered',
  palette: paletteInput,
  fonts: fontInput,
  placement = 'center',
  ...motionProps
}) => {
  const palette = resolvePalette(paletteInput);
  const fonts = resolveFonts(fontInput);
  const {reveal, visible} = useOverlayMotion(motionProps);
  const banner = variant === 'banner';
  const minimal = variant === 'minimal';
  return (
    <OverlayFill placement={placement} opacity={visible} style={{alignItems: 'center', background: minimal ? 'transparent' : `${palette.ink}B8`}}>
      <div style={{alignItems: banner ? 'flex-start' : 'center', background: banner ? palette.surface : 'transparent', borderLeft: banner ? `12px solid ${palette.accent}` : undefined, display: 'flex', flexDirection: 'column', opacity: reveal, padding: banner ? '44px 42px' : 0, textAlign: banner ? 'left' : 'center', transform: `translateY(${(1 - reveal) * 70}px) scale(${0.94 + reveal * 0.06})`, width: '100%'}}>
        {logoSrc ? <Img src={logoSrc} style={{maxHeight: 230, objectFit: 'contain', width: banner ? 230 : 310}} /> : null}
        {urgency ? <div style={{background: palette.accent, color: palette.ink, fontFamily: fonts.body, fontSize: 21, fontWeight: 900, letterSpacing: 4, marginTop: logoSrc ? 24 : 0, padding: '11px 16px 9px', textTransform: 'uppercase'}}>{urgency}</div> : null}
        <div style={{color: palette.text, fontFamily: fonts.display, fontSize: headline.length > 34 ? 58 : 76, lineHeight: 1, marginTop: urgency || logoSrc ? 22 : 0, maxWidth: 900}}>{headline}</div>
        {subheadline ? <div style={{color: palette.muted, fontFamily: fonts.body, fontSize: 29, lineHeight: 1.25, marginTop: 18, maxWidth: 820}}>{subheadline}</div> : null}
        <div style={{background: palette.accent, color: palette.ink, fontFamily: fonts.body, fontSize: 28, fontWeight: 900, letterSpacing: 3, marginTop: 30, padding: '18px 30px 16px', textTransform: 'uppercase'}}>{action}</div>
        {phone ? <div style={{color: palette.text, fontFamily: fonts.display, fontSize: 58, marginTop: 28}}>{phone}</div> : null}
        {url ? <div style={{color: palette.accent, fontFamily: fonts.body, fontSize: 25, marginTop: 12, overflowWrap: 'anywhere'}}>{url}</div> : null}
        {location ? <div style={{color: palette.muted, fontFamily: fonts.body, fontSize: 20, letterSpacing: 3, marginTop: 15, textTransform: 'uppercase'}}>{location}</div> : null}
      </div>
    </OverlayFill>
  );
};

// Semantic aliases make fixture/rendering code read naturally without creating
// duplicate implementations.
export const QuoteCard = TestimonialCard;
export const LocationScheduleChips = InfoChips;
export const DeadlineCard = CountdownCard;
export const MatchupCard = VersusCard;
export const SubtitlePanel = CaptionPanel;
export const EndCard = CTAEndCard;
