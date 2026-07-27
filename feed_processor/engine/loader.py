"""
SoloForge AI
MiniBoss Engine V2

Rules Loader
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

RULE_FILE = ROOT / "rules" / "miniboss_rules.json"


def load_rules():
    """
    Load MiniBoss rules from JSON.
    """

    with open(RULE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)