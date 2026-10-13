"""Chinese/English messages for the CLI; protocol keys and GDS names stay literal."""
from __future__ import annotations

import os
import re
import sys

LANGUAGES = ("en", "zh", "bilingual")
MESSAGES = {
    "description": ("Read-only GDS area measurement with per-layer/datatype overlap deduplication.", "只读统计 GDS 面积；同一 layer/datatype 内的重叠部分只计算一次。"),
    "usage": ("usage", "用法"),
    "positionals": ("positional arguments", "位置参数"),
    "options": ("options", "选项"),
    "help": ("Show this help message and exit", "显示帮助并退出"),
    "help_command": ("inspect: list layers/cells; measure: calculate deduplicated area", "inspect：列出图层与 cell；measure：计算去重面积"),
    "help_inspect": ("List layers, cells, hierarchy and database units", "列出图层、cell、层级和数据库单位"),
    "help_measure": ("Measure deduplicated area by layers or cells", "按图层或 cell 统计去重面积"),
    "help_file": ("Input GDS/GDSII file (read-only)", "输入 GDS/GDSII 文件（只读）"),
    "help_lang": ("Output/help language: en, zh or bilingual; CLI overrides GDS_AREA_LANG; default: bilingual", "输出和帮助语言：en、zh 或 bilingual；命令行优先于 GDS_AREA_LANG；默认 bilingual"),
    "help_json": ("Save a full UTF-8 JSON report; refuse overwrite unless --force", "保存完整 UTF-8 JSON 报告；未指定 --force 时拒绝覆盖"),
    "help_force": ("Replace existing reports; never replace the input layout", "覆盖已有报告；始终不覆盖输入版图"),
    "help_layers": ("e.g. 1/0 2/0; 1 or 1/* selects every datatype of layer 1", "例如 1/0 2/0；1 或 1/* 选择 layer 1 的全部 datatype"),
    "help_cells": ("Exact, case-sensitive cell names separated by spaces", "以空格分隔的精确 cell 名称，区分大小写"),
    "help_top": ("Top/reference cell for layer measurement or instance placement", "统计图层或实例放置时使用的顶层／参考 cell"),
    "help_scope": ("definitions: count each cell definition once; instances: placed occurrences below --top", "definitions：每个 cell 定义各算一次；instances：统计 --top 下放置的实例"),
    "help_direct": ("Use only direct shapes, excluding child-cell geometry", "只统计直接图形，不包含子 cell 图形"),
    "help_csv": ("Save UTF-8-BOM CSV; stable English headers by default", "保存 UTF-8-BOM CSV；默认使用稳定的英文字段名"),
    "help_localized_csv": ("Translate CSV headers and generated row labels using --lang", "按 --lang 翻译 CSV 表头及程序生成的行标签"),
    "invalid_language": ("Invalid language {value!r}; choose en, zh or bilingual.", "无效语言 {value!r}；请选择 en、zh 或 bilingual。"),
    "parser_required": ("The following arguments are required: {names}", "缺少必需参数：{names}"),
    "parser_unknown": ("Unrecognized arguments: {names}", "无法识别的参数：{names}"),
    "parser_argument": ("Argument {name}: {detail}", "参数 {name}：{detail}"),
    "parser_choice": ("Invalid choice {value}; choose from {choices}", "无效选项 {value}；可选值为 {choices}"),
    "parser_one": ("Expected one argument", "需要一个参数值"),
    "parser_many": ("Expected at least one argument", "至少需要一个参数值"),
    "parser_error": ("Invalid arguments: {detail}", "参数有误：{detail}"),
    "error": ("ERROR", "错误"),
    "external_error": ("Operation failed; original diagnostic: {detail}", "操作失败；原始诊断信息：{detail}"),
    "invalid_layer": ("Invalid layer selector {token!r}; use 1/0, 1/* or 1.", "无效图层选择 {token!r}；请使用 1/0、1/* 或 1。"),
    "missing_layer": ("Layer {token!r} not found. Run inspect to list layer/datatype pairs.", "未找到图层 {token!r}。请先运行 inspect 查看 layer/datatype 列表。"),
    "missing_cell": ("Cell {name!r} not found; names are case-sensitive. Run inspect first.", "未找到 cell {name!r}；名称区分大小写。请先运行 inspect。"),
    "choose_top": ("Specify --top: the file has {count} top cells: {names}", "请指定 --top：文件有 {count} 个顶层 cell：{names}"),
    "instances_need_cells": ("--scope instances requires --cells; for an entire layer use --top.", "--scope instances 必须配合 --cells；统计整个图层时请使用 --top。"),
    "unplaced_cells": ("Cells not instantiated below {root!r}: {names}", "以下 cell 未在 {root!r} 下实例化：{names}"),
    "definitions_with_top": ("--cells with --top requires --scope instances; definitions have independent coordinates.", "同时使用 --cells 和 --top 时必须指定 --scope instances；cell 定义各有独立坐标系。"),
    "aggregation_instances": ("Union of selected occurrences per layer in reference coordinates; repeated selections are deduplicated.", "在参考坐标系内逐图层合并所选实例；重复选择只计算一次。"),
    "aggregation_definitions": ("Arithmetic sum of independent cell definitions, each counted once; no common placement is assumed.", "每个独立 cell 定义各算一次后相加；不假定各定义具有共同放置位置。"),
    "warning_cell_rows": ("Per-cell rows may overlap or contain one another; use combined_total for the joint result.", "各 cell 行可能重叠或互相包含；共同结果请使用 combined_total。"),
    "warning_definitions": ("Definitions are independent; shared descendants may contribute to several definitions.", "各定义独立统计；共享子 cell 可能分别计入多个定义。"),
    "warning_ignored": ("Text labels and non-area shapes are ignored; text converted to polygons is included.", "忽略文字标签和无面积图形；已经转为多边形的文字计入面积。"),
    "warning_layers": ("Deduplicate each layer/datatype separately, then sum its area; do not merge different layers.", "各 layer/datatype 分别去重后相加；不同图层之间不合并。"),
    "union_method": ("Merge transformed polygons in reference coordinates, then multiply Region.area() by dbu_um^2.", "将变换后的多边形在参考坐标系内合并，再将 Region.area() 乘以 dbu_um 的平方。"),
    "precision": ("Geometry uses the file DBU grid; rotations/scales that do not preserve it may round vertices.", "几何计算使用文件的 DBU 网格；不保持网格的旋转或缩放可能使顶点坐标取整。"),
    "outputs_distinct": ("JSON and CSV outputs must be different files.", "JSON 和 CSV 必须使用不同的输出文件。"),
    "protect_input": ("Refusing to overwrite the input layout.", "拒绝覆盖输入版图。"),
    "report_extension": ("Report output must not use a layout-file extension.", "报告输出不得使用版图文件扩展名。"),
    "output_exists": ("Output exists: {path}. Choose another name or explicitly use --force.", "输出文件已存在：{path}。请改用其他名称，或明确指定 --force。"),
    "not_file": ("Not a file: {path}", "路径不是文件：{path}"),
    "invalid_dbu": ("Invalid database unit in the layout.", "版图的数据库单位无效。"),
    "runtime_failed": ("KLayout could not load after installation; check platform/wheel compatibility.", "安装后仍无法加载 KLayout；请检查平台与 wheel 的兼容性。"),
    "runtime_entrypoint": ("Run gds_area.py or self_test.py as a script to bootstrap dependencies.", "请以脚本方式运行 gds_area.py 或 self_test.py，以自动安装依赖。"),
    "runtime_install": ("Obtaining an isolated klayout=={version} environment...", "正在获取隔离的 klayout=={version} 运行环境……"),
    "need_powershell": ("PowerShell is required for automatic Windows dependency installation.", "Windows 自动安装依赖需要 PowerShell。"),
    "aggregation_label": ("Aggregation", "合计口径"),
    "note": ("Note", "说明"),
    "all_layers": ("ALL", "全部图层"),
    "all_selected": ("ALL_SELECTED", "全部所选实例"),
    "sum_definitions": ("SUM_OF_DEFINITIONS", "独立定义合计"),
}

FIELD_LABELS = {
    "schema_version": ("Schema version", "报告格式版本"), "input": ("Input file", "输入文件"),
    "created_utc": ("Created at (UTC)", "生成时间（UTC）"), "engine": ("Engine", "计算引擎"),
    "dbu_um": ("Database unit (um)", "数据库单位（微米）"), "language": ("Language", "语言"),
    "top_cells": ("Top cells", "顶层 cell"), "layers": ("Layers", "图层"), "cells": ("Cells", "cell 列表"),
    "index": ("Internal index", "内部索引"), "name": ("Name", "名称"), "spec": ("Layer/datatype", "图层／数据类型"),
    "is_top": ("Is top cell", "是否顶层 cell"), "direct_instances": ("Direct instances", "直接子实例数"),
    "children": ("Child cells", "子 cell"), "scope": ("Scope", "统计范围"),
    "reference_cell": ("Reference cell", "参考 cell"), "selected_cells": ("Selected cells", "所选 cell"),
    "selected_layers": ("Selected layers", "所选图层"), "recursive": ("Recursive", "包含子层级"),
    "overlap_policy": ("Overlap policy", "重叠处理口径"), "cross_layer_policy": ("Cross-layer policy", "跨层合计口径"),
    "aggregation": ("Aggregation", "合计口径"), "union_method": ("Union method", "去重计算方法"),
    "precision": ("Precision", "精度"), "warnings": ("Notes", "说明"), "rows": ("Results", "结果行"),
    "kind": ("Row type", "行类型"), "target": ("Target", "统计对象"), "layer": ("Layer", "图层号"),
    "datatype": ("Datatype", "数据类型"), "union_area_um2": ("Deduplicated area (um2)", "去重面积（平方微米）"),
    "union_area_mm2": ("Deduplicated area (mm2)", "去重面积（平方毫米）"),
    "shape_occurrences": ("Geometry occurrences before merging", "合并前图形出现次数"),
    "ignored_occurrences": ("Ignored occurrences", "忽略的对象出现次数"),
}
VALUE_LABELS = {
    "definitions": ("Cell definitions", "cell 定义"), "instances": ("Placed instances", "放置实例"),
    "cell_layer": ("Cell/layer", "cell 分层结果"), "cell_total": ("Cell total", "cell 合计"),
    "combined_layer": ("Combined/layer", "共同实例分层结果"), "combined_total": ("Combined total", "共同实例合计"),
    "definitions_total": ("Independent definitions total", "独立定义合计"),
    "union_per_layer_datatype": ("Union per layer/datatype", "同一 layer/datatype 内去重"),
    "sum_separate_layers": ("Sum separate layer areas", "各图层面积分别相加"),
    "true": ("Yes", "是"), "false": ("No", "否"),
}


def render(pair, language):
    en, zh = pair
    return en if language == "en" else zh if language == "zh" else zh + " / " + en


def text(key, language="bilingual", **values):
    return render(MESSAGES[key], language).format(**values)


def language_from_args(argv=None):
    values = list(sys.argv[1:] if argv is None else argv)
    language = os.environ.get("GDS_AREA_LANG") or "bilingual"
    for i, value in enumerate(values):
        if value == "--lang" and i + 1 < len(values):
            language = values[i + 1]
        elif value.startswith("--lang="):
            language = value.split("=", 1)[1]
    if language not in LANGUAGES:
        raise LocalizedError("invalid_language", value=language)
    return language


class LocalizedError(ValueError):
    def __init__(self, key, **values):
        self.key, self.values = key, values
        super().__init__(text(key, "en", **values))

    def message(self, language):
        return text(self.key, language, **self.values)


def parser_error(message, language):
    for prefix, key in (("the following arguments are required: ", "parser_required"),
                        ("unrecognized arguments: ", "parser_unknown")):
        if message.startswith(prefix):
            return text(key, language, names=message[len(prefix):])
    match = re.fullmatch(r"argument (.+?): (.+)", message)
    if match:
        detail = match[2]
        choice = re.fullmatch(r"invalid choice: (.+) \(choose from (.+)\)", detail)
        if choice:
            detail = text("parser_choice", language, value=choice[1], choices=choice[2])
        elif detail == "expected one argument":
            detail = text("parser_one", language)
        elif detail == "expected at least one argument":
            detail = text("parser_many", language)
        return text("parser_argument", language, name=match[1], detail=detail)
    return text("parser_error", language, detail=message)


def field_label(key, language):
    return render(FIELD_LABELS[key], language)


def value_label(value, language):
    return render(VALUE_LABELS[value], language) if value in VALUE_LABELS else value


def report_labels(language):
    return {"fields": {key: render(pair, language) for key, pair in FIELD_LABELS.items()},
            "values": {key: render(pair, language) for key, pair in VALUE_LABELS.items()}}


def configure_utf8_streams():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
