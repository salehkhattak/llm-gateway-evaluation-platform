from app.evaluator import Evaluator

def test_heuristic_score_nonempty():
    score = Evaluator.heuristic_score("Explain Kubernetes deployment", "A Kubernetes deployment manages replicas and rolling updates.")
    assert 0 < score <= 1

def test_heuristic_score_empty():
    assert Evaluator.heuristic_score("hello", "") == 0
