### [파일명: ATOM-Max vs. RNGD_260226.pdf]
주요NPU 제품비교

1

퓨리오사AI RNGD

리벨리온ATOM TM-Max

리벨리온우위항목

지원모델카테고리
(양사공식Model Zoo 기반)

Computer Vision 지원목록없음

Computer Vision

LLM

멀티모달AI 지원목록없음

Physical AI지원목록없음

LLM

멀티모달AI

Physical AI

➔ 4배이상의AI서비스종류지원

지원모델수

20+

281+

➔ 지원모델수약14배

메모리사양

주요지원
SW/API

용량

대역폭

HBM3, 48 GB

GDDR6, 64 GB

1.5 TB/sec

1 TB/sec

서빙

-vLLM-compatibleAPI 자체지원

오케스트레이션

-K8s 자체지원

-vLLM 하드웨어플러그인지원(공식인증)
-Triton InferenceServer 지원(공식배포)
-K8s 및 K8s 기반Red Hat OpenShift

 (공식인증)

➔ AI 상용서비스에필수요구되는

SW를공식지원

©  2026 Rebellions Inc. All rights reserved.

ATOM TM-Max 서버_ SW (호환성)
상용AI  서비스에필수적인SW  운영을지원합니다 (vLLM, Triton  추론서버, 쿠버네티스, Red Hat  등).

2

vLLM
공식지원

K8s
쿠버네티스
호환

리벨리온NPU 로컴파일된모델들이vLLM 을통해배포될수있도록,
vLLM Community 에서공식지원하는
vLLM 용하드웨어플러그인을제공합니다.
(Documentation Link )

Triton
추론서버호환

리벨리온NPU 를활용하는다양한모델을편리하게
배포할수있으며, 기존Triton Inference Server 로구축된
배포환경을그대로이용할수있습니다.
(Documentation Link )

Triton Inference
Server

리벨리온NPU  오퍼레이터를통해디바이스플러그인,
노드레이블, 메트릭모니터링툴을자동배포하며
쿠버네티스환경내NPU  리소스를통합관리할수있습니다.
(Documentation Link )

Red Hat
공식지원

리벨리온NPU 는Red Hat Enterprise Linux 와
호환되며, Red Hat OpenShift Certified

제품으로공식등록되어있습니다.
(Red Hat Ecosystem Catalog Link)

©  2026 Rebellions Inc. All rights reserved.

참고. ATOM TM-Max 서버_ 주요인증/지원사항

3

vLLM  공식지원NPU  (국내유일)

Red Hat 공식지원NPU  (국내유일)

*Red Hat Ecosystem Catalog Link

쿠버네티스오퍼레이터지원(공식배포)

*vLLM  공식문서링크

©  2026 Rebellions Inc. All rights reserved.

*rbln-npu-operator Github Link

