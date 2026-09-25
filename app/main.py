from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.models import MealFeedback, StreamControl
from app.services.food_engine import FoodWasteEngine

BASE_DIR = Path(__file__).resolve().parent
engine = FoodWasteEngine(BASE_DIR.parent / "data")
app = FastAPI(title="WasteWise AI", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.on_event("startup")
def start_engine() -> None:
    engine.start()


@app.on_event("shutdown")
def stop_engine() -> None:
    engine.stop()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "food.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "WasteWise AI real-time food waste platform"}


@app.get("/api/dashboard")
def dashboard() -> dict:
    return engine.snapshot()


@app.post("/api/stream")
def set_stream(control: StreamControl) -> dict:
    engine.set_stream(control.enabled)
    return engine.snapshot()


@app.post("/api/stream/tick")
def add_tick() -> dict:
    return engine.tick()


@app.post("/api/weather/refresh")
def refresh_weather() -> dict:
    return engine.refresh_weather()


@app.post("/api/feedback")
def record_feedback(feedback: MealFeedback) -> dict:
    try:
        return engine.record_feedback(feedback.dish, feedback.reaction)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/feedback/simulate")
def simulate_daily_feedback() -> dict:
    return engine.simulate_daily_feedback()


@app.post("/api/items/{item_name}/temperature")
def update_temperature(item_name: str, temperature_c: float) -> dict:
    try:
        return engine.update_temperature(item_name, temperature_c)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
