xs = [10, 20, 30]
print(len(xs))
print(xs[0])
print(xs[-1])
xs.append(40)
print(len(xs))
print(xs[3])
last = xs.pop()
print(last)
print(len(xs))
s = 0
for x in xs:
    s = s + x
print(s)
ys = [n for n in xs if n > 15]
print(len(ys))
print(ys[0])
