"""Safety checks for repo-managed OS maintenance; never run apt or reboot."""
import subprocess
import types
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT / "kubernetes/argocd/main-cluster/manifests/system-upgrade-plans"
MOON = ROOT / "kubernetes/argocd/moonbase/manifests/system-upgrade-plans"
SCRIPTS = yaml.safe_load((MAIN / "os-maintenance-scripts.secret.yaml").read_text())["stringData"]


@pytest.fixture
def maintenance():
    module = types.ModuleType("maintenance")
    exec(compile(SCRIPTS["maintenance.py"], "maintenance.py", "exec"), module.__dict__)
    return module


def node(name="gimli", ready="True", cordoned=False):
    return {
        "metadata": {"name": name, "labels": {}},
        "spec": {"unschedulable": cordoned},
        "status": {"conditions": [
            {"type": "Ready", "status": ready},
            *[{"type": p, "status": "False"} for p in
              ("MemoryPressure", "DiskPressure", "PIDPressure")],
        ]},
    }


def ceph(health="HEALTH_OK", details=None):
    return {"status": {"phase": "Ready", "ceph": {
        "health": health, "details": details or {},
        "lastChecked": datetime.now(timezone.utc).isoformat(),
    }}}


def test_script_copies_match():
    assert SCRIPTS == yaml.safe_load(
        (MOON / "os-maintenance-scripts.secret.yaml").read_text())["stringData"]


def test_healthy_cluster_and_own_cordon_are_allowed(maintenance):
    assert not maintenance.health_problems([node(cordoned=True)], ceph(), "gimli")


@pytest.mark.parametrize("mutate", [
    lambda n: n["status"]["conditions"][0].update(status="False"),
    lambda n: n["status"]["conditions"][1].update(status="True"),
    lambda n: n["status"]["conditions"].pop(),
    lambda n: n["spec"].update(unschedulable=True),
])
def test_unhealthy_or_cordoned_peer_blocks(maintenance, mutate):
    peer = node("helium")
    mutate(peer)
    assert maintenance.health_problems([peer], ceph(), "gimli")


@pytest.mark.parametrize("warning", ["PG_DEGRADED", "OSD_DOWN", "BLUESTORE_SLOW_OP_ALERT", "NEW_UNKNOWN_WARNING"])
def test_storage_warnings_block(maintenance, warning):
    assert maintenance.health_problems([node()], ceph("HEALTH_WARN", {warning: {}}))


def test_only_existing_auth_warnings_are_allowed(maintenance):
    details = {key: {} for key in maintenance.AUTH_WARNINGS}
    assert not maintenance.health_problems([node()], ceph("HEALTH_WARN", details))
    assert maintenance.health_problems([node()], ceph("HEALTH_WARN"))
    assert maintenance.health_problems([node()], ceph("HEALTH_ERR"))


def test_stale_ceph_status_blocks(maintenance):
    status = ceph()
    status["status"]["ceph"]["lastChecked"] = "2020-01-01T00:00:00Z"
    assert maintenance.health_problems([node()], status)


def test_scheduler_never_resets_an_active_cycle(maintenance, monkeypatch):
    calls = []
    def api(path, method="GET", body=None):
        calls.append(method)
        return {"status": {"applying": ["gimli"]}}
    monkeypatch.setattr(maintenance, "api", api)
    with pytest.raises(RuntimeError, match="still applying"):
        maintenance.trigger()
    assert calls == ["GET"]


def test_scheduler_checks_active_jobs_before_patch(maintenance, monkeypatch):
    calls = []
    def api(path, method="GET", body=None):
        calls.append(method)
        if path.endswith("/jobs"):
            return {"items": [{"metadata": {"labels": {"upgrade.cattle.io/plan": "ubuntu-os"}},
                               "status": {"active": 1}}]}
        return {"status": {}}
    monkeypatch.setattr(maintenance, "api", api)
    with pytest.raises(RuntimeError, match="still active"):
        maintenance.trigger()
    assert "PATCH" not in calls


def run_checkpoint_script(tmp_path, boot, pending=None, completed=None):
    state = tmp_path / "state"
    state.mkdir()
    release = tmp_path / "os-release"
    release.write_text('ID=ubuntu\nVERSION_ID="24.04"\n')
    boot_file = tmp_path / "boot-id"
    boot_file.write_text(boot)
    if pending:
        (state / "reboot-pending").write_text(pending)
    if completed:
        (state / "completed").write_text(completed)
    script = SCRIPTS["upgrade.sh"].replace("/var/lib/lesterlab-os-maintenance", str(state))
    script = script.replace("/etc/os-release", str(release))
    script = script.replace("/proc/sys/kernel/random/boot_id", str(boot_file))
    # Every external mutating command must be unreachable in checkpoint paths.
    guard = "\n".join(f'{c}() {{ echo "UNEXPECTED {c}" >&2; return 90; }}'
                      for c in ("apt-get", "systemd-run", "sleep", "sync", "zpool"))
    result = subprocess.run(["bash", "-s", "--", "os-2026-10-11"],
                            input=guard + "\n" + script, text=True, capture_output=True)
    assert "UNEXPECTED" not in result.stderr
    return result, state


def test_new_boot_acknowledges_reboot_without_repeating_updates(tmp_path):
    result, state = run_checkpoint_script(tmp_path, "new-boot", "os-2026-10-11\nold-boot\n")
    assert result.returncode == 0
    assert not (state / "reboot-pending").exists()
    assert (state / "completed").read_text().strip() == "os-2026-10-11"


def test_same_boot_cannot_claim_success_or_repeat_reboot(tmp_path):
    result, state = run_checkpoint_script(tmp_path, "old-boot", "os-2026-10-11\nold-boot\n")
    assert result.returncode != 0
    assert (state / "reboot-pending").exists()
    assert not (state / "completed").exists()


def test_completed_cycle_is_idempotent(tmp_path):
    result, state = run_checkpoint_script(tmp_path, "boot", completed="os-2026-10-11\n")
    assert result.returncode == 0


def test_main_drains_but_single_node_moonbase_does_not():
    main = yaml.safe_load((MAIN / "ubuntu-os-plan.yaml").read_text())["spec"]
    moon = yaml.safe_load((MOON / "debian-os-plan.yaml").read_text())["spec"]
    assert main["concurrency"] == moon["concurrency"] == 1
    assert main["drain"]["disableEviction"] is False
    assert "drain" not in moon and moon["cordon"] is True
    for directory, plan, day in ((MAIN, main, "0"), (MOON, moon, "6")):
        cron = yaml.safe_load((directory / "os-maintenance.cronjob.yaml").read_text())["spec"]
        assert cron["schedule"] == f"45 2 * * {day}"
        assert cron["timeZone"] == plan["window"]["timeZone"] == "America/New_York"
