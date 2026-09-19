n = None
if n is None:
    print("is-none")
if n is not None:
    print("FAIL is-not")
else:
    print("is-not-else")
if n:
    print("FAIL truthy none")
else:
    print("falsy none")
xs = []
if xs:
    print("FAIL empty list")
else:
    print("empty list falsy")
s = ""
if s:
    print("FAIL empty str")
else:
    print("empty str falsy")
