# ADvantage website

Single-page marketing site for ADvantage: presence, campaigns and customer
follow-up for local businesses, run for the owner and measured every week. Its
one job is to get an owner to book a free 15-minute review.

## Design

Built to the taste-skill rules (tasteskill.dev): one ground (`#f2f1ec`), one
ink (`#121316`), one accent (`#c5f03c`) used on the action and on the people
who light up in the hero. One typeface, Instrument Sans. Surfaces separate by a
step in tone, never by lines, shadows or gradients. No eyebrow labels, no index
numbers, no stock photography. Each section has its own composition; the strategy section changes the
whole field to ink and the closing call to action changes it to the accent.

Signature move (`src/hero.ts`, Three.js): the business sits at the centre of a
faint crowd. Every four seconds it sends its work out as a pulse; as the pulse
passes, the right people light up and travel in to orbit it.

Other motion uses GSAP (ScrollTrigger, SplitText, DrawSVG) and Lenis: headings
rise line by line, the "Trusted by" strip scrolls under the hero, the app hub draws its connections, the
platform section keeps a product screen pinned while its panels change, the
strategy section scrolls sideways while pinned, and the outcomes chart draws in
and re-animates as the sliders move. Everything has a reduced-motion fallback.

The outcomes chart follows the dataviz skill: one axis, a 2px line per series,
legend plus direct end labels, a crosshair tooltip (mouse or arrow keys) and a
table view. Its two colours were run through the palette validator against the
panel tone; the grey baseline is a deliberate de-emphasis encoding.

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # static output in dist/
```

Needs Node 18+. Deployed on Render as a static site from this branch; see
`render.yaml` (Blueprint). Pushes to `site` redeploy automatically.

## Content rules

- No client results. Mock screens say "Illustrative", the strategy row says
  "Example plan", and the calculator only does arithmetic on the visitor's own
  inputs. Add real results only with the client's written consent.
- The "Trusted by" strip under the hero lists kinds of business, not client
  names. Keep it to kinds of business you actually serve.
- App icons come from the `simple-icons` package and are used only to name the
  tools the service connects to.

## Before going live

- Fill in `src/config.ts`: booking link, business email, WhatsApp number.
  Until a booking link or email is set, every "Book a free review" button
  scrolls to the closing section.
- Prices are "from" figures from the price ranges still being tested.
- Several promised capabilities are not built yet: scheduled posting, Google
  Business Profile updates, review requests, WhatsApp/SMS messaging, and
  HubSpot/Calendly connections. Deliver them by hand or soften the copy.
- FAQ answers on contract terms, start time and the second-month-free
  guarantee are proposed policy; confirm them before launch.
