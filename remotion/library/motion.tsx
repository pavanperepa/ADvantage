import React from 'react';
import {Easing, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

export type MotionEasing = (value: number) => number;
export type SlideDirection = 'up' | 'down' | 'left' | 'right';
export type RevealDirection = 'left-to-right' | 'right-to-left' | 'top-to-bottom' | 'bottom-to-top';
export type LineOrientation = 'horizontal' | 'vertical';

export type MotionWrapperProps = {
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
  delayInFrames?: number;
  durationInFrames?: number;
};

export type ExitMotionProps = {
  exitAtFrame?: number;
  exitDurationInFrames?: number;
};

export type SpringTuning = {
  damping?: number;
  stiffness?: number;
  mass?: number;
  overshootClamping?: boolean;
};

const clamp = (value: number, minimum = 0, maximum = 1): number =>
  Math.min(maximum, Math.max(minimum, value));

const safeDuration = (durationInFrames: number): number => Math.max(1, durationInFrames);

const progressFor = (
  frame: number,
  delayInFrames: number,
  durationInFrames: number,
  easing: MotionEasing = Easing.linear,
): number =>
  interpolate(
    frame,
    [delayInFrames, delayInFrames + safeDuration(durationInFrames)],
    [0, 1],
    {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing,
    },
  );

const exitProgressFor = (
  frame: number,
  exitAtFrame: number | undefined,
  exitDurationInFrames: number,
  easing: MotionEasing = Easing.in(Easing.cubic),
): number => {
  if (exitAtFrame === undefined) {
    return 1;
  }

  return interpolate(
    frame,
    [exitAtFrame, exitAtFrame + safeDuration(exitDurationInFrames)],
    [1, 0],
    {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing,
    },
  );
};

const directionOffset = (direction: SlideDirection, distance: number): {x: number; y: number} => {
  switch (direction) {
    case 'up':
      return {x: 0, y: distance};
    case 'down':
      return {x: 0, y: -distance};
    case 'left':
      return {x: distance, y: 0};
    case 'right':
      return {x: -distance, y: 0};
  }
};

export type FadeProps = MotionWrapperProps &
  ExitMotionProps & {
    from?: number;
    to?: number;
    easing?: MotionEasing;
  };

export const Fade: React.FC<FadeProps> = ({
  children,
  className,
  style,
  delayInFrames = 0,
  durationInFrames = 12,
  exitAtFrame,
  exitDurationInFrames = 10,
  from = 0,
  to = 1,
  easing = Easing.out(Easing.cubic),
}) => {
  const frame = useCurrentFrame();
  const enter = progressFor(frame, delayInFrames, durationInFrames, easing);
  const exit = exitProgressFor(frame, exitAtFrame, exitDurationInFrames);
  const opacity = interpolate(enter, [0, 1], [from, to]) * exit;

  return (
    <div className={className} style={{...style, opacity: clamp(opacity, 0, 1)}}>
      {children}
    </div>
  );
};

export type SlideProps = MotionWrapperProps &
  ExitMotionProps & {
    direction?: SlideDirection;
    distance?: number;
    easing?: MotionEasing;
    fade?: boolean;
  };

export const Slide: React.FC<SlideProps> = ({
  children,
  className,
  style,
  delayInFrames = 0,
  durationInFrames = 16,
  exitAtFrame,
  exitDurationInFrames = 10,
  direction = 'up',
  distance = 60,
  easing = Easing.out(Easing.cubic),
  fade = true,
}) => {
  const frame = useCurrentFrame();
  const enter = progressFor(frame, delayInFrames, durationInFrames, easing);
  const exit = exitProgressFor(frame, exitAtFrame, exitDurationInFrames);
  const offset = directionOffset(direction, distance);
  const exitOffset = directionOffset(direction, -distance * 0.35);
  const translateX = offset.x * (1 - enter) + exitOffset.x * (1 - exit);
  const translateY = offset.y * (1 - enter) + exitOffset.y * (1 - exit);

  return (
    <div
      className={className}
      style={{
        ...style,
        opacity: fade ? clamp(enter * exit) : style?.opacity,
        transform: `translate3d(${translateX}px, ${translateY}px, 0)`,
        willChange: 'transform, opacity',
      }}
    >
      {children}
    </div>
  );
};

export type ScaleProps = MotionWrapperProps &
  ExitMotionProps & {
    from?: number;
    to?: number;
    easing?: MotionEasing;
    fade?: boolean;
    transformOrigin?: React.CSSProperties['transformOrigin'];
  };

export const Scale: React.FC<ScaleProps> = ({
  children,
  className,
  style,
  delayInFrames = 0,
  durationInFrames = 14,
  exitAtFrame,
  exitDurationInFrames = 10,
  from = 0.86,
  to = 1,
  easing = Easing.out(Easing.back(1.25)),
  fade = true,
  transformOrigin = 'center',
}) => {
  const frame = useCurrentFrame();
  const enter = progressFor(frame, delayInFrames, durationInFrames, easing);
  const exit = exitProgressFor(frame, exitAtFrame, exitDurationInFrames);
  const scale = interpolate(enter, [0, 1], [from, to]) * interpolate(exit, [0, 1], [0.96, 1]);

  return (
    <div
      className={className}
      style={{
        ...style,
        opacity: fade ? clamp(enter * exit) : style?.opacity,
        transform: `scale(${scale})`,
        transformOrigin,
        willChange: 'transform, opacity',
      }}
    >
      {children}
    </div>
  );
};

export type PopProps = MotionWrapperProps & {
  from?: number;
  tuning?: SpringTuning;
  fade?: boolean;
  transformOrigin?: React.CSSProperties['transformOrigin'];
};

export const Pop: React.FC<PopProps> = ({
  children,
  className,
  style,
  delayInFrames = 0,
  from = 0.4,
  tuning = {damping: 10, stiffness: 180, mass: 0.7},
  fade = true,
  transformOrigin = 'center',
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const value = spring({frame: frame - delayInFrames, fps, config: tuning});
  const opacity = progressFor(frame, delayInFrames, 7, Easing.out(Easing.quad));

  return (
    <div
      className={className}
      style={{
        ...style,
        opacity: fade ? opacity : style?.opacity,
        transform: `scale(${from + (1 - from) * value})`,
        transformOrigin,
        willChange: 'transform, opacity',
      }}
    >
      {children}
    </div>
  );
};

export type SpringRevealProps = MotionWrapperProps & {
  direction?: SlideDirection;
  distance?: number;
  fromScale?: number;
  fade?: boolean;
  tuning?: SpringTuning;
};

export const SpringReveal: React.FC<SpringRevealProps> = ({
  children,
  className,
  style,
  delayInFrames = 0,
  direction = 'up',
  distance = 48,
  fromScale = 0.96,
  fade = true,
  tuning = {damping: 18, stiffness: 125, mass: 0.9},
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const value = spring({frame: frame - delayInFrames, fps, config: tuning});
  const visibleValue = clamp(value);
  const offset = directionOffset(direction, distance);

  return (
    <div
      className={className}
      style={{
        ...style,
        opacity: fade ? visibleValue : style?.opacity,
        transform: `translate3d(${offset.x * (1 - value)}px, ${offset.y * (1 - value)}px, 0) scale(${fromScale + (1 - fromScale) * value})`,
        willChange: 'transform, opacity',
      }}
    >
      {children}
    </div>
  );
};

export type MaskRevealProps = MotionWrapperProps & {
  direction?: RevealDirection;
  easing?: MotionEasing;
  fade?: boolean;
};

const clipInset = (direction: RevealDirection, hiddenPercent: number): string => {
  switch (direction) {
    case 'left-to-right':
      return `inset(0 ${hiddenPercent}% 0 0)`;
    case 'right-to-left':
      return `inset(0 0 0 ${hiddenPercent}%)`;
    case 'top-to-bottom':
      return `inset(0 0 ${hiddenPercent}% 0)`;
    case 'bottom-to-top':
      return `inset(${hiddenPercent}% 0 0 0)`;
  }
};

export const MaskReveal: React.FC<MaskRevealProps> = ({
  children,
  className,
  style,
  delayInFrames = 0,
  durationInFrames = 18,
  direction = 'left-to-right',
  easing = Easing.inOut(Easing.cubic),
  fade = false,
}) => {
  const frame = useCurrentFrame();
  const progress = progressFor(frame, delayInFrames, durationInFrames, easing);

  return (
    <div
      className={className}
      style={{
        ...style,
        clipPath: clipInset(direction, (1 - progress) * 100),
        opacity: fade ? progress : style?.opacity,
        willChange: 'clip-path, opacity',
      }}
    >
      {children}
    </div>
  );
};

export type BlurRevealProps = MotionWrapperProps & {
  blur?: number;
  easing?: MotionEasing;
  fade?: boolean;
  fromScale?: number;
};

export const BlurReveal: React.FC<BlurRevealProps> = ({
  children,
  className,
  style,
  delayInFrames = 0,
  durationInFrames = 14,
  blur = 18,
  easing = Easing.out(Easing.cubic),
  fade = true,
  fromScale = 1.03,
}) => {
  const frame = useCurrentFrame();
  const progress = progressFor(frame, delayInFrames, durationInFrames, easing);

  return (
    <div
      className={className}
      style={{
        ...style,
        filter: `blur(${Math.max(0, blur * (1 - progress))}px)`,
        opacity: fade ? progress : style?.opacity,
        transform: `scale(${fromScale + (1 - fromScale) * progress})`,
        willChange: 'filter, transform, opacity',
      }}
    >
      {children}
    </div>
  );
};

export type StaggeredTextProps = {
  text: string;
  className?: string;
  style?: React.CSSProperties;
  itemStyle?: React.CSSProperties;
  delayInFrames?: number;
  staggerInFrames?: number;
  durationInFrames?: number;
  distance?: number;
  direction?: SlideDirection;
  easing?: MotionEasing;
};

const AnimatedTextUnit: React.FC<{
  children: React.ReactNode;
  frame: number;
  delay: number;
  duration: number;
  direction: SlideDirection;
  distance: number;
  easing: MotionEasing;
  style?: React.CSSProperties;
}> = ({children, frame, delay, duration, direction, distance, easing, style}) => {
  const progress = progressFor(frame, delay, duration, easing);
  const offset = directionOffset(direction, distance);

  return (
    <span
      aria-hidden="true"
      style={{
        ...style,
        display: 'inline-block',
        opacity: progress,
        transform: `translate3d(${offset.x * (1 - progress)}px, ${offset.y * (1 - progress)}px, 0)`,
        willChange: 'transform, opacity',
      }}
    >
      {children}
    </span>
  );
};

export const StaggeredWords: React.FC<StaggeredTextProps> = ({
  text,
  className,
  style,
  itemStyle,
  delayInFrames = 0,
  staggerInFrames = 3,
  durationInFrames = 10,
  distance = 36,
  direction = 'up',
  easing = Easing.out(Easing.cubic),
}) => {
  const frame = useCurrentFrame();
  const words = text.trim().length === 0 ? [] : text.trim().split(/\s+/u);

  return (
    <span className={className} style={style} aria-label={text}>
      {words.map((word, index) => (
        <React.Fragment key={`${word}-${index}`}>
          {index > 0 ? ' ' : null}
          <AnimatedTextUnit
            frame={frame}
            delay={delayInFrames + index * staggerInFrames}
            duration={durationInFrames}
            direction={direction}
            distance={distance}
            easing={easing}
            style={itemStyle}
          >
            {word}
          </AnimatedTextUnit>
        </React.Fragment>
      ))}
    </span>
  );
};

export const StaggeredCharacters: React.FC<StaggeredTextProps> = ({
  text,
  className,
  style,
  itemStyle,
  delayInFrames = 0,
  staggerInFrames = 1,
  durationInFrames = 8,
  distance = 24,
  direction = 'up',
  easing = Easing.out(Easing.cubic),
}) => {
  const frame = useCurrentFrame();

  return (
    <span className={className} style={{whiteSpace: 'pre-wrap', ...style}} aria-label={text}>
      {Array.from(text).map((character, index) => (
        <AnimatedTextUnit
          key={`${character}-${index}`}
          frame={frame}
          delay={delayInFrames + index * staggerInFrames}
          duration={durationInFrames}
          direction={direction}
          distance={distance}
          easing={easing}
          style={itemStyle}
        >
          {character === ' ' ? '\u00A0' : character}
        </AnimatedTextUnit>
      ))}
    </span>
  );
};

export type TypewriterProps = {
  text: string;
  className?: string;
  style?: React.CSSProperties;
  delayInFrames?: number;
  durationInFrames?: number;
  cursor?: string;
  cursorColor?: string;
  cursorBlinkEveryFrames?: number;
  showCursorAfterComplete?: boolean;
};

export const Typewriter: React.FC<TypewriterProps> = ({
  text,
  className,
  style,
  delayInFrames = 0,
  durationInFrames = 30,
  cursor = '|',
  cursorColor,
  cursorBlinkEveryFrames = 8,
  showCursorAfterComplete = true,
}) => {
  const frame = useCurrentFrame();
  const progress = progressFor(frame, delayInFrames, durationInFrames);
  const characters = Array.from(text);
  const visibleCount = Math.min(characters.length, Math.floor(progress * (characters.length + 1)));
  const complete = visibleCount >= characters.length;
  const blinkPhase = Math.floor(Math.max(0, frame - delayInFrames) / safeDuration(cursorBlinkEveryFrames));
  const cursorVisible = frame >= delayInFrames && blinkPhase % 2 === 0 && (!complete || showCursorAfterComplete);

  return (
    <span className={className} style={{whiteSpace: 'pre-wrap', ...style}} aria-label={text}>
      <span aria-hidden="true">{characters.slice(0, visibleCount).join('')}</span>
      <span aria-hidden="true" style={{color: cursorColor, opacity: cursorVisible ? 1 : 0}}>
        {cursor}
      </span>
    </span>
  );
};

export type DrawLineProps = {
  className?: string;
  style?: React.CSSProperties;
  lineStyle?: React.CSSProperties;
  delayInFrames?: number;
  durationInFrames?: number;
  orientation?: LineOrientation;
  length?: number | string;
  thickness?: number;
  color?: string;
  easing?: MotionEasing;
  reverse?: boolean;
};

export const DrawLine: React.FC<DrawLineProps> = ({
  className,
  style,
  lineStyle,
  delayInFrames = 0,
  durationInFrames = 18,
  orientation = 'horizontal',
  length = '100%',
  thickness = 4,
  color = 'currentColor',
  easing = Easing.inOut(Easing.cubic),
  reverse = false,
}) => {
  const frame = useCurrentFrame();
  const progress = progressFor(frame, delayInFrames, durationInFrames, easing);
  const horizontal = orientation === 'horizontal';

  return (
    <div
      className={className}
      style={{
        width: horizontal ? length : thickness,
        height: horizontal ? thickness : length,
        overflow: 'hidden',
        ...style,
      }}
    >
      <div
        style={{
          width: '100%',
          height: '100%',
          backgroundColor: color,
          transform: horizontal ? `scaleX(${progress})` : `scaleY(${progress})`,
          transformOrigin: horizontal
            ? reverse
              ? 'right center'
              : 'left center'
            : reverse
              ? 'center bottom'
              : 'center top',
          ...lineStyle,
        }}
      />
    </div>
  );
};

export type ProgressBarProps = {
  className?: string;
  style?: React.CSSProperties;
  fillStyle?: React.CSSProperties;
  delayInFrames?: number;
  durationInFrames?: number;
  progress?: number;
  height?: number;
  trackColor?: string;
  fillColor?: string;
  borderRadius?: number;
  easing?: MotionEasing;
};

export const ProgressBar: React.FC<ProgressBarProps> = ({
  className,
  style,
  fillStyle,
  delayInFrames = 0,
  durationInFrames = 24,
  progress = 1,
  height = 8,
  trackColor = 'rgba(255,255,255,0.25)',
  fillColor = 'currentColor',
  borderRadius = 999,
  easing = Easing.out(Easing.cubic),
}) => {
  const frame = useCurrentFrame();
  const animated = progressFor(frame, delayInFrames, durationInFrames, easing);

  return (
    <div
      className={className}
      style={{height, width: '100%', borderRadius, overflow: 'hidden', backgroundColor: trackColor, ...style}}
    >
      <div
        style={{
          height: '100%',
          width: `${clamp(progress) * 100}%`,
          borderRadius: 'inherit',
          backgroundColor: fillColor,
          transform: `scaleX(${animated})`,
          transformOrigin: 'left center',
          ...fillStyle,
        }}
      />
    </div>
  );
};

export type CountUpProps = {
  from?: number;
  to: number;
  className?: string;
  style?: React.CSSProperties;
  delayInFrames?: number;
  durationInFrames?: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  easing?: MotionEasing;
  format?: (value: number) => React.ReactNode;
};

export const CountUp: React.FC<CountUpProps> = ({
  from = 0,
  to,
  className,
  style,
  delayInFrames = 0,
  durationInFrames = 30,
  decimals = 0,
  prefix = '',
  suffix = '',
  easing = Easing.out(Easing.cubic),
  format,
}) => {
  const frame = useCurrentFrame();
  const progress = progressFor(frame, delayInFrames, durationInFrames, easing);
  const value = from + (to - from) * progress;
  const precision = Math.max(0, Math.min(20, Math.floor(decimals)));
  const rendered = format ? format(value) : `${prefix}${value.toFixed(precision)}${suffix}`;

  return (
    <span className={className} style={{fontVariantNumeric: 'tabular-nums', ...style}}>
      {rendered}
    </span>
  );
};

export type PulseProps = MotionWrapperProps & {
  minScale?: number;
  maxScale?: number;
  periodInFrames?: number;
  minOpacity?: number;
  maxOpacity?: number;
  activeDurationInFrames?: number;
};

export const Pulse: React.FC<PulseProps> = ({
  children,
  className,
  style,
  delayInFrames = 0,
  minScale = 0.97,
  maxScale = 1.03,
  periodInFrames = 24,
  minOpacity = 1,
  maxOpacity = 1,
  activeDurationInFrames,
}) => {
  const frame = useCurrentFrame();
  const localFrame = Math.max(0, frame - delayInFrames);
  const active = frame >= delayInFrames &&
    (activeDurationInFrames === undefined || localFrame <= activeDurationInFrames);
  const wave = active ? (Math.sin((localFrame / safeDuration(periodInFrames)) * Math.PI * 2 - Math.PI / 2) + 1) / 2 : 0;
  const scale = minScale + (maxScale - minScale) * wave;
  const opacity = minOpacity + (maxOpacity - minOpacity) * wave;

  return (
    <div className={className} style={{...style, opacity, transform: `scale(${scale})`, transformOrigin: 'center'}}>
      {children}
    </div>
  );
};

export type ShakeProps = MotionWrapperProps & {
  amplitude?: number;
  rotation?: number;
  frequency?: number;
  decay?: number;
};

export const Shake: React.FC<ShakeProps> = ({
  children,
  className,
  style,
  delayInFrames = 0,
  durationInFrames = 14,
  amplitude = 18,
  rotation = 1.2,
  frequency = 0.34,
  decay = 2.2,
}) => {
  const frame = useCurrentFrame();
  const localFrame = frame - delayInFrames;
  const progress = progressFor(frame, delayInFrames, durationInFrames);
  const active = localFrame >= 0 && localFrame <= durationInFrames;
  const envelope = active ? Math.pow(1 - progress, Math.max(0, decay)) : 0;
  const wave = Math.sin(localFrame * Math.PI * 2 * frequency);
  const secondaryWave = Math.sin(localFrame * Math.PI * 2 * frequency * 1.7 + 1.4);
  const x = amplitude * envelope * wave;
  const y = amplitude * 0.28 * envelope * secondaryWave;
  const angle = rotation * envelope * secondaryWave;

  return (
    <div
      className={className}
      style={{...style, transform: `translate3d(${x}px, ${y}px, 0) rotate(${angle}deg)`, willChange: 'transform'}}
    >
      {children}
    </div>
  );
};

export type ImpactProps = MotionWrapperProps & {
  fromScale?: number;
  translateY?: number;
  rotate?: number;
  tuning?: SpringTuning;
  fade?: boolean;
};

export const Impact: React.FC<ImpactProps> = ({
  children,
  className,
  style,
  delayInFrames = 0,
  fromScale = 1.35,
  translateY = -24,
  rotate = -1.5,
  tuning = {damping: 12, stiffness: 220, mass: 0.72},
  fade = true,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const value = spring({frame: frame - delayInFrames, fps, config: tuning});
  const opacity = progressFor(frame, delayInFrames, 5, Easing.out(Easing.quad));

  return (
    <div
      className={className}
      style={{
        ...style,
        opacity: fade ? opacity : style?.opacity,
        transform: `translate3d(0, ${translateY * (1 - value)}px, 0) rotate(${rotate * (1 - value)}deg) scale(${fromScale + (1 - fromScale) * value})`,
        transformOrigin: 'center',
        willChange: 'transform, opacity',
      }}
    >
      {children}
    </div>
  );
};

export type FloatProps = MotionWrapperProps & {
  distance?: number;
  horizontalDistance?: number;
  periodInFrames?: number;
  phase?: number;
  rotate?: number;
};

export const Float: React.FC<FloatProps> = ({
  children,
  className,
  style,
  delayInFrames = 0,
  distance = 12,
  horizontalDistance = 0,
  periodInFrames = 60,
  phase = 0,
  rotate = 0,
}) => {
  const frame = useCurrentFrame();
  const localFrame = Math.max(0, frame - delayInFrames);
  const active = frame >= delayInFrames;
  const angle = active ? (localFrame / safeDuration(periodInFrames)) * Math.PI * 2 + phase : phase;
  const y = Math.sin(angle) * distance;
  const x = Math.cos(angle) * horizontalDistance;
  const rotation = Math.sin(angle) * rotate;

  return (
    <div
      className={className}
      style={{...style, transform: `translate3d(${x}px, ${y}px, 0) rotate(${rotation}deg)`, willChange: 'transform'}}
    >
      {children}
    </div>
  );
};

export const Bobbing = Float;
