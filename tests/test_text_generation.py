from __future__ import annotations

from fastapi.testclient import TestClient

from cricket_posts import campaign_api, text_generation_api
from cricket_posts.campaign import (
    CampaignArtifact,
    CampaignRequest,
    CampaignResult,
    CreativeFormat,
    VerificationResult,
)
from cricket_posts.studio import PosterStudio
from cricket_posts.text_generation import PushVariant, PushVariants
from cricket_posts.web import create_app


class FakeGenerator:
    def __init__(self) -> None:
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        return PushVariants(
            variants=[
                PushVariant(
                    title=f"Variant {index + 1}",
                    body=f"Body {index + 1}: {request.offer or request.product_name}",
                    reasoning_summary="Uses a distinct, factual framing.",
                )
                for index in range(request.number_of_variants)
            ]
        )


def _client(tmp_path) -> TestClient:
    studio = PosterStudio(database_path=tmp_path / "studio.db", output_root=tmp_path)
    return TestClient(create_app(studio))


def test_generate_push_returns_structured_variants(tmp_path, monkeypatch):
    fake = FakeGenerator()
    monkeypatch.setattr(text_generation_api, "get_push_generator", lambda: fake)
    client = _client(tmp_path)

    response = client.post(
        "/api/text-generation/push",
        json={
            "productName": "Everyday Tote",
            "productDescription": "A lightweight reusable bag.",
            "offer": "20% off through Friday",
            "targetAudience": "Busy commuters",
            "objective": "promote_offer",
            "tone": "casual",
            "messageFocus": "convenience",
            "cta": "Shop now",
            "additionalInstructions": "No emoji.",
            "numberOfVariants": 3,
        },
    )

    assert response.status_code == 200
    assert len(response.json()["variants"]) == 3
    assert fake.requests[0].offer == "20% off through Friday"


def test_regeneration_instruction_and_selected_variant_reach_generator(
    tmp_path, monkeypatch
):
    fake = FakeGenerator()
    monkeypatch.setattr(text_generation_api, "get_push_generator", lambda: fake)
    client = _client(tmp_path)

    response = client.post(
        "/api/text-generation/push",
        json={
            "productName": "Everyday Tote",
            "numberOfVariants": 1,
            "regenerationInstruction": "Lead with the price and make the tone warmer.",
            "variantToReplace": "Old title\nOld body",
            "avoidVariants": ["Old title\nOld body"],
        },
    )

    assert response.status_code == 200
    request = fake.requests[0]
    assert request.regeneration_instruction == (
        "Lead with the price and make the tone warmer."
    )
    assert request.variant_to_replace == "Old title\nOld body"


def test_campaign_context_prefills_missing_generation_fields(tmp_path, monkeypatch):
    run_id = "campaign123"
    campaign_api._RUNS[run_id] = CampaignResult(
        request=CampaignRequest(
            business_name="Northstar Studio",
            brief_text="Beginner pottery classes for adults.",
            format=CreativeFormat.POSTER,
            offer_text="First class free",
            audience="Adults nearby",
        ),
        artifact=CampaignArtifact(
            format=CreativeFormat.POSTER,
            file_path="unused.png",
            width=1080,
            height=1350,
        ),
        verification=VerificationResult(passed=True),
    )
    fake = FakeGenerator()
    monkeypatch.setattr(text_generation_api, "get_push_generator", lambda: fake)
    client = _client(tmp_path)
    try:
        listed = client.get("/api/text-generation/campaigns")
        generated = client.post(
            "/api/text-generation/push",
            json={"campaignId": run_id, "numberOfVariants": 1},
        )
    finally:
        campaign_api._RUNS.pop(run_id, None)

    assert listed.status_code == 200
    assert listed.json()[0]["product_name"] == "Northstar Studio"
    assert generated.status_code == 200
    assert fake.requests[0].product_description == "Beginner pottery classes for adults."
    assert fake.requests[0].offer == "First class free"


def test_generation_requires_campaign_or_context(tmp_path):
    response = _client(tmp_path).post(
        "/api/text-generation/push", json={"numberOfVariants": 3}
    )

    assert response.status_code == 422
