# ADvantage website

Single-page marketing site for ADvantage, the all-in-one growth assistant for
youth academies: it builds an academy's presence, learns its audience, runs its
campaigns and keeps families engaged while the owner focuses on coaching. Its
one job is to get an owner to book a free 15-minute growth review.

Section content follows the "ADvantage: Growth Operator Strategy" doc. The
headline positioning (growth assistant rather than done-for-you enrollment
partner) is newer than the doc's Positioning section.

Light theme. The mock product screens use the `.dark` token scope.

Stack: Vite + TypeScript, Three.js (hero and closing orbit), GSAP ScrollTrigger
(reveals, counters, step progress) and Lenis (smooth scroll). Animations are
disabled for visitors who set "reduce motion".

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # static output in dist/
```

Needs Node 18+. Deploys as static files (Vercel, Netlify, Cloudflare Pages).

## Before going live

- Fill in `src/config.ts`: booking link, business email, WhatsApp number.
  Empty values are hidden; until a booking link or email is set, every
  "Book a free review" button scrolls to the contact section.
- Prices in Packages are "from" figures taken from the low end of the price
  ranges to test. Confirm them after the first owner interviews.
- The page shows no client results. Mock screens are labelled "Illustrative",
  the season plan is labelled "Example season", and the outcome calculator only
  does arithmetic on the visitor's own inputs. Add real results only with the
  client's written consent.
- Some promised capabilities are not built yet (Google Business Profile
  updates, scheduled posting, review requests, WhatsApp/SMS messaging).
  Deliver them by hand or soften the copy before launch.
- FAQ answers on contract terms, start time and the second-month-free guarantee
  are proposed policy; confirm them before launch.
