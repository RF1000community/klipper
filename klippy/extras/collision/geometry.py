class Rectangle:

    def __init__(self, x, y, max_x, max_y):
        if max_x < x:
            x, max_x = max_x, x
        if max_y < y:
            y, max_y = max_y, y
        self.x = x
        self.y = y
        self.max_x = max_x
        self.max_y = max_y

        self.width = max_x - x
        self.height = max_y - y

    def get_area(self):
        return self.width * self.height

    def __bool__(self):
        """Consider a rectangle as true if and only if its area is nonzero"""
        return bool(self.width and self.height)

    def __eq__(self, other):
        return (self.x == other.x and
                self.y == other.y and
                self.max_x == other.max_x and
                self.max_y == other.max_y)

    def intersection(self, other):
        """Return the intersection between two rectangles.
        This is always a rectangle, but may have no area if both rectangles are
        disjoint.
        """
        x = max(self.x, other.x)
        y = max(self.y, other.y)
        max_x = min(self.max_x, other.max_x)
        max_y = min(self.max_y, other.max_y)
        return Rectangle(x, y, max(max_x, x), max(max_y, y))

    def collides_with(self, other, padding=0):
        """Return, whether this rectangle collides with another rectangle.
        padding specifies a minimum distance that must be present between the
        Rectangles to not collide."""
        x = max(self.x, other.x)
        y = max(self.y, other.y)
        max_x = min(self.max_x, other.max_x)
        max_y = min(self.max_y, other.max_y)
        return max_x + padding > x and max_y + padding > y

    def grow(self, amount):
        """Return a new Rectangle with all sides grown by the given amount (or
        shrunk in case of negative values).
        """
        return Rectangle(self.x - amount, self.y - amount,
                         self.max_x + amount, self.max_y + amount)

    def translate(self, x_offset, y_offset):
        """Move the Rectangle by the given offset without changing its size"""
        return Rectangle(self.x + x_offset, self.y + y_offset,
                         self.max_x + x_offset, self.max_y + y_offset)

    def get_range_for_axis(self, axis):
        if axis == 1:  # Y-Axis
            return self.y, self.max_y
        return self.x, self.max_x  # X-Axis


class Cuboid:

    def __init__(self, x, y, z, max_x, max_y, max_z):
        if max_x < x:
            x, max_x = max_x, x
        if max_y < y:
            y, max_y = max_y, y
        if max_z < z:
            z, max_z = max_z, z
        self.x = x
        self.y = y
        self.z = z
        self.max_x = max_x
        self.max_y = max_y
        self.max_z = max_z

        self.width = max_x - x
        self.height = max_y - y
        self.z_height = max_z - z  # Yes, there are 2 heights. Get over it.

    def get_volume(self):
        return self.width * self.height * self.z_height

    def __bool__(self):
        return bool(self.width and self.height and self.z_height)

    def __eq__(self, other):
        return (self.x == other.x and
                self.y == other.y and
                self.z == other.z and
                self.max_x == other.max_x and
                self.max_y == other.max_y and
                self.max_z == other.max_z)

    def intersection(self, other):
        x = max(self.x, other.x)
        y = max(self.y, other.y)
        z = max(self.z, other.z)
        max_x = min(self.max_x, other.max_x)
        max_y = min(self.max_y, other.max_y)
        max_z = min(self.max_z, other.max_z)
        return Cuboid(x, y, z, max(max_x, x), max(max_y, y), max(max_z, z))

    def collides_with(self, other, padding=0):
        x = max(self.x, other.x)
        y = max(self.y, other.y)
        z = max(self.z, other.z)
        max_x = min(self.max_x, other.max_x)
        max_y = min(self.max_y, other.max_y)
        max_z = min(self.max_z, other.max_z)
        return (max_x + padding > x and
                max_y + padding > y and
                max_z + padding > z)

    def projection(self, axis=2):
        """Project the cuboid to a paraxial rectangle"""
        if axis == 2:  # Remove Z-axis
            return Rectangle(self.x, self.y, self.max_x, self.max_y)
        if axis == 1:  # Remove Y-axis
            return Rectangle(self.x, self.z, self.max_x, self.max_z)
        # Remove X-axis
        return Rectangle(self.y, self.z, self.max_y, self.max_z)

    def grow(self, amount):
        """Return a new Cuboid with all sides grown by the given amount (or
        shrunk in case of negative values).
        """
        return Cuboid(self.x - amount, self.y - amount, self.z - amount,
                      self.max_x + amount,
                      self.max_y + amount,
                      self.max_z + amount)

    def translate(self, x_offset, y_offset, z_offset):
        """Move the Cuboid by the given offset without changing its size"""
        return Cuboid(self.x + x_offset, self.y + y_offset,
                      self.z + z_offset,
                      self.max_x + x_offset, self.max_y + y_offset,
                      self.max_z + z_offset)

    def get_range_for_axis(self, axis):
        if axis == 2:  # Z-Axis
            return self.z, self.max_z
        if axis == 1:  # Y-Axis
            return self.y, self.max_y
        return self.x, self.max_x  # X-Axis
