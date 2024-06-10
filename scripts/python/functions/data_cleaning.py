import pandas as pd
import numpy as np
from scipy.stats import linregress


def compute_slope(elevations):
    """Calculate the slope of the elevations using linear regression."""
    x = np.arange(len(elevations))
    slope, _, _, _, _ = linregress(x, elevations)
    return slope

def segment_stats(segment):
    """Calculate the required statistics for a given segment."""
    segment = np.array(segment)
    mean = np.mean(segment)
    median = np.median(segment)
    min_val = np.min(segment)
    max_val = np.max(segment)
    std = np.std(segment)
    slope = compute_slope(segment)
    return mean, median, min_val, max_val, std, slope

def split_and_compute_stats(parent_id, child_df):
    elevations = child_df['elevation'].values
    n = len(elevations)
    segment_size = n // 10
    stats = []

    for i in range(10):
        start_idx = i * segment_size
        if i == 9:  # Ensure the last segment includes all remaining points
            end_idx = n
        else:
            end_idx = (i + 1) * segment_size

        segment = elevations[start_idx:end_idx]
        stats.extend(segment_stats(segment))

    result = [parent_id] + stats

    columns = ['line_id']
    for i in range(1, 11):
        columns.extend([f'{i}_mean', f'{i}_median', f'{i}_min', f'{i}_max', f'{i}_std', f'{i}_slope'])

    return pd.DataFrame([result], columns=columns)
