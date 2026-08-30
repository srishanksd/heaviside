const pageLoader = document.getElementById("pageLoader");
const themeToggle = document.getElementById("themeToggle");

function syncTheme() {
    const dark = document.body.classList.contains("dark-theme");
    if (themeToggle) {
        themeToggle.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
        themeToggle.querySelector("span").textContent = dark ? "☀" : "☾";
    }
    const chartElement = document.getElementById("groundwater-chart");
    if (typeof Plotly !== "undefined" && chartElement && chartElement.data && chartElement.data.length) {
        Plotly.relayout("groundwater-chart", {
            font: { color: dark ? "#d7edf2" : "#082f49" },
            "xaxis.gridcolor": dark ? "#264552" : "#edf2f5",
            "yaxis.gridcolor": dark ? "#264552" : "#edf2f5"
        });
    }
}

if (localStorage.getItem("heaviside-theme") === "dark") document.body.classList.add("dark-theme");
syncTheme();
if (themeToggle) themeToggle.addEventListener("click", function () {
    document.body.classList.toggle("dark-theme");
    localStorage.setItem("heaviside-theme", document.body.classList.contains("dark-theme") ? "dark" : "light");
    syncTheme();
});
window.addEventListener("load", function () { setTimeout(function () { if (pageLoader) pageLoader.classList.add("is-hidden"); }, 2300); });

const chart =
    document.getElementById(
        "groundwater-chart"
    );


if (!chart) {

    console.error(
        "Groundwater chart element not found."
    );

} else {


    // ========================================================
    // READ DATA FROM HTML
    // ========================================================

    const dates = JSON.parse(
        chart.dataset.dates
    );


    const values = JSON.parse(
        chart.dataset.values
    );


    const forecastDates = JSON.parse(
        chart.dataset.forecastDates
    );


    const forecastValues = JSON.parse(
        chart.dataset.forecastValues
    );

    const forecastLabel = chart.dataset.forecastLabel;


    // ========================================================
    // HISTORICAL TRACE
    // ========================================================

    const historicalTrace = {

        x: dates,

        y: values,

        type: "scatter",

        mode: "lines+markers",

        name: "Historical",

        line: {
            width: 4
        },

        marker: {
            size: 8
        }

    };


    // ========================================================
    // FORECAST TRACE
    // ========================================================

    const forecastTrace = {

        x: [

            dates[
                dates.length - 1
            ],

            ...forecastDates

        ],

        y: [

            values[
                values.length - 1
            ],

            ...forecastValues

        ],

        type: "scatter",

        mode: "lines+markers",

        name: forecastLabel,

        line: {

            width: 4,

            dash: "dash"

        },

        marker: {

            size: 11

        }

    };


    // ========================================================
    // LAYOUT
    // ========================================================

    const layout = {

        height: 480,

        margin: {

            l: 60,

            r: 25,

            t: 25,

            b: 55

        },

        paper_bgcolor:
            "rgba(0,0,0,0)",

        plot_bgcolor:
            "rgba(0,0,0,0)",

        hovermode:
            "x unified",

        xaxis: {

            title: "Month",

            gridcolor:
                "#edf2f5",

            zeroline: false

        },

        yaxis: {

            title:
                "Groundwater Level (m)",

            gridcolor:
                "#edf2f5",

            zeroline: false

        },

        legend: {

            orientation: "h",

            y: 1.08

        }

    };


    // ========================================================
    // CREATE CHART
    // ========================================================

    Plotly.newPlot(

        chart,

        [
            historicalTrace,
            forecastTrace
        ],

        layout,

        {

            responsive: true,

            displaylogo: false,

            modeBarButtonsToRemove: [

                "lasso2d",

                "select2d"

            ]

        }

    );


    // ========================================================
    // ENTRANCE ANIMATION
    // ========================================================

    Plotly.animate(

        chart,

        {

            data: [

                {

                    x: dates,

                    y: values

                }

            ]

        },

        {

            transition: {

                duration: 900

            },

            frame: {

                duration: 900,

                redraw: false

            }
        }
    );

    // Apply the selected theme after Plotly has created the graph.
    syncTheme();

}
