"""Illustrate multiple-testing risk; no strategy fitting or holdout access."""
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main():
    rng = np.random.default_rng(20261102)
    # Idealized independent, standard-normal null statistics, NOT market returns.
    # Each repetition selects the largest development statistic, then observes
    # that candidate's independent forward statistic.
    rows = []
    repetitions = 10000
    cutoff = 1.6448536269514722  # one-sided nominal 5% threshold
    for trials in [1, 10, 100, 1000]:
        selected = []
        forward = []
        for start in range(0, repetitions, 100):
            development = rng.normal(size=(100, trials))
            winners = development.argmax(axis=1)
            selected.extend(development[np.arange(100), winners])
            # Under independence, the selected candidate's new statistic
            # is still standard normal; no forward candidate selection occurs.
            forward.extend(rng.normal(size=100))
        rows.append({
            'trials': trials,
            'development_false_positive_fraction': float((np.array(selected) > cutoff).mean()),
            'theoretical_fraction': 1 - 0.95 ** trials,
            'independent_forward_positive_fraction': float((np.array(forward) > cutoff).mean()),
        })
    meta = pd.read_csv(ROOT / 'work/neural_v2/metadata.csv', usecols=['symbol', 'day'])
    # Preserve the reserved period: even metadata counts are restricted to 2021-24.
    years = meta.day.str[:4].astype(int)
    meta = meta.loc[years.between(2021, 2024)]
    result = {
        'seed': 20261102,
        'repetitions': repetitions,
        'interpretation': 'Synthetic independent null statistics, not trading results or an estimated probability our model is overfit. Actual strategy trials are correlated.',
        'multiple_testing_demo': rows,
        'sequence_sample_structure': {
            str(year): {'windows': len(group), 'unique_sessions': group.day.nunique(), 'symbols': group.symbol.nunique()}
            for year, group in meta.groupby(meta.day.str[:4])
        },
        'probability_example_bps': {
            'win_probability': 0.60, 'mean_win': 10, 'mean_loss': 20,
            'round_trip_cost': 3, 'expected_net': 0.60 * 10 - 0.40 * 20 - 3,
            'note': 'Hypothetical payoffs and costs, not observed model performance.'
        },
        'reserved_2025_accessed': False,
    }
    target = ROOT / 'experiments/research_review_2026_11_02'
    target.mkdir(parents=True, exist_ok=True)
    (target / 'sanity_checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
