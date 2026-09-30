"""
Vehicle-Bridge Coupling Simulation Module.

Implements the 6-step iterative algorithm for vehicle-bridge interaction
as described in system.md, with CPDV calculation for crack detection.

Core classes:
- BridgeVehicleSystem: Main simulation class (from system_iteration.py)
- EnhancedBridgeVehicleSystem: Enhanced version with multi-crack support
"""

from .system_iteration import (
    BridgeVehicleSystem,
    EnhancedBridgeVehicleSystem,
    create_system,
    create_enhanced_system,
)

__all__ = [
    "BridgeVehicleSystem",
    "EnhancedBridgeVehicleSystem",
    "create_system",
    "create_enhanced_system",
]