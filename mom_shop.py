import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime, date, timedelta

DB_PATH = "mom_shop.db"

# 🔐 관리자 비밀번호 (원하는 값으로 바꿔 사용하면 됨)
ADMIN_PASSWORD = "1234"


# ---------------------------
# DB 초기화
# ---------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
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
            created_at TEXT NOT NULL
        )
        """
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
    cur.execute(
        """
        INSERT INTO jobs (
            dropoff_date, customer_name, customer_phone,
            item_type, work_hem, work_sleeve, work_width, work_other,
            price, payment_method, is_prepaid, pickup_date,
            picked_up, memo, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
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
            0,  # 처음 저장될 때는 항상 아직 찾지 않음
            memo,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()
    conn.close()


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
    return df


def load_jobs_by_pickup(target_date):
    """찾는 날 기준으로 특정 날짜 찾아갈 옷 조회 (picked_up=0만)"""
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT * FROM jobs
        WHERE pickup_date = ? AND picked_up = 0
        ORDER BY dropoff_date ASC, id ASC
    """
    df = pd.read_sql_query(query, conn, params=[target_date])
    conn.close()
    return df


def mark_picked_up(job_id):
    """해당 옷을 '찾아감' 상태로 변경"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE jobs SET picked_up = 1 WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()


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
        st.caption("✅ 관리자 모드: 편집 / 삭제 / 입력 가능")
    else:
        st.caption("ℹ️ 관리자 비밀번호를 입력하지 않으면 조회만 가능합니다.")


# ---------------------------
# 메인
# ---------------------------
def main():
    st.set_page_config(page_title="엄마 수선가게 매출장", layout="centered")
    init_db()

    st.title("👗 엄마 수선가게 매출장")

    # 관리자 로그인 영역
    admin_login()

    menu = st.radio(
        "메뉴 선택",
        ["대시보드", "매출 입력하기", "매출 내역 보기", "데이터 수정", "월별 합계 보기"],
        horizontal=True,
    )

    if menu == "대시보드":
        page_dashboard()
    elif menu == "매출 입력하기":
        page_input()
    elif menu == "매출 내역 보기":
        page_list()
    elif menu == "데이터 수정":
        page_edit()
    else:
        page_monthly_summary()


# ---------------------------
# 대시보드 (날짜 선택 가능)
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

    # 고객 수 / 옷 개수
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
                if row['work_hem']:
                    tasks.append("기장")
                if row['work_sleeve']:
                    tasks.append("소매")
                if row['work_width']:
                    tasks.append("품")
                if row['work_other']:
                    tasks.append(row['work_other'])

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
            # 조회 전용: 체크박스 없이 정보만 표시
            tasks = []
            if row['work_hem']:
                tasks.append("기장")
            if row['work_sleeve']:
                tasks.append("소매")
            if row['work_width']:
                tasks.append("품")
            if row['work_other']:
                tasks.append(row['work_other'])

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
# 입력 화면
# ---------------------------
def page_input():
    st.header("📝 매출 입력하기")

    if not st.session_state.get("is_admin", False):
        st.warning("관리자 비밀번호를 입력해야 매출을 입력할 수 있습니다.")
        return

    # 최근 손님 유지용 세션 변수
    if "last_customer_name" not in st.session_state:
        st.session_state.last_customer_name = ""
    if "last_customer_phone" not in st.session_state:
        st.session_state.last_customer_phone = ""
    if "last_dropoff_date" not in st.session_state:
        st.session_state.last_dropoff_date = date.today()
    if "last_pickup_date" not in st.session_state:
        st.session_state.last_pickup_date = date.today() + timedelta(days=3)
    if "current_price" not in st.session_state:
        st.session_state.current_price = 4000   # 기본 금액 4,000원

    st.markdown("#### 0. 고객 정보")
    col1, col2 = st.columns(2)

    with col1:
        customer_name = st.text_input(
            "고객 이름",
            value=st.session_state.last_customer_name,
        )
    with col2:
        customer_phone = st.text_input(
            "연락처 (선택)",
            value=st.session_state.last_customer_phone,
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

    # 현재 금액 입력창
    price = st.number_input(
        "금액(원)",
        min_value=0,
        step=1000,
        value=st.session_state.current_price,
        format="%d",
    )

    # 금액 + 버튼들
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

    # 사용자가 number_input에서 직접 수정한 값도 반영
    st.session_state.current_price = price

    # 카드가 기본 선택 되도록 카드 / 현금 / 계좌이체 순서
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

        insert_job(
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

        # 저장 후 기본 금액 4,000원으로 초기화
        st.session_state.current_price = 4000

        # 같은 고객 이어서 입력 여부
        if same_customer:
            st.session_state.last_customer_name = customer_name
            st.session_state.last_customer_phone = customer_phone
            st.session_state.last_dropoff_date = dropoff_date_input
            st.session_state.last_pickup_date = pickup_date_input
        else:
            st.session_state.last_customer_name = ""
            st.session_state.last_customer_phone = ""
            st.session_state.last_dropoff_date = date.today()
            st.session_state.last_pickup_date = date.today() + timedelta(days=3)

        st.rerun()


# ---------------------------
# 내역 보기 (조회 전용)
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
                "메모",
            ]
        ]
    )


# ---------------------------
# 데이터 수정 (수정 & 삭제)
# ---------------------------
def page_edit():
    st.header("✏️ 데이터 수정 / 삭제")

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

    job_id = st.selectbox(
        "수정할 번호 선택",
        df["id"].tolist(),
    )

    row = df[df["id"] == job_id].iloc[0]

    st.markdown("---")
    st.subheader(f"번호 {job_id} 수정하기")

    # 날짜들
    dropoff_date_input = st.date_input(
        "맡긴 날",
        value=datetime.strptime(row["dropoff_date"], "%Y-%m-%d").date(),
    )

    pickup_date_input = st.date_input(
        "찾는 날",
        value=(
            datetime.strptime(row["pickup_date"], "%Y-%m-%d").date()
            if row["pickup_date"]
            else date.today()
        ),
    )

    customer_name = st.text_input("고객 이름", value=row["customer_name"] or "")
    customer_phone = st.text_input("연락처", value=row["customer_phone"] or "")
    item_type = st.text_input("옷 종류", value=row["item_type"])

    col_w1, col_w2, col_w3, col_w4 = st.columns(4)
    with col_w1:
        work_hem = st.checkbox("기장", value=bool(row["work_hem"]))
    with col_w2:
        work_sleeve = st.checkbox("소매", value=bool(row["work_sleeve"]))
    with col_w3:
        work_width = st.checkbox("품", value=bool(row["work_width"]))
    with col_w4:
        work_other_flag = st.checkbox("기타 있음", value=bool(row["work_other"]))

    work_other = ""
    if work_other_flag:
        work_other = st.text_input("기타 작업내용", value=row["work_other"] or "")

    price = st.number_input(
        "금액(원)",
        min_value=0,
        step=1000,
        value=int(row["price"]),
        format="%d",
    )

    payment_options = ["카드", "현금", "계좌이체"]
    payment_method = st.radio(
        "결제 수단",
        payment_options,
        index=payment_options.index(row["payment_method"])
        if row["payment_method"] in payment_options
        else 0,
        horizontal=True,
    )

    pay_timing = st.radio(
        "결제 시점",
        ["맡길 때 결제함", "나중에 결제(미결제)"],
        index=0 if row["is_prepaid"] == 1 else 1,
    )
    is_prepaid = 1 if pay_timing == "맡길 때 결제함" else 0

    picked_up = st.checkbox(
        "이미 찾아감 처리",
        value=bool(row["picked_up"]),
    )

    memo = st.text_input("메모", value=row["memo"] or "")

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

    st.dataframe(summary)

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

