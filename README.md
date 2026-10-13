# ADvantage website

Single-page marketing site for ADvantage, the enrollment growth partner for
youth academies. Its one job is to get an academy owner to book a free
15-minute ads and enrollment review. Copy and positioning come from the
"ADvantage: Growth Operator Strategy" doc (Positioning, Packages and Website
sections).

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
- The results section says "a Houston cricket academy". Name 22Yards only with
  their written consent.
- FAQ answers on contract terms, start time and the second-month-free guarantee
  are proposed policy; confirm them before launch.
