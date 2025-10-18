# r = 1/2\cdot\left(a+c\pm\sqrt{2b^2-(a-c)^2}\right)
# r_minus is valid when \frac{(a-c)^2}{2}\leq b^2\leq a^2+c^2
import sympy as sp

a, b, c = sp.symbols("a b c", positive=True, real=True)
r_m = sp.Rational(1, 2) * (a + c - sp.sqrt(2 * b**2 - (a - c)**2))
r_p = sp.Rational(1, 2) * (a + c + sp.sqrt(2 * b**2 - (a - c)**2))

# verify \frac{\pi r^2}{4}>r^2-r(a+c)+ac
lhs_m = sp.Rational(1, 4) * sp.pi * r_m**2
rhs_m = r_m**2 - r_m * (a + c) + a * c
simplified_m = sp.factor(lhs_m - rhs_m, deep=True) * 8  # manually multiply by 8 to clear denominators
# print("r_m:")
# print(sp.latex(simplified_m), " > 0")

lhs_p = sp.Rational(1, 4) * sp.pi * r_p**2
rhs_p = r_p**2 - r_p * (a + c) + a * c
simplified_p = sp.factor(lhs_p - rhs_p, deep=True) * 8  # manually multiply by 8 to clear denominators
# print("r_p:")
# print(sp.latex(simplified_p), " > 0")

# In order for r_minus to be valid, we need the above condition on b^2
bottom_m = simplified_m.subs(b**2, sp.Rational(1, 2) * (a - c)**2)
# print("bottom_m:")
# print(sp.latex(sp.simplify(bottom_m)), " > 0")

# print(4 * (a - c)**2 + sp.pi * (a + c)**2 > 0) # Always true since a,c>0

top_m = simplified_m.subs(b**2, a**2 + c**2)
# print("top_m:")
# print(sp.latex(sp.factor(top_m, deep=True)), " > 0")

# print(-8 * a * c > 0)  # Always false since a,c>0

# Upper limit of b is determined by lhs_m = rhs_m

eq = sp.Eq(lhs_m, rhs_m)
sol = sp.solve(eq, b**2)
# print("Upper limit of b^2 for r_minus to hold:")
# f = sp.Symbol("\\sqrt{(a-c)^2+4\\pi ac}", positive=True, real=True)
# g = sp.Symbol("(a+c)", positive=True, real=True)
# h = sp.Symbol("(a^2+c^2+16*a*c*(\\pi-2))", positive=True, real=True)
# print(
#     "b^2 \\leq",
#     sp.latex(
#         sp.factor(sp.simplify(sol[0].xreplace({
#             sp.sqrt(a**2 - 2 * a * c + sp.pi * a * c + c**2): f,
#             (a + c): g,
#             (a**2 + c**2 + 16 * a * c * (sp.pi - 2)): h
#         })),
#                   deep=True)))

# ok i fell for the trick question... the radius is just b ;(
