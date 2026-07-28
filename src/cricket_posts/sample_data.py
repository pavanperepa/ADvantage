from __future__ import annotations

from .models import Campaign


SAMPLE_CAMPAIGN = Campaign.model_validate(
    {
        "academy_name": "BOUNDARY CRICKET",
        "location": "NORTH DALLAS, TEXAS",
        "posts": [
            {
                "template_id": "information",
                "eyebrow": "ACADEMY UPDATE",
                "title": "SUMMER HOURS",
                "subtitle": "More daylight. More practice. Extended evening sessions start this Monday.",
                "details": [
                    {"label": "MON–FRI", "value": "4:00 PM — 10:00 PM"},
                    {"label": "WEEKENDS", "value": "8:00 AM — 10:00 PM"},
                    {"label": "EFFECTIVE", "value": "JULY 01"},
                ],
                "cta": "SAVE THE SCHEDULE",
                "contact": "boundarycricket.com  •  (469) 555-0188",
                "badge": "OPEN 7 DAYS",
                "art_prompt": (
                    "Text-free editorial sports photograph of an indoor cricket practice lane at dusk, "
                    "deep navy shadows, one athlete in white seen from behind, fluorescent lime wickets, "
                    "clean premium athletic campaign, strong negative space in the upper left, no letters, "
                    "no numbers, no signs, no logos, no watermark."
                ),
                "palette": {
                    "ink": "#07110D",
                    "surface": "#F2F0E8",
                    "accent": "#B8F23D",
                    "highlight": "#FF6A3D",
                },
            },
            {
                "template_id": "tournament",
                "eyebrow": "YOUTH T20 • 2026",
                "title": "NORTH TEXAS\nSUMMER CUP",
                "subtitle": "Three match minimum. Certified umpires. One unforgettable weekend.",
                "details": [
                    {"label": "WHEN", "value": "JUL 18–19"},
                    {"label": "DIVISIONS", "value": "U12 • U14 • U16"},
                    {"label": "TEAM FEE", "value": "$499"},
                    {"label": "DEADLINE", "value": "JUL 10"},
                ],
                "cta": "REGISTER YOUR TEAM",
                "contact": "boundarycricket.com/cup  •  (469) 555-0188",
                "badge": "12 TEAM LIMIT",
                "art_prompt": (
                    "Text-free cinematic night cricket stadium viewed from pitch level, a polished gold "
                    "trophy placed right of center, hazy floodlights, navy and electric blue atmosphere, "
                    "premium tournament campaign photography, left third kept dark and uncluttered for "
                    "layout, no letters, no numbers, no sponsor marks, no logos, no watermark."
                ),
                "palette": {
                    "ink": "#06142C",
                    "surface": "#F3EAD3",
                    "accent": "#E9B949",
                    "highlight": "#26D9FF",
                },
            },
            {
                "template_id": "services",
                "eyebrow": "TRAIN • PLAY • REPEAT",
                "title": "YOUR GAME.\nYOUR LANE.",
                "subtitle": "Private coaching and bookable indoor lanes—built around your goals and your schedule.",
                "details": [
                    {"label": "01", "value": "1-ON-1 COACHING"},
                    {"label": "02", "value": "BATTING LANES"},
                    {"label": "03", "value": "BOWLING MACHINE"},
                    {"label": "04", "value": "TEAM SESSIONS"},
                ],
                "cta": "BOOK A SESSION",
                "contact": "NORTH DALLAS  •  (469) 555-0188",
                "badge": "FROM $35 / HOUR",
                "art_prompt": (
                    "Text-free energetic split-scene sports photograph inside a modern indoor cricket "
                    "academy, close-up batter training on the right and empty premium practice lane receding "
                    "on the left, burnt orange rim light, charcoal shadows, sharp editorial advertising style, "
                    "clean center transition, no letters, no numbers, no signs, no logos, no watermark."
                ),
                "palette": {
                    "ink": "#111111",
                    "surface": "#F0E8D9",
                    "accent": "#FF5C35",
                    "highlight": "#D7FF42",
                },
            },
        ],
    }
)

