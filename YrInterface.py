# -*- coding: utf-8 -*-
"""
Created on Sat Mar  5 17:11:58 2022

@author: Bernt Moritz Schmid Olsen (s341528)   student at OsloMet

This module contains methods used to make http requests to the Met API:
    https://api.met.no/WeatherApi/locationforecast/2.0
    
The methods handles the air temperature and cloud_area_fraction for a 
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
    This class contains methods used to connect to the Met api and handle weather data. 
    """
    
    WORLD_CITIES_PATH = ".\\worldcities.csv"
    CACHE_PATH = ".\\WeatherCache\\wetherDataCache_{}.json"
    ABSOLUTE_ZERO = -273.15
    
    def __init__(self):  
        # Read the csv file containing data about cities
        try:
            self.cityData = pandas.read_csv(self.WORLD_CITIES_PATH)
        except FileNotFoundError:
            # Raise exception if the file does not exist
            raise FileNotFoundError("The worldcities file was not found in the programfiles: " +
                                    self.WORLD_CITIES_PATH)
        # Extract a list of all cities        
        self.cityList = self.cityData.loc[:, "city"]
                
        # Create the cache folder if it does not exist
        if not os.path.isdir("./WeatherCache"):
            # Create the directory
            os.mkdir("WeatherCache")
        
        
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
        """
        This method sends the http request to the Met Api and structures the 
        json response into a new json object with two new attributes 'Expires' 
        and 'City'. The json object is then written to cache.

        Raises
        ------
        Exception
            If the http request was unsuccesfull, an exception is raised.

        Returns
        -------
        None.

        """
        # The URL for the http request
        httpsString = f'https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={self.lat}&lon={self.long}'
        # The following header is added so Met api can identify the program 
        # that makes a request.
        headers = {'user-agent': 'PythonChatbot/1.0 s341528@oslomet.no', }
        # Executes the httprequest
        resp = requests.get(httpsString, headers=headers)
        
        if not resp.ok:
            # If the request did not succeed, an exceptin is raised
            raise Exception(str(resp.status_code) + ":" + resp.reason)
            
        # The response (json) is decoded and loaded into a json object
        self.jsonObj = json.loads(resp.content.decode())
        # The expiration data is extracted from the header and added in 
        # the json object.
        self.jsonObj["Expires"] = resp.headers["Expires"]
        # The cityname is added in the json object
        self.jsonObj["City"] = self.city
        # The current json object is written to cache
        self.writeToCache()
        
        
        
    def getCurrentWeatherData(self, city):
        """
        This method initiates the process of sending a request and receive the response
        from the Met api.
        
        Returns
        -------
        A tuple with air temperature and cloud_area_fraction for the specified 
        location for the next hour.
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
            # Control that the expiration time is not exceeded
            expirationTime = datetime.strptime(self.jsonObj["Expires"], "%a, %d %b %Y %H:%M:%S %Z")
            expirationTime = expirationTime.replace(tzinfo=timezone.utc)
            curTime = datetime.now(timezone.utc)
            if expirationTime < curTime:
                # If the expirationTime is exceeded, make a new request
                self.httpRequest()
        else:
            # If no cache exists for the city -> make a new request
            self.httpRequest()
            
        # Exctract the temperature and cloud area fraction of the next hour
        tempData = self.jsonObj["properties"]["timeseries"][0]["data"]["instant"]["details"]
        # Store the data as the curent data
        self.curData = {"Air temperature" : tempData["air_temperature"], 
                        "Cloud_area_fraction" : tempData["cloud_area_fraction"]}
        
        return (self.curData["Air temperature"], self.curData["Cloud_area_fraction"])
    
    def readExistingData(self):
        """
        This method reads the existing weather data for the location given by 
        the 'city' attribute. The data is loaded as a json object and added 
        to the jsonObj attribute.
        """
        with open(self.CACHE_PATH.format(self.city), "r") as file:
            # Load json from cache
            self.jsonObj = json.load(file)
            
    def writeToCache(self):
        """
        This method writes the curent json object to a file.
        """
        with open(self.CACHE_PATH.format(self.city), "w") as file:
            # The json object iw written to file
            file.write(self.jsonObj.__str__().replace("\'", "\""))
            
    def convertCloudArea(self, cloudAreaFrac):
        """
        This method converts the cloud_area_fraction number into 
        a word which describes how cloudy it is in the given city.

        Parameters
        ----------
        cloudAreaFrac : float
            This is the cloud_area_fraction found by the getCurrentWeatherData 
            method. It must be a float in the interval [0, 100].

        Raises
        ------
        TypeError
            If the argument is not of type float.
            
        RuntimeError
            If the argument is not a number between 0 and 100

        Returns
        -------
        str
            A word describing the amount of clouds in the sky.

        """
        if type(cloudAreaFrac) != float:
            # If the argument is not a float, raise an exception
            raise TypeError(f"The given argument cloudAreaFrac was of \
                            type {type(cloudAreaFrac)} when it should have \
                                been a float.")
        if cloudAreaFrac < 0 or cloudAreaFrac > 100:
            # The argument is invalid if it is not a number between 0 and 100
            raise RuntimeError("The cloud_area_fraction must be a number between 0 and 1!")
                            
        if cloudAreaFrac < 50:
            # if the cloud_area_fraction is less than 50%
            # then check if it is less than 25%
            if cloudAreaFrac < 25:
                # It is wery cloudy if the fraction is less than 25%
                return "wery cloudy"
            else:
                # It is cloudy if the fracction is greater or equal to 
                # 25% and less than 50% 
                return "cloudy"
        else:
            if cloudAreaFrac < 75:
                # If the fraction is less than 75% and greater or equal 
                # to 50 %
                return "partially cloudy"
            else:
                # If  the fraction is greater or equal to 75%
                return "clear"
    
    def convertTemperature(self, airTemp):
        """
        This method converts the air temperature into a word which 
        describes how hot or how cold it is.

        Parameters
        ----------
        airTemp : float
            This is the air_temperature found by the getCurrentWeatherData 
            method. It must be a float and cannot be less than −273.15 
            (absolute zero in celcius).
            
        Raises
        ------
        ValueError
            If the airTemp argument has a value 
            less than absolute zero.
            
        TypeError
            If the airTemp argument is not a float.
            
        Returns
        -------
        str
            A word that describes the air temperature.

        """
        # The input is validated
        if type(airTemp) != float:
            raise TypeError(f"The provided argument 'airTemp' was of type \
                             {type(airTemp)}. The argument should be of type float")
        
        if airTemp < self.ABSOLUTE_ZERO:
            # Verify that the argument is a valid temperature
            raise ValueError("The argument 'airTemp' should not be less than -273.15 \
                             degree celcius.")
                             
        # Convert the air temperature into a word which describes the temperature
        if airTemp > 10:
            if airTemp > 20:
                # The temperature is over 20 degree celcius
                return "hot"
            else:
                # The temperature is over 10 and less than or equal to 20 degree celcius
                return "not cold"
        else:
            if airTemp < 0:
                # The temperature is less than 0 degree celcius
                return "wery cold"
            else:
                # The temperature is less or equal to 10 or greater than 0 degree celcius 
                return "cold"

if __name__=="__main__":
        
    startTime = time.time()
    testAPI = WeatherApi()
    testAPI.getCurrentWeatherData("Oslo")
        
    print(time.time()-startTime)
    print(testAPI.curData.values())
    





    

    
