def point_in_polygon(x, y, poly):
    """
    Checks if a point (x, y) is inside a polygon `poly`.
    `poly` is a list of (x, y) vertices.
    Uses the Ray-Casting algorithm.
    """
    n = len(poly)
    if n < 3: # A polygon must have at least 3 vertices
        return False
        
    inside = False
    p1x, p1y = poly[0]
    for i in range(n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside 