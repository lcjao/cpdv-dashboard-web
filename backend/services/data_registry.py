"""
DataRegistry - Unified data access layer for all pipeline artifacts
Provides structured access to dashboard_summary.json, dashboard_data.js, NPZ files, etc.
"""
import json
import re
import numpy as np
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import config


class DataRegistry:
    """Unified data access for all pipeline outputs"""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_ttl: Dict[str, float] = {}
        self._default_ttl = 30.0  # seconds
    
    # ─────────────────────────────────────────────────────────────────────
    # Core Artifact Loading
    # ─────────────────────────────────────────────────────────────────────
    
    def load_dashboard_summary(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Load dashboard_summary.json - aggregated model metrics"""
        return self._load_json_artifact(
            config.DATA_DIR / "dashboard_summary.json",
            "dashboard_summary",
            force_refresh,
            default={"meta": {}, "bridges": {}}
        )
    
    def load_dashboard_data(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Load dashboard_data.js from legacy prototype"""
        return self._load_dashboard_data(force_refresh)
    
    def load_cpdv_signals(
        self,
        depth: float = 0.2,
        positions: Optional[List[float]] = None,
        downsample: int = 400,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Load or compute CPDV time series signals"""
        cache_key = f"cpdv_signals_d{depth}_ds{downsample}"
        cached = self._get_cached(cache_key, force_refresh)
        if cached is not None:
            return cached
        
        # Try to load from existing analysis outputs
        # If not available, compute from simulation
        result = self._compute_cpdv_signals(depth, positions, downsample)
        self._set_cache(cache_key, result)
        return result
    
    def load_peak_analysis(
        self,
        depths: Optional[List[float]] = None,
        distances: Optional[List[float]] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Load peak vs position/depth analysis"""
        cache_key = f"peak_analysis_d{depths}_dist{distances}"
        cached = self._get_cached(cache_key, force_refresh)
        if cached is not None:
            return cached
        
        result = self._compute_peak_analysis(depths, distances)
        self._set_cache(cache_key, result)
        return result
    
    def load_cv_analysis(
        self,
        n_samples: int = 50,
        crack_pos: float = 15.0,
        crack_depth: float = 0.2,
        mode: str = "single",
        positions: Optional[List[float]] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Load CV (coefficient of variation) analysis"""
        cache_key = f"cv_analysis_n{n_samples}_p{crack_pos}_d{crack_depth}_m{mode}"
        cached = self._get_cached(cache_key, force_refresh)
        if cached is not None:
            return cached
        
        result = self._compute_cv_analysis(n_samples, crack_pos, crack_depth, mode, positions)
        self._set_cache(cache_key, result)
        return result
    
    def load_model_metrics(
        self,
        model_type: Optional[str] = None,
        bridge_id: Optional[str] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Load model metrics from dashboard_summary or registry"""
        summary = self.load_dashboard_summary(force_refresh)
        
        if model_type and bridge_id:
            # Filter for specific model and bridge
            bridges = summary.get("bridges", {})
            bridge_data = bridges.get(bridge_id, {})
            models = bridge_data.get("models", {})
            return models.get(model_type, {})
        
        # Return all model metrics
        result = {}
        for bid, bdata in summary.get("bridges", {}).items():
            if bridge_id and bid != bridge_id:
                continue
            for mtype, metrics in bdata.get("models", {}).items():
                if model_type and mtype != model_type:
                    continue
                key = f"{bid}.{mtype}"
                result[key] = metrics
        return result
    
    def load_multi_crack_predictions(
        self,
        bridge_id: Optional[str] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Load multi-crack prediction results from export_dashboard_data output"""
        data = self.load_dashboard_data(force_refresh)
        bridges = data.get("bridges", [])
        
        if bridge_id:
            for b in bridges:
                if b.get("id") == bridge_id:
                    return b
            return {}
        
        return {"bridges": bridges, "meta": data.get("meta", {})}
    
    def load_training_history(
        self,
        model_type: Optional[str] = None,
        limit: int = 50,
        force_refresh: bool = False
    ) -> List[Dict[str, Any]]:
        """Load training history from records.jsonl"""
        from data_loader import load_records
        records = load_records(action="train", limit=limit)
        if model_type:
            records = [r for r in records if r.get("params", {}).get("model_type") == model_type]
        return records
    
    def load_road_profiles(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Load road profile data (ABC classes)"""
        cache_key = "road_profiles"
        cached = self._get_cached(cache_key, force_refresh)
        if cached is not None:
            return cached
        
        # Load from generated charts or compute
        result = {
            "road_types": ["a", "b", "c"],
            "profiles": {},
            "chart_path": str(config.OUTPUTS_DIR / "figures" / "cpdv" / "road_profile_ABC.png")
        }
        self._set_cache(cache_key, result)
        return result
    
    def load_error_distribution(
        self,
        model_type: str = "multi_crack_dual",
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Load error distribution data for model"""
        cache_key = f"error_distribution_{model_type}"
        cached = self._get_cached(cache_key, force_refresh)
        if cached is not None:
            return cached
        
        # Load from registry or dashboard data
        data = self.load_dashboard_data(force_refresh)
        # Extract error metrics from bridges
        errors = []
        for b in data.get("bridges", []):
            for pred in b.get("pred_cracks", []):
                if pred.get("hit") and pred.get("match") is not None:
                    true_cracks = b.get("true_cracks", [])
                    match_idx = pred["match"]
                    if match_idx < len(true_cracks):
                        true_crack = true_cracks[match_idx]
                        errors.append({
                            "pos_error": abs(pred["pos"] - true_crack["pos"]),
                            "depth_error": abs(pred["depth"] - true_crack["depth"])
                        })
        
        result = {
            "errors": errors,
            "model_type": model_type,
            "chart_path": str(config.OUTPUTS_DIR / "figures" / "cpdv" / "dual_head_error_distribution.png")
        }
        self._set_cache(cache_key, result)
        return result
    
    # ─────────────────────────────────────────────────────────────────────
    # Internal Computation Methods (fallback when artifacts don't exist)
    # ─────────────────────────────────────────────────────────────────────
    
    def _compute_cpdv_signals(
        self,
        depth: float,
        positions: Optional[List[float]],
        downsample: int
    ) -> Dict[str, Any]:
        """Compute CPDV signals using simulation"""
        # Import simulation dynamically
        sys.path.insert(0, str(config.pipeline_cwd("cpdv")))
        from simulation.system_coupling import BridgeVehicleSystem
        
        default_positions = [5, 7.5, 10, 12.5, 15, 17.5, 20, 22.5]
        positions = positions or default_positions
        
        # Create system with default params
        system = BridgeVehicleSystem(params={})
        system.run_analysis()
        
        signals = {}
        t = system.t
        
        for pos in positions:
            results = system.analyze_damage(pos, depth)
            cpdv = system.calculate_cpdv(results["uc"])
            
            # Downsample
            n = len(cpdv)
            if n > downsample:
                idx = np.linspace(0, n-1, downsample).astype(int)
                cpdv = cpdv[idx]
                t_ds = t[idx]
            else:
                t_ds = t[:n]
            
            signals[f"p={pos}m"] = cpdv.tolist()
        
        return {
            "t": t_ds.tolist(),
            "signals": signals,
            "depth": depth,
            "positions": positions,
            "downsample": downsample
        }
    
    def _compute_peak_analysis(
        self,
        depths: Optional[List[float]],
        distances: Optional[List[float]]
    ) -> Dict[str, Any]:
        """Compute peak vs position/depth analysis"""
        sys.path.insert(0, str(config.pipeline_cwd("cpdv")))
        from simulation.system_coupling import BridgeVehicleSystem
        
        default_depths = [0.1, 0.15, 0.2, 0.25, 0.3]
        default_distances = [5, 7.5, 10, 12.5, 15, 17.5, 20, 22.5]
        
        depths = depths or default_depths
        distances = distances or default_distances
        
        system = BridgeVehicleSystem(params={})
        system.run_analysis()
        
        # Peak vs Position (for each depth)
        peak_vs_position = {}
        for depth in depths:
            peaks = []
            for pos in distances:
                results = system.analyze_damage(pos, depth)
                cpdv = system.calculate_cpdv(results["uc"])
                peak = float(np.max(np.abs(cpdv)))
                peaks.append(peak)
            peak_vs_position[f"d={depth}"] = peaks
        
        # Peak vs Depth (for each position)
        peak_vs_depth = {}
        for pos in distances:
            peaks = []
            for depth in depths:
                results = system.analyze_damage(pos, depth)
                cpdv = system.calculate_cpdv(results["uc"])
                peak = float(np.max(np.abs(cpdv)))
                peaks.append(peak)
            peak_vs_depth[f"p={pos}m"] = peaks
        
        return {
            "peak_vs_position": peak_vs_position,
            "peak_vs_depth": peak_vs_depth,
            "depths": depths,
            "distances": distances
        }
    
    def _compute_cv_analysis(
        self,
        n_samples: int,
        crack_pos: float,
        crack_depth: float,
        mode: str,
        positions: Optional[List[float]]
    ) -> Dict[str, Any]:
        """Compute CV analysis using random condition script logic"""
        sys.path.insert(0, str(config.pipeline_cwd("cpdv")))
        from simulation.system_coupling import BridgeVehicleSystem
        import numpy as np
        
        DEFAULT_PARAM_RANGES = {
            "mv": [3000, 15000],
            "kv": [50000, 200000],
            "cv": [2000, 10000],
            "V": [1, 20],
            "L": [20, 50],
            "E": [2.0e10, 3.5e10],
            "I": [0.05, 0.2],
            "m": [200, 600],
        }
        
        rng = np.random.RandomState(42)
        
        def sample_params(ranges):
            return {k: rng.uniform(v[0], v[1]) for k, v in ranges.items()}
        
        def run_single_cpdv(params, pos, depth):
            system = BridgeVehicleSystem(params=params)
            system.run_analysis()
            results = system.analyze_damage(pos, depth)
            cpdv = system.calculate_cpdv(results["uc"])
            return float(np.max(np.abs(cpdv)))
        
        if mode == "multi_pos" and positions:
            position_results = {}
            for pos in positions:
                peaks = []
                for _ in range(n_samples):
                    params = sample_params(DEFAULT_PARAM_RANGES)
                    try:
                        peak = run_single_cpdv(params, pos, crack_depth)
                        peaks.append(peak)
                    except:
                        pass
                peaks_arr = np.array(peaks)
                if len(peaks_arr) > 0:
                    cv = np.std(peaks_arr) / max(np.mean(peaks_arr), 1e-12)
                    position_results[pos] = {
                        "peaks": peaks_arr.tolist(),
                        "mean": float(np.mean(peaks_arr)),
                        "std": float(np.std(peaks_arr)),
                        "cv": float(cv)
                    }
            return {
                "mode": "multi_pos",
                "crack_depth": crack_depth,
                "position_results": position_results
            }
        else:
            peaks = []
            for _ in range(n_samples):
                params = sample_params(DEFAULT_PARAM_RANGES)
                try:
                    peak = run_single_cpdv(params, crack_pos, crack_depth)
                    peaks.append(peak)
                except:
                    pass
            
            peaks_arr = np.array(peaks)
            if len(peaks_arr) > 0:
                mean = float(np.mean(peaks_arr))
                std = float(np.std(peaks_arr))
                cv = std / max(mean, 1e-12)
            else:
                mean = std = cv = 0.0
            
            return {
                "mode": "single",
                "crack_pos": crack_pos,
                "crack_depth": crack_depth,
                "peaks": peaks_arr.tolist(),
                "mean": mean,
                "std": std,
                "cv": cv,
                "needs_multi_condition": cv >= 0.30
            }
    
    # ─────────────────────────────────────────────────────────────────────
    # Cache Management
    # ─────────────────────────────────────────────────────────────────────
    
    def _load_json_artifact(
        self,
        path: Path,
        cache_key: str,
        force_refresh: bool,
        default: Any = None
    ) -> Any:
        """Load JSON file with caching"""
        cached = self._get_cached(cache_key, force_refresh)
        if cached is not None:
            return cached
        
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = default or {}
        
        self._set_cache(cache_key, data)
        return data
    
    def _load_dashboard_data(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Load dashboard_data.js from legacy prototype"""
        cache_key = "dashboard_data"
        cached = self._get_cached(cache_key, force_refresh)
        if cached is not None:
            return cached
        
        js_path = config.DASHBOARD_WORKSPACE / "看板原型" / "dashboard_data.js"
        if js_path.exists():
            text = js_path.read_text(encoding="utf-8")
            m = re.search(r"window\.DASHBOARD_DATA\s*=\s*(\{[\s\S]*\})\s*;?\s*$", text)
            if m:
                data = json.loads(m.group(1))
                self._set_cache(cache_key, data)
                return data
        
        return {"meta": {"metrics": {}}, "bridges": []}
    
    def _get_cached(self, key: str, force_refresh: bool) -> Optional[Any]:
        """Get cached value if valid"""
        if force_refresh:
            return None
        if key in self._cache:
            import time
            if time.time() - self._cache_ttl.get(key, 0) < self._default_ttl:
                return self._cache[key]
        return None
    
    def _set_cache(self, key: str, value: Any):
        """Set cache with timestamp"""
        import time
        self._cache[key] = value
        self._cache_ttl[key] = time.time()
    
    def clear_cache(self, key: Optional[str] = None):
        """Clear cache"""
        if key:
            self._cache.pop(key, None)
            self._cache_ttl.pop(key, None)
        else:
            self._cache.clear()
            self._cache_ttl.clear()


# Global registry instance
registry = DataRegistry()