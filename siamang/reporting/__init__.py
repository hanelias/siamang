"""Declarative reporting and visualization for survey data.

This module provides SPSS-like declarative tables and charts that
automatically leverage variable metadata (labels, scales, measurement levels)
to produce publication-ready outputs with minimal configuration.
"""

from siamang.reporting.tables import FreqTable, CrossTable, GroupMeanTable
from siamang.reporting.charts import BarChart, BoxPlot, HeatMap, ScatterPlot
from siamang.reporting.accessors import ReportAccessor, PlotAccessor

__all__ = [
    "FreqTable",
    "CrossTable",
    "GroupMeanTable",
    "BarChart",
    "BoxPlot",
    "HeatMap",
    "ScatterPlot",
    "ReportAccessor",
    "PlotAccessor",
]
