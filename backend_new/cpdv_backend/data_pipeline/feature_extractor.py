"""
Feature Extraction Module

Feature Extraction for CPDV signals
"""

import numpy as np
from scipy.fft import fft, fftfreq
from scipy.signal import find_peaks


def extract_features(cpdv: np.ndarray, dt: float = 0.005) -> np.ndarray:
    """
    Extract feature vector from a single CPDV signal

    Args:
        cpdv: 1D CPDV time series signal (n_timesteps,)
        dt:   Sampling time step, default 0.005s (200Hz)

    Returns:
        feature_vector: 1D feature array (n_features,)
    """
    features = []

    # ── 1. Statistical Features ─────────────────────────────────────────────
    features.extend(
        [
            np.max(cpdv),           # Maximum
            np.min(cpdv),           # Minimum
            np.mean(cpdv),          # Mean
            np.std(cpdv),           # Standard deviation
            np.percentile(cpdv, 25),  # 25th percentile
            np.percentile(cpdv, 75),  # 75th percentile
            np.max(cpdv) - np.min(cpdv),  # Peak-to-peak (range)
        ]
    )

    # Skewness & Kurtosis (requires scipy)
    try:
        from scipy.stats import skew, kurtosis

        features.extend([skew(cpdv), kurtosis(cpdv)])
    except ImportError:
        features.extend([0.0, 0.0])

    # ── 2. Frequency Domain Features ─────────────────────────────────────────────
    n = len(cpdv)
    fft_vals = np.abs(fft(cpdv))[: n // 2]
    freqs = fftfreq(n, dt)[: n // 2]
    eps = 1e-8

    # Dominant frequency
    main_freq_idx = np.argmax(fft_vals)
    main_freq = freqs[main_freq_idx]
    features.append(main_freq)

    # Spectral centroid
    spectral_centroid = np.sum(freqs * fft_vals) / (np.sum(fft_vals) + eps)
    features.append(spectral_centroid)

    # Spectral bandwidth
    spectral_bandwidth = np.sqrt(
        np.sum(((freqs - spectral_centroid) ** 2) * fft_vals) / (np.sum(fft_vals) + eps)
    )
    features.append(spectral_bandwidth)

    # Energy ratio per frequency band (normalized)
    total_energy = np.sum(fft_vals) + eps
    low_band = np.sum(fft_vals[freqs < 1.0]) / total_energy        # Low frequency
    mid_band = np.sum(fft_vals[(freqs >= 1.0) & (freqs < 5.0)]) / total_energy  # Mid frequency
    high_band = np.sum(fft_vals[freqs >= 5.0]) / total_energy      # High frequency
    features.extend([low_band, mid_band, high_band])

    # ── 3. Position-Sensitive Features ──────────────────────────────────────────
    # Peak-related
    peaks, _ = find_peaks(cpdv)
    n_peaks = len(peaks)
    features.append(n_peaks)

    if n_peaks > 1:
        mean_peak_spacing = np.mean(np.diff(peaks)) * dt  # Mean peak spacing (time)
        std_peak_spacing = np.std(np.diff(peaks)) * dt
    else:
        mean_peak_spacing = 0.0
        std_peak_spacing = 0.0
    features.extend([mean_peak_spacing, std_peak_spacing])

    # Zero crossing rate
    zero_crossings = np.where(np.diff(np.sign(cpdv)))[0]
    zero_cross_rate = len(zero_crossings) / len(cpdv)
    features.append(zero_cross_rate)

    # Area under curve (total energy)
    auc = np.trapz(np.abs(cpdv), dx=dt)
    features.append(auc)

    return np.array(features, dtype=np.float64)


def extract_features_batch(X_raw: np.ndarray, dt: float = 0.005) -> np.ndarray:
    """
    Batch extract features

    Args:
        X_raw: Raw CPDV matrix (n_timesteps, n_samples)
        dt:    Sampling time step

    Returns:
        X_feat: Feature matrix (n_features, n_samples)
    """
    n_samples = X_raw.shape[1]
    feat_list = []
    for i in range(n_samples):
        feat = extract_features(X_raw[:, i], dt)
        feat_list.append(feat)
    X_feat = np.array(feat_list).T  # → (n_features, n_samples)
    return X_feat


# Feature names for visualization and debugging
FEATURE_NAMES = [
    "max",
    "min",
    "mean",
    "std",
    "q25",
    "q75",
    "range",
    "skewness",
    "kurtosis",
    "main_freq",
    "spectral_centroid",
    "spectral_bandwidth",
    "low_band_ratio",
    "mid_band_ratio",
    "high_band_ratio",
    "n_peaks",
    "mean_peak_spacing",
    "std_peak_spacing",
    "zero_cross_rate",
    "auc",
]