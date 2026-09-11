---
name: claude-project-roots-dont-move
description: Claude 세션 기록은 절대경로로 키가 걸려 있어, 프로젝트 루트 폴더를 옮기거나 이름 바꾸면 과거 기록이 끊긴다
metadata:
  type: project
---

Claude Code는 세션 기록을 `~/.claude/projects/<경로를-변환한-이름>/`에 저장하고, `~/.claude.json`에도 절대경로를 그대로 기록한다. 2026-09-08 확인 시 D드라이브에서 등록된 루트는 다음 5개:

- `D:\` (세션 14개 — 가장 활발)
- `D:\orca work Claude`
- `D:\workclaude`
- `D:\PIPE CODE`
- `D:\2026년 과업\A. 인천광역시 송수관로 정밀안전점검...`

**Why:** 이 폴더들을 이동하거나 이름을 바꾸면 Claude가 새 프로젝트 디렉터리를 조용히 만들고, 기존 대화 기록은 고아가 된다. 에러가 안 나기 때문에 한참 뒤에야 알아차린다. 메모리 디렉터리(`~/.claude/projects/D--/memory`)도 cwd가 `D:\`이기 때문에 존재하는 것이라, `D:\`를 다른 폴더 밑으로 넣으면 같이 끊긴다.

추가로 2026-09-08 전수 스캔에서 확인: `D:\workclaude`는 세션 기록뿐 아니라 **하위 프로젝트 내부 파일들이 자기 절대경로를 하드코딩**하고 있다 (`pipe`, `RCsection`, `bridge-scour`의 스크립트·문서·PDF 참조에 `D:\workclaude\...` 다수). 이 폴더는 옮기면 Claude 기록과 내부 참조가 함께 깨진다.

**How to apply:** D드라이브 정리·이동 작업 전에 반드시 위 5개 경로를 확인 대상에서 제외한다. 꼭 구조를 바꿔야 하면 실제 폴더는 옮기되 원래 자리에 디렉터리 junction(`mklink /J`)을 남겨 기존 절대경로가 계속 해석되게 한다. 관련: [[claude-md-slim-rule]]
