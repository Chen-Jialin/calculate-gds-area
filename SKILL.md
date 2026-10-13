---
name: calculate-gds-area
description: >-
  Calculate deduplicated GDS/GDSII layout area with KLayout for one or more layers, layer/datatype pairs, cells or placed instances. Use for GDS area, mask coverage and layer/cell area requests in English or Chinese. Count overlaps once within each layer/datatype and sum separate layers. Handle hierarchy, arrays and transforms; automatically obtain missing Python/KLayout dependencies; export JSON/CSV with Chinese, English or bilingual presentation.
  使用 KLayout 统计 GDS/GDSII 图层、layer/datatype、cell 或放置实例的面积。用于中英文的版图面积、掩膜覆盖面积及图层／单元面积请求。同层重叠只计一次，各层面积分别相加；支持层级、阵列、变换、自动安装依赖及中英双语 JSON/CSV 报告。
---

# GDS 版图面积统计 / GDS Layout Area

使用随附脚本计算真实图形面积，保持输入只读。先检查实际 layer/datatype 和 cell 名称，不将包围盒面积当作图形面积。

Use the bundled scripts to measure actual geometry while keeping input read-only. Inspect real layer/datatype pairs and cell names first; do not substitute bounding-box area.

## 语言选择 / Language selection

- 按用户明确指定的语言解释结果；否则采用请求的主要语言。明确要求双语或语言不明确时采用双语。中文请求使用 `--lang zh`，英文请求使用 `--lang en`，双语请求使用 `--lang bilingual`。不翻译路径、cell 名称、图层号或命令参数。
- Explain results in the explicitly requested language, or the main language of the task. Use bilingual output when requested or when unclear. Select `--lang zh`, `--lang en` or `--lang bilingual` accordingly. Never translate paths, cell names, layer numbers or CLI identifiers.
- 命令行默认双语。`--lang` 可放在子命令前后，也支持 `--lang=en`，优先于 `GDS_AREA_LANG`。帮助、程序报错、说明与安装提示遵循该设置；第三方原始诊断保留原文。
- The CLI defaults to bilingual. Put `--lang` before or after a subcommand, or use `--lang=en`; it overrides `GDS_AREA_LANG`. Help, application errors, notes and bootstrap messages follow this setting; preserve third-party diagnostics verbatim.
- JSON 保留稳定英文字段名和枚举值，`labels.fields` / `labels.values` 提供翻译；说明按所选语言输出。CSV 默认保留英文字段名；添加 `--localized-csv` 可翻译表头和程序生成的行标签。
- Keep JSON protocol keys and enum values stable in English, with translations in `labels.fields` / `labels.values`; localize explanatory values. CSV keeps English protocol headers by default; add `--localized-csv` for translated headers and generated row labels.

## 执行流程 / Workflow

1. 定位用户的 `.gds` 文件；连接服务中的文件按宿主能力下载到本地。没有文件时请用户提供。
   Locate the user's `.gds` file; materialize connected-service files with supported host capabilities. Request the file if absent.
2. 在 skill 目录中运行平台启动器检查版图，按请求选择语言。
   From the skill directory, inspect the layout with the platform launcher and requested language.

   Windows PowerShell:
   ```powershell
   & ./scripts/run.ps1 inspect 'C:/data/chip.gds' --lang zh
   ```

   Linux / macOS:
   ```sh
   sh ./scripts/run.sh inspect '/data/chip.gds' --lang en
   ```

   已有 Python 3.10–3.14 时也可直接执行 / With Python 3.10–3.14 already available:
   ```sh
   python scripts/gds_area.py inspect chip.gds --lang bilingual
   ```

3. 从 `inspect` 核实名称。区分 GDS 图层号与 KLayout 内部索引，向用户使用 `layer/datatype`。不存在的图层／cell 必须报错，不替换为近似名称，不当成零面积。
   Verify names using `inspect`. Distinguish GDS layer numbers from internal indexes; report `layer/datatype`. Reject missing layers/cells without substituting similar names or silently returning zero.
4. 按下表选择范围；可靠的默认范围先执行并说明。仅当多顶层等歧义妨碍可靠计算时询问。
   Choose the scope below; proceed with and state an unambiguous default. Ask only when ambiguity, such as multiple tops, prevents reliable measurement.
5. 运行 `measure`，读取实际输出，报告范围、层级、去重口径、逐项结果、合计和说明。保存报告使用 `--json` / `--csv`。
   Run `measure`, read actual output, and report scope, hierarchy, deduplication, individual results, totals and notes. Save reports with `--json` / `--csv`.

## 选择与统计口径 / Selection and measurement rules

| 请求 / Request | 执行规则 / Rule |
| --- | --- |
| layer `1` | 包含全部 datatype，分别列出并合计 / Include all datatypes; list and sum them separately. |
| layer/datatype `1/0` | 仅这个逻辑图层 / Only this logical layer. |
| 一个或多个 cell / One or more cells | 默认 `--scope definitions`；每个定义各算一次，含子 cell / Default to `definitions`; count each definition once, including descendants. |
| 全部放置实例／阵列 / All placed instances or arrays | 使用 `--scope instances --cells ... --top ...`，保留实际位置、重复和变换 / Use `instances` with `--cells` and `--top`; preserve placement, repetition and transforms. |
| cell 内指定图层 / Layers within cells | 同时传入 `--cells` 和 `--layers` / Combine `--cells` and `--layers`. |
| 仅直接图形 / Direct geometry only | 使用 `--no-recursive` / Use `--no-recursive`. |
| 多层合计 / Multiple-layer total | 各 layer/datatype 先去重再相加，不跨层合并 / Deduplicate each layer/datatype, then sum; never merge different layers. |

- 只报告去重面积 `union_area_um2` / `union_area_mm2`。同一 layer/datatype 先合并所选图形，重叠只计一次；不提供逐图形累加或跨层投影口径。
- Report only `union_area_um2` / `union_area_mm2`. Merge selected geometry per layer/datatype so overlaps count once. Do not offer additive shape area or cross-layer projection modes.
- 使用文件实际 `dbu`；面积以 µm² 报告，除以 1,000,000 得 mm²。计入 polygon、box、path；忽略文字标签等无面积对象，已转成多边形的文字计入。
- Use the file's actual `dbu`; report µm² and divide by 1,000,000 for mm². Include polygons, boxes and paths. Ignore non-area objects such as text labels, but include polygonal text.
- 默认包含全部子层级、平移、镜像、旋转、缩放及阵列元素。不要用定义面积乘引用条数替代实例计算。
- Include descendants, translations, mirrors, rotations, scales and array elements by default. Do not replace instance measurement with definition area multiplied by reference count.
- `definitions_total` 仅为各独立定义内部去重后的面积相加，不假定共同坐标。选中父子定义时共享子 cell 可贡献多个定义，不能称为芯片的物理去重覆盖面积。
- `definitions_total` sums independent definitions without shared placement coordinates. A descendant may contribute to several selected definitions; this is not a physical chip-coverage union.
- 实例共同结果使用 `combined_total`，不要再相加各 cell 行。共同选择父子 cell 时同一图形实例只遍历一次。
- Use `combined_total` for joint instances instead of adding per-cell rows. Visit an occurrence only once when its ancestor and descendant are both selected.
- 未指定 cell 时从唯一顶层开始；多顶层要求指定 `--top` 或 `--cells`，不自动叠放。cell 名称精确匹配、区分大小写，不使用通配符。
- With no cell selection, use the unique top. Require `--top` or `--cells` for multiple tops; do not overlay them automatically. Match cell names exactly and case-sensitively, without wildcards.

## 命令示例 / Examples

将 `python scripts/gds_area.py` 替换为 `& ./scripts/run.ps1` 或 `sh ./scripts/run.sh` 可同时自动获取 Python。路径或名称有空格时加引号。

Replace `python scripts/gds_area.py` with `& ./scripts/run.ps1` or `sh ./scripts/run.sh` to obtain Python automatically as well. Quote paths/names containing spaces.

```sh
# 多图层 / Multiple layers
python scripts/gds_area.py measure chip.gds --top CHIP --layers 1/0 2/0 --lang bilingual
# layer 10 的所有 datatype / Every datatype of layer 10
python scripts/gds_area.py measure chip.gds --top CHIP --layers 10 --lang en
# 独立 cell 定义 / Independent cell definitions
python scripts/gds_area.py measure chip.gds --cells RING IDT --lang zh
# cell 内指定图层 / Selected layers within cells
python scripts/gds_area.py measure chip.gds --cells RING IDT --layers 1/0 3/0 --lang en
# 实例与机器可读报告 / Instances and machine-readable reports
python scripts/gds_area.py measure chip.gds --scope instances --top CHIP --cells IDT --layers 1/0 --lang zh --json area.json --csv area.csv
# Excel 用的双语 CSV / Bilingual CSV for human readers in Excel
python scripts/gds_area.py measure chip.gds --top CHIP --layers 1/0 --lang bilingual --csv area-bilingual.csv --localized-csv
# 中文／英文帮助 / Chinese or English help
python scripts/gds_area.py measure --lang zh --help
python scripts/gds_area.py --lang en measure --help
```

## 依赖与故障处理 / Dependencies and failures

- 自动检查 Python 和 KLayout；从官方来源取得 uv，在隔离环境安装 `klayout==0.30.12`。没有兼容 Python 时获取独立 Python 3.12，无需 GUI、pip 或 GPU。
- Check Python and KLayout; obtain uv from its official source and install `klayout==0.30.12` in isolation. Obtain managed Python 3.12 if needed; no GUI, pip or GPU is required.
- 已授权常规自动下载，不为缺包重复询问；仍遵守宿主网络、写权限与审批限制。不得绕过拒绝，不得在失败后声称成功。
- Routine automatic downloads are authorized; do not ask again for missing dependencies. Respect host network, filesystem and approval limits without bypassing denials or claiming success after failure.
- 受限环境用 `GDS_AREA_CACHE` 指向获准目录；用 `GDS_AREA_MANAGED_PYTHON=1` 请求独立 Python。详见 [运行环境 / Runtime](references/runtime.md)。
- Point `GDS_AREA_CACHE` at an approved directory; use `GDS_AREA_MANAGED_PYTHON=1` to request managed Python. See [运行环境 / Runtime](references/runtime.md).
- 缓存就绪可离线运行。安装失败报告实际诊断，不改用未说明的算法。除非明确要求 `--force`，不覆盖已有报告；始终保护输入版图。
- Reuse ready caches offline. Report installation diagnostics without changing the area algorithm. Refuse report overwrite unless explicitly authorized with `--force`; always protect input layouts.
- 大阵列可能消耗较多内存，先缩小 cell／图层范围。内存不足时报错，不取消去重或采用抽样。
- Large arrays may need substantial memory; narrow cell/layer selections first. Report memory failures rather than disabling deduplication or sampling.

## 方法与验证 / Method and verification

解释坐标、DBU 或精度时阅读 [计算方法 / Method](references/method.md)。先应用变换、集中插入 Region，再合并并求面积。

Read [计算方法 / Method](references/method.md) for coordinates, DBU and precision. Transform geometry, collect it in a Region, then merge and measure.

修改脚本或检查新环境时运行 `python scripts/self_test.py`，只报告实际执行的验证。本 skill 计算二维面积，不推断材料体积或工艺侧壁面积。

Run `python scripts/self_test.py` after script changes or when checking new environments; report only checks actually performed. Measure 2D area, not material volume or sidewall area.
