#!/usr/bin/env bash
# 查 GitHub Actions 最新一次 iOS 构建结果（Windows Git Bash / macOS / Linux 通用）
#
# 用法：
#   bash scripts/ci_status.sh          # 只看最近一次
#   bash scripts/ci_status.sh logs     # 失败时把报错行拉下来打印
#
# 背景：部分机器的 hosts 把 api.github.com 指到了 github.com 的 IP，
# 直接 curl api.github.com 会拿到 HTML 而不是 JSON。本脚本会先探一个可用 IP，
# 再用 --resolve 强制走它，因此不依赖你的 hosts 配置。

set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

REPO=$(git config --get remote.origin.url \
  | sed -E 's#.*github\.com[:/]([^/]+/[^/.]+)(\.git)?$#\1#')
if [ -z "${REPO:-}" ] || [ "$REPO" = "$(git config --get remote.origin.url)" ]; then
  echo "✗ 没找到 origin 远程仓库，请先 git remote add origin <你的仓库地址>"
  exit 1
fi
echo "仓库：$REPO"

TOKEN=$(printf "protocol=https\nhost=github.com\n\n" | git credential fill 2>/dev/null \
  | sed -n 's/^password=//p')
if [ -z "${TOKEN:-}" ]; then
  echo "✗ 拿不到 GitHub 凭据，请先手动 git push 一次完成登录"
  exit 1
fi

# 1) 选一个能正常返回 JSON 的 API IP
IP=""
CANDIDATES=$(grep -iE "^\s*[0-9.]+ +api\.github\.com" /c/Windows/System32/drivers/etc/hosts 2>/dev/null \
  | awk '{print $1}')
CANDIDATES="$CANDIDATES 20.205.243.168 140.82.112.6 140.82.114.6 140.82.116.6"
for ip in $CANDIDATES; do
  code=$(curl -sS --max-time 6 --noproxy '*' --resolve "api.github.com:443:$ip" \
    -o /dev/null -w "%{http_code}" "https://api.github.com/rate_limit" 2>/dev/null)
  if [ "$code" = "200" ]; then IP="$ip"; break; fi
done
if [ -z "$IP" ]; then
  echo "✗ 找不到可用的 api.github.com 出口，请检查网络/代理"
  exit 1
fi

api() {  # api <path>
  curl -sS --noproxy '*' --resolve "api.github.com:443:$IP" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/$REPO$1"
}

TMP=${TMPDIR:-/tmp}/ci_status_$$
mkdir -p "$TMP"

api "/actions/runs?per_page=1" > "$TMP/run.json"
read -r RUN_ID STATUS CONCL SHA MSG URL < <(python - "$TMP/run.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1],encoding='utf-8'))['workflow_runs'][0]
print(r['id'], r['status'], r.get('conclusion') or '-', r['head_sha'][:7],
      (r['head_commit']['message'].splitlines() or [''])[0].replace(' ','_'), r['html_url'])
PY
)

echo "提交：$SHA  $MSG"
echo "网址：$URL"

case "$STATUS/$CONCL" in
  completed/success)
    api "/actions/runs/$RUN_ID/artifacts" > "$TMP/art.json"
    echo "✅ 编译通过（无 error）"
    python - "$TMP/art.json" <<'PY'
import json,sys
for a in json.load(open(sys.argv[1],encoding='utf-8')).get('artifacts',[]):
    print(f"   产物：{a['name']}  {a['size_in_bytes']/1024/1024:.2f} MB（在 Actions 页面底部 Artifacts 下载）")
PY
    ;;
  completed/*)
    echo "❌ 编译失败（$CONCL），报错如下："
    api "/actions/runs/$RUN_ID/logs" > "$TMP/logs.zip"
    python - "$TMP/logs.zip" <<'PY'
import sys,zipfile,re
try:
    z=zipfile.ZipFile(sys.argv[1])
except Exception:
    print("   （日志下载失败，请到 Actions 页面查看）"); raise SystemExit
shown=False
for n in z.namelist():
    if '编译' not in n: continue
    t=z.read(n).decode('utf-8','replace')
    for line in t.splitlines():
        line=re.sub(r'^\S+Z ','',line)
        if '##[error]' in line:
            print('  ', line.replace('##[error]','').strip()[:220]); shown=True
if not shown: print("   （没抓到 error 行，请到 Actions 页面看完整日志）")
PY
    ;;
  *)
    echo "⏳ 正在编译中（$STATUS），预计 1–2 分钟后再查一次"
    ;;
esac
