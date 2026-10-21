// The season section's backdrop: a Vanta NET of points and links, read as the
// academy's network of families. Vanta 0.5 needs Three.js r134, so it gets its
// own pinned copy (`three-vanta`) and this module is loaded only when the
// section comes near the viewport.
import * as THREE from 'three-vanta';
import NET from 'vanta/dist/vanta.net.min';

export interface NetHandle {
  destroy(): void;
  setOptions(o: Record<string, unknown>): void;
}

export function createNet(el: HTMLElement): NetHandle | null {
  try {
    return NET({
      el,
      THREE,
      mouseControls: true,
      touchControls: false,
      gyroControls: false,
      minHeight: 200,
      minWidth: 200,
      scale: 1,
      scaleMobile: 1,
      color: 0x8a8e96,
      backgroundColor: 0x121316,
      backgroundAlpha: 1,
      points: 9,
      maxDistance: 22,
      spacing: 19,
      showDots: true,
    }) as NetHandle;
  } catch {
    return null;
  }
}
