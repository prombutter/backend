# 문서 작성 지침

| 항목 | 내용 |
|---|---|
| 문서 버전 | v1.6.0 |
| 작성일 | 2026-05-22 |
| 작성자 | 안승준 |

이 지침에 정의된 형식·문체·구조 규칙을 따라 산출물을 작성할 것.
도메인 내용(정책 값, 수치, 실제 데이터)은 각 소비 프로젝트에서 별도 제공한다.

> 본 문서는 ContextBuilder 의 표준 사양서이며, 각 소비 프로젝트 루트에 단독 배포된다.
> 본문이 참조하는 부속 문서(`Context/...`, `Common/...`, `Dev/...` 등)는 모두
> `D:\Project\ContextBuilder\Build\Context\` 하위에 위치하므로 절대 경로로 표기한다.

> ⚠️ **이식성 경고 (단일 머신 가정)**
> 본 문서의 모든 절대 경로 참조는 `D:/Project/ContextBuilder/` 를 가정한다.
> 다른 머신·드라이브·경로로 ContextBuilder 를 이동했다면 본 파일 전체에서
> `D:/Project/ContextBuilder/` 를 새 경로로 일괄 치환해야 한다.
>
> **소비 프로젝트 안내**
> . 본 파일은 ContextBuilder `/deploy` 시 자동 덮어쓰기됨. 소비 프로젝트 고유 규칙은 별도 파일로 분리.
> . 본 배포본에는 운영 규칙(§9 작업로그 자동 기록 등) 이 미포함됨. 작업로그·append-log 자동화는 ContextBuilder 메타 프로젝트 전용.
> . 본 문서가 참조하는 부속 문서는 모두 `D:/Project/ContextBuilder/Build/Context/` 하위에 위치. 동일 머신 접근 필수.

## 폴더 구조

이하 트리는 ContextBuilder 빌더 자체의 폴더 구조이며, 소비 프로젝트의 폴더 구조가 아니다. 소비 프로젝트는 본 CLAUDE.md 한 파일만 루트에 갖는다.

. `Context/` : 참고 문서 보관 폴더. 관점별 작성 규칙·가이드·템플릿을 보관한다. 세부 구조는 아래와 같으며 단일 출처(SSOT) 매트릭스는 [Context/INDEX.md](D:/Project/ContextBuilder/Build/Context/INDEX.md)를 준용한다.
. `Commands/` : 소비 프로젝트 전용 슬래시 명령 보관 폴더. ContextBuilder 배포 시 빈 폴더로 최초 생성되며, 이후 배포에서 제외된다. 소비 프로젝트가 자체 명령을 자유롭게 추가·관리한다.
. `Docs/` : 산출 문서 보관 폴더. 모든 산출물(MD·DOCX·PPTX)은 `Docs/md/`·`Docs/docx/`·`Docs/pptx/` 하위에 확장자별로 생성·저장한다.

### Context/ 세부 구조

```
Context/
├── INDEX.md                     ← 전체 목차·SSOT 매트릭스·문서 의존 관계도 (v2.3.9)
├── 자가점검_워크플로.md         ← 모든 액션 종료 시점에 실행되는 자가점검 구현 지침
├── Common/
│   ├── INDEX.md
│   ├── 가이드/
│   │   ├── 문체/                ← 문체규칙·작문_페르소나 (2) — 문체규칙.md 가 상태표기·이모지·문서유형별 예외 흡수
│   │   └── 표준/                ← 파일명규칙·템플릿목록·사용절차·표너비_가이드·표준용어사전 + 표준용어사전_데이터/ (5)
│   └── 공통섹션/                ← 메타데이터·변경이력·승인기록·영향범위·예외처리_제약사항·용어정리·기본문서 (7)
├── Planning/
│   └── 템플릿/
│       ├── 기획/                ← 제안서·기획서·스토리보드 (3)
│       ├── 요구사항/            ← 요구사항정의서·기능정의서·사용자스토리 (3)
│       ├── 명세/                ← API명세서·기술명세서 (2)
│       ├── 운영/                ← 운영정책·협업프로세스·회의록·주간보고서 (4)
│       └── 검증/                ← 테스트케이스·릴리즈노트 (2)
├── Dev/
│   ├── INDEX.md
│   ├── 품질/                    ← 코딩컨벤션·네이밍규칙·코드리뷰·테스트작성·디렉토리구조·에러처리 (6)
│   ├── 협업/                    ← 브랜치전략·커밋메시지·PR규칙 (3)
│   ├── 운영/                    ← 로깅규칙·환경변수·의존성관리·보안지침·배포전략 (5)
│   └── 아키텍처/                ← (예약, 현재 빈 폴더)
├── Design/
│   ├── INDEX.md
│   ├── 토큰/                    ← 컬러시스템·타이포그래피·간격시스템·아이콘규칙 (4)
│   ├── 레이아웃/                ← 레이아웃그리드·반응형규칙 (2)
│   ├── 컴포넌트/                ← 컴포넌트네이밍·상태표현 (2)
│   ├── 플랫폼/                  ← 플랫폼규칙·네비게이션패턴·제스처규칙 (3)
│   └── 협업/                    ← 접근성·핸드오프 (2)
├── QA/
│   ├── INDEX.md
│   ├── 전략/                    ← 테스트전략·테스트레벨·우선순위기준·심각도기준 (4)
│   ├── 실행/                    ← 테스트환경·테스트데이터·결함관리·리그레션범위 (4)
│   ├── 자동화/                  ← 자동화기준·자동화전략 (2)
│   └── 릴리즈/                  ← 릴리즈검증 (1)
├── DA/
│   ├── INDEX.md
│   ├── 스키마/                  ← 테이블네이밍·컬럼네이밍·데이터타입·PK_FK규칙·인덱스규칙 (5)
│   ├── 이력/                    ← 감사컬럼·이력관리·논리삭제 (3)
│   └── 운영/                    ← 코드테이블·마이그레이션규칙 (2)
└── Security/
    ├── INDEX.md
    ├── 적용/                    ← 적용범위·위협모델_신뢰경계·신규프로젝트_체크리스트 (3)
    ├── 방어/                    ← 인증_세션·요청보안·데이터보호·클라이언트·서버운영·데이터베이스_망 (6)
    ├── 운영/                    ← 운영심화·운영스크립트·운영_워크플로·로컬DB_원격운영 (4)
    ├── 검증/                    ← 침투드릴·외부점검_가이드·펜테스트_체크리스트·취약점_패턴별_대책·펜테스트_적용_이력 (5)
    ├── 규제/                    ← KISA보안조치_가이드·위치기반서비스_보안·GDPR_대응_가이드 (3)
    └── 이력/                    ← 카테고리별_변경히스토리 (1)
```

※ 프로젝트 루트의 `templates/` 는 본 Context 트리와 분리된 **실행 스캐폴드(scaffold) 자산**이다. LLM 이중 Provider 문서 생성 파이프라인·자가점검 CI·Playwright+Axe E2E 템플릿을 포함하며 `/deploy` 배포 대상이 아니다. 소비 프로젝트는 필요한 하위 트리를 수동 이식한다. 상세는 [Context/QA/자동화/자동화전략.md](D:/Project/ContextBuilder/Build/Context/QA/자동화/자동화전략.md) 를 준용한다.

## docx 출력 규칙

. 파일명 형식 : `[문서명]_v[Major].[Minor].[Patch].docx`
. 소스 기준 : 각 문서의 최신 MD 파일을 기준으로 생성한다
. 스타일 기준 : §5 DOCX 표 가독성 지침 및 기존 build 스크립트 스타일(맑은 고딕, 1F4E79/2E75B6 색상 체계) 준수
. 버전 일치 : docx 파일 내 커버·헤더·푸터·변경이력의 버전 표기가 파일명 버전과 반드시 일치해야 한다

각 소비 프로젝트의 산출물 목록·docx 빌드 대상은 해당 프로젝트 내부에서 관리한다. 본 지침은 형식·스타일 규칙만 제공한다.

---

# 1. 형식 선택 기준

문서 목적에 따라 두 가지 형식을 구분하여 사용한다.

## 1.1. 형식 A — 텍스트 나열형

. 사용 상황 : 비즈니스 요건 정리, 정책 초안, 현업 검토용 문서  
. 서술 방식 : `. 항목명 : 내용` 점-콜론 형식  
. 흐름 연결 : `→` 기호 사용  
. 테이블 : 사용하지 않음

## 1.2. 형식 B — 테이블 구조형

. 사용 상황 : 시스템 기획서, FSD, CRUD 명세, PB 명세  
. 서술 방식 : 줄글 단락(개요) + 테이블(명세)  
. 흐름 연결 : 문장 내 서술  
. 테이블 : 구조화된 정보는 반드시 테이블로 표현

---

# 2. 문체 규칙 (공통)

두 형식 모두 아래 규칙을 동일하게 적용한다.

## 2.0. 적용 맥락 분리 — 기획 문체 vs UX 라이팅

문체는 산출물의 소비 주체에 따라 두 갈래로 분리한다.

. **기획·설계 산출물** (FSD·정책서·기획서·CRUD·PB·API명세·시스템 문서 등) → **평서체 `~한다`** 적용. §2.1 이하 전 규칙 사용  
. **UX 라이팅** (실제 시스템에서 사용자가 보는 화면 텍스트 — 버튼 라벨·안내문·알림·에러 메시지·툴팁·이메일·푸시·온보딩 등) → **경어체 `~니다`** 적용 (~합니다, ~됩니다, ~입니다, ~주세요)

구분 기준 : 산출물 독자가 **내부 인력**(개발·기획·운영) 이면 평서체, **최종 사용자**(End User) 면 경어체. 동일 FSD 내에서 시스템 동작 서술은 평서체, 인용된 실제 UI 문구는 따옴표 + 경어체로 표기한다.

```
❌  (UI 문구) 파일을 업로드한다
✅  (UI 문구) "파일을 업로드합니다" 또는 "파일 업로드" (명사형)
```

상세는 [Common/가이드/문체/문체규칙.md §1.0](D:/Project/ContextBuilder/Build/Context/Common/가이드/문체/문체규칙.md) 를 준용한다.

## 2.1. 종결 어미 (기획·설계 산출물)

. 사용 : ~한다, ~이다, ~된다, ~불가하다  
. 금지 : ~합니다, ~할 수 있습니다, ~됩니다, ~해야함

## 2.2. 어휘

. 화면 표시 : 노출한다, 출력한다 / 금지 : 보여준다, 보인다  
. 상태 변경 : 갱신한다, 설정한다, 해제한다, 전환한다 / 금지 : 바꾼다  
. 데이터 저장 : INSERT한다, 저장한다, 기록한다 / 금지 : 넣는다  
. 데이터 삭제 : 삭제한다, 파기한다, 논리 삭제한다 / 금지 : 지운다  
. 제약·불가 : 불가하다, 제한한다, 선행되어야 한다 / 금지 : 안 된다, 못한다

## 2.3. 주어 명시

. 동작 서술 문장에는 행위 주체를 반드시 명시할 것  
. 허용 주어 : System, Server, Client, Admin, User, [역할명]  
. 주어 생략 금지

```
❌  로그인 실패 시 계정이 잠긴다.
✅  로그인 실패 5회 누적 시 System이 계정을 자동 잠금 처리한다.
```

## 2.4. 수치·코드 병기

. 상태값은 반드시 코드와 함께 표기할 것  
. 수치는 단위까지 명시할 것

```
❌  대기 상태 / 충분한 기간
✅  대기(C02101) / 발급일로부터 1년
```

## 2.5. 예외·제약 조건

. 예외 조건은 해당 항목 하단에 별도 행으로 기술할 것  
. `단,` 또는 `※` 으로 시작할 것

```
. 항목명 : 내용
단, [예외 조건]의 경우 [처리 방법]한다.
```

---

# 3. 형식 A 템플릿 — 텍스트 나열형

비즈니스 요건 정리, 정책 초안 작성 시 사용할 것.

## 3.1. 기본 구조

```
# N. [대분류명]

## N.N. [소분류명]

. [항목] : [내용]
. [항목] : [조건] → [결과] → [최종 처리]
. [항목] : [케이스A] / [케이스B] 로 구분

단, [예외 조건]의 경우 [처리 방법]한다.
```

## 3.2. 정책 섹션

```
# N. [정책 대분류]

## N.N. [정책 소분류]

. [항목] : [정책 내용 — ~한다 어미]
. [항목] : [조건A] → [처리A] / [조건B] → [처리B]

단, [예외 조건]의 경우 [처리 방법]한다.
※ [관련 항목 참조]
```

## 3.3. 개념 정의 섹션

유사 개념이 2개 이상인 경우 각각 별도 항목으로 분리하여 정의하고,
마지막에 구분 기준을 명시할 것.

```
## N.N. [개념 정의]

. [개념A] : [정의 내용]
. [개념B] : [정의 내용]
. 구분 기준 : [두 개념을 가르는 핵심 차이]
```

## 3.4. 번호·코드 체계 섹션

```
## N.N. [번호 유형]

. [번호유형] : [구성요소(설명, N자리)] + [구성요소(설명, N자리)] + …
```

## 3.5. 상태값 정의 섹션

```
## N.N. [상태값 분류]

. [상태명](코드) : [이 상태가 되는 조건 또는 의미]
. [상태명](코드) : [조건] → [다음 상태로 전이되는 조건]
```

---

# 4. 형식 B 템플릿 — 테이블 구조형

시스템 기획서, FSD, CRUD 명세, PB 명세 작성 시 사용할 것.

## 4.1. 테이블 필수 항목

아래 항목은 반드시 테이블로 표현할 것. 줄글 나열 금지.

. 상태 정의 : 코드 | 상태명 | 설명 및 트리거 조건  
. 개념 비교 : 구분 기준 | 개념A | 개념B  
. 역할·권한 매트릭스 : 기능 | 역할A | 역할B | …  
. 조건 분기 로직 : 조건 | 동작 | 결과  
. UI 컴포넌트 명세 : UI 컴포넌트 | 필수 | Validation / 시스템 동작  
. CRUD 제약조건 : 컬럼명 | 타입 | 길이 | 필수 | 유니크 | C | U | D | 비고  
. 프로그램 동작 : 단계 | 트리거 | Client 동작 | Server 동작 | DB/외부 연동

## 4.2. 정책 섹션

```
[정책이 규율하는 대상과 목적을 1~2문장 줄글로 서술. 주어 명시.]

| [기준 컬럼] | [정책 내용] |
|---|---|
| [항목] | [~한다 어미로 종결] |

단, [예외 조건]의 경우 [처리 방법]한다.
```

## 4.3. 개념 비교 섹션

유사 개념은 비교 테이블 없이 나열 금지.
비교 테이블 이후 각 개념의 처리 흐름을 반드시 분리하여 작성할 것.

```
[두 개념이 어디서 갈리는지 1문장 서술.]

| 구분 | [개념A] | [개념B] |
|---|---|---|
| 정의 | | |
| 트리거 조건 | | |
| 처리 주체 | | |
| DB 처리 방식 | | |

---

[개념A] 처리 흐름

| 단계 | 처리 주체 | 동작 | 결과 |
|---|---|---|---|
| 1 | | | |

---

[개념B] 처리 흐름

| 단계 | 처리 주체 | 동작 | 결과 |
|---|---|---|---|
| 1 | | | |
```

## 4.4. FSD 모듈 섹션

모듈 개요는 줄글로 작성할 것. 화면 명세는 반드시 테이블로 작성할 것.
화면이 여럿이면 소섹션(N.1, N.2 …)으로 분리할 것.

모듈 개요 필수 포함 항목:

. 모듈 목적 (1문장)  
. 핵심 업무 흐름 요약 (1~2문장)  
. `주요 접근 대상:` 역할 나열  
. `연관 시스템:` 외부 시스템명(연동 내용)  
. `핵심 테이블:` 테이블명 나열

```
[모듈 목적 1문장.]

[핵심 업무 흐름 1~2문장.]

주요 접근 대상: [역할1], [역할2].
연관 시스템: [시스템명(연동 내용)].
핵심 테이블: [TABLE1], [TABLE2].

N.1 [화면명]

| UI 컴포넌트 | 필수 | Validation / 시스템 동작 |
|---|---|---|
| [[유형]] [레이블명] | Y/N | [조건 및 동작 — ~한다 어미] |
```

UI 컴포넌트 유형 표기:  
`[Input]` `[Select]` `[Radio]` `[Checkbox]` `[File]` `[Button]` `[Table]` `[Popup]` `[Tab]`

## 4.5. CRUD 제약조건 섹션

```
| 컬럼명 | 타입 | 길이 | 필수 | 유니크 | C | U | D | 제약 / 비고 |
|---|---|---|---|---|---|---|---|---|
| [컬럼명] | [타입] | [길이/-] | Y/N | Y/- | [C] | [U] | [D] | [~한다 어미] |
```

C/U/D 셀 표기:

. ✅ : 허용  
. ❌ : 불가  
. 자동채번 : 시스템 자동 생성  
. ✅([역할]만) : 특정 역할만 허용  
. ✅(기본 [값]) : INSERT 시 기본값 자동 설정  
. ✅(시스템) : 시스템만 변경 가능

## 4.6. 프로그램 동작 명세 섹션 (PB)

```
| 단계 | 트리거 | Client 동작 | Server 동작 | DB / 외부 연동 |
|---|---|---|---|---|
| [N]. [단계명] | [이 단계를 시작하는 조건] | [프론트 처리] | [백엔드 처리] | [SQL 또는 API 호출] |
```

. 해당 레이어 동작 없으면 `-` 표기  
. DB 연동은 테이블명·조건 포함하여 구체적으로 기술할 것  
. 에러·실패 케이스는 정상 흐름과 별도 행으로 추가할 것

---

# 5. DOCX 표(Table) 가독성 지침

docx 생성 시 표가 깨지거나 텍스트가 잘리는 문제를 방지하기 위해 아래 규칙을 반드시 준수할 것.

## 5.1. 열 너비 산정 원칙

. 기준 폭 : A4 용지, 상하좌우 여백 1인치(1134 DXA) 기준 본문 폭 = **9026 DXA**
. 열 너비 합산 규칙 : 모든 `columnWidths` 합계가 반드시 표 `width`(= 9026)와 일치해야 한다.
. 비율 기반 산정 : 각 열의 예상 내용 길이를 비율로 환산하여 DXA를 계산한다.

```
❌  columnWidths: [2800, 6226]  → 합계 9026 ✅ 이지만, 내용이 긴 열에 좁은 폭 할당
✅  열 비율 판단 기준:
    - 짧은 코드·상태명 열 : 약 15~20% (1350~1800 DXA)
    - 중간 레이블 열      : 약 25~35% (2250~3160 DXA)
    - 설명·내용 열        : 나머지 전체 (잔여 DXA 배정)
```

. 7열 이상 권한 매트릭스 등 다열 표는 `pageBreakBefore: true` 또는 **가로 방향(Landscape)** 레이아웃 섹션을 별도 적용하는 것을 권장한다.

## 5.2. 셀 내 텍스트 줄바꿈 보장

. `TableCell`에 `margins: { top: 100, bottom: 100, left: 160, right: 160 }` 을 반드시 설정한다.
. `TextRun`에 `break` 옵션이나 별도 `Paragraph`로 줄을 분리할 때, 하나의 셀 내에 `Paragraph` 배열로 처리한다.

```javascript
// ✅ 셀 내 여러 줄 처리 — Paragraph 배열 사용
new TableCell({
  margins: { top: 100, bottom: 100, left: 160, right: 160 },
  children: [
    new Paragraph({ children: [new TextRun({ text: "1순위: 선수금", size: 18, font: "맑은 고딕" })] }),
    new Paragraph({ children: [new TextRun({ text: "2순위: 개별 크레딧", size: 18, font: "맑은 고딕" })] }),
  ]
})
```

## 5.3. 행 페이지 분리 방지 (cantSplit)

. 행 내용이 페이지 경계에서 잘리지 않도록 모든 `TableRow`에 `cantSplit: true`를 설정한다.

```javascript
// ✅ 행 분리 방지
new TableRow({
  cantSplit: true,
  children: [ /* cells */ ]
})
```

## 5.4. 헤더 행 반복 (tableHeader)

. 표가 여러 페이지에 걸칠 경우 헤더가 각 페이지에 반복되도록 헤더 행에 `tableHeader: true`를 설정한다.

```javascript
// ✅ 페이지 반복 헤더
new TableRow({
  tableHeader: true,
  cantSplit: true,
  children: [ /* header cells */ ]
})
```

## 5.5. 스트라이프(줄무늬) 적용

. 행 수가 5행 이상인 표는 홀짝 행에 배경색을 교차 적용하여 가독성을 높인다.
. 짝수 행: `fill: "F4F6F8"` (연회색), 홀수 행: `fill: "FFFFFF"` (흰색)

```javascript
// ✅ 스트라이프 적용
rows.map((row, rowIdx) => new TableRow({
  cantSplit: true,
  children: row.map((text, colIdx) => new TableCell({
    shading: { fill: rowIdx % 2 === 0 ? "FFFFFF" : "F4F6F8", type: ShadingType.CLEAR },
    margins: { top: 100, bottom: 100, left: 160, right: 160 },
    width: { size: colWidths[colIdx], type: WidthType.DXA },
    children: [new Paragraph({ children: [new TextRun({ text, size: 18, font: "맑은 고딕" })] })]
  }))
}))
```

## 5.6. 긴 텍스트 셀 처리 지침

. 셀에 들어갈 텍스트가 30자를 초과할 가능성이 있는 열은 전체 폭의 **40% 이상**을 확보한다.
. 콤마(,) 또는 슬래시(/)로 구분되는 나열형 값이 3개 이상이면 셀 내 줄바꿈(`Paragraph` 배열)으로 분리하여 표현한다.
. ✅/❌ 기호만 들어가는 열은 **700~900 DXA**로 좁게 설정한다.

## 5.7. makeTable() + optimalWidths() 권장 구현 패턴

docx 생성 스크립트에서 표 너비는 `colWidths` 인자를 하드코딩하지 않고,
`optimalWidths()` 함수가 실제 데이터를 분석하여 자동 산정한다.

### 핵심 원칙

. 셀 높이(행 수) 최소화 : 각 열의 내용이 최대한 한 줄에 들어오도록 너비를 배분한다.
. 한글 2배 가중 : 한글 1자를 영문 2자 너비로 계산하여 DXA를 산정한다. (단위당 85 DXA)
. 체크박스 열 별도 처리 : ✅/❌ 위주 열은 헤더 텍스트 폭 기준 최소 너비만 할당한다.
. MAX_SINGLE 캡 4500 DXA : 단일 열이 너비를 독점하지 않도록 상한을 둔다.
. surplus 비례 배분 : 남는 공간을 비체크박스 열의 콘텐츠 폭 비례로 배분한다.

```javascript
const CONTENT_W = 9026;

function optimalWidths(headers, rows) {
  const n = headers.length;
  const CELL_MARGIN = 320;  // 좌우 패딩 합계
  const DXA_PER_CW  = 85;   // char_width 단위당 DXA
  const MIN_W       = 700;
  const MAX_SINGLE  = 4500; // 단일 열 최대 너비 캡
  const CHKS = new Set(['✅','❌','-','Y','N','Y/N','✅ *','자동채번']);

  function cw(text) {  // 한글 2배 가중 문자 폭
    let w = 0;
    for (const c of String(text)) w += c.codePointAt(0) > 127 ? 2 : 1;
    return w;
  }

  const colCw = [], colIsChk = [];
  for (let i = 0; i < n; i++) {
    const vals = [headers[i], ...rows.map(r => String(r[i] ?? ''))];
    colCw.push(Math.max(...vals.map(cw)));
    const dv = rows.map(r => String(r[i] ?? '').trim());
    colIsChk.push(dv.length > 0 && dv.filter(v => CHKS.has(v)).length / dv.length > 0.5);
  }

  const minWs = headers.map((h, i) =>
    Math.max(MIN_W, (colIsChk[i] ? cw(h) : colCw[i]) * DXA_PER_CW + CELL_MARGIN)
  );
  const surplus = CONTENT_W - minWs.reduce((a,b)=>a+b,0);

  const weights = colCw.map((c, i) => colIsChk[i] ? 0 : c);
  const wTotal  = weights.reduce((a,b)=>a+b, 0);
  const extra   = wTotal > 0
    ? weights.map(w => Math.floor(surplus * w / wTotal))
    : weights.map(() => Math.floor(surplus / n));
  let result = minWs.map((w, i) => Math.max(MIN_W, w + (surplus > 0 ? extra[i] : 0)));

  // MAX_SINGLE 캡 초과분 재배분
  for (let pass = 0; pass < 3; pass++) {
    const over = result.reduce((a,w,i) => (!colIsChk[i] && w > MAX_SINGLE ? a+(w-MAX_SINGLE) : a), 0);
    if (!over) break;
    result = result.map((w,i) => (!colIsChk[i] && w > MAX_SINGLE) ? MAX_SINGLE : w);
    const others = result.filter((w,i) => !colIsChk[i] && w < MAX_SINGLE).length;
    if (others) result = result.map((w,i) =>
      (!colIsChk[i] && w < MAX_SINGLE) ? Math.min(MAX_SINGLE, w + Math.floor(over/others)) : w
    );
  }

  const tot = result.reduce((a,b)=>a+b,0);
  result[result.length-1] = Math.max(MIN_W, result[result.length-1] + (CONTENT_W-tot));
  return result;
}

function makeTable(headers, rows) {
  const cw = optimalWidths(headers, rows);  // colWidths 하드코딩 불필요
  const stripe = rows.length >= 3;
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: cw,
    rows: [
      new TableRow({ tableHeader: true, cantSplit: true,
        children: headers.map((text, i) => /* hdrCell(text, cw[i]) */ ...) }),
      ...rows.map((row, ri) => new TableRow({ cantSplit: true,
        children: row.map((text, ci) => /* cell(text, cw[ci], stripe 배경) */ ...) }))
    ]
  });
}
```

표준 템플릿(메타 표·기능정의 표·CRUD 표) 의 명시 DXA 값과 행 높이 최소화 체크리스트는 [표너비_가이드.md](D:/Project/ContextBuilder/Build/Context/Common/가이드/표준/표너비_가이드.md) 를 준용한다.

### 2단계 그리기 절차 (필수)

`makeTable()` 은 반드시 아래 2단계를 순서대로 거친다. 1단계만 수행한 결과로 표를 그리지 않는다.

. **1단계 — 초기 폭 산정** : `optimalWidths(headers, rows)` 또는 표준 템플릿 명시 DXA 값으로 1차 열 너비 결정  
. **2단계 — 콘텐츠 기반 재배분** : `rebalanceWidths(headers, rows, initWidths)` 호출. 셀별 예상 줄 수를 측정하여 slack 열(항상 1줄) → bottleneck 열(다중 줄) 로 100 DXA 단위 폭 이전 반복. 표 총 높이 비감소 시 종료

```javascript
function makeTable(headers, rows) {
  const init = optimalWidths(headers, rows);            // 1단계
  const cw   = rebalanceWidths(headers, rows, init);    // 2단계
  assertWidths(headers, cw);                            // 3단계 (게이트 — 필수)
  return new Table({ width: ..., columnWidths: cw, rows: ... });
}
```

3단계 `assertWidths()` 게이트는 합계·길이·최소 폭(≥600 DXA) 위반 시 즉시 throw 하여 빌드를 fail-fast 한다. `optimalWidths()` 자동 산정·`rebalanceWidths()` 재배분·명시 DXA 하드코딩 모든 경로에서 동일 적용한다. 자가점검 사후 검출과 별개로 빌드 단 사전 차단을 보장한다. 구현은 [표너비_가이드.md §7.7](D:/Project/ContextBuilder/Build/Context/Common/가이드/표준/표너비_가이드.md) 준용.

> **`makeTable()` 사용 의무**  
> 모든 표 생성은 반드시 `makeTable(headers, rows)` 함수를 통해 수행한다. 아래 저수준 API 직접 호출은 §9.3 의 "§5 DOCX 표 가독성 위반" 으로 분류한다.
>
> . `new Table({ ... })` 직접 호출 (docx-js)  
> . `document.add_table(...)` 직접 호출 (python-docx)  
> . `slide.shapes.add_table(...)` 직접 호출 (python-pptx, 표 가독성 적용 대상이면 동일)
>
> 위 API 들은 1·2·3단계(`optimalWidths` → `rebalanceWidths` → `assertWidths`) 게이트를 우회하므로 빌드 단 검증이 누락된다. 의도적 우회가 필요한 경우(예: 단일 셀 머리글 표, 페이지 푸터 등) 는 `makeTable()` 에 별도 플래그 파라미터를 추가하여 처리한다.

`rebalanceWidths()` 의 상세 알고리즘·종료 조건·예시는 [표너비_가이드.md §7](D:/Project/ContextBuilder/Build/Context/Common/가이드/표준/표너비_가이드.md) 를 준용한다.

```javascript
const CELL_MARGIN = 320;   // 좌우 패딩 합계
const DXA_PER_CW  = 85;    // char_width 단위당 DXA
const MIN_W       = 700;
const STEP        = 100;   // 한 회차당 이전 폭 (DXA)
const MAX_ITER    = 30;

function cw(text) {
  let w = 0;
  for (const c of String(text)) w += c.codePointAt(0) > 127 ? 2 : 1;
  return w;
}

function lineCount(text, colWidth) {
  const avail = Math.max(1, Math.floor((colWidth - CELL_MARGIN) / DXA_PER_CW));
  return Math.max(1, Math.ceil(cw(text) / avail));
}

function tableHeight(rows, widths) {
  return rows.reduce((sum, row) =>
    sum + Math.max(...row.map((cell, i) => lineCount(cell, widths[i]))), 0);
}

function rebalanceWidths(headers, rows, initWidths) {
  let widths = [...initWidths];
  let prevHeight = tableHeight(rows, widths);

  for (let iter = 0; iter < MAX_ITER; iter++) {
    // 1) 셀별 줄 수 매트릭스
    const lines = rows.map(r => r.map((c, i) => lineCount(c, widths[i])));
    // 2) 열별 최대 줄 수
    const colMaxLines = headers.map((_, i) =>
      Math.max(1, ...lines.map(r => r[i])));

    // 3) bottleneck = 줄수 > 1, slack = 줄수 == 1 인 열
    const bottlenecks = colMaxLines
      .map((n, i) => ({ i, n }))
      .filter(x => x.n > 1)
      .sort((a, b) => b.n - a.n);   // 가장 줄수 많은 열 우선
    const slacks = colMaxLines
      .map((n, i) => ({ i, n, w: widths[i] }))
      .filter(x => x.n === 1)
      .filter(x => x.w - STEP >= Math.max(MIN_W,
        cw(headers[x.i]) * DXA_PER_CW + CELL_MARGIN))
      .sort((a, b) => b.w - a.w);   // 가장 넓은 slack 열 우선

    if (bottlenecks.length === 0 || slacks.length === 0) break;

    // 4) 1회차당 STEP DXA 이전
    const give = bottlenecks[0].i;
    const take = slacks[0].i;
    widths[take] -= STEP;
    widths[give] += STEP;

    // 5) 수렴 검사 — 표 높이가 더 줄어들지 않으면 종료
    const newHeight = tableHeight(rows, widths);
    if (newHeight >= prevHeight) {
      // 직전 이전을 되돌리고 종료
      widths[take] += STEP;
      widths[give] -= STEP;
      break;
    }
    prevHeight = newHeight;
  }
  return widths;
}
```

예시 적용 결과·종료 조건·예외 처리 상세는 [표너비_가이드.md §7.4~§7.6](D:/Project/ContextBuilder/Build/Context/Common/가이드/표준/표너비_가이드.md) 준용

## 5.8. 특수문자 및 이스케이프 처리 지침

docx 생성 스크립트(docx-js 방식)에서 MD 파일의 특수문자가 올바르게 출력되도록 아래 규칙을 준수한다.

### 처리 원칙

. 코드블록 보호 우선 : MD 전체에 이스케이프 해제를 선적용하면 코드블록 내 ` ``` ` 감지가 깨져 이후 전체 내용이 스킵된다. 반드시 줄(line) 단위 또는 셀 단위로 적용한다.
. 표 파이프 구분자 보호 : `\|` 이스케이프 해제를 unescapeMd에 포함하면 표 셀 분리 로직이 파괴된다. `\|` 치환은 금지한다.
. 정규식 메타문자 : `\d`, `\w`, `\W`, `\s`, `\S` 등은 JS 문자열에서 `\d`, `\w` 등으로 정상 처리되므로 별도 치환이 불필요하다.

### unescapeMd() 적용 시점

```javascript
// ❌ 잘못된 방식 — MD 전체 선적용 (코드블록 파괴)
function parseMd(md) {
  md = unescapeMd(md);          // 코드블록 ``` 감지 오작동
  const lines = md.split('\n');
}

// ✅ 올바른 방식 — 줄/셀 단위 적용
function parseMd(md) {
  const lines = md.split('\n'); // 원본 그대로 분리
  // ...
  function flushParagraph(text) {
    const t = unescapeMd(text.trim()); // 텍스트 처리 시점에 적용
  }
  const parseRow = (l) =>
    l.trim().replace(/^\||\|$/g,'').split('|')
     .map(c => unescapeMd(c.trim()));  // 셀 단위 적용
}
```

### unescapeMd() 포함/제외 목록

| 패턴 | 처리 | 비고 |
|---|---|---|
| `\'` `\"` | ✅ 포함 | 따옴표 복원 |
| `\[` `\]` `\(` `\)` | ✅ 포함 | 괄호 복원 |
| `\^` `\~` `\#` `\*` `\$` | ✅ 포함 | MD 특수문자 복원 |
| `\<` `\>` `\+` `\.` `\-` `\!` | ✅ 포함 | MD 특수문자 복원 |
| `\\` | ✅ 포함 (마지막에 적용) | 백슬래시 자체 복원 |
| `\|` | ❌ 제외 | 표 파이프 구분자 파괴 |
| `\n` | ❌ 제외 | 줄 구분 파괴 |
| `\d` `\w` `\W` `\s` `\S` | ❌ 불필요 | JS 문자열에서 자동 처리 |

### MD 원본 작성 규칙

. 표 셀 내 정규식 표현 : `^BGK\d+$` 형태로 단일 백슬래시를 사용한다. 이중 백슬래시(`\d`)는 출력 시 `\d` 로 잘못 표시될 수 있다.
. `[Link]`, `[Input]` 등 UI 컴포넌트 표기 : MD에서 `\[Link\]` 로 이스케이프하지 않고 그대로 `[Link]` 로 작성한다. docx 빌드 시 unescapeMd가 자동 복원한다.

---

# 6. 버전 및 변경이력 규칙

## 6.1. 버전 번호 체계

. Major : 전체 구조 개편, 파트 체계 재설계  
. Minor : 섹션 신설, 모듈 추가, 대규모 보강  
. Patch : 오탈자·토시 수정, 문구 정정

## 6.2. 출력 파일명 작성 규칙

출력 파일명의 버전 표기는 반드시 점(`.`)을 사용하고 언더스코어(`_`) 사용을 금지한다.  
브라우저 다운로드 시 `.` 이 `_` 로 치환되는 현상은 파일명 내 공백·특수문자 처리 방식의 차이에서 발생한다. 버전 구분자로 점을 명시적으로 사용하면 이 치환이 발생하지 않는다.

```
❌  [시스템명]_[문서유형]_v0_3_3.docx   ← 버전 구분자가 언더스코어
✅  [시스템명]_[문서유형]_v0.3.3.docx   ← 버전 구분자가 점
```

. 파일명 구조 : `[시스템명]_[문서유형]_v[Major].[Minor].[Patch].[확장자]`  
. 버전 구분자 : 반드시 점(`.`) 사용. 언더스코어(`_`) 금지  
. 단어 구분자 : 파일명 내 단어 사이는 언더스코어(`_`) 사용

Node.js 스크립트에서 `fs.writeFileSync` 경로를 지정할 때도 동일 규칙을 적용한다.  
버전 문자열을 변수로 관리하는 경우 `sed` 치환이 경로 문자열을 놓칠 수 있으므로, 버전 업 시 내부 버전 문자열과 `writeFileSync` 경로를 함께 수동 확인한다.

```javascript
// ❌ 잘못된 예 — 버전 구분자 언더스코어
fs.writeFileSync('/mnt/user-data/outputs/[시스템명]_[문서유형]_v0_3_3.docx', buf);

// ✅ 올바른 예 — 버전 구분자 점
fs.writeFileSync('/mnt/user-data/outputs/[시스템명]_[문서유형]_v0.3.3.docx', buf);
```

## 6.3. 변경이력 작성

. 버전 오름차순 정렬 유지. 최신 버전을 맨 위에 추가할 것  
. 변경 내용은 섹션 번호를 포함하여 구체적으로 기술할 것

```
❌  내용 추가
✅  §15.5~15.6 공급업체 등록·대시보드 신설
✅  §19 변경 계약 vs 계약 수정 개념 비교표 및 처리 흐름 분리
```

---

# 7. 자가점검 워크플로

모든 액션(문서 작성·수정, 코드 편집, 파일 이동·삭제, 빌드 실행)의 종료 시점 직전에 System이 자동으로 자가점검을 실행한다. 상세 구현 지침은 [Context/자가점검_워크플로.md](D:/Project/ContextBuilder/Build/Context/자가점검_워크플로.md) v1.2.0 을 준용한다.

본 워크플로는 ContextBuilder 메타 프로젝트와 본 사양서를 따르는 소비 프로젝트의 모든 액션에 동일 적용된다.

## 7.1. 핵심 규약

. 실행 시점 : 사용자 최종 보고 직전. 복수 액션이 병렬 수행된 경우 모든 분기 완료 이후 단일 프로세스로 통합 실행한다  
. 회차 진행 : 1회차부터 시작하여 서로 다른 관점의 점검 방법을 중복 없이 선택한다. 전체 회차를 통틀어 최소 10가지 이상의 방법을 동원한다  
. 종료 조건 : 오류 검출 실패가 **3회 연속** 발생한 시점에 종료한다. 10회 상한은 조기 종료 조건이 아니며, 오류가 있는 한 무결성 확보까지 무제한 반복한다  
. 생략 대상 : 단순 조회(Read·Grep·Glob)만 수행한 액션, 질의응답만 수행한 액션은 생략 가능하다. 단, 조회 기반이라도 권장·판단·결론을 제시한 경우 간이 점검(3회)을 수행한다

## 7.2. 점검 방법 풀 (22종)

. 구조 무결성 (M01·M02·M08·M13) : 파일·링크·테이블·교차 참조 존재성  
. 규칙 준수 (M03·M04·M05·M09·M10) : 문체·주어·수치코드·파일명·섹션번호  
. 일관성 (M06·M07·M11·M12·M15) : 메타데이터·변경이력·중복·SSOT·예외표기  
. 완결성 (M14·M16·M17) : 이모지·요청충족·부작용  
. 관점별 특화 (M18·M19·M20·M21·M22) : 코드스타일·DB스키마·테스트·디자인토큰·관점 간 경계

관점별 필수 적용 방법은 [Context/자가점검_워크플로.md §3.2](D:/Project/ContextBuilder/Build/Context/자가점검_워크플로.md) 매핑 표를 준용한다.

## 7.3. 오류 분류 및 처리

. 크리티컬 오류 : 사용자 개입 없이 즉시 자동 수정한다 (깨진 경로·링크, 빌드 유발 문법 오류, 시크릿 노출, 파일명 규칙 위반, 요청 요건 누락 등)  
. 마이너 오류 : 사용자 개입을 받아 수정 여부를 결정한다 (문체 규칙 위반, 주어 누락, 이모지 치환, 오탈자 등)  
. 분류 모호 시 사용자에게 판단을 요청하며, 응답 전까지 해당 건은 보류 상태로 두고 나머지 점검을 진행한다

## 7.4. 보고 양식

자가점검 종료 후 사용자 최종 보고에 아래 항목을 포함한다.

```
[자가점검 결과]
. 총 검증 회차 : N회
. 종료 사유 : (3회 연속 무결성 | 10회 초과 후 3회 연속 무결성 달성)
. 적용 방법 : M01, M02, M03, ... (중복 없는 고유 방법 목록)
. 크리티컬 자동 수정 : N건 — 수정 내역 전부 나열
. 마이너 대기 : N건 — 각 건에 수정 제안 병기
```

---

# 8. Context 참조 우선순위 (SSOT)

산출물 작성 시 규칙이 여러 문서에서 언급되면 단일 출처(Single Source of Truth) 문서를 신뢰원으로 한다. 다른 문서는 SSOT 를 참조하거나 풀어 쓴 가이드이다.

## 8.1. 문서 우선순위

충돌 시 아래 순서로 우선 적용한다.

```
CLAUDE.md > D:/Project/ContextBuilder/Build/Context/Common/공통섹션/ > D:/Project/ContextBuilder/Build/Context/Common/가이드/ > D:/Project/ContextBuilder/Build/Context/관점별(개발·디자인·QA·DA) > D:/Project/ContextBuilder/Build/Context/Planning/템플릿/
```

. 최상위 권위 : `CLAUDE.md` — 형식 선택(§1)·문체(§2)·형식A/B 템플릿(§3·§4)·DOCX 표 가독성(§5)·파일명(§6.2)·자가점검(§7)  
. 공통 양식 : `D:/Project/ContextBuilder/Build/Context/Common/공통섹션/` — 메타데이터·변경이력·승인기록·영향범위·예외처리·용어정리  
. 작성 가이드 : `D:/Project/ContextBuilder/Build/Context/Common/가이드/문체/` (문체규칙·작문_페르소나) · `D:/Project/ContextBuilder/Build/Context/Common/가이드/표준/` (파일명규칙·템플릿목록·사용절차·표너비_가이드·표준용어사전)  
. 관점별 규칙 : `D:/Project/ContextBuilder/Build/Context/Dev/`·`D:/Project/ContextBuilder/Build/Context/Design/`·`D:/Project/ContextBuilder/Build/Context/QA/`·`D:/Project/ContextBuilder/Build/Context/DA/`·`D:/Project/ContextBuilder/Build/Context/Security/` — 각 관점 하위는 서브카테고리(품질/협업/운영/아키텍처·토큰/레이아웃/컴포넌트/플랫폼/협업·전략/실행/자동화/릴리즈·스키마/이력/운영·적용/방어/운영/검증/규제/이력)로 분류된다  
. 문서 템플릿 : `D:/Project/ContextBuilder/Build/Context/Planning/템플릿/` — 기획·요구사항·명세·운영·검증 5개 서브카테고리에 17종 템플릿 (기본문서.md 는 Common/공통섹션/ 로 이동)

## 8.2. 주요 SSOT 매핑

자주 참조되는 규칙의 SSOT 문서는 아래와 같다. 전체 매트릭스는 [Context/INDEX.md §SSOT 매트릭스](D:/Project/ContextBuilder/Build/Context/INDEX.md) 를 준용한다.

| 규칙 영역 | SSOT (단일 출처) |
|---|---|
| 형식 선택 (A/B) | `CLAUDE.md` §1 |
| 문체 (종결 어미·어휘·주어·수치병기) | `D:/Project/ContextBuilder/Build/Context/Common/가이드/문체/문체규칙.md` (CLAUDE.md §2 는 요약) |
| 예외 처리 (`단,`·`※`) | `D:/Project/ContextBuilder/Build/Context/Common/공통섹션/예외처리_제약사항.md` |
| DOCX 표 가독성 | `CLAUDE.md` §5 |
| 파일명 규칙 | `CLAUDE.md` §6.2 (`D:/Project/ContextBuilder/Build/Context/Common/가이드/표준/파일명규칙.md` 는 상세) |
| 변경 이력 양식 | `D:/Project/ContextBuilder/Build/Context/Common/공통섹션/변경이력.md` |
| 자가점검 워크플로 | `CLAUDE.md` §7 (`D:/Project/ContextBuilder/Build/Context/자가점검_워크플로.md` 는 상세) |
| 코딩 스타일·네이밍·브랜치·PR | `D:/Project/ContextBuilder/Build/Context/Dev/` 각 파일 |
| 디자인 토큰·컴포넌트·접근성 | `D:/Project/ContextBuilder/Build/Context/Design/` 각 파일 |
| 테스트 전략·레벨·환경·릴리즈 검증 | `D:/Project/ContextBuilder/Build/Context/QA/` 각 파일 |
| DB 테이블·컬럼·PK/FK·감사컬럼·이력 | `D:/Project/ContextBuilder/Build/Context/DA/` 각 파일 |

## 8.3. 명명 충돌 회피 규약 (소비 프로젝트)

소비 프로젝트는 ContextBuilder 트리 명칭(`Context/`·`Build/`·`Commands/`·`templates/`) 을 자체 폴더명으로 사용하지 않는다. 명명 충돌 시 자동화 스크립트가 잘못된 폴더를 대상으로 삼을 위험이 있다.

| 용도 | 권장 폴더명 | 회피 폴더명 |
|---|---|---|
| 도메인 참고 자료 (정책·매뉴얼·사양서) | `Reference/` 또는 `Domain/` | `Context/` |
| 도메인 산출 문서 | `Docs/` (소문자 `docs/` 도 허용, 프로젝트 내부 일관성 유지) | — |
| 빌드 산출물 (Vite·Webpack 등) | `dist/` 또는 `build/` (소문자) | `Build/` (대문자) |
| 슬래시 명령 (소비 자체) | `Commands/` 사용 가능 (배포 제외 폴더) | — |

. `public/` 폴더 사용 시 주의 : 빌드 도구(Vite·Webpack 등) 가 `public/` 을 `dist/` 로 복사하므로 `public/CLAUDE.md` 같은 사본을 두면 빌드 산출물에도 잔재가 따라간다. CLAUDE.md 는 항상 소비 프로젝트 루트에만 두고, `public/` 에 두지 않는다

## 8.4. 관점별 산출물 적용

. 기획 산출물 : `CLAUDE.md` §1~§6 + `D:/Project/ContextBuilder/Build/Context/Planning/` 전 영역 적용  
. 개발 산출물 : `CLAUDE.md` §6(파일명)·§7(자가점검) + `D:/Project/ContextBuilder/Build/Context/Dev/` 적용. 메타데이터·변경이력 양식은 `D:/Project/ContextBuilder/Build/Context/Common/공통섹션/` 준용  
. 디자인 산출물 : `CLAUDE.md` §6·§7 + `D:/Project/ContextBuilder/Build/Context/Design/` 적용. 상태 표현은 `D:/Project/ContextBuilder/Build/Context/Design/컴포넌트/상태표현.md` 와 `D:/Project/ContextBuilder/Build/Context/Dev/품질/에러처리.md` 간 경계를 준수한다  
. QA 산출물 : `CLAUDE.md` §6·§7 + `D:/Project/ContextBuilder/Build/Context/QA/` 적용. 테스트케이스 양식은 `D:/Project/ContextBuilder/Build/Context/Planning/템플릿/검증/테스트케이스.md` 준용  
. DA 산출물 : `CLAUDE.md` §6·§7 + `D:/Project/ContextBuilder/Build/Context/DA/` 적용. CRUD 제약조건 양식은 `CLAUDE.md` §4.5 준용

---

# 9. 컨텍스트 참조 의무 (소비 프로젝트 강제 규약)

본 섹션은 소비 프로젝트가 본 CLAUDE.md 와 부속 컨텍스트(`D:/Project/ContextBuilder/Build/Context/...`) 를 **선택적 가이드** 가 아닌 **강제 사양** 으로 따르도록 강제하는 규약이다. 본 규약 위반은 자가점검 §7 의 크리티컬 오류로 분류한다.

## 9.1. 적용 범위

. 본 CLAUDE.md 가 배포된 모든 소비 프로젝트의 모든 산출물 작성·수정 작업  
. Claude Code·자동화 스크립트·운영자 직접 편집 모두 동일 적용  
. 단, 소비 프로젝트가 자체 `CLAUDE.local.md` 등 별도 파일에 정의한 도메인 고유 규칙은 본 사양과 충돌하지 않는 한 병존 가능

## 9.2. 강제 의무 사항

. **참조 우선** : §1~§4 형식·문체 규칙, §5 DOCX 표 가독성, §6 파일명 규칙, §7 자가점검, §8 SSOT 매트릭스에 정의된 사항은 **반드시 준수** 한다. 다른 방식으로 작성하지 않는다  
. **부속 문서 참조** : §8.2 SSOT 매핑이 가리키는 부속 문서(`Common/공통섹션/`·`Common/가이드/`·`관점별/`·`Planning/템플릿/`)를 작성 시점에 절대 경로로 직접 조회한다. 캐시·기억·요약본으로 대체하지 않는다  
. **해석 금지** : 본 사양의 규칙을 임의로 완화·일반화·우회하지 않는다. 모호 시 SSOT 우선순위(§8.1)에 따라 상위 문서를 신뢰원으로 선택한다  
. **자가점검 적용** : 모든 액션 종료 시점에 §7 자가점검 워크플로를 가동한다. 단순 조회만 수행한 액션도 권장·결론을 제시한 경우 간이 점검(3회) 을 수행한다  
. **명명 충돌 회피** : §8.3 명명 충돌 회피 규약(권장 폴더명·회피 폴더명) 을 폴더 생성·이름 변경 시 반드시 적용한다  
. **참조 SSOT manifest 의무 기재** : 모든 산출물(MD·DOCX·코드 파일 헤더 주석) 의 메타데이터 또는 머리말에 본 작성에서 실제 참조한 SSOT 절대 경로 목록을 명시한다. 예: `참조 SSOT: D:/Project/ContextBuilder/Build/CLAUDE.md §4.4, D:/Project/ContextBuilder/Build/Context/Common/가이드/표준/표너비_가이드.md §3·§7`. 검증 주체·시점은 자가점검 워크플로 §7 의 회차 진행 중 **M02(링크 유효성)** 가 manifest 의 모든 절대 경로에 대해 PowerShell `Test-Path` 를 자동 호출하여 실재 여부를 확인한다 (산출물 종료 시점 자동 가동). manifest 가 없거나 절대 경로가 하나라도 Test-Path 실패하는 산출물은 §9.3 의 "manifest 미기재 또는 경로 실패" 로 분류한다

## 9.3. 위반 시 처리

| 위반 유형 | 분류 | 처리 |
|---|---|---|
| §1~§4 형식·문체 규칙 위반 | 마이너 | 자가점검 M03·M04 검출 → 운영자 확인 후 수정 |
| §5 DOCX 표 가독성 위반 (표 폭 합계 불일치, 2단계 절차 미수행 등) | 크리티컬 | 자동 수정 + 작업로그 기록 |
| §6 파일명 규칙 위반 (버전 구분자 `_` 사용 등) | 크리티컬 | 자동 수정 (`_` → `.`) + 작업로그 기록 |
| §7 자가점검 워크플로 미수행 | 크리티컬 | 보고 차단 + 자가점검 회차 강제 실행 |
| §8 SSOT 매핑 우회 (대체 규칙 임의 적용) | 크리티컬 | 적용 거부 + 운영자 보고 |
| §8.3 명명 충돌 폴더 생성 (`Context/`·`Build/` 등) | 크리티컬 | 폴더 생성 차단 + 권장명 제안 |
| 컨텍스트 참조 없이 산출물 작성 (캐시·기억으로 대체) | 크리티컬 | 산출물 폐기 + 절대 경로 재조회 후 재작성 |
| 산출물 head 에 참조 SSOT manifest 미기재 또는 manifest 의 절대 경로 Test-Path 실패 | 크리티컬 | manifest 추가·정정 후 자가점검 재가동 |

## 9.4. 자가점검 연동

본 규약 준수 여부는 §7 자가점검 워크플로 가동 시 아래 점검 방법으로 검증한다.

. **M01 파일 존재성** : 절대 경로 참조 대상이 실재하는가  
. **M02 링크 유효성** : 본문에 명시된 절대 경로가 모두 Test-Path 통과하는가  
. **M11 중복·우회** : SSOT 와 다른 규칙이 산출물에 적용됐는가  
. **M22 관점 간 경계** : 관점별 SSOT 분담이 지켜졌는가 (Dev/Design/QA/DA/Security)  
. **M14 요청 충족** : 운영자 요청에 SSOT 반영이 누락됐는가

자가점검 보고 양식(§7.4) 의 "크리티컬 자동 수정" 항목에 본 규약 위반 건수와 수정 내역을 명시한다.

## 9.5. 자동 검증 인프라 (Hooks·Build Gate)

본 규약 준수는 자가점검만으로는 시점 갭이 발생하므로, 아래 두 인프라 검증을 함께 가동한다.

. **SessionStart Hook (CLAUDE.md SHA 검증)** : 소비 프로젝트 `.claude/settings.json` 의 `hooks.SessionStart` 항목이 매 세션 시작 시 아래 명령을 실행한다.

```
powershell -NoProfile -Command "& D:\Project\ContextBuilder\scripts\verify-claude-md.ps1 -Path \"$PWD\""
```

  훅은 `-HookJson` 플래그로 호출되며 SHA-256 불일치 시 Claude Code SessionStart 훅 스펙(`hookSpecificOutput.additionalContext`) JSON 을 stdout 으로 반환한다. 이 JSON 은 Claude 세션 초기 컨텍스트에 강제 주입되어 사용자·LLM 모두 즉시 인지한다. 일치 시 출력 없이 exit 0. 운영자 직접 편집~다음 /deploy 사이의 시점 갭 감지.

  자동 주입 : `/deploy` 가 매 배포 시 `scripts/inject-session-hook.ps1` 을 호출해 소비 `.claude/settings.json` 에 본 훅을 idempotent 등록한다. 운영자 수동 등록 불필요. 환경 호환 : 본 환경은 Windows PowerShell 5.1(`powershell`) 기준이며, `pwsh`(PowerShell 7) 가 설치된 환경에서는 인터프리터를 교체할 수 있다. 단, 명령 형식·인자 패턴은 동일하게 유지한다.

  ⚠ 우회 인지 : Claude Code 의 `--dangerously-skip-permissions` 플래그 또는 settings.json 직접 수정으로 본 훅을 비활성화할 수 있다. 이는 운영자의 의도된 행위로 분류하며, 본 규약은 "정상 모드 사용자가 자기도 모르게 구버전 CLAUDE.md 로 작업하는 사고" 차단을 목표로 한다. 의도적 우회는 운영자 책임이며 작업로그에 사유를 기록해야 한다  
. **Build Gate (`assertWidths()`)** : DOCX·표 생성 빌드 스크립트는 반드시 `makeTable()` 함수를 통해 표를 생성하며, `new Table()` 또는 `docx.Document().add_table()` 등 저수준 API 직접 호출은 금지한다. `makeTable()` 내부에서 `optimalWidths()` → `rebalanceWidths()` → `assertWidths(headers, cw)` 3단계를 강제 실행한다. 합계·길이·최소 폭 위반 시 즉시 throw 로 산출물 생성 차단. §5.7 3단계 게이트 준용

자가점검(§7) 의 사후 검출과 본 인프라 검증의 사전 차단은 상호 보완 관계이며, 둘 중 하나라도 누락 시 §9.3 의 크리티컬로 분류한다.

## 9.6. 운영자 권한

운영자는 본 규약을 변경할 수 없으며, 변경이 필요한 경우 ContextBuilder 메타 프로젝트의 본 CLAUDE.md 원본을 수정 후 `/deploy` 로 일괄 재배포해야 한다. 소비 프로젝트 단독으로 본 사양을 수정한 결과는 다음 `/deploy` 시 무경고 덮어쓰기된다.

---

# 변경 이력

| 버전 | 날짜 | 변경 내용 |
|---|---|---|
| v1.6.0 | 2026-05-22 | Build/Context 전 7관점 원자화·카테고리 그룹화 — Common(가이드 문체·표준 2서브폴더, 문체규칙이 상태표기·이모지·문서유형별예외 흡수, 기본문서 공통섹션 이동), Planning(템플릿 5폴더: 기획·요구사항·명세·운영·검증 + 기술명세서 4분할·API명세서 4분할), Dev(품질·협업·운영·아키텍처 4폴더 + 배포전략 3분할·환경변수 2분할), Design(토큰·레이아웃·컴포넌트·플랫폼·협업 5폴더), QA(전략·실행·자동화·릴리즈 4폴더), DA(스키마·이력·운영 3폴더), Security(적용·방어·운영·검증·규제·이력 6폴더 + 취약점_패턴별_대책 7분할·백엔드협업→운영_워크플로 흡수). 표준용어사전_데이터 행정용어사전 14176행 초성별 4분할·속성명 2077행 2분할. 신규 폴더 29개·이동 95파일·분할 25파일+인덱스 7. 7관점 INDEX 모두 §문서 의존 관계도 신설·본문 절대 경로 마크다운 링크화. manifest Test-Path 387/387 통과 |
| v1.5.5 | 2026-05-19 | §폴더 구조 Docs/ 사양 — `Docs/md/`·`Docs/docx/` 2원 → `Docs/md/`·`Docs/docx/`·`Docs/pptx/` 3원으로 확장. PPTX 산출물(컨셉기획안·매뉴얼 슬라이드 등) 의 확장자별 분리 보관 명시 |
| v1.5.4 | 2026-05-18 | §Context/ 세부 구조 트리 — Security 19종 → 20종 갱신 (GDPR_대응_가이드.md 신규 등재, EU 거주자 대상 자산 도입 시 강제 적용). INDEX.md v2.3.8·Security/INDEX.md v1.0.2 와 정합 |
| v1.5.3 | 2026-05-18 | §Context/ 세부 구조 트리 — Security 16종 → 19종 갱신 (외부점검_가이드·KISA보안조치_가이드·위치기반서비스_보안 3종 신규 등재). 펜테스트체크리스트·취약점패턴별대책 누락분 보강 |
| v1.5.2 | 2026-05-18 | §Context/ 세부 구조 트리 — Security 1종 → 16종 + INDEX 분할 반영 (전사_보안_플레이북.md 단일 거대 파일 폐기, 적용범위·위협모델·인증세션·요청보안·데이터보호·서버운영·데이터베이스망·클라이언트·운영심화·운영스크립트·침투드릴·백엔드협업·카테고리별변경히스토리·신규프로젝트체크리스트·운영워크플로 16종 + INDEX 신설) |
| v1.5.1 | 2026-05-18 | [전체 콘텍스트 정규화] §Context/ 세부 구조 트리 — Common/가이드 8종 → 9종 동기화 (표너비_가이드.md v1.0.0 누락분 반영, INDEX.md v2.3.5·루트 CLAUDE.md v1.2.5 와 정합) |
| v1.5.0 | 2026-05-12 | F2 (a·b·c) 완전 보강 — §9.5 SessionStart 훅에 (a) /deploy 자동 주입 명시 (`scripts/inject-session-hook.ps1` idempotent 등록, 운영자 수동 등록 불필요), (b) `--dangerously-skip-permissions` 우회 인지 명시 (운영자 책임·작업로그 기록), (c) `-HookJson` 모드로 Claude SessionStart 스펙 `hookSpecificOutput.additionalContext` JSON 반환 (Claude 세션 초기 컨텍스트 강제 주입). verify-claude-md.ps1 `-HookJson` 모드 추가, inject-session-hook.ps1 신규, Commands/deploy.md v1.3.0 단계 4 SessionStart 훅 주입 신설 |
| v1.4.1 | 2026-05-10 | 멀티 에이전트 재검증 후속 보강 — F1: §9.5 SessionStart 훅 명령 표기를 settings.json 실제 형식(`powershell -NoProfile -Command "& ..."`)으로 통일 + 인터프리터 환경 안내 추가. F3: §9.2.6 manifest 검증 주체·시점을 자가점검 M02 자동 가동으로 명시. F4: §5.7 `makeTable()` 사용 의무 + `new Table()`·`add_table()` 직접 호출 금지 명시 (저수준 API 우회 차단) |
| v1.4.0 | 2026-05-10 | §9.5 자동 검증 인프라(Hooks·Build Gate) 신설 — SessionStart 훅으로 CLAUDE.md SHA 시점 갭 감지(H1 보강), `assertWidths()` 빌드 게이트로 표 폭 위반 사전 차단(H3 보강). 기존 §9.5 운영자 권한 → §9.6 으로 재번호. §5.7 makeTable 에 3단계 assertWidths 게이트 호출 강제 추가. 표너비_가이드.md v1.2.0 (§7.7 빌드 게이트) 와 연동 |
| v1.3.1 | 2026-05-10 | §9.2 — 강제 의무 6번째 항목 "참조 SSOT manifest 의무 기재" 추가 (산출물 head 메타데이터에 실제 참조한 절대 경로 명시·Test-Path 검증). §9.3 위반 분류 8행으로 확장 (manifest 미기재·경로 실패 = 크리티컬). §7 본문·§폴더 구조 자가점검_워크플로 버전 표기 v1.1.2/v1.1.3 → v1.1.4 동기화 (§3 헤더 17→22종 정정 반영) |
| v1.3.0 | 2026-05-10 | §9 컨텍스트 참조 의무(소비 프로젝트 강제 규약) 신설 — §9.1 적용 범위, §9.2 강제 의무 5종 (참조 우선·부속 문서 절대 경로 조회·해석 금지·자가점검 적용·명명 충돌 회피), §9.3 위반 시 처리 표 7종 (크리티컬·마이너 분류), §9.4 M01·M02·M11·M22·M14 자가점검 연동, §9.5 운영자 권한 (소비 단독 수정 시 /deploy 덮어쓰기). 본 사양을 선택적 가이드가 아닌 강제 사양으로 확정 |
| v1.2.3 | 2026-05-10 | §폴더 구조 트리 — 자가점검_워크플로.md 버전 표기 v1.1.0 → v1.1.3 동기화. 워크플로우 끊김 점검 후속 마이너 수정 |
| v1.2.2 | 2026-05-10 | §5.7 — rebalanceWidths() 함수 본체 인라인 통합. 소비 프로젝트 자기완결성 확보 |
| v1.2.1 | 2026-05-10 | §8.3 명명 충돌 회피 규약(소비 프로젝트) 신설 — 권장/회피 폴더명 표·`public/` 사용 시 주의. 기존 §8.3 → §8.4 로 재번호. 외부 워크플로 검증 결과 소비 프로젝트가 MANUAL.md/프로젝트목록.md 의 §15 규약에 도달 불가하던 결함 해소 |
| v1.2.0 | 2026-05-10 | §5.7 — 2단계 그리기 절차(필수) 신설. 1단계 `optimalWidths()` → 2단계 `rebalanceWidths()` 호출 순서 강제. 콘텐츠 기반 slack→bottleneck 폭 이전으로 행 높이 최소화. 상세 알고리즘은 표너비_가이드.md §7 (v1.1.0) 준용 |
| v1.1.9 | 2026-05-10 | §5.7 makeTable 섹션 말미에 `Common/가이드/표준/표너비_가이드.md` (v1.0.0) 준용 안내 1줄 추가 |
| v1.1.8 | 2026-05-09 | 이식성 경고·소비자 안내·관점 명시 추가 (단일 머신 가정 모델 강화) |
| v1.1.7 | 2026-05-09 | 내부 참조를 절대 경로로 일괄 교체. 단독 배포 시 링크 무결성 확보 |
| v1.1.6 | 2026-05-08 | §폴더 구조 트리 정합성 정정 — 미존재 `참고/` 행 삭제, `Security/` 행 신설, Dev 15종→14종·DA 11종→10종 보정. §7 자가점검_워크플로 참조 버전 v1.1.0 → v1.1.2 갱신 |
| v1.1.5 | 2026-05-07 | 폴더 경로 인덱싱을 영문 폴더명(Planning/Dev/Design)으로 갱신 — §폴더 구조 트리·§8 SSOT 우선순위·SSOT 매핑·관점별 산출물 적용 경로 일괄 갱신 |
| v1.1.4 | 2026-05-07 | 가이드·공통섹션 폴더를 기획에서 신규 Common/ 폴더로 분리. §폴더 구조 트리·§8 SSOT 우선순위·SSOT 매핑·관점별 산출물 적용 경로 일괄 갱신 |
| v1.1.3 | 2026-04-27 | §폴더 구조 — `Commands/` 항목 신설. ContextBuilder 배포 시 빈 폴더로 최초 생성·이후 배포 제외·소비 프로젝트 자체 관리 속성 명시 |
| v1.1.2 | 2026-04-21 | §Context/ 세부 구조 — 디자인 11→14종(플랫폼규칙·네비게이션패턴·제스처규칙 신설), QA 11→12종(자동화전략 신설) 반영 |
| | | §Context/ 세부 구조 — INDEX.md 버전 참조 v2.2 → v2.3 갱신 |
| | | §Context/ 세부 구조 주석 — 프로젝트 루트 `templates/` 실행 스캐폴드 경계 명시 (배포 제외, QA/자동화/자동화전략.md 참조) |
| v1.1.1 | 2026-04-21 | 문서 타이틀 도메인 중립화 — 특정 시스템명 접두어 제거 |
| | | §이 프로젝트의 산출물 섹션 삭제 — 특정 도메인의 5 카테고리 산출물 목록 전면 제거 |
| | | §docx 출력 규칙 도메인 중립화 — 고정 대상 문서 항목 제거, 형식·스타일 규칙만 유지 |
| | | §Context/ 세부 구조 — 특정 도메인 컨셉 정의서 항목 제거, 트리 마지막 표기 보정 |
| | | §6.2 예시 — 고유 시스템명 파일명 예시를 `[시스템명]_[문서유형]` 치환자로 도메인 중립화 |
| v1.1.0 | 2026-04-19 | §폴더 구조 확장 — Context/ 5 관점(기획·개발·디자인·QA·DA) + 참고/ 세부 구조 반영 (개발 15종·디자인 11종·QA 11종·DA 11종·참고 12종, 기획/ 가이드 8·공통섹션 6·템플릿 15) |
| | | §7 자가점검 워크플로 신설 — Context/자가점검_워크플로.md v1.1.0 준용, 22종 점검 방법 풀·3회 연속 무결성 종료·크리티컬/마이너 분류·보고 양식 |
| | | §8 Context 참조 우선순위(SSOT) 신설 — 문서 우선순위(CLAUDE.md > 공통섹션 > 가이드 > 관점별 > 템플릿), 주요 SSOT 매핑, 관점별 산출물 적용 기준 |
| v1.0.5 | 2026-03-23 | §5.7 makeTable() 패턴을 optimalWidths() 방식으로 전면 교체 |
| | | 셀 높이 최소화 원칙, 한글 2배 가중, 체크박스 열 처리, MAX_SINGLE 캡, surplus 비례 배분 |
| v1.0.4 | 2026-03-23 | §5.8 특수문자 및 이스케이프 처리 지침 신설 |
| | | unescapeMd 적용 시점·포함/제외 목록·MD 원본 작성 규칙 |
| v1.0.3 | 2026-03-23 | 프로젝트 산출물 목록 및 docx 출력 규칙 명시 |
| v1.0.2 | 2026-03-23 | §6.2 출력 파일명 작성 규칙 신설 (버전 구분자 점 사용, writeFileSync 경로 주의사항) |
| v1.0.1 | 2026-03-23 | §5 DOCX 표 가독성 지침 신설 (열 너비·cantSplit·헤더 반복·스트라이프·makeTable 패턴) |
| | | §6 버전 및 변경이력 규칙 번호 조정 (구 §5 → §6) |
| v1.0.0 | 2026-03-07 | 최초 작성 — §1 형식 선택 기준, §2 문체 규칙, §3 형식A 템플릿, §4 형식B 템플릿, §5 버전 규칙 |
