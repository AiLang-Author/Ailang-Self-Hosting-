import json

path = "/tmp/aimacro_cpython_file.txt"
f = open(path, "w")
f.write("hello")
f.close()
g = open(path, "r")
s = g.read()
g.close()
print(s)

print(json.dumps("hello"))
xs = json.loads("[1,2,3]")
print(len(xs))
print(xs[0])
d2 = json.dumps(xs)
if d2[0] == "[":
    print("dumps list")
print(json.dumps({"k": "v"}))
print(json.dumps(True))
print(json.dumps(None))

try:
    open("/no/such/aimacro_deep_missing.txt", "r")
    print("FAIL opened")
except:
    print("open catch")
