## Étape 1 — Importer les bibliothèques

import pandas as pd
import plotly.express as px
import calendar 
import plotly.graph_objects as go
from dash import Dash, html, dcc
from dash.dash_table import DataTable
import dash_bootstrap_components as dbc  
from dash.dash_table import DataTable

## Étape 2 — Charger et préparer les données


df = pd.read_csv("data.csv")

## Garder uniquement les colonnes utiles ('CustomerID', 'Gender', 'Location', 
# 'Product_Category', 'Quantity', 'Avg_Price', 'Transaction_Date', 'Month', 'Discount_pct').

cols_utiles = [
    "CustomerID", "Gender", "Location", "Product_Category",
    "Quantity", "Avg_Price", "Transaction_Date", "Month", "Discount_pct"
]
df = df[cols_utiles].copy()
# Remplacer les valeurs manquantes dans `CustomerID` par 0 et convertir `CustomerID` en entier.
df["CustomerID"] = df["CustomerID"].fillna(0).astype(int)

## Convertir `Transaction_Date` en date.
df["Transaction_Date"] = pd.to_datetime(df["Transaction_Date"], errors="coerce")

## Créer `Total_price` avec la remise.
df["Total_price"] = df["Quantity"] * df["Avg_Price"] * (1 - df["Discount_pct"] / 100)

## verification
print(df.head())
print("\nTypes de colonnes :")
print(df.dtypes)
print(df["Total_price"].describe())

## Étape 3 — Écrire les fonctions métier



### `calculer_chiffre_affaire(data)`
def calculer_chiffre_affaire(data):
    
    if "Total_price" not in data.columns:
        raise KeyError("La colonne 'Total_price' est introuvable. Crée-la à l'étape 2.")

    return float(data["Total_price"].sum())

### `frequence_meilleure_vente(data, top=10, ascending=False)`

def frequence_meilleure_vente(data, top = 10, ascending= False):

    # Compter le nombre de lignes par catégorie + genre
    freq = (
        data.groupby(["Product_Category", "Gender"])
            .size()
            .reset_index(name="Total")
    )

    # Calculer le total (F+M) par catégorie pour trouver le top
    total_cat = (
        freq.groupby("Product_Category")["Total"]
            .sum()
            .sort_values(ascending=False)  
    )

    # Récupérer les catégories du Top N
    top_categories = total_cat.head(top).index

    # Filtrer freq sur ces catégories
    freq_top = freq[freq["Product_Category"].isin(top_categories)].copy()

    # trier le résultat selon le total (F+M) dans l'ordre demandé
   
    order = (
        freq_top.groupby("Product_Category")["Total"]
               .sum()
               .sort_values(ascending=ascending)
               .index
               .tolist()
    )

    # On transforme Product_Category en catégorie ordonnée (utile ensuite pour Plotly)
    freq_top["Product_Category"] = pd.Categorical(freq_top["Product_Category"], categories=order, ordered=True)
    freq_top = freq_top.sort_values("Product_Category")

    return freq_top

### `indicateur_du_mois(data, current_month=12, freq=True, abbr=False)`
def indicateur_du_mois(data, current_month= 12, freq= True, abbr= False):

    
    if "Month" not in data.columns:
        raise KeyError("La colonne 'Month' est introuvable.")

    # Mois précédent 
    previous_month = 12 if current_month == 1 else current_month - 1

    # Filtrer les lignes
    cur = data[data["Month"] == current_month]
    prev = data[data["Month"] == previous_month]

    # Calcul indicateur (fréquence ou CA)
    if freq:
        value_cur = len(cur)
        value_prev = len(prev)
    else:
        if "Total_price" not in data.columns:
            raise KeyError("La colonne 'Total_price' est introuvable.")
        value_cur = cur["Total_price"].sum()
        value_prev = prev["Total_price"].sum()

    delta = value_cur - value_prev

    # Nom du mois
    month_name = calendar.month_abbr[current_month] if abbr else calendar.month_name[current_month]

    return {
        "month_name": month_name,
        "value": value_cur,
        "delta": delta
    }



print("CA total =", calculer_chiffre_affaire(df))

top10_freq = frequence_meilleure_vente(df, top=10, ascending=True)
print("\nTop10 fréquence (aperçu) :")
print(top10_freq.head())

ind_ca = indicateur_du_mois(df, current_month=12, freq=False, abbr=True)
ind_tx = indicateur_du_mois(df, current_month=12, freq=True, abbr=True)

print("\nIndicateur CA Décembre :", ind_ca)
print("Indicateur ventes Décembre :", ind_tx)

## Étape 4 — Créer les graphiques

### Fonctions graphiques

def barplot_top_10_ventes(data):

    top10 = frequence_meilleure_vente(data, top=10, ascending=True).copy()

    # Saut de ligne après le premier espace pour éviter le texte coupé
    top10["Product_Category"] = top10["Product_Category"].str.replace(" ", "<br>", n=1)

    category_order = {"Gender": ["F", "M"]}
    color_discrete_map = {"F": "#636EFA", "M": "#EF553B"}

    fig = px.bar(
        top10,
        x="Total",
        y="Product_Category",
        color="Gender",
        orientation="h",
        barmode="group",
        title="Frequence des 10 meilleures ventes",
        labels={
            "Total": "Total vente",
            "Product_Category": "Categorie du produit",
            "Gender": "Sexe"
        },
        category_orders=category_order,
        color_discrete_map=color_discrete_map,
    )

    fig.update_layout(
    title=dict(
        x=0.02,
        font=dict(size=14)
    ),
    paper_bgcolor="white",
    plot_bgcolor="#dfe6ef",
    margin=dict(l=80, r=20, t=50, b=35),
    height=340,
    legend=dict(
        title="Sexe",
        x=1.02,
        y=0.98
    ),
    font=dict(size=12)
)


    fig.update_xaxes(
        showgrid=True,
        gridcolor="white",
        tickfont=dict(size=10),
        title_font=dict(size=12)
    )

    fig.update_yaxes(
        showgrid=False,
        automargin=True,
        tickfont=dict(size=10),
        title_font=dict(size=12)
    )

    return fig


def plot_evolution_chiffre_affaire(data):

    d = data.copy()

    d["Transaction_Date"] = pd.to_datetime(d["Transaction_Date"])
    d["WeekStart"] = d["Transaction_Date"] - pd.to_timedelta(d["Transaction_Date"].dt.weekday, unit="D")
    d["WeekStart"] = d["WeekStart"].dt.normalize()

    weekly = (
        d.groupby("WeekStart")["Total_price"]
         .sum()
         .reset_index()
         .sort_values("WeekStart")
    )

    fig = px.line(
        weekly,
        x="WeekStart",
        y="Total_price",
        labels={
            "WeekStart": "Semaine",
            "Total_price": "Chiffre d'affaire"
        }
    )

    fig.update_traces(
        line=dict(color="#6272f2", width=2.5)
    )

    fig.update_layout(
        title={
            "text": "Evolution du chiffre d'affaire par semaine",
            "x": 0.02,
            "xanchor": "left",
            "font": dict(size=14, color="#344d73")
        },
        paper_bgcolor="white",
        plot_bgcolor="#dfe6ef",
        margin=dict(l=10, r=20, t=55, b=40),
        height=300, 
        font=dict(color="#344d73", size=12),
        xaxis=dict(
            title="Semaine",
            showgrid=True,
            gridcolor="white",
            zeroline=False
        ),
        yaxis=dict(
            title="Chiffre d'affaire",
            showgrid=True,
            gridcolor="white",
            zeroline=False
        )
    )

    fig.update_xaxes(tickfont=dict(size=10))
    fig.update_yaxes(tickfont=dict(size=10))

    return fig


def plot_chiffre_affaire_mois(data):

    monthly_ca = (
        data.groupby("Month")["Total_price"]
            .sum()
            .reset_index()
            .sort_values("Month")
    )

    fig = px.bar(
        monthly_ca,
        x="Month",
        y="Total_price",
        labels={"Month": "Mois", "Total_price": "Chiffre d'affaire"},
        title="Chiffre d'affaire par mois",
    )

    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="#f5f7fb",
        margin=dict(l=60, r=20, t=50, b=40),
        height=260,
        font=dict(size=11)
    )

    fig.update_xaxes(tickfont=dict(size=9))
    fig.update_yaxes(tickfont=dict(size=9))

    return fig


def plot_vente_mois(data, abbr=False):

    monthly_sales = (
        data.groupby("Month")
            .size()
            .reset_index(name="Total_sales")
            .sort_values("Month")
    )

    if abbr:
        monthly_sales["MonthLabel"] = monthly_sales["Month"].apply(lambda m: calendar.month_abbr[m])
    else:
        monthly_sales["MonthLabel"] = monthly_sales["Month"].apply(lambda m: calendar.month_name[m])

    fig = px.bar(
        monthly_sales,
        x="MonthLabel",
        y="Total_sales",
        labels={"MonthLabel": "Mois", "Total_sales": "Nombre de ventes"},
        title="Nombre de ventes par mois",
    )

    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="#f5f7fb",
        margin=dict(l=60, r=20, t=50, b=40),
        height=260,
        font=dict(size=11)
    )

    fig.update_xaxes(tickfont=dict(size=9))
    fig.update_yaxes(tickfont=dict(size=9))

    return fig


# Vérification (en dehors de Dash)
#barplot_top_10_ventes(df).show()
#plot_evolution_chiffre_affaire(df).show()
#plot_chiffre_affaire_mois(df).show()
#plot_vente_mois(df, abbr=True).show()

## Tableau de bord

# Le filtre au niveau de selection de zonnes: Location
locations_options = [
    {"label": "Toutes les zones", "value": "all"}
] + [
    {"label": loc, "value": loc}
    for loc in sorted(df["Location"].dropna().astype(str).unique())
]

# Les indicateurs

ind_ca = indicateur_du_mois(df, current_month=12, freq=False, abbr=False)
ind_tx = indicateur_du_mois(df, current_month=12, freq=True, abbr=False)
fig_evol_ca = plot_evolution_chiffre_affaire(df)
fig_top10 = barplot_top_10_ventes(df)

# 100 dernières ventes
last100 = (
    df.sort_values("Transaction_Date")
      .tail(100)
      .copy()
)

last100["Transaction_Date"] = pd.to_datetime(last100["Transaction_Date"]).dt.strftime("%Y-%m-%d")

# Colonnes exacts
last100_display = last100[[
    "Transaction_Date",
    "Gender",
    "Location",
    "Product_Category",
    "Quantity",
    "Avg_Price",
    "Discount_pct"
]].rename(columns={
    "Transaction_Date": "Date",
    "Product_Category": "Product Category",
    "Avg_Price": "Avg Price",
    "Discount_pct": "Discount Pct"
})


def format_k(value):
    if abs(value) >= 1000:
        return f"{value/1000:.0f}k"
    return f"{value:.0f}"


def format_delta(value):
    signe = "▲" if value >= 0 else "▼"
    valeur = round(value) 

    if abs(valeur) >= 1000:
        return f"{signe} {valeur/1000:.0f}k" 
    return f"{signe} {valeur:.0f}"


app = Dash(__name__)
server = app.server

app.layout = html.Div(
    [

        # Barre du haut
        html.Div(
            children=[
                html.H2(
                    "ECAP Store",
                    style={
                        "margin": "0",
                        "color": "#24385b",
                        "fontWeight": "700",
                        "fontSize": "30px"
                    }
                ),

                dcc.Dropdown(
                    id="zone-dropdown",
                    options=locations_options,
                    value="all",
                    placeholder="Choisissez des zones",
                    clearable=False,
                    style={
                        "width": "340px",
                        "fontSize": "13px"
                    }
                )
            ],
            style={
                "backgroundColor": "#d6eef8",
                "padding": "8px 32px",
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "center",
                "boxSizing": "border-box"
            }
        ),

        # Grille principale 2x2
        html.Div(
            children=[

                # LIGNE 1 : indicateurs (gauche) + courbe (droite)
                html.Div(
                    children=[

                        # Indicateurs
                        html.Div(
                            children=[
                                html.Div(
                                    children=[
                                        # Indicateur CA
                                        html.Div(
                                            children=[
                                                html.Div(
                                                    ind_ca["month_name"],
                                                    style={
                                                        "fontSize": "15px",
                                                        "color": "#3b547b",
                                                        "marginBottom": "6px",
                                                        "fontWeight": "400"
                                                    }
                                                ),
                                                html.Div(
                                                    format_k(ind_ca["value"]),
                                                    style={
                                                        "fontSize": "50px",
                                                        "fontWeight": "400",
                                                        "color": "#2f4770",
                                                        "lineHeight": "1"
                                                    }
                                                ),
                                                html.Div(
                                                    format_delta(ind_ca["delta"]),
                                                    style={
                                                        "fontSize": "25px",
                                                        "color": "#3ea06d" if ind_ca["delta"] >= 0 else "#ff4b42",
                                                        "marginTop": "3px",
                                                        "fontWeight": "400"
                                                    }
                                                )
                                            ],
                                            style={
                                                "flex": "1",
                                                "textAlign": "left"
                                            }
                                        ),

                                        # Indicateur ventes
                                        html.Div(
                                            children=[
                                                html.Div(
                                                    ind_tx["month_name"],
                                                    style={
                                                        "fontSize": "15px",
                                                        "color": "#3b547b",
                                                        "marginBottom": "6px",
                                                        "fontWeight": "400"
                                                    }
                                                ),
                                                html.Div(
                                                    f'{ind_tx["value"]:.0f}',
                                                    style={
                                                        "fontSize": "50px",
                                                        "fontWeight": "400",
                                                        "color": "#2f4770",
                                                        "lineHeight": "1"
                                                    }
                                                ),
                                                html.Div(
                                                    format_delta(ind_tx["delta"]),
                                                    style={
                                                        "fontSize": "25px",
                                                        "color": "#3ea06d" if ind_tx["delta"] >= 0 else "#ff4b42",
                                                        "marginTop": "3px",
                                                        "fontWeight": "400"
                                                    }
                                                )
                                            ],
                                            style={
                                                "flex": "1",
                                                "textAlign": "left"
                                            }
                                        )
                                    ],
                                    style={
                                        "display": "flex",
                                        "gap": "0px",
                                        "alignItems": "flex-start",
                                        "maxWidth": "380px",
                                        "marginTop": "-10px"
                                    }
                                )
                            ],
                            style={
                                "width": "40%",
                                "paddingTop": "24px",
                                "paddingBottom": "10px",
                                "marginLeft": "50px"  
                            }
                        ),

                        # Graphique évolution CA
                        html.Div(
                            children=[
                                dcc.Graph(
                                    figure=fig_evol_ca,
                                    config={"displayModeBar": False},
                                    style={
                                        "width": "100%",
                                        "height": "100%"
                                    }
                                )
                            ],
                            style={
                                "width": "65%",
                                "height": "298px",
                                "marginTop": "-10px"
                            }
                        )

                    ],
                    style={
                        "display": "flex",
                        "width": "100%",
                        "boxSizing": "border-box",
                        "gap": "24px"
                    }
                ),

                # LIGNE 2 : barplot (gauche) + tableau (droite)
                html.Div(
                    children=[

                        # Barplot top 10
                        html.Div(
                            children=[
                                dcc.Graph(
                                    figure=fig_top10,
                                    config={"displayModeBar": False},
                                    style={
                                        "width": "100%",
                                        "height": "100%"
                                    }
                                )
                            ],
                            style={
                                "width": "44%",
                                "height": "380px",
                                "marginTop": "-150px"
                            }
                        ),

                        # Tableau des 100 dernières ventes (compact)
                        html.Div(
                            children=[
                                html.Div(
                                    "Table des 100 dernières ventes",
                                    style={
                                        "fontSize": "15px",
                                        "fontWeight": "600",
                                        "marginBottom": "4px",
                                        "marginTop": "0px"
                                    }
                                ),
                                DataTable(
                                    id="table-last100",
                                    columns=[{"name": c, "id": c} for c in last100_display.columns],
                                    data=last100_display.to_dict("records"),
                                    page_size=5,
                                    sort_action="native",
                                    filter_action="native",
                                    style_table={
                                        "overflowX": "auto",
                                        "height": "100%"
                                    },
                                    style_header={
                                        "backgroundColor": "#f5f7fb",
                                        "fontWeight": "600",
                                        "padding": "2px"
                                    },
                                    style_cell={
                                        "fontFamily": "Arial, sans-serif",
                                        "fontSize": "11px",
                                        "padding": "1px 1px",
                                        "height": "16px",
                                        "lineHeight": "16px",
                                        "textAlign": "left"
                                    },
                                )
                            ],
                            style={
                                "width": "56%",
                                "height": "200px",
                                "marginTop": "-20px"
                            }
                        )

                    ],
                    style={
                        "display": "flex",
                        "width": "100%",
                        "marginTop": "35px",
                        "gap": "24px",
                        "boxSizing": "border-box"

                    }
                )

            ],
            style={
                "padding": "10px 4px 10px 7px",
                "boxSizing": "border-box"
            }
        )

    ],
    style={
        "backgroundColor": "white",
        "fontFamily": "Arial, sans-serif",
        "fontSize": "14px",
        "paddingBottom": "16px",
        "boxSizing": "border-box"
    }
)

if __name__ == "__main__":
    app.run(debug=True, port=8051)


