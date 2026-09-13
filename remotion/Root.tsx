import React from 'react';
import {Composition} from 'remotion';
import specJson from '../fixtures/reel-academy-remotion-v1.json';
import practiceMatchSpecJson from '../fixtures/reel-practice-match-v2.json';
import libraryDemoSpecJson from '../fixtures/reel-library-demo-v1.json';
import practiceMatchLibrarySpecJson from '../fixtures/reel-practice-match-library-v1.json';
import {AcademyIntro} from './AcademyIntro';
import {ComponentGallery, GALLERY_DURATION} from './ComponentGallery';
import type {EditSpec} from './types';

const spec = specJson as EditSpec;
const duration = Math.ceil(Math.max(...spec.shots.map((shot) => shot.timelineStart + shot.duration)) * spec.canvas.fps);
const practiceMatchSpec = practiceMatchSpecJson as EditSpec;
const practiceMatchDuration = Math.ceil(
  Math.max(...practiceMatchSpec.shots.map((shot) => shot.timelineStart + shot.duration)) * practiceMatchSpec.canvas.fps,
);
const libraryDemoSpec = libraryDemoSpecJson as EditSpec;
const libraryDemoDuration = Math.ceil(
  Math.max(...libraryDemoSpec.shots.map((shot) => shot.timelineStart + shot.duration)) * libraryDemoSpec.canvas.fps,
);
const practiceMatchLibrarySpec = practiceMatchLibrarySpecJson as EditSpec;
const practiceMatchLibraryDuration = Math.ceil(
  Math.max(...practiceMatchLibrarySpec.shots.map((shot) => shot.timelineStart + shot.duration)) * practiceMatchLibrarySpec.canvas.fps,
);

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="AcademyIntro"
      component={AcademyIntro}
      durationInFrames={duration}
      fps={spec.canvas.fps}
      width={spec.canvas.width}
      height={spec.canvas.height}
      defaultProps={{spec}}
    />
    <Composition
      id="PracticeMatchReel"
      component={AcademyIntro}
      durationInFrames={practiceMatchDuration}
      fps={practiceMatchSpec.canvas.fps}
      width={practiceMatchSpec.canvas.width}
      height={practiceMatchSpec.canvas.height}
      defaultProps={{spec: practiceMatchSpec}}
    />
    <Composition
      id="ReelComponentLibrary"
      component={ComponentGallery}
      durationInFrames={GALLERY_DURATION}
      fps={30}
      width={1080}
      height={1920}
    />
    <Composition
      id="ReelLibraryDemo"
      component={AcademyIntro}
      durationInFrames={libraryDemoDuration}
      fps={libraryDemoSpec.canvas.fps}
      width={libraryDemoSpec.canvas.width}
      height={libraryDemoSpec.canvas.height}
      defaultProps={{spec: libraryDemoSpec}}
    />
    <Composition
      id="PracticeMatchLibraryReel"
      component={AcademyIntro}
      durationInFrames={practiceMatchLibraryDuration}
      fps={practiceMatchLibrarySpec.canvas.fps}
      width={practiceMatchLibrarySpec.canvas.width}
      height={practiceMatchLibrarySpec.canvas.height}
      defaultProps={{spec: practiceMatchLibrarySpec}}
    />
  </>
);
