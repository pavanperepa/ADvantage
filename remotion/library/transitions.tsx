import React, {type CSSProperties, type ReactNode} from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from 'remotion';

export type ReelTransitionVariant =
  | 'none'
  | 'fade'
  | 'directional-wipe'
  | 'slide'
  | 'push'
  | 'zoom'
  | 'flash'
  | 'glitch-lite'
  | 'shutter'
  | 'bars'
  | 'iris';

export type TransitionDirection = 'left' | 'right' | 'up' | 'down';
export type TransitionPhase = 'enter' | 'exit';

export type ReelTransitionProps = {
  /** The incoming/current layer. */
  children: ReactNode;
  /** Optional outgoing layer. Useful for a true push rather than a slide-in. */
  previous?: ReactNode;
  variant?: ReelTransitionVariant;
  direction?: TransitionDirection;
  phase?: TransitionPhase;
  durationInFrames?: number;
  /** Supply a controlled 0..1 progress value when coordinating two Sequences. */
  progress?: number;
  accentColor?: string;
  backgroundColor?: string;
  /** Scales movement and flashes without changing timing. Recommended range: 0..1. */
  intensity?: number;
  style?: CSSProperties;
};

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

const directionVector = (direction: TransitionDirection) => {
  switch (direction) {
    case 'right':
      return {x: -1, y: 0};
    case 'up':
      return {x: 0, y: 1};
    case 'down':
      return {x: 0, y: -1};
    case 'left':
    default:
      return {x: 1, y: 0};
  }
};

const wipeClip = (direction: TransitionDirection, progress: number) => {
  const hidden = 100 - progress * 100;
  switch (direction) {
    case 'right':
      return `inset(0 0 0 ${hidden}%)`;
    case 'up':
      return `inset(${hidden}% 0 0 0)`;
    case 'down':
      return `inset(0 0 ${hidden}% 0)`;
    case 'left':
    default:
      return `inset(0 ${hidden}% 0 0)`;
  }
};

const edgeStyle = (direction: TransitionDirection, progress: number, color: string): CSSProperties => {
  const position = progress * 100;
  const shared: CSSProperties = {
    position: 'absolute',
    backgroundColor: color,
    boxShadow: `0 0 28px ${color}88`,
  };
  switch (direction) {
    case 'right':
      return {...shared, top: 0, bottom: 0, right: `${position - 1.2}%`, width: 14};
    case 'up':
      return {...shared, left: 0, right: 0, bottom: `${position - 1.2}%`, height: 14};
    case 'down':
      return {...shared, left: 0, right: 0, top: `${position - 1.2}%`, height: 14};
    case 'left':
    default:
      return {...shared, top: 0, bottom: 0, left: `${position - 1.2}%`, width: 14};
  }
};

const FrameLayer: React.FC<{children: ReactNode; style?: CSSProperties}> = ({children, style}) => (
  <AbsoluteFill style={{overflow: 'hidden', ...style}}>{children}</AbsoluteFill>
);

/**
 * A deterministic, dependency-free transition wrapper for reel shots.
 * Place it inside a Sequence so useCurrentFrame() starts at that shot's frame 0,
 * or supply progress explicitly when coordinating overlapping Sequences.
 */
export const ReelTransition: React.FC<ReelTransitionProps> = ({
  children,
  previous,
  variant = 'fade',
  direction = 'left',
  phase = 'enter',
  durationInFrames = 12,
  progress: controlledProgress,
  accentColor = '#FFD437',
  backgroundColor = '#061008',
  intensity = 0.65,
  style,
}) => {
  const frame = useCurrentFrame();
  const safeDuration = Math.max(1, durationInFrames);
  const rawProgress = controlledProgress ?? interpolate(frame, [0, safeDuration], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const enterProgress = clamp(rawProgress, 0, 1);
  const progress = phase === 'enter' ? enterProgress : 1 - enterProgress;
  const motionStrength = clamp(intensity, 0, 1);
  const vector = directionVector(direction);
  const translateDistance = 100 * (1 - progress);
  const flashOpacity = (1 - progress) * 0.56 * motionStrength;
  const localFrame = Math.max(0, Math.min(frame, safeDuration));

  let currentStyle: CSSProperties = {};
  let previousStyle: CSSProperties = {};
  let overlay: ReactNode = null;

  switch (variant) {
    case 'none':
      break;
    case 'fade':
      currentStyle = {opacity: progress};
      previousStyle = {opacity: 1 - progress};
      break;
    case 'directional-wipe':
      currentStyle = {clipPath: wipeClip(direction, progress)};
      overlay = progress < 1 ? <div style={edgeStyle(direction, progress, accentColor)} /> : null;
      break;
    case 'slide':
      currentStyle = {
        transform: `translate3d(${vector.x * translateDistance}%, ${vector.y * translateDistance}%, 0)`,
      };
      break;
    case 'push':
      currentStyle = {
        transform: `translate3d(${vector.x * translateDistance}%, ${vector.y * translateDistance}%, 0)`,
      };
      previousStyle = {
        transform: `translate3d(${-vector.x * progress * 100}%, ${-vector.y * progress * 100}%, 0)`,
      };
      break;
    case 'zoom': {
      const scale = interpolate(progress, [0, 1], [1 + 0.16 * motionStrength, 1]);
      currentStyle = {
        opacity: interpolate(progress, [0, 0.28, 1], [0, 1, 1]),
        transform: `scale(${scale})`,
        filter: `blur(${(1 - progress) * 7 * motionStrength}px)`,
      };
      previousStyle = {opacity: 1 - progress, transform: `scale(${1 - progress * 0.045 * motionStrength})`};
      break;
    }
    case 'flash':
      currentStyle = {opacity: interpolate(progress, [0, 0.16, 1], [0.35, 1, 1])};
      overlay = <AbsoluteFill style={{backgroundColor: accentColor, opacity: flashOpacity, mixBlendMode: 'screen'}} />;
      break;
    case 'glitch-lite': {
      const active = progress < 0.78;
      const pulse = active ? Math.sin(localFrame * 2.75) : 0;
      const offset = pulse * 14 * motionStrength * (1 - progress);
      currentStyle = {
        opacity: interpolate(progress, [0, 0.14, 1], [0.35, 1, 1]),
        transform: `translateX(${offset}px)`,
      };
      overlay = active ? (
        <>
          <AbsoluteFill
            style={{
              clipPath: `inset(${18 + (localFrame * 17) % 58}% 0 ${58 - (localFrame * 11) % 34}% 0)`,
              transform: `translateX(${-offset * 1.8}px)`,
              opacity: 0.22 * motionStrength * (1 - progress),
              backgroundColor: accentColor,
              mixBlendMode: 'screen',
            }}
          />
          <AbsoluteFill
            style={{
              background: 'repeating-linear-gradient(0deg, transparent 0 5px, rgba(255,255,255,.16) 5px 6px)',
              opacity: 0.18 * motionStrength * (1 - progress),
            }}
          />
        </>
      ) : null;
      break;
    }
    case 'shutter': {
      const open = progress * 50;
      currentStyle = {opacity: interpolate(progress, [0, 0.12, 1], [0.6, 1, 1])};
      overlay = (
        <AbsoluteFill style={{pointerEvents: 'none'}}>
          <div style={{position: 'absolute', inset: 0, bottom: `${50 + open}%`, backgroundColor}} />
          <div style={{position: 'absolute', inset: 0, top: `${50 + open}%`, backgroundColor}} />
        </AbsoluteFill>
      );
      break;
    }
    case 'bars': {
      const bars = Array.from({length: 8}, (_, index) => {
        const delay = index * 0.035;
        const barProgress = clamp((progress - delay) / (1 - 0.035 * 7), 0, 1);
        return (
          <div
            key={index}
            style={{
              position: 'absolute',
              left: `${index * 12.5}%`,
              top: 0,
              bottom: 0,
              width: '12.6%',
              backgroundColor,
              transform: `translateY(${barProgress * -101}%)`,
            }}
          />
        );
      });
      overlay = <AbsoluteFill style={{pointerEvents: 'none'}}>{bars}</AbsoluteFill>;
      break;
    }
    case 'iris':
      currentStyle = {clipPath: `circle(${progress * 76}% at 50% 50%)`};
      overlay = progress < 1 ? (
        <AbsoluteFill
          style={{
            background: `radial-gradient(circle at center, transparent ${Math.max(0, progress * 76 - 1.2)}%, ${accentColor} ${progress * 76}%, transparent ${Math.min(100, progress * 76 + 1.5)}%)`,
            opacity: 0.55 * motionStrength,
          }}
        />
      ) : null;
      break;
    default: {
      const exhaustive: never = variant;
      throw new Error(`Unsupported reel transition: ${exhaustive}`);
    }
  }

  return (
    <AbsoluteFill style={{backgroundColor, overflow: 'hidden', ...style}}>
      {previous ? <FrameLayer style={previousStyle}>{previous}</FrameLayer> : null}
      <FrameLayer style={currentStyle}>{children}</FrameLayer>
      {overlay}
    </AbsoluteFill>
  );
};
