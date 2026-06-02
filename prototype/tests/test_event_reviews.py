from mflog_proto.analysis.event_reviews import (
    EventReview,
    EventReviewState,
    build_event_reviews,
)


def test_build_event_reviews_defaults_to_unreviewed_without_notes():
    reviews = build_event_reviews(
        [
            {
                "name": "Battery low",
                "time_ms": 18320,
                "severity": "warning",
                "sensor": "Battery voltage",
                "value": 13.878,
                "condition": "value < 14.0",
            }
        ]
    )

    assert reviews == (
        EventReview(
            name="Battery low",
            time_ms=18320,
            severity="warning",
            sensor="Battery voltage",
            value=13.878,
            condition="value < 14.0",
            state=EventReviewState.UNREVIEWED,
            note="",
        ),
    )


def test_event_review_round_trips_project_json_shape():
    review = EventReview(
        name="G limit exceeded",
        time_ms=2500,
        severity="danger",
        sensor="ay",
        value=1.25,
        condition="abs(ay) > 1.0",
        state=EventReviewState.CONFIRMED,
        note="Corner entry spike",
    )

    restored = EventReview.from_dict(review.to_dict())

    assert restored == review
