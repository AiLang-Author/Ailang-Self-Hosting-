def sum_all(start, *rest):
    t = start
    i = 0
    n = len(rest)
    while i < n:
        t = t + rest[i]
        i = i + 1
    return t

def collect(*items):
    return len(items)

print(sum_all(1, 2, 3, 4))
print(collect())
print(collect(9, 8))
print(sum_all(10))
