import json
import re
from .openrouter import OpenRouterClient

class Evaluator:
    def __init__(self, client: OpenRouterClient):
        self.client = client

    @staticmethod
    def heuristic_score(prompt: str, response: str) -> float:
        if not response.strip():
            return 0.0
        prompt_terms = {w.lower() for w in re.findall(r"[a-zA-Z0-9]{4,}", prompt)}
        response_terms = {w.lower() for w in re.findall(r"[a-zA-Z0-9]{4,}", response)}
        overlap = len(prompt_terms & response_terms) / max(1, len(prompt_terms))
        completeness = min(len(response.strip()) / 500, 1.0)
        return round(min(1.0, 0.55 * overlap + 0.45 * completeness), 4)

    def judge(self, prompt: str, response: str, judge_model: str | None = None) -> float:
        score = self.heuristic_score(prompt, response)
        if not judge_model:
            return score
        judge_prompt = (
            "Score the answer from 0 to 10 for correctness, relevance, completeness and clarity. "
            'Return JSON only with a numeric score field, like {"score": 7}.\n\n'
            f"USER PROMPT:\\n{prompt}\\n\\nANSWER:\\n{response}"
        )
        try:
            data, _ = self.client.chat({
                "model": judge_model,
                "messages": [{"role": "user", "content": judge_prompt}],
                "temperature": 0,
                "max_tokens": 80,
            })
            raw = data["choices"][0]["message"]["content"]
            parsed = json.loads(re.sub(r"```json|```", "", raw).strip())
            return max(0.0, min(1.0, float(parsed["score"]) / 10.0))
        except Exception:
            return score
