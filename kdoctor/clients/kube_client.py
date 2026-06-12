from kubernetes import client, config


def get_core_v1():
    try:
        config.load_kube_config()
    except Exception:
        config.load_incluster_config()

    return client.CoreV1Api()