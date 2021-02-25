import logging
import os
import socket
from logging import Logger
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

import docker
import dockerpty
from docker import DockerClient
from docker.models.images import Image
from docker.errors import APIError, DockerException
from requests import RequestException

from .utils import BLDRSetupFailed


def _create_docker_client() -> DockerClient:
    try:
        return docker.from_env(version='auto')
    except DockerException as e:
        raise BLDRSetupFailed(
            'Cannot create Docker client. Is Docker daemon running?\nAdditional info: {}'.format(e)
        )


def _check_docker_client(client: DockerClient) -> None:
    try:
        client.ping()
    except (DockerException, RequestException) as e:
        raise BLDRSetupFailed(
            'Cannot connect to Docker daemon. Is Docker daemon running?\nAdditional info: {}'.format(e)
        )


class DockerImageBuilder:
    def __init__(self, client: Optional[DockerClient] = None, logger: Logger = logging.getLogger('DockerImageBuilder')) -> None:
        self._logger: logging.Logger = logger

        if client is None:
            client = _create_docker_client()
        self._client: DockerClient = client
        _check_docker_client(self._client)

    def build(self, path: Path, dockerfile: str, tag: str, buildargs: Dict, nocache: bool = False) -> 'DockerImage':
        stream = self._client.api.build(
            path=str(path),
            dockerfile=dockerfile,
            tag=tag,
            forcerm=True,
            nocache=nocache,
            buildargs=buildargs,
            decode=True,
        )
        for chunk in stream:
            if chunk.get('stream', None) is not None:
                self._logger.debug(chunk.get('stream').strip())
            elif chunk.get('errorDetail', None) is not None:
                raise DockerException(chunk.get('error'))

        return DockerImage(client=self._client, image=tag)


class DockerImage:
    def __init__(self, image: Union[str, Image], client: Optional[DockerClient] = None, logger: Optional[Logger] = None) -> None:
        if client is None:
            client = _create_docker_client()
        self._client = client
        _check_docker_client(self._client)

        self._logger = logger
        if self._logger is None:
            self._logger = logging.getLogger('DockerImage')

        self._tag = image

    def create_container(self, **kwargs: Any) -> 'DockerContainer':
        return DockerContainer(client=self._client, image=self._tag, **kwargs)


class DockerContainer:
    def __init__(
        self,
        image: Union[str, Image],
        command: Union[str, List],
        environment: Optional[Dict] = None,
        user: Optional[str] = None,
        volumes: Optional[Dict] = None,
        client: Optional[DockerClient] = None,
        logger: Logger = logging.getLogger('DockerContainer'),
        tmp_on_tmpfs: bool = True,
    ) -> None:

        if client is None:
            client = _create_docker_client()
        self._client = client
        _check_docker_client(self._client)

        self._logger = logger

        try:
            self._client.images.get(image)
        except docker.errors.ImageNotFound:
            self._client.images.pull(image)

        tmpfs = {'/tmp': 'rw,exec'} if tmp_on_tmpfs else {}

        self._container = self._client.containers.create(
            init=True,
            image=image,
            command=command,
            stdin_open=True,
            tty=os.isatty(0),
            environment=environment,
            network='host',
            security_opt=['seccomp=unconfined'],
            tmpfs=tmpfs,
            user=user,
            volumes=volumes,
            extra_hosts={socket.gethostname(): "127.0.0.1"},
        )

    def __enter__(self) -> 'DockerContainer':
        self._container.start()
        return self

    def run_with_pty(self, interactive: bool = False) -> int:
        dockerpty.start(self._client.api, self._container.id, interactive=interactive, logs=True)
        exit_code = self.get_exit_code()
        self._container.remove()
        return exit_code

    def exec(self, command: Union[str, List]) -> int:
        exec_id = self._client.api.exec_create(container=self._container.id, cmd=command)
        stream = self._client.api.exec_start(exec_id=exec_id, stream=True)

        for chunk in stream:
            self._logger.debug(chunk.decode('utf-8', errors='ignore').strip())

        return self._client.api.exec_inspect(exec_id=exec_id).get('ExitCode', 0)

    def exec_run(self, command: Union[str, List]) -> str:
        exitcode, output = self._container.exec_run(command)
        if exitcode != 0:
            raise ValueError('The following command "{}" exited with code: {}'.format(command, exitcode))
        output = output.decode('utf-8', errors='ignore')
        return output

    def exec_with_pty(self, command: Union[str, List]) -> None:
        dockerpty.exec_command(self._client.api, self._container.id, command=command)

    def get_exit_code(self) -> int:
        return self._client.api.inspect_container(self._container.id)['State'].get('ExitCode', 0)

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        try:
            self._container.kill()
        except APIError:
            pass
        finally:
            self._container.remove()
