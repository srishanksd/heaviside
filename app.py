import os
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from pipeline import Pipeline


app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
if not app.secret_key:
    if os.environ.get("FLASK_ENV") == "production":
        raise RuntimeError("FLASK_SECRET_KEY must be configured in production.")
    app.secret_key = "development-only-secret-change-me"
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production",
    MAX_CONTENT_LENGTH=16 * 1024,
)
pipeline = Pipeline()  # checkpoint, scalers and source data are loaded once


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/healthz")
def healthz():
    """Deployment health check; startup has already loaded the model and data."""
    return jsonify({"status": "ok", "stations": int(len(pipeline.predictor.stations))})


@app.route("/analyze", methods=["POST"])
def analyze():
    place = request.form.get("location", "").strip()
    if not place:
        return render_template("index.html", error="Please enter a location."), 400
    try:
        session["result"] = pipeline.analyze(place)
        return redirect(url_for("dashboard"))
    except Exception as error:
        app.logger.exception("Analysis failed for %r", place)
        return render_template("index.html", error=str(error)), 422


@app.route("/analyze-coords")
def analyze_coords():
    """Coordinate-based analysis entry point used by the interactive map."""
    lat = request.args.get("lat", type=float)
    lng = request.args.get("lng", type=float)
    name = request.args.get("name", "")
    if lat is None or lng is None or not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return render_template("index.html", error="Invalid map coordinates."), 400
    try:
        session["result"] = pipeline.analyze_coordinates(lat, lng, name or None)
        return redirect(url_for("dashboard"))
    except Exception as error:
        app.logger.exception("Analysis failed for coordinates %s, %s", lat, lng)
        return render_template("index.html", error=str(error)), 422


@app.route("/api/stations")
def api_stations():
    """Return all monitoring stations with status for map overlay."""
    return jsonify(pipeline.get_station_overview())


@app.route("/api/geocode")
def api_geocode():
    """Same-origin geocoding for the map; avoids browser CORS failures."""
    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return jsonify({"results": []}), 400
    try:
        return jsonify({"results": pipeline.map_agent.results(query)})
    except ValueError as error:
        return jsonify({"error": str(error), "results": []}), 503


@app.route("/dashboard")
def dashboard():
    result = session.get("result")
    # Results are intentionally short-lived when the dashboard schema changes.
    # This avoids rendering an old session with incomplete/newly renamed fields.
    if result is None or result.get("forecast_version") != 4:
        return redirect(url_for("home"))
    return render_template("dashboard.html", result=result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG") == "1")
