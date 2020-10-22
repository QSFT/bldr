import os
import pwd
from pathlib import Path
from pkg_resources import resource_filename


class BLDRError(Exception):
    def __init__(self, msg: str, exitcode: int = 1) -> None:
        self.msg = msg
        self.exitcode = exitcode

    def __str__(self) -> str:
        return self.msg


class BLDRSetupFailed(BLDRError):
    def __init__(self, msg: str, exitcode: int = 1) -> None:
        msg = 'Setting up BLDR failed: {}'.format(msg)
        super().__init__(msg, exitcode)


def get_resource(path: str) -> Path:
    return Path(resource_filename('bldr', str(Path('data', path))))


def escape_docker_image_tag(tag: str) -> str:
    return tag.replace(":", "-").replace("/", "-")


def get_home_dir() -> Path:
    if 'SUDO_UID' in os.environ and os.geteuid() == 0:
        uid = int(os.environ['SUDO_UID'])
    else:
        uid = os.getuid()

    pw_entry = pwd.getpwuid(uid)
    home = Path(pw_entry.pw_dir)

    return home


def get_config_file_paths():
    home_dir = get_home_dir()
    config_file_paths = [
        Path('/etc/bldr.conf'),
        home_dir.joinpath('.config/bldr.conf'),
        home_dir.joinpath('.bldr.conf'),
        Path('bldr.conf'),
    ]

    return config_file_paths
