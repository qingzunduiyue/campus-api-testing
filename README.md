# 教学管理系统与接口测试

[![回归测试](https://github.com/qingzunduiyue/campus-api-testing/actions/workflows/tests.yml/badge.svg)](https://github.com/qingzunduiyue/campus-api-testing/actions/workflows/tests.yml)

仓库包含完整的 FastAPI + Tortoise ORM 后端、Vue 3 + Element Plus 前端，以及接口自动化、缺陷复现和回归测试。可以先启动系统操作，再阅读测试如何验证相同业务。

## 启动完整项目

需要 Python 3.12、Node.js 22。下载或克隆仓库，在仓库根目录打开终端。

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r project/backend/requirements.txt
python run_project.py
```

macOS / Linux 将激活命令换成 `source .venv/bin/activate`，其余命令相同。

另开一个终端，在仓库根目录运行前端：

```text
npm --prefix project/frontend ci --ignore-scripts --no-audit --no-fund
npm --prefix project/frontend run dev
```

打开 http://127.0.0.1:5174 ，使用以下公开演示账号登录：

```text
账号：demo_admin
密码：Demo12345!
角色：管理员
```

后端接口文档为 http://127.0.0.1:9090/docs 。首次启动会自动创建 SQLite 数据库、演示管理员、示例专业与班级。数据保存在 `project/backend/data/`，后续启动继续使用，不会清空已有记录。不需要提供本机 MySQL 密码。

可操作功能包括登录、注册、修改密码、管理员管理、专业管理、班级与专业关联、查询分页、个人资料、图片 / 文本上传下载。当前版本没有学生档案模块，因此项目名称使用“教学管理系统”。

原教学项目采用本地账号与管理接口，当前版本用于本机学习和演示，尚未实现生产环境的登录令牌、接口权限控制及密码哈希。

## 可选 MySQL

默认 SQLite 已足够运行页面和自动化测试。若要切换 MySQL，先创建一个专用空数据库，然后安装：

```text
python -m pip install -r project/backend/requirements-mysql.txt
```

将 `project/backend/.env.example` 复制为同目录下 `.env`，填写自己的 `DATABASE_URL=mysql://...` 后重启后端。数据库初始化会创建缺少的数据表；该演示启动器不负责已有生产库的迁移。MySQL 路径尚未实连验证。

## 运行测试和构建

激活上面的 Python 环境，在仓库根目录运行：

```text
python -B run_all.py
python -B test_project.py
npm --prefix project/frontend run build
```

`run_all.py` 对原始与修复快照执行相同的 9 项用例：baseline 7 项通过、2 项已知断言失败，fixed 9 项通过。它严格核对失败名称，不能忽略所有错误来制造通过结果。

`test_project.py` 会启动实际后端，通过本地 HTTP 执行 5 项集成检查，覆盖首次启动与登录、注册和改密、专业与班级的增改查删、文件上传下载及参数校验。每次使用新的临时数据库和文件目录，不接触日常演示数据。`test_server.py` 仅用于这些检查中的进程启停，正常启动请用 `run_project.py`。

GitHub Actions 在 Windows 和 Ubuntu 上安装后端与前端依赖，执行上述两组测试，并构建完整 Vue 页面。云端运行结果以本页徽章和 Actions 日志为准。

## 目录与阅读顺序

| 目录 / 文件 | 内容 |
| --- | --- |
| `project/backend/` | 完整后端、环境配置示例、SQLite 初始化和演示数据 |
| `project/frontend/` | 完整前端源码、依赖锁定文件、开发代理配置 |
| `run_project.py` | 从仓库根目录启动后端 |
| `test_project.py` | 实际应用启动与 HTTP 集成检查 |
| `baseline/`、`fixed/` | 用于复现原问题和最小修复的冻结快照 |
| `test_student_system.py` | 9 项隔离接口与数据库断言 |
| `fixes.diff` | 已复现问题的修复差异 |
| `docs/TESTING.md` | 原测试设计、结果与覆盖边界 |

可运行项目采用已修复接口，并补充了启动配置、注册接口、空头像字段兼容及文件上传处理。冻结快照保持原有复现意义；之后的可运行性修正不会伪装成原来已统计的两项缺陷。

## 来源

业务界面和接口沿用既有 FastAPI + Vue 教学项目。界面内保留原作者“程序员青戈”的署名及[教学主页](https://space.bilibili.com/402779077)。本仓库新增内容为测试实践、缺陷修复、可移植启动配置、演示数据和持续集成；不声明整套业务系统为独立原创，也没有另行授予上游代码许可证。

测试与可运行版本整理于 2026 年 10 月。项目不包含原数据库、私人上传文件或真实用户数据。
