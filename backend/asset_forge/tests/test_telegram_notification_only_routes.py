"""Regression guard: only operational Telegram notifications are mounted."""

import ast
from pathlib import Path


MAIN = Path(__file__).resolve().parents[1] / "main.py"


def test_notification_only_telegram_routes_are_mounted():
    tree = ast.parse(MAIN.read_text(encoding="utf-8"))
    registered = {
        call.args[0].id
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr)
        and isinstance(call := node.value, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "include_router"
        and call.args
        and isinstance(call.args[0], ast.Name)
    }
    assert "ops_webhook_router" in registered
    assert "idea_flow_webhook_router" not in registered
    assert "telegram_miniapp_router" not in registered


def test_legacy_telegram_handlers_are_not_imported_at_startup():
    tree = ast.parse(MAIN.read_text(encoding="utf-8"))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert "backend.combined_telegram_webhook" not in imports
    assert "backend.telegram_miniapp" not in imports
