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

class wetherAPI:
    
    worldCitiesPath = ".\\simplemaps_worldcities_basicv1.74\\worldcities.csv"
    cachePath = ".\\wetherDataCache.json"
    
    def __init__(self, city):
        
        if (type(city) != str):
            raise TypeError("The city name must be a string")
        self.city = city
        
        try:
            self.cityData = pandas.read_csv(self.worldCitiesPath)
        except FileNotFoundError:
            raise FileNotFoundError("The worldcities was not found in the programfiles: " \
                                    ".\\simplemaps_worldcities_basicv1.74\\worldcities.csv")
                
        
    def getCoordinates(self):
        self.cityList = self.cityData.loc[:, "city"]

        for i in range(len(self.cityList)):
            if self.city == self.cityList[i]:
                self.long, self.lat = self.cityData.loc[i, ["lng", "lat"]]
                return
        
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
        
    def getCurrentWetherData(self):
        self.getCoordinates()
        
        if os.path.isfile(self.cachePath):
            self.readExistingData()
            if self.jsonObj["City"] != self.city:
                self.httpRequest()
        else:
            self.httpRequest()
            
        expirationTime = datetime.strptime(self.jsonObj["Expires"], "%a, %d %b %Y %H:%M:%S %Z")
        expirationTime.replace(tzinfo=timezone.utc)
        curTime = datetime.now(timezone.utc)
        if expirationTime < curTime:
            self.httpRequest()
        
        tempData = self.jsonObj["properties"]["timeseries"][0]["data"]["instant"]["details"]
        self.curData = {"Air temperature" : tempData["air_temperature"], "Clouds_percent" : tempData["cloud_area_fraction"]}
            
    
    def readExistingData(self):
        with open(self.cachePath, "r") as file:
            self.jsonObj = json.load(file)
            
    def writeToCache(self):
        with open(self.cachePath, "w") as file:
            file.write(self.jsonObj.__str__().replace("\'", "\""))

if __name__=="__main__":
        
    startTime = time.time()
    testAPI = wetherAPI("Oslo")
    testAPI.getCurrentWetherData()
        
    print(time.time()-startTime)
    print(testAPI.curData.values())
    





    

    
