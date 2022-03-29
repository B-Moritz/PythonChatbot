# -*- coding: utf-8 -*-
"""
Created on Sat Mar  5 14:32:10 2022

@author: b-mor
"""

import requests
import csv
import pandas
#import numpy as np
import time


# with open(".\\simplemaps_worldcities_basicv1.74\\worldcities.csv", "r", encoding=("utf8")) as cityData:
#     csvReader = csv.reader(cityData)
#     for line in csvReader:
#         print(line)

def hashFunc(city):
    hashVal = 0
    for i in range(len(city)):
        hashVal += ord(city[i])*13
    return hashVal % 10000

if __name__ == "__main__":

    startTime = time.time()
    
    test = pandas.read_csv(".\\simplemaps_worldcities_basicv1.74\\worldcities.csv")
    
    cityArr = test.loc[:, "city_ascii"]
    maxVal = 0
    hashList = [0] * 10000
    for i in range(len(hashList)):
        hashList[i] = []
    
    for j in range(len(cityArr)):
        city = cityArr[j]
        
        try:
            hashList[hashFunc(city)].append(j)
        except:
            print(hashFunc(city))
            
    testCity = "Oslo"
    lines = hashList[hashFunc(testCity)]
    for line in lines:
        curCity = test.loc[line, "city"]
        if curCity == testCity:
            long, lat = test.loc[line, ["lng", "lat"]]
            print(lat, long)
            break
        
    print(time.time() - startTime)
        

    
    

    
    
    
