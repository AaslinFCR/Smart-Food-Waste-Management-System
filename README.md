# WasteWise AI — Real-Time Food Waste Management

An executable-ready, local-first dashboard for a canteen or food-service operation. It combines an IoT-style simulated stream, a USDA FoodKeeper-compatible inventory dataset, calendar context, optional live weather, food-risk scoring, demand forecasting, and explainable multi-agent recommendations.

## Run the dashboard

Double-click [Launch WasteWise AI.vbs](<C:/Users/Aaslin/OneDrive/Documents/New project/Launch WasteWise AI.vbs>) or run:

```powershell
.\run.ps1
```

It opens at [http://127.0.0.1:8000](http://127.0.0.1:8000). The data stream emits a sensor event every four seconds; pause/resume it in the dashboard or refresh the weather context.

## Build the Windows executable

Run this once on Windows with an internet connection to install PyInstaller and make the bundle:

```powershell
.\build_exe.ps1
```

The generated app is `dist-real-dataset\WasteWiseAI\WasteWiseAI.exe`. Copy the whole `dist-real-dataset\WasteWiseAI` folder when sharing it, because the executable needs its bundled data and frontend assets alongside it.

## Dataset and external context

- `data/foodkeeper.json` is the supplied real USDA FoodKeeper v128 dataset, containing 661 product records and category metadata. It is used automatically by the application.
- The loader also supports a simplified `data/foodkeeper.csv` export as a fallback.
- The service requests current weather from Open-Meteo for Bengaluru. When it cannot reach the service, it transparently uses a labelled local simulation so the demo stays operational.
- Calendar context uses local day-of-week and switches demand history for weekends.

## Agent workflow

1. **Sensor agent** ingests simulated weight, age, and cold-chain readings.
2. **Demand forecaster** predicts meal demand using day pattern and weather adjustment.
3. **Food Safety Guardian** scores perishable-food risk from storage age and temperature.
4. **Recovery Planner** prioritizes safe use and routes unsuitable material to composting.

The suggestions are decision support only. Donation/reuse must be approved using the operator’s applicable food-safety policy and local regulations.

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Docker

With Docker Desktop running, launch the complete local service with:

```powershell
docker compose up --build
```

Open [http://localhost:8000](http://localhost:8000). Stop it with `docker compose down`.

## CI/CD

The GitHub Actions workflow in `.github/workflows/ci-cd.yml` runs automated tests and verifies the Docker build on every pull request and push. A push to `main` also publishes the container image to GitHub Container Registry as `ghcr.io/<your-account>/smart-food-waste-management-system:latest`.
