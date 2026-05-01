import streamlit as st

# =========================
# CONFIG (Your rules)
# =========================
MONTHLY_STANDARD_HOURS = 173.33
WEEKS_PER_YEAR = 52
MONTHS_PER_YEAR = 12

NIGHT_BONUS_PER_HOUR = 2.0
CARD_BONUS_PER_HOUR = 1.0
ROULETTE_BONUS_PER_HOUR = 1.0

LEVEL_RATE = {"Level 1 (€1/hour)": 1.0, "Level 2 (€2.5/hour)": 2.5}
COMMITMENT_RATE = {"10%": 0.10, "20%": 0.20, "30%": 0.30, "40%": 0.40, "50%": 0.50}

OVERTIME_TAX_RATE = 0.25  # Overtime taxed at flat 25% (company rule)

# Tax (Single) - 2026 rate/subtract
TAX_TABLE_SINGLE_2026 = [
    (12000, 0.00, 0),
    (16000, 0.15, 1800),
    (60000, 0.25, 3400),
    (float("inf"), 0.35, 9400),
]

# SSC assumption (most employees born 1962+)
ASSUMED_BIRTH_YEAR = 1990  # forces the 1962+ branch in SSC cap logic


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
    Simplified Class 1 employee SSC:
    - weekly <= 229.44  -> €22.94 fixed
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
st.set_page_config(page_title="Salary Calculator (Malta)", layout="centered")

st.title("Salary Calculator (Malta) — ESTIMATED NET")
st.caption("Tax: Single (2026 table) • SSC: simplified (assumes 1962+) • Overtime: 25% flat tax")

with st.sidebar:
    st.header("Notes")
    st.write("This tool provides an estimate. Official payroll calculations may differ.")
    st.write("SSC is calculated with a simplified model (assumed 1962+ cap).")
    st.write("Overtime is taxed separately at a flat 25% (company rule).")

st.subheader("1) Base Salary")
base = st.number_input("Base salary (gross) €", min_value=0.0, value=2000.0, step=50.0)

st.subheader("2) Overtime")
overtime_hours = st.number_input("Overtime hours", min_value=0.0, value=0.0, step=1.0)

st.subheader("3) Bonuses")
night_hours = st.number_input("Night shift hours", min_value=0.0, value=0.0, step=1.0)

# Eligibility switches for SGC / Performance
colA, colB = st.columns(2)
with colA:
    sgc_eligible = st.checkbox("I receive SGC bonus", value=True)
with colB:
    perf_eligible = st.checkbox("I receive Performance bonus", value=True)

# Total table hours should be provided if any table-based bonus is used
# (SGC/Performance use total table hours, Card/Roulette hours must not exceed total table hours)
table_hours = st.number_input(
    "Total table hours (used for SGC/Performance and validation)",
    min_value=0.0,
    value=0.0,
    step=1.0,
)

# Level selectors only if eligible
col1, col2 = st.columns(2)
with col1:
    sgc_level = st.selectbox("SGC level", list(LEVEL_RATE.keys()), index=0, disabled=not sgc_eligible)
with col2:
    perf_level = st.selectbox("Performance level", list(LEVEL_RATE.keys()), index=0, disabled=not perf_eligible)

st.subheader("4) Card / Roulette")
card_eligible = st.checkbox("I receive Card bonus", value=False)
card_hours = st.number_input("Card table hours", min_value=0.0, value=0.0, step=1.0, disabled=not card_eligible)

roulette_eligible = st.checkbox("I receive Roulette bonus", value=False)
roulette_hours = st.number_input("Roulette table hours", min_value=0.0, value=0.0, step=1.0, disabled=not roulette_eligible)

st.subheader("5) Commitment")
commitment_eligible = st.checkbox("I receive Commitment bonus", value=True)
commitment_choice = st.selectbox(
    "Commitment tier (applied to bonuses excluding night bonus)",
    list(COMMITMENT_RATE.keys()),
    index=0,
    disabled=not commitment_eligible,
)

st.divider()

# =========================
# Validation rules
# =========================
# If any of card/roulette hours > 0, total table hours must be >= their sum.
# Also, if SGC or Performance eligible, total table hours should be > 0 (otherwise bonus will be 0).
needs_table_hours = sgc_eligible or perf_eligible or card_eligible or roulette_eligible

validation_errors = []

if (card_hours + roulette_hours) > table_hours:
    validation_errors.append("Card hours + Roulette hours cannot exceed Total table hours.")

if needs_table_hours and table_hours == 0 and (sgc_eligible or perf_eligible):
    validation_errors.append("Total table hours is 0, but SGC/Performance is enabled. Please enter table hours (or disable those bonuses).")

if validation_errors:
    for e in validation_errors:
        st.error(e)
    can_calc = False
else:
    can_calc = True

# =========================
# Calculate
# =========================
if st.button("Calculate", type="primary", disabled=not can_calc):
    # Hourly rate from base (fixed monthly hours)
    hourly_from_base = base / MONTHLY_STANDARD_HOURS if MONTHLY_STANDARD_HOURS > 0 else 0.0

    # Overtime
    overtime_hourly = hourly_from_base * 1.5
    overtime_gross = overtime_hours * overtime_hourly
    overtime_tax = overtime_gross * OVERTIME_TAX_RATE
    overtime_net = overtime_gross - overtime_tax

    # Bonuses
    night_bonus = night_hours * NIGHT_BONUS_PER_HOUR

    sgc_rate = LEVEL_RATE[sgc_level] if sgc_eligible else 0.0
    perf_rate = LEVEL_RATE[perf_level] if perf_eligible else 0.0

    sgc_bonus = table_hours * sgc_rate
    perf_bonus = table_hours * perf_rate

    card_bonus = (card_hours * CARD_BONUS_PER_HOUR) if card_eligible else 0.0
    roulette_bonus = (roulette_hours * ROULETTE_BONUS_PER_HOUR) if roulette_eligible else 0.0

    bonuses_excl_night = sgc_bonus + perf_bonus + card_bonus + roulette_bonus

    commitment_rate = COMMITMENT_RATE[commitment_choice] if commitment_eligible else 0.0
    commitment_bonus = bonuses_excl_night * commitment_rate

    total_bonuses = night_bonus + bonuses_excl_night + commitment_bonus

    # SSC (base only, assumed 1962+)
    ssc_monthly = monthly_ssc_from_monthly_base(base, ASSUMED_BIRTH_YEAR)

    # Income tax (overtime excluded)
    non_overtime_gross = base + total_bonuses
    chargeable_annual = max(0.0, (non_overtime_gross - ssc_monthly) * 12.0)
    annual_tax = annual_income_tax_single_2026(chargeable_annual)
    monthly_tax = annual_tax / 12.0

    # Totals
    gross_total = non_overtime_gross + overtime_gross
    total_deductions = ssc_monthly + monthly_tax + overtime_tax
    net_total = gross_total - total_deductions

    st.success(f"ESTIMATED NET SALARY: €{net_total:,.2f}")

    st.write("### Breakdown")
    st.write(f"**Base (gross):** €{base:,.2f}")
    st.write(f"**SSC (monthly, on base):** €{ssc_monthly:,.2f}")
    st.write(f"**Income tax (monthly estimate, excluding overtime):** €{monthly_tax:,.2f}")

    st.write("#### Overtime")
    st.write(f"- Hourly rate from base: €{hourly_from_base:,.4f}")
    st.write(f"- Overtime hourly (x1.5): €{overtime_hourly:,.4f}")
    st.write(f"- Overtime gross: €{overtime_gross:,.2f}")
    st.write(f"- Overtime tax (25%): €{overtime_tax:,.2f}")
    st.write(f"- Overtime net: €{overtime_net:,.2f}")

    st.write("#### Bonuses")
    st.write(f"- Night bonus: €{night_bonus:,.2f}")
    st.write(f"- SGC bonus: €{sgc_bonus:,.2f}")
    st.write(f"- Performance bonus: €{perf_bonus:,.2f}")
    st.write(f"- Card bonus: €{card_bonus:,.2f}")
    st.write(f"- Roulette bonus: €{roulette_bonus:,.2f}")
    if commitment_eligible:
        st.write(f"- Commitment bonus ({commitment_choice}): €{commitment_bonus:,.2f}")
    else:
        st.write(f"- Commitment bonus: €{commitment_bonus:,.2f}")
    st.write(f"**Total bonuses:** €{total_bonuses:,.2f}")

    st.write("#### Totals")
    st.write(f"- Non-overtime gross (base + bonuses): €{non_overtime_gross:,.2f}")
    st.write(f"- Total gross: €{gross_total:,.2f}")
    st.write(f"- Total deductions: €{total_deductions:,.2f}")

    st.info("Note: This is an estimate. Official payroll (PAYE/SSC) calculations may differ.")
