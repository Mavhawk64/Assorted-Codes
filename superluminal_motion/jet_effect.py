import matplotlib.pyplot as plt
import numpy as np

# =========================================================
# ISM, no energy injection, p>2
# Build a full F_nu(t, nu) surface over the full nu domain
# using evolving break frequencies (nu_a, nu_m, nu_c) and
# the standard broken power-law synchrotron spectrum.
#
# NOTE: This assumes the common slow-cooling ordering:
#       nu_a < nu_m < nu_c
# and uses typical ISM (adiabatic) time scalings:
#   nu_m ∝ t^(-3/2),  nu_c ∝ t^(-1/2),  F_max ∝ t^(0),  nu_a ∝ t^(0)
# =========================================================

# -----------------------------
# User-facing "earlier parameters" (set here)
# -----------------------------
p = 2.4  # electron index (p>2)

# Choose a reference time and break values there (you can change these)
t0 = 1e3  # s
nu_a0 = 1e9  # Hz
nu_m0 = 5e14  # Hz  (optical-ish at t0)
nu_c0 = 1e17  # Hz  (X-ray-ish at t0)
Fmax0 = 1.0  # arbitrary normalization (e.g., mJy)


# -----------------------------
# Time scalings (ISM, no injection; adiabatic)
# -----------------------------
def nu_a(t):  # often ~constant in this regime; kept constant for a clean demo
    return nu_a0 * (t / t0) ** 0.0


def nu_m(t):
    return nu_m0 * (t / t0) ** (-1.5)


def nu_c(t):
    return nu_c0 * (t / t0) ** (-0.5)


def Fmax(t):
    return Fmax0 * (t / t0) ** 0.0


# -----------------------------
# Broken power-law spectrum (slow cooling: nu_a < nu_m < nu_c)
# Shapes consistent with your Table 8.3 beta values:
#   nu < nu_a:        beta = -2     => F_nu ∝ nu^(+2)
#   nu_a < nu < nu_m: beta = -1/3   => F_nu ∝ nu^(+1/3)
#   nu_m < nu < nu_c: beta = (p-1)/2=> F_nu ∝ nu^(-(p-1)/2)
#   nu > nu_c:        beta = p/2    => F_nu ∝ nu^(-p/2)
# Continuity enforced at break points using Fmax at nu_m.
# -----------------------------
def Fnu_surface(t_grid, nu_grid):
    """
    Return F_nu on a meshgrid defined by t_grid (1D) and nu_grid (1D).
    Output shape: (len(nu_grid), len(t_grid)) matching meshgrid(nu, t) style.
    """
    T, NU = np.meshgrid(t_grid, nu_grid)  # NU varies along rows, T along columns

    NA = nu_a(T)
    NM = nu_m(T)
    NC = nu_c(T)
    FM = Fmax(T)

    # Enforce the ordering for this demo; if violated, you'd need other regimes
    # (we'll still compute, but interpret cautiously)
    # Build piecewise with masks
    F = np.zeros_like(T, dtype=float)

    # Region 1: NU < NA
    # Match at NU=NA to the NU^(1/3) branch:
    # F(NA) = FM * (NA/NM)^(1/3)
    F_at_NA = FM * (NA / NM) ** (1 / 3)
    mask1 = NU < NA
    F[mask1] = F_at_NA[mask1] * (NU[mask1] / NA[mask1]) ** (2.0)

    # Region 2: NA <= NU < NM
    mask2 = (NU >= NA) & (NU < NM)
    F[mask2] = FM[mask2] * (NU[mask2] / NM[mask2]) ** (1 / 3)

    # Region 3: NM <= NU < NC
    mask3 = (NU >= NM) & (NU < NC)
    F[mask3] = FM[mask3] * (NU[mask3] / NM[mask3]) ** (-(p - 1) / 2)

    # Region 4: NU >= NC
    # Ensure continuity at NC:
    # F(NC) from region 3: FM * (NC/NM)^(-(p-1)/2)
    F_at_NC = FM * (NC / NM) ** (-(p - 1) / 2)
    mask4 = NU >= NC
    F[mask4] = F_at_NC[mask4] * (NU[mask4] / NC[mask4]) ** (-p / 2)

    return F


# -----------------------------
# Grids
# -----------------------------
t = np.logspace(1, 6, 220)  # 10 s -> 1e6 s
nu = np.logspace(8, 19, 260)  # 1e8 Hz -> 1e19 Hz (radio -> gamma-ish)

F = Fnu_surface(t, nu)

# -----------------------------
# 3D surface in log space
# -----------------------------
fig = plt.figure()
ax = fig.add_subplot(projection="3d")

T, NU = np.meshgrid(t, nu)
ax.plot_surface(
    np.log10(T), np.log10(NU), np.log10(F), rstride=4, cstride=4, linewidth=0
)

ax.set_xlabel("log10(t [s])")
ax.set_ylabel("log10(ν [Hz])")
ax.set_zlabel("log10(Fν)")

# plt.show()
plt.savefig("jet_effect.png", dpi=300, bbox_inches="tight")
