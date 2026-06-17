# -*- coding: utf-8 -*-
"""
Created on Wed Jun 10 11:55:12 2026

@author: Arzi
"""

import serial.tools.list_ports

for p in serial.tools.list_ports.comports():
    print(p.device, p.description)