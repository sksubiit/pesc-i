"""Install the verified official Stockfish 19 binary in this checkout (Linux x86-64)."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
URL = (
    "https://github.com/official-stockfish/Stockfish/releases/download/sf_19/"
    "stockfish-linux-x86-64-universal.tar.gz"
)
ARCHIVE_SHA256 = "9defc0d4e55d49c65a6d042f3e571a39fcea499ade6dbe741b53b8c65e03611f"
BINARY_SHA256 = "0f83d24cc46d2c66c60f16001af5444873bc112b7d028594513426894c12da19"
MEMBER = "stockfish/stockfish-linux-x86-64-universal"
BINARY_SIZE = 103153472


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def provenance():
    return {
        "version": "19",
        "platform": "linux-x86-64-universal",
        "release": "https://github.com/official-stockfish/Stockfish/releases/tag/sf_19",
        "archive_url": URL,
        "archive_sha256": ARCHIVE_SHA256,
        "executable_sha256": BINARY_SHA256,
        "source_url": "https://github.com/official-stockfish/Stockfish/tree/sf_19",
        "license": "GPL-3.0",
    }


def install_archive(archive_path, destination):
    """Never replace a working executable until both checksums and UCI validation pass."""
    if sha256(archive_path) != ARCHIVE_SHA256:
        raise ValueError("Archive SHA-256 mismatch; the existing executable was not changed.")
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / "stockfish"
    if target.is_symlink():
        raise ValueError("Refusing to replace a symlinked executable.")
    staged = None
    try:
        with tarfile.open(archive_path, "r:gz") as archive:
            member = archive.getmember(MEMBER)
            if not member.isfile() or member.size != BINARY_SIZE:
                raise ValueError("Unexpected binary in the verified archive.")
            # Read named regular files; never extract archive paths into the filesystem.
            notices = {}
            for source, output in (
                ("stockfish/Copying.txt", "COPYING.txt"),
                ("stockfish/AUTHORS", "AUTHORS"),
            ):
                entry = archive.getmember(source)
                if not entry.isfile():
                    raise ValueError("Invalid release notice.")
                notices[output] = archive.extractfile(entry).read()
            with tempfile.NamedTemporaryFile(
                prefix=".stockfish19-", dir=destination, delete=False
            ) as output:
                staged = Path(output.name)
                with archive.extractfile(member) as source:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
                output.flush()
                os.fsync(output.fileno())
        if sha256(staged) != BINARY_SHA256:
            raise ValueError(
                "Executable SHA-256 mismatch; the existing executable was not changed."
            )
        staged.chmod(0o755)
        check = subprocess.run(
            [str(staged)],
            input="uci\nisready\nquit\n",
            text=True,
            capture_output=True,
            timeout=15,
            check=True,
        )
        if "id name Stockfish 19" not in check.stdout or "readyok" not in check.stdout:
            raise ValueError("The downloaded engine failed UCI startup validation.")
        os.replace(staged, target)
        staged = None
        for name, content in notices.items():
            (destination / name).write_bytes(content)
        (destination / "RELEASE.json").write_text(json.dumps(provenance(), indent=2) + "\n")
        return target
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive", type=Path, help="Use a local archive; its checksum is still verified."
    )
    args = parser.parse_args()
    if sys.platform != "linux" or platform.machine().lower() not in ("x86_64", "amd64"):
        parser.error(
            "This installer supports Linux/WSL x86-64. Use STOCKFISH_PATH for another platform."
        )
    destination = ROOT / "stockfish"
    if destination.is_symlink():
        parser.error("Refusing to install into a symlinked stockfish directory.")
    target = destination / "stockfish"
    if (
        target.is_file()
        and not target.is_symlink()
        and sha256(target) == BINARY_SHA256
        and all(
            (destination / name).is_file() for name in ("AUTHORS", "COPYING.txt", "RELEASE.json")
        )
    ):
        target.chmod(0o755)
        print(f"Stockfish 19 already verified: {target}")
        return
    try:
        if args.archive:
            result = install_archive(args.archive, destination)
        else:
            with tempfile.TemporaryDirectory(prefix="pesc-i-stockfish19-") as temporary:
                archive_path = Path(temporary) / "release.tar.gz"
                print("Downloading the official Stockfish 19 Linux x86-64 release…", flush=True)
                request = Request(URL, headers={"User-Agent": "pesc-i-installer"})
                with urlopen(request, timeout=120) as source, archive_path.open("wb") as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
                result = install_archive(archive_path, destination)
        print(f"Installed and verified Stockfish 19: {result}")
    except (OSError, ValueError, KeyError, tarfile.TarError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"Stockfish installation failed: {exc}\n")


if __name__ == "__main__":
    main()
