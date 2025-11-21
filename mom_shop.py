import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime, date, timedelta

DB_PATH = "mom_shop.db"

# 🔐 관리자 비밀번호
ADMIN_PASSWORD = "1234"


# ---------------------------
# 연락처 포맷팅 함수
# ---------------------------
def format_phone(raw):
    """
    문자열에서 숫자만 뽑아서 휴대폰/전화번호 형태로 포맷팅.
    기본적으로 010 번호를 우선 가정.
    """
    if raw is None:
        return ""

    digits = "".join(ch for ch in str(raw) if ch.isdigit())

    if not digits:
        return ""

    # 8자리만 입력한 경우 → 010-xxxx-xxxx 로 간주
    if len(digits) == 8:
        return f"010-{digits[:4]}-{digits[4:]}"

    # 11자리, 010으로 시작
    if len(digits) == 11 and digits.startswith("010"):
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"

    # 10자리, 0으로 시작 (지역번호 포함)
    if len(digits) == 10 and digits.startswith("0"):
        if digits.startswith("02"):
            return f"{digits[:2]}-{digits[2:6]}-{digits[6:]}"
        else:
            return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"

    # 기타 11자리
    if len(digits) == 11:
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"

    # 그 외는 그냥 숫자 그대로
    return digits


# ---------------------------
# DB 초기화
# ---------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 기본 테이블 생성 (printed_count 포함)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dropoff_date TEXT NOT NULL,
            customer_name TEXT,
            customer_phone TEXT,
            item_type TEXT NOT NULL,
            work_hem INTEGER NOT NULL DEFAULT 0,
            work_sleeve INTEGER NOT NULL DEFAULT 0,
            work_width INTEGER NOT NULL DEFAULT 0,
            work_other TEXT,
            price INTEGER NOT NULL,
            payment_method TEXT NOT NULL,
            is_prepaid INTEGER NOT NULL DEFAULT 1,
            pickup_date TEXT,
            picked_up INTEGER NOT NULL DEFAULT 0,
            memo TEXT,
            printed_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )

    # 기존 DB에 printed_count 컬럼이 없으면 추가
    cur.execute("PRAGMA table_info(jobs)")
    cols = [row[1] for row in cur.fetchall()]
    if "printed_count" not in cols:
        cur.execute(
            "ALTER TABLE jobs ADD COLUMN printed_count INTEGER NOT NULL DEFAULT 0"
        )

    conn.commit()
    conn.close()


def insert_job(
    dropoff_date,
    customer_name,
    customer_phone,
    item_type,
    work_hem,
    work_sleeve,
    work_width,
    work_other,
    price,
    payment_method,
    is_prepaid,
    pickup_date,
    memo,
):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    phone_formatted = format_phone(customer_phone)
    cur.execute(
        """
        INSERT INTO jobs (
            dropoff_date, customer_name, customer_phone,
            item_type, work_hem, work_sleeve, work_width, work_other,
            price, payment_method, is_prepaid, pickup_date,
            picked_up, memo, printed_count, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
        """,
        (
            dropoff_date,
            customer_name,
            phone_formatted,
            item_type,
            work_hem,
            work_sleeve,
            work_width,
            work_other,
            price,
            payment_method,
            is_prepaid,
            pickup_date,
            0,
            memo,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    job_id = cur.lastrowid
    conn.commit()
    conn.close()
    return job_id


def update_job(
    job_id,
    dropoff_date,
    customer_name,
    customer_phone,
    item_type,
    work_hem,
    work_sleeve,
    work_width,
    work_other,
    price,
    payment_method,
    is_prepaid,
    pickup_date,
    picked_up,
    memo,
):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    phone_formatted = format_phone(customer_phone)
    cur.execute(
        """
        UPDATE jobs SET
            dropoff_date = ?,
            customer_name = ?,
            customer_phone = ?,
            item_type = ?,
            work_hem = ?,
            work_sleeve = ?,
            work_width = ?,
            work_other = ?,
            price = ?,
            payment_method = ?,
            is_prepaid = ?,
            pickup_date = ?,
            picked_up = ?,
            memo = ?
        WHERE id = ?
        """,
        (
            dropoff_date,
            customer_name,
            phone_formatted,
            item_type,
            work_hem,
            work_sleeve,
            work_width,
            work_other,
            price,
            payment_method,
            is_prepaid,
            pickup_date,
            picked_up,
            memo,
            job_id,
        ),
    )
    conn.commit()
    conn.close()


def delete_job(job_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()


def load_jobs(start_date=None, end_date=None):
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM jobs"
    params = []

    if start_date and end_date:
        query += " WHERE dropoff_date BETWEEN ? AND ?"
        params = [start_date, end_date]

    query += " ORDER BY dropoff_date DESC, id DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    if "printed_count" not in df.columns:
        df["printed_count"] = 0

    return df


def load_jobs_by_pickup(target_date):
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT * FROM jobs
        WHERE pickup_date = ? AND picked_up = 0
        ORDER BY dropoff_date ASC, id ASC
    """
    df = pd.read_sql_query(query, conn, params=[target_date])
    conn.close()
    if "printed_count" not in df.columns:
        df["printed_count"] = 0
    return df


def load_job_by_id(job_id):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM jobs WHERE id = ?", conn, params=[job_id])
    conn.close()
    if df.empty:
        return None
    if "printed_count" not in df.columns:
        df["printed_count"] = 0
    return df.iloc[0]


def mark_picked_up(job_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE jobs SET picked_up = 1 WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()


def mark_printed(job_id):
    """전표를 출력했다고 표시 (printed_count + 1)"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "UPDATE jobs SET printed_count = COALESCE(printed_count,0) + 1 WHERE id = ?",
        (job_id,),
    )
    conn.commit()
    conn.close()


# ---------------------------
# 전표 텍스트 생성 공통 함수
# ---------------------------
def build_receipt_text(row):
    tasks = []
    if row["work_hem"]:
        tasks.append("기장")
    if row["work_sleeve"]:
        tasks.append("소매")
    if row["work_width"]:
        tasks.append("품")
    if row["work_other"]:
        tasks.append(row["work_other"])

    task_text = ", ".join(tasks) if tasks else "없음"
    payment_status = "결제 완료" if row["is_prepaid"] == 1 else "미결제"

    dropoff = row["dropoff_date"] or ""
    pickup = row["pickup_date"] or ""
    name = row["customer_name"] or ""
    phone = row["customer_phone"] or ""
    item = row["item_type"] or ""
    pay_method = row["payment_method"] or ""
    price = int(row["price"]) if row["price"] is not None else 0
    job_id = row["id"]

    text = f"""────────────────────────
        에벤에셀옷수선
────────────────────────
고객명: {name}
연락처: {phone}

맡긴날: {dropoff}
찾는날: {pickup}

종류: {item}
작업: {task_text}

결제 여부: {payment_status}
결제수단: {pay_method}

금액: {price:,}원
번호(ID): #{job_id}
────────────────────────
        내부 보관용
────────────────────────
"""
    return text


# ---------------------------
# 관리자 로그인 처리
# ---------------------------
def admin_login():
    if "is_admin" not in st.session_state:
        st.session_state.is_admin = False

    with st.expander("🔐 관리자 로그인", expanded=not st.session_state.is_admin):
        pwd = st.text_input("비밀번호", type="password")
        if st.button("로그인"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.is_admin = True
                st.success("관리자 모드로 로그인되었습니다.")
            else:
                st.session_state.is_admin = False
                st.error("비밀번호가 올바르지 않습니다.")

    if st.session_state.is_admin:
        st.caption("✅ 관리자 모드: 매출 입력 / 수정 / 전표 출력 / 삭제 가능")
    else:
        st.caption("ℹ️ 관리자 비밀번호를 입력하지 않으면 조회만 가능합니다.")


# ---------------------------
# 메인
# ---------------------------
def main():
    st.set_page_config(page_title="에벤에셀옷수선 매출장", layout="centered")
    init_db()

    st.title("👗 에벤에셀옷수선 매출장")

    admin_login()
    is_admin = st.session_state.get("is_admin", False)

    if is_admin:
        menu_options = [
            "대시보드",
            "매출 입력하기",
            "전표 출력",
            "매출 내역 보기",
            "데이터 수정",
            "월별 합계 보기",
        ]
    else:
        menu_options = [
            "대시보드",
            "매출 내역 보기",
            "월별 합계 보기",
        ]

    menu = st.radio("메뉴 선택", menu_options, horizontal=True)

    if menu == "대시보드":
        page_dashboard()
    elif menu == "매출 입력하기":
        page_input()
    elif menu == "전표 출력":
        page_print()
    elif menu == "매출 내역 보기":
        page_list()
    elif menu == "데이터 수정":
        page_edit()
    else:
        page_monthly_summary()


# ---------------------------
# 대시보드
# ---------------------------
def page_dashboard():
    st.header("📊 찾으러 올 고객 대시보드")

    today = date.today()
    target_date = st.date_input("찾으러 올 날짜 선택", value=today)
    target_str = target_date.strftime("%Y-%m-%d")

    df = load_jobs_by_pickup(target_str)

    if df.empty:
        st.info(f"{target_str} 기준으로 찾으러 올 옷이 없습니다.")
        return

    df["customer_key"] = (
        df["customer_name"].fillna("").astype(str)
        + "|"
        + df["customer_phone"].fillna("").astype(str)
    )
    customer_count = df["customer_key"].nunique()

    st.subheader(f"👥 고객 수: {customer_count} 명")
    st.subheader(f"👗 옷 개수: {len(df)} 벌")

    st.markdown("---")
    st.markdown(f"### 🔽 {target_str} 에 찾으러 올 옷 리스트")

    is_admin = st.session_state.get("is_admin", False)

    for _, row in df.iterrows():
        if is_admin:
            col1, col2 = st.columns([1, 4])
            with col1:
                checked = st.checkbox("찾음", key=f"pickup_{row['id']}")
            with col2:
                tasks = []
                if row["work_hem"]:
                    tasks.append("기장")
                if row["work_sleeve"]:
                    tasks.append("소매")
                if row["work_width"]:
                    tasks.append("품")
                if row["work_other"]:
                    tasks.append(row["work_other"])

                st.markdown(
                    f"""
**[{row['id']}] {row['customer_name'] or '이름 없음'}**  
- 연락처: {row['customer_phone'] or '없음'}  
- 맡긴 날: {row['dropoff_date']}  
- 옷 종류: {row['item_type']}  
- 작업: {", ".join(tasks) if tasks else "기록 없음"}  
- 금액: {int(row['price']):,}원 | 결제: {row['payment_method']}
"""
                )

            if checked:
                mark_picked_up(row["id"])
                st.rerun()
        else:
            tasks = []
            if row["work_hem"]:
                tasks.append("기장")
            if row["work_sleeve"]:
                tasks.append("소매")
            if row["work_width"]:
                tasks.append("품")
            if row["work_other"]:
                tasks.append(row["work_other"])

            st.markdown(
                f"""
**[{row['id']}] {row['customer_name'] or '이름 없음'}**  
- 연락처: {row['customer_phone'] or '없음'}  
- 맡긴 날: {row['dropoff_date']}  
- 옷 종류: {row['item_type']}  
- 작업: {", ".join(tasks) if tasks else "기록 없음"}  
- 금액: {int(row['price']):,}원 | 결제: {row['payment_method']}  
- 상태: 아직 찾아가지 않음
"""
            )


# ---------------------------
# 매출 입력
# ---------------------------
def page_input():
    st.header("📝 매출 입력하기")

    if not st.session_state.get("is_admin", False):
        st.warning("관리자 비밀번호를 입력해야 매출을 입력할 수 있습니다.")
        return

    if "last_customer_name" not in st.session_state:
        st.session_state.last_customer_name = ""
    if "last_customer_phone" not in st.session_state:
        st.session_state.last_customer_phone = "010-"
    if "last_dropoff_date" not in st.session_state:
        st.session_state.last_dropoff_date = date.today()
    if "last_pickup_date" not in st.session_state:
        st.session_state.last_pickup_date = date.today() + timedelta(days=3)
    if "current_price" not in st.session_state:
        st.session_state.current_price = 4000

    st.markdown("#### 0. 고객 정보")
    col1, col2 = st.columns(2)

    with col1:
        customer_name = st.text_input(
            "고객 이름",
            value=st.session_state.last_customer_name,
        )
    with col2:
        customer_phone = st.text_input(
            "연락처 (숫자만 입력해도 자동으로 '-' 정리됨)",
            value=st.session_state.last_customer_phone or "010-",
        )

    col3, col4 = st.columns(2)
    with col3:
        dropoff_date_input = st.date_input(
            "맡긴 날",
            value=st.session_state.last_dropoff_date,
        )
    with col4:
        pickup_date_input = st.date_input(
            "찾는 날",
            value=st.session_state.last_pickup_date,
        )

    st.markdown("#### 1. 옷 종류")
    item_options = ["바지", "치마", "원피스", "외투/코트", "패딩", "셔츠/블라우스", "기타"]
    item_type = st.radio("선택", item_options, horizontal=True)

    if item_type == "기타":
        temp = st.text_input("직접 입력")
        if temp:
            item_type = temp

    st.markdown("#### 2. 작업 내용 (복수 선택 가능)")
    col_w1, col_w2, col_w3, col_w4 = st.columns(4)

    with col_w1:
        work_hem = st.checkbox("기장")
    with col_w2:
        work_sleeve = st.checkbox("소매")
    with col_w3:
        work_width = st.checkbox("품")
    with col_w4:
        work_other_flag = st.checkbox("기타")

    work_other = ""
    if work_other_flag:
        work_other = st.text_input("기타 작업내용 입력")

    st.markdown("#### 3. 금액 / 결제 정보")

    price = st.number_input(
        "금액(원)",
        min_value=0,
        step=1000,
        value=st.session_state.current_price,
        format="%d",
    )

    col_p1, col_p2, col_p3, col_p4 = st.columns(4)
    with col_p1:
        if st.button("+1,000원"):
            st.session_state.current_price += 1000
            st.rerun()
    with col_p2:
        if st.button("+5,000원"):
            st.session_state.current_price += 5000
            st.rerun()
    with col_p3:
        if st.button("+10,000원"):
            st.session_state.current_price += 10000
            st.rerun()
    with col_p4:
        if st.button("+50,000원"):
            st.session_state.current_price += 50000
            st.rerun()

    st.session_state.current_price = price

    payment_method = st.radio(
        "결제 수단",
        ["카드", "현금", "계좌이체"],
        horizontal=True,
    )

    pay_timing = st.radio(
        "결제 시점",
        ["맡길 때 결제함", "나중에 결제(미결제)"],
    )
    is_prepaid = 1 if pay_timing == "맡길 때 결제함" else 0

    memo = st.text_input("메모 (선택)")

    st.markdown("---")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        save = st.button("✅ 이 옷 저장하기", use_container_width=True)
    with col_s2:
        same_customer = st.checkbox("같은 고객 이어서 입력")

    if save:
        dropoff_str = dropoff_date_input.strftime("%Y-%m-%d")
        pickup_str = pickup_date_input.strftime("%Y-%m-%d")

        job_id = insert_job(
            dropoff_str,
            customer_name,
            customer_phone,
            item_type,
            int(work_hem),
            int(work_sleeve),
            int(work_width),
            work_other,
            int(price),
            payment_method,
            is_prepaid,
            pickup_str,
            memo,
        )

        st.success("저장되었습니다! 🙆‍♀️")
        st.balloons()

        phone_formatted = format_phone(customer_phone)

        if same_customer:
            st.session_state.last_customer_name = customer_name
            st.session_state.last_customer_phone = phone_formatted or "010-"
            st.session_state.last_dropoff_date = dropoff_date_input
            st.session_state.last_pickup_date = pickup_date_input
        else:
            st.session_state.last_customer_name = ""
            st.session_state.last_customer_phone = "010-"
            st.session_state.last_dropoff_date = date.today()
            st.session_state.last_pickup_date = date.today() + timedelta(days=3)

        st.session_state.current_price = 4000

        # 저장 후에는 전표 출력 탭에서 신규 출력/재출력 관리
        st.info("전표가 필요하면 상단 메뉴의 '전표 출력' 탭에서 신규 출력으로 관리할 수 있습니다.")
        st.rerun()


# ---------------------------
# 전표 출력 탭
# ---------------------------
def page_print():
    st.header("🧾 전표 출력")

    if not st.session_state.get("is_admin", False):
        st.warning("관리자 비밀번호를 입력해야 전표 출력 관리를 할 수 있습니다.")
        return

    today = date.today()
    start_date, end_date = st.date_input(
        "기간 선택 (맡긴 날 기준)",
        value=(date(today.year, today.month, 1), today),
    )

    df = load_jobs(
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d"),
    )

    if df.empty:
        st.info("해당 기간에 데이터가 없습니다.")
        return

    if "printed_count" not in df.columns:
        df["printed_count"] = 0

    new_df = df[df["printed_count"] == 0]
    re_df = df[df["printed_count"] > 0]

    tab1, tab2 = st.tabs(["🆕 신규 출력(한 번도 출력 안 한 건)", "🔁 재출력(이미 출력된 전표)"])

    # 신규 출력 탭
    with tab1:
        if new_df.empty:
            st.info("신규 출력할 전표가 없습니다. (printed_count=0 인 건이 없음)")
        else:
            st.markdown("#### 신규 출력 대상 목록")
            st.dataframe(
                new_df[["id", "dropoff_date", "customer_name", "item_type", "price"]],
                use_container_width=True,
            )

            st.markdown("---")
            st.markdown("#### 전표 출력할 건 선택")

            # 행마다 '전표 보기 / 출력했다고 표시' 버튼
            for _, row in new_df.iterrows():
                col1, col2, col3 = st.columns([1, 3, 2])
                with col1:
                    if st.button("🧾 전표 보기", key=f"new_view_{row['id']}"):
                        receipt = build_receipt_text(row)
                        st.session_state["last_receipt"] = receipt
                        st.session_state["last_receipt_id"] = row["id"]
                        st.session_state["last_receipt_mode"] = "new"
                        st.rerun()
                with col2:
                    st.markdown(
                        f"**[{row['id']}] {row['customer_name'] or '이름 없음'}** / {row['item_type']} / {int(row['price']):,}원"
                    )
                with col3:
                    if st.button("✅ 출력했다고 표시", key=f"new_print_{row['id']}"):
                        mark_printed(row["id"])
                        st.success(f"번호 {row['id']} 전표를 '신규 출력 완료'로 기록했습니다.")
                        st.rerun()

    # 재출력 탭
    with tab2:
        if re_df.empty:
            st.info("재출력할 전표가 없습니다. (printed_count>0 인 건이 없음)")
        else:
            st.markdown("#### 재출력 대상 목록")
            temp = re_df.copy()
            temp["출력횟수"] = temp["printed_count"]
            st.dataframe(
                temp[["id", "dropoff_date", "customer_name", "item_type", "price", "출력횟수"]],
                use_container_width=True,
            )

            st.markdown("---")
            st.markdown("#### 재출력할 건 선택")

            for _, row in re_df.iterrows():
                col1, col2, col3 = st.columns([1, 3, 2])
                with col1:
                    if st.button("🧾 전표 보기", key=f"re_view_{row['id']}"):
                        receipt = build_receipt_text(row)
                        st.session_state["last_receipt"] = receipt
                        st.session_state["last_receipt_id"] = row["id"]
                        st.session_state["last_receipt_mode"] = "re"
                        st.rerun()
                with col2:
                    st.markdown(
                        f"**[{row['id']}] {row['customer_name'] or '이름 없음'}** / {row['item_type']} / {int(row['price']):,}원 / {int(row['printed_count'])}회 출력"
                    )
                with col3:
                    if st.button("🔁 재출력했다고 표시(횟수 +1)", key=f"re_print_{row['id']}"):
                        mark_printed(row["id"])
                        st.success(f"번호 {row['id']} 전표를 '재출력'으로 1회 추가 기록했습니다.")
                        st.rerun()

    # 마지막으로 본 전표 내용 한 번에 보여주기
    if "last_receipt" in st.session_state:
        st.markdown("---")
        mode = st.session_state.get("last_receipt_mode", "")
        rid = st.session_state.get("last_receipt_id", "")
        title = "신규 출력 전표" if mode == "new" else "재출력 전표"
        st.markdown(f"#### 🧾 {title} (번호 {rid})")
        st.text_area(
            "전표 내용 (브라우저에서 Ctrl+P로 인쇄하세요)",
            value=st.session_state["last_receipt"],
            height=260,
        )
        st.caption("※ 이 텍스트 영역에서 바로 인쇄는 안 되고, 브라우저 인쇄 기능(Ctrl+P)을 사용하면 됩니다.")


# ---------------------------
# 매출 내역 보기
# ---------------------------
def page_list():
    st.header("📋 매출 내역")

    today = date.today()
    start_date, end_date = st.date_input(
        "기간 선택 (맡긴 날 기준)",
        value=(date(today.year, today.month, 1), today),
    )

    df = load_jobs(
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d"),
    )

    if df.empty:
        st.info("데이터 없음")
        return

    df["customer_key"] = (
        df["customer_name"].fillna("").astype(str)
        + "|"
        + df["customer_phone"].fillna("").astype(str)
        + "|"
        + df["dropoff_date"].astype(str)
    )

    st.subheader(f"👥 고객 수: {df['customer_key'].nunique()} 명")
    st.subheader(f"👗 옷 개수: {len(df)} 벌")
    st.subheader(f"💰 매출 합계: {int(df['price'].sum()):,} 원")

    df_display = df.copy()
    df_display["기장"] = df_display["work_hem"].replace({1: "✓", 0: ""})
    df_display["소매"] = df_display["work_sleeve"].replace({1: "✓", 0: ""})
    df_display["품"] = df_display["work_width"].replace({1: "✓", 0: ""})
    df_display["선결제"] = df_display["is_prepaid"].replace({1: "선결제", 0: "미결제"})
    df_display["찾음여부"] = df_display["picked_up"].replace({1: "찾아감", 0: "보관중"})
    df_display["출력횟수"] = df_display["printed_count"]

    df_display.rename(
        columns={
            "id": "번호",
            "dropoff_date": "맡긴날",
            "pickup_date": "찾는날",
            "customer_name": "고객이름",
            "customer_phone": "연락처",
            "item_type": "옷종류",
            "work_other": "기타작업",
            "price": "금액",
            "payment_method": "결제수단",
            "memo": "메모",
        },
        inplace=True,
    )

    st.dataframe(
        df_display[
            [
                "번호",
                "맡긴날",
                "찾는날",
                "고객이름",
                "연락처",
                "옷종류",
                "기장",
                "소매",
                "품",
                "기타작업",
                "금액",
                "결제수단",
                "선결제",
                "찾음여부",
                "출력횟수",
                "메모",
            ]
        ],
        use_container_width=True,
    )


# ---------------------------
# 데이터 수정 / 삭제
# ---------------------------
def page_edit():
    st.header("✏️ 데이터 수정 / 삭제 / 전표 미리보기")

    if not st.session_state.get("is_admin", False):
        st.warning("관리자 비밀번호를 입력해야 수정/삭제를 할 수 있습니다.")
        return

    today = date.today()
    start_date, end_date = st.date_input(
        "기간 선택 (맡긴 날 기준)",
        value=(date(today.year, today.month, 1), today),
    )

    df = load_jobs(
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d"),
    )

    if df.empty:
        st.info("해당 기간에 수정할 데이터가 없습니다.")
        return

    st.markdown("#### 현재 데이터 (요약)")
    st.dataframe(df[["id", "dropoff_date", "customer_name", "item_type", "price"]])

    # 각 행마다 '이 건 수정하기' 버튼
    st.markdown("#### 수정할 건 선택")
    if "edit_job_id" not in st.session_state and not df.empty:
        st.session_state.edit_job_id = int(df.iloc[0]["id"])

    for _, row in df.iterrows():
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("✏️ 이 건 수정하기", key=f"edit_btn_{row['id']}"):
                st.session_state.edit_job_id = int(row["id"])
                st.rerun()
        with col2:
            st.markdown(
                f"**[{row['id']}] {row['customer_name'] or '이름 없음'}** / {row['item_type']} / {int(row['price']):,}원"
            )

    job_id = st.session_state.get("edit_job_id")
    if job_id is None:
        st.info("수정할 건을 위에서 선택해 주세요.")
        return

    row = df[df["id"] == job_id].iloc[0]

    st.markdown("---")
    st.subheader(f"번호 {job_id} 수정하기")

    dropoff_date_input = st.date_input(
        "맡긴 날",
        value=datetime.strptime(row["dropoff_date"], "%Y-%m-%d").date(),
        key="edit_dropoff_date",
    )

    pickup_date_input = st.date_input(
        "찾는 날",
        value=(
            datetime.strptime(row["pickup_date"], "%Y-%m-%d").date()
            if row["pickup_date"]
            else date.today()
        ),
        key="edit_pickup_date",
    )

    customer_name = st.text_input(
        "고객 이름", value=row["customer_name"] or "", key="edit_customer_name"
    )
    customer_phone = st.text_input(
        "연락처", value=row["customer_phone"] or "010-", key="edit_customer_phone"
    )
    item_type = st.text_input(
        "옷 종류", value=row["item_type"], key="edit_item_type"
    )

    col_w1, col_w2, col_w3, col_w4 = st.columns(4)
    with col_w1:
        work_hem = st.checkbox("기장", value=bool(row["work_hem"]), key="edit_work_hem")
    with col_w2:
        work_sleeve = st.checkbox(
            "소매", value=bool(row["work_sleeve"]), key="edit_work_sleeve"
        )
    with col_w3:
        work_width = st.checkbox(
            "품", value=bool(row["work_width"]), key="edit_work_width"
        )
    with col_w4:
        work_other_flag = st.checkbox(
            "기타 있음", value=bool(row["work_other"]), key="edit_work_other_flag"
        )

    work_other = ""
    if work_other_flag:
        work_other = st.text_input(
            "기타 작업내용", value=row["work_other"] or "", key="edit_work_other"
        )

    price = st.number_input(
        "금액(원)",
        min_value=0,
        step=1000,
        value=int(row["price"]),
        format="%d",
        key="edit_price",
    )

    payment_options = ["카드", "현금", "계좌이체"]
    payment_method = st.radio(
        "결제 수단",
        payment_options,
        index=payment_options.index(row["payment_method"])
        if row["payment_method"] in payment_options
        else 0,
        horizontal=True,
        key="edit_payment_method",
    )

    pay_timing = st.radio(
        "결제 시점",
        ["맡길 때 결제함", "나중에 결제(미결제)"],
        index=0 if row["is_prepaid"] == 1 else 1,
        key="edit_pay_timing",
    )
    is_prepaid = 1 if pay_timing == "맡길 때 결제함" else 0

    picked_up = st.checkbox(
        "이미 찾아감 처리",
        value=bool(row["picked_up"]),
        key="edit_picked_up",
    )

    memo = st.text_input("메모", value=row["memo"] or "", key="edit_memo")

    # 전표 미리보기
    st.markdown("#### 🧾 작업 전표 미리보기 (내부 보관용)")

    tasks = []
    if work_hem:
        tasks.append("기장")
    if work_sleeve:
        tasks.append("소매")
    if work_width:
        tasks.append("품")
    if work_other_flag and work_other:
        tasks.append(work_other)

    task_text = ", ".join(tasks) if tasks else "없음"
    payment_status = "결제 완료" if is_prepaid == 1 else "미결제"
    phone_formatted = format_phone(customer_phone)

    receipt_text = f"""────────────────────────
        에벤에셀옷수선
────────────────────────
고객명: {customer_name or ''}
연락처: {phone_formatted or ''}

맡긴날: {dropoff_date_input.strftime('%Y-%m-%d')}
찾는날: {pickup_date_input.strftime('%Y-%m-%d')}

종류: {item_type}
작업: {task_text}

결제 여부: {payment_status}
결제수단: {payment_method}

금액: {int(price):,}원
번호(ID): #{job_id}
────────────────────────
        내부 보관용
────────────────────────
"""

    st.text_area("전표 내용", value=receipt_text, height=260)
    st.caption("※ 인쇄는 브라우저 Ctrl+P를 사용하세요.")

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("💾 수정 내용 저장하기", use_container_width=True):
            update_job(
                job_id,
                dropoff_date_input.strftime("%Y-%m-%d"),
                customer_name,
                customer_phone,
                item_type,
                int(work_hem),
                int(work_sleeve),
                int(work_width),
                work_other if work_other_flag else "",
                int(price),
                payment_method,
                is_prepaid,
                pickup_date_input.strftime("%Y-%m-%d"),
                1 if picked_up else 0,
                memo,
            )
            st.success("수정되었습니다.")
            st.rerun()

    with col_b2:
        if st.button("🗑️ 이 건 삭제하기", use_container_width=True):
            delete_job(job_id)
            st.success(f"번호 {job_id} 데이터가 삭제되었습니다.")
            st.rerun()


# ---------------------------
# 월별 합계
# ---------------------------
def page_monthly_summary():
    st.header("📆 월별 요약")

    df = load_jobs()

    if df.empty:
        st.info("데이터 없음")
        return

    df["year_month"] = df["dropoff_date"].str[:7]

    df["customer_key"] = (
        df["customer_name"].fillna("").astype(str)
        + "|"
        + df["customer_phone"].fillna("").astype(str)
        + "|"
        + df["dropoff_date"].astype(str)
    )

    summary = (
        df.groupby("year_month")
        .agg(
            매출=("price", "sum"),
            건수=("id", "count"),
            고객수=("customer_key", "nunique"),
        )
        .reset_index()
    )

    st.dataframe(summary, use_container_width=True)

    latest = summary.iloc[-1]
    st.subheader(f"📌 최근 월 ({latest['year_month']})")
    st.write(
        f"- 매출: {int(latest['매출']):,} 원\n"
        f"- 건수: {int(latest['건수'])} 벌\n"
        f"- 고객수: {int(latest['고객수'])} 명"
    )


# ---------------------------
# 실행
# ---------------------------
if __name__ == "__main__":
    main()
