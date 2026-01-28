"""Serialization tests."""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core import ExpProgram, ProgStep, EXP_PROGRAM_SCHEMA
from jsonschema import validate


def test_prog_step_to_dict():
    """Test ProgStep to_dict."""
    step = ProgStep(
        step_id=1,
        step_type="配液",
        step_name="Test",
        solution_type="溶液A",
        pump_speed=10.0
    )
    data = step.to_dict()
    assert data["step_id"] == 1
    assert data["step_type"] == "配液"
    print("✓ ProgStep.to_dict() passed")


def test_prog_step_from_dict():
    """Test ProgStep from_dict."""
    data = {
        "step_id": 2,
        "step_type": "电化学",
        "step_name": "EChem Test",
        "potential": 0.5,
        "duration": 60.0,
        "ocpt_enabled": True
    }
    step = ProgStep.from_dict(data)
    assert step.step_id == 2
    assert step.step_type == "电化学"
    print("✓ ProgStep.from_dict() passed")


def test_exp_program_json():
    """Test ExpProgram JSON serialization."""
    program = ExpProgram(program_id="prog_001", program_name="Test Program")
    
    step1 = ProgStep(step_id=1, step_type="配液", step_name="Mix")
    step2 = ProgStep(step_id=2, step_type="电化学", step_name="EChem")
    
    program.add_step(step1)
    program.add_step(step2)
    
    json_str = program.to_json()
    data = json.loads(json_str)
    
    # Validate against schema
    validate(instance=data, schema=EXP_PROGRAM_SCHEMA)
    print("✓ JSON Schema validation passed")
    
    # Load back
    program2 = ExpProgram.from_json(json_str)
    assert program2.program_id == program.program_id
    assert len(program2.steps) == 2
    print("✓ ExpProgram JSON round-trip passed")


if __name__ == "__main__":
    test_prog_step_to_dict()
    test_prog_step_from_dict()
    test_exp_program_json()
    print("\n✓ All serialization tests passed!")
