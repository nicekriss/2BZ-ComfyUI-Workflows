# ③ 사용 순서 — 텍스트 → 이미지

1. **Resolution Selector**: 비율 + 메가픽셀. 1MP(1024²)가 기본, 2K는 1:1 + 4.0MP.
2. 노드 안 **prompt** 에 문장을 씁니다. 영문 텍스트는 따옴표로 감싸면 정확히 나옵니다. 짧은 한글은 되고 긴 한글 문장은 헛글자가 섞입니다.
3. **cfg는 1 고정**(공식 경로, 네거티브 미사용). steps 25 → 2K는 40 권장(공식 파이프라인 기본값).
4. Queue. 결과는 RGBA PNG로 저장됩니다.

## 투명 PNG
프롬프트를 이렇게 감쌉니다: `This is an RGBA format image with transparency. [설명]. The image has an alpha channel and a transparent background.`

## 실행 전 확인
- 3090 24GB 실측: 1MP 15s, 2K 99s(25스텝) / 157s(40스텝). 4070TiS 16GB: 1MP 12s, 2K 81s.
- 2K에서 40스텝은 미세 디테일이 3~5% 늘고 구도가 살짝 바뀝니다. 25로 시작해서 디테일 컷만 40.
- 같은 시드라도 2K는 25↔40 결과가 다릅니다. 시드 고정으로 스텝만 비교하지 마세요.
