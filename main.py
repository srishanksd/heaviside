from pipeline import Pipeline


def main():
    place = input("Enter place: ").strip()
    if not place:
        raise ValueError("Place cannot be empty.")
    result = Pipeline().analyze(place)
    station = result["station"]
    print("\nGROUNDWATER INTELLIGENCE")
    print(f"Location: {result['location']['name']}")
    print(f"Station: {station['code']} ({station['distance_km']:.2f} km)")
    print(f"Current groundwater: {result['current_groundwater']:.2f} m")
    print(f"Predicted next month: {result['prediction']:.2f} m")
    print(f"Expected change: {result['change']:+.2f} m ({result['prediction_status']})")
    print("Raw CSV rows used:")
    for row in result["data_provenance"]["raw_csv_rows"]:
        print(f"  {row['monitoring_date']} | {row['groundwater_level']:.2f} m | CSV row {row['csv_row_index']}")


if __name__ == "__main__":
    main()
