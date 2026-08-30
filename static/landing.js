/* ============================================================
   HEAVISIDE — Landing Page JavaScript
   MapLibre GL JS + OpenFreeMap 3D interactive map
============================================================ */
(function () {
    "use strict";

    /* Shared visual preferences and a lightweight analysis transition. */
    var savedTheme = localStorage.getItem("heaviside-theme");
    if (savedTheme === "dark") document.body.classList.add("dark-theme");
    var themeToggle = document.getElementById("themeToggle");
    function syncThemeButton() {
        if (!themeToggle) return;
        var dark = document.body.classList.contains("dark-theme");
        themeToggle.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
        themeToggle.querySelector("span").textContent = dark ? "☀" : "☾";
    }
    syncThemeButton();
    if (themeToggle) themeToggle.addEventListener("click", function () {
        document.body.classList.toggle("dark-theme");
        localStorage.setItem("heaviside-theme", document.body.classList.contains("dark-theme") ? "dark" : "light");
        syncThemeButton();
    });
    var pageLoader = document.getElementById("pageLoader");
    window.addEventListener("load", function () { setTimeout(function () { if (pageLoader) pageLoader.classList.add("is-hidden"); }, 700); });
    document.addEventListener("click", function (event) {
        var link = event.target.closest("a[href*='analyze']");
        if (link && pageLoader) pageLoader.classList.remove("is-hidden");
    });

    /* ============================================================
       NAVBAR
    ============================================================ */
    var navbar = document.getElementById("navbar");
    window.addEventListener("scroll", function () {
        if (navbar) navbar.classList.toggle("scrolled", window.scrollY > 30);
    }, { passive: true });

    var hamburger = document.getElementById("navHamburger");
    var navLinks = document.getElementById("navLinks");
    if (hamburger && navLinks) {
        hamburger.addEventListener("click", function () {
            navLinks.classList.toggle("nav-open");
            hamburger.classList.toggle("active");
        });
        navLinks.querySelectorAll(".nav-link").forEach(function (l) {
            l.addEventListener("click", function () {
                navLinks.classList.remove("nav-open");
                hamburger.classList.remove("active");
            });
        });
    }

    /* ============================================================
       SMOOTH SCROLL
    ============================================================ */
    document.querySelectorAll('a[href^="#"]').forEach(function (a) {
        a.addEventListener("click", function (e) {
            var id = this.getAttribute("href");
            if (id === "#") return;
            var el = document.querySelector(id);
            if (!el) return;
            e.preventDefault();
            var top = el.getBoundingClientRect().top + window.scrollY - (navbar ? navbar.offsetHeight : 0) - 20;
            window.scrollTo({ top: top, behavior: "smooth" });
        });
    });

    /* ============================================================
       SCROLL REVEAL
    ============================================================ */
    var reveals = document.querySelectorAll(".reveal");
    if ("IntersectionObserver" in window) {
        var revealObs = new IntersectionObserver(function (entries) {
            entries.forEach(function (e) {
                if (e.isIntersecting) { e.target.classList.add("revealed"); revealObs.unobserve(e.target); }
            });
        }, { threshold: 0.1, rootMargin: "0px 0px -30px 0px" });
        reveals.forEach(function (el) { revealObs.observe(el); });
    } else {
        reveals.forEach(function (el) { el.classList.add("revealed"); });
    }

    /* ============================================================
       COUNTER ANIMATION
    ============================================================ */
    var counters = document.querySelectorAll("[data-count]");
    function animateCount(el) {
        var target = parseInt(el.getAttribute("data-count"), 10);
        if (isNaN(target)) return;
        var start = performance.now();
        function tick(now) {
            var p = Math.min((now - start) / 1500, 1);
            var eased = 1 - Math.pow(1 - p, 3);
            el.textContent = Math.round(eased * target);
            if (p < 1) requestAnimationFrame(tick); else el.textContent = target;
        }
        requestAnimationFrame(tick);
    }
    if ("IntersectionObserver" in window && counters.length) {
        var cObs = new IntersectionObserver(function (entries) {
            entries.forEach(function (e) {
                if (e.isIntersecting) { animateCount(e.target); cObs.unobserve(e.target); }
            });
        }, { threshold: 0.5 });
        counters.forEach(function (el) { cObs.observe(el); });
    }

    /* ============================================================
       FORM HANDLER (Explore section)
    ============================================================ */
    var locForm = document.getElementById("locationForm");
    if (locForm) {
        locForm.addEventListener("submit", function (e) {
            var inp = document.getElementById("location");
            var btn = document.getElementById("analyzeButton");
            if (!inp || !inp.value.trim()) { e.preventDefault(); return; }
            if (btn) { btn.disabled = true; btn.innerHTML = '<span class="btn-spinner"></span> Analyzing...'; }
        });
    }

    /* ============================================================
       MAPLIBRE GL JS — 3D MAP
    ============================================================ */
    if (typeof maplibregl === "undefined") {
        console.warn("MapLibre GL JS not loaded");
        return;
    }

    // Karnataka center
    var map = new maplibregl.Map({
        container: "map",
        style: "https://tiles.openfreemap.org/styles/liberty",
        center: [76.5, 14.0],
        zoom: 6.5,
        pitch: 35,
        bearing: -5,
        antialias: true,
        attributionControl: false
    });

    // Controls
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
    map.addControl(new maplibregl.FullscreenControl(), "top-right");
    map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");

    // Status colors
    var STATUS_COLORS = {
        normal: "#16a34a",
        watch: "#eab308",
        alert: "#f97316",
        critical: "#dc2626"
    };

    var selectedStation = null;
    var stationsData = [];

    /* ============================================================
       LOAD STATIONS + 3D BUILDINGS
    ============================================================ */
    map.on("load", function () {
        // Add 3D building extrusions if the style has a building layer
        var layers = map.getStyle().layers;
        for (var i = 0; i < layers.length; i++) {
            if (layers[i].id.indexOf("building") !== -1 && layers[i].type === "fill") {
                map.addLayer({
                    id: "3d-buildings",
                    source: layers[i].source,
                    "source-layer": layers[i]["source-layer"],
                    type: "fill-extrusion",
                    minzoom: 14,
                    paint: {
                        "fill-extrusion-color": "#dde4ec",
                        "fill-extrusion-height": ["get", "render_height"],
                        "fill-extrusion-base": ["get", "render_min_height"],
                        "fill-extrusion-opacity": 0.7
                    }
                });
                break;
            }
        }
        fetch("/api/stations")
            .then(function (r) { return r.json(); })
            .then(function (stations) {
                stationsData = stations;
                addStationsToMap(stations);
                updateStats(stations);
            })
            .catch(function (err) {
                console.error("Failed to load stations:", err);
            });
    });

    function addStationsToMap(stations) {
        // Build GeoJSON
        var features = stations.map(function (s) {
            return {
                type: "Feature",
                geometry: { type: "Point", coordinates: [s.longitude, s.latitude] },
                properties: {
                    code: s.code,
                    place_name: s.place_name,
                    district: s.district,
                    block: s.block,
                    gp_name: s.gp_name,
                    status: s.status,
                    level: s.level,
                    change: s.change,
                    anomaly_score: s.anomaly_score,
                    latest_month: s.latest_month,
                    rainfall: s.rainfall,
                    temperature: s.temperature,
                    color: STATUS_COLORS[s.status] || STATUS_COLORS.normal
                }
            };
        });

        var geojson = { type: "FeatureCollection", features: features };

        // Add source
        map.addSource("stations", { type: "geojson", data: geojson });

        // Outer pulse ring for alert/critical
        map.addLayer({
            id: "stations-pulse",
            type: "circle",
            source: "stations",
            filter: ["in", ["get", "status"], ["literal", ["alert", "critical"]]],
            paint: {
                "circle-radius": [
                    "interpolate", ["linear"], ["zoom"],
                    5, 12, 10, 20, 15, 28
                ],
                "circle-color": ["get", "color"],
                "circle-opacity": 0.16,
                "circle-stroke-width": 0
            }
        });

        // Main station circles
        map.addLayer({
            id: "stations-circles",
            type: "circle",
            source: "stations",
            paint: {
                "circle-radius": [
                    "interpolate", ["linear"], ["zoom"],
                    5, 5, 10, 8, 15, 12
                ],
                "circle-color": ["get", "color"],
                "circle-stroke-color": "#ffffff",
                "circle-stroke-width": 2.5,
                "circle-opacity": 0.95
            }
        });

        // Click handler
        map.on("click", "stations-circles", function (e) {
            if (!e.features || !e.features.length) return;
            var f = e.features[0];
            selectStation(f.properties, f.geometry.coordinates);
        });

        // Cursor
        map.on("mouseenter", "stations-circles", function () { map.getCanvas().style.cursor = "pointer"; });
        map.on("mouseleave", "stations-circles", function () { map.getCanvas().style.cursor = ""; });

        // Click elsewhere to deselect
        map.on("click", function (e) {
            var features = map.queryRenderedFeatures(e.point, { layers: ["stations-circles"] });
            if (!features.length) {
                deselectStation();
            }
        });
    }

    /* ============================================================
       STATION SELECTION / POPUP
    ============================================================ */
    var popup = document.getElementById("zonePopup");
    var popupClose = document.getElementById("zonePopupClose");

    function selectStation(props, coords) {
        selectedStation = props;

        // Fly to station
        map.flyTo({
            center: coords,
            zoom: Math.max(map.getZoom(), 10),
            pitch: 50,
            duration: 1500,
            essential: true
        });

        // Fill popup
        var statusEl = document.getElementById("zoneStatus");
        var dot = statusEl.querySelector(".zone-status-dot");
        var text = statusEl.querySelector(".zone-status-text");
        dot.style.background = STATUS_COLORS[props.status] || STATUS_COLORS.normal;
        text.textContent = props.status.toUpperCase() + " ZONE";
        statusEl.className = "zone-popup-status zone-status-" + props.status;

        document.getElementById("zoneTitle").textContent = props.place_name || props.district || "Monitoring location";
        document.getElementById("zoneCoords").textContent = [props.gp_name, props.block, props.district].filter(function (value) {
            return value && value !== "-" && value !== "nan";
        }).join(" · ") || (coords[1].toFixed(4) + "° N, " + coords[0].toFixed(4) + "° E");

        document.getElementById("zoneLevel").textContent = props.level + " m";
        var changeEl = document.getElementById("zoneLevelChange");
        var ch = parseFloat(props.change);
        changeEl.textContent = (ch >= 0 ? "▲ " : "▼ ") + Math.abs(ch).toFixed(2) + " m";
        changeEl.className = "zone-metric-change " + (ch >= 0 ? "positive" : "negative");

        var temperatureEl = document.getElementById("zoneTemp");
        if (temperatureEl) temperatureEl.textContent = props.temperature == null ? "Unavailable" : props.temperature + " °C";
        document.getElementById("zoneRain").textContent = props.latest_month || "Unavailable";
        document.getElementById("zoneAnomaly").textContent = props.anomaly_score;

        // CTA link
        var cta = document.getElementById("zoneCta");
        cta.href = "/analyze-coords?lat=" + encodeURIComponent(coords[1]) + "&lng=" + encodeURIComponent(coords[0]) +
            "&name=" + encodeURIComponent(props.place_name || props.district || "Monitoring location");

        popup.style.display = "flex";
        popup.classList.add("popup-visible");
    }

    function deselectStation() {
        selectedStation = null;
        popup.style.display = "none";
        popup.classList.remove("popup-visible");
    }

    if (popupClose) {
        popupClose.addEventListener("click", function (e) {
            e.stopPropagation();
            deselectStation();
        });
    }

    /* ============================================================
       SEARCH (Map hero search)
    ============================================================ */
    var searchInput = document.getElementById("mapSearchInput");
    var searchBtn = document.getElementById("mapSearchBtn");
    var searchResult = document.getElementById("searchResult");
    var resultName = document.getElementById("resultName");
    var resultCoords = document.getElementById("resultCoords");
    var pendingLocation = null;

    function searchLocation(query) {
        if (!query.trim()) return;

        searchBtn.disabled = true;
        searchBtn.innerHTML = '<span class="btn-spinner"></span>';

        // Geocoding runs through Flask so production browsers never have to
        // call a third-party service directly (which is blocked by CORS).
        var url = "/api/geocode?q=" + encodeURIComponent(query);

        fetch(url)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                searchBtn.disabled = false;
                searchBtn.innerHTML = 'Analyze <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 7H11M11 7L7.5 3.5M11 7L7.5 10.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';

                if (!data || !data.results || !data.results.length) {
                    searchResult.style.display = "flex";
                    resultName.textContent = data && data.error ? "Search unavailable" : "Location not found";
                    resultCoords.textContent = data && data.error ? data.error : "Try a more specific village, town, city, or district";
                    return;
                }

                var loc = data.results[0];
                var lat = Number(loc.latitude);
                var lng = Number(loc.longitude);
                pendingLocation = { latitude: lat, longitude: lng, name: loc.name };

                resultName.textContent = loc.name;
                resultCoords.textContent = lat.toFixed(4) + "° N, " + lng.toFixed(4) + "° E";
                searchResult.style.display = "flex";
                searchBtn.textContent = "View analysis";

                // Fly to location
                map.flyTo({
                    center: [lng, lat],
                    zoom: 10,
                    pitch: 50,
                    bearing: 0,
                    duration: 800,
                    essential: true
                });

                // One search is one action: the backend finds the nearest
                // valid coordinate from the complete raw Karnataka CSV.
                window.setTimeout(function () {
                    window.location.assign("/analyze-coords?lat=" + encodeURIComponent(lat) +
                        "&lng=" + encodeURIComponent(lng) + "&name=" + encodeURIComponent(loc.name));
                }, 2000);
            })
            .catch(function (err) {
                console.error("Search failed:", err);
                searchBtn.disabled = false;
                searchBtn.innerHTML = 'Analyze <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 7H11M11 7L7.5 3.5M11 7L7.5 10.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
                searchResult.style.display = "flex";
                resultName.textContent = "Search unavailable";
                resultCoords.textContent = "Please retry in a moment or use a monitoring station on the map.";
            });
    }

    function findNearestStation(lat, lng, maxKm) {
        var best = null;
        var bestDist = Infinity;
        stationsData.forEach(function (s) {
            var earthRadiusKm = 6371;
            var dlat = (s.latitude - lat) * Math.PI / 180;
            var dlng = (s.longitude - lng) * Math.PI / 180;
            var a = Math.sin(dlat / 2) * Math.sin(dlat / 2) +
                Math.cos(lat * Math.PI / 180) * Math.cos(s.latitude * Math.PI / 180) *
                Math.sin(dlng / 2) * Math.sin(dlng / 2);
            var dist = earthRadiusKm * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
            if (dist < bestDist) {
                bestDist = dist;
                best = s;
            }
        });
        // Avoid implying that a far-away station represents the searched place.
        if (!best) return null;
        if (maxKm && bestDist > maxKm) return null;
        return {
            properties: {
                code: best.code,
                status: best.status,
                level: best.level,
                change: best.change,
                anomaly_score: best.anomaly_score,
                latest_month: best.latest_month,
                rainfall: best.rainfall,
                temperature: best.temperature,
                color: STATUS_COLORS[best.status]
            },
            coordinates: [best.longitude, best.latitude]
        };
    }

    /* Show popup without flying to station (used after search) */
    function showStationPopup(props, coords) {
        selectedStation = props;

        var statusEl = document.getElementById("zoneStatus");
        var dot = statusEl.querySelector(".zone-status-dot");
        var text = statusEl.querySelector(".zone-status-text");
        dot.style.background = STATUS_COLORS[props.status] || STATUS_COLORS.normal;
        text.textContent = props.status.toUpperCase() + " ZONE";
        statusEl.className = "zone-popup-status zone-status-" + props.status;

        document.getElementById("zoneTitle").textContent = props.place_name || props.district || "Monitoring location";
        document.getElementById("zoneCoords").textContent = [props.gp_name, props.block, props.district].filter(function (value) {
            return value && value !== "-" && value !== "nan";
        }).join(" · ") || (coords[1].toFixed(4) + "° N, " + coords[0].toFixed(4) + "° E");

        document.getElementById("zoneLevel").textContent = props.level + " m";
        var changeEl = document.getElementById("zoneLevelChange");
        var ch = parseFloat(props.change);
        changeEl.textContent = (ch >= 0 ? "▲ " : "▼ ") + Math.abs(ch).toFixed(2) + " m";
        changeEl.className = "zone-metric-change " + (ch >= 0 ? "positive" : "negative");

        var temperatureEl = document.getElementById("zoneTemp");
        if (temperatureEl) temperatureEl.textContent = props.temperature == null ? "Unavailable" : props.temperature + " °C";
        document.getElementById("zoneRain").textContent = props.latest_month || "Unavailable";
        document.getElementById("zoneAnomaly").textContent = props.anomaly_score;

        var cta = document.getElementById("zoneCta");
        cta.href = "/analyze-coords?lat=" + encodeURIComponent(coords[1]) + "&lng=" + encodeURIComponent(coords[0]) +
            "&name=" + encodeURIComponent(props.place_name || props.district || "Monitoring location");

        popup.style.display = "flex";
        popup.classList.add("popup-visible");
    }

    if (searchBtn) {
        searchBtn.addEventListener("click", function () {
            if (pendingLocation) {
                window.location.assign("/analyze-coords?lat=" + encodeURIComponent(pendingLocation.latitude) +
                    "&lng=" + encodeURIComponent(pendingLocation.longitude) +
                    "&name=" + encodeURIComponent(pendingLocation.name));
                return;
            }
            searchLocation(searchInput.value);
        });
    }
    if (searchInput) {
        searchInput.addEventListener("input", function () {
            pendingLocation = null;
            if (searchBtn) searchBtn.textContent = "Analyze";
        });
        searchInput.addEventListener("keydown", function (e) {
            if (e.key === "Enter") {
                e.preventDefault();
                pendingLocation = null;
                searchLocation(searchInput.value);
            }
        });
    }

    /* ============================================================
       UPDATE STATS from real data
    ============================================================ */
    function updateStats(stations) {
        var total = stations.length;
        var anomalies = stations.filter(function (s) {
            return s.status === "alert" || s.status === "critical";
        }).length;

        var stEl = document.getElementById("statStations");
        var anEl = document.getElementById("statAnomalies");
        if (stEl) { stEl.setAttribute("data-count", total); stEl.textContent = total; }
        if (anEl) { anEl.setAttribute("data-count", anomalies); anEl.textContent = anomalies; }
    }

})();
