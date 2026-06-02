from mflog_proto.analysis.event_reviews import EventReview, EventReviewState
from mflog_proto.analysis.segments import SegmentSummary
from mflog_proto.reporting.html_report import render_html_report


def test_render_html_report_contains_session_events_and_segments():
    html = render_html_report(
        session={
            "file_name": "demo.csv",
            "row_count": 101,
            "duration_seconds": 10.0,
            "sample_ms": 100,
            "event_count": 1,
        },
        selected_channels=("RPM", "TPS"),
        event_reviews=(
            EventReview(
                "Battery low",
                18320,
                "warning",
                "Battery voltage",
                13.878,
                "value < 14.0",
                EventReviewState.CONFIRMED,
                "Check wiring",
            ),
        ),
        segment_summaries=(
            SegmentSummary(
                name="Corner 1",
                start_ms=1000,
                end_ms=3000,
                duration_ms=2000,
                row_count=20,
                average_speed=32.5,
                max_speed=44.0,
                min_rpm=2500.0,
                max_rpm=7200.0,
                average_tps=55.0,
                max_abs_ax=0.8,
                max_abs_ay=1.1,
                min_battery_voltage=13.5,
            ),
        ),
        generated_at="2026-06-02 09:00:00",
    )

    assert "MF-LOG-ANALYZER v2 Report" in html
    assert "demo.csv" in html
    assert "Battery low" in html
    assert "Check wiring" in html
    assert "Corner 1" in html
    assert "RPM" in html
