import logging
import os
import pwd
import re
import shutil
import sys
from logging import Logger
from pathlib import Path
from typing import Dict, IO, List, Union, Optional
from tempfile import TemporaryDirectory

from .docker_utils import DockerImageBuilder, DockerImage, DockerContainer
from .utils import BLDRError, BLDRSetupFailed, escape_docker_image_tag, get_resource


PRE_BUILD_HOOK = "/hooks/pre-build"


class BLDR:

    def __init__(self,
        local_repo_dir: Path,
        source_dir: Path,
        docker_from: str,
        deb_build_options: Optional[str] = None,
        debug_shell: bool = False,
        snapshot: bool = False,
        nocache: bool = False,
        logger: Logger = logging.getLogger("bldr"),
        container_env: Optional[Dict] = None,
        hooks_dir: Optional[Path] = None,
        disable_tmpfs: bool = False,
    ) -> None:

        if ("\n" in docker_from or " " in docker_from):
            raise BLDRSetupFailed("Invalid docker_from parameter: {!r}".format(docker_from))
        self._docker_from = docker_from

        self._local_repo_dir = local_repo_dir.resolve()
        self._source_dir = source_dir.resolve()

        self._debug_shell = debug_shell
        self._deb_build_options = deb_build_options
        self._snapshot = snapshot
        self._nocache = nocache

        if container_env is None:
            self._container_env = {}
        else:
            self._container_env = container_env.copy()

        self._hooks_dir = hooks_dir
        self._logger = logger

        self._nonpriv_user_uid = self._get_nonpriv_user_uid()
        self._nonpriv_user_name = pwd.getpwuid(self._nonpriv_user_uid).pw_name

        self._tmp_on_tmpfs = not disable_tmpfs

    @property
    def local_repo_dir(self) -> Path:
        return self._local_repo_dir

    def _get_nonpriv_user_uid(self) -> int:
        local_uid = os.getuid()
        if local_uid != 0:
            return local_uid

        nonpriv_user_uid = int(os.environ.get('SUDO_UID', default='0'))
        if nonpriv_user_uid != 0:
            return nonpriv_user_uid

        raise BLDRSetupFailed("Refusing to run as root. Please run this script as a non-root user.")

    @classmethod
    def _get_source_package_name(cls, package_dir: Path) -> str:
        control_file = package_dir.joinpath('debian', 'control')
        with control_file.open('r') as fp:
            for line in fp:
                if line.startswith('Source: '):
                    return line.split('Source: ', 1)[1].strip()

        raise BLDRSetupFailed("Cannot parse {}".format(control_file))

    @classmethod
    def _get_clean_package_name(cls, package_name: str) -> str:
        return re.sub('[^A-Za-z0-9_.-]+', '', package_name)

    def generate_dockerfile(self, template_file: Path, output_file: Path) -> None:
        template = template_file.read_text()
        content = template.format(docker_from=self._docker_from)
        output_file.write_text(content)

    def _build_image(self, tag: str, control_file: Optional[Path] = None) -> DockerImage:
        self._logger.debug('Start building container image.')
        buildargs = {}

        if os.environ.get('http_proxy', None) is not None:
            buildargs['http_proxy'] = os.environ.get('http_proxy')
        if os.environ.get('no_proxy', None) is not None:
            buildargs['no_proxy'] = os.environ.get('no_proxy')
        buildargs['NONPRIV_USER_UID'] = str(self._nonpriv_user_uid)
        buildargs['NONPRIV_USER_NAME'] = self._nonpriv_user_name

        with TemporaryDirectory(prefix="bldr_docker_dir_") as tmp_dir:
            docker_files_dir = Path(tmp_dir).joinpath('docker_files')
            shutil.copytree(str(get_resource('.')), str(docker_files_dir))
            if control_file is None:
                docker_files_dir.joinpath('control').write_text('')
            else:
                shutil.copyfile(str(control_file), str(docker_files_dir.joinpath('control')))

            dockerfile = docker_files_dir.joinpath('Dockerfile')
            self.generate_dockerfile(
                template_file=docker_files_dir.joinpath('Dockerfile.tpl'),
                output_file=dockerfile,
            )

            if self._hooks_dir is not None:
                docker_hooks_dir = docker_files_dir.joinpath("hooks")
                shutil.rmtree(str(docker_hooks_dir))
                shutil.copytree(str(self._hooks_dir), str(docker_hooks_dir))

            image = DockerImageBuilder().build(
                path=docker_files_dir,
                dockerfile=dockerfile.name,
                tag=tag,
                nocache=self._nocache,
                buildargs=buildargs,
            )

        return image

    def _create_container(self, image: DockerImage, command: Union[str, list, None] = None) -> DockerContainer:
        if command is None:
            command = ['/bin/sleep', '24h']    # with this command the containers stops surely after a day

        env_vars = {}
        if os.environ.get('http_proxy', None) is not None:
            env_vars['http_proxy'] = os.environ.get('http_proxy')
        if os.environ.get('no_proxy', None) is not None:
            env_vars['no_proxy'] = os.environ.get('no_proxy')
        if self._deb_build_options is not None:
            env_vars['DEB_BUILD_OPTIONS'] = self._deb_build_options
        env_vars['BLDR_SNAPSHOT'] = '1' if self._snapshot else ''
        env_vars['TERM'] = os.environ.get('TERM', 'xterm-256color')

        for env_key, env_value in self._container_env.items():
            env_vars[env_key] = env_value

        self._local_repo_dir.mkdir(parents=True, exist_ok=True)

        container = image.create_container(
            command=command,
            environment=env_vars,
            user=self._nonpriv_user_uid,
            volumes={
                self._source_dir: {'bind': '/source', 'mode': 'z'},
                self._local_repo_dir: {'bind': '/local-apt', 'mode': 'z'}
            },
            tmp_on_tmpfs=self._tmp_on_tmpfs,
        )

        return container

    def get_package_relative_dir(self, package_dir: Path) -> Path:
        return package_dir.relative_to(self._source_dir)

    def _container_exec(self, container: DockerContainer, command: Union[str, List]):
        exitcode = container.exec(command)
        if self._debug_shell and exitcode > 0:
            container.exec_with_pty(command='/bin/bash')
        return exitcode

    def build(self, package_dir: Path) -> DockerImage:
        package_dir = package_dir.resolve()

        source_package_name = self._get_source_package_name(package_dir)
        clean_package_name = self._get_clean_package_name(source_package_name)

        tag = 'bldr-deb-builder-{release}:{source_package_name}'.format(
            release=escape_docker_image_tag(self._docker_from),
            source_package_name=clean_package_name,
        )

        image = self._build_image(tag=tag, control_file=package_dir.joinpath('debian', 'control'))
        with self._create_container(image) as container:
            exitcode = self._container_exec(container, command=[PRE_BUILD_HOOK])
            if exitcode > 0:
                raise BLDRError('BLDR pre-build hook failed with exit code {exitcode}'.format(exitcode=exitcode), exitcode)

            exitcode = self._container_exec(container, command=['build-deb', str(self.get_package_relative_dir(package_dir))])
            if exitcode > 0:
                raise BLDRError('BLDR build failed with exit code {exitcode}'.format(exitcode=exitcode), exitcode)

        return image

    @classmethod
    def selftest(cls) -> None:
        for ubuntu_release in ['xenial', 'bionic', 'focal']:
            image = DockerImage(image='ubuntu:{}'.format(ubuntu_release))
            assert image is not None, "DockerImage should be initialized without Exception"

            with image.create_container(command=['sleep', '3600']) as container:
                assert container is not None, "docker should be able to start an ubuntu {} container".format(ubuntu_release)

                assert container.exec(command=['false']) == 1, "return code should be returned"

                cmd = 'useradd -u 1000 user && su user -c whoami'   # checking for possible SELinux issues
                assert container.exec_run(command=['bash', '-c', cmd]) == 'user\n', "'su user' should succeed"

                cmd = 'echo "deb http://archive.ubuntu.com/ubuntu {} main universe" > /etc/apt/sources.list'.format(ubuntu_release)
                container.exec_run(command=['bash', '-c', cmd])

                cmd = 'export DEBIAN_FRONTEND=noninteractive; apt-get -qq update && apt-get -qq install zip >/dev/null'
                container.exec_run(command=['bash', '-c', cmd])

    def reindex(self) -> None:
        tag = 'bldr-deb-builder-{release}:reindex'.format(
            release=escape_docker_image_tag(self._docker_from),
        )

        image = self._build_image(tag=tag)
        with self._create_container(image) as container:
            exitcode = self._container_exec(container, command=['reindex'])
            if exitcode > 0:
                raise BLDRError('BLDR reindex failed with exit code {exitcode}'.format(exitcode=exitcode), exitcode)

    def shell(self, package_dir: Path, stdin: IO[str] = None) -> None:
        package_dir = package_dir.resolve()

        control_file = package_dir.joinpath('debian', 'control')
        if control_file.is_file():
            source_package_name = self._get_source_package_name(package_dir)
            clean_package_name = self._get_clean_package_name(source_package_name)
            suffix = clean_package_name
        else:
            control_file = None     # type: ignore
            suffix = 'shell'

        tag = 'bldr-deb-builder-{release}:{suffix}'.format(
            release=escape_docker_image_tag(self._docker_from),
            suffix=suffix,
        )

        image = self._build_image(tag=tag, control_file=control_file)
        if os.isatty(0) and not stdin:
            container = self._create_container(image=image, command=['/bin/bash'])
            exitcode = container.run_with_pty(interactive=True)
        else:
            if stdin is None:
                stdin = sys.stdin
            command = stdin.read()
            container = self._create_container(image=image, command=['/bin/bash', '-c', command])
            exitcode = container.run_with_pty()

        if exitcode > 0:
            raise BLDRError('BLDR shell failed with exit code {exitcode}'.format(exitcode=exitcode), exitcode)
