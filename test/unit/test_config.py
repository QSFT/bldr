import argparse
import json

from pathlib import Path

from bldr.config import ArgumentParser, JSONConfigLoader


EXAMPLE_CONFIG = """
{
    "foo": "bar",
    "some_param": 1234
}
    """

NO_SUCH_FILE_PATH = Path("/tmp/____no_such_file_____")


def test_argparse_full_config(tmp_path: Path):
    config_path = tmp_path.joinpath("config.json")
    config_path.open('w').write(EXAMPLE_CONFIG)

    parser = ArgumentParser(config_loader=JSONConfigLoader([config_path]))

    parser.add_argument("--foo", help="Foo", default="default")
    parser.add_argument("--some-param", help="Some parameter", type=int, default=12)

    ns = parser.parse_args([])
    assert ns.foo == "bar"
    assert ns.some_param == 1234


def test_argparse_full_config_override(tmp_path: Path):
    config_path = tmp_path.joinpath("config.json")
    config_path.open('w').write(EXAMPLE_CONFIG)

    parser = ArgumentParser(config_loader=JSONConfigLoader([config_path]))
    parser.add_argument("--foo", help="Foo", default="default")
    parser.add_argument("--some-param", help="Some parameter", type=int, default=12)

    ns = parser.parse_args(["--foo", "cmdline", "--some-param", "7777"])
    assert ns.foo == "cmdline"
    assert ns.some_param == 7777


def test_argparse_no_config():

    assert not NO_SUCH_FILE_PATH.is_file(), "{} should not exist".format(NO_SUCH_FILE_PATH)

    parser = ArgumentParser(config_loader=JSONConfigLoader([NO_SUCH_FILE_PATH]))
    parser.add_argument("--foo", help="Foo", default="default")
    parser.add_argument("--some-param", help="Some parameter", type=int, default=12)

    ns = parser.parse_args([])
    assert ns.foo == "default"
    assert ns.some_param == 12


def test_argparse_empty_config(tmp_path: Path):
    config_path = tmp_path.joinpath("config.json")
    config_path.open('w').write("{}")

    parser = ArgumentParser(config_loader=JSONConfigLoader([config_path]))
    parser.add_argument("--foo", help="Foo", default="default")
    parser.add_argument("--some-param", help="Some parameter", type=int, default=12)

    ns = parser.parse_args([])
    assert ns.foo == "default"
    assert ns.some_param == 12


def test_argparse_inheritance(tmp_path: Path):
    example_config = json.loads(EXAMPLE_CONFIG)

    config1_path = tmp_path.joinpath("config1.json")
    config1_path.open('w').write(EXAMPLE_CONFIG)

    example_config["foo"] = "config2"
    del example_config["some_param"]

    config2_path = tmp_path.joinpath("config2.json")
    config2_path.open('w').write(json.dumps(example_config))

    example_config["foo"] = "config3"
    example_config["some_param"] = None
    config3_path = tmp_path.joinpath("config3.json")
    config3_path.open('w').write(json.dumps(example_config))

    parser = ArgumentParser(config_loader=JSONConfigLoader([config1_path, config2_path, config3_path]))
    parser.add_argument("--foo", help="Foo", default="default")
    parser.add_argument("--some-param", help="Some parameter", type=int, default=12)

    ns = parser.parse_args([])

    assert ns.foo == "config3", "foo should come from config3.json"
    assert ns.some_param == 12, "some_param should come from argparse default as config3.json clears it"


def test_argparse_api_definitions():
    parser = argparse.ArgumentParser()
    assert hasattr(parser, "_actions"), "parser object should have '_actions' attribute"
    assert type(parser._actions) == list, "parser's '_actions' attribute must be a list"
    assert hasattr(argparse, "_StoreAction"), "argparse must have a '_StoreAction' class defined"
