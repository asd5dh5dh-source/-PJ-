from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


BASE = Path(r"C:\Users\POSCOFUTUREM\Documents\Codex\2026-08-13\new-chat-3")
OUTPUT = BASE / "outputs" / "고객_대응_플랫폼_프로젝트_기획서.pdf"

NAVY = colors.HexColor("#17365D")
BLUE = colors.HexColor("#2F75B5")
LIGHT_BLUE = colors.HexColor("#DCE6F1")
PALE_BLUE = colors.HexColor("#EEF4FA")
GREEN = colors.HexColor("#4F7C57")
LIGHT_GREEN = colors.HexColor("#E8F2E8")
AMBER = colors.HexColor("#A66B18")
LIGHT_AMBER = colors.HexColor("#FFF2CC")
RED = colors.HexColor("#A94442")
LIGHT_RED = colors.HexColor("#F8E6E6")
MID = colors.HexColor("#6B7280")
LIGHT = colors.HexColor("#F4F6F8")
DARK = colors.HexColor("#1F2937")
GRID = colors.HexColor("#CBD5E1")

pdfmetrics.registerFont(TTFont("Malgun", r"C:\Windows\Fonts\malgun.ttf"))
pdfmetrics.registerFont(TTFont("Malgun-Bold", r"C:\Windows\Fonts\malgunbd.ttf"))

styles = getSampleStyleSheet()
TITLE = ParagraphStyle(
    "TitleKo", parent=styles["Title"], fontName="Malgun-Bold", fontSize=25,
    leading=33, textColor=NAVY, alignment=TA_LEFT, spaceAfter=6 * mm,
)
SUBTITLE = ParagraphStyle(
    "SubtitleKo", parent=styles["Normal"], fontName="Malgun", fontSize=12,
    leading=18, textColor=MID, spaceAfter=8 * mm,
)
H1 = ParagraphStyle(
    "H1Ko", parent=styles["Heading1"], fontName="Malgun-Bold", fontSize=17,
    leading=23, textColor=NAVY, spaceBefore=0, spaceAfter=4 * mm,
)
H2 = ParagraphStyle(
    "H2Ko", parent=styles["Heading2"], fontName="Malgun-Bold", fontSize=11.5,
    leading=16, textColor=BLUE, spaceBefore=3.5 * mm, spaceAfter=2 * mm,
)
BODY = ParagraphStyle(
    "BodyKo", parent=styles["BodyText"], fontName="Malgun", fontSize=9.2,
    leading=14.5, textColor=DARK, spaceAfter=2.2 * mm, wordWrap="CJK",
)
SMALL = ParagraphStyle(
    "SmallKo", parent=BODY, fontSize=7.8, leading=11.5, spaceAfter=1 * mm,
)
TABLE_HEAD = ParagraphStyle(
    "TableHeadKo", parent=SMALL, fontName="Malgun-Bold", textColor=colors.white,
    alignment=TA_CENTER, leading=11,
)
TABLE_BODY = ParagraphStyle(
    "TableBodyKo", parent=SMALL, fontSize=7.7, leading=11.2, spaceAfter=0,
)
TABLE_CENTER = ParagraphStyle(
    "TableCenterKo", parent=TABLE_BODY, alignment=TA_CENTER,
)
CALLOUT = ParagraphStyle(
    "CalloutKo", parent=BODY, fontName="Malgun-Bold", fontSize=10,
    leading=15, textColor=NAVY, spaceAfter=0,
)
CAPTION = ParagraphStyle(
    "CaptionKo", parent=SMALL, fontSize=7.2, leading=10, textColor=MID,
    alignment=TA_CENTER,
)


def P(text, style=BODY):
    return Paragraph(text, style)


def bullet(text):
    return Paragraph(f"• {text}", BODY)


def section_title(num, title):
    return P(f"{num}. {title}", H1)


def callout(text, fill=PALE_BLUE, border=BLUE):
    t = Table([[P(text, CALLOUT)]], colWidths=[171 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), fill),
        ("BOX", (0, 0), (-1, -1), 0.8, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


def data_table(rows, widths, header=True, font_size=7.7):
    cooked = []
    for r_idx, row in enumerate(rows):
        cooked.append([
            P(str(cell), TABLE_HEAD if header and r_idx == 0 else TABLE_BODY)
            for cell in row
        ])
    t = Table(cooked, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    cmds = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.35, GRID),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        cmds += [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ]
        for r in range(1, len(rows)):
            if r % 2 == 0:
                cmds.append(("BACKGROUND", (0, r), (-1, r), LIGHT))
    t.setStyle(TableStyle(cmds))
    return t


def status_table():
    rows = [
        ["구분", "현재 상태", "판정"],
        ["VOC 데이터", "시뮬레이션 150건 구성, DB 135건/Test 15건 분리", "완료"],
        ["검색 프로토타입", "Sentence Transformer 및 BM25 Top 3 비교", "완료"],
        ["점수 보정", "BM25 Type 일치 10% 가점 산식", "설계 완료"],
        ["웹 플랫폼", "업무 흐름·UI 기본 구성, Stitch 상세 조정", "설계 단계"],
    ]
    t = data_table(rows, [31 * mm, 105 * mm, 35 * mm])
    t.setStyle(TableStyle([
        ("TEXTCOLOR", (2, 1), (2, 2), GREEN),
        ("TEXTCOLOR", (2, 3), (2, 4), AMBER),
        ("FONTNAME", (2, 1), (2, -1), "Malgun-Bold"),
        ("ALIGN", (2, 1), (2, -1), "CENTER"),
    ]))
    return t


def on_page(canvas, doc):
    canvas.saveState()
    w, h = A4
    if doc.page > 1:
        canvas.setStrokeColor(LIGHT_BLUE)
        canvas.setLineWidth(0.6)
        canvas.line(20 * mm, h - 15 * mm, w - 20 * mm, h - 15 * mm)
        canvas.setFont("Malgun", 7.5)
        canvas.setFillColor(MID)
        canvas.drawString(20 * mm, h - 11.5 * mm, "고객 대응 플랫폼 프로젝트 기획서")
    canvas.setFont("Malgun", 7.5)
    canvas.setFillColor(MID)
    canvas.drawRightString(w - 20 * mm, 12 * mm, f"{doc.page} / 7")
    canvas.restoreState()


def build():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(OUTPUT), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=18 * mm, title="고객 대응 플랫폼 프로젝트 기획서",
        author="양극재품질그룹",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="report", frames=frame, onPage=on_page)])
    story = []

    # Page 1 - Cover and executive summary
    story += [Spacer(1, 12 * mm), P("고객 대응 플랫폼<br/>프로젝트 기획서", TITLE)]
    story += [P("VOC 데이터 재구성 · 유사사례 검색 검증 · 웹 협업 플랫폼 설계", SUBTITLE)]
    story += [callout(
        "핵심 결론: 대외비를 보호한 시뮬레이션 VOC 150건과 유사사례 검색 프로토타입을 구축했다. "
        "현재 데이터에서는 BM25가 핵심 업무 키워드를 구분하는 데 더 실용적이었으며, 다음 단계는 Type 가점 검증과 웹 플랫폼 구현이다."
    )]
    story += [Spacer(1, 8 * mm), P("Executive Summary", H1)]
    story += [P(
        "고객 메일은 비정형 문장으로 접수되기 때문에 담당자가 고객사, 제품, 요청 유형, 회신 기한과 필요한 조치를 직접 파악해야 한다. "
        "본 프로젝트는 과거 VOC 중 업무적으로 참고할 수 있는 Top 3 사례를 제시하고, 향후 유관부서 배정부터 고객 회신·종결까지 하나의 플랫폼에서 관리하는 것을 목표로 한다."
    )]
    story += [status_table()]
    story += [Spacer(1, 5 * mm), P(
        "본 문서는 실제 완료된 데이터·검색 검증과 향후 구현할 웹 플랫폼을 구분한다. 비전공 의사결정자는 각 페이지의 결론을, 개발 검토자는 데이터·알고리즘 근거를 확인할 수 있도록 구성하였다.", SMALL
    )]
    story.append(PageBreak())

    # Page 2 - Problem and system overview
    story += [section_title("1", "프로젝트 개요 및 목적")]
    story += [P("현업 문제", H2)]
    story += [bullet("과거 유사 사례를 찾기 위해 메일과 대응 이력을 수작업으로 검색해야 한다.")]
    story += [bullet("담당자의 경험에 따라 대응 방향과 유관부서 선정이 달라질 수 있다.")]
    story += [bullet("여러 부서의 진행 상태, 고객 회신과 종결 이력이 분산되어 기한 관리가 어렵다.")]
    story += [P("최종 목표", H2)]
    story += [P(
        "고객 메일 입력 후 핵심 정보를 확인·보정하고, 완료된 과거 VOC 중 Top 3를 조회한 뒤, 하나 이상의 유관부서에 업무를 배정하고 종결까지 진행 상황을 관리하는 협업 플랫폼을 구축한다."
    )]
    story += [P("전체 시스템 구성", H2)]
    system_rows = [
        ["단계", "역할", "현재 상태"],
        ["프론트엔드", "메일 입력, 정보 확정, Top 3 조회, 배정·진척·아카이브", "UI 설계 완료"],
        ["백엔드", "입력 검증, 텍스트 정제, BM25 실행, 결과·이력 저장", "구현 예정"],
        ["데이터베이스", "VOC, 신규 요청, 부서 배정, 진행 이력, 기준정보 관리", "적재 자료 준비"],
        ["검색", "Sentence Transformer와 BM25 비교, Top 3 산출", "프로토타입 완료"],
    ]
    story += [data_table(system_rows, [29 * mm, 105 * mm, 37 * mm])]
    story += [Spacer(1, 5 * mm), callout(
        "현재 단계의 중심 성과는 데이터와 검색 가능성 검증이다. Next.js·FastAPI 실행 코드는 아직 없으며, Stitch 화면 조정 후 Codex로 구현한다.",
        fill=LIGHT_AMBER, border=AMBER,
    )]
    story += [P("사용자가 최종적으로 할 수 있는 일", H2)]
    story += [bullet("메일 붙여넣기와 고객사·제품·VOC 정보 확인")]
    story += [bullet("과거 Top 3 사례와 당시 대응 부서 참고")]
    story += [bullet("제조·기술·정비·품질 부서 병렬 배정과 기한 지정")]
    story += [bullet("진척·첨부·고객 회신·종결·재접수 이력 관리")]
    story.append(PageBreak())

    # Page 3 - Data and preprocessing
    story += [section_title("2", "데이터 구성 및 전처리")]
    story += [callout(
        "실제 고객 메일은 대외비 문제로 사용하지 않았다. 실제 업무 유형과 처리 흐름을 참고해 최대한 유사한 시뮬레이션 VOC 150건을 재구성했다."
    )]
    story += [Spacer(1, 4 * mm)]
    dataset_rows = [
        ["구분", "건수", "구성·용도"],
        ["전체", "150", "Complaint 52 · Request 50 · Inquiry 48"],
        ["DB", "135", "검색 후보 및 Supabase/PostgreSQL 적재 대상"],
        ["Test", "15", "각 유형 5건, DB와 Case ID 중복 없음"],
    ]
    story += [data_table(dataset_rows, [31 * mm, 22 * mm, 118 * mm])]
    story += [P("핵심 데이터 22개 컬럼", H2)]
    col_rows = [
        ["영역", "주요 컬럼", "의미"],
        ["식별·분류", "Case ID, Customer, Country, VOC Type/Subtype, Priority", "사례 식별과 업무 분류"],
        ["요청", "Customer Request, Original Mail Body", "한글 요약과 다국어 원문"],
        ["대응", "Responsible Dept., First Response, Containment, Root Cause", "담당부서와 단계별 조치"],
        ["상태·이력", "Final Status, Delay, Auto Close, Reactivated, Full History", "진행·예외·종결 이력"],
    ]
    story += [data_table(col_rows, [28 * mm, 71 * mm, 72 * mm])]
    story += [P("실제로 수행한 전처리", H2)]
    preprocess = [
        ("업무 유형 구조화", "Complaint·Request·Inquiry와 Subtype으로 구분해 대응 절차 차이를 반영"),
        ("요청 요약", "다국어 원문에서 배경·핵심 요청·회신 기한을 한국어 Customer Request로 구성"),
        ("이력 통합", "단계별 날짜와 조치를 Full Response History로 시간순 결합"),
        ("DB 형식 정리", "업로드 파일 컬럼명을 snake_case로 변환하고 빈 Case ID 행 제외"),
        ("검색 입력 변환", "Sentence Transformer용 결합 텍스트 또는 BM25용 정제 토큰 생성"),
    ]
    for name, desc in preprocess:
        story += [P(f"<b>{name}</b> - {desc}", BODY)]
    story += [P(
        "수치 표준화, 시계열 Window, 모델 재학습, 결측치 임의 대체는 수행하지 않았다. Containment·5D·6D의 일부 공란은 유형 또는 진행 상태에 따라 해당 단계가 없는 구조적 공란으로 보존했다.", SMALL
    )]
    story.append(PageBreak())

    # Page 4 - Algorithm validation
    story += [section_title("3", "AI 모델 및 검색 알고리즘 검증")]
    method_rows = [
        ["구분", "입력·처리", "확인 결과", "상태"],
        ["1안 Sentence Transformer", "요청 요약+원문+처리 이력 → 다국어 384차원 벡터 → 코사인 유사도", "의미·언어 차이를 반영하나 일부 업무 유형·핵심어 구분이 약함", "검증 완료"],
        ["2안 BM25", "VOC Type+Subtype+요청 요약 → 키워드 점수", "현재 데이터에서 명시적 업무 키워드 구분이 더 실용적", "검증 완료"],
        ["3안 점수 보정", "BM25 × (1 + TypeMatch × 0.10)", "BM25 변별력 유지 + 동일 업무 유형 우선", "설계 완료"],
    ]
    story += [data_table(method_rows, [30 * mm, 62 * mm, 53 * mm, 26 * mm])]
    story += [P("1안: 다국어 Sentence Transformer", H2)]
    story += [P(
        "직접 학습한 모델이 아니라 사전학습 모델을 활용했다. 서로 다른 언어의 VOC를 384개의 숫자 좌표로 변환하고 코사인 유사도가 높은 3건을 추천한다. 정확한 체크포인트명은 자료에 없어 임의로 추정하지 않는다."
    )]
    story += [P("2안: BM25 키워드 검색", H2)]
    story += [P(
        "문서 안의 단어 빈도와 전체 DB에서의 희소도를 함께 반영한다. 입력은 VOC Type, Subtype, Customer Request이며, 한·영문 소문자화, 구분자 제거, 핵심 복합어 유지와 불용어 제외를 적용했다. 파라미터는 k1=1.5, b=0.75다."
    )]
    story += [P("3안: 결과 점수 보정", H2)]
    story += [callout(
        "최종 점수 = BM25 점수 × (1 + TypeMatch × 0.10)<br/>"
        "TypeMatch: 동일 VOC Type이면 1, 다르면 0. 동일 유형 사례에 10% 가점.",
        fill=LIGHT_GREEN, border=GREEN,
    )]
    story += [Spacer(1, 4 * mm), P("평가 해석과 한계", H2)]
    story += [P(
        "BM25 점수는 공식 정확도가 아니라 동일 검색 내 후보 순위를 비교하는 상대 점수다. Test 15건의 Top 3를 업무 유형, Subtype, 제품·Grade, 요청 행동과 대응 이력 관점에서 정성 검토했다. 사람의 적합/부적합 정답표가 없으므로 Accuracy·Precision·Top-3 적중률은 아직 산출하지 않았다."
    )]
    story.append(PageBreak())

    # Page 5 - Planned web platform
    story += [section_title("4", "웹 협업 플랫폼 설계")]
    story += [callout(
        "웹 플랫폼은 업무 흐름과 UI 기본 구성까지 설계했다. Stitch 상세 조정 후 Next.js·FastAPI로 구현할 예정이며, 현재 실행 가능한 웹 소스는 없다.",
        fill=LIGHT_AMBER, border=AMBER,
    )]
    story += [P("프론트엔드 - Next.js 계획", H2)]
    ui_rows = [
        ["화면", "주요 기능"],
        ["대시보드", "내 미완료·마감 임박 / 부서별 진행·지연 / 신규 미배정 요청"],
        ["새 요청 등록", "메일 붙여넣기, 임시 저장, 추출값 확인·수정, Top 3 실행"],
        ["고객 대응 관리", "신규·진행·검토·회신·지연·종결, 부서별 담당자·마감일"],
        ["아카이브", "제품·고객·Complaint/Request/Inquiry·날짜별 조회"],
        ["요청 상세·알림", "병렬 부서 대응, 첨부·타임라인, D-2/D-1/초과 알림"],
    ]
    story += [data_table(ui_rows, [38 * mm, 133 * mm])]
    story += [P("백엔드 - FastAPI 계획", H2)]
    story += [P(
        "메일과 사용자 확정 정보를 받아 입력값을 검증하고, BM25 검색 입력을 구성해 완료된 과거 VOC의 Top 3를 반환한다. 이후 신규 요청, 부서 배정, 상태 변경, 고객 회신과 감사 이력을 DB에 저장한다."
    )]
    story += [P("데이터베이스 - Supabase/PostgreSQL 계획", H2)]
    story += [P(
        "운영 후보는 Supabase PostgreSQL, 로컬 개발·통합 테스트는 Docker PostgreSQL이다. 현재는 업로드용 CSV와 벡터 데이터가 준비되어 있고 실제 운영 테이블 적재와 애플리케이션 연동은 예정 단계다."
    )]
    story += [P("업무 상태 흐름", H2)]
    status_flow = [[
        P("요청 접수", TABLE_CENTER), P("대응 중", TABLE_CENTER), P("부서 검토", TABLE_CENTER),
        P("선택: 직책자 검토", TABLE_CENTER), P("고객 회신", TABLE_CENTER), P("완료·종결", TABLE_CENTER),
    ]]
    st = Table(
        status_flow,
        colWidths=[25 * mm, 25 * mm, 27 * mm, 39 * mm, 27 * mm, 28 * mm],
        hAlign="LEFT",
    )
    st.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE), ("BOX", (0, 0), (-1, -1), 0.5, BLUE),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, GRID), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [st, Spacer(1, 2 * mm), P("모든 단계는 사유와 이력을 남기고 앞뒤로 이동할 수 있다. 고객 회신 후 추가 질문이 오면 요청 접수로 재전환한다.", SMALL)]
    story.append(PageBreak())

    # Page 6 - Features and status
    story += [section_title("5", "핵심 기능 및 현재 구현 현황")]
    feature_rows = [
        ["핵심 기능", "입력", "처리·결과", "현황"],
        ["VOC 데이터 구성", "실제 업무 패턴", "다국어 시뮬레이션 VOC 150건", "완료"],
        ["DB/Test 분리", "150건 Case ID", "DB 135 / Test 15, 중복 없음", "완료"],
        ["벡터 Top 3", "요약+원문+이력", "384차원·코사인 유사도", "완료"],
        ["BM25 Top 3", "Type+Subtype+요약", "키워드 상대 점수·선정 근거", "완료"],
        ["Type 가점", "BM25 점수+TypeMatch", "동일 Type 10% 보정", "설계 완료"],
        ["웹 협업", "고객 메일·사용자 갱신", "검색·배정·진척·종결·아카이브", "구현 예정"],
    ]
    story += [data_table(feature_rows, [35 * mm, 39 * mm, 67 * mm, 30 * mm])]
    story += [P("완료", H2)]
    story += [bullet("시뮬레이션 VOC 150건과 22개 컬럼 구성")]
    story += [bullet("DB 135건·Test 15건 분리 및 Supabase 업로드 자료 준비")]
    story += [bullet("다국어 임베딩·코사인 유사도 및 BM25 Top 3 결과 생성")]
    story += [bullet("검색 결과의 업무 적합성 정성 비교와 선정 근거 정리")]
    story += [P("개선·검증 중", H2)]
    story += [bullet("최종 DB 135건 기준 검색 결과 재검증")]
    story += [bullet("BM25 Type 일치 10% 가점 산식 검증")]
    story += [bullet("담당자 적합/부적합 판정 기반 Top-3 적중률 마련")]
    story += [bullet("Stitch 기반 UI 상세 조정")]
    story += [P("미구현", H2)]
    story += [bullet("Supabase 운영 테이블 적재·연동")]
    story += [bullet("Next.js·FastAPI·로그인·배정·진척·알림·첨부 기능")]
    story += [bullet("Docker 통합 환경, QA, GitHub/Vercel 배포")]
    story.append(PageBreak())

    # Page 7 - Flow and roadmap
    story += [section_title("6", "전체 흐름 및 향후 계획")]
    story += [P("현재까지의 데이터·검색 흐름", H2)]
    current_flow = [
        ["1", "시뮬레이션 VOC 150건"],
        ["2", "DB 135건 / Test 15건 분리"],
        ["3", "다국어 원문·한글 요청 요약·처리 이력 정리"],
        ["4", "Sentence Transformer 벡터 또는 BM25 입력 생성"],
        ["5", "Top 3 산출 및 업무 적합성 정성 검토"],
    ]
    story += [data_table([["단계", "처리"]] + current_flow, [24 * mm, 147 * mm])]
    story += [P("향후 웹 플랫폼 전체 흐름", H2)]
    flow_text = (
        "원본 데이터 > 데이터 전처리 > 사용자 메일 입력 > Next.js 프론트엔드 > "
        "FastAPI 백엔드 > PostgreSQL/Supabase + BM25 검색 > Top 3 결과 > 사용자 화면 > "
        "부서 배정·진척 관리 > 고객 회신·종결 또는 재접수"
    )
    story += [callout(flow_text, fill=LIGHT_GREEN, border=GREEN)]
    story += [P("다음 단계", H2)]
    next_rows = [
        ["순서", "실행 항목", "완료 기준"],
        ["1", "BM25 Type 10% 가점 재검증", "Test 15건 Top 3 비교표와 담당자 판정"],
        ["2", "Stitch UI 확정", "핵심 화면과 상태 전이 승인"],
        ["3", "DB 적재·스키마 확정", "Supabase·로컬 PostgreSQL 동일 구조"],
        ["4", "Next.js·FastAPI 구현", "메일 입력부터 Top 3 반환까지 연결"],
        ["5", "협업·알림·QA", "배정·진척·회신·종결 E2E 검증"],
        ["6", "배포", "환경변수·보안 검토 후 운영 URL 확인"],
    ]
    story += [data_table(next_rows, [19 * mm, 70 * mm, 82 * mm])]
    story += [Spacer(1, 5 * mm), callout(
        "결론: 데이터와 검색 프로토타입으로 핵심 가능성을 먼저 검증했다. 다음 단계는 BM25 점수 보정의 정식 평가와 웹 협업 기능 구현이며, 검색 결과를 실제 부서 대응과 종결 관리까지 연결하는 것이 최종 목표다."
    )]

    doc.build(story)


if __name__ == "__main__":
    build()
    print(OUTPUT)
