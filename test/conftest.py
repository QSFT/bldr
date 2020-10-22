import pytest
import shutil
from pathlib import Path

DEFAULT_DOCKER_IMAGES = ["ubuntu:xenial", "ubuntu:bionic", "ubuntu:focal", "debian:bullseye"]


def pytest_addoption(parser):
    parser.addoption(
        "--docker-image", nargs="+", default=DEFAULT_DOCKER_IMAGES, help="Select docker image to run the tests on (default: %(default)s)",
    )


def pytest_generate_tests(metafunc):
    if "docker_from" in metafunc.fixturenames:
        docker_image = metafunc.config.getoption("docker_image")
        metafunc.parametrize("docker_from", docker_image)


@pytest.fixture
def asset_dir() -> Path:
    test_dir = Path(__file__).resolve().parent
    return test_dir.joinpath('asset')


@pytest.fixture
def local_repo_dir(tmp_path: Path) -> Path:
    return tmp_path.joinpath('local_repo_dir')


@pytest.fixture
def reindex_data(tmp_path: Path, asset_dir: Path) -> Path:
    reindex_data_dir = tmp_path.joinpath('test-reindex-data')
    shutil.copytree(
        asset_dir.joinpath('test-reindex-data'),
        reindex_data_dir,
    )

    return reindex_data_dir
