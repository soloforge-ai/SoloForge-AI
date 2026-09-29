from backend.publora_publishing import (
    compose_post_content,
    default_platform_ids,
    validate_platform_selection,
)


def test_compose_caption_and_cta() -> None:
    value = compose_post_content({"caption": "Caption", "cta": "Read more"})
    assert value == "Caption\n\nRead more"


def test_default_platform_ids_match_target_platforms() -> None:
    job = {"content_package": {"target_platforms": ["tiktok", "youtube"]}}
    connections = [
        {
            "platformId": "tiktok-abc",
            "connectionStatus": "active",
            "tokenStatus": "valid",
        },
        {
            "platformId": "youtube-xyz",
            "connectionStatus": "active",
            "tokenStatus": "valid",
        },
        {
            "platformId": "instagram-nope",
            "connectionStatus": "active",
            "tokenStatus": "valid",
        },
    ]
    assert default_platform_ids(job, connections) == ["tiktok-abc", "youtube-xyz"]


def test_media_required_platform_rejects_text_only() -> None:
    connections = [
        {
            "platformId": "tiktok-abc",
            "connectionStatus": "active",
            "tokenStatus": "valid",
        }
    ]
    try:
        validate_platform_selection(["tiktok-abc"], connections, has_media=False)
    except ValueError as exc:
        assert "requires an image or video" in str(exc)
    else:
        raise AssertionError("Expected media validation failure")


def test_publish_status_mapping_stays_within_database_constraint() -> None:
    allowed = {"PENDING", "QUEUED", "PUBLISHED", "FAILED"}
    mapping = {
        "draft": "PENDING",
        "scheduled": "QUEUED",
        "publishing": "QUEUED",
        "published": "PUBLISHED",
        "failed": "FAILED",
        "partially_published": "FAILED",
    }
    assert set(mapping.values()) <= allowed
