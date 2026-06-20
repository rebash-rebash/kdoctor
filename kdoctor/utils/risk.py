def clamp_score(score: int) -> int:
    return max(0, min(100, int(score)))


def risk_from_score(score: int) -> str:
    if score >= 90:
        return "LOW"

    if score >= 70:
        return "MEDIUM"

    return "HIGH"


def score_style(score: int) -> str:
    if score >= 90:
        return "green"

    if score >= 70:
        return "yellow"

    return "red"


class RiskEngine:
    def __init__(self, starting_score: int = 100):
        self.score = starting_score
        self.reasons = []

    def penalize(self, points: int, reason: str):
        if points <= 0:
            return

        self.score -= points
        self.reasons.append(reason)

    def result(self):
        score = clamp_score(self.score)

        return {
            "score": score,
            "risk": risk_from_score(score),
            "reasons": self.reasons
        }


class RecommendationEngine:
    def __init__(self):
        self._items = []

    def add(self, condition: bool, text: str):
        if condition and text not in self._items:
            self._items.append(text)

    def items(self):
        return list(self._items)
