import sympy as sp

k, q = sp.symbols("k q")
expr = 3 - k + (k - q - 2) / (3 - 2 * q)

expr = (1 - q) * (expr**-1)

expr = expr * (k - q - 2) / (3 - 2 * q)

print(sp.factor(sp.simplify(expr)))
