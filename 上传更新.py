# -*- coding: utf-8 -*-
"""
一键推送到 GitHub Pages
优先用 git push，网络不通时自动走 GitHub API 兜底。
双击「一键更新到GitHub.bat」即可，不用改任何东西。
"""
import base64
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
REPO = "MFeng99/dianxi-beiyou-travel"
BRANCH = "main"
FILES = ["index.html"]  # 要上传的文件，可自行加
URL = "https://mfeng99.github.io/dianxi-beiyou-travel/"

os.chdir(ROOT)


def log(msg):
    print(msg, flush=True)


def pause(msg="按回车关闭..."):
    try:
        input("\n" + msg)
    except EOFError:
        pass


def run(cmd, timeout=120):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True,
                           text=True, encoding="utf-8", errors="ignore",
                           timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return -1, "timeout"


def get_token():
    env = os.environ.get("GITHUB_TOKEN", "").strip()
    if env:
        return env
    f = ROOT / "token.txt"
    if f.exists():
        return f.read_text(encoding="utf-8").strip()
    return ""


def api(path, method="GET", data=None, timeout=60):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        method=method,
        data=json.dumps(data).encode("utf-8") if data is not None else None,
        headers={
            "Authorization": "Bearer " + get_token(),
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "dianxi-travel-push",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_body": e.read().decode("utf-8", "ignore")[:300]}
    except Exception as e:
        return {"_error": -1, "_body": str(e)[:300]}


def remote_sha(path):
    d = api(f"/repos/{REPO}/contents/{path}?ref={BRANCH}")
    return d.get("sha") if "sha" in d else None


def remote_content(path):
    d = api(f"/repos/{REPO}/contents/{path}?ref={BRANCH}")
    if "content" in d and d.get("encoding") == "base64":
        return base64.b64decode(d["content"])
    return None


def api_upload(path, message):
    p = ROOT / path
    local = p.read_bytes()
    remote = remote_content(path)
    if remote == local:
        return "skip", f"{path} 云端已是最新，无需上传"
    d = api(f"/repos/{REPO}/contents/{path}", "PUT", {
        "message": message,
        "content": base64.b64encode(local).decode("utf-8"),
        "sha": remote_sha(path),
        "branch": BRANCH,
    }, timeout=120)
    if "commit" in d:
        return "ok", f"{path} 已上传（commit {d['commit']['sha'][:8]}）"
    return "fail", f"{path} 上传失败：{d.get('_error')} {d.get('_body', '')[:200]}"


def main():
    log("=" * 46)
    log("  滇西北攻略 · 一键更新到 GitHub")
    log("=" * 46)

    if not get_token():
        log("\n[错误] 找不到 Token。请在 token.txt 里放入 GitHub Token，")
        log("或设置环境变量 GITHUB_TOKEN。")
        input("\n按回车退出...")
        sys.exit(1)

    # 1) 本地提交
    log("\n[1/4] 本地提交...")
    run("git add -A")
    changed = False
    for f in FILES:
        code, out = run(f'git diff --cached --quiet -- "{f}"')
        if code != 0:
            changed = True
            break
    if changed:
        stamp = time.strftime("%Y-%m-%d %H:%M")
        run(f'git commit -m "更新攻略 {stamp}"')
        log("      已提交本地修改")
    else:
        log("      本地没有新修改")

    # 2) 尝试同步远程（git 协议，可能被墙）
    log("\n[2/4] 尝试用 git 同步远程...")
    code, out = run("git fetch origin main", timeout=90)
    if code == 0:
        log("      git 网络正常")
        code2, out2 = run("git pull --rebase --autostash origin main", timeout=90)
        if code2 != 0:
            log("      rebase 有冲突，改为直接用 API 上传")
            code = -1
    if code != 0:
        log("      git 网络连接失败，将走 API 兜底")

    # 3) 推送
    ok = False
    if code == 0:
        log("\n[3/4] git push ...")
        code3, out3 = run("git push origin main", timeout=180)
        if code3 == 0:
            log("      git push 成功")
            ok = True
        else:
            log("      git push 失败：" + out3.strip()[:120])

    if not ok:
        log("\n[3/4] 改用 GitHub API 上传（绕过网络限制）...")
        all_ok = True
        stamp = time.strftime("%Y-%m-%d %H:%M")
        for f in FILES:
            if not (ROOT / f).exists():
                continue
            st, msg = api_upload(f, f"更新攻略 {stamp}")
            log("      " + msg)
            if st == "fail":
                all_ok = False
        ok = all_ok

    # 4) 结果
    log("\n[4/4] 结果")
    if ok:
        log("      更新成功！")
        log("\n      网址（复制到浏览器地址栏打开，不要粘到搜索框）：")
        log("      " + URL)
        log("\n      GitHub Pages 大约 30 秒 ~ 2 分钟生效，刷新即可。")
    else:
        log("      更新失败，请检查网络后重试。")

    log("\n" + "=" * 46)
    pause()


if __name__ == "__main__":
    main()
