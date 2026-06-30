# GitHub 同步恢复指南

## 当前状态

本地仓库已经配置 remote：

```text
origin https://github.com/david-gao1/agent-learn.git
```

当前本地 `main` 相对 `origin/main` 是：

```text
behind: 0
ahead: positive
```

具体领先提交数以 `scripts/check_external_readiness.sh` 输出为准。也就是说：远端没有本地缺失的提交，本地可以快进推送；阻塞点不是 git 历史冲突，而是 GitHub 凭据。

## 当前阻塞

HTTPS 推送失败的原因：

```text
git: 'credential-osxkeychain' is not a git command
fatal: could not read Username for 'https://github.com': Device not configured
```

SSH 也暂不可用：

```text
git@github.com: Permission denied (publickey).
```

因此当前有两条恢复路径：修 HTTPS 凭据，或改用 SSH remote。

## 推送前检查

先运行：

```bash
scripts/check_external_readiness.sh
scripts/verify_offline.sh
```

确认：

- `working_tree: clean`
- `behind_origin: 0`
- `offline_verifier: available`
- `credential_helper_available` 是否可用
- `ssh_github_auth` 是否可用
- `scripts/verify_offline.sh` 通过

如果 readiness 输出：

```text
Fix git credential helper or switch to SSH before pushing.
Authorize an SSH key with GitHub if using SSH remote.
```

说明当前 HTTPS 和 SSH 两条推送路径都还没准备好，需要先修其中一条。

## 路径一：修 HTTPS 凭据

如果继续使用当前 HTTPS remote，可以任选一种方式恢复认证。

### 方式 A：安装或修复 macOS credential helper

当前 git 配置使用：

```bash
git config --get credential.helper
```

预期输出：

```text
osxkeychain
```

但当前环境找不到 `git-credential-osxkeychain`。修复后确认：

```bash
command -v git-credential-osxkeychain
scripts/check_external_readiness.sh
```

然后再推送：

```bash
git push origin main
```

### 方式 B：临时改用 cache/store helper

如果不想修 osxkeychain，可以改用其他 credential helper。注意不要把 token 写进仓库。

例如只对当前仓库修改：

```bash
git config credential.helper cache
git push origin main
```

Git 会提示输入 GitHub 用户名和 token。

## 路径二：改用 SSH remote

当前 SSH 未授权，所以需要先把本机 public key 加到 GitHub。

查看 public key：

```bash
cat ~/.ssh/id_ed25519.pub
```

把输出添加到 GitHub SSH keys 后验证：

```bash
ssh -T git@github.com
```

成功后把 remote 改为 SSH：

```bash
git remote set-url origin git@github.com:david-gao1/agent-learn.git
scripts/check_external_readiness.sh
git push origin main
```

## 推送后检查

推送成功后运行：

```bash
git status --short --branch
scripts/check_external_readiness.sh
```

期望：

```text
behind_origin: 0
ahead_of_origin: 0
working_tree: clean
```

然后到 GitHub 查看 Actions 是否执行：

```text
Offline Tests
```

该 workflow 会运行：

```bash
scripts/verify_offline.sh
```

## 不要做的事

- 不要 `git reset --hard`。
- 不要 `git clean -fd`。
- 不要把 token 写入文件或提交。
- 不要为了推送而删除本地领先远端的提交。
- 不要在没有确认远端状态时 force push。

## 当前最短路径

如果你只想尽快同步：

1. 修好 GitHub HTTPS 凭据或 SSH key。
2. 运行 `scripts/check_external_readiness.sh`，确认 `credential_helper_available` 或 `ssh_github_auth` 可用。
3. 运行 `scripts/verify_offline.sh`。
4. 运行 `git push origin main`。
5. 确认 `scripts/check_external_readiness.sh` 显示 `ahead_of_origin: 0`。
