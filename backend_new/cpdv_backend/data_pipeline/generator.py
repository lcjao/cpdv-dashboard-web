"""
Data Generation and Preprocessing Module

Data Generation Pipeline (from AGENTS.md):
- Step 1: Generate training data (single crack / multi-crack / multi-condition / feature engineering)
- CPDV = AP_damaged - AP_intact (damage state minus healthy state displacement)
"""

import numpy as np

try:
    import torch
    HAS_TORCH = True
except Exception:
    torch = None
    HAS_TORCH = False

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Use enhanced system (supports multi-crack)
from simulation.system_iteration import EnhancedBridgeVehicleSystem as BridgeVehicleSystem
SYSTEM_BACKEND = "enhanced"
HAS_MULTI_CRACKS = True


class DataGenerator:
    """
    Data Generator

    Batch generation of training data:
    - Input: CPDV sequences
    - Output: Crack position, depth
    """

    def __init__(self, params=None, seed=42):
        """
        Initialize data generator

        Args:
            params: System parameter dictionary
            seed: Random seed
        """
        self.params = params or {}
        self.seed = seed
        self.rng = np.random.RandomState(seed)

        # Default parameter ranges
        self.crack_position_range = self.params.get("crack_position_range", (0, 30))
        self.crack_depth_range = self.params.get("crack_depth_range", (0.01, 0.3))
        self.road_type = self.params.get("road_type", "a")  # Single road class

        # Multi-damage condition configs
        self.damages = self.params.get("damages", [])              # Predefined single crack damages
        self.multi_cracks = self.params.get("multi_cracks", [])    # Predefined multi-crack conditions
        self.random_damages = self.params.get("random_damages", {})  # Random generation config

        # Multi-condition mode config (Design doc §3/§4)
        self.multi_condition_ranges = self.params.get(
            "multi_condition_ranges", {}
        )  # Parameter sampling ranges
        self.MAX_CPDV_LENGTH = self.params.get(
            "MAX_CPDV_LENGTH", 5000
        )  # Fixed CPDV signal length
        self.max_cracks = self.params.get("max_cracks", 5)         # Max cracks

    def generate_sample(self, system):
        """
        Generate a single sample

        Args:
            system: BridgeVehicleSystem instance

        Returns:
            X: CPDV sequence (features)
            y: [position, depth_ratio] (labels)
        """
        # Randomly generate crack parameters
        pos = self.rng.uniform(*self.crack_position_range)
        depth = self.rng.uniform(*self.crack_depth_range)

        # Use single road class
        system.road_type = self.road_type

        # Analyze healthy state (if not already)
        if system.uc_healthy is None:
            system.run_analysis()

        # Analyze damaged state
        damaged_results = system.analyze_damage(pos, depth)

        # Calculate CPDV
        cpdv = system.calculate_cpdv(damaged_results["uc"])

        X = cpdv
        y = np.array([pos, depth])

        return X, y

    def generate_dataset_for_damage(
        self, system, position: float, depth: float, n_samples: int = 100
    ):
        """
        Generate dataset for specified damage condition

        Args:
            system: BridgeVehicleSystem instance
            position: Damage position (m)
            depth: Damage depth ratio
            n_samples: Number of samples for this condition

        Returns:
            X: CPDV data matrix
            y: Label matrix
            metadata: Metadata dictionary
        """
        X_list = []
        y_list = []

        # Pre-compute healthy state
        if system.uc_healthy is None:
            system.run_analysis()

        if system.uc_healthy is None or not np.all(np.isfinite(system.uc_healthy)):
            raise ValueError("Healthy state analysis failed")

        uc_healthy = system.uc_healthy.copy()

        for i in range(n_samples):
            # Create new system instance
            sample_system = BridgeVehicleSystem(self.params)
            sample_system.uc_healthy = uc_healthy
            sample_system.road_type = self.road_type

            try:
                # Use fixed damage parameters (position and depth fixed, variation may come from road)
                damaged_results = sample_system.analyze_damage(position, depth)
                cpdv = sample_system.calculate_cpdv(damaged_results["uc"])

                if cpdv is not None and len(cpdv) > 0 and np.all(np.isfinite(cpdv)):
                    X_list.append(cpdv)
                    y_list.append([position, depth])
            except Exception:
                continue

        if len(X_list) == 0:
            return None, None, None

        X = np.array(X_list).T
        y = np.array(y_list).T

        metadata = {
            "damage_id": f"pos{position}_depth{depth}",
            "position": position,
            "depth": depth,
            "n_samples": len(X_list),
        }

        return X, y, metadata

    def generate_multi_scenario_dataset(
        self, system, n_samples_per_scenario: int = 100
    ):
        """
        Batch generate dataset for multiple predefined damage conditions

        Args:
            system: BridgeVehicleSystem instance
            n_samples_per_scenario: Samples per condition

        Returns:
            Merged data dictionary
        """
        all_X = []
        all_y = []
        all_scenario_ids = []
        metadata_list = []

        # Use predefined damage conditions
        damages = self.damages
        if not damages:
            # If none predefined, use random generation
            n_scenarios = self.random_damages.get(
                "n_scenarios", 10
            )  # Default 10 random conditions
            for i in range(n_scenarios):
                pos = self.rng.uniform(*self.crack_position_range)
                depth = self.rng.uniform(*self.crack_depth_range)
                damages.append({"id": i + 1, "position": pos, "depth": depth})

        print(
            f"[Multi-scenario] {len(damages)} conditions, {n_samples_per_scenario} samples each"
        )

        for i, damage in enumerate(damages):
            pos = damage.get("position")
            depth = damage.get("depth")
            damage_id = damage.get("id", i + 1)

            print(f"  Condition {damage_id}: position={pos}m, depth={depth}")

            X, y, meta = self.generate_dataset_for_damage(
                system, pos, depth, n_samples_per_scenario
            )

            if X is not None:
                all_X.append(X)
                all_y.append(y)
                all_scenario_ids.extend([damage_id] * X.shape[1])
                metadata_list.append(meta)

        # ── Handle multi-crack conditions ────────────────────────────────
        if self.multi_cracks:
            mc_data = self.generate_multi_cracks_dataset(system, n_samples_per_scenario)
            if mc_data is not None:
                all_X.append(mc_data["X"])
                all_y.append(mc_data["y"])
                all_scenario_ids.extend(mc_data["scenario_ids"])
                metadata_list.extend(mc_data["metadata"])
                damages = damages + mc_data["damages"]

        if not all_X:
            raise ValueError("All condition data generation failed")

        # Merge all data
        X_merged = np.hstack(all_X)
        y_merged = np.hstack(all_y)
        scenario_ids = np.array(all_scenario_ids)

        print(f"[Multi-scenario] Merged data: X={X_merged.shape}, y={y_merged.shape}")

        return {
            "X": X_merged,
            "y": y_merged,
            "scenario_ids": scenario_ids,
            "metadata": metadata_list,
            "damages": damages,
        }

    def _pad_cpdv(self, cpdv: np.ndarray) -> np.ndarray:
        """
        Pad/truncate CPDV signal to fixed length

        Args:
            cpdv: CPDV signal (n,)

        Returns:
            padded: (MAX_CPDV_LENGTH,)
        """
        target = self.MAX_CPDV_LENGTH
        if len(cpdv) >= target:
            return cpdv[:target]
        else:
            padded = np.zeros(target)
            padded[: len(cpdv)] = cpdv
            return padded

    def _build_multi_crack_label(self, crack_list, max_cracks=None):
        """
        Build Scheme B label

        Args:
            crack_list: [(position, depth), ...]
            max_cracks: Maximum number of cracks

        Returns:
            y: (max_cracks * 2,)
        """
        if max_cracks is None:
            max_cracks = self.max_cracks
        y = np.full(max_cracks * 2, -1.0)
        crack_list = sorted(crack_list, key=lambda x: x[0])
        for j, (pos, depth) in enumerate(crack_list[:max_cracks]):
            y[j * 2] = float(pos)
            y[j * 2 + 1] = float(depth)
        return y

    def _sample_scenario_params(self):
        """
        Sample a set of parameters from multi-condition parameter space

        Returns:
            params: System parameter dictionary
        """
        ranges = self.multi_condition_ranges
        params = {}
        for key, (lo, hi) in ranges.items():
            # Ensure numeric types (YAML may parse scientific notation as strings)
            lo = float(lo)
            hi = float(hi)
            if key in ("mv", "kv", "cv", "E", "I", "m"):
                # Continuous parameters, log-uniform sampling
                log_lo, log_hi = np.log10(lo), np.log10(hi)
                params[key] = 10 ** self.rng.uniform(log_lo, log_hi)
            else:
                params[key] = self.rng.uniform(lo, hi)
        return params

    def generate_multi_cracks_dataset(self, system, n_samples_per_scenario: int = 100):
        """
        Batch generate dataset for predefined multi-crack conditions (Scheme B labels)

        Args:
            system: BridgeVehicleSystem instance (must support analyze_multi_cracks)
            n_samples_per_scenario: Samples per condition

        Returns:
            Merged data dictionary
        """
        all_X = []
        all_y = []
        all_scenario_ids = []
        metadata_list = []
        all_damages = []

        # Check if backend supports multi-crack
        if not HAS_MULTI_CRACKS:
            print("[Multi-crack] Backend does not support analyze_multi_cracks, skipping")
            return None

        # Use predefined multi-crack conditions
        multi_cracks = self.multi_cracks
        if not multi_cracks:
            print("[Multi-crack] No multi_cracks configured, skipping")
            return None

        print(
            f"[Multi-crack] {len(multi_cracks)} conditions, {n_samples_per_scenario} samples each"
        )

        # Pre-compute healthy state
        uc_healthy = system.uc_healthy.copy() if system.uc_healthy is not None else None

        for idx, damage in enumerate(multi_cracks):
            damage_id = damage.get("id", idx + 1)
            cracks = damage.get("cracks", [])

            if not cracks:
                continue

            # Parse crack list
            crack_list = [(c["position"], c["depth"]) for c in cracks]
            crack_desc = ", ".join(
                [f"pos{c['position']}@d{c['depth']}" for c in cracks]
            )
            print(f"  Condition {damage_id}: [{crack_desc}]")

            X_list = []
            y_list = []

            for i in range(n_samples_per_scenario):
                try:
                    # Create new system instance (reuse healthy state)
                    sample_system = BridgeVehicleSystem(self.params)
                    if uc_healthy is not None:
                        sample_system.uc_healthy = uc_healthy.copy()
                    sample_system.road_type = self.road_type

                    # Analyze multi-crack state
                    results = sample_system.analyze_multi_cracks(crack_list)
                    cpdv = sample_system.calculate_cpdv(results["uc"])

                    if cpdv is not None and len(cpdv) > 0 and np.all(np.isfinite(cpdv)):
                        # Pad to fixed length
                        cpdv_padded = self._pad_cpdv(cpdv)
                        X_list.append(cpdv_padded)
                        # Scheme B label
                        label = self._build_multi_crack_label(crack_list)
                        y_list.append(label)
                except Exception:
                    continue

            if X_list:
                all_X.append(np.array(X_list).T)
                all_y.append(np.array(y_list).T)
                all_scenario_ids.extend([damage_id] * len(X_list))
                metadata_list.append(
                    {
                        "damage_id": damage_id,
                        "cracks": crack_list,
                        "n_samples": len(X_list),
                    }
                )
                all_damages.append(damage)

        if not all_X:
            raise ValueError("All multi-crack condition data generation failed")

        # Merge all data
        X_merged = np.hstack(all_X)
        y_merged = np.hstack(all_y)
        scenario_ids = np.array(all_scenario_ids)

        print(f"[Multi-crack] Merged data: X={X_merged.shape}, y={y_merged.shape}")

        return {
            "X": X_merged,
            "y": y_merged,
            "scenario_ids": scenario_ids,
            "metadata": metadata_list,
            "damages": all_damages,
            "mode": "multi_cracks",
        }

    def generate_multi_condition_dataset(
        self,
        n_scenarios: int = 50,
        n_samples_per_scenario: int = 100,
        system_params: dict = None,
    ):
        """
        Generate multi-condition random data (Design doc core feature)

        Each scenario randomly samples vehicle/bridge parameters and random multi-cracks,
        generates Scheme B label data.

        Args:
            n_scenarios: Number of scenarios
            n_samples_per_scenario: Samples per scenario
            system_params: Base system parameters (overridden by sampled params)

        Returns:
            Data dictionary
        """
        all_X = []
        all_y = []
        all_scenario_ids = []
        metadata_list = []

        base_params = (system_params or self.params).copy() if self.params else {}

        print(f"[Multi-condition] Generating {n_scenarios} random scenarios, {n_samples_per_scenario} samples each")

        for sc_idx in range(n_scenarios):
            # 1) Sample random parameters
            sampled = self._sample_scenario_params() if self.multi_condition_ranges else {}

            # Merge into parameters
            sc_params = base_params.copy()
            sc_params.update(sampled)

            # Ensure required keys exist
            for k in ("mv", "kv", "cv", "V", "L", "E", "I", "m"):
                if k not in sc_params:
                    sc_params[k] = sc_params.get(k, 5000 if k == "mv" else 100000)

            # 2) Create system and run healthy analysis
            try:
                sc_system = BridgeVehicleSystem(sc_params)
                sc_system.road_type = self.road_type
                sc_system.run_analysis()
            except Exception as e:
                print(f"    Scenario {sc_idx} healthy analysis failed: {e}")
                continue

            if sc_system.uc_healthy is None:
                print(f"    Scenario {sc_idx} healthy analysis invalid, skipping")
                continue

            uc_healthy = sc_system.uc_healthy.copy()
            L = sc_params.get("L", 30)

            # 3) Generate random multi-cracks
            crack_list_raw = self._generate_random_multi_cracks_internal(
                n_scenarios=1, L=L
            )
            if not crack_list_raw:
                continue
            crack_info = crack_list_raw[0]["cracks"]
            crack_list = [(c["position"], c["depth"]) for c in crack_info]

            crack_desc = ", ".join([f"pos{p:.1f}@d{d:.2f}" for p, d in crack_list])
            param_desc = f"L={sc_params.get('L'):.1f} V={sc_params.get('V'):.1f} mv={sc_params.get('mv'):.0f}"
            print(f"  Scenario {sc_idx}: {param_desc} cracks: [{crack_desc}]")

            # 4) Generate samples
            X_list = []
            y_list = []

            for s in range(n_samples_per_scenario):
                try:
                    sample_sys = BridgeVehicleSystem(sc_params)
                    sample_sys.uc_healthy = uc_healthy.copy()
                    sample_sys.road_type = self.road_type

                    results = sample_sys.analyze_multi_cracks(crack_list)
                    cpdv = sample_sys.calculate_cpdv(results["uc"])

                    if cpdv is not None and len(cpdv) > 0 and np.all(np.isfinite(cpdv)):
                        cpdv_padded = self._pad_cpdv(cpdv)
                        X_list.append(cpdv_padded)
                        label = self._build_multi_crack_label(crack_list)
                        y_list.append(label)
                except Exception:
                    continue

            if X_list:
                all_X.append(np.array(X_list).T)
                all_y.append(np.array(y_list).T)
                all_scenario_ids.extend([sc_idx] * len(X_list))
                metadata_list.append(
                    {
                        "scenario_id": sc_idx,
                        "params": {k: float(v) if isinstance(v, (int, float)) else v
                                   for k, v in sc_params.items()
                                   if k in ("mv", "kv", "cv", "V", "L", "E", "I", "m")},
                        "cracks": crack_list,
                        "n_samples": len(X_list),
                    }
                )

        if not all_X:
            raise ValueError("All multi-condition data generation failed")

        X_merged = np.hstack(all_X)
        y_merged = np.hstack(all_y)
        scenario_ids = np.array(all_scenario_ids)

        print(f"[Multi-condition] Merged data: X={X_merged.shape}, y={y_merged.shape}")

        return {
            "X": X_merged,
            "y": y_merged,
            "scenario_ids": scenario_ids,
            "metadata": metadata_list,
            "mode": "multi_condition",
        }

    def _generate_random_multi_cracks_internal(
        self, n_scenarios: int = 1, L: float = 30.0
    ):
        """
        Internal random multi-crack generation

        Args:
            n_scenarios: Number of scenarios
            L: Bridge length

        Returns:
            scenarios: [{"id": ..., "cracks": [...]}, ...]
        """
        max_cracks = self.max_cracks
        min_distance = self.params.get("min_crack_distance", 1.0)
        depth_range = self.params.get("multi_crack_depth_range", self.crack_depth_range)

        max_possible = max(2, int(L / min_distance))
        effective_max = min(max_cracks, max_possible)

        result = []
        for i in range(n_scenarios):
            n_cracks = self.rng.randint(2, effective_max + 1)
            positions = []
            for _ in range(500):
                pos = self.rng.uniform(0, L)
                if all(abs(pos - p) >= min_distance for p in positions):
                    positions.append(pos)
                if len(positions) >= n_cracks:
                    break
            if len(positions) < 2:
                continue
            cracks = [
                {"position": round(pos, 4), "depth": round(float(self.rng.uniform(*depth_range)), 4)}
                for pos in positions
            ]
            result.append({"id": 1000 + i, "cracks": cracks})
        return result

    def _generate_multi_scenario_wrapper(
        self, system_params, road_type, n_samples_per_scenario
    ):
        """Multi-scenario mode wrapper"""
        if road_type is None:
            road_type = self.road_type

        # Create base system
        base_system = BridgeVehicleSystem(system_params)
        base_system.road_type = road_type

        # Pre-compute healthy state
        print("Computing healthy state baseline...")
        base_system.run_analysis()

        if base_system.uc_healthy is None or not np.all(
            np.isfinite(base_system.uc_healthy)
        ):
            raise ValueError("Healthy state analysis failed")

        # Call multi-scenario generation
        return self.generate_multi_scenario_dataset(base_system, n_samples_per_scenario)

    def generate_dataset(
        self,
        n_samples,
        system_params=None,
        road_type=None,
        multi_scenario=False,
        n_samples_per_scenario=100,
        multi_condition=False,
        n_scenarios=50,
    ):
        """
        Batch generate dataset

        Args:
            n_samples: Sample count (ignored in multi_condition mode)
            system_params: System parameter dictionary
            road_type: Road class, if None use config value
            multi_scenario: Whether to use multi-scenario mode (predefined damages)
            n_samples_per_scenario: Samples per scenario in multi-scenario mode
            multi_condition: Whether to use multi-condition random generation mode
            n_scenarios: Number of scenarios in multi-condition mode

        Returns:
            X: CPDV data matrix (n_features, n_samples)
            y: Label matrix
            Mode-specific additional info
        """
        # Multi-condition random generation mode (Design doc core feature)
        if multi_condition:
            return self.generate_multi_condition_dataset(
                n_scenarios=n_scenarios,
                n_samples_per_scenario=n_samples_per_scenario,
                system_params=system_params,
            )

        # Multi-scenario mode (predefined damages)
        if multi_scenario:
            return self._generate_multi_scenario_wrapper(
                system_params, road_type, n_samples_per_scenario
            )

        X_list = []
        y_list = []

        # If road type not specified, use configured single road class
        if road_type is None:
            road_type = self.road_type

        print(f"Using road class: {road_type}")

        # Create base system instance for healthy state analysis
        base_system = BridgeVehicleSystem(system_params)
        base_system.road_type = road_type

        # Pre-compute healthy state
        print("Computing healthy state baseline...")
        base_system.run_analysis()

        if base_system.uc_healthy is None or not np.all(
            np.isfinite(base_system.uc_healthy)
        ):
            raise ValueError("Healthy state analysis failed")

        uc_healthy = base_system.uc_healthy.copy()

        print(f"Generating {n_samples} samples...")
        for i in range(n_samples):
            if (i + 1) % 500 == 0:
                print(f"  Completed {i + 1}/{n_samples}")

            # Create new system instance for each sample
            system = BridgeVehicleSystem(system_params)
            system.uc_healthy = uc_healthy
            system.road_type = road_type  # Use same road class

            # Randomly generate crack parameters
            pos = self.rng.uniform(*self.crack_position_range)
            depth = self.rng.uniform(*self.crack_depth_range)

            try:
                # Analyze damaged state
                damaged_results = system.analyze_damage(pos, depth)

                # Calculate CPDV
                cpdv = system.calculate_cpdv(damaged_results["uc"])

                # Check CPDV validity
                if cpdv is not None and len(cpdv) > 0 and np.all(np.isfinite(cpdv)):
                    X_list.append(cpdv)
                    y_list.append([pos, depth])
                else:
                    # Invalid data, skip
                    continue
            except Exception as e:
                # Error occurred, skip sample
                continue

        X = np.array(X_list).T  # Transpose to (n_features, n_samples)
        y = np.array(y_list).T  # Transpose to (2, n_samples)

        print(f"Data generation complete - X: {X.shape}, y: {y.shape}")

        return X, y


class DataProcessor:
    """
    Data Preprocessor

    Functions:
    - Dataset splitting (train/val/test)
    - Normalization/standardization
    - Data statistics
    """

    def __init__(self, train_ratio=0.7, val_ratio=0.15, seed=42):
        """
        Initialize data processor

        Args:
            train_ratio: Training set ratio
            val_ratio: Validation set ratio
            seed: Random seed
        """
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = 1.0 - train_ratio - val_ratio
        self.seed = seed
        self.rng = np.random.RandomState(seed)

        # Normalization statistics
        self.X_mean = None
        self.X_std = None
        self.y_mean = None
        self.y_std = None

    def split_data(self, X, y):
        """
        Split dataset

        Args:
            X: Feature matrix (n_features, n_samples)
            y: Label matrix (2, n_samples)

        Returns:
            Split data dictionary
        """
        n = X.shape[1]
        indices = self.rng.permutation(n)

        train_split = int(n * self.train_ratio)
        val_split = int(n * (self.train_ratio + self.val_ratio))

        train_idx = indices[:train_split]
        val_idx = indices[train_split:val_split]
        test_idx = indices[val_split:]

        data = {
            "X_train": X[:, train_idx],
            "y_train": y[:, train_idx],
            "X_val": X[:, val_idx],
            "y_val": y[:, val_idx],
            "X_test": X[:, test_idx],
            "y_test": y[:, test_idx],
        }

        print(f"Dataset split:")
        print(f"  Train: {data['X_train'].shape[1]} samples")
        print(f"  Val: {data['X_val'].shape[1]} samples")
        print(f"  Test: {data['X_test'].shape[1]} samples")

        return data

    def normalize(self, X, y, fit=True):
        """
        Standardize data

        Multi-crack labels (Scheme B) have padding positions at -1.0,
        statistics automatically ignore these when computing.

        Args:
            X: Feature matrix
            y: Label matrix
            fit: Whether to fit statistics (training mode)

        Returns:
            Standardized X, y, statistics dictionary
        """
        if fit:
            self.X_mean = np.mean(X, axis=1, keepdims=True)
            self.X_std = np.std(X, axis=1, keepdims=True) + 1e-8

            # For labels, ignore padding positions (-1.0) when computing statistics
            self.y_mean = np.zeros((y.shape[0], 1))
            self.y_std = np.ones((y.shape[0], 1))
            for i in range(y.shape[0]):
                valid_mask = y[i, :] >= 0
                if valid_mask.sum() > 0:
                    self.y_mean[i, 0] = np.mean(y[i, valid_mask])
                    self.y_std[i, 0] = np.std(y[i, valid_mask]) + 1e-8
                else:
                    self.y_mean[i, 0] = 0.0
                    self.y_std[i, 0] = 1.0

        X_norm = (X - self.X_mean) / self.X_std
        y_norm = (y - self.y_mean) / self.y_std

        stats = {
            "X_mean": self.X_mean,
            "X_std": self.X_std,
            "y_mean": self.y_mean,
            "y_std": self.y_std,
        }

        return X_norm, y_norm, stats

    def normalize_with_stats(self, X, y, stats):
        """
        Standardize data using given statistics

        Args:
            X: Feature matrix
            y: Label matrix
            stats: Statistics dictionary

        Returns:
            Standardized X, y
        """
        X_norm = (X - stats["X_mean"]) / stats["X_std"]
        y_norm = (y - stats["y_mean"]) / stats["y_std"]
        return X_norm, y_norm

    def denormalize(self, y_norm, stats):
        """
        Denormalize

        Args:
            y_norm: Normalized labels
            stats: Statistics dictionary

        Returns:
            Original scale labels
        """
        return y_norm * stats["y_std"] + stats["y_mean"]

    def compute_statistics(self, X, y):
        """
        Compute data statistics

        Args:
            X: Feature matrix
            y: Label matrix

        Returns:
            Statistics dictionary
        """
        stats = {
            "X_shape": X.shape,
            "y_shape": y.shape,
            "X_min": np.min(X, axis=1),
            "X_max": np.max(X, axis=1),
            "X_mean": np.mean(X, axis=1),
            "X_std": np.std(X, axis=1),
            "y_position_min": np.min(y[0, :]),
            "y_position_max": np.max(y[0, :]),
            "y_depth_min": np.min(y[1, :]),
            "y_depth_max": np.max(y[1, :]),
        }
        return stats


class DataPipeline:
    """
    Complete Data Pipeline

    Integrates data generation, splitting, and preprocessing
    """

    def __init__(
        self,
        system_params=None,
        n_samples=10000,
        train_ratio=0.7,
        val_ratio=0.15,
        seed=42,
        road_type=None,
        multi_scenario=False,
        n_samples_per_scenario=100,
        use_feature_engineering=False,
        combine_with_raw=False,
        multi_condition=False,
        n_scenarios=50,
    ):
        """
        Initialize data pipeline

        Args:
            system_params: System parameters
            n_samples: Sample count
            train_ratio: Training set ratio
            val_ratio: Validation set ratio
            seed: Random seed
            road_type: Road class
            multi_scenario: Whether to use multi-scenario mode (predefined damages)
            n_samples_per_scenario: Samples per scenario
            use_feature_engineering: Whether to enable feature engineering
            combine_with_raw: Concatenate features + raw
            multi_condition: Whether to use multi-condition random generation mode
            n_scenarios: Number of scenarios in multi-condition mode
        """
        self.system_params = system_params
        self.n_samples = n_samples
        self.seed = seed
        self.road_type = road_type
        self.multi_scenario = multi_scenario
        self.multi_condition = multi_condition
        self.n_samples_per_scenario = n_samples_per_scenario
        self.n_scenarios = n_scenarios
        self.use_feature_engineering = use_feature_engineering
        self.combine_with_raw = combine_with_raw

        self.generator = DataGenerator(system_params, seed)
        self.processor = DataProcessor(train_ratio, val_ratio, seed)

        self.raw_data = None
        self.processed_data = None
        self.stats = None

    def run(self, verbose=True):
        """
        Run complete data pipeline

        Returns:
            Processed data dictionary
        """
        # Generate data
        if verbose:
            print("=" * 50)
            print("Step 1: Generate Data")
            print("=" * 50)

        # Multi-condition random generation mode
        if self.multi_condition:
            multi_data = self.generator.generate_dataset(
                self.n_samples,
                self.system_params,
                self.road_type,
                multi_condition=True,
                n_samples_per_scenario=self.n_samples_per_scenario,
                n_scenarios=self.n_scenarios,
            )

            X = multi_data["X"]
            y = multi_data["y"]
            self.raw_data = {
                "scenario_ids": multi_data["scenario_ids"],
                "metadata": multi_data["metadata"],
                "mode": "multi_condition",
            }
        # Multi-scenario mode (predefined damages)
        elif self.multi_scenario:
            multi_data = self.generator.generate_dataset(
                self.n_samples,
                self.system_params,
                self.road_type,
                multi_scenario=True,
                n_samples_per_scenario=self.n_samples_per_scenario,
            )

            X = multi_data["X"]
            y = multi_data["y"]
            self.raw_data = {
                "scenario_ids": multi_data["scenario_ids"],
                "damages": multi_data["damages"],
                "metadata": multi_data["metadata"],
            }
        else:
            X, y = self.generator.generate_dataset(
                self.n_samples, self.system_params, self.road_type
            )

        # ── Step 1.5: Feature Extraction (optional) ──────────────────────────────────
        if self.use_feature_engineering:
            if verbose:
                print("\n" + "=" * 50)
                print("Step 1.5: Feature Engineering")
                print("=" * 50)
            dt = self.system_params.get("dt", 0.005) if self.system_params else 0.005
            from .feature_extractor import extract_features_batch
            X_feat = extract_features_batch(X, dt)

            if self.combine_with_raw:
                # Scheme B: features + raw concatenation
                X = np.vstack([X, X_feat])
                if verbose:
                    print(f"Features concatenated: X_feat={X_feat.shape} → merged X={X.shape}")
            else:
                # Scheme A: features only
                X = X_feat
                if verbose:
                    print(f"Replaced with feature matrix: X={X.shape}")

        # Split dataset
        if verbose:
            print("\n" + "=" * 50)
            print("Step 2: Split Dataset")
            print("=" * 50)

        data = self.processor.split_data(X, y)

        # Save raw y (for inference/training to correctly identify padding -1)
        self.raw_y_test = data["y_test"].copy()
        self.raw_y_val = data["y_val"].copy()

        # Standardize
        if verbose:
            print("\n" + "=" * 50)
            print("Step 3: Data Standardization")
            print("=" * 50)

        X_train_norm, y_train_norm, stats = self.processor.normalize(
            data["X_train"], data["y_train"], fit=True
        )
        X_val_norm, y_val_norm = self.processor.normalize_with_stats(
            data["X_val"], data["y_val"], stats
        )
        X_test_norm, y_test_norm = self.processor.normalize_with_stats(
            data["X_test"], data["y_test"], stats
        )

        self.stats = stats
        self.processed_data = {
            "X_train": X_train_norm,
            "y_train": y_train_norm,
            "X_val": X_val_norm,
            "y_val": y_val_norm,
            "X_test": X_test_norm,
            "y_test": y_test_norm,
            "stats": stats,
        }

        if verbose:
            print(f"Feature statistics:")
            print(
                f"  X_mean range: [{stats['X_mean'].min():.6f}, {stats['X_mean'].max():.6f}]"
            )
            print(
                f"  X_std range: [{stats['X_std'].min():.6f}, {stats['X_std'].max():.6f}]"
            )
            print(f"  y_mean: {stats['y_mean'].flatten()}")
            print(f"  y_std: {stats['y_std'].flatten()}")

        return self.processed_data

    def save(self, filepath):
        """
        Save processed data

        Args:
            filepath: Training data save path (other files auto-saved in same directory)
        """
        # Ensure output directory exists
        output_dir = os.path.dirname(filepath)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Save training data (preserve original format)
        save_kwargs = {
            "X_train": self.processed_data["X_train"],
            "y_train": self.processed_data["y_train"],
            "X_val": self.processed_data["X_val"],
            "y_val": self.processed_data["y_val"],
            "X_test": self.processed_data["X_test"],
            "y_test": self.processed_data["y_test"],
            "X_mean": self.stats["X_mean"],
            "X_std": self.stats["X_std"],
            "y_mean": self.stats["y_mean"],
            "y_std": self.stats["y_std"],
        }

        # Multi-scenario mode: additional condition info
        if hasattr(self, "raw_data") and self.raw_data:
            save_kwargs["scenario_ids"] = self.raw_data.get(
                "scenario_ids", np.array([])
            )
            if "damages" in self.raw_data:
                save_kwargs["damages"] = str(self.raw_data.get("damages", []))
            if "mode" in self.raw_data:
                save_kwargs["mode"] = self.raw_data["mode"]
            if self.raw_data.get("metadata"):
                import json
                save_kwargs["metadata"] = str(self.raw_data["metadata"])

        np.savez(filepath, **save_kwargs)
        print(f"Training data saved to: {filepath}")

        # Save test data
        test_path = os.path.join(output_dir, "test_data.npz")
        np.savez(
            test_path,
            X_test=self.processed_data["X_test"],
            y_test=self.processed_data["y_test"],
            y_test_raw=self.raw_y_test if hasattr(self, 'raw_y_test') else self.processed_data["y_test"],
            X_mean=self.stats["X_mean"],
            X_std=self.stats["X_std"],
            y_mean=self.stats["y_mean"],
            y_std=self.stats["y_std"],
        )
        print(f"Test data saved to: {test_path}")

        # Save validation data
        verify_path = os.path.join(output_dir, "verify_data.npz")
        np.savez(
            verify_path,
            X_val=self.processed_data["X_val"],
            y_val=self.processed_data["y_val"],
            y_val_raw=self.raw_y_val if hasattr(self, 'raw_y_val') else self.processed_data["y_val"],
            X_mean=self.stats["X_mean"],
            X_std=self.stats["X_std"],
            y_mean=self.stats["y_mean"],
            y_std=self.stats["y_std"],
        )
        print(f"Validation data saved to: {verify_path}")

    def load(self, filepath):
        """
        Load preprocessed data

        Args:
            filepath: Data file path

        Returns:
            Processed data dictionary
        """
        data = np.load(filepath)

        self.processed_data = {
            "X_train": data["X_train"],
            "y_train": data["y_train"],
            "X_val": data["X_val"],
            "y_val": data["y_val"],
            "X_test": data["X_test"],
            "y_test": data["y_test"],
        }

        self.stats = {
            "X_mean": data["X_mean"],
            "X_std": data["X_std"],
            "y_mean": data["y_mean"],
            "y_std": data["y_std"],
        }

        print(f"Data loaded from {filepath}")

        return self.processed_data, self.stats