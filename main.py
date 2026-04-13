#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GanttPilot - Collaborative Project Manager
Unified entry script: supports both GUI and CLI modes

Usage:
    GanttPilot              # Launch GUI (default)
    GanttPilot --cli        # Launch CLI
    GanttPilot --cli -l zh  # Launch Chinese CLI
    GanttPilot --version    # Show version
"""

import sys
import argparse
from version import VERSION


def main():
    parser = argparse.ArgumentParser(
        description='GanttPilot - Collaborative Project Manager / 协作式项目管理器',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--cli', action='store_true',
                        help='Launch CLI mode / 启动命令行模式')
    parser.add_argument('--lang', '-l', choices=['zh', 'en'], default=None,
                        help='Language / 语言 (zh: 中文, en: English)')
    parser.add_argument('--version', '-v', action='version',
                        version=f'GanttPilot v{VERSION}')
    parser.add_argument('--zhihu', action='store_true',
                        help='Generate Zhihu article / 生成知乎推广文章')

    args = parser.parse_args()

    if args.zhihu:
        from temp.ganttpilot_zhihu import generate_zhihu_article
        generate_zhihu_article(args.lang or "zh")
    elif args.cli:
        from ganttpilot_cli import main as cli_main
        cli_main(language=args.lang)
    else:
        try:
            from ganttpilot_gui import main as gui_main
            gui_main()
        except ImportError as e:
            print(f"GUI not available: {e}")
            print("Try: GanttPilot --cli")
            sys.exit(1)


if __name__ == '__main__':
    main()
