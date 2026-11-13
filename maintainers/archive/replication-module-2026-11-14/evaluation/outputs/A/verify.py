"""Synthetic, no-network method checks; deliberately not media playback evidence."""
import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
INPUT = Path('/private/tmp/sdlc-replication-methods-20261114/maintainers/archive/replication-module-2026-11-14/evaluation/inputs/A.json')
PINNED_FIXTURE_SHA = {
    # Independently fixed expected fixture digests; not the accepted business pin.
    'video': '55465bfb37c9a1e3ea3f04878157e420153958b6af1a6d2b29c5f136fdc30dbc',
    'cover': '3f530dc985cd9c2b056b2658d0132385d2fc6aadc8663e7898b3dd2df6f749b3',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['legacy-etag', 'corrected'], required=True)
    args = parser.parse_args()
    facts = json.loads(INPUT.read_text())['facts']
    root = OUT / 'fixtures'
    root.mkdir(exist_ok=True)
    original_reference = copy.deepcopy(facts['fixed_reference'])
    blobs = {row['name']: row['bytes'].encode() for row in facts['source_responses']}
    for name, data in blobs.items():
        (root / (name + '.bin')).write_bytes(data)
    data_uri = facts['other_resource']['format'].split('inline ', 1)[1]
    inline_data = base64.b64decode(data_uri.split(',', 1)[1], validate=True)
    (root / 'method-cover.bin').write_bytes(inline_data)

    if args.mode == 'legacy-etag':
        mismatches = []
        for response in facts['source_responses']:
            actual = hashlib.md5(blobs[response['name']]).hexdigest()
            mismatches.append({'resource': response['name'], 'assumed_md5': response['etag'], 'actual_fixture_md5': actual})
        result = {'method': 'unsupported assumption: ETag == MD5', 'mismatches': mismatches,
                  'conclusion': 'validator assumption rejected; no source corruption conclusion', 'synthetic_only': True}
        write_json('legacy-etag-result.json', result)
        print(json.dumps(result, ensure_ascii=False))
        return 1

    checks = []
    def check(name, condition, detail):
        checks.append({'check': name, 'result': 'passed' if condition else 'failed', 'detail': detail})

    inventory = []
    for response in facts['source_responses']:
        name = response['name']
        data = (root / (name + '.bin')).read_bytes()
        check('fixture_sha256_' + name, digest(data) == PINNED_FIXTURE_SHA[name], digest(data))
        inventory.append({'resource': name, 'path': 'fixtures/' + name + '.bin', 'sha256': digest(data),
                          'length': len(data), 'declared_content_type': response['content_type'],
                          'source_etag_opaque': response['etag'], 'synthetic': True, 'decode': 'not verified',
                          'relation': 'original' if name == 'video' else 'snapshot_at_0 of demo-1@1/video'})
    inventory.append({'resource': 'method-cover', 'path': 'fixtures/method-cover.bin',
                      'sha256': digest(inline_data), 'length': len(inline_data),
                      'declared_content_type': 'image/webp', 'synthetic': True, 'decode': 'not verified'})
    expected = {'grid': 'cover', 'dialog': 'video', 'download': 'video'}
    consumers = {entry: 'local:' + resource for entry, resource in expected.items()}
    check('original_consumer_sources_are_remote', all(value.startswith('https://') for value in facts['consumer_sources'].values()),
          'the supplied current state does not meet the local requirement')
    check('all_three_static_consumers_mapped_local', set(consumers) == set(facts['consumer_sources']) and all(v.startswith('local:') for v in consumers.values()), consumers)

    def load_local(resource, given_root=root):
        candidate = (given_root / (resource + '.bin')).resolve()
        if not candidate.is_relative_to(root.resolve()):
            raise ValueError('path escape rejected')
        data = candidate.read_bytes()
        if digest(data) != PINNED_FIXTURE_SHA[resource]:
            raise ValueError('fixture digest mismatch; no network fallback')
        return data

    for entry, resource in expected.items():
        check('function_local_read_' + entry, load_local(resource) == blobs[resource],
              'function-level fixture read, not actual browser consumption')
    for name, resource in [('path_escape', '../outside'), ('missing', 'absent')]:
        try:
            load_local(resource)
        except (ValueError, FileNotFoundError) as exc:
            check(name + '_rejected', True, str(exc))
        else:
            check(name + '_rejected', False, 'unexpected success')
    original_good = (root / 'video.bin').read_bytes()
    (root / 'video.bin').write_bytes(b'corrupt synthetic fixture')
    try:
        load_local('video')
    except ValueError as exc:
        check('corrupt_rejected', True, str(exc))
    else:
        check('corrupt_rejected', False, 'unexpected success')
    finally:
        (root / 'video.bin').write_bytes(original_good)
    check('opaque_same_etag_not_same_object', digest(blobs['video']) != digest(blobs['cover']), 'video and transformed cover have different bytes')
    check('inline_resource_extracts_locally', (root / 'method-cover.bin').read_bytes() == b'Resource', 'bytes acquired from supplied fixture URI; decode remains unverified')
    check('fixture_does_not_validate_business_sha', digest(blobs['video']) != original_reference['sha256'], 'a mismatch remains explicit; the business pin is preserved')
    check('fixed_reference_unchanged', facts['fixed_reference'] == original_reference, original_reference)
    write_json('resource-inventory.json', inventory)
    write_json('proposed-local-consumers.json', {'fixed_reference': original_reference, 'consumers': consumers, 'status': 'synthetic proposal only'})
    result = {'synthetic_only': True, 'checks': checks,
              'passed': sum(row['result'] == 'passed' for row in checks),
              'failed': sum(row['result'] == 'failed' for row in checks),
              'not_verified': ['real source pin integrity', 'media decode', 'browser requests', 'real backend integration', 'video playback', 'HTTP HEAD/Range', 'package install', 'production deployment']}
    write_json('verification-result.json', result)
    print(json.dumps(result, ensure_ascii=False))
    return int(result['failed'] != 0)


if __name__ == '__main__':
    raise SystemExit(main())
