import requests 
import pandas as pd

def weatherApi(latitude,longitude,start_date,end_date):
    url = "https://archive-api.open-meteo.com/v1/archive"
    
    params = params = {
        "latitude":latitude,
        "longitude":longitude,
        "start_date":start_date,
        "end_date":end_date,
        "hourly": [
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation",
        "rain"],
        "timezone": "Asia/Kolkata"      
    }
    
    response = requests.get(url,params=params)
    
    response.raise_for_status() #Check for the status of url
    
    data = response.json()
    
    weather = pd.DataFrame(data["hourly"])
    
    weather["time"] = pd.to_datetime(weather["time"],errors="coerce")
    
    weather = weather.dropna(subset=["time"])
    
    return weather


print(weatherApi(15.3699, 75.1240,"2025-08-01","2025-08-03"))