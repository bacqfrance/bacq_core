"""
Harshit Verma -- October 2026

Define how to evaluate a BACQ-EP-MNR experiment (BACQ D3.2).

From the VQE runs (noiseless, raw, mitigated) at several ansatz depths:
    L1 -- fit the phenomenological convergence model E(Ng, Nit) and the effective noise eps_eff,
    L2 -- classical optimizer cost per iteration (power law in the number of layers),
    L3 -- minimal dressed energy per gate at gate error eps_eff (superconducting full-stack model),
    L4 -- least-energy operating point (Ng, Nit) at a target accuracy.
"""

import numpy as np
from scipy.optimize import curve_fit

from .helpers_energy import get_optimal_gate_energy
from .helpers_instance import get_num_measurement_groups
from .view import energy_txt

_NG_GRID = np.linspace(1, 2000, 4000)
_NIT_CONVERGED = 1e6
_NG_TH_STEP = 5
_NG_TH_MAX_FRAC = 0.8


def get_metric(exp_data, **meta_params):
    """
    """
    result = exp_data["result"]
    num_qubits = exp_data["parameters"]["n"]

    return compute_metric(result, num_qubits, **meta_params)


def compute_metric(result, num_qubits, mu_fit_window, alpha, energy_shots, classical_efficiency, flops_prefactor, flops_exponent,
                   cryo_efficiency, stage_temperatures, attenuation_range_db, gate_time_range_ns,
                   floor_margin, target_multipliers):
    """
    Computes the BACQ-EP-MNR figure of merit: the minimal error reachable on the device (dE_min),
    and the minimal total energy (E_min) to reach an accuracy just above it.
    """
    ## L1: convergence model and effective noise
    fit, eps_eff, eps_raw = fit_convergence_model(result, mu_fit_window, alpha)
    dE_min, Ng_floor = compute_error_floor(fit, eps_eff)

    ## Optimal circuit depth L* (Eq. 24), in ansatz layers of the device
    slope, intercept, _ = get_layer_relation(result)
    layers_opt = (Ng_floor - intercept) / slope

    metric = {
        "dE_min": dE_min,
        "E_min_J": None,
        "E_min_Wh": None,
        "Nit": None,
        "Ng": None,
        "classical_share": None,
        "eps_eff": eps_eff,
        "eps_raw": eps_raw,
        "Ng_floor": Ng_floor,
        "layers_opt": layers_opt,
        "optimization_possible": bool(layers_opt >= 1),
        "message": f"Optimal circuit depth: L* = {layers_opt:.2f} layers.",
        "gate": None,
        "fit": fit,
        "fit_settings": (("rate over full trajectories" if mu_fit_window is None
                          else f"rate over {mu_fit_window} iterations per layer")
                         + (", alpha fitted" if alpha is None else ", alpha fixed")),
        "energy_vs_error": [],
        "energy_report": "",
    }

    ## Without algorithmic optimization, no energetic figure of merit
    if not metric["optimization_possible"]:
        metric["message"] = (f"No optimization possible: the optimal circuit (L* = {layers_opt:.2f} layers) is shallower "
                             f"than the shallowest executable circuit (1 layer).")
        return metric

    ## L3: dressed energy per gate at gate error eps_eff
    device = result["device_params"]
    gate = get_optimal_gate_energy(eps_eff, device["gamma_hz"], device["freq_hz"], stage_temperatures,
                                   cryo_efficiency, attenuation_range_db, gate_time_range_ns)
    if gate is None:
        raise ValueError(f"Gate error {eps_eff=:.3g} is not reachable within {attenuation_range_db=} and {gate_time_range_ns=}.")

    ## L4: least-energy operating points
    composition = {
        "gate_energy": gate["gate_energy"],
        "layers_of_Ng": get_layers_of_Ng(result),
        "num_meas": get_num_measurement_groups(num_qubits),
        "energy_shots": energy_shots,
        "classical_efficiency": classical_efficiency,
        "flops_prefactor": flops_prefactor,
        "flops_exponent": flops_exponent,
    }
    fom = compute_min_energy(fit, eps_eff, dE_min * floor_margin, **composition)
    curve = [compute_min_energy(fit, eps_eff, dE_min * m, **composition) for m in target_multipliers]

    metric.update({
        "E_min_J": fom["energy"],
        "E_min_Wh": fom["energy"] / 3600,
        "Nit": fom["Nit"],
        "Ng": fom["Ng"],
        "classical_share": fom["classical_share"],
        "gate": gate,
        "energy_vs_error": curve,
    })
    metric["energy_report"] = energy_txt.format(metric=metric, floor_margin=floor_margin)

    return metric


def get_metric_success(exp_data, **meta_params):
    """
    No success criterion is defined yet for BACQ-EP-MNR: success is None.
    """
    metric = get_metric(exp_data, **meta_params)

    return metric, None


def get_score(exp_data):
    """
    """
    raise NotImplementedError("BACQ-EP-MNR is defined for a single problem size: no sequence score.")


## ------------------------------------------------------------------ L1: convergence model

def model_energy(fit, Ng, Nit, eps):
    """
    Phenomenological VQE error E(Ng, Nit) - E_gs (Eq. 17):
        (1-eps)^Ng * [alpha exp(-mu0 Nit (Ng - Ng_th)^-lambda) + beta exp(-kappa Ng) + E_gs] - E_gs
    """
    Ng = np.asarray(Ng, dtype=float)
    dNg = Ng - fit["Ng_th"]

    with np.errstate(invalid="ignore", divide="ignore"):
        dNg_pow = np.where(dNg > 0, dNg ** (-fit["lam"]), np.nan)
        energy = (1 - eps) ** Ng * (
            fit["alpha"] * np.exp(-fit["mu0"] * Nit * dNg_pow)
            + fit["beta"] * np.exp(-fit["kappa"] * Ng)
            + fit["E_gs"]
        )

    return energy - fit["E_gs"]


def fit_convergence_model(result, mu_fit_window=None, alpha=None):
    """
    Extracts the parameters of the convergence model from the VQE runs (Sec. 3.5, 3.7).

    Arguments:
        .result         -- dict, experiment result
        .mu_fit_window  -- int, iterations per ansatz layer used to fit the convergence rate (None: full trajectory)
        .alpha          -- float, amplitude of the convergence transient (None: fitted from the trajectories)

    Returns:
        .fit        -- dict, convergence-model parameters
        .eps_eff    -- float, effective depolarizing rate from the mitigated runs
        .eps_raw    -- float, effective depolarizing rate from the unmitigated runs
    """
    E_gs = result["ground_energy"]
    layers = sorted(result["layers"], key=int)
    runs = [result["layers"][layer] for layer in layers]

    Ng = np.array([run["Ng"] for run in runs], dtype=float)
    E_nl = np.array([np.mean(run["noiseless"]["finals"]) for run in runs])
    E_raw = np.array([np.mean(run["raw"]["finals"]) for run in runs])
    E_mit = np.array([np.mean(run["mitigated"]["finals"]) for run in runs])

    ## Converged noiseless energy vs circuit size (Eq. 14)
    beta, kappa = fit_converged_energy(Ng, E_nl, E_gs)

    ## Convergence rate per seed trajectory (Eq. 13), then vs circuit size (Eq. 15)
    mu, mu_err, amplitudes = [], [], []
    for layer, run, E_inf in zip(layers, runs, E_nl):
        window = None if mu_fit_window is None else mu_fit_window * int(layer)
        rates = np.array([fit_convergence_rate(history[:window], E_inf) for history in run["noiseless"]["histories"]])
        num_ok = np.sum(np.isfinite(rates[:, 0]))
        mu.append(np.nanmean(rates[:, 0]))
        mu_err.append(np.nanstd(rates[:, 0]) / np.sqrt(num_ok))
        amplitudes.append(np.nanmean(rates[:, 1]))

    mu0, lam, Ng_th = fit_convergence_power_law(Ng, np.array(mu), np.array(mu_err))

    fit = {
        "E_gs": E_gs,
        "alpha": float(np.nanmean(amplitudes)) if alpha is None else float(alpha),
        "beta": beta,
        "kappa": kappa,
        "mu0": mu0,
        "lam": lam,
        "Ng_th": Ng_th,
    }

    ## Effective noise from the noise floors (Eq. 16)
    eps_eff = extract_effective_noise(Ng, E_mit, beta, kappa, E_gs)
    eps_raw = extract_effective_noise(Ng, E_raw, beta, kappa, E_gs)

    return fit, eps_eff, eps_raw


def fit_converged_energy(Ng, E_inf, E_gs):
    """
    Fits E_inf(Ng) = beta * exp(-kappa * Ng) + E_gs.
    """
    popt, _ = curve_fit(
        lambda x, beta, kappa: beta * np.exp(-kappa * x) + E_gs, Ng, E_inf,
        p0=[4.0, 0.01], bounds=([0.0, 1e-6], [50.0, 1.0]), maxfev=10000,
    )

    return float(popt[0]), float(popt[1])


def fit_convergence_rate(history, E_inf):
    """
    Fits one trajectory E(Nit) - E_inf = alpha * exp(-mu * Nit).

    Returns:
        .(mu, alpha) -- tuple(float), NaN if the fit fails
    """
    t = np.arange(len(history), dtype=float)
    dE = np.asarray(history, dtype=float) - E_inf
    valid = dE > 1e-8

    if valid.sum() < 5:
        return np.nan, np.nan

    try:
        popt, _ = curve_fit(
            lambda x, a, mu: a * np.exp(-mu * x), t[valid], dE[valid],
            p0=[dE[valid].max(), 0.05], bounds=([0.0, 1e-8], [np.inf, 10.0]), maxfev=10000,
        )
    except RuntimeError:
        return np.nan, np.nan

    return float(popt[1]), float(popt[0])


def fit_convergence_power_law(Ng, mu, mu_err):
    """
    Fits mu(Ng) = mu0 * (Ng - Ng_th)^(-lambda), weighted by the seed spread of mu.
    The offset Ng_th is scanned and the best coefficient of determination is kept.
    """
    best = None

    for Ng_th in np.arange(0, max(1, int(Ng.min() * _NG_TH_MAX_FRAC)), _NG_TH_STEP):
        try:
            popt, _ = curve_fit(
                lambda x, mu0, lam, off=Ng_th: mu0 * (x - off) ** (-lam), Ng, mu,
                p0=[1.0, 0.6], sigma=mu_err, absolute_sigma=True, maxfev=20000,
            )
        except (RuntimeError, TypeError):
            continue

        prediction = popt[0] * (Ng - Ng_th) ** (-popt[1])
        r2 = 1 - np.sum((mu - prediction) ** 2) / np.sum((mu - mu.mean()) ** 2)
        if best is None or r2 > best[3]:
            best = (float(popt[0]), float(popt[1]), float(Ng_th), r2)

    if best is None:
        raise ValueError("Convergence-rate power law could not be fitted.")

    return best[:3]


def extract_effective_noise(Ng, E_noisy, beta, kappa, E_gs):
    """
    Effective global-depolarizing rate eps from E_noisy(Ng) = (1-eps)^Ng * (beta exp(-kappa Ng) + E_gs).
    """
    E_noiseless = beta * np.exp(-kappa * Ng) + E_gs
    ratios = E_noisy / E_noiseless
    valid = np.isfinite(ratios) & (ratios > 0) & (E_noiseless < 0) & (E_noisy < 0)

    if valid.sum() < 2:
        raise ValueError("Effective noise cannot be extracted: fewer than two valid depths.")

    slope, _ = np.polyfit(Ng[valid], np.log(ratios[valid]), 1)
    eps = 1 - np.exp(slope)

    if not eps > 0:
        raise ValueError(f"Extracted effective noise {eps=:.3g} is not positive: the noise floor is not resolved.")

    return float(eps)


def compute_error_floor(fit, eps):
    """
    Minimal error reachable over circuit sizes, with converged optimization (Nit -> infinity).
    """
    error = model_energy(fit, _NG_GRID, _NIT_CONVERGED, eps)
    valid = np.isfinite(error) & (_NG_GRID > fit["Ng_th"])
    k = np.flatnonzero(valid)[np.argmin(error[valid])]

    return float(error[k]), float(_NG_GRID[k])


## ------------------------------------------------------------------ L4: energetic composition

def get_layer_relation(result):
    """
    Linear relation Ng = slope * L + intercept between the number of ansatz layers and the transpiled gate count on the device.
    """
    layers = np.array(sorted(int(layer) for layer in result["layers"]), dtype=float)
    Ng = np.array([result["layers"][str(int(layer))]["Ng"] for layer in layers], dtype=float)
    slope, intercept = np.polyfit(layers, Ng, 1)

    return float(slope), float(intercept), float(layers.max())


def get_layers_of_Ng(result):
    """
    Number of ansatz layers of a circuit of Ng gate operations, within the range of layers run.
    """
    slope, intercept, max_layers = get_layer_relation(result)

    return lambda x: np.clip((np.asarray(x, dtype=float) - intercept) / slope, 1, max_layers)


def get_iterations_for_target(fit, eps, target, Ng):
    """
    Number of iterations reaching the target error at each circuit size (inverse of Eq. 17), NaN if unreachable.
    """
    dNg = Ng - fit["Ng_th"]

    with np.errstate(invalid="ignore", divide="ignore"):
        rhs = (target + fit["E_gs"]) / (1 - eps) ** Ng - fit["beta"] * np.exp(-fit["kappa"] * Ng) - fit["E_gs"]
        frac = rhs / fit["alpha"]
        dNg_pow = np.where(dNg > 0, dNg ** (-fit["lam"]), np.nan)
        Nit = -np.log(frac) / (fit["mu0"] * dNg_pow)

    Nit = np.where((frac > 0) & (frac < 1) & (dNg > 0) & np.isfinite(Nit), Nit, np.nan)

    return np.maximum(Nit, 1.0)


def compute_min_energy(fit, eps, target, gate_energy, layers_of_Ng, num_meas, energy_shots,
                       classical_efficiency, flops_prefactor, flops_exponent):
    """
    Least-energy operating point on the iso-accuracy contour 'target' (Eq. 36):
        E_total = Nit * (Ng * N_shots * N_meas * E_gate + FLOPs_opt(L) / zeta_c)
    """
    Nit = get_iterations_for_target(fit, eps, target, _NG_GRID)
    valid = np.isfinite(Nit) & (Nit > 1)
    if not valid.any():
        raise ValueError(f"Target error {target=:.3g} is not reachable.")

    Ng, Nit = _NG_GRID[valid], Nit[valid]
    E_quantum = Nit * Ng * energy_shots * num_meas * gate_energy
    E_classical = Nit * flops_prefactor * layers_of_Ng(Ng) ** flops_exponent / classical_efficiency
    E_total = E_quantum + E_classical
    k = int(np.argmin(E_total))

    return {
        "target_error": float(target),
        "energy": float(E_total[k]),
        "Nit": float(Nit[k]),
        "Ng": float(Ng[k]),
        "classical_share": float(E_classical[k] / E_total[k]),
    }
