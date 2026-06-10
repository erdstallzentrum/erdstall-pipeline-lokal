from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET
from PySide6.QtCore import  Signal
from erdstall_admin_gui.workers.cancelable_worker import CancelableWorker, CancellationToken
from erdstall_pipeline.config import XML_FILENAME, PLY_DIR, XML_NAMESPACE, XSI_NAMESPACE, XML_SCHEMA_LOCATION

class CreateXMLWorker(CancelableWorker):
    success = Signal(str)
    error = Signal(str)
    finished = Signal()

    def __init__(self,
                 mesh_id: str,
                 settings: dict[str, str],
                 cancel_token: CancellationToken | None = None) ->None:
        super().__init__()
        self.mesh_id = mesh_id
        self.settings = settings
        self.cancel_token = cancel_token

    def execute(self) -> None:
        output_path = Path(PLY_DIR) / self.mesh_id / XML_FILENAME
        output_path.parent.mkdir(parents=True, exist_ok=True)

        xml_tree = self._build_xml_tree()

        ET.indent(xml_tree, space="\t", level=0)

        xml_tree.write(
            output_path,
            encoding="utf-8",
            xml_declaration=True,
        )

        self.success.emit(f"XML created: {output_path}")

    def _build_xml_tree(self) -> ET.ElementTree:
        ET.register_namespace("", XML_NAMESPACE)
        ET.register_namespace("xsi", XSI_NAMESPACE)

        root = ET.Element(
            f"{{{XML_NAMESPACE}}}ErdstallMetaDaten",
            {
                f"{{{XSI_NAMESPACE}}}schemaLocation": (
                    f"{XML_SCHEMA_LOCATION}"
                ),
                "id": self.settings["id"],
            },
        )

        self._add_text(root, "Datenbankeintraege", self.settings["database_entries"])
        self._add_text(root, "Name", self.settings["name"])
        self._add_text(root, "Entdeckung", self.settings["discovery"])
        self._add_text(root, "Erst2Daten", self.settings["first_2d_data"])
        self._add_text(root, "Erst3DatenDatum", self.settings["first_3d_date"])
        self._add_text(root, "Erst3DatenPerson", self.settings["first_3d_person"])

        gps = ET.SubElement(root, "GPS")
        self._add_text(gps, "long",self.settings["longitude"])
        self._add_text(gps, "lat", self.settings["latitude"])

        ET.SubElement(
            root,
            "Type",
            {
                "kurz": self.settings["type_short"],
                "lang": self.settings["type_long"],
            },
        )

        self._add_text(root, "Beschreibung", self.settings["description"])
        dimensions = ET.SubElement(root, "Abmessung")
        self._add_text(dimensions, "Laenge", self.settings["length"])
        self._add_text(dimensions, "Tiefe", self.settings["depth"])
        self._add_text(dimensions, "Volumen", self.settings["volume"])


        traeger = ET.SubElement(root,
        "Traeger",

          {
              "link": self.settings["link"]
          }
        )

        traeger.text = self.settings["carrier"]

        return ET.ElementTree(root)


    def _add_text(self, parent: ET.Element, tag: str, value: str) -> ET.Element:
        element = ET.SubElement(parent, tag)
        element.text = value
        return element

    def _split_comma_list(self, value: str) -> list[str]:
        return [
            item.strip()
            for item in value.split(",")
            if item.strip()
        ]