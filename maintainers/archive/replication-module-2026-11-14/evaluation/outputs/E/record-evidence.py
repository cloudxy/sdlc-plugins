import hashlib
import json
from pathlib import Path

CONFIG = json.loads("{\"root\":\"/private/tmp/sdlc-method-scenario-outputs-20261114/E\",\"workspace\":\"/private/tmp/sdlc-replication-methods-20261114\",\"input\":\"maintainers/archive/replication-module-2026-11-14/evaluation/inputs/E.json\",\"methods\":[\"skills/coverage-matrix/SKILL.md\",\"skills/coverage-matrix/references/e2e-and-exploratory.md\",\"skills/coverage-matrix/references/test-layering.md\",\"skills/coverage-matrix/references/case-derivation.md\",\"skills/coverage-matrix/references/role-quality.md\",\"skills/coverage-matrix/templates/trace-matrix.md\",\"skills/coverage-matrix/templates/test-report.md\",\"skills/coverage-matrix/templates/bug-report.md\"],\"commands\":[{\"command\":\"cat maintainers/archive/replication-module-2026-11-14/evaluation/inputs/E.json skills/coverage-matrix/SKILL.md\",\"exit_code\":0,\"purpose\":\"Read only the specified input and skill\"},{\"command\":\"cat skills/coverage-matrix/references/e2e-and-exploratory.md skills/coverage-matrix/references/test-layering.md skills/coverage-matrix/references/case-derivation.md skills/coverage-matrix/references/role-quality.md skills/coverage-matrix/templates/trace-matrix.md skills/coverage-matrix/templates/test-report.md skills/coverage-matrix/templates/bug-report.md\",\"exit_code\":0,\"purpose\":\"Read routed method references and applicable report/matrix/defect templates\"},{\"command\":\"python3 -B /private/tmp/sdlc-method-scenario-outputs-20261114/E/record-evidence.py\",\"exit_code\":null,\"purpose\":\"Generate provenance only; not a scenario test\",\"result\":\"pending tool observation at generation time\"}]}")
ROOT = Path(CONFIG['root'])
WORKSPACE = Path(CONFIG['workspace'])

def bind(relative):
    data = (WORKSPACE / relative).read_bytes()
    return {'path': relative, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}

payload = {
    'scene': 'E',
    'evaluation_identity': 'prompt-bound independent evaluator; not a native SDLC QA role runtime',
    'input': bind(CONFIG['input']),
    'method_reads': [bind(path) for path in CONFIG['methods']],
    'hash_binding': 'Hashes calculated from the same read-only candidate method paths after method reads; parent maintained method text unchanged during evaluation.',
    'commands': [dict(row, cwd=str(WORKSPACE)) for row in CONFIG['commands']],
    'scenario_runtime_commands_executed': [],
    'artifacts': ['test-report.md', 'coverage.md'],
    'scope': 'Only supplied synthetic observations reviewed; no product runtime, clipboard, gesture, network, deployment, process operation or source mutation.',
    'limits': ['No actual media/download file or computed download SHA', 'No persistence record', 'No screenshot opened', 'No real input device used', 'No formal project FR/NFR/J/EV catalog supplied', 'No production reproduction or release conclusion'],
    'read_exclusions': 'No maintainer criteria, retrospective conclusions, VSC source evidence or other archive material was read.'
}
(ROOT / 'commands.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
print('E: recorded input and 8 method SHA-256 bindings; 0 scenario runtime tests; report and targeted coverage plan written.')
