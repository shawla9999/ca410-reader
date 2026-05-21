"""Test profile: JSON-based test configuration for Murideo + CA-410.

A profile defines a named test scenario with default Murideo parameters
and a list of test steps that vary across the run.

Usage:
    profile = load_profile('profiles/hdr_peak_brightness.json')
    for step in profile.steps:
        print(step.hdr, step.ire, step.window_size)
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from driver.murideo_driver import (
    CAT_TIMING, CAT_COLOR_SPACE, CAT_COLOR_DEPTH, CAT_HDR, CAT_BT2020,
    PATTERN_WINDOW, HDR_OFF,
)
from util.resolver import resource_path

# Defaults matching current auto-test behavior
_DEFAULTS = {
    'timing': 34,           # 3840x2160@60Hz
    'color_space': 0,       # RGB(0-255)
    'color_depth': 1,       # 10bit
    'pattern': PATTERN_WINDOW,
    'hdr': HDR_OFF,
    'bt2020': 0,
    'ire': 255,
    'window_size': 100,
}


@dataclass
class TestStep:
    """A single test step within a profile.

    All fields are optional — missing values fall back to profile defaults.
    """
    hdr: int | None = None
    bt2020: int | None = None
    ire: int | None = None
    window_size: int | None = None
    timing: int | None = None
    color_space: int | None = None
    color_depth: int | None = None
    pattern: int | None = None
    note: str = ''

    def resolved(self, defaults: dict) -> dict:
        """Return a dict with all fields filled in from defaults where missing."""
        result = dict(defaults)
        for f in ('hdr', 'bt2020', 'ire', 'window_size', 'timing',
                   'color_space', 'color_depth', 'pattern'):
            val = getattr(self, f)
            if val is not None:
                result[f] = val
        return result


@dataclass
class TestProfile:
    """A named test profile loaded from JSON."""
    name: str
    description: str = ''
    defaults: dict = field(default_factory=lambda: dict(_DEFAULTS))
    steps: list[TestStep] = field(default_factory=list)
    filepath: str = ''


def load_profile(filepath: str | Path) -> TestProfile:
    """Load a test profile from a JSON file."""
    filepath = Path(filepath)
    with open(filepath, encoding='utf-8') as f:
        data = json.load(f)

    defaults = dict(_DEFAULTS)
    if 'defaults' in data:
        defaults.update(data['defaults'])

    steps = []
    for s in data.get('steps', []):
        steps.append(TestStep(
            hdr=s.get('hdr'),
            bt2020=s.get('bt2020'),
            ire=s.get('ire'),
            window_size=s.get('window_size'),
            timing=s.get('timing'),
            color_space=s.get('color_space'),
            color_depth=s.get('color_depth'),
            pattern=s.get('pattern'),
            note=s.get('note', ''),
        ))

    return TestProfile(
        name=data.get('name', filepath.stem),
        description=data.get('description', ''),
        defaults=defaults,
        steps=steps,
        filepath=str(filepath),
    )


def save_profile(profile: TestProfile, filepath: str | Path) -> None:
    """Save a test profile to a JSON file."""
    filepath = Path(filepath)
    data = {
        'name': profile.name,
        'description': profile.description,
        'defaults': profile.defaults,
        'steps': [
            {k: v for k, v in [
                ('hdr', s.hdr), ('bt2020', s.bt2020), ('ire', s.ire),
                ('window_size', s.window_size), ('timing', s.timing),
                ('color_space', s.color_space), ('color_depth', s.color_depth),
                ('pattern', s.pattern), ('note', s.note),
            ] if v is not None and v != ''}
            for s in profile.steps
        ],
    }
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def list_profiles(directory: str | Path = None) -> list[Path]:
    """List all JSON profile files in a directory."""
    if directory is None:
        directory = resource_path('profiles')
    d = Path(directory)
    if not d.exists():
        return []
    return sorted(d.glob('*.json'))
