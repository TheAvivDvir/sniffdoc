# -*- coding: utf-8 -*-
"""Experiment orchestration service for SniffDoc GUI."""

import queue
import threading
from dataclasses import dataclass

import numpy as np

LANG_DICT = {
    "English": "/sounds/prepare_to_sniff_english.mp3",
    "Hebrew": "/sounds/prepare_to_sniff_hebrew.mp3",
    "French": "/sounds/prepare_to_sniff_french.mp3",
    "German": "/sounds/prepare_to_sniff_german.mp3",
    "Italian": "/sounds/prepare_to_sniff_italian.mp3",
    "Arabic": "/sounds/prepare_to_sniff_arabic.mp3",
}
BEEP_SOUND_PATH = "/sounds/beep_short.mp3"


@dataclass
class ExperimentConfig:
    num_jars: int = 3
    num_repetitions: int = 10
    cooldown_time: int = 8
    experiment_lang: str = "Hebrew"
    prep_sound_duration_s: float = 3.0
    beep_duration_s: float = 2.0


class ExperimentService:
    def __init__(self, sniffdoc):
        self.sd = sniffdoc
        self.config = ExperimentConfig()

        self.is_running = False
        self.stage = "idle"
        self.current_jar = None
        self.jar_index = 0
        self.inhales_in_cycle = 0
        self.jar_order = []

        self.cue_active = False
        self.cue_sequence_id = 0

        self.ui_event_queue = queue.Queue()

    def set_config(self, config: ExperimentConfig):
        self.config = config

    def start(self):
        self.stop_cue_sequence()

        self.is_running = True
        self.stage = "waiting"
        self.current_jar = None
        self.jar_index = 0
        self.inhales_in_cycle = 0

        num_of_experiments = self.config.num_jars * self.config.num_repetitions
        jar_order = np.random.permutation(np.arange(1, num_of_experiments + 1))
        self.jar_order = ((jar_order % self.config.num_jars) + 1).tolist()

        self._emit_instruction("waiting")
        self.clear_detection_queues()
        self.sd.inhale_detect_start()

    def stop(self):
        self.is_running = False
        self.stop_cue_sequence()
        self.sd.inhale_detect_stop()
        self.stage = "idle"
        self._emit_ui_event({"type": "status", "status": "stopped"})

    def poll(self):
        if not self.is_running:
            return

        event_queue = getattr(self.sd, "event_queue", None)
        if event_queue is None:
            return

        while True:
            try:
                event = event_queue.get_nowait()
            except queue.Empty:
                break

            event_type = event.get("type")
            if event_type == "inhale_detected":
                if self.cue_active:
                    continue
                self.inhales_in_cycle = int(event.get("count", 0))
                self._emit_instruction("inhale", count=self.inhales_in_cycle)
            elif event_type == "experiment_activated":
                if self.cue_active:
                    continue

                if self.jar_index < len(self.jar_order):
                    jar_number = int(self.jar_order[self.jar_index])
                    self.current_jar = jar_number
                    self.jar_index += 1
                    self.inhales_in_cycle = 0
                    self.start_cue_sequence(jar_number)
                else:
                    self._emit_instruction("complete")
                    self.stop()

    def drain_ui_events(self):
        events = []
        while True:
            try:
                events.append(self.ui_event_queue.get_nowait())
            except queue.Empty:
                break
        return events

    def start_cue_sequence(self, jar_number):
        self.cue_active = True
        self.cue_sequence_id += 1
        sequence_id = self.cue_sequence_id

        self.sd.inhale_detect_stop()
        self.clear_detection_queues()

        prep_sound_path = LANG_DICT.get(self.config.experiment_lang, LANG_DICT["Hebrew"])
        self._emit_instruction("prepare", jar_number=jar_number)
        self._emit_ui_event(
            {
                "type": "sound",
                "kind": "prep_then_beep",
                "prep_sound_path": prep_sound_path,
                "beep_sound_path": BEEP_SOUND_PATH,
            }
        )

        def start_present_stage():
            if (not self.is_running or sequence_id != self.cue_sequence_id):
                return
            self._emit_instruction("present", jar_number=jar_number)

        def start_cooldown_stage():
            if (not self.is_running or sequence_id != self.cue_sequence_id):
                return
            self._emit_instruction("cooldown")

        def finish_cue_sequence():
            if (not self.is_running or sequence_id != self.cue_sequence_id):
                return

            self.clear_detection_queues()
            self.sd.inhale_detect_start()
            self.cue_active = False
            self._emit_instruction("waiting")

        threading.Timer(float(self.config.prep_sound_duration_s), start_present_stage).start()
        threading.Timer(
            float(self.config.prep_sound_duration_s) + float(self.config.beep_duration_s),
            start_cooldown_stage,
        ).start()
        threading.Timer(
            float(self.config.prep_sound_duration_s)
            + float(self.config.beep_duration_s)
            + float(self.config.cooldown_time),
            finish_cue_sequence,
        ).start()

    def stop_cue_sequence(self):
        self.cue_active = False
        self.cue_sequence_id += 1

    def clear_detection_queues(self):
        self.clear_queue(self.sd.event_queue)
        self.clear_queue(self.sd.inhale_queue)

    def clear_queue(self, q):
        while True:
            try:
                q.get_nowait()
            except queue.Empty:
                break

    def _emit_instruction(self, stage, jar_number=None, count=None):
        payload = {"type": "instruction", "stage": stage}
        if jar_number is not None:
            payload["jar_number"] = int(jar_number)
        if count is not None:
            payload["count"] = int(count)
        self._emit_ui_event(payload)

    def _emit_ui_event(self, event):
        self.ui_event_queue.put(event)
