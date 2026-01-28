"""JSON Schema definitions for validation."""

PROG_STEP_SCHEMA = {
    "type": "object",
    "required": ["step_id", "step_type", "step_name"],
    "properties": {
        "step_id": {"type": "integer"},
        "step_type": {"type": "string", "enum": ["配液", "电化学", "冲洗", "移液", "空白"]},
        "step_name": {"type": "string"},
        "solution_type": {"type": ["string", "null"]},
        "high_concentration": {"type": ["number", "null"]},
        "target_volume": {"type": ["number", "null"]},
        "volume_unit": {"type": ["string", "null"]},
        "pump_address": {"type": ["integer", "null"]},
        "pump_speed": {"type": ["number", "null"]},
        "potential": {"type": ["number", "null"]},
        "current_limit": {"type": ["number", "null"]},
        "duration": {"type": ["number", "null"]},
        "ocpt_enabled": {"type": "boolean"},
        "flush_pump_address": {"type": ["integer", "null"]},
        "flush_volume": {"type": ["number", "null"]},
        "flush_cycles": {"type": ["integer", "null"]},
        "flush_direction": {"type": ["string", "null"]},
        "source_well": {"type": ["string", "null"]},
        "target_well": {"type": ["string", "null"]},
        "transfer_volume": {"type": ["number", "null"]},
        "transfer_speed": {"type": ["number", "null"]},
        "delay_time": {"type": ["number", "null"]},
        "enabled": {"type": "boolean"},
        "notes": {"type": "string"}
    }
}

EXP_PROGRAM_SCHEMA = {
    "type": "object",
    "required": ["program_id", "program_name", "steps"],
    "properties": {
        "program_id": {"type": "string"},
        "program_name": {"type": "string"},
        "ocpt_enabled": {"type": "boolean"},
        "notes": {"type": "string"},
        "created_at": {"type": "string"},
        "modified_at": {"type": "string"},
        "steps": {
            "type": "array",
            "items": PROG_STEP_SCHEMA
        }
    }
}
