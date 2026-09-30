"""
Vehicle-Bridge Coupled System Simulation (Based on system.md Methodology)

This module implements the core methodology from system.md:
1. 6-step iterative algorithm for vehicle-bridge interaction simulation
2. AP (Apparent Profile) calculation from vehicle acceleration
3. CPDV calculation: CPDV = AP_damaged - AP_intact

Reference: system.md - "求解接触点位移（CPDV）的具体数值方法"
"""

import numpy as np
from scipy import linalg
import math
from typing import Dict, List, Tuple, Optional


class BridgeVehicleSystem:
    """
    Vehicle-Bridge Coupling System Class - Based on system.md methodology

    Core concepts:
    - CPDV (Contact Point Displacement Variation): Contact point displacement variation
    - AP (Apparent Profile): Apparent profile = vehicle-bridge contact point displacement time history + road roughness
    - 6-step iterative algorithm for vehicle-bridge coupling analysis
    """

    def __init__(self, params: Optional[Dict] = None):
        """
        Initialize vehicle-bridge coupling system

        Args:
            params: Parameter dictionary, uses defaults if None
        """
        self.params = params or {}

        # Parameter type conversion helpers
        def to_float(val, default):
            if val is None:
                return default
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, str):  # Handle scientific notation strings from YAML
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return default
            return default

        def to_int(val, default):
            if val is None:
                return default
            if isinstance(val, (int, float)):
                return int(val)
            if isinstance(val, str):
                try:
                    return int(val)
                except (ValueError, TypeError):
                    return default
            return default

        # Road type parameter
        self.road_type = self.params.get("road_type", "a")

        # Vehicle parameters (1/4 car model)
        self.mv = to_float(self.params.get("mv", 1000), 1000)        # Vehicle mass (kg)
        self.kv = to_float(self.params.get("kv", 170000), 170000)    # Suspension stiffness (N/m)
        self.cv = to_float(self.params.get("cv", 1000), 1000)        # Suspension damping (N/(m/s))
        self.k_a = to_float(self.params.get("k_a", 170000), 170000)  # Axle stiffness (N/m)
        self.V = to_float(self.params.get("V", 10), 5)               # Vehicle speed (m/s)
        self.g = 9.8                                                 # Gravity (m/s^2)
        self.fv = np.sqrt(self.kv / self.mv) / (2 * np.pi)          # Vehicle natural frequency (Hz)

        # Bridge parameters
        self.L = to_float(self.params.get("L", 30), 30)              # Bridge length (m)
        self.E = to_float(self.params.get("E", 2.75e10), 2.75e10)   # Elastic modulus (Pa)
        self.I = to_float(self.params.get("I", 0.175), 0.175)       # Moment of inertia (m^4)
        self.m = to_float(self.params.get("m", 1000), 1000)          # Mass per unit length (kg/m)
        self.EL = to_int(self.params.get("EL", 30), 30)              # Number of elements
        self.depth = to_float(self.params.get("depth", 1.0), 1.0)    # Beam depth (m)
        self.width = to_float(self.params.get("width", 0.3), 0.3)    # Beam width (m)

        # Modal parameters
        self.n_modes = to_int(self.params.get("n_modes", 4), 4)
        self.kexi = to_float(self.params.get("kexi", 0.02), 0.02)    # Damping ratio

        # Rayleigh damping coefficients [C_b] = α[M_b] + β[K_b]
        self.alpha = to_float(self.params.get("alpha", 0.0), 0.0)    # Mass matrix coefficient
        self.beta_damping = to_float(
            self.params.get("beta_damping", 0.0), 0.0
        )  # Stiffness matrix coefficient

        # Analysis parameters
        self.ttotal = self.L / self.V                                # Total analysis time (s)
        self.deltat = to_float(self.params.get("deltat", 0.01), 0.01)  # Time step (s)
        self.t = np.arange(0, self.ttotal + self.deltat, self.deltat)  # Time vector
        self.tstep = len(self.t)

        # Newmark-β parameters
        self.gamma = to_float(self.params.get("gamma", 0.5), 0.5)
        self.beta_nb = to_float(
            self.params.get("beta", 0.25), 0.25
        )  # Avoid confusion with damping beta
        self._setup_newmark_params()

        # Iteration convergence parameters (system.md Step 6)
        self.max_iterations = to_int(self.params.get("max_iterations", 50), 50)
        self.convergence_tol = to_float(
            self.params.get("convergence_tol", 0.01), 0.01
        )  # 1% convergence criterion

        # Crack damage parameters
        self.cracks: List[Dict] = []
        self.has_crack = False

        # Result storage
        self.results = {}
        self.healthy_results = {}
        self.damaged_results = {}
        self.uc = []                      # Contact point displacement response (AP)
        self.CPDV = []                    # Contact point displacement variation
        self.uc_healthy = None            # Healthy state AP
        self.vehicle_acc = None           # Vehicle acceleration time history

        # Random seed for reproducibility
        self.rng = np.random.RandomState(42)

    def _setup_newmark_params(self):
        """Setup Newmark-β method parameters"""
        dt = self.deltat
        beta = self.beta_nb
        gamma = self.gamma

        self.Alpha_0 = 1 / (beta * dt**2)
        self.Alpha_1 = gamma / (beta * dt)
        self.Alpha_2 = 1 / (beta * dt)
        self.Alpha_3 = 1 / (2 * beta) - 1
        self.Alpha_4 = gamma / beta - 1
        self.Alpha_5 = dt / 2 * (gamma / beta - 2)
        self.Alpha_6 = dt * (1 - gamma)
        self.Alpha_7 = gamma * dt

    def add_crack(self, position: float, depth_ratio: float, width: float = 0.3):
        """Add a crack"""
        self.cracks.append(
            {"position": position, "depth_ratio": depth_ratio, "width": width}
        )
        self.has_crack = True

    def clear_cracks(self):
        """Clear all cracks"""
        self.cracks = []
        self.has_crack = False

    def beam_km0_f(
        self, m: float, L: float, E: float, I: float, EL: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate bridge finite element mass and stiffness matrices

        Reference: system.md boundary conditions - simply supported beam with
        zero vertical displacement at both ends

        Args:
            m: Mass per unit length (kg/m)
            L: Bridge length (m)
            E: Elastic modulus (Pa)
            I: Moment of inertia (m^4)
            EL: Number of elements

        Returns:
            M_global: Global mass matrix
            K_global: Global stiffness matrix
        """
        Le = L / EL

        # Element mass matrix (consistent mass matrix)
        mb = (m * Le / 420) * np.array(
            [
                [156, 22 * Le, 54, -13 * Le],
                [22 * Le, 4 * Le**2, 13 * Le, -3 * Le**2],
                [54, 13 * Le, 156, 22 * Le],
                [-13 * Le, -3 * Le**2, 22 * Le, 4 * Le**2],
            ]
        )

        # Element stiffness matrix
        kb = (E * I / Le**3) * np.array(
            [
                [12, 6 * Le, -12, 6 * Le],
                [6 * Le, 4 * Le**2, -6 * Le, 2 * Le**2],
                [-12, -6 * Le, 12, -6 * Le],
                [6 * Le, 2 * Le**2, -6 * Le, 4 * Le**2],
            ]
        )

        n_dof = 2 * (EL + 1)
        K_global = np.zeros((n_dof, n_dof))
        M_global = np.zeros((n_dof, n_dof))

        # Multi-crack handling
        if self.has_crack and len(self.cracks) > 0:
            for crack in self.cracks:
                crack_position = crack["position"]
                crack_depth_ratio = crack["depth_ratio"]
                crack_width = crack["width"]

                crack_elem = int(np.floor(crack_position / Le)) + 1
                if crack_elem > EL:
                    crack_elem = EL
                xi_j = crack_position - (crack_elem - 1) * Le

                d = self.depth
                w = crack_width
                I_0 = w * d**3 / 12
                d_cj = crack_depth_ratio * d
                I_cj = w * (d - d_cj) ** 3 / 12

                l_c = 1.5 * self.depth
                xi_j_norm = xi_j / Le

                # Stiffness reduction matrix elements
                k11 = (12 * E * (I_0 - I_cj) / Le**4) * (
                    (2 * l_c**3) / (Le**2) + 3 * l_c * ((2 * xi_j_norm - 1) ** 2)
                )
                k12 = (12 * E * (I_0 - I_cj) / Le**3) * (
                    (l_c**3) / (Le**2) + l_c * (2 - 7 * xi_j_norm + 6 * xi_j_norm**2)
                )
                k14 = (12 * E * (I_0 - I_cj) / Le**3) * (
                    (l_c**3) / (Le**2) + l_c * (1 - 5 * xi_j_norm + 6 * xi_j_norm**2)
                )
                k22 = (12 * E * (I_0 - I_cj) / Le**2) * (
                    (3 * l_c**3) / (Le**2) + 2 * l_c * ((3 * xi_j_norm - 2) ** 2)
                )
                k24 = (12 * E * (I_0 - I_cj) / Le**2) * (
                    (3 * l_c**3) / (Le**2)
                    + 2 * l_c * (2 - 9 * xi_j_norm + 9 * xi_j_norm**2)
                )
                k44 = (12 * E * (I_0 - I_cj) / Le**2) * (
                    (3 * l_c**3) / (Le**2) + 2 * l_c * ((3 * xi_j_norm - 1) ** 2)
                )

                K_crack = np.array(
                    [
                        [k11, k12, -k11, k14],
                        [k12, k22, -k12, k24],
                        [-k11, -k12, k11, -k14],
                        [k14, k24, -k14, k44],
                    ]
                )

                # Apply crack stiffness reduction
                K_e = kb.copy()
                K_e_crack = K_e - K_crack
                K_e_crack = (K_e_crack + K_e_crack.T) / 2
                K_global[
                    2 * (crack_elem - 1) : 2 * (crack_elem - 1) + 4,
                    2 * (crack_elem - 1) : 2 * (crack_elem - 1) + 4,
                ] += K_e_crack

        # Assemble global matrices (undamaged elements)
        for i in range(EL):
            # Skip elements with cracks already applied
            if self.has_crack:
                skip = False
                for crack in self.cracks:
                    crack_elem = int(np.floor(crack["position"] / Le)) + 1
                    if (i + 1) == crack_elem:
                        skip = True
                        break
                if skip:
                    continue

            K_global[2 * i : 2 * i + 4, 2 * i : 2 * i + 4] += kb
            M_global[2 * i : 2 * i + 4, 2 * i : 2 * i + 4] += mb

        # Apply boundary conditions (simply supported beam)
        # system.md: "vertical displacement at both ends constrained to zero"
        keep_indices = list(range(n_dof))
        keep_indices.remove(0)          # Left end vertical displacement
        keep_indices.remove(n_dof - 2)  # Right end vertical displacement
        M_global = M_global[np.ix_(keep_indices, keep_indices)]
        K_global = K_global[np.ix_(keep_indices, keep_indices)]

        return M_global, K_global

    def setup_damping(self, M: np.ndarray, K: np.ndarray) -> np.ndarray:
        """
        Setup Rayleigh damping [C_b] = α[M_b] + β[K_b]

        Reference: system.md - "Damping: bridge uses classical viscous Rayleigh model"

        Args:
            M: Mass matrix
            K: Stiffness matrix

        Returns:
            C: Damping matrix
        """
        if self.alpha == 0 and self.beta_damping == 0:
            # Auto-compute Rayleigh damping coefficients
            if hasattr(self, "Frequ") and len(self.Frequ) >= 2:
                f_1 = self.Frequ[0]
                f_2 = self.Frequ[1]
                w1 = 2 * np.pi * f_1
                w2 = 2 * np.pi * f_2

                # Based on damping ratio
                coefficient = 2 * w1 * w2 / (w1**2 - w2**2)
                matrix = np.array([[w1, -w2], [-1 / w1, 1 / w2]])
                a0, a1 = np.dot(matrix, [self.kexi, self.kexi]) * coefficient
                self.alpha = a0
                self.beta_damping = a1

        C = self.alpha * M + self.beta_damping * K
        return C

    def psd_r(
        self, roadtype: str, L: float, V: float, deltat: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Road roughness generation function (ISO 8608 standard)

        Args:
            roadtype: Road class 'a', 'b', 'c'
            L: Bridge length (m)
            V: Vehicle speed (m/s)
            deltat: Time step (s)

        Returns:
            RX: Road roughness sequence
            dRX: Road roughness first derivative
        """
        ts = 5 * deltat

        road_dict = {
            "a": 0.001 * 1e-6,
            "b": 8 * 1e-6,
            "c": 16 * 1e-6,
        }
        Gd_n0 = road_dict.get(roadtype.lower(), 0.001 * 1e-6)

        n_max = 2.83
        n_min = 0.011
        n0 = 0.1
        N = max(100, int(L / V / ts))

        t_total = L / V
        num_points = int(t_total / deltat) + 1
        t = np.linspace(0, t_total, num_points)

        theta = self.rng.uniform(0, 2 * np.pi, N)

        delta_n = (n_max - n_min) / N
        n_k = n_min + np.arange(N) * delta_n

        Gd_n = Gd_n0 * (n_k / n0) ** (-2)

        RX = np.zeros(num_points)
        dRX = np.zeros(num_points)
        amplitude = np.sqrt(2 * Gd_n * delta_n)

        for i in range(num_points):
            phase = 2 * np.pi * n_k * V * t[i] + theta
            RX[i] = np.sum(amplitude * np.cos(phase))
            dRX[i] = -2 * np.pi * V * np.sum(n_k * amplitude * np.sin(phase))

        if len(RX) > self.tstep:
            return RX[: self.tstep], dRX[: self.tstep]
        else:
            RX_full = np.zeros(self.tstep)
            dRX_full = np.zeros(self.tstep)
            RX_full[: len(RX)] = RX
            dRX_full[: len(dRX)] = dRX
            return RX_full, dRX_full

    def get_shape_function(self, xc: float, Le: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get shape function and its derivative

        Reference: system.md Step 4 - Use shape function vector {N_b}_i
        to convert contact point forces to bridge nodes

        Args:
            xc: Vehicle position within element (m)
            Le: Element length (m)

        Returns:
            N: Shape function vector [N1, N2, N3, N4]
            dN: Shape function derivative vector
        """
        if Le <= 0:
            return np.zeros(4), np.zeros(4)

        zeta = xc / Le

        N1 = 1 - 3 * zeta**2 + 2 * zeta**3
        N2 = Le * (zeta - 2 * zeta**2 + zeta**3)
        N3 = 3 * zeta**2 - 2 * zeta**3
        N4 = Le * (-(zeta**2) + zeta**3)

        N = np.array([N1, N2, N3, N4])

        dN1_dx = (-6 * zeta + 6 * zeta**2) / Le
        dN2_dx = 1 - 4 * zeta + 3 * zeta**2
        dN3_dx = (6 * zeta - 6 * zeta**2) / Le
        dN4_dx = -2 * zeta + 3 * zeta**2

        dN = np.array([dN1_dx, dN2_dx, dN3_dx, dN4_dx])

        return N, dN

    def get_element_location_vector(self, elem_num: int, EL: int) -> np.ndarray:
        """
        Get element location vector

        Reference: system.md Step 4 - Use element location vector [L_i]
        to convert forces to global nodes

        Args:
            elem_num: Element number (1-based)
            EL: Total number of elements

        Returns:
            L_vec: Element location vector
        """
        n_dof = 2 * (EL + 1)
        L_vec = np.zeros(n_dof)

        if elem_num < 1 or elem_num > EL:
            return L_vec

        # Element's 4 DOFs
        L_vec[2 * (elem_num - 1)] = 1
        L_vec[2 * (elem_num - 1) + 1] = 1
        L_vec[2 * elem_num] = 1
        L_vec[2 * elem_num + 1] = 1

        # Remove boundary condition indices
        keep_indices = list(range(n_dof))
        keep_indices.remove(0)
        keep_indices.remove(n_dof - 2)

        return L_vec[keep_indices]

    def solve_vehicle_newmark(
        self,
        f_v: float,
        u_prev: float,
        du_prev: float,
        ddu_prev: float,
    ) -> Tuple[float, float, float]:
        """
        Solve vehicle equation of motion using Newmark-β method

        Reference: system.md Step 3 - Use Newmark-β to solve vehicle acceleration

        Args:
            f_v: External force on vehicle (scalar)
            u_prev: Previous time step vehicle displacement
            du_prev: Previous time step vehicle velocity
            ddu_prev: Previous time step vehicle acceleration

        Returns:
            u_new: Current time step displacement
            du_new: Current time step velocity
            ddu_new: Current time step acceleration
        """
        # Vehicle mass matrix (1 DOF)
        M_v = self.mv

        # Vehicle stiffness
        K_v = self.kv

        # Vehicle damping
        C_v = self.cv

        # Newmark-β effective stiffness
        Keff = K_v + self.Alpha_0 * M_v + self.Alpha_1 * C_v

        # Prevent division by zero
        if abs(Keff) < 1e-15:
            Keff = 1e-15

        # Compute effective force
        term1 = self.Alpha_0 * u_prev + self.Alpha_2 * du_prev + self.Alpha_3 * ddu_prev
        term2 = self.Alpha_1 * u_prev + self.Alpha_4 * du_prev + self.Alpha_5 * ddu_prev
        Feff = f_v + M_v * term1 + C_v * term2

        # Solve
        u_new = Feff / Keff

        # Compute velocity and acceleration
        ddu_new = (
            self.Alpha_0 * (u_new - u_prev)
            - self.Alpha_2 * du_prev
            - self.Alpha_3 * ddu_prev
        )
        du_new = du_prev + self.Alpha_6 * ddu_prev + self.Alpha_7 * ddu_new

        # Numerical stability checks
        if not np.isfinite(u_new):
            u_new = u_prev
        if not np.isfinite(du_new):
            du_new = du_prev
        if not np.isfinite(ddu_new):
            ddu_new = ddu_prev

        # Clip outliers
        max_val = 1e10
        u_new = np.clip(u_new, -max_val, max_val)
        du_new = np.clip(du_new, -max_val, max_val)
        ddu_new = np.clip(ddu_new, -max_val, max_val)

        return u_new, du_new, ddu_new

    def solve_bridge_newmark(
        self,
        f_b: np.ndarray,
        u_prev: np.ndarray,
        du_prev: np.ndarray,
        ddu_prev: np.ndarray,
        M: np.ndarray,
        K: np.ndarray,
        C: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Solve bridge equation of motion using Newmark-β method

        Reference: system.md Step 5 - Use Newmark-β to solve bridge displacement

        Args:
            f_b: External force vector on bridge
            u_prev: Previous time step bridge displacement
            du_prev: Previous time step bridge velocity
            ddu_prev: Previous time step bridge acceleration
            M: Bridge mass matrix
            K: Bridge stiffness matrix
            C: Bridge damping matrix

        Returns:
            u_new: Current time step displacement
            du_new: Current time step velocity
            ddu_new: Current time step acceleration
        """
        # Newmark-β effective stiffness
        Keff = K + self.Alpha_0 * M + self.Alpha_1 * C

        # Add regularization to prevent singularity
        Keff = Keff + 1e-6 * np.eye(Keff.shape[0])

        # Compute effective force
        term1 = self.Alpha_0 * u_prev + self.Alpha_2 * du_prev + self.Alpha_3 * ddu_prev
        term2 = self.Alpha_1 * u_prev + self.Alpha_4 * du_prev + self.Alpha_5 * ddu_prev
        Feff = f_b + M @ term1 + C @ term2

        # Check numerical stability of effective force and matrix
        if not np.all(np.isfinite(Feff)):
            Feff = np.nan_to_num(Feff, nan=0.0, posinf=1e10, neginf=-1e10)

        if not np.all(np.isfinite(Keff)):
            Keff = np.eye(Keff.shape[0])  # Fallback to identity

        # Solve
        try:
            u_new = linalg.solve(Keff, Feff)
        except Exception:
            # Solve failed, fall back to previous step
            u_new = u_prev.copy()

        # Compute velocity and acceleration
        ddu_new = (
            self.Alpha_0 * (u_new - u_prev)
            - self.Alpha_2 * du_prev
            - self.Alpha_3 * ddu_prev
        )
        du_new = du_prev + self.Alpha_6 * ddu_prev + self.Alpha_7 * ddu_new

        # Numerical stability checks and clipping
        max_val = 1e10

        if not np.all(np.isfinite(u_new)):
            u_new = u_prev.copy()
        else:
            u_new = np.clip(u_new, -max_val, max_val)

        if not np.all(np.isfinite(du_new)):
            du_new = du_prev.copy()
        else:
            du_new = np.clip(du_new, -max_val, max_val)

        if not np.all(np.isfinite(ddu_new)):
            ddu_new = ddu_prev.copy()
        else:
            ddu_new = np.clip(ddu_new, -max_val, max_val)

        return u_new.flatten(), du_new.flatten(), ddu_new.flatten()

    def analyze_iterative(self):
        """
        Execute vehicle-bridge coupling analysis - 6-step iterative algorithm

        Reference: system.md Part 1 - "Iterative Solution Steps (6-step algorithm)"

        Step 1: Initialize. Assume contact point (CP) displacement is zero at each time step.
        Step 2: Calculate contact force on vehicle axle. f_va_i = k_a * (w_bi + r_ci)
        Step 3: Solve vehicle acceleration. Using Newmark-β method.
        Step 4: Calculate global force vector on bridge.
        Step 5: Solve bridge global displacement. Using Newmark-β method.
        Step 6: Convergence check. Relative error < 1%.
        """
        # Bridge finite element model
        M, K = self.beam_km0_f(self.m, self.L, self.E, self.I, self.EL)

        # Save matrices for later use
        self.M = M
        self.K = K

        # Ensure matrix symmetry
        K = (K + K.T) / 2
        M = (M + M.T) / 2

        # Add regularization to prevent numerical issues
        K_reg = K + 1e-6 * np.eye(K.shape[0])
        M_reg = M + 1e-6 * np.eye(M.shape[0])

        # Eigenvalue analysis to get frequencies
        if np.all(np.linalg.eigvals(K_reg) > 0) and np.all(
            np.linalg.eigvals(M_reg) > 0
        ):
            eigvals, eigvecs = linalg.eig(K_reg, M_reg)
            real_mask = np.isreal(eigvals)

            if np.sum(real_mask) >= self.n_modes:
                eigvals = np.real(eigvals[real_mask])
                eigvecs = np.real(eigvecs[:, real_mask])

                sorted_indices = np.argsort(eigvals)
                eigvals = eigvals[sorted_indices]
                eigvecs = eigvecs[:, sorted_indices]

                self.phi = eigvecs[:, : self.n_modes]
                self.Omega = np.sqrt(eigvals[: self.n_modes])
                self.Frequ = self.Omega / (2 * np.pi)
            else:
                self.Frequ = self._compute_theoretical_freq()
        else:
            self.Frequ = self._compute_theoretical_freq()

        # Setup Rayleigh damping
        C = self.setup_damping(M, K)
        self.C = C

        # Road excitation
        RX, dRX = self.psd_r(self.road_type, self.L, self.V, self.deltat)

        # Initialize variables
        n_dof = M.shape[0]
        Le = self.L / self.EL

        # Vehicle variables
        u_v = np.zeros(self.tstep)    # Vehicle displacement
        du_v = np.zeros(self.tstep)   # Vehicle velocity
        ddu_v = np.zeros(self.tstep)  # Vehicle acceleration

        # Contact point variables
        w_bi = np.zeros(self.tstep)   # Bridge displacement at contact point

        # Bridge variables
        u_b = np.zeros((n_dof, self.tstep))
        du_b = np.zeros((n_dof, self.tstep))
        ddu_b = np.zeros((n_dof, self.tstep))

        # Time step loop
        for k in range(1, self.tstep):
            xp = self.V * k * self.deltat  # Vehicle position

            if xp > self.L:
                # Vehicle has left bridge, maintain previous state
                u_v[k] = u_v[k - 1]
                du_v[k] = du_v[k - 1]
                ddu_v[k] = ddu_v[k - 1]
                continue

            # Get current element info
            s = int(np.floor(xp / Le)) + 1
            if s > self.EL:
                s = self.EL
            xc = xp - (s - 1) * Le  # Vehicle position within element

            N, dN = self.get_shape_function(xc, Le)
            L_vec = self.get_element_location_vector(s, self.EL)

            # Road roughness
            r_c = RX[k] if k < len(RX) else 0

            # ==================== 6-step iterative algorithm ====================

            # Step 1: Initialize - assume contact point displacement is zero (first iteration)
            if k == 1:
                w_bi[k] = 0

            # Iterative solution
            iteration = 0
            converged = False
            diverged = False  # Divergence detection
            w_bi_new = 0      # Initialize

            while iteration < self.max_iterations and not converged and not diverged:
                try:
                    # Step 2: Calculate contact force on vehicle axle
                    # f_va_i = k_a * (w_bi + r_ci)
                    f_va = self.k_a * (w_bi[k] + r_c)

                    # Vehicle equation of motion RHS force (with gravity)
                    f_vehicle = f_va - self.mv * self.g

                    # Step 3: Solve vehicle acceleration (Newmark-β)
                    u_v_prev = u_v[k - 1]
                    du_v_prev = du_v[k - 1]
                    ddu_v_prev = ddu_v[k - 1]

                    u_v_new, du_v_new, ddu_v_new = self.solve_vehicle_newmark(
                        f_vehicle, u_v_prev, du_v_prev, ddu_v_prev
                    )

                    u_v[k] = u_v_new
                    du_v[k] = du_v_new
                    ddu_v[k] = ddu_v_new

                    # Step 4: Calculate global force vector on bridge
                    # Contact force = vehicle gravity + inertia force
                    # Inertia force f_inertia = -m_v * a_v
                    f_inertia = -self.mv * ddu_v[k]
                    f_total = f_va + f_inertia

                    # Assemble global force vector using shape function and location vector
                    f_b_global = f_total * L_vec

                    # Step 5: Solve bridge global displacement (Newmark-β)
                    u_b_prev = u_b[:, k - 1]
                    du_b_prev = du_b[:, k - 1]
                    ddu_b_prev = ddu_b[:, k - 1]

                    u_b_new, du_b_new, ddu_b_new = self.solve_bridge_newmark(
                        f_b_global, u_b_prev, du_b_prev, ddu_b_prev, M, K, C
                    )

                    u_b[:, k] = u_b_new
                    du_b[:, k] = du_b_new
                    ddu_b[:, k] = ddu_b_new

                    # Calculate new contact point displacement (using shape function interpolation)
                    if len(N) >= 4 and len(u_b_new) >= 4:
                        w_bi_new = N @ u_b_new[:4]
                    else:
                        w_bi_new = 0

                    # Divergence detection: if value exceeds threshold, stop iteration
                    if abs(w_bi_new) > 1e8 or not np.isfinite(w_bi_new):
                        diverged = True
                        # Fall back to previous time step value
                        w_bi_new = w_bi[k - 1] if k > 1 else 0
                        break

                    # Step 6: Convergence check
                    # Convergence criterion: contact point displacement relative error < 1%
                    if abs(w_bi[k]) > 1e-10:
                        rel_error = abs(w_bi_new - w_bi[k]) / abs(w_bi[k])
                    else:
                        rel_error = abs(w_bi_new - w_bi[k])

                    if rel_error < self.convergence_tol:
                        converged = True
                        w_bi[k] = w_bi_new
                    else:
                        # Update contact point displacement, start next iteration
                        w_bi[k] = w_bi_new
                        iteration += 1

                except Exception as e:
                    # Exception fallback
                    diverged = True
                    w_bi_new = w_bi[k - 1] if k > 1 else 0
                    w_bi[k] = w_bi_new
                    break

            # If diverged, fall back to previous time step values
            if diverged:
                u_v[k] = u_v[k - 1]
                du_v[k] = du_v[k - 1]
                ddu_v[k] = ddu_v[k - 1]
                u_b[:, k] = u_b[:, k - 1]
                du_b[:, k] = du_b[:, k - 1]
                ddu_b[:, k] = ddu_b[:, k - 1]
                w_bi[k] = w_bi[k - 1] if k > 1 else 0

        # Store results
        self.u = np.vstack([u_v.reshape(1, -1), u_b])
        self.du = np.vstack([du_v.reshape(1, -1), du_b])
        self.ddu = np.vstack([ddu_v.reshape(1, -1), ddu_b])

        self.zv_DIS = u_v
        self.zv_VEL = du_v
        self.zv_ACC = ddu_v

        # Contact point displacement (AP) = bridge contact point displacement + road roughness
        # Reference: system.md - "AP is the sum of vehicle-bridge contact point displacement time history and road roughness"
        self.uc = w_bi + RX[: self.tstep]

        # Numerical stability handling
        self.uc = np.clip(self.uc, -1e6, 1e6)
        self.uc = np.nan_to_num(self.uc, nan=0.0, posinf=1e6, neginf=-1e6)

        # Store intermediate bridge displacement
        self.u_b = u_b

    def _compute_theoretical_freq(self) -> np.ndarray:
        """Compute theoretical frequencies"""
        freq = np.zeros(self.n_modes)
        for n in range(1, self.n_modes + 1):
            freq[n - 1] = (
                (n**2) / (2 * self.L**2) * np.sqrt(self.E * self.I / (np.pi * self.m))
            )
        return freq

    def analyze(self):
        """
        Execute vehicle-bridge coupling analysis - using 6-step iterative algorithm
        """
        self.analyze_iterative()

    def run_analysis(self) -> Dict:
        """
        Run complete analysis pipeline: healthy state -> damaged state -> CPDV
        """
        # Healthy state analysis
        self.clear_cracks()
        self.analyze()
        self.healthy_results = {
            "zv_DIS": self.zv_DIS.copy(),
            "zv_VEL": self.zv_VEL.copy(),
            "zv_ACC": self.zv_ACC.copy(),
            "uc": self.uc.copy(),
            "Frequ": self.Frequ.copy() if hasattr(self, "Frequ") else None,
            "K_matrix": self.K.copy() if hasattr(self, "K") else None,
        }
        self.uc_healthy = self.uc.copy()

        return self.healthy_results

    def analyze_damage(self, crack_position: float, crack_depth_ratio: float) -> Dict:
        """
        Analyze specified damage state

        Args:
            crack_position: Crack position (m)
            crack_depth_ratio: Crack depth ratio (0-1)

        Returns:
            Damage state results dictionary
        """
        # Set crack
        self.clear_cracks()
        self.add_crack(crack_position, crack_depth_ratio)

        # Analyze
        self.analyze()

        return {
            "zv_DIS": self.zv_DIS.copy(),
            "zv_VEL": self.zv_VEL.copy(),
            "zv_ACC": self.zv_ACC.copy(),
            "uc": self.uc.copy(),
            "Frequ": self.Frequ.copy() if hasattr(self, "Frequ") else None,
            "K_matrix": self.K.copy() if hasattr(self, "K") else None,
        }

    def analyze_multi_cracks(self, crack_list: List[Tuple[float, float]]) -> Dict:
        """
        Analyze multi-crack damage state

        Args:
            crack_list: List of cracks [(position1, depth_ratio1), (position2, depth_ratio2), ...]

        Returns:
            Damage state results dictionary
        """
        self.clear_cracks()
        for pos, depth in crack_list:
            self.add_crack(pos, depth)

        self.analyze()

        return {
            "zv_DIS": self.zv_DIS.copy(),
            "zv_VEL": self.zv_VEL.copy(),
            "zv_ACC": self.zv_ACC.copy(),
            "uc": self.uc.copy(),
            "Frequ": self.Frequ.copy() if hasattr(self, "Frequ") else None,
            "K_matrix": self.K.copy() if hasattr(self, "K") else None,
            "cracks": self.cracks.copy(),
        }

    def calculate_cpdv(self, damaged_uc: np.ndarray) -> np.ndarray:
        """
        Calculate CPDV (Contact Point Displacement Variation)

        Reference: system.md - "CPDV = AP_damaged - AP_intact"

        Args:
            damaged_uc: Damaged state contact point displacement (AP)

        Returns:
            CPDV sequence
        """
        if self.uc_healthy is None:
            raise ValueError("Please run healthy state analysis first")

        # CPDV = AP_damaged - AP_intact
        cpdv = damaged_uc - self.uc_healthy

        # Numerical stability handling - reasonable clipping range
        # Bridge displacement typically in mm (10^-3 m), ±0.1m clipping is sufficient
        cpdv = np.clip(cpdv, -0.1, 0.1)
        cpdv = np.nan_to_num(cpdv, nan=0.0, posinf=0.0, neginf=0.0)

        return cpdv

    def normalize_cpdv(self, cpdv: np.ndarray) -> Tuple[np.ndarray, float, float]:
        """
        Data normalization - min-max scaling to [0,1] interval

        Reference: system.md - "Data preprocessing: CPDV data was normalized
        (min-max scaling to [0,1] interval) before input to BP neural network"

        Args:
            cpdv: CPDV data

        Returns:
            Normalized CPDV, min value, max value
        """
        cpdv_min = np.min(cpdv)
        cpdv_max = np.max(cpdv)

        if cpdv_max - cpdv_min < 1e-10:
            return np.zeros_like(cpdv), cpdv_min, cpdv_max

        cpdv_norm = (cpdv - cpdv_min) / (cpdv_max - cpdv_min)

        return cpdv_norm, cpdv_min, cpdv_max

    def denormalize_cpdv(
        self, cpdv_norm: np.ndarray, cpdv_min: float, cpdv_max: float
    ) -> np.ndarray:
        """
        Denormalize

        Args:
            cpdv_norm: Normalized CPDV
            cpdv_min: Min value
            cpdv_max: Max value

        Returns:
            Original scale CPDV
        """
        return cpdv_norm * (cpdv_max - cpdv_min) + cpdv_min


class EnhancedBridgeVehicleSystem(BridgeVehicleSystem):
    """
    Enhanced Vehicle-Bridge Coupling System Class

    Inherits from BridgeVehicleSystem, adds multi-crack support
    """

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(params)

        # Multi-vehicle support
        self.multi_vehicle_mode = self.params.get("multi_vehicle", False)
        self.vehicle_spacing = self.params.get("vehicle_spacing", 5.0)

    def analyze_multi_cracks(self, crack_list: List[Tuple[float, float]]) -> Dict:
        """
        Analyze multi-crack damage state

        Args:
            crack_list: Crack list [(position1, depth_ratio1), (position2, depth_ratio2), ...]

        Returns:
            Damage state results dictionary
        """
        self.clear_cracks()
        for pos, depth in crack_list:
            self.add_crack(pos, depth)

        self.analyze()

        return {
            "zv_DIS": self.zv_DIS.copy(),
            "zv_VEL": self.zv_VEL.copy(),
            "zv_ACC": self.zv_ACC.copy(),
            "uc": self.uc.copy(),
            "Frequ": self.Frequ.copy() if hasattr(self, "Frequ") else None,
            "K_matrix": self.K.copy() if hasattr(self, "K") else None,
            "cracks": self.cracks.copy(),
        }


def create_system(params: Optional[Dict] = None) -> BridgeVehicleSystem:
    """
    Factory function: create vehicle-bridge coupling system

    Args:
        params: System parameter dictionary

    Returns:
        BridgeVehicleSystem instance
    """
    return BridgeVehicleSystem(params)


def create_enhanced_system(
    params: Optional[Dict] = None,
) -> EnhancedBridgeVehicleSystem:
    """
    Factory function: create enhanced vehicle-bridge coupling system

    Args:
        params: System parameter dictionary

    Returns:
        EnhancedBridgeVehicleSystem instance
    """
    return EnhancedBridgeVehicleSystem(params)