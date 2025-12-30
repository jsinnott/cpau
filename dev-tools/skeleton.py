#!/usr/bin/env python

from datetime import datetime, timedelta
from logging import Logger, WARN
import os
import time
from typing import Optional
from argparse import ArgumentParser
import sys

from baseapp import BaseApp
import pprint

class BaseAppSubclassSkeleton(BaseApp):

    def add_arg_definitions(self, parser: ArgumentParser) -> None:
        super().add_arg_definitions(parser)
        
# ------------------------------------------------------------------------------

    def go(self, argv: list) -> int:
        super().go(argv)

        return 0

# ------------------------------------------------------------------------------
if __name__ == '__main__':
    app = BaseAppSubclassSkeleton()
    sys.exit(app.go(sys.argv[1:]))
