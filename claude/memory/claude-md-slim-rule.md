---
name: claude-md-slim-rule
description: D드라이브 루트 CLAUDE.md는 환경 정보만 짧게 유지하고, 긴 업무 지침은 스킬로 분리한다
metadata:
  type: feedback
---

`D:\CLAUDE.md`에는 D드라이브 전역 환경 정보만 짧게 둔다. 특정 업무에만 쓰이는 긴 지침(수백 줄짜리 검토 프레임, 도메인 체크리스트 등)은 CLAUDE.md가 아니라 **스킬**(`~/.claude/skills/<name>/SKILL.md`)로 만든다.

**Why:** CLAUDE.md는 그 폴더에서 시작하는 모든 세션에 통째로 로드된다. 2026-09-08 기준 `D:\CLAUDE.md`가 60KB/913줄(정밀안전점검 보고서 검토 에이전트 사양)이어서, 엑셀 정리든 잡무든 D드라이브의 모든 세션이 매번 이 분량을 읽고 있었다. 스킬은 설명문만 목록에 뜨고 필요할 때만 본문이 로드되므로, 안 쓰는 세션에서 비용이 0이다.

**How to apply:** CLAUDE.md에 긴 지침을 추가하려 할 때 "이게 이 폴더의 *모든* 작업에 필요한가?"를 먼저 묻는다. 아니면 스킬로 만들고 CLAUDE.md에는 한 줄 표로만 남긴다. 분리할 때는 원본을 `.bak-<날짜>`로 백업하고 `diff`로 내용 동일성을 확인한다. 관련: [[claude-project-roots-dont-move]]
