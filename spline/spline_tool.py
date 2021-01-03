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
from qgis.PyQt.QtCore import Qt, QSettings
from qgis.PyQt.QtGui import QCursor, QPixmap, QColor
from qgis.core import (
    QgsCoordinateTransform,
    QgsFeature,
    QgsGeometry,
    QgsPoint,
    QgsPointXY,
    QgsProject,
    QgsSettings,
    QgsWkbTypes,
)
from qgis.gui import QgsRubberBand, QgsMapToolEdit, QgsVertexMarker

from .spline_interp import interpolate


class SplineTool(QgsMapToolEdit):
    def __init__(self, iface):
        super(SplineTool, self).__init__(iface.mapCanvas())
        self.iface = iface
        self.canvas = self.iface.mapCanvas()

        self.rb = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        self.snap_marker = QgsVertexMarker(self.canvas)
        self.snapping_utils = self.canvas.snappingUtils()

        self.points = []  # digitized, not yet interpolated points
        self.type = QgsWkbTypes.LineGeometry  # layer geometry type
        self.tolerance = None
        self.tightness = None
        self.is_polygon = None

        self.cursor = QCursor(
            QPixmap(
                [
                    "16 16 3 1",
                    "      c None",
                    ".     c #FF0000",
                    "+     c #FFFFFF",
                    "                ",
                    "       +.+      ",
                    "      ++.++     ",
                    "     +.....+    ",
                    "    +.     .+   ",
                    "   +.   .   .+  ",
                    "  +.    .    .+ ",
                    " ++.    .    .++",
                    " ... ...+... ...",
                    " ++.    .    .++",
                    "  +.    .    .+ ",
                    "   +.   .   .+  ",
                    "   ++.     .+   ",
                    "    ++.....+    ",
                    "      ++.++     ",
                    "       +.+      ",
                ]
            )
        )

        s = QgsSettings()
        self.snap_col = s.value("/qgis/digitizing/snap_color", QColor("#ff00ff"))

    def canvasMoveEvent(self, event):
        color = QColor(255, 0, 0, 100)
        self.rb.setColor(color)
        self.rb.setWidth(1)
        point = self.toMapCoordinates(event.pos())

        # try to snap to a feature
        result = self.snapping_utils.snapToMap(point)
        if result.isValid():
            point = result.point()
            self.update_snap_marker(snapped_pt=point)
        else:
            self.update_snap_marker()

        points = list(self.points)
        points.append(QgsPoint(point))
        points = interpolate(points)
        self.set_rubber_band_points(points)

    def canvasReleaseEvent(self, event):
        color = QColor(255, 0, 0, 100)
        self.rb.setColor(color)
        self.rb.setWidth(1)
        point = self.toMapCoordinates(event.pos())

        if event.button() == Qt.LeftButton:
            # try to snap to a feature
            result = self.snapping_utils.snapToMap(point)
            if result.isValid():
                point = result.point()
            self.points.append(QgsPoint(point))
            points = interpolate(self.points)
            self.set_rubber_band_points(points)
        else:
            if len(self.points) >= 2:
                # refresh without last point
                self.refresh()
                self.create_feature()
            self.reset_points()
            self.reset_rubber_band()
            self.canvas.refresh()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.deactivate()
            self.activate()
        elif e.key() == Qt.Key_Backspace:
            if self.points:
                self.points.pop()
            points = interpolate(self.points)
            self.set_rubber_band_points(points)
            self.canvas.refresh()

    def reset_points(self):
        self.points = []

    # Create feature from digitized points, i.e. without the last moving point
    # where right click happened. This the same way how core QGIS Add Feature works.
    def create_feature(self):
        layer = self.iface.activeLayer()
        provider = layer.dataProvider()
        fields = provider.fields()
        f = QgsFeature(fields)
        coords = [QgsPointXY(pt) for pt in interpolate(self.points)]

        proj = QgsProject.instance()
        if layer.crs() != proj.crs():
            trans_context = proj.transformContext()
            transf = QgsCoordinateTransform(proj.crs(), layer.crs(), trans_context)
            coords_tmp = coords[:]
            coords = []
            for point in coords_tmp:
                transformed_pt = transf.transform(point)
                coords.append(transformed_pt)

        # Add geometry to feature
        if self.is_polygon:
            g = QgsGeometry.fromPolygonXY([coords])
        else:
            g = QgsGeometry.fromPolylineXY(coords)
        f.setGeometry(g)

        # Add attribute fields to feature
        for field in fields.toList():
            ix = fields.indexFromName(field.name())
            f[field.name()] = provider.defaultValue(ix)

        layer.beginEditCommand("Feature added")

        settings = QSettings()
        disable_attributes = settings.value("/qgis/digitizing/disable_enter_attribute_values_dialog", False, type=bool)
        layer.addFeature(f)
        if disable_attributes:
            layer.endEditCommand()
        else:
            dlg = self.iface.getFeatureForm(layer, f)
            if dlg.exec_():
                layer.endEditCommand()
            else:
                layer.destroyEditCommand()

    def refresh(self):
        if self.points:
            points = interpolate(self.points)
            self.set_rubber_band_points(points)

    def canvasPressEvent(self, event):
        pass

    def showSettingsWarning(self):
        pass

    def activate(self):
        self.canvas.setCursor(self.cursor)
        layer = self.iface.activeLayer()
        self.type = layer.geometryType()
        self.is_polygon = False
        if self.type == QgsWkbTypes.PolygonGeometry:
            self.is_polygon = True

    def reset_rubber_band(self):
        self.rb.reset(self.type)

    def set_rubber_band_points(self, points):
        self.reset_rubber_band()
        for point in points:
            update = point is points[-1]
            if isinstance(point, QgsPoint):
                point = QgsPointXY(point)
            self.rb.addPoint(point, update)

    def update_snap_marker(self, snapped_pt=None):
        self.canvas.scene().removeItem(self.snap_marker)
        if snapped_pt is None:
            return
        self.snap_marker = QgsVertexMarker(self.canvas)
        self.snap_marker.setCenter(snapped_pt)
        self.snap_marker.setIconSize(16)
        self.snap_marker.setIconType(QgsVertexMarker.ICON_BOX)
        self.snap_marker.setPenWidth(3)
        self.snap_marker.setColor(self.snap_col)

    def deactivate(self):
        self.reset_points()
        self.update_snap_marker()
        self.reset_rubber_band()
        QgsMapToolEdit.deactivate(self)

    def isZoomTool(self):
        return False

    def isTransient(self):
        return False

    def isEditTool(self):
        return True
