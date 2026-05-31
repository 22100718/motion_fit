# Motion Fit — AI 기반 자세 인식 운동 웹앱 v4.0
# 개선: 세트별/총점 UI, 한국어 숫자 음성, 피드백 세분화, 반동감지, 등급(S/A/B/C)
from flask import Flask, request, render_template_string, redirect, url_for, jsonify, send_from_directory
import csv, json
from datetime import datetime
from pathlib import Path

app = Flask(__name__)
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "motionfit_data"
DATA_DIR.mkdir(exist_ok=True)
CSV_PATH = DATA_DIR / "session_logs.csv"
STATIC_DIR = BASE_DIR / "static"

exercise_names = {
    "squat":"스쿼트","pushup":"푸시업","lunge":"런지","pullup":"풀업",
    "legraise":"레그레이즈","shoulderpress":"숄더프레스","lateralraise":"레터럴레이즈",
    "dumbbellcurl":"덤벨컬","triceppushdown":"트라이셉 푸쉬다운",
}
exercise_demo = {
    "squat":          "bodyweight-squat.gif",
    "lateralraise":   "Dumbbell-Lateral-Raise.webp",
    "shoulderpress":  "Seated-dumbbell-shoulder-press.webp",
    "dumbbellcurl":   "dumbbellcurl.webp",
    "triceppushdown": "triceps-pushdown-with-straight-handle.webp",
    "lunge":          "Dumbbell-Lunge.webp",
    "legraise":       "LegRaise.webp",
    "pushup":         "PushUp.gif",
    "pullup":         "pullup.gif",
}

exercise_meta = {
    "squat":        {"tag":"하체","goal":"횟수","camera":"측면 권장",          "target":12,"sets":3},
    "pushup":       {"tag":"상체","goal":"횟수","camera":"측면 권장",          "target":10,"sets":3},
    "lunge":        {"tag":"하체","goal":"횟수","camera":"측면 권장",          "target":10,"sets":3},
    "pullup":       {"tag":"등",  "goal":"횟수","camera":"정면 또는 약간 측면","target": 8,"sets":3},
    "legraise":     {"tag":"코어","goal":"횟수","camera":"측면 권장",          "target":12,"sets":3},
    "shoulderpress":{"tag":"상체","goal":"횟수","camera":"정면 권장",          "target":12,"sets":3},
    "lateralraise":   {"tag":"어깨","goal":"횟수","camera":"정면 권장",          "target":12,"sets":3},
    "dumbbellcurl":   {"tag":"상체","goal":"횟수","camera":"측면 권장",          "target":12,"sets":3},
    "triceppushdown": {"tag":"상체","goal":"횟수","camera":"측면 권장",          "target":12,"sets":3},
}
exercise_tips = {
    "squat":        ["단일 카메라 기준으로는 측면 구도가 가장 안정적입니다","내려갈 때 엉덩이를 뒤로 보내고 올라올 때 발바닥 전체로 밀어주세요","무릎은 발끝 방향을 따라가게 유지하세요","평행 정도까지 앉았다면 과하게 더 낮추려 하지 않아도 됩니다"],
    "pushup":       ["몸통을 어깨부터 발끝까지 일직선으로 유지하세요","가슴이 바닥에 거의 닿을 만큼 내려가세요","측면에서 어깨·골반·발이 보이게 위치하세요","팔꿈치가 너무 벌어지지 않게 하세요"],
    "lunge":        ["앞무릎이 발 안쪽으로 무너지지 않게 하세요","상체는 최대한 수직으로 유지하세요","측면에서 골반·앞무릎·앞발목이 모두 보이게 위치하세요","앞무릎이 90~100도 정도까지 내려오면 충분한 깊이로 봅니다"],
    "pullup":       ["팔을 충분히 편 뒤 턱이 손 높이 근처까지 오도록 당기세요","상단 도달 후 내려오며 1회를 마무리합니다","얼굴과 손목이 함께 보이게 위치하세요","반동보다 수직 이동과 하강 제어를 우선하세요"],
    "legraise":     ["다리를 곧게 펴서 올리세요","허리가 과하게 들리지 않게 복부를 고정하세요","측면에서 어깨·골반·무릎·발끝이 모두 보이게 위치하세요","내려왔다가 다시 들어올려 상단에 도달하면 1회로 봅니다"],
    "shoulderpress":["양팔 높이를 대칭으로 맞추세요","머리 위까지 밀어올린 뒤 내려오며 1회를 마무리합니다","정면에서 양어깨·팔꿈치·손목이 모두 보이고 손목 안쪽이 카메라를 향하게 해주세요","허리를 과하게 젖히지 마세요"],
    "lateralraise":   ["양팔을 어깨 높이 전후까지 들어올리세요","상단 도달 뒤 천천히 내리며 1회를 마무리합니다","정면에서 양팔 전체가 보이게 위치하세요","팔꿈치는 살짝만 구부리고 반동은 줄이세요"],
    "dumbbellcurl":   ["어깨는 중립, 팔꿈치를 몸통에 고정한 채 들어올리세요","손바닥이 위를 향하는 회외(supination) 자세를 유지하세요","측면에서 어깨·팔꿈치·손목이 모두 보이게 위치하세요","반동 없이 천천히 내리며 1회를 마무리합니다"],
    "triceppushdown": ["상체를 살짝 앞으로 숙이고 팔꿈치를 몸통에 고정하세요","팔을 완전히 펴서 삼두근을 완전 수축시키세요","측면에서 어깨·팔꿈치·손목이 모두 보이게 위치하세요","올라올 때 팔꿈치가 옆으로 벌어지지 않게 하세요"],
}
exercise_limitations = {
    "squat":        ["2D 관절 추정이라 발끝 각도와 무릎 회전을 완벽하게 측정하진 못합니다","카메라가 너무 낮거나 가까우면 실제보다 덜 앉은 것으로 보일 수 있습니다","측면에서 하체 전체가 잘리지 않게 들어와야 깊이 판정이 안정적입니다"],
    "pushup":       ["손목 각도나 가슴의 실제 바닥 접촉은 카메라 한 대로 완전 판별하기 어렵습니다","너무 비스듬한 구도에서는 몸통 일직선 판정이 흔들릴 수 있습니다"],
    "lunge":        ["앞뒤 발 간격이 큰 동작이라 하체 일부가 잘리면 깊이 판정이 급격히 불안정해집니다","정면 회전이 섞이면 앞무릎과 발목 정렬 오차가 커질 수 있습니다"],
    "pullup":       ["철봉 가림, 손 위치, 상체 회전에 따라 턱 높이 판정이 달라질 수 있습니다","손이 프레임 밖으로 나가면 상단 도달 여부가 불안정해집니다"],
    "legraise":     ["골반 말림과 허리 들림은 2D 기준이라 매트 두께나 카메라 높이에 영향을 받습니다","측면이 아니라 사선 구도면 다리 높이가 실제보다 낮게 보일 수 있습니다"],
    "shoulderpress":["현재 Pose 모델만으로 손목 안쪽/바깥쪽 면 자체를 정확히 구분하진 못하고 전완 정렬로 근사 판정합니다","덤벨·바벨이 손목 랜드마크를 가리면 상단/하단 판정이 흔들릴 수 있습니다","한쪽 팔이 카메라 뒤로 숨으면 좌우 대칭 점수가 보수적으로 나옵니다"],
    "lateralraise":   ["손목 높이 중심이라 손보다 팔꿈치가 먼저 올라가는 패턴은 일부 오차가 있을 수 있습니다","몸통 회전이 크면 양팔 높이 차이를 실제보다 크게 볼 수 있습니다"],
    "dumbbellcurl":   ["팔꿈치 위치가 카메라에 가려지면 굴곡 각도 판정이 불안정해질 수 있습니다","덤벨이 손목 랜드마크를 가리면 상단 도달 여부 판정이 흔들릴 수 있습니다","좌우 팔을 번갈아 하는 경우 한쪽이 프레임 밖으로 나갈 수 있습니다"],
    "triceppushdown": ["케이블 기구나 밴드가 손목·팔꿈치 랜드마크를 가리면 신전 각도 판정이 어렵습니다","측면 구도가 아니면 팔꿈치 고정 여부 판정이 부정확할 수 있습니다","상체를 과하게 숙이면 어깨 랜드마크 위치가 달라져 오차가 생길 수 있습니다"],
}

# EMG 채널 매핑 & MVC 가이드
# channels 리스트: 센서 순서대로 CH1~CHn 에 대응
# side: "left"/"right"/"both" — 좌우 불균형 분석에 사용
# feedback_logic: 피드백 판단 기준 설명 (UI 표시 + 분석용)
# calib_rest: 힘 빼기(안정) 자세 설명
# calib_mvc: 최대 수축 자세 설명
exercise_emg_guide = {
    "squat": {
        "muscle": "대퇴사두근 (Quadriceps)",
        "reference": "정강이뼈 또는 슬개골(무릎뼈) 부위",
        "channels": [
            {"ch": 1, "side": "left",  "label": "왼쪽 외측광근",  "placement": "왼쪽 허벅지 바깥쪽 전면, 엉덩이~무릎 중간"},
            {"ch": 2, "side": "right", "label": "오른쪽 외측광근", "placement": "오른쪽 허벅지 바깥쪽 전면, 엉덩이~무릎 중간"},
            {"ch": 3, "side": "left",  "label": "왼쪽 대퇴직근",  "placement": "왼쪽 허벅지 전면 중앙, 엉덩이~무릎 중간"},
            {"ch": 4, "side": "right", "label": "오른쪽 대퇴직근", "placement": "오른쪽 허벅지 전면 중앙, 엉덩이~무릎 중간"},
        ],
        "mvc_protocol": [
            "앉은 자세, 무릎 60~90° 굴곡 유지",
            "움직이지 않는 저항에 대해 최대한 무릎을 펴는 힘 발휘",
            "3~5초 유지 / 1~2분 휴식 후 2~3회 반복",
        ],
        "calib_rest": {
            "title": "① 힘 빼기 — 안정 자세 (3초)",
            "steps": [
                "의자에 편하게 앉아 허벅지 힘을 완전히 뺍니다",
                "다리는 자연스럽게 바닥에 놓고 움직이지 않습니다",
                "이 상태에서 버튼을 누르고 3초간 유지하세요",
            ],
        },
        "calib_mvc": {
            "title": "② 최대 수축 — MVC 자세 (3초)",
            "steps": [
                "의자에 앉아 무릎을 약 60~90° 구부립니다",
                "파트너가 발목 위를 손으로 고정하거나, 의자 다리에 발을 걸어둡니다",
                "최대한 세게 무릎을 펴는 힘을 발휘하며 버튼을 누르고 3초 유지합니다",
                "실제로 다리가 움직이지 않아도 괜찮습니다 — 힘만 최대로 내면 됩니다",
            ],
        },
        "feedback_logic": [
            {"type": "activation", "desc": "CH1+CH3 (왼쪽) 평균 < 40% MVC → '왼쪽 대퇴 자극 부족'"},
            {"type": "activation", "desc": "CH2+CH4 (오른쪽) 평균 < 40% MVC → '오른쪽 대퇴 자극 부족'"},
            {"type": "asymmetry",  "desc": "좌우 차이 > 20%p → '좌우 불균형 — 약한 쪽 의식하여 힘 주기'"},
            {"type": "eccentric",  "desc": "올라올 때 MAV < 내려갈 때 30% 미만 → '올라올 때 너무 빠름'"},
        ],
    },
    "lateralraise": {
        "muscle": "삼각근 중부 (Middle Deltoid)",
        "reference": "쇄골 부위 또는 어깨뼈 상부",
        "channels": [
            {"ch": 1, "side": "left",  "label": "왼쪽 삼각근 중부",  "placement": "왼쪽 어깨 상부~위팔 중간, 삼각근 중부 근복"},
            {"ch": 2, "side": "right", "label": "오른쪽 삼각근 중부", "placement": "오른쪽 어깨 상부~위팔 중간, 삼각근 중부 근복"},
        ],
        "mvc_protocol": [
            "앉거나 선 자세, 어깨 약 90° 외전 유지",
            "움직이지 않는 저항에 대해 최대한 팔을 옆으로 드는 힘 발휘",
            "3~5초 유지 / 1~2분 휴식 후 2~3회 반복",
        ],
        "calib_rest": {
            "title": "① 힘 빼기 — 안정 자세 (3초)",
            "steps": [
                "편하게 서거나 앉아 양팔을 몸통 옆에 자연스럽게 늘어뜨립니다",
                "어깨 힘을 완전히 빼고 팔이 중력에 의해 내려진 상태를 유지합니다",
                "이 상태에서 버튼을 누르고 3초간 유지하세요",
            ],
        },
        "calib_mvc": {
            "title": "② 최대 수축 — MVC 자세 (3초)",
            "steps": [
                "팔을 옆으로 약 90° 들어 올려 어깨 높이에 맞춥니다",
                "파트너가 팔꿈치 위를 아래로 눌러 저항을 줍니다",
                "최대한 세게 팔을 옆으로 들어올리는 힘을 발휘하며 버튼을 누르고 3초 유지합니다",
                "양쪽을 동시에 측정합니다",
            ],
        },
        "feedback_logic": [
            {"type": "activation", "desc": "CH1 또는 CH2 < 35% MVC → '해당 쪽 삼각근 자극 부족 — 팔꿈치 높이 확인'"},
            {"type": "asymmetry",  "desc": "좌우 차이 > 15%p → '좌우 불균형 — 약한 쪽 팔 더 의식하기'"},
            {"type": "eccentric",  "desc": "내릴 때 MAV < 올릴 때 30% 미만 → '내릴 때 너무 빠름 — 천천히 제어하기'"},
        ],
    },
    "dumbbellcurl": {
        "muscle": "상완이두근 (Biceps Brachii)",
        "reference": "팔꿈치 뼈 또는 쇄골 부위",
        "channels": [
            {"ch": 1, "side": "left",  "label": "왼쪽 이두근",  "placement": "왼쪽 위팔 전면 중앙, 어깨~팔꿈치 중간 (이두근 근복)"},
            {"ch": 2, "side": "right", "label": "오른쪽 이두근", "placement": "오른쪽 위팔 전면 중앙, 어깨~팔꿈치 중간 (이두근 근복)"},
        ],
        "mvc_protocol": [
            "앉은 자세, 어깨 중립, 팔꿈치 약 90° 굴곡",
            "손바닥이 위를 향하는 회외(supination) 상태 유지",
            "움직이지 않는 저항에 대해 최대한 팔을 굽히는 힘 발휘",
            "3~5초 유지 / 1~2분 휴식 후 2~3회 반복",
        ],
        "calib_rest": {
            "title": "① 힘 빼기 — 안정 자세 (3초)",
            "steps": [
                "의자에 앉아 양팔을 무릎 위에 자연스럽게 올려놓습니다",
                "손바닥이 위를 향하게 하고 이두근 힘을 완전히 뺍니다",
                "이 상태에서 버튼을 누르고 3초간 유지하세요",
            ],
        },
        "calib_mvc": {
            "title": "② 최대 수축 — MVC 자세 (3초)",
            "steps": [
                "의자에 앉아 팔꿈치를 약 90° 구부리고 손바닥이 위를 향하게 합니다",
                "파트너가 손목 위에서 아래로 눌러 저항을 줍니다",
                "최대한 세게 팔을 굽히는 힘을 발휘하며 버튼을 누르고 3초 유지합니다",
                "팔꿈치는 몸통에 붙인 채 움직이지 않아도 됩니다",
            ],
        },
        "feedback_logic": [
            {"type": "activation", "desc": "CH1 또는 CH2 < 40% MVC → '이두근 자극 부족 — 완전 굴곡까지 올리기'"},
            {"type": "asymmetry",  "desc": "좌우 차이 > 20%p → '양팔 불균형 — 약한 쪽 단독 훈련 고려'"},
            {"type": "eccentric",  "desc": "내릴 때 MAV < 올릴 때 30% 미만 → '내릴 때 너무 빠름 — 천천히 제어하기'"},
        ],
    },
    "triceppushdown": {
        "muscle": "상완삼두근 (Triceps Brachii)",
        "reference": "팔꿈치 뼈 또는 어깨 상부",
        "channels": [
            {"ch": 1, "side": "left",  "label": "왼쪽 삼두근",  "placement": "왼쪽 위팔 후면 중앙, 어깨~팔꿈치 중간 (삼두근 근복)"},
            {"ch": 2, "side": "right", "label": "오른쪽 삼두근", "placement": "오른쪽 위팔 후면 중앙, 어깨~팔꿈치 중간 (삼두근 근복)"},
        ],
        "mvc_protocol": [
            "앉거나 선 자세, 어깨 중립, 팔꿈치 약 90° 굴곡",
            "움직이지 않는 저항에 대해 최대한 팔을 펴는 힘 발휘",
            "3~5초 유지 / 1~2분 휴식 후 2~3회 반복",
        ],
        "calib_rest": {
            "title": "① 힘 빼기 — 안정 자세 (3초)",
            "steps": [
                "편하게 서거나 앉아 양팔을 몸통 옆에 자연스럽게 늘어뜨립니다",
                "삼두근 힘을 완전히 빼고 팔이 중력에 의해 내려진 상태를 유지합니다",
                "이 상태에서 버튼을 누르고 3초간 유지하세요",
            ],
        },
        "calib_mvc": {
            "title": "② 최대 수축 — MVC 자세 (3초)",
            "steps": [
                "팔꿈치를 약 90° 구부려 몸통 옆에 고정합니다",
                "파트너가 손목 위에서 위쪽으로 들어올려 저항을 줍니다",
                "최대한 세게 팔을 펴는(아래로 미는) 힘을 발휘하며 버튼을 누르고 3초 유지합니다",
                "팔꿈치가 몸통에서 떨어지지 않게 고정합니다",
            ],
        },
        "feedback_logic": [
            {"type": "activation", "desc": "CH1 또는 CH2 < 40% MVC → '삼두근 자극 부족 — 팔꿈치 완전 신전까지 밀기'"},
            {"type": "asymmetry",  "desc": "좌우 차이 > 20%p → '좌우 불균형 — 팔꿈치 고정 위치 확인'"},
            {"type": "eccentric",  "desc": "올라올 때 MAV < 내릴 때 30% 미만 → '올라올 때 너무 빠름 — 천천히 제어하기'"},
        ],
    },
    "pushup": {
        "muscle": "대흉근 (Pectoralis Major) · 삼두근 보조",
        "reference": "쇄골 아래 또는 흉골 부위",
        "channels": [
            {"ch": 1, "side": "left",  "label": "왼쪽 대흉근",  "placement": "왼쪽 가슴 중앙~바깥쪽, 유두 높이 2~3cm 위"},
            {"ch": 2, "side": "right", "label": "오른쪽 대흉근", "placement": "오른쪽 가슴 중앙~바깥쪽, 유두 높이 2~3cm 위"},
        ],
        "mvc_protocol": [
            "벽 밀기 자세, 팔꿈치 약 90° 굴곡 유지",
            "움직이지 않는 벽에 대해 최대한 가슴으로 미는 힘 발휘",
            "3~5초 유지 / 1~2분 휴식 후 2~3회 반복",
        ],
        "calib_rest": {
            "title": "① 힘 빼기 — 안정 자세 (3초)",
            "steps": [
                "편하게 서거나 앉아 양팔을 몸통 옆에 자연스럽게 늘어뜨립니다",
                "가슴 힘을 완전히 빼고 어깨를 내립니다",
                "이 상태에서 버튼을 누르고 3초간 유지하세요",
            ],
        },
        "calib_mvc": {
            "title": "② 최대 수축 — MVC 자세 (3초)",
            "steps": [
                "벽 앞에 서서 양손을 어깨 높이 벽에 댑니다",
                "팔꿈치를 약 90°로 구부리고 가슴이 벽에 가까워지게 합니다",
                "최대한 세게 벽을 미는 힘을 발휘하며 버튼을 누르고 3초 유지합니다",
                "실제로 몸이 움직이지 않아도 됩니다",
            ],
        },
        "feedback_logic": [
            {"type": "activation", "desc": "CH1 또는 CH2 < 40% MVC → '가슴 자극 부족 — 더 내려가거나 팔꿈치 각도 확인'"},
            {"type": "asymmetry",  "desc": "좌우 차이 > 20%p → '좌우 불균형 — 손 위치나 체중 분배 확인'"},
            {"type": "eccentric",  "desc": "올라올 때 MAV < 내려갈 때 30% 미만 → '올라올 때 너무 빠름 — 천천히 제어하기'"},
        ],
    },
    "lunge": {
        "muscle": "대퇴사두근 · 대둔근 (Gluteus Maximus)",
        "reference": "정강이뼈 또는 장골능(골반 윗 뼈) 부위",
        "channels": [
            {"ch": 1, "side": "left",  "label": "앞다리 대퇴사두근",  "placement": "앞다리 허벅지 전면 중앙, 엉덩이~무릎 중간"},
            {"ch": 2, "side": "right", "label": "뒷다리 대둔근", "placement": "뒷다리 엉덩이 중앙, 대둔근 근복"},
        ],
        "mvc_protocol": [
            "앉은 자세에서 무릎 60~90° 굴곡 유지 (대퇴사두근)",
            "엎드린 자세에서 무릎 구부리고 엉덩이를 뒤로 미는 힘 발휘 (대둔근)",
            "3~5초 유지 / 1~2분 휴식 후 2~3회 반복",
        ],
        "calib_rest": {
            "title": "① 힘 빼기 — 안정 자세 (3초)",
            "steps": [
                "의자에 편하게 앉아 허벅지와 엉덩이 힘을 완전히 뺍니다",
                "다리는 자연스럽게 바닥에 놓고 움직이지 않습니다",
                "이 상태에서 버튼을 누르고 3초간 유지하세요",
            ],
        },
        "calib_mvc": {
            "title": "② 최대 수축 — MVC 자세 (3초)",
            "steps": [
                "의자에 앉아 무릎을 약 60~90° 구부립니다",
                "파트너가 발목 위를 손으로 고정하거나 의자 다리에 발을 겁니다",
                "최대한 세게 무릎을 펴는 힘을 발휘하며 버튼을 누르고 3초 유지합니다",
            ],
        },
        "feedback_logic": [
            {"type": "activation", "desc": "CH1 < 40% MVC → '앞다리 대퇴 자극 부족 — 무릎 90° 깊이 확인'"},
            {"type": "activation", "desc": "CH2 < 35% MVC → '엉덩이 자극 부족 — 상체 수직 유지하며 더 내려가기'"},
            {"type": "asymmetry",  "desc": "좌우 차이 > 20%p → '좌우 불균형 — 앞다리 교체 시 균형 확인'"},
        ],
    },
    "pullup": {
        "muscle": "광배근 (Latissimus Dorsi) · 이두근 보조",
        "reference": "겨드랑이 아래 옆구리 또는 팔꿈치 내측",
        "channels": [
            {"ch": 1, "side": "left",  "label": "왼쪽 광배근",  "placement": "왼쪽 겨드랑이 아래 옆구리, 등 측면 중앙"},
            {"ch": 2, "side": "right", "label": "오른쪽 광배근", "placement": "오른쪽 겨드랑이 아래 옆구리, 등 측면 중앙"},
        ],
        "mvc_protocol": [
            "철봉에 매달린 자세에서 팔꿈치 약 90° 굴곡",
            "움직이지 않고 최대한 등을 아래로 당기는 힘 발휘",
            "3~5초 유지 / 1~2분 휴식 후 2~3회 반복",
        ],
        "calib_rest": {
            "title": "① 힘 빼기 — 안정 자세 (3초)",
            "steps": [
                "철봉에 매달려 양팔을 완전히 펴고 등 힘을 완전히 뺍니다",
                "어깨가 귀 쪽으로 올라간 상태(데드행)를 유지합니다",
                "이 상태에서 버튼을 누르고 3초간 유지하세요",
            ],
        },
        "calib_mvc": {
            "title": "② 최대 수축 — MVC 자세 (3초)",
            "steps": [
                "철봉에 매달려 팔꿈치를 약 90° 구부립니다",
                "등을 아래로 당기고 어깨를 내리며 최대 수축 상태를 유지합니다",
                "최대한 세게 등을 당기는 힘을 발휘하며 버튼을 누르고 3초 유지합니다",
            ],
        },
        "feedback_logic": [
            {"type": "activation", "desc": "CH1 또는 CH2 < 40% MVC → '광배근 자극 부족 — 팔이 아닌 등으로 당기기'"},
            {"type": "asymmetry",  "desc": "좌우 차이 > 15%p → '좌우 불균형 — 한쪽 등이 더 약함'"},
            {"type": "eccentric",  "desc": "내려올 때 MAV < 올라갈 때 30% 미만 → '내려올 때 너무 빠름 — 천천히 제어하기'"},
        ],
    },
    "legraise": {
        "muscle": "장요근 (Iliopsoas) · 복직근 하부",
        "reference": "ASIS(앞 위 장골극, 골반 앞 뼈 돌출부) 부위",
        "channels": [
            {"ch": 1, "side": "left",  "label": "왼쪽 복직근 하부",  "placement": "배꼽 아래 5~8cm, 정중선에서 2cm 왼쪽"},
            {"ch": 2, "side": "right", "label": "오른쪽 복직근 하부", "placement": "배꼽 아래 5~8cm, 정중선에서 2cm 오른쪽"},
        ],
        "mvc_protocol": [
            "누운 자세에서 다리를 45° 들어 유지",
            "움직이지 않고 최대한 다리를 들어올리는 힘 발휘",
            "3~5초 유지 / 1~2분 휴식 후 2~3회 반복",
        ],
        "calib_rest": {
            "title": "① 힘 빼기 — 안정 자세 (3초)",
            "steps": [
                "매트에 편하게 누워 양다리를 바닥에 자연스럽게 펴고 복부 힘을 완전히 뺍니다",
                "허리가 매트에 닿은 상태를 유지합니다",
                "이 상태에서 버튼을 누르고 3초간 유지하세요",
            ],
        },
        "calib_mvc": {
            "title": "② 최대 수축 — MVC 자세 (3초)",
            "steps": [
                "매트에 누워 양다리를 약 45° 들어 유지합니다",
                "복부에 최대한 힘을 주고 허리를 매트에 누르며 다리를 버팁니다",
                "최대한 세게 복부를 수축하며 버튼을 누르고 3초 유지합니다",
            ],
        },
        "feedback_logic": [
            {"type": "activation", "desc": "CH1 또는 CH2 < 35% MVC → '복부 하부 자극 부족 — 허리를 매트에 눌러 복부로 들기'"},
            {"type": "asymmetry",  "desc": "좌우 차이 > 15%p → '좌우 불균형 — 복부 중심 유지 확인'"},
            {"type": "eccentric",  "desc": "내릴 때 MAV < 올릴 때 30% 미만 → '내릴 때 너무 빠름 — 천천히 제어하기'"},
        ],
    },
    "shoulderpress": {
        "muscle": "삼각근 전부·중부 (Anterior/Middle Deltoid)",
        "reference": "쇄골 부위 또는 어깨뼈 상부",
        "channels": [
            {"ch": 1, "side": "left",  "label": "왼쪽 삼각근",  "placement": "왼쪽 어깨 상부, 삼각근 전부~중부 경계 (위팔 전면 상단)"},
            {"ch": 2, "side": "right", "label": "오른쪽 삼각근", "placement": "오른쪽 어깨 상부, 삼각근 전부~중부 경계 (위팔 전면 상단)"},
        ],
        "mvc_protocol": [
            "앉거나 선 자세, 팔꿈치 90° 구부려 어깨 높이 유지",
            "움직이지 않는 저항에 대해 최대한 팔을 위로 미는 힘 발휘",
            "3~5초 유지 / 1~2분 휴식 후 2~3회 반복",
        ],
        "calib_rest": {
            "title": "① 힘 빼기 — 안정 자세 (3초)",
            "steps": [
                "의자에 앉아 양팔을 허벅지 위에 자연스럽게 올려놓습니다",
                "어깨와 삼각근 힘을 완전히 빼고 팔을 내립니다",
                "이 상태에서 버튼을 누르고 3초간 유지하세요",
            ],
        },
        "calib_mvc": {
            "title": "② 최대 수축 — MVC 자세 (3초)",
            "steps": [
                "의자에 앉아 팔꿈치를 90°로 구부려 어깨 높이에 맞춥니다",
                "파트너가 손목 위에서 아래로 눌러 저항을 줍니다",
                "최대한 세게 팔을 위로 밀어올리는 힘을 발휘하며 버튼을 누르고 3초 유지합니다",
            ],
        },
        "feedback_logic": [
            {"type": "activation", "desc": "CH1 또는 CH2 < 40% MVC → '삼각근 자극 부족 — 팔꿈치를 귀 높이까지 밀어올리기'"},
            {"type": "asymmetry",  "desc": "좌우 차이 > 15%p → '좌우 불균형 — 양팔 높이와 무게 균형 확인'"},
            {"type": "eccentric",  "desc": "내려올 때 MAV < 올라갈 때 30% 미만 → '내려올 때 너무 빠름 — 천천히 제어하기'"},
        ],
    },
}

HISTORY_HTML = """
<!DOCTYPE html><html lang="ko"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>운동 기록 — Motion Fit</title>
<style>
:root{--bg:#f8fafc;--panel:#fff;--line:#e2e8f0;--text:#0f172a;--muted:#64748b;--soft:#f1f5f9;--accent:#3b82f6;--good:#16a34a;--warn:#d97706;--bad:#dc2626;--shadow:0 4px 24px rgba(0,0,0,.08);}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:Inter,"Segoe UI","Apple SD Gothic Neo",sans-serif;min-height:100vh;}
.shell{max-width:960px;margin:0 auto;padding:28px 20px;}
.topbar{display:flex;align-items:center;justify-content:space-between;margin-bottom:24px;gap:12px;flex-wrap:wrap;}
h1{margin:0;font-size:26px;font-weight:900;letter-spacing:-.03em;}
a.back{display:inline-flex;align-items:center;gap:6px;padding:8px 16px;border-radius:999px;border:1px solid var(--line);background:var(--panel);text-decoration:none;color:var(--muted);font-size:13px;font-weight:700;transition:.15s;}
a.back:hover{color:var(--text);border-color:var(--text);}
.empty{text-align:center;padding:60px 20px;color:var(--muted);font-size:15px;}
/* 세션 카드 */
.session-card{background:var(--panel);border:1px solid var(--line);border-radius:20px;margin-bottom:16px;overflow:hidden;box-shadow:var(--shadow);}
.session-head{display:flex;align-items:center;gap:14px;padding:16px 20px;cursor:pointer;user-select:none;}
.session-head:hover{background:var(--soft);}
.grade-badge{width:48px;height:48px;border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:900;flex-shrink:0;}
.grade-s{background:rgba(124,58,237,.1);color:#7c3aed;}
.grade-a{background:rgba(22,163,74,.1);color:var(--good);}
.grade-b{background:rgba(217,119,6,.1);color:var(--warn);}
.grade-c{background:rgba(220,38,38,.1);color:var(--bad);}
.session-info{flex:1;min-width:0;}
.session-title{font-size:16px;font-weight:800;margin-bottom:3px;}
.session-meta{font-size:12px;color:var(--muted);}
.session-stats{display:flex;gap:16px;flex-shrink:0;}
.stat{text-align:center;}
.stat-v{font-size:18px;font-weight:900;}
.stat-k{font-size:10px;color:var(--muted);font-weight:700;letter-spacing:.04em;}
.chevron{color:var(--muted);font-size:18px;transition:.2s;flex-shrink:0;}
.chevron.open{transform:rotate(90deg);}
/* 펼쳐지는 상세 */
.session-detail{display:none;border-top:1px solid var(--line);padding:16px 20px;}
.session-detail.open{display:block;}
.detail-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:16px;}
.dg-item{background:var(--soft);border-radius:12px;padding:10px 12px;}
.dg-k{font-size:10px;color:var(--muted);font-weight:700;letter-spacing:.04em;margin-bottom:3px;}
.dg-v{font-size:17px;font-weight:900;}
/* 세트 테이블 */
.set-table{width:100%;border-collapse:collapse;font-size:12px;margin-bottom:14px;}
.set-table th{color:var(--muted);font-weight:700;padding:5px 8px;text-align:left;border-bottom:2px solid var(--line);}
.set-table td{padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top;}
.set-table tr:last-child td{border-bottom:none;}
/* 피드백 태그 */
.fb-tags{display:flex;flex-wrap:wrap;gap:4px;}
.fb-tag{padding:2px 8px;border-radius:999px;font-size:10px;font-weight:700;}
.fb-tag.bad{background:rgba(220,38,38,.08);color:var(--bad);border:1px solid rgba(220,38,38,.2);}
.fb-tag.ok{background:rgba(217,119,6,.08);color:var(--warn);border:1px solid rgba(217,119,6,.18);}
.score-bar-wrap{height:5px;background:var(--line);border-radius:3px;margin-top:4px;overflow:hidden;}
.score-bar-fill{height:100%;border-radius:3px;background:var(--good);}
@media(max-width:600px){.detail-grid{grid-template-columns:repeat(2,1fr)}.session-stats{display:none}}
</style></head><body>
<div class="shell">
  <div class="topbar">
    <h1>운동 기록</h1>
    <a class="back" href="/">← 운동 선택</a>
  </div>
  {% if not sessions %}
  <div class="empty">아직 저장된 운동 기록이 없습니다.<br>운동 후 기록 저장을 눌러주세요.</div>
  {% else %}
  {% for s in sessions %}
  <div class="session-card">
    <div class="session-head" onclick="toggle('s{{loop.index}}')">
      <div class="grade-badge grade-{{s.grade|lower}}">{{s.grade}}</div>
      <div class="session-info">
        <div class="session-title">{{s.exercise_kor}} · {{s.saved_at[:10]}} {{s.saved_at[11:16]}}</div>
        <div class="session-meta">{{s.total_sets}}세트 · {{s.total_reps}}회 수행 · 좋은 동작 {{s.total_good_reps}}회</div>
      </div>
      <div class="session-stats">
        <div class="stat"><div class="stat-v" style="color:{{s.grade_color}}">{{s.avg_score}}점</div><div class="stat-k">종합점수</div></div>
        <div class="stat"><div class="stat-v">{{s.total_reps}}</div><div class="stat-k">총횟수</div></div>
      </div>
      <div class="chevron" id="chev_s{{loop.index}}">›</div>
    </div>
    <div class="session-detail" id="s{{loop.index}}">
      <div class="detail-grid">
        <div class="dg-item"><div class="dg-k">종합점수</div><div class="dg-v" style="color:{{s.grade_color}}">{{s.avg_score}}점</div></div>
        <div class="dg-item"><div class="dg-k">등급</div><div class="dg-v" style="color:{{s.grade_color}}">{{s.grade}}</div></div>
        <div class="dg-item"><div class="dg-k">달성률</div><div class="dg-v">{{s.achieve_pct}}%</div></div>
        <div class="dg-item"><div class="dg-k">운동 시간</div><div class="dg-v">{{s.duration_str}}</div></div>
      </div>
      <table class="set-table">
        <tr><th>세트</th><th>횟수</th><th>점수</th><th>등급</th><th>시간</th><th>주요 피드백</th></tr>
        {% for r in s.sets %}
        <tr>
          <td>{{r.set_no}}세트</td>
          <td>{{r.total_reps}}/{{r.target_reps}}</td>
          <td>
            {{r.avg_score}}점
            <div class="score-bar-wrap"><div class="score-bar-fill" style="width:{{r.avg_score}}%;background:{{r.bar_color}};"></div></div>
          </td>
          <td class="grade-{{r.grade|lower}}" style="font-weight:800;">{{r.grade}}</td>
          <td>{{r.set_duration_sec}}초</td>
          <td>
            <div class="fb-tags">
            {% for issue, cnt in r.top_issues %}
              <span class="fb-tag bad">{{issue}} ×{{cnt}}</span>
            {% endfor %}
            {% if not r.top_issues %}<span style="color:var(--good);font-size:11px;font-weight:700;">피드백 없음 (완벽)</span>{% endif %}
            </div>
          </td>
        </tr>
        {% endfor %}
      </table>
    </div>
  </div>
  {% endfor %}
  {% endif %}
</div>
<script>
function toggle(id){
  const el=document.getElementById(id);
  const chev=document.getElementById('chev_'+id);
  const open=el.classList.toggle('open');
  chev.classList.toggle('open',open);
}
</script>
</body></html>
"""

INDEX_HTML = """
<!DOCTYPE html><html lang="ko"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Motion Fit</title>
<style>
:root{--bg:#f8fafc;--panel:#fff;--line:#e2e8f0;--text:#0f172a;--muted:#64748b;--soft:#f1f5f9;--accent:#3b82f6;--shadow:0 4px 24px rgba(0,0,0,.08);}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:Inter,"Segoe UI","Apple SD Gothic Neo",sans-serif;min-height:100vh;}
.shell{max-width:1220px;margin:0 auto;padding:32px 24px;}
.hero{background:var(--panel);border:1px solid var(--line);border-radius:24px;padding:36px;box-shadow:var(--shadow);}
.brand{display:inline-flex;align-items:center;gap:8px;padding:8px 16px;border:1px solid var(--line);border-radius:999px;background:rgba(59,130,246,.08);font-weight:800;margin-bottom:24px;color:var(--accent);font-size:13px;letter-spacing:.04em;}
.brand:before{content:"";width:7px;height:7px;border-radius:50%;background:var(--accent);}
h1{margin:0 0 6px;font-size:36px;letter-spacing:-.03em;font-weight:900}
.sub{margin:0 0 28px;color:var(--muted);font-size:15px}
.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.card{width:100%;text-align:left;border:1px solid var(--line);border-radius:20px;background:var(--soft);padding:20px;cursor:pointer;transition:.18s ease;}
.card:hover{transform:translateY(-2px);box-shadow:0 8px 28px rgba(59,130,246,.13);border-color:var(--accent);}
.card:hover .title{color:var(--accent)}
.row{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}
.tag,.goal{border-radius:999px;padding:5px 11px;font-size:11px;font-weight:800;letter-spacing:.04em}
.tag{background:var(--accent);color:#fff}.goal{background:var(--line);color:var(--muted)}
.title{font-size:24px;font-weight:800;letter-spacing:-.02em;margin-bottom:4px;transition:.18s}
.caption{color:var(--muted);font-size:13px}
@media(max-width:960px){.grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:640px){.shell{padding:16px}.grid{grid-template-columns:1fr}h1{font-size:26px}}
</style></head><body>
<div class="shell"><section class="hero">
<div class="brand">MOTION FIT v4</div>
<h1>운동 선택</h1>
<p class="sub">AI 자세 분석 · 실시간 음성 피드백 · 개수 카운팅 · 세션 점수</p>
<form method="post" class="grid">{{ cards|safe }}</form>
<div style="margin-top:20px;text-align:right"><a href="/history" style="display:inline-flex;align-items:center;gap:6px;padding:10px 20px;border-radius:999px;border:1px solid var(--line);background:var(--panel);text-decoration:none;color:var(--muted);font-size:13px;font-weight:700;transition:.15s;" onmouseover="this.style.color='var(--text)';this.style.borderColor='var(--text)'" onmouseout="this.style.color='var(--muted)';this.style.borderColor='var(--line)'">📋 운동 기록 보기</a></div>
</section></div></body></html>
"""

CAMERA_HTML = r"""
<!DOCTYPE html><html lang="ko"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{{ exercise_kor }} — Motion Fit</title>
<style>
:root{
  --bg:#f8fafc;--panel:#fff;--line:#e2e8f0;--text:#0f172a;--muted:#64748b;--soft:#f1f5f9;
  --shadow:0 4px 24px rgba(0,0,0,.08);--accent:#3b82f6;--good:#16a34a;--warn:#d97706;--bad:#dc2626;
}
*{box-sizing:border-box}
html,body{margin:0;height:100%;overflow:hidden;background:var(--bg);color:var(--text);font-family:Inter,"Segoe UI","Apple SD Gothic Neo",sans-serif;}
.shell{height:100vh;display:flex;flex-direction:column;padding:10px 16px;gap:8px;}
.topbar{display:flex;justify-content:space-between;align-items:center;gap:8px;flex-shrink:0;}
.left{display:flex;gap:6px;flex-wrap:wrap}
.pill{display:inline-flex;align-items:center;gap:6px;padding:6px 12px;border-radius:999px;border:1px solid var(--line);background:var(--panel);font-size:12px;font-weight:700;color:var(--text);}
.pill.accent{background:rgba(59,130,246,.1);border-color:var(--accent);color:var(--accent);}
a.back{display:inline-flex;align-items:center;gap:6px;padding:6px 14px;border-radius:999px;border:1px solid var(--line);background:var(--panel);text-decoration:none;color:var(--muted);font-size:12px;font-weight:700;transition:.15s;}
a.back:hover{color:var(--text);border-color:var(--text);}
.layout{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(0,1fr);gap:10px;flex:1;min-height:0;}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:16px;box-shadow:var(--shadow)}
.viewer{padding:10px;display:flex;flex-direction:column;min-height:0;}
.camera-box{position:relative;flex:1;min-height:0;overflow:hidden;border-radius:12px;background:#0f172a;border:1px solid var(--line);}
video,canvas{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;transform:scaleX(-1);background:transparent;}
.cam-placeholder{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;z-index:1;pointer-events:none;}
.score-guide-popup{position:absolute;top:60px;left:50%;transform:translateX(-50%);z-index:10;background:rgba(255,255,255,.97);border-radius:14px;padding:14px 18px;box-shadow:0 8px 32px rgba(0,0,0,.18);border:1px solid var(--line);min-width:200px;display:none;}
.score-guide-popup.show{display:block;}
.sg-title{font-size:11px;font-weight:800;color:var(--muted);letter-spacing:.06em;margin-bottom:8px;}
.sg-row{display:flex;align-items:center;gap:8px;margin-bottom:5px;font-size:14px;font-weight:700;}
.sg-grade{width:24px;height:24px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:900;flex-shrink:0;}
.sg-desc{color:var(--muted);font-size:12px;font-weight:500;}
.cam-placeholder .play-tri{width:0;height:0;border-top:22px solid transparent;border-bottom:22px solid transparent;border-left:36px solid rgba(255,255,255,0.5);}
.cam-placeholder .play-label{color:rgba(255,255,255,0.45);font-size:12px;font-weight:700;letter-spacing:.05em;}
canvas{pointer-events:none}
/* 누끼 미니 프리뷰 */
.demo-overlay{position:absolute;bottom:52px;right:10px;width:175px;height:240px;border-radius:12px;z-index:5;pointer-events:none;object-fit:cover;box-shadow:0 4px 16px rgba(0,0,0,0.5);border:2px solid rgba(255,255,255,0.2);}
.demo-overlay-wide{width:300px;height:175px;}
/* 상단 오버레이 */
.overlay{position:absolute;left:10px;right:10px;top:10px;display:flex;justify-content:space-between;gap:8px;z-index:2}
.overlay-box{min-width:82px;background:rgba(255,255,255,.93);border-radius:12px;padding:7px 11px;backdrop-filter:blur(8px);border:1px solid rgba(0,0,0,.07);box-shadow:0 2px 8px rgba(0,0,0,.09);}
.overlay-k{font-size:10px;color:var(--muted);margin-bottom:2px;letter-spacing:.06em;font-weight:700}
.overlay-v{font-size:22px;font-weight:900;letter-spacing:-.02em;color:var(--text)}
.overlay-v.good{color:var(--good)}.overlay-v.warn{color:var(--warn)}.overlay-v.bad{color:var(--bad)}
/* 카메라 하단 피드백 배너 */
.fb-banner{position:absolute;bottom:0;left:0;right:0;z-index:3;display:flex;align-items:center;gap:10px;padding:10px 14px;background:rgba(255,255,255,.94);border-top:3px solid #e2e8f0;backdrop-filter:blur(8px);transition:border-color .2s;}
.fb-banner.good{border-top-color:var(--good);}
.fb-banner.warn{border-top-color:var(--warn);}
.fb-banner.bad{border-top-color:var(--bad);}
.fb-dot{width:9px;height:9px;border-radius:50%;flex-shrink:0;background:var(--muted);}
.fb-dot.good{background:var(--good)}.fb-dot.warn{background:var(--warn)}.fb-dot.bad{background:var(--bad)}
.fb-msg{font-size:16px;font-weight:700;color:var(--text);flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.fb-sub-txt{font-size:13px;color:var(--muted);white-space:nowrap;}
/* rep 완료 팝업 */
.rep-toast{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%) scale(.85);z-index:4;background:rgba(255,255,255,.97);border-radius:18px;padding:14px 26px;text-align:center;border:2px solid var(--good);opacity:0;pointer-events:none;transition:opacity .15s,transform .15s;box-shadow:0 8px 32px rgba(0,0,0,.15);}
.rep-toast.show{opacity:1;transform:translate(-50%,-50%) scale(1);}
.rt-num{font-size:48px;font-weight:900;color:var(--good);line-height:1;}
.rt-grade{font-size:13px;font-weight:800;margin-top:2px;}
.rt-label{font-size:12px;color:var(--muted);margin-top:1px;}
/* 툴바 */
.toolbar{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px;margin-top:8px;flex-shrink:0;}
button{border:none;border-radius:10px;padding:9px 8px;font-size:12px;font-weight:700;cursor:pointer;transition:.15s;}
button:active{transform:scale(.97)}
.btn-primary{background:var(--accent);color:#fff}.btn-primary:hover{background:#2563eb}
.btn-accent{background:rgba(59,130,246,.1);color:var(--accent);border:1px solid var(--accent)}.btn-accent:hover{background:rgba(59,130,246,.18)}
.btn-light{background:var(--soft);color:var(--text);border:1px solid var(--line)}.btn-light:hover{border-color:var(--muted)}
.btn-danger{background:rgba(220,38,38,.08);color:var(--bad);border:1px solid var(--bad)}.btn-danger:hover{background:rgba(220,38,38,.15)}
.btn-camera-stop{background:var(--bad);color:#fff;border:1px solid var(--bad)}.btn-camera-stop:hover{background:#b91c1c}
.btn-good{background:rgba(22,163,74,.08);color:var(--good);border:1px solid var(--good)}.btn-good:hover{background:rgba(22,163,74,.16)}
/* 사이드 */
.card{border:1px solid var(--line);border-radius:12px;background:var(--soft);padding:10px}
.side{display:flex;flex-direction:column;gap:8px;padding:10px;height:100%;overflow-y:auto;overflow-x:hidden;}
.side::-webkit-scrollbar{width:3px}.side::-webkit-scrollbar-thumb{background:var(--line);border-radius:2px}
.status-chip{display:inline-flex;padding:5px 11px;border-radius:999px;background:var(--line);font-size:11px;font-weight:800;margin-bottom:8px;letter-spacing:.04em;color:var(--muted)}
.status-chip.live{background:rgba(22,163,74,.12);color:var(--good);border:1px solid var(--good)}
.status-chip.warn{background:rgba(217,119,6,.1);color:var(--warn);border:1px solid var(--warn)}
.status-chip.rest{background:rgba(59,130,246,.1);color:var(--accent);border:1px solid var(--accent)}
.feedback-main{font-size:17px;font-weight:800;line-height:1.3;margin-bottom:4px;letter-spacing:-.02em}
.feedback-sub{color:var(--muted);line-height:1.5;font-size:14px;min-height:0}
/* 이슈 리스트 */
.issue-list{display:flex;flex-direction:column;gap:4px;margin-top:6px}
.issue-item{display:flex;align-items:center;gap:7px;padding:7px 10px;border-radius:9px;font-size:14px;font-weight:700;}
.issue-item.bad{background:rgba(220,38,38,.07);color:var(--bad);border:1px solid rgba(220,38,38,.2);}
.issue-item.warn{background:rgba(217,119,6,.07);color:var(--warn);border:1px solid rgba(217,119,6,.18);}
.issue-item.good{background:rgba(22,163,74,.07);color:var(--good);border:1px solid rgba(22,163,74,.2);}
.issue-dot{width:6px;height:6px;border-radius:50%;flex-shrink:0;}
.issue-dot.bad{background:var(--bad)}.issue-dot.warn{background:var(--warn)}.issue-dot.good{background:var(--good)}
/* EMG 이슈 아이템 — 모션 피드백과 같은 리스트에, 구근(筋) 배지로 구분 */
.issue-item.emg-warn{background:rgba(124,58,237,.07);color:#7c3aed;border:1px solid rgba(124,58,237,.25);}
.issue-item.emg-bad{background:rgba(190,18,60,.07);color:#be123c;border:1px solid rgba(190,18,60,.2);}
.issue-item.emg-good{background:rgba(22,163,74,.07);color:var(--good);border:1px solid rgba(22,163,74,.2);}
.issue-dot.emg-warn{background:#7c3aed}.issue-dot.emg-bad{background:#be123c}.issue-dot.emg-good{background:var(--good)}
.emg-tag{font-size:9px;font-weight:800;letter-spacing:.04em;padding:1px 5px;border-radius:4px;background:rgba(124,58,237,.15);color:#7c3aed;flex-shrink:0;}
.metric-grid{display:grid;grid-template-columns:1fr 1fr;gap:5px}
.metric{border:1px solid var(--line);border-radius:10px;background:var(--bg);padding:8px}
.metric-k{color:var(--muted);font-size:10px;margin-bottom:2px;letter-spacing:.04em;font-weight:700}
.metric-v{font-size:16px;font-weight:900;color:var(--text)}
.config-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px}
.field{display:grid;gap:3px}.field label{font-size:10px;font-weight:700;color:var(--muted);letter-spacing:.04em}
.field input{border:1px solid var(--line);border-radius:8px;padding:7px 9px;font-size:13px;font-weight:700;background:var(--bg);color:var(--text);outline:none;}
.field input:focus{border-color:var(--accent)}
/* 세트 요약 카드 */
.set-summary{display:none;border-radius:12px;padding:12px;margin-top:8px}
.set-summary.show{display:block}
.ss-title{font-size:12px;font-weight:800;margin-bottom:8px;letter-spacing:.04em}
.ss-row{display:flex;align-items:center;justify-content:space-between;padding:4px 0;border-bottom:1px solid var(--line);font-size:12px;}
.ss-row:last-child{border-bottom:none}
.ss-grade{font-size:18px;font-weight:900}
/* 총 세션 점수 패널 */
.session-score-panel{display:none;border:2px solid var(--accent);border-radius:16px;background:rgba(59,130,246,.04);padding:14px;margin-top:10px;text-align:center}
.session-score-panel.show{display:block}
.ssp-title{font-size:11px;font-weight:800;letter-spacing:.06em;color:var(--accent);margin-bottom:6px}
.ssp-grade{font-size:52px;font-weight:900;line-height:1}
.ssp-score{font-size:14px;font-weight:700;color:var(--muted);margin-top:2px}
.ssp-sub{font-size:12px;color:var(--muted);margin-top:6px;line-height:1.5}
/* 세트 히스토리 테이블 */
.set-history{width:100%;border-collapse:collapse;font-size:11px;margin-top:8px}
.set-history th{color:var(--muted);font-weight:700;padding:4px 6px;text-align:left;border-bottom:1px solid var(--line)}
.set-history td{padding:4px 6px;border-bottom:1px solid var(--line)}
.set-history tr:last-child td{border-bottom:none}
.grade-s{color:#7c3aed;font-weight:900}.grade-a{color:var(--good);font-weight:900}.grade-b{color:var(--warn);font-weight:900}.grade-c{color:var(--bad);font-weight:900}
.summary{display:none;border:1px solid rgba(59,130,246,.25);background:rgba(59,130,246,.05);border-radius:12px;padding:12px;margin-top:8px}
.summary.show{display:block}
.summary-title{font-size:12px;font-weight:800;margin-bottom:6px;color:var(--accent)}
.summary-text{color:var(--muted);line-height:1.6;font-size:12px}
.save-row{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.save-status{font-size:11px;color:var(--muted);margin-top:4px}
.score-bar{height:5px;border-radius:999px;background:var(--line);margin-top:7px;overflow:hidden}
.score-fill{height:100%;border-radius:999px;transition:width .4s ease}
.guide{display:grid;gap:6px;color:var(--muted);font-size:12px;line-height:1.5}
.guide-item{display:flex;gap:7px;align-items:flex-start}
.guide-dot{width:5px;height:5px;border-radius:50%;background:var(--accent);flex-shrink:0;margin-top:4px}
.voice-row{display:flex;align-items:center;gap:10px;margin-top:8px}
.toggle{position:relative;width:40px;height:22px;cursor:pointer}
.toggle input{opacity:0;width:0;height:0}
.slider{position:absolute;inset:0;background:var(--line);border-radius:999px;transition:.2s}
.slider:before{content:"";position:absolute;left:3px;top:3px;width:16px;height:16px;border-radius:50%;background:#fff;transition:.2s}
input:checked+.slider{background:var(--accent)}
input:checked+.slider:before{transform:translateX(18px)}
.toggle-label{font-size:13px;font-weight:700;color:var(--muted)}
.debug-panel{display:none;border:1px dashed var(--accent);border-radius:12px;padding:10px;margin-top:10px;background:rgba(59,130,246,.05)}
.debug-panel.show{display:block}
.debug-grid{display:grid;grid-template-columns:1fr 1fr;gap:7px}
.debug-item{border:1px solid var(--line);border-radius:10px;padding:8px;background:var(--panel)}
.debug-k{font-size:10px;color:var(--muted);font-weight:700;letter-spacing:.04em}
.debug-v{font-size:13px;font-weight:800;margin-top:3px;word-break:break-word}
h3{margin:0 0 6px;font-size:13px;font-weight:800;color:var(--text)}
.save-row{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}
.save-status{font-size:10px;color:var(--muted);margin-top:3px}
.voice-row{display:flex;align-items:center;gap:8px;margin-top:6px}
@media(max-width:1100px){.layout{grid-template-columns:1fr;overflow-y:auto}html,body{overflow:auto}}
@media(max-width:760px){.toolbar{grid-template-columns:1fr 1fr}}
@media(max-width:560px){.toolbar,.metric-grid,.config-grid,.debug-grid{grid-template-columns:1fr}}

/* ── 토스트 알림 ── */
#toastContainer{position:fixed;top:18px;left:50%;transform:translateX(-50%);z-index:9999;display:flex;flex-direction:column;align-items:center;gap:8px;pointer-events:none;}
.toast{min-width:260px;max-width:420px;padding:12px 18px;border-radius:14px;font-size:13px;font-weight:700;color:#fff;box-shadow:0 6px 28px rgba(0,0,0,.22);display:flex;align-items:flex-start;gap:10px;pointer-events:auto;animation:toastIn .3s cubic-bezier(.34,1.56,.64,1);}
.toast-icon{font-size:18px;line-height:1;flex-shrink:0;}
.toast-body{display:flex;flex-direction:column;gap:2px;}
.toast-title{font-size:13px;font-weight:800;}
.toast-msg{font-size:11px;font-weight:500;opacity:.88;}
.toast.info   {background:linear-gradient(135deg,#3b82f6,#1d4ed8);}
.toast.success{background:linear-gradient(135deg,#22c55e,#15803d);}
.toast.warn   {background:linear-gradient(135deg,#f97316,#c2410c);}
.toast.danger {background:linear-gradient(135deg,#ef4444,#b91c1c);}
.toast.calib  {background:linear-gradient(135deg,#8b5cf6,#6d28d9);}
@keyframes toastIn{from{opacity:0;transform:translateY(-16px) scale(.95)}to{opacity:1;transform:none}}
@keyframes toastOut{to{opacity:0;transform:translateY(-10px) scale(.95)}}

/* ── EMG 세션 리포트 모달 ── */
#emgReportOverlay{position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:10000;display:none;align-items:center;justify-content:center;padding:16px;}
#emgReportOverlay.show{display:flex;}
#emgReportBox{background:#fff;border-radius:18px;width:100%;max-width:680px;max-height:90vh;display:flex;flex-direction:column;box-shadow:0 20px 60px rgba(0,0,0,.3);overflow:hidden;}
#emgReportHeader{padding:18px 22px 14px;background:linear-gradient(135deg,#1e293b,#0f172a);color:#fff;display:flex;align-items:center;justify-content:space-between;flex-shrink:0;}
#emgReportHeader h2{margin:0;font-size:16px;font-weight:800;letter-spacing:-.02em;}
#emgReportHeader .sub{font-size:11px;opacity:.65;margin-top:2px;}
#emgReportClose{background:rgba(255,255,255,.15);border:none;color:#fff;border-radius:8px;padding:5px 12px;font-size:12px;font-weight:700;cursor:pointer;}
#emgReportClose:hover{background:rgba(255,255,255,.25);}
#emgReportBody{padding:18px 22px;overflow-y:auto;flex:1;}
.emg-report-summary{display:flex;gap:10px;margin-bottom:14px;flex-wrap:wrap;}
.emg-report-stat{flex:1;min-width:110px;background:#f8fafc;border-radius:10px;padding:10px 14px;border:1px solid #e2e8f0;}
.emg-report-stat .label{font-size:10px;color:#64748b;font-weight:700;text-transform:uppercase;letter-spacing:.05em;}
.emg-report-stat .val{font-size:22px;font-weight:900;color:#0f172a;margin-top:2px;}
.emg-report-stat .val.good{color:#16a34a;}.emg-report-stat .val.warn{color:#ea580c;}.emg-report-stat .val.danger{color:#dc2626;}
.emg-report-table{width:100%;border-collapse:collapse;font-size:12px;}
.emg-report-table th{background:#f1f5f9;color:#475569;font-weight:700;padding:8px 10px;text-align:left;border-bottom:2px solid #e2e8f0;white-space:nowrap;}
.emg-report-table td{padding:7px 10px;border-bottom:1px solid #f1f5f9;vertical-align:middle;}
.emg-report-table tr:last-child td{border-bottom:none;}
.emg-report-table tr:hover td{background:#f8fafc;}
.emg-badge{display:inline-block;padding:2px 8px;border-radius:20px;font-size:10px;font-weight:800;letter-spacing:.03em;}
.emg-badge.부족{background:#fff7ed;color:#c2410c;border:1px solid #fed7aa;}
.emg-badge.정상{background:#f0fdf4;color:#15803d;border:1px solid #bbf7d0;}
.emg-badge.과부하{background:#fff1f2;color:#be123c;border:1px solid #fecdd3;}
.emg-badge.불균형{background:#faf5ff;color:#7e22ce;border:1px solid #e9d5ff;}
#emgReportFooter{padding:12px 22px;background:#f8fafc;border-top:1px solid #e2e8f0;display:flex;gap:8px;justify-content:flex-end;flex-shrink:0;}
#emgReportFooter button{padding:8px 18px;border-radius:8px;border:none;font-size:12px;font-weight:700;cursor:pointer;}
.btn-report-copy{background:#3b82f6;color:#fff;}.btn-report-copy:hover{background:#2563eb;}
.btn-report-close{background:#e2e8f0;color:#374151;}.btn-report-close:hover{background:#cbd5e1;}
</style></head><body>
<div id="toastContainer"></div>

<!-- EMG 세션 피드백 리포트 모달 -->
<div id="emgReportOverlay">
  <div id="emgReportBox">
    <div id="emgReportHeader">
      <div>
        <h2>세션 피드백 리포트</h2>
        <div class="sub" id="emgReportMeta"></div>
      </div>
      <button id="emgReportClose" onclick="document.getElementById('emgReportOverlay').classList.remove('show')">닫기</button>
    </div>
    <div id="emgReportBody">
      <div class="emg-report-summary" id="emgReportSummary"></div>
      <div id="emgReportTableWrap"></div>
    </div>
    <div id="emgReportFooter">
      <button class="btn-report-copy" onclick="copyEmgReport()">텍스트 복사</button>
      <button class="btn-report-close" onclick="document.getElementById('emgReportOverlay').classList.remove('show')">닫고 계속하기</button>
    </div>
  </div>
</div>
<div class="shell">
<div class="topbar">
  <div class="left">
    <div class="pill accent">MOTION FIT v4.1</div>
    <div class="pill" style="font-weight:900;font-size:14px;">{{ exercise_kor }}</div>
    <div class="pill">{{ meta.tag }}</div>
    <div class="pill" style="color:var(--muted);font-weight:600;">📷 {{ meta.camera }}</div>
  </div>
  <div style="display:flex;gap:6px;align-items:center;">
    <button onclick="utGuideConnect()" style="padding:6px 12px;border-radius:999px;border:1px solid #93c5fd;background:#eff6ff;color:#1d4ed8;font-size:11px;font-weight:800;cursor:pointer;" title="유저 테스트 순서 안내 시작">🎯 테스트 시작</button>
    <button onclick="utGuideExercise()" style="padding:6px 12px;border-radius:999px;border:1px solid #86efac;background:#f0fdf4;color:#15803d;font-size:11px;font-weight:800;cursor:pointer;" title="캘리브레이션 완료 후 운동 시작">▶ 운동 시작</button>
    <a href="/" class="back">← 운동 변경</a>
  </div>
</div>

<div class="layout">
<section class="panel viewer">
  <div class="camera-box">
    <video id="video" autoplay playsinline muted style="display:none"></video>
    <canvas id="canvas"></canvas>
    <div class="cam-placeholder" id="camPlaceholder">
      <div class="play-tri"></div>
      <div class="play-label">카메라 시작</div>
    </div>
    <div class="overlay">
      <div class="overlay-box"><div class="overlay-k">COUNT</div><div class="overlay-v" id="countText">0</div></div>
      <div class="overlay-box"><div class="overlay-k">GOOD REP</div><div class="overlay-v good" id="goodText">0</div></div>
      <div class="overlay-box" onclick="toggleScoreGuide()" style="cursor:pointer;position:relative;" title="점수 기준 보기"><div class="overlay-k">SCORE ⓘ</div><div class="overlay-v" id="overlayScore">-</div></div>
      <div class="overlay-box"><div class="overlay-k">SET</div><div class="overlay-v" id="setOverlay">-</div></div>
      <div class="overlay-box"><div class="overlay-k">STATE</div><div class="overlay-v" id="stateText">READY</div></div>
    </div>
    <div class="score-guide-popup" id="scoreGuidePopup">
      <div class="sg-title">점수 기준</div>
      <div class="sg-row"><div class="sg-grade" style="background:#f3e8ff;color:#7c3aed;">S</div><span>90점 이상</span><span class="sg-desc">완벽한 자세</span></div>
      <div class="sg-row"><div class="sg-grade" style="background:#dcfce7;color:#16a34a;">A</div><span>80–89점</span><span class="sg-desc">좋은 자세</span></div>
      <div class="sg-row"><div class="sg-grade" style="background:#fef9c3;color:#b45309;">B</div><span>65–79점</span><span class="sg-desc">보통 (개선 필요)</span></div>
      <div class="sg-row"><div class="sg-grade" style="background:#fee2e2;color:#dc2626;">C</div><span>64점 이하</span><span class="sg-desc">자세 교정 필요</span></div>
    </div>
    <div class="fb-banner" id="fbBanner">
      <div class="fb-dot" id="fbDot"></div>
      <div class="fb-msg" id="fbMsg">카메라를 시작하세요</div>
      <div class="fb-sub-txt" id="fbSubTxt"></div>
    </div>
    <div class="rep-toast" id="repToast">
      <div class="rt-num" id="rtNum">0</div>
      <div class="rt-grade" id="rtGrade"></div>
      <div class="rt-label">회 완료!</div>
    </div>
    {% if demo_img %}
    <img class="demo-overlay{% if exercise_key == 'pushup' %} demo-overlay-wide{% endif %}" src="/static/{{ demo_img }}" alt="예시">
    {% endif %}
  </div>
  <div class="toolbar">
    <button class="btn-primary" id="cameraToggleBtn" onclick="toggleCamera()">카메라 시작</button>
    <button class="btn-accent" id="startSetBtn" onclick="startSet()">세트 시작</button>
    <button class="btn-light" id="pauseSetBtn" onclick="pauseSet()">세트 일시정지</button>
    <button class="btn-good" id="finishSetBtn" onclick="finishCurrentSet()">세트 저장 후 종료</button>
    <button class="btn-danger" onclick="endSession()">세션 종료</button>
  </div>
</section>

<aside class="panel side">
	  <div class="card">
	    <div class="status-chip" id="statusChip">대기 중</div>
	    <div class="feedback-main" id="feedbackMain">카메라를 시작한 뒤 세트를 시작하세요.</div>
	    <div class="feedback-sub" id="feedbackSub">세트 중 실시간 큐, 종료 후 요약을 제공합니다.</div>
	    <div class="issue-list" id="issueListWrap"></div>
    <div id="scoreBarWrap" style="display:none;margin-top:8px">
      <div class="score-bar"><div class="score-fill" id="scoreFill" style="width:0%"></div></div>
    </div>
    <div class="voice-row">
      <label class="toggle"><input type="checkbox" id="voiceToggle" checked onchange="toggleVoice(this.checked)"><span class="slider"></span></label>
      <span class="toggle-label">음성 피드백</span>
    </div>
    <div class="voice-row">
      <label class="toggle"><input type="checkbox" id="musicToggle" onchange="toggleBgMusic(this.checked)"><span class="slider"></span></label>
      <span class="toggle-label">배경음악</span>
    </div>
	    <div class="voice-row">
	      <label class="toggle"><input type="checkbox" id="debugToggle" onchange="toggleDebug(this.checked)"><span class="slider"></span></label>
	      <span class="toggle-label">테스트 모드</span>
	    </div>
		    <div class="config-grid">
		      <div class="field"><label>목표 횟수</label><input id="targetInput" type="number" min="1" max="50" value="{{ meta.target }}"></div>
		      <div class="field"><label>세트 수</label><input id="setsInput" type="number" min="1" max="10" value="{{ meta.sets }}"></div>
		    </div>
	    <div class="save-row">
	      <button class="btn-light" onclick="startCalibration()">자세 보정 시작</button>
	    </div>
	    <div class="save-status" id="calibrationStatus">기본 기준 사용 중입니다.</div>

	    <div class="debug-panel" id="debugPanel">
	      <div class="debug-grid">
	        <div class="debug-item"><div class="debug-k">품질 점수</div><div class="debug-v" id="dbgQuality">-</div></div>
	        <div class="debug-item"><div class="debug-k">가시 랜드마크</div><div class="debug-v" id="dbgVisible">-</div></div>
        <div class="debug-item"><div class="debug-k">무릎/팔꿈치</div><div class="debug-v" id="dbgAnglesA">-</div></div>
        <div class="debug-item"><div class="debug-k">골반/몸통</div><div class="debug-v" id="dbgAnglesB">-</div></div>
        <div class="debug-item"><div class="debug-k">상태/페이즈</div><div class="debug-v" id="dbgPhase">-</div></div>
        <div class="debug-item"><div class="debug-k">대표 이슈</div><div class="debug-v" id="dbgIssue">-</div></div>
      </div>
    </div>

    <!-- 세트별 점수 요약 -->
    <div class="set-summary" id="setSummary">
      <div class="ss-title" id="setSummaryTitle">세트 요약</div>
      <div id="setSummaryRows"></div>
    </div>

    <!-- 전체 세션 총점 -->
    <div class="session-score-panel" id="sessionScorePanel">
      <div class="ssp-title">세션 완료 · 총 평가</div>
      <div class="ssp-grade" id="sspGrade">-</div>
      <div class="ssp-score" id="sspScore"></div>
      <div class="ssp-sub" id="sspSub"></div>
      <table class="set-history" id="setHistoryTable"></table>
    </div>

    <div class="summary" id="summaryBox">
      <div class="summary-title" id="summaryTitle">세트 요약</div>
      <div class="summary-text" id="summaryText"></div>
    </div>
    <div class="save-row"><button class="btn-light" onclick="saveSession()">기록 저장</button></div>
    <div class="save-status" id="saveStatus">아직 저장된 세션 기록이 없습니다.</div>
  </div>

  <!-- EMG 근육 활성도 패널 -->
  <div class="card" id="emgCard">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
      <h3 style="margin:0;display:flex;align-items:center;gap:6px;">
        <span id="emgLiveDot" style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#94a3b8;transition:.3s;flex-shrink:0;"></span>
        EMG 근육 활성도
      </h3>
      <div style="display:flex;align-items:center;gap:6px;">
        <span id="emgHz" style="font-size:10px;color:var(--muted);">— Hz</span>
        <span id="emgConnBadge" style="font-size:10px;font-weight:700;color:var(--muted);padding:2px 8px;border-radius:999px;border:1px solid var(--line);">대기</span>
        <button onclick="document.getElementById('emgCfgWrap').style.display=document.getElementById('emgCfgWrap').style.display==='none'?'block':'none'" style="padding:3px 8px;border-radius:6px;background:var(--soft);color:var(--muted);font-size:11px;font-weight:700;border:1px solid var(--line);cursor:pointer;">⚙</button>
      </div>
    </div>

    <!-- 채널별 MAV 바 차트 -->
    <div id="emgChList" style="display:flex;flex-direction:column;gap:8px;margin-bottom:10px;">
      <div style="font-size:12px;color:var(--muted);">연결 대기 중…</div>
    </div>

    <!-- 원시 신호 파형 (채널별 동적 생성) -->
    <div id="emgWaveSection" style="margin-bottom:6px;display:flex;flex-direction:column;gap:5px;"></div>

    {% if emg_guide %}
    <!-- 운동별 EMG 채널 매핑 & MVC 가이드 -->
    <div style="margin-bottom:8px;padding:8px;border-radius:8px;background:#eff6ff;border:1px solid #bfdbfe;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <span style="font-size:11px;font-weight:800;color:#1d4ed8;">EMG 부착 & MVC 가이드</span>
        <span style="font-size:10px;color:#3b82f6;font-weight:700;background:#dbeafe;padding:2px 7px;border-radius:999px;">{{ emg_guide.muscle }}</span>
      </div>

      <!-- 채널 매핑 테이블 -->
      <div style="font-size:10px;font-weight:800;color:#1d4ed8;margin-bottom:4px;">채널 부착 위치</div>
      {% for ch in emg_guide.channels %}
      <div style="display:flex;align-items:flex-start;gap:6px;margin-bottom:4px;">
        <span style="flex-shrink:0;font-size:10px;font-weight:800;color:#fff;background:{% if ch.side=='left' %}#3b82f6{% else %}#f97316{% endif %};padding:1px 6px;border-radius:999px;">CH{{ ch.ch }}</span>
        <div>
          <div style="font-size:10px;font-weight:700;color:#1e40af;">{{ ch.label }}</div>
          <div style="font-size:10px;color:#3b82f6;">{{ ch.placement }}</div>
        </div>
      </div>
      {% endfor %}
      <div style="font-size:10px;color:#64748b;margin:4px 0 8px;">기준 전극: {{ emg_guide.reference }}</div>

      <!-- MVC 프로토콜 -->
      <div style="font-size:10px;font-weight:800;color:#1d4ed8;margin-bottom:4px;">MVC 측정 방법</div>
      {% for s in emg_guide.mvc_protocol %}
      <div style="font-size:10px;color:#1e40af;padding:2px 0 2px 8px;border-left:2px solid #93c5fd;margin-bottom:3px;">{{ s }}</div>
      {% endfor %}

      <!-- 피드백 로직 설명 -->
      <div style="font-size:10px;font-weight:800;color:#1d4ed8;margin:8px 0 4px;">분석 피드백 기준</div>
      {% for f in emg_guide.feedback_logic %}
      <div style="display:flex;gap:5px;align-items:flex-start;margin-bottom:3px;">
        <span style="flex-shrink:0;font-size:9px;font-weight:800;padding:1px 5px;border-radius:4px;
          {% if f.type=='asymmetry' %}background:#fef9c3;color:#854d0e;
          {% elif f.type=='eccentric' %}background:#fce7f3;color:#9d174d;
          {% else %}background:#dcfce7;color:#166534;{% endif %}">
          {% if f.type=='activation' %}활성도{% elif f.type=='asymmetry' %}불균형{% else %}편심{% endif %}
        </span>
        <span style="font-size:10px;color:#374151;">{{ f.desc }}</span>
      </div>
      {% endfor %}
    </div>
    {% endif %}

    <!-- 캘리브레이션 패널 -->
    <div style="margin-bottom:8px;border-radius:8px;border:1px solid var(--line);overflow:hidden;">

      {% if emg_guide and emg_guide.calib_rest %}
      <!-- 힘 빼기 설명 -->
      <div style="padding:8px;background:#f0fdf4;border-bottom:1px solid #bbf7d0;">
        <div style="font-size:10px;font-weight:800;color:#16a34a;margin-bottom:4px;">{{ emg_guide.calib_rest.title }}</div>
        {% for s in emg_guide.calib_rest.steps %}
        <div style="display:flex;gap:5px;margin-bottom:2px;">
          <span style="flex-shrink:0;font-size:10px;color:#16a34a;font-weight:800;">{{ loop.index }}.</span>
          <span style="font-size:10px;color:#166534;">{{ s }}</span>
        </div>
        {% endfor %}
        <button id="emgCalibBtnrest" onclick="emgCalibStart('rest')" style="margin-top:6px;width:100%;padding:6px;border-radius:6px;background:#16a34a;color:#fff;font-size:11px;font-weight:800;border:none;cursor:pointer;">측정 시작 (3초)</button>
      </div>

      <!-- 최대 수축 설명 -->
      <div style="padding:8px;background:#fff7ed;border-bottom:1px solid #fed7aa;">
        <div style="font-size:10px;font-weight:800;color:#c2410c;margin-bottom:4px;">{{ emg_guide.calib_mvc.title }}</div>
        {% for s in emg_guide.calib_mvc.steps %}
        <div style="display:flex;gap:5px;margin-bottom:2px;">
          <span style="flex-shrink:0;font-size:10px;color:#c2410c;font-weight:800;">{{ loop.index }}.</span>
          <span style="font-size:10px;color:#7c2d12;">{{ s }}</span>
        </div>
        {% endfor %}
        <button id="emgCalibBtnmvc" onclick="emgCalibStart('mvc')" style="margin-top:6px;width:100%;padding:6px;border-radius:6px;background:#ea580c;color:#fff;font-size:11px;font-weight:800;border:none;cursor:pointer;">측정 시작 (3초)</button>
      </div>
      {% else %}
      <!-- 가이드 없는 운동용 간단 버튼 -->
      <div style="padding:8px;background:var(--soft);">
        <div style="font-size:11px;font-weight:800;color:var(--text);margin-bottom:6px;">캘리브레이션 (MVC 기준 설정)</div>
        <div style="display:flex;gap:5px;margin-bottom:6px;">
          <button id="emgCalibBtnrest" onclick="emgCalibStart('rest')" style="flex:1;padding:5px;border-radius:6px;background:#dcfce7;color:#16a34a;font-size:11px;font-weight:700;border:1px solid #86efac;cursor:pointer;">① 힘 빼기 (3초)</button>
          <button id="emgCalibBtnmvc" onclick="emgCalibStart('mvc')" style="flex:1;padding:5px;border-radius:6px;background:#fee2e2;color:#dc2626;font-size:11px;font-weight:700;border:1px solid #fca5a5;cursor:pointer;">② 최대 수축 (3초)</button>
        </div>
      </div>
      {% endif %}

      <!-- 공통: 상태 + 결과 + 초기화 -->
      <div style="padding:8px;background:var(--panel);">
        <div id="emgCalibStatus" style="font-size:11px;font-weight:700;color:var(--muted);margin-bottom:4px;">① 힘 빼기부터 순서대로 측정하세요</div>
        <div id="emgCalibValues" style="margin-bottom:6px;"></div>
        <button onclick="emgCalibReset()" style="width:100%;padding:5px;border-radius:6px;background:var(--soft);color:var(--muted);font-size:11px;font-weight:700;border:1px solid var(--line);cursor:pointer;">초기화 (동적 피크 모드로 복귀)</button>
      </div>
    </div>

    <!-- 설정 패널 -->
    <div id="emgCfgWrap" style="display:block;margin-top:8px;padding-top:8px;border-top:1px solid var(--line);">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:6px;">
        <div>
          <div style="font-size:10px;color:var(--muted);font-weight:700;margin-bottom:3px;">IP</div>
          <input id="emgCfgIP" type="text" value="172.18.140.60" style="width:100%;border:1px solid var(--line);border-radius:6px;padding:5px 7px;font-size:12px;font-weight:700;background:var(--bg);color:var(--text);outline:none;">
        </div>
        <div>
          <div style="font-size:10px;color:var(--muted);font-weight:700;margin-bottom:3px;">PORT</div>
          <input id="emgCfgPort" type="text" value="8080" style="width:100%;border:1px solid var(--line);border-radius:6px;padding:5px 7px;font-size:12px;font-weight:700;background:var(--bg);color:var(--text);outline:none;">
        </div>
        <div>
          <div style="font-size:10px;color:var(--muted);font-weight:700;margin-bottom:3px;">간격 (ms)</div>
          <input id="emgCfgInterval" type="number" value="100" min="50" max="2000" style="width:100%;border:1px solid var(--line);border-radius:6px;padding:5px 7px;font-size:12px;background:var(--bg);color:var(--text);outline:none;">
        </div>
        <div style="display:flex;align-items:flex-end;gap:5px;">
          <button onclick="emgApply()" style="flex:1;padding:6px;border-radius:6px;background:var(--accent);color:#fff;font-size:11px;font-weight:700;border:none;cursor:pointer;">적용</button>
          <button onclick="emgStop()" style="flex:1;padding:6px;border-radius:6px;background:var(--soft);color:var(--muted);font-size:11px;font-weight:700;border:1px solid var(--line);cursor:pointer;">중지</button>
        </div>
      </div>
    </div>
  </div>

  <!-- OpenCV 상태 -->
  <div class="card">
    <h3>OpenCV 상태</h3>
    <div class="metric-grid">
      <div class="metric"><div class="metric-k">측정 준비</div><div class="metric-v" id="measureReadyText">불가</div></div>
      <div class="metric"><div class="metric-k">전처리</div><div class="metric-v" id="cvStatusText">대기</div></div>
      <div class="metric"><div class="metric-k">밝기</div><div class="metric-v" id="cvBrightnessText">-</div></div>
      <div class="metric"><div class="metric-k">선명도</div><div class="metric-v" id="cvBlurText">-</div></div>
      <div class="metric"><div class="metric-k">권장 상태</div><div class="metric-v" id="cvAdviceText">카메라 시작 전</div></div>
    </div>
    <div class="save-status" id="measureReadySub">카메라 시작 전</div>
  </div>

  <div class="card">
    <h3>세션 상태</h3>
    <div class="metric-grid">
      <div class="metric"><div class="metric-k">현재 세트</div><div class="metric-v" id="setText">0 / 0</div></div>
      <div class="metric"><div class="metric-k">세션 점수</div><div class="metric-v" id="scoreText">-</div></div>
      <div class="metric"><div class="metric-k">카메라</div><div class="metric-v" id="cameraText">OFF</div></div>
      <div class="metric"><div class="metric-k">추적</div><div class="metric-v" id="trackingText">IDLE</div></div>
    </div>
  </div>

  <div class="card">
    <h3>운동 시작 가이드</h3>
    <div class="guide">
      <div class="guide-item"><div class="guide-dot"></div><span>권장 카메라: {{ meta.camera }}</span></div>
      {% for tip in tips %}<div class="guide-item"><div class="guide-dot"></div><span>{{ tip }}</span></div>{% endfor %}
    </div>
  </div>

  <div class="card">
    <h3>인식 한계점</h3>
    <div class="guide">
      {% for limitation in limitations %}<div class="guide-item"><div class="guide-dot"></div><span>{{ limitation }}</span></div>{% endfor %}
    </div>
  </div>

</aside>
</div></div>

<script src="https://cdn.jsdelivr.net/npm/@mediapipe/pose/pose.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js"></script>
<script>
const EXERCISE_KEY = "{{ exercise_key }}";
// 운동별 EMG 채널 정의: [{ch:1(1-based), label:"왼쪽 외측광근"}, ...]
const EMG_GUIDE_CHANNELS = {{ (emg_guide.channels | tojson) if emg_guide else '[]' }};

// ── DOM ───────────────────────────────────────────────────────────────────────
const video=document.getElementById("video"),canvas=document.getElementById("canvas"),ctx=canvas.getContext("2d");
const countText=document.getElementById("countText"),goodText=document.getElementById("goodText");
const stateText=document.getElementById("stateText"),overlayScore=document.getElementById("overlayScore");
const feedbackMain=document.getElementById("feedbackMain"),feedbackSub=document.getElementById("feedbackSub");
const statusChip=document.getElementById("statusChip"),setText=document.getElementById("setText");
const scoreText=document.getElementById("scoreText"),scoreFill=document.getElementById("scoreFill");
const scoreBarWrap=document.getElementById("scoreBarWrap"),cameraText=document.getElementById("cameraText");
const trackingText=document.getElementById("trackingText"),targetInput=document.getElementById("targetInput");
const cameraToggleBtn=document.getElementById("cameraToggleBtn");
const startSetBtn=document.getElementById("startSetBtn"),pauseSetBtn=document.getElementById("pauseSetBtn"),finishSetBtn=document.getElementById("finishSetBtn");
const cvStatusText=document.getElementById("cvStatusText"),cvBrightnessText=document.getElementById("cvBrightnessText");
const cvBlurText=document.getElementById("cvBlurText"),cvAdviceText=document.getElementById("cvAdviceText");
const measureReadyText=document.getElementById("measureReadyText"),measureReadySub=document.getElementById("measureReadySub");
const setsInput=document.getElementById("setsInput"),summaryBox=document.getElementById("summaryBox");
const summaryTitle=document.getElementById("summaryTitle"),summaryText=document.getElementById("summaryText");
const saveStatus=document.getElementById("saveStatus"),fbBanner=document.getElementById("fbBanner");
const calibrationStatus=document.getElementById("calibrationStatus");
const fbDot=document.getElementById("fbDot"),fbMsg=document.getElementById("fbMsg"),fbSubTxt=document.getElementById("fbSubTxt");
const repToast=document.getElementById("repToast"),rtNum=document.getElementById("rtNum"),rtGrade=document.getElementById("rtGrade");
const issueListWrap=document.getElementById("issueListWrap"),setOverlay=document.getElementById("setOverlay");
const setSummary=document.getElementById("setSummary"),setSummaryTitle=document.getElementById("setSummaryTitle");
const setSummaryRows=document.getElementById("setSummaryRows");
const sessionScorePanel=document.getElementById("sessionScorePanel");
const sspGrade=document.getElementById("sspGrade"),sspScore=document.getElementById("sspScore"),sspSub=document.getElementById("sspSub");
const setHistoryTable=document.getElementById("setHistoryTable");
const debugPanel=document.getElementById("debugPanel");
const dbgQuality=document.getElementById("dbgQuality"),dbgVisible=document.getElementById("dbgVisible");
const dbgAnglesA=document.getElementById("dbgAnglesA"),dbgAnglesB=document.getElementById("dbgAnglesB");
const dbgPhase=document.getElementById("dbgPhase"),dbgIssue=document.getElementById("dbgIssue");
let voiceCmdBtn=null,voiceCmdStatus=null;

// ── Selfie Segmentation (누끼) ─────────────────────────────────────────────────

// ── State ─────────────────────────────────────────────────────────────────────
let pose=null,camera=null;
let totalCount=0,goodCount=0,phase="idle",stableUp=0,stableDown=0,repLock=0;
let cameraStarted=false,setActive=false,paused=false;
let currentSet=0,totalSets=0,targetReps=0,liveScore=null;
let repScores=[],repIssues=[],issueCounter={},sessionHistory=[];
let repCycleScores=[],repCycleIssues=[],repCycleAnchor=null;
let repCycleStartedAt=0,repCycleInvalidReason=null;
let voiceEnabled=true,lastSpokenIssue=null,lastIssueSpeakTime=0,lastNoDetectSpoken=0,repToastTimer=null;
let sessionId=null,setStartedAt=0,sessionStartedAt=0,lastSavedSignature="",hasUnsavedChanges=false;
let lastRepAt=0,lastTransitionAt=0,qualityStableFrames=0;
let debugMode=false,lastQualityMetrics=null;
// EMG 활성 피드백 — {cls, dot, label, msg} 배열, EMG 모듈이 직접 갱신
let activeEmgFeedbacks=[];
let voiceCommandEnabled=false,speechRecognition=null,speechRestartTimer=null;
let lastPassiveVoiceKey="",lastPassiveVoiceAt=0,lastFeedbackVoiceKey="",lastFeedbackVoiceAt=0;
let cvReady=false,lastCameraQualityCheckAt=0,lastDarkWarnAt=0,lastBlurWarnAt=0,lastDistanceWarnAt=0;
let qualityCanvas=null,qualityCtx=null;
let lastCvQualityState={status:"대기",brightness:"-",blur:"-",advice:"카메라 시작 전"};
let measurementReadiness={level:"blocked",label:"불가",reason:"카메라 시작 전"};
let calibrationProfile=null,calibrationActive=false,calibrationStartedAt=0,calibrationSamples=[];
// 반동 감지용
let prevKneeAng=null,prevHipAng=null,prevElbowAng=null;
let smoothKneeAng=null,smoothHipAng=null,smoothElbowAng=null,smoothBodyAng=null,smoothTrunk=null;
// 세트 히스토리 (점수 카드용)
let allSetResults=[];
const BACKUP_KEY=`motionfit-backup-${EXERCISE_KEY}`;

// ── 점수 기준 팝업 ────────────────────────────────────────────────────────────
function toggleScoreGuide(){
  const p=document.getElementById("scoreGuidePopup");
  p.classList.toggle("show");
  if(p.classList.contains("show")){
    setTimeout(()=>p.classList.remove("show"),4000);
  }
}
document.addEventListener("click",e=>{
  const p=document.getElementById("scoreGuidePopup");
  if(p&&!e.target.closest("[onclick='toggleScoreGuide()']"))p.classList.remove("show");
});

// ── 한국어 숫자 ────────────────────────────────────────────────────────────────
const KOR_NUM=["","하나","둘","셋","넷","다섯","여섯","일곱","여덟","아홉","열",
  "열하나","열둘","열셋","열넷","열다섯","열여섯","열일곱","열여덟","열아홉","스물",
  "스물하나","스물둘","스물셋","스물넷","스물다섯","스물여섯","스물일곱","스물여덟","스물아홉","서른"];
function korNum(n){return(n>0&&n<KOR_NUM.length)?KOR_NUM[n]:String(n);}
function repCountVoice(count,score){
  const num=korNum(count);
  if(score>=90){
    const cheers=["완벽해요!","훌륭해요!","최고예요!","좋아요!"];
    const cheer=cheers[(count-1)%cheers.length];
    return `${cheer} ${num}회`;
  }else if(score>=80){
    return `좋아요! ${num}회`;
  }else if(score>=65){
    return `${num}회, 자세를 조금 더 신경써요`;
  }else{
    return `${num}회`;
  }
}

// ── 등급 ──────────────────────────────────────────────────────────────────────
function scoreToGrade(s){return s>=90?"S":s>=80?"A":s>=65?"B":"C";}
function gradeColor(g){return g==="S"?"#7c3aed":g==="A"?"var(--good)":g==="B"?"var(--warn)":"var(--bad)";}
function gradeCls(g){return"grade-"+g.toLowerCase();}

// ── Voice ─────────────────────────────────────────────────────────────────────
// Chrome TTS 버그 대응:
// 1) cancel() 직후 speak()는 묵음 → 딜레이 필요
// 2) 15~20초 이상 발화 없으면 speechSynthesis가 내부적으로 멈춤 → paused 상태 체크 후 resume
// 3) pending 큐가 쌓이면 무한 대기 → cancel로 비움
let _ttsTimer=null;
function _doSpeak(t){
  if(window.speechSynthesis.paused)window.speechSynthesis.resume();
  window.speechSynthesis.cancel();
  clearTimeout(_ttsTimer);
  _ttsTimer=setTimeout(()=>{
    const u=new SpeechSynthesisUtterance(t);
    u.lang="ko-KR";u.rate=1.05;u.volume=1;
    u.onerror=(e)=>{if(e.error!=="interrupted")console.warn("[TTS error]",e.error,t);};
    window.speechSynthesis.speak(u);
  },120);
}
function speak(t,p=false){
  if(!voiceEnabled||!window.speechSynthesis)return;
  _doSpeak(t);
}
function toggleVoice(v){voiceEnabled=v;if(!v)window.speechSynthesis.cancel();}

// ── 배경음악 (Web Audio API 비트 루프) ──────────────────────────────────────
let _bgAudioCtx=null,_bgScheduled=false,_bgNextTime=0,_bgPlaying=false;
const _BPM=128,_BEAT=60/_BPM;
function _bgKick(ctx,t){
  const o=ctx.createOscillator(),g=ctx.createGain();
  o.connect(g);g.connect(ctx.destination);
  o.frequency.setValueAtTime(160,t);o.frequency.exponentialRampToValueAtTime(40,t+0.08);
  g.gain.setValueAtTime(1,t);g.gain.exponentialRampToValueAtTime(0.001,t+0.12);
  o.start(t);o.stop(t+0.13);
}
function _bgHihat(ctx,t,loud){
  const buf=ctx.createBuffer(1,ctx.sampleRate*0.05,ctx.sampleRate);
  const d=buf.getChannelData(0);for(let i=0;i<d.length;i++)d[i]=(Math.random()*2-1);
  const src=ctx.createBufferSource(),g=ctx.createGain(),f=ctx.createBiquadFilter();
  f.type="highpass";f.frequency.value=8000;
  src.buffer=buf;src.connect(f);f.connect(g);g.connect(ctx.destination);
  g.gain.setValueAtTime(loud?0.25:0.12,t);g.gain.exponentialRampToValueAtTime(0.001,t+0.05);
  src.start(t);src.stop(t+0.06);
}
function _bgSnare(ctx,t){
  const o=ctx.createOscillator(),og=ctx.createGain();
  o.type="triangle";o.frequency.value=200;o.connect(og);og.connect(ctx.destination);
  og.gain.setValueAtTime(0.5,t);og.gain.exponentialRampToValueAtTime(0.001,t+0.1);
  o.start(t);o.stop(t+0.11);
  const buf=ctx.createBuffer(1,ctx.sampleRate*0.1,ctx.sampleRate);
  const d=buf.getChannelData(0);for(let i=0;i<d.length;i++)d[i]=(Math.random()*2-1);
  const src=ctx.createBufferSource(),g=ctx.createGain(),f=ctx.createBiquadFilter();
  f.type="bandpass";f.frequency.value=2500;f.Q.value=0.8;
  src.buffer=buf;src.connect(f);f.connect(g);g.connect(ctx.destination);
  g.gain.setValueAtTime(0.4,t);g.gain.exponentialRampToValueAtTime(0.001,t+0.1);
  src.start(t);src.stop(t+0.11);
}
function _bgScheduleBar(ctx,barStart){
  // 4/4 박자: kick on 1,3 / snare on 2,4 / hihat every 8th
  for(let b=0;b<4;b++){
    const bt=barStart+b*_BEAT;
    if(b===0||b===2)_bgKick(ctx,bt);
    if(b===1||b===3)_bgSnare(ctx,bt);
    _bgHihat(ctx,bt,true);
    _bgHihat(ctx,bt+_BEAT/2,false);
  }
}
function _bgLoop(){
  if(!_bgPlaying||!_bgAudioCtx)return;
  const now=_bgAudioCtx.currentTime;
  while(_bgNextTime<now+0.3){
    _bgScheduleBar(_bgAudioCtx,_bgNextTime);
    _bgNextTime+=_BEAT*4;
  }
  setTimeout(_bgLoop,100);
}
function toggleBgMusic(v){
  if(v){
    if(!_bgAudioCtx)_bgAudioCtx=new(window.AudioContext||window.webkitAudioContext)();
    if(_bgAudioCtx.state==="suspended")_bgAudioCtx.resume();
    _bgPlaying=true;_bgNextTime=_bgAudioCtx.currentTime+0.05;_bgLoop();
  }else{
    _bgPlaying=false;
  }
}

// Chrome: 15초마다 resume()으로 내부 멈춤 방지
setInterval(()=>{
  if(window.speechSynthesis&&window.speechSynthesis.paused)window.speechSynthesis.resume();
},15000);
function toggleDebug(v){debugMode=v;debugPanel.classList.toggle("show",v);if(v)renderDebugPanel();}
function maybeSpeak(issue,text){
  if(!voiceEnabled||!setActive)return;
  const now=Date.now(),cd=(issue===lastSpokenIssue)?5500:2800;
  if(now-lastIssueSpeakTime<cd)return;
  lastSpokenIssue=issue;lastIssueSpeakTime=now;
  speak(text,true);
}
function maybeSpeakPassive(key,text,cooldown=6000,priority=false){
  if(!voiceEnabled||!cameraStarted||!text)return;
  const now=Date.now();
  const cd=(key===lastPassiveVoiceKey)?cooldown:Math.min(cooldown,4200);
  if(now-lastPassiveVoiceAt<cd)return;
  lastPassiveVoiceKey=key;
  lastPassiveVoiceAt=now;
  speak(text,priority);
}
function feedbackVoiceText(top){
  if(!top)return"";
  const issue=top.issue||"";
  if(issue.includes("깊이 매우 부족"))return EXERCISE_KEY==="pushup"?"가슴을 더 내려주세요.":EXERCISE_KEY==="lunge"?"조금 더 내려가세요.": "조금 더 깊게 내려가세요.";
  if(issue.includes("깊이 부족"))return EXERCISE_KEY==="pushup"?"조금만 더 내려가세요.": "조금 더 내려가세요.";
  if(issue.includes("무릎 심한 내측 붕괴"))return"무릎이 안으로 모이지 않게 바깥으로 밀어주세요.";
  if(issue.includes("무릎 내측 붕괴"))return"무릎을 발 방향으로 유지하세요.";
  if(issue.includes("무릎 과도한 앞쏠림"))return EXERCISE_KEY==="lunge"?"보폭을 더 넓혀주세요.":"엉덩이를 더 뒤로 빼주세요.";
  if(issue.includes("무릎 앞쏠림"))return EXERCISE_KEY==="lunge"?"무릎이 발끝을 넘지 않게 해주세요.":"엉덩이를 조금 더 뒤로 빼주세요.";
  if(issue.includes("무릎 심한 굽힘"))return"무릎을 더 펴고 올려주세요.";
  if(issue.includes("무릎 굽힘"))return"무릎을 펴고 유지하세요.";
  if(issue.includes("엉덩이 심한 처짐"))return"복부에 힘을 주고 엉덩이를 올려주세요.";
  if(issue.includes("엉덩이 처짐"))return"엉덩이를 조금 올려주세요.";
  if(issue.includes("엉덩이 심한 들림"))return"엉덩이를 더 내려 몸통을 일직선으로 맞춰주세요.";
  if(issue.includes("엉덩이 들림"))return"엉덩이를 조금 내려주세요.";
  if(issue.includes("팔꿈치 과도한 모임"))return"팔꿈치를 더 벌려주세요.";
  if(issue.includes("팔꿈치 많이 모임"))return"어깨너비보다 조금 더 넓게 벌려주세요.";
  if(issue.includes("팔꿈치 모임"))return"팔꿈치를 조금 더 벌려주세요.";
  if(issue.includes("팔꿈치 과도한 벌어짐"))return"팔꿈치를 조금 좁혀주세요.";
  if(issue.includes("팔꿈치 벌어짐"))return EXERCISE_KEY==="pushup"?"팔꿈치를 몸통 가까이 당겨주세요.":"팔꿈치를 조금 좁혀주세요.";
  if(issue.includes("팔꿈치 굽힘"))return"팔꿈치를 살짝만 구부려 유지하세요.";
  if(issue.includes("팔꿈치 과도한 굽힘"))return"팔꿈치를 너무 많이 굽히지 마세요.";
  if(issue.includes("손목 전완 정렬 불량"))return"손목을 팔꿈치 위에 쌓아주세요.";
  if(issue.includes("손목 전완 정렬 부족"))return"손목과 팔꿈치 정렬을 더 맞춰주세요.";
  if(issue.includes("손목 정렬 불량"))return"손목 정렬을 다시 맞춰주세요.";
  if(issue.includes("손목 바깥 회전"))return"손목 안쪽이 정면을 보게 잡아주세요.";
  if(issue.includes("완전 신전 미달"))return EXERCISE_KEY==="pullup"?"팔을 끝까지 펴고 다시 당겨주세요.":"팔을 끝까지 펴주세요.";
  if(issue.includes("신전 부족"))return"상단에서 조금만 더 밀어올려주세요.";
  if(issue.includes("상단 미달"))return"턱을 더 높이 끌어올려주세요.";
  if(issue.includes("골반 심한 비대칭"))return"골반 좌우 균형을 맞춰주세요.";
  if(issue.includes("골반 비대칭"))return"골반을 수평으로 유지하세요.";
  if(issue.includes("허리 심한 과신전"))return"복부에 힘을 주고 허리를 세워주세요.";
  if(issue.includes("허리 과신전"))return"허리를 젖히지 말고 복부에 힘을 주세요.";
  if(issue.includes("허리 경미한 과신전"))return"허리를 조금 더 고정해 주세요.";
  if(issue.includes("양팔 심한 비대칭"))return"양쪽 팔 높이를 맞춰주세요.";
  if(issue.includes("양팔 비대칭"))return EXERCISE_KEY==="pullup"?"양팔을 같은 힘으로 당겨주세요.":"양쪽 팔 높이를 맞춰주세요.";
  if(issue.includes("양팔 경미한 비대칭"))return"양팔 균형을 맞춰주세요.";
  if(issue.includes("상체 과도 기울기"))return"상체를 더 세워주세요.";
  if(issue.includes("상체 기울기"))return"상체를 조금 더 세워주세요.";
  if(issue.includes("고개 숙임"))return"시선을 조금 앞쪽으로 두세요.";
  if(issue.includes("반동 킵핑"))return"반동 없이 천천히 내려오세요.";
  if(issue.includes("경미한 반동"))return"반동을 조금만 줄여주세요.";
  if(issue.includes("반동 사용"))return EXERCISE_KEY==="lateralraise"?"반동 없이 어깨로 올려주세요.":"반동 없이 천천히 움직이세요.";
  if(issue.includes("높이 매우 부족"))return"다리를 훨씬 더 높이 올려주세요.";
  if(issue.includes("높이 부족"))return"조금 더 높이 올려주세요.";
  if(issue.includes("팔 높이 매우 부족"))return"팔을 어깨 높이까지 올려주세요.";
  if(issue.includes("팔 높이 부족"))return"팔을 조금 더 올려주세요.";
  if(issue.includes("어깨 들림"))return"어깨를 내리고 팔만 움직여주세요.";
  if(issue.includes("하체 관절 인식 부족"))return"하체가 보이게 카메라를 조금 조정해 주세요.";
  return top.msg||"자세를 조정해주세요.";
}
function maybeSpeakFeedback(top){
  if(!voiceEnabled||!setActive||!top)return;
  if(top.severity!=="bad"&&top.severity!=="warn")return;
  const key=`${top.severity}:${top.issue||top.msg}`;
  const now=Date.now();
  const cooldown=key===lastFeedbackVoiceKey?5200:3200;
  if(now-lastFeedbackVoiceAt<cooldown)return;
  lastFeedbackVoiceKey=key;
  lastFeedbackVoiceAt=now;
  speak(feedbackVoiceText(top));
}

// ── UI helpers ────────────────────────────────────────────────────────────────
function setBanner(msg,sub,sev){
  fbBanner.className="fb-banner "+(sev||"");
  fbDot.className="fb-dot "+(sev||"");
  fbMsg.textContent=msg;fbSubTxt.textContent=sub||"";
}
function issueUrgency(issue){
  if(!issue)return 0;
  const safetyCritical=[
    "무릎 심한 내측 붕괴","무릎 과도한 앞쏠림","엉덩이 심한 처짐","엉덩이 심한 들림",
    "허리 심한 과신전","손목 정렬 불량","손목 바깥 회전","반동 킵핑","반동 사용",
    "골반 심한 비대칭","상체 과도 기울기","양팔 심한 비대칭"
  ];
  const countBlocking=[
    "깊이 매우 부족","높이 매우 부족","완전 신전 미달","상단 미달",
    "팔꿈치 과도한 모임","팔꿈치 많이 모임","팔꿈치 과도한 벌어짐","손목 전완 정렬 불량"
  ];
  const majorForm=[
    "무릎 내측 붕괴","무릎 앞쏠림","엉덩이 처짐","엉덩이 들림","허리 과신전",
    "양팔 비대칭","골반 비대칭","신전 부족","깊이 부족","높이 부족","팔 높이 매우 부족"
  ];
  const minorForm=[
    "팔꿈치 모임","팔꿈치 벌어짐","팔꿈치 굽힘","무릎 굽힘","상체 기울기",
    "어깨 들림","고개 숙임","팔 높이 부족","경미한 반동","하체 관절 인식 부족"
  ];
  const findRank=(arr)=>arr.findIndex(v=>issue.includes(v));
  const safetyIdx=findRank(safetyCritical);
  if(safetyIdx!==-1)return 4000-safetyIdx*10;
  const blockIdx=findRank(countBlocking);
  if(blockIdx!==-1)return 3000-blockIdx*10;
  const majorIdx=findRank(majorForm);
  if(majorIdx!==-1)return 2000-majorIdx*10;
  const minorIdx=findRank(minorForm);
  if(minorIdx!==-1)return 1000-minorIdx*10;
  if(/심한|과도한|불량/.test(issue))return 900;
  if(/비대칭|기울기|모임|벌어짐|굽힘/.test(issue))return 700;
  return 500;
}
function feedbackUrgency(f){
  const sevBase=f?.severity==="bad"?300:f?.severity==="warn"?200:100;
  const issue=f?.issue||"";
  return sevBase+issueUrgency(issue);
}
function rankFeedbacks(fbs){
  return [...(fbs||[])].sort((a,b)=>feedbackUrgency(b)-feedbackUrgency(a));
}
// EMG 피드백만 사이드바에 표시 (모션 피드백 없을 때)
function renderEmgOnlyFeedbacks(){
  const items=(window.activeEmgFeedbacks||[]);
  if(!items.length){issueListWrap.innerHTML="";return;}
  issueListWrap.innerHTML=items.slice(0,3).map(f=>
    `<div class="issue-item ${f.cls}"><div class="issue-dot ${f.dot}"></div><span class="emg-tag">EMG</span><span>${f.msg}</span></div>`
  ).join("");
}
function setFeedbacks(fbs){
  if(!fbs||!fbs.length)return;
  const ranked=rankFeedbacks(fbs);
  const top=ranked[0];
  // fix 텍스트: 교정 방법을 배너 sub에 표시
  const fixText=(top.severity==="bad"||top.severity==="warn")?feedbackVoiceText(top):"";
  feedbackMain.textContent=top.msg;feedbackSub.textContent=fixText||top.sub||"";
  // 모션 피드백 (최대 3개) + EMG 피드백 (최대 2개) 합쳐서 표시
  const motionItems=ranked.slice(0,3).map(f=>{
    const fix=(f.severity==="bad"||f.severity==="warn")?feedbackVoiceText(f):"";
    return `<div class="issue-item ${f.severity}"><div class="issue-dot ${f.severity}"></div><div style="display:flex;flex-direction:column;gap:1px;"><span>${f.msg}</span>${fix?`<span style="font-size:12px;font-weight:500;opacity:.75;">${fix}</span>`:"" }</div></div>`;
  });
  const emgItems=(activeEmgFeedbacks||[]).slice(0,2).map(f=>
    `<div class="issue-item ${f.cls}"><div class="issue-dot ${f.dot}"></div><span class="emg-tag">EMG</span><span>${f.msg}</span></div>`
  );
  issueListWrap.innerHTML=[...motionItems,...emgItems].join("");
  setBanner(top.msg,fixText||top.sub,top.severity);
  maybeSpeakFeedback(top);
}
function showRepToast(num,score){
  clearTimeout(repToastTimer);
  const g=scoreToGrade(score);
  rtNum.textContent=num;
  rtGrade.textContent=`${g}등급 · ${score}점`;
  rtGrade.style.color=gradeColor(g);
  repToast.style.borderColor=gradeColor(g);
  repToast.classList.add("show");
  repToastTimer=setTimeout(()=>repToast.classList.remove("show"),1000);
}
function resizeCanvas(){const r=canvas.getBoundingClientRect();canvas.width=r.width;canvas.height=r.height;}
function setStatus(chip,main,sub,cls=""){
  statusChip.className="status-chip "+cls;statusChip.textContent=chip;
  if(!setActive){feedbackMain.textContent=main;feedbackSub.textContent=sub;renderEmgOnlyFeedbacks();setBanner(main,sub,"");}
}
function newSessionId(){
  return `mf-${Date.now()}-${Math.random().toString(36).slice(2,8)}`;
}
function clamp(n,min,max){return Math.max(min,Math.min(max,n));}
function ema(prev,next,alpha=0.55){
  if(next==null)return prev;
  if(prev==null)return next;
  return prev+(next-prev)*alpha;
}
function resetSmoothing(){
  smoothKneeAng=null;smoothHipAng=null;smoothElbowAng=null;smoothBodyAng=null;smoothTrunk=null;
}
function sessionSignature(){
  return JSON.stringify({sessionId,exercise:EXERCISE_KEY,sets:sessionHistory});
}
function backupPayload(){
  return {
    sessionId,sessionStartedAt,currentSet,totalSets,targetReps,
    sessionHistory,allSetResults,saveStatus:saveStatus.textContent,savedAt:new Date().toISOString()
  };
}
function saveLocalBackup(){
  try{
    if(!sessionHistory.length&&!allSetResults.length)return localStorage.removeItem(BACKUP_KEY);
    localStorage.setItem(BACKUP_KEY,JSON.stringify(backupPayload()));
  }catch(_){}
}
function clearLocalBackup(){
  try{localStorage.removeItem(BACKUP_KEY);}catch(_){}
}
function restoreLocalBackup(){
  try{
    const raw=localStorage.getItem(BACKUP_KEY);
    if(!raw)return;
    const data=JSON.parse(raw);
    if(!data||!Array.isArray(data.sessionHistory)||!data.sessionHistory.length)return;
    sessionId=data.sessionId||newSessionId();
    sessionStartedAt=data.sessionStartedAt||Date.now();
    currentSet=data.currentSet||data.sessionHistory.length;
    totalSets=data.totalSets||Math.max(1,currentSet);
    targetReps=data.targetReps||Number(targetInput.value||{{ meta.target }});
    sessionHistory=data.sessionHistory;
    allSetResults=Array.isArray(data.allSetResults)&&data.allSetResults.length?data.allSetResults:data.sessionHistory;
    hasUnsavedChanges=true;
    updateSetSummaryUI();
    if(allSetResults.length)showSessionScore();
    saveStatus.textContent=`임시 기록을 복구했습니다 (${data.savedAt||"시간 정보 없음"}).`;
    setStatus("복구됨","이전 세션 임시 기록을 불러왔습니다.","계속 진행하거나 저장할 수 있습니다.","rest");
    updateHud();
  }catch(_){}
}
function landmarkVisible(lm,i,min=0.45){return(lm[i]?.visibility||0)>=min;}
function requiredIndicesForExercise(){
  if(EXERCISE_KEY==="squat")return[11,23,25,27];
  if(EXERCISE_KEY==="lunge")return[11,23,25,27,26,28];
  if(EXERCISE_KEY==="legraise")return[11,23,25,27];
  if(EXERCISE_KEY==="pushup")return[11,13,15,23,25,27];
  if(EXERCISE_KEY==="pullup")return[0,11,13,15,16];
  if(EXERCISE_KEY==="shoulderpress"||EXERCISE_KEY==="lateralraise")return[11,12,13,14,15,16];
  if(EXERCISE_KEY==="dumbbellcurl"||EXERCISE_KEY==="triceppushdown")return[11,13,15];
  return[];
}
function missingLandmarkMessage(){
  if(EXERCISE_KEY==="squat")return"골반·무릎·발목이 모두 보이게 측면 구도를 맞춰주세요.";
  if(EXERCISE_KEY==="lunge")return"앞뒤 다리와 골반이 함께 보이게 한 걸음 더 멀리 서주세요.";
  if(EXERCISE_KEY==="legraise")return"어깨·골반·무릎·발끝이 모두 보이게 측면 구도를 맞춰주세요.";
  if(EXERCISE_KEY==="pushup")return"어깨·팔꿈치·골반·무릎·발목이 함께 보이게 측면 구도를 맞춰주세요.";
  if(EXERCISE_KEY==="pullup")return"얼굴과 양손이 프레임 안에 들어오게 카메라를 조금 더 멀리 두세요.";
  if(EXERCISE_KEY==="dumbbellcurl")return"측면에서 어깨·팔꿈치·손목이 모두 보이게 구도를 조정해주세요.";
  if(EXERCISE_KEY==="triceppushdown")return"어깨·팔꿈치·손목이 모두 보이게 구도를 조정해주세요. (정면·측면·45도 모두 가능)";
  return"운동 핵심 관절이 모두 보이게 구도를 조정해주세요.";
}
function repMinDurationMs(){
  if(EXERCISE_KEY==="shoulderpress")return 700;
  if(EXERCISE_KEY==="lateralraise")return 650;
  if(EXERCISE_KEY==="dumbbellcurl")return 500;
  if(EXERCISE_KEY==="triceppushdown")return 500;
  return 360;
}
function qualityScore(visibleCount,faceVisible,lm){
  let score=visibleCount*3;
  if(faceVisible)score+=8;
  const core=[11,12,23,24,25,26,27,28].reduce((s,i)=>s+((lm[i]?.visibility||0)>0.55?1:0),0);
  score+=core*5;
  const requiredVisible=requiredIndicesForExercise().reduce((s,i)=>s+(landmarkVisible(lm,i)?1:0),0);
  score+=requiredVisible*6;
  if(smoothTrunk!=null)score+=6;
  if(smoothKneeAng!=null||smoothElbowAng!=null)score+=6;
  return clamp(Math.round(score),0,100);
}
function renderDebugPanel(){
  if(!debugMode)return;
  dbgQuality.textContent=lastQualityMetrics?`${lastQualityMetrics.score} / 100`:"-";
  dbgVisible.textContent=lastQualityMetrics?`${lastQualityMetrics.visibleCount}개`:"-";
  dbgAnglesA.textContent=`무릎 ${smoothKneeAng!=null?Math.round(smoothKneeAng)+"°":"-"} · 팔꿈치 ${smoothElbowAng!=null?Math.round(smoothElbowAng)+"°":"-"}`;
  dbgAnglesB.textContent=`골반 ${smoothHipAng!=null?Math.round(smoothHipAng)+"°":"-"} · 몸통 ${smoothTrunk!=null?Math.round(smoothTrunk)+"°":"-"}`;
  dbgPhase.textContent=`${phase.toUpperCase()} · state ${stateText.textContent}`;
  dbgIssue.textContent=(issueListWrap.textContent||feedbackMain.textContent||"-").trim();
}
function setCvQualityState(status,brightness,blur,advice){
  lastCvQualityState={status,brightness,blur,advice};
  cvStatusText.textContent=status;
  cvBrightnessText.textContent=brightness;
  cvBlurText.textContent=blur;
  cvAdviceText.textContent=advice;
}
function setMeasurementReadiness(level,reason){
  const label=level==="ready"?"측정 가능":level==="warn"?"주의":"불가";
  measurementReadiness={level,label,reason};
  measureReadyText.textContent=label;
  measureReadySub.textContent=reason;
}
function canStartMeasurement(){
  return measurementReadiness.level!=="blocked";
}
function updateCalibrationStatus(text){
  if(calibrationStatus)calibrationStatus.textContent=text;
}
function getCalibrationMetric(lm){
  const side=chooseSide(lm);
  const S=side==="left"
    ?{sh:11,el:13,wr:15,hp:23,kn:25,an:27,oSh:12,oWr:16}
    :{sh:12,el:14,wr:16,hp:24,kn:26,an:28,oSh:11,oWr:15};
  const sh=pointLoose(lm,S.sh),el=pointLoose(lm,S.el),wr=pointLoose(lm,S.wr);
  const hp=pointLoose(lm,S.hp),kn=pointLoose(lm,S.kn),an=pointLoose(lm,S.an);
  const avgShY=avg([pointLoose(lm,11)?.y,pointLoose(lm,12)?.y]);
  const avgWrY=avg([wr?.y,pointLoose(lm,S.oWr)?.y]);
  if(EXERCISE_KEY==="squat"||EXERCISE_KEY==="lunge")return angle(hp,kn,an);
  if(EXERCISE_KEY==="pushup"||EXERCISE_KEY==="pullup"||EXERCISE_KEY==="shoulderpress")return angle(sh,el,wr);
  if(EXERCISE_KEY==="legraise")return angle(sh,hp,kn);
  if(EXERCISE_KEY==="lateralraise"&&avgShY!=null&&avgWrY!=null)return avgWrY-avgShY;
  if(EXERCISE_KEY==="dumbbellcurl"||EXERCISE_KEY==="triceppushdown")return angle(sh,el,wr);
  return null;
}
function calibrationMinRange(){
  if(EXERCISE_KEY==="lateralraise")return 0.05;
  if(EXERCISE_KEY==="shoulderpress")return 24;
  if(EXERCISE_KEY==="dumbbellcurl")return 20;
  if(EXERCISE_KEY==="triceppushdown")return 20;
  return 18;
}
function startCalibration(){
  if(!cameraStarted){
    setStatus("대기 중","먼저 카메라를 시작하세요.","카메라가 켜진 뒤 자세 보정을 시작할 수 있습니다.");
    return;
  }
  if(setActive){
    setStatus("세트 진행","세트 중에는 자세 보정을 시작할 수 없습니다.","세트 종료 후 다시 시도하세요.","warn");
    return;
  }
  calibrationActive=true;
  calibrationStartedAt=Date.now();
  calibrationSamples=[];
  calibrationProfile=null;
  updateCalibrationStatus("보정 중: 6초 동안 준비 자세와 1회 동작 범위를 천천히 보여주세요.");
  setBanner("자세 보정 시작","준비 자세 2초 후 천천히 1회 동작을 수행하세요.","good");
  feedbackMain.textContent="자세 보정 중입니다.";
  feedbackSub.textContent="준비 자세를 잠깐 유지한 뒤 1회 동작 범위를 천천히 수행하세요.";
  speak("자세 보정을 시작합니다. 준비 자세를 유지한 뒤 한 번 천천히 움직여주세요.",true);
}
function finishCalibration(){
  calibrationActive=false;
  if(calibrationSamples.length<12){
    calibrationProfile=null;
    updateCalibrationStatus("보정 실패: 표본이 부족합니다. 카메라 구도를 맞춘 뒤 다시 시도하세요.");
    setBanner("자세 보정 실패","관절 인식이 부족했습니다. 구도를 맞춘 뒤 다시 시도하세요.","warn");
    return;
  }
  const minVal=Math.min(...calibrationSamples),maxVal=Math.max(...calibrationSamples);
  const range=maxVal-minVal;
  if(range<calibrationMinRange()){
    calibrationProfile=null;
    updateCalibrationStatus("보정 실패: 동작 범위가 너무 작습니다. 1회 동작을 더 크게 수행해 주세요.");
    setBanner("자세 보정 실패","동작 범위가 너무 작아 개인 기준을 만들지 못했습니다.","warn");
    return;
  }
  calibrationProfile={min:minVal,max:maxVal,range,updatedAt:Date.now()};
  updateCalibrationStatus(`개인 기준 적용 중 · 범위 ${EXERCISE_KEY==="lateralraise"?range.toFixed(2):Math.round(range)}${EXERCISE_KEY==="lateralraise"?"":"°"}`);
  setBanner("자세 보정 완료","현재 사용자 범위 기준으로 카운트 민감도를 조정합니다.","good");
  speak("자세 보정이 완료되었습니다.",true);
}
function maybeCaptureCalibration(lm){
  if(!calibrationActive)return;
  const metric=getCalibrationMetric(lm);
  if(metric==null||isNaN(metric))return;
  calibrationSamples.push(metric);
  const elapsed=Date.now()-calibrationStartedAt;
  if(elapsed>=6000)finishCalibration();
}
function getThresholds(metricType){
  if(!calibrationProfile)return null;
  const {min,max,range}=calibrationProfile;
  if(metricType==="down_to_up_low_angle")return{down:min+range*0.32,up:max-range*0.18};
  if(metricType==="up_to_down_high_angle")return{up:max-range*0.18,down:min+range*0.32};
  if(metricType==="up_to_down_low_y")return{up:min+range*0.28,down:max-range*0.22};
  return null;
}
function loadOpenCv(){
  if(cvReady||(typeof cv!=="undefined"&&cv?.Mat)){
    cvReady=true;
    setCvQualityState("준비 완료","-","-","OpenCV 전처리 분석을 사용할 수 있습니다.");
    return;
  }
  // OpenCV는 선택 기능 — 로딩 중이어도 측정 차단하지 않음
  window.Module=window.Module||{};
  window.Module.onRuntimeInitialized=()=>{
    cvReady=true;
    setCvQualityState("준비 완료",lastCvQualityState.brightness,lastCvQualityState.blur,"OpenCV 전처리 분석을 사용할 수 있습니다.");
  };
  if(document.querySelector('script[data-opencv-loader="true"]'))return;
  const script=document.createElement("script");
  script.async=true;
  script.src="https://docs.opencv.org/4.x/opencv.js";
  script.dataset.opencvLoader="true";
  script.onerror=()=>setCvQualityState("로드 실패","-","-","네트워크 상태를 확인하고 새로고침 해주세요.");
  document.head.appendChild(script);
}
function initQualityCanvas(){
  if(qualityCanvas)return;
  qualityCanvas=document.createElement("canvas");
  qualityCtx=qualityCanvas.getContext("2d",{willReadFrequently:true});
}
function checkCameraQuality(){
  if(!cameraStarted||!video.videoWidth||!video.videoHeight)return;
  const now=Date.now();
  if(now-lastCameraQualityCheckAt<1000)return;
  lastCameraQualityCheckAt=now;
  initQualityCanvas();
  qualityCanvas.width=video.videoWidth;
  qualityCanvas.height=video.videoHeight;
  qualityCtx.drawImage(video,0,0,qualityCanvas.width,qualityCanvas.height);
  const frame=qualityCtx.getImageData(0,0,qualityCanvas.width,qualityCanvas.height);
  let avgBrightness=0,blurScore=0;
  if(cvReady&&typeof cv!=="undefined"){
    let src=null,gray=null,lap=null,mean=null,stddev=null;
    try{
      src=cv.matFromImageData(frame);
      gray=new cv.Mat();lap=new cv.Mat();mean=new cv.Mat();stddev=new cv.Mat();
      cv.cvtColor(src,gray,cv.COLOR_RGBA2GRAY);
      cv.meanStdDev(gray,mean,stddev);
      avgBrightness=mean.data64F[0];
      cv.Laplacian(gray,lap,cv.CV_64F);
      cv.meanStdDev(lap,mean,stddev);
      blurScore=(stddev.data64F[0]||0)*(stddev.data64F[0]||0);
    }catch(_){
      avgBrightness=0;blurScore=0;
    }finally{
      if(src)src.delete();if(gray)gray.delete();if(lap)lap.delete();if(mean)mean.delete();if(stddev)stddev.delete();
    }
  }else{
    let totalBrightness=0;
    for(let i=0;i<frame.data.length;i+=4){
      const r=frame.data[i],g=frame.data[i+1],b=frame.data[i+2];
      totalBrightness+=(r+g+b)/3;
    }
    avgBrightness=totalBrightness/(frame.data.length/4);
  }
  const brightnessText=Math.round(avgBrightness)||0;
  const blurText=blurScore?Math.round(blurScore):"-";
  let status="양호",advice="현재 환경에서 측정 가능합니다.";
  let readinessLevel="ready",readinessReason="카메라 환경이 안정적입니다.";
  if(avgBrightness<60&&now-lastDarkWarnAt>5000){
    lastDarkWarnAt=now;
    setBanner("화면이 너무 어둡습니다.","조명을 밝게 하거나 밝은 곳에서 운동하세요.","warn");
    maybeSpeakPassive("cv-dark","화면이 어둡습니다. 조명을 더 밝게 해주세요.");
  }
  if(avgBrightness<60){
    status="조명 부족";advice="조명을 밝게 하거나 밝은 곳에서 운동하세요.";
    readinessLevel="warn";readinessReason=advice;
  }else if(avgBrightness>215&&now-lastDarkWarnAt>5000){
    lastDarkWarnAt=now;
    setBanner("화면이 너무 밝습니다.","역광을 피하고 조명을 조금 낮춰주세요.","warn");
    maybeSpeakPassive("cv-bright","화면이 너무 밝습니다. 역광을 피해 주세요.");
  }
  if(avgBrightness>215){
    status="과다 밝기";advice="역광을 피하고 조명을 조금 낮춰주세요.";
    readinessLevel="warn";readinessReason=advice;
  }
  if(blurScore&&blurScore<45&&now-lastBlurWarnAt>5000){
    lastBlurWarnAt=now;
    setBanner("카메라 화면이 흐립니다.","렌즈를 닦고 카메라를 고정해 주세요.","warn");
    maybeSpeakPassive("cv-blur","카메라 화면이 흐립니다. 렌즈를 닦고 카메라를 고정해 주세요.");
  }
  if(blurScore&&blurScore<45){
    status="흐림 감지";advice="렌즈를 닦고 카메라를 고정해 주세요.";
    readinessLevel="warn";readinessReason=advice;
  }
  setCvQualityState(status,String(brightnessText),String(blurText),advice);
  setMeasurementReadiness(readinessLevel,readinessReason);
}

// ── Math utils ────────────────────────────────────────────────────────────────
function avg(vals){const v=vals.filter(x=>typeof x==="number"&&!isNaN(x));return v.length?v.reduce((a,b)=>a+b,0)/v.length:null;}
function point(lm,i){const p=lm[i];return(p&&p.visibility>0.3)?{x:p.x,y:p.y,z:p.z,v:p.visibility}:null;}
function chooseSide(lm){
  const L=[11,13,15,23,25,27].reduce((s,i)=>s+(lm[i]?.visibility||0),0);
  const R=[12,14,16,24,26,28].reduce((s,i)=>s+(lm[i]?.visibility||0),0);
  return L>=R?"left":"right";
}
function angle(a,b,c){
  if(!a||!b||!c)return null;
  const ab={x:a.x-b.x,y:a.y-b.y},cb={x:c.x-b.x,y:c.y-b.y};
  const dot=ab.x*cb.x+ab.y*cb.y,mag=Math.hypot(ab.x,ab.y)*Math.hypot(cb.x,cb.y);
  if(!mag)return null;
  return Math.acos(Math.min(1,Math.max(-1,dot/mag)))*180/Math.PI;
}
// 몸통 기울기: hip.y > sh.y 정상
function trunkLean(sh,hp){
  if(!sh||!hp)return null;
  const dy=hp.y-sh.y;if(dy<=0)return null;
  return Math.abs(Math.atan2(Math.abs(hp.x-sh.x),dy)*180/Math.PI);
}
// 각도 변화 속도 (반동 감지용)
function angSpeed(cur,prev){return(cur!=null&&prev!=null)?Math.abs(cur-prev):0;}
function pointLoose(lm,i){
  const p=lm[i];
  return(p&&typeof p.x==="number"&&typeof p.y==="number"&&(p.visibility||0)>0.15)?{x:p.x,y:p.y,z:p.z||0,v:p.visibility||0}:null;
}
function mapMoveNetPoseToPseudoLandmarks(pose){
  if(!pose?.keypoints?.length||!video.videoWidth||!video.videoHeight)return null;
  const out=Array.from({length:33},()=>({x:0,y:0,z:0,visibility:0}));
  const map={0:0,5:11,6:12,7:13,8:14,9:15,10:16,11:23,12:24,13:25,14:26,15:27,16:28};
  pose.keypoints.forEach((kp,idx)=>{
    const target=map[idx];
    if(target===undefined)return;
    out[target]={
      x:kp.x/video.videoWidth,
      y:kp.y/video.videoHeight,
      z:0,
      visibility:kp.score||0
    };
  });
  return out;
}
function getCompareSignal(lm){
  const side=chooseSide(lm);
  const S=side==="left"
    ?{sh:11,el:13,wr:15,hp:23,kn:25,an:27,oWr:16}
    :{sh:12,el:14,wr:16,hp:24,kn:26,an:28,oWr:15};
  const sh=pointLoose(lm,S.sh),el=pointLoose(lm,S.el),wr=pointLoose(lm,S.wr);
  const hp=pointLoose(lm,S.hp),kn=pointLoose(lm,S.kn),an=pointLoose(lm,S.an),nose=pointLoose(lm,0),oWr=pointLoose(lm,S.oWr);
  const avgWrY=avg([wr?.y,oWr?.y]);
  const avgShY=avg([pointLoose(lm,11)?.y,pointLoose(lm,12)?.y]);
  const kneeAng=angle(hp,kn,an),elbowAng=angle(sh,el,wr),hipAng=angle(sh,hp,kn);
  const kneeAngL=angle(pointLoose(lm,23),pointLoose(lm,25),pointLoose(lm,27));
  const kneeAngR=angle(pointLoose(lm,24),pointLoose(lm,26),pointLoose(lm,28));
  const kneeAngBoth=avg([kneeAngL,kneeAngR]);
  const sqFrontal=(pointLoose(lm,11)?.visibility||0)>0.4&&(pointLoose(lm,12)?.visibility||0)>0.4&&kneeAngBoth!=null;
  const sqKnee=sqFrontal?kneeAngBoth:(kneeAng??kneeAngBoth);
  if(EXERCISE_KEY==="squat"&&sqKnee!=null)return{inDown:sqKnee<112,inUp:sqKnee>150,phaseLabel:sqKnee<112?"DOWN":sqKnee>150?"UP":"MID"};
  if(EXERCISE_KEY==="pushup"&&elbowAng!=null)return{inDown:elbowAng<96,inUp:elbowAng>150,phaseLabel:elbowAng<96?"DOWN":elbowAng>150?"UP":"MID"};
  if(EXERCISE_KEY==="lunge"&&kneeAng!=null)return{inDown:kneeAng<112,inUp:kneeAng>148,phaseLabel:kneeAng<112?"DOWN":kneeAng>148?"UP":"MID"};
  if(EXERCISE_KEY==="pullup"&&elbowAng!=null&&nose&&avgWrY!=null)return{atTop:nose.y<avgWrY+0.025&&elbowAng<124,atBottom:elbowAng>150,phaseLabel:nose.y<avgWrY+0.025&&elbowAng<124?"TOP":elbowAng>150?"BOTTOM":"MID"};
  if(EXERCISE_KEY==="legraise"&&hipAng!=null)return{inUp:hipAng<98,inDown:hipAng>148,phaseLabel:hipAng<98?"UP":hipAng>148?"DOWN":"MID"};
  if(EXERCISE_KEY==="shoulderpress"){
    const elAngL=angle(pointLoose(lm,11),pointLoose(lm,13),pointLoose(lm,15));
    const elAngR=angle(pointLoose(lm,12),pointLoose(lm,14),pointLoose(lm,16));
    const spFr=(pointLoose(lm,11)?.visibility||0)>0.4&&(pointLoose(lm,12)?.visibility||0)>0.4&&elAngL!=null&&elAngR!=null;
    const spEA=spFr?avg([elAngL,elAngR]):elbowAng;
    // UP: 145° 이상 (손목이 어깨 위), DOWN: 115° 이하 (하단 준비 자세)
    if(spEA!=null)return{inUp:spEA>145,inDown:spEA<115,phaseLabel:spEA>145?"UP":spEA<115?"DOWN":"MID"};
  }
  if(EXERCISE_KEY==="lateralraise"&&avgShY!=null){
    const wY=avg([pointLoose(lm,15)?.y,pointLoose(lm,16)?.y]);
    if(wY!=null)return{inUp:wY<avgShY+0.08,inDown:wY>avgShY+0.14,phaseLabel:wY<avgShY+0.08?"UP":wY>avgShY+0.14?"DOWN":"MID"};
  }
  // 덤벨컬: 정면/측면 자동
  if(EXERCISE_KEY==="dumbbellcurl"){
    const elYL=pointLoose(lm,13)?.y,wrYL=pointLoose(lm,15)?.y;
    const elYR=pointLoose(lm,14)?.y,wrYR=pointLoose(lm,16)?.y;
    const avgElYS=avg([elYL,elYR]),avgWrYS=avg([wrYL,wrYR]);
    const curlFr=(pointLoose(lm,11)?.visibility||0)>0.4&&(pointLoose(lm,12)?.visibility||0)>0.4&&avgElYS!=null&&avgWrYS!=null;
    if(curlFr){
      const m=avgWrYS-avgElYS;
      return{inUp:m<-0.04,inDown:m>0.10,phaseLabel:m<-0.04?"UP":m>0.10?"DOWN":"MID"};
    }
    if(elbowAng!=null)return{inUp:elbowAng<85,inDown:elbowAng>145,phaseLabel:elbowAng<85?"UP":elbowAng>145?"DOWN":"MID"};
  }
  // 트라이셉 푸쉬다운: 45도/정면/측면 자동 — 양팔 보이면 평균 사용
  if(EXERCISE_KEY==="triceppushdown"){
    const elAngL=angle(pointLoose(lm,11),pointLoose(lm,13),pointLoose(lm,15));
    const elAngR=angle(pointLoose(lm,12),pointLoose(lm,14),pointLoose(lm,16));
    const triFr=(pointLoose(lm,11)?.visibility||0)>0.4&&(pointLoose(lm,12)?.visibility||0)>0.4&&elAngL!=null&&elAngR!=null;
    const triEA=triFr?avg([elAngL,elAngR]):elbowAng;
    if(triEA!=null)return{inUp:triEA<100,inDown:triEA>148,phaseLabel:triEA>148?"DOWN":triEA<100?"UP":"MID"};
  }
  return null;
}
function evaluateMoveNetForm(lm,conf){
  const fbs=[];
  const bad=(msg,sub,issue)=>fbs.push({msg,sub:sub||"",severity:"bad",issue:issue||null});
  const warn=(msg,sub,issue)=>fbs.push({msg,sub:sub||"",severity:"warn",issue:issue||null});
  const good=(msg,sub)=>fbs.push({msg,sub:sub||"",severity:"good",issue:null});
  const side=chooseSide(lm);
  const S=side==="left"
    ?{sh:11,el:13,wr:15,hp:23,kn:25,an:27,oSh:12,oEl:14,oWr:16}
    :{sh:12,el:14,wr:16,hp:24,kn:26,an:28,oSh:11,oEl:13,oWr:15};
  const sh=pointLoose(lm,S.sh),el=pointLoose(lm,S.el),wr=pointLoose(lm,S.wr);
  const hp=pointLoose(lm,S.hp),kn=pointLoose(lm,S.kn),an=pointLoose(lm,S.an),nose=pointLoose(lm,0);
  const oSh=pointLoose(lm,S.oSh),oEl=pointLoose(lm,S.oEl),oWr=pointLoose(lm,S.oWr);
  const avgShY=avg([sh?.y,oSh?.y]),avgWrY=avg([wr?.y,oWr?.y]);
  const signal=getCompareSignal(lm);
  if(!signal)return{valid:false,main:"MoveNet 관절 인식 중",sub:""};
  let score=Math.round(45+conf*0.45);
  if(EXERCISE_KEY==="squat"){
    const kneeAng=angle(hp,kn,an);
    if(kneeAng<92)good("MoveNet: 충분한 스쿼트 깊이",`무릎 ${Math.round(kneeAng)}°`);
    else if(kneeAng>130){score-=14;warn("MoveNet: 깊이가 부족합니다",`무릎 ${Math.round(kneeAng)}°`,"깊이 부족");}
    else good("MoveNet: 진행 중",`무릎 ${Math.round(kneeAng)}°`);
  }else if(EXERCISE_KEY==="pushup"){
    const elbowAng=angle(sh,el,wr);
    if(elbowAng<95)good("MoveNet: 충분히 내려갔습니다",`팔꿈치 ${Math.round(elbowAng)}°`);
    else if(elbowAng>125){score-=14;warn("MoveNet: 더 내려가세요",`팔꿈치 ${Math.round(elbowAng)}°`,"깊이 부족");}
  }else if(EXERCISE_KEY==="lunge"){
    const kneeAng=angle(hp,kn,an);
    if(kneeAng<95)good("MoveNet: 충분한 런지 깊이",`무릎 ${Math.round(kneeAng)}°`);
    else if(kneeAng>128){score-=12;warn("MoveNet: 더 내려가세요",`무릎 ${Math.round(kneeAng)}°`,"깊이 부족");}
  }else if(EXERCISE_KEY==="pullup"){
    const elbowAng=angle(sh,el,wr);
    if(signal.atTop)good("MoveNet: 상단 도달",`팔꿈치 ${Math.round(elbowAng)}°`);
    else if(elbowAng<132){score-=10;warn("MoveNet: 턱을 더 올리세요",`팔꿈치 ${Math.round(elbowAng)}°`,"상단 미달");}
  }else if(EXERCISE_KEY==="legraise"){
    const hipAng=angle(sh,hp,kn);
    if(signal.inUp)good("MoveNet: 충분한 레그레이즈 높이",`골반 ${Math.round(hipAng)}°`);
    else if(hipAng>112){score-=10;warn("MoveNet: 다리를 더 올리세요",`골반 ${Math.round(hipAng)}°`,"높이 부족");}
  }else if(EXERCISE_KEY==="shoulderpress"){
    const elbowAng=angle(sh,el,wr);
    if(signal.inUp)good("MoveNet: 상단 신전 도달",`팔꿈치 ${Math.round(elbowAng)}°`);
    else if(elbowAng!=null&&elbowAng>148){score-=8;warn("MoveNet: 끝까지 밀어올리세요",`팔꿈치 ${Math.round(elbowAng)}°`,"신전 부족");}
  }else if(EXERCISE_KEY==="lateralraise"){
    const wY=avg([pointLoose(lm,15)?.y,pointLoose(lm,16)?.y]);
    if(signal.inUp)good("MoveNet: 어깨 높이 도달",wY!=null?`손목 y ${wY.toFixed(2)}`:"");
    else score-=8,warn("MoveNet: 팔을 더 올리세요","어깨 높이 전후까지 올려주세요.","팔 높이 부족");
  }else if(EXERCISE_KEY==="dumbbellcurl"){
    const elbowAng=angle(sh,el,wr);
    if(signal.inUp)good("MoveNet: 완전 굴곡 도달",elbowAng!=null?`팔꿈치 ${Math.round(elbowAng)}°`:"");
    else if(elbowAng!=null&&elbowAng>100){score-=10;warn("MoveNet: 끝까지 굽혀 올리세요",`팔꿈치 ${Math.round(elbowAng)}°`,"굴곡 부족");}
  }else if(EXERCISE_KEY==="triceppushdown"){
    const elbowAng=angle(sh,el,wr);
    if(signal.inDown)good("MoveNet: 완전 신전 도달",elbowAng!=null?`팔꿈치 ${Math.round(elbowAng)}°`:"");
    else if(elbowAng!=null&&elbowAng<140){score-=10;warn("MoveNet: 팔을 완전히 펴주세요",`팔꿈치 ${Math.round(elbowAng)}°`,"신전 부족");}
  }
  if(conf<55){score-=10;warn("MoveNet: 신뢰도가 낮습니다",`품질 ${conf}%`,"저신뢰도");}
  fbs.sort((a,b)=>({bad:0,warn:1,good:2}[a.severity]-({bad:0,warn:1,good:2}[b.severity])));
  const issues=fbs.filter(f=>f.issue).map(f=>f.issue);
  const curlOrPush=EXERCISE_KEY==="dumbbellcurl"||EXERCISE_KEY==="triceppushdown";
  return{
    valid:true,feedbacks:fbs.length?fbs:[{msg:"MoveNet 진행 중",sub:`품질 ${conf}%`,severity:"good",issue:null}],
    score:clamp(score,45,100),topIssue:issues[0]||null,allIssues:issues,countOn:(EXERCISE_KEY==="shoulderpress"||EXERCISE_KEY==="lateralraise"||EXERCISE_KEY==="triceppushdown")?"up_to_down":"down_to_up",
    inUp:!!signal.inUp,inDown:!!signal.inDown,upLabel:signal.phaseLabel==="TOP"?"TOP":"UP",downLabel:signal.phaseLabel==="BOTTOM"?"BOTTOM":"DOWN",
    atTop:!!signal.atTop,atBottom:!!signal.atBottom,phaseLabel:signal.phaseLabel||"-"
  };
}
function updateMoveNetRep(signal,score,conf,issueList){
  const now=Date.now();
  if(moveNetRepLock>0){moveNetRepLock--;return;}
  if("atTop"in signal||"atBottom"in signal){
    if(signal.atTop){
      moveNetStableUp++;moveNetStableDown=0;moveNetPhase="up";
      if(moveNetStableUp>=2&&now-moveNetLastTransitionAt>180)moveNetLastTransitionAt=now;
    }else if(signal.atBottom){
      moveNetStableDown++;moveNetStableUp=0;
      if(moveNetStableDown>=2){
        if(moveNetPhase==="up"&&now-moveNetLastTransitionAt>280){moveNetCount++;moveNetRepScores.push(score||0);moveNetRepConfs.push(conf||0);if(issueList)moveNetIssues.push(...issueList);moveNetRepLock=8;moveNetPhase="down";moveNetLastTransitionAt=now;}
        else if(now-moveNetLastTransitionAt>180){moveNetPhase="down";moveNetLastTransitionAt=now;}
      }
    }
    return;
  }
  if(signal.inDown){
    moveNetStableDown++;moveNetStableUp=0;
    if(moveNetStableDown>=2){
      if(moveNetPhase!=="down"&&now-moveNetLastTransitionAt>180){moveNetPhase="down";moveNetLastTransitionAt=now;}
    }
  }else if(signal.inUp){
    moveNetStableUp++;moveNetStableDown=0;
    if(moveNetStableUp>=2){
      const upToDown=EXERCISE_KEY==="shoulderpress"||EXERCISE_KEY==="lateralraise"||EXERCISE_KEY==="triceppushdown";
      if(!upToDown&&moveNetPhase==="down"){
        if(now-moveNetLastTransitionAt>280){moveNetCount++;moveNetRepScores.push(score||0);moveNetRepConfs.push(conf||0);if(issueList)moveNetIssues.push(...issueList);moveNetRepLock=8;moveNetPhase="up";moveNetLastTransitionAt=now;}
      }else if(now-moveNetLastTransitionAt>180){moveNetPhase="up";moveNetLastTransitionAt=now;}
    }
  }else{
    moveNetStableUp=Math.max(0,moveNetStableUp-1);moveNetStableDown=Math.max(0,moveNetStableDown-1);
  }
  const upToDownEx=EXERCISE_KEY==="shoulderpress"||EXERCISE_KEY==="lateralraise"||EXERCISE_KEY==="triceppushdown";
  if(upToDownEx&&signal.inDown&&moveNetPhase==="up"&&now-moveNetLastTransitionAt>280){
    moveNetCount++;moveNetRepScores.push(score||0);moveNetRepConfs.push(conf||0);if(issueList)moveNetIssues.push(...issueList);moveNetRepLock=8;moveNetPhase="down";moveNetLastTransitionAt=now;
  }
}
async function runMoveNetCompare(){return false;}

// ── Rep counter ───────────────────────────────────────────────────────────────
const STABLE=2;
function resetRepCounters(){
  totalCount=0;goodCount=0;phase="idle";stableUp=0;stableDown=0;repLock=0;
  repScores=[];repIssues=[];issueCounter={};lastSpokenIssue=null;lastIssueSpeakTime=0;
  repCycleScores=[];repCycleIssues=[];repCycleAnchor=null;
  prevKneeAng=null;prevHipAng=null;prevElbowAng=null;lastRepAt=0;lastTransitionAt=0;resetSmoothing();updateHud();
}
function updateHud(){
  if(cameraToggleBtn){
    cameraToggleBtn.textContent=cameraStarted?"카메라 중지":"카메라 시작";
    cameraToggleBtn.className=cameraStarted?"btn-camera-stop":"btn-primary";
  }
  if(startSetBtn)startSetBtn.textContent=paused?"세트 재개":"세트 시작";
  if(pauseSetBtn)pauseSetBtn.textContent="세트 일시정지";
  if(finishSetBtn)finishSetBtn.textContent="세트 저장 후 종료";
  countText.textContent=String(totalCount);goodText.textContent=String(goodCount);
  setText.textContent=`${currentSet} / ${totalSets||0}`;
  setOverlay.textContent=totalSets?`${currentSet}/${totalSets}`:"-";
  if(liveScore!=null){
    const sc=Math.round(liveScore);
    scoreText.textContent=sc;overlayScore.textContent=sc;
    overlayScore.className="overlay-v"+(sc>=80?" good":sc>=65?" warn":" bad");
    scoreBarWrap.style.display="block";
    scoreFill.style.width=sc+"%";
    scoreFill.style.background=sc>=80?"var(--good)":sc>=65?"var(--warn)":"var(--bad)";
  }else{
    scoreText.textContent="-";overlayScore.textContent="-";
    overlayScore.className="overlay-v";scoreBarWrap.style.display="none";
  }
}
async function changeMainModel(_model){return false;}
function addIssue(n){if(n)issueCounter[n]=(issueCounter[n]||0)+1;}
function resetRepCycle(){
  repCycleScores=[];repCycleIssues=[];repCycleAnchor=null;repCycleStartedAt=0;repCycleInvalidReason=null;
}
function startRepCycle(anchor,score,issueList){
  repCycleAnchor=anchor;
  repCycleScores=[];
  repCycleIssues=[];
  repCycleStartedAt=Date.now();
  repCycleInvalidReason=null;
  captureRepSample(score,issueList);
}
function invalidateRepCycle(reason){
  repCycleInvalidReason=reason||"동작 품질 부족";
}
function captureRepSample(score,issueList){
  if(score!=null&&!isNaN(score))repCycleScores.push(score);
  if(issueList&&issueList.length)repCycleIssues.push(...issueList.filter(Boolean));
}
function finalizeRepCycle(score,issue,issueList){
  captureRepSample(score,issueList||[issue].filter(Boolean));
  const duration=repCycleStartedAt?Date.now()-repCycleStartedAt:0;
  if(duration&&duration<repMinDurationMs())repCycleInvalidReason=repCycleInvalidReason||"동작 속도 과다";
  if(repCycleInvalidReason){
    const invalidIssue=repCycleInvalidReason;
    resetRepCycle();
    return {invalid:true,issue:invalidIssue};
  }
  const scores=repCycleScores.length?repCycleScores:[score];
  const avgScore=Math.round(scores.reduce((a,b)=>a+b,0)/scores.length);
  const issues=repCycleIssues.length?[...new Set(repCycleIssues)]:issueList?.filter(Boolean)||[issue].filter(Boolean);
  let topIssue=issue||null;
  if(repCycleIssues.length){
    const freq={};
    repCycleIssues.forEach(i=>{freq[i]=(freq[i]||0)+1;});
    topIssue=Object.entries(freq).sort((a,b)=>{
      const urgencyDiff=issueUrgency(b[0])-issueUrgency(a[0]);
      if(urgencyDiff!==0)return urgencyDiff;
      return b[1]-a[1];
    })[0]?.[0]||topIssue;
  }
  resetRepCycle();
  return {score:avgScore,issue:topIssue,issueList:issues};
}
function registerRep(score,issue,issueList){
  const now=Date.now();
  if(now-lastRepAt<300)return;
  lastRepAt=now;
  totalCount++;
  const g=scoreToGrade(score);
  if(score>=80)goodCount++;
  repScores.push(score);
  repIssues.push(issue||null);
  if(issue)addIssue(issue);
  if(issueList)issueList.forEach(i=>{if(i)addIssue(i);});
  updateHud();
  // 긍정적 음성 카운트
  const repVoice=repCountVoice(totalCount,score);
  speak(repVoice,true);
  showRepToast(totalCount,score);
  if(totalCount>=targetReps)finishSet();
}
function topIssues(){return Object.entries(issueCounter).sort((a,b)=>b[1]-a[1]).slice(0,3).map(([n])=>n);}
function ensureVoiceControlUI(){
  if(voiceCmdBtn)return;
  const toolbar=document.querySelector(".toolbar");
  if(!toolbar)return;
  voiceCmdBtn=document.createElement("button");
  voiceCmdBtn.className="btn-light";
  voiceCmdBtn.textContent="음성 명령 시작";
  voiceCmdBtn.onclick=()=>toggleVoiceCommands();
  toolbar.appendChild(voiceCmdBtn);
  voiceCmdStatus=document.createElement("div");
  voiceCmdStatus.style.marginTop="8px";
  voiceCmdStatus.style.fontSize="12px";
  voiceCmdStatus.style.color="var(--muted)";
  voiceCmdStatus.textContent="음성 명령: 꺼짐";
  toolbar.parentElement.appendChild(voiceCmdStatus);
}
function setVoiceCommandStatus(text){
  if(voiceCmdStatus)voiceCmdStatus.textContent=text;
  if(voiceCmdBtn)voiceCmdBtn.textContent=voiceCommandEnabled?"음성 명령 중지":"음성 명령 시작";
}
function toggleCamera(){
  if(cameraStarted){stopCamera();return;}
  startCamera();
}
async function initMoveNetDetector(){return false;}
async function toggleCompareMode(_v){return false;}
function handleVoiceCommand(text){
  if(!text)return;
  const cmd=text.replace(/\s+/g,"").toLowerCase();
  if(cmd.includes("카메라시작")){startCamera();setVoiceCommandStatus(`음성 명령: ${text}`);return;}
  if(cmd.includes("카메라종료")||cmd.includes("카메라꺼")){stopCamera();setVoiceCommandStatus(`음성 명령: ${text}`);return;}
  if(cmd.includes("세트시작")||cmd.includes("운동시작")||cmd.includes("세트재개")){startSet();setVoiceCommandStatus(`음성 명령: ${text}`);return;}
  if(cmd.includes("일시정지")||cmd.includes("잠깐멈춰")){pauseSet();setVoiceCommandStatus(`음성 명령: ${text}`);return;}
  if(cmd.includes("세트종료")){finishCurrentSet();setVoiceCommandStatus(`음성 명령: ${text}`);return;}
  if(cmd.includes("세션종료")||cmd.includes("운동끝")){endSession();setVoiceCommandStatus(`음성 명령: ${text}`);return;}
  if(cmd.includes("음성명령중지")||cmd.includes("마이크중지")||cmd.includes("마이크꺼")||cmd.includes("음성중지")){
    stopVoiceCommandsInternal();setVoiceCommandStatus(`음성 명령: ${text}`);return;
  }
}
function stopVoiceCommandsInternal(){
  if(speechRestartTimer){clearTimeout(speechRestartTimer);speechRestartTimer=null;}
  if(speechRecognition){try{speechRecognition.onend=null;speechRecognition.stop();}catch(_){}}
  voiceCommandEnabled=false;
  setVoiceCommandStatus("음성 명령: 꺼짐");
}
function startVoiceCommandsInternal(){
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR){setVoiceCommandStatus("음성 명령: 이 브라우저는 음성 인식을 지원하지 않습니다.");return;}
  speechRecognition=new SR();
  speechRecognition.lang="ko-KR";
  speechRecognition.continuous=false; // Chrome에서 continuous=true는 TTS와 충돌 — false로 onend 재시작 방식 사용
  speechRecognition.interimResults=false;
  speechRecognition.maxAlternatives=1;
  speechRecognition.onresult=(event)=>{
    const latest=event.results[event.results.length-1];
    if(!latest?.isFinal)return;
    handleVoiceCommand(latest[0]?.transcript||"");
  };
  speechRecognition.onerror=(e)=>{
    if(e.error==="not-allowed"){
      setVoiceCommandStatus("음성 명령: 마이크 권한이 없습니다. 브라우저 설정에서 허용해주세요.");
      voiceCommandEnabled=false;return;
    }
    // no-speech, aborted 등은 재시작
    if(voiceCommandEnabled){
      speechRestartTimer=setTimeout(()=>{
        try{speechRecognition.start();setVoiceCommandStatus("음성 명령: 듣는 중");}catch(_){}
      },500);
    }
  };
  speechRecognition.onend=()=>{
    if(!voiceCommandEnabled)return;
    // TTS 발화 중이면 끝날 때까지 잠깐 기다렸다가 재시작
    const delay=window.speechSynthesis?.speaking?600:300;
    speechRestartTimer=setTimeout(()=>{
      try{speechRecognition.start();setVoiceCommandStatus("음성 명령: 듣는 중");}
      catch(_){}
    },delay);
  };
  try{
    speechRecognition.start();
    voiceCommandEnabled=true;
    setVoiceCommandStatus("음성 명령: 듣는 중");
  }catch(e){
    setVoiceCommandStatus(`음성 명령: 시작 실패 — ${e.message||e}`);
  }
}
function toggleVoiceCommands(){
  if(voiceCommandEnabled){stopVoiceCommandsInternal();return;}
  startVoiceCommandsInternal();
}

// countOn="down_to_up": 하단 도달 후 상단 도달 시 카운트
// countOn="up_to_down": 상단 도달 후 하단 복귀 시 카운트
function updateRep(inUp,inDown,upLbl,downLbl,score,issue,countOn,issueList){
  if(countOn===undefined)countOn="down_to_up";
  const now=Date.now();
  if(repLock>0){repLock--;return;}
  if(inDown){
    if(repCycleAnchor)captureRepSample(score,issueList);
    stableDown++;stableUp=0;stateText.textContent=downLbl;
    if(stableDown>=STABLE){
      if(countOn==="up_to_down"&&phase==="up"&&now-lastTransitionAt>200){
        const repResult=finalizeRepCycle(score,issue,issueList);
        repLock=6;phase="down";lastTransitionAt=now;
        if(repResult.invalid){setBanner("동작이 너무 빠르거나 불안정해 카운트하지 않았습니다.",repResult.issue,"warn");}
        else registerRep(repResult.score,repResult.issue,repResult.issueList);
      }else if((phase==="idle"||phase==="up")&&now-lastTransitionAt>120){
        phase="down";lastTransitionAt=now;
        if(countOn==="down_to_up")startRepCycle("down",score,issueList);
      }
    }
  }else if(inUp){
    if(repCycleAnchor)captureRepSample(score,issueList);
    stableUp++;stableDown=0;stateText.textContent=upLbl;
    if(stableUp>=STABLE){
      if(countOn==="down_to_up"&&phase==="down"&&now-lastTransitionAt>200){
        const repResult=finalizeRepCycle(score,issue,issueList);
        repLock=6;phase="up";lastTransitionAt=now;
        if(repResult.invalid){setBanner("동작이 너무 빠르거나 불안정해 카운트하지 않았습니다.",repResult.issue,"warn");}
        else registerRep(repResult.score,repResult.issue,repResult.issueList);
      }else if((phase==="idle"||phase==="down")&&now-lastTransitionAt>120){
        phase="up";lastTransitionAt=now;
        if(countOn==="up_to_down")startRepCycle("up",score,issueList);
      }
    }
  }else{
    stableUp=Math.max(0,stableUp-1);stableDown=Math.max(0,stableDown-1);
    stateText.textContent="MID";
  }
}
function updateRepPullup(atTop,atBottom,score,issue,issueList){
  const now=Date.now();
  if(repLock>0){repLock--;return;}
  if(atTop){
    if(repCycleAnchor)captureRepSample(score,issueList);
    stableUp++;stableDown=0;stateText.textContent="TOP";
    if(stableUp>=STABLE&&(phase==="down"||phase==="idle")&&now-lastTransitionAt>120){
      phase="up";lastTransitionAt=now;
      startRepCycle("up",score,issueList);
    }
  }else if(atBottom){
    if(repCycleAnchor)captureRepSample(score,issueList);
    stableDown++;stableUp=0;stateText.textContent="BOTTOM";
    if(stableDown>=STABLE){
      if(phase==="up"&&now-lastTransitionAt>200){
        const repResult=finalizeRepCycle(score,issue,issueList);
        repLock=6;phase="down";lastTransitionAt=now;
        if(repResult.invalid){setBanner("동작이 너무 빠르거나 불안정해 카운트하지 않았습니다.",repResult.issue,"warn");}
        else registerRep(repResult.score,repResult.issue,repResult.issueList);
      }
      else if(phase==="idle"&&now-lastTransitionAt>120){phase="down";lastTransitionAt=now;}
    }
  }else{stableUp=Math.max(0,stableUp-1);stableDown=Math.max(0,stableDown-1);stateText.textContent="MID";}
}

// ── Set flow ──────────────────────────────────────────────────────────────────
function startSet(){
  if(!cameraStarted){setStatus("대기 중","먼저 카메라를 시작하세요.","카메라가 켜진 뒤 세트 시작이 가능합니다.");return;}
  if(setActive&&!paused)return;
  // blocked 시 경고만 하고 시작은 허용 — 세트 진행 중처럼 관절 인식이 약해도 계속
  if(measurementReadiness.level==="blocked"){
    setBanner("관절 인식이 약합니다. 카메라 구도를 맞춰주세요.",measurementReadiness.reason,"warn");
  }
  targetReps=Math.max(1,Number(targetInput.value||{{ meta.target }}));
  totalSets=Math.max(1,Number(setsInput.value||{{ meta.sets }}));
  if(!sessionId){sessionId=newSessionId();sessionStartedAt=Date.now();}
  if(paused){paused=false;setActive=true;trackingText.textContent="LIVE";statusChip.className="status-chip live";statusChip.textContent="세트 진행";speak("세트를 다시 시작합니다. 자세를 유지하고 진행하세요.",true);return;}
  if(currentSet>=totalSets&&currentSet>0){
    // 이전 세션 완료 상태 — 자동으로 새 세션으로 리셋 후 시작
    currentSet=0;totalSets=0;allSetResults=[];sessionHistory=[];
    sessionId=newSessionId();sessionStartedAt=Date.now();
    hasUnsavedChanges=false;lastSavedSignature="";
    resetRepCounters();resetSmoothing();qualityStableFrames=0;
    summaryBox.classList.remove("show");setSummary.classList.remove("show");sessionScorePanel.classList.remove("show");
  }
  currentSet++;setActive=true;paused=false;resetRepCounters();
  setStartedAt=Date.now();lastTransitionAt=Date.now();qualityStableFrames=0;liveScore=null;stateText.textContent="READY";
  lastNoDetectSpoken=0;resetRepCycle();renderEmgOnlyFeedbacks();updateHud();
  summaryBox.classList.remove("show");setSummary.classList.remove("show");sessionScorePanel.classList.remove("show");
  trackingText.textContent="LIVE";statusChip.className="status-chip live";statusChip.textContent="세트 진행";
  feedbackMain.textContent=`${currentSet}세트 시작!`;feedbackSub.textContent=measurementReadiness.level==="warn"?"주의 상태에서 시작합니다. 카메라 상태를 함께 확인하세요.":"자세를 잡고 운동을 시작하세요.";
  speak(`${currentSet}세트 시작. 준비 자세를 잡고 첫 동작을 시작하세요. 횟수와 자세는 음성으로 안내합니다.`,true);
}
function pauseSet(){
  if(!setActive)return;paused=true;setActive=false;trackingText.textContent="PAUSE";
  setStatus("일시정지","세트가 일시정지되었습니다.","다시 시작을 누르면 이어서 진행합니다.","warn");speak("세트를 일시정지합니다.",true);
}

function finishSet(){
  setActive=false;paused=false;phase="idle";stableUp=0;stableDown=0;repLock=0;resetRepCycle();
  const avgScore=repScores.length?Math.round(repScores.reduce((a,b)=>a+b,0)/repScores.length):0;
  const grade=scoreToGrade(avgScore);
  const issues=topIssues();
  const setResult={exercise:EXERCISE_KEY,exercise_kor:"{{ exercise_kor }}",
    set_no:currentSet,target_reps:targetReps,total_reps:totalCount,
    good_reps:goodCount,avg_score:avgScore,grade,issues,rep_scores:[...repScores],
    issue_counts:{...issueCounter},rep_issues:[...repIssues],
    set_duration_sec:Math.max(1,Math.round((Date.now()-setStartedAt)/1000))};
  sessionHistory.push(setResult);
  allSetResults.push(setResult);
  hasUnsavedChanges=true;
  saveLocalBackup();

  // 세트 요약 카드 업데이트
  updateSetSummaryUI();

  const done=currentSet>=totalSets;
  trackingText.textContent=done?"DONE":"REST";

  // 세트 요약 텍스트
  summaryTitle.textContent=`${currentSet}세트 완료 · 종합점수 ${avgScore}점`;
  let t=`목표 ${targetReps}회 중 ${totalCount}회 수행. 좋은 동작 ${goodCount}회. 세트별 종합점수 ${avgScore}점 (${grade}등급).`;
  if(issues.length)t+=` 보완: ${issues.slice(0,2).join(", ")}.`;
  else t+=` 자세 균형이 좋았습니다!`;
  summaryText.textContent=t;summaryBox.classList.add("show");
  setSummary.classList.add("show");

  if(done){
    showSessionScore();
    setStatus("완료","전체 세트 완료!","기록 저장을 눌러 CSV로 남길 수 있습니다.");
    const totalAvg=Math.round(allSetResults.reduce((s,r)=>s+r.avg_score,0)/allSetResults.length);
    speak(`운동 완료. 총 ${allSetResults.reduce((s,r)=>s+r.total_reps,0)}회, 세션 점수 ${totalAvg}점입니다.`,true);
    saveSession(true);
  }else{
    setStatus("세트 종료",`${currentSet}세트 완료 (${grade}등급 · ${avgScore}점)`,"다음 세트를 시작하려면 세트 시작을 누르세요.","rest");
    speak(`${currentSet}세트 완료. ${korNum(totalCount)}회 수행했습니다. ${issues.length?issues[0]+"를 다음 세트에서 보완하세요.":"좋은 자세였습니다. 다음 세트를 준비하세요."}`,true);
  }
}

function updateSetSummaryUI(){
  setSummaryTitle.textContent=`세트별 종합점수 (${allSetResults.length}세트)`;
  setSummaryRows.innerHTML=allSetResults.map(r=>`
    <div class="ss-row">
      <span>${r.set_no}세트</span>
      <span>종합 ${r.avg_score}점</span>
      <span>${r.total_reps}/${r.target_reps}회</span>
      <span class="${gradeCls(r.grade)}">${r.grade}</span>
    </div>`).join("");
  setSummary.classList.add("show");
}

function showSessionScore(){
  const n=allSetResults.length;
  if(!n)return;
  const totalAvg=Math.round(allSetResults.reduce((s,r)=>s+r.avg_score,0)/n);
  const totalReps=allSetResults.reduce((s,r)=>s+r.total_reps,0);
  const totalGood=allSetResults.reduce((s,r)=>s+r.good_reps,0);
  const totalTarget=allSetResults.reduce((s,r)=>s+r.target_reps,0);
  const achieve=Math.round(totalReps/totalTarget*100);
  const grade=scoreToGrade(totalAvg);

  sspGrade.textContent=grade;
  sspGrade.style.color=gradeColor(grade);
  sspScore.textContent=`총점 ${totalAvg}점 · 달성률 ${achieve}%`;
  sspSub.textContent=`총 ${n}세트 · ${totalReps}회 수행 · 좋은 동작 ${totalGood}회`;

  // 세트 히스토리 테이블
  setHistoryTable.innerHTML=`<tr><th>세트</th><th>횟수</th><th>점수</th><th>등급</th></tr>`+
    allSetResults.map(r=>`<tr>
      <td>${r.set_no}</td>
      <td>${r.total_reps}/${r.target_reps}</td>
      <td>${r.avg_score}</td>
      <td class="${gradeCls(r.grade)}">${r.grade}</td>
    </tr>`).join("");

  sessionScorePanel.classList.add("show");
}

async function saveSession(auto=false){
  if(!sessionHistory.length){saveStatus.textContent="저장할 기록이 없습니다.";return false;}
  const signature=sessionSignature();
  if(signature===lastSavedSignature&&!hasUnsavedChanges){
    saveStatus.textContent="이미 최신 기록이 저장되어 있습니다.";return true;
  }
  try{
    saveStatus.textContent=auto?"자동 저장 중...":"저장 중...";
    const payload={
      created_at:new Date().toISOString(),
      session_id:sessionId||newSessionId(),
      save_mode:auto?"auto":"manual",
      exercise_key:EXERCISE_KEY,
      exercise_kor:"{{ exercise_kor }}",
      session_summary:{
        total_sets:allSetResults.length,
        total_reps:allSetResults.reduce((s,r)=>s+r.total_reps,0),
        total_good_reps:allSetResults.reduce((s,r)=>s+r.good_reps,0),
        avg_score:allSetResults.length?Math.round(allSetResults.reduce((s,r)=>s+r.avg_score,0)/allSetResults.length):0,
        session_duration_sec:sessionStartedAt?Math.max(1,Math.round((Date.now()-sessionStartedAt)/1000)):0
      },
      sets:sessionHistory
    };
    const res=await fetch("/api/save-session",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify(payload)});
    // Flask가 500 에러를 HTML로 반환하면 res.json()이 파싱 오류를 던짐
    const text=await res.text();
    let data;
    try{data=JSON.parse(text);}
    catch{throw new Error(`서버 응답 오류 (HTTP ${res.status}) — ${text.slice(0,120)}`);}
    if(!res.ok)throw new Error(data.message||`HTTP ${res.status}`);
    lastSavedSignature=signature;
    hasUnsavedChanges=false;
    clearLocalBackup();
    saveStatus.textContent=data.message||"저장 완료";
    return true;
  }catch(err){
    console.error("[saveSession]",err);
    saveStatus.textContent=`저장 실패: ${err.message||"알 수 없는 오류"}`;
    saveLocalBackup();
    return false;
  }
}
function finishCurrentSet(){
  if(!setActive){setStatus("대기 중","진행 중인 세트가 없습니다.","카메라를 켜고 세트를 시작하세요.");return;}
  finishSet();
}
async function endSession(){
  if(setActive&&totalCount>0)finishSet();
  if(hasUnsavedChanges&&sessionHistory.length){
    const saved=await saveSession(true);
    if(!saved){
      setStatus("저장 실패","기록 저장에 실패해 세션을 유지합니다.","네트워크나 서버 상태를 확인한 뒤 다시 저장하세요.","warn");
      return;
    }
  }
  setActive=false;paused=false;currentSet=0;totalSets=0;allSetResults=[];sessionHistory=[];resetRepCounters();
  sessionId=null;sessionStartedAt=0;setStartedAt=0;hasUnsavedChanges=false;lastSavedSignature="";qualityStableFrames=0;resetSmoothing();
  summaryBox.classList.remove("show");setSummary.classList.remove("show");sessionScorePanel.classList.remove("show");
  trackingText.textContent=cameraStarted?"IDLE":"OFF";
  setStatus("종료","세션을 종료했습니다.","다시 시작하려면 카메라를 켜고 세트를 시작하세요.");speak("세션 종료.",true);updateHud();
  clearLocalBackup();
  saveStatus.textContent="세션이 종료되었습니다. 새 세션은 새로 저장됩니다.";
  setTimeout(showEmgReport, 400);
}

// ══════════════════════════════════════════════════════════════════════════════
// Form evaluator v4  — 피드백 세분화 + 반동감지 + 좌우비대칭 강화
// 반환: {valid, feedbacks, inUp, inDown, upLabel, downLabel, score, countOn, topIssue, allIssues}
// feedbacks: bad(0) > warn(1) > good(2) 정렬
// ══════════════════════════════════════════════════════════════════════════════
function evaluateForm(lm){
  const SEV={bad:0,warn:1,good:2};
  const fbs=[];
  const bad =(msg,sub,iss)=>fbs.push({msg,sub:sub||"",severity:"bad", issue:iss||null});
  const warn=(msg,sub,iss)=>fbs.push({msg,sub:sub||"",severity:"warn",issue:iss||null});
  const good=(msg,sub)    =>fbs.push({msg,sub:sub||"",severity:"good",issue:null});
  const sort=()=>fbs.sort((a,b)=>{
    const sevDiff=SEV[a.severity]-SEV[b.severity];
    if(sevDiff!==0)return sevDiff;
    return feedbackUrgency(b)-feedbackUrgency(a);
  });

  const side=chooseSide(lm);
  const S=side==="left"
    ?{sh:11,el:13,wr:15,hp:23,kn:25,an:27,oSh:12,oEl:14,oWr:16,oHp:24,oKn:26,oAn:28}
    :{sh:12,el:14,wr:16,hp:24,kn:26,an:28,oSh:11,oEl:13,oWr:15,oHp:23,oKn:25,oAn:27};

  const sh=point(lm,S.sh),el=point(lm,S.el),wr=point(lm,S.wr);
  const hp=point(lm,S.hp),kn=point(lm,S.kn),an=point(lm,S.an);
  const oSh=point(lm,S.oSh),oEl=point(lm,S.oEl),oWr=point(lm,S.oWr);
  const oHp=point(lm,S.oHp),oKn=point(lm,S.oKn),oAn=point(lm,S.oAn),nose=point(lm,0);

  const avgShY=avg([sh?.y,oSh?.y]),avgWrY=avg([wr?.y,oWr?.y]);
  const hipDiff=(hp&&oHp)?Math.abs(hp.y-oHp.y):0;
  const wrDiff=(wr&&oWr)?Math.abs(wr.y-oWr.y):0;
  const elDiff=(el&&oEl)?Math.abs(el.y-oEl.y):0;
  const rawKneeAng=angle(hp,kn,an),rawElbowAng=angle(sh,el,wr);
  const rawHipAng=angle(sh,hp,kn),rawBodyAng=angle(sh,hp,an);
  const rawTrunk=trunkLean(sh,hp);

  // 정면 양팔 평균 팔꿈치 각도 (덤벨컬·숄더프레스 정면 판정용)
  const rawElbowAngL=angle(point(lm,11),point(lm,13),point(lm,15));
  const rawElbowAngR=angle(point(lm,12),point(lm,14),point(lm,16));
  const rawElbowAngBoth=avg([rawElbowAngL,rawElbowAngR]);
  // 정면 양쪽 무릎 평균 각도 (스쿼트 정면 판정용)
  const rawKneeAngL=angle(point(lm,23),point(lm,25),point(lm,27));
  const rawKneeAngR=angle(point(lm,24),point(lm,26),point(lm,28));
  const rawKneeAngBoth=avg([rawKneeAngL,rawKneeAngR]);
  // 정면 손목Y 평균 (덤벨컬에서 손목이 팔꿈치보다 위로 올라오는지 판정)
  const avgElY=avg([point(lm,13)?.y,point(lm,14)?.y]);
  const avgWrYBoth=avg([point(lm,15)?.y,point(lm,16)?.y]);

  smoothKneeAng=ema(smoothKneeAng,rawKneeAng);
  smoothHipAng=ema(smoothHipAng,rawHipAng);
  smoothElbowAng=ema(smoothElbowAng,rawElbowAng);
  smoothBodyAng=ema(smoothBodyAng,rawBodyAng);
  smoothTrunk=ema(smoothTrunk,rawTrunk);
  const kneeAng=smoothKneeAng,elbowAng=smoothElbowAng;
  const hipAng=smoothHipAng,bodyAng=smoothBodyAng;
  const trunk=smoothTrunk;

  let inUp=false,inDown=false,upLabel="UP",downLabel="DOWN",score=100,countOn="down_to_up";

  // ══════════════════════════════════════════════════════════════════════════
  // SQUAT
  // ══════════════════════════════════════════════════════════════════════════
  if(EXERCISE_KEY==="squat"){
    // 정면/측면 자동 판별: 양쪽 어깨가 모두 보이면 정면으로 간주
    const squatFrontal=rawKneeAngBoth!=null&&(point(lm,11)?.visibility||0)>0.4&&(point(lm,12)?.visibility||0)>0.4;
    const effectiveKneeAng=squatFrontal?ema(smoothKneeAng,rawKneeAngBoth):kneeAng;
    if(!kn&&!point(lm,25)||!hp&&!point(lm,23))return{valid:false,main:"무릎과 골반이 보이게 해주세요.",sub:""};
    if(effectiveKneeAng==null)return{valid:false,main:"관절 인식 중.",sub:""};
    const squatThr=getThresholds("down_to_up_low_angle");
    const eKA=effectiveKneeAng;
    inDown=eKA<(squatThr?.down??112);inUp=eKA>(squatThr?.up??150);countOn="down_to_up";
    const prevSquatKneeAng=prevKneeAng;
    const kSpd=angSpeed(eKA,prevSquatKneeAng);prevKneeAng=eKA;
    const sub=`무릎 ${Math.round(eKA)}°${squatFrontal?" (정면)":""}`;
    const squatDescending=prevSquatKneeAng!=null&&eKA<prevSquatKneeAng-1.5;
    const squatAscending=prevSquatKneeAng!=null&&eKA>prevSquatKneeAng+1.5;
    const squatStatic=prevSquatKneeAng!=null&&Math.abs(eKA-prevSquatKneeAng)<1.2;

    if(phase==="idle"&&squatStatic&&eKA>148){
      good("준비 자세 확인 중입니다.",sub);
      sort();
      return{valid:true,feedbacks:fbs,inUp,inDown,upLabel,downLabel,score,countOn,topIssue:fbs[0]?.issue||null,allIssues:[]};
    }

    // 1) 깊이
    if(eKA<88){good("완벽한 깊이입니다!",sub);}
    else if(eKA<108){good("충분한 깊이입니다.",sub);}
    else if(squatDescending&&eKA>152){score-=20;bad("조금 더 앉아주세요 (목표 95~100°)",sub,"깊이 매우 부족");maybeSpeak("깊이 매우 부족","엉덩이를 조금 더 내려주세요.");}
    else if(squatDescending&&eKA>124){score-=10;warn("조금만 더 앉으면 더 좋습니다",sub,"깊이 부족");maybeSpeak("깊이 부족","조금만 더 앉아주세요.");}
    else if(squatAscending){good("좋습니다. 올라오는 구간입니다.",sub);}
    else{warn("스쿼트 깊이를 확인 중입니다.",sub);}

    // 2) 무릎 내측 붕괴 — 정면/측면 모두 동작
    const lKn=point(lm,25),rKn=point(lm,26),lAn=point(lm,27),rAn=point(lm,28);
    if(lKn&&rKn&&lAn&&rAn){
      const kW=Math.abs(lKn.x-rKn.x),aW=Math.abs(lAn.x-rAn.x);
      if(aW>0.02&&kW/aW<0.65){score-=22;bad("무릎이 심하게 안쪽으로 무너졌어요!","발 바깥으로 무릎을 강하게 밀어주세요.","무릎 심한 내측 붕괴");maybeSpeak("무릎 심한 내측 붕괴","무릎이 심하게 안으로 모이고 있습니다.");}
      else if(aW>0.02&&kW/aW<0.80){score-=14;bad("무릎이 안쪽으로 쏠려요","발 바깥 방향으로 무릎을 밀어주세요.","무릎 내측 붕괴");maybeSpeak("무릎 내측 붕괴","무릎을 발 방향으로 밀어주세요.");}
    }

    // 3) 무릎 앞쏠림 — 측면 구도에서만 유효
    if(!squatFrontal&&kn&&an){
      const f=(side==="left")?(an.x-kn.x):(kn.x-an.x);
      if(f>0.10){score-=15;bad("무릎이 발끝을 크게 넘었어요!","엉덩이를 훨씬 뒤로 빼주세요.","무릎 과도한 앞쏠림");maybeSpeak("무릎 과도한 앞쏠림","엉덩이를 뒤로 빼주세요.");}
      else if(f>0.06){score-=8;warn("엉덩이를 좀 더 뒤로 빼주세요","무릎이 발끝을 약간 넘었습니다.","무릎 앞쏠림");maybeSpeak("무릎 앞쏠림","엉덩이를 살짝 더 뒤로 빼주세요.");}
    }

    // 4) 상체 기울기
    if(trunk!=null){
      if(trunk>45){score-=15;bad("상체가 너무 앞으로 기울었어요",`기울기 ${Math.round(trunk)}°`,"상체 과도 기울기");maybeSpeak("상체 과도 기울기","가슴을 들고 상체를 세워주세요.");}
      else if(trunk>30){score-=8;warn("상체를 더 세워주세요",`기울기 ${Math.round(trunk)}°`,"상체 기울기");maybeSpeak("상체 기울기","상체를 조금 더 세워주세요.");}
    }

    // 5) 골반 비대칭 (정면에서 더 잘 보임)
    if(hipDiff>0.06){score-=12;bad("골반이 심하게 한쪽으로 기울었어요","좌우 균형을 맞추세요.","골반 심한 비대칭");maybeSpeak("골반 심한 비대칭","골반 좌우 균형을 맞춰주세요.");}
    else if(hipDiff>0.035){score-=6;warn("골반이 살짝 기울었어요","좌우 균형을 의식하세요.","골반 비대칭");}

    // 6) 반동
    if(kSpd>30&&phase==="up"){score-=10;warn("반동 없이 천천히 올라오세요","천천히 컨트롤하며 일어서세요.","반동 사용");maybeSpeak("반동 사용","반동을 줄이고 천천히 올라오세요.");}
  }

  // ══════════════════════════════════════════════════════════════════════════
  // PUSH-UP
  // ══════════════════════════════════════════════════════════════════════════
  else if(EXERCISE_KEY==="pushup"){
    if(!sh||!el||!wr||!hp||!an)return{valid:false,main:"측면에서 어깨·골반·발이 모두 보이게 해주세요.",sub:""};
    if(elbowAng==null)return{valid:false,main:"관절 인식 중. 측면으로 조정해주세요.",sub:""};
    const pushupThr=getThresholds("down_to_up_low_angle");
    inDown=elbowAng<(pushupThr?.down??96);inUp=elbowAng>(pushupThr?.up??150);countOn="down_to_up";
    const eSpd=angSpeed(elbowAng,prevElbowAng);prevElbowAng=elbowAng;
    const sub=`팔꿈치 ${Math.round(elbowAng)}°`;

    // 1) 엉덩이 처짐/들림 (좌표 기반 hipSag) — 세 단계
    if(sh&&an&&hp){
      const expY=sh.y+(an.y-sh.y)*0.5,sag=hp.y-expY;
      if(!kn){score-=8;warn("무릎이 프레임에 함께 보이게 해주세요","허벅지와 골반 정렬이 잘 보여야 하체 판정이 안정적입니다.","하체 관절 인식 부족");}
      if(sag>0.07){score-=25;bad("엉덩이가 심하게 처졌어요!","복근과 엉덩이에 강하게 힘 주세요.","엉덩이 심한 처짐");maybeSpeak("엉덩이 심한 처짐","복근에 강하게 힘을 주세요.");}
      else if(sag>0.04){score-=15;bad("엉덩이를 올려주세요","몸통이 처지고 있습니다.","엉덩이 처짐");maybeSpeak("엉덩이 처짐","복근에 힘을 주세요.");}
      else if(sag<-0.08){score-=15;bad("엉덩이가 너무 높이 들렸어요","골반을 내려 일직선을 만드세요.","엉덩이 심한 들림");maybeSpeak("엉덩이 심한 들림","엉덩이를 많이 내려주세요.");}
      else if(sag<-0.04){score-=8;warn("엉덩이를 약간 내려주세요","몸통을 일직선으로 맞추세요.","엉덩이 들림");maybeSpeak("엉덩이 들림","엉덩이를 살짝 내려주세요.");}
      else if(inDown){good("완벽한 정렬 + 충분한 깊이!",sub);}
      else{good("몸통 정렬 완벽!",sub);}
    }

    // 2) 깊이 — 두 단계
    if(elbowAng>130&&elbowAng<155){score-=15;bad("가슴을 훨씬 더 내리세요",`팔꿈치 ${Math.round(elbowAng)}°, 목표 90° 이하`,"깊이 매우 부족");maybeSpeak("깊이 매우 부족","가슴을 바닥 가까이 내려보세요.");}
    else if(elbowAng>110&&elbowAng<=130){score-=8;warn("조금 더 내려가주세요",`팔꿈치 ${Math.round(elbowAng)}°`,"깊이 부족");maybeSpeak("깊이 부족","조금만 더 내려가세요.");}

    // 3) 팔꿈치 벌어짐 — 두 단계
    if(sh&&el&&oSh){
      const ef=Math.abs(el.x-sh.x),sw=Math.abs(sh.x-oSh.x);
      if(sw>0.01&&ef/sw>0.75){score-=12;bad("팔꿈치가 너무 많이 벌어졌어요","45도 이내로 좁혀주세요.","팔꿈치 과도한 벌어짐");maybeSpeak("팔꿈치 과도한 벌어짐","팔꿈치를 몸통 가까이 당기세요.");}
      else if(sw>0.01&&ef/sw>0.55){score-=6;warn("팔꿈치가 살짝 벌어졌어요","몸통 가까이 당겨주세요.","팔꿈치 벌어짐");maybeSpeak("팔꿈치 벌어짐","팔꿈치를 살짝 안으로 당기세요.");}
    }

    // 4) 반동 감지
    if(eSpd>35&&phase==="up"){score-=8;warn("반동 없이 밀어올리세요","근육으로 천천히 올리세요.","반동 사용");maybeSpeak("반동 사용","반동을 줄이고 근육으로 올리세요.");}

    // 5) 머리 위치 (고개 숙임)
    if(nose&&sh&&nose.y>sh.y+0.05){score-=6;warn("고개를 들어 시선을 앞으로","목을 중립으로 유지하세요.","고개 숙임");maybeSpeak("고개 숙임","고개를 들어 목을 중립으로 하세요.");}
  }

  // ══════════════════════════════════════════════════════════════════════════
  // LUNGE
  // ══════════════════════════════════════════════════════════════════════════
  else if(EXERCISE_KEY==="lunge"){
    if(!sh||!hp||!kn||!an)return{valid:false,main:"측면에서 앞다리 각도가 보이게 해주세요.",sub:""};
    if(kneeAng==null)return{valid:false,main:"관절 인식 중. 측면으로 조정해주세요.",sub:""};
    const lungeThr=getThresholds("down_to_up_low_angle");
    inDown=kneeAng<(lungeThr?.down??112);inUp=kneeAng>(lungeThr?.up??148);countOn="down_to_up";
    const sub=`앞무릎 ${Math.round(kneeAng)}° · 기울기 ${trunk!=null?Math.round(trunk)+"°":"-"}`;

    // 1) 깊이
    if(kneeAng<88){good("완벽한 런지 깊이!",sub);}
    else if(kneeAng<108){good("좋은 깊이입니다.",sub);}
    else if(kneeAng>142){score-=18;bad("조금 더 내려가세요 (목표 95~100°)",sub,"깊이 매우 부족");maybeSpeak("깊이 매우 부족","뒷무릎을 조금 더 내려주세요.");}
    else if(kneeAng>118){score-=10;warn("한 단계만 더 내려가면 좋습니다",sub,"깊이 부족");maybeSpeak("깊이 부족","조금만 더 내려가주세요.");}
    else{warn("좋은 깊이입니다.",sub);}

    // 2) 앞무릎 앞쏠림
    if(kn&&an){
      const f=(side==="left")?(an.x-kn.x):(kn.x-an.x);
      if(f>0.10){score-=15;bad("앞무릎이 발끝을 많이 넘어갔어요!","보폭을 더 넓히세요.","무릎 과도한 앞쏠림");maybeSpeak("무릎 과도한 앞쏠림","보폭을 넓혀주세요.");}
      else if(f>0.06){score-=8;warn("앞무릎이 발끝을 살짝 넘었어요","발목 위에 무릎을 유지하세요.","무릎 앞쏠림");maybeSpeak("무릎 앞쏠림","무릎이 발끝을 넘지 않게 해주세요.");}
    }

    // 3) 상체 기울기 — 두 단계
    if(trunk!=null){
      if(trunk>30){score-=14;bad("상체가 많이 기울었어요",`기울기 ${Math.round(trunk)}°`,"상체 과도 기울기");maybeSpeak("상체 과도 기울기","상체를 세워주세요.");}
      else if(trunk>18){score-=7;warn("상체를 조금 더 세워주세요",`기울기 ${Math.round(trunk)}°`,"상체 기울기");maybeSpeak("상체 기울기","상체를 수직으로 세워주세요.");}
    }

    // 4) 골반 비대칭
    if(hipDiff>0.06){score-=12;bad("골반이 심하게 기울었어요","좌우 균형을 맞추세요.","골반 심한 비대칭");maybeSpeak("골반 심한 비대칭","골반 균형을 맞춰주세요.");}
    else if(hipDiff>0.04){score-=6;warn("골반이 약간 기울었어요","좌우를 균등하게 맞추세요.","골반 비대칭");}

    // 5) 무릎 내측 붕괴
    if(kn&&an&&oKn&&oAn){
      const kW=Math.abs(lm[25].x-lm[26].x),aW=Math.abs(lm[27].x-lm[28].x);
      if(aW>0.02&&kW/aW<0.70){score-=14;bad("앞무릎이 안쪽으로 무너지고 있어요","무릎을 발 방향으로 유지하세요.","무릎 내측 붕괴");maybeSpeak("무릎 내측 붕괴","무릎이 안으로 모이지 않게 해주세요.");}
    }
  }

  // ══════════════════════════════════════════════════════════════════════════
  // PULL-UP
  // ══════════════════════════════════════════════════════════════════════════
  else if(EXERCISE_KEY==="pullup"){
    if(!sh||!el||!wr||!nose)return{valid:false,main:"얼굴과 손목이 함께 보이게 해주세요.",sub:""};
    if(elbowAng==null)return{valid:false,main:"관절 인식 중.",sub:""};
    const pullupThr=getThresholds("up_to_down_high_angle");
    const atTop=nose.y<((avgWrY||wr.y)+0.025)&&elbowAng<(pullupThr?.down??124),atBottom=elbowAng>(pullupThr?.up??150);
    const eSpd=angSpeed(elbowAng,prevElbowAng);prevElbowAng=elbowAng;
    const sub=`팔꿈치 ${Math.round(elbowAng)}°`;

    // 1) 상단 도달 품질
    if(atTop&&elbowAng<90){good("완벽! 완전히 당겨올렸어요!",sub);}
    else if(atTop){good("상단 도달!",sub);}
    else if(elbowAng<130){score-=12;warn("턱을 손 위로 끌어올리세요",sub,"상단 미달");maybeSpeak("상단 미달","턱을 손 높이 위로 끌어올리세요.");}

    // 2) 완전 신전
    if(!atBottom&&elbowAng<170&&phase==="up"){score-=10;warn("팔을 완전히 펴고 당기세요","완전 신전 후 다음 동작을 하세요.","완전 신전 미달");maybeSpeak("완전 신전 미달","팔을 완전히 펴주세요.");}

    // 3) 양팔 비대칭 (팔꿈치 높이)
    if(elDiff>0.08){score-=12;bad("양팔이 비대칭으로 당겨지고 있어요","양쪽을 균등하게 당기세요.","양팔 비대칭");maybeSpeak("양팔 비대칭","양팔을 균등하게 당기세요.");}
    else if(elDiff>0.05){score-=6;warn("양팔 균형을 맞춰주세요","좌우 같은 힘으로 당기세요.","양팔 경미한 비대칭");}

    // 4) 반동/킵핑 감지
    if(eSpd>40&&phase==="down"){score-=10;warn("반동(킵핑)을 줄이세요","천천히 내려오며 컨트롤하세요.","반동 킵핑");maybeSpeak("반동 킵핑","반동 없이 천천히 내려오세요.");}

    // 5) 어깨 들림 (상단에서)
    if(sh&&nose&&atTop&&sh.y<nose.y-0.1){score-=6;warn("어깨가 너무 들렸어요","승모근 힘을 빼고 광배근으로 당기세요.","어깨 들림");}

    sort();score=Math.max(45,Math.min(100,Math.round(score)));
    if(setActive){
      updateRepPullup(atTop,atBottom,score,fbs[0]?.issue||null,fbs.filter(f=>f.issue).map(f=>f.issue));
      setFeedbacks(fbs.length?fbs:[{msg:"Pull-up 진행 중",sub,severity:"good",issue:null}]);
      liveScore=score;updateHud();statusChip.className="status-chip live";statusChip.textContent="세트 진행";
    }else{setFeedbacks(fbs.length?fbs:[{msg:"Pull-up 자세를 잡아주세요",sub,severity:"good"}]);liveScore=score;updateHud();}
    stateText.textContent=atTop?"TOP":atBottom?"BOTTOM":"MID";
    return{valid:true,pullupHandled:true,score};
  }

  // ══════════════════════════════════════════════════════════════════════════
  // LEG RAISE
  // ══════════════════════════════════════════════════════════════════════════
  else if(EXERCISE_KEY==="legraise"){
    if(!sh||!hp||!kn||!an)return{valid:false,main:"측면에서 어깨·골반·발끝이 보이게 해주세요.",sub:""};
    if(hipAng==null||kneeAng==null)return{valid:false,main:"관절 인식 중. 측면으로 조정해주세요.",sub:""};
    const legraiseThr=getThresholds("down_to_up_low_angle");
    inUp=hipAng<(legraiseThr?.down??98);inDown=hipAng>(legraiseThr?.up??148);countOn="down_to_up";
    const hSpd=angSpeed(hipAng,prevHipAng);prevHipAng=hipAng;
    const sub=`골반 ${Math.round(hipAng)}° · 무릎 ${Math.round(kneeAng)}°`;

    // 1) 높이 — 세 단계
    if(hipAng<70){good("완벽! 수직에 가깝게 올라왔어요!",sub);}
    else if(inUp){good("충분한 높이입니다!",sub);}
    else if(hipAng>132){score-=20;bad("다리를 훨씬 높이 올려야 해요","수직 가까이까지 올리세요.","높이 매우 부족");maybeSpeak("높이 매우 부족","다리를 훨씬 높이 올려주세요.");}
    else if(hipAng>102){score-=10;warn("다리를 조금 더 높이 올리세요",`목표 각도 90° 전후 · ${sub}`,"높이 부족");maybeSpeak("높이 부족","조금만 더 높이 올려주세요.");}
    else{warn("높이가 조금 부족해요.",sub);}

    // 2) 무릎 굽힘 — 두 단계
    if(kneeAng<145){score-=18;bad("무릎을 완전히 펴서 올리세요",`무릎 ${Math.round(kneeAng)}°`,"무릎 심한 굽힘");maybeSpeak("무릎 심한 굽힘","다리를 쭉 펴주세요.");}
    else if(kneeAng<160){score-=8;warn("무릎이 조금 굽었어요",`무릎 ${Math.round(kneeAng)}°`,"무릎 굽힘");maybeSpeak("무릎 굽힘","무릎을 펴고 올리세요.");}

    // 3) 허리 과신전
    if(bodyAng!=null&&bodyAng<130){score-=12;bad("허리가 크게 들리고 있어요!","복근을 강하게 눌러주세요.","허리 과신전");maybeSpeak("허리 과신전","허리가 너무 들리고 있습니다.");}
    else if(bodyAng!=null&&bodyAng<150){score-=6;warn("허리가 살짝 들렸어요","복근에 힘을 유지하세요.","허리 경미한 과신전");}

    // 4) 반동 감지
    if(hSpd>35&&phase==="up"){score-=8;warn("반동 없이 복근으로 올리세요","천천히 컨트롤하며 올리세요.","반동 사용");maybeSpeak("반동 사용","반동을 줄이고 복근으로 올리세요.");}
  }

  // ══════════════════════════════════════════════════════════════════════════
  // SHOULDER PRESS
  // ══════════════════════════════════════════════════════════════════════════
  else if(EXERCISE_KEY==="shoulderpress"){
    if(!sh||!el||!wr||!oWr)return{valid:false,main:"정면에서 양어깨와 양손이 보이게 해주세요.",sub:""};
    // 정면 판별: 양쪽 어깨가 모두 보이면 양팔 평균 팔꿈치 각도 사용 (더 안정적)
    const spFrontal=(point(lm,11)?.visibility||0)>0.4&&(point(lm,12)?.visibility||0)>0.4&&rawElbowAngBoth!=null;
    const spElbowAng=spFrontal?ema(smoothElbowAng,rawElbowAngBoth):elbowAng;
    if(spElbowAng==null)return{valid:false,main:"관절 인식 중. 정면으로 조정해주세요.",sub:""};
    const shoulderThr=getThresholds("up_to_down_high_angle");
    // UP 145°, DOWN 115° — 여유 있게 판정
    inUp=spElbowAng>(shoulderThr?.up??145);inDown=spElbowAng<(shoulderThr?.down??115);countOn="up_to_down";
    const eSpd=angSpeed(spElbowAng,prevElbowAng);prevElbowAng=spElbowAng;
    const sub=`팔꿈치 ${Math.round(spElbowAng)}°${spFrontal?" (정면)":""} · 손 높이차 ${Math.round(wrDiff*100)}`;
    const forearmOffset=(sh&&el&&wr&&oSh&&oEl&&oWr)
      ?avg([Math.abs(wr.x-el.x),Math.abs(oWr.x-oEl.x)])
      :null;
    const wristOutside=(sh&&el&&wr&&oSh&&oEl&&oWr)
      ?(wr.x<el.x-0.03||oWr.x>oEl.x+0.03)
      :false;
    const elbowOutside=(sh&&el&&oSh&&oEl)
      ?(el.x<sh.x-0.04||oEl.x>oSh.x+0.04)
      :false;
    if(eSpd>52)invalidateRepCycle("속도가 너무 빨라 숄더프레스 판정 신뢰도가 낮습니다");

    // 1) 완전 신전 — 두 단계
    if(inUp&&spElbowAng>170){good("완벽! 완전히 밀어올렸습니다.",sub);}
    else if(inUp){good("팔을 끝까지 밀어올렸어요.",sub);}
    else if(spElbowAng>144){score-=16;bad("팔을 조금 더 펴서 밀어올리세요",`팔꿈치 ${Math.round(spElbowAng)}°`,"완전 신전 미달");maybeSpeak("완전 신전 미달","팔을 조금 더 펴주세요.");}
    else if(spElbowAng>124){score-=8;warn("상단에서 조금만 더 밀어올리세요",sub,"신전 부족");maybeSpeak("신전 부족","조금만 더 밀어올리세요.");}
    else{warn("내려오는 중...",sub);}

    // 2) 양팔 비대칭 — 두 단계 (카운트 무효화 없음)
    if(wrDiff>0.12){score-=12;bad("양손 높이가 크게 차이 나요",`높이차 ${Math.round(wrDiff*100)}`,"양팔 심한 비대칭");maybeSpeak("양팔 심한 비대칭","양쪽 팔의 높이를 맞추세요.");}
    else if(wrDiff>0.08){score-=6;warn("양손 높이를 맞춰주세요",`높이차 ${Math.round(wrDiff*100)}`,"양팔 비대칭");maybeSpeak("양팔 비대칭","양쪽을 동일한 높이로 올리세요.");}

    // 3) 손목/전완 정렬 — 점수만 감점, 카운트 무효화 없음
    if(forearmOffset!=null&&forearmOffset>0.10){score-=8;warn("손목 위치를 팔꿈치 위에 쌓아주세요","전완이 수직으로 향하게 유지하세요.","손목 전완 정렬 부족");maybeSpeak("손목 전완 정렬 부족","손목을 팔꿈치 위에 맞춰주세요.");}

    // 4) 손목 바깥 회전 — 정면에서 감지되면 안내만 (카운트 무효화 없음)
    if(wristOutside&&elbowOutside){
      score-=6;warn("손목 안쪽이 카메라를 향하게 해주세요","그립 방향만 조정해도 됩니다.","손목 바깥 회전");
    }

    // 5) 팔꿈치 간격 (하단에서) — 기준 완화
    if(inDown&&sh&&el&&oSh&&oEl){
      const ew=Math.abs(el.x-oEl.x),sw=Math.abs(sh.x-oSh.x);
      if(sw>0.01&&ew/sw<0.80){
        score-=12;bad("팔꿈치가 너무 모여 있어요","어깨보다 약간 바깥으로 벌려 바벨 경로를 확보하세요.","팔꿈치 과도한 모임");maybeSpeak("팔꿈치 과도한 모임","팔꿈치를 조금 더 벌려주세요.");
      }
      else if(sw>0.01&&ew/sw<0.92){
        score-=6;warn("팔꿈치를 어깨너비로 맞춰주세요","어깨너비 정도 벌리는 게 안정적입니다.","팔꿈치 모임");maybeSpeak("팔꿈치 모임","팔꿈치를 조금 더 벌려주세요.");
      }
      // 팔꿈치 벌어짐: 어깨 너비의 1.65배 이상일 때만 경고 (어느 정도 넓어도 괜찮음)
      if(sw>0.01&&ew/sw>1.65){score-=8;warn("팔꿈치를 너무 넓게 벌렸어요","어깨 너비에서 약간만 넓게 잡아주세요.","팔꿈치 과도한 벌어짐");maybeSpeak("팔꿈치 과도한 벌어짐","팔꿈치를 조금 좁혀주세요.");}
    }

    // 6) 허리 과신전
    if(trunk!=null&&trunk>25){score-=12;bad("허리를 너무 젖히고 있어요!",`복근에 힘 주고 허리를 세우세요. · 기울기 ${Math.round(trunk)}°`,"허리 심한 과신전");maybeSpeak("허리 심한 과신전","허리를 젖히지 마세요.");}
    else if(trunk!=null&&trunk>15){score-=6;warn("허리를 살짝 젖혔어요",`기울기 ${Math.round(trunk)}°`,"허리 과신전");maybeSpeak("허리 과신전","허리를 너무 젖히지 마세요.");}

    // 7) 반동
    if(eSpd>40&&phase==="down"){score-=8;warn("반동을 줄이고 내려오세요","천천히 컨트롤하며 내리세요.","반동 사용");maybeSpeak("반동 사용","반동 없이 내려오세요.");}
  }

  // ══════════════════════════════════════════════════════════════════════════
  // LATERAL RAISE
  // ══════════════════════════════════════════════════════════════════════════
  else if(EXERCISE_KEY==="lateralraise"){
    if(!sh||!wr||!oWr||avgShY==null)return{valid:false,main:"정면에서 양팔 전체가 보이게 해주세요.",sub:""};
    const wY=avg([wr?.y,oWr?.y]);
    const yMetric=wY!=null?wY-avgShY:null;
    const lateralThr=getThresholds("up_to_down_low_y");
    inUp=yMetric!=null&&yMetric<(lateralThr?.up??0.08);inDown=yMetric!=null&&yMetric>(lateralThr?.down??0.14);countOn="up_to_down";
    const eSpd=angSpeed(elbowAng,prevElbowAng);prevElbowAng=elbowAng;
    const sub=`손목 ${wY!=null?(wY<avgShY?"어깨 위":"어깨 아래"):"-"} · 좌우차 ${Math.round(wrDiff*100)}`;

    // 1) 팔 높이 — 세 단계
    if(inUp&&wY<avgShY-0.03){good("어깨보다 높이 올라왔어요! (완벽)",sub);}
    else if(inUp){good("어깨 높이 전후까지 잘 올라왔어요!",sub);}
    else if(wY!=null&&wY>avgShY+0.12){score-=18;bad("팔을 어깨 높이까지 올려야 해요",`많이 부족합니다. · ${sub}`,"팔 높이 매우 부족");maybeSpeak("팔 높이 매우 부족","팔을 어깨 높이까지 올려주세요.");}
    else if(wY!=null&&wY>avgShY+0.08){score-=8;warn("팔을 조금 더 올려주세요",`어깨 높이 전후가 목표입니다. · ${sub}`,"팔 높이 부족");maybeSpeak("팔 높이 부족","조금 더 올려주세요.");}
    else{warn("좋은 높이입니다.",sub);}

    // 2) 팔꿈치 과굽힘 — 두 단계
    if(elbowAng!=null&&elbowAng<80){score-=14;bad("팔꿈치가 너무 굽었어요",`팔꿈치 ${Math.round(elbowAng)}°`,"팔꿈치 과도한 굽힘");maybeSpeak("팔꿈치 과도한 굽힘","팔꿈치를 살짝만 구부리세요.");}
    else if(elbowAng!=null&&elbowAng<100){score-=7;warn("팔꿈치를 살짝만 구부린 채 올리세요",`팔꿈치 ${Math.round(elbowAng)}°`,"팔꿈치 굽힘");maybeSpeak("팔꿈치 굽힘","팔꿈치를 살짝만 구부리세요.");}

    // 3) 양팔 비대칭 — 두 단계
    if(wrDiff>0.10){score-=16;bad("양팔 높이가 크게 차이 나요!",`높이차 ${Math.round(wrDiff*100)}`,"양팔 심한 비대칭");maybeSpeak("양팔 심한 비대칭","양팔을 같은 높이로 올리세요.");}
    else if(wrDiff>0.06){score-=8;warn("양팔 높이를 맞춰주세요",`높이차 ${Math.round(wrDiff*100)}`,"양팔 비대칭");maybeSpeak("양팔 비대칭","양쪽 팔의 높이를 맞추세요.");}

    // 4) 반동/상체 흔들림
    if(trunk!=null&&trunk>18){score-=10;warn("반동을 줄이고 어깨로 올리세요",`허리 기울기 ${Math.round(trunk)}°`,"반동 사용");maybeSpeak("반동 사용","반동을 줄이고 어깨 근육으로 제어해주세요.");}
    else if(trunk!=null&&trunk>12){score-=5;warn("살짝 반동이 있어요","허리를 고정하고 올리세요.","경미한 반동");}

    // 5) 어깨 높이 (상단에서 어깨가 들리면)
    if(sh&&oSh&&inUp&&Math.abs(sh.y-oSh.y)>0.06){score-=8;warn("한쪽 어깨가 들렸어요","어깨를 내리고 팔만 올리세요.","어깨 들림");maybeSpeak("어깨 들림","어깨를 내리고 팔만 올리세요.");}
  }

  // ══════════════════════════════════════════════════════════════════════════
  // DUMBBELL CURL — 정면/측면 자동 판별
  // 정면: 손목Y가 팔꿈치Y보다 위로 올라왔는지로 굴곡 판정 (팔꿈치 각도는 정면에서 신뢰 불가)
  // 측면: 팔꿈치 각도 기준
  // 카운트: down_to_up
  // ══════════════════════════════════════════════════════════════════════════
  else if(EXERCISE_KEY==="dumbbellcurl"){
    // 정면 판별: 양쪽 어깨가 모두 보이면 정면
    const curlFrontal=(point(lm,11)?.visibility||0)>0.4&&(point(lm,12)?.visibility||0)>0.4
      &&rawElbowAngBoth!=null&&avgElY!=null&&avgWrYBoth!=null;

    if(curlFrontal){
      // 정면 모드: 손목Y - 팔꿈치Y (음수=손목이 위) 기준
      // 완전 굴곡: 손목이 팔꿈치와 같거나 위 (wY - elY < 0.02)
      // 완전 신전: 손목이 팔꿈치보다 많이 아래 (wY - elY > 0.12)
      const curlMetric=avgWrYBoth-avgElY; // 양수=손목 아래, 음수=손목 위
      inUp=curlMetric<-0.04;inDown=curlMetric>0.10;countOn="down_to_up";
      upLabel="수축";downLabel="신전";
      const eaB=rawElbowAngBoth??0;
      const eSpd=angSpeed(eaB,prevElbowAng);prevElbowAng=eaB;
      const sub=`손목↑팔꿈치 차 ${curlMetric>0?"+":""}${(curlMetric*100).toFixed(0)} · 정면`;

      if(inUp&&curlMetric<-0.03){good("완벽! 이두근 완전 수축!",sub);}
      else if(inUp){good("충분히 굽혔어요!",sub);}
      else if(!inDown&&curlMetric>0.06){score-=12;bad("팔꿈치를 굽혀 손목을 올리세요!","손목이 팔꿈치 높이까지 와야 해요.","굴곡 부족");maybeSpeak("굴곡 부족","팔꿈치를 더 굽혀 올리세요.");}

      // 팔꿈치 이탈 — 수축(UP) 단계에서만 체크, 정면 덤벨컬은 팔꿈치가 어깨 너비 허용
      const lEl=point(lm,13),rEl=point(lm,14),lSh=point(lm,11),rSh=point(lm,12);
      const lWr=point(lm,15),rWr=point(lm,16);
      if(phase==="up"&&lEl&&rEl&&lSh&&rSh){
        const ew=Math.abs(lEl.x-rEl.x),sw=Math.abs(lSh.x-rSh.x);
        if(sw>0.01&&ew/sw>1.75){score-=12;bad("팔꿈치가 너무 벌어졌어요!","팔꿈치를 몸통 옆에 붙이세요.","팔꿈치 이탈");maybeSpeak("팔꿈치 이탈","팔꿈치를 몸에 붙이세요.");}
      }
      // 손목 꺾임 — 수축 시 손목이 팔꿈치 X에서 많이 벗어나면 손목 꺾임
      if(inUp&&lEl&&lWr&&rEl&&rWr){
        const lWrDev=Math.abs(lWr.x-lEl.x),rWrDev=Math.abs(rWr.x-rEl.x);
        const avgWrDev=avg([lWrDev,rWrDev]);
        if(avgWrDev>0.07){score-=12;bad("손목이 많이 꺾였어요!","수축 시 손목을 중립으로 유지하세요.","손목 꺾임");maybeSpeak("손목 꺾임","손목을 곧게 펴서 올리세요.");}
        else if(avgWrDev>0.045){score-=6;warn("손목이 살짝 꺾였어요","손목을 중립으로 유지하세요.","손목 경미한 꺾임");}
      }
      if(eSpd>55&&phase==="up"){score-=10;warn("반동을 줄이세요!","천천히 이두근으로 굽혀 올리세요.","반동 사용");maybeSpeak("반동 사용","반동 없이 올리세요.");}

      // 좌우 손목 높이 비대칭 — 정면에서만 유효
      if(lWr&&rWr){
        const lrDiff=Math.abs(lWr.y-rWr.y);
        if(lrDiff>0.10){score-=12;bad("양팔 높이가 많이 차이 나요!","같은 높이로 올려주세요.","양팔 비대칭");maybeSpeak("양팔 비대칭","양팔을 같은 높이로 올리세요.");}
        else if(lrDiff>0.06){score-=6;warn("한쪽 팔이 더 높아요","양팔 높이를 맞춰주세요.","양팔 약간 비대칭");}
      }
      // 완전 신전 미달 — 내리는 단계에서 손목이 팔꿈치 아래로 충분히 안 내려오면
      if(phase==="down"&&curlMetric<0.06){score-=8;warn("팔을 끝까지 내려주세요","완전히 펴고 다시 올려야 이두근 전체 운동이 됩니다.","완전 신전 미달");maybeSpeak("완전 신전 미달","팔을 끝까지 내려주세요.");}

    } else {
      // 측면 모드: 팔꿈치 각도 기준
      if(!sh||!el||!wr)return{valid:false,main:"어깨·팔꿈치·손목이 보이게 정면 또는 측면으로 조정해주세요.",sub:""};
      if(elbowAng==null)return{valid:false,main:"관절 인식 중.",sub:""};
      const curlThr=getThresholds("down_to_up_low_angle");
      inUp=elbowAng<(curlThr?.up??85);inDown=elbowAng>(curlThr?.down??145);countOn="down_to_up";
      upLabel="수축";downLabel="신전";
      const eSpd=angSpeed(elbowAng,prevElbowAng);prevElbowAng=elbowAng;
      const sub=`팔꿈치 ${Math.round(elbowAng)}°`;

      if(inUp&&elbowAng<65){good("완벽! 이두근 완전 수축!",sub);}
      else if(inUp){good("충분히 굽혔어요!",sub);}
      else if(elbowAng>100&&elbowAng<125){score-=14;bad("끝까지 굽혀 올리세요!",`목표 85° 이하`,"굴곡 매우 부족");maybeSpeak("굴곡 매우 부족","팔꿈치를 더 굽혀 올리세요.");}
      else if(elbowAng>=85&&elbowAng<=100){score-=7;warn("조금만 더 굽혀 올리세요",sub,"굴곡 부족");maybeSpeak("굴곡 부족","조금만 더 굽혀 올리세요.");}

      if(phase==="down"&&elbowAng<130&&elbowAng>100){score-=10;warn("팔을 끝까지 내려주세요","완전 신전 후 다시 올리세요.","완전 신전 미달");maybeSpeak("완전 신전 미달","팔을 완전히 펴주세요.");}

      if(sh&&el){
        const elbowForward=side==="right"?(el.x-sh.x):(sh.x-el.x);
        if(elbowForward>0.08){score-=14;bad("팔꿈치가 앞으로 많이 나왔어요!","팔꿈치를 몸통 옆에 고정하세요.","팔꿈치 이탈");maybeSpeak("팔꿈치 이탈","팔꿈치를 몸 옆에 붙이세요.");}
        else if(elbowForward>0.05){score-=7;warn("팔꿈치가 살짝 앞으로 나왔어요","팔꿈치를 몸통에 고정하세요.","팔꿈치 흔들림");}
      }
      if(eSpd>55&&phase==="up"){score-=10;warn("반동을 줄이세요!","천천히 이두근으로 굽혀 올리세요.","반동 사용");maybeSpeak("반동 사용","반동 없이 천천히 올리세요.");}
    }

    // 공통: 허리 반동
    if(trunk!=null&&trunk>20){score-=12;bad("허리를 젖히지 마세요!",`기울기 ${Math.round(trunk)}°`,"허리 반동");maybeSpeak("허리 반동","허리를 세우고 이두근만으로 올리세요.");}
    else if(trunk!=null&&trunk>12){score-=6;warn("상체를 살짝 뒤로 젖혔어요",`기울기 ${Math.round(trunk)}°`,"경미한 허리 반동");}
  }

  // ══════════════════════════════════════════════════════════════════════════
  // TRICEP PUSHDOWN — 삼두근 신전: 팔꿈치 각도 기준
  // 정면/측면/45도 자동 판별: 양어깨 보이면 양팔 평균 사용
  // 카운트: up_to_down (팔 올라온 상태 → 완전 신전으로 내리면 1회)
  // ══════════════════════════════════════════════════════════════════════════
  else if(EXERCISE_KEY==="triceppushdown"){
    if(!sh||!el||!wr)return{valid:false,main:"어깨·팔꿈치·손목이 모두 보이게 해주세요.",sub:""};
    // 양쪽 어깨가 보이면 양팔 평균 팔꿈치각 사용 (45도/정면 구도 지원)
    const triFrontal=(point(lm,11)?.visibility||0)>0.4&&(point(lm,12)?.visibility||0)>0.4&&rawElbowAngBoth!=null;
    const triElbowAng=triFrontal?ema(smoothElbowAng,rawElbowAngBoth):elbowAng;
    if(triElbowAng==null)return{valid:false,main:"관절 인식 중.",sub:""};
    const triThr=getThresholds("up_to_down_high_angle");
    // DOWN = 팔꿈치 완전 신전(큰 각도, 아래로 밀어냄), UP = 팔꿈치 굴곡(작은 각도, 위로 올라옴)
    inDown=triElbowAng>(triThr?.up??148);inUp=triElbowAng<(triThr?.down??100);countOn="up_to_down";
    upLabel="굴곡";downLabel="신전";
    const eSpd=angSpeed(triElbowAng,prevElbowAng);prevElbowAng=triElbowAng;
    const sub=`팔꿈치 ${Math.round(triElbowAng)}°${triFrontal?" (양팔)":""}`;

    // 1) 완전 신전 도달 여부 — 세 단계
    if(inDown&&triElbowAng>168){good("완벽! 삼두근 완전 수축!",sub);}
    else if(inDown){good("잘 밀어냈어요! 끝에서 1초 버티면 더 좋아요.",sub);}
    else if(triElbowAng<130&&triElbowAng>100){score-=14;bad("팔을 완전히 펴서 밀어내세요!",`팔꿈치 ${Math.round(triElbowAng)}°, 목표 155° 이상`,"신전 매우 부족");maybeSpeak("신전 매우 부족","팔을 끝까지 펴주세요.");}
    else if(triElbowAng>=130&&triElbowAng<155){score-=7;warn("조금만 더 펴주세요",sub,"신전 부족");maybeSpeak("신전 부족","조금만 더 밀어주세요.");}

    // 2) 팔꿈치 고정 — UP(올라온) 상태에서만 체크, 자연스러운 구도 오차 감안해 임계값 높임
    if(phase==="up"&&sh&&el&&oSh&&oEl){
      const ew=Math.abs(el.x-oEl.x),sw=Math.abs(sh.x-oSh.x);
      if(sw>0.01&&ew/sw>1.7){score-=12;bad("팔꿈치가 너무 벌어졌어요!","팔꿈치를 몸통 옆에 고정하세요.","팔꿈치 벌어짐");maybeSpeak("팔꿈치 벌어짐","팔꿈치를 모아 주세요.");}
    }

    // 3) 팔꿈치 앞쏠림 (측면에서만 유효)
    if(!triFrontal&&sh&&el){
      const elbowForward=side==="right"?(el.x-sh.x):(sh.x-el.x);
      if(elbowForward>0.09){score-=12;bad("팔꿈치가 너무 앞으로 나왔어요","팔꿈치를 몸통 옆에 붙이세요.","팔꿈치 앞쏠림");maybeSpeak("팔꿈치 앞쏠림","팔꿈치를 몸 옆에 붙이세요.");}
      else if(elbowForward>0.06){score-=6;warn("팔꿈치가 조금 앞으로 나왔어요","팔꿈치를 고정하세요.","팔꿈치 약간 앞쏠림");}
    }

    // 4) 반동 — 빠른 속도
    if(eSpd>55&&phase==="down"){score-=10;warn("반동을 줄이세요!","삼두근으로 천천히 밀어내세요.","반동 사용");maybeSpeak("반동 사용","반동 없이 천천히 밀어주세요.");}

    // 5) 상체 과도한 숙임
    if(trunk!=null&&trunk>30){score-=12;bad("상체를 너무 숙이지 마세요!",`기울기 ${Math.round(trunk)}°`,"상체 과도한 숙임");maybeSpeak("상체 과도한 숙임","상체를 조금 세우세요.");}
    else if(trunk!=null&&trunk>20){score-=6;warn("상체를 살짝 숙였어요",`기울기 ${Math.round(trunk)}°`,"상체 숙임");}

    // 6) 좌우 손목 높이 비대칭 (정면·45도 구도에서 양손 보일 때)
    if(triFrontal&&wr&&oWr){
      const lrDiff=Math.abs(wr.y-oWr.y);
      if(lrDiff>0.09){score-=10;bad("양손 높이가 많이 차이 나요!","양손을 같은 높이로 내려주세요.","양팔 비대칭");maybeSpeak("양팔 비대칭","양손을 같은 높이로 맞추세요.");}
      else if(lrDiff>0.055){score-=5;warn("한쪽 손이 더 내려왔어요","양손 높이를 맞춰주세요.","양팔 약간 비대칭");}
    }

    // 7) 손목 꺾임 — 신전 단계에서 손목이 일직선인지 (측면에서만 유효)
    if(!triFrontal&&wr&&el&&sh){
      const wrElDiff=side==="right"?(wr.x-el.x):(el.x-wr.x);
      if(inDown&&Math.abs(wrElDiff)>0.06){score-=8;warn("손목이 꺾였어요","손목을 곧게 펴고 밀어주세요.","손목 꺾임");maybeSpeak("손목 꺾임","손목을 곧게 펴주세요.");}
    }
  }

  sort();
  if(!fbs.length)good("자세를 잡아주세요","카메라 구도를 맞추고 운동을 시작하세요.");
  score=Math.max(45,Math.min(100,Math.round(score)));
  const allIssues=fbs.filter(f=>f.issue).map(f=>f.issue);
  return{valid:true,feedbacks:fbs,inUp,inDown,upLabel,downLabel,score,countOn,topIssue:fbs[0]?.issue||null,allIssues};
}

// ── Skeleton ──────────────────────────────────────────────────────────────────
function drawCustomSkeleton(lm,sc){
  const c=sc==null?"#3b82f6":sc>=80?"#16a34a":sc>=65?"#d97706":"#dc2626";
  drawConnectors(ctx,lm,POSE_CONNECTIONS,{color:c,lineWidth:3});
  drawLandmarks(ctx,lm,{color:"#fff",fillColor:c,lineWidth:1,radius:5});
}

// ── Main loop ─────────────────────────────────────────────────────────────────
function onResults(results){
  resizeCanvas();ctx.clearRect(0,0,canvas.width,canvas.height);
  if(cameraStarted)checkCameraQuality();
  if(!results.poseLandmarks){
    const now=Date.now();
    if(cameraStarted&&now-lastNoDetectSpoken>6000){lastNoDetectSpoken=now;if(setActive)speak("자세를 인식하지 못하고 있습니다.");}
    stateText.textContent="READY";liveScore=null;updateHud();
    qualityStableFrames=0;resetSmoothing();
    lastQualityMetrics={score:0,visibleCount:0};
    setCvQualityState(cvReady?"인식 대기":"OpenCV 로딩 중",lastCvQualityState.brightness,lastCvQualityState.blur,"화면 안으로 들어와 전신이 보이게 맞춰주세요.");
    setMeasurementReadiness("blocked","화면 안으로 들어와 전신과 핵심 관절이 보이게 맞춰주세요.");
    renderDebugPanel();
    setBanner("화면 안으로 들어와 주세요.","관절이 보이면 자동으로 측정 시작","");
    maybeSpeakPassive("no-pose","화면 안으로 들어와 주세요. 전신이 보이게 맞춰주세요.",7000);
    if(!setActive){feedbackMain.textContent="화면 안으로 들어와 주세요.";feedbackSub.textContent="관절이 보이면 자동으로 측정이 시작됩니다.";renderEmgOnlyFeedbacks();statusChip.className="status-chip";statusChip.textContent=cameraStarted?"인식 대기":"대기 중";}
    return;
  }
  const lm=results.poseLandmarks;
  const visibleCount=lm.filter(p=>(p?.visibility||0)>0.55).length;
  maybeCaptureCalibration(lm);
  const faceVisible=(lm[0]?.visibility||0)>0.45;
  const requiredIndices=requiredIndicesForExercise();
  const requiredVisible=requiredIndices.filter(i=>landmarkVisible(lm,i)).length;
  const xVals=[11,12,23,24].map(i=>lm[i]?.x).filter(v=>typeof v==="number");
  const torsoSpan=xVals.length>=2?Math.max(...xVals)-Math.min(...xVals):0;
  lastQualityMetrics={score:qualityScore(visibleCount,faceVisible,lm),visibleCount};
  // 상체 운동(덤벨컬/푸쉬다운)은 전신 불필요 — 최소 관절 수 기준 낮춤
  const isUpperOnly=EXERCISE_KEY==="dumbbellcurl"||EXERCISE_KEY==="triceppushdown"||EXERCISE_KEY==="shoulderpress"||EXERCISE_KEY==="lateralraise";
  const minVisible=isUpperOnly?4:8;
  if(visibleCount<minVisible){
    if(!setActive){
      qualityStableFrames=0;liveScore=null;updateHud();
      const hint=isUpperOnly?"어깨·팔꿈치·손목이 보이게 구도를 맞춰주세요.":"전신 또는 핵심 관절이 보이게 조금 물러나 주세요.";
      setCvQualityState(lastCvQualityState.status,lastCvQualityState.brightness,lastCvQualityState.blur,hint);
      setMeasurementReadiness("blocked",hint);
      setBanner("관절 인식이 불안정합니다.",hint,"warn");
      feedbackMain.textContent="핵심 관절이 충분히 보이지 않습니다.";
      feedbackSub.textContent=hint;renderEmgOnlyFeedbacks();
      maybeSpeakPassive("low-visible","관절이 보이도록 카메라 구도를 조정해 주세요.",12000);
      renderDebugPanel();return;
    }
    // 세트 진행 중엔 경고만 표시하고 측정 계속
    setBanner("관절 인식이 약합니다.","카메라 구도를 조금 조정해주세요.","warn");
  }
  if(requiredIndices.length&&requiredVisible<Math.max(requiredIndices.length-1,3)){
    if(!setActive){
      qualityStableFrames=0;liveScore=null;updateHud();
      setCvQualityState(lastCvQualityState.status,lastCvQualityState.brightness,lastCvQualityState.blur,missingLandmarkMessage());
      setMeasurementReadiness("blocked",missingLandmarkMessage());
      setBanner("핵심 관절 인식이 부족합니다.",missingLandmarkMessage(),"warn");
      feedbackMain.textContent="현재 운동의 핵심 관절이 충분히 보이지 않습니다.";
      feedbackSub.textContent=missingLandmarkMessage();renderEmgOnlyFeedbacks();
      maybeSpeakPassive("missing-core","핵심 관절이 보이게 자세와 카메라 위치를 맞춰주세요.",12000);
      renderDebugPanel();return;
    }
    // 세트 진행 중엔 경고만 표시하고 측정 계속
    setBanner("핵심 관절 인식 부족.",missingLandmarkMessage(),"warn");
  }
  if((EXERCISE_KEY==="pullup"||EXERCISE_KEY==="pushup")&&!faceVisible){
    qualityStableFrames=0;liveScore=null;updateHud();
    setCvQualityState(lastCvQualityState.status,lastCvQualityState.brightness,lastCvQualityState.blur,"얼굴과 상체가 함께 보이게 구도를 맞춰주세요.");
    setMeasurementReadiness("warn","얼굴과 상체가 함께 보이게 구도를 맞춰주세요.");
    setBanner("얼굴 인식이 약합니다.","얼굴과 상체를 조금 더 밝고 정면에 가깝게 맞춰주세요.","warn");
    feedbackMain.textContent="얼굴 위치가 잘 보이지 않아 일부 피드백이 부정확할 수 있습니다.";
    feedbackSub.textContent="고개와 어깨가 함께 보이도록 구도를 맞추세요.";
    renderEmgOnlyFeedbacks();
    maybeSpeakPassive("face-weak","얼굴과 상체가 함께 보이게 구도를 맞춰주세요.",6500);
    renderDebugPanel();
    return;
  }
  const now=Date.now();
  // 거리 판정: 상체 운동은 기준 완화 (어깨 너비만 보임)
  const tooCloseThr=isUpperOnly?0.70:0.55;
  const tooFarThr  =isUpperOnly?0.08:0.10;
  if(torsoSpan>tooCloseThr){
    setMeasurementReadiness("warn","카메라와 너무 가까워 측정 오차가 커질 수 있습니다.");
    if(now-lastDistanceWarnAt>5000){
      lastDistanceWarnAt=now;
      const hint=isUpperOnly?"반 걸음 뒤로 물러나 어깨와 팔꿈치가 함께 보이게 해주세요.":"한 걸음 뒤로 물러나 전신과 핵심 관절이 함께 보이게 해주세요.";
      setCvQualityState("너무 가까움",lastCvQualityState.brightness,lastCvQualityState.blur,hint);
      setBanner("카메라에 너무 가깝습니다.",hint,"warn");
      maybeSpeakPassive("too-close","카메라에 너무 가깝습니다. 조금 뒤로 물러나 주세요.");
    }
  }else if(torsoSpan>0&&torsoSpan<tooFarThr){
    setMeasurementReadiness("warn","카메라와 너무 멀어 관절 인식이 약해질 수 있습니다.");
    if(now-lastDistanceWarnAt>5000){
      lastDistanceWarnAt=now;
      const hint=isUpperOnly?"조금 가까이 와서 어깨·팔꿈치·손목이 잘 보이게 해주세요.":"조금 가까이 와서 상체와 하체 관절이 더 크게 보이게 해주세요.";
      setCvQualityState("너무 멂",lastCvQualityState.brightness,lastCvQualityState.blur,hint);
      setBanner("카메라와 너무 멉니다.",hint,"warn");
      maybeSpeakPassive("too-far","카메라와 너무 멉니다. 조금 더 가까이 와주세요.");
    }
  }else if(lastCvQualityState.status==="양호"){
    setMeasurementReadiness("ready","현재 카메라 상태에서 측정 가능합니다.");
  }
  qualityStableFrames=Math.min(qualityStableFrames+1,30);
  if(setActive&&qualityStableFrames<4){
    stateText.textContent="READY";
    setBanner("자세 확인 중...","짧게 안정화한 뒤 측정을 시작합니다.","warn");
    feedbackMain.textContent="인식 안정화 중입니다.";
    feedbackSub.textContent="1초 이내로 자동 측정이 시작됩니다.";
    renderEmgOnlyFeedbacks();
    maybeSpeakPassive("stabilizing","자세 인식 안정화 중입니다. 잠시만 유지해 주세요.",5000);
    renderDebugPanel();
    return;
  }
  const result=evaluateForm(lm);
  drawCustomSkeleton(lm,result.valid?result.score:null);
  if(!result.valid){liveScore=null;updateHud();feedbackMain.textContent=result.main;feedbackSub.textContent=result.sub||"";renderEmgOnlyFeedbacks();setBanner(result.main,"","warn");return;}
  if(result.pullupHandled)return;
  liveScore=clamp(result.score-(qualityStableFrames<8?4:0),45,100);updateHud();
  setFeedbacks(result.feedbacks);
  renderDebugPanel();
  if(setActive){
    updateRep(result.inUp,result.inDown,result.upLabel,result.downLabel,result.score,result.topIssue,result.countOn,result.allIssues);
    statusChip.className="status-chip live";statusChip.textContent="세트 진행";
  }else if(paused){statusChip.className="status-chip warn";statusChip.textContent="일시정지";}
  else{statusChip.className="status-chip";statusChip.textContent="카메라 연결";}
}

// ── Camera start ──────────────────────────────────────────────────────────────
async function startCamera(){
  if(camera)return;
  try{
    pose=new Pose({locateFile:f=>`https://cdn.jsdelivr.net/npm/@mediapipe/pose/${f}`});
    pose.setOptions({modelComplexity:2,smoothLandmarks:true,enableSegmentation:false,smoothSegmentation:false,minDetectionConfidence:0.6,minTrackingConfidence:0.6});
    pose.onResults(onResults);
    camera=new Camera(video,{onFrame:async()=>{await pose.send({image:video});},width:1280,height:720});
    await camera.start();
    cameraStarted=true;cameraText.textContent="ON";trackingText.textContent="IDLE";
    // 실제 영상 프레임이 도착할 때까지 video 숨김 유지
    const showVideoWhenReady=()=>{
      video.style.display="";
      document.getElementById("camPlaceholder").style.display="none";
    };
    if(video.readyState>=2){showVideoWhenReady();}
    else{video.addEventListener("loadeddata",showVideoWhenReady,{once:true});}
    setCvQualityState("측정 준비","-","-","카메라 상태를 자동 점검합니다.");
    setMeasurementReadiness("warn","화면 안으로 들어와 자세를 맞춰주세요.");
    statusChip.className="status-chip";statusChip.textContent="카메라 연결";
    feedbackMain.textContent="카메라가 시작되었습니다.";feedbackSub.textContent="자세를 잡고 세트 시작을 눌러주세요.";
    setBanner("카메라 연결됨","자세를 잡고 세트를 시작하세요.","good");
    speak("카메라가 시작되었습니다. 자세를 잡고 세트 시작을 눌러주세요.");resizeCanvas();
  }catch(err){
    pose=null;camera=null;cameraStarted=false;cameraText.textContent="OFF";trackingText.textContent="ERROR";
    setCvQualityState("오류","-","-","카메라 권한과 네트워크 상태를 확인하세요.");
    setMeasurementReadiness("blocked","카메라 또는 모델 로딩에 실패했습니다.");
    setBanner("카메라 시작 실패","브라우저 권한과 네트워크 상태를 확인하세요.","bad");
    feedbackMain.textContent="카메라 또는 모델 로딩에 실패했습니다.";
    feedbackSub.textContent=err?.message||"권한 허용 후 다시 시도하세요.";
    statusChip.className="status-chip warn";statusChip.textContent="오류";
  }
}
function stopCamera(){
  try{
    if(camera&&typeof camera.stop==="function")camera.stop();
  }catch(_){}
  try{
    const stream=video.srcObject;
    if(stream&&typeof stream.getTracks==="function")stream.getTracks().forEach(t=>t.stop());
  }catch(_){}
  video.srcObject=null;
  pose=null;camera=null;cameraStarted=false;
  setActive=false;paused=false;phase="idle";stableUp=0;stableDown=0;repLock=0;
  resetRepCycle();resetSmoothing();
  setCvQualityState("대기","-","-","카메라 시작 전");
  setMeasurementReadiness("blocked","카메라 시작 전");
  cameraText.textContent="OFF";trackingText.textContent="OFF";stateText.textContent="READY";liveScore=null;updateHud();
  statusChip.className="status-chip";statusChip.textContent="대기 중";
  setBanner("카메라가 종료되었습니다.","다시 시작하려면 카메라 시작을 누르세요.","");
  feedbackMain.textContent="카메라가 종료되었습니다.";feedbackSub.textContent="다시 시작하려면 카메라 시작을 누르세요.";issueListWrap.innerHTML="";
  video.style.display="none";
  document.getElementById("camPlaceholder").style.display="";
}
window.addEventListener("resize",resizeCanvas);
window.addEventListener("beforeunload",e=>{
  if(hasUnsavedChanges){
    e.preventDefault();
    e.returnValue="";
  }
});
window.onload=()=>{
  loadOpenCv();
  setMeasurementReadiness("blocked","카메라 시작 전");
  updateCalibrationStatus("기본 기준 사용 중입니다.");
  resizeCanvas();updateHud();restoreLocalBackup();renderDebugPanel();ensureVoiceControlUI();
  emgInit();
};

// ── EMG ──────────────────────────────────────────────────────────────────────
(function(){
  const WAVE_LEN=200;
  // MAV 버퍼: 절댓값 평균 계산용 (채널별 최근 N샘플)
  const MAV_N=100;
  const CH_COLORS=["#3b82f6","#22c55e","#f59e0b","#ef4444","#a78bfa","#ec4899","#06b6d4","#84cc16"];
  // 활성도 레벨 라벨 (MAV 백분위 기준)
  const LEVEL_LABELS=["없음","낮음","보통","높음","매우높음"];
  // 없음=회색, 낮음=초록, 보통=노랑, 높음=주황, 매우높음=빨강
  const LEVEL_COLORS=["#94a3b8","#22c55e","#eab308","#f97316","#ef4444"];

  let emgIP="172.18.140.60",emgPORT="8080",emgInterval=100;
  let emgTimer=null,emgInited=false,emgChCount=0;
  let emgWaveBufs=[],emgMavBufs=[],emgReqTimes=[];
  let emgMavPeak=[];
  let emgStartTime=0;  // warm-up 기준 시각
  // 캘리브레이션
  let emgCalibRest=[], emgCalibMvc=[];
  let emgCalibMode=null, emgCalibBuf=[], emgCalibTimer=null;

  // ── 채널-근육 매핑 ────────────────────────────────────────
  // 운동별 선택 가능한 근육 목록
  const MUSCLE_OPTIONS={
    squat:          ["미지정","왼쪽 외측광근","오른쪽 외측광근","왼쪽 대퇴직근","오른쪽 대퇴직근"],
    lateralraise:   ["미지정","왼쪽 삼각근 중부","오른쪽 삼각근 중부"],
    dumbbellcurl:   ["미지정","왼쪽 이두근","오른쪽 이두근"],
    triceppushdown: ["미지정","왼쪽 삼두근","오른쪽 삼두근"],
  };
  // 근육별 피드백 기준
  const MUSCLE_THRESHOLDS={
    "왼쪽 외측광근":   {low:50,high:85,side:"left", group:"squat"},
    "오른쪽 외측광근": {low:50,high:85,side:"right",group:"squat"},
    "왼쪽 대퇴직근":   {low:50,high:85,side:"left", group:"squat"},
    "오른쪽 대퇴직근": {low:50,high:85,side:"right",group:"squat"},
    "왼쪽 삼각근 중부":  {low:40,high:75,side:"left", group:"lr"},
    "오른쪽 삼각근 중부":{low:40,high:75,side:"right",group:"lr"},
    "왼쪽 이두근":    {low:50,high:80,side:"left", group:"curl"},
    "오른쪽 이두근":   {low:50,high:80,side:"right",group:"curl"},
    "왼쪽 삼두근":    {low:45,high:80,side:"left", group:"tri"},
    "오른쪽 삼두근":   {low:45,high:80,side:"right",group:"tri"},
  };
  // 근육별 자극 부족/과부하 교정 멘트
  const MUSCLE_FIX={
    "왼쪽 외측광근":   {low:"더 깊이 앉고 왼발 바깥쪽으로 밀어주세요",   high:"무게를 줄이거나 깊이를 낮추세요"},
    "오른쪽 외측광근": {low:"더 깊이 앉고 오른발 바깥쪽으로 밀어주세요",  high:"무게를 줄이거나 깊이를 낮추세요"},
    "왼쪽 대퇴직근":   {low:"발 앞쪽으로 체중을 싣고 더 깊이 앉으세요",   high:"무게를 줄이거나 깊이를 낮추세요"},
    "오른쪽 대퇴직근": {low:"발 앞쪽으로 체중을 싣고 더 깊이 앉으세요",   high:"무게를 줄이거나 깊이를 낮추세요"},
    "왼쪽 삼각근 중부":  {low:"팔꿈치를 손목보다 높게 들어주세요",          high:"무게를 줄이고 천천히 올려주세요"},
    "오른쪽 삼각근 중부":{low:"팔꿈치를 손목보다 높게 들어주세요",          high:"무게를 줄이고 천천히 올려주세요"},
    "왼쪽 이두근":    {low:"끝까지 굴곡하고 1초 버티세요",               high:"무게를 줄이고 천천히 내려주세요"},
    "오른쪽 이두근":   {low:"끝까지 굴곡하고 1초 버티세요",               high:"무게를 줄이고 천천히 내려주세요"},
    "왼쪽 삼두근":    {low:"팔꿈치를 완전히 펴서 끝까지 밀어주세요",       high:"무게를 줄이고 팔꿈치를 고정하세요"},
    "오른쪽 삼두근":   {low:"팔꿈치를 완전히 펴서 끝까지 밀어주세요",       high:"무게를 줄이고 팔꿈치를 고정하세요"},
  };
  // 채널별 현재 근육 매핑 (index → 근육명, 기본 "미지정")
  let chMuscleMap=[];   // chMuscleMap[i] = 근육명 문자열
  // 세션 피드백 로그 (문서화용)
  let emgFeedbackLog=[];

  // 채널별 캔버스 배열 (initChs에서 동적 생성)
  let emgCanvases=[];  // [{cvs, ctx, wrap}]

  function resizeEmgCanvas(){
    emgCanvases.forEach(({cvs,wrap})=>{
      if(!wrap)return;
      const w=wrap.clientWidth, h=wrap.clientHeight;
      if(w>0&&h>0){
        cvs.width=Math.round(w*devicePixelRatio);
        cvs.height=Math.round(h*devicePixelRatio);
      }
    });
  }
  window.addEventListener("resize",resizeEmgCanvas);

  // 운동 가이드에 정의된 채널 목록 (0-based 인덱스로 변환)
  // EMG_GUIDE_CHANNELS = [{ch:1, label:"왼쪽 외측광근", ...}, ...]
  // guideChs[i] = { chIdx: 0-based, label: string, muscle: string }
  let guideChs = [];

  function initChs(totalFromServer){
    // 가이드 채널이 있으면 그 수, 없으면 서버 채널 수 사용
    const useGuide = EMG_GUIDE_CHANNELS && EMG_GUIDE_CHANNELS.length > 0;
    const displayCount = useGuide ? EMG_GUIDE_CHANNELS.length : Math.min(totalFromServer, 4);

    // 이미 같은 구성이면 무시
    if(emgChCount === displayCount && emgInited) return;
    emgChCount = displayCount;

    // 가이드 채널 인덱스 맵핑 구성 (ch는 1-based)
    guideChs = useGuide
      ? EMG_GUIDE_CHANNELS.map(g => ({
          chIdx: g.ch - 1,          // Noraxon 배열 인덱스 (0-based)
          label: g.label || `CH${g.ch}`,
          muscle: g.label || "미지정"
        }))
      : Array.from({length: displayCount}, (_,i) => ({
          chIdx: i, label: `CH${i+1}`, muscle: "미지정"
        }));

    // 버퍼 초기화 (displayCount 개)
    emgWaveBufs = [];
    emgMavBufs  = [];
    emgMavPeak  = [];
    // chMuscleMap: 인덱스는 guideChs 순서 (0~displayCount-1)
    chMuscleMap = guideChs.map(g => g.muscle);

    for(let i = 0; i < displayCount; i++){
      emgWaveBufs.push(new Float32Array(WAVE_LEN));
      emgMavBufs.push([]);
      emgMavPeak.push(1);
    }

    // UI 렌더링 — 바 차트
    const list = document.getElementById("emgChList");
    list.innerHTML = "";

    guideChs.forEach((g, i) => {
      const d = document.createElement("div");
      d.style.cssText = "display:flex;flex-direction:column;gap:3px;padding-bottom:6px;border-bottom:1px solid var(--line);";
      d.innerHTML =
        `<div style="display:flex;align-items:center;gap:4px;">`+
          `<span style="font-size:11px;font-weight:800;color:var(--muted);flex-shrink:0;">CH${g.chIdx+1}</span>`+
          `<span style="flex:1;font-size:10px;font-weight:700;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${g.label}</span>`+
          `<span id="emgVal${i}" style="font-size:10px;font-weight:800;font-variant-numeric:tabular-nums;`+
            `color:var(--muted);min-width:52px;text-align:right;flex-shrink:0;">— μV</span>`+
        `</div>`+
        `<div style="display:flex;align-items:center;gap:4px;">`+
          `<span id="emgLvLabel${i}" style="font-size:10px;font-weight:800;padding:1px 7px;border-radius:999px;`+
            `background:#94a3b822;color:#94a3b8;transition:.2s;white-space:nowrap;flex-shrink:0;">대기</span>`+
          `<div style="flex:1;height:16px;background:rgba(0,0,0,.07);border-radius:8px;overflow:hidden;position:relative;">`+
            `<div id="emgBar${i}" style="height:100%;width:0%;border-radius:8px;background:#94a3b8;transition:width .1s ease,background .2s ease;"></div>`+
            `<span id="emgPct${i}" style="position:absolute;right:5px;top:50%;transform:translateY(-50%);`+
              `font-size:9px;font-weight:800;color:rgba(0,0,0,.35);pointer-events:none;">0%</span>`+
          `</div>`+
        `</div>`;
      list.appendChild(d);
    });

    // 파형 캔버스 영역 동적 생성 (채널별)
    emgCanvases = [];
    const waveSection = document.getElementById("emgWaveSection");
    waveSection.innerHTML = "";
    guideChs.forEach((g, i) => {
      const wrap = document.createElement("div");
      wrap.style.cssText = "display:flex;flex-direction:column;gap:2px;";
      const label = document.createElement("div");
      label.style.cssText = "font-size:10px;font-weight:700;color:var(--muted);letter-spacing:.04em;";
      label.textContent = `원시 신호 CH${g.chIdx+1} — ${g.label}`;
      const cvsWrap = document.createElement("div");
      cvsWrap.style.cssText = "width:100%;height:56px;border-radius:6px;background:rgba(0,0,0,.04);overflow:hidden;border:1px solid var(--line);position:relative;";
      const cvs = document.createElement("canvas");
      cvs.width = 300; cvs.height = 56;
      cvs.style.cssText = "position:absolute;top:0;left:0;width:100%;height:100%;display:block;";
      cvsWrap.appendChild(cvs);
      wrap.appendChild(label);
      wrap.appendChild(cvsWrap);
      waveSection.appendChild(wrap);
      const ctx = cvs.getContext("2d");
      emgCanvases.push({cvs, ctx, wrap: cvsWrap});
      // ResizeObserver 채널별 부착
      if(window.ResizeObserver){
        new ResizeObserver(()=>{
          const w=cvsWrap.clientWidth,h=cvsWrap.clientHeight;
          if(w>0&&h>0){cvs.width=Math.round(w*devicePixelRatio);cvs.height=Math.round(h*devicePixelRatio);}
        }).observe(cvsWrap);
      }
    });
    setTimeout(resizeEmgCanvas, 50);

    emgInited = true;
  }

  function setChMuscle(chIdx, muscleName){
    chMuscleMap[chIdx] = muscleName;
  }


  // MAV(Mean Absolute Value) 계산: 절댓값의 평균
  function calcMAV(buf){
    if(!buf.length)return 0;
    return buf.reduce((s,v)=>s+Math.abs(v),0)/buf.length;
  }

  // MAV → 0~100% 정규화
  function mavToPct(mav,chIdx){
    const rest=emgCalibRest[chIdx]||0;
    const mvc=emgCalibMvc[chIdx]||0;
    if(mvc>rest+1){
      // 캘리브레이션 완료: rest~mvc 사이로 선형 정규화
      return Math.min(Math.max((mav-rest)/(mvc-rest)*100,0),100);
    }
    // 캘리브레이션 전: 동적 피크 방식 (fallback)
    // 처음 4초는 warm-up — 피크 누적만, 실제 상대값 표시 (100% 방지)
    const elapsed=Date.now()-emgStartTime;
    const warmup=elapsed<4000;
    if(mav>emgMavPeak[chIdx]*1.1) emgMavPeak[chIdx]=mav;
    else if(!warmup) emgMavPeak[chIdx]=emgMavPeak[chIdx]*0.9995+mav*0.0005;
    emgMavPeak[chIdx]=Math.max(emgMavPeak[chIdx],1);
    // warm-up 중에는 최대 60%로 클램프 (초기 스파이크로 100% 뜨는 거 방지)
    const raw=Math.min((mav/emgMavPeak[chIdx])*100,100);
    return warmup?Math.min(raw,60):raw;
  }

  // 활성도 퍼센트 → 레벨 (0~4)
  function pctToLevel(pct){
    if(pct<5)return 0;
    if(pct<30)return 1;
    if(pct<60)return 2;
    if(pct<85)return 3;
    return 4;
  }

  // 원시 신호 파형 — 채널별 캔버스에 그리기
  function drawEmgWave(){
    emgCanvases.forEach(({cvs, ctx}, i)=>{
      const W=cvs.width, H=cvs.height;
      if(W===0||H===0) return;
      ctx.clearRect(0,0,W,H);
      // 중심선
      ctx.strokeStyle="rgba(0,0,0,0.12)";
      ctx.lineWidth=1;
      ctx.beginPath();ctx.moveTo(0,H/2);ctx.lineTo(W,H/2);ctx.stroke();

      if(!emgWaveBufs[i]) return;
      const buf=emgWaveBufs[i];
      const mav=calcMAV(emgMavBufs[i]||[]);
      const lv=pctToLevel(mavToPct(mav,i));
      const col=LEVEL_COLORS[lv];
      // 진폭: 버퍼 내 절댓값 최대 (최소 1로 방어)
      let amp=0;
      for(const v of buf) if(Math.abs(v)>amp) amp=Math.abs(v);
      amp=Math.max(amp,1);
      ctx.strokeStyle=col;
      ctx.lineWidth=1.5;
      ctx.lineJoin="round";
      ctx.beginPath();
      for(let j=0;j<WAVE_LEN;j++){
        const x=(j/(WAVE_LEN-1))*W;
        const y=(H/2)-((buf[j]/amp)*(H/2)*0.85);
        j===0?ctx.moveTo(x,y):ctx.lineTo(x,y);
      }
      ctx.stroke();
    });
    requestAnimationFrame(drawEmgWave);
  }
  drawEmgWave();

  async function emgPoll(){
    try{
      const t0=performance.now();
      const res=await fetch(`http://${emgIP}:${emgPORT}/samples`,{signal:AbortSignal.timeout(3000)});
      const data=await res.json();

      // Hz 계산
      emgReqTimes.push(t0);
      if(emgReqTimes.length>20)emgReqTimes.shift();
      if(emgReqTimes.length>=2){
        const hz=(emgReqTimes.length-1)/((performance.now()-emgReqTimes[0])/1000);
        document.getElementById("emgHz").textContent=hz.toFixed(1)+" Hz";
      }

      // 채널 배열 정규화 — 파트너 형식 우선
      let chSamples=[];
      if(data&&data.batch&&typeof data.batch==="object"){
        // 파트너 형식: {exercise, active_channels, emg:{emg1:v}, batch:{emg1:[...], emg2:[...]}}
        const keys=Object.keys(data.batch).filter(k=>/^emg\d+$/.test(k))
          .sort((a,b)=>parseInt(a.slice(3))-parseInt(b.slice(3)));
        chSamples=keys.map(k=>{
          const v=data.batch[k];
          return Array.isArray(v)?v:[Number(v)];
        });
      } else if(data&&data.channels&&Array.isArray(data.channels)){
        // Noraxon 형식: {channels:[{samples:[...]}, ...]}
        chSamples=data.channels.map(ch=>Array.isArray(ch.samples)?ch.samples:[Number(ch)]);
      } else if(data&&Array.isArray(data.samples)){
        if(Array.isArray(data.samples[0])){
          const rows=data.samples,nCh=rows[0].length;
          for(let c=0;c<nCh;c++) chSamples.push(rows.map(r=>r[c]));
        } else { chSamples=[data.samples]; }
      } else if(Array.isArray(data)){
        chSamples=[data];
      } else if(data&&typeof data==="object"){
        chSamples=Object.values(data).filter(v=>typeof v==="number").map(v=>[v]);
      }

      if(!chSamples.length)return;
      initChs(chSamples.length);

      // 연결됨 표시
      const dot=document.getElementById("emgLiveDot");
      const wasConnected=dot.style.background==="#22c55e"||dot.dataset.connected==="1";
      dot.style.background="#22c55e";dot.style.boxShadow="0 0 6px #22c55e";dot.dataset.connected="1";
      const badge=document.getElementById("emgConnBadge");
      badge.textContent="연결됨";badge.style.color="#16a34a";badge.style.borderColor="#86efac";
      if(!wasConnected)utOnConnected();

      // 채널별 처리: guideChs 순서로 UI 인덱스(i)와 서버 인덱스(chIdx) 분리
      guideChs.forEach((g,i)=>{
        const samples=chSamples[g.chIdx];
        if(!samples||!samples.length)return;
        if(i>=emgWaveBufs.length)return;

        const lastVal=Number(samples[samples.length-1]);
        emgWaveBufs[i].copyWithin(0,1);
        emgWaveBufs[i][WAVE_LEN-1]=lastVal;

        const batchMav=samples.reduce((s,v)=>s+Math.abs(Number(v)),0)/samples.length;
        emgMavBufs[i].push(batchMav);
        if(emgMavBufs[i].length>MAV_N)emgMavBufs[i].shift();

        const mav=calcMAV(emgMavBufs[i]);
        if(emgCalibMode!==null){
          if(!emgCalibBuf[i])emgCalibBuf[i]=[];
          emgCalibBuf[i].push(mav);
        }
        const pct=mavToPct(mav,i);
        const lv=pctToLevel(pct);
        const lvCol=LEVEL_COLORS[lv];

        const bar=document.getElementById("emgBar"+i);
        if(bar){bar.style.width=pct.toFixed(1)+"%";bar.style.background=lvCol;}

        const pctEl=document.getElementById("emgPct"+i);
        if(pctEl){
          pctEl.textContent=Math.round(pct)+"%";
          pctEl.style.color=pct>70?"rgba(255,255,255,.7)":"rgba(0,0,0,.35)";
        }

        const valEl=document.getElementById("emgVal"+i);
        if(valEl){valEl.textContent=mav.toFixed(1)+" μV";valEl.style.color=lvCol;}

        const lvEl=document.getElementById("emgLvLabel"+i);
        if(lvEl){
          lvEl.textContent=LEVEL_LABELS[lv];
          lvEl.style.background=lvCol+"28";
          lvEl.style.color=lvCol;
          lvEl.style.borderColor=lvCol+"44";
        }
      });

      runEmgFeedback();

    }catch(e){
      const dot=document.getElementById("emgLiveDot");
      dot.dataset.connected="0";
      dot.style.background="#94a3b8";dot.style.boxShadow="none";
      const badge=document.getElementById("emgConnBadge");
      badge.textContent="대기";badge.style.color="var(--muted)";badge.style.borderColor="var(--line)";
    }
  }

  function emgStart(){
    if(emgTimer)clearInterval(emgTimer);
    emgStartTime=Date.now();
    emgTimer=setInterval(emgPoll,emgInterval);
    emgPoll();
  }
  function emgStop(){
    if(emgTimer){clearInterval(emgTimer);emgTimer=null;}
    const dot=document.getElementById("emgLiveDot");
    dot.style.background="#94a3b8";dot.style.boxShadow="none";
    document.getElementById("emgConnBadge").textContent="중지됨";
    document.getElementById("emgHz").textContent="— Hz";
  }
  function emgApply(){
    emgIP=document.getElementById("emgCfgIP").value.trim()||"127.0.0.1";
    emgPORT=document.getElementById("emgCfgPort").value.trim()||"8080";
    emgInterval=parseInt(document.getElementById("emgCfgInterval").value)||100;
    emgStart();
  }

  // ── 캘리브레이션 ──────────────────────────────────────
  const CALIB_SEC=3;

  function emgCalibStart(mode){
    // mode: "rest" | "mvc"
    if(!emgInited){alert("EMG 연결 후 시도하세요.");return;}
    emgCalibMode=mode;
    emgCalibBuf=Array.from({length:emgChCount},()=>[]);
    const btn=document.getElementById("emgCalibBtn"+mode);
    const status=document.getElementById("emgCalibStatus");
    let remaining=CALIB_SEC;
    status.textContent=(mode==="rest"?"① 힘 빼는 중…":"② 최대 수축 중…")+" "+remaining+"초";
    status.style.color=mode==="rest"?"#22c55e":"#ef4444";
    if(btn)btn.disabled=true;
    emgCalibTimer=setInterval(()=>{
      remaining--;
      status.textContent=(mode==="rest"?"① 힘 빼는 중…":"② 최대 수축 중…")+" "+remaining+"초";
      if(remaining<=0){
        clearInterval(emgCalibTimer);
        emgCalibFinish(mode);
        if(btn)btn.disabled=false;
      }
    },1000);
  }

  function emgCalibCollect(mavArr){
    // emgPoll에서 호출 — 캘리브레이션 중에 MAV 샘플 수집
    if(emgCalibMode===null)return;
    mavArr.forEach((mav,i)=>{
      if(!emgCalibBuf[i])emgCalibBuf[i]=[];
      emgCalibBuf[i].push(mav);
    });
  }

  function emgCalibFinish(mode){
    const status=document.getElementById("emgCalibStatus");
    emgCalibBuf.forEach((samples,i)=>{
      if(!samples.length)return;
      const avg=samples.reduce((s,v)=>s+v,0)/samples.length;
      if(mode==="rest"){
        emgCalibRest[i]=avg;
      } else {
        emgCalibMvc[i]=avg;
      }
    });
    emgCalibMode=null;
    emgCalibBuf=[];
    updateCalibDisplay();
    if(mode==="rest"){
      status.textContent="✓ 안정 측정 완료 — 이제 최대 수축을 측정하세요";
      status.style.color="#22c55e";
      showToast("✓ 힘 빼기 완료","이제 최대 수축 측정을 진행하세요","success",4000);
    } else {
      status.textContent="✓ 캘리브레이션 완료! 운동을 시작하세요";
      status.style.color="#3b82f6";
      showToast("✓ 캘리브레이션 완료","MVC 기준 설정 완료 — 운동을 시작하세요","success",4000);
    }
    utOnCalibDone(mode);
  }

  function updateCalibDisplay(){
    const el=document.getElementById("emgCalibValues");
    if(!el)return;
    let html="";
    for(let i=0;i<emgChCount;i++){
      const r=(emgCalibRest[i]||0).toFixed(1);
      const m=(emgCalibMvc[i]||0).toFixed(1);
      const ready=emgCalibMvc[i]>emgCalibRest[i]+1;
      html+=`<span style="font-size:10px;color:${ready?"#3b82f6":"var(--muted)"}">CH${i+1}: 안정 ${r} / 최대 ${m} μV</span><br>`;
    }
    el.innerHTML=html||"<span style='font-size:10px;color:var(--muted)'>아직 측정 전</span>";
  }

  function emgCalibReset(){
    emgCalibRest=[];emgCalibMvc=[];emgMavPeak=emgMavPeak.map(()=>1);
    const status=document.getElementById("emgCalibStatus");
    if(status){status.textContent="초기화됨 — 동적 피크 모드로 복귀";status.style.color="var(--muted)";}
    updateCalibDisplay();
  }

  // ── 토스트 알림 ─────────────────────────────────────────
  function showToast(title, msg, type="info", duration=4000){
    const c=document.getElementById("toastContainer");
    if(!c)return;
    const icons={info:"ℹ️",success:"✅",warn:"⚠️",danger:"🔴",calib:"🎯"};
    const t=document.createElement("div");
    t.className=`toast ${type}`;
    t.innerHTML=`<span class="toast-icon">${icons[type]||"ℹ️"}</span>`+
      `<div class="toast-body"><div class="toast-title">${title}</div>`+
      (msg?`<div class="toast-msg">${msg}</div>`:"")+`</div>`;
    c.appendChild(t);
    setTimeout(()=>{
      t.style.animation="toastOut .3s ease forwards";
      setTimeout(()=>t.remove(),300);
    },duration);
  }

  // 음성 안내 (TTS)
  function speak(text){
    if(!window.speechSynthesis)return;
    window.speechSynthesis.cancel();
    const u=new SpeechSynthesisUtterance(text);
    u.lang="ko-KR";u.rate=0.95;u.volume=1;
    window.speechSynthesis.speak(u);
  }

  // ── 유저 테스트 순서 안내 ────────────────────────────────
  // 단계: connect → rest → mvc → exercise → feedback
  let utStep="idle"; // idle | connect | rest | mvc | exercise

  function utGuideConnect(){
    utStep="connect";
    showToast("1단계: EMG 센서 연결","IP/PORT 확인 후 [적용] 버튼을 누르세요","info",6000);
    speak("첫번째 단계입니다. EMG 센서를 연결해주세요. IP와 포트를 확인하고 적용 버튼을 눌러주세요.");
  }

  function utGuideRest(){
    utStep="rest";
    showToast("2단계: 힘 빼기 측정","지금 자세 안내를 확인하고 [측정 시작] 버튼을 누르세요","calib",6000);
    speak("두번째 단계입니다. 근육 힘을 완전히 빼고 안정 자세를 취한 후, 힘 빼기 측정 시작 버튼을 눌러주세요.");
  }

  function utGuideMvc(){
    utStep="mvc";
    showToast("3단계: 최대 수축 측정","최대한 힘을 주는 자세로 [측정 시작] 버튼을 누르세요","calib",6000);
    speak("세번째 단계입니다. 안내된 자세로 최대한 힘을 주고 최대 수축 측정 시작 버튼을 눌러주세요.");
  }

  function utGuideExercise(){
    utStep="exercise";
    showToast("4단계: 운동 시작 준비","캘리브레이션 완료! 카메라를 시작하고 세트를 시작하세요","success",5000);
    speak("캘리브레이션이 완료됐습니다. 이제 카메라를 시작하고 운동을 시작하세요. 실시간으로 근육 활성도를 분석합니다.");
  }

  // EMG 연결 감지 시 자동으로 다음 단계 안내
  function utOnConnected(){
    if(utStep==="connect"||utStep==="idle"){
      utStep="rest";
      setTimeout(()=>{
        showToast("연결 성공! 다음: 힘 빼기 측정","사이드바에서 ① 힘 빼기 측정을 진행하세요","success",5000);
        speak("EMG 연결에 성공했습니다. 이제 힘 빼기 안정 측정을 진행해주세요.");
      },800);
    }
  }

  // 캘리브레이션 완료 시 호출 (emgCalibFinish에서 연결)
  function utOnCalibDone(mode){
    if(mode==="rest"){
      setTimeout(()=>utGuideMvc(),600);
    } else if(mode==="mvc"){
      setTimeout(()=>utGuideExercise(),600);
    }
  }

  // ── 실시간 EMG 피드백 (채널-근육 매핑 기반) ──────────────
  const FEEDBACK_COOLDOWN=15000;
  const GOOD_COOLDOWN=30000;
  let lastFeedbackTime={};

  function canFire(key,cooldown=FEEDBACK_COOLDOWN){
    const now=Date.now();
    if(!lastFeedbackTime[key]||now-lastFeedbackTime[key]>cooldown){
      lastFeedbackTime[key]=now;return true;
    }
    return false;
  }

  function getChPct(chIdx){
    if(!emgMavBufs[chIdx]||!emgMavBufs[chIdx].length)return 0;
    return mavToPct(calcMAV(emgMavBufs[chIdx]),chIdx);
  }

  // 피드백 로그 기록
  function logFeedback(muscle, type, pct, msg){
    emgFeedbackLog.push({
      time: new Date().toLocaleTimeString("ko-KR"),
      muscle, type, pct: Math.round(pct), msg
    });
  }

  // EMG 활성 피드백을 사이드바에 반영 (전역 activeEmgFeedbacks 갱신)
  const emgSidebarItems={};  // key → {cls,dot,msg,expireAt}
  function flushEmgSidebar(){
    const now=Date.now();
    Object.keys(emgSidebarItems).forEach(k=>{if(emgSidebarItems[k].expireAt<now)delete emgSidebarItems[k];});
    window.activeEmgFeedbacks=Object.values(emgSidebarItems);
  }
  function pushEmgSidebar(key,cls,dot,msg,ttl=8000){
    emgSidebarItems[key]={cls,dot,msg,expireAt:Date.now()+ttl};
    flushEmgSidebar();
  }

  // 채널 하나에 대한 3단계 판정
  function checkCh(chIdx){
    const muscle=chMuscleMap[chIdx];
    if(!muscle||muscle==="미지정")return;
    const th=MUSCLE_THRESHOLDS[muscle];
    const fix=MUSCLE_FIX[muscle];
    if(!th||!fix)return;
    const pct=getChPct(chIdx);
    const key=`ch${chIdx}`;

    if(pct<th.low){
      if(canFire(key+"_low")){
        const msg=`${muscle} 자극 부족 (${Math.round(pct)}%)`;
        pushEmgSidebar(key+"_low","emg-warn","emg-warn",msg,9000);
        speak(`${muscle} 자극이 부족합니다. ${fix.low}`);
        logFeedback(muscle,"부족",pct,fix.low);
      }
    } else {
      // 정상 구간 — 사이드바에 잠깐 good으로 표시
      if(canFire(key+"_good",GOOD_COOLDOWN)){
        pushEmgSidebar(key+"_good","emg-good","emg-good",`${muscle} 자극 양호 (${Math.round(pct)}%)`,6000);
        logFeedback(muscle,"정상",pct,"이 강도를 유지하세요");
      }
    }
  }

  // 같은 그룹(좌/우 쌍) 채널 찾아서 불균형 체크
  function checkAsymByMap(){
    const groups={};
    chMuscleMap.forEach((m,i)=>{
      if(!m||m==="미지정")return;
      const th=MUSCLE_THRESHOLDS[m];
      if(!th)return;
      const g=th.group;
      if(!groups[g])groups[g]={left:null,right:null};
      if(th.side==="left"&&groups[g].left===null) groups[g].left=i;
      if(th.side==="right"&&groups[g].right===null)groups[g].right=i;
    });
    Object.entries(groups).forEach(([g,{left,right}])=>{
      if(left===null||right===null)return;
      const lp=getChPct(left), rp=getChPct(right);
      const diff=Math.abs(lp-rp);
      const asymLimit={squat:20,lr:15,curl:20,tri:20}[g]||20;
      if(diff>asymLimit&&canFire(g+"_asym")){
        const wside=lp<rp?"왼쪽":"오른쪽";
        const wmuscle=chMuscleMap[lp<rp?left:right];
        const msg=`좌우 불균형 — ${wside} ${wmuscle} 약함 (${Math.round(diff)}%p 차이)`;
        pushEmgSidebar(g+"_asym","emg-warn","emg-warn",msg,10000);
        speak(`좌우 불균형이 감지됩니다. ${wside}을 더 의식해서 힘을 주세요.`);
        logFeedback(wmuscle,"불균형",diff,`${wside} 약함`);
      }
    });
  }

  const EMG_EXERCISE="{{ exercise_key }}";
  let feedbackCheckCounter=0;

  function runEmgFeedback(){
    const calibrated=emgCalibMvc.some(v=>v>0);
    // 만료된 항목 주기적으로 정리
    flushEmgSidebar();
    if(!calibrated||utStep!=="exercise")return;
    feedbackCheckCounter++;
    if(feedbackCheckCounter%20!==0)return;  // 약 2초마다
    for(let i=0;i<emgChCount;i++) checkCh(i);
    checkAsymByMap();
  }

  window.emgInit=emgStart;
  window.emgStop=emgStop;
  window.emgApply=emgApply;
  window.emgCalibStart=emgCalibStart;
  window.emgCalibReset=emgCalibReset;
  window.utGuideConnect=utGuideConnect;
  window.utGuideExercise=utGuideExercise;
  window.getEmgFeedbackLog=()=>emgFeedbackLog;
  window.clearEmgFeedbackLog=()=>{emgFeedbackLog=[];};
})();

// ── 세션 피드백 리포트 (EMG + 모션 통합) ───────────────────────────────────
function showEmgReport(){
  const log=(window.getEmgFeedbackLog&&window.getEmgFeedbackLog())||[];
  // 모션 피드백: 전역 issueCounter + repScores
  const motionIssues=typeof issueCounter!=="undefined"?{...issueCounter}:{};
  const motionScores=typeof repScores!=="undefined"?[...repScores]:[];
  const hasEmg=log.length>0;
  const hasMotion=Object.keys(motionIssues).length>0||motionScores.length>0;

  const overlay=document.getElementById("emgReportOverlay");
  if(!overlay)return;

  // 둘 다 없으면 표시 안 함
  if(!hasEmg&&!hasMotion){
    window.clearEmgFeedbackLog&&window.clearEmgFeedbackLog();
    return;
  }

  const exerciseKor=document.querySelector(".pill[style*='font-weight:900']")?.textContent||"운동";
  const now=new Date().toLocaleString("ko-KR");
  const totalReps=motionScores.length;
  const avgScore=totalReps?Math.round(motionScores.reduce((a,b)=>a+b,0)/totalReps):0;

  document.getElementById("emgReportMeta").textContent=
    `${exerciseKor} · 종료 ${now} · 총 ${totalReps}회`;

  // ── 요약 통계 ──
  const cnt={부족:0,정상:0,과부하:0,불균형:0};
  log.forEach(e=>{if(cnt[e.type]!==undefined)cnt[e.type]++;});
  const muscles=[...new Set(log.map(e=>e.muscle))];
  const topMotionIssues=Object.entries(motionIssues).sort((a,b)=>b[1]-a[1]).slice(0,3);

  const sumEl=document.getElementById("emgReportSummary");
  sumEl.innerHTML=
    `<div class="emg-report-stat"><div class="label">총 횟수</div><div class="val">${totalReps}</div></div>`+
    `<div class="emg-report-stat"><div class="label">평균 점수</div><div class="val ${avgScore>=80?"good":avgScore>=65?"warn":"danger"}">${avgScore}</div></div>`+
    `<div class="emg-report-stat"><div class="label">EMG 부족</div><div class="val warn">${cnt["부족"]}</div></div>`+
    `<div class="emg-report-stat"><div class="label">EMG 과부하</div><div class="val danger">${cnt["과부하"]}</div></div>`+
    `<div class="emg-report-stat"><div class="label">좌우 불균형</div><div class="val">${cnt["불균형"]}</div></div>`+
    `<div class="emg-report-stat"><div class="label">분석 근육</div><div class="val">${muscles.length}</div></div>`;

  let html="";

  // ── 모션 인식 피드백 섹션 ──
  if(hasMotion){
    html+=`<div style="font-size:12px;font-weight:800;color:#475569;margin-bottom:8px;padding-bottom:4px;border-bottom:2px solid #e2e8f0;">📹 모션 인식 피드백</div>`;
    if(topMotionIssues.length){
      const issueRows=topMotionIssues.map(([iss,cnt])=>
        `<tr>
          <td style="font-weight:700;">${iss}</td>
          <td style="text-align:center;"><span class="emg-badge 과부하" style="background:#fff7ed;color:#c2410c;border-color:#fed7aa;">${cnt}회</span></td>
          <td style="color:#64748b;font-size:11px;">${cnt>=5?"집중 개선 필요":cnt>=3?"주의 필요":"가끔 발생"}</td>
        </tr>`
      ).join("");
      html+=`<table class="emg-report-table" style="margin-bottom:14px;">
        <thead><tr><th>자세 문제</th><th style="text-align:center;">발생</th><th>평가</th></tr></thead>
        <tbody>${issueRows}</tbody>
      </table>`;
    } else {
      html+=`<div style="color:#16a34a;font-size:12px;font-weight:700;padding:8px;background:#f0fdf4;border-radius:8px;margin-bottom:14px;">✓ 자세 문제가 기록되지 않았습니다</div>`;
    }
  }

  // ── EMG 피드백 섹션 ──
  if(hasEmg){
    html+=`<div style="font-size:12px;font-weight:800;color:#475569;margin-bottom:8px;padding-bottom:4px;border-bottom:2px solid #e2e8f0;">⚡ EMG 근육 활성도 피드백</div>`;
    const emgRows=log.map(e=>
      `<tr>
        <td style="color:#94a3b8;font-size:11px;white-space:nowrap;">${e.time}</td>
        <td style="font-weight:700;">${e.muscle}</td>
        <td><span class="emg-badge ${e.type}">${e.type}</span></td>
        <td style="text-align:right;font-weight:800;font-variant-numeric:tabular-nums;">${e.pct}%</td>
        <td style="color:#475569;">${e.msg}</td>
      </tr>`
    ).join("");
    html+=`<table class="emg-report-table">
      <thead><tr>
        <th>시각</th><th>근육</th><th>유형</th><th style="text-align:right;">%MVC</th><th>가이드</th>
      </tr></thead>
      <tbody>${emgRows}</tbody>
    </table>`;
  } else {
    html+=`<div style="color:#64748b;font-size:12px;padding:8px;background:#f8fafc;border-radius:8px;">EMG 피드백이 기록되지 않았습니다 (캘리브레이션 후 운동 시 기록됩니다)</div>`;
  }

  document.getElementById("emgReportTableWrap").innerHTML=html;
  overlay.classList.add("show");
  window.clearEmgFeedbackLog&&window.clearEmgFeedbackLog();
}

function copyEmgReport(){
  const exerciseKor=document.querySelector(".pill[style*='font-weight:900']")?.textContent||"운동";
  const now=new Date().toLocaleString("ko-KR");
  let txt=`[MotionFit 세션 피드백 리포트]\n운동: ${exerciseKor}\n종료: ${now}\n${"═".repeat(50)}\n\n`;

  // 모션 피드백 섹션 — DOM 테이블에서 읽기
  const tables=document.querySelectorAll(".emg-report-table");
  const headers=document.querySelectorAll("#emgReportTableWrap > div");
  let tableIdx=0;
  headers.forEach(h=>{
    txt+=h.textContent.replace(/[📹⚡]/g,"").trim()+"\n"+"─".repeat(40)+"\n";
    const tbl=tables[tableIdx++];
    if(!tbl)return;
    const ths=[...tbl.querySelectorAll("th")].map(t=>t.textContent.trim());
    txt+=ths.join("\t")+"\n";
    tbl.querySelectorAll("tbody tr").forEach(r=>{
      const cells=[...r.querySelectorAll("td")].map(c=>c.textContent.trim());
      txt+=cells.join("\t")+"\n";
    });
    txt+="\n";
  });

  navigator.clipboard.writeText(txt).then(()=>{
    const btn=document.querySelector(".btn-report-copy");
    if(btn){btn.textContent="복사됨 ✓";setTimeout(()=>{btn.textContent="텍스트 복사";},2000);}
  }).catch(()=>{
    alert("클립보드 복사에 실패했습니다. 브라우저 권한을 확인하세요.");
  });
}
</script></body></html>
"""

def ensure_csv_header():
    if not CSV_PATH.exists():
        with CSV_PATH.open("w",newline="",encoding="utf-8-sig") as f:
            csv.writer(f).writerow([
                "saved_at","client_created_at","session_id","save_mode","exercise_key","exercise_kor","set_no",
                "target_reps","total_reps","good_reps","avg_score","grade","set_duration_sec",
                "session_total_sets","session_total_reps","session_total_good_reps","session_avg_score","session_duration_sec",
                "issues_json","issue_counts_json","rep_scores_json","rep_issues_json"
            ])

@app.route("/",methods=["GET","POST"])
def index():
    if request.method=="POST":
        sel=request.form.get("exercise")
        if sel in exercise_names:return redirect(url_for("camera",exercise=sel))
    cards="".join(
        f"<button class='card' type='submit' name='exercise' value='{k}'>"
        f"<div class='row'><span class='tag'>{exercise_meta[k]['tag']}</span><span class='goal'>{exercise_meta[k]['goal']}</span></div>"
        f"<div class='title'>{exercise_names[k]}</div><div class='caption'>{exercise_meta[k]['camera']}</div></button>"
        for k in exercise_names)
    return render_template_string(INDEX_HTML,cards=cards)

@app.route("/camera/<exercise>")
def camera(exercise):
    if exercise not in exercise_names:return redirect(url_for("index"))
    return render_template_string(CAMERA_HTML,exercise_key=exercise,
        exercise_kor=exercise_names[exercise],meta=exercise_meta[exercise],
        tips=exercise_tips[exercise],limitations=exercise_limitations[exercise],
        emg_guide=exercise_emg_guide.get(exercise,None),
        demo_img=exercise_demo.get(exercise,None))

@app.route("/history")
def history():
    sessions=[]
    if CSV_PATH.exists():
        grade_color={"S":"#7c3aed","A":"#16a34a","B":"#d97706","C":"#dc2626"}
        bar_color={"S":"#7c3aed","A":"#16a34a","B":"#d97706","C":"#dc2626"}
        raw={}  # session_id -> session dict
        with CSV_PATH.open(newline="",encoding="utf-8-sig") as f:
            reader=csv.DictReader(f)
            for row in reader:
                sid=row.get("session_id","?")
                if sid not in raw:
                    # client_created_at(ISO UTC) → 한국시간(KST=UTC+9) 표시
                    created_raw=row.get("client_created_at","") or row.get("saved_at","")
                    try:
                        from datetime import timezone,timedelta
                        kst=timezone(timedelta(hours=9))
                        dt_utc=datetime.fromisoformat(created_raw.replace("Z","+00:00"))
                        dt_kst=dt_utc.astimezone(kst)
                        display_at=dt_kst.strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        display_at=created_raw[:16].replace("T"," ")
                    raw[sid]={
                        "session_id":sid,"saved_at":display_at,
                        "exercise_kor":row.get("exercise_kor",""),
                        "total_sets":int(row.get("session_total_sets") or 0),
                        "total_reps":int(row.get("session_total_reps") or 0),
                        "total_good_reps":int(row.get("session_total_good_reps") or 0),
                        "avg_score":int(row.get("session_avg_score") or 0),
                        "sets":[]
                    }
                try:issue_counts=json.loads(row.get("issue_counts_json","{}") or "{}")
                except:issue_counts={}
                try:rep_scores=json.loads(row.get("rep_scores_json","[]") or "[]")
                except:rep_scores=[]
                top_issues=sorted(issue_counts.items(),key=lambda x:-x[1])[:4]
                score=int(row.get("avg_score") or 0)
                grade=row.get("grade","C")
                raw[sid]["sets"].append({
                    "set_no":row.get("set_no",""),
                    "total_reps":int(row.get("total_reps") or 0),
                    "target_reps":int(row.get("target_reps") or 0),
                    "avg_score":score,"grade":grade,
                    "bar_color":bar_color.get(grade,"#94a3b8"),
                    "set_duration_sec":int(row.get("set_duration_sec") or 0),
                    "top_issues":top_issues
                })
        for s in reversed(list(raw.values())):
            g="S" if s["avg_score"]>=90 else "A" if s["avg_score"]>=80 else "B" if s["avg_score"]>=65 else "C"
            tr=s["total_reps"];tg=sum(r["target_reps"] for r in s["sets"])
            s["grade"]=g;s["grade_color"]=grade_color.get(g,"#94a3b8")
            s["achieve_pct"]=round(tr/tg*100) if tg>0 else 0
            # 세트별 실측 시간 합산으로 운동 시간 계산
            actual_dur=sum(r["set_duration_sec"] for r in s["sets"])
            s["duration_str"]=f"{actual_dur//60}분 {actual_dur%60}초" if actual_dur>=60 else f"{actual_dur}초"
            sessions.append(s)
    return render_template_string(HISTORY_HTML,sessions=sessions)

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)

@app.route("/api/save-session",methods=["POST"])
def save_session():
    try:
        payload=request.get_json(force=True)
        if not payload:
            return jsonify({"ok":False,"message":"요청 본문이 비어있거나 JSON이 아닙니다."}),400
        sets=payload.get("sets",[])
        if not sets:return jsonify({"ok":False,"message":"저장할 세트 기록이 없습니다."}),400
        ensure_csv_header();saved_at=datetime.now().isoformat(timespec="seconds")
        summary=payload.get("session_summary",{})
        with CSV_PATH.open("a",newline="",encoding="utf-8-sig") as f:
            w=csv.writer(f)
            for r in sets:
                w.writerow([
                    saved_at,payload.get("created_at",""),payload.get("session_id",""),payload.get("save_mode","manual"),
                    payload.get("exercise_key",""),payload.get("exercise_kor",""),
                    r.get("set_no",""),r.get("target_reps",""),r.get("total_reps",""),
                    r.get("good_reps",""),r.get("avg_score",""),r.get("grade",""),r.get("set_duration_sec",""),
                    summary.get("total_sets",""),summary.get("total_reps",""),summary.get("total_good_reps",""),
                    summary.get("avg_score",""),summary.get("session_duration_sec",""),
                    json.dumps(r.get("issues",[]),ensure_ascii=False),
                    json.dumps(r.get("issue_counts",{}),ensure_ascii=False),
                    json.dumps(r.get("rep_scores",[]),ensure_ascii=False),
                    json.dumps(r.get("rep_issues",[]),ensure_ascii=False)
                ])
        return jsonify({"ok":True,"message":f"{len(sets)}개 세트 기록을 저장했습니다."})
    except Exception as e:
        import traceback;traceback.print_exc()
        return jsonify({"ok":False,"message":f"서버 오류: {str(e)}"}),500

_EMG_HTML_UNUSED = """
<!DOCTYPE html><html lang="ko"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>EMG 모니터 — Motion Fit</title>
<style>
:root{
  --bg:#0f172a;--panel:#1e293b;--line:#334155;--text:#f1f5f9;--muted:#94a3b8;
  --accent:#3b82f6;--good:#22c55e;--warn:#f59e0b;--bad:#ef4444;
  --shadow:0 4px 24px rgba(0,0,0,.4);
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:Inter,"Segoe UI","Apple SD Gothic Neo",sans-serif;min-height:100vh;}
.shell{max-width:1200px;margin:0 auto;padding:24px 20px;}

/* 헤더 */
.topbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;flex-wrap:wrap;gap:12px;}
.brand{display:flex;align-items:center;gap:10px;}
.brand-dot{width:10px;height:10px;border-radius:50%;background:var(--good);box-shadow:0 0 8px var(--good);animation:pulse 1.5s infinite;}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.6;transform:scale(1.3)}}
.brand-text{font-size:18px;font-weight:800;letter-spacing:.04em;color:var(--text);}
.brand-sub{font-size:12px;color:var(--muted);font-weight:500;}
a.back{display:inline-flex;align-items:center;gap:6px;padding:8px 16px;border-radius:999px;border:1px solid var(--line);background:var(--panel);text-decoration:none;color:var(--muted);font-size:13px;font-weight:700;transition:.15s;}
a.back:hover{color:var(--text);border-color:var(--text);}

/* 상태 배지 */
.status-row{display:flex;gap:10px;margin-bottom:20px;flex-wrap:wrap;}
.badge{display:inline-flex;align-items:center;gap:6px;padding:8px 14px;border-radius:12px;font-size:12px;font-weight:700;border:1px solid var(--line);background:var(--panel);}
.badge.connected{border-color:var(--good);color:var(--good);}
.badge.disconnected{border-color:var(--bad);color:var(--bad);}
.badge .dot{width:7px;height:7px;border-radius:50%;background:currentColor;}

/* 메인 레이아웃 */
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;}
.grid-3{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:16px;}

/* 패널 */
.panel{background:var(--panel);border:1px solid var(--line);border-radius:20px;padding:20px;box-shadow:var(--shadow);}
.panel-title{font-size:12px;font-weight:700;color:var(--muted);letter-spacing:.08em;text-transform:uppercase;margin-bottom:16px;display:flex;align-items:center;gap:6px;}
.panel-title .icon{font-size:14px;}

/* 큰 숫자 표시 */
.big-val{font-size:52px;font-weight:900;letter-spacing:-.04em;line-height:1;font-variant-numeric:tabular-nums;}
.big-unit{font-size:14px;color:var(--muted);font-weight:600;margin-top:4px;}
.big-label{font-size:13px;color:var(--muted);margin-top:8px;}

/* 채널별 바 */
.ch-list{display:flex;flex-direction:column;gap:10px;}
.ch-item{display:flex;align-items:center;gap:10px;}
.ch-name{font-size:12px;font-weight:700;color:var(--muted);width:32px;flex-shrink:0;}
.ch-bar-wrap{flex:1;height:16px;background:rgba(255,255,255,.06);border-radius:8px;overflow:hidden;}
.ch-bar{height:100%;border-radius:8px;transition:width .1s ease;background:var(--accent);}
.ch-val{font-size:12px;font-weight:700;font-variant-numeric:tabular-nums;width:52px;text-align:right;color:var(--text);}

/* 파형 캔버스 */
.waveform-wrap{position:relative;width:100%;height:180px;border-radius:12px;overflow:hidden;background:rgba(0,0,0,.3);}
canvas.waveform{width:100%;height:100%;display:block;}
.wave-label{position:absolute;top:8px;left:10px;font-size:11px;font-weight:700;color:var(--accent);opacity:.7;}
.wave-zero{position:absolute;top:50%;left:0;right:0;height:1px;background:rgba(255,255,255,.08);pointer-events:none;}

/* 통계 */
.stat-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
.stat-item{background:rgba(255,255,255,.04);border-radius:12px;padding:14px;}
.stat-val{font-size:22px;font-weight:800;font-variant-numeric:tabular-nums;}
.stat-lbl{font-size:11px;color:var(--muted);font-weight:600;margin-top:3px;}

/* 로그 */
.log-box{background:rgba(0,0,0,.3);border-radius:12px;padding:14px;height:140px;overflow-y:auto;font-size:12px;font-family:"JetBrains Mono",monospace,sans-serif;line-height:1.7;}
.log-box::-webkit-scrollbar{width:4px}
.log-box::-webkit-scrollbar-thumb{background:var(--line);border-radius:2px}
.log-line{color:var(--muted);}
.log-line.ok{color:var(--good);}
.log-line.err{color:var(--bad);}
.log-line .ts{color:var(--accent);margin-right:6px;}

/* 설정 섹션 */
.cfg-row{display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap;}
.cfg-row label{font-size:12px;color:var(--muted);font-weight:600;width:60px;}
.cfg-row input{background:rgba(255,255,255,.08);border:1px solid var(--line);border-radius:8px;padding:6px 10px;color:var(--text);font-size:13px;font-weight:700;width:130px;outline:none;}
.cfg-row input:focus{border-color:var(--accent);}
.btn{padding:8px 18px;border-radius:10px;border:none;cursor:pointer;font-size:13px;font-weight:700;transition:.15s;}
.btn.primary{background:var(--accent);color:#fff;}
.btn.primary:hover{filter:brightness(1.1);}
.btn.danger{background:var(--bad);color:#fff;}
.btn.danger:hover{filter:brightness(1.1);}
.btn.ghost{background:transparent;border:1px solid var(--line);color:var(--muted);}
.btn.ghost:hover{color:var(--text);border-color:var(--text);}

@media(max-width:768px){
  .grid,.grid-3{grid-template-columns:1fr}
  .big-val{font-size:36px}
}
</style>
</head><body>
<div class="shell">

  <!-- 헤더 -->
  <div class="topbar">
    <div class="brand">
      <div class="brand-dot" id="liveDot"></div>
      <div>
        <div class="brand-text">EMG 실시간 모니터</div>
        <div class="brand-sub">Motion Fit · 근전도 신호 시각화</div>
      </div>
    </div>
    <a class="back" href="/">← 운동 선택으로</a>
  </div>

  <!-- 연결 상태 배지 -->
  <div class="status-row">
    <div class="badge disconnected" id="connBadge"><div class="dot"></div><span id="connText">연결 대기 중</span></div>
    <div class="badge" id="ipBadge" style="color:var(--muted)">🌐 <span id="ipText">127.0.0.1:8080</span></div>
    <div class="badge" style="color:var(--muted)">📡 <span id="rateText">— Hz</span></div>
    <div class="badge" style="color:var(--muted)">⏱ 업데이트: <span id="lastUpdate">—</span></div>
  </div>

  <!-- 상단 3칸: 채널별 현재값 / 파형 -->
  <div class="grid" style="grid-template-columns:1fr 2fr">

    <!-- 채널별 바 -->
    <div class="panel">
      <div class="panel-title"><span class="icon">📊</span> 채널별 현재값</div>
      <div class="ch-list" id="chList">
        <!-- JS로 동적 생성 -->
        <div style="color:var(--muted);font-size:13px;">데이터 수신 대기 중…</div>
      </div>
    </div>

    <!-- 파형 -->
    <div class="panel">
      <div class="panel-title"><span class="icon">〰️</span> 실시간 파형</div>
      <div class="waveform-wrap">
        <div class="wave-label" id="waveLabel">CH 1</div>
        <div class="wave-zero"></div>
        <canvas class="waveform" id="waveCanvas"></canvas>
      </div>
      <!-- 채널 선택 버튼 -->
      <div style="display:flex;gap:6px;margin-top:12px;flex-wrap:wrap;" id="chBtns"></div>
    </div>
  </div>

  <!-- 통계 + RMS 피크 + 로그 -->
  <div class="grid-3">

    <!-- 통계 -->
    <div class="panel">
      <div class="panel-title"><span class="icon">📈</span> 세션 통계</div>
      <div class="stat-grid">
        <div class="stat-item"><div class="stat-val" id="statPeak" style="color:var(--warn)">—</div><div class="stat-lbl">피크값</div></div>
        <div class="stat-item"><div class="stat-val" id="statMin" style="color:var(--accent)">—</div><div class="stat-lbl">최솟값</div></div>
        <div class="stat-item"><div class="stat-val" id="statAvg">—</div><div class="stat-lbl">평균</div></div>
        <div class="stat-item"><div class="stat-val" id="statCnt" style="color:var(--good)">0</div><div class="stat-lbl">수신 샘플</div></div>
      </div>
    </div>

    <!-- RMS -->
    <div class="panel">
      <div class="panel-title"><span class="icon">⚡</span> RMS (근활성도)</div>
      <div class="big-val" id="rmsVal" style="color:var(--good)">—</div>
      <div class="big-unit">μV (RMS)</div>
      <div class="big-label">최근 50 샘플 기준</div>
    </div>

    <!-- 로그 -->
    <div class="panel">
      <div class="panel-title"><span class="icon">🖥️</span> 수신 로그</div>
      <div class="log-box" id="logBox"></div>
    </div>

  </div>

  <!-- 설정 -->
  <div class="panel">
    <div class="panel-title"><span class="icon">⚙️</span> 연결 설정</div>
    <div class="cfg-row">
      <label>IP</label>
      <input type="text" id="cfgIP" value="127.0.0.1">
    </div>
    <div class="cfg-row">
      <label>PORT</label>
      <input type="text" id="cfgPort" value="8080">
    </div>
    <div class="cfg-row">
      <label>간격</label>
      <input type="number" id="cfgInterval" value="100" min="50" max="2000"> ms
    </div>
    <div style="display:flex;gap:8px;margin-top:8px;">
      <button class="btn primary" onclick="applySettings()">적용 · 재연결</button>
      <button class="btn danger" onclick="stopPolling()">중지</button>
      <button class="btn ghost" onclick="clearStats()">통계 초기화</button>
    </div>
  </div>

</div>

<script>
// ── 설정 ──────────────────────────────────────────
let IP = "127.0.0.1";
let PORT = "8080";
let INTERVAL = 100;
let selectedCh = 0;       // 파형에 표시할 채널 인덱스
let pollingTimer = null;

// ── 파형 버퍼 ─────────────────────────────────────
const WAVE_LEN = 300;
let waveBuffers = [];      // waveBuffers[ch] = Float32Array
let rmsBuffer = [];        // 최근 50 샘플 (채널 0 기준)
const RMS_N = 50;

// ── 통계 ─────────────────────────────────────────
let sampleCount = 0;
let allPeak = -Infinity;
let allMin = Infinity;
let allSum = 0;
let requestTimes = [];    // Hz 계산용

// ── 유틸 ─────────────────────────────────────────
function now() {
  const d = new Date();
  return d.toTimeString().slice(0,8) + "." + String(d.getMilliseconds()).padStart(3,"0");
}
function addLog(msg, type="") {
  const box = document.getElementById("logBox");
  const line = document.createElement("div");
  line.className = "log-line " + type;
  line.innerHTML = `<span class="ts">${now()}</span>${msg}`;
  box.appendChild(line);
  if (box.children.length > 120) box.removeChild(box.firstChild);
  box.scrollTop = box.scrollHeight;
}

// ── 채널 UI 초기화 ────────────────────────────────
function initChannels(n) {
  const list = document.getElementById("chList");
  const btns = document.getElementById("chBtns");
  list.innerHTML = "";
  btns.innerHTML = "";
  waveBuffers = [];
  for (let i = 0; i < n; i++) {
    waveBuffers.push(new Float32Array(WAVE_LEN));

    // 바
    const item = document.createElement("div");
    item.className = "ch-item";
    const colors = ["#3b82f6","#22c55e","#f59e0b","#ef4444","#a78bfa","#ec4899","#06b6d4","#84cc16"];
    const col = colors[i % colors.length];
    item.innerHTML = `
      <div class="ch-name">CH${i+1}</div>
      <div class="ch-bar-wrap"><div class="ch-bar" id="chBar${i}" style="width:0%;background:${col}"></div></div>
      <div class="ch-val" id="chVal${i}">—</div>
    `;
    list.appendChild(item);

    // 버튼
    const btn = document.createElement("button");
    btn.className = "btn ghost";
    btn.id = "chBtn" + i;
    btn.textContent = "CH " + (i+1);
    btn.style.cssText = `font-size:11px;padding:5px 10px;border-radius:8px;background:${i===selectedCh?"rgba(59,130,246,.2)":"transparent"};border-color:${i===selectedCh?col:""};color:${col}`;
    btn.onclick = () => selectChannel(i, col);
    btns.appendChild(btn);
  }
}

function selectChannel(i, col) {
  selectedCh = i;
  document.querySelectorAll("#chBtns .btn").forEach((b, idx) => {
    b.style.background = idx === i ? "rgba(59,130,246,.2)" : "transparent";
  });
  document.getElementById("waveLabel").textContent = "CH " + (i+1);
}

// ── 파형 그리기 ───────────────────────────────────
const canvas = document.getElementById("waveCanvas");
const ctx = canvas.getContext("2d");
const colors = ["#3b82f6","#22c55e","#f59e0b","#ef4444","#a78bfa","#ec4899","#06b6d4","#84cc16"];

function resizeCanvas() {
  canvas.width = canvas.offsetWidth * devicePixelRatio;
  canvas.height = canvas.offsetHeight * devicePixelRatio;
}
window.addEventListener("resize", resizeCanvas);
resizeCanvas();

function drawWave() {
  const W = canvas.width, H = canvas.height;
  ctx.clearRect(0, 0, W, H);

  if (!waveBuffers.length) { requestAnimationFrame(drawWave); return; }

  const buf = waveBuffers[selectedCh];
  const col = colors[selectedCh % colors.length];

  // 범위 계산
  let lo = Infinity, hi = -Infinity;
  for (let v of buf) { if (v < lo) lo = v; if (v > hi) hi = v; }
  const span = Math.max(hi - lo, 1);
  const pad = span * 0.15;

  // 그리드
  ctx.strokeStyle = "rgba(255,255,255,0.05)";
  ctx.lineWidth = 1;
  for (let g = 0; g <= 4; g++) {
    const y = (g / 4) * H;
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
  }

  // 중심선
  const midY = H / 2;
  ctx.strokeStyle = "rgba(255,255,255,0.1)";
  ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(0, midY); ctx.lineTo(W, midY); ctx.stroke();

  // 파형
  const gradient = ctx.createLinearGradient(0, 0, W, 0);
  gradient.addColorStop(0, col + "44");
  gradient.addColorStop(0.5, col);
  gradient.addColorStop(1, col + "44");

  ctx.strokeStyle = gradient;
  ctx.lineWidth = 1.8 * devicePixelRatio;
  ctx.lineJoin = "round";
  ctx.beginPath();
  for (let i = 0; i < WAVE_LEN; i++) {
    const x = (i / (WAVE_LEN - 1)) * W;
    const norm = (buf[i] - lo + pad) / (span + 2 * pad);
    const y = H - norm * H;
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }
  ctx.stroke();

  // 현재값 점
  const lastVal = buf[WAVE_LEN - 1];
  const norm = (lastVal - lo + pad) / (span + 2 * pad);
  const y = H - norm * H;
  ctx.beginPath();
  ctx.arc(W, y, 4 * devicePixelRatio, 0, Math.PI * 2);
  ctx.fillStyle = col;
  ctx.fill();

  requestAnimationFrame(drawWave);
}
drawWave();

// ── EMG 데이터 수신 ───────────────────────────────
let initialized = false;

async function getEMGData() {
  try {
    const t0 = performance.now();
    const response = await fetch(`http://${IP}:${PORT}/samples`);
    const data = await response.json();

    // Hz 추적
    requestTimes.push(t0);
    if (requestTimes.length > 20) requestTimes.shift();
    if (requestTimes.length >= 2) {
      const elapsed = (performance.now() - requestTimes[0]) / 1000;
      const hz = (requestTimes.length - 1) / elapsed;
      document.getElementById("rateText").textContent = hz.toFixed(1) + " Hz";
    }

    // 채널 배열 정규화
    let channels = [];
    if (Array.isArray(data)) {
      channels = data;
    } else if (data && typeof data === "object") {
      if (data.samples) channels = Array.isArray(data.samples[0]) ? data.samples[data.samples.length-1] : data.samples;
      else if (data.channels) channels = data.channels;
      else channels = Object.values(data).filter(v => typeof v === "number");
    }
    if (!channels.length) { addLog("데이터 형식 불명: " + JSON.stringify(data).slice(0,60), "err"); return; }

    // 채널 초기화
    if (!initialized || waveBuffers.length !== channels.length) {
      initChannels(channels.length);
      initialized = true;
      addLog(`채널 ${channels.length}개 감지`, "ok");
    }

    // 연결 상태
    const badge = document.getElementById("connBadge");
    badge.className = "badge connected";
    document.getElementById("connText").textContent = "연결됨";
    document.getElementById("liveDot").style.background = "var(--good)";
    document.getElementById("liveDot").style.boxShadow = "0 0 8px var(--good)";
    document.getElementById("lastUpdate").textContent = now();

    // 버퍼·UI 업데이트
    channels.forEach((val, i) => {
      if (i >= waveBuffers.length) return;
      val = Number(val);

      // 버퍼 shift
      waveBuffers[i].copyWithin(0, 1);
      waveBuffers[i][WAVE_LEN - 1] = val;

      // 채널 바 & 값
      const lo = Math.min(...waveBuffers[i]);
      const hi = Math.max(...waveBuffers[i]);
      const pct = hi > lo ? ((val - lo) / (hi - lo)) * 100 : 50;
      const barEl = document.getElementById("chBar" + i);
      const valEl = document.getElementById("chVal" + i);
      if (barEl) barEl.style.width = pct.toFixed(1) + "%";
      if (valEl) valEl.textContent = val.toFixed ? val.toFixed(2) : val;
    });

    // RMS (채널 0)
    rmsBuffer.push(Number(channels[0]));
    if (rmsBuffer.length > RMS_N) rmsBuffer.shift();
    const rms = Math.sqrt(rmsBuffer.reduce((s, v) => s + v*v, 0) / rmsBuffer.length);
    document.getElementById("rmsVal").textContent = isNaN(rms) ? "—" : rms.toFixed(2);

    // 통계
    sampleCount++;
    const v0 = Number(channels[0]);
    if (v0 > allPeak) allPeak = v0;
    if (v0 < allMin) allMin = v0;
    allSum += v0;
    document.getElementById("statPeak").textContent = allPeak.toFixed(2);
    document.getElementById("statMin").textContent = allMin.toFixed(2);
    document.getElementById("statAvg").textContent = (allSum / sampleCount).toFixed(2);
    document.getElementById("statCnt").textContent = sampleCount;

    // 로그 (10개마다)
    if (sampleCount % 10 === 0) addLog("CH: " + channels.map(v => Number(v).toFixed(1)).join(", "), "ok");

  } catch (error) {
    document.getElementById("connBadge").className = "badge disconnected";
    document.getElementById("connText").textContent = "연결 대기";
    document.getElementById("liveDot").style.background = "var(--bad)";
    document.getElementById("liveDot").style.boxShadow = "0 0 8px var(--bad)";
    // 연결 실패는 로그에 조용히 기록 (반복 노이즈 방지)
    if (!window._lastErrLog || Date.now() - window._lastErrLog > 5000) {
      addLog("EMG 센서 연결 대기 중…", "err");
      window._lastErrLog = Date.now();
    }
  }
}

// ── 컨트롤 ───────────────────────────────────────
function startPolling() {
  if (pollingTimer) clearInterval(pollingTimer);
  pollingTimer = setInterval(getEMGData, INTERVAL);
  getEMGData();
  addLog(`폴링 시작 (${IP}:${PORT}, ${INTERVAL}ms)`, "ok");
}

function stopPolling() {
  if (pollingTimer) { clearInterval(pollingTimer); pollingTimer = null; }
  document.getElementById("connBadge").className = "badge disconnected";
  document.getElementById("connText").textContent = "중지됨";
  addLog("폴링 중지", "err");
}

function applySettings() {
  IP = document.getElementById("cfgIP").value.trim() || "127.0.0.1";
  PORT = document.getElementById("cfgPort").value.trim() || "8080";
  INTERVAL = parseInt(document.getElementById("cfgInterval").value) || 100;
  document.getElementById("ipText").textContent = IP + ":" + PORT;
  startPolling();
}

function clearStats() {
  sampleCount = 0; allPeak = -Infinity; allMin = Infinity; allSum = 0; rmsBuffer = [];
  document.getElementById("statPeak").textContent = "—";
  document.getElementById("statMin").textContent = "—";
  document.getElementById("statAvg").textContent = "—";
  document.getElementById("statCnt").textContent = "0";
  document.getElementById("rmsVal").textContent = "—";
  addLog("통계 초기화", "");
}

// ── 시작 ─────────────────────────────────────────
addLog("EMG 모니터 준비됨. 아래 설정을 확인하고 [적용·재연결]을 누르세요.");
startPolling();
</script>
</body></html>
"""


if __name__=="__main__":
    print("RUNNING_MOTIONFIT_v4.0")
    try:
        from pyngrok import ngrok
        public_url = ngrok.connect(5001)
        print(f"공개 URL: {public_url}")
    except Exception:
        pass
    app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False)
