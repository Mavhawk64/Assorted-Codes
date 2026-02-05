import sympy as sp

dG_dr, G_eff, G, c, dm_dr, M_0, m, U, dG_eff_dG = sp.symbols(
    "\\frac{d\\Gamma}{dr} \\Gamma_\\text{eff} \\Gamma c \\frac{dm}{dr} M_0 m U \\frac{d\\Gamma_\\text{eff}}{d\\Gamma}"
)
g_hat = sp.symbols("\\hat{\\gamma}")
r = sp.symbols("r")
rho = sp.symbols("\\rho(r)")

dm_dr = 4 * sp.pi * r**2 * rho  # Mass continuity equation (8.49)
G_eff = (g_hat * G**2 - g_hat + 1) / G  # Equation (8.54)
dG_eff_dG = (g_hat * G**2 + g_hat - 1) / G**2  # Derivative of Equation (8.54) -> (8.65)

dUad_dr = -(g_hat - 1) * (3 / r - 1 / G * dG_dr) * U  # Equation (8.64)

eq1 = sp.Eq(
    dG_dr,
    -(
        ((G_eff + 1) * (G + 1) * c**2 * dm_dr + G_eff * dUad_dr)
        / ((M_0 + m) * c**2 + U * dG_eff_dG)
    ),
)  # Equation (8.60)

# Solve for dG_dr
solution = sp.solve(eq1, dG_dr)

print(len(solution))
print("\\frac{d\\Gamma}{dr} = ", sp.latex(sp.factor(solution[0])))
