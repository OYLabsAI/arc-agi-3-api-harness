"""Verify level action counts against both sets of public ARC Prize recordings.

Uses only the Python standard library. Makes no model calls.
Copyright 2026 Orca Labs sp. z o.o. Licensed under Apache-2.0.
"""

import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def count_levels(record, content):
    require(hashlib.sha256(content).hexdigest() == record['sha256'], 'Recording hash mismatch')
    require(len(content) == record['bytes'], 'Recording size mismatch')
    previous, start = 0, 0
    levels, resets = [], []
    for i, line in enumerate(content.splitlines()):
        row = json.loads(line)['data']
        require(row['game_id'] == record['game_id'] and row['guid'] == record['guid'],
                'Recording identity mismatch')
        completed = row['levels_completed']
        if i == 0:
            require(completed == 0 and row['action_input']['id'] == 'RESET',
                    'Expected initial reset')
        elif row.get('full_reset'):
            resets.append(i)
        require(completed in (previous, previous + 1), 'Level progression is not monotonic')
        if completed == previous + 1:
            levels.append({'level': completed, 'actions': i - start,
                           'observation_rows_inclusive': [start, i]})
            start, previous = i, completed
    require(levels and row['state'] == 'WIN', 'Recording does not end in WIN')
    require(i == record['actions'] == sum(x['actions'] for x in levels), 'Action total mismatch')
    require(levels == record['levels'], 'Level counts differ')
    require(resets == record['resets_after_initial'], 'Reset rows differ')
    return levels


def compare_levels(games):
    result = []
    for game in games:
        a, b = game['oy1'], game['provider_adapter']
        require(a['game_id'] == b['game_id'], 'Game versions differ')
        require(len(a['levels']) == len(b['levels']), 'Level totals differ')
        for x, y in zip(a['levels'], b['levels']):
            require(x['level'] == y['level'] and y['actions'] > 0, 'Invalid matched level')
            result.append({'game_id': a['game_id'], 'level': x['level'],
                           'oy1_actions': x['actions'], 'provider_adapter_actions': y['actions'],
                           'reduction_percent': 100 * (1 - x['actions'] / y['actions']),
                           'actions_saved': y['actions'] - x['actions'],
                           'oy1_rows': x['observation_rows_inclusive'],
                           'provider_adapter_rows': y['observation_rows_inclusive']})
    return sorted(result, key=lambda x: (Fraction(x['oy1_actions'], x['provider_adapter_actions']),
                                        -x['actions_saved'], x['game_id'], x['level']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    audit = json.loads((ROOT / 'evidence/public-level-comparison.json').read_text())
    own = {r['game_id']: r for r in json.loads((ROOT / 'evidence/public-replays.json').read_text())['games']}
    baseline = {r['game_id']: r for r in json.loads((ROOT / 'evidence/public-token-comparison.json').read_text())['games']}
    require(len(audit['games']) == 25, 'Expected 25 games')
    require({g['oy1']['game_id'] for g in audit['games']} == set(own) == set(baseline),
            'Game selection differs')
    for game in audit['games']:
        for side, source in [('oy1', own), ('provider_adapter', baseline)]:
            record = game[side]
            ref = source[record['game_id']]
            require(record['sha256'] == ref['sha256'], 'Source hash differs')
            require(record['recording_url'] == ref['recording_url'], 'Source URL differs')
            require(record['guid'] == ref['replay_url'].rsplit('/', 1)[1], 'Source session differs')
            if side == 'provider_adapter':
                require(ref['config'] == 'openai-gpt-6-astra-high-provider-adapter', 'Wrong comparator')
            path = args.cache / f"{record['guid']}.jsonl"
            data = path.read_bytes() if path.exists() else urlopen(record['recording_url'], timeout=120).read()
            count_levels(record, data)
            if not path.exists():
                path.write_bytes(data)
    levels = compare_levels(audit['games'])
    require(len(levels) == 183 and levels == audit['levels'], 'Level comparison differs')
    highlights = [{'game_id': x['game_id'], 'level': x['level']} for x in levels[:4]]
    require(highlights == audit['highlights'], 'Highlights are not the top four reductions')
    for item in levels[:4]:
        clip = next(c for c in own[item['game_id']]['clips'] if c['level'] == item['level'])
        require(clip['level'] == item['level'] and clip['actions'] == item['oy1_actions']
                and clip['observation_rows_inclusive'] == item['oy1_rows'], 'Selected clip differs')
        require(clip['provider_adapter_actions'] == item['provider_adapter_actions'], 'Clip comparator differs')
    summary = {'levels': len(levels), 'oy1_actions': sum(x['oy1_actions'] for x in levels),
               'provider_adapter_actions': sum(x['provider_adapter_actions'] for x in levels),
               'oy1_fewer': sum(x['actions_saved'] > 0 for x in levels),
               'equal': sum(x['actions_saved'] == 0 for x in levels),
               'oy1_more': sum(x['actions_saved'] < 0 for x in levels)}
    require(summary == audit['summary'], 'Summary differs')
    print(json.dumps({'status': 'passed', **summary, 'paid_requests': 0}, indent=2))


if __name__ == '__main__':
    main()
