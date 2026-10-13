#!/usr/bin/env python3
"""Analytic regression cases, using temporary GDS files; no user data needed."""
from __future__ import annotations

import hashlib
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid

from runtime import ensure_runtime


def build_fixture(k, path):
    layout = k.Layout()
    layout.dbu = 0.001
    a, ad, b, c, d = [layout.layer(*pair) for pair in ((1, 0), (1, 1), (2, 0), (3, 0), (4, 0))]
    leaf = layout.create_cell("LEAF")
    leaf.shapes(c).insert(k.Polygon([k.Point(0, 0), k.Point(6000, 0), k.Point(0, 4000)]))
    unit = layout.create_cell("UNIT")
    unit.shapes(a).insert(k.Box(0, 0, 10000, 10000))
    unit.shapes(a).insert(k.Box(5000, 0, 15000, 10000))
    unit.shapes(a).insert(k.Text("label", k.Trans()))
    unit.shapes(ad).insert(k.Box(0, 20000, 2000, 22000))
    unit.shapes(b).insert(k.Box(0, 0, 10000, 10000))
    unit.insert(k.CellInstArray(leaf.cell_index(), k.Trans(0, 40000)))
    top = layout.create_cell("TOP")
    top.insert(k.CellInstArray(unit.cell_index(), k.Trans()))
    top.insert(k.CellInstArray(unit.cell_index(), k.Trans(10000, 0)))
    top.insert(k.CellInstArray(unit.cell_index(), k.Trans(100000, 0),
                              k.Vector(30000, 0), k.Vector(0, 70000), 2, 2))
    top.insert(k.CellInstArray(unit.cell_index(), k.ICplxTrans(2, 90, True, 300000, 0)))
    top.insert(k.CellInstArray(leaf.cell_index(), k.Trans(0, -100000)))
    top.shapes(a).insert(k.Box(-30000, 0, -20000, 10000))
    top.shapes(d).insert(k.Path([k.Point(0, 200000), k.Point(20000, 200000)], 2000))
    hole = k.Polygon(k.Box(100000, 200000, 110000, 210000))
    hole.insert_hole(k.Box(103000, 203000, 107000, 207000))
    top.shapes(d).insert(hole)
    empty = layout.create_cell("EMPTY")
    top.insert(k.CellInstArray(empty.cell_index(), k.Trans()))
    layout.write(str(path))
    return path


class AreaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import klayout.db as k
        import gds_area as area
        cls.k, cls.area = k, area
        # Normal inherited ACLs are needed in sandboxed Windows hosts.
        base = Path(os.environ.get("GDS_AREA_TEST_TMP", tempfile.gettempdir())).resolve()
        cls.folder = base / ("gds-area-test-" + uuid.uuid4().hex)
        cls.folder.mkdir(parents=True, exist_ok=False)
        cls.path = build_fixture(k, cls.folder / "fixture.gds")
        cls.before = hashlib.sha256(cls.path.read_bytes()).hexdigest()

    @classmethod
    def tearDownClass(cls):
        if hashlib.sha256(cls.path.read_bytes()).hexdigest() != cls.before:
            raise AssertionError("Input GDS was modified")
        if cls.folder.resolve().parent != cls.folder.parent or not cls.folder.name.startswith("gds-area-test-"):
            raise AssertionError("Unexpected cleanup path")
        shutil.rmtree(cls.folder)

    def report(self, *options):
        args = self.area.parser().parse_args(["measure", str(self.path), *options])
        layout = self.k.Layout()
        layout.read(str(self.path))
        return self.area.measure(self.k, layout, args, self.path)

    def row(self, report, kind, target=None):
        return next(r for r in report["rows"] if r["kind"] == kind and (target is None or r["target"] == target))

    def values(self, row, union):
        self.assertAlmostEqual(row["union_area_um2"], union, places=7)
        self.assertAlmostEqual(row["union_area_mm2"], union / 1e6, places=12)

    def test_definition_overlap_and_label(self):
        r = self.row(self.report("--cells", "UNIT", "--layers", "1/0"), "cell_total")
        self.values(r, 150)
        self.assertEqual(r["shape_occurrences"], 2)
        self.assertEqual(r["ignored_occurrences"], 1)

    def test_layer_datatypes_and_duplicate_selectors(self):
        report = self.report("--cells", "UNIT", "--layers", "1", "1/0", "1/*")
        self.assertEqual(report["selected_layers"], ["1/0", "1/1"])
        self.values(self.row(report, "cell_total"), 154)

    def test_multilayer_total_keeps_layers_separate(self):
        report = self.report("--cells", "UNIT", "--layers", "1/0", "2/0")
        self.values(self.row(report, "cell_total"), 250)
        self.assertEqual([r["union_area_um2"] for r in report["rows"] if r["kind"] == "cell_layer"], [150, 100])

    def test_array_rotation_mirror_scaling(self):
        r = self.row(self.report("--scope", "instances", "--top", "TOP", "--cells", "UNIT", "--layers", "1/0"), "combined_total")
        self.values(r, 1450)
        self.assertEqual(r["shape_occurrences"], 14)

    def test_entire_layer_includes_direct_shapes(self):
        self.values(self.row(self.report("--layers", "1/0"), "cell_total"), 1550)

    def test_direct_shapes_only(self):
        self.values(self.row(self.report("--top", "TOP", "--layers", "1/0", "--no-recursive"), "cell_total"), 100)

    def test_selected_subtree_excludes_same_descendant_elsewhere(self):
        r = self.report("--scope", "instances", "--cells", "UNIT", "--layers", "3/0")
        self.values(self.row(r, "combined_total"), 120)

    def test_nested_selections_do_not_double_count(self):
        r = self.report("--scope", "instances", "--cells", "UNIT", "LEAF", "--layers", "3/0")
        self.values(self.row(r, "cell_total", "UNIT"), 120)
        self.values(self.row(r, "cell_total", "LEAF"), 132)
        self.values(self.row(r, "combined_total"), 132)

    def test_instances_no_recursive(self):
        r = self.report("--scope", "instances", "--cells", "UNIT", "--layers", "3/0", "--no-recursive")
        self.values(self.row(r, "combined_total"), 0)

    def test_reference_cell_selected(self):
        r = self.report("--scope", "instances", "--cells", "TOP", "UNIT", "--layers", "1/0")
        self.values(self.row(r, "combined_total"), 1550)

    def test_multiple_definitions_are_separate(self):
        r = self.report("--cells", "UNIT", "LEAF", "UNIT", "--layers", "3/0")
        self.values(self.row(r, "definitions_total"), 24)

    def test_paths_and_holes(self):
        self.values(self.row(self.report("--layers", "4/0"), "cell_total"), 124)

    def test_empty_cell(self):
        self.values(self.row(self.report("--cells", "EMPTY"), "cell_total"), 0)

    def test_invalid_selections(self):
        for options in (("--cells", "TYPO"), ("--layers", "999/0"), ("--layers", "1/0/2"),
                        ("--scope", "instances"), ("--cells", "UNIT", "--top", "TOP")):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.report(*options)

    def test_multiple_tops_require_choice(self):
        layout = self.k.Layout()
        layout.create_cell("A")
        layout.create_cell("B")
        with self.assertRaises(ValueError):
            self.area.choose_top(layout, None)

    def test_non_default_dbu(self):
        layout = self.k.Layout()
        layout.dbu = 0.01
        cell = layout.create_cell("DBU")
        cell.shapes(layout.layer(1, 0)).insert(self.k.Box(0, 0, 1000, 1000))
        args = self.area.parser().parse_args(["measure", str(self.path)])
        self.values(self.row(self.area.measure(self.k, layout, args, self.path), "cell_total"), 100)

    def test_cli_json_csv_and_input_protection(self):
        folder = self.folder
        out_json, out_csv = folder / "area.json", folder / "area.csv"
        command = [sys.executable, str(Path(__file__).with_name("gds_area.py")), "measure", str(self.path),
                   "--cells", "UNIT", "--layers", "1/0", "--json", str(out_json), "--csv", str(out_csv)]
        first = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(first.returncode, 0, first.stderr)
        report_text = out_json.read_text(encoding="utf-8")
        report = json.loads(report_text)
        self.values(self.row(report, "cell_total"), 150)
        self.assertEqual(report["schema_version"], 2)
        csv_text = out_csv.read_text(encoding="utf-8-sig")
        self.assertIn("union_area_um2", csv_text)
        for output in (first.stdout, report_text, csv_text):
            self.assertNotIn("raw_", output)
            self.assertNotIn("projection", output)
        second = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        self.assertNotEqual(second.returncode, 0)
        args = self.area.parser().parse_args(["measure", str(self.path), "--json", str(self.path), "--force"])
        with self.assertRaises(ValueError):
            self.area.check_outputs(args, self.path)

    def test_inspect(self):
        layout = self.k.Layout()
        layout.read(str(self.path))
        report = self.area.inventory(layout, self.path)
        self.assertEqual(report["top_cells"], ["TOP"])
        self.assertEqual(len(report["layers"]), 5)

    def cli(self, *options, extra_env=None):
        env = os.environ.copy()
        env.pop("GDS_AREA_LANG", None)
        if extra_env:
            env.update(extra_env)
        return subprocess.run([sys.executable, str(Path(__file__).with_name("gds_area.py")), *options],
                              capture_output=True, text=True, encoding="utf-8", env=env)

    def test_language_modes_keep_numerical_results_and_names(self):
        results = []
        for language in ("zh", "en", "bilingual"):
            with self.subTest(language=language):
                output = self.folder / ("language-" + language + ".json")
                result = self.cli("measure", str(self.path), "--cells", "UNIT", "--layers", "1/0",
                                  "--lang", language, "--json", str(output))
                self.assertEqual(result.returncode, 0, result.stderr)
                report = json.loads(output.read_text(encoding="utf-8"))
                results.append(report["rows"])
                self.assertEqual(report["language"], language)
                self.assertEqual(report["selected_cells"], ["UNIT"])
                self.values(self.row(report, "cell_total"), 150)
                self.assertIn("UNIT", result.stdout)
                if language != "en":
                    self.assertIn("去重面积", result.stdout)
                    self.assertIn("各 layer/datatype", report["warnings"][-1])
                if language != "zh":
                    self.assertIn("Deduplicated area", result.stdout)
                    self.assertIn("Deduplicate each layer/datatype", report["warnings"][-1])
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[1], results[2])

    def test_localized_help_and_parse_errors(self):
        for language, marker in (("zh", "去重面积"), ("en", "Deduplicated"), ("bilingual", "去重面积")):
            with self.subTest(language=language):
                help_result = self.cli("measure", "--lang", language, "--help")
                self.assertEqual(help_result.returncode, 0)
                self.assertIn("--localized-csv", help_result.stdout)
                if language != "en":
                    self.assertIn("选项", help_result.stdout)
                    self.assertNotIn("用法: 用法:", help_result.stdout)
                if language != "zh":
                    self.assertIn("options", help_result.stdout)
                    self.assertNotIn("usage: usage:", help_result.stdout)
                result = self.cli("measure", "--lang", language)
                self.assertEqual(result.returncode, 2)
                if language != "en":
                    self.assertIn("缺少必需参数", result.stderr)
                if language != "zh":
                    self.assertIn("arguments are required", result.stderr)
                result = self.cli("measure", str(self.path), "--lang", language, "--cells", "TYPO")
                self.assertEqual(result.returncode, 2)
                self.assertIn("TYPO", result.stderr)
                self.assertIn("未找到 cell" if language == "zh" else "not found", result.stderr)
        invalid = self.cli("measure", str(self.path), "--lang", "fr")
        self.assertEqual(invalid.returncode, 2)
        self.assertIn("无效语言", invalid.stderr)
        self.assertIn("Invalid language", invalid.stderr)

    def test_language_precedence_and_option_positions(self):
        cases = [(('--lang', 'en', 'inspect', str(self.path)), 'en'),
                 (('inspect', str(self.path), '--lang=zh'), 'zh'),
                 (('--lang', 'zh', 'inspect', str(self.path), '--lang', 'en'), 'en'),
                 (('inspect', str(self.path)), 'zh')]
        for options, expected in cases:
            with self.subTest(options=options):
                result = self.cli(*options, extra_env={"GDS_AREA_LANG": "zh"})
                self.assertEqual(result.returncode, 0, result.stderr)
                report = json.loads(result.stdout)
                self.assertEqual(report["language"], expected)
                self.assertEqual(report["top_cells"], ["TOP"])
        override = self.cli("inspect", str(self.path), "--lang", "en", extra_env={"GDS_AREA_LANG": "invalid"})
        self.assertEqual(override.returncode, 0, override.stderr)

    def test_localized_csv_and_stable_default_headers(self):
        fieldnames = ["kind", "target", "layer", "datatype", "union_area_um2", "union_area_mm2",
                      "shape_occurrences", "ignored_occurrences"]
        for language in ("zh", "en", "bilingual"):
            for localized in (False, True):
                with self.subTest(language=language, localized=localized):
                    output = self.folder / f"csv-{language}-{localized}.csv"
                    options = ["measure", str(self.path), "--cells", "UNIT", "--layers", "1/0",
                               "--lang", language, "--csv", str(output)]
                    if localized:
                        options.append("--localized-csv")
                    result = self.cli(*options)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertTrue(output.read_bytes().startswith(b"\xef\xbb\xbf"))
                    with output.open(encoding="utf-8-sig", newline="") as stream:
                        rows = list(csv.reader(stream))
                    self.assertEqual(float(rows[1][4]), 150)
                    self.assertEqual(rows[1][1], "UNIT")
                    if localized:
                        self.assertIn("面积" if language == "zh" else "area", rows[0][4])
                    else:
                        self.assertEqual(rows[0], fieldnames)
                        self.assertEqual(rows[1][0], "cell_layer")

    def test_unicode_paths_and_output_names(self):
        folder = self.folder / "中文目录"
        folder.mkdir()
        source = folder / "版图.gds"
        source.write_bytes(self.path.read_bytes())
        output = folder / "面积报告.json"
        result = self.cli("measure", str(source), "--cells", "UNIT", "--layers", "1/0", "--lang", "zh",
                          "--json", str(output))
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report["input"], str(source.resolve()))
        self.values(self.row(report, "cell_total"), 150)

    def test_runtime_language_is_forwarded(self):
        import runtime
        from unittest.mock import patch
        with patch.object(runtime, "compatible", return_value=False), \
             patch.object(runtime.sys, "argv", [str(Path(__file__).with_name("gds_area.py")), "--lang", "zh", "inspect", str(self.path)]), \
             patch.object(runtime.shutil, "which", return_value="shell"), \
             patch.object(runtime.subprocess, "call", return_value=0) as child, \
             patch.object(runtime.os, "environ", {"GDS_AREA_CACHE": str(self.folder)}):
            with self.assertRaises(SystemExit):
                runtime.ensure_runtime("zh")
            self.assertEqual(child.call_args.kwargs["env"]["GDS_AREA_LANG"], "zh")
            self.assertEqual(child.call_args.kwargs["env"]["PYTHONIOENCODING"], "utf-8")


if __name__ == "__main__":
    ensure_runtime()
    unittest.main(verbosity=2)
