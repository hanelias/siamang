"""Accessor classes for convenient reporting from SurveyData.

These provide a fluent API:
    data.report.freq("it_role")
    data.report.crosstab("it_role", "remote_freq")
    data.report.means("autonomy", by="remote_freq")

    data.plot.bar("it_role")
    data.plot.boxplot("autonomy", by="remote_freq")
    data.plot.heatmap(["surv_keystroke", "surv_camera"], by="remote_freq")
    data.plot.scatter("autonomy", "satisfaction")
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from siamang.data.survey_data import SurveyData
    from siamang.reporting.tables import FreqTable, CrossTable, GroupMeanTable
    from siamang.reporting.charts import BarChart, BoxPlot, HeatMap, ScatterPlot


class ReportAccessor:
    """Table-generation accessor attached to SurveyData.

    Usage:
        table = data.report.freq("remote_freq")
        print(table.to_markdown())
    """

    def __init__(self, data: "SurveyData") -> None:
        self._data = data

    def freq(self, column: str, *, exclude_missing: bool = True, sort: str = "value") -> "FreqTable":
        """Generate a frequency distribution table.

        Parameters
        ----------
        column : str
            Variable name to tabulate.
        exclude_missing : bool
            Exclude NaN values from the base (default True).
        sort : str
            Sort order: "value", "freq", or "label".
        """
        from siamang.reporting.tables import FreqTable

        return FreqTable(data=self._data, column=column, exclude_missing=exclude_missing, sort=sort)

    def crosstab(
        self,
        row: str,
        col: str,
        *,
        pct: str = "none",
        test: bool = True,
    ) -> "CrossTable":
        """Generate a cross-tabulation table.

        Parameters
        ----------
        row : str
            Row variable (independent).
        col : str
            Column variable (dependent).
        pct : str
            Percentage direction: "none", "row", "col", "total".
        test : bool
            Run Chi-square test and report statistics.
        """
        from siamang.reporting.tables import CrossTable

        return CrossTable(data=self._data, row=row, col=col, pct=pct, test=test)

    def means(
        self,
        column: str,
        *,
        by: str,
        test: bool = True,
    ) -> "GroupMeanTable":
        """Generate a grouped means comparison table.

        Parameters
        ----------
        column : str
            Continuous dependent variable.
        by : str
            Categorical grouping variable.
        test : bool
            Run appropriate significance test.
        """
        from siamang.reporting.tables import GroupMeanTable

        return GroupMeanTable(data=self._data, column=column, by=by, test=test)


class PlotAccessor:
    """Chart-generation accessor attached to SurveyData.

    Usage:
        data.plot.bar("it_role")
        data.plot.boxplot("autonomy", by="remote_freq")
    """

    def __init__(self, data: "SurveyData") -> None:
        self._data = data

    def bar(
        self,
        column: str,
        *,
        by: str | None = None,
        horizontal: bool = False,
        show_values: bool = True,
        figsize: tuple[float, float] = (10, 6),
        palette: str = "muted",
        title: str | None = None,
    ) -> "BarChart":
        """Create a bar chart.

        Parameters
        ----------
        column : str
            Variable to plot.
        by : str | None
            If specified, plots grouped means.
        horizontal : bool
            Horizontal bars.
        show_values : bool
            Annotate bars with values.
        """
        from siamang.reporting.charts import BarChart

        return BarChart(
            data=self._data, column=column, by=by,
            horizontal=horizontal, show_values=show_values,
            figsize=figsize, palette=palette, title=title,
        )

    def boxplot(
        self,
        column: str,
        *,
        by: str,
        show_points: bool = False,
        figsize: tuple[float, float] = (10, 6),
        palette: str = "muted",
        title: str | None = None,
    ) -> "BoxPlot":
        """Create a box plot comparing distributions across groups.

        Parameters
        ----------
        column : str
            Continuous dependent variable.
        by : str
            Categorical grouping variable.
        show_points : bool
            Overlay individual data points.
        """
        from siamang.reporting.charts import BoxPlot

        return BoxPlot(
            data=self._data, column=column, by=by,
            show_points=show_points,
            figsize=figsize, palette=palette, title=title,
        )

    def heatmap(
        self,
        columns: list[str],
        *,
        by: str | None = None,
        annot: bool = True,
        cmap: str = "YlOrRd",
        vmin: float | None = None,
        vmax: float | None = None,
        figsize: tuple[float, float] = (10, 6),
        title: str | None = None,
    ) -> "HeatMap":
        """Create a heatmap.

        Parameters
        ----------
        columns : list[str]
            Variables to include.
        by : str | None
            If specified, plots grouped means. Otherwise, correlation matrix.
        """
        from siamang.reporting.charts import HeatMap

        return HeatMap(
            data=self._data, columns=columns, by=by,
            annot=annot, cmap=cmap, vmin=vmin, vmax=vmax,
            figsize=figsize, title=title,
        )

    def scatter(
        self,
        x: str,
        y: str,
        *,
        hue: str | None = None,
        trendline: bool = True,
        figsize: tuple[float, float] = (10, 6),
        palette: str = "muted",
        title: str | None = None,
    ) -> "ScatterPlot":
        """Create a scatter plot.

        Parameters
        ----------
        x : str
            X-axis variable.
        y : str
            Y-axis variable.
        hue : str | None
            Optional grouping variable for color.
        trendline : bool
            Add linear regression trendline.
        """
        from siamang.reporting.charts import ScatterPlot

        return ScatterPlot(
            data=self._data, x=x, y=y, hue=hue,
            trendline=trendline,
            figsize=figsize, palette=palette, title=title,
        )
