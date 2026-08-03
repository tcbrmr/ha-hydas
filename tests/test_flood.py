"""Tests for LHP flood-alert retrieval and spatial matching."""

from typing import Any

from custom_components.hydas.flood import FloodAlert, LHPClient, alert_applies_to_station


class FakeResponse:
    def __init__(self, payload=None, status=200, headers=None):
        self.payload = payload
        self.status = status
        self.headers = headers or {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    def raise_for_status(self):
        return None

    async def json(self, **kwargs):
        return self.payload


class FakeSession:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def _alert(geometry_type="Polygon", coordinates=None, **changes):
    values = {
        "id": "NI_ems",
        "geometry_type": geometry_type,
        "coordinates": coordinates
        or [[[7.2, 52.4], [7.4, 52.4], [7.4, 52.6], [7.2, 52.6], [7.2, 52.4]]],
        "area_description": "Ems bei Lingen",
        "area_type": "Region",
        "headline": "Hochwasserwarnung",
        "link": "https://example.test/warning",
        "lhp_class": 4,
        "class_name": "Hochwasser",
        "identifier": "LHP.NI.ems",
        "sender_name": "NLWKN",
        "sent": "2026-08-03 20:00:00",
        "onset": "2026-08-03 19:00:00",
        "expires": "2026-08-04 08:00:00",
        "severity": "Moderate",
        "certainty": "Observed",
        "description": "Hochwasser an der Ems",
        "instruction": "Meiden Sie das Gewässer.",
    }
    values.update(changes)
    return FloodAlert(**values)


def _lingen_station():
    return {
        "id": "lingen",
        "waterBodyName": "Ems",
        "coordinates": {"lat": 52.496589, "lon": 7.288342},
    }


async def test_client_normalizes_cap_alert_and_uses_etag():
    payload = {
        "status": "success",
        "updated": "2026-08-03T19:13:47+01:00",
        "source": "https://www.hochwasserzentralen.de",
        "licence": "CC BY 4.0",
        "data": [
            {
                "id": "NI_ems",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": _alert().coordinates,
                },
                "areaDesc": "Ems bei Lingen",
                "areaType": "Region",
                "alertHeadline": "Hochwasserwarnung",
                "alertLink": "https://example.test/warning",
                "lhpClass": "4",
                "lhpClassName": "Hochwasser",
                "cap": {
                    "identifier": "LHP.NI.ems",
                    "sent": "2026-08-03 20:00:00",
                    "info": {
                        "headline": "Hochwasserwarnung",
                        "sendername": "NLWKN",
                        "onset": "2026-08-03 19:00:00",
                        "expires": "2026-08-04 08:00:00",
                        "severity": "Moderate",
                        "certainty": "Observed",
                        "description": "Hochwasser an der Ems",
                        "instruction": "Meiden Sie das Gewässer.",
                    },
                },
            }
        ],
    }
    session = FakeSession(
        FakeResponse(payload, headers={"ETag": '"current"'}),
        FakeResponse(status=304),
    )
    client = LHPClient(session)

    first = await client.async_get_alerts({"DE-NI"})
    second = await client.async_get_alerts({"DE-NI"})

    assert first is second
    assert first.alerts == (_alert(),)
    assert session.calls[0][1]["params"] == {"cap": "true", "states": "NI"}
    assert session.calls[1][1]["headers"]["If-None-Match"] == '"current"'


def test_polygon_alert_applies_when_station_point_is_inside():
    assert alert_applies_to_station(_alert(), _lingen_station())


def test_polygon_alert_does_not_apply_when_station_point_is_outside():
    bavaria = _alert(
        coordinates=[[[10.6, 48.8], [11.2, 48.8], [11.2, 49.2], [10.6, 49.2], [10.6, 48.8]]]
    )

    assert not alert_applies_to_station(bavaria, _lingen_station())


def test_river_line_requires_matching_water_and_close_distance():
    ems_line = _alert(
        geometry_type="LineString",
        coordinates=[[7.28, 52.48], [7.29, 52.51]],
        area_type="River",
    )
    other_river = _alert(
        geometry_type="LineString",
        coordinates=ems_line.coordinates,
        area_description="Hase bei Lingen",
        description="Hochwasser an der Hase",
    )

    assert alert_applies_to_station(ems_line, _lingen_station())
    assert not alert_applies_to_station(other_river, _lingen_station())
