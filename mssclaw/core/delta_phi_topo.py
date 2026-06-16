"""
S-035: delta_phi_topo — Independent S Validation.

Validates Δφ_topo (structural phase change) against an independent S set,
not the same S used for calibration. This prevents circular reasoning
where the same stabilizer pairs both define and validate the threshold.

Protocol:
  1. Split S pairs into train (70%) and test (30%).
  2. Calibrate φ_critical on train.
  3. Evaluate breach prediction on test.
  4. Report precision/recall/F1.

Also computes Spearman ρ between Δφ_topo and A3 Tax_logic
to validate the formal bridge: Δφ_topo ∝ Tax_logic.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import random
import statistics
import math


@dataclass
class SPairWithTurn:
    """An S pair at a specific turn."""
    char_a: str
    char_b: str
    equivalent: bool
    turn: int
    eta_at_turn: float
    dim_scores: Dict[str, float] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Independent validation result."""
    n_train: int
    n_test: int
    phi_critical_train: float
    phi_critical_test: float

    # Prediction
    true_breaches: int       # Actual breaches in test
    predicted_breaches: int   # Predicted breaches in test
    true_positives: int
    false_positives: int
    false_negatives: int

    @property
    def precision(self) -> float:
        d = self.true_positives + self.false_positives
        return self.true_positives / max(d, 1)

    @property
    def recall(self) -> float:
        d = self.true_positives + self.false_negatives
        return self.true_positives / max(d, 1)

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / max(p + r, 1e-9)

    @property
    def stability_ratio(self) -> float:
        """phi_critical_test / phi_critical_train. ~1.0 = stable."""
        if self.phi_critical_train == 0:
            return 1.0
        return self.phi_critical_test / self.phi_critical_train


def split_train_test(
    turns: List[SPairWithTurn],
    train_ratio: float = 0.7,
    seed: int = 42,
) -> Tuple[List[SPairWithTurn], List[SPairWithTurn]]:
    """Random split preserving equivalent/divergent ratio."""
    random.seed(seed)
    equiv = [t for t in turns if t.equivalent]
    diff = [t for t in turns if not t.equivalent]

    random.shuffle(equiv)
    random.shuffle(diff)

    n_eq_train = int(len(equiv) * train_ratio)
    n_df_train = int(len(diff) * train_ratio)

    train = equiv[:n_eq_train] + diff[:n_df_train]
    test = equiv[n_eq_train:] + diff[n_df_train:]
    random.shuffle(train)
    random.shuffle(test)

    return train, test


def calibrate_from_turns(
    turns: List[SPairWithTurn],
    breach_threshold: float = 0.50,
) -> float:
    """
    Calibrate φ_critical from turns using median_delta.

    For each turn pair (i, i+1) where eta drops significantly,
    compute delta = |eta_before - eta_after| / eta_before.
    Return median as φ_critical.
    """
    if len(turns) < 2:
        return 0.60  # default

    # Group by turn, compute consecutive drops
    turns_sorted = sorted(turns, key=lambda t: t.turn)
    drops = []

    for i in range(len(turns_sorted) - 1):
        eta_before = turns_sorted[i].eta_at_turn
        eta_after = turns_sorted[i + 1].eta_at_turn

        if eta_after < eta_before and eta_before > 0:
            delta = (eta_before - eta_after) / eta_before
            if delta > 0.01:  # filter noise
                drops.append(delta)

    if not drops:
        return 0.60

    return statistics.median(drops)


def validate_phi_critical(
    turns: List[SPairWithTurn],
    train_ratio: float = 0.7,
    phi_threshold_multiplier: float = 1.0,
    seed: int = 42,
) -> ValidationResult:
    """
    Train/test split validation of φ_critical.

    Returns ValidationResult with precision/recall/F1.
    """
    train, test = split_train_test(turns, train_ratio, seed)

    phi_crit_train = calibrate_from_turns(train)
    phi_crit_test = calibrate_from_turns(test)

    # Apply multiplier for sensitivity analysis
    effective_threshold = phi_crit_train * phi_threshold_multiplier

    # Classify test set
    true_breaches = 0
    predicted_breaches = 0
    tp = fp = fn = 0

    test_sorted = sorted(test, key=lambda t: t.turn)
    for i in range(len(test_sorted) - 1):
        eta_before = test_sorted[i].eta_at_turn
        eta_after = test_sorted[i + 1].eta_at_turn

        actual_breach = eta_after < 0.50  # ground truth: eta drops below threshold
        if actual_breach:
            true_breaches += 1

        delta = 0.0
        if eta_before > 0:
            delta = (eta_before - eta_after) / eta_before

        predicted = delta > effective_threshold
        if predicted:
            predicted_breaches += 1

        if actual_breach and predicted:
            tp += 1
        elif not actual_breach and predicted:
            fp += 1
        elif actual_breach and not predicted:
            fn += 1

    return ValidationResult(
        n_train=len(train),
        n_test=len(test),
        phi_critical_train=round(phi_crit_train, 4),
        phi_critical_test=round(phi_crit_test, 4),
        true_breaches=true_breaches,
        predicted_breaches=predicted_breaches,
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
    )


def compute_spearman_rho(
    delta_phi_values: List[float],
    tax_logic_values: List[float],
) -> float:
    """
    Spearman rank correlation between Δφ_topo and Tax_logic.
    Validates: Δφ_topo ∝ Tax_logic (conflict edges = unprovable propositions).
    """
    if len(delta_phi_values) < 3:
        return 0.0

    def rank(data):
        sorted_idx = sorted(range(len(data)), key=lambda i: data[i])
        ranks = [0] * len(data)
        for rank_val, idx in enumerate(sorted_idx):
            ranks[idx] = rank_val + 1
        return ranks

    rank_x = rank(delta_phi_values)
    rank_y = rank(tax_logic_values)

    n = len(rank_x)
    mean_x = statistics.mean(rank_x)
    mean_y = statistics.mean(rank_y)

    cov = sum((rank_x[i] - mean_x) * (rank_y[i] - mean_y) for i in range(n))
    std_x = math.sqrt(sum((r - mean_x) ** 2 for r in rank_x))
    std_y = math.sqrt(sum((r - mean_y) ** 2 for r in rank_y))

    if std_x * std_y == 0:
        return 0.0

    return cov / (std_x * std_y)


# ═══════════════════════════════════════════════════════
# Self-test
# ═══════════════════════════════════════════════════════

def _test():
    # Build 30 turns with known breach pattern
    turns = []
    base_eta = 0.85
    rng = random.Random(42)

    for t in range(30):
        if t == 12:
            # Breach at turn 12: eta drops from 0.82 to 0.22
            eta = 0.22
            equiv = False
        elif t == 25:
            # Second breach at turn 25
            eta = 0.18
            equiv = False
        else:
            # Normal: eta drifts slowly (0.85 -> 0.72 over 30 turns)
            eta = base_eta - t * 0.003 + rng.uniform(-0.02, 0.02)
            equiv = True

        turns.append(SPairWithTurn(
            char_a=f"角色{t}",
            char_b=f"角色{t + (1 if not equiv else 0)}",
            equivalent=equiv,
            turn=t + 1,
            eta_at_turn=eta,
            dim_scores={"D1": eta, "D2": eta + 0.05, "D3": eta - 0.02},
        ))

    # Validate
    result = validate_phi_critical(turns)
    print(f"Validation: train={result.n_train}, test={result.n_test}")
    print(f"  phi_crit train={result.phi_critical_train}, test={result.phi_critical_test}")
    print(f"  stability_ratio={result.stability_ratio:.4f}")
    print(f"  TP={result.true_positives}, FP={result.false_positives}, FN={result.false_negatives}")
    print(f"  Precision={result.precision:.4f}, Recall={result.recall:.4f}, F1={result.f1:.4f}")

    assert result.n_test > 0, "Test set should not be empty"
    # With 1 breach, random split causes variance; stability_ratio > 0.5 is acceptable
    assert result.stability_ratio > 0.50, f"Stability ratio {result.stability_ratio}"

    # Spearman: Δφ_topo ∝ Tax_logic
    delta_phi = [0.1, 0.3, 0.5, 0.7, 0.9]
    tax_logic = [5, 25, 50, 75, 95]  # perfect monotonic
    rho = compute_spearman_rho(delta_phi, tax_logic)
    print(f"Spearman(Δφ, Tax_logic) = {rho:.4f}")
    assert rho > 0.95, f"Expected rho ~1.0, got {rho}"

    # Edge case: empty
    assert compute_spearman_rho([], []) == 0.0
    assert compute_spearman_rho([0.5], [10]) == 0.0

    print("\n✅ delta_phi_topo: ALL TESTS PASSED")


if __name__ == "__main__":
    _test()
