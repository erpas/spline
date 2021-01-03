# -*- coding: utf-8 -*-

"""
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

from qgis.PyQt.QtCore import QCoreApplication, QSettings
from qgis.core import (
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProcessing,
    QgsFeatureSink,
    QgsProcessingException,
    QgsProcessingAlgorithm,
    QgsProcessingParameterNumber,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFeatureSink,
    QgsWkbTypes,
)
from qgis import processing
from ..spline_interp import interpolate

SINGLE_LINE_TYPES = (
    QgsWkbTypes.LineString,
    QgsWkbTypes.LineStringM,
    QgsWkbTypes.LineStringZ,
    QgsWkbTypes.LineStringZM,
    QgsWkbTypes.LineString25D,
    QgsWkbTypes.LineGeometry,
)

from ..utils import DEFAULT_TIGHTNESS, DEFAULT_TOLERANCE, DEFAULT_MAX_SEGMENTS, SETTINGS_NAME


class Lines2SplinesProcessingAlgorithm(QgsProcessingAlgorithm):
    """
    This algorithm converts features line geometry to spline.
    """

    INPUT = "INPUT"
    TENSION = "TENSION"
    TOLERANCE = "TOLERANCE"
    MAX_SEGMENTS = "MAX_SEGMENTS"
    OUTPUT = "OUTPUT"

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate("Spline Plugin", string)

    def createInstance(self):
        return Lines2SplinesProcessingAlgorithm()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "lines2splines"

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr("Lines to splines")

    def helpUrl(self):
        return "https://github.com/erpas/spline"

    def shortHelpString(self):
        help_str = """
        Convert single line geometries to splines (chains of straight lines).
        
        A modified <a href=https://en.wikipedia.org/wiki/Cubic_Hermite_spline>cubic Hermite spline interpolator</a> is used to obtain continuous piecewise third-degree polynomials between knots (known spline points).
        Each piece is converted to a chain of lines which is then simplified with <a href=https://en.wikipedia.org/wiki/Ramer%E2%80%93Douglas%E2%80%93Peucker_algorithm>Douglas-Peuker algorithm</a>. 

        <i>z</i> and <i>m</i> values are interpolated linearly between knots, if properly defined in input layer.
        
        Parameters:
         * Tightness or tension - can be interpreted as the length of the curve tangent at digitized points, must be in interval [0,1]
         * Tolerance for Douglas-Peuker simplification algorithm - the smaller it is, the more segmented is the resulting linestring.
         * Max number of spline segments - initial number of spline segments interpolated between knots. This line is then simplified.
        """
        return self.tr(help_str)

    def initAlgorithm(self, config=None):
        tension = QSettings().value(SETTINGS_NAME + "/tightness", DEFAULT_TIGHTNESS, float)
        tolerance = QSettings().value(SETTINGS_NAME + "/tolerance", DEFAULT_TOLERANCE, float)
        max_segments = QSettings().value(SETTINGS_NAME + "/max_segments", DEFAULT_MAX_SEGMENTS, float)

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT, self.tr("Input layer"), [QgsProcessing.TypeVectorLine]
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.TENSION,
                self.tr("Tension parameter"),
                QgsProcessingParameterNumber.Double,
                tension,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.TOLERANCE,
                self.tr("Tolerance parameter"),
                QgsProcessingParameterNumber.Double,
                tolerance,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.MAX_SEGMENTS,
                self.tr("Max number of spline segments between vertices"),
                QgsProcessingParameterNumber.Integer,
                max_segments,
            )
        )
        self.addParameter(QgsProcessingParameterFeatureSink(self.OUTPUT, self.tr("Splines layer")))

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        # Check if the input layer is single type geometry
        if source.wkbType() not in SINGLE_LINE_TYPES:
            raise QgsProcessingException(
                "Wrong input geometry type (multi). Convert it to single type and try again.")

        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context, source.fields(), source.wkbType(), source.sourceCrs()
        )
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        tension = self.parameterAsDouble(
            parameters,
            self.TENSION,
            context,
        )
        tolerance = self.parameterAsDouble(
            parameters,
            self.TOLERANCE,
            context,
        )
        max_segments = self.parameterAsInt(
            parameters,
            self.MAX_SEGMENTS,
            context,
        )
        has_z = source.wkbType() in (
            QgsWkbTypes.LineStringZ,
            QgsWkbTypes.LineStringZM,
        )
        has_m = source.wkbType() in (
            QgsWkbTypes.LineStringM,
            QgsWkbTypes.LineStringZM,
        )

        total = 100.0 / source.featureCount() if source.featureCount() else 0
        features = source.getFeatures()

        for current, feature in enumerate(features):
            if feedback.isCanceled():
                break
            feedback.pushInfo(f"\nFeature id={feature.id()}")
            cur_geom = feature.geometry()

            vertices_xy = [QgsPointXY(v) for v in cur_geom.vertices()]
            if len(vertices_xy) < 3:
                # it is a 2 points line - keep it as is
                sink.addFeature(feature, QgsFeatureSink.FastInsert)
                continue
            spline_pts = [QgsPointXY(pt) for pt in interpolate(vertices_xy, tolerance, tension, max_segments)]
            spline_geom = QgsGeometry.fromPolylineXY(spline_pts)
            if not spline_geom.isGeosValid():
                raise QgsProcessingException(f"Invalid resulting spline geometry for feature id {feature.id()}")

            # linearly interpolate m and z values, if applicable
            if has_m:
                m_pts = [
                    QgsPointXY(spline_geom.lineLocatePoint(QgsGeometry.fromPointXY(QgsPointXY(v))), v.m())
                    for v in cur_geom.vertices()
                ]
                m_line = QgsGeometry.fromPolylineXY(m_pts)
                if not m_line.isGeosValid():
                    feedback.pushInfo("Invalid m data")
                    has_m = False
            if has_z:
                z_pts = [
                    QgsPointXY(spline_geom.lineLocatePoint(QgsGeometry.fromPointXY(QgsPointXY(v))), v.z())
                    for v in cur_geom.vertices()
                ]
                z_line = QgsGeometry.fromPolylineXY(z_pts)
                if not z_line.isGeosValid():
                    feedback.pushInfo("Invalid z data")
                    has_z = False

            if has_m or has_z:
                new_vertices = []
                for vertex in spline_geom.vertices():
                    dist = spline_geom.lineLocatePoint(QgsGeometry.fromPointXY(QgsPointXY(vertex)))
                    if has_m:
                        m_line_pt = m_line.interpolate(dist)
                        if m_line_pt.isGeosValid():
                            vertex.addMValue(m_line_pt.asPoint().y())
                    if has_z:
                        z_line_pt = z_line.interpolate(dist).asPoint()
                        vertex.addZValue(z_line_pt.y())
                    new_vertices.append(vertex)
                spline_geom = QgsGeometry.fromPolyline(new_vertices)

            spline_feat = QgsFeature(feature)
            spline_feat.setGeometry(spline_geom)
            sink.addFeature(spline_feat, QgsFeatureSink.FastInsert)

            feedback.setProgress(int(current * total))

        return {self.OUTPUT: dest_id}
