import esphome.codegen as cg
import esphome.config_validation as cv
import esphome.automation as automation
from esphome.const import CONF_ID

# Vorhandene Definitionen
abus_ns = cg.esphome_ns.namespace("abus_ns")
abus_socket = abus_ns.class_("abus_socket", cg.Component)

# Hilfs-Schema für die Sub-Konfigurationen
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

    # Werte für socket_receive übergeben
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


# Registrierung der Action
@automation.register_action(
    "abus_socket.send_data",
    abus_ns.class_("SendDataAction", automation.Action),
    cv.Schema(
        {
            cv.Required(CONF_ID): cv.use_id(abus_socket),
            cv.Required("socket_id"): cv.templatable(cv.int_range(min=1)),
            cv.Optional("bits"): cv.templatable(cv.ensure_list(cv.uint8_t)),
            cv.Optional("ints"): cv.templatable(cv.ensure_list(cv.int_)),
            cv.Optional("longs"): cv.templatable(cv.ensure_list(cv.int_)),
            cv.Optional("reals"): cv.templatable(cv.ensure_list(cv.float_)),
        }
    ),
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
                # WICHTIG: Explizites Casting in einen std_vector für den C++ Code
                vector_data = cg.std_vector.template(cg_type)(value)
                cg.add(getattr(rhs, f"set_{setter}_static")(vector_data))

    return rhs
