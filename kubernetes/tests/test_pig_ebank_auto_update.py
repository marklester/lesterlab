"""Exercise rollout decisions without connecting to GHCR or Kubernetes."""
import copy
import types
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml


@pytest.fixture
def updater():
    root = Path(__file__).resolve().parents[2]
    manifest = root / "kubernetes/argocd/main-cluster/manifests/pig-ebank/pig-ebank.image-update.configmap.yaml"
    script = yaml.safe_load(manifest.read_text())["data"]["check-image.py"]
    module = types.ModuleType("updater")
    exec(compile(script, str(manifest), "exec"), module.__dict__)
    return module


def deployment(updater, annotation=None):
    return {
        "metadata": {"resourceVersion": "123"},
        "spec": {"template": {
            "metadata": {"annotations": {updater.ANNOTATION: annotation} if annotation else {}},
            "spec": {"containers": [{"name": "pig-ebank", "image": updater.IMAGE}]},
        }},
    }


@pytest.mark.parametrize("previous", [None, "sha256:" + "a" * 64])
def test_changed_or_initial_digest_requests_one_rollout(updater, previous):
    current = "sha256:" + "b" * 64
    updater.resolve_digest = Mock(return_value=current)
    updater.deployment_request = Mock(return_value=deployment(updater, previous))
    updater.main()
    assert updater.deployment_request.call_count == 2
    patch = updater.deployment_request.call_args.args[0]
    assert patch == {
        "metadata": {"resourceVersion": "123"},
        "spec": {"template": {"metadata": {"annotations": {updater.ANNOTATION: current}}}},
    }


def test_unchanged_digest_does_not_roll_out(updater):
    digest = "sha256:" + "a" * 64
    updater.resolve_digest = Mock(return_value=digest)
    updater.deployment_request = Mock(return_value=deployment(updater, digest))
    updater.main()
    updater.deployment_request.assert_called_once_with()


@pytest.mark.parametrize("mode", ["paused", "pinned"])
def test_operator_pause_or_pinned_rollback_is_respected(updater, mode):
    spec = copy.deepcopy(deployment(updater))
    if mode == "paused":
        spec["spec"]["paused"] = True
    else:
        spec["spec"]["template"]["spec"]["containers"][0]["image"] += "@sha256:" + "a" * 64
    updater.deployment_request = Mock(return_value=spec)
    updater.resolve_digest = Mock()
    updater.main()
    updater.resolve_digest.assert_not_called()
    updater.deployment_request.assert_called_once_with()


def test_registry_failure_leaves_deployment_unchanged(updater):
    updater.deployment_request = Mock(return_value=deployment(updater))
    updater.resolve_digest = Mock(side_effect=RuntimeError("registry unavailable"))
    with pytest.raises(RuntimeError, match="registry unavailable"):
        updater.main()
    updater.deployment_request.assert_called_once_with()


def test_conflicting_deployment_change_is_not_silently_retried(updater):
    updater.deployment_request = Mock(side_effect=[deployment(updater), RuntimeError("409 conflict")])
    updater.resolve_digest = Mock(return_value="sha256:" + "a" * 64)
    with pytest.raises(RuntimeError, match="409 conflict"):
        updater.main()
    assert updater.deployment_request.call_count == 2
