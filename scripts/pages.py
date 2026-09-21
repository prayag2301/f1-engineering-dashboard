#!/usr/bin/env python3
"""Export reviewed public releases and prepare an independent GitHub Pages site.

Standard library only. Never reads .env, the database, or authenticated endpoints.
Large assets live in an immutable GitHub Release bundle, not in Git history.
"""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import ssl
import struct
import sys
import tarfile
import tempfile
from urllib.parse import quote, urlparse
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
DESCRIPTOR = ROOT / "data/pages/snapshot.json"
TEAMS = tuple(json.loads((ROOT / "modeling/catalog.json").read_text())["teams"])
VIEWS = ("front", "side", "rear", "three_quarter")
ASSETS = {"glb": "car.glb"} | {
    f"{kind}_{view}": f"{kind}_{view}.png"
    for kind in ("preview", "render")
    for view in VIEWS
}
# Leave room below Pages' 1 GB site limit for the application itself.
MAX_ARCHIVE_BYTES = 850 * 1024 * 1024
ASSET_PATTERN = re.compile(r"assets/[a-f0-9]{64}\.(glb|png)")
SOURCE_FIELDS = (
    "id",
    "url",
    "title",
    "publisher",
    "published_at",
    "retrieved_at",
    "source_type",
    "event_name",
    "image_urls",
    "rights",
)


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def open_url(url, timeout):
    context = ssl.create_default_context()
    # Python.org macOS installs can have an empty OpenSSL CA store until their
    # certificate installer is run. Use the OS trust bundle in that case, while
    # preserving explicit certificate overrides and full TLS verification.
    if (
        sys.platform == "darwin"
        and not os.environ.get("SSL_CERT_FILE")
        and not os.environ.get("SSL_CERT_DIR")
        and context.cert_store_stats()["x509_ca"] == 0
        and Path("/etc/ssl/cert.pem").is_file()
    ):
        context.load_verify_locations(cafile="/etc/ssl/cert.pem")
    return urlopen(url, timeout=timeout, context=context)


def download(url, destination, limit=MAX_ARCHIVE_BYTES):
    """No credentials or cookies, with bounded streaming and a timeout."""
    total = 0
    with open_url(url, timeout=60) as response, Path(destination).open("wb") as out:
        while chunk := response.read(1024 * 1024):
            total += len(chunk)
            if total > limit:
                raise ValueError("Download exceeds the archive size limit.")
            out.write(chunk)


def get_json(url):
    with open_url(url, timeout=30) as response:
        payload = response.read(10 * 1024 * 1024 + 1)
    if len(payload) > 10 * 1024 * 1024:
        raise ValueError("Archive metadata is too large.")
    return json.loads(payload)


def public_version(record):
    """An explicit schema prevents future private API fields leaking into a bundle."""
    if record.get("status") != "published" or not record.get("published_at"):
        raise ValueError(
            "Only published releases can be exported; complete visual review first."
        )
    fields = (
        "id",
        "team_key",
        "season",
        "label",
        "configuration_event",
        "configuration_kind",
        "reverts_to_id",
        "as_of",
        "evidence_cutoff",
        "status",
        "parent_id",
        "published_at",
        "is_current",
        "notes",
        "component_revisions",
    )
    value = {key: deepcopy(record.get(key)) for key in fields}
    review = record.get("visual_review", {})
    value["visual_review"] = {
        key: deepcopy(review.get(key))
        for key in (*VIEWS, "notes", "reference_urls", "reviewed_at")
    }
    manifest = record["manifest"]
    value["manifest"] = {
        key: deepcopy(manifest[key])
        for key in (
            "components",
            "component_hashes",
            "no_new_modeled_change",
            "reconstruction_notice",
        )
    }
    if "validation" in manifest:
        value["manifest"]["validation"] = deepcopy(manifest["validation"])
    value["manifest"]["sources"] = [
        {key: deepcopy(source.get(key)) for key in SOURCE_FIELDS}
        for source in manifest["sources"]
    ]
    change_fields = (
        "id",
        "source_id",
        "team_key",
        "season",
        "component",
        "event_name",
        "observed_at",
        "summary",
        "supporting_passage",
        "page",
        "evidence_status",
        "representation",
        "status",
        "review_notes",
    )
    value["manifest"]["changes"] = [
        {key: deepcopy(change.get(key)) for key in change_fields}
        for change in manifest["changes"]
    ]
    value["manifest"]["assets"] = {
        key: {
            field: manifest["assets"][key][field]
            for field in ("filename", "sha256", "bytes")
        }
        for key in ASSETS
    }
    return value


def validate(directory, require_baselines=False):
    directory = Path(directory)
    snapshot = read_json(directory / "index.json")
    teams = set(snapshot.get("catalog", {}).get("teams", {}))
    if (
        snapshot.get("schema_version") != 1
        or set(snapshot["versions"]) != teams
        or not teams
        or not teams <= set(TEAMS)
    ):
        raise ValueError("Unsupported archive schema or team set.")
    if not {"ferrari", "mercedes"} <= teams or snapshot["catalog"]["season"] != 2026:
        raise ValueError("Expected a supported 2026 constructor catalog.")
    expected = {"index.json"}
    checked = set()
    count = 0
    for team in sorted(teams):
        versions = snapshot["versions"][team]
        ids = {v["id"] for v in versions}
        if len(ids) != len(versions):
            raise ValueError("Duplicate release IDs.")
        if versions and sum(v["is_current"] is True for v in versions) != 1:
            raise ValueError(f"{team} must have exactly one current published release.")
        if require_baselines and not versions:
            raise ValueError(
                f"{team} has no reviewed release. The existing Pages deployment must stay live."
            )
        for version in versions:
            count += 1
            if version["team_key"] != team or version["season"] != 2026:
                raise ValueError("Release team/season mismatch.")
            if version["status"] != "published" or not version["published_at"]:
                raise ValueError("Unpublished release found in archive.")
            if version["parent_id"] and version["parent_id"] not in ids:
                raise ValueError("Release history is incomplete.")
            if version.get("reverts_to_id") and version["reverts_to_id"] not in ids:
                raise ValueError("Reversion target missing from archive.")
            review = version["visual_review"]
            if (
                not all(review.get(view) is True for view in VIEWS)
                or not review.get("reference_urls")
                or len(review.get("notes") or "") < 20
            ):
                raise ValueError(
                    "Release has not completed the four-view reference review."
                )
            assets = version["manifest"]["assets"]
            if set(assets) != set(ASSETS):
                raise ValueError(
                    "Expected the GLB, four previews, and four final renders only."
                )
            for key, asset in assets.items():
                relative = asset["url"]
                extension = ".glb" if key == "glb" else ".png"
                if (
                    not ASSET_PATTERN.fullmatch(relative)
                    or relative != f"assets/{asset['sha256']}{extension}"
                ):
                    raise ValueError("Unsafe or non-immutable asset path.")
                if asset["filename"] != ASSETS[key]:
                    raise ValueError("Unexpected asset filename.")
                path = directory / relative
                expected.add(relative)
                if (
                    not path.is_file()
                    or path.is_symlink()
                    or path.stat().st_size != asset["bytes"]
                ):
                    raise ValueError("Asset missing or byte count mismatch.")
                if relative not in checked and sha256(path) != asset["sha256"]:
                    raise ValueError("Asset checksum mismatch.")
                checked.add(relative)
                with path.open("rb") as stream:
                    header = stream.read(24)
                if key == "glb":
                    if len(header) < 12 or struct.unpack("<4sII", header[:12]) != (
                        b"glTF",
                        2,
                        asset["bytes"],
                    ):
                        raise ValueError("Invalid GLB export.")
                else:
                    dimensions = (
                        (1920, 1080) if key.startswith("preview_") else (3840, 2160)
                    )
                    if (
                        len(header) < 24
                        or header[:8] != b"\x89PNG\r\n\x1a\n"
                        or struct.unpack(">II", header[16:24]) != dimensions
                    ):
                        raise ValueError("Incorrect preview/final PNG dimensions.")
    files = list(directory.rglob("*"))
    if any(path.is_symlink() for path in files):
        raise ValueError("Archive cannot contain symbolic links.")
    actual = {
        path.relative_to(directory).as_posix() for path in files if path.is_file()
    }
    if actual != expected:
        raise ValueError("Unexpected files in the public archive.")
    size = sum(path.stat().st_size for path in files if path.is_file())
    if size > MAX_ARCHIVE_BYTES:
        raise ValueError("Archive exceeds 850 MiB; reduce assets before deployment.")
    return {"versions": count, "unique_assets": len(checked), "bytes": size}


def export(api, output):
    output = Path(output)
    if output.exists():
        raise ValueError("Export destination exists; choose a new snapshot filename.")
    parsed = urlparse(api)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "Use an HTTP(S) API origin without credentials, query, or fragment."
        )
    api = api.rstrip("/")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        directory = Path(temporary) / "archive"
        (directory / "assets").mkdir(parents=True)
        snapshot = {
            "schema_version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "catalog": get_json(api + "/api/v1/cars/catalog"),
            "versions": {},
        }
        for team in snapshot["catalog"]["teams"]:
            records = get_json(api + f"/api/v1/cars/{team}/versions?season=2026")
            snapshot["versions"][team] = []
            for record in records:
                version = public_version(record)
                for key, filename in ASSETS.items():
                    asset = version["manifest"]["assets"][key]
                    if not re.fullmatch(r"[a-f0-9]{64}", asset["sha256"]):
                        raise ValueError("Invalid asset checksum.")
                    asset["url"] = f"assets/{asset['sha256']}{Path(filename).suffix}"
                    destination = directory / asset["url"]
                    if not destination.exists():
                        # Reconstruct the documented public endpoint. Never follow manifest URLs to private services.
                        download(
                            api
                            + f"/api/v1/releases/{quote(version['id'], safe='')}/{filename}",
                            destination,
                        )
                snapshot["versions"][team].append(version)
        write_json(directory / "index.json", snapshot)
        summary = validate(directory, require_baselines=True)
        bundle = Path(temporary) / "bundle.tar.gz"
        with tarfile.open(bundle, "w:gz") as archive:
            for path in sorted(directory.rglob("*")):
                if path.is_file():
                    archive.add(
                        path,
                        arcname=path.relative_to(directory).as_posix(),
                        recursive=False,
                    )
        os.replace(bundle, output)
    return summary | {"bundle": str(output), "sha256": sha256(output)}


def unpack(bundle, directory):
    """Extract only regular, size-bounded archive files; no paths/links/devices."""
    directory = Path(directory)
    seen = set()
    size = 0
    with tarfile.open(bundle, "r:gz") as archive:
        for member in archive:
            if (
                not member.isfile()
                or member.name in seen
                or (
                    member.name != "index.json"
                    and not ASSET_PATTERN.fullmatch(member.name)
                )
            ):
                raise ValueError("Unsafe or duplicate archive entry.")
            size += member.size
            if size > MAX_ARCHIVE_BYTES:
                raise ValueError("Uncompressed archive exceeds the size limit.")
            seen.add(member.name)
            destination = directory / member.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as source, destination.open("wb") as out:
                shutil.copyfileobj(source, out)
    return validate(directory)


def prepare(bundle=None, repository="prayag2301/f1-engineering-dashboard"):
    target = ROOT / "frontend/public/archive"
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = read_json(DESCRIPTOR)
    with tempfile.TemporaryDirectory(dir=target.parent) as temporary:
        directory = Path(temporary) / "archive"
        directory.mkdir()
        if bundle:
            unpack(bundle, directory)
        elif descriptor["release"]:
            if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
                raise ValueError("Expected owner/repository.")
            if not re.fullmatch(r"pages-[A-Za-z0-9_.-]+", descriptor["release"]):
                raise ValueError(
                    "Snapshot tags must start with pages- and contain only letters, digits, periods, underscores or hyphens."
                )
            downloaded = Path(temporary) / "snapshot.tar.gz"
            download(
                f"https://github.com/{repository}/releases/download/{descriptor['release']}/pages-archive.tar.gz",
                downloaded,
            )
            if sha256(downloaded) != descriptor["sha256"]:
                raise ValueError("Snapshot bundle checksum mismatch.")
            unpack(downloaded, directory)
            validate(directory, require_baselines=True)
        else:
            catalog = read_json(ROOT / "modeling/catalog.json")
            write_json(
                directory / "index.json",
                {
                    "schema_version": 1,
                    "generated_at": None,
                    "catalog": {key: catalog[key] for key in ("teams", "components")}
                    | {"season": 2026},
                    "versions": {team: [] for team in TEAMS},
                },
            )
        summary = validate(directory)
        # Only the generated public archive is replaced, after all validation succeeds.
        if target.exists():
            shutil.rmtree(target)
        shutil.move(str(directory), target)
    return summary


def pin(bundle, release):
    if not re.fullmatch(r"pages-[A-Za-z0-9_.-]+", release):
        raise ValueError("Use a unique pages- prefixed release tag.")
    with tempfile.TemporaryDirectory() as temporary:
        unpack(bundle, temporary)
        summary = validate(temporary, require_baselines=True)
    write_json(
        DESCRIPTOR, {"schema_version": 1, "release": release, "sha256": sha256(bundle)}
    )
    return summary | {"release": release}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser(
        "export", help="Package all published history from the public local API"
    )
    command.add_argument("--api", default="http://127.0.0.1:3000")
    command.add_argument("--output", type=Path, required=True)
    command = commands.add_parser(
        "prepare", help="Populate frontend/public/archive for a static build"
    )
    command.add_argument("--bundle", type=Path)
    command.add_argument(
        "--repository",
        default=os.environ.get(
            "GITHUB_REPOSITORY", "prayag2301/f1-engineering-dashboard"
        ),
    )
    command = commands.add_parser(
        "pin", help="Validate a bundle and select its immutable GitHub Release tag"
    )
    command.add_argument("--bundle", type=Path, required=True)
    command.add_argument("--release", required=True)
    command = commands.add_parser("validate")
    command.add_argument("directory", type=Path)
    command.add_argument("--require-baselines", action="store_true")
    args = vars(parser.parse_args())
    command = args.pop("command")
    try:
        result = globals()[command](**args)
    except (ValueError, KeyError, OSError, tarfile.TarError) as error:
        parser.exit(1, f"Pages archive: {error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
