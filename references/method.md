# 面积计算方法 / Area measurement method

## KLayout 方法 / KLayout method

采用用户指定的 [Area of objects](https://www.klayout.de/forum/discussion/25/area-of-objects) 中的 Region 合并方法：先应用变换，集中插入 Region，最后合并并求面积。同一 layer/datatype 内重叠只计一次。采用 Python 数据库 API，无需 GUI 选择状态，仅提供这一面积口径。

Follow the Region union approach in [Area of objects](https://www.klayout.de/forum/discussion/25/area-of-objects): transform geometry, collect it in a Region, then merge and measure. Count overlaps once within each layer/datatype. Use the Python database API without GUI selection state; this is the only area policy.

计算公式 / Formula:

```python
A_union_um2 = Region(transformed_polygons).merged().area() * layout.dbu**2
```

`dbu` 单位为 µm／数据库坐标单位，所以面积换算必须平方。递归迭代器提供父层级累积变换和阵列位移；KLayout 处理 path 多边形化与孔洞。

`dbu` is measured in µm per database coordinate unit, so area conversion squares it. The recursive iterator supplies accumulated hierarchy transforms and array offsets. KLayout handles path polygonization and holes.

## 选择与合计 / Selection and totals

`definitions` 在每个 cell 的独立坐标系内计算一次。`instances` 选取参考 cell 中的指定实例，保留真实放置变换；参考 cell 本身也可选中。迭代器选择标记防止同时选中父子 cell 时重复遍历同一实例。

`definitions` measures each cell once in its own coordinates. `instances` selects occurrences below a reference cell, preserving placement transforms; the reference cell can itself be selected. Iterator selection flags avoid visiting an occurrence twice when its ancestor and descendant are both selected.

| 示例 / Example | 结果 / Result |
| --- | --- |
| 同层两个 10 × 10 µm 方块，沿 x 相隔 5 µm / Two 10 × 10 µm squares on one layer, offset by 5 µm in x | 去重面积 / Union area: 150 µm² |
| 相同 10 × 10 µm 方块分别在两个图层，投影重合 / Identical 10 × 10 µm squares on separate layers, overlapping in projection | 每层 / Each layer: 100 µm²；合计 / Total: 200 µm² |

`cell_total` 与 `combined_total` 将各 layer/datatype 去重面积相加。逻辑图层按 layer/datatype 对标识，各 datatype 分别统计，不跨层合并。独立 cell 定义之间不假定放置关系；`definitions_total` 仅为各定义内部去重面积之和。

`cell_total` and `combined_total` sum the deduplicated areas of separate layer/datatype pairs. Each pair is a logical layer; datatypes remain separate and different layers are never merged. Assume no placement relationships between independent definitions; `definitions_total` only sums areas deduplicated within each definition.

## 精度与限制 / Precision and limits

- 在整数 DBU 网格上求并集；非正交旋转或不保持网格的缩放可能使顶点取整。
  Compute unions on the integer DBU grid. Non-orthogonal rotations or scales that do not preserve it may round vertices.
- 原始多边形离散化、孔洞和 path 多边形化影响精度；不报告超出数据精度的有效数字。
  Original polygon discretization, holes and path polygonization affect precision. Do not imply more significant figures than supported.
- TEXT 不计面积，多边形文字计入；零面积对象贡献零面积。
  Exclude TEXT objects, include polygonal text, and let zero-area geometry contribute zero.
- 所选实例展开几何，内存随实例数量增长；没有 DRC 分块或多线程。换用算法前验证同一范围及边界处理。
  Selected occurrences are expanded, so memory grows with instance count. DRC tiling and multithreading are not implemented. Validate equivalent scope and boundary handling before substituting algorithms.
- 语言只改变面向人的文字，不改变几何、面积、单位、实际名称和 JSON／默认 CSV 的技术字段名。
  Language changes presentation only, never geometry, area, units, actual names or technical keys in JSON/default CSV.

## 官方参考 / Official references

- [用户指定讨论 / User-specified discussion](https://www.klayout.de/forum/discussion/25/area-of-objects)
- [Region API](https://www.klayout.de/doc/code/class_Region.html)
- [RecursiveShapeIterator API](https://www.klayout.de/doc/code/class_RecursiveShapeIterator.html)
- [KLayout Python package](https://www.klayout.org/klayout-pypi/)
- [Agent Skills 规范 / Agent Skills specification](https://agentskills.io/specification)：使用 `SKILL.md`、`scripts` 和 `references`；`agents/openai.yaml` 为可选客户端元数据。 / Use `SKILL.md`, `scripts` and `references`; `agents/openai.yaml` is optional client metadata.
