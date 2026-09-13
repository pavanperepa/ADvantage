import React from 'react';
import {AbsoluteFill, Sequence, staticFile, useCurrentFrame} from 'remotion';
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
} from './library/overlays';
import {
  AccentBars,
  CornerBrackets,
  DotPattern,
  FilmGrain,
  FloatingParticles,
  FocusCircle,
  GradientScrim,
  GridPattern,
  PointerArrow,
  ProgressRail,
  Ticker,
  Vignette,
} from './library/decorations';
import {Impact, StaggeredWords, Typewriter} from './library/motion';

export const GALLERY_SLIDE_FRAMES = 75;
export const GALLERY_SLIDE_COUNT = 18;
export const GALLERY_DURATION = GALLERY_SLIDE_FRAMES * GALLERY_SLIDE_COUNT;

const palette: OverlayPalette = {
  primary: '#8CC63F',
  accent: '#FFD437',
  ink: '#07130A',
  surface: 'rgba(3,11,8,.92)',
  text: '#FFFFFF',
  muted: 'rgba(255,255,255,.76)',
};

const fonts: OverlayFonts = {display: 'Display', body: 'Body'};

const GalleryBackdrop: React.FC<{variant?: 'grid' | 'dots' | 'clean'}> = ({variant = 'grid'}) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(${135 + frame * 0.08}deg, #07130A 0%, #0E351B 54%, #0757A6 140%)`,
      }}
    >
      {variant === 'grid' ? <GridPattern opacity={0.45} /> : null}
      {variant === 'dots' ? <DotPattern opacity={0.5} /> : null}
      <GradientScrim topStrength={0.28} bottomStrength={0.62} />
      <Vignette strength={0.34} />
    </AbsoluteFill>
  );
};

const GalleryLabel: React.FC<{index: number; label: string}> = ({index, label}) => (
  <div
    style={{
      position: 'absolute',
      right: 54,
      top: 72,
      zIndex: 100,
      color: '#FFFFFF',
      fontFamily: 'Body',
      fontSize: 18,
      fontWeight: 800,
      letterSpacing: 3,
      textAlign: 'right',
      textShadow: '0 2px 10px #000',
    }}
  >
    <div style={{color: palette.accent}}>REEL COMPONENT LIBRARY</div>
    <div style={{marginTop: 6}}>{String(index + 1).padStart(2, '0')} / {GALLERY_SLIDE_COUNT} · {label}</div>
  </div>
);

const GallerySlide: React.FC<{
  index: number;
  label: string;
  children: React.ReactNode;
  backdrop?: 'grid' | 'dots' | 'clean';
  decorations?: React.ReactNode;
}> = ({index, label, children, backdrop, decorations}) => (
  <AbsoluteFill>
    <GalleryBackdrop variant={backdrop} />
    {decorations}
    {children}
    <GalleryLabel index={index} label={label} />
  </AbsoluteFill>
);

export const ComponentGallery: React.FC = () => {
  const slides: Array<{label: string; backdrop?: 'grid' | 'dots' | 'clean'; decorations?: React.ReactNode; content: React.ReactNode}> = [
    {
      label: 'HOOK · STACKED',
      content: <HookTitle palette={palette} fonts={fonts} durationInFrames={GALLERY_SLIDE_FRAMES} eyebrow="AT 22YARDS" line1="BUILD THE SKILL" line2="OWN THE MOMENT" variant="stacked" />,
    },
    {
      label: 'HOOK · HIGHLIGHT',
      backdrop: 'dots',
      content: <HookTitle palette={palette} fonts={fonts} durationInFrames={GALLERY_SLIDE_FRAMES} eyebrow="MATCH DAY" line1="PRESSURE MAKES" line2="PLAYERS" variant="highlight" />,
    },
    {
      label: 'HOOK · OUTLINE',
      backdrop: 'clean',
      decorations: <FilmGrain strength={0.07} />,
      content: <HookTitle palette={palette} fonts={fonts} durationInFrames={GALLERY_SLIDE_FRAMES} eyebrow="TRAIN WITH PURPOSE" line1="READY FOR" line2="THE NEXT BALL" variant="outline" placement="center" />,
    },
    {
      label: 'CHAPTER CARD',
      content: <ChapterCard palette={palette} fonts={fonts} durationInFrames={GALLERY_SLIDE_FRAMES} number="01" label="THE FOUNDATION" title="MOVE WITH BALANCE" detail="Footwork, control and coordination" variant="numbered" />,
    },
    {
      label: 'LOWER THIRD',
      backdrop: 'clean',
      content: <LowerThird palette={palette} fonts={fonts} durationInFrames={GALLERY_SLIDE_FRAMES} kicker="MEET THE COACH" name="COACH NAME" role="22Yards Cricket Academy" />,
    },
    {
      label: 'STAT CARDS',
      decorations: <CornerBrackets color={palette.accent} />,
      content: <StatCards palette={palette} fonts={fonts} durationInFrames={GALLERY_SLIDE_FRAMES} heading="PROGRAM AT A GLANCE" items={[{value: 'U5–U13', label: 'Age Groups'}, {value: 'WEEKLY', label: 'Match Exposure'}, {value: '1 TEAM', label: 'Coaching Path'}]} columns={3} variant="glass" />,
    },
    {
      label: 'TESTIMONIAL',
      backdrop: 'dots',
      content: <TestimonialCard palette={palette} fonts={fonts} durationInFrames={GALLERY_SLIDE_FRAMES} quote="The coaches helped our child become more confident, focused and excited to play." author="PARENT TESTIMONIAL" role="Houston academy family" rating={5} />,
    },
    {
      label: 'CHECKLIST',
      content: <Checklist palette={palette} fonts={fonts} durationInFrames={GALLERY_SLIDE_FRAMES} heading="WHAT THEY DEVELOP" items={['Cricket fundamentals', 'Movement and balance', 'Speed and coordination', 'Match-day decisions']} />,
    },
    {
      label: 'SPLIT HEADLINE',
      backdrop: 'clean',
      content: <SplitHeadline palette={palette} fonts={fonts} durationInFrames={GALLERY_SLIDE_FRAMES} topLabel="THE TRAINING LOOP" left="LEARN THE SKILL" dividerText="THEN" right="APPLY IT" />,
    },
    {
      label: 'INFORMATION CHIPS',
      content: <InfoChips palette={palette} fonts={fonts} durationInFrames={GALLERY_SLIDE_FRAMES} items={[{icon: '⌖', label: 'Location', value: 'Houston, Texas'}, {icon: '◷', label: 'Program', value: 'U5–U13 development'}, {icon: '☎', label: 'Call', value: '+1 (713) 498-2155'}]} />,
    },
    {
      label: 'BADGE',
      backdrop: 'dots',
      decorations: <FloatingParticles confetti count={22} opacity={0.48} />,
      content: <Badge palette={palette} fonts={fonts} durationInFrames={GALLERY_SLIDE_FRAMES} text="FREE TRIAL" subtext="Limited time" shape="burst" />,
    },
    {
      label: 'CAPTIONS',
      backdrop: 'clean',
      content: <CaptionPanel palette={palette} fonts={fonts} durationInFrames={GALLERY_SLIDE_FRAMES} speaker="COACH" text="Watch the ball, stay balanced, and finish the shot." activeWords={['balanced', 'finish']} variant="karaoke" />,
    },
    {
      label: 'MATCHUP CARD',
      content: <VersusCard palette={palette} fonts={fonts} durationInFrames={GALLERY_SLIDE_FRAMES} label="SATURDAY SERIES" left="22YARDS" right="VISITORS" leftMeta="Houston" rightMeta="Match day" />,
    },
    {
      label: 'SCOREBOARD',
      backdrop: 'clean',
      content: <Scoreboard palette={palette} fonts={fonts} durationInFrames={GALLERY_SLIDE_FRAMES} competition="ACADEMY PRACTICE MATCH" home="22YARDS" away="CHALLENGERS" homeScore="84" awayScore="81" status="FINAL" detail="Great game" />,
    },
    {
      label: 'COUNTDOWN',
      backdrop: 'dots',
      content: <CountdownCard palette={palette} fonts={fonts} durationInFrames={GALLERY_SLIDE_FRAMES} label="REGISTRATION CLOSES" value="5" unit="DAYS" variant="urgent" />,
    },
    {
      label: 'CTA / END CARD',
      backdrop: 'clean',
      content: <CTAEndCard palette={palette} fonts={fonts} durationInFrames={GALLERY_SLIDE_FRAMES} logoSrc={staticFile('brand/logo.png')} urgency="Limited availability" headline="READY TO START?" subheadline="Build cricket skills and athletic confidence." action="CLAIM A FREE TRIAL" phone="+1 (713) 498-2155" url="axon22yards.com/join?location=houston" location="Houston, Texas" variant="centered" />,
    },
    {
      label: 'TEXT MOTION',
      decorations: <AccentBars colors={[palette.primary, palette.accent]} />,
      content: (
        <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', padding: 80, textAlign: 'center'}}>
          <Impact>
            <div style={{color: palette.accent, fontFamily: fonts.display, fontSize: 112, lineHeight: 0.9}}>IMPACT</div>
          </Impact>
          <StaggeredWords text="WORD BY WORD REVEAL" delayInFrames={10} style={{color: palette.text, fontFamily: fonts.display, fontSize: 62, lineHeight: 1, marginTop: 34}} />
          <Typewriter text="Deterministic, editable text" delayInFrames={28} durationInFrames={26} style={{color: palette.muted, fontFamily: fonts.body, fontSize: 30, marginTop: 30}} />
        </AbsoluteFill>
      ),
    },
    {
      label: 'DECORATIONS',
      backdrop: 'clean',
      decorations: (
        <>
          <ProgressRail color={palette.accent} label="PROGRESS RAIL" />
          <CornerBrackets color={palette.primary} />
          <FocusCircle x="38%" y="48%" label="FOCUS CALLOUT" />
          <PointerArrow x="52%" y="58%" rotation={-12} />
          <Ticker items={['SKILLS', 'FITNESS', 'CONFIDENCE', 'MATCH PLAY']} />
        </>
      ),
      content: null,
    },
  ];

  return (
    <AbsoluteFill style={{backgroundColor: palette.ink}}>
      <style>{`@font-face{font-family:Display;src:url('${staticFile('fonts/display.woff2')}')}@font-face{font-family:Body;src:url('${staticFile('fonts/body.woff2')}')}`}</style>
      {slides.map((slide, index) => (
        <Sequence key={slide.label} from={index * GALLERY_SLIDE_FRAMES} durationInFrames={GALLERY_SLIDE_FRAMES} name={slide.label}>
          <GallerySlide index={index} label={slide.label} backdrop={slide.backdrop} decorations={slide.decorations}>
            {slide.content}
          </GallerySlide>
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
