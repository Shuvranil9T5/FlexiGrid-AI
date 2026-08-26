import numpy as np
from sklearn.cluster import DBSCAN


def cluster_start_events(starts: list[dict], eps: float = 0.55, min_samples: int = 2) -> dict[int, list[dict]]:
    """Cluster recurring START events using circular time and normalized power."""
    if len(starts) < min_samples:
        return {}
    powers = np.asarray([event["change_kw"] for event in starts], dtype=float)
    slots = np.asarray([event["slot"] for event in starts], dtype=float)
    scale = max(float(np.median(np.abs(powers))), 0.5)
    features = np.column_stack((np.sin(2*np.pi*slots/96), np.cos(2*np.pi*slots/96), powers/scale))
    labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(features)
    groups: dict[int, list[dict]] = {}
    for label, event in zip(labels, starts):
        if label >= 0:
            groups.setdefault(int(label), []).append(event)
    return groups
