def boom():
    raise ValueError("nope")

caught = 0
try:
    raise ValueError("bad")
    print("FAIL after raise")
except:
    caught = 1
    print("bare catch")
if caught == 1:
    print("caught ok")

try:
    boom()
    print("FAIL boom continued")
except ValueError as e:
    print("valueerror")
    print(e)

fin = 0
try:
    raise RuntimeError("x")
except:
    print("rt")
finally:
    fin = 1
if fin == 1:
    print("finally ok")
