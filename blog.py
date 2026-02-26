#!/usr/bin/env python3
"""
# QY 学习笔记管理工具
#
# 常见使用场景：
#   - 新建笔记，自动填充 front matter
#   - 本地预览 Hugo 站点
#   - 一键发布到 GitHub（git add/commit/push）
#   - 管理草稿状态（draft: true/false）
#   - 查看文章列表
#
# 参数说明：
#   无需参数，运行后进入交互式菜单
#
# 常见使用命令和用法：
#   python3 blog.py          # 启动交互式管理菜单
"""

import os
import re
import readline  # 启用行编辑支持（方向键、退格、中文输入）
import subprocess
import sys
from datetime import datetime, timezone, timedelta

# ============================================================
# 常量
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.join(SCRIPT_DIR, "content")
TZ = timezone(timedelta(hours=8))

NOTE_SUBCATEGORIES = {
    "1": ("programming", "编程技术"),
    "2": ("reading", "读书总结"),
    "3": ("thinking", "思考感悟"),
}


# ============================================================
# 工具函数
# ============================================================
def now_str():
    """返回当前时间字符串，格式如 2026-02-26T10:00:00+08:00"""
    return datetime.now(TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def input_with_default(prompt, default=""):
    """带默认值的输入，直接回车则使用默认值"""
    if default:
        val = input(f"{prompt} [{default}]: ").strip()
        return val if val else default
    return input(f"{prompt}: ").strip()


def parse_front_matter(filepath):
    """解析 markdown 文件的 front matter，返回 dict 和 body"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    fm = {}
    body = content

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1].strip()
            body = parts[2]
            for line in fm_text.split("\n"):
                line = line.strip()
                if ":" in line:
                    key, _, value = line.partition(":")
                    key = key.strip()
                    value = value.strip()
                    # 去除引号
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    fm[key] = value
    return fm, body


def scan_articles():
    """扫描 content 目录下所有 .md 文章（排除 _index.md）"""
    articles = []
    for root, _dirs, files in os.walk(CONTENT_DIR):
        for fname in files:
            if fname.endswith(".md") and fname != "_index.md":
                filepath = os.path.join(root, fname)
                fm, _ = parse_front_matter(filepath)
                rel_path = os.path.relpath(filepath, SCRIPT_DIR)
                articles.append({
                    "path": rel_path,
                    "title": fm.get("title", fname),
                    "date": fm.get("date", ""),
                    "draft": fm.get("draft", "false").lower() == "true",
                    "categories": fm.get("categories", "[]"),
                    "tags": fm.get("tags", "[]"),
                })
    # 按日期降序
    articles.sort(key=lambda a: a["date"], reverse=True)
    return articles


# ============================================================
# 功能 1: 新建文章
# ============================================================
def create_article():
    print("\n===== 新建笔记 =====")

    # 选择子分类
    print("选择分类：")
    for k, (_, label) in NOTE_SUBCATEGORIES.items():
        print(f"  {k}. {label}")
    sub_choice = input("请输入编号: ").strip()
    if sub_choice not in NOTE_SUBCATEGORIES:
        print("无效选择，返回主菜单。")
        return
    subcategory, subcat_label = NOTE_SUBCATEGORIES[sub_choice]

    # 输入标题
    title = input("\n请输入文章标题: ").strip()
    if not title:
        print("标题不能为空，返回主菜单。")
        return

    # 输入文件名
    filename = input_with_default("请输入文件名（不含 .md 后缀）", "")
    if not filename:
        print("文件名不能为空，返回主菜单。")
        return
    if not filename.endswith(".md"):
        filename += ".md"

    # 输入 tags
    tags_input = input_with_default("请输入 tags（逗号分隔）", "")
    if tags_input:
        tags = [t.strip() for t in re.split(r"[,，]", tags_input) if t.strip()]
        tags_str = "[" + ",".join(f'"{t}"' for t in tags) + "]"
    else:
        tags_str = "[]"

    # 是否为草稿
    draft_input = input_with_default("是否为草稿 (y/n)", "y")
    draft = "true" if draft_input.lower() in ("y", "yes", "") else "false"

    # 生成时间
    date_str = now_str()

    # 确定目标目录和路径
    target_dir = os.path.join(CONTENT_DIR, "notes", subcategory)
    os.makedirs(target_dir, exist_ok=True)
    filepath = os.path.join(target_dir, filename)

    if os.path.exists(filepath):
        overwrite = input(f"文件 {filepath} 已存在，是否覆盖？(y/n) [n]: ").strip()
        if overwrite.lower() not in ("y", "yes"):
            print("已取消。")
            return

    # 生成 front matter
    content = f"""---
title: "{title}"
date: {date_str}
lastmod: {date_str}
draft: {draft}
tags: {tags_str}
series: []
summary: ""
description: ""
ShowToc: true
TocOpen: true
weight: 0
---

## 概述



## 核心内容



## 总结



## 参考资料

-
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    rel_path = os.path.relpath(filepath, SCRIPT_DIR)
    print(f"\n文章已创建: {rel_path}")


# ============================================================
# 功能 2: 本地预览
# ============================================================
def local_preview():
    print("\n===== 本地预览 =====")
    print("启动 Hugo 开发服务器...")
    print("访问地址: http://localhost:1313/")
    print("按 Ctrl+C 停止服务器\n")
    try:
        subprocess.run(
            ["hugo", "server", "-D", "--navigateToChanged"],
            cwd=SCRIPT_DIR,
        )
    except KeyboardInterrupt:
        print("\n服务器已停止。")
    except FileNotFoundError:
        print("错误: 未找到 hugo 命令，请确认已安装 Hugo。")


# ============================================================
# 功能 3: 发布到 GitHub
# ============================================================
def publish():
    print("\n===== 发布到 GitHub =====")

    # 显示 git status
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=SCRIPT_DIR,
        capture_output=True,
        text=True,
    )
    status = result.stdout.strip()
    if not status:
        print("没有需要提交的变更。")
        return

    print("当前变更文件：")
    print(status)
    print()

    # 列出变更文件供用户选择
    lines = status.split("\n")
    files = []
    for i, line in enumerate(lines, 1):
        # git status --short 格式: XY filename
        fname = line[3:].strip()
        # 处理重命名情况
        if " -> " in fname:
            fname = fname.split(" -> ")[1]
        files.append(fname)
        print(f"  {i}. [{line[:2]}] {fname}")

    print(f"\n  a. 添加全部文件")
    choice = input("\n请选择要提交的文件（输入编号，逗号分隔，或 a 全选）: ").strip()

    if choice.lower() == "a":
        selected_files = files
    else:
        try:
            indices = [int(x.strip()) for x in choice.split(",")]
            selected_files = [files[i - 1] for i in indices if 1 <= i <= len(files)]
        except (ValueError, IndexError):
            print("无效输入，返回主菜单。")
            return

    if not selected_files:
        print("未选择任何文件，返回主菜单。")
        return

    print(f"\n将提交以下文件：")
    for f in selected_files:
        print(f"  - {f}")

    # 自动生成 commit message
    today = datetime.now(TZ).strftime("%m%d")
    note_names = []
    other_names = []
    for f in selected_files:
        basename = os.path.basename(f).replace(".md", "")
        if "content/notes/" in f:
            note_names.append(basename)
        else:
            other_names.append(basename)

    if note_names:
        suggestion = f"notes: {', '.join(note_names)}"
    elif other_names:
        suggestion = f"update: {', '.join(other_names)}"
    else:
        suggestion = f"update: {today}"

    msg = input_with_default("\n请输入 commit message", suggestion)
    if not msg:
        print("commit message 不能为空，返回主菜单。")
        return

    # 确认
    confirm = input(f"\n确认提交并推送？(y/n) [y]: ").strip()
    if confirm.lower() in ("n", "no"):
        print("已取消。")
        return

    # git add
    subprocess.run(["git", "add"] + selected_files, cwd=SCRIPT_DIR)

    # git commit
    result = subprocess.run(
        ["git", "commit", "-m", msg],
        cwd=SCRIPT_DIR,
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"提交失败: {result.stderr}")
        return

    # git push
    print("正在推送到 GitHub...")
    result = subprocess.run(
        ["git", "push"],
        cwd=SCRIPT_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print("已推送到 GitHub，GitHub Actions 将自动部署。")
    else:
        print(f"推送失败: {result.stderr}")


# ============================================================
# 功能 4: 草稿管理
# ============================================================
def manage_drafts():
    print("\n===== 草稿管理 =====")
    articles = scan_articles()
    drafts = [a for a in articles if a["draft"]]

    if not drafts:
        print("没有找到草稿文章。")
        return

    print(f"找到 {len(drafts)} 篇草稿：\n")
    for i, d in enumerate(drafts, 1):
        print(f"  {i}. {d['title']}")
        print(f"     路径: {d['path']}  日期: {d['date']}")

    choice = input("\n请输入要发布的文章编号（逗号分隔，或直接回车返回）: ").strip()
    if not choice:
        return

    try:
        indices = [int(x.strip()) for x in choice.split(",")]
    except ValueError:
        print("无效输入。")
        return

    current_time = now_str()
    for idx in indices:
        if 1 <= idx <= len(drafts):
            draft = drafts[idx - 1]
            filepath = os.path.join(SCRIPT_DIR, draft["path"])
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # 将 draft: true 改为 draft: false
            content = re.sub(
                r"^(draft:\s*)true\s*$",
                r"\g<1>false",
                content,
                count=1,
                flags=re.MULTILINE,
            )
            # 更新 lastmod
            content = re.sub(
                r"^(lastmod:\s*).*$",
                rf"\g<1>{current_time}",
                content,
                count=1,
                flags=re.MULTILINE,
            )

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  已发布: {draft['title']}")
        else:
            print(f"  编号 {idx} 无效，已跳过。")


# ============================================================
# 功能 5: 文章列表
# ============================================================
def list_articles():
    print("\n===== 文章列表 =====")
    articles = scan_articles()

    if not articles:
        print("没有找到文章。")
        return

    print(f"共 {len(articles)} 篇文章：\n")
    for a in articles:
        draft_tag = " [草稿]" if a["draft"] else ""
        print(f"  {a['date'][:10]}  {a['title']}{draft_tag}")
        print(f"             分类: {a['categories']}  标签: {a['tags']}")
        print(f"             路径: {a['path']}")
        print()


# ============================================================
# 主菜单
# ============================================================
def main():
    while True:
        print("\n===== QY 学习笔记管理工具 =====")
        print("  1. 新建笔记")
        print("  2. 本地预览")
        print("  3. 发布到 GitHub")
        print("  4. 草稿管理")
        print("  5. 文章列表")
        print("  0. 退出")

        choice = input("\n请选择操作: ").strip()

        if choice == "1":
            create_article()
        elif choice == "2":
            local_preview()
        elif choice == "3":
            publish()
        elif choice == "4":
            manage_drafts()
        elif choice == "5":
            list_articles()
        elif choice == "0":
            print("再见！")
            break
        else:
            print("无效选择，请重新输入。")


if __name__ == "__main__":
    main()
