#!/usr/bin/env python3
"""Manager CLI for continuous work; JSON inputs keep complex operations reviewable."""
from __future__ import annotations
import argparse
import json
import sys
from runtime_protocol import load


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    # All mutations use named, inspectable JSON requests, no shell interpolation.
    commands = ('state-update', 'bind-result', 'artifact-capture', 'artifact-promote', 'project-ready',
                'workspace-register', 'claim', 'heartbeat', 'release-claim', 'import-result',
                'candidate-create', 'candidate-verify', 'dataset-capture',
                'job-request', 'job-start', 'job-status', 'job-reconcile')
    for command in commands:
        p = sub.add_parser(command); p.add_argument('--request', required=True, help='JSON object of named operation arguments')
    args = parser.parse_args(argv)
    from state_store import update, bind_result
    from artifact_versions import capture, promote
    from project_graph import readiness
    from workspaces import register, import_result
    from coordination import claim, heartbeat, release
    import candidate, datasets, data_jobs
    functions = dict(zip(commands, (update, bind_result, capture, promote, readiness, register,
                    claim, heartbeat, release, import_result, candidate.create, candidate.verify,
                    datasets.capture, data_jobs.request, data_jobs.start, data_jobs.poll, data_jobs.reconcile)))
    try:
        arguments = load(args.request)
        result = functions[args.command](**arguments)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return int(bool(result.get('errors')))
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as error:
        print('continuous work: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__': raise SystemExit(main())
