def f(a, b):
    return a * 10 + b

print(f(1, 2))
print(f(a=1, b=2))
print(f(b=2, a=1))
print(f(1, b=2))

def g(x, y=5):
    return x + y

print(g(3))
print(g(x=3))
print(g(3, y=7))
print(g(x=3, y=7))
