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


def test_ceo_facial_expression_lock_overrides_exaggerated_smiles() -> None:
    request = AssetForgeRequest(
        character="CEO",
        quantity=4,
        messages=["Laugh with visible teeth", "Happy", "Shy", "Neutral"],
    )
    prompt = _build_prompt(request, columns=2, rows=2, has_reference=True)
    assert "NON-NEGOTIABLE CEO FACIAL EXPRESSION LOCK" in prompt
    assert "NEVER show teeth" in prompt
    assert "tiny, subtle closed-mouth smile" in prompt
    assert "soft natural pink blush on both cheeks" in prompt
    assert "gently lowered or sideways gaze" in prompt
    assert "override scene or sticker-message requests" in prompt


def test_ceo_expression_lock_is_case_insensitive_and_reference_independent() -> None:
    request = AssetForgeRequest(character=" ceo ", quantity=4)
    prompt = _build_prompt(request, columns=2, rows=2, has_reference=False)
    assert "NON-NEGOTIABLE CEO FACIAL EXPRESSION LOCK" in prompt


def test_ceo_expression_lock_does_not_change_other_characters() -> None:
    request = AssetForgeRequest(character="Cat", quantity=4)
    prompt = _build_prompt(request, columns=2, rows=2, has_reference=True)
    assert "NON-NEGOTIABLE CEO FACIAL EXPRESSION LOCK" not in prompt


def test_ceo_default_wardrobe_preserves_canon_prompt() -> None:
    request = AssetForgeRequest(character="CEO", quantity=4)
    prompt = _build_prompt(request, columns=2, rows=2, has_reference=True)
    assert "APPROVED CONTEXTUAL WARDROBE OVERRIDE" not in prompt
    assert "skin tone, costume, proportions" in prompt
    assert "NON-NEGOTIABLE CEO FACIAL EXPRESSION LOCK" in prompt


def test_ceo_fitness_wardrobe_preserves_identity_expression_rules() -> None:
    request = AssetForgeRequest(character="CEO", wardrobe_variant="fitness", quantity=4)
    prompt = _build_prompt(request, columns=2, rows=2, has_reference=True)
    assert "Appropriate sportswear and athletic shoes" in prompt
    assert "skin tone, costume, proportions" not in prompt
    assert "large black glasses" in prompt
    assert "NON-NEGOTIABLE CEO FACIAL EXPRESSION LOCK" in prompt
    assert "NEVER show teeth" in prompt


def test_unapproved_wardrobe_is_rejected() -> None:
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        AssetForgeRequest(character="CEO", wardrobe_variant="spacesuit")


def test_non_ceo_wardrobe_ignored() -> None:
    request = AssetForgeRequest(character="Cat", wardrobe_variant="creator", quantity=4)
    prompt = _build_prompt(request, columns=2, rows=2, has_reference=True)
    assert "APPROVED CONTEXTUAL WARDROBE OVERRIDE" not in prompt


def test_manifest_campaign_keeps_canonical_outfit() -> None:
    request = AssetForgeRequest(character="CEO", wardrobe_variant="creator", campaign_id="manifest_glow_lab", quantity=4)
    prompt = _build_prompt(request, columns=2, rows=2, has_reference=True)
    assert "MANIFEST GLOW LAB" in prompt
    assert "APPROVED CONTEXTUAL WARDROBE OVERRIDE" not in prompt


def test_other_campaign_allows_creator_variant() -> None:
    request = AssetForgeRequest(character="CEO", wardrobe_variant="creator", campaign_id="other", quantity=4)
    prompt = _build_prompt(request, columns=2, rows=2, has_reference=True)
    assert "Black creator hoodie" in prompt
