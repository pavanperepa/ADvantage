"""Content decomposed into placeable blocks with a priority.

`PosterContent` is a flat record, which gives a layout engine nothing to
negotiate with: it can only render everything or fail. Splitting it into blocks
that each carry a priority is what makes layout adjustable in *both* directions
— `OPTIONAL` blocks are promoted to fill space that would otherwise sit empty,
and demoted when copy overruns.

Two invariants hold, and both are tested:

* **Nothing is invented.** Every value is copied verbatim from the source.
* **Nothing is lost or duplicated.** The union of block values equals the set of
  display strings, each owned by exactly one block.
"""

from __future__ import annotations

from enum import Enum

import re

from pydantic import BaseModel, ConfigDict, Field

from .models import (
    BrandProfile,
    CampContent,
    PosterContent,
    TournamentContent,
)


_DOMAIN = re.compile(r"[\w-]+\.(com|org|net|io|co)", re.I)


class BlockRole(str, Enum):
    LOCKUP = "lockup"
    HEADLINE = "headline"
    BADGE = "badge"
    SCHEDULE = "schedule"
    PRICE = "price"
    PARAGRAPH = "paragraph"
    BULLETS = "bullets"
    CATEGORY = "category"
    RIBBON = "ribbon"
    STAT_CHIPS = "stat_chips"
    INFO_BAR = "info_bar"
    BANNER = "banner"


class BlockPriority(str, Enum):
    #: Never dropped. If it cannot fit, the poster is reported as over-long.
    REQUIRED = "required"
    #: Dropped only after every optional block has already gone.
    PREFERRED = "preferred"
    #: Rendered only when there is room. This is the filler that closes gaps.
    OPTIONAL = "optional"


class ContentBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: BlockRole
    priority: BlockPriority
    values: list[str] = Field(default_factory=list)
    heading: str = ""
    #: Long prose can be broken across columns.
    splittable: bool = False
    #: Adjacent blocks of the same role can be folded together.
    mergeable: bool = False
    order: int = 0

    def display_values(self) -> list[str]:
        return [value for value in ([self.heading] + self.values) if value.strip()]


def _looks_like_link(value: str) -> bool:
    """A URL or an email: something the reader clicks rather than reads."""
    return " " not in value and ("@" in value or _DOMAIN.search(value) is not None)


def _clean(*values: str) -> list[str]:
    return [value.strip() for value in values if value and value.strip()]


def derive_blocks(
    content: PosterContent,
    brand: BrandProfile | None = None,
) -> list[ContentBlock]:
    blocks: list[ContentBlock] = []
    order = 0

    def add(
        role: BlockRole,
        priority: BlockPriority,
        values: list[str],
        *,
        heading: str = "",
        splittable: bool = False,
        mergeable: bool = False,
    ) -> None:
        nonlocal order
        if not values and not heading.strip():
            return
        blocks.append(
            ContentBlock(
                role=role,
                priority=priority,
                values=values,
                heading=heading.strip(),
                splittable=splittable,
                mergeable=mergeable,
                order=order,
            )
        )
        order += 1

    # --- identity ----------------------------------------------------------
    lockup = _clean(content.organization or (brand.name if brand else ""))
    # The eyebrow is one source string even when it carries newlines. Breaking
    # it into lines is the component's job at render time; doing it here would
    # invent strings that never appeared in the source.
    lockup += _clean(content.eyebrow)
    if brand and brand.tagline:
        lockup += _clean(brand.tagline)
    add(BlockRole.LOCKUP, BlockPriority.REQUIRED, lockup)

    add(BlockRole.HEADLINE, BlockPriority.REQUIRED, _clean(content.title))
    add(BlockRole.BADGE, BlockPriority.PREFERRED, _clean(content.subtitle))

    if isinstance(content, TournamentContent):
        add(
            BlockRole.BADGE,
            BlockPriority.PREFERRED,
            _clean(content.short_name, content.organizer_tagline),
        )

    if content.schedule and content.schedule.display():
        add(BlockRole.SCHEDULE, BlockPriority.PREFERRED, [content.schedule.display()])
    add(BlockRole.PRICE, BlockPriority.PREFERRED, _clean(content.price_line))
    if isinstance(content, CampContent):
        add(BlockRole.PRICE, BlockPriority.PREFERRED, _clean(content.program_info))

    # Short facts make good filler: they read well as chips when there is room.
    add(
        BlockRole.STAT_CHIPS,
        BlockPriority.OPTIONAL,
        _clean(*content.detail_lines),
        mergeable=True,
    )

    # --- body --------------------------------------------------------------
    for section in content.sections:
        heading = section.heading.strip()
        text = section.text.strip()
        items = _clean(*section.items)
        if items:
            add(
                BlockRole.BULLETS,
                BlockPriority.PREFERRED,
                items,
                heading=heading,
                splittable=True,
            )
            # A heading paired with items owns the heading; any prose alongside
            # it becomes its own paragraph so neither string is lost.
            if text:
                add(BlockRole.PARAGRAPH, BlockPriority.PREFERRED, [text], splittable=True)
        elif heading and text:
            # A short heading plus a short payoff line is a slogan ribbon.
            add(BlockRole.RIBBON, BlockPriority.OPTIONAL, [text], heading=heading)
        elif text:
            add(
                BlockRole.PARAGRAPH,
                BlockPriority.PREFERRED,
                [text],
                splittable=True,
                mergeable=True,
            )
        elif heading:
            add(BlockRole.PARAGRAPH, BlockPriority.PREFERRED, [], heading=heading)

    if isinstance(content, CampContent) and (content.coach_heading or content.coach_bio):
        add(
            BlockRole.PARAGRAPH,
            BlockPriority.PREFERRED,
            _clean(content.coach_bio),
            heading=content.coach_heading.strip(),
            splittable=True,
        )

    if isinstance(content, TournamentContent):
        for category in content.categories:
            values = _clean(category.registration_fee)
            values += [prize.display() for prize in category.prizes if prize.display()]
            values += _clean(category.awards_heading, *category.awards)
            values += [
                contact.display() for contact in category.contacts if contact.display()
            ]
            add(
                BlockRole.CATEGORY,
                BlockPriority.PREFERRED,
                values,
                heading=category.name,
                mergeable=True,
            )

    # --- contact -----------------------------------------------------------
    # Emitted as separate blocks rather than one flat list. Re-deriving which
    # label belongs to which value from string shape put "CALL OR TEXT" above a
    # website; the source order already knows, so carry it.
    where = list(_clean(*content.location_lines))
    if not where and brand and brand.location:
        where = _clean(brand.location)
    if brand:
        where += _clean(*brand.contact_lines)
    add(BlockRole.INFO_BAR, BlockPriority.REQUIRED, where, heading="")

    # A call-to-action line immediately before a link labels that link; the last
    # unclaimed one labels the phone numbers. Anything still unclaimed becomes a
    # chip rather than being dropped — an earlier version kept only the final
    # label and silently lost "Contact Us Now To Register".
    web_label, links, pending, spare = "", [], "", []
    for line in _clean(*content.cta_lines):
        if _looks_like_link(line):
            links.append(line)
            if pending:
                web_label, pending = pending, ""
        else:
            if pending:
                spare.append(pending)
            pending = line
    add(BlockRole.INFO_BAR, BlockPriority.REQUIRED, links, heading=web_label)

    phones = [contact.display() for contact in content.contacts if contact.display()]
    add(BlockRole.INFO_BAR, BlockPriority.REQUIRED, phones, heading=pending)
    add(BlockRole.STAT_CHIPS, BlockPriority.REQUIRED, spare, mergeable=True)

    add(BlockRole.BANNER, BlockPriority.OPTIONAL, _clean(content.tagline))
    return blocks


def block_values(blocks: list[ContentBlock]) -> list[str]:
    values: list[str] = []
    for block in blocks:
        values.extend(block.display_values())
    return values


def missing_from_blocks(
    blocks: list[ContentBlock],
    expected: list[str],
) -> list[str]:
    """Source strings that no block claimed — must always be empty."""
    owned = set(block_values(blocks))
    return [value for value in expected if value.strip() and value.strip() not in owned]


#: Roles that repeat as sibling cards. Two divisions genuinely sharing an entry
#: fee is correct content, not a double-render, so they are excluded from the
#: duplication check.
REPEATING_ROLES = frozenset({BlockRole.CATEGORY})


def duplicated_in_blocks(
    blocks: list[ContentBlock],
    *,
    ignore_roles: frozenset[BlockRole] = REPEATING_ROLES,
) -> list[str]:
    """Strings claimed by more than one block, which would render twice."""
    seen: dict[str, int] = {}
    for block in blocks:
        if block.role in ignore_roles:
            continue
        for value in block.display_values():
            seen[value] = seen.get(value, 0) + 1
    return sorted(value for value, count in seen.items() if count > 1)


def by_priority(
    blocks: list[ContentBlock],
    priority: BlockPriority,
) -> list[ContentBlock]:
    return [block for block in blocks if block.priority is priority]
