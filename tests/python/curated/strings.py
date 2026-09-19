s = "Hello"
print(s.lower())
print(s.upper())
print(len(s))
print(s[1])
t = s + "!"
print(t)
if "ell" in s:
    print("has ell")
if s.startswith("He"):
    print("starts")
if s.endswith("lo"):
    print("ends")
print(s.find("ll"))
u = "  x  ".strip()
print(u)
print("a,b,c".split(",")[1])
print("-".join(["a", "b"]))
