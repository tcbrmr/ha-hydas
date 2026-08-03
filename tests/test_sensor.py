"""Tests for HyDAS sensor value derivation."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from custom_components.hydas.api import Measurement
from custom_components.hydas.const import DOMAIN
from custom_components.hydas.sensor import (
    HyDASAbsoluteWaterLevelSensor,
    HyDASReferenceElevationSensor,
    _absolute_water_level,
    _is_relative_water_level,
    _reference_elevation,
    async_setup_entry,
)


def _measurement(
    value=116.0,
    unit="cm",
    reference_value=14.980,
    reference_unit="m. ü. NN",
    parameter_id="W",
    observed_property=None,
):
    return Measurement(
        station={
            "id": "lingen",
            "referenceElevation": {
                "value": reference_value,
                "unit": "m",
                "unitDisplay": reference_unit,
            },
        },
        parameter={
            "id": parameter_id,
            "observedProperty": observed_property,
            "unitDisplay": unit,
        },
        value=value,
        timestamp="2026-08-03T19:15:00+02:00",
    )


def test_absolute_water_level_converts_centimetres_and_preserves_reference_unit():
    measurement = _measurement()

    assert _is_relative_water_level(measurement)
    assert _reference_elevation(measurement.station) == (14.980, "m. ü. NN")
    assert _absolute_water_level(measurement) == pytest.approx(16.140)


def test_absolute_water_level_accepts_standard_property_and_metres():
    measurement = _measurement(
        value=0.24,
        unit="m",
        reference_value=24.529,
        reference_unit="m. ü. NHN",
        parameter_id="water-level-rel-15min",
        observed_property="water-level-rel",
    )

    assert _is_relative_water_level(measurement)
    assert _absolute_water_level(measurement) == pytest.approx(24.769)


@pytest.mark.parametrize(
    "measurement",
    [
        _measurement(value=None),
        _measurement(unit="ft"),
        _measurement(reference_value=None),
        _measurement(parameter_id="Q"),
    ],
)
def test_invalid_or_unrelated_measurements_do_not_produce_absolute_level(measurement):
    assert _absolute_water_level(measurement) is None


async def test_setup_adds_raw_reference_and_absolute_water_level_sensors():
    measurement = _measurement()
    coordinator = MagicMock()
    coordinator.data = {measurement.key: measurement}
    coordinator.health_supported = False
    entry = MagicMock()
    entry.entry_id = "entry"
    hass = SimpleNamespace(data={DOMAIN: {entry.entry_id: coordinator}})
    added = []

    await async_setup_entry(hass, entry, added.extend)

    reference_sensor = next(
        entity for entity in added if isinstance(entity, HyDASReferenceElevationSensor)
    )
    absolute_sensor = next(
        entity for entity in added if isinstance(entity, HyDASAbsoluteWaterLevelSensor)
    )
    assert len(added) == 3
    assert reference_sensor.native_value == pytest.approx(14.980)
    assert reference_sensor.native_unit_of_measurement == "m. ü. NN"
    assert absolute_sensor.native_value == pytest.approx(16.140)
    assert absolute_sensor.native_unit_of_measurement == "m. ü. NN"
