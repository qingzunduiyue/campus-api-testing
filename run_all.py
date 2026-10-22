"""Run the saved baseline and fixed snapshots using the current interpreter.

Exit zero only when the baseline has exactly the two documented assertion
failures, neither run has execution errors, and all fixed tests pass.
"""
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
EXPECTED_FAILURES = {
    'test_major_update_same_code_changes_name',
    'test_login_unsupported_role_is_rejected',
}


def installed_versions():
    versions = {}
    for line in (ROOT/'requirements-test.txt').read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        name, expected = line.split('==',1)
        actual = metadata.version(name)
        if actual != expected:
            raise RuntimeError(f'Dependency version mismatch: {name} expected {expected}, got {actual}')
        versions[name] = actual
    return versions


def main():
    versions = installed_versions()
    result_dir = ROOT/'results'
    result_dir.mkdir(exist_ok=True)
    runs = {}
    for snapshot in ['baseline','fixed']:
        result_path = result_dir/f'{snapshot}_results.json'
        if result_path.exists():
            result_path.unlink()
        completed = subprocess.run(
            [sys.executable,'-B',str(ROOT/'test_student_system.py'),
             '--snapshot',str(ROOT/snapshot),'--result',str(result_path)],
            cwd=ROOT, text=True, encoding='utf-8', capture_output=True,
            env={**os.environ,'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1'})
        if not result_path.is_file():
            # Keep error output in the console for diagnosis; do not embed the
            # local machine's paths in the checked-in evidence examples.
            print(completed.stdout,completed.stderr,file=sys.stderr)
            raise RuntimeError(f'{snapshot} failed to produce structured results')
        result = json.loads(result_path.read_text(encoding='utf-8'))
        runs[snapshot] = result
        runs[snapshot]['process_exit_code'] = completed.returncode
        summary = {key:result[key] for key in ['tests_run','passed','assertion_failures','execution_errors']}
        print(snapshot,json.dumps(summary,ensure_ascii=False))

    baseline, fixed = runs['baseline'], runs['fixed']
    actual_failures = {test['name'] for test in baseline['tests'] if test['status']=='assertion_failed'}
    checks = {
        'baseline_has_nine_tests':baseline['tests_run']==9,
        'baseline_failures_match_documented_cases':actual_failures==EXPECTED_FAILURES,
        'baseline_has_seven_passes_and_two_assertion_failures':baseline['passed']==7 and baseline['assertion_failures']==2,
        'baseline_has_no_execution_errors':baseline['execution_errors']==0,
        'baseline_exit_code_is_one':baseline['process_exit_code']==1,
        'fixed_all_nine_pass':fixed['tests_run']==9 and fixed['passed']==9,
        'fixed_has_no_failures_or_errors':fixed['assertion_failures']==0 and fixed['execution_errors']==0,
        'fixed_exit_code_is_zero':fixed['process_exit_code']==0,
        'original_main_and_settings_not_imported':all(not run['original_main_or_settings_imported'] for run in runs.values()),
    }
    report = {
        'verification_passed':all(checks.values()),'checks':checks,
        'python':platform.python_version(),'platform':platform.system(),
        'dependencies':versions,
        'expected_baseline_failure_names':sorted(EXPECTED_FAILURES),
        'execution_scope':'Fresh in-memory SQLite per test, in-process ASGI, no original settings or network connections.',
        'github_actions_status':'Configuration prepared; no GitHub-hosted run has been performed.',
    }
    (result_dir/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('verification_passed',report['verification_passed'])
    return 0 if report['verification_passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
