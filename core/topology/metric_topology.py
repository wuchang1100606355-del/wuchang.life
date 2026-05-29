# 五常智慧雲 度規總拓樸核心
import hashlib

def _h(x: str) -> float:
    return int(hashlib.sha256(str(x).encode()).hexdigest()[:8], 16) / 16**8

def compute_metric_tensor(nodes):
    nodes = list(nodes)
    n = len(nodes)
    g = [[0.0 for _ in range(n)] for _ in range(n)]
    for i, node in enumerate(nodes):
        g[i][i] = _h(node)
    for i in range(n):
        for j in range(i + 1, n):
            g[i][j] = g[j][i] = _h(nodes[i] + "<->" + nodes[j])
    return {
        "topology_version": "Wuchang-Metric-Topology-v1",
        "nodes": nodes,
        "metric_tensor": g
    }
