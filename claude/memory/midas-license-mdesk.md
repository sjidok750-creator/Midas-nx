---
name: midas-license-mdesk
description: MIDAS CIVIL NX 인증 오류는 MDesk(라이선스 관문)와 레지스트리 PROTECTION 키부터 확인 — 키를 다시 넣는 건 대개 헛수고
metadata: 
  node_type: memory
  type: reference
  originSessionId: 3608cdcc-51f8-4f29-b15e-59d912b4a76c
  modified: 2026-09-09T06:05:57.086Z
---

MIDAS CIVIL NX가 "인증 문제로 새 작업 열기 안 됨" 증상을 보일 때, 아이디·비번·인증키를 다시 넣는 건 대개 소용없다. 저장될 자리가 망가진 경우가 많다.

## 확인 순서

**1. MDesk 로그** — 여기에 원인이 적혀 있다
```
C:\Users\ahj02\AppData\Roaming\MDesk\logs\<날짜>.log
```
`[error]`만 grep. MDesk는 자동 업데이트가 켜져 있어 업데이트 직후 깨지는 사고가 실제로 있었다.

**2. 레지스트리 PROTECTION 키**
```
HKCU\SOFTWARE\MIDAS\CVLwNX_KR_HYPER_S\PROTECTION   (CIVIL NX)
HKCU\SOFTWARE\MIDAS\CVLw_KR\PROTECTION             (구버전, 정상 동작 시 비교용)
```
정상이면 `AuthType`이 2이고 `PKNumber`(16자리)·`KeyType`·`ServerName`이 채워져 있다.
`AuthType = 0`이고 `PKNumber`가 아예 없으면 인증 설정이 초기화된 것 — 키를 넣어도 저장이 안 된다.

**3. MDesk 프로세스** — CIVIL NX 인증의 관문이다(`WINDOW_START_PROGRAM: true`).
MDesk가 죽어 있으면 CIVIL NX는 라이선스를 못 가져와 메뉴가 전부 비활성으로 뜬다. 좀비가 여러 개(7개까지 본 적 있음) 쌓여도 세션이 꼬인다.
실행 경로: `C:\Users\ahj02\AppData\Local\MIDAS\MDesk\MDesk.exe`

**4. 어카운트 선택** — MDesk 재실행 시 뜨는 화면.
계정 하나에 여러 어카운트(회사/개인)가 붙어 있고, 만료·폐업된 어카운트를 붙잡고 있으면 유효한 라이선스가 있어도 못 쓴다. 라이선스 현황은 `accounts.midasuser.com`에서 확인.

## 2026-09-09 실제 사례

오전 11:46 MDesk 1.9.0 자동 업데이트 → 12:02 `registry.js`의 `setSetting`에서 TypeError → `AuthType`이 0으로 초기화. 라이선스(2027.09.30 만료, 사용자 0명)도 계정도 멀쩡했는데 저장 자리가 깨져서 키 입력이 계속 실패했다. 해결: MDesk 재실행 → 로그인 → 어카운트 재선택.

## 제약

CIVIL NX는 관리자 권한으로 실행되는 경우가 있어, 일반 권한 세션에서는 프로세스 종료(`taskkill /F` 포함)와 키 입력이 모두 `Access is denied`로 거부된다. 이때는 대표님이 작업 관리자로 직접 끄셔야 한다. 우회 불가.

관련: [[midas-mct-syntax]]
