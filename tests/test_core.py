from pathlib import Path

from app.services.food_engine import FoodWasteEngine


def test_dashboard_has_agentic_recommendations() -> None:
    snapshot = FoodWasteEngine(Path("data")).snapshot()
    assert snapshot["prediction"]["recommended_prepare"] > 0
    assert len(snapshot["agents"]) == 3
    assert snapshot["inventory"][0]["risk_score"] >= snapshot["inventory"][-1]["risk_score"]


def test_temperature_increases_safety_risk() -> None:
    engine = FoodWasteEngine(Path("data"))
    name = next(item["food"] for item in engine.snapshot()["inventory"] if item["risk_score"] < 100)
    before = next(item for item in engine.snapshot()["inventory"] if item["food"] == name)["risk_score"]
    after = next(item for item in engine.update_temperature(name, 9.0)["inventory"] if item["food"] == name)["risk_score"]
    assert after > before
