from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException


def load_config():
    try:
        config.load_kube_config()
    except ConfigException:
        config.load_incluster_config()


def get_core_v1():
    load_config()
    return client.CoreV1Api()


def get_apps_v1():
    load_config()
    return client.AppsV1Api()
