---
title: "Hello Hugo"
date: 2026-02-25T01:55:56+08:00
lastmod: 2026-02-25T01:55:56+08:00
draft: false
tags: ["Hugo", "建站"]
categories: ["编程技术"]
summary: "使用 Hugo + PaperMod + GitHub Pages 搭建个人学习笔记站点的记录"
description: "记录使用 Hugo 搭建个人学习笔记站点的过程"
ShowToc: true
TocOpen: true
---

## 概述

本站使用 Hugo 静态站点生成器搭建，主题为 PaperMod，部署在 GitHub Pages 上。

## 核心内容

### 技术栈

- **Hugo**：Go 语言编写的静态站点生成器，构建速度极快
- **PaperMod**：极简风格的 Hugo 主题，支持暗色模式、全文搜索
- **GitHub Pages**：免费的静态站点托管服务
- **GitHub Actions**：自动构建和部署

### 日常工作流

1. 使用 `hugo new content notes/xxx/article-name.md` 创建新笔记
2. 用编辑器编写 Markdown 内容
3. `hugo server -D` 本地预览
4. 将 `draft: true` 改为 `draft: false`
5. `git add` + `git commit` + `git push`
6. GitHub Actions 自动构建部署

## 总结

Hugo + GitHub Pages 是一个轻量、免费、维护成本低的个人站点方案，适合以 Markdown 写作为主的学习笔记场景。

## 参考资料

- [Hugo 官方文档](https://gohugo.io/documentation/)
- [PaperMod 主题文档](https://adityatelange.github.io/hugo-PaperMod/)
