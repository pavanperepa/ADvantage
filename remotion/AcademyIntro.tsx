import React from 'react';
import {
  AbsoluteFill,
  Easing,
  Img,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {Audio, Video} from '@remotion/media';
import type {ChapterOverlay, ClosingOverlay, DeadlineOverlay, EditSpec, HeroOverlay, Shot} from './types';
import {OverlayRenderer} from './library/OverlayRenderer';
import {ReelTransition, type ReelTransitionProps} from './library/transitions';

const seconds = (value: number, fps: number) => Math.round(value * fps);

const ShotLayer: React.FC<{shot: Shot; brand: EditSpec['brand']; transitionColor?: string}> = ({shot, brand, transitionColor}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const duration = seconds(shot.duration, fps);
  const progress = interpolate(frame, [0, Math.max(1, duration - 1)], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const entrance = interpolate(frame, [0, 8], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const scaleStart = shot.motion === 'hero_push' ? 1.02 : shot.motion === 'zoom_out' ? 1.075 : 1;
  const scaleEnd = shot.motion === 'none' || shot.motion === 'zoom_out' ? 1 : shot.motion === 'hero_push' ? 1.075 : 1.035;
  const handheldX = shot.motion === 'handheld' ? Math.sin(frame * 0.71) * 5 + Math.sin(frame * 0.19) * 3 : 0;
  const handheldY = shot.motion === 'handheld' ? Math.cos(frame * 0.57) * 4 : 0;
  const drift = shot.motion === 'gentle_drift_left' ? -18 * progress : shot.motion === 'gentle_drift_right' ? 18 * progress : 0;
  const verticalDrift = shot.motion === 'pan_up' ? 22 - 44 * progress : shot.motion === 'pan_down' ? -22 + 44 * progress : 0;
  const rotation = shot.motion === 'handheld' ? Math.sin(frame * 0.31) * 0.18 : 0;
  const opacity = shot.transition === 'soft_dissolve' ? entrance : 1;
  const clipPath = shot.transition === 'brand_wipe' ? `inset(0 ${100 - entrance * 100}% 0 0)` : undefined;
  const impactScale = shot.transition === 'impact_cut' ? interpolate(frame, [0, 9], [1.09, 1], {extrapolateRight: 'clamp'}) : 1;

  const content = (
    <AbsoluteFill style={{backgroundColor: '#061008', opacity, clipPath, overflow: 'hidden'}}>
      <Video
        src={staticFile(shot.media)}
        volume={shot.audio}
        objectFit="cover"
        style={{
          width: '100%',
          height: '100%',
          filter: 'brightness(1.1) contrast(1.035) saturate(1.1)',
          transform: `translate3d(${drift + handheldX}px, ${verticalDrift + handheldY}px, 0) rotate(${rotation}deg) scale(${interpolate(progress, [0, 1], [scaleStart, scaleEnd]) * impactScale})`,
        }}
      />
      <AbsoluteFill
        style={{
          background: 'linear-gradient(180deg, rgba(2,9,4,.02) 0%, rgba(2,9,4,0) 52%, rgba(2,9,4,.15) 100%)',
        }}
      />
      {shot.transition === 'brand_wipe' && frame < 12 ? (
        <div
          style={{
            position: 'absolute',
            top: 0,
            bottom: 0,
            left: `${entrance * 100 - 3}%`,
            width: 34,
            background: transitionColor ?? brand.primary,
            transform: 'skewX(-7deg)',
            boxShadow: `0 0 34px ${transitionColor ?? brand.primary}`,
          }}
        />
      ) : null}
      {shot.transition === 'impact_cut' && frame < 7 ? (
        <AbsoluteFill
          style={{
            background: brand.accent,
            opacity: interpolate(frame, [0, 6], [0.42, 0], {extrapolateRight: 'clamp'}),
            mixBlendMode: 'screen',
          }}
        />
      ) : null}
    </AbsoluteFill>
  );

  const transition: Pick<ReelTransitionProps, 'variant' | 'direction'> | null = (() => {
    switch (shot.transition) {
      case 'wipe_left': return {variant: 'directional-wipe', direction: 'left'};
      case 'wipe_right': return {variant: 'directional-wipe', direction: 'right'};
      case 'wipe_up': return {variant: 'directional-wipe', direction: 'up'};
      case 'wipe_down': return {variant: 'directional-wipe', direction: 'down'};
      case 'slide_left': return {variant: 'slide', direction: 'left'};
      case 'slide_right': return {variant: 'slide', direction: 'right'};
      case 'push_left': return {variant: 'push', direction: 'left'};
      case 'push_right': return {variant: 'push', direction: 'right'};
      case 'zoom': return {variant: 'zoom'};
      case 'flash': return {variant: 'flash'};
      case 'glitch': return {variant: 'glitch-lite'};
      case 'shutter': return {variant: 'shutter'};
      case 'bars': return {variant: 'bars'};
      case 'iris': return {variant: 'iris'};
      default: return null;
    }
  })();

  return transition ? (
    <ReelTransition
      {...transition}
      durationInFrames={Math.min(16, Math.max(8, Math.round(fps * 0.4)))}
      accentColor={transitionColor ?? brand.accent}
      backgroundColor={brand.ink}
    >
      {content}
    </ReelTransition>
  ) : content;
};

const BrandRail: React.FC<{brand: EditSpec['brand']}> = ({brand}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const progress = interpolate(frame, [0, durationInFrames - 1], [0, 1], {extrapolateRight: 'clamp'});
  return (
    <>
      <div style={{position: 'absolute', left: 54, right: 54, top: 56, height: 3, background: 'rgba(255,255,255,.22)'}}>
        <div style={{height: '100%', width: `${progress * 100}%`, background: brand.primary}} />
      </div>
      <div style={{position: 'absolute', left: 54, top: 76, color: 'white', fontFamily: 'Body', fontSize: 22, letterSpacing: 4, textShadow: '0 2px 8px rgba(0,0,0,.9)'}}>
        {brand.academy}
      </div>
    </>
  );
};

const HeroTitle: React.FC<{overlay: HeroOverlay; brand: EditSpec['brand']}> = ({overlay, brand}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const settle = spring({frame, fps, config: {damping: 18, stiffness: 115, mass: 0.9}});
  const line2 = spring({frame: frame - 5, fps, config: {damping: 17, stiffness: 105, mass: 0.95}});
  const fadeOut = interpolate(frame, [seconds(overlay.duration, fps) - 12, seconds(overlay.duration, fps)], [1, 0], {extrapolateLeft: 'clamp'});
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', padding: '0 62px 285px', opacity: fadeOut}}>
      <div
        style={{
          position: 'absolute',
          left: 38,
          right: 38,
          bottom: 235,
          height: 448,
          background: 'linear-gradient(110deg, rgba(3,11,8,.92), rgba(3,11,8,.72))',
          borderLeft: `11px solid ${brand.accent}`,
          borderTop: '1px solid rgba(255,255,255,.2)',
          boxShadow: '0 24px 64px rgba(0,0,0,.42)',
          opacity: settle,
          zIndex: 0,
          transform: `translateX(${(1 - settle) * -70}px) scaleX(${0.96 + settle * 0.04})`,
          transformOrigin: 'left center',
        }}
      />
      <div style={{position: 'relative', zIndex: 1, fontFamily: 'Body', color: brand.accent, fontSize: 24, fontWeight: 700, letterSpacing: 6, marginBottom: 22, opacity: settle, textShadow: '0 2px 8px rgba(0,0,0,.9)'}}>{overlay.eyebrow}</div>
      <div style={{position: 'relative', zIndex: 1, overflow: 'hidden'}}>
        <div style={{fontFamily: 'Display', color: 'white', fontSize: 94, lineHeight: 0.9, textShadow: '0 5px 18px rgba(0,0,0,.9)', transform: `translateY(${(1 - settle) * 110}px)`}}>{overlay.line1}</div>
      </div>
      <div style={{position: 'relative', zIndex: 1, overflow: 'hidden', marginTop: 10}}>
        <div
          style={{
            fontFamily: 'Display',
            color: brand.accent,
            fontSize: 146,
            lineHeight: 0.86,
            textShadow: '0 7px 24px rgba(0,0,0,.72)',
            transform: `translateY(${(1 - line2) * 145}px)`,
          }}
        >
          {overlay.line2}
        </div>
      </div>
      <div style={{position: 'relative', zIndex: 1, width: 120 * settle, height: 8, marginTop: 28, background: brand.accent}} />
    </AbsoluteFill>
  );
};

const Chapter: React.FC<{overlay: ChapterOverlay; brand: EditSpec['brand']}> = ({overlay, brand}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({frame, fps, config: {damping: 20, stiffness: 135}});
  const exit = interpolate(frame, [seconds(overlay.duration, fps) - 10, seconds(overlay.duration, fps)], [1, 0], {extrapolateLeft: 'clamp'});
  const label = overlay.label ?? (overlay.number ? `STEP ${overlay.number}` : 'THE DIFFERENCE');
  const hasLabel = label.trim().length > 0;
  const hasDetail = overlay.detail.trim().length > 0;
  const isMinimal = !hasLabel && !hasDetail;
  const titleSize = isMinimal ? (overlay.title.length > 25 ? 66 : 78) : overlay.title.length > 18 ? 62 : 70;
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', padding: '0 58px 250px', opacity: exit, pointerEvents: 'none'}}>
      <div style={{display: 'flex', alignItems: 'stretch', transform: `translateX(${(1 - enter) * -70}px) translateY(${(1 - enter) * 28}px) scale(${0.97 + enter * 0.03})`, opacity: enter}}>
        <div style={{width: 11, background: brand.accent, marginRight: 20, boxShadow: `0 0 24px ${brand.accent}88`}} />
        <div style={{position: 'relative', background: 'rgba(3,11,8,.9)', padding: '28px 32px 30px', border: `1px solid ${brand.accent}70`, minWidth: 520, backdropFilter: 'blur(14px)', boxShadow: '0 22px 48px rgba(0,0,0,.36)'}}>
          <div style={{position: 'absolute', left: 0, top: 0, width: 150 * enter, height: 6, background: brand.accent}} />
          {hasLabel ? <div style={{fontFamily: 'Body', color: brand.accent, fontSize: 22, letterSpacing: 5, marginBottom: 8}}>{label}</div> : null}
          <div style={{fontFamily: 'Display', color: 'white', fontSize: titleSize, lineHeight: 1}}>{overlay.title}</div>
          {hasDetail ? <div style={{fontFamily: 'Body', color: 'rgba(255,255,255,.78)', fontSize: 27, marginTop: 11}}>{overlay.detail}</div> : null}
        </div>
      </div>
    </AbsoluteFill>
  );
};

const DeadlineTeaser: React.FC<{overlay: DeadlineOverlay; brand: EditSpec['brand']}> = ({overlay, brand}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({frame, fps, config: {damping: 18, stiffness: 150}});
  const fadeOut = interpolate(frame, [seconds(overlay.duration, fps) - 8, seconds(overlay.duration, fps)], [1, 0], {
    extrapolateLeft: 'clamp',
  });

  return (
    <AbsoluteFill style={{padding: '160px 54px 0', alignItems: 'flex-end', pointerEvents: 'none', opacity: fadeOut}}>
      <div
        style={{
          display: 'flex',
          alignItems: 'stretch',
          background: 'rgba(3,11,8,.92)',
          border: `2px solid ${brand.accent}`,
          boxShadow: '0 18px 42px rgba(0,0,0,.42)',
          transform: `translateX(${(1 - enter) * 90}px)`,
          opacity: enter,
        }}
      >
        <div style={{padding: '18px 20px 15px'}}>
          <div style={{fontFamily: 'Body', color: brand.accent, fontSize: 18, fontWeight: 700, letterSpacing: 4}}>{overlay.label}</div>
          <div style={{fontFamily: 'Display', color: 'white', fontSize: 54, lineHeight: 0.95, marginTop: 5}}>{overlay.date}</div>
        </div>
        <div style={{width: 13, background: brand.accent}} />
      </div>
    </AbsoluteFill>
  );
};

const ClosingCard: React.FC<{overlay: ClosingOverlay; brand: EditSpec['brand']}> = ({overlay, brand}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const reveal = spring({frame, fps, config: {damping: 19, stiffness: 105, mass: 0.95}});
  const details = spring({frame: frame - 8, fps, config: {damping: 20, stiffness: 115}});
  const deadline = spring({frame: frame - 13, fps, config: {damping: 17, stiffness: 125, mass: 0.9}});
  const hasDeadline = Boolean(overlay.deadlineMonth && overlay.deadlineDay);
  return (
    <AbsoluteFill style={{background: `rgba(2,10,4,${0.42 * reveal})`, justifyContent: 'center', alignItems: 'center', padding: 64}}>
      <div style={{width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', transform: `scale(${0.94 + reveal * 0.06})`, opacity: reveal}}>
        <Img src={staticFile('brand/logo.png')} style={{width: hasDeadline ? 275 : 360, maxHeight: hasDeadline ? 220 : 300, objectFit: 'contain', filter: 'drop-shadow(0 14px 28px rgba(0,0,0,.36))'}} />
        <div style={{fontFamily: 'Display', color: 'white', fontSize: hasDeadline ? 52 : 65, textAlign: 'center', lineHeight: 1.02, marginTop: hasDeadline ? 18 : 30}}>{overlay.headline}</div>
        <div style={{width: 92 * details, height: 7, background: brand.accent, margin: hasDeadline ? '18px 0' : '26px 0'}} />
        <div style={{fontFamily: 'Body', color: hasDeadline ? 'white' : brand.ink, background: hasDeadline ? 'rgba(3,11,8,.82)' : brand.accent, fontSize: 24, fontWeight: 700, letterSpacing: 4, padding: hasDeadline ? '7px 14px' : '12px 18px', opacity: details, boxShadow: hasDeadline ? 'none' : '0 10px 28px rgba(0,0,0,.25)'}}>{overlay.action}</div>
        {hasDeadline ? (
          <div
            style={{
              width: 730,
              height: 245,
              marginTop: 14,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 28,
              color: brand.ink,
              background: brand.accent,
              border: '4px solid white',
              boxShadow: '0 18px 46px rgba(0,0,0,.42)',
              transform: `scale(${0.86 + deadline * 0.14})`,
              opacity: deadline,
            }}
          >
            <div style={{fontFamily: 'Body', fontSize: 50, fontWeight: 800, letterSpacing: 7, transform: 'rotate(-90deg)'}}>{overlay.deadlineMonth}</div>
            <div style={{width: 4, height: 170, background: `${brand.ink}55`}} />
            <div style={{fontFamily: 'Display', fontSize: 210, lineHeight: 0.8}}>{overlay.deadlineDay}</div>
          </div>
        ) : null}
        <div style={{fontFamily: 'Display', color: 'white', fontSize: hasDeadline ? 60 : 72, marginTop: hasDeadline ? 16 : 12, opacity: details}}>{brand.phone}</div>
        <div style={{fontFamily: 'Body', color: 'white', fontSize: 29, marginTop: 17, opacity: details}}>{brand.registrationUrl}</div>
        <div style={{fontFamily: 'Body', color: brand.accent, fontSize: 20, letterSpacing: 5, marginTop: 7, opacity: details}}>LINK IN BIO</div>
        <div style={{fontFamily: 'Body', color: 'rgba(255,255,255,.7)', fontSize: 20, letterSpacing: 4, marginTop: 15, opacity: details}}>{brand.location}</div>
      </div>
    </AbsoluteFill>
  );
};

const MusicBed: React.FC<{music: EditSpec['music']}> = ({music}) => {
  const {fps, durationInFrames} = useVideoConfig();
  const fadeInEnd = seconds(music.fadeIn, fps);
  const duckStart = seconds(music.duckStart, fps);
  const duckInEnd = duckStart + seconds(0.42, fps);
  const duckEnd = seconds(music.duckEnd, fps);
  const duckOutEnd = duckEnd + seconds(0.45, fps);
  const fadeOutStart = durationInFrames - seconds(music.fadeOut, fps);
  const lastFrame = Math.max(1, durationInFrames - 1);
  const safeFadeOutStart = Math.min(lastFrame - 1, Math.max(0, fadeOutStart));

  return (
    <Audio
      src={staticFile(music.file)}
      durationInFrames={durationInFrames}
      name={`Music: ${music.title} — ${music.artist}`}
      volume={(frame) => {
        const fadeIn = interpolate(frame, [0, Math.max(1, fadeInEnd)], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        });
        const fadeOut = interpolate(frame, [safeFadeOutStart, lastFrame], [1, 0], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        });
        const duckedVolume = frame < duckInEnd
          ? interpolate(frame, [duckStart, Math.max(duckStart + 1, duckInEnd)], [music.baseVolume, music.duckVolume], {
              extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
            })
          : frame <= duckEnd
            ? music.duckVolume
            : interpolate(frame, [duckEnd, Math.max(duckEnd + 1, duckOutEnd)], [music.duckVolume, music.baseVolume], {
                extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
              });
        return duckedVolume * fadeIn * fadeOut;
      }}
    />
  );
};

export const AcademyIntro: React.FC<{spec: EditSpec}> = ({spec}) => {
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill style={{backgroundColor: spec.brand.ink}}>
      <style>{`@font-face{font-family:Display;src:url('${staticFile('fonts/display.woff2')}')}@font-face{font-family:Body;src:url('${staticFile('fonts/body.woff2')}')}`}</style>
      <MusicBed music={spec.music} />
      {spec.shots.map((shot) => (
        <Sequence key={shot.id} from={seconds(shot.timelineStart, fps)} durationInFrames={seconds(shot.duration, fps)} name={`Shot: ${shot.id}`}>
          <ShotLayer shot={shot} brand={spec.brand} transitionColor={spec.style?.transitionColor} />
        </Sequence>
      ))}
      {spec.style?.showBrandRail === false ? null : <BrandRail brand={spec.brand} />}
      {spec.overlays.map((overlay, index) => (
        <Sequence key={`${overlay.type}-${index}`} from={seconds(overlay.start, fps)} durationInFrames={seconds(overlay.duration, fps)} name={`Overlay: ${overlay.type}`}>
          {overlay.variant || overlay.animation || spec.style?.theme || spec.style?.defaultOverlayAnimation ? (
            <OverlayRenderer
              overlay={overlay}
              brand={spec.brand}
              durationInFrames={seconds(overlay.duration, fps)}
              themeName={spec.style?.theme}
              animation={overlay.animation ?? spec.style?.defaultOverlayAnimation}
            />
          ) : overlay.type === 'hero_title' ? <HeroTitle overlay={overlay} brand={spec.brand} />
            : overlay.type === 'chapter' ? <Chapter overlay={overlay} brand={spec.brand} />
              : overlay.type === 'deadline' ? <DeadlineTeaser overlay={overlay} brand={spec.brand} />
                : overlay.type === 'closing' ? <ClosingCard overlay={overlay} brand={spec.brand} />
                  : <OverlayRenderer
                      overlay={overlay}
                      brand={spec.brand}
                      durationInFrames={seconds(overlay.duration, fps)}
                      themeName={spec.style?.theme}
                      animation={overlay.animation ?? spec.style?.defaultOverlayAnimation}
                    />}
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
