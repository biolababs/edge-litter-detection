#!/usr/bin/env python3

import argparse
import os
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as StandardElementTree

from defusedxml import ElementTree as ET


CORE_PROPERTIES = "docProps/core.xml"
DOCUMENT_XML = "word/document.xml"
DC = "http://purl.org/dc/elements/1.1/"
CP = (
    "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
)
TITLE_NOTICE_MARKER = (
    b"All output is AI-generated and must be independently verified before "
    b"sharing with customers or taking action."
)


def remove_generated_title_notice(document_xml: bytes) -> bytes:
    marker_index = document_xml.find(TITLE_NOTICE_MARKER)
    if marker_index < 0:
        raise ValueError("Generated title-page notice was not found")

    paragraph_start = document_xml.rfind(b"<w:p>", 0, marker_index)
    paragraph_end = document_xml.find(b"</w:p>", marker_index)
    if paragraph_start < 0 or paragraph_end < 0:
        raise ValueError("Generated title-page notice paragraph is malformed")

    paragraph_end += len(b"</w:p>")
    paragraph = document_xml[paragraph_start:paragraph_end]
    if b"AI &amp; Data Notice" not in paragraph:
        raise ValueError("First verification notice is not the title-page notice")
    return document_xml[:paragraph_start] + document_xml[paragraph_end:]


def update_metadata(
    document: Path,
    *,
    title: str,
    creator: str,
    subject: str,
    description: str,
    remove_title_notice: bool,
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
                    if item.filename == CORE_PROPERTIES:
                        payload = core_xml
                    else:
                        payload = source.read(item.filename)
                        if (
                            remove_title_notice
                            and item.filename == DOCUMENT_XML
                        ):
                            payload = remove_generated_title_notice(payload)
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
    parser.add_argument(
        "--remove-title-notice",
        action="store_true",
        help=(
            "Remove the report generator's title-page notice when the same "
            "required notice is included in the manuscript declarations."
        ),
    )
    arguments = parser.parse_args()
    update_metadata(
        arguments.document.resolve(),
        title=arguments.title,
        creator=arguments.creator,
        subject=arguments.subject,
        description=arguments.description,
        remove_title_notice=arguments.remove_title_notice,
    )


if __name__ == "__main__":
    main()
