"""Exercise the shipped authentication block without credentials or network calls."""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "pmi_auth.json"
NODE = shutil.which("node")

# Replace only import destinations. The exact shipped control flow runs against
# these inert dependencies; nothing can launch a real login, browser, or cloud call.
DEPENDENCIES = r"""
import { appendFileSync } from "node:fs";
const scenario = JSON.parse(process.env.PMI_AUTH_TEST_SCENARIO);
function record(event) {
  appendFileSync(process.env.PMI_AUTH_TEST_TRACE, JSON.stringify(event) + "\n");
}
export const LOCAL_PRINCIPAL = "owner@example.test";
export const APPROVED_PREDECESSOR = { canonicalOrigin: "https://pmi.example.test" };
export function homedir() { return "/wsl-owner"; }
export function join(...parts) { return parts.join("/"); }
export function existsSync(path) {
  return path.endsWith("gh.exe") ? Boolean(scenario.windowsGh) : scenario.profile !== false;
}
let checkIndex = 0;
export async function ensureAuthenticated(options) {
  record({ kind: "check", ...options });
  const step = (scenario.checks ?? [])[checkIndex++] ?? {};
  if (step.throw) throw new Error("PRIVATE_PROVIDER_ERROR");
  return {
    exitCode: step.exitCode ?? (step.codes?.length ? 2 : 0),
    lines: ["safe authentication status"],
    items: step.items ?? (step.codes ?? []).map((code) => ({ state: "blocked", code })),
  };
}
let ghStatusIndex = 0;
export function spawnSync(command, args, options) {
  record({
    kind: "spawn", command, args, stdio: options.stdio,
    promptDisabled: options.env?.GH_PROMPT_DISABLED,
  });
  if (command === "git") {
    return { status: 0, stdout: scenario.remote ?? "https://github.com/example-owner/pmi.git" };
  }
  if (command === "gh" && scenario.nativeGhMissing) {
    return { status: null, error: { code: "ENOENT" } };
  }
  if (args[0] === "auth" && args[1] === "status") {
    const diagnostic = (scenario.ghStatuses ?? [])[ghStatusIndex++] ?? "";
    return { status: diagnostic ? 1 : 0, stdout: "", stderr: diagnostic };
  }
  if (args[0] === "api") {
    return { status: scenario.ghApiStatus ?? 0, stdout: scenario.githubUser ?? "example-owner" };
  }
  return { status: scenario.enrollmentStatus ?? 0 };
}
export const chromium = { launchPersistentContext() {} };
export function resolveHarnessBrowser() { return "/test/chromium"; }
export function validateProfilePath(path) { return path; }
export async function launchGuardedManagedBrowser(input) {
  record({ kind: "browser", profile: input.profile, headless: input.headless });
  if (scenario.mutation) input.onMutationAttempt();
  return {
    async newPage() {
      return {
        async goto() {},
        locator() {
          return { first() { return {
            async textContent() { return scenario.renderedRole ?? "Admin"; },
          }; } };
        },
      };
    },
    request: {
      async get(url, options) {
        record({ kind: "session", url, ...options });
        return { status() { return scenario.sessionStatus ?? 204; } };
      },
    },
    async cookies() {
      const claims = {
        email: scenario.appEmail ?? LOCAL_PRINCIPAL,
        role: scenario.appRole ?? "Admin",
      };
      const payload = Buffer.from(JSON.stringify(claims)).toString("base64url");
      const value = "header." + payload + ".signature";
      return scenario.noSession ? [] : [{ name: "__session", path: "/", value }];
    },
  };
}
export async function closeGuardedManagedBrowser() { record({ kind: "close" }); }
"""


def _content():
    return json.loads(TEMPLATE.read_text(encoding="utf-8"))["content"]


def _run(tmp_path, scenario=None, overrides=None):
    if not NODE:
        pytest.skip("Node is required to exercise the WSL command's JavaScript")
    dependency = tmp_path / "dependencies.mjs"
    dependency.write_text(DEPENDENCIES, encoding="utf-8")
    source = re.search(r"<<'PMI_AUTH'\n(.*?)\nPMI_AUTH\n", _content(), re.S).group(1)
    source = re.sub(r'from "[^"]+"', f'from "{dependency.as_uri()}"', source)
    trace = tmp_path / "trace.jsonl"
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("CLOUDSDK_AUTH_")
        and key
        not in {"GOOGLE_APPLICATION_CREDENTIALS", "CLOUDSDK_CONFIG", "GH_TOKEN", "GITHUB_TOKEN"}
    }
    env.update(
        PMI_AUTH_TEST_SCENARIO=json.dumps(scenario or {}),
        PMI_AUTH_TEST_TRACE=str(trace),
    )
    env.update(overrides or {})
    result = subprocess.run(
        [NODE, "--input-type=module"],
        input=source,
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )
    events = (
        [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]
        if trace.exists()
        else []
    )
    return result, events


def _enrollments(events):
    return [
        event
        for event in events
        if event["kind"] == "spawn"
        and (event["command"] == "npm" or event["args"][:2] == ["auth", "login"])
    ]


def test_pmi_auth_is_raw_wsl_bash_with_private_values_resolved_locally():
    data = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    content = data["content"]
    assert data["trigger"] == ":pmi-auth"
    assert data["category"] == "utility"
    assert data["stage"] == "authentication"
    assert content.startswith("(\n  set -euo pipefail\n")
    assert content.endswith("PMI_AUTH\n)\n")
    assert "/proc/version" in content
    assert "3<&0 <<'PMI_AUTH'" in content  # Enrollment keeps the terminal, not the JS heredoc.
    assert "LOCAL_PRINCIPAL" in content
    assert "APPROVED_PREDECESSOR.canonicalOrigin" in content
    assert 'join(homedir(), "pmi-assurance", "owner-admin")' in content
    assert not re.search(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", content)
    assert "/home/" not in content
    assert not re.search(r"/mnt/c/Users/[^*]", content)
    assert chr(96) * 3 not in content
    assert "powershell" not in content.lower()
    assert "USER CONTEXT" not in content
    assert not data.get("variables")


def test_ready_credentials_are_reused_without_enrollment(tmp_path):
    result, events = _run(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "canonical PMI Admin authentication verified." in result.stdout
    assert not _enrollments(events)
    checks = [event for event in events if event["kind"] == "check"]
    assert [event["need"] for event in checks] == [
        ["env"],
        ["gcloud", "adc"],
        ["canary"],
        ["gcloud", "adc", "env", "gh"],
    ]
    assert all(event["unattended"] for event in checks)
    assert checks[2]["canary"] == [
        {
            "label": "admin",
            "profile": "/wsl-owner/pmi-assurance/owner-admin",
            "origin": "https://pmi.example.test",
            "email": "owner@example.test",
        }
    ]
    session = next(event for event in events if event["kind"] == "session")
    assert session["url"] == "https://pmi.example.test/api/auth/session"
    assert session["maxRedirects"] == 0
    assert any(event["kind"] == "close" for event in events)


@pytest.mark.parametrize(
    "diagnostic",
    ["You are not logged into any GitHub hosts.", "The token in the keyring is invalid."],
)
def test_github_enrolls_once_using_its_browser_flow(tmp_path, diagnostic):
    result, events = _run(tmp_path, {"ghStatuses": [diagnostic]})
    assert result.returncode == 0, result.stderr
    assert _enrollments(events) == [
        {
            "kind": "spawn",
            "command": "gh",
            "args": [
                "auth",
                "login",
                "--hostname",
                "github.com",
                "--git-protocol",
                "https",
                "--web",
            ],
            "stdio": [3, "inherit", "inherit"],
            "promptDisabled": "1",
        }
    ]


def test_github_uses_the_same_windows_fallback_as_pmi(tmp_path):
    result, events = _run(tmp_path, {"nativeGhMissing": True, "windowsGh": True})
    assert result.returncode == 0, result.stderr
    assert any(
        event.get("command") == "/mnt/c/Program Files/GitHub CLI/gh.exe"
        and event["args"][0] == "api"
        for event in events
    )


@pytest.mark.parametrize(
    "scenario",
    [
        {"nativeGhMissing": True},
        {"ghStatuses": ["Connection timed out"]},
        {"ghApiStatus": 1},
        {"githubUser": "someone-else"},
        {"remote": "https://unexpected.example/repository.git"},
    ],
)
def test_unknown_or_wrong_github_state_stops_without_login(tmp_path, scenario):
    result, events = _run(tmp_path, scenario)
    assert result.returncode != 0
    assert not _enrollments(events)
    assert not any(event["kind"] == "browser" for event in events)


@pytest.mark.parametrize("key", ["GH_TOKEN", "GITHUB_TOKEN"])
def test_invalid_environment_github_token_is_not_replaced(tmp_path, key):
    result, events = _run(
        tmp_path,
        {"ghStatuses": ["The token in the environment is invalid."]},
        {key: "test-only"},
    )
    assert result.returncode != 0
    assert not _enrollments(events)


@pytest.mark.parametrize("code", ["adc_missing", "principal_unknown", "stale_token", "adc_stale"])
def test_google_enrollment_is_reserved_for_enrollment_failures(tmp_path, code):
    result, events = _run(tmp_path, {"checks": [{}, {"codes": [code]}]})
    assert result.returncode == 0, result.stderr
    enrollments = _enrollments(events)
    assert len(enrollments) == 1
    assert enrollments[0]["args"] == ["run", "auth:session", "--", "--browser"]
    assert enrollments[0]["stdio"][0] == 3


@pytest.mark.parametrize(
    "codes",
    [
        ["permission_denied"],
        ["unexpected_identity"],
        ["personal_identity"],
        ["unexpected_impersonation"],
        ["wrong_store"],
        ["credential_type_forbidden"],
        ["gcloud_unavailable"],
        ["identity_probe_unavailable"],
        ["auth_probe_failed"],
        ["stale_token", "unexpected_identity"],
    ],
)
def test_other_google_failures_never_start_enrollment(tmp_path, codes):
    result, events = _run(tmp_path, {"checks": [{}, {"codes": codes}]})
    assert result.returncode == 2
    assert not _enrollments(events)


@pytest.mark.parametrize("code", ["env_missing", "env_incomplete"])
def test_provider_configuration_failure_remains_a_real_blocker(tmp_path, code):
    result, events = _run(tmp_path, {"checks": [{"codes": [code]}]})
    assert result.returncode == 2
    assert not any(event["kind"] == "spawn" for event in events)


@pytest.mark.parametrize(
    "key",
    [
        "GOOGLE_APPLICATION_CREDENTIALS",
        "CLOUDSDK_CONFIG",
        "CLOUDSDK_AUTH_ACCESS_TOKEN",
        "CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE",
    ],
)
def test_google_overrides_stop_before_any_authentication(tmp_path, key):
    result, events = _run(tmp_path, overrides={key: "test-only"})
    assert result.returncode == 2
    assert not events


@pytest.mark.parametrize(
    "scenario",
    [
        {"profile": False},
        {"checks": [{}, {}, {"codes": ["human_required"]}]},
    ],
)
def test_app_enrollment_is_only_for_a_missing_profile_or_a_human_step(tmp_path, scenario):
    result, events = _run(tmp_path, scenario)
    assert result.returncode == 0, result.stderr
    enrollments = _enrollments(events)
    assert len(enrollments) == 1
    assert enrollments[0]["args"] == [
        "run",
        "auth:enroll-canary",
        "--",
        "--profile=/wsl-owner/pmi-assurance/owner-admin",
        "--origin=https://pmi.example.test",
        "--email=owner@example.test",
    ]


@pytest.mark.parametrize("code", ["canary_error", "permission_denied", "canary_not_run"])
def test_other_app_failures_do_not_open_an_enrollment_browser(tmp_path, code):
    result, events = _run(tmp_path, {"checks": [{}, {}, {"codes": [code]}]})
    assert result.returncode == 2
    assert not _enrollments(events)


@pytest.mark.parametrize(
    "scenario",
    [
        {"checks": [{}, {"codes": ["adc_stale"]}], "enrollmentStatus": 130},
        {"checks": [{}, {"codes": ["adc_stale"]}, {"codes": ["adc_stale"]}]},
        {"profile": False, "enrollmentStatus": 1},
        {"profile": False, "checks": [{}, {}, {"codes": ["human_required"]}]},
        {"ghStatuses": ["You are not logged into any GitHub hosts."], "enrollmentStatus": 1},
        {"ghStatuses": ["You are not logged into any GitHub hosts.", "Connection failed"]},
    ],
)
def test_failed_or_cancelled_enrollment_stops_without_a_login_loop(tmp_path, scenario):
    result, events = _run(tmp_path, scenario)
    assert result.returncode != 0
    assert len(_enrollments(events)) == 1
    assert "canonical PMI Admin authentication verified." not in result.stdout


@pytest.mark.parametrize(
    "scenario",
    [
        {"appEmail": "someone-else@example.test"},
        {"appRole": "Editor"},
        {"renderedRole": "Editor"},
        {"sessionStatus": 401},
        {"sessionStatus": 403},
        {"sessionStatus": 500},
        {"noSession": True},
        {"mutation": True},
    ],
)
def test_app_acceptance_requires_the_exact_identity_role_and_read_only_session(tmp_path, scenario):
    result, events = _run(tmp_path, scenario)
    assert result.returncode != 0
    assert not _enrollments(events)
    assert events[-1]["kind"] == "close"
    assert "canonical PMI Admin authentication verified." not in result.stdout


def test_unexpected_errors_do_not_print_provider_error_contents(tmp_path):
    result, events = _run(tmp_path, {"checks": [{"throw": True}]})
    assert result.returncode == 1
    assert "PRIVATE_PROVIDER_ERROR" not in result.stdout + result.stderr
    assert not _enrollments(events)
