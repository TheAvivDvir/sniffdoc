# -*- coding: utf-8 -*-
"""
Created on Mon Jun 15 14:59:10 2026

@author: Arzi
"""

import os
import json

import tkinter as tk
from tkinter import filedialog
from nicegui import ui, app

from SniffDoc import SniffDoc
from experiment import ExperimentConfig, ExperimentService, LANG_DICT
from plotting import create_pressure_figure, update_pressure_figure

BEEP_SOUND_PATH = "/sounds/beep_short.mp3"

def build_main_page(sd: SniffDoc = None):
    # Top header
    with ui.row().classes("w-full items-center justify-between p-4"):
        ui.label("SniffDoc").classes("text-3xl font-bold")
        ui.label("Connected ●").classes("text-lg")

    ui.separator()

    # Recording state
    recording_state = {"is_recording": False, "recording_path": "./recordings"}
    experiment_state = {"is_running": False, "num_jars": 3, "num_repetitions": 10, "cooldown_time": 8, 
                        "experiment_lang": "Hebrew", "stage": "idle", "current_jar": None,
                        "jar_index": 0, "inhales_in_cycle": 0, "prep_sound_duration_s": 3.0}
    experiment_service = ExperimentService(sd)
    experiment_window_state = {"dialog": None, "figure": None, "plot": None, "instruction": None}

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

    def update_experiment_instruction(stage, jar_number=None):
        experiment_state["stage"] = stage

        if stage == "waiting":
            message = "Look for 3 good inhales."
        elif stage == "inhale":
            message = f"Inhale {experiment_state['inhales_in_cycle']}/3"
        elif stage == "prepare":
            message = f"Prepare jar {jar_number}."
        elif stage == "present":
            message = f"Present jar {jar_number} to subject."
        elif stage == "cooldown":
            message = f"Cooldown for {experiment_state['cooldown_time']} seconds."
        elif stage == "complete":
            message = "Experiment complete."
        elif stage == "recording_needed":
            message = "Start recording first."
        elif stage == "idle":
            message = ""
        else:
            message = stage

        if experiment_window_state["instruction"] is not None:
            experiment_window_state["instruction"].text = message

    def play_sound_then_beep(prep_sound_path, beep_sound_path):
        prep_web_path = prep_sound_path.replace("\\", "/")
        beep_web_path = beep_sound_path.replace("\\", "/")
        ui.run_javascript(
            """
            (() => {
                const prep = new Audio(PREP_PATH);
                const beep = new Audio(BEEP_PATH);
                prep.onended = () => {
                    beep.play().catch(() => {});
                };
                prep.play().catch(() => {});
            })()
            """.replace("PREP_PATH", json.dumps(prep_web_path)).replace("BEEP_PATH", json.dumps(beep_web_path))
        )

    def poll_inhale_events():
        if not experiment_state["is_running"]:
            return

        experiment_service.poll()
        for event in experiment_service.drain_ui_events():
            event_type = event.get("type")
            if event_type == "instruction":
                if "count" in event:
                    experiment_state["inhales_in_cycle"] = int(event["count"])
                if "jar_number" in event:
                    experiment_state["current_jar"] = int(event["jar_number"])
                update_experiment_instruction(event.get("stage", "idle"), jar_number=event.get("jar_number"))
            elif event_type == "sound" and event.get("kind") == "prep_then_beep":
                play_sound_then_beep(event.get("prep_sound_path", ""), event.get("beep_sound_path", BEEP_SOUND_PATH))
            elif event_type == "status" and event.get("status") == "stopped":
                experiment_state["is_running"] = False
                experiment_label.text = "Experiment: Idle"
                experiment_button.text = "Run Experiment"

    def start_experiment_window():
        if experiment_window_state["dialog"] is not None:
            experiment_window_state["dialog"].open()
            return

        with ui.dialog() as experiment_dialog:
            with ui.card().classes("w-[95vw] max-w-none h-[95vh] max-h-none"):
                with ui.row().classes("w-full items-center justify-between pb-2"):
                    ui.label("Experiment Running").classes("text-2xl font-bold")
                    ui.label(f"Language: {experiment_state['experiment_lang']}").classes("text-base text-gray-600")

                with ui.column().classes("w-full h-full gap-4"):
                    with ui.column().classes("w-full"):
                        experiment_window_state["figure"] = create_pressure_figure(sd.buffer.maxlen, sd.sample_rate_hz)
                        experiment_window_state["plot"] = (
                            ui.plotly(experiment_window_state["figure"]).classes("w-full h-[55vh]")
                            .props('config={"displaylogo": False, "displayModeBar": False}')
                        )

                        def refresh_experiment_plot():
                            if sd is None or experiment_window_state["figure"] is None:
                                return

                            buffer = sd.get_buffer()
                            window_size = sd.buffer.maxlen / sd.get_sample_rate()
                            update_pressure_figure(
                                experiment_window_state["figure"],
                                buffer,
                                window_size,
                                recording_state["is_recording"],
                            )
                            experiment_window_state["plot"].update()

                        ui.timer(0.1, refresh_experiment_plot)
                        ui.timer(0.1, poll_inhale_events)

                    with ui.column().classes("w-full items-center justify-center p-4 bg-gray-50 rounded-lg min-h-[18vh]"):
                        experiment_window_state["instruction"] = ui.label("").classes("text-5xl font-black text-center leading-tight")

                with ui.row().classes("w-full justify-center pt-4"):
                    def on_close_window():
                        close_experiment_and_save()

                    ui.button("Close", on_click=on_close_window)

        experiment_window_state["dialog"] = experiment_dialog
        experiment_dialog.open()

    def start_experiment():
        experiment_service.set_config(
            ExperimentConfig(
                num_jars=experiment_state["num_jars"],
                num_repetitions=experiment_state["num_repetitions"],
                cooldown_time=experiment_state["cooldown_time"],
                experiment_lang=experiment_state["experiment_lang"],
                prep_sound_duration_s=experiment_state["prep_sound_duration_s"],
                beep_duration_s=2.0,
            )
        )

        experiment_state["is_running"] = True
        experiment_state["current_jar"] = None
        experiment_state["jar_index"] = 0
        experiment_state["inhales_in_cycle"] = 0
        experiment_label.text = "Experiment: Running"
        experiment_button.text = "Stop Experiment"
        ui.notify("Experiment started", type="positive")

        start_experiment_window()
        experiment_service.start()

    def stop_experiment():
        experiment_state["is_running"] = False
        experiment_service.stop()
        update_experiment_instruction("idle")
        experiment_label.text = "Experiment: Idle"
        experiment_button.text = "Run Experiment"
        ui.notify("Experiment stopped", type="negative")

    def close_experiment_and_save():
        if experiment_window_state["dialog"] is not None:
            experiment_window_state["dialog"].close()

        stop_experiment()

        if recording_state["is_recording"]:
            on_recording_click()
            on_save_click()
    
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
            with ui.card().classes('w-[700px] max-w-[90vw]'):
                ui.label("Settings").classes("text-xl font-bold")
                
                ui.label("Recording Settings").classes("text-lg font-semibold mt-4")
                with ui.row().classes("w-full items-center gap-2"):
                    recording_path_input = ui.input(
                        label="Save recordings to:",
                        value=recording_state["recording_path"]
                    ).classes("flex-grow")

                    def on_browse():
                        root = tk.Tk()
                        root.withdraw()
                        try:
                            path = filedialog.askdirectory(
                                initialdir=recording_state["recording_path"],
                                parent=root,
                            )
                            if path:
                                recording_path_input.value = path
                        except Exception as ex:
                            ui.notify(f"Error opening folder chooser: {ex}", type="negative")
                        finally:
                            root.destroy()

                    ui.button("Browse", on_click=on_browse)
                
                ui.label("Experiment Settings").classes("text-lg font-semibold mt-4")
                with ui.row().classes("w-1/2 items-center gap-2"):
                    num_jars_input = ui.input(
                        label="Number of Jars:",
                        value=str(experiment_state["num_jars"])
                    ).classes("w-full").props("type='number' min=1")

                with ui.row().classes("w-1/2 items-center gap-2"):
                    num_repetitions_input = ui.input(
                        label="Number of Repetitions for each Jar:",
                        value=str(experiment_state["num_repetitions"])
                    ).classes("w-full").props("type='number' min=1")

                with ui.row().classes("w-1/2 items-center gap-2"):
                    cooldown_time_input = ui.input(
                        label="Cooldown time (seconds) between repetitions:",
                        value=str(experiment_state["cooldown_time"])
                    ).classes("w-full").props("type='number' min=0")

                with ui.row().classes("w-1/2 items-center gap-2"):
                    experiment_lang = ui.select(
                        label="Language for experiment instructions:", 
                        options=list(LANG_DICT.keys()),
                        value="Hebrew"
                    ).classes("w-full")

                with ui.row().classes("justify-end gap-2 mt-4"):
                    def on_cancel():
                        settings_dialog.close()
                    
                    def on_apply():
                        # Store the selected path
                        recording_state["recording_path"] = recording_path_input.value
                        ui.notify(f"Recording path set to: {recording_path_input.value}")

                        # Store the number of jars
                        try:
                            num_jars = int(num_jars_input.value)
                            if num_jars < 1:
                                raise ValueError("Number of jars must be at least 1")
                            experiment_state["num_jars"] = num_jars
                            ui.notify(f"Number of jars set to: {num_jars}")
                        except ValueError as ve:
                            ui.notify(f"Invalid number of jars: {ve}", type="negative")
                            return

                        # Store the number of repetitions
                        try:
                            num_repetitions = int(num_repetitions_input.value)
                            if num_repetitions < 1:
                                raise ValueError("Number of repetitions must be at least 1")
                            experiment_state["num_repetitions"] = num_repetitions
                            ui.notify(f"Number of repetitions set to: {num_repetitions}")
                        except ValueError as ve:
                            ui.notify(f"Invalid number of repetitions: {ve}", type="negative")
                            return

                        # Store the cooldown time
                        try:
                            cooldown_time = int(cooldown_time_input.value)
                            if cooldown_time < 0:
                                raise ValueError("Cooldown time must be a non-negative number")
                            experiment_state["cooldown_time"] = cooldown_time
                            ui.notify(f"Cooldown time set to: {cooldown_time}")
                        except ValueError as ve:
                            ui.notify(f"Invalid cooldown time: {ve}", type="negative")
                            return
                        
                        # Store the selected language for experiment instructions
                        experiment_state["experiment_lang"] = experiment_lang.value

                        settings_dialog.close()
                    
                    ui.button("Cancel", on_click=on_cancel)
                    ui.button("Apply", on_click=on_apply)
        
        settings_dialog.open()
    
    def on_experiment_click():
        if not experiment_state["is_running"]:
            # Start the experiment
            if not recording_state["is_recording"]:
                with ui.dialog() as warning_dialog:
                    with ui.card():
                        ui.label("Warning").classes("text-xl font-bold")
                        ui.label("You must start recording before running the experiment. Would you like to start recording now?").classes("text-lg mt-4")
                        with ui.row().classes("justify-end gap-2 mt-4"):
                            def on_cancel():
                                warning_dialog.close()
                                return
                            
                            def on_start_recording():
                                warning_dialog.close()
                                on_recording_click()  # Start recording
                                start_experiment()
                            
                            ui.button("Cancel", on_click=on_cancel)
                            ui.button("Start Recording", on_click=on_start_recording)

                        warning_dialog.open()
                        return

            start_experiment()
        else:
            # Stop the experiment
            stop_experiment()
            
            # Here you would add the logic to stop the experiment using the SniffDoc instance (sd)
            # For example: sd.stop_experiment()

    record_button.on_click(on_recording_click)
    save_button.on_click(on_save_click)
    settings_button.on_click(on_settings_click)
    experiment_button.on_click(on_experiment_click)