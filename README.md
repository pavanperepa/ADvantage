# ADvantage website

Single-page marketing site for ADvantage, the go-to-market and marketing
partner for small businesses, starting with sports academies (cricket,
football, table tennis, badminton and other sports). Its one job is to get an
academy owner to book a free 15-minute review.

The page is organised around the five services:

1. Campaign analysis, strategy and execution
2. Video editing and social media (Instagram) management
3. Lead engagement and follow-ups
4. Mass customer engagement (text and email to past and current leads,
   students and families)
5. Banner placement analysis

Each service has a pain in the "second job" list, a panel on the sticky
product screen, a card in the season row and an FAQ answer. Keep those four in
step when a service changes.

## Design

Built to the taste-skill rules (tasteskill.dev): one ground (`#f2f1ec`), one
ink (`#121316`), one accent (`#c5f03c`) used on the action and on the people
who light up in the hero. One typeface, Instrument Sans. Surfaces separate by a
step in tone. No eyebrow labels, no index numbers, no stock photography. The
season section changes the whole field to ink and the closing call to action
changes it to the accent. The one deliberate exception to "no gradients" is
the cursor spotlight on cards.

Motion:

- Hero (`src/hero.ts`, Three.js): the academy sits at the centre of a faint
  crowd and sends its work out as a pulse; the right families light up and
  travel in to orbit it.
- GSAP (ScrollTrigger, SplitText, DrawSVG, ScrambleText) and Lenis: headings
  rise line by line, the channel hub draws its connections, the services
  section keeps a product screen pinned while its panels change (the screen
  title decrypts and audience counts count up), the season row scrolls
  sideways while pinned, and the chart redraws as the sliders move.
- Vanta.js NET (`src/net.ts`) behind the season section. Vanta 0.5 needs
  Three.js r134, so it uses a pinned alias (`three-vanta`) and is lazy-loaded
  only when the section approaches, destroyed when it leaves, and skipped
  under 700px. Expect one "multiple instances of Three.js" console warning on
  desktop; it is harmless.
- React Bits-style effects (`src/bits.ts`), ported to vanilla TypeScript since
  the page is not React: ScrollVelocity (the "Built for" strip speeds up and
  reverses with the scroll), Magnet (booking buttons), SpotlightCard,
  CountUp and DecryptedText.

Everything has a reduced-motion fallback; pointer effects are off on touch.

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # static output in dist/
```

Needs Node 18+. Deployed on Render as a static site from the `site` branch,
which mirrors this folder at its root plus `render.yaml` (Blueprint). Pushes
to `site` redeploy automatically.

## Content rules

- No client results. Mock screens say "Illustrative", the season row says
  "Example season", and the calculator only does arithmetic on the visitor's
  own inputs. The page mentions the cricket-academy client only as where the
  services come from, unnamed and without numbers. Add names or results only
  with the client's written consent.
- No prices, guarantees or reply-time promises: none are confirmed. The FAQ
  says ad budget is recommended in the review.
- The "Built for" strip lists kinds of academy, not client names.
- Channel icons come from the `simple-icons` package and only name the tools
  the services use.

## Before going live

- Fill in `src/config.ts`: booking link, business email, WhatsApp number.
  Until a booking link or email is set, every "Book a free review" button
  scrolls to the closing section.
- Mass text messaging needs an SMS provider and opt-in/opt-out handling before
  it is offered; the "consent-first messaging" line commits to it.
