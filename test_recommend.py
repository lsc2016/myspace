#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_recommend.py - agy 기준으로 근처 가게 3곳 추천 검증 시험
기획서: 2026-10-30_기준으로-근처-가게-3곳-추천하기.md
요구 원칙:
1. "파일이 나왔다"가 아니라 "agy가 기준에 맞춰 3곳을 골랐다"를 확인한다.
2. 필수 항목(이름, 거리, 전화, 고른 이유, 지도 링크)이 올바르게 채워졌는지 확인한다.
3. 기존 '내 장소'에 저장된 곳은 "가봤음"으로 정상 판정되는지 확인한다.
4. 조용한 대체 금지: 후보가 없거나 기준 미달 시 조용히 임의의 장소로 대체하지 않는지 확인한다.
5. index.html에 기준 편집창, 카카오 키 발급 안내 및 입력칸, 추천 UI가 구현되어 있는지 확인한다.
"""

import os
import sys
import math
import re
from recommend import (
    calc_distance,
    format_distance,
    parse_criteria,
    generate_reason,
    evaluate_and_recommend
)

def assert_true(cond, msg):
    if not cond:
        print(f"❌ 검증 실패: {msg}")
        sys.exit(1)
    else:
        print(f"  ✓ {msg}")

def test_criteria_file():
    print("\n[1] criteria.md 파일 검증")
    assert_true(os.path.exists("criteria.md"), "criteria.md 파일이 루트에 존재해야 함")
    with open("criteria.md", "r", encoding="utf-8") as f:
        content = f.read()
    
    assert_true(len(content.strip()) > 0, "criteria.md 파일 내용이 비어있지 않아야 함")
    
    required_cats = ["카페", "음식점", "미용실", "관광지", "마트", "기타"]
    parsed = parse_criteria(content)
    for cat in required_cats:
        assert_true(cat in parsed, f"criteria.md에 '{cat}' 카테고리 기준이 정의되어 있어야 함")
        crit = parsed[cat]
        assert_true(crit["radius"] > 0, f"'{cat}' 기준의 반경(m)이 파싱되어야 함 (현재: {crit['radius']}m)")
        assert_true(len(crit["condition"]) > 5, f"'{cat}' 기준의 한 줄 조건이 충분히 기술되어야 함")

def test_agy_selects_hair_salon():
    print("\n[2] agy 미용실 카테고리 3곳 선별 및 이유 생성 검증")
    with open("criteria.md", "r", encoding="utf-8") as f:
        criteria_text = f.read()

    # 기준 위치: 서울 시청 (37.5665, 126.9780)
    user_lat, user_lng = 37.5665, 126.9780

    candidates = [
        {
            "place_name": "살롱드헤어 시청점",
            "category_name": "서비스,맞춤 > 미용 > 미용실",
            "phone": "02-111-2222",
            "y": 37.5670, "x": 126.9790,
            "place_url": "https://place.map.kakao.com/101",
            "road_address_name": "서울 중구 태평로1가 10"
        },
        {
            "place_name": "청담바버샵 시청점",
            "category_name": "서비스,맞춤 > 미용 > 미용실",
            "phone": "02-333-4444",
            "y": 37.5680, "x": 126.9800,
            "place_url": "https://place.map.kakao.com/102",
            "road_address_name": "서울 중구 무교로 15"
        },
        {
            "place_name": "헤어스타일 아뜰리에",
            "category_name": "서비스,맞춤 > 미용 > 헤어살롱",
            "phone": "02-555-6666",
            "y": 37.5700, "x": 126.9810,
            "place_url": "https://place.map.kakao.com/103",
            "road_address_name": "서울 종로구 서린동 20"
        },
        {
            "place_name": "멀리있는 헤어샵",
            "category_name": "서비스,맞춤 > 미용 > 미용실",
            "phone": "02-777-8888",
            "y": 37.6200, "x": 127.0500, # 거리 약 8km 이상 (반경 2km 초과로 탈락해야 함)
            "place_url": "https://place.map.kakao.com/104",
            "road_address_name": "서울 노원구 상계동 99"
        },
        {
            "place_name": "시청네일케어",
            "category_name": "서비스,맞춤 > 미용 > 네일아트", # 헤어 아님
            "phone": "02-888-9999",
            "y": 37.5666, "x": 126.9782,
            "place_url": "https://place.map.kakao.com/105",
            "road_address_name": "서울 중구 태평로1가 5"
        }
    ]

    saved_places = [
        {
            "id": "p-saved-101",
            "name": "살롱드헤어 시청점",
            "address": "서울 중구 태평로1가 10",
            "category": "미용실",
            "lat": 37.5670,
            "lng": 126.9790
        }
    ]

    top3 = evaluate_and_recommend("미용실", candidates, user_lat, user_lng, criteria_text, saved_places)

    assert_true(len(top3) == 3, f"agy가 반경 내 적합한 미용실 3곳을 정확히 골라내야 함 (골라낸 수: {len(top3)})")

    selected_names = [p["name"] for p in top3]
    assert_true("멀리있는 헤어샵" not in selected_names, "반경 2km를 초과하는 먼 가게는 제외되어야 함")
    assert_true("살롱드헤어 시청점" in selected_names, "가장 가깝고 기준에 부합하는 '살롱드헤어 시청점'이 선별되어야 함")

    # 필수 항목 검증
    for p in top3:
        assert_true(bool(p["name"]), "가게 이름이 존재해야 함")
        assert_true(p["distance"] > 0, f"현재 위치 기준 거리가 계산되어야 함 (현재: {p['distance']}m)")
        assert_true(bool(p["distance_text"]), "거리 텍스트가 표시되어야 함")
        assert_true(bool(p["phone"]), "전화번호 항목이 포함되어야 함")
        assert_true(bool(p["url"]), "카카오 지도 링크가 포함되어야 함")
        assert_true(bool(p["reason"]), "agy가 왜 골랐는지 한 줄 이유가 작성되어야 함")
        
        # 이유 내용 검증: 거리 정보와 카테고리 기준 부합 이유가 들어있는지
        assert_true(any(k in p["reason"] for k in ["거리", "위치", "방문"]), "선별 이유에 위치/거리 접근성 평가가 포함되어야 함")
        assert_true(any(k in p["reason"] for k in ["헤어", "케어", "디자이너", "살롱", "미용"]), "미용실 기준의 특화 이유가 명시되어야 함")

    # 기존 장소 연동 ("가봤음") 검증
    saved_target = next(p for p in top3 if p["name"] == "살롱드헤어 시청점")
    assert_true(saved_target["is_saved"] is True, "'살롱드헤어 시청점'은 이미 저장된 장소이므로 '가봤음(is_saved=True)'이어야 함")
    assert_true(saved_target["saved_id"] == "p-saved-101", "저장된 장소의 ID가 매핑되어야 함")

    other_target = next(p for p in top3 if p["name"] != "살롱드헤어 시청점")
    assert_true(other_target["is_saved"] is False, "저장되지 않은 새로운 장소는 is_saved=False이어야 함")

def test_agy_selects_cafe():
    print("\n[3] agy 카페 카테고리 3곳 선별 검증")
    with open("criteria.md", "r", encoding="utf-8") as f:
        criteria_text = f.read()

    user_lat, user_lng = 37.4979, 127.0276 # 강남역

    candidates = [
        {
            "place_name": "강남로스터스 카페",
            "category_name": "음식점 > 카페 > 커피전문점",
            "phone": "02-1234-5678",
            "y": 37.4985, "x": 127.0280,
            "place_url": "https://place.map.kakao.com/c1",
            "road_address_name": "서울 강남구 테헤란로 1"
        },
        {
            "place_name": "조용한 디저트 베이커리",
            "category_name": "음식점 > 카페 > 테마카페 > 디저트카페",
            "phone": "02-2345-6789",
            "y": 37.4990, "x": 127.0290,
            "place_url": "https://place.map.kakao.com/c2",
            "road_address_name": "서울 강남구 테헤란로 5"
        },
        {
            "place_name": "공부하기 좋은 북카페",
            "category_name": "음식점 > 카페 > 북카페",
            "phone": "02-3456-7890",
            "y": 37.4970, "x": 127.0260,
            "place_url": "https://place.map.kakao.com/c3",
            "road_address_name": "서울 서초구 강남대로 10"
        },
        {
            "place_name": "강남역 삼겹살식당",
            "category_name": "음식점 > 한식 > 육류,고기", # 카페 아님
            "phone": "02-9999-8888",
            "y": 37.4980, "x": 127.0277,
            "place_url": "https://place.map.kakao.com/c4",
            "road_address_name": "서울 서초구 강남대로 20"
        }
    ]

    top3 = evaluate_and_recommend("카페", candidates, user_lat, user_lng, criteria_text, [])
    assert_true(len(top3) == 3, f"카페 후보 중 최적 3곳을 선정해야 함 (선정: {len(top3)})")

    for p in top3:
        assert_true("카페" in p["reason"] or "커피" in p["reason"] or "휴식" in p["reason"], 
                    f"선별 이유에 카페/커피/휴식 기준이 반영되어야 함 (이유: {p['reason']})")

def test_strict_no_silent_fallback():
    print("\n[4] 조용한 대체 금지(Strict No Silent Fallback) 원칙 검증")
    with open("criteria.md", "r", encoding="utf-8") as f:
        criteria_text = f.read()

    user_lat, user_lng = 37.5665, 126.9780

    # 후보가 없을 때: 임의의 가짜 장소를 조용히 대신 추천하지 않고 빈 리스트 반환해야 함
    empty_result = evaluate_and_recommend("음식점", [], user_lat, user_lng, criteria_text, [])
    assert_true(len(empty_result) == 0, "후보가 없을 때 엉뚱한 견본 값으로 조용히 대체하지 않고 빈 목록을 반환해야 함")

    # 후보가 모두 기준 반경(음식점 1.5km)을 훨씬 벗어난 경우 (거리 10km 이상)
    far_candidates = [
        {
            "place_name": "수원맛집",
            "category_name": "음식점 > 한식",
            "y": 37.2636, "x": 127.0286, # 서울 시청에서 약 33km
            "phone": "031-111-2222",
            "place_url": "https://place.map.kakao.com/far1"
        }
    ]
    far_result = evaluate_and_recommend("음식점", far_candidates, user_lat, user_lng, criteria_text, [])
    assert_true(len(far_result) == 0, "기준 반경을 초과하는 장소를 조용히 대신 추천하지 않아야 함")

def test_index_html_integration():
    print("\n[5] index.html 설정 UI 및 카테고리 추천 UI 구현 정적 검증")
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()

    # 1. 카카오 REST API 키 등록 및 4단계 발급 안내
    assert_true("카카오 지역 검색 키" in html, "설정 화면에 카카오 지역 검색 키 섹션이 존재해야 함")
    assert_true("id=\"stKakaoKey\"" in html or "id='stKakaoKey'" in html, "카카오 REST API 키 입력 필드(stKakaoKey)가 존재해야 함")
    assert_true("btnSaveKakaoKey" in html, "카카오 키 저장 버튼(btnSaveKakaoKey)이 존재해야 함")
    assert_true("developers.kakao.com" in html, "카카오 개발자 사이트 링크 안내가 포함되어야 함")
    assert_true("애플리케이션 추가하기" in html, "무료 키 발급 4단계 안내가 포함되어야 함")

    # 2. criteria.md 추천 기준 편집 영역
    assert_true("추천 기준 관리" in html, "설정 화면에 추천 기준 관리 섹션이 존재해야 함")
    assert_true("id=\"stCriteria\"" in html or "id='stCriteria'" in html, "추천 기준 텍스트 영역(stCriteria)이 존재해야 함")
    assert_true("btnSaveCriteria" in html, "추천 기준 저장 버튼이 존재해야 함")
    assert_true("btnResetCriteria" in html, "기본 기준 불러오기 버튼이 존재해야 함")

    # 3. 카테고리 칩 선택 시 내 장소 아래 추천 섹션 노출
    assert_true("rec-reason" in html, "추천 이유(rec-reason) 스타일 및 요소가 존재해야 함")
    assert_true("badge visited" in html or "가봤음" in html, "'가봤음' 뱃지 표시가 구현되어야 함")
    assert_true("data-rec-add" in html, "추천 장소를 내 장소로 바로 추가하는 버튼(data-rec-add)이 구현되어야 함")
    assert_true("fetchRecommendations" in html, "카테고리 연동 추천 수집 함수(fetchRecommendations)가 구현되어야 함")

def main():
    print("==================================================")
    print("   기준으로 근처 가게 3곳 추천 기능 검증 시험   ")
    print("==================================================")
    test_criteria_file()
    test_agy_selects_hair_salon()
    test_agy_selects_cafe()
    test_strict_no_silent_fallback()
    test_index_html_integration()
    print("\n==================================================")
    print("🎉 모든 검증 시험을 성공적으로 통과했습니다!")
    print("==================================================")

if __name__ == "__main__":
    main()
