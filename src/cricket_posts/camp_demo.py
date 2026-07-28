from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field

from .ideogram import generate_from_prompt
from .renderer import ASSET_DIR, PROJECT_ROOT, TEMPLATE_DIR, screenshot


RAW_PROMPT = """A cricket academy summer camp promotional poster. Include the following text
exactly as written, rendered clearly:

Header text: "SUPER KINGS ACADEMY"

Title: "HIGH PERFORMANCE SUMMER CAMP 2026"
Subtitle: "TRAIN LIKE A PROFESSIONAL THIS SUMMER"

Schedule line: "June 15 - August 21, 2026 | Monday - Friday | 8:00 AM - 12:00 PM"
Program info line: "High Performance Cricket Program | Ages 10-14 Years | 8-Week Program"

Section heading: "PROGRAM HIGHLIGHTS"
Bullet points: "Batting Development", "Fast & Spin Bowling Programs",
"Match Simulation & Game Awareness", "Power Hitting & Finishing Skills",
"Fielding & Athletic Development", "Tactical & Mental Preparation",
"High-Intensity Outdoor Training"

Section heading: "LEARN FROM"
Text: "First-Class Cricketers, ICC Certified Coaches, Pakistan First-Class
Professionals, Elite High-Performance Coaches"

Section heading: "WHY JOIN"
Text: "Professional training environment focused on: Skill Development,
Tactical Awareness, Match Preparation, Confidence & Discipline"

Head coach section: "Head Coach: IAN DEV SINGH CHAUHAN"
Coach bio text: "Professional Cricketer, Head Coach Super Kings Academy Texas -
17 First-Class Centuries - Houston Open Champion 2026 - 8000+ First-Class
Runs across all 3 formats - MiLC Seattle Thunderbolts Captain"

Call to action text: "Contact Us Now To Register" and "Limited Spots Available"

Footer text: "15905 Ronald Reagan Blvd, Leander, Texas" and phone number
"+1 (678) 938-9396"

Style: bold sports academy poster, cricket theme, blue and yellow color
scheme, vertical format."""


CAMP_COPY = {
    "header": "SUPER KINGS ACADEMY",
    "title": "HIGH PERFORMANCE SUMMER CAMP 2026",
    "subtitle": "TRAIN LIKE A PROFESSIONAL THIS SUMMER",
    "schedule": "June 15 - August 21, 2026 | Monday - Friday | 8:00 AM - 12:00 PM",
    "program_info": "High Performance Cricket Program | Ages 10-14 Years | 8-Week Program",
    "highlights_heading": "PROGRAM HIGHLIGHTS",
    "highlights": [
        "Batting Development",
        "Fast & Spin Bowling Programs",
        "Match Simulation & Game Awareness",
        "Power Hitting & Finishing Skills",
        "Fielding & Athletic Development",
        "Tactical & Mental Preparation",
        "High-Intensity Outdoor Training",
    ],
    "learn_heading": "LEARN FROM",
    "learn_text": (
        "First-Class Cricketers, ICC Certified Coaches, Pakistan First-Class "
        "Professionals, Elite High-Performance Coaches"
    ),
    "why_heading": "WHY JOIN",
    "why_text": (
        "Professional training environment focused on: Skill Development, "
        "Tactical Awareness, Match Preparation, Confidence & Discipline"
    ),
    "coach": "Head Coach: IAN DEV SINGH CHAUHAN",
    "coach_bio": (
        "Professional Cricketer, Head Coach Super Kings Academy Texas - "
        "17 First-Class Centuries - Houston Open Champion 2026 - 8000+ First-Class "
        "Runs across all 3 formats - MiLC Seattle Thunderbolts Captain"
    ),
    "cta": "Contact Us Now To Register",
    "availability": "Limited Spots Available",
    "address": "15905 Ronald Reagan Blvd, Leander, Texas",
    "phone": "+1 (678) 938-9396",
}


class ArtDirection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ideogram_prompt: str = Field(min_length=80, max_length=1600)
    rationale: str = Field(min_length=20, max_length=500)


NO_TEXT_GUARDRAIL = (
    " STRICT OUTPUT CONSTRAINT: background artwork only. The image must contain zero "
    "readable typography and zero pseudo-typography: no text, letters, words, numbers, "
    "labels, signs, banners, logos, brand marks, jersey writing, captions, interface "
    "elements, borders, or watermarks anywhere. Clothing must be completely unbranded."
)


def guarded_art_prompt(prompt: str) -> str:
    clean = prompt.replace("â€œ", "").replace("â€\u009d", "").rstrip(" ,.")
    return f"{clean}.{NO_TEXT_GUARDRAIL}"


def create_art_direction() -> ArtDirection:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.responses.parse(
        model=os.getenv("OPENAI_MODEL", "gpt-5.4"),
        instructions=(
            "You are an art director. Convert the supplied dense cricket camp poster request "
            "into a prompt for BACKGROUND ARTWORK ONLY. Preserve the blue and yellow sports "
            "identity and vertical composition. Put a dynamic teenage cricket batter on the "
            "right, stadium/training atmosphere behind them, and keep the left and lower areas "
            "dark, simple, and usable for typography. Absolutely no text, letters, numbers, "
            "signage, logos, sponsor marks, UI, borders, or watermarks. Do not repeat any factual "
            "copy in the art prompt."
        ),
        input=RAW_PROMPT,
        text_format=ArtDirection,
        reasoning={"effort": "low"},
    )
    if response.output_parsed is None:
        raise RuntimeError("GPT-5.4 did not return a usable art direction.")
    return response.output_parsed


def render_hybrid(background: Path, destination: Path) -> Path:
    environment = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(("html", "xml")),
    )
    html = environment.get_template("camp.html").render(
        copy=CAMP_COPY,
        background_url=background.resolve().as_uri(),
        logo_url=(ASSET_DIR / "mark.svg").resolve().as_uri(),
    )
    html_path = PROJECT_ROOT / "output" / "html" / "camp-hybrid.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html, encoding="utf-8")
    return screenshot(html_path, destination)


def render_comparison(raw_image: Path, hybrid_image: Path, destination: Path) -> Path:
    environment = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    html = environment.get_template("camp-comparison.html").render(
        raw_url=raw_image.resolve().as_uri(),
        hybrid_url=hybrid_image.resolve().as_uri(),
    )
    html_path = PROJECT_ROOT / "output" / "html" / "camp-comparison.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html, encoding="utf-8")
    return screenshot(html_path, destination, width=1460, height=820)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--refine-art",
        action="store_true",
        help="Regenerate only the guarded text-free artwork and hybrid poster.",
    )
    args = parser.parse_args()

    load_dotenv(PROJECT_ROOT / ".env")
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("IDEOGRAM_API_KEY"):
        raise RuntimeError("Both OPENAI_API_KEY and IDEOGRAM_API_KEY are required.")

    output = PROJECT_ROOT / "output" / "camp"
    output.mkdir(parents=True, exist_ok=True)

    if args.refine_art:
        direction_text = (output / "art-direction.txt").read_text(encoding="utf-8")
        original_prompt = direction_text.split("\n\nRATIONALE\n", maxsplit=1)[0]
        final_prompt = guarded_art_prompt(original_prompt)
        (output / "art-direction-guarded.txt").write_text(final_prompt, encoding="utf-8")
        artwork = generate_from_prompt(final_prompt, output / "artwork-clean.png")
        hybrid = render_hybrid(artwork, output / "hybrid-poster.png")
        render_comparison(
            output / "raw-ideogram.png",
            hybrid,
            output / "comparison.png",
        )
        print(f"Refined text-free artwork and hybrid poster in {output}")
        return

    direction = create_art_direction()
    (output / "art-direction.txt").write_text(
        f"{direction.ideogram_prompt}\n\nRATIONALE\n{direction.rationale}\n",
        encoding="utf-8",
    )
    raw = generate_from_prompt(RAW_PROMPT, output / "raw-ideogram.png")
    final_prompt = guarded_art_prompt(direction.ideogram_prompt)
    (output / "art-direction-guarded.txt").write_text(final_prompt, encoding="utf-8")
    artwork = generate_from_prompt(final_prompt, output / "artwork.png")
    hybrid = render_hybrid(artwork, output / "hybrid-poster.png")
    render_comparison(raw, hybrid, output / "comparison.png")
    print(f"Created raw and hybrid camp poster versions in {output}")


if __name__ == "__main__":
    main()
