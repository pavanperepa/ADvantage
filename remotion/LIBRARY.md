# Reel component library

The Remotion reel system is now a small design system rather than a single
template. An `EditSpec` still owns the editorial facts and timing. The library
owns how those facts are drawn and animated.

Existing fixtures remain backward compatible. If a fixture has no `style`, no
overlay `variant`, and no overlay `animation`, the original `AcademyIntro`
components render exactly as before. New reels opt into the library through
JSON.

## Preview the catalog

Open Remotion Studio and select `ReelComponentLibrary`:

```powershell
npm run library:studio
```

Render the complete component reel or one representative still:

```powershell
npm run library:render
npm run library:still
```

The gallery source is `remotion/ComponentGallery.tsx`. It contains 18 scenes
showing hooks, cards, captions, score graphics, CTAs, motion, and decorations.
`fixtures/reel-library-demo-v1.json` is a separate starter EditSpec proving that
the same components can be selected entirely through JSON over real footage.

## Reel-level styles

Add an optional `style` block to an EditSpec:

```json
{
  "style": {
    "theme": "match_day",
    "showBrandRail": true,
    "transitionColor": "#FFD437",
    "defaultOverlayAnimation": "spring"
  }
}
```

Available themes:

- `classic`
- `cinematic`
- `match_day`
- `kinetic`
- `minimal`
- `youth_energy`
- `premium`
- `testimonial`

Themes set default component treatments while continuing to use the colors and
contact information in the fixture's `brand` block. A component-level `variant`
overrides the theme default.

Available overlay entrance animations:

- `fade`
- `slide_up`
- `slide_left`
- `slide_right`
- `pop`
- `spring`
- `mask`
- `blur`
- `impact`

The component itself always has a restrained built-in reveal. Set `animation`
only when an additional entrance treatment is useful.

## Overlay catalog

Every overlay uses `type`, `start`, and `duration`. It may also use `variant`,
`animation`, and `position` (`top`, `center`, or `bottom`).

| Type | Use | Main content | Variants |
|---|---|---|---|
| `hero_title` | Opening hook | `eyebrow`, `line1`, `line2` | `stacked`, `boxed`, `highlight`, `outline` |
| `chapter` | Story beat | `number`, `label`, `title`, `detail` | `rail`, `numbered`, `minimal` |
| `lower_third` | Identify a person | `eyebrow`, `title`, `subtitle` | `left`, `right` |
| `stat` | Facts or program metrics | `value`, `label`, optional `items` | `solid`, `glass`, `outline` |
| `quote` | Parent/coach quotation | `quote`, `attribution`, `role` | `standard`, `five_star` |
| `checklist` | Benefits or outcomes | `title`, `items` | — |
| `split_headline` | Two-part idea | `left`, `right`, `dividerText`, `topLabel` | — |
| `info_chips` | Several compact facts | `items`, `direction` | — |
| `location` | Venue callout | `label`, `location`, `detail` | — |
| `badge` | Offer or urgency | `text`, `detail` | `pill`, `stamp`, `burst` |
| `caption` | Dialogue/subtitles | `text`, `speaker`, `emphasis` | `panel`, `floating`, `karaoke` |
| `matchup` | Team comparison | `sideA`, `sideB`, `label`, `detail` | — |
| `scoreboard` | Score/result | team names, scores, `status` | — |
| `deadline` | Date/countdown | `label`, `date` | `counter`, `calendar`, `urgent` |
| `ticker` | Repeating support points | `label`, `items` | — |
| `closing` | Final CTA | `headline`, `action`, optional deadline | `centered`, `banner`, `minimal` |

Example:

```json
{
  "type": "stat",
  "start": 5.2,
  "duration": 3.4,
  "variant": "glass",
  "animation": "slide_up",
  "heading": "PROGRAM FOCUS",
  "value": "3",
  "label": "CORE OUTCOMES",
  "items": [
    {"value": "SKILL", "label": "Cricket technique"},
    {"value": "FITNESS", "label": "Athletic movement"},
    {"value": "DECISIONS", "label": "Match awareness"}
  ],
  "columns": 3
}
```

## Shot motion and transitions

Shot `motion` values:

```text
none, slow_push, hero_push, zoom_out, gentle_drift_left,
gentle_drift_right, pan_up, pan_down, handheld
```

Shot `transition` values:

```text
none, soft_dissolve, brand_wipe, impact_cut,
wipe_left, wipe_right, wipe_up, wipe_down,
slide_left, slide_right, push_left, push_right,
zoom, flash, glitch, shutter, bars, iris
```

The first four values preserve the original reel treatments. The others route
through the reusable transition renderer.

## Direct React components

For a composition that needs more control than JSON, import from the library:

```tsx
import {
  HookTitle,
  Scoreboard,
  StaggeredWords,
  ReelTransition,
  GradientScrim,
} from './library';
```

The library exports:

- 14 primary overlay components plus semantic aliases
- 18 motion/text/data primitives
- 11 transition-renderer variants
- 13 decorative elements
- 8 theme presets
- machine-readable catalogs for editors and validation

Decorations include scrims, vignette, progress rail, brackets, accent bars,
grid and dot patterns, ticker, seeded particles/confetti, focus circle, pointer
arrow, and deterministic film grain. Decorative defaults are edge-weighted or
low-opacity so they do not obscure children in the footage.

## Current boundaries

- Captions accept exact text and highlighted words, but they are not yet timed
  word by word from a transcript.
- Reframing is selected during FFmpeg preparation with `focusX`; automated
  face-aware tracking is not yet implemented.
- JSON is TypeScript-checked when imported by the renderer, but a standalone
  command-line EditSpec validator is still a useful future addition.
- New component combinations still require representative-frame QA for safe
  areas, copy fit, contrast, and subject visibility.
