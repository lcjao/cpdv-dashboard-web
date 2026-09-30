"""
Data Pipeline Module for CPDV Backend.

This module provides:
- DataGenerator: Batch generation of training data (CPDV signals -> crack position/depth)
- DataProcessor: Data preprocessing (split, normalize, statistics)
- DataPipeline: Complete data pipeline integrating generation and preprocessing

Pipeline stages (from AGENTS.md):
1. Data Generation (scripts/01_generate_data.py)
2. Feature Engineering (optional, 20-dim features)
"""

from .generator import DataGenerator, DataProcessor, DataPipeline
from .feature_extractor import extract_features, extract_features_batch, FEATURE_NAMES

__all__ = [
    "DataGenerator",
    "DataProcessor",
    "DataPipeline",
    "extract_features",
    "extract_features_batch",
    "FEATURE_NAMES",
]