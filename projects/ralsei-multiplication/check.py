"""Check deterministic population identity and causal foreground contact without assets."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / 'source'))
import numpy as np
import story
from crowd import Crowd


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    story.validate()
    crowd = Crowd(story)
    births = []
    for change in story.DOUBLINGS:
        before = crowd.sample(change['t'] - .0001)
        after = crowd.sample(change['t'])
        assert before['count'] == change['from']
        assert after['count'] == change['to']
        assert np.array_equal(after['ids'], np.arange(change['to']))
        assert np.isfinite(after['positions']).all()
        error = float(np.abs(after['positions'][change['from']:] -
                             after['positions'][:change['from']]).max())
        assert error == 0
        births.append({'time': change['t'], 'count': after['count'], 'parent_origin_error': error})
    impact = crowd.collision_events[0]
    assert (impact['id'], impact['partner']) == (5, 6)
    assert (impact['fall_time'], impact['recovery_time']) == (23.2, 26.8)
    assert impact['contact'] > 0 and np.linalg.norm(impact['displacement']) > 0
    assert crowd.positions.shape[1] == 1024
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'births': births, 'foreground_impact': impact,
                                     'physical_cache_shape': crowd.positions.shape}, indent=2) + '\n')
    print(f'Checked 15 exact births, stable IDs, contact-driven fall: {args.output}')


if __name__ == '__main__':
    main()
