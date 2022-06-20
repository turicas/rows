import re
import subprocess
import warnings
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from rows import __version__
from rows.utils import subclasses

REGEXP_VERSION = re.compile("([0-9][a-z0-9.+-]+)")


@dataclass
class Download:
    url: str
    filename: Path = None

    def __post_init__(self):
        if self.filename is not None and not isinstance(self.filename, Path):
            self.filename = Path(self.filename)


class Downloader:
    name = None
    version_command = None

    def __init__(
        self, path=None, user_agent=None, continue_paused=True, timeout=10, max_tries=5
    ):
        self.path = path
        if self.path is not None and not isinstance(self.path, Path):
            self.path = Path(self.path)
        self._user_agent = user_agent
        self._commands = []
        self._directories = set()
        self._continue_paused = continue_paused
        self._timeout = timeout
        self._max_tries = max_tries
        self._urls = set()

        if type(self).get_version() is None:
            raise FileNotFoundError(
                "Command not found: {}".format(self.version_command[0])
            )

    @property
    def user_agent(self):
        if self._user_agent is None:
            # TODO: implement
            self._user_agent = "python/rows-{} ({} {})".format(
                __version__, self.name, type(self).get_version()
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
            except FileNotFoundError:
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
            if filename.is_absolute():
                warnings.warn(
                    f"filename {repr(filename)} cannot be absolute", RuntimeWarning
                )
                filename = Path(*filename.parts[1:])
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
        if self._timeout is not None:
            cmd.extend(["--timeout", str(self._timeout)])
        if self._continue_paused:  # -c
            cmd.append("--continue")
        if self._max_tries:  # -t
            cmd.extend(["--tries", str(self._max_tries)])
        if filename is not None:  # -O
            cmd.extend(["--output-document", str(path / filename)])
        else:
            cmd.extend(["--directory-prefix", str(path)])
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
        **kwargs,
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
        if self._timeout is not None:
            parameters.extend(["--connect-timeout", str(self._timeout)])
        if self._continue_paused:  # -c
            parameters.append("--continue")
        if self._max_concurrent_downloads is not None:  # -j
            parameters.extend(
                ["--max-concurrent-downloads", str(self._max_concurrent_downloads)]
            )
        if self._max_connections_per_download is not None:  # -x
            parameters.extend(
                ["--max-connection-per-server", str(self._max_connections_per_download)]
            )
        if self._split_download_parts is not None:  # -s
            parameters.extend(["--split", str(self._split_download_parts)])
        if self._max_tries is not None:
            parameters.extend(["--max-tries", str(self._max_tries)])
        return parameters

    def _add_download(self, url, path, filename=None):
        if self.method == "file":
            self._aria2c_downloads.append((url, path, filename))

        elif self.method == "commands":
            cmd = [
                "aria2c",
                *self._build_parameters(),
                "--dir",
                str(path),
            ]
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
            with open(tmp.name, mode="w") as output:
                for url, path, filename in self._aria2c_downloads:
                    data = f"{url}\n" f"  dir={str(path)}\n"
                    if filename is not None:
                        data += f"  out={filename}\n"
                    output.write(f"{data}\n")
            self._temp_filename = Path(tmp.name)

            cmd = [
                "aria2c",
                *self._build_parameters(),
                "--input-file",
                tmp.name,
            ]
            return [cmd]

        elif self.method == "commands":
            return super().commands

    def cleanup(self):
        if self.method == "file":
            self._temp_filename.unlink()


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
