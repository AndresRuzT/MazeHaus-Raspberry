from __future__ import annotations

from fingermaze.core.types import Viewport
from fingermaze.input.mailbox import LatestValueMailbox
from fingermaze.input.mapping import ActiveRegion, CoordinateMapper


def test_latest_value_mailbox() -> None:
    mb: LatestValueMailbox[str] = LatestValueMailbox()
    assert mb.read_value() is None

    mb.publish("first")
    mb.publish("second")
    val, rev = mb.read()
    assert val == "second"
    assert rev == 2
    assert mb.read_value() == "second"


def test_coordinate_mapping() -> None:
    viewport = Viewport(x=100, y=50, width=800, height=600)
    region = ActiveRegion(min_x=0.0, max_x=1.0, min_y=0.0, max_y=1.0)
    mapper = CoordinateMapper(viewport=viewport, active_region=region)

    pt_center = mapper.map_to_viewport(0.5, 0.5)
    assert pt_center.x == 100 + 400
    assert pt_center.y == 50 + 300

    pt_top_left = mapper.map_to_viewport(0.0, 0.0)
    assert pt_top_left.x == 100
    assert pt_top_left.y == 50
