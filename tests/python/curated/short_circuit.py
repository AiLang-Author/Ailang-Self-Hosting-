def boom():
    print("BOOM")
    return 1

print(0 and boom())
print(1 or boom())
print(1 and 2)
print(0 or 5)
x = None
print(x or "d")
print(1 < 5 < 9)
print(5 < 3 < boom())
if 0 and boom():
    print("FAIL and")
else:
    print("skip and")
if 1 or boom():
    print("skip or")
ys = [n for n in [0, 1, 2] if n and n > 0]
print(len(ys))
print(ys[0])
