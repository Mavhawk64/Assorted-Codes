# Definition: v_\perp^{\text{app}}/c=\beta\cdot\frac{\sin\theta}{1-\beta\cos\theta}
# 2 arguments: beta, theta
# Goal: solve for beta in terms of theta.
import sympy as sp

beta, theta = sp.symbols("\\beta \\theta")

bs = sp.solve(sp.Eq(1, beta * sp.sin(theta) / (1 - beta * sp.cos(theta))), beta)

print(len(bs))
print(sp.latex(bs[0]))
