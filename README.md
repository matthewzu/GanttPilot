# GanttPilot

<div align="center">

![Version](https://img.shields.io/badge/version-0.3.0-blue.svg)
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

Version: 0.3.0

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
- 📋 **Plan Management** - Executor, date range, skip non-workdays, color, finish, set progress
- ⏱ **Activity Tracking** - Per-executor time logging
- 🔗 **Per-project Git Repos** - Independent repos with configurable remote (bare repos)
- 🔄 **Smart Sync** - Background sync on startup/switch/exit
- ↩️ **Undo/Redo** - Ctrl+Z / Ctrl+Y
- 📝 **Rich Reports** - Markdown with milestone completion rates, plan progress details, executor activity logs
- 🖥️ **GUI + CLI** - Single executable, both modes
- 🌏 **Bilingual** - English and Chinese
- 🔤 **Font Scaling** - Independent tree font and Gantt zoom
- 🔄 **Auto Update** - Download and replace from GitHub
- 💾 **Config Persistence** - Window state, language, font, paths with folder browser
- 📦 **Clone from Remote** - Create project by cloning existing remote repo
- 📂 **Load Example** - Built-in demo project

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
        └── Plan (executor, dates, progress, actual_end_date)
              └── Activity (executor, date, hours, content)
```

### 🔗 Git Sync

- Per-project bare remote repos with configurable main branch
- Work branch: `priv`, sync: fetch → rebase → merge → push
- Clone existing projects from remote repos

### 📄 License

GPL-3.0

---

## 中文

### 📖 简介

GanttPilot 是一款基于甘特图的协作式项目管理器。每个项目作为独立 Git 仓库，通过 Git 同步实现多人协作。

版本：0.3.0

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
- 📋 **计划管理** - 执行者、日期范围、跳过非工作日、颜色、终结、设置进度
- ⏱ **活动跟踪** - 按执行者记录工时
- 🔗 **项目级独立 Git 仓库** - 可配置远端（bare 仓库）
- 🔄 **智能同步** - 启动/切换/退出时后台同步
- ↩️ **撤销/恢复** - Ctrl+Z / Ctrl+Y
- 📝 **丰富报告** - 里程碑完成率、计划进度详情、执行者工时明细
- 🖥️ **GUI + CLI 双模式**
- 🌏 **中英文双语**
- 🔤 **字体缩放** - 树状图和甘特图独立缩放
- 🔄 **在线自动更新**
- 💾 **配置持久化** - 含文件夹浏览按钮
- 📦 **远端克隆** - 从远端仓库克隆已有项目
- 📂 **加载示例** - 内置演示项目

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
        └── 计划 (执行者、日期范围、进度、实际完成时间)
              └── 活动 (执行者、日期、小时数、内容)
```

### 🔗 Git 同步

- 每个项目独立 bare 远端仓库，可配置主分支名
- 工作分支 `priv`，同步：fetch → rebase → merge → push
- 支持从远端仓库克隆已有项目

### 📄 许可证

GPL-3.0

---

<div align="center">

**⭐ If you like this project, please give it a star! ⭐**

**⭐ 如果这个项目对你有帮助，请给它一个 Star！⭐**

[Report Bug](https://github.com/matthewzu/GanttPilot/issues) · [Request Feature](https://github.com/matthewzu/GanttPilot/issues)

</div>
