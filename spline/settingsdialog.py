"""
/***************************************************************************
  Spline plugin SettingsDialog
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
import os
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, pyqtSignal, QSettings
from qgis.PyQt.QtWidgets import QDialogButtonBox

from .utils import DEFAULT_TIGHTNESS, DEFAULT_TOLERANCE, SETTINGS_NAME

base_dir = os.path.dirname(__file__)
uicls_log, basecls_log = uic.loadUiType(os.path.join(base_dir, "ui_settingsdialog.ui"))


class SettingsDialog(uicls_log, basecls_log):

    changed = pyqtSignal()

    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.setupUi(self)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.tolerance = QSettings().value(SETTINGS_NAME + "/tolerance", DEFAULT_TOLERANCE, float)
        self.splineToleranceSpinBox.setValue(self.tolerance)

        self.tightness = QSettings().value(SETTINGS_NAME + "/tightness", DEFAULT_TIGHTNESS, float)
        self.splineTightnessSpinBox.setValue(self.tightness)

        self.buttonBox.button(QDialogButtonBox.Ok).clicked.connect(self.ok)
        self.buttonBox.button(QDialogButtonBox.Cancel).clicked.connect(self.cancel)
        self.buttonBox.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self.defaults)
        self.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(self.apply)

    def ok(self):
        self.apply()
        self.close()

    def apply(self):
        QSettings().setValue(SETTINGS_NAME + "/tolerance", self.splineToleranceSpinBox.value())
        QSettings().setValue(SETTINGS_NAME + "/tightness", self.splineTightnessSpinBox.value())
        self.changed.emit()

    def cancel(self):
        self.close()

    def defaults(self):
        self.splineToleranceSpinBox.setValue(DEFAULT_TOLERANCE)
        self.splineTightnessSpinBox.setValue(DEFAULT_TIGHTNESS)
