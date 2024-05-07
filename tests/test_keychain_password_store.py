"""Tests password-store keychain provider."""

import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap

import pytest


_is_macos = sys.platform == "darwin"


pytestmark = pytest.mark.skipif(
    not shutil.which("pass"),
    reason="password-store is not found",
)


if _is_macos:
    # Unfortunately, when 'gpg' is ran on macOS with GNUPGHOME set to a
    # temporary directory and generate-key template pointed to a file in
    # temporary directory too, it complains about using too long names.  It's
    # not clear why 'gpg' complains about too long names, but it's clear that
    # built-in 'tmp_path' fixture produces too long names. That's why on macOS we
    # override 'tmp_path' fixture to return much shorter path to a temporary
    # directory.
    @pytest.fixture()
    def tmp_path():
        with tempfile.TemporaryDirectory() as path:
            yield pathlib.Path(path)


@pytest.fixture()
def gpg_key_id(monkeypatch, tmp_path):
    """Return a Key ID of just generated GPG key."""

    gpghome = tmp_path.joinpath(".gnupg")
    gpgtemplate = tmp_path.joinpath("gpg-template")

    monkeypatch.setenv("GNUPGHOME", str(gpghome))
    gpgtemplate.write_text(
        textwrap.dedent(
            """
                %no-protection
                Key-Type: RSA
                Subkey-Type: RSA
                Name-Real: Test
                Name-Email: test@test
                Expire-Date: 0
                %commit
            """
        ),
        encoding="UTF-8",
    )

    subprocess.check_output(
        f"gpg --batch --generate-key {gpgtemplate}",
        shell=True,
        stderr=subprocess.STDOUT,
    )
    keys = subprocess.check_output(
        "gpg --list-secret-keys", shell=True, stderr=subprocess.STDOUT
    ).decode("UTF-8")

    key = re.search(r"\s+([0-9A-F]{40})\s+", keys)
    if not key:
        error_message = "cannot generate a GPG key"
        raise RuntimeError(error_message)
    return key.group(1)


@pytest.fixture(autouse=True)
def password_store_dir(monkeypatch, tmp_path):
    """Set password-store home directory to a temporary one."""

    passstore = tmp_path.joinpath(".password-store")
    monkeypatch.setenv("PASSWORD_STORE_DIR", str(passstore))
    return passstore


@pytest.fixture()
def testkeychain():
    """Keychain instance under test."""

    # For the same reasons as in tests/test_plugin.py, all imports that trigger
    # HTTPie importing must be postponed till one of our fixtures is evaluated
    # and patched a path to HTTPie configuration.
    from httpie_credential_store import _keychain

    return _keychain.PasswordStoreKeychain()


def test_secret_retrieved(testkeychain, gpg_key_id):
    """The keychain returns stored secret, no bullshit."""

    subprocess.run(["pass", "init", gpg_key_id], check=True)
    subprocess.run(["pass", "insert", "--echo", "service/user"], input=b"f00b@r", check=True)

    assert testkeychain.get(name="service/user") == "f00b@r"


def test_secret_not_found(testkeychain):
    """LookupError is raised when no secrets are found in the keychain."""

    with pytest.raises(LookupError) as excinfo:
        testkeychain.get(name="service/user")

    assert str(excinfo.value) == "password-store: no secret found: 'service/user'"
