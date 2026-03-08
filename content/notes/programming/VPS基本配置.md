---
title: "VPS 安全配置五步走"
date: 2026-03-09T01:05:56+08:00
lastmod: 2026-03-09T01:05:56+08:00
draft: false
tags: ["VPS", "网络安全", "Linux"]
categories: ["编程技术"]
summary: "从零开始加固一台 VPS：创建 sudo 用户、修改 SSH 端口、配置密钥登录、部署 fail2ban、启用自动安全更新"
description: "记录 VPS 安全加固的完整流程"
ShowToc: true
TocOpen: true
---

## 写在前面

拿到一台新 VPS，第一件事不是装服务，而是把门锁好。这篇文章记录了我从裸机到基本安全加固的完整过程，适用于 Ubuntu / Debian 系统。

---

## 第一步：创建 Sudo 用户并配置免密

拿到 VPS 后通常只有 root 账户。长期用 root 操作风险太大，第一步是创建一个日常使用的管理员账户。

### 创建新用户并赋予 sudo 权限

```bash
# 用 root 登录后执行
ssh root@<你的服务器IP>

# 创建用户
sudo adduser myadmin
sudo usermod -aG sudo myadmin

# 切换到新用户验证
su - myadmin
sudo whoami
# 返回 root 就说明权限没问题
```

### 配置 sudo 免密码

用 `visudo` 编辑配置，不要直接 `vim /etc/sudoers`——`visudo` 会做语法检查，写错了不会把自己锁在外面。

```bash
sudo visudo
```

在文件末尾加一行：

```
myadmin ALL=(ALL) NOPASSWD:ALL
```

各字段的含义：
- `myadmin`：用户名
- 第一个 `ALL`：适用于所有主机
- `(ALL)`：允许以任意用户身份执行
- `NOPASSWD:ALL`：所有命令免密码

保存退出后验证：

```bash
exit  # 回到 myadmin
sudo ls /root
# 不再提示输入密码就算成功
```

### 更安全的做法：用 sudoers.d 子文件

现代 Linux 推荐把自定义配置放在 `/etc/sudoers.d/` 下，升级系统时不会被覆盖：

```bash
echo "myadmin ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/myadmin
sudo chmod 440 /etc/sudoers.d/myadmin
```

如果只想对特定命令免密码（更严格），可以这样写：

```
myadmin ALL=(ALL) NOPASSWD:/bin/systemctl restart sshd,/usr/bin/vim /etc/ssh/sshd_config
```

---

## 第二步：修改 SSH 端口

默认的 22 端口每天都在被扫描器轰炸，换个端口能挡掉绝大多数自动化攻击。

### 注意 systemd socket 激活的坑

Ubuntu 较新版本默认启用了 `ssh.socket`，由 systemd 在 22 端口上监听，等有连接再拉起 sshd。这会绕过你在 `sshd_config` 里改的端口。

用 `ss` 检查一下：

```bash
sudo ss -ltnp | grep ssh
```

如果看到 `"systemd",pid=1` 字样，说明 socket 激活在工作。需要先关掉它。

### 操作步骤

**1. 先配置双端口，防止失联**

编辑 `/etc/ssh/sshd_config`：

```bash
sudo vi /etc/ssh/sshd_config
```

临时保留两个端口：

```
Port 22
Port 2222
```

检查配置语法：

```bash
sudo sshd -t
```

**2. 禁用 socket 激活**

```bash
sudo systemctl stop ssh.socket
sudo systemctl disable ssh.socket
```

有的系统单元名是 `sshd.socket`，如果上面报不存在，换个名字试：

```bash
systemctl status ssh.socket
systemctl status sshd.socket
```

**3. 重启 SSH 服务**

```bash
sudo systemctl daemon-reload
sudo systemctl restart ssh || sudo systemctl restart sshd
```

**4. 验证**

```bash
sudo ss -ltnp | grep -E ':(22|2222)\b|sshd'
```

应该看到 22 和 2222 都由 sshd 监听，不再出现 systemd。

**5. 测试新端口能连上后，去掉旧端口**

用客户端连接 `ssh -p 2222 myadmin@<服务器IP>`，确认正常后，回到 `sshd_config` 注释掉 `Port 22`，只留：

```
Port 2222
```

再重启一次：

```bash
sudo systemctl daemon-reload
sudo systemctl restart ssh || sudo systemctl restart sshd
```

---

## 第三步：配置 SSH 密钥登录

密码登录迟早会被暴力破解，密钥登录才是正道。

### 在本地生成密钥对

```bash
ssh-keygen -t ed25519 -C "your_email@example.com" -f ~/.ssh/id_ed25519_vps
```

会生成两个文件：
- 私钥：`id_ed25519_vps`（绝对不能泄露）
- 公钥：`id_ed25519_vps.pub`（放到服务器上）

### 在服务器上配置公钥

```bash
# 确保 .ssh 目录存在且权限正确
sudo mkdir -p /home/myadmin/.ssh
sudo chmod 700 /home/myadmin/.ssh
sudo chown -R myadmin:myadmin /home/myadmin/.ssh

# 把公钥内容写入 authorized_keys
sudo vim /home/myadmin/.ssh/authorized_keys
# 粘贴公钥（以 ssh-ed25519 开头的那整行），保存退出

# 设置权限
sudo chmod 600 /home/myadmin/.ssh/authorized_keys
sudo chown myadmin:myadmin /home/myadmin/.ssh/authorized_keys
```

权限必须严格，否则 SSH 会直接拒绝：

| 路径 | 权限 | 所有者 |
|------|------|--------|
| `/home/myadmin/.ssh` | 700 | myadmin:myadmin |
| `/home/myadmin/.ssh/authorized_keys` | 600 | myadmin:myadmin |

### 测试密钥登录

```bash
ssh -i ~/.ssh/id_ed25519_vps -p 2222 myadmin@<你的服务器IP>
```

`-i` 指定私钥路径。如果生成密钥时设了密码，这里会要求输入密钥口令（不是服务器密码）。

### 禁用密码登录

确认密钥登录正常后，关掉密码认证：

```bash
sudo vim /etc/ssh/sshd_config
```

修改以下配置项：

```
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
UsePAM yes
```

重启 SSH：

```bash
sudo systemctl restart ssh
```

验证配置是否生效：

```bash
sudo sshd -T | grep passwordauthentication
# 应输出：passwordauthentication no

sudo sshd -T | grep pubkeyauthentication
# 应输出：pubkeyauthentication yes
```

### 连不上的排查思路

```bash
sudo tail -n 30 /var/log/auth.log
```

常见原因：
- `.ssh` 目录或 `authorized_keys` 权限不对
- 文件属于 root 而不是目标用户
- 公钥没完整复制（少了 `ssh-ed25519` 前缀）
- Windows 上密钥路径包含中文或空格

---

## 第四步：部署 fail2ban

改了端口、上了密钥，还会有人拿字典来试。fail2ban 监控登录日志，把多次失败的 IP 自动拉黑。

### 安装

```bash
sudo apt install fail2ban
```

### 配置

```bash
cd /etc/fail2ban
sudo cp jail.conf jail.local
sudo vim jail.local
```

找到 `[sshd]` 段，改成：

```ini
[sshd]
enabled = true
port = 2222
backend = systemd
journalmatch = _SYSTEMD_UNIT=ssh.service
mode = aggressive
maxretry = 5
bantime = 24h
findtime = 10m
```

`mode = aggressive` 会匹配更多类型的失败尝试。`bantime = 24h` 表示封禁 24 小时，`findtime = 10m` 内失败 `maxretry = 5` 次触发封禁。

### 检查配置语法

fail2ban 配置写错会导致服务起不来，改完后先测试：

```bash
sudo fail2ban-client -t
```

看到 `OK: configuration test is successful` 就没问题。

### 启动并设置开机自启

```bash
sudo systemctl restart fail2ban
sudo systemctl enable fail2ban
sudo systemctl status fail2ban
```

可以故意用错密钥连几次试试，被封后错误提示会从 `Permission denied` 变成 `Connection refused`。

---

## 第五步：启用安全补丁自动更新

手动盯着更新不现实。`unattended-upgrades` 可以自动安装安全补丁。

### 安装和启用

```bash
sudo apt install unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

弹出提示时选 **Yes**。

### 验证

```bash
cat /etc/apt/apt.conf.d/20auto-upgrades
```

应该看到：

```
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
```

两项都是 `"1"` 就说明自动更新已启用。

检查服务状态：

```bash
sudo systemctl status unattended-upgrades
```

看到 `Active: active (running)` 就好。

### 关于自动重启

`/etc/apt/apt.conf.d/50unattended-upgrades` 里有个 `Automatic-Reboot` 选项，默认是注释掉的（等同于 `false`）。对于跑服务的 VPS，不建议开启自动重启——内核更新后手动找个合适的时间重启就行。

### Ubuntu 补充说明

Ubuntu 通常预装了 `unattended-upgrades`，默认就会从 `*-security` 仓库拉安全补丁。即使 `50unattended-upgrades` 里没有显式写 `Origins-Pattern`，安全更新也是生效的。只要确认 `20auto-upgrades` 里两项都是 `"1"`，就不用额外操作。

---

## 小结

五步下来，VPS 的基本安全面就有了：

1. 非 root 用户日常操作
2. SSH 端口不用默认值
3. 密钥登录，密码认证关闭
4. fail2ban 自动封禁暴力破解
5. 安全补丁自动更新

这不是万无一失的方案，但能挡掉绝大多数自动化攻击和脚本小子。后续还可以考虑配置防火墙规则（ufw / iptables）、启用 2FA 等进一步加固。
