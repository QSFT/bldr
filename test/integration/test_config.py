#
# Copyright (c) 2006-2020 Balabit
# All Rights Reserved.
#

import json
import pytest

from pathlib import Path
from bldr.cli import CLI
from ..testutil import skip_if_global_config


def test_config_with_an_existent_file(tmp_path: Path):
    config = tmp_path.joinpath('config.json')
    with config.open('w') as config_file:
        json.dump({'container_env': ['foo=bar', 'bar=baz']}, config_file)
    bldr = CLI(['bldr', '--config', str(config), 'build', 'ubuntu:bionic'])
    assert bldr.args.container_env == [('foo', 'bar'), ('bar', 'baz')]


def test_config_and_cmdline_arg_has_a_same_value_and_a_proper_type(tmp_path: Path):
    config = tmp_path.joinpath('config.json')
    with config.open('w') as config_file:
        json.dump({'hooks_dir': '/foo/hooks'}, config_file)
    bldr = CLI(['bldr', '--config', str(config), 'build', 'ubuntu:bionic'])
    hooks_dir1 = bldr.args.hooks_dir
    bldr = CLI(['bldr', 'build', 'ubuntu:bionic', '--hooks-dir', '/foo/hooks'])
    hooks_dir2 = bldr.args.hooks_dir

    assert hooks_dir1 == Path('/foo/hooks')
    assert hooks_dir2 == Path('/foo/hooks')


def test_config_override_with_cmdline_arg(tmp_path):
    config = tmp_path.joinpath('config.json')
    with config.open('w') as config_file:
        json.dump({'hooks_dir': '/foo/hooks'}, config_file)
    bldr = CLI(
        ['bldr', 'build', 'ubuntu:bionic', '--hooks-dir', '/override/hooks']
    )

    assert bldr.args.hooks_dir == Path('/override/hooks')


@skip_if_global_config
@pytest.mark.parametrize(
    'config_data, arguments, expected',
    [
        (
            {'container_env': ['foo=bar']},
            [],
            [('foo', 'bar')],
        ),
        (
            {'container_env': ['foo=bar', 'bar=baz']},
            [],
            [('foo', 'bar'), ('bar', 'baz')],
        ),
        (
            {'container_env': ['foo=bar']},
            ['--container-env', 'bar=baz'],
            [('foo', 'bar'), ('bar', 'baz')],
        ),
        (
            {},
            ['--container-env', 'foo=bar'],
            [('foo', 'bar')]
        ),
        (
            {},
            ['--container-env', 'foo=bar', '--container-env', 'bar=baz'],
            [('foo', 'bar'), ('bar', 'baz')],
        ),
    ]
)
def test_container_env(tmp_path: Path, config_data, arguments, expected):
    config = tmp_path.joinpath('config.json')

    with config.open('w') as config_file:
        json.dump(config_data, config_file)
    base_arguments = [
        'bldr', '--config', str(config), 'build', 'ubuntu:bionic',
    ]
    bldr = CLI(base_arguments + arguments)

    assert bldr.args.container_env == expected
