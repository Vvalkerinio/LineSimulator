from src.core.station_reservation_service import StationReservationService


def test_provisional_station_release_can_be_rescheduled_and_finalized():
    reservations = StationReservationService()
    assert reservations.reserve(8, 1, 100.0, source="provisional_transport")

    reservations.plan_release_at(8, 1, 200.0)
    assert not reservations.can_reserve(8, 2, 199.0)

    reservations.plan_release_at(8, 1, 220.0)
    assert not reservations.can_reserve(8, 2, 219.0)
    assert reservations.can_reserve(8, 2, 220.0)

    reservations.release_at(8, 1, 220.0)
    reservation = reservations.active_reservations()[0]
    assert reservation.end_time == 220.0
    assert not reservation.release_is_provisional


def test_provisional_target_reservation_tracks_replanned_drop_time():
    reservations = StationReservationService()
    assert reservations.update_open_reservation(
        14,
        1,
        100.0,
        source="provisional_transport",
    )
    assert reservations.update_open_reservation(
        14,
        1,
        150.0,
        source="provisional_transport",
    )

    assert reservations.can_reserve(14, 2, 149.0)
    assert not reservations.can_reserve(14, 2, 150.0)
    assert reservations.active_reservations()[0].start_time == 150.0


def test_committing_provisional_target_uses_final_drop_time():
    reservations = StationReservationService()
    assert reservations.update_open_reservation(
        14,
        1,
        150.0,
        source="provisional_transport",
    )

    assert reservations.reserve(
        14,
        1,
        160.0,
        source="scheduled_transport",
    )

    reservation = reservations.active_reservations()[0]
    assert reservation.start_time == 160.0
    assert reservation.source == "scheduled_transport"


def test_cancel_provisional_plan_restores_source_and_removes_target():
    reservations = StationReservationService()
    assert reservations.reserve(8, 1, 100.0, source="scheduled_transport")
    assert reservations.update_open_reservation(
        14,
        1,
        200.0,
        source="provisional_transport",
    )
    reservations.plan_release_at(8, 1, 150.0)

    reservations.cancel_provisional_release(8, 1)
    reservations.cancel_provisional_reservation(14, 1)

    assert not reservations.can_reserve(8, 2, 500.0)
    assert reservations.can_reserve(14, 2, 200.0)
