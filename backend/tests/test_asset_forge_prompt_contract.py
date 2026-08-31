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
