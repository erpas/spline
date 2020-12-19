"""
/***************************************************************************
                                Spline Plugin
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
import os

SETTINGS_NAME = "SplinePlugin"

DEFAULT_TOLERANCE = 1.0
DEFAULT_TIGHTNESS = 0.5


def icon_path(icon_filename):
    plugin_dir = os.path.dirname(__file__)
    return os.path.join(plugin_dir, icon_filename)
