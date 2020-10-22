from bldr.utils import get_config_file_paths
import shutil
import subprocess
from pathlib import Path
import pytest


def copytree(source: Path, destination: Path, exist_ok: bool = False) -> None:
    for source_child in source.iterdir():
        destination_child = destination.joinpath(source_child.name)
        if source_child.is_dir():
            destination_child.mkdir(exist_ok=exist_ok)
            copytree(source_child, destination_child, exist_ok=exist_ok)
        else:
            shutil.copy2(str(source_child), str(destination_child))


def extract_deb(deb_file: Path, extract_dir: Path) -> None:
    subprocess.check_call(['ar', 'x', deb_file], cwd=extract_dir)
    tar_file = list(extract_dir.glob('data.tar.*'))[0]
    subprocess.check_call(['tar', '-xf', tar_file], cwd=extract_dir)


def get_existing_config_paths():
    return [str(path) for path in get_config_file_paths() if path.exists()]


skip_if_global_config = pytest.mark.skipif(
    len(get_existing_config_paths()) > 0,
    reason="Config file(s) already exist(s): {}".format(", ".join(get_existing_config_paths()))
)
