def score_lead(budget: str, need: str) -> tuple[int, str]:
    score = 30
    b = (budget or "").lower()
    n = (need or "").lower()

    high_budget_terms = ["1000", "2000", "3000", "5000", "10000", "$", "usd", "บาท", "thb"]
    urgent_terms = ["urgent", "asap", "this week", "immediately"]
    automation_terms = ["automation", "telegram", "bot", "api", "crm", "lead", "notification"]

    if any(t in b for t in high_budget_terms):
        score += 25
    if any(t in n for t in automation_terms):
        score += 25
    if any(t in n for t in urgent_terms):
        score += 15
    if len(n.strip()) >= 40:
        score += 5

    score = max(0, min(score, 100))
    label = "HOT" if score >= 80 else "WARM" if score >= 60 else "COLD"
    return score, label
