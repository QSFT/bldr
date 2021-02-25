import argparse
import logging
import os
import sys
import json
from pathlib import Path
from textwrap import dedent
from typing import List, Tuple

from .bldr import BLDR
from .version import get_version
from .utils import BLDRError, escape_docker_image_tag, get_config_file_paths
from .config import ArgumentParser, JSONConfigLoader, ConfigLoader, SubParsers


EXTRA_HELP = """
There are 2 repositories used in building, in priority order:\n
    1. The local repository, to which the built packages go. This is here to enable building packages that depend on
        other locally built packages.\n
    2. The pre-configured repositories\n
\n
The packages will be installed from the highest priority repository where they are available, even if they are older
than the ones in the following repositories where it exists, with the version corresponding to that repository.\n
\n
Important info: -dev packages usually depend on the normal ones with a "= version" clause. If an old package is present
in a high priority repository (such as the filtering proxy), but the -dev package is not, the -dev one will be acquired
from a lower priority repo, possibly with a different version. This will cause apt to fail with a dependency error,
because it can't resolve such situations.
"""

logging.basicConfig(format="%(message)s", level=logging.DEBUG, stream=sys.stdout)
logging.getLogger("docker").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


class CLI:
    description = ""

    def __init__(self, argv: List[str], logger: logging.Logger = logging.getLogger("cli")) -> None:
        self._logger = logger
        self.args = self._parse_arguments(argv)
        if hasattr(self.args, 'container_env'):
            self.args.container_env = self.format_container_env(
                self.args.container_env
            )

    def format_container_env(self, elements: List[str]) -> List[Tuple[str, str]]:
        retval = []
        for element in elements:
            if isinstance(element, str):
                key, value = element.split("=", 1)
                retval.append((key, value))
            if isinstance(element, (tuple, list)):
                retval.append(element)
        return retval

    @classmethod
    def _add_common_arguments(cls, parser: argparse.ArgumentParser) -> None:

        parser.add_argument(
            "docker_from",
            help="Specify the value which will be used for the FROM keyword when building the docker image. Example: 'ubuntu:bionic'",
        )
        parser.add_argument(
            '-s', '--snapshot',
            help="Build a snapshot version. "
                 "If this flag is set, a dummy entry is added to the debian changelog file, "
                 "and +xsnapshot+$date will be appended to the package version.",
            action='store_true',
        )
        parser.add_argument(
            '--shell',
            help="Launch a debug shell in the running docker container if build fails."
                 "(default: %(default)s)",
            action='store_true',
        )
        parser.add_argument(
            '--deb-build-options',
            help="This variable can contain several flags to change how a package is compiled and built. "
                 "Each flag must be in the form flag or flag=options. "
                 "If multiple flags are given, they must be separated by whitespace. "
                 "(default: %(default)s)",
            action='store', default=os.environ.get('DEB_BUILD_OPTIONS', None)
        )
        parser.add_argument(
            '--local-repo-dir',
            help="The directory for the local apt repository. The value will be: "
                 "1. This argument, if given. "
                 "2. $BLDR_LOCAL_REPO_DIR environment variable, if set. "
                 "3. 'local-apt-<image_tag>, in the cwd. Image tag will be normalized, all ':' and '/' will be replaced to '-'",
            action='store',
            type=Path,
        )
        parser.add_argument(
            '--nocache',
            help="Disable caching of docker image layers. "
                 "Useful to sanity-check that an error is not caused by cache layers. "
                 "A dedicated CI machine should use this option. "
                 "(default: %(default)s)",
            action='store_true'
        )
        parser.add_argument(
            "--container-env",
            help="Specify environment variables for the container in the form of key=value. Can be specified multiple times.",
            action="append",
            default=[],
        )
        parser.add_argument(
            "--hooks-dir",
            help="A path pointing to a directory containing the hooks",
            type=Path,
        )
        parser.add_argument(
            "--disable-tmpfs",
            help="Disable using tmpfs.",
            action="store_true",
        )

    def _create_config_loader(self) -> ConfigLoader:
        return JSONConfigLoader(get_config_file_paths())

    def _parse_arguments(self, argv: List) -> argparse.Namespace:
        config_loader = self._create_config_loader()
        parser = ArgumentParser(
            description=self.description,
            epilog=self._extra_help,
            formatter_class=argparse.RawTextHelpFormatter,
            config_loader=config_loader,
        )
        parser.add_argument(
            '-v', '--version',
            action='version', version='%(prog)s {version}'.format(version=get_version())
        )
        parser.add_argument(
            '--config',
            help='JSON File used to set command line parameter default values, in addition to the defaults written below.',
            metavar='PATH',
            type=Path,
        )

        subparsers = SubParsers(config_loader, parser.add_subparsers(metavar='command', help='description'))

        build_option_parser = subparsers.add_parser(
            'build',
            help="This command builds snapshot .deb files in a docker container."
                 "Call from any source dir that has a debian directory, from just outside the debian directory."
                 "Places compiled .deb files into the specified repository.",
        )
        build_option_parser.add_argument(
            'package',
            nargs='?', default=Path.cwd(),
            help="Source directory, which will be built. (default: %(default)s)",
            type=Path,
        )
        build_option_parser.set_defaults(action=lambda self, args: self.build(args.package))
        self._add_common_arguments(build_option_parser)

        reindex_option_parser = subparsers.add_parser(
            'reindex',
            help="This command reindexes a simple apt-repository (i.e. creates Packages and Sources files)."
                 "The working directory is arbitrary, if BLDR_LOCAL_REPO_DIR is set "
                 "or --local-repo-dir is specified via command line.",
        )
        reindex_option_parser.set_defaults(action=lambda self, args: self.reindex())
        self._add_common_arguments(reindex_option_parser)

        selftest_option_parser = subparsers.add_parser(
            'selftest',
            help="This command runs system configuration tests (e.g. is docker properly configured "
                 "and works for all supported Ubuntu releases).",
        )
        selftest_option_parser.set_defaults(action=lambda self, args: self.selftest())

        shell_option_parser = subparsers.add_parser(
            'shell',
            help="This command puts you in a docker shell, which already contains the build dependencies of your project"
                 "Call from any source dir that has a debian directory, from just outside the debian directory."
                 "It mounts your home directory into the docker container.",
        )
        shell_option_parser.add_argument(
            'package',
            nargs='?', default=Path.cwd(),
            help="Source directory, where the dependencies come from. (default: %(default)s)",
            type=Path,
        )
        shell_option_parser.set_defaults(action=lambda self, args: self.shell(args.package))
        self._add_common_arguments(shell_option_parser)

        ns, _ = parser.parse_known_args(argv[1:])
        if ns.config:
            try:
                config_loader.load_config_file(ns.config)
            except OSError:
                parser.error("Unable to open configuration file: '{}'".format(ns.config))
            except json.JSONDecodeError as err:
                parser.error("Unable to parse configuration file: '{}'".format(err))
            parser.config_loader.paths.append(ns.config)

        return parser.parse_args(argv[1:])

    @property
    def _extra_help(self) -> str:
        config_loader = self._create_config_loader()
        config_extra_help = dedent("""

            Configuration files:

              You can use configuration files to change the default settings.
              The format of the config file is JSON-formatted dictionary. The keys are the parameter names, but '-' characters are replaced with '_'.
              The order of looking up a parameter value is:
                - Command line argument
                - If --config is set, read from that file
                - Search in default config files (in order):
        """)
        for config_file_path in reversed(config_loader.paths):
            config_extra_help += "      {}\n".format(config_file_path)
        config_extra_help += "    - Default value"

        return EXTRA_HELP + config_extra_help

    def _find_local_repo_dir(self) -> Path:
        local_repo_dir = self.args.local_repo_dir

        if not local_repo_dir:
            local_repo_dir = os.environ.get("BLDR_LOCAL_REPO_DIR")
        if not local_repo_dir:
            local_repo_dir = Path().cwd().joinpath("local-apt-{}".format(escape_docker_image_tag(self.args.docker_from)))

        return local_repo_dir

    def _init_bldr(self) -> BLDR:
        bldr = BLDR(
            local_repo_dir=self._find_local_repo_dir(),
            source_dir=Path().cwd().parent,
            docker_from=self.args.docker_from,
            deb_build_options=self.args.deb_build_options,
            debug_shell=self.args.shell,
            snapshot=self.args.snapshot,
            nocache=self.args.nocache,
            container_env=dict(self.args.container_env),
            hooks_dir=self.args.hooks_dir,
            disable_tmpfs=self.args.disable_tmpfs,
        )
        return bldr

    def main(self) -> int:
        try:
            self.args.action(self, self.args)
        except BLDRError as bldr_err:
            self._logger.error(bldr_err.msg)
            return bldr_err.exitcode

        return 0

    def build(self, package_dir: Path) -> None:
        self._logger.debug("BLDR build with {}".format(package_dir))

        bldr = self._init_bldr()
        bldr.build(package_dir=package_dir)
        deb_path = bldr.local_repo_dir.joinpath(bldr.get_package_relative_dir(package_dir), 'debs')
        self._logger.debug("Your deb files are at {}".format(deb_path))

    def reindex(self) -> None:
        self._logger.debug("BLDR reindex")

        bldr = self._init_bldr()
        bldr.reindex()

    def selftest(self) -> None:
        self._logger.debug("BLDR selftest")

        BLDR.selftest()

        self._logger.debug("Selftest: PASSED")

    def shell(self, package_dir: Path) -> None:
        self._logger.debug("BLDR shell")

        bldr = self._init_bldr()
        bldr.shell(package_dir=package_dir)


def main(argv: List[str] = sys.argv) -> None:
    cli = CLI(argv=argv)
    sys.exit(cli.main())


if __name__ == '__main__':
    main()
