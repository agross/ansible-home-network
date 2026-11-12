#!/usr/bin/env python3
"""Run the reviewer scenarios through the locally pinned Sevro installation."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', action='append', dest='names')
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--dry', action='store_true')
    parser.add_argument('--trials', type=int, default=1)
    parser.add_argument('--model', default='gpt-6.1-sol')
    parser.add_argument('--effort', default='medium')
    parser.add_argument('--codex-auth-file', type=Path,
                        default=Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'auth.json')
    args = parser.parse_args()
    cases = json.loads((HERE / 'cases.json').read_text())
    names = args.names or [case['name'] for case in cases]
    if not set(names) <= {case['name'] for case in cases}:
        parser.error('unknown case')
    package = HERE / 'node_modules/@bjoernrochel/sevro/package.json'
    if not package.is_file() or json.loads(package.read_text())['version'] != '1.1.2':
        parser.error('run npm ci in evals/reviewer to install Sevro 1.1.2')
    codex = shutil.which('codex')
    if not codex:
        parser.error('Codex CLI is required for the isolated surrogate host')
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    results = []
    with tempfile.TemporaryDirectory(prefix='reviewer-sevro-config-') as temporary:
        command = Path(temporary) / 'extension-command.json'
        command.write_text(json.dumps([sys.executable, str(HERE / 'extension.py')]))
        for name in names:
            destination = output / name
            if destination.exists():
                parser.error('use a fresh output directory for every run')
            destination.mkdir()
            argv = [str(HERE / 'node_modules/.bin/sevro'), 'run', '--json',
                    '--extension-command-file', str(command), '--case-id', name,
                    '--project-root', str(ROOT), '--results-root', str(destination / 'evidence'),
                    '--runtime-config-file', str(HERE / 'runtime.json'),
                    '--host', 'codex', '--codex-bin', codex,
                    '--codex-auth-file', str(args.codex_auth_file.resolve()),
                    '--model', args.model, '--effort', args.effort,
                    '--condition', 'passive', '--trials', str(args.trials), '--threshold', '1',
                    '--codex-timeout-ms', '300000', '--shell-isolation', '--protected-root', str(ROOT)]
            sources = [HERE / 'extension.py', HERE / 'fixture.py', HERE / 'grade.py', HERE / 'cases.json']
            skill = ROOT / 'templates/hermes-agent/hermes/templates/app/profiles/reviewer/skills/development/github-pr-review'
            sources.extend(path for path in skill.rglob('*') if path.is_file() and '__pycache__' not in path.parts)
            sources.append(skill.parents[2] / 'SOUL.md')
            for source in sources:
                argv.extend(['--extension-source-file', str(source)])
            if args.dry:
                argv.append('--dry')
            print(f'Running {name} through Sevro 1.1.2...', flush=True)
            completed = subprocess.run(argv, text=True, capture_output=True)
            (destination / 'result.json').write_text(completed.stdout)
            (destination / 'stderr.txt').write_text(completed.stderr)
            results.append({'name': name, 'exit_code': completed.returncode,
                            'result': str(destination / 'result.json')})
            print(f'{name}: exit {completed.returncode}; {destination / "result.json"}', flush=True)
    (output / 'index.json').write_text(json.dumps({'sevro': '1.1.2', 'dry': args.dry, 'cases': results}, indent=2) + '\n')
    return 0 if all(result['exit_code'] == 0 for result in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
