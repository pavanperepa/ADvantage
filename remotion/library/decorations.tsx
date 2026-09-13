import React, {type CSSProperties, type ReactNode} from 'react';
import {AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

export type Edge = 'top' | 'bottom';

type OverlayProps = {
  opacity?: number;
  style?: CSSProperties;
};

const seededValue = (seed: number) => {
  const value = Math.sin(seed * 12.9898 + 78.233) * 43758.5453;
  return value - Math.floor(value);
};

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

/** Edge-weighted contrast that leaves the middle of the footage clear. */
export const GradientScrim: React.FC<OverlayProps & {
  color?: string;
  topStrength?: number;
  bottomStrength?: number;
}> = ({color = '3, 11, 8', topStrength = 0.18, bottomStrength = 0.48, opacity = 1, style}) => (
  <AbsoluteFill
    style={{
      pointerEvents: 'none',
      background: `linear-gradient(180deg, rgba(${color},${clamp(topStrength, 0, 1)}) 0%, rgba(${color},0) 34%, rgba(${color},0) 58%, rgba(${color},${clamp(bottomStrength, 0, 1)}) 100%)`,
      opacity,
      ...style,
    }}
  />
);

export const Vignette: React.FC<OverlayProps & {color?: string; strength?: number}> = ({
  color = '0, 0, 0',
  strength = 0.42,
  opacity = 1,
  style,
}) => (
  <AbsoluteFill
    style={{
      pointerEvents: 'none',
      background: `radial-gradient(ellipse at center, transparent 48%, rgba(${color},${clamp(strength, 0, 0.75)}) 100%)`,
      opacity,
      ...style,
    }}
  />
);

export const ProgressRail: React.FC<OverlayProps & {
  color?: string;
  trackColor?: string;
  edge?: Edge;
  inset?: number;
  thickness?: number;
  progress?: number;
  label?: string;
}> = ({
  color = '#FFD437',
  trackColor = 'rgba(255,255,255,.22)',
  edge = 'top',
  inset = 54,
  thickness = 4,
  progress: controlledProgress,
  label,
  opacity = 1,
  style,
}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const progress = clamp(controlledProgress ?? frame / Math.max(1, durationInFrames - 1), 0, 1);
  return (
    <div
      style={{
        position: 'absolute',
        left: inset,
        right: inset,
        [edge]: inset,
        height: thickness,
        backgroundColor: trackColor,
        opacity,
        pointerEvents: 'none',
        ...style,
      }}
    >
      <div style={{height: '100%', width: `${progress * 100}%`, backgroundColor: color}} />
      {label ? (
        <div style={{position: 'absolute', top: edge === 'top' ? 14 : -34, left: 0, color: 'white', fontFamily: 'Body', fontSize: 18, letterSpacing: 3, textShadow: '0 2px 8px rgba(0,0,0,.8)'}}>
          {label}
        </div>
      ) : null}
    </div>
  );
};

export const CornerBrackets: React.FC<OverlayProps & {
  color?: string;
  inset?: number;
  size?: number;
  thickness?: number;
  animate?: boolean;
}> = ({color = '#FFD437', inset = 56, size = 54, thickness = 5, animate = true, opacity = 0.82, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const reveal = animate ? spring({frame, fps, config: {damping: 18, stiffness: 120}}) : 1;
  const corners = [
    {top: inset, left: inset, borderTop: `${thickness}px solid ${color}`, borderLeft: `${thickness}px solid ${color}`},
    {top: inset, right: inset, borderTop: `${thickness}px solid ${color}`, borderRight: `${thickness}px solid ${color}`},
    {bottom: inset, left: inset, borderBottom: `${thickness}px solid ${color}`, borderLeft: `${thickness}px solid ${color}`},
    {bottom: inset, right: inset, borderBottom: `${thickness}px solid ${color}`, borderRight: `${thickness}px solid ${color}`},
  ] satisfies CSSProperties[];
  return (
    <AbsoluteFill style={{pointerEvents: 'none', opacity: opacity * reveal, ...style}}>
      {corners.map((corner, index) => (
        <div key={index} style={{position: 'absolute', width: size * reveal, height: size * reveal, ...corner}} />
      ))}
    </AbsoluteFill>
  );
};

export const AccentBars: React.FC<OverlayProps & {
  colors?: readonly string[];
  edge?: Edge;
  inset?: number;
  width?: number;
  height?: number;
  gap?: number;
}> = ({colors = ['#8CC63F', '#FFD437'], edge = 'bottom', inset = 58, width = 92, height = 7, gap = 10, opacity = 1, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const reveal = spring({frame, fps, config: {damping: 20, stiffness: 130}});
  return (
    <div style={{position: 'absolute', left: inset, [edge]: inset, display: 'flex', gap, opacity, pointerEvents: 'none', ...style}}>
      {colors.map((color, index) => (
        <div key={`${color}-${index}`} style={{width: width * reveal * (1 - index * 0.14), height, backgroundColor: color}} />
      ))}
    </div>
  );
};

export const GridPattern: React.FC<OverlayProps & {
  color?: string;
  size?: number;
  lineWidth?: number;
  mask?: 'full' | 'edges' | 'bottom';
}> = ({color = 'rgba(255,255,255,.12)', size = 72, lineWidth = 1, mask = 'edges', opacity = 0.32, style}) => {
  const maskImage = mask === 'bottom'
    ? 'linear-gradient(to bottom, transparent 35%, black 100%)'
    : mask === 'edges'
      ? 'radial-gradient(ellipse at center, transparent 30%, black 100%)'
      : undefined;
  return (
    <AbsoluteFill
      style={{
        pointerEvents: 'none',
        backgroundImage: `linear-gradient(${color} ${lineWidth}px, transparent ${lineWidth}px), linear-gradient(90deg, ${color} ${lineWidth}px, transparent ${lineWidth}px)`,
        backgroundSize: `${size}px ${size}px`,
        maskImage,
        WebkitMaskImage: maskImage,
        opacity,
        ...style,
      }}
    />
  );
};

export const DotPattern: React.FC<OverlayProps & {
  color?: string;
  spacing?: number;
  radius?: number;
  mask?: 'full' | 'edges' | 'bottom';
}> = ({color = 'rgba(255,255,255,.28)', spacing = 42, radius = 2, mask = 'bottom', opacity = 0.42, style}) => {
  const maskImage = mask === 'bottom'
    ? 'linear-gradient(to bottom, transparent 45%, black 100%)'
    : mask === 'edges'
      ? 'radial-gradient(ellipse at center, transparent 32%, black 100%)'
      : undefined;
  return (
    <AbsoluteFill
      style={{
        pointerEvents: 'none',
        backgroundImage: `radial-gradient(circle, ${color} 0 ${radius}px, transparent ${radius + 0.5}px)`,
        backgroundSize: `${spacing}px ${spacing}px`,
        maskImage,
        WebkitMaskImage: maskImage,
        opacity,
        ...style,
      }}
    />
  );
};

export const Ticker: React.FC<OverlayProps & {
  items: readonly string[];
  color?: string;
  backgroundColor?: string;
  edge?: Edge;
  speed?: number;
  separator?: ReactNode;
  fontSize?: number;
  reverse?: boolean;
}> = ({
  items,
  color = '#061008',
  backgroundColor = '#FFD437',
  edge = 'bottom',
  speed = 2.4,
  separator = ' • ',
  fontSize = 24,
  reverse = false,
  opacity = 0.96,
  style,
}) => {
  const frame = useCurrentFrame();
  const content = items.length > 0 ? items : [''];
  const repeated = [...content, ...content, ...content, ...content];
  const distance = ((frame * speed) % 50) * (reverse ? -1 : 1);
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        [edge]: 0,
        overflow: 'hidden',
        whiteSpace: 'nowrap',
        color,
        backgroundColor,
        opacity,
        fontFamily: 'Body',
        fontSize,
        fontWeight: 700,
        letterSpacing: 3,
        lineHeight: 1,
        padding: '15px 0 13px',
        pointerEvents: 'none',
        ...style,
      }}
    >
      <div style={{display: 'inline-flex', minWidth: '220%', transform: `translateX(${-25 - distance}%)`}}>
        {repeated.map((item, index) => (
          <React.Fragment key={`${item}-${index}`}>
            <span>{item}</span>
            <span style={{padding: '0 24px'}}>{separator}</span>
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};

export const FloatingParticles: React.FC<OverlayProps & {
  count?: number;
  colors?: readonly string[];
  seed?: number;
  speed?: number;
  minSize?: number;
  maxSize?: number;
  confetti?: boolean;
}> = ({
  count = 18,
  colors = ['#FFD437', '#8CC63F', '#FFFFFF'],
  seed = 22,
  speed = 0.7,
  minSize = 3,
  maxSize = 8,
  confetti = false,
  opacity = 0.38,
  style,
}) => {
  const frame = useCurrentFrame();
  const {height} = useVideoConfig();
  const particles = Array.from({length: Math.max(0, Math.round(count))}, (_, index) => {
    const x = seededValue(seed + index * 5.31) * 100;
    const baseY = seededValue(seed + index * 7.77) * height;
    const size = interpolate(seededValue(seed + index * 3.17), [0, 1], [minSize, maxSize]);
    const travel = frame * speed * (0.55 + seededValue(seed + index * 9.91));
    const y = ((baseY - travel) % (height + 80) + height + 80) % (height + 80) - 40;
    const rotation = frame * (0.5 + seededValue(seed + index * 2.43) * 1.8) + index * 31;
    return (
      <div
        key={index}
        style={{
          position: 'absolute',
          left: `${x}%`,
          top: y,
          width: confetti ? size * 0.62 : size,
          height: confetti ? size * 2.25 : size,
          borderRadius: confetti ? 1 : '50%',
          backgroundColor: colors[index % Math.max(1, colors.length)] ?? '#FFFFFF',
          transform: `rotate(${rotation}deg)`,
        }}
      />
    );
  });
  return <AbsoluteFill style={{pointerEvents: 'none', overflow: 'hidden', opacity, ...style}}>{particles}</AbsoluteFill>;
};

export const FocusCircle: React.FC<OverlayProps & {
  x?: number | string;
  y?: number | string;
  size?: number;
  color?: string;
  thickness?: number;
  label?: string;
}> = ({x = '50%', y = '50%', size = 190, color = '#FFD437', thickness = 6, label, opacity = 0.9, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const reveal = spring({frame, fps, config: {damping: 17, stiffness: 115}});
  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: y,
        width: size,
        height: size,
        border: `${thickness}px solid ${color}`,
        borderRadius: '50%',
        transform: `translate(-50%, -50%) scale(${0.72 + reveal * 0.28})`,
        opacity: opacity * reveal,
        boxShadow: `0 0 20px ${color}55`,
        pointerEvents: 'none',
        ...style,
      }}
    >
      {label ? <div style={{position: 'absolute', top: '100%', left: '50%', transform: 'translateX(-50%)', marginTop: 12, color: 'white', fontFamily: 'Body', fontSize: 18, letterSpacing: 2, textShadow: '0 2px 8px rgba(0,0,0,.9)', whiteSpace: 'nowrap'}}>{label}</div> : null}
    </div>
  );
};

export const PointerArrow: React.FC<OverlayProps & {
  x?: number | string;
  y?: number | string;
  length?: number;
  color?: string;
  thickness?: number;
  rotation?: number;
  pulse?: boolean;
}> = ({x = '50%', y = '50%', length = 140, color = '#FFD437', thickness = 7, rotation = -18, pulse = true, opacity = 0.92, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const reveal = spring({frame, fps, config: {damping: 18, stiffness: 120}});
  const nudge = pulse ? Math.sin((frame / fps) * Math.PI * 2) * 5 : 0;
  return (
    <div style={{position: 'absolute', left: x, top: y, width: length, height: 40, transform: `translateY(${nudge}px) rotate(${rotation}deg) scaleX(${reveal})`, transformOrigin: 'left center', opacity: opacity * reveal, pointerEvents: 'none', ...style}}>
      <div style={{position: 'absolute', left: 0, right: 14, top: 17, height: thickness, borderRadius: thickness, backgroundColor: color}} />
      <div style={{position: 'absolute', right: 0, top: 7, width: 25, height: 25, borderTop: `${thickness}px solid ${color}`, borderRight: `${thickness}px solid ${color}`, transform: 'rotate(45deg)'}} />
    </div>
  );
};

/** A subtle deterministic texture; unlike random noise it renders identically every time. */
export const FilmGrain: React.FC<OverlayProps & {strength?: number; scale?: number}> = ({
  strength = 0.09,
  scale = 1,
  opacity = 1,
  style,
}) => {
  const frame = useCurrentFrame();
  const offsetX = (frame * 17) % 31;
  const offsetY = (frame * 29) % 37;
  const safeScale = Math.max(0.5, scale);
  return (
    <AbsoluteFill
      style={{
        pointerEvents: 'none',
        backgroundImage: [
          'repeating-radial-gradient(circle at 17% 23%, rgba(255,255,255,.36) 0 1px, transparent 1px 4px)',
          'repeating-radial-gradient(circle at 71% 67%, rgba(0,0,0,.42) 0 1px, transparent 1px 5px)',
        ].join(','),
        backgroundSize: `${17 * safeScale}px ${19 * safeScale}px, ${23 * safeScale}px ${21 * safeScale}px`,
        backgroundPosition: `${offsetX}px ${offsetY}px, ${-offsetY}px ${offsetX}px`,
        mixBlendMode: 'soft-light',
        opacity: clamp(strength, 0, 0.24) * opacity,
        ...style,
      }}
    />
  );
};

/** Convenience host for grouping multiple pointer-events-safe decoration layers. */
export const DecorationLayer: React.FC<{children: ReactNode; style?: CSSProperties}> = ({children, style}) => (
  <AbsoluteFill style={{pointerEvents: 'none', overflow: 'hidden', ...style}}>{children}</AbsoluteFill>
);
