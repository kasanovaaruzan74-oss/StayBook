"""StayBook: FastAPI серверімен жұмыс істейтін Streamlit интерфейсі."""

import os
from datetime import date, timedelta
from decimal import Decimal

import requests
import streamlit as st


API_URL = os.getenv("BACKEND_URL", os.getenv("API_URL", "http://127.0.0.1:8000")).rstrip("/")
STATUS_NAMES = {
    "confirmed": "Расталған",
    "cancelled": "Бас тартылған",
    "completed": "Аяқталған",
}


class ApiError(Exception):
    """Пайдаланушыға көрсетуге болатын сервер қатесі."""


def request(method: str, path: str, **kwargs):
    """Барлық әрекет API арқылы өтеді; интерфейс БД-ға қосылмайды."""
    try:
        response = requests.request(
            method, f"{API_URL}{path}", timeout=5.0, allow_redirects=True, **kwargs
        )
    except requests.RequestException as exc:
        raise ApiError(
            "Серверге қосылу мүмкін болмады. Сервердің іске қосылғанын тексеріп, "
            "бетті қайта жүктеңіз."
        ) from exc

    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", "Сұрауды орындау мүмкін болмады.")
        except (ValueError, AttributeError):
            detail = "Сұрауды орындау мүмкін болмады."
        if isinstance(detail, list):
            detail = "; ".join(
                f"{'.'.join(str(part) for part in item.get('loc', [])[1:])}: "
                f"{item.get('msg', 'Мән дұрыс емес')}"
                for item in detail
                if isinstance(item, dict)
            )
        raise ApiError(str(detail))
    if response.status_code == 204:
        return None
    try:
        return response.json()
    except ValueError as exc:
        raise ApiError("Сервер жауабы оқылмады. Кейінірек қайталап көріңіз.") from exc


def save(method: str, path: str, message: str, payload=None) -> None:
    """Сақтап, тізімді жаңарту және келесі көрсетілімде хабарлама шығару."""
    try:
        kwargs = {"json": payload} if payload is not None else {}
        request(method, path, **kwargs)
    except ApiError as exc:
        st.error(str(exc))
    else:
        st.session_state["notice"] = message
        st.rerun()


def money(value) -> str:
    return f"{Decimal(str(value)):,.0f}".replace(",", " ") + " ₸"


def table(rows: list[dict], empty_message: str) -> None:
    if rows:
        st.dataframe(rows, hide_index=True, width="stretch")
    else:
        st.info(empty_message)


def clear_room_filters() -> None:
    """Батырма callback-і келесі рендерге дейін сүзгі өрістерін тазартады."""
    st.session_state["room_search"] = ""
    st.session_state["room_category"] = None
    st.session_state["room_min_price"] = 0.0
    st.session_state["room_max_price"] = 0.0


def show_rooms(rooms: list[dict], categories: list[dict]) -> None:
    category_names = {item["id"]: item["name"] for item in categories}
    st.subheader("Нөмірлер каталогы")
    st.caption("Қонақтарға лайық нөмірді іздеп, бағасы мен сыйымдылығын басқарыңыз.")
    first, second, third, fourth = st.columns([2, 1.5, 1, 1])
    # Формаға қоспаймыз: виджет өзгергенде Streamlit скриптті қайта орындайды.
    search = first.text_input("Нөмірді іздеу", placeholder="Мысалы: 10", key="room_search")
    category_id = second.selectbox(
        "Санат", [None, *category_names], key="room_category",
        format_func=lambda value: "Барлық санат" if value is None else category_names[value],
    )
    min_price = third.number_input("Ең төмен баға, ₸", min_value=0.0, step=1000.0, key="room_min_price")
    max_price = fourth.number_input("Ең жоғары баға, ₸", min_value=0.0, step=1000.0, key="room_max_price")
    st.caption("Іздеу өзгергенде кесте автоматты жаңарады. Ең жоғары бағадағы 0 — шектеусіз.")
    filters = {"search": search.strip(), "min_price": min_price}
    if max_price:
        filters["max_price"] = max_price
    if category_id is not None:
        filters["category_id"] = category_id
    if max_price and min_price > max_price:
        st.warning("Ең төмен баға ең жоғары бағадан аспауы керек.")
        filtered_rooms = []
    else:
        try:
            filtered_rooms = request("GET", "/rooms", params=filters)
        except ApiError as exc:
            st.error(str(exc))
            filtered_rooms = []
    if search or min_price or max_price or category_id is not None:
        st.button("Сүзгіні тазарту", on_click=clear_room_filters)
    table(
        [{"ID": room["id"], "Нөмір": room["room_number"],
          "Санат": category_names.get(room["category_id"], "—"),
          "Тәуліктік баға": money(room["price_per_night"]),
          "Орын саны": room["capacity"]} for room in filtered_rooms],
        "Таңдалған шарттарға сәйкес нөмір табылмады.",
    )

    with st.expander("＋ Жаңа нөмір қосу"):
        if not categories:
            st.info("Алдымен «Санаттар» бөлімінен санат қосыңыз.")
        else:
            with st.form("create_room", clear_on_submit=True):
                left, right = st.columns(2)
                number = left.text_input("Нөмір атауы", placeholder="Мысалы: 401")
                category = right.selectbox("Нөмір санаты", list(category_names), format_func=category_names.get)
                price = left.number_input("Бір тәулік бағасы, ₸", min_value=0.0, step=1000.0, value=25000.0)
                capacity = right.number_input("Сыйымдылығы", min_value=1, max_value=20, value=2)
                submitted = st.form_submit_button("Нөмірді қосу", type="primary")
            if submitted:
                if not number.strip():
                    st.warning("Нөмір атауын енгізіңіз.")
                else:
                    save("POST", "/rooms", "Жаңа нөмір қосылды.", {
                        "room_number": number.strip(), "category_id": category,
                        "price_per_night": str(price), "capacity": capacity,
                    })

    if not rooms:
        return
    room_map = {room["id"]: room for room in rooms}
    with st.expander("Нөмірді өзгерту"):
        room_id = st.selectbox("Өзгертілетін нөмір", list(room_map),
                               format_func=lambda value: f"{room_map[value]['room_number']} · #{value}")
        selected = room_map[room_id]
        # Нөмір ауысса, форманың бастапқы мәндері де өзгереді.
        with st.form(f"edit_room_{room_id}"):
            fields = st.multiselect("Өзгертілетін өрістер", ["Бағасы", "Орын саны", "Санаты", "Нөмір атауы"])
            price = st.number_input("Жаңа баға, ₸", min_value=0.0, value=float(selected["price_per_night"]), step=1000.0)
            capacity = st.number_input("Жаңа орын саны", min_value=1, max_value=20, value=int(selected["capacity"]))
            category_ids = list(category_names)
            category = st.selectbox("Жаңа санат", category_ids,
                                   index=category_ids.index(selected["category_id"]), format_func=category_names.get)
            number = st.text_input("Жаңа нөмір атауы", value=selected["room_number"])
            submitted = st.form_submit_button("Өзгерісті сақтау", type="primary")
        if submitted:
            values = {"Бағасы": ("price_per_night", str(price)), "Орын саны": ("capacity", capacity),
                      "Санаты": ("category_id", category), "Нөмір атауы": ("room_number", number.strip())}
            payload = {values[field][0]: values[field][1] for field in fields}
            if not payload:
                st.warning("Өзгертетін өрісті таңдаңыз.")
            elif "room_number" in payload and not payload["room_number"]:
                st.warning("Нөмір атауы бос болмауы керек.")
            else:
                save("PATCH", f"/rooms/{room_id}", "Нөмір деректері жаңартылды.", payload)

    with st.expander("Нөмірді өшіру"):
        with st.form("delete_room"):
            room_id = st.selectbox("Өшірілетін нөмір", list(room_map),
                                   format_func=lambda value: f"{room_map[value]['room_number']} · #{value}")
            confirmed = st.checkbox("Таңдалған нөмірді өшіруді растаймын")
            submitted = st.form_submit_button("Өшіру")
        if submitted:
            if confirmed:
                save("DELETE", f"/rooms/{room_id}", "Нөмір өшірілді.")
            else:
                st.warning("Өшіру үшін растау белгісін қойыңыз.")


def show_guests(guests: list[dict]) -> None:
    st.subheader("Қонақтар")
    st.caption("Қонақтың байланыс деректерін тіркеп, кейін брондау кезінде таңдаңыз.")
    table([{"ID": guest["id"], "Аты-жөні": guest["full_name"],
            "Телефон": guest["phone"], "Электрондық пошта": guest["email"]} for guest in guests],
          "Әзірге қонақ тіркелмеген.")
    with st.expander("＋ Қонақ тіркеу", expanded=not guests):
        with st.form("create_guest", clear_on_submit=True):
            full_name = st.text_input("Аты-жөні", placeholder="Мысалы: Айдана Серік")
            first, second = st.columns(2)
            phone = first.text_input("Телефон", placeholder="+77001234567")
            email = second.text_input("Электрондық пошта", placeholder="guest@example.com")
            submitted = st.form_submit_button("Тіркеу", type="primary")
        if submitted:
            if not all(value.strip() for value in (full_name, phone, email)):
                st.warning("Барлық өрісті толтырыңыз.")
            else:
                save("POST", "/guests", "Қонақ тіркелді.", {
                    "full_name": full_name.strip(), "phone": phone.strip(), "email": email.strip(),
                })


def show_categories(categories: list[dict]) -> None:
    st.subheader("Нөмір санаттары")
    st.caption("Стандарт, люкс және басқа санаттарды бір жерден басқарыңыз.")
    table([{"ID": category["id"], "Санат": category["name"],
            "Сипаттама": category.get("description", "")} for category in categories],
          "Әзірге санат қосылмаған.")
    with st.expander("＋ Санат қосу", expanded=not categories):
        with st.form("create_category", clear_on_submit=True):
            name = st.text_input("Санат атауы", placeholder="Мысалы: Отбасылық")
            description = st.text_area("Сипаттама", placeholder="Нөмірдің ерекшеліктері")
            submitted = st.form_submit_button("Қосу", type="primary")
        if submitted:
            if not name.strip():
                st.warning("Санат атауын енгізіңіз.")
            else:
                save("POST", "/categories", "Жаңа санат қосылды.",
                     {"name": name.strip(), "description": description.strip()})


def show_bookings(bookings: list[dict], guests: list[dict], rooms: list[dict]) -> None:
    guest_names = {guest["id"]: guest["full_name"] for guest in guests}
    room_names = {room["id"]: room["room_number"] for room in rooms}
    st.subheader("Брондаулар")
    st.caption("Келу мен кету күнін таңдаңыз. Қабаттасатын брондауларды жүйе тексереді.")
    table([{"ID": booking["id"], "Қонақ": guest_names.get(booking["guest_id"], "—"),
            "Нөмір": room_names.get(booking["room_id"], "—"),
            "Келу күні": booking["check_in"], "Кету күні": booking["check_out"],
            "Мәртебесі": STATUS_NAMES.get(booking["status"], booking["status"])} for booking in bookings],
          "Әзірге брондау жасалмаған.")
    with st.expander("＋ Жаңа брондау", expanded=not bookings):
        if not guests or not rooms:
            st.info("Брондау жасау үшін алдымен қонақ пен нөмір қосыңыз.")
        else:
            with st.form("create_booking"):
                first, second = st.columns(2)
                guest_id = first.selectbox("Қонақ", list(guest_names),
                                          format_func=lambda value: f"{guest_names[value]} · #{value}")
                room_id = second.selectbox("Нөмір", list(room_names),
                                           format_func=lambda value: f"{room_names[value]} · #{value}")
                check_in = first.date_input("Келу күні", value=date.today())
                check_out = second.date_input("Кету күні", value=date.today() + timedelta(days=1))
                submitted = st.form_submit_button("Брондау жасау", type="primary")
            if submitted:
                if check_out <= check_in:
                    st.warning("Кету күні келу күнінен кейін болуы керек.")
                else:
                    save("POST", "/bookings", "Брондау расталды.", {
                        "guest_id": guest_id, "room_id": room_id,
                        "check_in": check_in.isoformat(), "check_out": check_out.isoformat(),
                        "status": "confirmed",
                    })
    if bookings:
        booking_map = {booking["id"]: booking for booking in bookings}
        with st.expander("Брондау мәртебесін өзгерту"):
            with st.form("update_booking"):
                booking_id = st.selectbox("Брондау", list(booking_map), format_func=lambda value:
                    f"#{value} · {guest_names.get(booking_map[value]['guest_id'], '—')} · "
                    f"{room_names.get(booking_map[value]['room_id'], '—')}")
                status = st.selectbox("Жаңа мәртебе", list(STATUS_NAMES), format_func=STATUS_NAMES.get)
                submitted = st.form_submit_button("Мәртебені сақтау", type="primary")
            if submitted:
                save("PATCH", f"/bookings/{booking_id}", "Брондау мәртебесі жаңартылды.", {"status": status})


def main() -> None:
    st.set_page_config(page_title="StayBook · Қонақүйді басқару", page_icon="🏨", layout="wide")
    st.markdown("""<style>
    .stApp {background-color: #f8f7f2;}
    section[data-testid="stSidebar"] {background-color: #e8eeea;}
    h1, h2, h3 {color: #173d37;}
    button[kind="primary"] {background-color: #23675a; border-color: #23675a;}
    [data-testid="stMetric"] {background: white; border: 1px solid #e2e8e1;
        border-radius: 12px; padding: 18px;}
    </style>""", unsafe_allow_html=True)
    st.sidebar.title("StayBook")
    st.sidebar.caption("Қонақжайлықты оңай басқарыңыз")
    page = st.sidebar.radio("Бөлімдер", ["Нөмірлер", "Қонақтар", "Брондаулар", "Санаттар"], label_visibility="collapsed")
    st.sidebar.divider()
    st.sidebar.caption("Қонақүй нөмірлерін брондау жүйесі")
    if st.sidebar.button("Деректерді жаңарту", width="stretch"):
        st.rerun()
    st.title("StayBook")
    st.write("Әр қонаққа — жайлы қоныс.")
    if "notice" in st.session_state:
        st.success(st.session_state.pop("notice"))
    try:
        rooms = request("GET", "/rooms")
        categories = request("GET", "/categories")
        guests = request("GET", "/guests")
        bookings = request("GET", "/bookings")
    except ApiError as exc:
        st.error(str(exc))
        with st.expander("Қосылу нұсқаулығы"):
            st.write("Жоба папкасындағы терминалда серверді іске қосыңыз:")
            st.code("uvicorn app.main:app --reload", language="bash")
            st.write("Содан кейін «Деректерді жаңарту» батырмасын басыңыз.")
        return

    first, second, third, fourth = st.columns(4)
    first.metric("Нөмірлер", len(rooms))
    second.metric("Қонақтар", len(guests))
    third.metric("Белсенді брондау", sum(item["status"] == "confirmed" for item in bookings))
    fourth.metric("Санаттар", len(categories))
    st.divider()
    if page == "Нөмірлер":
        show_rooms(rooms, categories)
    elif page == "Қонақтар":
        show_guests(guests)
    elif page == "Брондаулар":
        show_bookings(bookings, guests, rooms)
    else:
        show_categories(categories)


if __name__ == "__main__":
    main()
