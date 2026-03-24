from __future__ import annotations

from functools import lru_cache
from typing import List

import numpy as np


def _clamp01(value: float) -> float:
    return float(max(0.0, min(1.0, value)))


def _normalize_self_confidence(self_confidence: float) -> float:
    return _clamp01(float(self_confidence))


def _normalize_face_list(face_confidence_per_question: List[float]) -> List[float]:
    normalized = []
    for value in face_confidence_per_question:
        normalized.append(_clamp01(float(value)))
    return normalized


def _feature_vector(self_confidence: float, face_confidence_per_question: List[float]) -> np.ndarray:
    self_n = _normalize_self_confidence(self_confidence)
    faces = _normalize_face_list(face_confidence_per_question)

    if not faces:
        faces = [self_n]

    arr = np.array(faces, dtype=np.float32)
    features = np.array(
        [
            self_n,
            float(np.mean(arr)),
            float(np.std(arr)),
            float(np.min(arr)),
            float(np.max(arr)),
            float(arr[-1]),
            float(len(arr)) / 50.0,
        ],
        dtype=np.float32,
    )
    return features


def _generate_synthetic_training_data(n_samples: int = 3000, seed: int = 42):
    rng = np.random.default_rng(seed)

    X = []
    y = []

    for _ in range(n_samples):
        n_questions = int(rng.integers(5, 31))
        self_n = float(rng.uniform(0, 1))

        # Face confidence centered around self confidence with some variation
        faces = np.clip(
            rng.normal(loc=self_n, scale=float(rng.uniform(0.06, 0.22)), size=n_questions),
            0,
            1,
        )

        # Target "true confidence": weighted blend penalized by inconsistency
        face_mean = float(np.mean(faces))
        face_std = float(np.std(faces))
        target = (0.58 * self_n) + (0.42 * face_mean) - (0.12 * face_std)
        target = _clamp01(target)

        features = _feature_vector(self_n, faces.tolist())
        X.append(features)
        y.append(target)

    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _train_numpy_mlp(X: np.ndarray, y: np.ndarray, seed: int = 42):
    """Train a tiny 1-hidden-layer neural network regressor using NumPy only."""
    rng = np.random.default_rng(seed)
    n_samples, in_dim = X.shape
    hidden_dim = 16

    # Xavier-like init
    W1 = rng.normal(0, np.sqrt(1 / in_dim), size=(in_dim, hidden_dim)).astype(np.float32)
    b1 = np.zeros((1, hidden_dim), dtype=np.float32)
    W2 = rng.normal(0, np.sqrt(1 / hidden_dim), size=(hidden_dim, 1)).astype(np.float32)
    b2 = np.zeros((1, 1), dtype=np.float32)

    y = y.reshape(-1, 1).astype(np.float32)
    lr = 0.03
    epochs = 700

    for _ in range(epochs):
        # Forward
        z1 = X @ W1 + b1
        a1 = np.tanh(z1)
        z2 = a1 @ W2 + b2
        y_hat = _sigmoid(z2)

        # MSE loss gradient
        dL_dyhat = (2.0 / n_samples) * (y_hat - y)
        dyhat_dz2 = y_hat * (1.0 - y_hat)
        dL_dz2 = dL_dyhat * dyhat_dz2

        dW2 = a1.T @ dL_dz2
        db2 = np.sum(dL_dz2, axis=0, keepdims=True)

        dL_da1 = dL_dz2 @ W2.T
        da1_dz1 = 1.0 - (a1 ** 2)
        dL_dz1 = dL_da1 * da1_dz1

        dW1 = X.T @ dL_dz1
        db1 = np.sum(dL_dz1, axis=0, keepdims=True)

        # Update
        W1 -= lr * dW1
        b1 -= lr * db1
        W2 -= lr * dW2
        b2 -= lr * db2

    return {
        "W1": W1,
        "b1": b1,
        "W2": W2,
        "b2": b2,
    }


def _predict_numpy_mlp(model: dict, X: np.ndarray) -> np.ndarray:
    z1 = X @ model["W1"] + model["b1"]
    a1 = np.tanh(z1)
    z2 = a1 @ model["W2"] + model["b2"]
    return _sigmoid(z2)


@lru_cache(maxsize=1)
def _get_model() -> dict:
    X, y = _generate_synthetic_training_data()
    return _train_numpy_mlp(X, y)


def predict_true_confidence(self_confidence: float, face_confidence_per_question: List[float]) -> dict:
    model = _get_model()
    features = _feature_vector(self_confidence, face_confidence_per_question).reshape(1, -1)
    pred = float(_predict_numpy_mlp(model, features)[0, 0])
    pred = _clamp01(pred)

    return {
        "true_confidence_normalized": round(pred, 4),
        "true_confidence": round(pred * 100.0, 2),
        "input_summary": {
            "self_confidence_normalized": round(_normalize_self_confidence(self_confidence), 4),
            "questions_count": len(face_confidence_per_question),
        },
        "model": "numpy_mlp_regressor",
    }
