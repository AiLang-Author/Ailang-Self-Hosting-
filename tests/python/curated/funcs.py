def add(a, b):
    return a + b

def fact(n):
    if n <= 1:
        return 1
    return n * fact(n - 1)

print(add(3, 4))
print(fact(5))
