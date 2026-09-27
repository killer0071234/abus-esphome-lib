import esphome.codegen as cg
import esphome.config_validation as cv
import esphome.automation as automation
import esphome.final_validate as fv
from esphome.const import CONF_ID

# Existing definitions
abus_ns = cg.esphome_ns.namespace("abus_ns")
abus_socket = abus_ns.class_("abus_socket", cg.Component)

CONF_ABUS_SOCKET_ID = "abus_socket_id"
CONF_SOCKET_RECEIVE = "socket_receive"
CONF_SOCKET_ID = "socket_id"
CONF_LAYOUT = "layout"
CONF_INDEX = "index"

# Data types of a single socket tag
ab_type = cg.global_ns.enum("ab_type")
VALUE_TYPES = {
    "bit": (ab_type.AB_BIT, cv.Any(cv.boolean, cv.int_range(min=0, max=1))),
    "int": (ab_type.AB_INT, cv.int_range(min=-32768, max=32767)),
    "long": (ab_type.AB_LONG, cv.int_range(min=-2147483648, max=2147483647)),
    "real": (ab_type.AB_REAL, cv.float_),
}
TYPE_SIZES = {"bit": 1, "int": 2, "long": 4, "real": 4}
# A received packet may be at most 128 bytes: 14 bytes header, data, 2 bytes ts_id, 2 bytes crc
MAX_RECEIVE_DATA_SIZE = 128 - 18

# num_bit / num_int / num_long / num_real describe a layout in fixed order
FIXED_ORDER_COUNTS = (
    ("num_bit", "bit"),
    ("num_int", "int"),
    ("num_long", "long"),
    ("num_real", "real"),
)


def build_receive_layout(config):
    has_counts = any(key in config for key, _ in FIXED_ORDER_COUNTS)
    if CONF_LAYOUT in config and has_counts:
        raise cv.Invalid(
            "'layout' cannot be combined with 'num_bit', 'num_int', 'num_long' or 'num_real'"
        )
    if CONF_LAYOUT not in config:
        config[CONF_LAYOUT] = [
            type_
            for key, type_ in FIXED_ORDER_COUNTS
            for _ in range(config.get(key, 0))
        ]
    if not config[CONF_LAYOUT]:
        raise cv.Invalid("Socket needs a 'layout' with at least one data type")
    size = sum(TYPE_SIZES[type_] for type_ in config[CONF_LAYOUT])
    if size > MAX_RECEIVE_DATA_SIZE:
        raise cv.Invalid(
            f"Socket layout needs {size} bytes of data, maximum is {MAX_RECEIVE_DATA_SIZE}"
        )
    return config


def validate_unique_socket_ids(sockets):
    ids = [sock[CONF_SOCKET_ID] for sock in sockets]
    for socket_id in ids:
        if ids.count(socket_id) > 1:
            raise cv.Invalid(f"socket_id {socket_id} is configured more than once")
    return sockets


SOCKET_RECEIVE_SCHEMA = cv.All(
    cv.Schema(
        {
            cv.Required(CONF_SOCKET_ID): cv.int_range(min=1, max=255),
            cv.Optional(CONF_LAYOUT): cv.ensure_list(
                cv.one_of(*VALUE_TYPES, lower=True)
            ),
            **{
                cv.Optional(key): cv.int_range(min=0, max=MAX_RECEIVE_DATA_SIZE)
                for key, _ in FIXED_ORDER_COUNTS
            },
        }
    ),
    build_receive_layout,
)

CONFIG_SCHEMA = cv.COMPONENT_SCHEMA.extend(
    {
        cv.GenerateID(): cv.declare_id(abus_socket),
        cv.Optional(CONF_SOCKET_RECEIVE): cv.All(
            cv.ensure_list(SOCKET_RECEIVE_SCHEMA), validate_unique_socket_ids
        ),
    }
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    # Receive sockets: the data types in the order they are expected in the packet
    for sock in config.get(CONF_SOCKET_RECEIVE, []):
        for type_ in sock[CONF_LAYOUT]:
            cg.add(var.add_receive_value(sock[CONF_SOCKET_ID], VALUE_TYPES[type_][0]))


# Schema for sensor platforms that publish one value of a receive socket
RECEIVE_VALUE_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_ABUS_SOCKET_ID): cv.use_id(abus_socket),
        cv.Required(CONF_SOCKET_ID): cv.int_range(min=1, max=255),
        cv.Required(CONF_INDEX): cv.int_range(min=0, max=MAX_RECEIVE_DATA_SIZE - 1),
    }
)


def final_validate_receive_value(allowed_types):
    """Check that socket_id and index point to a value of an allowed type."""

    def validator(config):
        full_config = fv.full_config.get()
        path = full_config.get_path_for_id(config[CONF_ABUS_SOCKET_ID])[:-1]
        parent = full_config.get_config_for_path(path)
        sockets = {
            sock[CONF_SOCKET_ID]: sock for sock in parent.get(CONF_SOCKET_RECEIVE, [])
        }
        socket_id = config[CONF_SOCKET_ID]
        if socket_id not in sockets:
            raise cv.Invalid(
                f"socket_id {socket_id} is not configured under 'socket_receive'",
                path=[CONF_SOCKET_ID],
            )
        layout = sockets[socket_id][CONF_LAYOUT]
        index = config[CONF_INDEX]
        if index >= len(layout):
            raise cv.Invalid(
                f"index {index} is out of range, socket {socket_id} has "
                f"{len(layout)} values (index 0 to {len(layout) - 1})",
                path=[CONF_INDEX],
            )
        if layout[index] not in allowed_types:
            raise cv.Invalid(
                f"index {index} of socket {socket_id} is a '{layout[index]}', "
                f"expected {' or '.join(allowed_types)}",
                path=[CONF_INDEX],
            )
        return config

    return validator


# One entry of the `values` list, e.g. `- real: 21.5`
VALUE_SCHEMA = cv.All(
    cv.Schema(
        {
            cv.Optional(key): cv.templatable(validator)
            for key, (_, validator) in VALUE_TYPES.items()
        }
    ),
    cv.has_exactly_one_key(*VALUE_TYPES),
)

FIXED_ORDER_KEYS = ("bits", "ints", "longs", "reals")


def validate_send_data(config):
    if "values" in config and any(key in config for key in FIXED_ORDER_KEYS):
        raise cv.Invalid(
            "'values' cannot be combined with 'bits', 'ints', 'longs' or 'reals'"
        )
    return config


# Action registration
@automation.register_action(
    "abus_socket.send_data",
    abus_ns.class_("SendDataAction", automation.Action),
    cv.All(
        cv.Schema(
            {
                cv.Required(CONF_ID): cv.use_id(abus_socket),
                cv.Required("socket_id"): cv.templatable(cv.int_range(min=1, max=255)),
                cv.Optional("values"): cv.All(
                    cv.ensure_list(VALUE_SCHEMA), cv.Length(min=1)
                ),
                cv.Optional("bits"): cv.templatable(cv.ensure_list(cv.uint8_t)),
                cv.Optional("ints"): cv.templatable(cv.ensure_list(cv.int_)),
                cv.Optional("longs"): cv.templatable(cv.ensure_list(cv.int_)),
                cv.Optional("reals"): cv.templatable(cv.ensure_list(cv.float_)),
            }
        ),
        validate_send_data,
    ),
    synchronous=True,
)
async def abus_send_data_to_code(config, action_id, template_arg, args):
    var = await cg.get_variable(config[CONF_ID])
    rhs = cg.new_Pvariable(action_id, template_arg, var)

    # socket_id
    if cg.is_template(config["socket_id"]):
        template_ = await cg.templatable(config["socket_id"], args, cg.int_)
        cg.add(rhs.set_socket_id(template_))
    else:
        cg.add(rhs.set_socket_id_static(config["socket_id"]))

    # Arrays (reals, ints, etc.)
    for key, cg_type, setter in [
        ("reals", cg.float_, "reals"),
        ("bits", cg.uint8, "bits"),
        ("ints", cg.int16, "ints"),
        ("longs", cg.int32, "longs"),
    ]:
        if key in config:
            value = config[key]
            if cg.is_template(value):
                template_ = await cg.templatable(
                    value, args, cg.std_vector.template(cg_type)
                )
                cg.add(getattr(rhs, f"set_{setter}")(template_))
            else:
                # IMPORTANT: explicit cast to std_vector for the C++ code
                vector_data = cg.std_vector.template(cg_type)(value)
                cg.add(getattr(rhs, f"set_{setter}_static")(vector_data))

    # Typed tags, sent in list order
    for entry in config.get("values", []):
        ((key, value),) = entry.items()
        if cg.is_template(value):
            value = await cg.templatable(value, args, cg.double)
        cg.add(rhs.add_value(VALUE_TYPES[key][0], value))

    return rhs
