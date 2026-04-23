import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
STEP_04_PATH = ROOT / "pipeline/phases/phase_01_build_world--Lucas_Starkey/steps/step_04_build_graph.py"


def load_step_04_module():
    package_name = "phase1_step4_testpkg"
    module_name = f"{package_name}.step_04_build_graph"

    if module_name in sys.modules:
        return sys.modules[module_name]

    package_module = types.ModuleType(package_name)
    package_module.__path__ = [str(STEP_04_PATH.parent)]
    sys.modules[package_name] = package_module

    people_module = types.ModuleType(f"{package_name}.step_03_resolve_people")

    class People:
        def __init__(self):
            self.identityMap = {}

    people_module.People = People
    sys.modules[people_module.__name__] = people_module

    wap_module = types.ModuleType(f"{package_name}.step_02_build_wap_index")

    class WAPIndex:
        def __init__(self):
            self.index = {}

    wap_module.WAPIndex = WAPIndex
    sys.modules[wap_module.__name__] = wap_module

    spec = importlib.util.spec_from_file_location(module_name, STEP_04_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def make_wap_index(module, wap_to_devices: dict[str, list[str]]):
    wap_index = module.WAPIndex()
    for wap_id, devices in wap_to_devices.items():
        wap_index.index[wap_id] = (
            np.array([], dtype=np.int64),
            np.array(devices, dtype=object),
            np.array([], dtype=object),
        )
    return wap_index


def make_people(module, identity_map: dict[str, str]):
    people = module.People()
    people.identityMap = identity_map
    return people


class Step04BuildGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_step_04_module()

    def test_normalize_real_node_key(self):
        normalize = self.module._normalize_real_node_key

        self.assertEqual(normalize("BRUN-RM303"), "brun-303")
        self.assertEqual(normalize("Brun-209-1"), "brun-209-1")
        self.assertEqual(normalize("trav-brun-203"), "trav-brun203")
        self.assertEqual(normalize("trrav-brun203"), "trav-brun203")

    def test_real_graph_single_svg_skips_unmatched_waps_and_keeps_connectors(self):
        svg = """
        <svg>
          <path id="Brun-107,trav-brun102" d="M0 0L10 10"/>
          <path id="trav-brun102,brun-303" d="M10 10L20 20"/>
        </svg>
        """

        with tempfile.TemporaryDirectory() as temp_dir:
            svg_path = Path(temp_dir) / "brun.svg"
            svg_path.write_text(svg, encoding="utf-8")

            wap_index = make_wap_index(
                self.module,
                {
                    "BRUN-107": ["d1", "d2"],
                    "BRUN-RM303": ["d3"],
                    "BRUN-104-Hallway": ["d4"],
                },
            )
            people = make_people(
                self.module,
                {
                    "d1": "p1",
                    "d2": "p2",
                    "d3": "p3",
                    "d4": "p4",
                },
            )

            graph = self.module.Graph()
            graph.build(wap_index, people, is_synthetic=False, real_svg_source=str(svg_path))

        self.assertIn("BRUN-107", graph.nodes)
        self.assertIn("BRUN-RM303", graph.nodes)
        self.assertIn("trav-brun102", graph.nodes)
        self.assertNotIn("BRUN-104-Hallway", graph.nodes)

        self.assertEqual(graph.node_counts["BRUN-107"], 2)
        self.assertEqual(graph.node_counts["BRUN-RM303"], 1)
        self.assertNotIn("trav-brun102", graph.node_counts)

        self.assertIn("trav-brun102", graph.physical_edges["BRUN-107"])
        self.assertIn("trav-brun102", graph.physical_edges["BRUN-RM303"])

    def test_real_graph_merges_multiple_svgs_and_deduplicates_edges(self):
        svg_a = """
        <svg>
          <path id="Brun-107,trav-brun102" d="M0 0L10 10"/>
          <path id="Brun-107,trav-brun102" d="M0 0L10 10"/>
        </svg>
        """
        svg_b = """
        <svg>
          <path id="trav-brun102,Brun-209-1" d="M10 10L20 20"/>
        </svg>
        """

        with tempfile.TemporaryDirectory() as temp_dir:
            svg_dir = Path(temp_dir)
            (svg_dir / "a.svg").write_text(svg_a, encoding="utf-8")
            (svg_dir / "b.svg").write_text(svg_b, encoding="utf-8")

            wap_index = make_wap_index(
                self.module,
                {
                    "BRUN-107": ["d1"],
                    "BRUN-209-1": ["d2"],
                },
            )
            people = make_people(self.module, {"d1": "p1", "d2": "p2"})

            graph = self.module.Graph()
            graph.build(wap_index, people, is_synthetic=False, real_svg_source=str(svg_dir))

        self.assertEqual(set(graph.physical_edges["trav-brun102"].keys()), {"BRUN-107", "BRUN-209-1"})
        self.assertEqual(graph.node_counts["BRUN-107"], 1)
        self.assertEqual(graph.node_counts["BRUN-209-1"], 1)

    def test_synthetic_graph_still_uses_double_underscore_edges(self):
        svg = """
        <svg>
          <path id="NODE_A__NODE_B" d="M0 0L10 10"/>
          <path id="NODE_B__NODE_C" d="M10 10L20 20"/>
        </svg>
        """

        with tempfile.TemporaryDirectory() as temp_dir:
            svg_path = Path(temp_dir) / "synthetic.svg"
            svg_path.write_text(svg, encoding="utf-8")

            original_path = self.module.SYNTHETIC_SVG_PATH
            self.module.SYNTHETIC_SVG_PATH = str(svg_path)
            try:
                wap_index = make_wap_index(
                    self.module,
                    {
                        "NODE_A": ["d1"],
                        "NODE_B": ["d2"],
                        "NODE_C": ["d3"],
                    },
                )
                people = make_people(self.module, {"d1": "p1", "d2": "p2", "d3": "p3"})

                graph = self.module.Graph()
                graph.build(wap_index, people, is_synthetic=True)
            finally:
                self.module.SYNTHETIC_SVG_PATH = original_path

        self.assertIn("NODE_B", graph.physical_edges["NODE_A"])
        self.assertIn("NODE_C", graph.physical_edges["NODE_B"])
        self.assertEqual(graph.node_counts["NODE_A"], 1)


if __name__ == "__main__":
    unittest.main()
