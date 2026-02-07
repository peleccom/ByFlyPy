"""Plotting module for ByFly statistics visualization."""

import calendar
import datetime
from collections.abc import Generator

try:
    import matplotlib as mpl
    import matplotlib.pylab as plt
except ImportError as err:
    raise ImportError("matplotlib is required for plotting") from err

mpl.rcParams["font.sans-serif"] = "Tahoma, Arial, DejaVu Serif"

_MONTHS = {
    1: "Января",
    2: "Февраля",
    3: "Марта",
    4: "Апреля",
    5: "Мая",
    6: "Июня",
    7: "Июля",
    8: "Августа",
    9: "Сентября",
    10: "Октября",
    11: "Ноября",
    12: "Декабря",
}


def _get_weekends(date: datetime.datetime) -> Generator[int, None, None]:
    """Get dates and return generator of weekend days in this month.

    Args:
        date: Date to get weekends for

    Yields:
        Day numbers that are weekends
    """
    if not isinstance(date, datetime.datetime):
        return

    try:
        for day_num in range(1, 32):
            day = date.replace(day=day_num)
            if day.weekday() > 4:
                yield day_num
    except ValueError:
        return


class Plotter:
    """Class for plotting ByFly statistics."""

    def __init__(self) -> None:
        pass

    def _get_traf_peaks(self, sessions: list) -> tuple[list[int], list[float], int]:
        """Get traffic data per day of month.

        Args:
            sessions: List of session objects

        Returns:
            Tuple of (days, traffic_values, max_day)
        """
        traffic_per_day: dict[int, float] = {}
        begin_date = datetime.datetime(sessions[0].begin.year, sessions[0].begin.month, 1)

        max_day = calendar.monthrange(begin_date.year, begin_date.month)[1]
        for day_num in range(1, max_day + 1):
            traffic_per_day[day_num] = 0.0

        for session in sessions:
            traffic_per_day[session.begin.day] += session.ingoing

        return list(traffic_per_day.keys()), list(traffic_per_day.values()), max_day

    def _get_time_peaks(self, sessions: list) -> tuple[list[int], list[float], int]:
        """Fill the month structure with connection time data.

        Args:
            sessions: List of session objects

        Returns:
            Tuple of (days, hours_with_minutes, max_day)
        """
        days: list[int] = []
        hours: list[float] = []

        begin_date = datetime.datetime(sessions[0].begin.year, sessions[0].begin.month, 1)

        minute_delta = datetime.timedelta(minutes=1)

        for session in sessions:
            x = begin_date
            while x < session.end:
                if session.begin < x < session.end:
                    days.append(x.day)
                    hours.append(x.hour + float(x.minute) / 60)
                x += minute_delta

        max_day = calendar.monthrange(begin_date.year, begin_date.month)[1]
        return days, hours, max_day

    def plot_time_allocation(
        self, sessions: list, fname: str | None = None, title: str | None = None, show: bool = True
    ) -> bool:
        """Plot time allocation graph.

        Args:
            sessions: List of session objects
            fname: Optional filename to save plot to
            title: Optional plot title
            show: Whether to display the plot

        Returns:
            True if successful, False otherwise
        """
        if not sessions:
            return False

        time_peaks = self._get_time_peaks(sessions)
        plt.clf()
        plt.plot(
            time_peaks[0],
            time_peaks[1],
            "b.",
            linewidth=1,
            label="Время использования соединения",
        )
        plt.grid(True)
        plt.xlabel(f"Дни {_MONTHS[sessions[0].begin.month].lower()}")
        plt.ylabel("Время")
        plt.legend(loc="best")
        _, la = plt.xticks(range(1, time_peaks[2] + 1))
        for day_num in _get_weekends(sessions[0].begin):
            la[day_num - 1].set_backgroundcolor("red")
        plt.yticks(range(24))

        if title:
            plt.title(title)

        if fname:
            try:
                plt.savefig(fname)
            except Exception as err:
                print(f"Exception: {err}")

        if show:
            plt.show()

        return True

    def plot_traf_allocation(
        self, sessions: list, fname: str | None = None, title: str | None = None, show: bool = True
    ) -> bool:
        """Plot traffic allocation graph.

        Args:
            sessions: List of session objects
            fname: Optional filename to save plot to
            title: Optional plot title
            show: Whether to display the plot

        Returns:
            True if successful, False otherwise
        """
        if not sessions:
            return False

        time_peaks = self._get_traf_peaks(sessions)
        fig = plt.figure()
        ax = fig.add_subplot(111)

        # Adjust x positions for bar chart
        for idx, val in enumerate(time_peaks[0]):
            time_peaks[0][idx] = val - 0.5

        rects = ax.bar(time_peaks[0], time_peaks[1], width=0.5, label="Трафик за день")

        # Add labels for bars
        for idx, rect in enumerate(rects):
            height = rect.get_height()
            traf = time_peaks[1][idx]
            if traf == 0:
                continue
            ax.text(
                rect.get_x() + rect.get_width() / 1.5,
                1.05 * height,
                f"{traf:.2f}",
                ha="center",
                va="bottom",
                rotation="vertical",
                color="green",
            )

        ax.grid(True)
        plt.xlabel(f"Дни {_MONTHS[sessions[0].begin.month].lower()}")
        plt.ylabel("MB")
        ax.legend(loc="best")
        _, la = plt.xticks(range(1, time_peaks[2] + 1))

        for day_num in _get_weekends(sessions[0].begin):
            la[day_num - 1].set_backgroundcolor("red")

        if title:
            plt.title(title)

        if fname:
            try:
                plt.savefig(fname)
            except Exception as err:
                print(f"Exception: {err}")

        if show:
            plt.show()

        return True
