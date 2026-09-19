class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def mag2(self):
        return self.x * self.x + self.y * self.y

p = Point(3, 4)
print(p.x)
print(p.y)
print(p.mag2())
if isinstance(p, Point):
    print("isinstance")
