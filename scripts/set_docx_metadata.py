#!/usr/bin/env python3

import argparse
import os
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as StandardElementTree

from defusedxml import ElementTree as ET


CORE_PROPERTIES = "docProps/core.xml"
DC = "http://purl.org/dc/elements/1.1/"
CP = (
    "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
)


def update_metadata(
    document: Path,
    *,
    title: str,
    creator: str,
    subject: str,
    description: str,
) -> None:
    with zipfile.ZipFile(document, "r") as source:
        core = ET.fromstring(source.read(CORE_PROPERTIES))
        values = {
            f"{{{DC}}}title": title,
            f"{{{DC}}}creator": creator,
            f"{{{DC}}}subject": subject,
            f"{{{DC}}}description": description,
            f"{{{CP}}}lastModifiedBy": creator,
        }
        for tag, value in values.items():
            element = core.find(tag)
            if element is None:
                element = StandardElementTree.SubElement(core, tag)
            element.text = value
        core_xml = StandardElementTree.tostring(
            core,
            encoding="utf-8",
            xml_declaration=True,
        )

        handle, temporary_name = tempfile.mkstemp(
            prefix=f".{document.name}.",
            suffix=".tmp",
            dir=document.parent,
        )
        os.close(handle)
        temporary = Path(temporary_name)
        try:
            with zipfile.ZipFile(
                temporary,
                "w",
                compression=zipfile.ZIP_DEFLATED,
            ) as target:
                for item in source.infolist():
                    payload = (
                        core_xml
                        if item.filename == CORE_PROPERTIES
                        else source.read(item.filename)
                    )
                    target.writestr(item, payload)
            os.replace(temporary, document)
        finally:
            temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Set publication metadata in an existing DOCX file."
    )
    parser.add_argument("document", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--creator", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--description", required=True)
    arguments = parser.parse_args()
    update_metadata(
        arguments.document.resolve(),
        title=arguments.title,
        creator=arguments.creator,
        subject=arguments.subject,
        description=arguments.description,
    )


if __name__ == "__main__":
    main()
