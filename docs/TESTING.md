# 教学管理接口测试与缺陷回归

[![回归测试](https://github.com/qingzunduiyue/campus-api-testing/actions/workflows/tests.yml/badge.svg)](https://github.com/qingzunduiyue/campus-api-testing/actions/workflows/tests.yml)

这是一个基于既有教学管理项目的测试练习包，演示如何从接口需求设计用例、核对数据库结果、复现缺陷，并验证最小修复。

本地已执行同一组 9 项接口测试：原始快照 7 项通过、2 项业务断言失败；修复副本 9 项全部通过，两次运行均无执行错误。两项基线失败被保留下来用于复现，因此 `run_all.py` 会核对失败名称，并在结果符合预期时返回成功。

测试与修复实践于 2026 年 10 月补充完成；业务源码沿用既有项目，新增成果为测试用例、隔离执行器、缺陷修复与回归材料。

## 快速运行

使用 Python 3.12 创建虚拟环境，在本目录执行：

```text
python -m venv .venv
```

Windows PowerShell 激活环境：

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS 或 Linux 激活环境：

```sh
source .venv/bin/activate
```

安装锁定依赖并运行：

```text
python -m pip install -r requirements-test.txt
python -B run_all.py
```

不需要 MySQL、数据库账号、API Key 或 HTTP 服务端口。安装依赖需要包源访问；测试执行本身不访问网络。

预期摘要：

```text
baseline {"tests_run": 9, "passed": 7, "assertion_failures": 2, "execution_errors": 0}
fixed {"tests_run": 9, "passed": 9, "assertion_failures": 0, "execution_errors": 0}
verification_passed True
```

逐项结果写入 `results/`。`examples/` 保存便携包本地实跑的脱敏示例，不包含本机绝对路径。

## 测试结构

- `baseline/`：现有模型、路由、异常处理的必要源码快照。
- `fixed/`：只修复两项已复现问题的独立副本。
- `test_student_system.py`：标准库 unittest 与进程内 ASGI 请求调用器。
- `run_all.py`：分别运行两份快照，检查基线恰好出现已知失败，并检查修复副本全部通过。
- `requirements-test.txt`：本地已验证环境的直接和传递依赖版本。
- `fixes.diff`：两项最小修复的差异。
- `provenance.json`：必要源码文件的相对路径与 SHA-256，不含原始本机路径。
- `.github/workflows/tests.yml`：GitHub Actions 配置，在 Windows 和 Ubuntu 上执行同一套回归。

## 9 项测试覆盖

| 测试内容 | 检查依据 |
| --- | --- |
| 正常创建与查询专业 | 接口数据与临时数据库记录一致 |
| 重复创建专业 | 返回重复错误，不增加记录 |
| 保留自身编号修改专业名称 | 应更新当前记录 |
| 修改为另一记录的专业编号 | 应保留重复限制 |
| 新建班级与专业关联 | `majorId` 写入正确，分页返回专业 ID 和名称 |
| 非整数班级 ID | 返回统一参数错误 |
| 班级修改缺少 ID | 拒绝更新 |
| 不存在的管理员登录 | 拒绝登录 |
| 不支持的角色登录 | 不能跳过账号检查得到成功 |

应用使用 HTTP 200 加业务 `code` 表示成功或失败，所以测试区分 HTTP 状态与业务码，不能只看请求是否返回 200。

## 两项缺陷及最小修复

**专业更新误判自身重复。** 新建专业后，携带相同 ID 和编号，只改名称。基线返回“专业代码重复”，名称没有更新。更新查重没有排除自身是根因；修复仅在查重记录属于其他 ID 时拒绝。回归同时检查另一记录编号仍不能被占用。

**不支持的登录角色跳过账号检查。** 在空数据库中使用不存在的合成账户，将角色设为 `QA-UNSUPPORTED-ROLE`。基线返回登录成功业务码，因为只有“管理员”分支执行了账号检查。修复在入口拒绝不支持角色；对照测试确认不存在的管理员仍会被拒绝。这不等于已验证完整认证授权或生产安全。

## 隔离方式与局限

每项测试使用新的 SQLite 内存数据库，结束后关闭连接。调用器在同一进程内执行 ASGI 请求；测试期间阻止网络连接。快照不含原来的 `main.py`、`settings.py`、上传路由、数据库文件或用户图片，导入原应用配置也被显式阻止。

SQLite 结果不证明 MySQL 特有约束、排序规则及并发行为正确。此处未执行浏览器、真实部署、CORS、上传下载、性能或负载测试，也没有使用 pytest、HTTPX、JMeter 或 Jenkins。

本地验证环境是 Windows、Python 3.12.4。GitHub Actions 已于 2026 年 10 月 22 日在 Python 3.12 的 Windows 和 Ubuntu 上从空环境安装依赖，并完成基线复现及修复回归。详见[云端执行记录](https://github.com/qingzunduiyue/campus-api-testing/actions/runs/39786151537)。

## 源码来源与发布状态

业务快照采用 FastAPI 和 Tortoise ORM，当前覆盖管理员、专业和班级模块。

业务代码基于既有 FastAPI 教学管理项目，本次新增内容为接口用例、隔离执行器、缺陷复现与回归材料。仓库不声明整个业务系统为独立开发；上游来源链接待补，目前未设置开源许可证。项目已发布；可通过上方运行命令复现测试，并通过 Actions 查看云端验证结果。

## 建议阅读顺序

先看 `test_major_create_query_and_database_consistency` 理解“请求、响应、数据库断言”；再看 `test_major_update_same_code_changes_name` 与 `fixes.diff` 理解复现和修复；最后运行整套回归，对照 `results/verification.json` 检查结论是否成立。
