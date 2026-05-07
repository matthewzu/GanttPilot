# GanttPilot

<div align="center">

![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.6+-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)
![License](https://img.shields.io/badge/license-GPL--3.0-orange.svg)

**Collaborative Project Manager with Gantt Chart | 基于甘特图的协作式项目管理器**

[English](#english) | [中文](#中文)

</div>

---

## English

### What is GanttPilot?

GanttPilot is a lightweight, Git-based collaborative project manager. Each project lives in its own Git repository, so your team can work together through familiar Git workflows — branches, push, pull, and PRs.

It covers the full project lifecycle: define requirements, break them into tasks, plan milestones, track progress on a Gantt chart, log work hours, and generate reports — all from a single desktop app.

### Quick Start

#### Download (Recommended)

Grab the latest release — no Python needed:

👉 [Download Latest Version](https://github.com/matthewzu/GanttPilot/releases/latest)

| Platform | File |
| --- | --- |
| Windows | `GanttPilot.exe` |
| macOS | `GanttPilot.dmg` |
| Linux | `GanttPilot` |

Double-click to launch. For CLI mode: `GanttPilot --cli`

#### Run from Source

```bash
git clone https://github.com/matthewzu/GanttPilot.git
cd GanttPilot
python main.py              # GUI (default)
python main.py --cli        # CLI mode
python main.py --lang en    # English UI
python main.py --version    # Show version
```

### How It Works

#### Project Structure

Every project follows this hierarchy:

```
Project
  ├── Requirement Analysis          ← Define what to build
  │     └── Requirement               (category, subject, description)
  │           └── Task                 (subject, effort in person-days)
  └── Plan Execution                ← Plan how to build it
        └── Milestone                  (deadline, description, color)
              └── Plan                 (executor, date range, linked task, progress)
                    └── Activity       (executor, date, hours, tag, description, content)
```

- **Requirements & Tasks** define *what* needs to be done and the estimated effort
- **Milestones & Plans** define *when* and *who* will do it
- **Activities** record *actual work* done — hours, content, and tags
- **Linked Tasks** connect plans back to requirements, creating a full traceability chain

#### Typical Workflow

1. **Create a project** — right-click empty area → Add Project (or clone from a remote repo)
2. **Define requirements** — expand "Requirement Analysis", add requirements and break them into tasks
3. **Set up milestones** — expand "Plan Execution", create milestones with deadlines
4. **Create plans** — under each milestone, add plans with executor, date range, and optionally link to a task
5. **Log activities** — under each plan, record daily work with hours and content
6. **Track progress** — view the Gantt chart, check the Requirement Tracking tab, set plan progress (0-100%)
7. **Generate reports** — right-click project → Generate Report (Markdown with embedded Gantt chart PNG)
8. **Collaborate** — push/pull via Git, each team member works on their private branch, merge via PR

### Interface Guide

#### Main Window

The main window has two areas:

- **Left panel**: Project tree — all your projects, requirements, milestones, plans, and activities in a tree view
- **Right panel**: Tabbed view with Gantt Chart, Time Statistics, Requirement Tracking, and History

#### Toolbar

The toolbar at the top provides quick access to common actions. Buttons are context-sensitive — they enable/disable based on what you've selected in the tree:

| Button | Action | Shortcut |
| --- | --- | --- |
| Add | Add child node (requirement/task/milestone/plan/activity) | `Ctrl+N` |
| Edit | Edit selected node | `F2` |
| Delete | Delete selected node | `Delete` |
| Copy | Copy node to clipboard | `Ctrl+C` |
| Paste | Paste from clipboard | `Ctrl+V` |
| Duplicate | Clone node with all children | `Ctrl+D` |
| Move Up | Reorder node up among siblings | `Alt+Up` |
| Move Down | Reorder node down among siblings | `Alt+Down` |
| ⟳ | Check for updates | — |

Other shortcuts: `Ctrl+Z` Undo, `Ctrl+Y` Redo, `Ctrl+S` Push, `F5` Refresh. All shortcuts are customizable in Config.

#### Right-Click Menus

Right-click is the primary way to access all operations. What you see depends on what you clicked:

| Right-click on | Available actions |
| --- | --- |
| Empty area | Add Project, Load Example, Push, Pull, Refresh |
| Project | Edit, Git Config, Copy, Duplicate, Generate Report, Push, Pull, Refresh, Delete |
| Requirement Analysis | Add Requirement, Paste |
| Requirement | Add Task, Edit, Copy, Paste, Duplicate, Move Up/Down, Delete |
| Task | Edit, Copy, Duplicate, Move Up/Down, Delete |
| Plan Execution | Add Milestone, Paste |
| Milestone | Add Plan, Edit, Color, Copy, Paste, Duplicate, Move Up/Down, Delete |
| Plan | Add Activity, Edit, Color, Copy, Paste, Duplicate, Finish/Reopen, Set Progress, Move Up/Down, Delete |
| Activity | Edit, Copy, Duplicate, Delete |

#### Gantt Chart Tab

- Each plan is rendered as a horizontal bar, colored by executor
- Milestones appear as diamond markers at their deadline
- Progress is shown as a filled portion of each bar
- Skipped dates (holidays) are overlaid with red hatching
- Use 🔍+/- buttons to zoom in/out independently from the tree font size

#### Time Statistics Tab

Shows work hours logged across activities, with four view modes:

- **By Project** — total hours per executor across the whole project
- **By Milestone** — hours grouped by milestone
- **By Plan** — hours grouped by plan
- **By Tag** — hours grouped by activity tag

Each view shows group totals and per-executor percentage.

#### Requirement Tracking Tab

Displays the full traceability chain: Requirement → Task → Linked Plan → Progress → Actual Hours. This is where you verify that every requirement has been planned and track its completion status.

#### History Tab

Shows the Git commit log for the current project. You can:

- Switch branches via the dropdown (remote branches show a `[Remote]` prefix)
- View commit details: author, date, message, and diff
- Right-click a commit to **Reset to Here** (hard reset) or **Revert This Commit** (inverse commit)

### Creating a Project

Right-click empty area → Add Project. The dialog offers two modes via radio buttons:

#### Local Mode (default)

For personal, offline use. Only two fields:

- **Project Name** (required)
- **Description** (optional)

Data is stored at `~/.ganttpilot/data/{project_name}/`. You can add a remote later via right-click → Git Config.

#### Collaboration Mode

For team projects with Git sync. Shows all fields needed to set up collaboration in one step:

- **Project Name** and **Description** — same as local mode
- **Remote URL** — bare repository address (local path or server URL like `https://github.com/user/repo.git`)
- **Remote Main Branch** — defaults to `main`
- **Username** — Git repository username
- **Password/Token** — personal access token or password (masked)
- **Committer Name** — name for Git commits (auto-detected from system git config if empty)
- **Committer Email** — email for Git commits (auto-detected if empty)
- **Private Branch** — leave empty to auto-generate `priv_{committer_name}`

Each field has placeholder hints to guide you. The dialog auto-resizes when switching modes.

### Recording Work Hours

Activities support two ways to log hours (mutually exclusive):

- **Time Slots**: Enter start/end pairs like `0900/1200,1400/1700` — hours are auto-calculated
- **Direct Hours**: Enter a number like `3.5`

Both Chinese and English commas are accepted as separators.

### Skip Dates (Holidays & Workdays)

In plan creation/editing, the "Skip Dates" field controls which days are excluded from the plan duration:

- `20260501` — skip this date (e.g., a holiday)
- `-20260510` — un-skip this date (e.g., make a weekend day a workday)
- Enable "Skip Non-workdays" to automatically skip weekends

Skipped days appear as red hatched overlay on Gantt bars.

### Git Collaboration

Each project is an independent Git repo stored at `~/.ganttpilot/data/{project_name}/`.

#### How It Works

- Each user works on a private branch: `priv_{committer_name}`
- Push sends your private branch to the remote (right-click → Push, or `Ctrl+S`)
- Pull fetches the latest from remote and auto-updates local main branch (right-click → Pull)
- Changes are merged to the main branch via Pull Request on your Git platform
- After pull/sync, if main has new commits, a dialog asks whether to rebase your branch to latest main
- GanttPilot never pushes to the main branch — only your private branch is pushed

#### Setup

1. Right-click project → Git Config
2. Set Remote URL (must be a bare repo), committer name, and email
3. Git user info can be auto-detected from your system git config

#### Background Sync

- On startup, all projects auto-fetch from remote (pull only, no push)
- A periodic background check (default: every 5 minutes, configurable) detects remote updates

### Reports

Right-click a project → Generate Report. The Markdown report includes:

1. **Gantt Chart** — embedded PNG image (rendered locally, no external dependencies)
2. **Requirement Analysis** — requirements table with task counts
3. **Milestones** — deadline, completion rate
4. **Plan Progress** — per-plan details with planned vs actual hours, ahead/behind schedule detection
5. **Requirement Tracking** — full traceability from requirement to plan progress
6. **Project Total Hours** — per-executor breakdown with percentages
7. **Time Details** — by project, by milestone, by plan, and by tag

Long projects auto-compress the day width in report images (configurable threshold).

### Configuration

Menu → Config opens the settings dialog:

| Setting | Description |
| --- | --- |
| Language | Chinese / English |
| Font Size | Tree view font size |
| Data Directory | Where project data is stored |
| Compress Threshold | Days threshold for auto-compressing report Gantt images |
| Max Chart Width | Maximum width in pixels for report images |
| Pull Interval | Background remote check interval in minutes (default: 5) |
| Shortcuts | Customize all keyboard shortcuts with conflict detection |

### Project Tags

Define tags at the project level (Edit Project → Tags field, comma-separated). When adding activities, the tag dropdown only shows project-defined tags. Tags are used to group hours in Time Statistics and Reports.

### License

GPL-3.0

---

## 中文

### GanttPilot 是什么？

GanttPilot 是一款轻量级、基于 Git 的协作式项目管理器。每个项目都是一个独立的 Git 仓库，团队成员通过 Git 工作流（分支、推送、拉取、PR）进行协作。

它覆盖项目全生命周期：定义需求、拆解任务、规划里程碑、甘特图跟踪进度、记录工时、生成报告——全部在一个桌面应用中完成。

### 快速开始

#### 下载安装（推荐）

直接下载，无需安装 Python：

👉 [下载最新版本](https://github.com/matthewzu/GanttPilot/releases/latest)

| 平台 | 文件 |
| --- | --- |
| Windows | `GanttPilot.exe` |
| macOS | `GanttPilot.dmg` |
| Linux | `GanttPilot` |

双击运行即可。CLI 模式：`GanttPilot --cli`

#### 从源码运行

```bash
git clone https://github.com/matthewzu/GanttPilot.git
cd GanttPilot
python main.py              # GUI（默认）
python main.py --cli        # CLI 模式
python main.py --lang zh    # 中文界面
python main.py --version    # 显示版本
```

### 工作原理

#### 项目结构

每个项目遵循以下层级：

```
项目
  ├── 需求分析                      ← 定义要做什么
  │     └── 需求                      (类别、主题、描述)
  │           └── 任务                 (主题、工作量/人日)
  └── 计划执行                      ← 规划怎么做
        └── 里程碑                     (截止日期、描述、颜色)
              └── 计划                  (执行者、日期范围、关联任务、进度)
                    └── 活动            (执行者、日期、工时、标签、描述、内容)
```

- **需求和任务**定义"做什么"以及预估工作量
- **里程碑和计划**定义"什么时候做"和"谁来做"
- **活动**记录实际工作——工时、内容和标签
- **关联任务**将计划与需求连接起来，形成完整的跟踪链条

#### 典型工作流程

1. **创建项目** — 空白处右键 → 添加项目（或从远端仓库克隆）
2. **定义需求** — 展开"需求分析"，添加需求并拆解为任务
3. **设置里程碑** — 展开"计划执行"，创建带截止日期的里程碑
4. **创建计划** — 在里程碑下添加计划，指定执行者、日期范围，可选关联任务
5. **记录活动** — 在计划下记录每日工作，填写工时和内容
6. **跟踪进度** — 查看甘特图，检查需求跟踪标签页，设置计划进度（0-100%）
7. **生成报告** — 项目右键 → 生成报告（Markdown 格式，内嵌甘特图 PNG）
8. **团队协作** — 通过 Git 推送/拉取，每人在私有分支上工作，通过 PR 合并

### 界面指南

#### 主窗口

主窗口分为两个区域：

- **左侧面板**：项目树 — 以树形结构展示所有项目、需求、里程碑、计划和活动
- **右侧面板**：标签页视图，包含甘特图、工时统计、需求跟踪和历史记录

#### 工具栏

顶部工具栏提供常用操作的快捷入口。按钮会根据当前选中的节点类型自动启用/禁用：

| 按钮 | 功能 | 快捷键 |
| --- | --- | --- |
| 添加 | 添加子节点（需求/任务/里程碑/计划/活动） | `Ctrl+N` |
| 编辑 | 编辑选中节点 | `F2` |
| 删除 | 删除选中节点 | `Delete` |
| 复制 | 复制节点到剪贴板 | `Ctrl+C` |
| 粘贴 | 从剪贴板粘贴 | `Ctrl+V` |
| 克隆 | 复制节点及其所有子节点 | `Ctrl+D` |
| 上移 | 在同级节点中上移 | `Alt+Up` |
| 下移 | 在同级节点中下移 | `Alt+Down` |
| ⟳ | 检查更新 | — |

其他快捷键：`Ctrl+Z` 撤销、`Ctrl+Y` 恢复、`Ctrl+S` 推送、`F5` 刷新。所有快捷键均可在配置中自定义。

#### 右键菜单

右键菜单是执行各种操作的主要方式。菜单内容取决于你点击的位置：

| 右键点击 | 可用操作 |
| --- | --- |
| 空白处 | 添加项目、加载示例、推送、拉取、刷新 |
| 项目 | 编辑、Git 配置、复制、克隆、生成报告、推送、拉取、刷新、删除 |
| 需求分析 | 添加需求、粘贴 |
| 需求 | 添加任务、编辑、复制、粘贴、克隆、上移/下移、删除 |
| 任务 | 编辑、复制、克隆、上移/下移、删除 |
| 计划执行 | 添加里程碑、粘贴 |
| 里程碑 | 添加计划、编辑、设置颜色、复制、粘贴、克隆、上移/下移、删除 |
| 计划 | 添加活动、编辑、设置颜色、复制、粘贴、克隆、完结/重开、设置进度、上移/下移、删除 |
| 活动 | 编辑、复制、克隆、删除 |

#### 甘特图标签页

- 每个计划显示为一条水平条形，按执行者着色
- 里程碑在截止日期处显示为菱形标记
- 进度以条形的填充比例展示
- 跳过的日期（节假日）以红色斜线覆盖显示
- 使用 🔍+/- 按钮独立缩放甘特图（不影响树形图字体）

#### 工时统计标签页

展示活动中记录的工时数据，支持四种查看模式：

- **按项目** — 整个项目中每位执行者的总工时
- **按里程碑** — 按里程碑分组的工时
- **按计划** — 按计划分组的工时
- **按标签** — 按活动标签分组的工时

每种模式都显示分组合计和每位执行者的占比。

#### 需求跟踪标签页

展示完整的跟踪链条：需求 → 任务 → 关联计划 → 进度 → 实际工时。在这里可以验证每个需求是否已被规划，并跟踪其完成状态。

#### 历史记录标签页

显示当前项目的 Git 提交日志。你可以：

- 通过下拉列表切换分支（远端分支显示 `[远端]` 前缀）
- 查看提交详情：提交者、时间、提交信息和修改内容
- 右键提交记录 → **回退到此处**（hard reset）或 **撤销此提交**（生成反向提交）

### 创建项目

空白处右键 → 添加项目。对话框提供两种模式（通过单选按钮切换）：

#### 本地模式（默认）

适合个人离线使用，仅需填写两个字段：

- **项目名称**（必填）
- **描述**（可选）

数据存储在 `~/.ganttpilot/data/{项目名}/`。后续可通过项目右键 → Git 配置添加远端仓库。

#### 协作模式

适合团队协作，一步完成 Git 配置：

- **项目名称**和**描述** — 同本地模式
- **远端仓库地址** — bare 仓库地址（本地路径或服务器地址如 `https://github.com/user/repo.git`）
- **远端主分支** — 默认 `main`
- **用户名** — Git 仓库用户名
- **密码/Token** — 个人访问令牌或密码（掩码显示）
- **提交者名称** — 用于 Git 提交记录的名称（留空可自动检测系统 Git 配置）
- **提交者邮箱** — 用于 Git 提交记录的邮箱（留空可自动检测）
- **私有分支名称** — 留空则自动生成 `priv_{提交者名称}`

每个字段都有占位提示信息引导填写。切换模式时对话框自动调整大小。

### 记录工时

活动支持两种工时记录方式（二选一）：

- **时间段**：填写起止时间对，如 `0900/1200,1400/1700`，系统自动计算总工时
- **直接填写小时数**：输入数字，如 `3.5`

中英文逗号均可作为分隔符。

### 跳过日期（节假日与工作日）

在创建/编辑计划时，"跳过日期列表"字段控制哪些日期不计入计划工期：

- `20260501` — 跳过该日期（如节假日）
- `-20260510` — 取消跳过（如让周末变为工作日）
- 勾选"跳过非工作日"可自动跳过周末

跳过的日期在甘特图上以红色斜线覆盖显示。

### Git 协作

每个项目是独立的 Git 仓库，存储在 `~/.ganttpilot/data/{项目名}/`。

#### 协作流程

- 每位用户在私有分支上工作：`priv_{提交者名称}`
- 推送将私有分支发送到远端（项目右键 → 推送，或 `Ctrl+S`）
- 拉取从远端获取最新数据并自动更新本地 main 分支（项目右键 → 拉取）
- 通过 Git 平台的 Pull Request 将更改合并到主分支
- 拉取/同步后如果 main 有新提交，会弹窗询问是否将私有分支变基到最新 main
- GanttPilot 不会向远端 main 分支推送——仅推送私有分支

#### 配置方法

1. 项目右键 → Git 配置
2. 设置远端仓库地址（必须是 bare 仓库）、提交者名称和邮箱
3. Git 用户信息可从系统 git 配置自动检测

#### 后台同步

- 启动时自动拉取所有项目的远端更新（仅拉取，不推送）
- 定期后台检测远端更新（默认每 5 分钟，可在配置中调整）

### 报告

项目右键 → 生成报告。Markdown 报告包含：

1. **甘特图** — 内嵌 PNG 图片（本地渲染，无需外部依赖）
2. **需求分析** — 需求表格及任务数
3. **里程碑** — 截止日期、完成率
4. **计划进度详情** — 每个计划的计划工时 vs 实际工时、提前/延期检测
5. **需求跟踪** — 从需求到计划进度的完整跟踪链
6. **项目总工时** — 每位执行者的工时明细和占比
7. **工时明细** — 按项目、按里程碑、按计划、按标签四个维度

长周期项目会自动压缩报告图片的日宽度（可配置阈值）。

### 配置

菜单 → 配置，打开设置对话框：

| 设置项 | 说明 |
| --- | --- |
| 语言 | 中文 / 英文 |
| 字体大小 | 树形图字体大小 |
| 数据文件夹路径 | 项目数据存储位置 |
| 报告图片压缩阈值 | 超过此天数自动压缩甘特图日宽度 |
| 报告图片最大宽度 | 报告图片最大像素宽度 |
| 拉取间隔 | 后台远端检测间隔（分钟，默认 5） |
| 快捷键配置 | 自定义所有键盘快捷键，支持冲突检测 |

### 项目标签

在项目级别定义标签（编辑项目 → 标签字段，逗号分隔）。添加活动时，标签下拉框只显示项目已定义的标签。标签用于在工时统计和报告中按类别分组汇总。

### 许可证

GPL-3.0

---

<div align="center">

**⭐ If you like this project, please give it a star! ⭐**

**⭐ 如果这个项目对你有帮助，请给它一个 Star！⭐**

[Report Bug](https://github.com/matthewzu/GanttPilot/issues) · [Request Feature](https://github.com/matthewzu/GanttPilot/issues)

</div>
