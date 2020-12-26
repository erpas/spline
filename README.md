# Spline

Spline is a QGIS plugin for digitizing spline curves. 
It uses a modified [cubic Hermite interpolator](https://en.wikipedia.org/wiki/Cubic_Hermite_spline).
The result is a chain of straight lines created by simplification of interpolated curve with [Douglas-Peuker algorithm](https://en.wikipedia.org/wiki/Ramer%E2%80%93Douglas%E2%80%93Peucker_algorithm). 

The digitizing map tool has two parameters:

* tightness or tension - can be interpreted as the length of the curve tangent at digitized points, must be in interval [0,1]
* tolerance for Douglas-Peuker simplification algorithm - the smaller it is, the more segmented is the resulting linestring.
