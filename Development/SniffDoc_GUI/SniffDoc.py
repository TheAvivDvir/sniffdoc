# -*- coding: utf-8 -*-
"""
Created on Wed Jun 10 16:54:10 2026

@author: Arzi
"""

import time
import csv
import threading
import queue
from collections import deque

from snifflogic_basic.basic import Basic

class SniffDoc:
    def __init__(self, port="COM4", buffer_size=1000, sample_rate_hz=100):
        self.basic = Basic(port)
        self.t0 = time.perf_counter()

        self.buffer = deque(maxlen=buffer_size)
        self.buffer_lock = threading.Lock()

        self.csv_queue = queue.Queue()
        self.inhale_queue = queue.Queue()

        self.sample_rate_hz = sample_rate_hz
        self.sample_period_s = 1.0 / sample_rate_hz

        self.running = True
        self.recording_csv = False
        self.inhale_detect = False
        
    def acquisition_loop(self):
        next_sample_time = time.perf_counter()
        while self.running:
            sleep_time = next_sample_time - time.perf_counter()
            if sleep_time > 0:
                time.sleep(sleep_time)

            try:
                t = self.clock()
                pressure = self.basic.get_data()
    
            except IndexError:
                continue   # skip bad/empty sample
    
            except Exception as e:
                print("Acquisition error:", e)
                continue
    
            sample = (t, pressure)
    
            with self.buffer_lock:
                self.buffer.append(sample)
    
            if self.recording_csv:
                self.csv_queue.put(sample)

            if self.inhale_detect:
                self.inhale_queue.put(sample)

            next_sample_time += self.sample_period_s
            if time.perf_counter() > next_sample_time:
                next_sample_time = time.perf_counter() + self.sample_period_s
    
    def start_acquisition(self):
        self.acq_thread = threading.Thread(
            target=self.acquisition_loop,
            daemon=True
        )
        self.acq_thread.start()
    
    def csv_writer_loop(self, path):
        file = open(path, "w", newline="") #Code debt - maybe slow down updating csv
        writer = csv.writer(file)
        writer.writerow(["time", "pressure", "notes"])

        while self.recording_csv:
            try:
                sample = self.csv_queue.get(timeout=0.5)
                writer.writerow([sample[0], sample[1], ""])
            except queue.Empty:
                pass

        file.close()
        
    def start_csv_recording(self, path="default.csv"):
        self.recording_csv = True
        self.csv_thread = threading.Thread(
            target=self.csv_writer_loop,
            args=(path,),
            daemon=True
        )
        self.csv_thread.start()

    def stop_csv_recording(self):
        self.recording_csv = False
    
    def inhale_detect_loop(self):
        """
        This function is the loop running inside the inhale detection loop.
        It taps into the aquisition process from the device and performs the
        following analysis on the data.
        
        It first detects an inhale by looking at consecutive points above a
        given amplitudal threshold that acumelate to be above a specifc number
        of points. Then, it looks for consecutive inhales taken at least one
        second appart and if these inhales's volumes are overlapping within 20%
        of eachother, the expirement is activated.
        """
        amp_th = 0.1
        min_time_th = 0.25
        min_dist_s = 1
        overlap_th = 0.2

        prev_t = None
        inhales_cnt = 0
        inhale_flag = False
        time_count = 0
        curr_vol = 0
        vol_deque = deque(maxlen=3)
        onset_time_prev = self.clock()
        onset_time = onset_time_prev
 
        while self.inhale_detect:
            try:
                t, pressure = self.inhale_queue.get(timeout=0.5)
            except queue.Empty:
                print("Inhale detect: no data received in 0.5s")
                continue
            
            dt = t-prev_t if prev_t is not None else 0
            prev_t = t

            if pressure > amp_th:
                if inhale_flag:
                    time_count = t - onset_time
                    curr_vol += pressure * dt
                else:
                    inhale_flag = True
                    time_count = t - onset_time
                    curr_vol += pressure * dt
                    onset_time = t
            else:
                if inhale_flag and time_count >= min_time_th and (onset_time -
                                                                        onset_time_prev) >= min_dist_s:
                    if inhales_cnt < 3:
                        inhales_cnt += 1
                    print(f"Inhale detected! Total count: {inhales_cnt}")
                    vol_deque.append(curr_vol)
                    onset_time_prev = onset_time
                    if len(vol_deque) == 3:
                        v1, v2, v3 = vol_deque
                        
                        cond1 = abs(v2 - v1) <= overlap_th * max(v1, v2)
                        cond2 = abs(v3 - v2) <= overlap_th * max(v2, v3)
                        cond3 = abs(v3 - v1) <= overlap_th * max(v1, v3)
                        if cond1 and cond2 and cond3:
                            print("Experiment activated!")
                            self.inhale_detect = False
                            continue
                inhale_flag = False
                time_count = 0
                curr_vol = 0

    
    def inhale_detect_start(self):
        """
        This function starts the inhale detection thread.
        """
        self.inhale_detect = True
        self.inhale_thread = threading.Thread(
            target=self.inhale_detect_loop,
            daemon=True
        )
        self.inhale_thread.start()
    
    def inhale_detect_stop(self):
        """
        This function deactivates the inhale detection thread.
        """
        self.inhale_detect = False
    
    def close(self):
        self.running = False
        self.recording_csv = False
        self.inhale_detect = False
        time.sleep(0.5)
        self.basic.close()

# -------- HELPER FUNCTIONS --------
    
    def clock(self):
        return time.perf_counter() - self.t0

    
    def get_buffer(self):
        with self.buffer_lock:
            return self.buffer
        
    def get_sample_rate(self):
        return self.sample_rate_hz
        