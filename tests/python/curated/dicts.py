d = {"a": 1, "b": 2}
print(d["a"])
print(len(d))
print(d.get("b"))
print(d.get("z", 9))
d["c"] = 3
print(d["c"])
ks = d.keys()
print(len(ks))
print(d)
