import time

# t = (2009, 2, 17, 17, 3, 38, 1, 48, 0)
t = time.localtime()
secs = time.mktime(t)
print("Time in seconds:",  secs)

t2 = (2025, 1, 13, 10, 27, 55, 0, 0)
secs2 = time.mktime(t2)
print("Time in seconds:",  secs2)

print("Difference in seconds:", secs2 - secs)
