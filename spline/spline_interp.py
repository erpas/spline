"""
/***************************************************************************
    Digitize spline, based on CircularArcDigitizer (Stefan Ziegler)
    and Generalizer plugin (Piotr Pociask) which is based on GRASS v.generalize
                              -------------------
        begin                : February 2014
        copyright            : (C) 2014 by Radim Blazek
        email                : radim.blazek@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings
from qgis.core import (
    QgsGeometry,
    QgsPoint,
    QgsPointXY,
)

import math
from .utils import DEFAULT_TIGHTNESS, DEFAULT_TOLERANCE, SETTINGS_NAME


def interpolate(points, tolerance=None, tightness=None):
    if tolerance is None:
        tolerance = QSettings().value(SETTINGS_NAME + "/tolerance", DEFAULT_TOLERANCE, float)
    if tightness is None:
        tightness = QSettings().value(SETTINGS_NAME + "/tightness", DEFAULT_TIGHTNESS, float)
    points = hermite(points, tolerance, tightness)
    return [QgsPointXY(pt) for pt in points]


def hermite(points, tolerance, tightness):
    npoints = len(points)
    if npoints < 3:
        return list(points)  # return copy
    output = []  # output points

    # calculate tangents, first and last go in edge direction
    tangents = [points_tangent_scaled(points[0], points[1], tightness)]
    for i in range(1, npoints - 1):
        tangents.append(points_tangent_scaled(points[i - 1], points[i + 1], tightness))
    tangents.append(points_tangent_scaled(points[-2], points[-1], tightness))

    h1 = lambda s: (2 * (s ** 3)) - (3 * (s ** 2)) + 1
    h2 = lambda s: 3 * (s ** 2) - 2 * (s ** 3)
    h3 = lambda s: (s ** 3) - (2 * (s ** 2)) + s
    h4 = lambda s: (s ** 3) - (s ** 2)

    for i in range(0, npoints - 1):
        p0 = points[i]
        p1 = points[i + 1]

        output.append(p0)

        # It would be better to divide each segment to steps according
        # to tolerance but how to find maximum step size for tolerance?
        # It should be probably possible for with some math.
        # step = ???
        # dist = pointsDist(p0, p1)
        # if dist == 0 or dist < step:
        # continue
        # else:
        # t = float(step)/dist

        # for now we just make 50 points (more may become slow) and prune them using tolerance
        t = 1.0 / 50.
        s = t

        tmp_points = []
        output.append(tmp_points)
        while s < 1:
            h1p1 = point_scalar(p0, h1(s))
            h2p2 = point_scalar(p1, h2(s))
            h3t1 = point_scalar(tangents[i], h3(s))
            h4t2 = point_scalar(tangents[i + 1], h4(s))

            tmp1 = points_add(h1p1, h2p2)
            tmp2 = points_add(h3t1, h4t2)
            tmp = points_add(tmp1, tmp2)

            tmp_points.append(tmp)
            s = s + t

    output.append(p1)  # last point

    # now we have mix of points and point lists, we clean the lists keeping the digitized points
    result = []
    for i in range(len(output)):
        p = output[i]
        if type(p) == list:
            pnts = [output[i - 1]] + p + [output[i + 1]]
            pnts = simplify_points(pnts, tolerance)
            result.extend(pnts[1:-1])
        else:
            result.append(p)

    return result


def points_tangent_scaled(p1, p2, k):
    x = p2.x() - p1.x()
    y = p2.y() - p1.y()
    return point_scalar(QgsPoint(x, y), k)


def simplify_points(points, tolerance):
    geo = QgsGeometry.fromPolyline(points)
    geo = geo.simplify(tolerance)
    return geo.asPolyline()


def point_scalar(p, k):
    return QgsPoint(p.x() * k, p.y() * k)


def points_add(p1, p2):
    return QgsPoint(p1.x() + p2.x(), p1.y() + p2.y())


def points_dist(a, b):
    dx = a.x() - b.x()
    dy = a.y() - b.y()
    return math.sqrt(dx * dx + dy * dy)
