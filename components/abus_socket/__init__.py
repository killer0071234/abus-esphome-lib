import esphome.codegen as cg
import esphome.config_validation as cv
import esphome.automation as automation
from esphome.const import CONF_ID

# Existing definitions
abus_ns = cg.esphome_ns.namespace("abus_ns")
abus_socket = abus_ns.class_("abus_socket", cg.Component)

# Helper schema for the sub-configurations
SOCKET_STRUCT_SCHEMA = cv.Schema(
    {
        cv.Required("socket_id"): cv.templatable(cv.int_range(min=1)),
        cv.Optional("num_bit", default=0): cv.int_,
        cv.Optional("num_int", default=0): cv.int_,
        cv.Optional("num_long", default=0): cv.int_,
        cv.Optional("num_real", default=0): cv.int_,
    }
)

CONFIG_SCHEMA = cv.COMPONENT_SCHEMA.extend(
    {
        cv.GenerateID(): cv.declare_id(abus_socket),
        cv.Optional("socket_receive"): SOCKET_STRUCT_SCHEMA,
    }
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    # Pass the socket_receive values
    if "socket_receive" in config:
        recv_cfg = config["socket_receive"]
        cg.add(
            var.set_socket_receive_config(
                recv_cfg["socket_id"],
                recv_cfg["num_bit"],
                recv_cfg["num_int"],
                recv_cfg["num_long"],
                recv_cfg["num_real"],
            )
        )


# Data types of a single socket tag
ab_type = cg.global_ns.enum("ab_type")
VALUE_TYPES = {
    "bit": (ab_type.AB_BIT, cv.Any(cv.boolean, cv.int_range(min=0, max=1))),
    "int": (ab_type.AB_INT, cv.int_range(min=-32768, max=32767)),
    "long": (ab_type.AB_LONG, cv.int_range(min=-2147483648, max=2147483647)),
    "real": (ab_type.AB_REAL, cv.float_),
}

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
                cv.Required("socket_id"): cv.templatable(cv.int_range(min=1)),
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
