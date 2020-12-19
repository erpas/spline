"""
/***************************************************************************
                     SplinePlugin QGIS plugin
                              -------------------
        begin                : 2014-02-05
        copyright            : (C) 2014 by Radim Blažek
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
import os.path

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from qgis.core import QgsWkbTypes, QgsMapLayerType

from .spline_tool import SplineTool
from .settingsdialog import SettingsDialog
from .utils import icon_path


class SplinePlugin(object):
    def __init__(self, iface):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.plugin_dir = os.path.dirname(__file__)
        locale = QSettings().value("locale/userLocale")[0:2]
        locale_path = os.path.join(self.plugin_dir, "i18n", "splineplugin_{}.qm".format(locale))
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        self.tool = SplineTool(self.iface)
        self.connected_layer = None
        self.settings_dialog = None
        self.action_settings = None
        self.action_spline = None

    def initGui(self):
        self.action_settings = QAction(QCoreApplication.translate("Spline", "Settings"), self.iface.mainWindow())
        self.action_settings.setObjectName("splineAction")
        self.action_settings.triggered.connect(self.open_settings)

        self.iface.addPluginToVectorMenu(u"Digitize Spline", self.action_settings)

        ico = QIcon(icon_path("icon.png"))
        self.action_spline = QAction(
            ico,
            QCoreApplication.translate("spline", "Digitize Spline Curves"),
            self.iface.mainWindow(),
        )
        self.action_spline.setObjectName("actionSpline")
        self.action_spline.setEnabled(False)
        self.action_spline.setCheckable(True)

        # Connect to signals for button behaviour
        self.action_spline.triggered.connect(self.digitize)
        self.iface.currentLayerChanged.connect(self.layer_changed)
        self.layer_changed()  # to enable when plugin is loaded

        self.canvas.mapToolSet.connect(self.deactivate)

        # Add actions to the toolbar
        self.iface.addToolBarIcon(self.action_spline)

    def unload(self):
        # Remove the plugin menu item and icon
        self.iface.removeToolBarIcon(self.action_spline)
        self.iface.removePluginVectorMenu(u"Digitize Spline", self.action_settings)

    def open_settings(self):
        self.settings_dialog = SettingsDialog()
        self.settings_dialog.changed.connect(self.settings_changed)
        self.settings_dialog.show()

    def digitize(self):
        self.canvas.setMapTool(self.tool)
        self.action_spline.setChecked(True)

    def is_active_layer_for_spline(self):
        layer = self.iface.activeLayer()
        if layer is None:
            return False
        if layer.type() != QgsMapLayerType.VectorLayer:
            return False
        if not layer.geometryType() in (
            QgsWkbTypes.LineGeometry,
            QgsWkbTypes.PolygonGeometry,
        ):
            return False
        return True

    def enable_action(self):
        self.action_spline.setEnabled(False)
        self.action_spline.setChecked(False)
        if self.is_active_layer_for_spline():
            if self.iface.activeLayer().isEditable():
                self.action_spline.setEnabled(True)

    def layer_changed(self):
        self.deactivate()
        self.tool.deactivate()
        self.enable_action()
        self.connect_layer()

    def connect_layer(self):
        self.disconnect_layer()
        if not self.is_active_layer_for_spline():
            return
        layer = self.iface.activeLayer()
        if layer is None:
            return
        self.connected_layer = layer
        layer.editingStopped.connect(self.enable_action)
        layer.editingStarted.connect(self.enable_action)

    def disconnect_layer(self):
        try:
            self.connected_layer.editingStopped.disconnect(self.enable_action)
            self.connected_layer.editingStarted.disconnect(self.enable_action)
        except (RuntimeError, AttributeError, TypeError):
            pass
        self.connected_layer = None

    def deactivate(self):
        self.tool.deactivate()
        self.action_spline.setChecked(False)

    def settings_changed(self):
        self.tool.refresh()
