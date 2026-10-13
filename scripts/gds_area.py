#!/usr/bin/env python3
"""Read-only GDS geometry area measurement using KLayout's database engine."""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import re
import sys
from datetime import datetime, timezone

from runtime import ensure_runtime
from i18n import (LANGUAGES, LocalizedError, configure_utf8_streams, field_label,
                  language_from_args, parser_error, report_labels, text, value_label)


class LocalizedHelpFormatter(argparse.HelpFormatter):
    def __init__(self, prog, language):
        self.language = language
        super().__init__(prog)

    def add_usage(self, usage, actions, groups, prefix=None):
        super().add_usage(usage, actions, groups,
                          text("usage", self.language) + ": " if prefix is None else prefix)


class LocalizedArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, language="bilingual", **kwargs):
        self.language = language
        kwargs.setdefault("add_help", False)
        kwargs.setdefault("formatter_class", lambda prog: LocalizedHelpFormatter(prog, language))
        super().__init__(*args, **kwargs)
        self._positionals.title = text("positionals", language)
        self._optionals.title = text("options", language)
        self.add_argument("-h", "--help", action="help", help=text("help", language))

    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: {text('error', self.language)}: {parser_error(message, self.language)}\n")


def parser(argv=None) -> argparse.ArgumentParser:
    language = language_from_args(argv)
    p = LocalizedArgumentParser(description=text("description", language), language=language)
    p.add_argument("--lang", choices=LANGUAGES, default=language, help=text("help_lang", language))
    sub = p.add_subparsers(dest="command", required=True, help=text("help_command", language))
    for command in ("inspect", "measure"):
        q = sub.add_parser(command, language=language, help=text("help_" + command, language))
        q.add_argument("file", type=Path, metavar="GDS_FILE", help=text("help_file", language))
        q.add_argument("--lang", choices=LANGUAGES, default=argparse.SUPPRESS, help=text("help_lang", language))
        q.add_argument("--json", type=Path, help=text("help_json", language))
        q.add_argument("--force", action="store_true", help=text("help_force", language))
        if command == "measure":
            q.add_argument("--layers", nargs="+", help=text("help_layers", language))
            q.add_argument("--cells", nargs="+", help=text("help_cells", language))
            q.add_argument("--top", help=text("help_top", language))
            q.add_argument("--scope", choices=("definitions", "instances"), default="definitions", help=text("help_scope", language))
            q.add_argument("--no-recursive", action="store_true", help=text("help_direct", language))
            q.add_argument("--csv", type=Path, help=text("help_csv", language))
            q.add_argument("--localized-csv", action="store_true", help=text("help_localized_csv", language))
    return p


def layer_records(layout):
    return sorted(
        ({"index": i, "layer": layout.get_info(i).layer, "datatype": layout.get_info(i).datatype,
          "name": layout.get_info(i).name, "spec": f"{layout.get_info(i).layer}/{layout.get_info(i).datatype}"}
         for i in layout.layer_indexes()),
        key=lambda r: (r["layer"], r["datatype"], r["index"]),
    )


def choose_layers(layout, selectors):
    available = layer_records(layout)
    if not selectors:
        return available
    chosen = set()
    for token in selectors:
        match = re.fullmatch(r"(\d+)(?:[/:](\d+|\*))?", token)
        if not match:
            raise LocalizedError("invalid_layer", token=token)
        layer, datatype = int(match[1]), match[2]
        found = [r for r in available if r["layer"] == layer and
                 (datatype in (None, "*") or r["datatype"] == int(datatype))]
        if not found:
            raise LocalizedError("missing_layer", token=token)
        chosen.update(r["index"] for r in found)
    return [r for r in available if r["index"] in chosen]


def exact_cell(layout, name):
    cell = layout.cell(name)
    if cell is None:
        raise LocalizedError("missing_cell", name=name)
    return cell


def choose_top(layout, name):
    if name:
        return exact_cell(layout, name)
    tops = list(layout.top_cells())
    if len(tops) != 1:
        raise LocalizedError("choose_top", count=len(tops), names=", ".join(c.name for c in tops))
    return tops[0]


def inventory(layout, source, language="bilingual"):
    return {
        "schema_version": 1, "input": str(source), "dbu_um": layout.dbu,
        "language": language, "labels": report_labels(language),
        "top_cells": sorted(c.name for c in layout.top_cells()),
        "layers": layer_records(layout),
        "cells": [{"name": c.name, "index": c.cell_index(), "is_top": c.is_top(),
                   "direct_instances": c.child_instances(),
                   "children": sorted(layout.cell(i).name for i in c.each_child_cell())}
                  for c in sorted(layout.each_cell(), key=lambda c: c.name)],
    }


def make_iterator(root, layer_index, recursive, selected=None):
    it = root.begin_shapes_rec(layer_index)
    if selected is None:
        if not recursive:
            it.max_depth = 0
    elif recursive:
        # Stop delivery at the reference cell. Re-enable selected subtrees only;
        # do not globally select their descendants (which could occur elsewhere).
        it.unselect_cells([root.cell_index()])
        it.select_cells([c.cell_index() for c in selected])
    else:
        it.unselect_all_cells()
        it.select_cells([c.cell_index() for c in selected])
    return it


def geometry(kdb, root, layer_index, recursive, selected=None):
    region = kdb.Region()
    it = make_iterator(root, layer_index, recursive, selected)
    count = ignored = 0
    while not it.at_end():
        shape = it.shape()
        if shape.is_box() or shape.is_polygon() or shape.is_path():
            polygon = shape.polygon
            trans = it.trans()
            region.insert(polygon.transformed(trans))
            count += 1
        else:
            ignored += 1
        it.next()
    # Do not call area after every insertion: one union per completed region.
    region.merged_semantics = True
    region.merge()
    return region, count, ignored


def base_row(kind, target, layer, datatype, merged, count, ignored, dbu):
    return {"kind": kind, "target": target, "layer": layer, "datatype": datatype,
            "union_area_um2": merged * dbu ** 2,
            "union_area_mm2": merged * dbu ** 2 / 1e6,
            "shape_occurrences": count, "ignored_occurrences": ignored}


def measure_target(kdb, layout, layers, root, recursive, target, kind, selected=None):
    rows = []
    for layer in layers:
        region, count, ignored = geometry(kdb, root, layer["index"], recursive, selected)
        rows.append(base_row(kind + "_layer", target, layer["layer"], layer["datatype"],
                             region.area(), count, ignored, layout.dbu))
    total = {"kind": kind + "_total", "target": target, "layer": None, "datatype": None}
    for key in ("union_area_um2", "union_area_mm2"):
        total[key] = math.fsum(r[key] for r in rows)
    for key in ("shape_occurrences", "ignored_occurrences"):
        total[key] = sum(r[key] for r in rows)
    rows.append(total)
    return rows


def measure(kdb, layout, args, source):
    language = getattr(args, "lang", "bilingual")
    layers = choose_layers(layout, args.layers)
    cells = [exact_cell(layout, name) for name in dict.fromkeys(args.cells or [])]
    recursive = not args.no_recursive
    rows, warnings = [], []
    root = None
    if args.scope == "instances":
        if not cells:
            raise LocalizedError("instances_need_cells")
        root = choose_top(layout, args.top)
        reachable = set(root.called_cells()) | {root.cell_index()}
        missing = [c.name for c in cells if c.cell_index() not in reachable]
        if missing:
            raise LocalizedError("unplaced_cells", root=root.name, names=", ".join(missing))
        for cell in cells:
            rows.extend(measure_target(kdb, layout, layers, root, recursive, cell.name, "cell", [cell]))
        # A single traversal with the union of selected subtrees avoids counting
        # an ancestor and its selected descendant twice in the combined result.
        rows.extend(measure_target(kdb, layout, layers, root, recursive, "ALL_SELECTED", "combined", cells))
        aggregation = text("aggregation_instances", language)
        if len(cells) > 1:
            warnings.append(text("warning_cell_rows", language))
    else:
        if cells and args.top:
            raise LocalizedError("definitions_with_top")
        if not cells:
            root = choose_top(layout, args.top)
            cells = [root]
        for cell in cells:
            rows.extend(measure_target(kdb, layout, layers, cell, recursive, cell.name, "cell"))
        totals = [r for r in rows if r["kind"] == "cell_total"]
        overall = {"kind": "definitions_total", "target": "SUM_OF_DEFINITIONS", "layer": None, "datatype": None}
        for key in ("union_area_um2", "union_area_mm2"):
            overall[key] = math.fsum(r[key] for r in totals)
        for key in ("shape_occurrences", "ignored_occurrences"):
            overall[key] = sum(r[key] for r in totals)
        rows.append(overall)
        aggregation = text("aggregation_definitions", language)
        if len(cells) > 1:
            warnings.append(text("warning_definitions", language))
    if any(r.get("ignored_occurrences", 0) for r in rows):
        warnings.append(text("warning_ignored", language))
    warnings.append(text("warning_layers", language))
    return {
        "schema_version": 2, "input": str(source), "created_utc": datetime.now(timezone.utc).isoformat(),
        "engine": f"KLayout {kdb.__version__}", "dbu_um": layout.dbu,
        "language": language, "labels": report_labels(language),
        "scope": args.scope, "reference_cell": root.name if root else None,
        "selected_cells": [c.name for c in cells], "selected_layers": [r["spec"] for r in layers],
        "recursive": recursive, "overlap_policy": "union_per_layer_datatype",
        "cross_layer_policy": "sum_separate_layers",
        "aggregation": aggregation,
        "union_method": text("union_method", language),
        "precision": text("precision", language),
        "warnings": warnings, "rows": rows,
    }


def check_outputs(args, source):
    paths = [p for p in (args.json, getattr(args, "csv", None)) if p is not None]
    resolved = [p.expanduser().resolve() for p in paths]
    if len(set(resolved)) != len(resolved):
        raise LocalizedError("outputs_distinct")
    for path in resolved:
        if path == source or (path.exists() and path.samefile(source)):
            raise LocalizedError("protect_input")
        if path.suffix.lower() in (".gds", ".gdsii", ".oas", ".oasis"):
            raise LocalizedError("report_extension")
        if path.exists() and not args.force:
            raise LocalizedError("output_exists", path=path)


def write_outputs(args, report):
    language = report.get("language", "bilingual")
    if args.json:
        path = args.json.expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w" if args.force else "x", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.write("\n")
    if getattr(args, "csv", None):
        path = args.csv.expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        fields = ["kind", "target", "layer", "datatype", "union_area_um2",
                  "union_area_mm2", "shape_occurrences", "ignored_occurrences"]
        with path.open("w" if args.force else "x", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            localized = getattr(args, "localized_csv", False)
            if localized:
                writer.writerow({key: field_label(key, language) for key in fields})
            else:
                writer.writeheader()
            # Text cells are untrusted names from the input GDS; prevent spreadsheet formulas.
            for row in report["rows"]:
                if localized:
                    row = {**row, "kind": value_label(row["kind"], language),
                           "target": display_target(row, language)}
                safe = {k: ("'" + v if isinstance(v, str) and v.startswith(("=", "+", "-", "@", "\t", "\r")) else v)
                        for k, v in row.items()}
                writer.writerow(safe)


def display_target(row, language):
    if row["kind"].startswith("combined_"):
        return text("all_selected", language)
    if row["kind"] == "definitions_total":
        return text("sum_definitions", language)
    return row["target"]


def print_report(report, command):
    language = report.get("language", "bilingual")
    if command == "inspect":
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    print(f"DBU: {report['dbu_um']} um | {field_label('scope', language)}: {value_label(report['scope'], language)}"
          f" | {field_label('recursive', language)}: {value_label(str(report['recursive']).lower(), language)}")
    print("\t".join([field_label('kind', language), field_label('target', language),
                     field_label('spec', language), field_label('union_area_um2', language),
                     field_label('union_area_mm2', language)]))
    for row in report["rows"]:
        layer = text("all_layers", language) if row["layer"] is None else f"{row['layer']}/{row['datatype']}"
        print(f"{value_label(row['kind'], language)}\t{display_target(row, language)}\t{layer}"
              f"\t{row['union_area_um2']:.12g}\t{row['union_area_mm2']:.12g}")
    print(text("aggregation_label", language) + ": " + report["aggregation"])
    for warning in report["warnings"]:
        print(text("note", language) + ": " + warning)


def main():
    configure_utf8_streams()
    language = "bilingual"
    try:
        language = language_from_args()
        args = parser().parse_args()
        language = args.lang
        source = args.file.expanduser().resolve(strict=True)
        if not source.is_file():
            raise LocalizedError("not_file", path=source)
        check_outputs(args, source)
        ensure_runtime(language)
        import klayout.db as kdb
        layout = kdb.Layout()
        layout.read(str(source))
        if not math.isfinite(layout.dbu) or layout.dbu <= 0:
            raise LocalizedError("invalid_dbu")
        report = inventory(layout, source, language) if args.command == "inspect" else measure(kdb, layout, args, source)
        write_outputs(args, report)
        print_report(report, args.command)
        return 0
    except LocalizedError as exc:
        print(f"{text('error', language)}: {exc.message(language)}", file=sys.stderr)
        return 2
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"{text('error', language)}: {text('external_error', language, detail=str(exc))}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"{text('error', language)} ({type(exc).__name__}): {text('external_error', language, detail=str(exc))}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
