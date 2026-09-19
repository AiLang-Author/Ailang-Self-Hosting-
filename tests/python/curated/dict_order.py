d = {"z": 1, "a": 2}
print(d)
d["m"] = 3
print(d)
for k in d:
    print(k)
e = {}
e["first"] = 10
e["second"] = 20
print(e)
import json
print(json.dumps({"z": 1, "a": 2}))
