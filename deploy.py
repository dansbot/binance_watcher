import sys
import time
from typing import List, Set
import yaml

import k8s_commands

# a list of yaml files to be applied to the cluster.
YAML_FILES = [
    "k8s/postgres.yaml",
    "k8s/watcher-config.yaml",
    "k8s/watcher-deployments.yaml",
]


def wait_until_running(deployment_name: str, timeout: int = 60):
    """
    Wait for the specified deployment to be in "Running" status, or raise an error if the
    waiting period exceeds the specified timeout.
    """
    start_time = time.time()
    while time.time() - start_time <= timeout:
        pods = k8s_commands.get("pods", "describe", do_not_write=True)
        pods = [pod for pod in pods if k8s_commands.deployment_from_pod_name(pod["NAME"]) == deployment_name]
        if pods and sum([pod["STATUS"] == "Running" for pod in pods]) == len(pods):
            return
    raise RuntimeError(f"Waiting for {deployment_name} timed out after {timeout} seconds.")


def get_kinds() -> Set[str]:
    """
    Extract the kind from each of the yaml files and return a set of unique kinds.
    """
    kinds = set()
    for fn in YAML_FILES:
        with open(fn) as fp:
            ymls = yaml.safe_load_all(fp)
            for yml in list(ymls):
                if yml.get("kind"):
                    kinds.add(yml["kind"])
    return kinds


def clean_start(new_volume: bool):
    """
    Deletes existing resources and starts new resources, optionally skipping deletion of PersistentVolumes.
    """
    for kind in sorted(list(get_kinds())):
        if 'PersistentVolume' in kind:
            if new_volume:
                k8s_commands.delete(kind, force=True)
        else:
            k8s_commands.delete(kind)
    start()


def start():
    """
    Applies the yaml files to the cluster.
    """
    for fn in YAML_FILES:
        k8s_commands.run_process(["kubectl", "apply", "-f", fn])
        if "postgres" in fn:
            wait_until_running("postgres")


if __name__ == "__main__":
    """
    Parse command line arguments and perform either a clean start or a start.
    """
    if "--clean" in sys.argv or "-c" in sys.argv:
        clean_start("--new_volume" in sys.argv or "-nv" in sys.argv)
    else:
        start()
