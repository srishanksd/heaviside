import numpy as np   

def nearestStation(df,latitude,longitude):
    
    distance = np.sqrt(
        (df["latitude"]-latitude)**2 +
        (df["longitude"]-longitude)**2
    )
    
    index = distance.idxmin()
    
    station = df.loc[index]
    
    return station