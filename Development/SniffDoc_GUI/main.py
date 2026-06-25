# %matplotlib qt

# from snifflogic_basic.basic import *
# import numpy as np
# import matplotlib.pyplot as plt
from pathlib import Path

from nicegui import ui, app
# import time
# import serial
# import csv

# import time
from SniffDoc import SniffDoc

from main_page import build_main_page

@ui.page("/")
def index():
    build_main_page(sd)

def main():
    global sd
    project_root = Path(__file__).resolve().parents[2]
    sounds_dir = project_root / "Sounds"
    app.add_static_files("/sounds", str(sounds_dir))

    sd = SniffDoc()
    sd.start_acquisition()
    app.on_shutdown(sd.close)
    ui.run(reload=False)

    

if __name__ == "__main__":
    main()





# def main():
#     slb = SniffDoc()

#     plt.ion()
#     fig, ax = plt.subplots()
#     line, = ax.plot([], [])

#     ax.set_xlabel("Time [s]")
#     ax.set_ylabel("Pressure")
#     ax.grid(True)    

#     try:
#         slb.start_acquisition()
#         time.sleep(2)

#         slb.start_csv_recording()
#         time.sleep(1)

#         slb.inhale_detect_start()
        
#         for i in range(2000):
#             buffer = slb.get_buffer()
#             if not buffer:
#                 continue
#             times, pressures = zip(*buffer)
#             line.set_data(times, pressures)
#             ax.relim()
#             ax.autoscale_view()
#             fig.canvas.draw()
#             fig.canvas.flush_events()
#             time.sleep(0.005)

#         slb.stop_csv_recording()
#         slb.close()
#     finally:
#         slb.close()






# def main():
    # f = open("data.csv", "w", newline="")
    # writer = csv.writer(f)
    # writer.writerow(["time", "pressure", "inh_vol"])
    # plt.close('all')
    
    # data = np.full((300, 2), np.nan)
    # basic = Basic("COM4")
    # startTime = time.time_ns()
    
    # plt.ion()
    # fig, ax = plt.subplots()
    # line, = ax.plot([], [])

    # ax.set_xlabel("Time [s]")
    # ax.set_ylabel("Value")
    # ax.grid(True)

    # print('start')
    
    # inh_cnt = 0
    # inh_vol = 0
    # pres_th = 10
    # vol_th = 30
    # time_th = 0.6
    
    # inh_flag = False
    # inh_t_s = 0
    
    # for i in range(4000):
    #     curr_loc = i%300
        
    #     pres = basic.get_data()
    #     curr_time = (time.time_ns()-startTime)/1000000000
        
    #     data[curr_loc, 0] = curr_time
    #     data[curr_loc, 1] = pres
        
    #     dt = curr_time - data[curr_loc-1, 0] if curr_loc > 0 else 0

    #     if pres > pres_th:
    #         inh_vol += pres*dt
    #         if not inh_flag:
    #             inh_flag = True
    #             inh_t_s = curr_time
    #     else:
    #         if inh_vol > vol_th and curr_time - inh_t_s > time_th:
    #             inh_cnt += 1
    #             print(f"Inhalation detected! Count: {inh_cnt}")
    #         inh_flag = False
    #         inh_vol = 0
            
    #     writer.writerow([curr_time, pres, inh_vol])

    #     # print(inh_vol)    
            
        
    #     x = np.r_[data[curr_loc+1:,0], np.nan, data[:curr_loc+1,0]]
    #     y = np.r_[data[curr_loc+1:,1], np.nan, data[:curr_loc+1,1]]
    #     line.set_data(x, y)
        
    #     ax.relim()
    #     ax.autoscale_view()

    #     fig.canvas.draw()
    #     fig.canvas.flush_events()
        
        
    #     # time.sleep(0.005)

    # print('end')
    # basic.close()
    # f.close()
    
    # plt.ioff()
    # plt.show()
    # return data
    
    

# if __name__ == "__main__":
#     data = main()
