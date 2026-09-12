---
name: github-repo-midas-nx
description: "MIDAS 자동화 코드는 GitHub 비공개 레포 sjidok750-creator/Midas-nx(루트 D:\\Midas)에 있다 — 변경은 커밋으로 남기고, 도면·NX 바이너리·납품물은 절대 올리지 않는다"
metadata: 
  node_type: memory
  type: project
  originSessionId: ac048fbe-9263-4808-af0f-0d086cbaf089
  modified: 2026-09-11T23:22:11.708Z
---

2026-09-12 대표님 지시로 D:\Midas 전체를 git 레포로 만들어 https://github.com/sjidok750-creator/Midas-nx (비공개)에 올렸다. 초기 커밋 fc1047b.

- 들어 있는 것: tools, projects/<교량>(계산기·NX 모델 스크립트·제원서·결과 JSON·PNG·MCT·도면 추출 JSON), references(설계기준 원문 PDF·텍스트·편람 요약 — 매번 다시 찾지 않도록 함께 둠), claude/(CLAUDE.md·skills·memory 사본), README, 계획서.
- .gitignore로 막은 것: *.dwg *.dxf(준공도면 원본), *.mcb *.nfxp *.blk(NX 대용량), *.hwpx *.hwp *.xlsx *.docx(납품물), projects/*/report/. MAPI-Key는 레지스트리에서 읽으므로 코드에 값이 없다.
- 대표님이 정한 핵심: "도면을 주면 이 PC의 CIVIL NX를 API로 직접 모델링해 결과를 내는 것"이 코드로 재현돼야 한다. 보고서 조립은 차츰 손본다.

**How to apply:** 세션 시작 시 `git -C D:\Midas status`·`log`로 현재 상태를 보고 시작한다. 도구·계산기를 고치면 커밋 메시지에 왜 바꿨는지 남긴다(대표님이 diff로 확인). 푸시는 대표님 지시가 있을 때. 새 PC에서는 claude/ 아래를 ~/.claude/로 복사. 관련: [[midas-open-api]], [[hwpx-guideline-pointer]], [[diagnosis-report-principles]]
