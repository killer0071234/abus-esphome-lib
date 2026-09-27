import esphome.codegen as cg
from esphome.components import sensor

from . import (
    CONF_ABUS_SOCKET_ID,
    CONF_INDEX,
    CONF_SOCKET_ID,
    RECEIVE_VALUE_SCHEMA,
    final_validate_receive_value,
)

DEPENDENCIES = ["abus_socket"]

# Publishes one int, long or real value of a receive socket
CONFIG_SCHEMA = sensor.sensor_schema().extend(RECEIVE_VALUE_SCHEMA)

FINAL_VALIDATE_SCHEMA = final_validate_receive_value(["int", "long", "real"])


async def to_code(config):
    parent = await cg.get_variable(config[CONF_ABUS_SOCKET_ID])
    sens = await sensor.new_sensor(config)
    cg.add(parent.add_sensor(config[CONF_SOCKET_ID], config[CONF_INDEX], sens))
