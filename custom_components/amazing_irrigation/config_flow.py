"""Config flow for the Amazing Irrigation integration.

The shell creates a single integration instance (a hub). Irrigation Zones are
added later through this entry's options/subentries; the shell only ensures the
integration can be installed and loaded safely.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN, INTEGRATION_TITLE


class AmazingIrrigationConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Amazing Irrigation."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step.

        Only a single Amazing Irrigation instance is supported; it acts as a
        hub that owns all Irrigation Zones.
        """
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title=INTEGRATION_TITLE, data={})

        return self.async_show_form(step_id="user")
