from __future__ import annotations

import csv
import json
import random
import threading
import urllib.request
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


DEFAULT_FOODKEEPER = [
    {"food": "Cooked Rice", "category": "Prepared food", "fridge_days": 4, "freezer_months": 2, "priority": "High"},
    {"food": "Cooked Chicken", "category": "Prepared food", "fridge_days": 4, "freezer_months": 4, "priority": "High"},
    {"food": "Milk", "category": "Dairy", "fridge_days": 7, "freezer_months": 3, "priority": "Medium"},
    {"food": "Leafy Greens", "category": "Produce", "fridge_days": 5, "freezer_months": 0, "priority": "High"},
    {"food": "Yogurt", "category": "Dairy", "fridge_days": 14, "freezer_months": 2, "priority": "Medium"},
    {"food": "Bread", "category": "Bakery", "fridge_days": 7, "freezer_months": 3, "priority": "Medium"},
]


class FoodWasteEngine:
    """Local digital-twin stream with an explainable multi-agent decision workflow."""

    def __init__(self, data_dir: Path) -> None:
        self._lock, self._stop = threading.RLock(), threading.Event()
        self._running, self._thread = True, None
        self._foodkeeper = self._load_foodkeeper(data_dir)
        self._dataset_label = "USDA FoodKeeper v128 dataset (661 food records)" if (data_dir / "foodkeeper.json").exists() else "USDA FoodKeeper-compatible local dataset"
        self._events: deque[dict[str, Any]] = deque(maxlen=18)
        self._history: deque[dict[str, Any]] = deque(maxlen=28)
        self._inventory = self._initial_inventory()
        self._weather = self._fallback_weather()
        self._last_weather_refresh = "Simulation context"
        self._seed_history()
        self._add_event("SYSTEM", "Live food telemetry simulator ready", "info")

    def _load_foodkeeper(self, data_dir: Path) -> list[dict[str, Any]]:
        # The Kaggle USDA FoodKeeper JSON is an XLSX-sheet export, with Product and Category sheets.
        json_candidate = data_dir / "foodkeeper.json"
        if json_candidate.exists():
            try:
                with json_candidate.open(encoding="utf-8") as file:
                    workbook = json.load(file)
                sheets = {sheet.get("name"): sheet.get("data", []) for sheet in workbook.get("sheets", [])}
                categories = {}
                for row in sheets.get("Category", []):
                    category = self._flatten_sheet_row(row)
                    if category.get("ID") is not None:
                        categories[category["ID"]] = category.get("Category_Name", "USDA FoodKeeper")
                parsed = []
                for row in sheets.get("Product", []):
                    product = self._flatten_sheet_row(row)
                    name = str(product.get("Name") or "").strip()
                    if not name:
                        continue
                    subtitle = str(product.get("Name_subtitle") or "").strip()
                    fridge_days = self._storage_days(product, ("Refrigerate_After_Opening", "Refrigerate", "DOP_Refrigerate", "Refrigerate_After_Thawing"))
                    freezer_days = self._storage_days(product, ("Freeze", "DOP_Freeze"))
                    if fridge_days is None:
                        continue
                    parsed.append({
                        "food": f"{name} — {subtitle}" if subtitle else name,
                        "category": categories.get(product.get("Category_ID"), "USDA FoodKeeper"),
                        "fridge_days": fridge_days,
                        "freezer_months": round((freezer_days or 0) / 30, 1),
                        "priority": "High" if fridge_days <= 7 else "Medium",
                    })
                if parsed:
                    return parsed
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                pass

        # The alternate Kaggle CSV export can be dropped in data/ as foodkeeper.csv.
        candidate = data_dir / "foodkeeper.csv"
        if not candidate.exists():
            return DEFAULT_FOODKEEPER
        try:
            with candidate.open(encoding="utf-8-sig", newline="") as file:
                rows = list(csv.DictReader(file))
            parsed = []
            for row in rows:
                text = {str(k).lower().replace(" ", "_"): v for k, v in row.items()}
                food = text.get("food", text.get("food_name", text.get("name", ""))).strip()
                if food:
                    parsed.append({"food": food, "category": text.get("category", "USDA FoodKeeper"), "fridge_days": self._number(text.get("refrigerator_days", text.get("fridge_days", 4))), "freezer_months": self._number(text.get("freezer_months", 0)), "priority": "High"})
            return parsed or DEFAULT_FOODKEEPER
        except (OSError, csv.Error):
            return DEFAULT_FOODKEEPER

    @staticmethod
    def _flatten_sheet_row(row: Any) -> dict[str, Any]:
        """Convert the JSON/XLSX export's [{column: value}, ...] row to a record."""
        if not isinstance(row, list):
            return row if isinstance(row, dict) else {}
        return {key: value for cell in row if isinstance(cell, dict) for key, value in cell.items()}

    def _storage_days(self, product: dict[str, Any], prefixes: tuple[str, ...]) -> int | None:
        """Normalize FoodKeeper Days, Weeks, and Months values to a conservative day count."""
        multiplier = {"day": 1, "days": 1, "week": 7, "weeks": 7, "month": 30, "months": 30}
        for prefix in prefixes:
            maximum, metric = product.get(f"{prefix}_Max"), str(product.get(f"{prefix}_Metric") or "").lower()
            if maximum is None or metric not in multiplier:
                continue
            try:
                return max(1, round(float(maximum) * multiplier[metric]))
            except (TypeError, ValueError):
                continue
        return None

    @staticmethod
    def _number(value: Any) -> int:
        try:
            return max(0, int(float(value)))
        except (TypeError, ValueError):
            return 4

    def _initial_inventory(self) -> list[dict[str, Any]]:
        weights = [18.2, 11.8, 9.6, 7.4, 6.1, 5.7]
        ages = [3.2, 3.7, 4.8, 4.4, 10.0, 5.6]
        terms = ("rice", "chicken", "milk", "lettuce", "yogurt", "bread")
        chosen = []
        for term in terms:
            found = next((item for item in self._foodkeeper if term in item["food"].lower()), None)
            if found and found not in chosen:
                chosen.append(found)
        chosen.extend(item for item in self._foodkeeper if item not in chosen)
        return [{**item, "kg": weights[index % len(weights)], "age_days": ages[index % len(ages)], "temperature_c": 4.0 + (index % 2) * 0.8} for index, item in enumerate(chosen[:6])]

    def _seed_history(self) -> None:
        for days_ago in range(14, 0, -1):
            date = datetime.now() - timedelta(days=days_ago)
            weekday = date.weekday()
            base = 475 if weekday < 5 else 180
            demand = base + random.randint(-35, 35)
            prepared = demand + random.randint(15, 48)
            self._history.append({"date": date.strftime("%a"), "demand": demand, "prepared": prepared, "waste": max(4, prepared - demand - random.randint(6, 22))})

    def _fallback_weather(self) -> dict[str, Any]:
        hour = datetime.now().hour
        return {"temperature_c": 31 if 10 < hour < 18 else 26, "condition": "Warm / simulated", "rain_probability": 25, "source": "Local simulation"}

    def refresh_weather(self) -> dict[str, Any]:
        try:
            url = "https://api.open-meteo.com/v1/forecast?latitude=12.9716&longitude=77.5946&current=temperature_2m,weather_code&daily=precipitation_probability_max&timezone=auto"
            with urllib.request.urlopen(url, timeout=4) as response:
                payload = json.loads(response.read().decode("utf-8"))
            code = payload["current"]["weather_code"]
            conditions = "Clear" if code <= 1 else "Cloudy" if code <= 3 else "Rainy"
            weather = {"temperature_c": round(payload["current"]["temperature_2m"], 1), "condition": conditions, "rain_probability": payload.get("daily", {}).get("precipitation_probability_max", [0])[0], "source": "Open-Meteo live"}
        except Exception:
            weather = self._fallback_weather()
        with self._lock:
            self._weather, self._last_weather_refresh = weather, datetime.now().strftime("%H:%M:%S")
            self._add_event("CONTEXT", f"Weather context updated: {weather['condition']}, {weather['temperature_c']}°C", "info")
            return self.snapshot()

    def start(self) -> None:
        self.refresh_weather()
        self._thread = threading.Thread(target=self._stream, daemon=True, name="food-telemetry-stream")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def set_stream(self, enabled: bool) -> None:
        with self._lock:
            self._running = enabled

    def _stream(self) -> None:
        while not self._stop.wait(4):
            if self._running:
                self.tick()

    def _add_event(self, agent: str, message: str, level: str) -> None:
        self._events.appendleft({"time": datetime.now().strftime("%H:%M:%S"), "agent": agent, "message": message, "level": level})

    def tick(self) -> dict[str, Any]:
        with self._lock:
            item = random.choice(self._inventory)
            item["age_days"] = round(item["age_days"] + 0.12, 1)
            item["kg"] = round(max(0.4, item["kg"] - random.uniform(0.05, 0.3)), 1)
            if random.random() < 0.16:
                item["temperature_c"] = round(random.uniform(7.2, 9.4), 1)
                self._add_event("SENSOR", f"Cold-chain alert: {item['food']} reached {item['temperature_c']}°C", "warning")
            else:
                self._add_event("SENSOR", f"{item['food']}: {item['kg']} kg scanned; age {item['age_days']} days", "info")
            return self.snapshot()

    def update_temperature(self, item_name: str, temperature_c: float) -> dict[str, Any]:
        with self._lock:
            for item in self._inventory:
                if item["food"].lower() == item_name.lower():
                    item["temperature_c"] = temperature_c
                    self._add_event("SENSOR", f"Manual temperature reading received for {item['food']}: {temperature_c}°C", "warning" if temperature_c > 5 else "info")
                    return self.snapshot()
        raise ValueError("Food item not found")

    def _calendar_context(self) -> dict[str, Any]:
        today = datetime.now()
        weekend = today.weekday() >= 5
        return {"day": today.strftime("%A"), "weekend": weekend, "meal": "Lunch", "event": "Weekend attendance pattern" if weekend else "Normal academic calendar"}

    def _risk(self, item: dict[str, Any]) -> dict[str, Any]:
        shelf = max(1, item["fridge_days"])
        age_ratio = item["age_days"] / shelf
        temp_penalty = max(0, item["temperature_c"] - 5) * 12
        score = min(100, round(age_ratio * 72 + temp_penalty))
        status = "Critical" if score >= 85 else "Use soon" if score >= 55 else "Safe"
        action = "Do not donate; assess disposal/composting under your food-safety policy." if item["temperature_c"] > 8 or score >= 90 else "Prioritize serving; donate only if your local food-safety policy confirms eligibility." if score >= 55 else "Keep refrigerated and rotate FIFO."
        return {**item, "risk_score": score, "status": status, "action": action}

    def _prediction(self, calendar: dict[str, Any]) -> dict[str, Any]:
        matching = [r["demand"] for r in self._history if (r["date"] in ("Sat", "Sun")) == calendar["weekend"]]
        baseline = sum(matching) / len(matching) if matching else 420
        weather_adjustment = -18 if self._weather["rain_probability"] > 55 else 8 if self._weather["temperature_c"] > 32 else 0
        predicted = round(baseline + weather_adjustment)
        buffer = max(12, round(predicted * 0.04))
        return {"demand": predicted, "recommended_prepare": predicted + buffer, "confidence": 82, "reason": f"{calendar['day']} history + {self._weather['condition'].lower()} weather adjustment"}

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            calendar = self._calendar_context()
            inventory = sorted((self._risk(i) for i in self._inventory), key=lambda x: x["risk_score"], reverse=True)
            prediction = self._prediction(calendar)
            at_risk_kg = round(sum(i["kg"] for i in inventory if i["risk_score"] >= 55), 1)
            recent_waste = sum(r["waste"] for r in list(self._history)[-7:])
            agent_actions = [
                {"agent": "Demand Forecaster", "finding": f"Forecasts {prediction['demand']} lunch portions.", "action": f"Prepare {prediction['recommended_prepare']} portions."},
                {"agent": "Food Safety Guardian", "finding": f"{inventory[0]['food']} is highest risk ({inventory[0]['risk_score']}/100).", "action": inventory[0]["action"]},
                {"agent": "Recovery Planner", "finding": f"{at_risk_kg} kg requires action today.", "action": "Use eligible food first; route ineligible material to composting."},
            ]
            return {"streaming": self._running, "generated_at": datetime.now(timezone.utc).isoformat(), "weather": self._weather, "weather_refreshed": self._last_weather_refresh, "calendar": calendar, "prediction": prediction, "inventory": inventory, "events": list(self._events), "agents": agent_actions, "metrics": {"inventory_kg": round(sum(i["kg"] for i in inventory), 1), "at_risk_kg": at_risk_kg, "weekly_waste_kg": recent_waste, "waste_reduction_pct": 18}, "data_source": self._dataset_label}
