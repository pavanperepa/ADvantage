# 22Yards Remotion prototype

This prototype separates editorial decisions from rendering:

```text
TwelveLabs scene understanding
        -> EditSpec JSON
        -> FFmpeg media preparation
        -> reusable Remotion primitives
        -> MP4
```

The current EditSpecs are `fixtures/reel-academy-remotion-v1.json` and
`fixtures/reel-practice-match-v2.json`. They define source ranges, timeline
placement, motion intent, transition restraint, audio priority, copy, brand
values, and closing action. `AcademyIntro.tsx` turns those decisions into
reusable visual components.

The reusable first-cut design system lives in `remotion/library/`. See
`remotion/LIBRARY.md` for the component catalog, JSON fields, themes, animation
vocabulary, and preview commands. Existing fixtures retain their original look;
new themes and variants are opt-in.

## Render locally

```powershell
npm install
npm run video:prepare
npm run video:studio
npm run video:render
```

Prepared media is cached in `remotion/public/` and stays out of Git. To rebuild
only one changed source range:

```powershell
.\.venv\Scripts\python.exe scripts\media\prepare_remotion_media.py fixtures\reel-academy-remotion-v1.json --shot belong --force
```

## Editing vocabulary implemented

- Longer semantic shots with explicit editorial purpose
- `slow_push`, `hero_push`, and controlled horizontal drift
- `soft_dissolve` and restrained `brand_wipe` chapter transitions
- Animated hero title and chapter cards
- Per-shot natural-audio priority
- Licensed music bed with automatic dialogue ducking
- Slow-motion application shot
- Freeze-on-payoff closing shot
- Reusable logo, phone, and location closing card
- Theme presets and variant-based overlay rendering
- Hooks, lower thirds, stat cards, testimonials, checklists, captions,
  scoreboards, matchup cards, countdowns, tickers, and CTA variants
- Reusable text motion, transitions, and decorative accents

The next useful capabilities are beat markers, face-aware reframing, transcript-
driven word timing, and standalone EditSpec validation. They can be added
without changing the EditSpec -> renderer boundary.
