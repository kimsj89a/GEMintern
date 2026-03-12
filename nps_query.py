"""
국민연금 가입 사업장 내역 조회 모듈 (OpenAPI)
- 데이터 출처: https://www.data.go.kr/data/15083277/fileData.do
- 연도별, 월별, 사업자명별 조회 지원
- API: api.odcloud.kr/api/15083277/v1

사용법:
    from nps_query import NpsQuery
    nps = NpsQuery("YOUR_SERVICE_KEY")
    results = nps.search(name="삼성", year=2024, month=3)
    nps.print_results(results)
"""

import json
import sys
import urllib.request
import urllib.parse
from typing import Optional

BASE_URL = "https://api.odcloud.kr/api/15083277/v1"

# 월별 엔드포인트 UUID 매핑 (2015-12 ~ 2026-02)
ENDPOINTS = {
    "2015-12": "uddi:b9bf303e-a60e-4a49-a517-99797889484e",
    "2016-01": "uddi:37493930-4de8-4f00-8743-aeb803dcd795",
    "2016-02": "uddi:6ee79a68-53e3-4d63-ac62-a7979952e89b",
    "2016-03": "uddi:f2bba05e-c160-412f-800e-edc2327ab0f0",
    "2016-04": "uddi:42e4a970-2989-42bc-b357-94c31990d534",
    "2016-05": "uddi:735caf7c-2cd2-4570-a480-b4d9b57e1902",
    "2016-06": "uddi:9c5a563f-882a-4309-a05e-c7f6bc346bf5",
    "2016-07": "uddi:c11a6a3d-706c-422e-bca8-dca8bd93df8e",
    "2016-08": "uddi:73bd88e6-16e9-4803-ba58-a03604d52f74",
    "2016-09": "uddi:f430c5ab-3f7f-44f9-97f4-c327f0df7934",
    "2016-10": "uddi:3625c650-d32b-4ccf-be60-d3f0fcf962e6",
    "2016-11": "uddi:21e63777-8300-4e65-864e-b406bf408ebd",
    "2016-12": "uddi:dd4d69f9-2937-4785-83e0-b5fefdc361df",
    "2017-01": "uddi:c43047e8-9aea-42a3-ae44-c0e6d365f75e",
    "2017-02": "uddi:720f5972-ad02-49f8-b3a7-e26356f7c501",
    "2017-03": "uddi:a2ed5062-cc7f-4474-9e87-bcc0c9458ae9",
    "2017-04": "uddi:a201b487-f425-4f27-9378-f26cb9503ce6",
    "2017-05": "uddi:ad211696-f7b8-440b-b1d2-c14d28528bb7",
    "2017-06": "uddi:72aa6fc6-4d87-4156-bc91-e93289cdb0d1",
    "2017-07": "uddi:bf28351f-a1d6-4553-bb56-b753aef41fc2",
    "2017-08": "uddi:9fbeeafc-4bc8-4d42-8ac2-c2a1e090935b",
    "2017-09": "uddi:3ee261dc-747f-49dd-a157-f0bb17bc48e5",
    "2017-10": "uddi:0c963b82-5230-4aa3-9241-d157cb75b567",
    "2017-11": "uddi:a05d66c1-8056-4ed8-8197-b5bdd3b722f6",
    "2017-12": "uddi:f616dc6d-eb7a-45b1-a205-f91cdab72e40",
    "2018-01": "uddi:643c5346-a1cc-48e9-9217-d37c5de93c02",
    "2018-02": "uddi:49de868a-9fb3-4e6c-8835-f7718f9b446b",
    "2018-03": "uddi:2828565f-6cd9-4f9e-8326-91c394d451a3",
    "2018-04": "uddi:f3cdfbf4-12d8-40e0-9d97-bc7489e8820c",
    "2018-05": "uddi:c87d8aa5-cf12-40f9-8517-f9b5ab4d792c",
    "2018-06": "uddi:a9cb5774-238c-40f1-9d3a-badc3d3864d0",
    "2018-07": "uddi:202031a2-24eb-44b8-8c43-88f2de2b2d48",
    "2018-08": "uddi:658159ed-ce5d-4c09-9d7b-a1b2b7ab8089",
    "2018-09": "uddi:8b52fe84-5ed7-4232-a468-ca42091447a0",
    "2018-10": "uddi:30f90a31-09c9-41b6-9828-d05e2939db9f",
    "2018-11": "uddi:cf1753c5-0080-4c6d-b68e-cbeafa31f371",
    "2018-12": "uddi:088e933f-b16a-4002-9122-d4fb0c0f9832",
    "2019-01": "uddi:7f7319d8-df12-489c-9f1f-d46b987b05e9",
    "2019-02": "uddi:c310c1b7-4791-4bae-aea0-dfb81ce5f4cd",
    "2019-03": "uddi:2a2c6ef7-e956-464b-bc33-fcf33e9c2d0e",
    "2019-04": "uddi:8926074b-d33c-40fa-aa06-9e145b63c22d",
    "2019-09": "uddi:41296667-bc83-454f-bcfa-fd00ebacdab4",
    "2019-10": "uddi:1b4e4b0c-6f6c-4b43-8080-8b4c3746ddec",
    "2019-11": "uddi:ecd8b423-aa81-4c08-b1fe-b9037cd66a83",
    "2019-12": "uddi:02ad33d5-f387-4446-8884-a96bbf321a55",
    "2020-01": "uddi:32a88167-3191-47a5-8c58-e74f96393fb0",
    "2020-02": "uddi:3ede1edb-f56f-4248-af5c-d4b031333439",
    "2020-03": "uddi:fef9cdc9-8a2e-42bb-85af-82aee48119eb",
    "2020-04": "uddi:c56acab8-dcf0-40e6-9bca-d8260ff714a6",
    "2020-05": "uddi:79803eb8-0b53-423b-bf0d-e37a4dad398d",
    "2020-06": "uddi:088d6341-ebdb-473f-bdd7-b2e229404db8",
    "2020-07": "uddi:618aa96f-14c3-443b-bfa2-893f5902b8ea",
    "2020-08": "uddi:c38428d1-8408-4c4e-a814-f81651f1b8b6",
    "2020-09": "uddi:14afa7a7-becf-4e74-a440-c32e5c4ad19f",
    "2020-10": "uddi:d7b668da-60c3-4f4a-bcf9-9166dc5bc49e",
    "2020-11": "uddi:7eecccd0-c268-4c77-a4ae-a3c673ffa682",
    "2020-12": "uddi:7ff17f03-3072-4f20-b265-aa60ee041401",
    "2021-01": "uddi:b2a76201-9cf7-458d-a6e0-c2194e6ee40f",
    "2021-02": "uddi:d066a0fa-34e1-4149-9980-f5c9f7f9e2e3",
    "2021-03": "uddi:995de2fb-5dc2-4a3f-b0c7-c95deb374224",
    "2021-04": "uddi:f1d30736-6610-4a2d-a830-850c7da466e6",
    "2021-05": "uddi:0beb7252-2d35-4b74-af04-c77eed7ca44b",
    "2021-06": "uddi:d4781c30-5b0a-470b-a2b5-fd3e9cb20606",
    "2021-07": "uddi:9c7be522-8efa-427b-892f-ce95568d8779",
    "2021-08": "uddi:d54b642a-8db0-4359-a7f2-e8869b00913c",
    "2021-11": "uddi:2e4217d6-7c19-4e10-bcb6-a71e83a733bd",
    "2021-12": "uddi:4db30f80-d2a1-4a90-a89f-80a118ae4b85",
    "2022-01": "uddi:9bdcbdbb-5402-4028-9a90-eaef6492e208",
    "2022-02": "uddi:6dea9362-4865-4ede-8b7f-98683b206668",
    "2022-03": "uddi:2ead034f-65e0-4d5d-b72e-f8dedba041a3",
    "2022-04": "uddi:23712302-15c4-4034-96b1-8ec80a415e44",
    "2022-05": "uddi:d7e2de87-da03-4ec4-9741-ef4208ce393c",
    "2022-06": "uddi:da7e3a30-3401-4232-87b1-b279d0d97088",
    "2022-07": "uddi:814e0e45-ab16-401d-92d6-bfc51260eba5",
    "2022-08": "uddi:d2683037-b144-466f-b287-90f79a4bd8b2",
    "2022-09": "uddi:e9b54ba9-04e7-4730-9def-db6f05bf1925",
    "2022-10": "uddi:ffe2743c-f90d-4644-bfeb-c770d319bec5",
    "2022-12": "uddi:9a6668fe-9df7-4118-9e1c-9fec68de7c03",
    "2023-01": "uddi:e80b5227-bbd2-4620-ae95-b82064f54da0",
    "2023-02": "uddi:86233d7b-8f57-4ed7-aab8-b59464141971",
    "2023-03": "uddi:e825a3c5-86c1-48b0-9450-a898731ec064",
    "2023-04": "uddi:e2be1bab-b4b5-4073-97dd-8a8487ecb487",
    "2023-05": "uddi:63837df0-61d0-4aa8-8890-ff3720b255f3",
    "2023-06": "uddi:84b05020-c26e-4a57-9a15-c60554764534",
    "2023-07": "uddi:b32e56a7-17cd-4ebf-8833-ac01662800da",
    "2023-08": "uddi:8617a7f1-3665-48d0-8b71-922cc1bdca07",
    "2023-09": "uddi:8b59078d-9a70-489f-98d8-ba27d7e573c5",
    "2023-10": "uddi:f42b3ec1-4fe9-4338-a282-91f61dc7f288",
    "2023-11": "uddi:2c0534ef-64f5-4f65-a627-b7ac918390dc",
    "2023-12": "uddi:00ade2e8-46b6-436d-9287-ae03d5a63a6f",
    "2024-01": "uddi:5cdf7e9e-dc5d-4369-96d3-d22744d8d10d",
    "2024-02": "uddi:c70b85ac-0146-41a9-8f4a-d2acafaa3c92",
    "2024-03": "uddi:67ccdcc5-727f-408d-802a-dce95772acb8",
    "2024-04": "uddi:f2d5995e-5b47-4476-9f04-c8b2519735a3",
    "2024-05": "uddi:ccc6764a-b232-494e-a453-d21b929878f8",
    "2024-06": "uddi:5ae3f030-6646-4239-b0f5-8e1b7b284007",
    "2024-07": "uddi:fbc9aff6-7496-4c14-bc49-adfefb93557d",
    "2024-08": "uddi:3f8e431e-efcf-4d25-b6f6-cef316722b84",
    "2024-09": "uddi:ae2d6a33-e33b-4312-a902-c9a8c22d9ab0",
    "2024-10": "uddi:a1d51e9d-f55a-4f94-a06c-ef98691479fd",
    "2024-11": "uddi:f6873590-8c0d-4328-af24-8b24f81deb8b",
    "2024-12": "uddi:819641d2-a9ba-498a-a689-db8ad2c9800a",
    "2025-01": "uddi:3a89a14e-7230-467a-bf07-9ca33d06812d",
    "2025-02": "uddi:45ba8ffb-ab8c-44da-abd6-b10ec30821cd",
    "2025-03": "uddi:6d064493-1c29-4ddb-9bc5-be98e40a1e57",
    "2025-04": "uddi:45b0b01c-16bd-4621-ad04-fdaeb400b4f6",
    "2025-05": "uddi:6ec70fba-037c-4e20-8d47-88e26912b4e2",
    "2025-06": "uddi:58d465f8-71bf-4378-b4e8-e4b265e805da",
    "2025-07": "uddi:7c8ebb8e-baf4-49a0-a281-aa483c3158b8",
    "2025-08": "uddi:20ddf65d-51d8-421f-8ee5-b64f05554151",
    "2025-09": "uddi:14c0beb5-b153-4b03-892b-8d30a7600de1",
    "2025-10": "uddi:466a4aef-5a2d-4b2b-a3d9-8a6c11b81d23",
    "2025-11": "uddi:f9787983-d48a-4c94-b7b6-c805a5be3cca",
    "2025-12": "uddi:06b329ca-54a4-47f8-8c8f-8268d61c7d7c",
    "2026-01": "uddi:10a6e7bd-a2ee-4ee1-967c-bb9a6aea89a9",
    "2026-02": "uddi:74d9aa39-bc2c-4124-9cff-ec389dbf51e3",
}


class NpsQuery:
    """국민연금 가입 사업장 조회 클래스"""

    def __init__(self, service_key: str):
        """
        Args:
            service_key: data.go.kr 발급 인증키 (Encoding 또는 Decoding 모두 가능)
        """
        self.service_key = service_key

    def _get_endpoints(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> list[tuple[str, str]]:
        """조건에 맞는 (년월, UUID) 리스트 반환"""
        results = []
        for ym, uddi in sorted(ENDPOINTS.items()):
            y, m = ym.split("-")
            if year is not None and int(y) != year:
                continue
            if month is not None and int(m) != month:
                continue
            results.append((ym, uddi))
        return results

    def _call_api(
        self,
        uddi: str,
        name: Optional[str] = None,
        page: int = 1,
        per_page: int = 100,
    ) -> dict:
        """단일 API 호출"""
        params = {
            "page": str(page),
            "perPage": str(per_page),
            "serviceKey": self.service_key,
        }
        if name:
            params["cond[사업장명::LIKE]"] = name

        url = f"{BASE_URL}/{uddi}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def search(
        self,
        *,
        name: Optional[str] = None,
        year: Optional[int] = None,
        month: Optional[int] = None,
        per_page: int = 100,
        max_pages: int = 10,
    ) -> list[dict]:
        """
        사업장 검색

        Args:
            name: 사업장명 (부분 일치 검색)
            year: 연도 (예: 2024). None이면 전체 연도
            month: 월 (예: 3). None이면 전체 월
            per_page: 페이지당 건수 (최대 1000)
            max_pages: 월별 최대 페이지 수

        Returns:
            검색 결과 리스트

        Examples:
            # 2024년 3월 "삼성" 검색
            nps.search(name="삼성", year=2024, month=3)

            # 2024년 전체 "카카오" 검색
            nps.search(name="카카오", year=2024)

            # 2026년 1월 전체 사업장 (주의: 대량)
            nps.search(year=2026, month=1, per_page=1000)
        """
        endpoints = self._get_endpoints(year, month)
        if not endpoints:
            print(f"해당 기간의 데이터가 없습니다. (year={year}, month={month})")
            print(f"사용 가능: {sorted(ENDPOINTS.keys())[0]} ~ {sorted(ENDPOINTS.keys())[-1]}")
            return []

        all_results = []
        for ym, uddi in endpoints:
            page = 1
            while page <= max_pages:
                try:
                    resp = self._call_api(uddi, name=name, page=page, per_page=per_page)
                except Exception as e:
                    print(f"  [{ym}] API 오류: {e}")
                    break

                data = resp.get("data", [])
                match_count = resp.get("matchCount", 0)

                if page == 1:
                    print(f"  [{ym}] {match_count:,}건 매칭")

                all_results.extend(data)

                # 다음 페이지 필요 여부
                fetched = page * per_page
                if fetched >= match_count or not data:
                    break
                page += 1

        return all_results

    def count(
        self,
        *,
        name: Optional[str] = None,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> dict[str, int]:
        """
        월별 매칭 건수만 조회 (빠름)

        Returns:
            {"2024-03": 1234, ...}
        """
        endpoints = self._get_endpoints(year, month)
        counts = {}
        for ym, uddi in endpoints:
            try:
                resp = self._call_api(uddi, name=name, page=1, per_page=1)
                counts[ym] = resp.get("matchCount", 0)
                print(f"  [{ym}] {counts[ym]:,}건")
            except Exception as e:
                print(f"  [{ym}] 오류: {e}")
                counts[ym] = -1
        return counts

    @staticmethod
    def available_periods() -> list[str]:
        """조회 가능한 년월 목록"""
        return sorted(ENDPOINTS.keys())

    @staticmethod
    def print_results(results: list[dict], limit: int = 30):
        """조회 결과 출력"""
        if not results:
            print("조회 결과 없음")
            return

        print(f"\n총 {len(results):,}건\n")
        print(f"{'년월':<10} {'사업장명':<28} {'가입자수':>8} {'당월고지금액':>14} {'업종명'}")
        print("-" * 100)
        for r in results[:limit]:
            print(
                f"{r.get('자료생성년월', ''):<10} "
                f"{r.get('사업장명', ''):<28} "
                f"{r.get('가입자수', 0):>8,} "
                f"{r.get('당월고지금액', 0):>14,} "
                f"{r.get('사업장업종코드명', '') or ''}"
            )
        if len(results) > limit:
            print(f"  ... 외 {len(results) - limit:,}건")

        # 요약
        total_sub = sum(r.get("가입자수", 0) or 0 for r in results)
        total_amt = sum(r.get("당월고지금액", 0) or 0 for r in results)
        months = sorted(set(r.get("자료생성년월", "") for r in results))
        print(f"\n[요약] 기간: {months[0]}~{months[-1]} | "
              f"총 가입자: {total_sub:,}명 | 총 고지금액: {total_amt:,}원")


# --- CLI ---
def main():
    import argparse

    parser = argparse.ArgumentParser(description="국민연금 가입 사업장 조회 (OpenAPI)")
    parser.add_argument("--key", type=str, help="data.go.kr 서비스키")
    parser.add_argument("--name", type=str, help="사업장명 검색 (부분 일치)")
    parser.add_argument("--year", type=int, help="연도 (예: 2024)")
    parser.add_argument("--month", type=int, help="월 (예: 3)")
    parser.add_argument("--limit", type=int, default=30, help="출력 건수")
    parser.add_argument("--count", action="store_true", help="건수만 조회")
    parser.add_argument("--periods", action="store_true", help="조회 가능 기간 출력")

    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    if args.periods:
        periods = NpsQuery.available_periods()
        print(f"조회 가능 기간: {periods[0]} ~ {periods[-1]} ({len(periods)}개월)")
        return

    key = args.key
    if not key:
        # 환경변수에서 시도
        import os
        key = os.environ.get("NPS_SERVICE_KEY", "")
    if not key:
        print("서비스키 필요: --key 또는 NPS_SERVICE_KEY 환경변수")
        return

    nps = NpsQuery(key)

    if args.count:
        counts = nps.count(name=args.name, year=args.year, month=args.month)
        total = sum(v for v in counts.values() if v > 0)
        print(f"\n총 {total:,}건")
    else:
        results = nps.search(
            name=args.name, year=args.year, month=args.month,
        )
        nps.print_results(results, limit=args.limit)


if __name__ == "__main__":
    main()
