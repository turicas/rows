import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from rows.utils import subclasses


@dataclass
class DownloadLink:
    url: str
    save_path: str


class Downloader:
    name = None

    def __init__(self, user_agent="Mozilla", continue_paused=True, timeout=10, max_tries=5):
        self.user_agent = user_agent
        self._commands = []
        self._directories = set()
        self._continue_paused = continue_paused
        self._timeout = timeout
        self._max_tries = max_tries

    @classmethod
    def subclasses(cls):
        return {class_.name: class_ for class_ in subclasses(cls)}

    def add(self, link):
        # TODO: what if I don't want to add save path (don't know remote
        # filename/extension)?
        download_filename = Path(link.save_path)
        self._directories.add(download_filename.parent)
        self._add_download(link.url, download_filename)

    def add_many(self, links):
        for link in links:
            self.add(link)

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
    name = "wget"

    def _add_download(self, url, filename):
        parameters = ["--user-agent", self.user_agent]
        if self._timeout is not None:
            parameters.extend(["-t", str(self._timeout)])
        if self._continue_paused:
            parameters.append("-c")
        if self._max_tries:
            parameters.extend(["-t", str(self._max_tries)])
        cmd = ["wget", "-O", str(filename), *parameters, url]
        if cmd not in self._commands:
            self._commands.append(cmd)


class Aria2cDownloader(Downloader):
    name = "aria2c"

    def __init__(self, max_concurrent_downloads=4, max_connections_per_download=4, split_download_parts=4, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._max_connections_per_download = max_connections_per_download
        self._max_concurrent_downloads = max_concurrent_downloads
        self._split_download_parts = split_download_parts

    def _build_parameters(self):
        parameters = ["--user-agent", self.user_agent]
        if self._timeout is not None:
            parameters.extend(["--connect-timeout", str(self._timeout)])
        if self._continue_paused:
            parameters.append("-c")
        if self._max_concurrent_downloads is not None:
            parameters.extend(["-j", str(self._max_concurrent_downloads)])
        if self._max_connections_per_download is not None:
            parameters.extend(["-x", str(self._max_connections_per_download)])
        if self._split_download_parts is not None:
            parameters.extend(["-s", str(self._split_download_parts)])
        if self._max_tries is not None:
            parameters.extend(["--max-tries", str(self._max_tries)])
        return parameters

    def _add_download(self, url, filename):
        cmd = [
            "aria2c",
            *self._build_parameters(),
            "--dir", str(filename.parent),
            url,
        ]
        if cmd not in self._commands:
            self._commands.append(cmd)


class Aria2cFileDownloader(Aria2cDownloader):
    name = "aria2c-file"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aria_files = []

    def _add_download(self, url, filename):
        data = (url, filename.parent)
        if data not in self._aria_files:
            self._aria_files.append(data)

    @property
    def commands(self):
        tmp = NamedTemporaryFile(delete=False, prefix="aria-download-", suffix=".txt")
        with open(tmp.name, mode="w") as output:
            for download_url, download_path in self._aria_files:
                output.write(f"{download_url}\n  dir={download_path}\n")
        self._temp_filename = Path(tmp.name)

        cmd = [
            "aria2c",
            *self._build_parameters(),
            "--dir", str(self._temp_filename.parent),
            "--input-file", tmp.name,
        ]
        return [cmd]

    def cleanup(self):
        self._temp_filename.unlink()


# TODO: implement checks for each class (if executable is available)
# TODO: implement curl downloader
# TODO: implement aria2p downloader
__all__ = [
    "Aria2cDownloader",
    "Aria2cFileDownloader",
    "DownloadLink",
    "Downloader",
    "WgetDownloader",
]

if __name__ == "__main__":
    import argparse


    # TODO: add parameters: continue_paused, connections etc.
    # TODO: add logging
    subclasses = Downloader.subclasses()
    parser = argparse.ArgumentParser()
    parser.add_argument("downloader", choices=list(subclasses.keys()))
    parser.add_argument("output_path")
    parser.add_argument("url", nargs="+")
    args = parser.parse_args()
    output_path = Path(args.output_path)

    links = [DownloadLink(url=url, save_path=output_path / Path(url).name) for url in args.url]
    downloader = subclasses[args.downloader]()
    downloader.add_many(links)
    downloader.run()
