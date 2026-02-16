# UI 업그레이드: Notion 스타일 적용

## 개요
GEM Intern PyQt6 애플리케이션의 UI를 Notion 스타일로 전면 개선했습니다.

## 변경된 파일들

### 1. `styles.py` (전면 개편)
#### 새로운 컬러 팔레트
- **배경색**
  - `BG_PRIMARY`: #FFFFFF (순백색)
  - `BG_SECONDARY`: #F7F6F3 (따뜻한 오프화이트, 사이드바)
  - `BG_TERTIARY`: #FAFAF9 (호버용 미묘한 그레이)

- **보더 색상**
  - `BORDER_LIGHT`: #E9E9E7 (매우 연한 그레이)
  - `BORDER_MEDIUM`: #DBDBD9 (중간 그레이)
  - `BORDER_DARK`: #D3D3D1 (강조용 어두운 보더)

- **텍스트 색상**
  - `TEXT_PRIMARY`: #37352F (메인 텍스트용 다크 그레이)
  - `TEXT_SECONDARY`: #787774 (보조 텍스트용 미디엄 그레이)
  - `TEXT_TERTIARY`: #9B9A97 (캡션용 라이트 그레이)

- **액센트 색상** (소프트 블루)
  - `PRIMARY`: #2383E2
  - `PRIMARY_LIGHT`: #E8F3FC
  - `PRIMARY_LIGHTER`: #F3F9FE
  - `PRIMARY_DARK`: #1F6FC1

- **시맨틱 컬러** (Success, Info, Warning, Error)
  - 각각 배경색, 보더색, 텍스트 색상 3단계로 정의

#### 스타일 개선사항

1. **사이드바 네비게이션**
   - 깔끔한 배경 (#F7F6F3)
   - 부드러운 호버 효과
   - active 상태일 때 미묘한 배경색 변경

2. **버튼**
   - Primary: 소프트 블루, 8px 라운드 코너
   - Secondary: 흰 배경에 연한 보더
   - Ghost: 투명 배경, 호버 시에만 배경색

3. **카드 & 컨테이너**
   - `card`: 기본 카드 스타일
   - `card-clickable`: 호버 효과가 있는 클릭 가능한 카드
   - `card-done`: 왼쪽 초록색 액센트 보더
   - `card-active`: 왼쪽 파란색 액센트 보더

4. **Step Indicators**
   - `step-done`: 초록색 배경
   - `step-active`: 파란색 배경
   - `step-pending`: 뉴트럴 그레이 배경

5. **Callout Boxes**
   - `info`, `success`, `warning`, `error` 각각 Notion 스타일 적용

6. **입력 필드**
   - 깔끔한 8px 라운드 코너
   - 호버 시 보더 색상 변경
   - 포커스 시 파란색 보더
   - 넉넉한 패딩 (12px)

7. **탭**
   - 보더 없는 깔끔한 디자인
   - 선택된 탭만 하단에 파란색 언더라인
   - 호버 시 배경색 변경

8. **스크롤바**
   - 투명 배경
   - 미니멀한 핸들 디자인
   - 호버 시에만 강조

9. **테이블**
   - 깔끔한 라운드 코너
   - 헤더에 미묘한 배경색
   - 호버 및 선택 시 배경색 변경

10. **타이포그래피**
    - `title`: 26px, 700 weight
    - `heading1`: 22px, 700 weight
    - `heading2`: 18px, 600 weight
    - `heading3`: 16px, 600 weight
    - `subtitle`: 14px, secondary color
    - `caption`: 13px, tertiary color
    - `small`: 12px, tertiary color

11. **배지**
    - `badge`: 기본 뉴트럴
    - `badge-blue`: 파란색
    - `badge-green`: 초록색
    - `badge-orange`: 주황색
    - `badge-red`: 빨간색

### 2. `main_window.py`
- 사이드바 여백 증가 (16px)
- 타이틀 폰트 크기 및 두께 조정 (18px, 700)
- 섹션 헤더 스타일 개선
- 네비게이션 버튼을 전역 스타일시트 사용하도록 변경
- 프로젝트 배너 패딩 및 폰트 개선
- 활성 버튼 상태 관리 개선 (property 기반)

### 3. `main.py`
- 기본 폰트를 Notion과 유사한 "Segoe UI"로 변경
- 폰트 폴백 체인 추가

### 4. `pages/home_page.py`
- DashCard 위젯을 cssClass 기반 스타일링으로 변경
- 카드 내부 여백 증가 (24px)
- 아이콘 크기 증가 (40px)
- 레이아웃 간격 조정
- 모든 레이블을 cssClass property 사용하도록 변경
- 세퍼레이터 스타일 개선

### 5. `pages/settings_page.py`
- 여백 및 간격 조정 (40px, 32px)
- 모든 레이블을 cssClass property 사용하도록 변경

### 6. `widgets/status_box.py`
- 하드코딩된 스타일 제거
- cssClass 기반 스타일링으로 변경
- 패딩 증가 (16px, 12px)
- 폰트 크기 증가 (14px)

## Notion 스타일 특징 구현 완료

✅ 깔끔한 여백과 패딩
✅ 부드러운 라운드 코너 (6-10px)
✅ 밝고 깨끗한 컬러 팔레트
✅ 세련된 타이포그래피
✅ 부드러운 호버 효과
✅ 미니멀한 아이콘/버튼 스타일
✅ 깔끔한 구분선
✅ 미묘한 그림자 효과

## 실행 방법

```bash
# 가상환경 활성화
.venv\Scripts\activate

# 애플리케이션 실행
python main.py
```

## 기존 기능 호환성
- 모든 기존 기능은 그대로 유지됨
- 스타일만 변경되었으며 로직은 수정하지 않음
- cssClass property를 통한 스타일 적용으로 유연성 증가

## 추가 개선 가능 항목

1. **애니메이션**: PyQt6의 QPropertyAnimation을 활용한 부드러운 전환 효과
2. **다크 모드**: Notion처럼 라이트/다크 모드 토글 기능
3. **커스텀 스크롤바**: 더 세련된 스크롤바 디자인
4. **드래그 앤 드롭**: Notion처럼 블록 재정렬 기능
5. **인라인 에디팅**: 더 직관적인 편집 경험

## 참고사항
- 모든 색상은 Notion의 실제 디자인 시스템을 참고하여 선정
- 한국어 폰트 지원을 위해 "Malgun Gothic" 폴백 유지
- PyQt6 QSS의 제한사항으로 일부 고급 CSS 기능은 구현 불가
