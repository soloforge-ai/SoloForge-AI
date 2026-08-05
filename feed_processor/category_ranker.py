"""
SoloForge AI
Category Ranker

Sprint 43

Streaming Category Ranking Engine
"""

import heapq
from collections import defaultdict


class CategoryRanker:
    """
    Streaming Category Ranker

    Keep only Top N products for each category.
    """

    def __init__(self, top_n: int = 200):

        self.top_n = top_n

        self.heaps = defaultdict(list)

    # --------------------------------------------------

    def add(self, product: dict):
        """
        Add one product into the ranking.
        """

        category = self._category(product)
        score = self._score(product)

        heap = self.heaps[category]

        # ยังไม่เต็ม
        if len(heap) < self.top_n:

            heapq.heappush(
                heap,
                (score, id(product), product),
            )

        # เต็มแล้ว
        elif score > heap[0][0]:

            heapq.heapreplace(
                heap,
                (score, id(product), product),
            )

    # --------------------------------------------------

    def finish(self) -> dict:
        """
        Return ranked products by category.
        """

        output = {}

        for category, heap in self.heaps.items():

            products = sorted(
                heap,
                key=lambda x: x[0],
                reverse=True,
            )

            output[category] = [
                product
                for _, _, product in products
            ]

        return output

    # --------------------------------------------------

    @staticmethod
    def _score(product):

        return (
            product.get("miniBossScore")
            or product.get("miniboss", {}).get("score")
            or 0.0
        )

    # --------------------------------------------------

    @staticmethod
    def _category(product):

        category = (
            product.get("category", "")
            .strip()
        )

        if not category:
            return "Uncategorized"

        return category