"""Config flow for GoodWe Inverter AA55 over RS485 integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult

from .const import DEFAULT_NAME, DOMAIN
from .exceptions import InverterError
from .inverter import Inverter

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {vol.Required(CONF_HOST): str, vol.Required(CONF_PORT): int}
)


class GoodweAA55FlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for GoodWe Inverter AA55 over RS485."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            try:
                inverter = Inverter(host, port)
            except InverterError:
                errors[CONF_HOST] = "connection_error"
            else:
                await self.async_set_unique_id(inverter.serial_number)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=DEFAULT_NAME, data={CONF_HOST: host, CONF_PORT: port}
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
