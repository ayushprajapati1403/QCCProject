"""Register normalisation, measurement law, depolarising channel, purity."""
import numpy as np
import pytest
from scipy import stats
from qi_quantum import (born_probs, renormalise, probs, measure, basis_state, project, purity, depolarise, uniform_state)

MODES = ["born_signed", "born_abs", "linear"]


def test_renormalise_unit_rows_and_zero_rows():
    psi = np.array([[3.0, 4.0, 0.0], [0.0, 0.0, 0.0], [-1.0, 1.0, 1.0]])
    out = renormalise(psi.copy(), 3)
    assert np.allclose((out ** 2).sum(1), 1.0)
    assert np.allclose(out[1], 1 / np.sqrt(3))
    assert np.allclose(out[0], [0.6, 0.8, 0.0])


@pytest.mark.parametrize("mode", MODES)
def test_project_returns_valid_state(mode):
    rng = np.random.default_rng(0)
    psi = rng.normal(size=(50, 7))
    psi[3] = 0.0
    out = project(psi, 7, mode)
    p = probs(out, mode)
    assert np.allclose(p.sum(1), 1.0) and np.all(p >= 0)
    if mode.startswith("born"):
        assert np.allclose((out ** 2).sum(1), 1.0)
    if mode == "born_abs":
        assert np.all(out >= 0)
    if mode == "linear":
        assert np.allclose(out.sum(1), 1.0) and np.all(out >= 0)


@pytest.mark.parametrize("mode", MODES)
def test_uniform_state_has_minimal_purity(mode):
    u = uniform_state(9, 4, mode)
    assert np.allclose(purity(u, mode), 0.25)


@pytest.mark.parametrize("mode", MODES)
def test_depolarise_normalisation_and_monotone_purity(mode):
    E = basis_state(np.array([1, 2, 0, 3]), 5)
    purs = []
    for g in [0.0, 0.05, 0.2, 0.5, 0.9, 1.0]:
        D = depolarise(E, g, 5, mode)
        p = probs(D, mode)
        assert np.allclose(p.sum(1), 1.0)
        if mode.startswith("born"):
            assert np.allclose((D ** 2).sum(1), 1.0)
        purs.append(purity(D, mode).mean())
    assert all(np.diff(purs) < 0)
    assert purs[0] == pytest.approx(1.0) and purs[-1] == pytest.approx(0.2)


def test_depolarise_exact_mixture_and_sign_preservation():
    rng = np.random.default_rng(3)
    psi = renormalise(rng.normal(size=(6, 4)), 4)
    g = 0.3
    D = depolarise(psi, g, 4, "born_signed")
    assert np.allclose(D ** 2, (1 - g) * psi ** 2 + g / 4)
    assert np.all(np.sign(D) == np.sign(psi + (psi == 0)))


def test_purity_bounds():
    rng = np.random.default_rng(1)
    for mode in MODES:
        psi = project(rng.normal(size=(100, 6)), 6, mode)
        pur = purity(psi, mode)
        assert np.all(pur >= 1 / 6 - 1e-12) and np.all(pur <= 1 + 1e-12)


def test_measurement_follows_born_rule():
    psi = renormalise(np.array([[0.1, 0.5, 0.3, 0.8]]), 4)
    p = born_probs(psi)[0]
    rng = np.random.default_rng(11)
    draws = np.array([measure(psi, rng, "born_signed")[0] for _ in range(20000)])
    counts = np.bincount(draws, minlength=4)
    assert stats.chisquare(counts, 20000 * p).pvalue > 1e-3


def test_measurement_follows_linear_rule():
    psi = np.array([[0.1, 0.5, 0.3, 0.1]])
    rng = np.random.default_rng(12)
    draws = np.array([measure(psi, rng, "linear")[0] for _ in range(20000)])
    assert stats.chisquare(np.bincount(draws, minlength=4), 20000 * psi[0]).pvalue > 1e-3


def test_one_hot_measures_deterministically_all_modes():
    a = np.array([2, 0, 1, 2, 2, 0])
    for mode in MODES:
        for s in range(5):
            assert np.array_equal(measure(basis_state(a, 3), np.random.default_rng(s), mode), a)


def test_zero_probability_columns_never_sampled():
    p = np.array([[0.5, 0.5, 0.0], [0.0, 1.0, 0.0], [0.3, 0.0, 0.7]])
    psi = np.sqrt(p)
    rng = np.random.default_rng(0)
    for _ in range(3000):
        a = measure(psi, rng, "born_signed")
        assert p[np.arange(3), a].min() > 0


def test_measurement_indices_in_range():
    rng = np.random.default_rng(5)
    psi = renormalise(rng.normal(size=(200, 9)), 9)
    for _ in range(50):
        a = measure(psi, rng, "born_signed")
        assert a.min() >= 0 and a.max() <= 8


def test_expected_hamming_between_measurements_equals_n_minus_purity():
    """E[#tasks differing between two independent measurements] = n - sum_t purity_t (the move-size identity)."""
    rng = np.random.default_rng(7)
    psi = depolarise(basis_state(rng.integers(0, 5, 40), 5), 0.3, 5, "born_signed")
    expected = 40 - purity(psi, "born_signed").sum()
    d = [np.sum(measure(psi, rng, "born_signed") != measure(psi, rng, "born_signed")) for _ in range(4000)]
    assert np.mean(d) == pytest.approx(expected, rel=0.05)
