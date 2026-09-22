"""Bit-exact regression against fingerprints recorded from the original (V0-V4) code.
Any refactoring or runtime optimisation must keep these identical; new behaviour must be opt-in."""
import json, os
import pytest
from make_golden import make_all

GOLD = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden_v0.json")))


@pytest.fixture(scope="module")
def current():
    return make_all()


def test_all_fingerprints_identical(current):
    gold = GOLD["fingerprints"]
    assert set(current) == set(gold)
    diffs = [k for k in gold if current[k] != gold[k]]
    assert not diffs, f"{len(diffs)} fingerprints changed, e.g. {diffs[:5]}"
