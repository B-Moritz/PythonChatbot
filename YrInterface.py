# -*- coding: utf-8 -*-
"""
Created on Sat Mar  5 17:11:58 2022

@author: Bernt Moritz Schmid Olsen (s341528)   student at OsloMet

This module contains methods used to make http requests to the Met API:
    https://api.met.no/WeatherApi/locationforecast/2.0
    
The methods handles the air temperature and cloud_area_percentage for a 
given location. The forecast is for now and the next hour.

"""

import requests
import pandas
import time
import json
import os
from datetime import datetime, timezone

class WeatherApi:
    """
    This class contains method to connect to the Met api. 
    """
    
    WORLD_CITIES_PATH = ".\\simplemaps_worldcities_basicv1.74\\worldcities.csv"
    CACHE_PATH = ".\\wetherDataCache_{}.json"
    
    def __init__(self):  
        # Read the csv file containing data about cities
        try:
            self.cityData = pandas.read_csv(self.WORLD_CITIES_PATH)
        except FileNotFoundError:
            # Raise exception if the file does not exist
            raise FileNotFoundError("The worldcities was not found in the programfiles: " \
                                    ".\\simplemaps_worldcities_basicv1.74\\worldcities.csv")
        # Extract a list of all cities        
        self.cityList = self.cityData.loc[:, "city"]
                
        
    def getCoordinates(self, city):
        """
        This method finds the coordinates (latitude and longitued)
        of the city provided as argument to this method. The coordinates 
        are stored in the atributes long and lat.        

        Parameters
        ----------
        city : String
            City name.

        Raises
        ------
        ValueError
            Raised if the city name was not recognised.

        Returns
        -------
        bool
            Returns true if coordinates were found.

        """
        
        for i in range(len(self.cityList)):
            # For each city in the city list, check if it matches the given cityname.
            if city == self.cityList[i]:
                # Find the coordinates in the among the city data
                self.long, self.lat = self.cityData.loc[i, ["lng", "lat"]]
                return True
        
        # Raise error if the cityname was not found in the list.
        raise ValueError(f"The provided city name, {city}, was not found.")
        
    def httpRequest(self):
        httpsString = f'https://api.met.no/WeatherApi/locationforecast/2.0/compact?lat={self.lat}&lon={self.long}'
        headers = {'user-agent': 'PythonChatbot/1.0 s341528@oslomet.no', }

        resp = requests.get(httpsString, headers=headers)
        
        if not resp.ok:
            raise Exception(str(resp.status_code) + ":" + resp.reason)
            
        self.jsonObj = json.loads(resp.content.decode())
        self.jsonObj["Expires"] = resp.headers["Expires"]
        self.jsonObj["City"] = self.city
        
        self.writeToCache()
        
    def getCurrentWeatherData(self, city):
        """
        This method initiates the process of sending a request and receive the response
        from the Met api. 
        """
        if (type(city) != str):
            # Raise an exeption if the city argument provided is not a string.
            raise TypeError("The city name must be a string")
        # Set the city attribute
        self.city = city
        
        try:
            # Try to get the coordinates of the city
            self.getCoordinates(self.city)
        except ValueError:
            # The method throws a ValueError if the city was not found.
            # The exception is re-raised
            raise
        
        
        if os.path.isfile(self.CACHE_PATH.format(self.city)):
            # If cache file exists for the specific city, read the existing data
            self.readExistingData()
            if self.jsonObj["City"] != self.city:
                self.httpRequest()
        else:
            self.httpRequest()
            
        expirationTime = datetime.strptime(self.jsonObj["Expires"], "%a, %d %b %Y %H:%M:%S %Z")
        expirationTime = expirationTime.replace(tzinfo=timezone.utc)
        curTime = datetime.now(timezone.utc)
        if expirationTime < curTime:
            self.httpRequest()
        
        tempData = self.jsonObj["properties"]["timeseries"][0]["data"]["instant"]["details"]
        self.curData = {"Air temperature" : tempData["air_temperature"], 
                        "Cloud_percent" : tempData["cloud_area_fraction"]}
    
    def readExistingData(self):
        """
        This method reads the existing weather data for the given location.

        Returns
        -------
        None.

        """
        with open(self.CACHE_PATH.format(self.city), "r") as file:
            self.jsonObj = json.load(file)
            
    def writeToCache(self):
        with open(self.CACHE_PATH.format(self.city), "w") as file:
            file.write(self.jsonObj.__str__().replace("\'", "\""))
            
    def classifyCloudArea(self):
        if self.curData["Cloud_percent"]:
            ratio = self.curData["Cloud_percent"]
        else:
            raise Exception("No cloud percentage was found. \
                            Did you forget to run 'getCurrentWeatherData'?")
                            
        if ratio < 0.5:
            if ratio < 0.25:
                return "wery cloudy"
            else:
                return "cloudy"
        else:
            if ratio < 0.75:
                return "partially cloudy"
            else:
                return "Sunny"
    
    def classsifyTemperature(self):
        if self.curData["Air temperature"]:
            temp = self.curData["Air temperature"]
        else:
            raise Exception("No air temperature data was found. \
                            Did you forget to run 'getCurrentWeatherData'?")
        
        if temp > 10:
            if temp > 20:
                return "hot"
            else:
                return "not cold"
        else:
            if temp < 0:
                return "wery cold"
            else:
                return "cold"

if __name__=="__main__":
        
    startTime = time.time()
    testAPI = WeatherApi()
    testAPI.getCurrentWeatherData("Oslo")
        
    print(time.time()-startTime)
    print(testAPI.curData.values())
    





    

    
