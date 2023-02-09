import sys
import time
from typing import Set
import yaml

from pprint import pprint

import k8s_commands


def get_yaml_files():
    yaml_files = [
        "k8s/postgres.yaml",
        "k8s/watcher-config.yaml",
        "k8s/watcher-deployments.yaml",
    ]
    return yaml_files


def wait_until_running(deployment_name: str, timeout: int = 60):
    start_time = time.time()
    while time.time() - start_time <= timeout:
        pods = k8s_commands.get("pods", "describe", do_not_write=True)
        pods = [pod for pod in pods if k8s_commands.deployment_from_pod_name(pod["NAME"]) == deployment_name]
        if pods and sum([pod["STATUS"] == "Running" for pod in pods]) == len(pods):
            return
    raise RuntimeError(f"Waiting for {deployment_name} timed out after {timeout} seconds.")


def get_kinds() -> Set[str]:
    kinds = set()
    for fn in get_yaml_files():
        with open(fn) as fp:
            ymls = yaml.safe_load_all(fp)
            for yml in list(ymls):
                if yml.get("kind"):
                    kinds.add(yml["kind"])
    return kinds


def clean_start(new_volume: bool):
    for kind in get_kinds():
        if new_volume and 'PersistentVolume' in kind:
            continue
        k8s_commands.delete(kind)
    start()


def start():
    for fn in get_yaml_files():
        k8s_commands.run_process(["kubectl", "apply", "-f", fn])
        if "postgres" in fn:
            wait_until_running("postgres")


if __name__ == "__main__":
    if "--clean" in sys.argv or "-c" in sys.argv:
        clean_start("--new_volume" in sys.argv or "-nv" in sys.argv)
    else:
        start()
