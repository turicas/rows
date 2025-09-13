# coding: utf-8

# Copyright 2014-2025 Álvaro Justen <https://github.com/turicas/rows/>
#    This program is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General
#    Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option)
#    any later version.
#    This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
#    warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for
#    more details.
#    You should have received a copy of the GNU Lesser General Public License along with this program.  If not, see
#    <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import re
import subprocess
import warnings
from pathlib import Path
from tempfile import NamedTemporaryFile

from rows.compat import PYTHON_VERSION, TEXT_TYPE
from rows.utils import subclasses
from rows.version import as_string as rows_version

REGEXP_VERSION = re.compile("([0-9][a-z0-9.+-]+)")

if PYTHON_VERSION < (3, 0, 0):
    NotFoundError = OSError
else:
    NotFoundError = FileNotFoundError


class Download(object):
    def __init__(self, url, filename=None):
        self.url = url  # str
        self.filename = filename  # Path
        if self.filename is not None and not isinstance(self.filename, Path):
            self.filename = Path(self.filename)


class Downloader(object):
    name = None
    version_command = None

    def __init__(
        self, path=None, user_agent=None, continue_paused=True, timeout=10,
        max_tries=5, quiet=False, disable_ipv6=False, check_certificate=True,
    ):
        # TODO: implement proxy support
        self.path = path
        if self.path is not None and not isinstance(self.path, Path):
            self.path = Path(self.path)
        self._check_certificate = check_certificate
        self._commands = []
        self._continue_paused = continue_paused
        self._directories = set()
        self._disable_ipv6 = disable_ipv6
        self._max_tries = max_tries
        self._quiet = quiet
        self._timeout = timeout
        self._urls = set()
        self._user_agent = user_agent

        if type(self).get_version() is None:
            raise NotFoundError(
                "Command not found: {}".format(self.version_command[0])
            )

    @property
    def user_agent(self):
        if self._user_agent is None:
            # TODO: implement
            self._user_agent = "python/rows-{} ({} {})".format(
                rows_version, self.name, type(self).get_version()
            )
        return self._user_agent

    @classmethod
    def subclasses(cls, available_only=False):
        all_classes = {class_.name: class_ for class_ in subclasses(cls)}
        if available_only:
            all_classes = {
                name: class_
                for name, class_ in all_classes.items()
                if class_.get_version() is not None
            }
        return all_classes

    @classmethod
    def get_version(cls):
        if not hasattr(cls, "_version"):
            try:
                process = subprocess.Popen(
                    cls.version_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                stdout, stderr = process.communicate()
                result = REGEXP_VERSION.findall(stdout.splitlines()[0])
            except NotFoundError:
                cls._version = None
            else:
                cls._version = result[0]
        return cls._version

    def _get_path_and_filename(self, download):
        current_directory = Path.cwd()
        save_path = (
            (current_directory / self.path)
            if self.path is not None
            else current_directory
        )

        if download.filename is None:
            filename = None
        else:
            filename = download.filename
            if self.path is not None and filename.is_absolute():
                warnings.warn(
                    "filename {} cannot be absolute when downloader path is set (will be saved in downloader root path)".format(repr(TEXT_TYPE(filename)))
                    , RuntimeWarning
                )
                filename = filename.name
            full_filename = save_path / filename
            save_path = full_filename.parent
            filename = full_filename.name

        return save_path, filename

    def add(self, download):
        url = download.url
        if url in self._urls:
            return
        path, filename = self._get_path_and_filename(download)
        self._directories.add(path)
        self._add_download(url, path, filename)
        self._urls.add(url)

    def add_many(self, downloads):
        for download in downloads:
            self.add(download)

    @property
    def commands(self):
        return self._commands

    @property
    def directories(self):
        return self._directories

    def _add_download(self, url, filename):
        raise NotImplementedError()

    def run(self):
        for path in self.directories:
            if not path.exists():
                path.mkdir(parents=True)
        for command in self.commands:
            subprocess.call(command)
        self.cleanup()

    def cleanup(self):
        pass


class WgetDownloader(Downloader):
    """Use `wget` command to download files

    Each download URL will be executed as a new command, since wget's
    `--input-file` allows to specify many URLs but only one filename (`-O`).
    """

    name = "wget"
    version_command = ("wget", "--version")

    # TODO: add parameter so the user can specify custom command-line arguments

    def _add_download(self, url, path, filename=None):
        # TODO: use --restrict-file-names ?
        cmd = [
            "wget",
            "--user-agent",
            self.user_agent,
            "--trust-server-names",  # When a redirect occurs, set filename based on last URL, not first
            "--content-disposition",  # Use filename if available in Content-Disposition
        ]
        if not self._check_certificate:
            cmd.append("--no-check-certificate")
        if self._quiet:
            cmd.append("--quiet")
        if self._disable_ipv6:
            cmd.append("--inet4-only")
        if self._timeout is not None:
            cmd.extend(["--timeout", TEXT_TYPE(self._timeout)])
        if self._continue_paused:  # -c
            cmd.append("--continue")
        if self._max_tries:  # -t
            cmd.extend(["--tries", TEXT_TYPE(self._max_tries)])
        if filename is not None:  # -O
            cmd.extend(["--output-document", TEXT_TYPE(path / filename)])
        else:
            cmd.extend(["--directory-prefix", TEXT_TYPE(path)])
        cmd.append(url)
        self._commands.append(cmd)


class Aria2cDownloader(Downloader):
    """Use `aria2c` command to download files"""

    name = "aria2c"
    version_command = ("aria2c", "--version")

    def __init__(
        self,
        method="file",
        max_concurrent_downloads=4,
        max_connections_per_download=4,
        split_download_parts=4,
        *args,
        **kwargs
    ):
        """
        method can be:
        - 'file' (default): use `--input-file` and run only one command
        - 'commands': run one command for each URL
        """
        # TODO: add parameter so the user can specify custom command-line
        # arguments
        super().__init__(*args, **kwargs)
        assert method in ("file", "commands")
        self.method = method
        self._max_connections_per_download = max_connections_per_download
        self._max_concurrent_downloads = max_concurrent_downloads
        self._split_download_parts = split_download_parts
        self._aria2c_downloads = []

    def _build_parameters(self):
        parameters = ["--user-agent", self.user_agent]
        if not self._check_certificate:
            parameters.append("--check-certificate=false")
        if self._quiet:
            parameters.append("--quiet")
        if self._disable_ipv6:
            parameters.append("--disable-ipv6")
        if self._timeout is not None:
            parameters.extend(["--connect-timeout", TEXT_TYPE(self._timeout)])
        if self._continue_paused:  # -c
            parameters.append("--continue")
        if self._max_concurrent_downloads is not None:  # -j
            parameters.extend(
                ["--max-concurrent-downloads", TEXT_TYPE(self._max_concurrent_downloads)]
            )
        if self._max_connections_per_download is not None:  # -x
            parameters.extend(
                ["--max-connection-per-server", TEXT_TYPE(self._max_connections_per_download)]
            )
        if self._split_download_parts is not None:  # -s
            parameters.extend(["--split", TEXT_TYPE(self._split_download_parts)])
        if self._max_tries is not None:
            parameters.extend(["--max-tries", TEXT_TYPE(self._max_tries)])
        return parameters

    def _add_download(self, url, path, filename=None):
        if self.method == "file":
            self._aria2c_downloads.append((url, path, filename))

        elif self.method == "commands":
            cmd = ["aria2c"]
            cmd.extend(self._build_parameters())
            cmd.extend(["--dir", TEXT_TYPE(path)])
            if filename is not None:
                cmd.extend(["--out", filename])
            cmd.append(url)
            self._commands.append(cmd)

    @property
    def commands(self):
        if self.method == "file":
            tmp = NamedTemporaryFile(
                delete=False, prefix="aria2c-download-", suffix=".txt"
            )
            with open(tmp.name, mode="w", encoding="utf-8") as output:
                for url, path, filename in self._aria2c_downloads:
                    data = "{}\n".format(url) + "  dir={}\n".format(TEXT_TYPE(path))
                    if filename is not None:
                        # TODO: path not working when filename =
                        # dir1/dir2/filename (instead of only filename)?
                        data += "  out={}\n".format(filename)
                    output.write("{}\n".format(data))
            self._temp_filename = Path(tmp.name)

            cmd = ["aria2c"]
            cmd.extend(self._build_parameters())
            cmd.extend(["--input-file", tmp.name])
            return [cmd]

        elif self.method == "commands":
            return super().commands

    def cleanup(self):
        if self.method == "file":
            self._temp_filename.unlink()


# TODO: implement requests downloader
# TODO: implement curl downloader
# curl --create-dirs --output-dir tmp/curl/ --remote-name URL
# curl --create-dirs --output-dir tmp/curl/ --output some-filename.ext URL

# TODO: implement aria2p downloader


__all__ = [
    "Aria2cDownloader",
    "Download",
    "Downloader",
    "WgetDownloader",
]

if __name__ == "__main__":
    import argparse

    # TODO: add parameters: continue_paused, connections etc.
    # TODO: add logging
    subclasses = Downloader.subclasses(available_only=True)
    parser = argparse.ArgumentParser()
    parser.add_argument("downloader", choices=list(subclasses.keys()))
    parser.add_argument("output_path")
    parser.add_argument("url", nargs="+")
    args = parser.parse_args()
    output_path = Path(args.output_path)

    links = [Download(url=url) for url in args.url]
    downloader = subclasses[args.downloader](path=args.output_path)
    downloader.add_many(links)
    downloader.run()
