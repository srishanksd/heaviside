import numpy as np
import pandas as pd


FEATURE_COLUMNS = [
    "Latitude",
    "Longitude",
    "groundwater_level",
    "temperature_c",
    "rainfall_mm",
    "soil_ph",
    "clay_percent",
    "sand_percent",
    "silt_percent",
    "organic_carbon",
    "nitrogen",
    "elevation_m"
]


def create_sequences(
    df,
    sequence_length=12,
    target_start_date=None
):
    """
    Creates sequences for LSTM.

    Input:
        Previous `sequence_length` months

    Target:
        Next month's groundwater level
    """

    X = []
    y = []

    for station_id, group in df.groupby("Station Code"):

        group = (
            group
            .sort_values("Month")
            .reset_index(drop=True)
        )

        dates = group["Month"].values

        features = group[
            FEATURE_COLUMNS
        ].values

        targets = group[
            "groundwater_level"
        ].values

        for i in range(
            sequence_length,
            len(group)
        ):

            target_date = dates[i]

            # Validation/test can specify
            # from which date targets should start
            if target_start_date is not None:

                if target_date < target_start_date:
                    continue

            # Check that previous months are consecutive
            previous_dates = pd.DatetimeIndex(
                dates[
                    i - sequence_length:i
                ]
            )

            expected_dates = pd.date_range(
                end=target_date
                - pd.offsets.MonthBegin(1),
                periods=sequence_length,
                freq="MS"
            )

            if not previous_dates.equals(
                expected_dates
            ):
                continue

            X.append(
                features[
                    i - sequence_length:i
                ]
            )

            y.append(
                targets[i]
            )

    return (
        np.asarray(
            X,
            dtype=np.float32
        ),
        np.asarray(
            y,
            dtype=np.float32
        )
    )