# Code_Status.md — 임의 결정 기록

> 이 문서는 **4개 설계 문서에 명시되지 않아 구현 중 임의로 정한 결정**을 기록한다.
> 설계서에 답이 있는 사항은 여기 적지 않는다(설계서가 진실의 원천).
> 각 항목은 **무엇을 / 왜 / 영향 / 되돌릴 때** 형식으로 남긴다.
> 코드를 짜다가 설계서에 없는 선택을 할 때마다 이 문서에 한 줄이라도 추가한다.

---

## 기록 형식

```
### [ID] 제목  (Step N, YYYY-MM-DD)
- 무엇을: 어떤 결정을 내렸는가
- 왜: 설계서에 왜 없었고, 왜 이렇게 정했는가
- 영향: 어떤 모듈/동작에 영향을 주는가
- 되돌릴 때: 나중에 바꾸려면 무엇을 고치면 되는가
```

---

## 사전 식별된 결정 (착수 전 미리 합의)

아래는 Code_Plan 수립 단계에서 이미 드러난, 구현 시 따를 결정들이다. 해당 Step에 도달하면 실제 값과 함께 확정한다.

### [D-01] LLM 백엔드 = OpenRouter (OpenAI 호환), 모델명은 .env  (Step 0)
- 무엇을: LLM 호출은 OpenRouter(OpenAI 호환) 클라이언트로 하고, 모델명은 `.env`의 `OPENROUTER_MODEL`로 주입식 지정한다.
- 왜: 설계서는 LLM 제공자를 명시하지 않음. 기존 프로젝트 config 관례(api_key/model_name/base_url)와 사용자 지시(OpenRouter + .env)를 따름.
- 영향: `twinmarket_kr/llm/client.py`, 모든 LLM 호출(belief/decision/news tool calling).
- 되돌릴 때: `client.py`의 클라이언트 초기화부와 `.env` 키만 교체. 모델 교체는 `.env` 한 줄.

### [D-02] 시뮬레이션 상태 저장소 = SQLite (outputs/sim.db)  (Step 0)
- 무엇을: belief_history / portfolio_state / trade_log / StockData / TradingDetails를 단일 SQLite `sim.db`에 둔다. 선발 결과는 `outputs/sys_100.db`.
- 왜: 설계서는 "이렇게 기록되어야 한다"는 참고 스키마만 제시. 기존 sys_*.db(SQLite) 관례와 일관성·단순성 위해 SQLite 선택.
- 영향: `db/schema.py`, `db/connection.py`, Memory/Exchange Agent.
- 되돌릴 때: connection 계층만 교체하면 Postgres 등으로 이전 가능(스키마 동일).

### [D-03] 원본 sys_1000.db는 읽기 전용  (Step 1)
- 무엇을: `data/sys_1000.db`는 절대 수정하지 않고, 선발 결과만 `outputs/sys_100.db`에 신규 기록.
- 왜: 풀 데이터 보존. 재현성 확보.
- 영향: `persona/select.py`.
- 되돌릴 때: 해당 없음(보존 원칙 유지 권장).

### [D-04] Fundamental 파생지표 계산 (ma20 / volatility_20d / volume_chg)  (Step 3)
- 무엇을: `stock_data.csv`에 `ma_hfq_5/10/30`만 있고 `ma20`이 없음. `ma20`·`volatility_20d`·`volume_chg`는 close 시계열로 파생 계산한다(ma20=20일 단순이동평균, volatility_20d=20일 로그수익률 표준편차, volume_chg=전일 대비 거래량 변화율).
- 왜: 설계서(Overall §6)는 ma20 등을 요구하지만 원본 데이터 컬럼과 불일치.
- 영향: `agents/fundamental_agent.py`.
- 되돌릴 때: stock_data.csv에 해당 컬럼이 생기면 파생 계산을 직접 조회로 교체.
- ※ 실제 컬럼명/존재 여부는 Step 3에서 데이터 확인 후 확정.

### [D-05] News 일일 중요도 계산 = 휴리스틱  (Step 4a)
- 무엇을: 하루 후보 30건 → 일일 10건(종목5/섹터3/경제2) 선정 시 중요도를 휴리스틱(삼성/반도체/거시 키워드 빈도 + 카테고리 가중 + 발행시각)으로 계산한다.
- 왜: News 설계서는 "중요도를 계산한다"만 명시하고 구체 알고리즘 미제시.
- 영향: `scripts/02_prepare_news.py`.
- 되돌릴 때: 중요도 함수만 교체(예: 가격충격 기반·LLM 스코어링).

### [D-06] search_news는 키워드 기반(임베딩 미사용)  (Step 4c)
- 무엇을: `search_news`는 최근 7일 뉴스에서 키워드 중복 등장 수로 점수화·정렬한다. 의미검색(임베딩)은 쓰지 않는다.
- 왜: News 설계 §4.2가 키워드 매칭 방식으로 명시(의미유사도 비의존). 임베딩 인프라 불필요 → 단순화.
- 영향: `agents/news_agent.py`, `.env`의 EMBED_MODEL 비활성.
- 되돌릴 때: 의미검색 필요 시 임베딩 인덱스 추가.

### [D-07] Thinking Depth 부여 방식  (Step 4d)
- 무엇을: 에이전트별 Depth(1/2)는 sys_100 스키마에 없으므로 별도 부여한다. 분포 비율은 config 파라미터로 두고, 선발 후 결정적 시드로 할당(재현성).
- 왜: News 설계는 Depth를 페르소나 속성이라 하지만 Persona 설계의 agents 스키마엔 Depth 컬럼이 없음.
- 영향: `config.py`(Depth 비율), 페르소나 로드부.
- 되돌릴 때: sys_100 스키마에 depth 컬럼을 추가하면 그쪽을 우선 사용.

### [D-08] 100명 LLM 호출 = async 배치  (Step 9)
- 무엇을: 하루 100명×2콜을 비동기 배치로 처리(동시성 상한은 config).
- 왜: 설계서 미명시. 처리량·시간 위해. (원본도 비동기 사용)
- 영향: `simulation.py`, `llm/client.py`(async).
- 되돌릴 때: 동시성 상한을 1로 두면 순차 실행.

### [D-09] 실험 기간·거래 상수 config화  (Step 0)
- 무엇을: 실험 start/end date, 수수료율, 서킷브레이커(±30%), Phase 경계(N_WARMUP=3, N_TRANSITION=4), ini_cash 티어(1억/10억)를 `config.py`에 둔다.
- 왜: 데이터 가용 기간·KRX 규칙에 맞춰 조정 가능해야 함. (Matching §3 기본값 채택)
- 영향: 전 모듈.
- 되돌릴 때: config.py 값만 수정.

---

## 구현 중 추가 결정 (Step 진행하며 누적)

*(여기에 Step별로 새로 내린 임의 결정을 [D-10]부터 추가한다.)*
