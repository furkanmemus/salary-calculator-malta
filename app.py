import streamlit as st

# =========================
# CONFIG (Kuralların)
# =========================
MONTHLY_STANDARD_HOURS = 173.33
WEEKS_PER_YEAR = 52
MONTHS_PER_YEAR = 12

NIGHT_BONUS_PER_HOUR = 2.0
CARD_BONUS_PER_HOUR = 1.0
ROULETTE_BONUS_PER_HOUR = 1.0

LEVEL_RATE = {"Level 1 (1 €/saat)": 1.0, "Level 2 (2.5 €/saat)": 2.5}
COMMITMENT_RATE = {"%10": 0.10, "%20": 0.20, "%30": 0.30, "%40": 0.40, "%50": 0.50}

OVERTIME_TAX_RATE = 0.25  # Overtime %25 flat tax (işyeri kuralı)

# Vergi (Single) - 2026 rate/subtract
TAX_TABLE_SINGLE_2026 = [
    (12000, 0.00, 0),
    (16000, 0.15, 1800),
    (60000, 0.25, 3400),
    (float("inf"), 0.35, 9400),
]


# =========================
# TAX / SSC
# =========================
def annual_income_tax_single_2026(chargeable_annual: float) -> float:
    if chargeable_annual <= 0:
        return 0.0
    for upper, rate, subtract in TAX_TABLE_SINGLE_2026:
        if chargeable_annual <= upper:
            tax = chargeable_annual * rate - subtract
            return tax if tax > 0 else 0.0
    upper, rate, subtract = TAX_TABLE_SINGLE_2026[-1]
    tax = chargeable_annual * rate - subtract
    return tax if tax > 0 else 0.0


def weekly_ssc_employee(weekly_wage: float, birth_year: int) -> float:
    """
    Basitleştirilmiş Class 1 employee SSC:
    - weekly <= 229.44  -> 22.94 fixed
    - born <= 1961: up to 490.38 -> 10% cap 49.04, above -> 49.04
    - born >= 1962: up to 559.30 -> 10% cap 55.93, above -> 55.93
    """
    if weekly_wage <= 229.44:
        return 22.94

    if birth_year <= 1961:
        if weekly_wage <= 490.38:
            return round(weekly_wage * 0.10, 2)
        return 49.04

    if weekly_wage <= 559.30:
        return round(weekly_wage * 0.10, 2)
    return 55.93


def monthly_ssc_from_monthly_base(base_monthly: float, birth_year: int) -> float:
    weekly_base = base_monthly * MONTHS_PER_YEAR / WEEKS_PER_YEAR
    ssc_weekly = weekly_ssc_employee(weekly_base, birth_year)
    return ssc_weekly * WEEKS_PER_YEAR / MONTHS_PER_YEAR


# =========================
# UI
# =========================
st.set_page_config(page_title="Maaş Hesaplayıcı (Malta)", layout="centered")

st.title("Maaş Hesaplayıcı (Malta) — TAHMİNİ NET")
st.caption("Vergi: Single (2026 tablo) • SSC: basitleştirilmiş • Overtime: %25 flat tax")

st.subheader("1) Base Maaş & Kişisel Bilgi")
base = st.number_input("Bonussuz ham maaş (Base maaş) €", min_value=0.0, value=2000.0, step=50.0)
birth_year = st.number_input("Doğum yılı", min_value=1900, max_value=2100, value=1995, step=1)

st.subheader("2) Fazla Mesai (Overtime)")
overtime_hours = st.number_input("Fazla mesai saati", min_value=0.0, value=0.0, step=1.0)

st.subheader("3) Bonuslar")
night_hours = st.number_input("Gece çalışılan saat", min_value=0.0, value=0.0, step=1.0)

table_hours = st.number_input("Toplam masa saati (SGC + Performans için)", min_value=0.0, value=0.0, step=1.0)

col1, col2 = st.columns(2)
with col1:
    sgc_level = st.selectbox("SGC bonus level", list(LEVEL_RATE.keys()), index=0)
with col2:
    perf_level = st.selectbox("Performans bonus level", list(LEVEL_RATE.keys()), index=0)

st.subheader("4) Kart / Rulet")
card_eligible = st.checkbox("Kart bonusu alıyorum", value=False)
card_hours = st.number_input("Kart masa saati", min_value=0.0, value=0.0, step=1.0, disabled=not card_eligible)

roulette_eligible = st.checkbox("Rulet bonusu alıyorum", value=False)
roulette_hours = st.number_input("Rulet masa saati", min_value=0.0, value=0.0, step=1.0, disabled=not roulette_eligible)

st.subheader("5) Commitment")
commitment_choice = st.selectbox(
    "Commitment kademesi (gece hariç bonuslar üzerinden)",
    list(COMMITMENT_RATE.keys()),
    index=0,
)

st.divider()

# Validasyon: kart+rulet > masa olamaz
if (card_hours + roulette_hours) > table_hours:
    st.error("Kart + Rulet masa saatleri, toplam masa saatini GEÇEMEZ. Lütfen düzelt.")
    can_calc = False
else:
    can_calc = True

if st.button("Hesapla", type="primary", disabled=not can_calc):
    # Saatlik (base üzerinden)
    hourly_from_base = base / MONTHLY_STANDARD_HOURS if MONTHLY_STANDARD_HOURS > 0 else 0.0

    # Overtime
    overtime_hourly = hourly_from_base * 1.5
    overtime_gross = overtime_hours * overtime_hourly
    overtime_tax = overtime_gross * OVERTIME_TAX_RATE
    overtime_net = overtime_gross - overtime_tax

    # Bonuslar
    night_bonus = night_hours * NIGHT_BONUS_PER_HOUR

    sgc_rate = LEVEL_RATE[sgc_level]
    perf_rate = LEVEL_RATE[perf_level]

    sgc_bonus = table_hours * sgc_rate
    perf_bonus = table_hours * perf_rate

    card_bonus = (card_hours * CARD_BONUS_PER_HOUR) if card_eligible else 0.0
    roulette_bonus = (roulette_hours * ROULETTE_BONUS_PER_HOUR) if roulette_eligible else 0.0

    bonus_excl_night = sgc_bonus + perf_bonus + card_bonus + roulette_bonus

    commitment_rate = COMMITMENT_RATE[commitment_choice]
    commitment_bonus = bonus_excl_night * commitment_rate

    total_bonuses = night_bonus + bonus_excl_night + commitment_bonus

    # SSC (base only)
    ssc_monthly = monthly_ssc_from_monthly_base(base, int(birth_year))

    # Gelir vergisi (overtime hariç)
    non_overtime_gross = base + total_bonuses
    chargeable_annual = max(0.0, (non_overtime_gross - ssc_monthly) * 12.0)
    annual_tax = annual_income_tax_single_2026(chargeable_annual)
    monthly_tax = annual_tax / 12.0

    # Toplamlar
    gross_total = non_overtime_gross + overtime_gross
    total_deductions = ssc_monthly + monthly_tax + overtime_tax
    net_total = gross_total - total_deductions

    st.success(f"TAHMİNİ NET MAAŞ: €{net_total:,.2f}")

    st.write("### Döküm")
    st.write(f"**Base (brüt):** €{base:,.2f}")
    st.write(f"**SSC (aylık, base üstünden):** €{ssc_monthly:,.2f}")
    st.write(f"**Gelir vergisi (overtime hariç, aylık tahmini):** €{monthly_tax:,.2f}")
    st.write(f"**Overtime brüt:** €{overtime_gross:,.2f}  | **Overtime vergi (%25):** €{overtime_tax:,.2f} | **Overtime net:** €{overtime_net:,.2f}")

    st.write("#### Bonuslar")
    st.write(f"- Gece bonusu: €{night_bonus:,.2f}")
    st.write(f"- SGC bonusu: €{sgc_bonus:,.2f}")
    st.write(f"- Performans bonusu: €{perf_bonus:,.2f}")
    st.write(f"- Kart bonusu: €{card_bonus:,.2f}")
    st.write(f"- Rulet bonusu: €{roulette_bonus:,.2f}")
    st.write(f"- Commitment bonusu ({commitment_choice}): €{commitment_bonus:,.2f}")
    st.write(f"**Toplam bonus:** €{total_bonuses:,.2f}")

    st.write("#### Genel Toplam")
    st.write(f"**Non-overtime brüt (base+bonus):** €{non_overtime_gross:,.2f}")
    st.write(f"**Toplam brüt:** €{gross_total:,.2f}")
    st.write(f"**Toplam kesinti:** €{total_deductions:,.2f}")

    st.info("Not: Bu sonuç tahminidir. Bordro hesapları işyerine göre küçük farklılık gösterebilir.")
