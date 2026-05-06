# This file is vendored from jsinnott_utils v1.3.0.
# Do NOT edit it here — run tools/sync_baseapp.sh to refresh.
#
# Source: /Users/jsinnott/code/python-utils/src/jsinnott_utils/baseapp.py

from abc import ABC, abstractmethod
import argparse
from argparse import ArgumentParser, Namespace
from importlib.metadata import version, PackageNotFoundError
import json
import logging
from math import e
import os
import sys
from typing import Optional

import coloredlogs


class BaseApp(ABC):

    def get_version(self) -> str:
        """Get version of the package containing the subclass."""
        module_name = self.__class__.__module__

        # When running as __main__, get the actual module name from __spec__
        if module_name == '__main__':
            main_module = sys.modules.get('__main__')
            if main_module and hasattr(main_module, '__spec__') and main_module.__spec__:
                module_name = main_module.__spec__.name

        package = module_name.split('.')[0]
        try:
            return version(package)
        except PackageNotFoundError:
            return "unknown"

    @classmethod
    def build_parser(cls):
        """Build and return the ArgumentParser without running the app.

        Creates an instance of the class, constructs an ArgumentParser
        (using DESCRIPTION and EPILOG class attributes if defined), and
        populates it via add_arg_definitions. Useful for man page generation
        with tools like argparse-manpage.
        """
        instance = cls()
        parser = argparse.ArgumentParser(
            description=getattr(cls, 'DESCRIPTION', None),
            epilog=getattr(cls, 'EPILOG', None),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        instance.add_arg_definitions(parser)
        return parser

    def parse_args(self, argv: list) -> Namespace:
        parser = argparse.ArgumentParser()
        self.add_arg_definitions(parser)
        return parser.parse_args(argv)

    def add_arg_definitions(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument('--version',
                            action='version',
                            version=f'%(prog)s {self.get_version()}')
        group = parser.add_mutually_exclusive_group(required=False)
        group.add_argument("-s",
                            "--silent",
                            action = "store_true",
                            dest = "silent",
                            required = False,
                            help = "supress non-error logging")
        group.add_argument("-v",
                            "--verbose",
                            action = "store_true",
                            dest = "verbose",
                            required = False,
                            help = "log debug-level processing information")

    def add_arg_definitions_prompting(self, parser: argparse.ArgumentParser, prompting_default: bool = True) -> None:
        group = parser.add_mutually_exclusive_group(required=False)
        group.add_argument("--prompt",
                            action = "store_true",
                            dest = "prompt",
                            required = False,
                            help = "prompt for confirmation before proceeding")
        group.add_argument("--no-prompt",
                            action = "store_false",
                            dest = "prompt",
                            required = False,
                            help = "do not prompt for confirmation before proceeding")
        group.set_defaults(prompt=prompting_default)

    def confirmed_with_prompt(self, prompt: str, default_is_confirm: bool, confirm_label: str = "confirm", deny_label: str = "deny") -> bool:
        confirm_label = confirm_label.upper() if default_is_confirm else confirm_label.lower()
        deny_label = deny_label.upper() if not default_is_confirm else deny_label.lower()
        default_label = confirm_label if default_is_confirm else deny_label
        prompt_msg = f"{prompt} ({confirm_label}/{deny_label}): "

        def is_unique_prefix(response: str, target: str, other: str) -> bool:
            return target.startswith(response) and not other.startswith(response)

        confirm_lower = confirm_label.lower()
        deny_lower = deny_label.lower()

        try:
            # Always read from /dev/tty to avoid issues with stdin being closed or redirected (as in a pipe being used to read data)
            with open('/dev/tty') as prompt_stream:
                while True:
                    print(prompt_msg, end='', flush=True)
                    response = prompt_stream.readline().strip().lower()

                    if not response:
                        return default_is_confirm

                    if is_unique_prefix(response, confirm_lower, deny_lower):
                        return True
                    if is_unique_prefix(response, deny_lower, confirm_lower):
                        return False

                    print(f"Invalid response: '{response}'. Expected a unique abbreviation of '{confirm_label}' or '{deny_label}'.")
        except Exception as e:
            self.logger.error(f"Error reading user input: {e}")
            return default_is_confirm

    def create_logger(self, logger_name: Optional[str]) -> logging.Logger:
        coloredlogs.install(milliseconds=True, level='WARNING', logger=logging.getLogger())
        logger = logging.getLogger(logger_name or os.path.basename(__file__))
        if self.args.verbose:
            coloredlogs.set_level(logging.DEBUG)
            logger.debug("debug logging enabled")
        elif self.args.silent:
            coloredlogs.set_level(logging.ERROR)
        else:
            coloredlogs.set_level(logging.INFO)
        return logger

    def print_args(self) -> None:
        self.logger.info("argument and option values:")
        for k,v in sorted(vars(self.args).items()):
            self.logger.info("...{0}: {1}".format(k,v))

    def configuration_is_valid_for_required_items(self, config: dict, required_items: dict) -> bool:
        for key, expected_type in required_items.items():
            if key not in config:
                self.logger.error(f"Missing required config key {key}")
                return False
            if not isinstance(config[key], expected_type):
                self.logger.error(f"Incorrect value type associated with config key {key}. Required type is {type(expected_type)}, found type is {type(config[key])}")
                return False
        return True

    def get_configuration(self, fn: str='config.json') -> dict:
        with open(fn) as f:
            return json.load(f)

    def deep_get(self, o, path: str, separator="."):
        for attribute in path.split(separator):
            if o is None:
                return None
            o = getattr(o, attribute, None)
        return o

    @abstractmethod
    def go(self, argv: list) -> int:
        self.args = self.parse_args(argv)
        self.logger = self.create_logger(type(self).__name__)
        self.print_args()
        return 0

