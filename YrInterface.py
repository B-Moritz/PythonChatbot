# -*- coding: utf-8 -*-
"""
Created on Sat Mar  5 17:11:58 2022

@author: b-mor
"""

import requests
import pandas
import time
import json
import os
from datetime import datetime, timezone

class weatherAPI:
    
    worldCitiesPath = ".\\simplemaps_worldcities_basicv1.74\\worldcities.csv"
    cachePath = ".\\wetherDataCache_{}.json"
    
    def __init__(self):       
        try:
            self.cityData = pandas.read_csv(self.worldCitiesPath)
        except FileNotFoundError:
            raise FileNotFoundError("The worldcities was not found in the programfiles: " \
                                    ".\\simplemaps_worldcities_basicv1.74\\worldcities.csv")
                
        self.cityList = self.cityData.loc[:, "city"]
                
        
    def getCoordinates(self, city):
        
        for i in range(len(self.cityList)):
            if city == self.cityList[i]:
                self.long, self.lat = self.cityData.loc[i, ["lng", "lat"]]
                return True
        
        raise ValueError(f"The provided city name, {self.city}, was not found.")
        
    def httpRequest(self):
        httpsString = f'https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={self.lat}&lon={self.long}'
        headers = {'user-agent': 'PythonChatbot/1.0 s341528@oslomet.no', }

        resp = requests.get(httpsString, headers=headers)
        
        if not resp.ok:
            raise Exception(resp.status_code + ":" + resp.reason)
            
        self.jsonObj = json.loads(resp.content.decode())
        self.jsonObj["Expires"] = resp.headers["Expires"]
        self.jsonObj["City"] = self.city
        
        self.writeToCache()
        
    def getCurrentWeatherData(self, city):
        
        if (type(city) != str):
            raise TypeError("The city name must be a string")
        self.city = city
        
        try:
            self.getCoordinates(self.city)
        except ValueError:
            raise
            
        if os.path.isfile(self.cachePath.format(self.city)):
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
        with open(self.cachePath.format(self.city), "r") as file:
            self.jsonObj = json.load(file)
            
    def writeToCache(self):
        with open(self.cachePath.format(self.city), "w") as file:
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
    testAPI = weatherAPI()
    testAPI.getCurrentWeatherData("Oslo")
        
    print(time.time()-startTime)
    print(testAPI.curData.values())
    





    

    
