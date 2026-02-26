### [파일명: Project Redvelvet_IM_v5.pdf]




Strictly Private and Confidential
2
DRAFT
Disclaimer


Strictly Private and Confidential
3
DRAFT
Glossary




Strictly Private and Confidential
5
DRAFT
I. Executive Summary
16.7%
10,549,700
20.5%
10,549,700
14.8%
9,352,840
18.2%
9,352,840
5.1%
3,199,114
5.0%
2,555,480
4.0%
2,521,200
4.9%
2,521,200
2.7%
1,718,520
3.3%
1,718,520
SV인베스트먼트
2.6%
1,620,860
3.1%
1,620,860
카카오벤처스
2.2%
1,366,980
2.7%
1,366,980
Pavillion Capital
2.2%
1,365,180
2.7%
1,365,180
지유투자
2.0%
1,247,020
2.4%
1,247,020
인터베스트
1.9%
1,193,860
2.3%
1,193,860
KB인베스트먼트
28.4%
17,999,100
35.0%
17,999,100
기타주주
82.4%
52,134,374
100.0%
51,490,740
기존주주소계
8.5%
5,363,619
-
-
국민성장펀드
3.1%
1,930,903
-
-
당펀드
0.3%
214,545
-
-
노앤Blind
5.8%
3,647,260
-
-
타GP
17.6%
11,156,327
신규주주소계
100.0%
63,290,701
100.0%
51,490,740


Strictly Private and Confidential
6
DRAFT
RCPS Term Sheet(안)
I. Executive Summary


Strictly Private and Confidential
7
DRAFT
PEF Term sheet(안)
I. Executive Summary


Strictly Private and Confidential
8
DRAFT
Funding History
I. Executive Summary
설립이후누적6,400억원투자유치, Pre-money Valuation ‘21년1,900억원→ ‘26년[2.3]조원으로급성장


Strictly Private and Confidential
9
DRAFT
Deal Timeline
I. Executive Summary


Strictly Private and Confidential
10
DRAFT
01
Investment Highlight
02
03
04
05
I. Executive Summary




Strictly Private and Confidential
12
DRAFT
회사개요
II. 대상회사분석


Strictly Private and Confidential
13
DRAFT


Strictly Private and Confidential
14
DRAFT
제품라인업
II. 대상회사분석
NPU 카드, 서버, 랙단위까지다양한스케일의AI 서비스를위한HW 솔루션라인업보유
RSD(Rebellions Scalable Design) 아키텍처를기반으로, 규모가커질수록성능과효율최적화
구분
AI 카드(Card)
AI 서버(Server)
AI 랙(Rack)
사진
기능
칩을탑재한확장형모듈로, 
서버에장착하여AI 연산을수행
여러개의AI 카드를탑재해
대량의AI 연산을처리하는장치
여러대의서버를하나로연결하여
대규모AI 인프라를구축하는시스템
구성
1~4x Chip
4~16x Card
1~4x Server
특징
소모전력이매우낮아, 
카드당추론비용이매우저렴
저전력카드탑재
제한된전력內더조밀한서버구성가능+
냉각장치등추가요소최소화가능
저전력카드탑재
단위면적당더높은컴퓨팅성능제공,
데이터센터Capex 절감가능
ResNet-50
ResNet-50
Llama-70B
Llama-70B
Rebellions
ATOM
NVIDIA
L4
NVIDIA
H100
Rebellions
REBEL-Q
NVIDIA
H100
Habana Labs
Gaudi-2
0.28x
1.0x
5.0x
0.29x
1.0x
2.5x
추론당전력비용– Vision
추론당전력비용- Language
실적


Strictly Private and Confidential
15
DRAFT
제품로드맵
II. 대상회사분석
ION → ATOM → REBEL → 차세대(IO, CPU) 제품까지지속적진화, 하이퍼스케일러요구성능충족을향한기술
로드맵구현
• 복잡한대규모연산처리를위
해CPU 칩렛을결합
• Arm, 삼성전자와공동개발
• 데이터센터내고속통신을
위한네트워크전용칩렛
• NPU 칩렛과연결, 
확장가능한시스템
• LLM, 멀티모달AI 연산최적화
된하이퍼스케일DC 전용
NPU 
• 고대역폭메모리HBM3E와
멀티칩렛(Chiplet) 적용
• 소규모DC 및엔터프라이즈
추론용
• 저전력GDDR6 탑재로LLM,
Vision 모델지원
• 고성능저지연
AI 전용반도체
• HFT(High-
Frequency 
Trading) 및AI 
추론용


Strictly Private and Confidential
16
DRAFT
01
추론특화(Inference-first)
•
Training 겸용GPU와달리, 추론워크로드에최적화된전용설계
•
불필요한Training용회로를제거하여동일트랜지스터대비추론처리
량을극대화하고전력효율향상
02
HBM 최적화메모리설계
•
144GB HBM3e(6스택) 탑재로405B 파라미터초거대모델을단일카드
로구동
•
4.8TB/s 대역폭으로메모리바운드추론의병목제거, Groq(SRAM 
230MB) 대비압도적효율
03
칩렛(Chiplet) 확장아키텍처
•
Compute Die + I/O Die 분리설계로대면적다이수율문제해결
•
Compute Die 추가만으로성능스케일링(1 PFLOPS 구현입증) 
•
최신공정(Compute) + 성숙공정(I/O)으로비용최적화
vs GPU (NVIDIA) 
GPU는Training+Inference 범용설계추론시불필요한회로에전력낭비
NPU는추론전용최적화로동일전력에서약3배높은추론효율
기술아키텍처/ 칩설계원칙
II. 대상회사분석
추론특화(Inference-first) 아키텍처로동일전력대비극대화된추론처리량확보, 칩렛구조로확장성보장


Strictly Private and Confidential
17
DRAFT
•
LLM, ImageNet, 
YOLO 등다양한모
델의추론최적화
•
Keras Applications
사전학습모델즉시
활용
•
사전조정없이
TensorFlow 모델을
곧바로서빙파이프
라인에연결
•
PyTorch 2.0
완벽지원
(자연어처리(NLP), 
음성, 비전모델등
다양한워크로드)
•
PyTorch 컴파일
•
사전조정없이
Torch 2.0 모델을곧
바로서빙파이프라
인에연결
•
Hugging Face의
Transformer 및
Diffuser 모델지원
(Llama3-8B, SDXL 
등최신모델배포가
능)
•
Hugging Face 모델
컴파일및추론
•
Llama, SDXL 등
멀티칩구성지원
SW 스택및오픈소스생태계
II. 대상회사분석
Full-stack SW “RBLN SDK”를통해거의모든AI 추론모델에즉시적용가능하여고객의전환비용최소화
NVIDIA CUDA 대비전환비용을최소화하는개방형SW 아키텍처로, 기존인프라에그대로통합가능
AI 인프라
업계표준
AI 인프라
업계표준
대상회사
고유기술
대상회사
고유기술
기존AI 인프라를그대로유지하며HW만변경가능(GPU NPU) 
고객/개발자입장에서전환비용근본적절감가능


Strictly Private and Confidential
18
DRAFT
현세대제품스펙및경쟁력(1)
II. 대상회사분석


Strictly Private and Confidential
19
DRAFT
현세대제품스펙및경쟁력(2)
II. 대상회사분석
비전AI
(ResNet-50)
언어AI
(LLama-70B)
절대처리량(TPS) 14~30% 우위+ 전력효율(TPS/W) 142~175% 우위→ TCO 절감
REBEL-Quad
NVIDIA H100
NVIDIA H200
NVIDIA B200
2.57
0.54
1.06
1.5
$19K
$20~25K
$24~30K
$30~40K
비고
REBEL-Quad
NVIDIA H200
항목
24% 저렴
$19K
$25K
카드단가
24% 저렴
$190K
$250K
서버구성(8카드)
50% 절감
$25K
$50K
연간전력비(서버당)
34% 절감
$265K
$400K
3년TCO (서버당)
$17M 절감
$33M
$50M
1,000카드DC 3년
34%
TCO 절감
동일추론성능, 2/3 수준의저렴한비용
→ 데이터센터운영비용획기적절감
Rebellions
ATOM
NVIDIA
L4
NVIDIA
H100
0.28x
1.0x
5.0x
Rebellions
REBEL-Q
NVIDIA
H100
Habana Labs
Gaudi-2
0.29x
1.0x
2.5x


Strictly Private and Confidential
20
DRAFT
국내외NPU 제품비교
II. 대상회사분석
기술개발/ PoC 단계를넘어양산/납품실적확보, SKT의에이닷(음성통화요약서비스) 등대규모실사용레퍼런스확보, 
대용량메모리(HBM3E)사용으로모델매개변수초거대화, 멀티모달리티적용된최신AI 모델서빙가능
데이터센터추론
(‘25.12~) 
미국주요AI 회사들과
성능테스트(PoC) 
진행중
FuriosaAI
HBM3 48GB → (대상회사대비) 대규모실사용레퍼런스부족
DeepX
Edge 중심→ DC 시장진입어려움
Groq
SRAM 230MB → 초거대화된대규모매개변수의AI모델활용제약
Etched
PoC 단계로양산실적및HBM3E 공급망확보미비
HBM3e + Full-stack SW
DC 전용설계, 양산/납품실적
대규모실사용레퍼런스확보


Strictly Private and Confidential
21
DRAFT
사업화현황(국내)
II. 대상회사분석
국내1위통신사업자(SKT), IDC 사업자(KT) SI 투자유치및'K-스타게이트' 핵심파트너선정되어, 
‘27년까지주요고객사대상연1,500억원이상의가시적매출확보전망


Strictly Private and Confidential
22
DRAFT
사업화현황(해외)
II. 대상회사분석
글로벌핵심거점별AI DC 파이프라인구축및현지화전략본격화
사우디'Vision 2030' 등대규모인프라프로젝트참여를통한글로벌수주확대


Strictly Private and Confidential
23
DRAFT
산업별AI 적용사례
II. 대상회사분석
금융, 의료, 제조등전산업분야에걸쳐산업별특화솔루션과의결합을통해실질적인생산성혁신을주도하며
NPU 기반의산업맞춤형AI 도입및서비스환경구축중




Strictly Private and Confidential
25
DRAFT
대상회사TAM / SAM / SOM 분석
III. 시장분석
AI Chip 시장은’27년까지400조원이상성장예상되며, 추론용시장은84조원규모시장형성예상
대상회사는데이터센터추론칩수요폭증에힘입어, 2026년이후본격적인J커브성장궤도진입예상
AI Chip 시장
$300bn(400조원)+
추론용
AI Chip 시장
$40~60bn
(56~84조원)
Red Velvet
‘27년
5,000억원+
SOM Bottom-up 매출산출('27F)
매출
침투율
시장규모
세그먼트
1,000억+
30~40%
3,000억+
국내(SKT)
300억+
20~30%
1,500억+
국내(KT)
200억+
5~10%
2,000억+
국내(기타)
1,000억+
0.1~1.5%
10조원+
사우디(Aramco/SDAIA)
500억+
0.1~0.5%
5조원+
일본/동남아
1,000억+
0.5~1%
5조원+
네오클라우드
1,000억+
글로벌기타매출처
5,000억+
합계


Strictly Private and Confidential
26
DRAFT
AI 관여도
YoY 
Growth
연환산
매출
25.4Q
매출
회사
• Trainium 커스텀칩
AI ARR 3자릿수성장
• 13분기만에최고성장률
• 백로그$244bn
24%
$142bn
$35.6bn
• Azure가성장16%p 기여
• OpenAI 파트너십
• AI 기업고객7만+ 
• 분기토큰100T+ 
29%
$132bn
$32.9bn1
• Gemini 유료시트800만+
• Gemini 앱MAU 7.5억+
• 빅3 중최고성장률
• 서빙비용78% 절감
48%
$71bn
$17.7bn
$345bn
$86bn
빅3 합계
1.6
0.2
6
1
0.1
20
14
3.8
OpenAI
Anthropic
Xai
23
24
25E
(단위: USD bn)
전방시장: AI 서비스는역사상가장빠른매출성장
III. 시장분석
3년만에$0 → $35bn+ ARR로소수AI 모델기업이초고속성장하여과점구도를형성중이며, 
주요클라우드인프라합산25.4분기매출$86bn, 연간Run Rate $345bn로AI가핵심성장동력
OpenAI
+233% YoY
$20bn
월매출$1bn 돌파(2025.7)
주간사용자800M+
Anthropic
+1,300% YoY
$14bn
3년연속매년10x 성장
엔터프라이즈매출80%
xAI (Grok)
+3,700% YoY
$3.8bn
세계최대AI 슈퍼컴퓨터
Grok 모델
Mistral AI
EU #1
$0.4bn
유럽최대AI 스타트업
1) Microsoft Intelligent Cloud(Azure+HW+Enterprise 합계)


Strictly Private and Confidential
27
DRAFT
전방시장: AI 데이터센터인프라투자
III. 시장분석
데이터센터전력수요가2030년220GW까지폭증하며전력관리가최대변수가됨에따라, 
랙밀도를높이면서전력부하최소화할수있는NPU 인프라가투자효율성의결정적요소로부각
YoY
2026 가이던스
2025
2024
구분
+53%
$200bn
$131bn
$83bn
Amazon(AWS)
+103%
$175~185bn
$91bn
$53bn
Alphabet
+88%
$115~135bn
$72bn
$39bn
Meta
+2%
$120+bn
$118bn
$76bn
Microsoft
+43%
$45~50bn
$35bn
$11bn
Oracle
+54%
$660~690bn
$448bn
$261bn
빅5 합계
비고
수치
항목
GS 컨센서스
$527bn+
2026E CAPEX
하이퍼스케일단독수치
$1,4tn
2025~27 누적
-
$3~4tn
2030E
수치
항목
기관
$400~450bn
AI DC 전용CAPEX ('26)
Deloitte TMT
$5.2tn
DC 누적투자('25~30)
McKinsey
$7.9tn
가속시나리오
$3.7tn
보수시나리오


Strictly Private and Confidential
28
DRAFT
40만
70만
40만
25만
60만
140만
0
50
100
150
Google
Microsoft
Meta
AWS
Other
NVIDIA GPU
Custom ASIC


Strictly Private and Confidential
29
DRAFT
DRAFT
125
150
500
1,000
2024
2025E
2026E
2030F
• 학습(Training)은1회성비용이지만, 추론(Inference)는사용량에비례하
여지속발생
• AI 서비스확산시추론연산량이기하급수적으로증가하는구조
긴컨텍스트추론
128K→1M 토큰확장, 메모리요구량급증
→ HBM 대용량탑재필수화
고급추론(CoT/Reasoning)
대규모추론모델, AI Agent 등장
→ 토큰당연산량10~100배증가
3
멀티모달처리
영상/음성/이미지통합처리확산
→ 텍스트대비연산부하수십배
4
AI Agent 시대
단일쿼리→ 수십번추론호출
→ Agent 자율실행으로추론수요폭증
AI 칩시장: 규모및성장전망
III. 시장분석
생성형AI 서비스의폭발적확산에따라AI 칩시장규모가급속도로성장하고있음
특히Training → Inference 전환이가속화되며추론칩수요급증
(단위: USD bn)
104
118
313
2025
2026E
2034E
2
1


Strictly Private and Confidential
30
DRAFT
4
10
15
18
23
26
31
36
39
41
51
58
경쟁사: NVIDIA 데이터센터매출및칩세대별매출/출하량동향
III. 시장분석
NVIDIA 데이터센터매출, 2025년1,890억달러전망하며독보적성장세지속중
Blackwell 비중이매출의80% 상회예상되며높은이익률이반증하는공급병목현상은지속되고있음
(단위: USD bn)
FY2025 (CY2024) Data Center
$115.2bn
전체매출$130.5bn 중88%
+143% YoY
FY2026E (CY2025) Data Center
$189bn
25.Q3 YTD $131.4, 이미CY25 전체초과
+64% YoY
Rev ($bn)
ASP ($k)
Units (K)
Year
Chip
5-9
10-15
500-600
2022
A100
15-20
25-35
500-700
2023
H100
50-60
20-30
2,000-2,500
2024
H100/H200
100-140
30-45
3,000-5,000
2025E
Blackwell
155-185
4,000-5,700
25E Total 
①2025년Blackwell 전환
매출의80%가Blackwell
나머지20%가H100 계속판매
FY26E DC 매출약$189bn 예상(Q3 YTD $131.4bn)
②주요바이어별구매량(2024)
Microsoft: 485K H100 (1위) 
Meta: 300K  |  Google: 400K (자체포함)
xAI: 200-300K Blackwell 클러스터구축중
③ASP 변화추이
A100: $10-15k → H100: $25-40k → Blackwell: $30-45k
NVL72 랙: $1.8-2.0m (72x B200)
H20 (중국향): $10-12k → 수출규제中
GPM 73.6% OPM 63.2%
반도체업계최고수준
(Broadcom/Qualcomm은30-40%대)


Strictly Private and Confidential
31
DRAFT
AI 가속기경쟁구도
III. 시장분석
범용GPU가생태계지배력을보유하고있으나높은가격과전력소모, 생산병목에직면함에따라, 전력효율과연산
속도를획기적개선한추론전용ASIC/NPU가하이퍼스케일러및기업용DC 가속기로강력하게부각되고있음
한계/기회
강점
주요제품
대표기업
구분
가격·전력·공급부족
생태계·SW 지배력
H200, B200, Rubin
NVIDIA
범용GPU
SW 생태계약세
가성비, ROCm 개선
MI300X, RDNA4
AMD
범용GPU
외부판매제한
범용성부족
자체인프라최적화
비용절감30~50%
TPU v7, Trainium2
Inferentia2, Maia
Google
AWS
Microsoft
하이퍼스케일러
Custom
SW 생태계구축
스케일업과제
전력효율·지연시간
추론특화설계
REBEL-Quad
LPU
Corsair
Target
Groq
d-Matrix
추론전용
ASIC/NPU
DC 시장미진출
성능한계
초저전력
온디바이스AI
Hexagon NPU
Edge Brain (<5W)
Qualcomm
현대Edge Brain
Edge NPU


Strictly Private and Confidential
32
DRAFT


Strictly Private and Confidential
33
DRAFT
미국빅테크의존도를낮추려는글로벌수요에대응가능한Non-US 하이퍼스케일AI 칩기업의희소성대두
글로벌'Sovereign AI' 트렌드와기회
III. 시장분석
소버린AI(Sovereign AI) 환경조성을위해디지털주권확보및데이터센터구축이우선순위가됨에따라, 
Non-Nvidia + 저전력·고성능에부합하는NPU 가속기가글로벌공공및민간인프라구축에대한침투가능성高




Strictly Private and Confidential
35
DRAFT
0
27
156
320
1,544
5,388
11,557
25,102
2022A 2023A 2024A 2025A
2026F
2027F
2028F
2029F
매출전망및성장Projection
IV. 재무분석
REBEL-Quad 양산('26.2H) 이후본격적매출성장진입. FY27 5,388억원→ FY29 2.5조원+ 목표
(단위: 억원)


Strictly Private and Confidential
36
DRAFT
비용구조및수익성개선Projection
IV. 재무분석
R&D 집중투자기(~'26년)를거쳐'27년이후매출레버리지효과로빠른수익성개선기대
2028F
2027F
2026F
2025
(가결산)
2024A1
단위: 억원
11,557
5,388
1,544
320
156
매출액
5,234
2,368
713
148
36
매출총이익
45.3%
43.9%
46.2%
46.4%
23.0%
GPM%
1,877
185
(905)
(1,184)
(1,284)
영업이익
16.2%
3.4%
-58.6%
-369.8%
-821.0%
OPM%
1,942
262
(790)
(2,048)
(3,008)
당기순이익
16.8%
4.9%
-51.1%
-639.6%
-1922.4%
NPM%
120
172
831
3,020
6,322
1,126
1,168
1,247
1,614
2,474
194
164
372
569
883
1,441
1,504
2,449
5,203
9,679
2024A
2025A
2026F
2027F
2028F
매출원가
연구개발비
기타판관비


Strictly Private and Confidential
37
DRAFT
2025A
2024A1
2023A
2022A
(단위: 백만원)
392,432
199,261
168,476
86,057
유동자산
316,086
157,873
115,552
82,752
현금성자산
294,937
262,917
14,276
14,644
비유동자산
687,396
462,178
182,752
100,701
자산총계
921,998
506,238
330,356
127,709
부채총계
894,065
449,439
310,602
124,536
RCPS 부채
(234,629)
(44,060)
(147,604)
(27,008)
자본총계
*K-IFRS 기준RCPS는부채로계상됨. 전환시자본으로전환되어자본구조
정상화가능하여실질적자본잠식상태아님.
재무상태표및현금흐름
IV. 재무분석
본건투자금[5,500]억원투자유치후'27년IPO까지충분한운영자금확보가능




Strictly Private and Confidential
39
DRAFT
PSR
Sales
Market
2027F
2025A
2027F
2025A2
Cap1
단위: $ B
13.6x
23.7x
327
187
4,443
NVIDIA
5.2x
9.8x
65
35
338
AMD
11.4x
24.1x
135
64
1,542
Broadcom
6.7x
8.6x
10
8
67
Marvell
9.2x
16.5x
Average
금액
단위: 억원
[24,000]
Equity Value (100%)
5,388
Sales (2027F)
4.5x
PSR (Forward)
Trailing
PSR
최근
매출액
Equity
Value
단계
기업명
2,666.7x
3억원
0.80조원
PoC
딥엑스
(S. Korea)
280.4x
30억원
0.83조원
PoC
퓨리오사AI
(S. Korea)
76.7x
$0.1B
(0.13조원)
$6.9B
(10조원)
대량양산
(데이터센터, Groq Cloud)
Groq
(USA)
25.7x
$0.3B
(0.4조원)
$7.0B
(10조원)
대량양산
(Open AI)
Cerebras
(USA)
nm
-
(매우낮음)
$4.5 B
(6.5조원)
제품개발~PoC
Etched
(USA)
74.9x
320억원
[2.4]조원
초기양산
리벨리온
①매출성장잠재력
•
FY25 320억원FY27 5,000억원이상성장예상
•
CAGR 200% 이상의초고속성장
•
FY27 흑자전환예상(당기순이익262억원)
②전략적희소성
•
유일한Non-US 하이퍼스케일AI 칩메이커
•
Soverign AI 최대수혜기업
•
NVIDIA 수출규제반사이익
③정책적수혜
•
국민성장펀드제1호과제(K-엔비디아육성)
•
50조원규모의K-스타게이트인프라핵심수혜
•
국산가속기채택률50% 달성정책목표
④캡티브매출확보
•
SKT 1,000억원이상, KT 300억원이상매출확정
•
ARMACO, SDAIA 중동대형계약체결예정
•
SoftBank, Singtel 등일본, 동남아시아확장
내용
구분
학습, 추론용AI가속기설계(Hopper, Blackwell, Rubin 등)
NVIDIA
학습, 추론용AI가속기설계(Instinct)
AMD
구글(TPU), 메타(MTIA) 등ASIC 설계
Broadcom
아마존(Trainium), MS(Maia) 등ASIC 설계
Marvell


Strictly Private and Confidential
40
DRAFT


Strictly Private and Confidential
41
DRAFT
Scenario
IRR Calculation
IPO 후
Block Deal
(기본Exit Plan)
IPO
성공
산출내역
#
단위: 백만원
194,163
A
'28년추정당기순이익
27.7x
B
Forward PER
20%
C
공모할인율
4,298,760
D = A x B x (1-C)
IPO Pre-value
12.2%
E
공모비율
4,823,208
F = D x (1 + E)
IPO Post-value
2.72%
G
당PEF 지분율1
5.0%
H
Block deal 할인율
124,591
I = F x G x (1 - H)
회수예상금액
15.5%
Gross IRR
1.4x
Gross MOIC
IPO
무산
M&A를통한
구주매각
상환청구
Block Deal
•
지분매각시점: [2028]년[7]월말
•
보호예수기간: [12]개월가정
•
Multiple: 비교기업forward P/E 멀티플적용
M&A
•
지분매각시점: [2028]년[12]월말
IPO 기한[1]년경과후지분매각절차진행, [6]개월후매각
상환청구
•
상환시점: [2031]년[4]월말(펀드만기)
6.0%
Gross IRR
1.3x
Gross MOIC
산출내역
#
단위: 백만원
538,776
A
'27년추정매출액
50%
B
사업계획달성률
269,388
C = A x B
2027년조정매출액
15.0x
D
Trailing PSR
4,040,821
E = C x D
Equity Value
3.05%
F
당펀드지분율
123,279
G = E x F
회수예상금액
12.5%
Gross IRR
1.4x
Gross MOIC


Strictly Private and Confidential
42
DRAFT
PER
Net income
Market
2027F
2025A
2027F
2025A
Cap
단위: USD bn
23.8x
44.8x
187
99
4,443
NVIDIA
31.1x
78.0x
11
4
338
AMD
32.5x
66.7x
47
23
1,542
Broadcom
23.4x
26.9x
3
2
67
Marvell
27.7x
54.1x
Average
PSR
Sales
Equity
Acquirer
Target
Date
Value
n/a
-
$2.0B
Intel
Habana Labs
2019.12.
150.0x
$4M
$0.6B
SoftBank
Graphcore
2024. 07.
59.5x
56억원
3,325억원
리벨리온
사피온1
2024.12.
222.2x
$0.09B
$20B
NVIDIA
Groq2
2025.12.
143.9x
Average


Strictly Private and Confidential
43
DRAFT
2028
2027
2026
4Q
3Q
2Q
1Q
4Q
3Q
2Q
1Q
4Q
3Q
Apr
Net IRR
단위: 백만원
-
125,091
500
500
500
500
-
-
-
-
92,200
Cash-in
-
500
500
500
500
500
-
-
-
-
92,200
Capital Call
-
124,591
-
-
-
-
-
-
-
-
-
지분매각
-
(125,192)
(500)
(500)
(500)
(500)
-
-
-
-
(92,099)
Cash-out
-
-
-
-
-
-
-
-
-
-
(90,000)
투자금집행
-
-
-
-
-
-
-
-
-
-
(99)
실사비용
-
(500)
(500)
(500)
(500)
(500)
-
-
-
-
(2,000)
관리보수
-
(2,484)
-
-
-
-
-
-
-
-
-
성과보수
-
(122,208)
-
-
-
-
-
-
-
-
-
LP분배
-
124,192
(500)
(500)
(500)
(500)
-
-
-
-
(92,200)
13.24%
성과보수차감전CF
-
121,708
(500)
(500)
(500)
(500)
-
-
-
-
(92,200)
12.21%
성과보수차감후CF
2028
2027
2026
4Q
3Q
2Q
1Q
4Q
3Q
2Q
1Q
4Q
3Q
Apr
Net IRR
단위: 백만원
124,113
500
500
500
500
500
-
-
-
-
92,200
Cash-in
833
500
500
500
500
500
-
-
-
-
92,200
Capital Call
123,279
-
-
-
-
-
-
-
-
-
-
지분매각
(124,214)
(500)
(500)
(500)
(500)
(500)
-
-
-
-
(92,099)
Cash-out
-
-
-
-
-
-
-
-
-
-
(90,000)
투자금집행
-
-
-
-
-
-
-
-
-
-
(99)
실사비용
(833)
(500)
(500)
(500)
(500)
(500)
-
-
-
-
(2,000)
관리보수
(1,318)
-
-
-
-
-
-
-
-
-
-
성과보수
(122,063)
-
-
-
-
-
-
-
-
-
-
LP분배
122,547
(500)
(500)
(500)
(500)
(500)
-
-
-
-
(92,200)
10.29%
성과보수차감전CF
121,229
(500)
(500)
(500)
(500)
(500)
-
-
-
-
(92,200)
9.84%
성과보수차감후CF




Strictly Private and Confidential
45
DRAFT
주요재무제표
VI. Appendix
2025A
2024A1
2023A
2022A
단위: 백만원
K-IFRS
K-IFRS
K-IFRS
K-IFRS
회계기준
392,432
199,261
168,476
86,057
유동자산
316,086
157,872
115,552
82,752
현금및단기금융상품
22,831
8,059
10
-
매출채권
26,233
3,575
1,853
-
재고자산
27,282
29,754
51,062
3,305
기타유동자산
294,937
262,917
14,276
14,644
비유동자산
274,401
254,258
13,369
13,017
유무형자산
20,536
8,658
907
1,627
기타비유동자산
687,369
462,178
182,752
100,701
자산총계
912,220
503,180
328,118
125,616
유동부채
2,485
47,088
14,435
288
미지급금
894,065
449,439
310,602
124,536
RCPS
15,669
6,654
3,082
792
기타유동부채
9,778
3,057
2,238
2,094
비유동부채
921,998
506,238
330,356
127,709
부채총계
13,254
13,005
7,215
6,901
자본금
(596,995)
(392,948)
(158,596)
(35,344)
이익잉여금
349,113
335,883
3,777
1,435
기타자본
(234,629)
(44,060)
(147,604)
(27,008)
자본총계
687,369
462,178
182,752
100,701
부채및자본총계
2025A
2024A1
2023A
2022A
단위: 백만원
K-IFRS
K-IFRS
K-IFRS
K-GAAP
회계기준
32,022
15,644
2,735
-
매출액
28,440
12,773
2,526
-
제품매출
3,582
2,871
209
-
용역매출
17,173
12,041
712
-
매출원가
14,848
3,603
2,023
-
매출총이익
133,267
132,035
31,690
9,911
판매비와관리비
116,849
112,645
27,685
8,448
경상연구개발비
9,305
10,273
1,816
442
인건비
3,174
4,799
1,442
646
지급수수료
1,012
2,542
268
45
유무형상각비
2,928
1,776
480
331
기타판관비
(118,419)
(128,432)
(29,667)
(9,911)
영업이익
5,879
6,667
2,503
1,808
영업외수익
92,259
175,144
96,089
10
영업외비용
(204,799)
(296,909)
(123,252)
(8,112)
세전이익
-
3,841
-
-
법인세비용
(204,799)
(300,750)
(123,252)
(8,112)
당기순이익
46.4%
23.0%
74.0%
-
GPM%
-369.8%
-821.0%
-1084.8%
-
OPM%
-639.6%
-1922.4%
-4506.9%
-
NPM%


Strictly Private and Confidential
46
DRAFT
Business Plan
VI. Appendix
Forecast
Historical
2029F
2028F
2027F
2026F
2025A
2024A
2023A
단위: 백만원
2,510,177
1,155,662
538,776
154,416
32,022
15,644
2,735
매출액
117.2%
114.5%
248.9%
382.2%
209.4%
472.0%
yoy growth%
2,510,177
1,155,662
538,776
154,416
28,440
12,773
2,526
제품매출
-
-
-
-
3,582
2,871
209
용역매출
1,399,460
632,245
302,013
83,068
17,173
12,041
712
매출원가
1,110,717
523,417
236,763
71,348
14,848
3,603
2,023
매출총이익
44.2%
45.3%
43.9%
46.2%
46.4%
23.0%
74.0%
GPM%
621,583
335,698
218,276
161,880
133,267
132,035
31,690
판매관리비
464,949
247,370
161,362
124,714
116,849
112,645
27,685
경상연구개발비
251,018
115,566
75,637
66,791
n/a
n/a
n/a
제품개발비
213,931
131,804
85,725
57,923
n/a
n/a
n/a
인건비
156,634
88,328
56,914
37,166
16,418
19,390
4,006
기타판매관리비
489,134
187,719
18,487
(90,532)
(118,419)
(128,432)
(29,667)
영업이익
19.5%
16.2%
3.4%
-58.6%
-369.8%
-821.0%
-1084.8%
OPM%
3,175
6,444
7,753
11,578
(86,380)
(168,476)
(93,585)
영업외손익
492,310
194,163
26,241
(78,954)
(204,799)
(296,909)
(123,252)
세전이익
31,504
-
-
-
-
3,841
-
법인세비용
460,806
194,163
26,241
(78,954)
(204,799)
(300,750)
(123,252)
당기순이익
18.4%
16.8%
4.9%
-51.1%
-639.6%
-1922.4%
-4506.9%
NPM%


Strictly Private and Confidential
47
DRAFT
국민성장펀드개요
VI. Appendix


Strictly Private and Confidential
48
DRAFT
노앤파트너스소개
VI. Appendix


