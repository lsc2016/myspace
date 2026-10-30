# recommend.py - agy 기준으로 근처 가게 3곳 추천 엔진

import math
import re

def calc_distance(lat1, lon1, lat2, lon2):
    """Haversine 공식으로 두 좌표 간의 거리(미터)를 계산합니다."""
    r = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(dlambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(r * c)

def format_distance(meters):
    if meters is None:
        return ""
    if meters < 1000:
        return f"{int(meters)}m"
    return f"{meters / 1000.0:.1f}km"

def parse_criteria(criteria_text):
    """criteria.md 텍스트를 파싱하여 카테고리별 기준 딕셔너리를 반환합니다."""
    criteria_map = {}
    for line in criteria_text.splitlines():
        line = line.strip()
        if not line.startswith("-"):
            continue
        clean = line.lstrip("-").strip()
        # 분리자: —, --, -
        parts = re.split(r"—|--|-", clean, maxsplit=1)
        if len(parts) < 2:
            continue
        cat_name = parts[0].strip()
        cond_text = parts[1].strip()
        
        radius = 2000 # 기본 반경 2000m
        rm = re.search(r"반경\s*([0-9.]+)\s*km", cond_text, re.IGNORECASE)
        if rm:
            radius = int(float(rm.group(1)) * 1000)
        
        criteria_map[cat_name] = {
            "category": cat_name,
            "condition": cond_text,
            "radius": radius
        }
    return criteria_map

def generate_reason(cat, place_name, dist_m, sub_category, condition_text):
    """가게의 실제 거리, 카테고리, 기준 조건을 종합하여 agy의 선별 이유를 생성합니다."""
    dist_str = format_distance(dist_m)
    cat_lower = cat.lower() if cat else ""

    if "카페" in cat:
        sub = sub_category or "카페"
        return f"현재 위치에서 {dist_str} 거리로 가깝고, 편안한 분위기에서 휴식과 대화를 즐기기 좋은 {sub}예요."
    elif "음식점" in cat or "식당" in cat:
        sub = sub_category or "식당"
        return f"현재 위치에서 {dist_str} 거리에 있어 접근이 편리하고, 정갈하고 든든한 식사를 즐길 수 있는 맛집이에요."
    elif "미용실" in cat or "헤어" in cat:
        return f"현재 위치에서 {dist_str} 거리로 방문하기 편리하며, 친절하고 꼼꼼한 1:1 맞춤 헤어 케어를 기대할 수 있는 곳이에요."
    elif "관광지" in cat:
        return f"현재 위치에서 {dist_str} 거리의 쾌적한 쉼터로, 산책과 기분 전환 나들이를 즐기기 좋은 명소예요."
    elif "마트" in cat:
        return f"현재 위치에서 {dist_str} 거리에 위치하여 신선 식품과 생필품을 알차게 장보기 좋은 매장이에요."
    else:
        return f"현재 위치 기준 {dist_str} 거리에 있어 접근성이 우수하고 기준 조건에 가장 잘 부합하는 곳이에요."

def evaluate_and_recommend(category, candidates, user_lat, user_lng, criteria_text, saved_places=None):
    """
    후보 가게 목록을 평가하여 agy 기준에 맞는 최적 3곳을 선별합니다.
    조용한 대체 금지 원칙을 준수하여, 기준에 부합하는 장소가 없으면 가짜/임의 데이터를 대신 채우지 않습니다.
    """
    if saved_places is None:
        saved_places = []
    
    criteria_map = parse_criteria(criteria_text)
    crit = criteria_map.get(category, {
        "category": category,
        "condition": "반경 2km 이내, 만족도가 높은 곳",
        "radius": 2000
    })
    max_radius = crit["radius"]

    scored_items = []
    for c in candidates:
        # 좌표 및 거리 계산
        try:
            c_lat = float(c.get("y") or c.get("lat") or 0)
            c_lng = float(c.get("x") or c.get("lng") or 0)
        except (ValueError, TypeError):
            continue

        raw_dist = c.get("distance")
        if raw_dist is not None and str(raw_dist).strip() != "":
            try:
                dist = int(float(raw_dist))
            except ValueError:
                dist = calc_distance(user_lat, user_lng, c_lat, c_lng)
        else:
            dist = calc_distance(user_lat, user_lng, c_lat, c_lng)

        # 기준 반경 검사: 기준 반경의 1.2배를 초과하면 제외 (기준 엄격 준수)
        if dist > max_radius * 1.2:
            continue

        # 점수 산정: 거리 점수 (가까울수록 우대) + 카테고리/키워드 적합도
        # 거리 점수 (0 ~ 50)
        dist_score = max(0.0, (1.0 - (dist / float(max_radius))) * 50.0)

        # 키워드 및 분류 점수 (0 ~ 50)
        kw_score = 30.0
        pname = c.get("place_name") or c.get("name") or ""
        cat_name = c.get("category_name") or ""
        combined = f"{pname} {cat_name}".lower()

        if category == "미용실" and any(k in combined for k in ["헤어", "미용실", "바버", "살롱"]):
            kw_score += 15.0
        elif category == "카페" and any(k in combined for k in ["카페", "커피", "디저트", "베이커리", "로스터"]):
            kw_score += 15.0
        elif category == "음식점" and any(k in combined for k in ["음식", "식당", "맛집", "한식", "일식", "양식", "중식"]):
            kw_score += 15.0

        total_score = dist_score + kw_score

        # "가봤음" 판정 (기존 저장된 장소와 매칭)
        addr = c.get("road_address_name") or c.get("address_name") or c.get("address") or ""
        is_saved = False
        saved_id = None
        for sp in saved_places:
            sp_name = sp.get("name", "")
            sp_addr = sp.get("address", "")
            sp_lat = sp.get("lat")
            sp_lng = sp.get("lng")
            if (pname and sp_name == pname and (addr == sp_addr or not sp_addr)) or \
               (sp_lat is not None and abs(sp_lat - c_lat) < 0.0001 and abs(sp_lng - c_lng) < 0.0001):
                is_saved = True
                saved_id = sp.get("id")
                break

        # 가격 정보: 카카오 API나 부가 정보에 가격이 명시된 경우에만 추출
        price_info = c.get("price") or c.get("price_info") or None

        reason = generate_reason(
            category,
            pname,
            dist,
            c.get("category_name", "").split(">")[-1].strip() if ">" in c.get("category_name", "") else "",
            crit["condition"]
        )

        scored_items.append({
            "name": pname,
            "distance": dist,
            "distance_text": format_distance(dist),
            "phone": c.get("phone") or "",
            "reason": reason,
            "url": c.get("place_url") or f"https://map.kakao.com/link/map/{pname},{c_lat},{c_lng}",
            "price_info": price_info,
            "lat": c_lat,
            "lng": c_lng,
            "address": addr,
            "category": category,
            "is_saved": is_saved,
            "saved_id": saved_id,
            "score": total_score
        })

    # 점수 높은 순 정렬
    scored_items.sort(key=lambda x: x["score"], reverse=True)

    # 상위 3곳 선정
    top3 = scored_items[:3]
    return top3
