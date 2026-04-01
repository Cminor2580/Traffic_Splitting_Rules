import subprocess
import os
import sys

# ── 从环境变量读取配置 ──────────────────────────────────────────────
_HOST      = os.environ.get("SYNC_HOST")
_TOKEN     = os.environ.get("SYNC_TOKEN")
_FORCE_ALL = os.environ.get("SYNC_FORCE_ALL", "false").lower() == "true"

if not _HOST or not _TOKEN:
    print("❌ 错误：必要的环境变量未设置，请检查配置。")
    sys.exit(1)

# ── 仓库根目录（脚本位于 Scripts/，上一级即为仓库根） ───────────────
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── 全部规则文件（相对仓库根的路径 → 绝对路径） ────────────────────
ALL_RULES = {
    "Rules/ChinaMobile_IPTV.yaml":             os.path.join(REPO_ROOT, "Rules",         "ChinaMobile_IPTV.yaml"),
    "Rules/CustomizedDirect.yaml":             os.path.join(REPO_ROOT, "Rules",         "CustomizedDirect.yaml"),
    "Rules/CustomizedProxy.yaml":              os.path.join(REPO_ROOT, "Rules",         "CustomizedProxy.yaml"),
    "Rules/CustomizedReject.yaml":             os.path.join(REPO_ROOT, "Rules",         "CustomizedReject.yaml"),
}


# ── 通过 git diff 获取本次 push 中实际变动的规则文件 ────────────────
def get_changed_rules() -> list[str]:
    """返回本次 commit 中发生变动的规则文件绝对路径列表。"""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            capture_output=True, text=True, cwd=REPO_ROOT, check=True
        )
    except subprocess.CalledProcessError as e:
        # 首次 commit 时 HEAD~1 不存在，回退到与空树对比
        print("⚠️  无法获取 HEAD~1，尝试与初始状态对比…")
        result = subprocess.run(
            ["git", "diff", "--name-only", "4b825dc642cb6eb9a060e54bf8d69288fbee4904", "HEAD"],
            capture_output=True, text=True, cwd=REPO_ROOT
        )

    changed = set(result.stdout.strip().splitlines())
    matched = [abs_path for rel, abs_path in ALL_RULES.items() if rel in changed]
    return matched


# ── 同步函数 ────────────────────────────────────────────────────────
def sync_file(file_path: str) -> bool:
    file_name = os.path.basename(file_path)

    if not os.path.isfile(file_path):
        print(f"⚠️  跳过（文件不存在）：{file_path}")
        return False

    endpoint = (
        f"https://{_HOST}/config/upload_config"
        f"/customized_clash_rules/{file_name}"
        f"?token={_TOKEN}"
    )

    cmd = [
        "curl",
        "--silent",
        "--show-error",
        "--fail",
        "-X", "POST",
        "--data-binary", f"@{file_path}",
        endpoint,
    ]

    print(f"🔄 正在同步：{file_name}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"✅ 同步成功：{file_name}")
        if result.stdout.strip():
            print(f"   响应：{result.stdout.strip()}")
        return True
    else:
        print(f"❌ 同步失败：{file_name}")
        print(f"   错误：{result.stderr.strip()}")
        return False


# ── 主流程 ──────────────────────────────────────────────────────────
def main():
    print("=" * 50)
    print("  DNS Rules Sync")
    print("=" * 50)

    if _FORCE_ALL:
        # 定时 / 手动触发：全量同步
        print("📋 模式：全量同步（所有规则文件）")
        targets = list(ALL_RULES.values())
    else:
        # push 触发：仅同步本次 commit 中变动的规则文件
        print("🔍 模式：增量同步（仅变动文件）")
        targets = get_changed_rules()
        if not targets:
            print("✅ 本次提交未涉及规则文件，无需同步。")
            return

    print(f"📂 待同步文件数：{len(targets)}")
    print("-" * 50)

    success_count = 0
    fail_count    = 0

    for rule_file in targets:
        if sync_file(rule_file):
            success_count += 1
        else:
            fail_count += 1

    print("-" * 50)
    print(f"📊 完成：成功 {success_count} 个 / 失败 {fail_count} 个")

    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
