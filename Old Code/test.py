# -*- coding: utf-8 -*-
"""
Created on Wed Jun 10 11:57:25 2026

@author: Arzi
"""
from snifflogic_basic.basic import Basic
import time
import pandas as pd
import matplotlib.pyplot as plt

# portName = "COM4"
# numPoints = 1000

# # set start time

# # try to connect to port 
# basic = Basic(portName)
# startTime = time.time_ns()

# data_time0 = (time.time_ns()-startTime)/1000000000 # time from start in seconds   
# data = basic.get_data()
# data_time1 = (time.time_ns()-startTime)/1000000000 # time from start in seconds   

# basic.close()


df = pd.read_csv('C:/Users/Arzi/Desktop/SniffDoc/daniel_recording.csv')
plt.plot(df['timestamp (s)'].diff())
plt.show()