"""Shared application infrastructure for cpau CLI tools.

Provides:

- ``CpauCredentials`` — typed container for the (userid, password) pair the
  CPAU and WaterSmart portals require.
- ``load_credentials()`` — reads credentials from a JSON file. Resolves the
  path from (in order): an explicit argument, the ``CPAU_SECRETS_FILE``
  environment variable, or ``~/.cpau/secrets.json``.
- ``CpauApp`` — intermediate ``BaseApp`` subclass for the cpau-* CLI tools.
  Adds a ``--secrets-file`` argument and loads credentials once during
  ``go()``, exposing them to subclasses as ``self.credentials``.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .baseapp import BaseApp

# The default location for the credentials file. The ~/.cpau/ directory is
# already used by the water-meter cookie cache, so credentials live there
# alongside it.
DEFAULT_SECRETS_PATH = Path.home() / ".cpau" / "secrets.json"

# Environment variable users can set to override the default path without
# having to pass --secrets-file on every invocation.
SECRETS_FILE_ENV_VAR = "CPAU_SECRETS_FILE"


@dataclass(frozen=True)
class CpauCredentials:
    """The userid/password pair used to log in to the CPAU portals."""

    userid: str
    password: str


class CredentialsError(Exception):
    """Raised when credentials cannot be loaded or are invalid."""


def resolve_secrets_path(explicit: Optional[str] = None) -> Path:
    """Determine which credentials file to read.

    Resolution order: explicit argument, then ``CPAU_SECRETS_FILE`` env var,
    then the default ``~/.cpau/secrets.json``.
    """
    if explicit:
        return Path(explicit).expanduser()
    env_value = os.environ.get(SECRETS_FILE_ENV_VAR)
    if env_value:
        return Path(env_value).expanduser()
    return DEFAULT_SECRETS_PATH


def load_credentials(secrets_file: Optional[str] = None) -> CpauCredentials:
    """Load CPAU credentials from a JSON file.

    The file must contain top-level ``userid`` and ``password`` string
    fields. Raises :class:`CredentialsError` with a human-readable message
    if the file is missing, malformed, or missing required fields.
    """
    path = resolve_secrets_path(secrets_file)

    if not path.exists():
        raise CredentialsError(
            f"Credentials file not found: {path}. "
            f"Create one with 'userid' and 'password' fields, or set "
            f"{SECRETS_FILE_ENV_VAR} or pass --secrets-file."
        )

    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise CredentialsError(f"Invalid JSON in credentials file {path}: {e}") from e
    except OSError as e:
        raise CredentialsError(f"Failed to read credentials file {path}: {e}") from e

    if not isinstance(data, dict):
        raise CredentialsError(
            f"Credentials file {path} must contain a JSON object, not {type(data).__name__}"
        )

    for field in ("userid", "password"):
        if field not in data:
            raise CredentialsError(
                f"Credentials file {path} is missing required field '{field}'"
            )
        if not isinstance(data[field], str) or not data[field]:
            raise CredentialsError(
                f"Credentials file {path}: field '{field}' must be a non-empty string"
            )

    return CpauCredentials(userid=data["userid"], password=data["password"])


class CpauApp(BaseApp):
    """Base class for cpau-* CLI tools.

    Adds a ``--secrets-file`` argument and loads credentials in ``go()``,
    making them available to subclasses as ``self.credentials``.

    Subclasses should override ``add_arg_definitions`` (calling
    ``super()`` first) to add their own arguments, and ``go()`` to do
    their own work after calling ``super().go(argv)``.
    """

    def add_arg_definitions(self, parser: argparse.ArgumentParser) -> None:
        super().add_arg_definitions(parser)
        parser.add_argument(
            "--secrets-file",
            type=str,
            default=None,
            help=(
                f"Path to JSON file with 'userid' and 'password' fields "
                f"(default: ${SECRETS_FILE_ENV_VAR} or {DEFAULT_SECRETS_PATH})"
            ),
        )

    def go(self, argv: list) -> int:
        super().go(argv)
        try:
            self.credentials = load_credentials(self.args.secrets_file)
        except CredentialsError as e:
            self.logger.error(str(e))
            return 1
        return 0
