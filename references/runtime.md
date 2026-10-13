# 自动依赖与运行环境 / Automatic dependencies and runtime

支持常见 Windows、Linux 和 macOS 环境，目标平台需有兼容 KLayout wheel。测试依赖为 `klayout==0.30.12`。启动器优先复用 Python 3.10–3.14，缺失时用 uv 获取独立 Python 3.12；缺包时构建隔离环境，不要求 pip／ensurepip。直接运行 Python 脚本要求 Python 已经可用。

Support common Windows, Linux and macOS environments with a compatible KLayout wheel. The tested dependency is `klayout==0.30.12`. Reuse Python 3.10–3.14 or obtain managed Python 3.12 with uv. Build isolated environments for missing packages without pip/ensurepip. Direct Python invocation requires Python already to be available.

默认无需管理员权限，不修改全局 Python 包。Windows 缓存为 `%LOCALAPPDATA%/gds-area`；Linux/macOS 为 `${XDG_CACHE_HOME:-~/.cache}/gds-area`。用 `GDS_AREA_CACHE` 指向获准的可写目录。缓存就绪后可离线复用。

Administrator access is not normally needed; global Python packages are not modified. Cache under `%LOCALAPPDATA%/gds-area` on Windows or `${XDG_CACHE_HOME:-~/.cache}/gds-area` on Linux/macOS. Set `GDS_AREA_CACHE` to an approved writable directory. Ready caches can be reused offline.

## 语言与编码 / Language and encoding

| 选项／变量 / Option or variable | 作用 / Effect |
| --- | --- |
| `--lang zh` | 中文帮助、输出和程序错误 / Chinese help, output and application errors |
| `--lang en` | 英文帮助、输出和程序错误 / English help, output and application errors |
| `--lang bilingual` | 中英文一起显示，默认 / Chinese and English together; default |
| `GDS_AREA_LANG` | 没有 `--lang` 时的默认语言 / Default language when `--lang` is absent |
| `--localized-csv` | 翻译 CSV 表头及程序生成的行标签 / Translate CSV headers and generated row labels |

`--lang` 可放在子命令前后，也支持 `--lang=en`，优先于环境变量。JSON 和默认 CSV 保留稳定字段名及枚举值；JSON 的 `labels.fields` / `labels.values` 提供翻译。合计、精度说明及警告按选定语言显示。`inspect` JSON 同样包含语言和翻译标签。

Put `--lang` before or after a subcommand, or use `--lang=en`; it overrides the environment variable. JSON and default CSV retain stable keys and enum values, with translations in `labels.fields` / `labels.values`. Localize aggregation, precision and warning descriptions. The `inspect` JSON also contains language and translated labels.

文本资源及 JSON 使用 UTF-8；CSV 使用 UTF-8 BOM，方便 Excel 识别。Windows 启动器以 UTF-8 BOM 保存，使 Windows PowerShell 5.1 正确读取中文，并在运行期间使用 UTF-8 控制台输出。不翻译路径或版图的实际名称。

Use UTF-8 for text resources and JSON, and UTF-8 BOM for CSV so Excel can detect its encoding. Save the Windows launcher with UTF-8 BOM for Chinese text in Windows PowerShell 5.1; use UTF-8 console output while running. Never translate paths or actual layout names.

程序自己的安装提示支持三种语言；uv、Python、KLayout 和系统的原始诊断保留原文，便于排查，不声称第三方日志全部翻译。

Localize application-owned bootstrap messages in all three modes. Preserve original uv, Python, KLayout and system diagnostics for troubleshooting; do not claim third-party logs are fully translated.

## 示例 / Examples

Windows PowerShell:

```powershell
$env:GDS_AREA_CACHE = 'C:/work/gds-area-cache'
$env:GDS_AREA_LANG = 'zh'
& ./scripts/run.ps1 inspect 'C:/data/chip.gds'
# 命令行优先，下面使用英文 / CLI takes precedence: English below
& ./scripts/run.ps1 measure 'C:/data/chip.gds' --top CHIP --layers 1/0 --lang en
```

Linux / macOS:

```sh
GDS_AREA_CACHE=/work/gds-area-cache GDS_AREA_LANG=en sh ./scripts/run.sh inspect /data/chip.gds
sh ./scripts/run.sh measure /data/chip.gds --top CHIP --layers 1/0 --lang bilingual
```

报告示例 / Report examples:

```sh
# 机器可读 JSON/CSV，中文说明 / Machine-readable JSON/CSV with Chinese descriptions
python scripts/gds_area.py measure chip.gds --top CHIP --lang zh --json area.json --csv area.csv
# 面向人的双语 CSV / Bilingual CSV for human readers
python scripts/gds_area.py measure chip.gds --top CHIP --lang bilingual --csv area-bilingual.csv --localized-csv
```

## 环境修复与来源 / Recovery and sources

系统 Python 没有兼容 wheel 或环境损坏时设置 `GDS_AREA_MANAGED_PYTHON=1` 再运行启动器。不要删除现有用户环境，遵守沙箱与执行策略，不绕过权限拒绝。

Set `GDS_AREA_MANAGED_PYTHON=1` and run the launcher when system Python lacks a compatible wheel or its environment is damaged. Do not delete existing environments; respect the sandbox and execution policy without bypassing denials.

KLayout 从 `https://pypi.org/simple` 获取；uv 安装器来自 `https://astral.sh/uv/install.ps1` 或 `https://astral.sh/uv/install.sh`，由 uv 获取托管 CPython。保持 TLS 验证。POSIX 启动器需要 curl 或 wget；两者都缺失时由宿主在已有权限内通过官方包管理器安装，无法执行则明确报告。

Obtain KLayout from `https://pypi.org/simple` and uv from `https://astral.sh/uv/install.ps1` or `https://astral.sh/uv/install.sh`; uv obtains managed CPython. Keep TLS verification enabled. POSIX launchers need curl or wget; if neither exists, use an official package manager within existing authorization or report that installation cannot proceed.

安装日志写入 stderr，结果写入 stdout。`python scripts/gds_area.py measure --lang en --help` 查看英文帮助，`--lang zh` 查看中文帮助。报告包含引擎版本、DBU、范围和面积口径。

Send installation logs to stderr and results to stdout. Use `python scripts/gds_area.py measure --lang en --help` for English help or `--lang zh` for Chinese help. Reports include engine version, DBU, scope and area policy.

官方资料 / Official documentation: [uv installation](https://docs.astral.sh/uv/getting-started/installation/), [uv Python management](https://docs.astral.sh/uv/guides/install-python/).
