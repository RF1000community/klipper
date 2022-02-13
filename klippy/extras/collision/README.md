# Collision

Klipper module to check whether another print job can be printed right away
without causing collisions. In case this isn't possible, this module also
provides a function to find an offset that allows a print job to be printed
anyway at a different place on the print bed.

This is meant to be used in [D4SK/klipperui](https://github.com/D4SK/klipperui).


## Configuration

For this module to work some measurements will need to be configured in the
Klipper configuration file under the `collision` section, describing the size of
the printhead and gantry.

```
printhead_x_min
printhead_x_max
printhead_y_min
printhead_y_max
gantry_xy_min
gantry_xy_max
gantry_z_min
gantry_orientation
padding
```

`gantry_orientation` should be either `x` or `y` and specifies the axis to which
the gantry is parallel to.

`padding` is optional and specifies how much extra space should be left between
two objects until they are considered to not be colliding. If not provided, this
value defaults to 5mm.

All measurements should be positive numbers (int or float) in millimeters.

The following diagrams should help in understanding how all the values are
interpreted:

![Diagrams for configuration](diagrams.png)

An example configuration for this section can be found in 
[test_config.cfg](test_config.cfg).

## Tests

The unit tests can be run using `./test.py` or for example `./test.py
CollisionTest` or `./test.py GeometryTest.test_cuboid_eq` to run individual
tests.
