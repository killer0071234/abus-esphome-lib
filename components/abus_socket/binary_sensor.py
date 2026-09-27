import esphome.codegen as cg
from esphome.components import binary_sensor

from . import (
    CONF_ABUS_SOCKET_ID,
    CONF_INDEX,
    CONF_SOCKET_ID,
    RECEIVE_VALUE_SCHEMA,
    final_validate_receive_value,
)

DEPENDENCIES = ["abus_socket"]

# Publishes one bit value of a receive socket
CONFIG_SCHEMA = binary_sensor.binary_sensor_schema().extend(RECEIVE_VALUE_SCHEMA)

FINAL_VALIDATE_SCHEMA = final_validate_receive_value(["bit"])


async def to_code(config):
    parent = await cg.get_variable(config[CONF_ABUS_SOCKET_ID])
    sens = await binary_sensor.new_binary_sensor(config)
    cg.add(parent.add_binary_sensor(config[CONF_SOCKET_ID], config[CONF_INDEX], sens))
