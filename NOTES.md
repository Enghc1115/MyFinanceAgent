# 项目注意事项

## Python 环境

### 系统 Python 与项目 Python

- **系统自带 Python**：macOS 自带 Python 3.9（`/usr/bin/python3`），属于系统组件，**不要升级或替换**，否则可能影响系统稳定性。
- **Homebrew 安装的 Python 3.12**：位于 `/usr/local/opt/python@3.12/bin/python3.12`，是供项目使用的独立版本。
- **项目虚拟环境**：`.venv/` 目录基于 Homebrew 的 Python 3.12 创建，所有项目依赖（akshare、pandas、requests 等）安装在其中。

### 如何运行脚本

**正确方式** — 使用虚拟环境的 Python：

```bash
.venv/bin/python your_script.py
```

或先激活虚拟环境：

```bash
source .venv/bin/activate
python your_script.py
```

**错误方式** — 使用系统 Python 3.9：

```bash
python3 your_script.py    # 系统 python3 是 3.9，缺少依赖且无法安装 akshare
```

### 安装/更新依赖

```bash
.venv/bin/pip install -r requirements.txt
```

### 让终端默认用 Python 3.12（可选）

如果希望 `python3` 命令默认指向 Homebrew 的 Python 3.12，可以加到 PATH 中：

```bash
echo 'export PATH="/usr/local/opt/python@3.12/bin:$PATH"' >> ~/.zshrc
```

但项目脚本仍建议通过 `.venv/` 运行，保持环境隔离。

---

## 数据文件

- CSV 数据统一存放在 `data/` 目录下
- 通过 `git push` 同步到 GitHub

## 依赖库版本（2026-05-09）

| 库 | 版本 |
|---|---|
| akshare | 1.18.60 |
| pandas | 3.0.2 |
| requests | 2.33.1 |
