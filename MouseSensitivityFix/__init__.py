"""
Mouse Sensitivity Fix for Borderlands 1

Scales mouse input before the game applies its own
MouseSensitivity. This lets you go below the in-game slider's minimum.

"""

import argparse
from typing import Any

import unrealsdk
from mods_base import BoolOption, SliderOption, build_mod, command, get_pc
from unrealsdk import logging
from unrealsdk.hooks import Type, add_hook, remove_hook
from unrealsdk.unreal import BoundFunction, UObject, WrappedStruct

HOOK_ID = "MouseSensitivityFix:PlayerInput"

# The per-frame input event. WillowPlayerInput may override it; if so we hook the override only, so
# the scaling can't be applied twice in one frame (the override would call super).
HOOK_CANDIDATES = (
    "WillowGame.WillowPlayerInput:PlayerInput",
    "Engine.PlayerInput:PlayerInput",
)

SensitivityPercent = SliderOption(
    "Sensitivity",
    50,
    1,
    200,
    1,
    True,
    description=(
        "Percentage multiplier applied to all mouse look on top of in-game sensitivity"
        " slider. 100 = unchanged."
    ),
)
VerticalPercent = SliderOption(
    "Vertical Ratio",
    100,
    50,
    150,
    1,
    True,
    description=(
        "Vertical axis sensitivity in percent. 100 = identical X and Y."
    ),
)
DisableSmoothing = BoolOption(
    "Disable Mouse Smoothing",
    False,
    description=(
        "Turns off bEnableMouseSmoothing"
    ),
)

hooked_func: str | None = None
hook_calls: int = 0
original_smoothing: bool | None = None


def on_player_input(obj: UObject, _args: WrappedStruct, _ret: Any, _func: BoundFunction) -> None:
    global hook_calls, original_smoothing
    hook_calls += 1

    if original_smoothing is None:
        original_smoothing = bool(obj.bEnableMouseSmoothing)
    obj.bEnableMouseSmoothing = (not DisableSmoothing.value) and original_smoothing

    scale = SensitivityPercent.value / 100
    obj.aMouseX *= scale
    obj.aMouseY *= scale * VerticalPercent.value / 100


def find_hook_target() -> str | None:
    for name in HOOK_CANDIDATES:
        try:
            unrealsdk.find_object("Function", name)
        except ValueError:
            continue
        return name
    return None


def on_enable() -> None:
    global hooked_func, hook_calls
    hooked_func = find_hook_target()
    hook_calls = 0
    if hooked_func is None:
        logging.error(
            "[MouseSensitivityFix] Could not find PlayerInput function to hook. Mod will"
            " have no effect. Run 'mousefix' in the console for details.",
        )
        return
    add_hook(hooked_func, Type.PRE, HOOK_ID, on_player_input)
    logging.info(f"[MouseSensitivityFix] Hooked {hooked_func}")


def on_disable() -> None:
    global hooked_func, original_smoothing
    if hooked_func is not None:
        remove_hook(hooked_func, Type.PRE, HOOK_ID)
        hooked_func = None

    if original_smoothing is not None:
        pc = get_pc(possibly_loading=True)
        if pc is not None and pc.PlayerInput is not None:
            pc.PlayerInput.bEnableMouseSmoothing = original_smoothing
        original_smoothing = None


@command("mousefix", description="Print mouse fix diagnostics")
def mousefix_cmd(_args: argparse.Namespace) -> None:
    print(f"Hooked function: {hooked_func}  (calls so far: {hook_calls})")
    for name in HOOK_CANDIDATES:
        try:
            unrealsdk.find_object("Function", name)
            exists = True
        except ValueError:
            exists = False
        print(f"  {name}: {'exists' if exists else 'not found'}")
    print(
        f"Multiplier: {SensitivityPercent.value}%  Vertical ratio: {VerticalPercent.value}%"
        f"  Disable smoothing: {DisableSmoothing.value}",
    )

    pc = get_pc(possibly_loading=True)
    if pc is None or pc.PlayerInput is None:
        print("No player controller / PlayerInput right now (load into game first)")
        return
    pi = pc.PlayerInput
    print(f"PlayerInput class: {pi.Class.Name}")
    for prop in (
        "MouseSensitivity",
        "bEnableMouseSmoothing",
        "bEnableFOVScaling",
        "LookRightScale",
        "LookUpScale",
        "bInvertMouse",
    ):
        try:
            print(f"  {prop} = {getattr(pi, prop)}")
        except AttributeError:
            print(f"  {prop} = <no such property>")


build_mod(
    options=[SensitivityPercent, VerticalPercent, DisableSmoothing],
    hooks=[],
    commands=[mousefix_cmd],
    on_enable=on_enable,
    on_disable=on_disable,
)
