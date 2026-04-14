# GanttPilot

<div align="center">

![Version](https://img.shields.io/badge/version-0.5.1-blue.svg)
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

Version: 0.5.1

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
- 🏷️ **Milestone Management** - Deadline, description, custom color
- 📋 **Plan Management** - Executor, date range, planned hours, skip non-workdays, skip dates with `-YYYYMMDD` support, color, finish, set progress
- ⏱ **Activity Tracking** - Per-executor time logging
- 🔗 **Per-project Git Repos** - Independent repos with configurable remote (bare repos)
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

### 🖱️ Usage

All operations via right-click context menus:

| Right-click on | Available actions |
| --- | --- |
| Empty area | Add project, Load example, Sync, Refresh |
| Project | Add milestone, Edit, Git config, Report, Sync, Delete |
| Milestone | Add plan, Edit, Color, Delete |
| Plan | Add activity, Edit, Color, Set progress, Finish, Delete |
| Activity | Edit, Delete |

### 📐 Data Structure

```
Project (independent Git repo, with description)
  └── Milestone (deadline, description, color)
        └── Plan (executor, dates, planned hours, progress, skip dates, actual_end_date)
              └── Activity (executor, date, hours, content)
```

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
- Work branch: `priv` — all local operations commit here
- Sync flow: fetch → pull main --rebase → rebase priv onto main → ff-merge → push main
- Automatic background sync: on startup (all projects), on project switch (previous project), on exit (current project)
- Manual sync: right-click project → Sync

### 📄 License

GPL-3.0

---

## 中文

### 📖 简介

GanttPilot 是一款基于甘特图的协作式项目管理器。每个项目作为独立 Git 仓库，通过 Git 同步实现多人协作。

版本：0.5.1

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
- 🏷️ **里程碑管理** - 截止日期、描述、自定义颜色
- 📋 **计划管理** - 执行者、日期范围、计划工时、跳过非工作日、跳过日期（支持 `-YYYYMMDD` 格式）、颜色、终结、设置进度
- ⏱ **活动跟踪** - 按执行者记录工时
- 🔗 **项目级独立 Git 仓库** - 可配置远端（bare 仓库）
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

### 🖱️ 操作方式

| 右键点击 | 可用操作 |
| --- | --- |
| 空白处 | 添加项目、加载示例、同步、刷新 |
| 项目 | 添加里程碑、编辑项目、Git 配置、生成报告、同步、删除 |
| 里程碑 | 添加计划、编辑里程碑、设置颜色、删除 |
| 计划 | 添加活动、编辑属性、设置颜色、设置进度、终结、删除 |
| 活动 | 编辑活动、删除 |

### 📐 数据结构

```
项目 (独立 Git 仓库，含描述)
  └── 里程碑 (截止日期、描述、颜色)
        └── 计划 (执行者、日期范围、计划工时、进度、跳过日期、实际完成时间)
              └── 活动 (执行者、日期、小时数、内容)
```

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
- 工作分支：`priv` — 所有本地操作在此分支提交
- 同步流程：fetch → pull main --rebase → rebase priv onto main → ff-merge → push main
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
