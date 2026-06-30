#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GanttPilot - Internationalization / 国际化"""

TEXTS = {
    "zh": {
        "app_title": "GanttPilot - 协作式项目管理器",
        "project": "项目",
        "milestone": "里程碑",
        "plan": "计划",
        "activity": "活动",
        "config": "配置",
        "add": "添加",
        "delete": "删除",
        "finish": "完结",
        "report": "生成报告",
        "push": "推送",
        "pushing": "正在推送...",
        "push_done": "推送完成",
        "push_fail": "推送失败: {}",
        "pull": "拉取",
        "pulling": "正在拉取...",
        "pull_done": "拉取完成",
        "pull_fail": "拉取失败: {}",
        "sync": "同步",
        "syncing": "正在同步...",
        "sync_done": "同步完成",
        "sync_fail": "同步失败: {}",
        "no_remote": "未配置远端仓库",
        "select_project": "选择项目",
        "no_projects": "暂无项目",
        "project_name": "项目名称",
        "milestone_name": "里程碑名称",
        "belongs_to_project": "所属项目",
        "belongs_to_milestone": "所属里程碑",
        "belongs_to_plan": "所属计划",
        "description": "描述",
        "executor": "执行者",
        "content": "内容",
        "start_date": "开始时间",
        "end_date": "结束时间",
        "skip_non_workdays": "跳过非工作日",
        "skip_dates": "跳过日期列表",
        "skip_dates_hint": "格式: YYYYMMDD,YYYYMMDD  前缀-表示取消跳过(如 -20260510)",
        "date": "日期",
        "hours": "小时数",
        "yes": "是",
        "no": "否",
        "confirm_delete": "确认删除 '{}'？",
        "confirm_finish": "确认完结计划 '{}'？",
        "gantt_chart": "甘特图",
        "time_report": "工时统计",
        "participant": "参与者",
        "total_hours": "总小时数",
        "total_days": "总天数",
        "percentage": "占比",
        "group_total": "合计",
        "font_size": "字体大小",
        "language": "语言",
        "config_dir": "本地配置路径",
        "data_dir": "数据文件夹路径",
        "remote_url": "远端仓库地址",
        "username": "用户名",
        "password": "密码/Token",
        "save_config": "保存配置",
        "config_saved": "配置已保存",
        "help": "帮助",
        "about": "关于",
        "more": "更多",
        "search_placeholder": "搜索节点...",
        "version": "版本",
        "exit": "退出",
        "error": "错误",
        "success": "成功",
        "warning": "警告",
        "input_required": "请输入{}",
        "invalid_date": "日期格式无效，请使用YYYYMMDD",
        "plan_status_active": "进行中",
        "plan_status_finished": "已完结",
        "refresh": "刷新",
        "open_in_browser": "在浏览器中查看",
        "generating_gantt": "正在生成甘特图...",
        "cli_welcome": "欢迎使用 GanttPilot 命令行模式",
        "cli_help": "输入 help 查看可用命令",
        "cli_unknown_cmd": "未知命令: {}",
        "cli_bye": "再见！",
        "update_available": "发现新版本 v{}，是否立即下载更新？",
        "update_check": "检查更新",
        "no_update": "已是最新版本",
        "zhihu_generated": "知乎文章已生成: {}",
        "project_added": "项目 '{}' 已添加",
        "project_deleted": "项目 '{}' 已删除",
        "milestone_added": "里程碑 '{}' 已添加",
        "milestone_deleted": "里程碑 '{}' 已删除",
        "plan_added": "计划 '{}' 已添加",
        "plan_deleted": "计划 '{}' 已删除",
        "plan_finished": "计划 '{}' 已完结",
        "activity_added": "活动已添加",
        "activity_deleted": "活动已删除",
        "not_found": "未找到: {}",
        "edit_project": "编辑项目",
        "edit_milestone": "编辑里程碑",
        "edit_activity": "编辑活动",
        "git_config": "Git 配置",
        "undo": "撤销",
        "redo": "恢复",
        "undo_tooltip": "撤销 (Ctrl+Z)",
        "redo_tooltip": "恢复 (Ctrl+Y)",
        "name_duplicate": "名称已存在: {}",
        "name_required": "请输入名称",
        "invalid_url": "无效的仓库地址",
        "remote_branch": "远端主分支",
        "undo_done": "已撤销",
        "redo_done": "已恢复",
        "no_undo": "无可撤销的操作",
        "no_redo": "无可恢复的操作",
        "color": "颜色",
        "set_progress": "设置进度",
        "progress": "进度",
        "progress_input": "请输入进度百分比 (0-100)",
        "invalid_progress": "请输入 0 到 100 之间的整数",
        "completion_rate": "完成率",
        "ahead_of_schedule": "提前完成",
        "behind_schedule": "延期完成",
        "load_example": "加载示例",
        "example_loaded": "示例项目已加载",
        "file_not_found": "文件未找到: {}",
        "clone_failed": "克隆失败: {}",
        "cloning": "正在克隆...",
        "downloading_update": "正在下载更新...",
        "actual_end_date": "实际完成时间",
        "max_segment_days": "甘特图每段最大天数",
        "export_scale": "导出图片缩放倍数",
        "planned_hours": "计划工时",
        "committer_name": "提交者名称",
        "committer_email": "提交者邮箱",
        "priv_branch": "私有分支名称",
        "git_not_installed": "未检测到 Git，请先安装 Git",
        "committer_not_configured": "请先配置提交者名称和邮箱",
        "detect_git_user_confirm": "检测到 Git 用户信息：\n名称: {}\n邮箱: {}\n是否使用？",
        "priv_branch_auto": "未填写私有分支名称，将使用 \"{}\"",
        "sync_pr_hint": "已推送到 {}，请在远端创建 PR: {} → {}",
        "bg_check_interval": "后台检查间隔(分钟)",
        "pull_interval": "拉取间隔(分钟)",
        "git_log_max_days": "日志保留天数",
        "main_update_detected": "检测到主线更新，请及时同步",
        "project_tags": "项目标签",
        "project_tags_hint": "逗号分隔，如: 前端,后端,测试",
        "project_members": "项目成员",
        "project_members_hint": "格式: 全名:缩写,全名:缩写  如: 张三:ZS,李四:LS",
        "invalid_member_format": "成员格式错误，请使用 '全名:缩写' 格式，逗号分隔",
        "duplicate_member_abbr": "缩写重复: {}",
        "select_executor": "请选择执行者",
        "committer_fallback_hint": "留空则使用全局配置: {} <{}>",
        "manage_tags": "管理标签",
        "tag_select": "选择标签",
        "committer_required": "提交者名称和邮箱为必填项，请填写后重试",
        "history": "历史记录",
        "branch": "分支",
        "no_history": "无历史记录",
        "not_git_repo": "当前项目不是 Git 仓库",
        "main_updated": "主线有更新",
        "sync_main": "同步主线",
        "rebase_success": "变基成功",
        "rebase_conflict": "变基冲突，已自动中止。请手动解决冲突。",
        "rebase_prompt": "远端主分支有更新，是否将私有分支变基到最新？",
        "time_slots": "工时（时间段）",
        "time_slots_hint": "格式: HHMM/HHMM,HHMM/HHMM",
        "invalid_time_slots": "工时（时间段）格式错误",
        "effort_hours": "工时（小时数）",
        "effort_hours_hint": "与'工时（时间段）'二选一填写，直接输入小时数(如 3.5)",
        "time_slots_or_hours_hint": "请填写'工时（小时数）'或'工时（时间段）'其中之一，不可同时填写",
        "invalid_hours": "请输入有效的小时数",
        "hours_non_negative": "小时数必须大于等于 0",
        "hours_conflict": "工时（小时数）与工时（时间段）不可同时填写，请只填其中一项",
        "tag": "标签",
        "tag_summary": "标签工时汇总",
        "commit_author": "提交者",
        "commit_date": "提交时间",
        "commit_message": "提交信息",
        "commit_diff": "修改内容",
        "remote_prefix": "[远端]",
        "report_by_project": "按项目查看",
        "report_by_milestone": "按里程碑查看",
        "report_by_plan": "按计划查看",
        "report_by_tag": "按标签查看",
        "report_mode": "查看模式",
        "group_col": "分组",
        "reopen": "重开",
        "confirm_reopen": "确认重开计划 '{}'？",
        "plan_reopened": "计划 '{}' 已重开",
        "update_check": "更新检查",
        "update_available": "发现新版本 {}！是否立即下载更新？",
        "update_not_ready": "v{} 发布资源尚未就绪，请稍后重试。",
        "update_restart": "v{} 更新完成，即将自动重启。",
        "view_changelog": "查看更新内容",
        "view_readme": "查看使用说明",
        "downloading_update": "正在下载更新...",
        "checking_update": "正在检查更新...",
        "check_update_fail": "检查更新失败",
        # ── View detail / 查看详情 ──
        "view": "查看",
        "view_detail": "查看详情",
        "shortcut_view": "查看",
        "view_project": "查看项目",
        "view_requirement": "查看需求",
        "view_task": "查看任务",
        "view_milestone": "查看里程碑",
        "view_plan": "查看计划",
        "view_activity": "查看活动",
        # ── MCP Server / MCP 服务 ──
        "mcp_server": "MCP 服务",
        "mcp_enabled": "MCP 服务已启用",
        "mcp_disabled": "MCP 服务已停止",
        "mcp_start": "启动",
        "mcp_stop": "停止",
        "mcp_status_running": "运行中",
        "mcp_status_stopped": "已停止",
        "mcp_config_title": "MCP Server 配置",
        "mcp_config_desc": "GanttPilot MCP Server 允许 AI 助手（如 Kiro、Claude）直接管理你的项目数据。",
        "mcp_copy_config": "复制配置",
        "mcp_copied": "已复制到剪贴板",
        "mcp_template_kiro": "Kiro 配置模板",
        "mcp_template_claude": "Claude Desktop 配置模板",
        "mcp_template_generic": "通用 MCP 配置模板",
        "mcp_data_dir_label": "数据目录",
        "mcp_script_path_label": "脚本路径",
        # ── Requirement tracking / 需求跟踪 ──
        "requirement_analysis": "需求分析",
        "plan_execution": "计划执行",
        "requirement": "需求",
        "task": "任务",
        "category": "类别",
        "subject": "主题",
        "effort_days": "工作量(人日)",
        "linked_task": "关联任务",
        "tracking_tab": "需求跟踪",
        "req_category": "需求类别",
        "req_subject": "需求主题",
        "task_subject": "任务主题",
        "linked_plan": "关联计划",
        "plan_progress": "计划进度",
        "move_up": "上移",
        "move_down": "下移",
        "edit": "编辑",
        "add_requirement": "添加需求",
        "edit_requirement": "编辑需求",
        "add_task": "添加任务",
        "edit_task": "编辑任务",
        "edit_plan": "编辑计划",
        "requirement_added": "需求 '{}' 已添加",
        "requirement_deleted": "需求 '{}' 已删除",
        "task_added": "任务 '{}' 已添加",
        "task_deleted": "任务 '{}' 已删除",
        "subject_required": "请输入主题",
        "invalid_effort": "请输入有效数值",
        "effort_non_negative": "工作量必须大于等于 0",
        "report_req_analysis": "需求分析",
        "report_req_tracking": "需求跟踪",
        "actual_hours": "实际工时",
        "planned_hours": "计划工时",
        "variance": "差异",
        "total_planned_hours": "总计划工时",
        "total_actual_hours": "总实际工时",
        "project_overtime_summary": "项目工时统计（已完结计划）",
        "task_count": "任务数",
        "duplicate": "克隆",
        "copy": "复制",
        "cut": "剪切",
        "paste": "粘贴",
        "duplicate_tooltip": "克隆选中节点",
        "copy_tooltip": "复制 (Ctrl+C)",
        "cut_tooltip": "剪切 (Ctrl+X)",
        "paste_tooltip": "粘贴 (Ctrl+V)",
        "nothing_to_paste": "剪贴板为空",
        "paste_type_mismatch": "无法在此处粘贴该类型的节点",
        "duplicated": "已克隆: {}",
        "copied": "已复制: {}",
        "cut_done": "已剪切: {}",
        "pasted": "已粘贴: {}",
        "overtime": "超出",
        "undertime": "少用",
        "help_text": (
            "GanttPilot - 协作式项目管理器\n\n"
            "【日志路径】操作日志: 本地配置路径/ganttpilot.log\n\n"
            "【快速上手】\n"
            "1. 空白处右键 → 添加项目（或加载示例体验）\n"
            "2. 展开「需求分析」→ 添加需求 → 拆解为任务\n"
            "3. 展开「计划执行」→ 添加里程碑 → 创建计划\n"
            "4. 在计划下记录活动（工时和内容）\n"
            "5. 项目右键 → 生成报告（可选概况/细节）\n\n"
            "【项目结构】\n"
            "📋 需求分析 → 需求 → 任务（定义做什么）\n"
            "📊 计划执行 → 里程碑 → 计划 → 活动（规划怎么做）\n"
            "🔗 计划可关联任务，形成需求→任务→计划跟踪链\n\n"
            "【搜索过滤】工具栏下方搜索框\n"
            "• 输入关键字实时过滤项目树节点\n"
            "• 匹配节点蓝色高亮，非匹配节点自动隐藏\n"
            "• 点击 ✕ 或清空内容恢复显示全部节点\n\n"
            "【工具栏】分组显示，根据选中节点自动启用/禁用\n"
            "• ↩↪ 撤销/恢复 │ +✏👁✕ 增删改查 │ 📋✂📌⧉ 剪贴板 │ ↑↓ 排序\n"
            "• 添加(Ctrl+N) / 编辑(F2) / 查看(F3) / 删除(Delete)\n"
            "• 复制(Ctrl+C) / 剪切(Ctrl+X) / 粘贴(Ctrl+V) / 克隆(Ctrl+D)\n"
            "• 上移(Alt+↑) / 下移(Alt+↓)\n"
            "• ⚙ 配置（语言、字体、路径、快捷键）\n"
            "• ⋯ 更多（检查更新、帮助、MCP服务、关于）\n\n"
            "【右键菜单】所有操作的主要入口\n"
            "• 空白处 → 添加项目、推送、拉取、刷新\n"
            "• 项目 → 编辑、Git配置、报告、推送、拉取、删除\n"
            "• 需求/任务 → 添加、编辑、复制、剪切、克隆、删除\n"
            "• 里程碑 → 添加计划、编辑、颜色、删除\n"
            "• 计划 → 添加活动、编辑、颜色、进度、完结/重开、删除\n"
            "• 活动 → 编辑、复制、剪切、克隆、删除\n\n"
            "【右侧标签页】\n"
            "• 甘特图 — 可视化项目进度，🔍+/- 独立缩放\n"
            "• 工时统计 — 按项目/里程碑/计划/标签四种模式查看，已完结计划显示超出/少用\n"
            "• 需求跟踪 — 需求→任务→计划→进度→差异完整链条，已完结计划显示工时差异\n"
            "• 历史记录 — Git提交日志，可切换分支、回退、撤销\n\n"
            "【工时记录】二选一\n"
            "• 时间段：0900/1200,1400/1700（自动算工时）\n"
            "• 直接填写小时数：3.5\n\n"
            "【活动描述】\n"
            "• 活动支持多行描述字段，记录背景和补充说明\n"
            "• 添加活动时执行者默认使用提交者名称（项目级 > 全局）\n"
            "• 配置成员后执行者从下拉列表选择（编辑项目 → 成员字段）\n\n"
            "【报告生成】\n"
            "• 概况模式：甘特图 + 需求 + 里程碑 + 进度（不含工时）\n"
            "• 细节模式：完整报告含所有工时明细\n\n"
            "【跳过日期】\n"
            "• 20260501 → 跳过（节假日）\n"
            "• -20260510 → 取消跳过（周末变工作日）\n\n"
            "【Git协作】Ctrl+S 推送 / 右键拉取\n"
            "• 每人私有分支，通过 PR 合并到主线\n"
            "• 推送前弹出确认对话框，显示待推送内容摘要\n"
            "• 启动时自动拉取主线，后台定期检测更新\n"
            "• 退出时展示未推送内容并提示推送\n"
            "• 撤销/恢复操作同步创建 Git commit，历史标签页可见\n"
            "• 提交包含 project.json 及 requirements/ milestones/ activities/ 目录\n"
            "• 拉取后自动更新本地 main，提示 rebase（变基后自动推送）\n"
            "• 项目右键 → 同步主线：手动将私有分支变基到最新 main\n"
            "• 项目右键 → 升级主线格式：维护者一键迁移到 v2 拆分格式并推送主线\n"
            "• 私有分支名不能为 \"priv\" 或与主分支同名\n"
            "• 推送失败排查：查看数据目录下 ganttpilot.log 日志文件\n"
            "• 日志记录 Git 操作、配置修改、MCP 启停等所有重要操作\n\n"
            "【提交者信息】创建项目时必须\n"
            "• 获取顺序：手动输入 → 全局配置(⚙) → 系统 git config\n"
            "• 全部获取不到则阻止创建，请先配置\n\n"
            "【其他】Ctrl+Z 撤销 / Ctrl+Y 恢复 / 快捷键可自定义\n"
            "• 查看详情、配置、活动编辑等弹窗可最大化，方便查看/填写大段文字\n\n"
            "【MCP Server】AI 助手集成\n"
            "• 点击 ⋯ → MCP服务 打开 MCP 配置，启动/停止服务\n"
            "• 支持 Kiro、Claude Desktop 等 AI 工具直接管理项目\n"
            "• 提供配置模板一键复制，粘贴到对应工具的配置文件即可\n\n"
        ),
        # ── Keyboard shortcuts / 键盘快捷键 ──
        "shortcut_add": "添加",
        "shortcut_edit": "编辑",
        "shortcut_delete": "删除",
        "shortcut_move_up": "上移",
        "shortcut_move_down": "下移",
        "shortcut_duplicate": "克隆",
        "shortcut_copy": "复制",
        "shortcut_cut": "剪切",
        "shortcut_paste": "粘贴",
        "shortcut_undo": "撤销",
        "shortcut_redo": "恢复",
        "shortcut_push": "推送",
        "shortcut_pull": "拉取",
        "shortcut_sync": "同步",
        "shortcut_refresh": "刷新",
        "shortcut_config": "快捷键配置",
        "shortcut_conflict": "快捷键 \"{}\" 已绑定到 \"{}\"",
        "shortcut_reset": "恢复默认",
        "shortcut_press_key": "请按下新的快捷键...",
        "optional": "可选",
        "reset_to_here": "回退到此处",
        "confirm_reset": "确认回退到此提交？之后的所有更改将丢失。\n\n{}",
        "reset_done": "已回退到: {}",
        "reset_failed": "回退失败: {}",
        "revert_commit": "撤销此提交",
        "confirm_revert": "确认撤销此提交？将生成一个反向提交。\n\n{}",
        "revert_done": "已撤销提交: {}",
        "revert_failed": "撤销失败: {}",
        # ── Report type dialog / 报告类型 ──
        "report_type_title": "选择报告类型",
        "report_type_summary": "概况",
        "report_type_detail": "细节",
        "report_type_summary_desc": "包含甘特图、需求分析、里程碑、进度概览（不含工时）",
        "report_type_detail_desc": "包含完整工时、备注等详细信息",
        # ── Exit push prompt / 退出推送提示 ──
        "exit_push_prompt": "以下内容尚未推送到远端，是否现在推送？",
        "exit_push_title": "退出前推送",
        # ── Manual push confirmation / 手动推送确认 ──
        "confirm_push_title": "确认推送",
        "confirm_push_prompt": "确认推送以下内容到远端？",
        "unpushed_content_header": "\n\n包含内容:",
        # ── Executor default hint / 执行者默认提示 ──
        "executor_default_hint": "默认使用提交者名称: {}（优先级: 活动 > 项目 > 全局）",
        # ── Project creation modes / 项目创建模式 ──
        "mode_local": "本地模式",
        "mode_collab": "协作模式",
        "ph_project_name": "请输入项目名称",
        "ph_description": "可选，输入项目描述",
        "ph_remote_url": "如 https://github.com/user/repo.git",
        "ph_remote_branch": "默认 main",
        "ph_username": "Git 仓库用户名",
        "ph_password": "个人访问令牌或密码",
        "ph_committer_name": "用于 Git 提交记录的名称",
        "ph_committer_email": "用于 Git 提交记录的邮箱",
        "ph_priv_branch": "留空则自动生成 priv_{提交者名称}",
        "url_required": "请填写远端仓库地址",
        "invalid_url_format": "远端仓库地址格式无效",
        "desc_optional": "(可选)",
        # ── Private branch validation / 私有分支名校验 ──
        "priv_branch_invalid_priv": "不能使用 'priv' 作为私有分支名称",
        "priv_branch_same_as_main": "私有分支名称不能与主分支相同",
        "priv_branch_invalid_chars": "分支名称包含非法字符",
        # ── Storage migration / 存储格式迁移 ──
        "migration_title": "存储格式升级",
        "migration_message": "检测到项目数据使用旧格式存储（活动记录内嵌在 project.json 中）。\n\n新格式将活动记录拆分为独立文件，可显著减少多人协作时的 Git 合并冲突。\n\n是否立即迁移？",
        "migration_success": "迁移完成，已升级 {} 个项目的存储格式。",
        "migration_skipped": "已跳过迁移，下次启动时将再次提示。",
        "migrate_main": "升级主线格式",
        "migrate_main_title": "升级主线存储格式",
        "migrate_main_confirm": "将存储格式升级提交到主线分支并推送到远端。\n\n其他成员变基时将自动迁移到新格式。\n\n确定执行？",
        "migrate_main_running": "正在升级主线格式...",
        "migrate_main_success": "主线格式升级完成，已推送到远端。",
    },
    "en": {
        "app_title": "GanttPilot - Collaborative Project Manager",
        "project": "Project",
        "milestone": "Milestone",
        "plan": "Plan",
        "activity": "Activity",
        "config": "Config",
        "add": "Add",
        "delete": "Delete",
        "finish": "Finish",
        "report": "Generate Report",
        "push": "Push",
        "pushing": "Pushing...",
        "push_done": "Push complete",
        "push_fail": "Push failed: {}",
        "pull": "Pull",
        "pulling": "Pulling...",
        "pull_done": "Pull complete",
        "pull_fail": "Pull failed: {}",
        "sync": "Sync",
        "syncing": "Syncing...",
        "sync_done": "Sync complete",
        "sync_fail": "Sync failed: {}",
        "no_remote": "Remote repository not configured",
        "select_project": "Select Project",
        "no_projects": "No projects yet",
        "project_name": "Project Name",
        "milestone_name": "Milestone Name",
        "belongs_to_project": "Project",
        "belongs_to_milestone": "Milestone",
        "belongs_to_plan": "Plan",
        "description": "Description",
        "executor": "Executor",
        "content": "Content",
        "start_date": "Start Date",
        "end_date": "End Date",
        "skip_non_workdays": "Skip Non-workdays",
        "skip_dates": "Skip Dates",
        "skip_dates_hint": "Format: YYYYMMDD,YYYYMMDD  prefix - to un-skip (e.g. -20260510)",
        "date": "Date",
        "hours": "Hours",
        "yes": "Yes",
        "no": "No",
        "confirm_delete": "Confirm delete '{}'?",
        "confirm_finish": "Confirm finish plan '{}'?",
        "gantt_chart": "Gantt Chart",
        "time_report": "Time Statistics",
        "participant": "Participant",
        "total_hours": "Total Hours",
        "total_days": "Total Days",
        "percentage": "Percentage",
        "group_total": "Total",
        "font_size": "Font Size",
        "language": "Language",
        "config_dir": "Config Directory",
        "data_dir": "Data Directory",
        "remote_url": "Remote URL",
        "username": "Username",
        "password": "Password/Token",
        "save_config": "Save Config",
        "config_saved": "Config saved",
        "help": "Help",
        "about": "About",
        "more": "More",
        "search_placeholder": "Search nodes...",
        "version": "Version",
        "exit": "Exit",
        "error": "Error",
        "success": "Success",
        "warning": "Warning",
        "input_required": "Please enter {}",
        "invalid_date": "Invalid date format, use YYYYMMDD",
        "plan_status_active": "Active",
        "plan_status_finished": "Finished",
        "refresh": "Refresh",
        "open_in_browser": "Open in Browser",
        "generating_gantt": "Generating Gantt chart...",
        "cli_welcome": "Welcome to GanttPilot CLI",
        "cli_help": "Type 'help' for available commands",
        "cli_unknown_cmd": "Unknown command: {}",
        "cli_bye": "Goodbye!",
        "update_available": "New version v{} available. Download now?",
        "update_check": "Check for Updates",
        "no_update": "Already up to date",
        "zhihu_generated": "Zhihu article generated: {}",
        "project_added": "Project '{}' added",
        "project_deleted": "Project '{}' deleted",
        "milestone_added": "Milestone '{}' added",
        "milestone_deleted": "Milestone '{}' deleted",
        "plan_added": "Plan '{}' added",
        "plan_deleted": "Plan '{}' deleted",
        "plan_finished": "Plan '{}' finished",
        "activity_added": "Activity added",
        "activity_deleted": "Activity deleted",
        "not_found": "Not found: {}",
        "edit_project": "Edit Project",
        "edit_milestone": "Edit Milestone",
        "edit_activity": "Edit Activity",
        "git_config": "Git Config",
        "undo": "Undo",
        "redo": "Redo",
        "undo_tooltip": "Undo (Ctrl+Z)",
        "redo_tooltip": "Redo (Ctrl+Y)",
        "name_duplicate": "Name already exists: {}",
        "name_required": "Name is required",
        "invalid_url": "Invalid repository URL",
        "remote_branch": "Remote Main Branch",
        "undo_done": "Undone",
        "redo_done": "Redone",
        "no_undo": "Nothing to undo",
        "no_redo": "Nothing to redo",
        "color": "Color",
        "set_progress": "Set Progress",
        "progress": "Progress",
        "progress_input": "Enter progress (0-100)",
        "invalid_progress": "Please enter an integer between 0 and 100",
        "completion_rate": "Completion Rate",
        "ahead_of_schedule": "Ahead of Schedule",
        "behind_schedule": "Behind Schedule",
        "load_example": "Load Example",
        "example_loaded": "Example project loaded",
        "file_not_found": "File not found: {}",
        "clone_failed": "Clone failed: {}",
        "cloning": "Cloning...",
        "downloading_update": "Downloading update...",
        "actual_end_date": "Actual End Date",
        "max_segment_days": "Gantt Chart Max Days Per Segment",
        "export_scale": "Export Image Scale Factor",
        "planned_hours": "Planned Hours",
        "committer_name": "Committer Name",
        "committer_email": "Committer Email",
        "priv_branch": "Private Branch",
        "git_not_installed": "Git not found, please install Git first",
        "committer_not_configured": "Please configure committer name and email first",
        "detect_git_user_confirm": "Detected Git user:\nName: {}\nEmail: {}\nUse these?",
        "priv_branch_auto": "Private branch not set, will use \"{}\"",
        "sync_pr_hint": "Pushed to {}, please create PR: {} → {}",
        "bg_check_interval": "Background Check Interval (min)",
        "pull_interval": "Pull Interval (min)",
        "git_log_max_days": "Log Retention Days",
        "main_update_detected": "Main branch has updates, please sync",
        "project_tags": "Project Tags",
        "project_tags_hint": "Comma separated, e.g.: frontend,backend,test",
        "project_members": "Project Members",
        "project_members_hint": "Format: name:abbr,name:abbr  e.g.: John:JN,Alice:AL",
        "invalid_member_format": "Invalid member format, use 'name:abbreviation' separated by commas",
        "duplicate_member_abbr": "Duplicate abbreviation: {}",
        "select_executor": "Please select an executor",
        "committer_fallback_hint": "Leave empty to use global: {} <{}>",
        "manage_tags": "Manage Tags",
        "tag_select": "Select Tag",
        "committer_required": "Committer name and email are required",
        "history": "History",
        "branch": "Branch",
        "no_history": "No history",
        "not_git_repo": "Not a Git repository",
        "main_updated": "Main branch updated",
        "sync_main": "Sync Main",
        "rebase_success": "Rebase successful",
        "rebase_conflict": "Rebase conflict, auto-aborted. Please resolve manually.",
        "rebase_prompt": "Remote main branch updated. Rebase your branch to latest?",
        "time_slots": "Time Slots",
        "time_slots_hint": "Format: HHMM/HHMM,HHMM/HHMM",
        "invalid_time_slots": "Invalid time slots format",
        "effort_hours": "Effort(hours)",
        "effort_hours_hint": "Fill in either this or Time Slots, enter hours directly (e.g. 3.5)",
        "time_slots_or_hours_hint": "Fill in either Effort(hours) or Time Slots, not both",
        "invalid_hours": "Please enter a valid number of hours",
        "hours_non_negative": "Hours must be >= 0",
        "hours_conflict": "Cannot fill both Effort(hours) and Time Slots, please choose one",
        "tag": "Tag",
        "tag_summary": "Tag Summary",
        "commit_author": "Author",
        "commit_date": "Date",
        "commit_message": "Message",
        "commit_diff": "Changes",
        "remote_prefix": "[Remote]",
        "report_by_project": "By Project",
        "report_by_milestone": "By Milestone",
        "report_by_plan": "By Plan",
        "report_by_tag": "By Tag",
        "report_mode": "View Mode",
        "group_col": "Group",
        "reopen": "Reopen",
        "confirm_reopen": "Reopen plan '{}'?",
        "plan_reopened": "Plan '{}' reopened",
        "update_check": "Update",
        "update_available": "New version {} available! Download now?",
        "update_not_ready": "v{} release assets are not ready yet. Please try again later.",
        "update_restart": "v{} update complete. Restarting now.",
        "view_changelog": "View Changelog",
        "view_readme": "View README",
        "downloading_update": "Downloading update...",
        "checking_update": "Checking for updates...",
        "check_update_fail": "Update check failed",
        # ── View detail ──
        "view": "View",
        "view_detail": "View Detail",
        "shortcut_view": "View",
        "view_project": "View Project",
        "view_requirement": "View Requirement",
        "view_task": "View Task",
        "view_milestone": "View Milestone",
        "view_plan": "View Plan",
        "view_activity": "View Activity",
        # ── MCP Server ──
        "mcp_server": "MCP Server",
        "mcp_enabled": "MCP Server enabled",
        "mcp_disabled": "MCP Server stopped",
        "mcp_start": "Start",
        "mcp_stop": "Stop",
        "mcp_status_running": "Running",
        "mcp_status_stopped": "Stopped",
        "mcp_config_title": "MCP Server Config",
        "mcp_config_desc": "GanttPilot MCP Server allows AI assistants (Kiro, Claude, etc.) to manage your project data directly.",
        "mcp_copy_config": "Copy Config",
        "mcp_copied": "Copied to clipboard",
        "mcp_template_kiro": "Kiro Config Template",
        "mcp_template_claude": "Claude Desktop Config Template",
        "mcp_template_generic": "Generic MCP Config Template",
        "mcp_data_dir_label": "Data Directory",
        "mcp_script_path_label": "Script Path",
        # ── Requirement tracking ──
        "requirement_analysis": "Requirement Analysis",
        "plan_execution": "Plan Execution",
        "requirement": "Requirement",
        "task": "Task",
        "category": "Category",
        "subject": "Subject",
        "effort_days": "Effort(days)",
        "linked_task": "Linked Task",
        "tracking_tab": "Requirement Tracking",
        "req_category": "Category",
        "req_subject": "Requirement",
        "task_subject": "Task",
        "linked_plan": "Linked Plan",
        "plan_progress": "Progress",
        "move_up": "Move Up",
        "move_down": "Move Down",
        "edit": "Edit",
        "add_requirement": "Add Requirement",
        "edit_requirement": "Edit Requirement",
        "add_task": "Add Task",
        "edit_task": "Edit Task",
        "edit_plan": "Edit Plan",
        "requirement_added": "Requirement '{}' added",
        "requirement_deleted": "Requirement '{}' deleted",
        "task_added": "Task '{}' added",
        "task_deleted": "Task '{}' deleted",
        "subject_required": "Subject is required",
        "invalid_effort": "Please enter a valid number",
        "effort_non_negative": "Effort must be greater than or equal to 0",
        "report_req_analysis": "Requirement Analysis",
        "report_req_tracking": "Requirement Tracking",
        "actual_hours": "Actual Hours",
        "planned_hours": "Planned Hours",
        "variance": "Variance",
        "total_planned_hours": "Total Planned Hours",
        "total_actual_hours": "Total Actual Hours",
        "project_overtime_summary": "Project Hours (Finished Plans)",
        "task_count": "Tasks",
        "duplicate": "Duplicate",
        "copy": "Copy",
        "cut": "Cut",
        "paste": "Paste",
        "duplicate_tooltip": "Duplicate selected node",
        "copy_tooltip": "Copy (Ctrl+C)",
        "cut_tooltip": "Cut (Ctrl+X)",
        "paste_tooltip": "Paste (Ctrl+V)",
        "nothing_to_paste": "Nothing to paste",
        "paste_type_mismatch": "Cannot paste this type of node here",
        "duplicated": "Duplicated: {}",
        "copied": "Copied: {}",
        "cut_done": "Cut: {}",
        "pasted": "Pasted: {}",
        "overtime": "Overtime",
        "undertime": "Undertime",
        "help_text": (
            "GanttPilot - Collaborative Project Manager\n\n"
            "[Log Path] Application log: <Config Directory>/ganttpilot.log\n\n"
            "[Quick Start]\n"
            "1. Right-click empty area → Add Project (or Load Example)\n"
            "2. Expand Requirement Analysis → Add requirements → Break into tasks\n"
            "3. Expand Plan Execution → Add milestones → Create plans\n"
            "4. Log activities under plans (hours and content)\n"
            "5. Right-click project → Generate Report (Summary or Detail)\n\n"
            "[Project Structure]\n"
            "📋 Requirement Analysis → Requirement → Task (define what)\n"
            "📊 Plan Execution → Milestone → Plan → Activity (plan how)\n"
            "🔗 Plans can link to tasks for requirement traceability\n\n"
            "[Search Filter] Search bar below toolbar\n"
            "• Type keywords to filter tree nodes in real-time\n"
            "• Matching nodes highlighted in blue, non-matching hidden\n"
            "• Click ✕ or clear text to show all nodes\n\n"
            "[Toolbar] Grouped with separators, auto-enabled based on selected node\n"
            "• ↩↪ Undo/Redo │ +✏👁✕ CRUD │ 📋✂📌⧉ Clipboard │ ↑↓ Reorder\n"
            "• Add(Ctrl+N) / Edit(F2) / View(F3) / Delete(Delete)\n"
            "• Copy(Ctrl+C) / Cut(Ctrl+X) / Paste(Ctrl+V) / Duplicate(Ctrl+D)\n"
            "• Move Up(Alt+↑) / Move Down(Alt+↓)\n"
            "• ⚙ Config (language, font, paths, shortcuts)\n"
            "• ⋯ More (check updates, help, MCP server, about)\n\n"
            "[Right-Click Menus] Primary entry for all operations\n"
            "• Empty area → Add Project, Push, Pull, Refresh\n"
            "• Project → Edit, Git Config, Report, Push, Pull, Delete\n"
            "• Requirement/Task → Add, Edit, Copy, Cut, Duplicate, Delete\n"
            "• Milestone → Add Plan, Edit, Color, Delete\n"
            "• Plan → Add Activity, Edit, Color, Progress, Finish/Reopen, Delete\n"
            "• Activity → Edit, Copy, Cut, Duplicate, Delete\n\n"
            "[Right Panel Tabs]\n"
            "• Gantt Chart — Visualize progress, 🔍+/- to zoom\n"
            "• Time Statistics — View by project/milestone/plan/tag, overtime/undertime for finished plans\n"
            "• Requirement Tracking — Requirement→Task→Plan→Progress→Variance chain, shows hours variance for finished plans\n"
            "• History — Git log, switch branches, reset, revert\n\n"
            "[Work Hours] Choose one\n"
            "• Time Slots: 0900/1200,1400/1700 (auto-calculated)\n"
            "• Direct hours: 3.5\n\n"
            "[Activity]\n"
            "• Activities support multi-line description for background notes\n"
            "• Executor defaults to committer name (project > global)\n"
            "• Configure members to use a dropdown for executor (Edit Project → Members)\n\n"
            "[Reports]\n"
            "• Summary: Gantt + requirements + milestones + progress (no hours)\n"
            "• Detail: Full report with all hour breakdowns\n\n"
            "[Skip Dates]\n"
            "• 20260501 → Skip (holiday)\n"
            "• -20260510 → Un-skip (make weekend a workday)\n\n"
            "[Git Collaboration] Ctrl+S Push / Right-click Pull\n"
            "• Each user on private branch, merge via PR\n"
            "• Push shows confirmation dialog with content summary\n"
            "• Auto-fetch main on startup, periodic background check\n"
            "• Exit dialog shows unpushed content and prompts to push\n"
            "• Undo/Redo creates Git commits, visible in History tab\n"
            "• Commits include project.json + requirements/ milestones/ activities/\n"
            "• Pull auto-updates local main, prompts rebase (auto-pushes after)\n"
            "• Right-click project → Sync Main: manually rebase to latest main\n"
            "• Right-click project → Upgrade Main Format: migrate to v2 split format and push\n"
            "• Private branch name cannot be \"priv\" or same as main\n"
            "• Push troubleshooting: check ganttpilot.log in config directory\n"
            "• Log records Git ops, config changes, MCP start/stop and more\n\n"
            "[Committer Info] Required when creating a project\n"
            "• Fallback order: manual input → global config(⚙) → system git config\n"
            "• Blocks creation if none found; configure first\n\n"
            "[Other] Ctrl+Z Undo / Ctrl+Y Redo / Shortcuts customizable\n"
            "• View detail, Config, Activity dialogs support maximize for large text\n\n"
            "[MCP Server] AI Assistant Integration\n"
            "• Click 🔌 to open MCP config, start/stop the server\n"
            "• Supports Kiro, Claude Desktop, and other AI tools\n"
            "• Copy config templates with one click, paste into your tool's config file\n\n"
        ),
        # ── Keyboard shortcuts ──
        "shortcut_add": "Add",
        "shortcut_edit": "Edit",
        "shortcut_view": "View",
        "shortcut_delete": "Delete",
        "shortcut_move_up": "Move Up",
        "shortcut_move_down": "Move Down",
        "shortcut_duplicate": "Duplicate",
        "shortcut_copy": "Copy",
        "shortcut_cut": "Cut",
        "shortcut_paste": "Paste",
        "shortcut_undo": "Undo",
        "shortcut_redo": "Redo",
        "shortcut_push": "Push",
        "shortcut_pull": "Pull",
        "shortcut_sync": "Sync",
        "shortcut_refresh": "Refresh",
        "shortcut_config": "Shortcut Config",
        "shortcut_conflict": "Shortcut \"{}\" is already bound to \"{}\"",
        "shortcut_reset": "Reset to Defaults",
        "shortcut_press_key": "Press new shortcut key...",
        "optional": "optional",
        "reset_to_here": "Reset to Here",
        "confirm_reset": "Reset to this commit? All changes after it will be lost.\n\n{}",
        "reset_done": "Reset to: {}",
        "reset_failed": "Reset failed: {}",
        "revert_commit": "Revert This Commit",
        "confirm_revert": "Revert this commit? A new inverse commit will be created.\n\n{}",
        "revert_done": "Reverted: {}",
        "revert_failed": "Revert failed: {}",
        # ── Report type dialog ──
        "report_type_title": "Select Report Type",
        "report_type_summary": "Summary",
        "report_type_detail": "Detail",
        "report_type_summary_desc": "Gantt chart, requirements, milestones, progress overview (no hours)",
        "report_type_detail_desc": "Full details including hours, notes, etc.",
        # ── Exit push prompt ──
        "exit_push_prompt": "The following changes have not been pushed. Push now?",
        "exit_push_title": "Push Before Exit",
        # ── Manual push confirmation ──
        "confirm_push_title": "Confirm Push",
        "confirm_push_prompt": "Push the following to remote?",
        "unpushed_content_header": "\n\nIncludes:",
        # ── Executor default hint ──
        "executor_default_hint": "Default from committer: {} (priority: activity > project > global)",
        # ── Project creation modes ──
        "mode_local": "Local Mode",
        "mode_collab": "Collaboration Mode",
        "ph_project_name": "Enter project name",
        "ph_description": "Optional, enter project description",
        "ph_remote_url": "e.g. https://github.com/user/repo.git",
        "ph_remote_branch": "Default: main",
        "ph_username": "Git repository username",
        "ph_password": "Personal access token or password",
        "ph_committer_name": "Name for Git commits",
        "ph_committer_email": "Email for Git commits",
        "ph_priv_branch": "Leave empty to auto-generate priv_{committer_name}",
        "url_required": "Remote URL is required",
        "invalid_url_format": "Invalid remote URL format",
        "desc_optional": "(Optional)",
        # ── Private branch validation ──
        "priv_branch_invalid_priv": "Cannot use 'priv' as private branch name",
        "priv_branch_same_as_main": "Private branch name cannot be the same as main branch",
        "priv_branch_invalid_chars": "Branch name contains invalid characters",
        # ── Storage migration ──
        "migration_title": "Storage Format Upgrade",
        "migration_message": "Project data is stored in the old format (activities embedded in project.json).\n\nThe new format stores activities in separate files, significantly reducing Git merge conflicts during collaboration.\n\nMigrate now?",
        "migration_success": "Migration complete. Upgraded storage format for {} project(s).",
        "migration_skipped": "Migration skipped. You will be prompted again on next launch.",
        "migrate_main": "Upgrade Main Format",
        "migrate_main_title": "Upgrade Main Branch Format",
        "migrate_main_confirm": "This will commit the storage format upgrade to the main branch and push to remote.\n\nOther members will auto-migrate when they rebase.\n\nProceed?",
        "migrate_main_running": "Upgrading main branch format...",
        "migrate_main_success": "Main branch format upgraded and pushed to remote.",
    },
}


def t(key, lang="zh", *args):
    """Get translated text"""
    text = TEXTS.get(lang, TEXTS["zh"]).get(key, key)
    if args:
        return text.format(*args)
    return text
