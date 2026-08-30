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


    const forecastDate =
        chart.dataset.forecastDate;


    const forecastValue =
        Number(
            chart.dataset.forecastValue
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

            forecastDate

        ],

        y: [

            values[
                values.length - 1
            ],

            forecastValue

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

}
