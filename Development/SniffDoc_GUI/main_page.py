# -*- coding: utf-8 -*-
"""
Created on Mon Jun 15 14:59:10 2026

@author: Arzi
"""

import os
import asyncio

import tkinter as tk
from tkinter import filedialog
from nicegui import ui, app

from SniffDoc import SniffDoc
from plotting import create_pressure_figure, update_pressure_figure

# Pre-create a hidden Tk root so the folder dialog opens quickly on demand.
# The first call to tkinter can be slow, so we do it once when the module loads.
try:
    _tk_root = tk.Tk()
    _tk_root.withdraw()
except Exception:
    _tk_root = None

def build_main_page(sd: SniffDoc = None):
    # Top header
    with ui.row().classes("w-full items-center justify-between p-4"):
        ui.label("SniffDoc").classes("text-3xl font-bold")
        ui.label("Connected ●").classes("text-lg")

    ui.separator()

    # Recording state
    recording_state = {"is_recording": False, "recording_path": "./recordings"}

    # Main plot area with Start Recording button to the right
    ui.label("Live Pressure Signal").classes("text-xl font-bold pl-4")
    
    with ui.row().classes("w-full p-4 gap-4"):
        # Plot on the left
        pressure_figure = create_pressure_figure(sd.buffer.maxlen, sd.sample_rate_hz)
        pressure_plot = (ui.plotly(pressure_figure).classes("w-1/2 h-[300px]")
                         .props('config={"displaylogo": False, "displayModeBar": False}'))
        
        def refresh_plot():
            if sd is None:
                return

            buffer = sd.get_buffer()
            window_size = sd.buffer.maxlen / sd.get_sample_rate()
            update_pressure_figure(pressure_figure, buffer, window_size, recording_state["is_recording"])
            pressure_plot.update()

        ui.timer(0.1, refresh_plot)

        # Container for buttons on the right
        with ui.row().classes("self-center"):
            record_button = ui.button("Start Recording")
            save_button = ui.button("Save Recording")
            save_button.visible = False

    ui.separator()

    with ui.row().classes("w-full justify-between p-4"):

        # Left side
        with ui.column():
            status_label = ui.label("Status: Waiting")
            recording_label = ui.label("Recording: Off")
            experiment_label = ui.label("Experiment: Idle")

        # Right side
        with ui.row():
            experiment_button = ui.button("Run Experiment")
            settings_button = ui.button("Settings")

    #------------------- BUTTON FUNCTIONS -------------------#
    
    # Recording and Save button handlers
    def on_recording_click():
        if not recording_state["is_recording"]:
            # Start recording
            recording_state["is_recording"] = True
            
            # Create directory if it doesn't exist
            os.makedirs(recording_state["recording_path"], exist_ok=True)
            
            # Build file path for current recording
            curr_recording_path = os.path.join(recording_state["recording_path"], "curr_recording.csv")
            
            # Delete old curr_recording if it exists
            if os.path.exists(curr_recording_path):
                os.remove(curr_recording_path)
            
            # Start CSV recording
            sd.start_csv_recording(curr_recording_path)
            
            # Update UI
            record_button.text = "Stop Recording"
            save_button.visible = False
            recording_label.text = "Recording: On"
        else:
            # Stop recording
            recording_state["is_recording"] = False
            sd.stop_csv_recording()
            
            # Update UI
            record_button.text = "Start Recording"
            save_button.visible = True
            recording_label.text = "Recording: Off"

    def on_save_click():
        # Open dialog to ask for filename
        with ui.dialog() as save_dialog:
            with ui.card():
                ui.label("Save Recording").classes("text-xl font-bold")
                
                ui.label("Enter a name for this recording:").classes("text-lg font-semibold mt-4")
                filename_input = ui.input(
                    label="Recording name:",
                    placeholder="my_recording"
                ).classes("w-full")
                
                with ui.row().classes("justify-end gap-2 mt-4"):
                    def on_cancel():
                        save_dialog.close()
                    
                    def on_confirm():
                        # Get the filename and ensure it has .csv extension
                        filename = filename_input.value.strip()
                        if not filename:
                            ui.notify("Please enter a filename", type="negative")
                            return
                        
                        if not filename.endswith(".csv"):
                            filename += ".csv"
                        
                        # Build paths
                        curr_recording_path = os.path.join(recording_state["recording_path"], "curr_recording.csv")
                        new_recording_path = os.path.join(recording_state["recording_path"], filename)
                        # If target file exists, ask user to choose another name
                        if os.path.exists(new_recording_path):
                            ui.notify("A file with that name already exists. Please choose a different name.", type="negative")
                            return

                        # Rename file from curr_recording to new name
                        try:
                            os.rename(curr_recording_path, new_recording_path)
                            ui.notify(f"Recording saved to: {new_recording_path}", type="positive")
                        except FileNotFoundError:
                            ui.notify("No recording found to save", type="negative")
                            return
                        except Exception as e:
                            ui.notify(f"Error saving recording: {str(e)}", type="negative")
                            return

                        save_button.visible = False
                        save_dialog.close()
                    
                    ui.button("Cancel", on_click=on_cancel)
                    ui.button("Save", on_click=on_confirm)
        
        save_dialog.open()
    
    def on_settings_click():
        # Create settings dialog
        with ui.dialog() as settings_dialog:
            with ui.card():
                ui.label("Settings").classes("text-xl font-bold")
                
                ui.label("Recording Path").classes("text-lg font-semibold mt-4")
                with ui.row().classes("items-center gap-2"):
                    recording_path_input = ui.input(
                        label="Save recordings to:",
                        value=recording_state["recording_path"]
                    ).classes("w-1/2")

                    async def on_browse(e=None):
                        def open_tk_dialog():
                            if _tk_root is None:
                                raise RuntimeError('Tkinter is unavailable or failed to initialize')

                            path = filedialog.askdirectory(
                                initialdir=recording_state["recording_path"],
                                parent=_tk_root,
                            )
                            return path

                        try:
                            path = await asyncio.to_thread(open_tk_dialog)
                        except Exception as ex:
                            ui.notify(f"Error opening folder chooser: {ex}", type="negative")
                            return

                        if path:
                            recording_path_input.value = path

                    ui.button("Browse", on_click=lambda e=None: asyncio.create_task(on_browse(e)))
                
                with ui.row().classes("justify-end gap-2 mt-4"):
                    def on_cancel():
                        settings_dialog.close()
                    
                    def on_apply():
                        # Store the selected path
                        recording_state["recording_path"] = recording_path_input.value
                        ui.notify(f"Recording path set to: {recording_path_input.value}")
                        settings_dialog.close()
                    
                    ui.button("Cancel", on_click=on_cancel)
                    ui.button("Apply", on_click=on_apply)
        
        settings_dialog.open()
    
    record_button.on_click(on_recording_click)
    save_button.on_click(on_save_click)
    settings_button.on_click(on_settings_click)