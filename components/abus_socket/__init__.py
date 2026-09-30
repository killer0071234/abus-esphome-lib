import esphome.codegen as cg
import esphome.config_validation as cv
import esphome.automation as automation
from esphome.const import CONF_ID, CONF_TRIGGER_ID

# Existing definitions
abus_ns = cg.esphome_ns.namespace("abus_ns")
abus_socket = abus_ns.class_("abus_socket", cg.Component)
ab_socket_const_ref = cg.global_ns.struct("ab_socket").operator("ref").operator("const")
ReceiveTrigger = abus_ns.class_(
    "ReceiveTrigger", automation.Trigger.template(ab_socket_const_ref)
)

# Helper schema for the sub-configurations
SOCKET_STRUCT_SCHEMA = cv.Schema(
    {
        cv.Required("socket_id"): cv.int_range(min=1, max=255),
        cv.Optional("num_bit", default=0): cv.int_range(min=0, max=100),
        cv.Optional("num_int", default=0): cv.int_range(min=0, max=100),
        cv.Optional("num_long", default=0): cv.int_range(min=0, max=100),
        cv.Optional("num_real", default=0): cv.int_range(min=0, max=100),
        cv.Optional("on_receive"): automation.validate_automation(
            {
                cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(ReceiveTrigger),
            }
        ),
    }
)


def _validate_unique_socket_ids(sockets):
    ids = [sock["socket_id"] for sock in sockets]
    for socket_id in ids:
        if ids.count(socket_id) > 1:
            raise cv.Invalid(f"socket_id {socket_id} is configured more than once")
    return sockets


CONFIG_SCHEMA = cv.COMPONENT_SCHEMA.extend(
    {
        cv.GenerateID(): cv.declare_id(abus_socket),
        cv.Optional("socket_receive"): cv.All(
            cv.ensure_list(SOCKET_STRUCT_SCHEMA), _validate_unique_socket_ids
        ),
    }
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    # Pass the socket_receive values
    for recv_cfg in config.get("socket_receive", []):
        cg.add(
            var.add_socket_receive_config(
                recv_cfg["socket_id"],
                recv_cfg["num_bit"],
                recv_cfg["num_int"],
                recv_cfg["num_long"],
                recv_cfg["num_real"],
            )
        )

        # Automations for this socket (x = the received ab_socket)
        for conf in recv_cfg.get("on_receive", []):
            trigger = cg.new_Pvariable(
                conf[CONF_TRIGGER_ID], var, recv_cfg["socket_id"]
            )
            await automation.build_automation(
                trigger, [(ab_socket_const_ref, "x")], conf
            )


# Action registration
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

    return rhs
