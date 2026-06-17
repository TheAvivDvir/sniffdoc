# -*- coding: utf-8 -*-
"""
Created on Mon Jun 15 14:59:10 2026

@author: Arzi
"""
import plotly.graph_objects as go

def create_pressure_figure(buffer_size=1000, sample_rate_hz=100):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=[],
            y=[],
            mode="lines",
            name="Pressure",
        )
    )

    # Calculate max time based on buffer size and sample rate
    max_time = buffer_size / sample_rate_hz

    fig.update_layout(
        xaxis_title="Time [s]",
        yaxis_title="Pressure",
        xaxis=dict(range=[0, max_time]),
        margin=dict(l=40, r=20, t=40, b=40),
    )

    return fig

def update_pressure_figure(fig, buffer, window_size=10, is_recording=False):
    if not buffer:
        return fig

    t = [sample[0] for sample in buffer]
    pressure = [sample[1] for sample in buffer]

    # Change color based on recording state
    color = "orange" if is_recording else "blue"
    fig.data[0].line.color = color
    
    fig.data[0].x = t
    fig.data[0].y = pressure
    
    # Update x-axis range to keep a sliding window of fixed size
    if t:
        max_time = t[-1]
        min_time = max(0, max_time - window_size)
        fig.update_layout(xaxis=dict(range=[min_time, min_time + window_size]))

    return fig