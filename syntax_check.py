import py_compile
import sys

files = [
    'MicroHySeeker/src/api/routes/template.py',
    'MicroHySeeker/src/api/routes/device.py',
    'MicroHySeeker/src/api/routes/system.py',
    'MicroHySeeker/src/api/bridge.py',
    'MicroHySeeker/src/api/server.py',
    'MicroHySeeker/src/echem_sdl/utils/constants.py',
    'MicroHySeeker/src/echem_sdl/hardware/pump_manager.py',
    'MicroHySeeker/src/echem_sdl/hardware/rs485_protocol.py',
    'MicroHySeeker/src/echem_sdl/hardware/flusher.py',
    'MicroHySeeker/src/echem_sdl/hardware/diluter.py',
    'MicroHySeeker/src/services/rs485_wrapper.py',
    'MicroHySeeker/src/dialogs/config_dialog.py',
    'AutoHySeeker/src/tools/experiment_ctrl.py'
]

failed = []
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f"✓ {f}")
    except py_compile.PyCompileError as e:
        print(f"✗ {f}")
        print(f"  Error: {e}")
        failed.append(f)

if failed:
    print(f"\nFAILED: {len(failed)} file(s) have syntax errors")
    sys.exit(1)
else:
    print("\nALL SYNTAX OK")
    sys.exit(0)
