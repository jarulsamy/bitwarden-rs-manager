# -*- coding: utf-8 -*-
import argparse
import time

import docker


class DockerContainerAlreadyRunningError(Exception):
    """
    Raised when a trying to start an already running docker container
    """

    def __init__(self, container_name: str):
        super().__init__(f"Docker Container {container_name} is already running.")


class DockerContainerNotFoundError(Exception):
    """
    Raised when a docker container doesn't exist
    """

    def __init__(self, container_name: str):
        super().__init__(f"Docker container {container_name} is not running.")


class DockerMultipleContainersWithSameName(Exception):
    """
    Raised when mutliple containers with the same name are found
    """

    def __init__(self, container_name: str):
        super().__init__(
            f"Multiple docker containers with name '{container_name}' found"
        )


def start():
    """
    Start docker env for bitwarden_rs
    """
    if DATA_DIR[-1] != "/":
        raise ValueError("Invalid DATA_DIR")
    filters = {"name": CONTAINER_NAME}
    containers = CLIENT.containers.list(filters=filters)
    if len(containers):
        raise DockerContainerAlreadyRunningError(CONTAINER_NAME)

    CLIENT.images.pull("bitwardenrs/server:latest")
    print(f"IMAGE: {CLIENT.images.list('bitwardenrs/server')[0].short_id}")

    env_var = [f"DOMAIN={FQDN}"]
    # volumes = {"/data/": {"bind": DATA_DIR, "mode": "rw"}}
    volumes = {DATA_DIR: {"bind": "/data/", "mode": "rw"}}
    ports = {"80/tcp": PORT}

    # Grab list of all containers named `filter`
    cont = CLIENT.containers.list(filters=filters, all=True)

    # If the container already exists, start it,
    # otherwise create it.
    if len(cont):
        cont[0].start()
        print(f"{CONTAINER_NAME}: {cont[0].short_id}")
    else:
        CLIENT.containers.run(
            "bitwardenrs/server:latest",
            environment=env_var,
            volumes=volumes,
            ports=ports,
            name=CONTAINER_NAME,
            detach=True,
        )


def stop():
    """
    Stop a running instance of bitwarden_rs
    """
    # Find the container based on the name
    filters = {"name": CONTAINER_NAME}
    containers = CLIENT.containers.list(filters=filters)
    if not containers:
        raise DockerContainerNotFoundError(CONTAINER_NAME)
    # Stop all containers with matching name.
    container = containers[0]
    container.stop()
    print(container.id)
    return container


def status():
    """
    Returns whether bitwarden_rs is running
    """
    filters = {"name": CONTAINER_NAME}
    c = CLIENT.containers.list(filters=filters)

    if not c:
        print("Not running.")
    else:
        for cont in c:
            print(f"{cont.name}: {cont.id}")


def purge():
    """
    Removes the bitwarden_rs docker container
    Data should be safe wherever it is stored on root
    """
    filters = {"name": CONTAINER_NAME}
    # Try to stop,
    # if it already stopped, find the object manually.
    try:
        container = stop()
    except DockerContainerNotFoundError:
        containers = CLIENT.containers.list(filters=filters, all=True)
        if not containers:
            raise DockerContainerNotFoundError
        container = containers[0]
    container.remove()


def restart():
    stop()
    time.sleep(2)
    start()


CLIENT = docker.from_env()
containers = CLIENT.containers.list()

FUNCTION_MAP = {
    "start": start,
    "stop": stop,
    # "init": init,
    "status": status,
    "purge": purge,
    "restart": restart,
}
CONTAINER_NAME = "bitwarden_rs"
FQDN = "https://vault.arulsamy.me"
DATA_DIR = "/bw-data/"
PORT = 8881

parser = argparse.ArgumentParser(description="Manage bitwarden_rs docker service")

ap = argparse.ArgumentParser(
    usage="./bitwarden_rs.py [start | stop | status | purge | restart"
)
ap.add_argument(
    dest="Operation", type=str, choices=FUNCTION_MAP.keys(), help="Start/Stop service"
)

args = vars(ap.parse_args())
operation = FUNCTION_MAP[args["Operation"]]

operation()
