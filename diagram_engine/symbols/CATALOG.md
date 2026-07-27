# Symbol catalog — first 20 (piping + mechanical)

Canonical pack for installation / technical-package sketches.
Keep symbols simple and readable at print size.

See also: `schema/graph.yaml`, `electrical/` (separate pack).

## Piping (12)

| ID | Label | Ports |
|----|-------|-------|
| `pipe_straight` | Pipe | `in` L · `out` R |
| `pipe_elbow` | Elbow | `in` L · `out` bottom |
| `pipe_tee` | Tee | `run_in` L · `run_out` R · `branch` bottom |
| `pipe_reducer` | Reducer | `in` L · `out` R |
| `valve_ball` | Ball valve | `in` L · `out` R |
| `valve_gate` | Gate valve | `in` L · `out` R |
| `valve_check` | Check valve | `in` L · `out` R |
| `valve_control` | Control valve | `in` L · `out` R · `signal` top |
| `centrifugal_pump` | Centrifugal pump | `suction` L · `discharge` R · `drive` bottom |
| `tank_vertical` | Vertical tank | `outlet` bottom · `inlet` top · `vent` top |
| `strainer` | Strainer | `in` L · `out` R |
| `instrument_pt` | Pressure/Temp point | `process` bottom |

Extras (beyond first 20): `drain`, `vent`.

## Mechanical (8)

| ID | Label | Ports |
|----|-------|-------|
| `motor_ac` | AC motor | `electrical` L · `shaft` R |
| `gearbox` | Gearbox | `input_shaft` L · `output_shaft` R |
| `coupling` | Coupling | `in` L · `out` R |
| `fan` | Fan | `drive` L · `air_out` R |
| `cylinder_pneumatic` | Pneumatic cylinder | `port_a` L · `port_b` R · `rod` R |
| `bearing_block` | Bearing block | `shaft_l` L · `shaft_r` R *(through)* |
| `skid_frame` | Skid / frame | *(outline only)* |
| `pump_motor_set` | Motor–pump set | `suction` · `discharge` · `electrical` *(hybrid)* |

Extras: `belt_drive`.

## Typical connections

```text
motor_ac.shaft ──shaft── centrifugal_pump.drive
motor_ac.electrical ──wire── (starter / panel)
centrifugal_pump.suction / discharge ──pipe── process lines

tank.outlet ──pipe── valve_ball ──pipe── pump.suction
pump.discharge ──pipe── valve_check ──pipe── …
```

Each symbol: `id.yaml` + matching `id.svg` under `piping/` or `mechanical/`.
