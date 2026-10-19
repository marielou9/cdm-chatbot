"""Download the CDM files the Banking scope needs, keeping the original folder structure."""

import json
import posixpath
import urllib.request
from pathlib import Path

# source repo at a fixed commit, and target folder
BASE_URL = "https://raw.githubusercontent.com/microsoft/CDM/dd21d715e05ebf740a11356c80b5c3b4c38a89c2/schemaDocuments"
TARGET = Path(__file__).parent.parent / "data" / "cdm"
START_MANIFEST = "/manifests/bankingAccelerator.manifest.cdm.json"

# downloaded files, by CDM path
downloaded: dict[str, bytes] = {}


def fetch(path: str) -> dict:
    """Download a CDM file once and return its JSON content."""

    if path not in downloaded:
        downloaded[path] = urllib.request.urlopen(BASE_URL + path).read()

    return json.loads(downloaded[path])


def follow_entity(path: str, name: str) -> None:
    """Download an entity file and every parent along its extendsEntity chain."""

    # find the entity
    definition = next(d for d in fetch(path)["definitions"] if d.get("entityName") == name)
    parent = definition.get("extendsEntity", "")

    # follow the parent through the folder's monikers
    if isinstance(parent, str) and "/" in parent:
        moniker, parent_name = parent.split("/")
        folder = posixpath.dirname(path)
        imports = fetch(folder + "/_allImports.cdm.json")["imports"]
        parent_path = next(i["corpusPath"] for i in imports if i.get("moniker") == moniker)
        follow_entity(parent_path, parent_name)


def follow_manifest(path: str) -> None:
    """Download a manifest, its entities and its nested manifests."""

    manifest = fetch(path)
    folder = posixpath.dirname(path)

    # every listed entity
    for entry in manifest.get("entities", []):
        file_name, entity_name = entry["entityPath"].rsplit("/", 1)
        follow_entity(file_name if file_name.startswith("/") else folder + "/" + file_name, entity_name)

    # nested manifests
    for sub_manifest in manifest.get("subManifests", []):
        follow_manifest(sub_manifest["definition"])


def main():
    """Download the Banking scope and write the files below data/cdm."""

    follow_manifest(START_MANIFEST)

    # write unchanged, same paths as in the CDM repo
    for path, content in downloaded.items():
        target = TARGET / path.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    print(f"{len(downloaded)} files written to {TARGET}")


if __name__ == "__main__":
    main()
