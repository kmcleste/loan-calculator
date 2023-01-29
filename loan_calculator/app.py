import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd


def main():
    st.title(body="Loan Calculator")

    sale_price: float = st.number_input(
        label="Sale Price", min_value=0.0, value=500_000.0
    )
    down_pmt: float = st.number_input(
        label="Down Payment",
        min_value=0.0,
        value=0.05,
        help="Accepts either dollar amount or percentage.",
    )
    interest_rate: float = st.number_input(
        label="Interest Rate",
        min_value=0.0,
        value=6.125,
        format="%.3f",
        help="Accepts percentage or value [0, 100].",
    )
    property_taxes: float = st.number_input(
        label="Property Taxes",
        min_value=0.0,
        max_value=100.0,
        value=1.3,
        help="Accepts percentage or value [0, 100].",
        format="%.3f",
    )
    home_insurance: float = st.number_input(
        label="Homeowners Insurance", min_value=0.0, value=1000.0
    )
    hoa: float = st.number_input(label="HOA Dues", min_value=0.0, value=200.0)

    kwargs: dict = {
        "sale_price": sale_price,
        "down_pmt": down_pmt,
        "interest_rate": interest_rate,
        "property_taxes": property_taxes,
        "home_insurance": home_insurance,
        "hoa": hoa,
    }

    resp = calculate(**kwargs)

    df: pd.DataFrame = resp["amortization"]
    total_payment: float = df["Interest Payment"].sum() + df["Principal Payment"].sum()

    labels: list = ["Monthly Payment", "Homeowners Insurace", "Property Taxes", "HOA"]
    values: list = [
        resp["monthly_pmt"],
        resp["monthly_home_insurance"],
        resp["monthly_property_tax"],
        hoa,
    ]

    fig: go.Figure = payment_pie(
        labels=labels, values=values, total_monthly_payment=resp["total_payment"]
    )
    st.plotly_chart(fig, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    col1.metric(
        label=":green[Principal Payment]",
        value=f"${df['Principal Payment'].sum():,.0f}",
    )
    col2.metric(
        label=":green[Interest Payment]", value=f"${df['Interest Payment'].sum():,.0f}"
    )
    col3.metric(label=":green[Total Payment (P+I)]", value=f"${total_payment:,.0f}")

    st.plotly_chart(figure_or_data=resp["chart"], use_container_width=True)

    st.dataframe(df.style.format(formatter="$ {:,.2f}"), use_container_width=True)

    st.download_button(
        label="Export Amortization Schedule",
        file_name="Amortization Schedule.csv",
        data=df.to_csv(sep=",", index=False),
    )


def calculate(**kwargs) -> float:
    kwargs["down_pmt"] = convert_down_payment(
        down_pmt=kwargs["down_pmt"], sale_price=kwargs["sale_price"]
    )
    financed_amt: float = kwargs["sale_price"] - kwargs["down_pmt"]
    kwargs["property_taxes"] = convert_rates(rate=kwargs["property_taxes"])
    kwargs["interest_rate"] = convert_rates(rate=kwargs["interest_rate"])
    monthly_interest_rate: float = kwargs["interest_rate"] / 12

    monthly_pmt: float = monthly_payment(
        monthly_interest_rate=monthly_interest_rate, financed_amt=financed_amt
    )
    principal_pmt, interest_pmt, balance = amortization(
        monthly_payment=monthly_pmt,
        monthly_interest_rate=monthly_interest_rate,
        financed_amt=financed_amt,
    )
    total_payment, monthly_home_insurance, monthly_property_tax = total_monthly_payment(
        monthly_payment=monthly_pmt,
        property_taxes=kwargs["property_taxes"],
        home_insurance=kwargs["home_insurance"],
        hoa=kwargs["hoa"],
        sale_price=kwargs["sale_price"],
    )

    df: pd.DataFrame = pd.DataFrame(
        zip(principal_pmt, interest_pmt, balance),
        columns=["Principal Payment", "Interest Payment", "Balance"],
    )

    fig = amortization_chart(dataframe=df)

    return {
        "financed_amt": financed_amt,
        "monthly_pmt": monthly_pmt,
        "amortization": df,
        "chart": fig,
        "total_payment": total_payment,
        "monthly_home_insurance": monthly_home_insurance,
        "monthly_property_tax": monthly_property_tax,
    }


def convert_down_payment(down_pmt: float, sale_price: float) -> float:
    if 0 <= down_pmt <= 1:
        return sale_price * down_pmt
    else:
        return down_pmt


def convert_rates(rate: float) -> float:
    if 0 <= rate <= 1:
        return rate
    else:
        return rate / 100


def monthly_payment(monthly_interest_rate: float, financed_amt: float) -> float:
    numer: float = monthly_interest_rate * (1 + monthly_interest_rate) ** 361
    denom: float = (1 + monthly_interest_rate) ** 361 - 1

    return financed_amt * (numer / denom)


def principal_payment(
    monthly_payment: float, monthly_interest_rate: float, financed_amt: float
) -> float:
    return monthly_payment - (financed_amt * monthly_interest_rate)


def amortization(
    monthly_payment: float, monthly_interest_rate: float, financed_amt: float
) -> tuple[list]:
    interest_pmt: list = []
    principal_pmt: list = []
    balance: list = []

    for _ in range(1, 362):
        principal: float = principal_payment(
            monthly_payment=monthly_payment,
            monthly_interest_rate=monthly_interest_rate,
            financed_amt=financed_amt,
        )
        interest: float = monthly_payment - principal

        interest_pmt.append(interest)
        principal_pmt.append(principal)

        financed_amt = financed_amt - principal
        balance.append(financed_amt)

    return principal_pmt, interest_pmt, balance


def amortization_chart(dataframe: pd.DataFrame) -> go.Figure:
    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    hovertemplate = "$%{y:,.2f}"

    fig.update_layout(
        template="ggplot2",
        height=750,
        legend={"font": {"size": 20}},
        font={"size": 20},
        hovermode="x unified",
        hoverlabel={"font_size": 20},
    )

    # Add traces
    fig.add_trace(
        go.Scatter(
            y=dataframe["Principal Payment"],
            name="Principal",
            hovertemplate=hovertemplate,
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            y=dataframe["Interest Payment"],
            name="Interest",
            hovertemplate=hovertemplate,
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(y=dataframe["Balance"], name="Balance", hovertemplate=hovertemplate),
        secondary_y=True,
    )

    # Add figure title
    fig.update_layout(title_text="Amortization Schedule")

    fig.update_xaxes(tickfont={"size": 20})

    # Set y-axes titles
    fig.update_yaxes(tickfont={"size": 20}, titlefont={"size": 20})
    fig.update_yaxes(title_text="P + I", secondary_y=False)
    fig.update_yaxes(title_text="Remaining Balance", secondary_y=True)

    return fig


def total_monthly_payment(
    monthly_payment: float,
    property_taxes: float,
    home_insurance: float,
    hoa: float,
    sale_price: float,
) -> float:
    monthly_home_insurance: float = home_insurance / 12
    monthly_property_tax: float = (sale_price * property_taxes) / 12

    total_payment: float = (
        monthly_payment + monthly_home_insurance + monthly_property_tax + hoa
    )

    return total_payment, monthly_home_insurance, monthly_property_tax


def payment_pie(
    labels: list[str], values: list[float], total_monthly_payment: float
) -> go.Figure:
    fig = go.Figure()

    hovertemplate = "%{label}: $%{value:,.2f} <extra></extra>"

    fig.update_layout(
        font={"size": 20},
        template="ggplot2",
        height=650,
        legend={"font": {"size": 20}},
        hoverlabel={"font_size": 20},
    )
    fig.add_trace(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.5,
            title=f"${total_monthly_payment:,.2f}",
            hovertemplate=hovertemplate,
        )
    )

    return fig


if __name__ == "__main__":
    st.set_page_config(page_title="Loan Calculator", page_icon="🏠", layout="wide")
    main()
