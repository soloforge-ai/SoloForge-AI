from backend.content_router import classify_route


def test_text_route_for_personal_post() -> None:
    assert classify_route({"format": "personal_post", "needs_video": False}) == "TEXT"


def test_visual_route_for_carousel() -> None:
    assert classify_route({"format": "carousel", "needs_video": False}) == "VISUAL"


def test_video_route_wins_when_needs_video_is_true() -> None:
    assert classify_route({"format": "personal_post", "needs_video": True}) == "VIDEO"


def test_video_route_from_format_hint() -> None:
    assert classify_route({"format": "short_video_demo"}) == "VIDEO"
