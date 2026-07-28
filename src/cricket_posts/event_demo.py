from __future__ import annotations

import argparse
import html as html_module
import os
from pathlib import Path

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field

from .camp_demo import NO_TEXT_GUARDRAIL
from .ideogram import generate_from_prompt
from .renderer import ASSET_DIR, PROJECT_ROOT, TEMPLATE_DIR, screenshot


EVENT = {
    "event_name": "SVATS Cricket Cup 2026",
    "short_name": "SCC-2026",
    "organizer": "SVATS",
    "organizer_tagline": "Your Technology Partner",
    "date": "July 25, 2026",
    "location": "Avery Park Dublin, 7401 Avery Rd, Dublin, OH 43017",
    "tagline": "One Dream. One Chance. One Champion.",
    "categories": [
        {
            "name": "T7",
            "fee": "$150.00 per team",
            "contacts": [
                "Hari — +1 (248) 679-2806",
                "Sujith — +1 (612) 413-0983",
            ],
            "prize_heading": "Prize Money",
            "prizes": [
                "Winner $1000",
                "Finalist $700",
                "Semi Finalist $200",
            ],
            "awards_heading": "Individual Awards (Trophy)",
            "awards": [
                "Best Bowler",
                "Best Bats(man)",
                "MVP",
                "Power Hitter",
                "Economy",
            ],
        },
        {
            "name": "T7 40+",
            "fee": "$150.00 per team",
            "contacts": [
                "Venu — +1 (804) 873-6873",
                "Rama — +1 (303) 808-3700",
            ],
            "prize_heading": "Prize Money",
            "prizes": [
                "Winner $1000",
                "Finalist $700",
                "Semi Finalist $200",
            ],
            "awards_heading": "Individual Awards (Trophy)",
            "awards": [
                "Best Bowler",
                "Best Bats(man)",
                "Power Hitter",
                "Economy",
            ],
        },
        {
            "name": "KIDS",
            "fee": "$10.00 per player",
            "contacts": ["Raghu — +1 (425) 495-9221"],
            "prize_heading": "Prizes",
            "prizes": [
                "Winner Team (Individual Trophies)",
                "Runner-up Team (Individual Trophies)",
            ],
            "awards_heading": "Individual Awards",
            "awards": [
                "Best Bowler",
                "Best Batsman",
                "MVP",
                "Power Hitter (Most 6s)",
                "Most Dot Balls",
            ],
        },
    ],
}


RAW_PROMPT = """Create a bold vertical promotional poster for a one-day cricket tournament.
Render every supplied word, number, punctuation mark, and phone number clearly and accurately.

Event Name: "SVATS Cricket Cup 2026 (SCC-2026)"
Organized By: "SVATS — Your Technology Partner"
Date: "July 25, 2026"
Location: "Avery Park Dublin, 7401 Avery Rd, Dublin, OH 43017"
Tagline: "One Dream. One Chance. One Champion."

Category: "T7"
Registration Fee: "$150.00 per team"
Contact: "Hari — +1 (248) 679-2806; Sujith — +1 (612) 413-0983"
Prize Money: "Winner $1000 | Finalist $700 | Semi Finalist $200"
Individual Awards (Trophy): "Best Bowler, Best Bats(man), MVP, Power Hitter, Economy"

Category: "T7 40+"
Registration Fee: "$150.00 per team"
Contact: "Venu — +1 (804) 873-6873; Rama — +1 (303) 808-3700"
Prize Money: "Winner $1000 | Finalist $700 | Semi Finalist $200"
Individual Awards (Trophy): "Best Bowler, Best Bats(man), Power Hitter, Economy"

Category: "Kids"
Registration Fee: "$10.00 per player"
Contact: "Raghu — +1 (425) 495-9221"
Prizes: "Winner Team (Individual Trophies), Runner-up Team (Individual Trophies), Best Bowler, Best Batsman, MVP, Power Hitter (Most 6s), Most Dot Balls"

Style: premium modern cricket tournament poster, deep navy blue, electric cyan, warm gold,
dramatic trophy and stadium lighting, clean information hierarchy, vertical format."""


class TournamentArtDirection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ideogram_prompt: str = Field(min_length=80, max_length=1400)


def create_art_direction() -> str:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.responses.parse(
        model=os.getenv("OPENAI_MODEL", "gpt-5.4"),
        instructions=(
            "Create an Ideogram prompt for background artwork only. This is for a premium "
            "one-day community cricket tournament in Ohio. Use a cinematic cricket stadium, "
            "a trophy, a ball, deep navy, electric cyan, and warm gold. Keep the top-left area "
            "and entire lower two-thirds dark and visually quiet for dense typography. Place "
            "the trophy and sporting action in the upper-right. Do not include factual event "
            "content. Finish with an explicit prohibition against every form of text."
        ),
        input=RAW_PROMPT,
        text_format=TournamentArtDirection,
        reasoning={"effort": "low"},
    )
    if response.output_parsed is None:
        raise RuntimeError("GPT-5.4 returned no tournament art direction.")
    return f"{response.output_parsed.ideogram_prompt.rstrip(' ,.')}." + NO_TEXT_GUARDRAIL


def render_hybrid(background: Path, destination: Path) -> Path:
    environment = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(("html", "xml")),
    )
    rendered = environment.get_template("scc-event.html").render(
        event=EVENT,
        background_url=background.resolve().as_uri(),
        logo_url=(ASSET_DIR / "mark.svg").resolve().as_uri(),
    )
    html_path = PROJECT_ROOT / "output" / "html" / "scc-event.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(rendered, encoding="utf-8")
    return screenshot(html_path, destination)


def render_comparison(raw: Path, hybrid: Path, destination: Path) -> Path:
    environment = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    rendered = environment.get_template("scc-comparison.html").render(
        raw_url=raw.resolve().as_uri(),
        hybrid_url=hybrid.resolve().as_uri(),
    )
    html_path = PROJECT_ROOT / "output" / "html" / "scc-comparison.html"
    html_path.write_text(rendered, encoding="utf-8")
    return screenshot(html_path, destination, width=1460, height=820)


def exact_copy_audit() -> None:
    page = html_module.unescape(
        (PROJECT_ROOT / "output" / "html" / "scc-event.html").read_text(encoding="utf-8")
    )
    required = [
        EVENT["event_name"],
        EVENT["short_name"],
        EVENT["organizer"],
        EVENT["organizer_tagline"],
        EVENT["date"],
        EVENT["location"],
        EVENT["tagline"],
    ]
    for category in EVENT["categories"]:
        required.extend(
            [
                category["name"],
                category["fee"],
                category["prize_heading"],
                category["awards_heading"],
                *category["contacts"],
                *category["prizes"],
                *category["awards"],
            ]
        )
    missing = [value for value in required if value not in page]
    if missing:
        raise RuntimeError(f"Hybrid exact-copy audit failed: {missing}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--render-only",
        action="store_true",
        help="Reuse the existing raw and background images and rerender HTML only.",
    )
    args = parser.parse_args()

    load_dotenv(PROJECT_ROOT / ".env")
    output = PROJECT_ROOT / "output" / "scc-event"
    output.mkdir(parents=True, exist_ok=True)

    if args.render_only:
        raw = output / "raw-ideogram.png"
        artwork = output / "artwork.png"
        if not raw.exists() or not artwork.exists():
            raise RuntimeError("Run the full event demo before using --render-only.")
        hybrid = render_hybrid(artwork, output / "hybrid-poster.png")
        exact_copy_audit()
        render_comparison(raw, hybrid, output / "comparison.png")
        print(f"Rerendered SCC-2026 hybrid poster in {output}")
        print("Hybrid exact-copy audit: PASS")
        return

    if not os.getenv("OPENAI_API_KEY") or not os.getenv("IDEOGRAM_API_KEY"):
        raise RuntimeError("Both OPENAI_API_KEY and IDEOGRAM_API_KEY are required.")

    art_prompt = create_art_direction()
    (output / "art-direction.txt").write_text(art_prompt, encoding="utf-8")

    raw = generate_from_prompt(RAW_PROMPT, output / "raw-ideogram.png")
    artwork = generate_from_prompt(art_prompt, output / "artwork.png")
    hybrid = render_hybrid(artwork, output / "hybrid-poster.png")
    exact_copy_audit()
    render_comparison(raw, hybrid, output / "comparison.png")
    print(f"Created SCC-2026 raw and hybrid posters in {output}")
    print("Hybrid exact-copy audit: PASS")


if __name__ == "__main__":
    main()
