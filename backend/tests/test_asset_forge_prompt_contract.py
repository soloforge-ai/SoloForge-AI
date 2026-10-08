from backend.asset_forge.main import AssetForgeRequest, _build_prompt


def test_explicit_dog_color_overrides_white_master_fur() -> None:
    request = AssetForgeRequest(
        character="Red Dog chibi mascot",
        quantity=4,
    )

    prompt = _build_prompt(request, columns=2, rows=2, has_reference=True)

    assert "requested primary character color is RED" in prompt
    assert "main fur, coat, skin, body, or shell to red" in prompt
    assert "Do not keep the master reference's original main body color" in prompt


def test_named_character_without_explicit_color_gets_no_color_override() -> None:
    request = AssetForgeRequest(character="CEO", quantity=4)

    prompt = _build_prompt(request, columns=2, rows=2, has_reference=True)

    assert "NON-NEGOTIABLE COLOR OVERRIDE" not in prompt


def test_ceo_default_outfit_remains_unchanged() -> None:
    request = AssetForgeRequest(character="CEO", quantity=4)
    prompt = _build_prompt(request, columns=2, rows=2, has_reference=True)
    assert "APPROVED CONTEXTUAL WARDROBE OVERRIDE" not in prompt
    assert "skin tone, costume, proportions" in prompt


def test_ceo_fitness_outfit_preserves_identity_not_suit() -> None:
    request = AssetForgeRequest(character="CEO", wardrobe_variant="fitness", quantity=4)
    prompt = _build_prompt(request, columns=2, rows=2, has_reference=True)
    assert "Appropriate sportswear and athletic shoes" in prompt
    assert "clothing-only variation" in prompt
    assert "exact approved face, eyes, hair, glasses" in prompt
    assert "skin tone, costume, proportions" not in prompt
    assert "face, hair, glasses, outfit, and body proportions" not in prompt


def test_ceo_creator_outfit_does_not_change_other_characters() -> None:
    request = AssetForgeRequest(character="Cat", wardrobe_variant="creator", quantity=4)
    prompt = _build_prompt(request, columns=2, rows=2, has_reference=True)
    assert "APPROVED CONTEXTUAL WARDROBE OVERRIDE" not in prompt


def test_wardrobe_variant_rejects_unapproved_values() -> None:
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        AssetForgeRequest(character="CEO", wardrobe_variant="spacesuit")


def test_manifest_campaign_keeps_canon_outfit_even_when_creator_requested() -> None:
    request = AssetForgeRequest(character="CEO", campaign_id="manifest_glow_lab", wardrobe_variant="creator", quantity=4)
    prompt = _build_prompt(request, columns=2, rows=2, has_reference=True)
    assert "MANIFEST GLOW LAB: Keep the canonical white/cream luxury suit" in prompt
    assert "APPROVED CONTEXTUAL WARDROBE OVERRIDE" not in prompt


def test_non_manifest_campaign_allows_creator_variant() -> None:
    request = AssetForgeRequest(character="CEO", campaign_id="other", wardrobe_variant="creator", quantity=4)
    prompt = _build_prompt(request, columns=2, rows=2, has_reference=True)
    assert "APPROVED CONTEXTUAL WARDROBE OVERRIDE" in prompt
