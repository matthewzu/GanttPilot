# GanttPilot

<div align="center">

![Version](https://img.shields.io/badge/version-0.9.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.6+-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)
![License](https://img.shields.io/badge/license-GPL--3.0-orange.svg)

**Collaborative Project Manager with Gantt Chart | 基于甘特图的协作式项目管理器**

[English](#english) | [中文](#中文)

</div>

---

## English

### 📖 Introduction

GanttPilot is a collaborative project manager that visualizes project status with Gantt charts. Each project is an independent Git repository, enabling multi-user collaboration through Git sync. Manage projects, milestones, plans, and activities — all from a clean right-click menu interface.

Version: 0.9.0

### 🚀 Quick Start

#### Download Packaged Program (Recommended)

Download from GitHub Releases — no Python required:

👉 [Download Latest Version](https://github.com/matthewzu/GanttPilot/releases/latest)

| Platform | File |
| --- | --- |
| Windows | `GanttPilot.exe` |
| macOS | `GanttPilot.dmg` |
| Linux | `GanttPilot` |

Double-click to launch GUI. CLI: `GanttPilot --cli`

#### Run from Source (Alternative)

```bash
git clone https://github.com/matthewzu/GanttPilot.git
cd GanttPilot
python main.py          # GUI (default)
python main.py --cli    # CLI mode
python main.py --lang en
python main.py --version
```

### ✨ Features

- 📊 **Native Gantt Chart** - Canvas rendering, independent zoom, per-executor coloring, progress bars
- 📌 **Milestone Deadlines** - Diamond markers on Gantt chart
- 📈 **Progress Tracking** - Plan progress (0-100%), actual end date, ahead/behind schedule detection
- 📁 **Project Management** - Add/edit/delete/clone via right-click, project description
- 📋 **Requirement Management** - Create requirements with category, subject, and description under Requirement Analysis node
- ✅ **Task Management** - Break down requirements into tasks with effort estimation (person-days)
- 🔗 **Requirement Tracking** - Link plans to tasks, track requirements → tasks → plans → progress in a dedicated tab
- 🏷️ **Milestone Management** - Deadline, description, custom color
- 📋 **Plan Management** - Executor, date range, linked task, skip non-workdays, skip dates with `-YYYYMMDD` support, color, finish/reopen, set progress
- ⏱ **Activity Tracking** - Per-executor time logging
- 🛠️ **Unified Toolbar** - Add, Edit, Delete, Copy, Paste, Duplicate, Move Up, Move Down buttons with context-sensitive enable/disable
- ⧉ **Duplicate Node** - Clone any node (project, requirement, task, milestone, plan, activity) with all children via toolbar or right-click
- 📋 **Copy & Paste** - Copy nodes to clipboard and paste across projects/milestones/requirements (Ctrl+C / Ctrl+V)
- 🔗 **Per-project Git Repos** - Independent repos with configurable remote, private branch per user, PR workflow
- 🔄 **Smart Sync** - Background sync on startup/switch/exit
- ↩️ **Undo/Redo** - Ctrl+Z / Ctrl+Y
- 📝 **Rich Reports** - Markdown with milestone completion rates, plan progress details, executor activity logs
- 🖥️ **GUI + CLI** - Single executable, both modes
- 🌏 **Bilingual** - English and Chinese
- 🔤 **Font Scaling** - Independent tree font and Gantt zoom
- 🔄 **Auto Update** - Download with progress display from GitHub
- 💾 **Config Persistence** - Window state, language, font, paths with folder browser, report image settings
- 📦 **Clone from Remote** - Create project by cloning existing remote repo
- 📂 **Load Example** - Built-in demo project
- 🚫 **Skip Date Visualization** - Skipped days shown as red hatch overlay on Gantt bars
- 🖼️ **PNG Report** - Reports embed locally rendered PNG Gantt chart (no PlantUML dependency)
- 📐 **Auto-compress** - Long projects auto-shrink day width in report images (configurable threshold)
- 📜 **History Tab** - Gantt window includes a History tab showing Git commit log (author, date, message, diff)
- 🌿 **Branch Selector** - Dropdown to switch branches and view Gantt chart / history for each branch
- 🔀 **Manual Rebase Sync** - Sync no longer auto-rebases; a banner prompts when main has updates, click to rebase manually
- ⏱ **Time Slot Hours** - Activity hours entered as start/end time slots (e.g. `0900/1200,1430/1500`), total hours auto-calculated
- 🏷️ **Activity Tags** - Single tag per activity; time reports and project reports group summaries by tag
- 🏷️ **Remote Branch Labels** - Remote branches in the branch selector show `[Remote]` prefix for clear identification
- ↔️ **Resizable Panels** - Draggable splitter between Gantt chart/history and time report areas
- 📊 **Report View Modes** - Time report supports 4 view modes: by project, by milestone, by plan, by tag; Markdown reports include all 4 dimensions
- 🪟 **Window State Persistence** - Maximized window state saved and restored correctly on relaunch
- 📝 **Milestone Multiline Description** - Milestone description uses resizable multiline editor in create/edit dialogs

### 🖱️ Usage

All operations via toolbar buttons and right-click context menus:

| Node / Area | Toolbar | Right-click |
| --- | --- | --- |
| Empty area | — | Add project, Load example, Sync, Refresh |
| Project | Edit, Copy, Duplicate | Edit, Git config, Copy, Duplicate, Report, Sync, Refresh, Delete |
| Requirement Analysis | Add (requirement), Paste | Add requirement, Paste |
| Requirement | Add (task), Edit, Delete, Copy, Paste, Duplicate, Move Up/Down | Add task, Edit, Copy, Paste, Duplicate, Delete |
| Task | Edit, Delete, Copy, Duplicate, Move Up/Down | Edit, Copy, Duplicate, Delete |
| Plan Execution | Add (milestone), Paste | Add milestone, Paste |
| Milestone | Add (plan), Edit, Delete, Copy, Paste, Duplicate, Move Up/Down | Add plan, Edit, Color, Copy, Paste, Duplicate, Delete |
| Plan | Add (activity), Edit, Delete, Copy, Paste, Duplicate, Move Up/Down | Add activity, Edit, Color, Copy, Paste, Duplicate, Finish, Reopen, Set progress, Delete |
| Activity | Edit, Delete, Copy, Duplicate | Edit, Copy, Duplicate, Delete |

### 📐 Data Structure

```
Project (independent Git repo, with description)
  ├── Requirement Analysis
  │     └── Requirement (category, subject, description)
  │           └── Task (subject, effort_days, description)
  └── Plan Execution
        └── Milestone (deadline, description, color)
              └── Plan (executor, dates, linked_task, progress, skip dates, actual_end_date)
                    └── Activity (executor, date, hours, time_slots, tag, content)
```

- `linked_task_id`: References a task ID from requirements, linking plan to requirement tracking
- `time_slots`: Start/end time slot list, format `HHMM/HHMM` comma-separated (e.g. `0900/1200,1430/1500`)
- `hours`: Auto-calculated from `time_slots`; retains manual value when `time_slots` is empty
- `tag`: Single string tag for activity classification, default empty

### � Creating a Project

There are two ways to create a project (right-click empty area → Add project):

#### Method 1: Clone from Remote Repository

Fill in the "Remote URL" field in the create project dialog. The remote must be a **bare repository** (`git init --bare`).

- Remote can be a local path (e.g. `E:\repos\myproject`) or a server URL (e.g. `https://github.com/user/repo.git`)
- "Project Name" and "Description" are optional — if the remote already contains a `project.json`, the name and description will be read from it
- "Remote Main Branch" defaults to `main`, change to `master` or other as needed
- After cloning, a local `priv` work branch is created automatically

#### Method 2: Create Local Project

Leave the "Remote URL" field empty to create a purely local project.

- Only "Project Name" is required
- Data is stored locally at `~/.ganttpilot/data/{project_name}/`
- You can configure a remote repository later via right-click → Git Config on the project
- Once a remote is configured, the project will sync automatically on project switch and program exit

### 🔗 Git Sync

- Each project is an independent Git repository stored in `~/.ganttpilot/data/{project_name}/`
- Remote repositories must be **bare repos** (created with `git init --bare`)
- Configurable remote main branch name (default: `main`)
- Per-user private branch: `priv_{committer_name}` (configurable)
- Sync flow: fetch main → push priv to origin (no auto-rebase)
- Manual rebase: banner prompts when main has updates, click "Sync Main" to rebase
- Changes are merged to main via Pull Request on the remote platform
- Project-level committer identity (name + email), auto-detected from git config
- Automatic background sync: on startup (all projects), on project switch (previous project), on exit (current project)
- Manual sync: right-click project → Sync

### 📄 License

GPL-3.0

---

## 中文

### 📖 简介

GanttPilot 是一款基于甘特图的协作式项目管理器。每个项目作为独立 Git 仓库，通过 Git 同步实现多人协作。

版本：0.9.0

### 🚀 快速开始

#### 下载打包程序（首选）

👉 [下载最新版本](https://github.com/matthewzu/GanttPilot/releases/latest)

| 平台 | 文件 |
| --- | --- |
| Windows | `GanttPilot.exe` |
| macOS | `GanttPilot.dmg` |
| Linux | `GanttPilot` |

双击运行 GUI，CLI：`GanttPilot --cli`

#### 从源码运行（备选）

```bash
git clone https://github.com/matthewzu/GanttPilot.git
cd GanttPilot
python main.py          # GUI（默认）
python main.py --cli    # CLI 模式
python main.py --lang zh
python main.py --version
```

### ✨ 功能特性

- 📊 **原生甘特图** - Canvas 渲染，独立缩放，执行者颜色，进度条
- 📌 **里程碑截止日期** - 甘特图菱形标记
- 📈 **进度追踪** - 计划进度（0-100%）、实际完成时间、提前/延期检测
- 📁 **项目管理** - 右键添加/编辑/删除/克隆，项目描述
- 📋 **需求管理** - 在需求分析节点下创建需求，支持类别、主题和描述
- ✅ **任务管理** - 将需求拆解为任务，支持工作量估算（人日）
- 🔗 **需求跟踪** - 计划关联任务，在需求跟踪标签页中查看需求→任务→计划→进度跟踪链条
- 🏷️ **里程碑管理** - 截止日期、描述、自定义颜色
- 📋 **计划管理** - 执行者、日期范围、关联任务、跳过非工作日、跳过日期（支持 `-YYYYMMDD` 格式）、颜色、完结/重开、设置进度
- ⏱ **活动跟踪** - 按执行者记录工时
- 🛠️ **统一工具栏** - 添加、编辑、删除、复制、粘贴、克隆、上移、下移按钮，根据选中节点类型自动启用/禁用
- ⧉ **节点克隆** - 通过工具栏或右键菜单克隆任意节点（项目、需求、任务、里程碑、计划、活动）及其所有子节点
- 📋 **复制粘贴** - 复制节点到剪贴板，支持跨项目/跨里程碑/跨需求粘贴（Ctrl+C / Ctrl+V）
- 🔗 **项目级独立 Git 仓库** - 可配置远端，每用户私有分支，PR 工作流
- 🔄 **智能同步** - 启动/切换/退出时后台同步
- ↩️ **撤销/恢复** - Ctrl+Z / Ctrl+Y
- 📝 **丰富报告** - 里程碑完成率、计划进度详情、执行者工时明细
- 🖥️ **GUI + CLI 双模式**
- 🌏 **中英文双语**
- 🔤 **字体缩放** - 树状图和甘特图独立缩放
- 🔄 **在线自动更新** - 含下载进度显示
- 💾 **配置持久化** - 含文件夹浏览按钮、报告图片压缩参数
- 📦 **远端克隆** - 从远端仓库克隆已有项目
- 📂 **加载示例** - 内置演示项目
- 🚫 **跳过日期可视化** - 甘特图中跳过的日期以红色斜线标注
- 🖼️ **PNG 报告** - 报告内嵌本地渲染的 PNG 甘特图（无需 PlantUML）
- 📐 **自动压缩** - 长项目自动缩小报告图片日宽度（可配置阈值）
- 📜 **历史记录标签页** - 甘特图窗口增加历史记录标签，显示 Git 提交记录（提交者、时间、message、diff）
- 🌿 **分支选择** - 下拉列表切换不同分支查看甘特图和历史记录
- 🔀 **手动 Rebase 同步** - 同步时不自动 rebase，提示主线有更新后手动点击同步按钮
- ⏱ **起止时间工时** - 活动工时改为填写起止时间列表（如 `0900/1200,1430/1500`），自动计算总工时
- 🏷️ **活动标签** - 活动增加单个标签字段，工时报告和项目报告按标签分组汇总
- 🏷️ **远端分支标识** - 分支选择器中远端分支显示 `[远端]` 前缀，便于区分
- ↔️ **可调整面板** - 甘特图/历史记录与工时报告之间的分隔栏可拖拽调整
- 📊 **报告查看模式** - 工时报告支持按项目、按里程碑、按计划、按标签四种查看模式；Markdown 报告同时包含四种维度统计
- 🪟 **窗口状态记忆** - 最大化状态正确保存和恢复，重启后不再偏移
- 📝 **里程碑多行描述** - 里程碑创建/编辑对话框中描述字段改为可调整大小的多行编辑框

### 🖱️ 操作方式

通过工具栏按钮和右键菜单进行所有操作：

| 节点 / 区域 | 工具栏 | 右键菜单 |
| --- | --- | --- |
| 空白处 | — | 添加项目、加载示例、同步、刷新 |
| 项目 | 编辑、复制、克隆 | 编辑项目、Git 配置、复制、克隆、生成报告、同步、刷新、删除 |
| 需求分析 | 添加（需求）、粘贴 | 添加需求、粘贴 |
| 需求 | 添加（任务）、编辑、删除、复制、粘贴、克隆、上移/下移 | 添加任务、编辑、复制、粘贴、克隆、删除 |
| 任务 | 编辑、删除、复制、克隆、上移/下移 | 编辑、复制、克隆、删除 |
| 计划执行 | 添加（里程碑）、粘贴 | 添加里程碑、粘贴 |
| 里程碑 | 添加（计划）、编辑、删除、复制、粘贴、克隆、上移/下移 | 添加计划、编辑里程碑、设置颜色、复制、粘贴、克隆、删除 |
| 计划 | 添加（活动）、编辑、删除、复制、粘贴、克隆、上移/下移 | 添加活动、编辑属性、设置颜色、复制、粘贴、克隆、完结、重开、设置进度、删除 |
| 活动 | 编辑、删除、复制、克隆 | 编辑活动、复制、克隆、删除 |

### 📐 数据结构

```
项目 (独立 Git 仓库，含描述)
  ├── 需求分析
  │     └── 需求 (类别、主题、描述)
  │           └── 任务 (主题、工作量/人日、描述)
  └── 计划执行
        └── 里程碑 (截止日期、描述、颜色)
              └── 计划 (执行者、日期范围、关联任务、进度、跳过日期、实际完成时间)
                    └── 活动 (执行者、日期、小时数、工时时段、标签、内容)
```

- `linked_task_id`：引用需求中的任务 ID，将计划与需求跟踪链条关联
- `time_slots`：起止时间段列表，格式 `HHMM/HHMM` 逗号分隔（如 `0900/1200,1430/1500`）
- `hours`：由 `time_slots` 自动计算；当 `time_slots` 为空时保留手动输入值
- `tag`：单个字符串标签，用于活动分类，默认为空

### � 创建项目

有两种方式创建项目（空白处右键 → 添加项目）：

#### 方式一：从远端仓库克隆

在创建项目对话框中填写"远端仓库地址"。远端必须是 **bare 仓库**（通过 `git init --bare` 创建）。

- 远端可以是本地路径（如 `E:\repos\myproject`）或服务器地址（如 `https://github.com/user/repo.git`）
- "项目名称"和"描述"为可选项 — 如果远端仓库已包含 `project.json`，名称和描述会从中读取
- "远端主分支"默认为 `main`，可根据需要改为 `master` 或其他分支名
- 克隆完成后会自动创建本地 `priv` 工作分支

#### 方式二：本地创建项目

"远端仓库地址"留空即可创建纯本地项目。

- 仅"项目名称"为必填项
- 数据存储在 `~/.ganttpilot/data/{项目名}/`
- 后续可通过项目右键菜单 → Git 配置 来添加远端仓库
- 配置远端后，切换项目和退出程序时会自动后台同步

### 🔗 Git 同步

- 每个项目是独立的 Git 仓库，存储在 `~/.ganttpilot/data/{项目名}/`
- 远端仓库必须是 **bare 仓库**（通过 `git init --bare` 创建）
- 可配置远端主分支名称（默认 `main`）
- 每用户私有分支：`priv_{提交者名称}`（可配置）
- 同步流程：fetch main → push priv 到远端（不自动 rebase）
- 手动 rebase：主线有更新时显示提示横幅，点击"同步主线"按钮执行 rebase
- 通过远端平台的 Pull Request 合并到主分支
- 项目级提交者身份（名称 + 邮箱），可自动检测 git 配置
- 自动后台同步：启动时（所有项目）、切换项目时（上一个项目）、退出时（当前项目）
- 手动同步：项目右键 → 同步

### 📄 许可证

GPL-3.0

---

<div align="center">

**⭐ If you like this project, please give it a star! ⭐**

**⭐ 如果这个项目对你有帮助，请给它一个 Star！⭐**

[Report Bug](https://github.com/matthewzu/GanttPilot/issues) · [Request Feature](https://github.com/matthewzu/GanttPilot/issues)

</div>
