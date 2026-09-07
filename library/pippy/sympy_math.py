# TITLE: Symbolic Math with SymPy
# DESCRIPTION: Learn how to simplify expressions and solve equations with SymPy.

import sympy as sp

def main():
    x = sp.Symbol('x')

    print("--- 1. Simplifying Algebra ---")
    expr = (x**2 - 1) / (x - 1)
    print("Original:  (x^2 - 1) / (x - 1)")
    print("Simplified:", sp.simplify(expr))

    print("\n--- 2. Solving an Equation ---")
    # Solving 2*x + 4 = 0 for x
    equation = sp.Eq(2*x + 4, 0)
    solution = sp.solve(equation, x)
    print("Equation: 2*x + 4 = 0")
    print("Solution for x:", solution[0])

if __name__ == "__main__":
    main()