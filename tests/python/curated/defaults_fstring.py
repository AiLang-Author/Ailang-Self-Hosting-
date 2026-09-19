def greet(name, punct="!"):
    msg = f"hello {name}{punct}"
    print(msg)

def add(a, b=10):
    return a + b

greet("Ada")
greet("Bob", ".")
print(add(3))
print(add(3, 4))
name = "Zed"
print(f"hi {name}")
