#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT_DIR"

test -f frontend/app/\(app\)/profile/page.tsx
test -f frontend/lib/profileApi.ts
test -f frontend/components/profile/ProfileOverview.tsx
test -f frontend/components/profile/ProfileEvidence.tsx

grep -q "学习画像" frontend/app/\(app\)/profile/page.tsx
grep -q "系统记住了什么" frontend/app/\(app\)/profile/page.tsx
grep -q "getProfileSummary" frontend/lib/profileApi.ts
grep -q "知识基础" frontend/components/profile/ProfileEvidence.tsx
grep -q "薄弱点" frontend/components/profile/ProfileEvidence.tsx
grep -q "错题模式" frontend/components/profile/ProfileEvidence.tsx
grep -q "学习画像" frontend/lib/nav.ts

echo "check_profile_page -> ok"
