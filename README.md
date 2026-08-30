# HEAVISIDE

Groundwater intelligence for Karnataka. Search a location on the map to inspect
the nearest monitoring station, its recent groundwater history, and a short
monthly forecast.

## What is included

- Interactive MapLibre station map and place search.
- Light/dark theme switch and loading transition on the map and dashboard.
- Phone and tablet layouts for the search panel, dashboard cards, charts, and
  monitoring table.
- Three-month recursive outlook. Only the first month is the primary model
  forecast; later months are a damped continuation and are labelled as forecast,
  not observation.
- Exact terrain elevation for the searched or map-selected coordinate, with a
  station-matched fallback only if the elevation service is unavailable.

## Data

The project loads both tracked Karnataka monthly groundwater files:

- `karnataka_man_gw_wl_monthly_data_2021_2025.csv`
- `karnataka_man_gw_wl_monthly_data_2026_2030.csv`

The second file is the rolling **Ground Water Level Manual Monthly Karnataka
2026–2030** resource published by the Government of India’s National Water Data
Portal (NWIC). It contains observations available through its publication date;
the `2030` filename does not mean future observations are present. The app uses
the latest available station history to forecast following months.

Source: [National Water Data Portal resource](https://nwdp.nwic.gov.in/dataset/1cbc78e5-42e2-4140-a584-ec752c994955/resource/4e393536-9a75-4ae8-a246-64a2530e16a9).

## Run locally

```powershell
uv sync
uv run flask --app app run --debug
```

Open `http://127.0.0.1:5000`.

## Project layout

```text
app.py                    Flask routes
pipeline.py               location and station orchestration
prediction_service.py     data loading, station matching, forecasts
agents/map_agent.py       map geocoding helper
templates/                map landing page and analysis dashboard
static/                   page styles and browser behaviour
weights/                  trained model artefacts
*.csv                     tracked groundwater and environmental data
```

## Model notes

### What the model predicts

The platform predicts the **groundwater level for the next month** at the
nearest monitoring station with a complete twelve-month history. Values are
reported in metres, consistent with the official station CSV. The dashboard’s
three-month panel is deliberately conservative: its first entry is the primary
one-month forecast, while the second and third entries recursively extend that
forecast using a damped recent trend. They are decision-support estimates, not
future observations.

### Inputs and station matching

For every selected location, HEAVISIDE finds the closest Karnataka monitoring
station using latitude/longitude distance. It requires the station’s latest
twelve readings to be consecutive months; this avoids predicting across missing
data. The station-aware model uses the last 1, 2, 3 and 12 months of groundwater
levels, recent changes, and the calendar month encoded as sine/cosine features.
The calendar encoding lets the model represent recurring seasonal behaviour
without treating December and January as far apart.

The prepared environmental data also contains temperature, rainfall, soil and
terrain fields for the dashboard and optional LSTM comparison. Exact terrain
elevation displayed on the dashboard is resolved for the selected coordinate;
the station-matched record is used only if that lookup is unavailable.

### How the primary forecast works

`train_station_forecaster.py` fits a regularised station-aware regression model.
Each station has its own indicator feature, allowing the forecast to retain both
statewide seasonality and local well behaviour. The model output is blended with
the latest observed value rather than used unmodified. This reduces unrealistic
month-to-month jumps and makes the result more robust when a single recent
reading is unusual.

If a selected station is not represented by the trained feature dataset—such as
when it has newer official 2026 readings—the application uses the raw station
history and a damped directional baseline. This fallback is clearly named in
the dashboard, so it is never presented as a trained-model result.

### Validation and responsible use

The model is evaluated chronologically: earlier observations are used for
training and the 2025 observations are held out for testing. This mirrors real
deployment, where a model must forecast months it has not already seen.
`station_forecaster_validation.json` stores the validation metrics and
`validation_report.json` / `rf_validation_report.json` store supporting model
reports. `validate_model.py` can be run before replacing any model weights.

The anomaly score compares the latest monthly change with that station’s usual
change using a median-absolute-deviation scale. The red/orange/green prediction
status is a screening aid based on the forecasted change; it is not a water
quality, safety, or regulatory classification. Results should be verified with
field measurements before operational decisions such as pumping restrictions or
crop changes.

### Evidence to show judges

Use the following evidence trail in a demonstration:

1. Show the selected station, its coordinates and distance on the dashboard.
   This establishes exactly which monitoring record represents the searched
   location.
2. Show the twelve historical points in the chart and the matching raw-row list
   returned in `data_provenance.raw_csv_rows`. These are source observations,
   not model-generated values.
3. Cite the Government of India [National Water Data Portal Karnataka monthly
   dataset](https://nwdp.nwic.gov.in/dataset/1cbc78e5-42e2-4140-a584-ec752c994955/resource/4e393536-9a75-4ae8-a246-64a2530e16a9)
   and the [CGWB groundwater-level monitoring explanation](https://cgwb.gov.in/en/ground-water-level-monitoring).
   These establish the data producer and how groundwater levels are monitored.
4. Explain that the forecast is one month ahead and that the model was tested
   using a chronological 2025 holdout. Open `station_forecaster_validation.json`
   to state the reported held-out error, rather than claiming that any one
   future value is guaranteed correct.
5. State the limitation plainly: forecasts are decision support, and the latest
   official station reading or a field measurement is the proof for an observed
   groundwater level. Zero readings that contradict adjacent normal readings
   are excluded as source-quality faults, not converted into forecasts.

## Team

| Member | USN |
| --- | --- |
| Abhilash | 251EE241 |
| Srishank | 251AI040 |
| Laxman | 251CS233 |
| Vedanth | 251EC168 |
| Monith | 251EE137 |
| Vandana | 251CS165 |
