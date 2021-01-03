from qgis.core import QgsProcessingProvider

from .processing_alg import Lines2SplinesProcessingAlgorithm


class Provider(QgsProcessingProvider):
    def loadAlgorithms(self, *args, **kwargs):
        self.addAlgorithm(Lines2SplinesProcessingAlgorithm())

    def id(self, *args, **kwargs):
        """The ID of your plugin, used for identifying the provider."""
        return "spline"

    def name(self, *args, **kwargs):
        """The human friendly name of your plugin in Processing."""
        return self.tr("Spline")

    def icon(self):
        """Should return a QIcon which is used for your provider inside the Processing toolbox."""
        return QgsProcessingProvider.icon(self)
