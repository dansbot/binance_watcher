import os
import subprocess
from typing import List, Tuple, Union

KUBE_CONFIG = os.path.join(os.environ.get('USERPROFILE'), ".kube", "config")


def set_config(file: str):
    global KUBE_CONFIG
    KUBE_CONFIG = file


def run_process(cmd: List[str], **kwargs) -> Tuple[str, str]:
    cmd.append(f"--kubeconfig={KUBE_CONFIG}")
    if not kwargs.get("do_not_write"):
        if len(cmd) > 9:
            print(f"running command: {' '.join(cmd[:6] + ['...'] + cmd[-2:-1])}")
        else:
            print(f"running command: {' '.join(cmd[:-1])}")
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    out, err = out.decode('utf-8'), err.decode('utf-8')
    if kwargs.get("allowed_errors") and err:
        okay = False
        for ok_err in kwargs.get("allowed_errors"):
            if ok_err == err.strip():
                okay = True
        assert okay, err
    else:
        assert not err, err
    return out, err


def get_contexts(**kwargs):
    # TODO: finish this code
    cmd = ['kubectl', 'config', 'get-contexts']
    out, err = run_process(cmd, **kwargs)
    print(out)
    # for o in out.split('\n'):
    #     print(o)


def set_context(context: str, **kwargs):
    cmd = ['kubectl', 'config', 'use-context', context]
    run_process(cmd, **kwargs)


def get(kind: str, filt: str, **kwargs) -> List[Union[str, dict]]:
    cmd = ["kubectl", "get", kind]
    out, err = run_process(
        cmd,
        **{**kwargs, **{
            "allowed_errors": [
                "No resources found in default namespace.",
                "No resources found"
            ]}})
    ret = []
    lines = out.split('\n')
    cols = [s.strip() for s in lines[0].split()]
    for s in lines[1:]:
        if not s.strip():
            continue
        if filt == 'name':
            s = s.split()[0].strip()
        elif filt == 'describe':
            info = {}
            for k, v in zip(cols, [x.strip() for x in s.split()]):
                info[k] = v
            s = info
        ret.append(s)
    return ret


def delete(kind: str, delete_list: List[str] = None, **kwargs):
    force = kwargs.get('force', False)
    if delete_list is None:
        delete_list = get(kind, 'name', **kwargs)
    if delete_list:
        cmd = ["kubectl", "delete", kind] + delete_list
        if force:
            cmd.extend(["--grace-period=0"])
        run_process(cmd, **kwargs)


def get_kind_by_status(kind: str, **kwargs) -> dict:
    ret = {}
    for p in get(kind, 'describe', **kwargs):
        try:
            ret[p["STATUS"]].append(p)
        except KeyError:
            ret[p["STATUS"]] = [p]
    return ret


def deployment_from_pod_name(pod_name: str) -> str:
    return pod_name.split('-')[0]


if __name__ == "__main__":
    delete("deployments")
