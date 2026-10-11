"""CSV MATLAB e clustering radar, senza dipendenze oltre a NumPy.

Colonne: Frame, Time_s, X_m, Y_m, Velocity_mps, Azimuth_deg.
Gli ID dei cluster valgono solo all'interno del singolo frame.
"""
import csv
from collections import deque

import numpy as np


COLUMNS = ('Frame', 'Time_s', 'X_m', 'Y_m', 'Velocity_mps', 'Azimuth_deg')


def load_radar(path):
    """Raggruppa i punti per Frame; non assume l'origine della numerazione."""
    frames = {}
    with open(path, newline='', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        if not set(COLUMNS).issubset(reader.fieldnames or []):
            raise ValueError('Il CSV deve contenere: ' + ', '.join(COLUMNS))
        for line, row in enumerate(reader, start=2):
            try:
                values = [float(row[column]) for column in COLUMNS]
            except (TypeError, ValueError) as error:
                raise ValueError(f'CSV: valore non numerico alla riga {line}.') from error
            if not np.isfinite(values).all() or not values[0].is_integer():
                raise ValueError(f'CSV: valori non finiti o Frame non intero alla riga {line}.')
            frame, time, x, y, velocity, azimuth = values
            frames.setdefault(int(frame), []).append([time, x, y, velocity, azimuth])
    if not frames:
        raise ValueError('Il CSV radar è vuoto.')
    for frame, rows in frames.items():
        points = np.asarray(rows, dtype=float)
        if np.ptp(points[:, 0]) > 1e-6:
            raise ValueError(f'CSV: Time_s diversi per lo stesso Frame {frame}.')
        frames[frame] = points
    return frames


def dbscan(features, eps=0.5, min_samples=3):
    """DBSCAN euclideo: -1 rumore; il punto stesso conta nei min_samples.

    Ricerca diretta dei vicini: memoria O(N), tempo O(N²) per frame.
    Adatto a piccoli insiemi radar; non crea una matrice NxN.
    """
    if not np.isfinite(eps) or eps <= 0 or min_samples < 1:
        raise ValueError('DBSCAN richiede eps > 0 e min_samples >= 1.')
    labels = np.full(len(features), -1, dtype=int)
    visited = np.zeros(len(features), dtype=bool)

    def neighbors(index):
        delta = features - features[index]
        return np.flatnonzero(np.sum(delta * delta, axis=1) <= eps * eps)

    cluster_id = 0
    for index in range(len(features)):
        if visited[index]:
            continue
        visited[index] = True
        nearby = neighbors(index)
        if len(nearby) < min_samples:
            continue
        labels[index] = cluster_id
        queue = deque(nearby.tolist())
        queued = np.zeros(len(features), dtype=bool)
        queued[nearby] = True
        while queue:
            point = queue.popleft()
            if not visited[point]:
                visited[point] = True
                nearby = neighbors(point)
                if len(nearby) >= min_samples:
                    for candidate in nearby:
                        if not queued[candidate]:
                            queued[candidate] = True
                            queue.append(int(candidate))
            if labels[point] == -1:
                labels[point] = cluster_id
        cluster_id += 1
    return labels


def cluster_frame(points, eps=0.5, min_samples=3):
    """Riprende StandardScaler + DBSCAN dell'esempio, solo su X/Y/velocità.

    Input: righe [Time_s, X_m, Y_m, Velocity_mps, Azimuth_deg].
    Velocità e coordinate restituite nelle unità originali, non standardizzate.
    """
    if len(points) == 0:
        return []
    features = np.asarray(points, dtype=float)[:, 1:4]
    scale = features.std(axis=0)
    scale[scale == 0] = 1
    normalized = (features - features.mean(axis=0)) / scale
    labels = dbscan(normalized, eps, min_samples)
    clusters = []
    for cluster_id in sorted(set(labels) - {-1}):
        group = features[labels == cluster_id]
        mean = group.mean(axis=0)
        spread = group.std(axis=0, ddof=1) if len(group) > 1 else np.zeros(3)
        clusters.append({
            'cluster_id': int(cluster_id),
            'x_m': float(mean[0]), 'y_m': float(mean[1]),
            'velocity_mps': float(mean[2]),
            'velocity_spread_mps': float(spread[2]),
            'spatial_spread_x_m': float(spread[0]),
            'spatial_spread_y_m': float(spread[1]),
            'point_count': len(group),
        })
    return clusters
