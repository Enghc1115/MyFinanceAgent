#!/bin/bash
# run_daily.sh - A 股数据定时抓取调度脚本
#
# 用法:
#   ./run_daily.sh morning   # 早盘 (10:00)，仅打印
#   ./run_daily.sh noon      # 午盘 (11:30)，打印 + 保存 CSV + 板块快照
#   ./run_daily.sh close     # 收盘 (15:15)，打印 + 保存 CSV + 板块快照
#
# 功能:
#   - 自动检测休市（周末 / 节假日），休市时直接退出
#   - 按不同时段执行抓取逻辑
#   - 保存行情 CSV + 板块资金流向快照（供异动分析使用）
#   - 收盘后运行 generate_report.py 生成日度简报

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
FETCH_SCRIPT="$PROJECT_DIR/scripts/get_market_data.py"

# ---------- 参数校验 ----------

SLOT="${1:-}"
if [[ ! "$SLOT" =~ ^(morning|noon|close)$ ]]; then
    echo "用法: $0 {morning|noon|close}"
    exit 1
fi

SLOT_LABEL=$(echo "$SLOT" | tr '[:lower:]' '[:upper:]')

if [ ! -f "$VENV_PYTHON" ]; then
    echo "[错误] 未找到虚拟环境: $VENV_PYTHON"
    echo "请先执行: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi

# ---------- 休市检测 ----------

is_weekend() {
    local dow
    dow=$(date +%u)
    [ "$dow" -ge 6 ]
}

is_trading_day() {
    local today
    today=$(date +%Y%m%d)

    local market_date
    # 使用新浪指数实时接口获取市场日期，比 stock_sse_summary 更及时准确
    market_date=$("$VENV_PYTHON" -c "
import requests, re
try:
    url = 'https://hq.sinajs.cn/list=sh000001'
    headers = {'Referer': 'https://finance.sina.com.cn'}
    resp = requests.get(url, headers=headers, timeout=5)
    match = re.search(r'(\d{4}/\d{2}/\d{2})', resp.text)
    if match:
        print(match.group(1).replace('/', ''))
    else:
        print('')
except Exception:
    print('')
" 2>/dev/null || echo "")

    # API 失败时放行（后续抓取自己报错）
    [ -z "$market_date" ] || [ "$market_date" = "$today" ]
}

# ---------- 主流程 ----------

echo "[$SLOT_LABEL] $(date '+%Y-%m-%d %H:%M') — 开始执行"

if is_weekend; then
    echo "[$SLOT_LABEL] 今日休市（周末），跳过执行"
    exit 0
fi

if ! is_trading_day; then
    echo "[$SLOT_LABEL] 今日休市（非交易日），跳过执行"
    exit 0
fi

echo "[$SLOT_LABEL] 今日为交易日，继续..."

# ---------- 分时段执行 ----------

REPORT_SCRIPT="$PROJECT_DIR/scripts/generate_report.py"
PREP_DEEP_SCRIPT="$PROJECT_DIR/scripts/prep_deep_data.py"
DEEP_REPORT_SCRIPT="$PROJECT_DIR/scripts/generate_deep_report.py"
SLIDES_SCRIPT="$PROJECT_DIR/scripts/report_to_slides.py"
ARCHIVER_SCRIPT="$PROJECT_DIR/scripts/data_archiver.py"

case "$SLOT" in
    morning)
        "$VENV_PYTHON" "$FETCH_SCRIPT" --mode morning
        ;;
    noon)
        "$VENV_PYTHON" "$FETCH_SCRIPT" --mode noon --save
        ;;
    close)
        "$VENV_PYTHON" "$FETCH_SCRIPT" --mode close --save && \
        echo "[$SLOT_LABEL] 正在准备深度数据..." && \
        ("$VENV_PYTHON" "$PREP_DEEP_SCRIPT" || echo "[$SLOT_LABEL] 深度数据准备失败（不影响后续）") && \
        echo "[$SLOT_LABEL] 正在生成日度简报..." && \
        "$VENV_PYTHON" "$REPORT_SCRIPT" && \
        echo "[$SLOT_LABEL] 正在生成深度报告..." && \
        "$VENV_PYTHON" "$DEEP_REPORT_SCRIPT" --date $(date +%Y-%m-%d) || \
        echo "[$SLOT_LABEL] 深度报告生成失败（不影响日度简报）" && \
        echo "[$SLOT_LABEL] 正在生成HTML幻灯片..." && \
        "$VENV_PYTHON" "$SLIDES_SCRIPT" $(date +%Y-%m-%d) || \
        echo "[$SLOT_LABEL] 幻灯片生成失败" && \
        echo "[$SLOT_LABEL] 正在检查月度归档..." && \
        "$VENV_PYTHON" "$ARCHIVER_SCRIPT" || true
        ;;
esac

EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo "[$SLOT_LABEL] 执行完毕"
else
    echo "[$SLOT_LABEL] 执行失败（exit code: $EXIT_CODE）"
fi
exit $EXIT_CODE
