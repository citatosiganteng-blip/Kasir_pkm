from datetime import datetime
from types import SimpleNamespace

from PyQt5.QtWidgets import QApplication
import pytest

from ui.laporan.laporan_page import (
    BarChartWidget,
    aggregate_intraday_revenue,
)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_intraday_revenue_uses_transaction_minute_and_sums_same_minute():
    transactions = [
        SimpleNamespace(
            tanggal=datetime(2026, 11, 13, 17, 46, 10),
            total=1000,
        ),
        SimpleNamespace(
            tanggal=datetime(2026, 11, 13, 17, 45, 59),
            total=2500,
        ),
        SimpleNamespace(
            tanggal=datetime(2026, 11, 13, 17, 45, 2),
            total=1500,
        ),
    ]

    assert aggregate_intraday_revenue(transactions) == [
        ("17:45", 4000.0),
        ("17:46", 1000.0),
    ]


def test_intraday_chart_positions_bar_at_exact_transaction_time(qapp, test_db):
    chart = BarChartWidget()
    chart.resize(1000, 350)
    chart.set_data([("17:45", 4000.0)], time_axis=True)
    chart.show()
    qapp.processEvents()

    rect, label, _ = chart._bar_rects[0]
    chart_width = chart.width() - 68 - 24
    expected_x = 68 + ((17 * 60 + 45 - 8 * 60) / (20 * 60 - 8 * 60)) * chart_width

    assert label == "17:45"
    assert abs(rect.center().x() - expected_x) < 1
    chart.close()
