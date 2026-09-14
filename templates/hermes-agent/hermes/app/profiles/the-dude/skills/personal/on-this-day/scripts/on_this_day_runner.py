#!/usr/bin/env python3
"""On-This-Day runner: stage / generate / publish outside the scrubbed sandbox.

Reads MINIMAX_API_KEY from the profile .env at runtime into the child process
only, never prints it, and prefixes /opt/hermes/.venv/bin to PATH so `hermes
send` resolves during publish.

Usage:
  python3 on-this-day-runner.py stage    --selection <selection-file>
  python3 on-this-day-runner.py generate --prompt-file <prompt-file> --output-dir <dir>
  python3 on-this-day-runner.py publish  --image <abs-path> --image-token <token>
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

SKILL_SCRIPT = Path_ = None


def _skill_script():
    home = os.environ.get('HERMES_HOME', '/opt/data/profiles/the-dude')
    return Path(home) / 'skills/personal/on-this-day/scripts/on_this_day.py'


def run(argv):
    skill = _skill_script()
    if not skill.exists():
        print(json.dumps({'status': 'error', 'message': f'missing {skill}'}), file=sys.stderr)
        sys.exit(1)
    env = dict(os.environ)
    dotenv = Path(env.get('HERMES_HOME', '/opt/data/profiles/the-dude')) / '.env'
    if dotenv.exists():
        for line in dotenv.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                if key not in env:
                    env[key] = value
    envdir = Path('/opt/hermes/.venv/bin')
    env['PATH'] = f'{envdir}:{env.get("PATH", "")}'
    result = subprocess.run([sys.executable, str(skill)] + argv, env=env,
                            capture_output=True, text=True, timeout=600)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    sys.exit(result.returncode)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['stage', 'generate', 'publish'])
    parser.add_argument('--selection')
    parser.add_argument('--prompt-file')
    parser.add_argument('--output-dir')
    parser.add_argument('--image')
    parser.add_argument('--image-token')
    args = parser.parse_args()
    if args.command == 'stage' and args.selection:
        run(['stage', '--selection', args.selection])
    elif args.command == 'generate' and args.prompt_file and args.output_dir:
        home = Path(os.environ.get('HERMES_HOME', '/opt/data/profiles/the-dude'))
        gen = home / 'skills/media/minimax-image-gen/scripts/generate.py'
        if not gen.exists():
            print(json.dumps({'status': 'error', 'message': f'missing {gen}'}), file=sys.stderr)
            sys.exit(1)
        env = dict(os.environ)
        dotenv = home / '.env'
        if dotenv.exists():
            for line in dotenv.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    if key not in env:
                        env[key] = value
        result = subprocess.run([sys.executable, str(gen),
                                 '--prompt-file', args.prompt_file,
                                 '--output-dir', args.output_dir],
                                env=env, capture_output=True, text=True, timeout=600)
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        sys.exit(result.returncode)
    elif args.command == 'publish' and args.image and args.image_token:
        run(['publish', '--image', args.image, '--image-token', args.image_token])
    else:
        parser.error('missing required arguments for the selected command')


if __name__ == '__main__':
    main()
