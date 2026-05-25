"""
Cosine similarity utilities.
Used for in-memory re-ranking and score comparison.
"""
from __future__ import annotations
import numpy as np


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors. Returns value in [-1, 1]."""
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / denom) if denom > 1e-8 else 0.0


def cosine_matrix(
    queries: list[list[float]], docs: list[list[float]]
) -> np.ndarray:
    """
    Returns shape (Q, D) cosine similarity matrix.
    queries: list of Q query vectors
    docs: list of D document vectors
    """
    Q = np.array(queries, dtype=np.float32)
    D = np.array(docs, dtype=np.float32)
    nQ = np.linalg.norm(Q, axis=1, keepdims=True)
    nD = np.linalg.norm(D, axis=1, keepdims=True)
    Q_norm = Q / (nQ + 1e-8)
    D_norm = D / (nD + 1e-8)
    return Q_norm @ D_norm.T


def top_k_indices(scores: list[float], k: int) -> list[int]:
    """Return indices of top-k scores in descending order."""
    indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    return [i for i, _ in indexed[:k]]


def max_pooled_score(matrix: np.ndarray) -> np.ndarray:
    """
    For multi-query scenarios: take max score per document across all queries.
    matrix: shape (Q, D)
    Returns: shape (D,)
    """
    return matrix.max(axis=0)
