#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPTS_ROOT/_lib.sh"

ensure_logs
cd_root

{
  log_header "check_frontend_ia"
  required=(
    "frontend/app/(public)/page.tsx"
    "frontend/app/(public)/tracks/[slug]/page.tsx"
    "frontend/app/(app)/layout.tsx"
    "frontend/app/(app)/spaces/page.tsx"
    "frontend/app/(app)/chat/page.tsx"
    "frontend/app/(app)/plan/page.tsx"
    "frontend/app/(app)/resources/page.tsx"
    "frontend/components/resource/ResourceDiscovery.tsx"
    "frontend/app/(app)/knowledge/page.tsx"
    "frontend/app/(app)/mistakes/page.tsx"
    "frontend/app/(app)/growth/page.tsx"
    "frontend/components/growth/GrowthEvidence.tsx"
    "frontend/components/growth/GrowthSummary.tsx"
    "frontend/lib/nav.ts"
  )
  for path in "${required[@]}"; do
    [[ -f "$path" ]] || { echo "missing $path" >&2; exit 1; }
  done
  grep -q "/spaces" "frontend/app/(app)/spaces/page.tsx"
  grep -q "/resources" "frontend/app/(app)/resources/page.tsx"
  grep -q "ResourceDiscovery" "frontend/app/(app)/resources/page.tsx"
  grep -q "按当前画像推荐" "frontend/components/resource/ResourceDiscovery.tsx"
  grep -q "按学习目标搜索" "frontend/components/resource/ResourceDiscovery.tsx"
  grep -q "B 站" "frontend/components/resource/ResourceDiscovery.tsx"
  grep -q "公开课程" "frontend/components/resource/ResourceDiscovery.tsx"
  grep -q "官方文档" "frontend/components/resource/ResourceDiscovery.tsx"
  grep -q "外部来源策略" "frontend/components/resource/ResourceDiscovery.tsx"
  grep -q "/knowledge/documents" "frontend/app/(app)/knowledge/page.tsx"
  grep -q "/growth/lora-samples" "frontend/app/(app)/growth/page.tsx"
  grep -q "workspaceNavItems" "frontend/lib/nav.ts"
  grep -q "1 对 1 AI 学习导师" "frontend/app/(app)/chat/page.tsx"
  grep -q "构建学习画像" "frontend/components/chat/TutorActionBar.tsx"
  grep -q "生成学习路径" "frontend/components/chat/TutorActionBar.tsx"
  grep -q "生成一组练习" "frontend/components/chat/TutorActionBar.tsx"
  grep -q "复盘一道错题" "frontend/components/chat/TutorActionBar.tsx"
  grep -q "推荐学习资源" "frontend/components/chat/TutorActionBar.tsx"
  grep -q "你正在准备什么课程、考试或项目" "frontend/components/chat/TutorEmptyState.tsx"
  grep -q "PlanTimeline" "frontend/app/(app)/plan/page.tsx"
  grep -q "PlanActionPanel" "frontend/app/(app)/plan/page.tsx"
  grep -q "当前学习路径" "frontend/app/(app)/plan/page.tsx"
  grep -q "推荐理由" "frontend/components/plan/PlanTimeline.tsx"
  grep -q "关联资源" "frontend/components/plan/PlanActionPanel.tsx"
  grep -q 'href="/chat"' "frontend/components/plan/PlanActionPanel.tsx"
  grep -q 'href="/mistakes"' "frontend/components/plan/PlanActionPanel.tsx"
  grep -q "GrowthSummary" "frontend/app/(app)/growth/page.tsx"
  grep -q "GrowthEvidence" "frontend/app/(app)/growth/page.tsx"
  grep -q "成长趋势" "frontend/components/growth/GrowthSummary.tsx"
  grep -q "能力变化" "frontend/components/growth/GrowthSummary.tsx"
  grep -q "薄弱点变化" "frontend/components/growth/GrowthEvidence.tsx"
  grep -q "学习证据" "frontend/components/growth/GrowthEvidence.tsx"
  ! grep -q "对话工作区" "frontend/app/(app)/chat/page.tsx"
  echo "check_frontend_ia: ok"
} 2>&1 | tee -a "$LOG_DIR/check_frontend_ia.log"
