"""Generic Watering Actuator configuration and call generation.

An actuator is how a zone physically starts and stops watering. To stay generic
the integration supports three modes — a switch, a service call, or a script —
each optionally injecting the bounded Watering Volume. The *call-spec builders*
here are pure (no Home Assistant dependency) so payload generation can be tested
directly; :func:`async_execute` performs the resulting call.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from homeassistant.core import HomeAssistant

from .const import (
    ACTUATOR_NONE,
    ACTUATOR_SCRIPT,
    ACTUATOR_SERVICE,
    ACTUATOR_SWITCH,
    CONF_ACTUATOR_START_DATA,
    CONF_ACTUATOR_START_SCRIPT,
    CONF_ACTUATOR_START_SERVICE,
    CONF_ACTUATOR_STOP_DATA,
    CONF_ACTUATOR_STOP_SCRIPT,
    CONF_ACTUATOR_STOP_SERVICE,
    CONF_ACTUATOR_SWITCH,
    CONF_ACTUATOR_TYPE,
    CONF_VOLUME_FIELD,
    CONF_VOLUME_SENSOR,
    CONF_WATERING_SENSOR,
    DEFAULT_VOLUME_FIELD,
)


@dataclass(frozen=True)
class CallSpec:
    """A resolved Home Assistant service call."""

    domain: str
    service: str
    data: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ActuatorConfig:
    """A zone's Watering Actuator configuration."""

    actuator_type: str = ACTUATOR_NONE
    switch: str | None = None
    start_service: str | None = None
    start_data: dict = field(default_factory=dict)
    stop_service: str | None = None
    stop_data: dict = field(default_factory=dict)
    start_script: str | None = None
    stop_script: str | None = None
    volume_field: str = DEFAULT_VOLUME_FIELD
    watering_sensor: str | None = None
    volume_sensor: str | None = None

    @classmethod
    def from_record(cls, record: dict) -> ActuatorConfig:
        """Build an ActuatorConfig from a stored zone options record."""
        return cls(
            actuator_type=record.get(CONF_ACTUATOR_TYPE, ACTUATOR_NONE) or ACTUATOR_NONE,
            switch=record.get(CONF_ACTUATOR_SWITCH) or None,
            start_service=record.get(CONF_ACTUATOR_START_SERVICE) or None,
            start_data=dict(record.get(CONF_ACTUATOR_START_DATA) or {}),
            stop_service=record.get(CONF_ACTUATOR_STOP_SERVICE) or None,
            stop_data=dict(record.get(CONF_ACTUATOR_STOP_DATA) or {}),
            start_script=record.get(CONF_ACTUATOR_START_SCRIPT) or None,
            stop_script=record.get(CONF_ACTUATOR_STOP_SCRIPT) or None,
            volume_field=record.get(CONF_VOLUME_FIELD) or DEFAULT_VOLUME_FIELD,
            watering_sensor=record.get(CONF_WATERING_SENSOR) or None,
            volume_sensor=record.get(CONF_VOLUME_SENSOR) or None,
        )

    @property
    def can_water(self) -> bool:
        """Whether a usable start path is configured."""
        return build_start_call(self, 0.0) is not None

    @property
    def can_stop(self) -> bool:
        """Whether an explicit stop path is configured."""
        return build_stop_call(self) is not None

    @property
    def has_feedback(self) -> bool:
        """Whether any confirmation feedback is configured."""
        return self.watering_sensor is not None or self.volume_sensor is not None


def _parse_service(value: str | None) -> tuple[str, str] | None:
    """Split a ``domain.service`` string into its parts."""
    if not value or "." not in value:
        return None
    domain, _, service = value.partition(".")
    if not domain or not service:
        return None
    return domain, service


def build_start_call(actuator: ActuatorConfig, volume_liters: float) -> CallSpec | None:
    """Build the call that starts watering, injecting the bounded volume.

    Returns ``None`` when the actuator has no usable start path configured.
    """
    if actuator.actuator_type == ACTUATOR_SWITCH and actuator.switch:
        return CallSpec("switch", "turn_on", {"entity_id": actuator.switch})

    if actuator.actuator_type == ACTUATOR_SERVICE:
        parsed = _parse_service(actuator.start_service)
        if parsed is None:
            return None
        data = dict(actuator.start_data)
        if actuator.volume_field:
            data[actuator.volume_field] = volume_liters
        return CallSpec(parsed[0], parsed[1], data)

    if actuator.actuator_type == ACTUATOR_SCRIPT and actuator.start_script:
        variables = {actuator.volume_field: volume_liters} if actuator.volume_field else {}
        return CallSpec(
            "script",
            "turn_on",
            {"entity_id": actuator.start_script, "variables": variables},
        )

    return None


def build_stop_call(actuator: ActuatorConfig) -> CallSpec | None:
    """Build the call that stops watering, or ``None`` when unsupported."""
    if actuator.actuator_type == ACTUATOR_SWITCH and actuator.switch:
        return CallSpec("switch", "turn_off", {"entity_id": actuator.switch})

    if actuator.actuator_type == ACTUATOR_SERVICE:
        parsed = _parse_service(actuator.stop_service)
        if parsed is None:
            return None
        return CallSpec(parsed[0], parsed[1], dict(actuator.stop_data))

    if actuator.actuator_type == ACTUATOR_SCRIPT and actuator.stop_script:
        return CallSpec("script", "turn_on", {"entity_id": actuator.stop_script})

    return None


async def async_execute(hass: HomeAssistant, spec: CallSpec) -> None:
    """Execute a resolved call spec."""
    await hass.services.async_call(
        spec.domain, spec.service, dict(spec.data), blocking=True
    )
