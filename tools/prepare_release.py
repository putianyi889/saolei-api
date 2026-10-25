"""Validate the version tag and create documentation/checksum release assets."""

import hashlib
import os
import re
import tomllib
import zipfile
from pathlib import Path


def main() -> None:
    version = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
    tag = os.environ["RELEASE_TAG"]
    if not re.fullmatch(r"v\d+\.\d+\.\d+", tag) or tag != f"v{version}":
        raise SystemExit("Release tag does not match pyproject.toml version")
    source = Path("src/saolei_api/__init__.py").read_text(encoding="utf-8")
    if f'__version__ = "{version}"' not in source:
        raise SystemExit("Package __version__ does not match pyproject.toml")
    dist = Path("dist")
    assets = [
        dist / f"saolei_api-{version}-py3-none-any.whl",
        dist / f"saolei_api-{version}.tar.gz",
    ]
    for asset in assets:
        if not asset.is_file():
            raise SystemExit(f"Missing release artifact: {asset.name}")
    docs = dist / f"saolei_api-{version}-docs.zip"
    with zipfile.ZipFile(docs, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in [Path("README.md"), Path("LICENSE"), *sorted(Path("docs").rglob("*"))]:
            if path.is_file():
                archive.write(path, path.as_posix())
    assets.append(docs)
    lines = [f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}" for path in assets]
    (dist / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Prepared {len(assets)} assets and SHA256SUMS for {tag}")


if __name__ == "__main__":
    main()
