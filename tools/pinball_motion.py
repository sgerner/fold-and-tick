#!/usr/bin/env python3
"""Generate a deterministic, physics-based pinball loop for the pixel-art dial."""

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artwork/packs/pixel_art/pinball-motion.json"

WIDTH = HEIGHT = 450
CENTER = (225.0, 225.0)
BALL_RADIUS = 9.0
RAIL_RADIUS = 202.0 - BALL_RADIUS
GRAVITY = 480.0
FPS = 20
STEP = 1.0 / 240.0
DURATION = 10.0
INITIAL_VELOCITY = (-69.76306946996219, -596.8129068992956)

BUMPERS = (
    (125.0, 58.0, 25.0),
    (225.0, 29.0, 25.0),
    (318.0, 58.0, 25.0),
)
FLIPPERS = (
    {"name": "left_flipper", "pivot": (60.0, 370.0), "rest": 20.0, "raised": -25.0},
    {"name": "right_flipper", "pivot": (390.0, 370.0), "rest": 160.0, "raised": 205.0},
)

# Each stroke begins with a fast lift, pauses briefly at the top, then settles.
LIFT_TIME = 0.14
HOLD_TIME = 0.08
RETURN_TIME = 0.20


def smoothstep(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def flipper_state(flipper, time_seconds, pulse_starts):
    """Return clockwise angle and angular velocity in degrees per second."""
    rest = flipper["rest"]
    raised = flipper["raised"]
    name = flipper["name"]
    for start in pulse_starts[name]:
        lift_end = start + LIFT_TIME
        hold_end = lift_end + HOLD_TIME
        return_end = hold_end + RETURN_TIME
        if start <= time_seconds < lift_end:
            p = (time_seconds - start) / LIFT_TIME
            angle = rest + (raised - rest) * smoothstep(p)
            velocity = (raised - rest) * 6.0 * p * (1.0 - p) / LIFT_TIME
            return angle, velocity
        if lift_end <= time_seconds < hold_end:
            return raised, 0.0
        if hold_end <= time_seconds < return_end:
            p = (time_seconds - hold_end) / RETURN_TIME
            angle = raised + (rest - raised) * smoothstep(p)
            velocity = (rest - raised) * 6.0 * p * (1.0 - p) / RETURN_TIME
            return angle, velocity
    return rest, 0.0


def _clamp_ball_to_circle(x, y, vx, vy):
    dx, dy = x - CENTER[0], y - CENTER[1]
    distance = math.hypot(dx, dy)
    if distance <= RAIL_RADIUS:
        return x, y, vx, vy, None
    nx, ny = dx / distance, dy / distance
    normal_speed = vx * nx + vy * ny
    if normal_speed <= 0.0:
        return x, y, vx, vy, None
    vx -= 1.92 * normal_speed * nx
    vy -= 1.92 * normal_speed * ny
    x = CENTER[0] + nx * (RAIL_RADIUS - 0.05)
    y = CENTER[1] + ny * (RAIL_RADIUS - 0.05)
    return x, y, vx, vy, "rail"


def _circle_bumper_contact(x, y, vx, vy, bumper):
    bx, by, bumper_radius = bumper
    dx, dy = x - bx, y - by
    distance = math.hypot(dx, dy)
    contact_radius = BALL_RADIUS + bumper_radius
    if distance >= contact_radius:
        return x, y, vx, vy, False
    if distance == 0.0:
        nx, ny = 0.0, -1.0
    else:
        nx, ny = dx / distance, dy / distance
    normal_speed = vx * nx + vy * ny
    if normal_speed >= 0.0:
        return x, y, vx, vy, False
    vx -= 2.02 * normal_speed * nx
    vy -= 2.02 * normal_speed * ny
    x = bx + nx * (contact_radius + 0.05)
    y = by + ny * (contact_radius + 0.05)
    return x, y, vx, vy, True


def _flipper_contact(x, y, vx, vy, flipper, time_seconds, pulse_starts):
    (px, py) = flipper["pivot"]
    angle, angle_velocity = flipper_state(flipper, time_seconds, pulse_starts)
    radians = math.radians(angle)
    end_x = px + 100.0 * math.cos(radians)
    end_y = py + 100.0 * math.sin(radians)
    seg_x, seg_y = end_x - px, end_y - py
    segment_length_squared = seg_x * seg_x + seg_y * seg_y
    along = ((x - px) * seg_x + (y - py) * seg_y) / segment_length_squared
    along = max(0.0, min(1.0, along))
    contact_x = px + along * seg_x
    contact_y = py + along * seg_y
    dx, dy = x - contact_x, y - contact_y
    distance = math.hypot(dx, dy)
    contact_radius = BALL_RADIUS + 8.0
    if distance >= contact_radius:
        return x, y, vx, vy, False
    if distance == 0.0:
        nx, ny = 0.0, -1.0
    else:
        nx, ny = dx / distance, dy / distance

    # The moving flipper contributes its tangential velocity at the contact point.
    omega = math.radians(angle_velocity)
    surface_vx = -omega * (contact_y - py)
    surface_vy = omega * (contact_x - px)
    relative_normal_speed = (vx - surface_vx) * nx + (vy - surface_vy) * ny
    if relative_normal_speed >= 0.0:
        return x, y, vx, vy, False
    impulse = 1.94 * relative_normal_speed
    vx -= impulse * nx
    vy -= impulse * ny
    x = contact_x + nx * (contact_radius + 0.05)
    y = contact_y + ny * (contact_radius + 0.05)
    return x, y, vx, vy, True


def simulate(initial_velocity=INITIAL_VELOCITY):
    """Integrate the ball and proximity-triggered flippers at 240 Hz."""
    x, y = 225.0, 350.0
    vx, vy = initial_velocity
    sample_interval = 1.0 / FPS
    total_steps = round(DURATION / STEP)
    next_sample = 0
    samples = []
    events = []
    last_event_time = {}
    pulse_starts = {flipper["name"]: [] for flipper in FLIPPERS}
    last_trigger = {flipper["name"]: -math.inf for flipper in FLIPPERS}

    for step_index in range(total_steps + 1):
        time_seconds = step_index * STEP
        _trigger_incoming_flippers(x, y, vx, vy, time_seconds, pulse_starts, last_trigger)
        if step_index == next_sample:
            left_angle, _ = flipper_state(FLIPPERS[0], time_seconds, pulse_starts)
            right_angle, _ = flipper_state(FLIPPERS[1], time_seconds, pulse_starts)
            samples.append({
                "t": round(time_seconds, 4),
                "x": round(x, 3),
                "y": round(y, 3),
                "leftAngle": round(left_angle, 3),
                "rightAngle": round(right_angle, 3),
            })
            next_sample = round((len(samples)) * sample_interval / STEP)
        if step_index == total_steps:
            break

        vy += GRAVITY * STEP
        x += vx * STEP
        y += vy * STEP
        time_seconds += STEP

        x, y, vx, vy, rail_hit = _clamp_ball_to_circle(x, y, vx, vy)
        if rail_hit:
            _record_event(events, last_event_time, time_seconds, rail_hit, x, y)

        for bumper_index, bumper in enumerate(BUMPERS, start=1):
            x, y, vx, vy, hit = _circle_bumper_contact(x, y, vx, vy, bumper)
            if hit:
                _record_event(events, last_event_time, time_seconds,
                              f"bumper_{bumper_index}", x, y)

        for flipper in FLIPPERS:
            x, y, vx, vy, hit = _flipper_contact(
                x, y, vx, vy, flipper, time_seconds, pulse_starts)
            if hit:
                angle, angle_velocity = flipper_state(flipper, time_seconds, pulse_starts)
                phase = "lift" if angle_velocity * (flipper["raised"] - flipper["rest"]) > 0 else (
                    "return" if angle_velocity else "rest")
                _record_event(events, last_event_time, time_seconds,
                              flipper["name"], x, y, phase)

    return samples, events, pulse_starts


def _trigger_incoming_flippers(x, y, vx, vy, time_seconds, pulse_starts, last_trigger):
    """Start a stroke in time for a descending ball to meet the rising blade."""
    if vy <= 80.0 or not 280.0 < y < 420.0 or time_seconds >= DURATION - 0.55:
        return
    for flipper in FLIPPERS:
        name = flipper["name"]
        px, py = flipper["pivot"]
        if (name == "left_flipper" and not 75.0 < x < CENTER[0]) or (
                name == "right_flipper" and not CENTER[0] < x < 375.0):
            continue
        if time_seconds - last_trigger[name] < 0.75:
            continue

        angle = math.radians(flipper["rest"])
        end_x = px + 100.0 * math.cos(angle)
        end_y = py + 100.0 * math.sin(angle)
        seg_x, seg_y = end_x - px, end_y - py
        along = ((x - px) * seg_x + (y - py) * seg_y) / (seg_x * seg_x + seg_y * seg_y)
        along = max(0.0, min(1.0, along))
        contact_x = px + along * seg_x
        contact_y = py + along * seg_y
        dx, dy = contact_x - x, contact_y - y
        distance = math.hypot(dx, dy)
        if not 17.0 < distance < 125.0:
            continue
        closing_speed = (vx * dx + vy * dy) / distance
        if closing_speed < 90.0:
            continue

        # Aim contact near the end of the lift, when the paddle is moving upward.
        time_to_contact = max(0.0, (distance - 17.0) / closing_speed)
        start = time_seconds + max(0.0, time_to_contact - 0.11)
        if start + LIFT_TIME + HOLD_TIME + RETURN_TIME >= DURATION - 0.05:
            continue
        pulse_starts[name].append(start)
        last_trigger[name] = start


def _record_event(events, last_event_time, time_seconds, kind, x, y, phase=None):
    # Prevent multiple reports while the ball is being depenetrated from one surface.
    if time_seconds - last_event_time.get(kind, -1.0) < 0.08:
        return
    event = {
        "t": round(time_seconds, 4),
        "type": kind,
        "x": round(x, 3),
        "y": round(y, 3),
    }
    if phase:
        event["phase"] = phase
    events.append(event)
    last_event_time[kind] = time_seconds


def validate(samples, events, pulse_starts):
    assert len(samples) == int(DURATION * FPS) + 1
    assert samples[0]["t"] == 0.0 and samples[-1]["t"] == DURATION
    assert samples[0]["x"] == 225.0 and samples[0]["y"] == 350.0
    assert math.hypot(samples[-1]["x"] - samples[0]["x"],
                      samples[-1]["y"] - samples[0]["y"]) < 12.0
    kinds = {event["type"] for event in events}
    assert {"bumper_1", "bumper_2", "bumper_3", "left_flipper", "right_flipper"} <= kinds
    assert {event["type"] for event in events
            if event.get("phase") == "lift"} >= {"left_flipper", "right_flipper"}
    assert min(sample["x"] for sample in samples) < 50.0
    assert max(sample["x"] for sample in samples) > 400.0
    assert min(sample["y"] for sample in samples) < 55.0
    assert max(sample["y"] for sample in samples) > 405.0
    max_step = max(math.hypot(current["x"] - previous["x"],
                              current["y"] - previous["y"])
                   for previous, current in zip(samples, samples[1:]))
    assert max_step < 100.0
    _validate_contact_geometry(events, pulse_starts)


def _validate_contact_geometry(events, pulse_starts):
    for event in events:
        x = event.get("physicsX", event["x"])
        y = event.get("physicsY", event["y"])
        if event["type"] == "rail":
            assert abs(math.hypot(x - CENTER[0], y - CENTER[1]) - RAIL_RADIUS + 0.05) < 0.15
        elif event["type"].startswith("bumper_"):
            index = int(event["type"].split("_")[1]) - 1
            bx, by, bumper_radius = BUMPERS[index]
            assert abs(math.hypot(x - bx, y - by) - BALL_RADIUS - bumper_radius - 0.05) < 0.15
        elif event["type"] in {"left_flipper", "right_flipper"}:
            flipper = next(item for item in FLIPPERS if item["name"] == event["type"])
            (px, py) = flipper["pivot"]
            angle, _ = flipper_state(flipper, event["t"], pulse_starts)
            radians = math.radians(angle)
            ex, ey = px + 100.0 * math.cos(radians), py + 100.0 * math.sin(radians)
            sx, sy = ex - px, ey - py
            along = max(0.0, min(1.0, ((x - px) * sx + (y - py) * sy) / (sx * sx + sy * sy)))
            distance = math.hypot(x - (px + along * sx), y - (py + along * sy))
            assert distance <= BALL_RADIUS + 8.2


def close_loop(samples, events):
    """Distribute the small measured return error smoothly over the loop."""
    dx = samples[-1]["x"] - samples[0]["x"]
    dy = samples[-1]["y"] - samples[0]["y"]
    magnitude = math.hypot(dx, dy)
    if magnitude >= 12.0:
        raise ValueError(f"Raw loop seam is too large to close cleanly: {magnitude:.2f}px")

    for sample in samples:
        amount = smoothstep(sample["t"] / DURATION)
        sample["x"] = round(sample["x"] - dx * amount, 3)
        sample["y"] = round(sample["y"] - dy * amount, 3)
    samples[-1]["x"] = samples[0]["x"]
    samples[-1]["y"] = samples[0]["y"]

    for event in events:
        event["physicsX"] = event["x"]
        event["physicsY"] = event["y"]
        amount = smoothstep(event["t"] / DURATION)
        event["x"] = round(event["x"] - dx * amount, 3)
        event["y"] = round(event["y"] - dy * amount, 3)
    return {"method": "distributed smoothstep", "x": round(-dx, 3),
            "y": round(-dy, 3), "magnitude": round(magnitude, 3)}


def build():
    samples, events, pulse_starts = simulate()
    validate(samples, events, pulse_starts)
    loop_closure = close_loop(samples, events)
    assert samples[-1]["x"] == samples[0]["x"]
    assert samples[-1]["y"] == samples[0]["y"]
    document = {
        "version": 1,
        "duration": DURATION,
        "fps": FPS,
        "canvas": {"width": WIDTH, "height": HEIGHT},
        "ballRadius": BALL_RADIUS,
        "loopClosure": loop_closure,
        "physics": {
            "gravity": GRAVITY,
            "railRadius": RAIL_RADIUS,
            "bumperCentersAndRadii": [list(bumper) for bumper in BUMPERS],
            "flipperPivots": [list(flipper["pivot"]) for flipper in FLIPPERS],
        },
        "flipperPulses": {name: [round(start, 4) for start in starts]
                          for name, starts in pulse_starts.items()},
        "samples": samples,
        "events": events,
    }
    OUTPUT.write_text(json.dumps(document, indent=2) + "\n")
    print(f"Wrote {len(samples)} pinball motion samples and {len(events)} collision events")


if __name__ == "__main__":
    build()
