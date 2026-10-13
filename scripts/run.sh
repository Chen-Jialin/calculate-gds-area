#!/bin/sh
set -eu
gds_language=${GDS_AREA_LANG:-bilingual}
gds_expect_language=0
for gds_argument in "$@"; do
    if [ "$gds_expect_language" = 1 ]; then
        gds_language=$gds_argument
        gds_expect_language=0
    elif [ "$gds_argument" = --lang ]; then
        gds_expect_language=1
    else
        case "$gds_argument" in --lang=*) gds_language=${gds_argument#--lang=} ;; esac
    fi
done
gds_message() {
    case "$gds_language" in
        en) printf '%s\n' "$1" ;;
        zh) printf '%s\n' "$2" ;;
        *) printf '%s / %s\n' "$2" "$1" ;;
    esac
}
case "$gds_language" in
    en|zh|bilingual) ;;
    *) printf '%s\n' '无效语言；请选择 en、zh 或 bilingual。 / Invalid language; choose en, zh or bilingual.' >&2; exit 2 ;;
esac
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
entrypoint=gds_area.py
if [ "${GDS_AREA_ENTRYPOINT:-}" = self_test.py ]; then entrypoint=self_test.py; fi
if [ "${GDS_AREA_MANAGED_PYTHON:-0}" != "1" ]; then
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] < (3,15) else 1)' >/dev/null 2>&1; then
            exec "$candidate" -X utf8 "$script_dir/$entrypoint" "$@"
        fi
    done
fi
cache_dir=${GDS_AREA_CACHE:-${XDG_CACHE_HOME:-$HOME/.cache}/gds-area}
mkdir -p "$cache_dir"
uv_exe="$cache_dir/uv/uv"
if command -v uv >/dev/null 2>&1; then
    uv_exe=$(command -v uv)
elif [ ! -x "$uv_exe" ]; then
    gds_message 'Downloading uv from astral.sh to install an isolated Python runtime...' '正在从 astral.sh 下载 uv，以安装隔离的 Python 运行环境……' >&2
    installer="$cache_dir/uv-install.sh"
    if command -v curl >/dev/null 2>&1; then
        curl --proto '=https' --tlsv1.2 -LsSf https://astral.sh/uv/install.sh -o "$installer"
    elif command -v wget >/dev/null 2>&1; then
        wget -qO "$installer" https://astral.sh/uv/install.sh
    else
        gds_message 'ERROR: Need curl or wget to download uv, or provide Python 3.10-3.14.' '错误：下载 uv 需要 curl 或 wget；也可以提供 Python 3.10–3.14。' >&2
        exit 2
    fi
    UV_INSTALL_DIR="$cache_dir/uv" UV_NO_MODIFY_PATH=1 sh "$installer" >&2
fi
export UV_PYTHON_INSTALL_DIR="$cache_dir/python"
export UV_CACHE_DIR="$cache_dir/uv-cache"
if [ -n "${GDS_AREA_UV_PYTHON:-}" ]; then
    exec "$uv_exe" run --no-project --python "$GDS_AREA_UV_PYTHON" --default-index https://pypi.org/simple --with klayout==0.30.12 -- python -X utf8 "$script_dir/$entrypoint" "$@"
fi
exec "$uv_exe" run --no-project --managed-python --python 3.12 --default-index https://pypi.org/simple --with klayout==0.30.12 -- python -X utf8 "$script_dir/$entrypoint" "$@"
