from __future__ import annotations

import os

from openai import OpenAI

from .models import Campaign


SYSTEM_PROMPT = """You are the content and art director for a modern cricket academy.
Return exactly three social posts: one information/announcement post, one tournament
registration post, and one combined coaching plus cricket-lane rental post.

Writing rules:
- Use concise, confident copy that can be read on a phone.
- Do not invent real claims about certifications, awards, or availability.
- If the request omits business facts, use clearly fictional sample facts.
- Keep required dates, prices, locations, and contact information in structured fields.
- Each art_prompt must describe artwork only. Explicitly require no text, letters,
  numbers, signage, logos, sponsor marks, or watermarks.
- Compose art_prompt artwork around useful negative space for the selected template.
- Use exactly 3-5 details per post and one post for each template_id.
- Palettes must be distinct but feel like one bold premium sports brand.
"""


def generate_campaign(user_request: str) -> Campaign:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing. Add it to .env.")

    client = OpenAI(api_key=api_key)
    response = client.responses.parse(
        model=os.getenv("OPENAI_MODEL", "gpt-5.4"),
        instructions=SYSTEM_PROMPT,
        input=user_request,
        text_format=Campaign,
        reasoning={"effort": "low"},
    )
    if response.output_parsed is None:
        raise RuntimeError(f"OpenAI returned no structured campaign: {response.output_text}")
    return response.output_parsed

