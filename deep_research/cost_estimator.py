"""
CostEstimator - Analyzes query complexity and estimates research costs.

Provides pre-research cost and duration estimates based on query analysis.
Uses heuristics to predict whether research will complete synchronously or
require async background execution.
"""

from typing import Tuple

from . import CostEstimate


class CostEstimator:
    """Estimates cost and duration for deep research queries."""

    # Complexity indicators
    COMPLEX_KEYWORDS = [
        "comprehensive", "detailed", "in-depth", "thorough", "extensive",
        "analysis", "compare", "contrast", "evaluate", "synthesize",
        "implications", "geopolitical", "historical", "trends", "forecast"
    ]

    MULTI_DOMAIN_INDICATORS = [
        "and", "vs", "versus", "between", "across", "multiple",
        "different", "various", "compare", "relation"
    ]

    TEMPORAL_INDICATORS = [
        "history", "evolution", "timeline", "past", "future",
        "trends", "forecast", "prediction", "development", "changes"
    ]

    # Base estimates by complexity (min, max, likely) in minutes
    DURATION_ESTIMATES = {
        "simple": (0.5, 3, 1),
        "medium": (3, 20, 8),
        "complex": (15, 60, 35)
    }

    # Base cost estimates by complexity (min, max, likely) in USD
    COST_ESTIMATES = {
        "simple": (0.10, 0.50, 0.25),
        "medium": (0.50, 2.00, 1.00),
        "complex": (1.50, 6.00, 3.00)
    }

    def estimate(self, query: str) -> CostEstimate:
        """Generate a cost estimate for a research query.

        Args:
            query: The research question/topic to analyze

        Returns:
            CostEstimate with complexity, duration, cost, and recommendations
        """
        complexity = self._analyze_complexity(query)
        duration = self._estimate_duration(complexity)
        cost = self._estimate_cost(complexity)

        return CostEstimate(
            query_complexity=complexity,
            min_minutes=duration[0],
            max_minutes=duration[1],
            likely_minutes=duration[2],
            min_usd=cost[0],
            max_usd=cost[1],
            likely_usd=cost[2],
            will_likely_go_async=duration[2] > 1,  # >1 min likely goes async
            recommendation=self._generate_recommendation(complexity, query)
        )

    def _analyze_complexity(self, query: str) -> str:
        """Analyze query to determine complexity level.

        Factors considered:
        - Query length
        - Presence of complexity keywords
        - Multi-domain scope indicators
        - Temporal scope requirements
        - Question structure (compound vs simple)

        Args:
            query: The research query

        Returns:
            "simple", "medium", or "complex"
        """
        query_lower = query.lower()
        score = 0

        # Length factor
        word_count = len(query.split())
        if word_count > 50:
            score += 3
        elif word_count > 25:
            score += 2
        elif word_count > 10:
            score += 1

        # Complex keywords
        complex_count = sum(1 for kw in self.COMPLEX_KEYWORDS if kw in query_lower)
        score += min(complex_count, 4)  # Cap at 4 points

        # Multi-domain indicators
        domain_count = sum(1 for ind in self.MULTI_DOMAIN_INDICATORS if ind in query_lower)
        score += min(domain_count, 3)  # Cap at 3 points

        # Temporal indicators
        temporal_count = sum(1 for ind in self.TEMPORAL_INDICATORS if ind in query_lower)
        score += min(temporal_count, 2)  # Cap at 2 points

        # Question structure (multiple questions = more complex)
        question_marks = query.count("?")
        if question_marks > 2:
            score += 2
        elif question_marks > 1:
            score += 1

        # Entity detection (proper nouns, technical terms)
        # Simple heuristic: count capitalized words (excluding start of sentences)
        words = query.split()
        proper_nouns = sum(1 for i, w in enumerate(words[1:], 1)
                          if w and w[0].isupper() and not words[i-1].endswith(('.', '?', '!')))
        score += min(proper_nouns // 2, 2)  # Cap at 2 points

        # Determine complexity
        if score >= 8:
            return "complex"
        elif score >= 4:
            return "medium"
        else:
            return "simple"

    def _estimate_duration(self, complexity: str) -> Tuple[float, float, float]:
        """Get duration estimates based on complexity.

        Args:
            complexity: "simple", "medium", or "complex"

        Returns:
            Tuple of (min_minutes, max_minutes, likely_minutes)
        """
        return self.DURATION_ESTIMATES.get(complexity, self.DURATION_ESTIMATES["medium"])

    def _estimate_cost(self, complexity: str) -> Tuple[float, float, float]:
        """Get cost estimates based on complexity.

        Args:
            complexity: "simple", "medium", or "complex"

        Returns:
            Tuple of (min_usd, max_usd, likely_usd)
        """
        return self.COST_ESTIMATES.get(complexity, self.COST_ESTIMATES["medium"])

    def _generate_recommendation(self, complexity: str, query: str) -> str:
        """Generate human-readable recommendation based on analysis.

        Args:
            complexity: The determined complexity level
            query: The original query (for specific advice)

        Returns:
            Recommendation string
        """
        recommendations = {
            "simple": (
                "Simple query detected. Should complete quickly (under 2 minutes) "
                "and stay within synchronous execution."
            ),
            "medium": (
                "Medium complexity query. May take 5-15 minutes and could switch "
                "to async mode if initial processing exceeds 30 seconds. "
                "Consider enabling notifications for status updates."
            ),
            "complex": (
                "Complex multi-domain query detected. Will likely require 30+ minutes "
                "and switch to async mode. Consider breaking into smaller focused "
                "queries if time is critical, or enable notifications for completion alert."
            )
        }

        base_rec = recommendations.get(complexity, recommendations["medium"])

        # Add specific advice based on query content
        query_lower = query.lower()

        if "compare" in query_lower or "vs" in query_lower:
            base_rec += " Comparative analysis typically requires extensive source gathering."

        if any(geo in query_lower for geo in ["geopolitical", "international", "global"]):
            base_rec += " Geopolitical topics often involve diverse perspectives and may take longer."

        if len(query.split()) > 100:
            base_rec += " Very long query - consider summarizing or focusing on key aspects."

        return base_rec


# Module-level singleton for convenient access
_cost_estimator = None


def get_cost_estimator() -> CostEstimator:
    """Get or create the singleton CostEstimator instance."""
    global _cost_estimator
    if _cost_estimator is None:
        _cost_estimator = CostEstimator()
    return _cost_estimator
