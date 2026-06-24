"""
Calculadora IPTU — São José/SC
LC 21/2005 (Código Tributário) · Lei 3.440/1999 (Planta Genérica de Valores)

Correção monetária via API do BCB/SGS (IPCA, INPC, IGP-M, IGP-DI, IPC-FIPE)
com fallback para valores históricos embutidos caso a API esteja indisponível.
"""

import streamlit as st
import pandas as pd
import requests
from datetime import date

st.set_page_config(
    page_title="Calculadora IPTU — São José/SC",
    page_icon="🏠",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────
# INDICADORES DISPONÍVEIS (SGS/BCB)
# ─────────────────────────────────────────────────────────────
INDICADORES = {
    "IPCA (IBGE)":  {"codigo": 433,  "desc": "Índice de Preços ao Consumidor Amplo"},
    "INPC (IBGE)":  {"codigo": 188,  "desc": "Índice Nacional de Preços ao Consumidor"},
    "IGP-M (FGV)":  {"codigo": 189,  "desc": "Índice Geral de Preços do Mercado"},
    "IGP-DI (FGV)": {"codigo": 190,  "desc": "Índice Geral de Preços — Disponibilidade Interna"},
    "IPC-FIPE":     {"codigo": 193,  "desc": "Índice de Preços ao Consumidor FIPE"},
    "IPCA-15 (IBGE)":{"codigo":7478, "desc": "IPCA-15"},
}

# Fallback IPCA anual (Dez→Dez) para uso sem internet
IPCA_FALLBACK = {
    1999:8.94, 2000:5.97, 2001:7.67, 2002:12.53, 2003:9.30,
    2004:7.60, 2005:5.69, 2006:3.14, 2007:4.46, 2008:5.90,
    2009:4.31, 2010:5.91, 2011:6.50, 2012:5.84, 2013:5.91,
    2014:6.41, 2015:10.67,2016:6.29, 2017:2.95, 2018:3.75,
    2019:4.31, 2020:4.52, 2021:10.06,2022:5.79, 2023:4.62,
    2024:4.83, 2025:4.26,
}

# ─────────────────────────────────────────────────────────────
# TABELAS DA LEGISLAÇÃO
# ─────────────────────────────────────────────────────────────
VB_TABLE = {
    "Casa":          6.75,
    "Apartamento":   3.40,
    "Sala Comercial":3.40,
    "Galpão":        2.70,
    "Telheiro":      1.35,
    "Fábrica":       3.15,
    "Especial":      5.40,
    "Garagem":       3.00,
}

T1_OPTIONS = {
    "Meio de quadra":               1.00,
    "Esquina / Mais de uma frente": 1.10,
    "Vila":                         0.80,
    "Condomínio horizontal":        0.80,
    "Encravado":                    0.80,
    "Aglomerado":                   0.80,
    "Gleba":                        0.50,
}
T2_OPTIONS = {
    "Sem restrição":         1.00,
    "APP Total":             0.20,
    "APP Limitada Parcial":  0.50,
    "APM Permanente Total":  0.20,
    "APM Limitada Parcial":  0.50,
}
T3_OPTIONS = {"Plano":1.00,"Aclive":0.90,"Declive":0.70,"Irregular":0.80}
T4_OPTIONS = {"Firme":1.00,"Alagado/Brejo/Mangue":0.70,"Arenoso":0.80}
C1_OPTIONS = {
    "Novo (até 1 ano)":       1.00,
    "Mais de 1 até 5 anos":   0.90,
    "Acima de 5 até 10 anos": 0.80,
    "Acima de 10 até 20 anos":0.70,
    "Acima de 20 até 50 anos":0.60,
    "Acima de 50 anos":       0.50,
}

C2_TABLE = {
    "Cobertura":{
        "Telha de cimento amianto":{"Casa":8,"Apartamento":8,"Sala Comercial":8,"Galpão":11,"Telheiro":20,"Fábrica":16,"Especial":16,"Garagem":8},
        "Telha de barro Jage":     {"Casa":4,"Apartamento":4,"Sala Comercial":4,"Galpão":9, "Telheiro":15,"Fábrica":8, "Especial":3, "Garagem":4},
        "Laje":                    {"Casa":7,"Apartamento":10,"Sala Comercial":7,"Galpão":13,"Telheiro":28,"Fábrica":11,"Especial":3, "Garagem":10},
        "Especial":                {"Casa":9,"Apartamento":9,"Sala Comercial":9,"Galpão":16,"Telheiro":35,"Fábrica":12,"Especial":3, "Garagem":9},
    },
    "Paredes":{
        "Sem":            {"Casa":0, "Apartamento":0, "Sala Comercial":0, "Galpão":0, "Telheiro":0,"Fábrica":0, "Especial":0, "Garagem":0},
        "Alvenaria":      {"Casa":23,"Apartamento":20,"Sala Comercial":20,"Galpão":20,"Telheiro":0,"Fábrica":30,"Especial":22,"Garagem":20},
        "Madeira simples":{"Casa":3, "Apartamento":3, "Sala Comercial":10,"Galpão":10,"Telheiro":0,"Fábrica":20,"Especial":10,"Garagem":3},
        "Madeira dupla":  {"Casa":5, "Apartamento":5, "Sala Comercial":5, "Galpão":10,"Telheiro":0,"Fábrica":20,"Especial":10,"Garagem":5},
        "Refugos":        {"Casa":2, "Apartamento":2, "Sala Comercial":2, "Galpão":2, "Telheiro":0,"Fábrica":2, "Especial":2, "Garagem":2},
        "Mista":          {"Casa":5, "Apartamento":5, "Sala Comercial":5, "Galpão":5, "Telheiro":0,"Fábrica":10,"Especial":10,"Garagem":5},
    },
    "Forro":{
        "Sem":     {"Casa":0, "Apartamento":0, "Sala Comercial":0, "Galpão":0,"Telheiro":0,"Fábrica":0,"Especial":0,"Garagem":0},
        "Madeira": {"Casa":6, "Apartamento":6, "Sala Comercial":6, "Galpão":4,"Telheiro":2,"Fábrica":4,"Especial":3,"Garagem":6},
        "Laje":    {"Casa":13,"Apartamento":17,"Sala Comercial":17,"Galpão":5,"Telheiro":3,"Fábrica":3,"Especial":3,"Garagem":17},
        "Chapas":  {"Casa":3, "Apartamento":3, "Sala Comercial":3, "Galpão":5,"Telheiro":3,"Fábrica":3,"Especial":3,"Garagem":3},
        "Especial":{"Casa":13,"Apartamento":17,"Sala Comercial":17,"Galpão":5,"Telheiro":3,"Fábrica":5,"Especial":5,"Garagem":17},
    },
    "Instalação":{
        "Sem":               {"Casa":0, "Apartamento":0, "Sala Comercial":0, "Galpão":0,"Telheiro":0, "Fábrica":0, "Especial":0, "Garagem":0},
        "Mais de 1 inteira": {"Casa":17,"Apartamento":10,"Sala Comercial":10,"Galpão":2,"Telheiro":12,"Fábrica":12,"Especial":10,"Garagem":10},
        "Interna simples":   {"Casa":5, "Apartamento":5, "Sala Comercial":5, "Galpão":5,"Telheiro":5, "Fábrica":5, "Especial":5, "Garagem":5},
        "Interna completa":  {"Casa":10,"Apartamento":5, "Sala Comercial":5, "Galpão":2,"Telheiro":1, "Fábrica":2, "Especial":5, "Garagem":5},
    },
    "Piso":{
        "Taco":        {"Casa":8, "Apartamento":5, "Sala Comercial":21,"Galpão":18,"Telheiro":20,"Fábrica":15,"Especial":20,"Garagem":5},
        "Cimento":     {"Casa":3, "Apartamento":3, "Sala Comercial":3, "Galpão":14,"Telheiro":10,"Fábrica":12,"Especial":10,"Garagem":3},
        "Terra batida":{"Casa":0, "Apartamento":0, "Sala Comercial":0, "Galpão":0, "Telheiro":0, "Fábrica":0, "Especial":0, "Garagem":0},
        "Tábuas":      {"Casa":4, "Apartamento":4, "Sala Comercial":18,"Galpão":16,"Telheiro":15,"Fábrica":14,"Especial":0, "Garagem":4},
        "Carpete":     {"Casa":19,"Apartamento":15,"Sala Comercial":18,"Galpão":20,"Telheiro":29,"Fábrica":17,"Especial":19,"Garagem":15},
        "Cerâmica":    {"Casa":8, "Apartamento":8, "Sala Comercial":19,"Galpão":18,"Telheiro":20,"Fábrica":19,"Especial":20,"Garagem":8},
        "Especial":    {"Casa":19,"Apartamento":19,"Sala Comercial":19,"Galpão":20,"Telheiro":27,"Fábrica":17,"Especial":21,"Garagem":19},
    },
    "Esquadrias":{
        "Ferro":            {"Casa":11,"Apartamento":11,"Sala Comercial":11,"Galpão":11,"Telheiro":11,"Fábrica":11,"Especial":11,"Garagem":11},
        "Alumínio":         {"Casa":13,"Apartamento":21,"Sala Comercial":21,"Galpão":21,"Telheiro":21,"Fábrica":21,"Especial":21,"Garagem":21},
        "Madeira Veneziana":{"Casa":9, "Apartamento":8, "Sala Comercial":8, "Galpão":8, "Telheiro":8, "Fábrica":8, "Especial":8, "Garagem":8},
        "Madeira simples":  {"Casa":3, "Apartamento":3, "Sala Comercial":2, "Galpão":2, "Telheiro":2, "Fábrica":2, "Especial":2, "Garagem":3},
        "Especial":         {"Casa":13,"Apartamento":13,"Sala Comercial":13,"Galpão":13,"Telheiro":13,"Fábrica":13,"Especial":13,"Garagem":13},
    },
}

# ─────────────────────────────────────────────────────────────
# FUNÇÕES
# ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=86400, show_spinner="Consultando BCB/SGS...")
def fetch_bcb(codigo: int, data_ini: str, data_fim: str) -> pd.DataFrame:
    """Busca série mensal do SGS/BCB e retorna DataFrame tratado."""
    url = (
        f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
        f"?formato=json&dataInicial={data_ini}&dataFinal={data_fim}"
    )
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    raw = resp.json()
    if not raw:
        raise ValueError("API retornou lista vazia para o período informado.")
    df = pd.DataFrame(raw)
    df["data"]      = pd.to_datetime(df["data"], format="%d/%m/%Y")
    df["taxa"]      = pd.to_numeric(df["valor"], errors="coerce")
    df["fator_mes"] = 1 + df["taxa"] / 100
    df["fator_acum"]= df["fator_mes"].cumprod()
    df["ano"]       = df["data"].dt.year
    df["mes"]       = df["data"].dt.month
    return df[["data","ano","mes","taxa","fator_mes","fator_acum"]].dropna()


def fator_fallback_ipca(ano_lei: int, ano_exercicio: int) -> float:
    """Fator acumulado usando taxas anuais hardcoded (fallback sem internet)."""
    f = 1.0
    for y in range(ano_lei + 1, ano_exercicio + 1):
        if y in IPCA_FALLBACK:
            f *= (1 + IPCA_FALLBACK[y] / 100)
    return f


def df_anual(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega variação anual a partir do DataFrame mensal."""
    return (
        df.groupby("ano")["fator_mes"]
        .prod()
        .reset_index()
        .assign(variacao_pct=lambda x: (x["fator_mes"] - 1) * 100)
        .rename(columns={"fator_mes": "fator_anual"})
    )


def calc_vt(vu, at, t1, t2, t3, t4):
    return ((vu * at) * t1 * t2 * t3 * t4) * 1.10

def calc_vc(ac, vb_rs, c1, c2):
    return (ac * vb_rs * c1 * c2) * 1.18

def calc_c2(tipo, cob, par, forr, inst, piso, esq):
    pts = (
        C2_TABLE["Cobertura"][cob][tipo]   +
        C2_TABLE["Paredes"][par][tipo]      +
        C2_TABLE["Forro"][forr][tipo]       +
        C2_TABLE["Instalação"][inst][tipo]  +
        C2_TABLE["Piso"][piso][tipo]        +
        C2_TABLE["Esquadrias"][esq][tipo]
    )
    return pts, pts / 100

def fmt(v): return f"R$ {v:,.2f}"

# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Parâmetros Gerais")

    urm = st.number_input("URM do exercício (R$)", value=275.41,
                          step=0.01, format="%.2f")

    st.divider()
    st.subheader("Planta Genérica de Valores")
    vu_original = st.number_input(
        "Vu original na PGV (R$/m²)", value=149.35,
        step=0.0001, format="%.4f",
        help="Valor unitário básico do terreno na lei original",
    )

    anos = list(range(1994, 2028))
    c1s, c2s = st.columns(2)
    with c1s:
        ano_lei = st.selectbox("Ano da lei", anos, index=anos.index(1999))
    with c2s:
        ano_exercicio = st.selectbox("Exercício", anos, index=anos.index(2026))

    st.divider()
    st.subheader("Índice de Correção")

    indicador_nome = st.selectbox(
        "Indicador", list(INDICADORES.keys()),
        help="Dados obtidos em tempo real via API do Banco Central (SGS)",
    )
    ind = INDICADORES[indicador_nome]
    st.caption(ind["desc"])

    # Datas para a API: Jan/(ano_lei+1) → Dez/(ano_exercicio-1)
    d_ini = f"01/01/{ano_lei + 1}"
    d_fim = f"31/12/{ano_exercicio - 1}"

    usar_api = True
    df_series = None
    fator = None
    fonte = ""

    if st.button("🔄 Buscar / Atualizar", use_container_width=True):
        st.cache_data.clear()

    try:
        df_series = fetch_bcb(ind["codigo"], d_ini, d_fim)
        fator = df_series["fator_mes"].prod()
        fonte = f"API BCB/SGS — código {ind['codigo']}"
    except Exception as e:
        usar_api = False
        if indicador_nome == "IPCA (IBGE)":
            fator = fator_fallback_ipca(ano_lei, ano_exercicio)
            fonte = "⚠️ Fallback — taxas anuais IPCA embutidas (sem API)"
        else:
            fator = None
            fonte = f"❌ API indisponível e não há fallback para {indicador_nome}"
        with st.expander("Detalhes do erro"):
            st.code(str(e))

    vu_corrigido = vu_original * fator if fator else None

    if fator:
        st.metric("Fator acumulado", f"{fator:.6f}")
        st.metric("Vu corrigido", fmt(vu_corrigido))
        st.caption(fonte)
    else:
        st.error("Não foi possível calcular o fator. Verifique a conexão ou escolha IPCA.")

    # Gráfico e tabela do indicador
    if df_series is not None and not df_series.empty:
        with st.expander("📊 Evolução do indicador"):
            tab_graf, tab_anual, tab_mensal = st.tabs(["Gráfico", "Anual", "Mensal"])
            dfa = df_anual(df_series)
            with tab_graf:
                st.line_chart(
                    df_series.set_index("data")["fator_acum"],
                    x_label="Data", y_label="Fator acumulado",
                )
            with tab_anual:
                dfa_show = dfa.copy()
                dfa_show["variacao_pct"] = dfa_show["variacao_pct"].map("{:.2f}%".format)
                dfa_show["fator_anual"]  = dfa_show["fator_anual"].map("{:.6f}".format)
                st.dataframe(dfa_show.rename(columns={
                    "ano":"Ano","fator_anual":"Fator","variacao_pct":"Variação (%)"
                }), hide_index=True, use_container_width=True)
            with tab_mensal:
                df_show = df_series[["data","taxa","fator_acum"]].copy()
                df_show["data"]       = df_show["data"].dt.strftime("%m/%Y")
                df_show["taxa"]       = df_show["taxa"].map("{:.2f}%".format)
                df_show["fator_acum"] = df_show["fator_acum"].map("{:.6f}".format)
                st.dataframe(df_show.rename(columns={
                    "data":"Período","taxa":"Taxa (%)","fator_acum":"Fator Acum."
                }), hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("Valor cobrado (opcional)")
    valor_cobrado = st.number_input("Total no carnê (R$)", value=0.0,
                                    step=0.01, format="%.2f")

# ─────────────────────────────────────────────────────────────
# CORPO PRINCIPAL
# ─────────────────────────────────────────────────────────────
st.title("🏠 Calculadora IPTU — São José/SC")
st.caption("LC 21/2005 (Código Tributário Municipal) · Lei 3.440/1999 (Planta Genérica de Valores)")

if not fator:
    st.error("Configure o índice de correção na barra lateral para continuar.")
    st.stop()

# ── Unidades ─────────────────────────────────────────────────
st.subheader("Unidades do Imóvel")
n_unidades = st.number_input("Quantidade de unidades", min_value=1, max_value=8,
                              value=2, step=1)

DEFAULTS = [
    {"nome":"Apartamento nº","tipo_idx":1,"at":10.0,"ac":100.0,
     "t1_idx":1,"t2_idx":0,"t3_idx":0,"t4_idx":0,"c1_idx":1,
     "cob_idx":2,"par_idx":1,"for_idx":2,"ins_idx":1,"pis_idx":5,"esq_idx":1},
    {"nome":"Garagem nº","tipo_idx":7,"at":1.0,"ac":15.0,
     "t1_idx":1,"t2_idx":0,"t3_idx":0,"t4_idx":0,"c1_idx":1,
     "cob_idx":2,"par_idx":1,"for_idx":2,"ins_idx":0,"pis_idx":1,"esq_idx":1},
]

def dfl(i, key, fallback):
    return DEFAULTS[i].get(key, fallback) if i < len(DEFAULTS) else fallback

tipos = list(VB_TABLE.keys())
resultados = []
tabs = st.tabs([f"Unidade {i+1}" for i in range(n_unidades)])

for i, tab in enumerate(tabs):
    with tab:
        col_id, col_areas = st.columns(2)

        with col_id:
            st.markdown("##### Identificação")
            nome = st.text_input("Descrição", key=f"nome_{i}",
                                 value=dfl(i,"nome",f"Unidade {i+1}"))
            tipo = st.selectbox("Tipo de edificação (Art. 237 / Anexo I)",
                                tipos, key=f"tipo_{i}",
                                index=dfl(i,"tipo_idx",0))
            vb_urm = VB_TABLE[tipo]
            vb_rs  = vb_urm * urm
            st.info(f"**Vb:** {vb_urm} URM/m² = {fmt(vb_rs)}/m²")

        with col_areas:
            st.markdown("##### Áreas")
            at = st.number_input("At — Fração ideal do terreno (m²)",
                                 min_value=0.0001, step=0.0001, format="%.4f",
                                 key=f"at_{i}", value=float(dfl(i,"at",10.0)))
            ac = st.number_input("Ac — Área construída / real total (m²)",
                                 min_value=0.0001, step=0.0001, format="%.4f",
                                 key=f"ac_{i}", value=float(dfl(i,"ac",50.0)))

        st.divider()
        st.markdown("##### Fatores de Correção do Terreno (Art. 233 §1)")
        ft1, ft2, ft3, ft4 = st.columns(4)
        with ft1: t1k = st.selectbox("T1 — Situação",    list(T1_OPTIONS), key=f"t1_{i}", index=dfl(i,"t1_idx",0))
        with ft2: t2k = st.selectbox("T2 — Aproveitamento",list(T2_OPTIONS),key=f"t2_{i}", index=dfl(i,"t2_idx",0))
        with ft3: t3k = st.selectbox("T3 — Topografia",  list(T3_OPTIONS), key=f"t3_{i}", index=dfl(i,"t3_idx",0))
        with ft4: t4k = st.selectbox("T4 — Pedologia",   list(T4_OPTIONS), key=f"t4_{i}", index=dfl(i,"t4_idx",0))
        t1,t2,t3,t4 = T1_OPTIONS[t1k],T2_OPTIONS[t2k],T3_OPTIONS[t3k],T4_OPTIONS[t4k]

        st.divider()
        st.markdown("##### Fatores de Correção da Construção (Art. 233 §2)")
        fc1, fc2 = st.columns([1, 3])

        with fc1:
            c1k = st.selectbox("C1 — Depreciação (idade)", list(C1_OPTIONS),
                               key=f"c1_{i}", index=dfl(i,"c1_idx",0))
            c1  = C1_OPTIONS[c1k]
            st.metric("C1", c1)

        with fc2:
            st.markdown("**C2 — Componentes da Edificação**")
            gc1, gc2, gc3 = st.columns(3)
            with gc1:
                cob  = st.selectbox("Cobertura",  list(C2_TABLE["Cobertura"]),  key=f"cob_{i}", index=dfl(i,"cob_idx",2))
                par  = st.selectbox("Paredes",     list(C2_TABLE["Paredes"]),    key=f"par_{i}", index=dfl(i,"par_idx",1))
            with gc2:
                forr = st.selectbox("Forro",       list(C2_TABLE["Forro"]),      key=f"for_{i}", index=dfl(i,"for_idx",2))
                inst = st.selectbox("Instalação",  list(C2_TABLE["Instalação"]), key=f"ins_{i}", index=dfl(i,"ins_idx",1))
            with gc3:
                piso = st.selectbox("Piso",        list(C2_TABLE["Piso"]),       key=f"pis_{i}", index=dfl(i,"pis_idx",5))
                esq  = st.selectbox("Esquadrias",  list(C2_TABLE["Esquadrias"]), key=f"esq_{i}", index=dfl(i,"esq_idx",1))

        pts, c2 = calc_c2(tipo, cob, par, forr, inst, piso, esq)
        det = " + ".join(
            f"{k}={C2_TABLE[k][v][tipo]}"
            for k,v in [("Cobertura",cob),("Paredes",par),("Forro",forr),
                        ("Instalação",inst),("Piso",piso),("Esquadrias",esq)]
        )
        st.info(f"**C2:** {det} = **{pts} pts → {c2:.2f}**")

        st.divider()

        # ── Cálculo ──────────────────────────────────────────
        vt     = calc_vt(vu_corrigido, at, t1, t2, t3, t4)
        vc     = calc_vc(ac, vb_rs, c1, c2)
        vi     = vt + vc
        iptu_t = vt * 0.01
        iptu_p = vc * 0.005
        iptu   = iptu_t + iptu_p

        resultados.append({
            "Unidade":       nome,
            "Tipo":          tipo,
            "C2 (pts)":      pts,
            "Vt (R$)":       vt,
            "Vc (R$)":       vc,
            "Vi (R$)":       vi,
            "IPTU Territ.":  iptu_t,
            "IPTU Predial":  iptu_p,
            "IPTU Total":    iptu,
        })

        m1,m2,m3,m4,m5 = st.columns(5)
        m1.metric("Vt",              fmt(vt))
        m2.metric("Vc",              fmt(vc))
        m3.metric("Vi",              fmt(vi))
        m4.metric("IPTU Territ. 1%", fmt(iptu_t))
        m5.metric("IPTU Predial 0,5%",fmt(iptu_p))
        st.success(f"**IPTU — {nome}: {fmt(iptu)}**")

# ─────────────────────────────────────────────────────────────
# RESULTADO CONSOLIDADO
# ─────────────────────────────────────────────────────────────
st.divider()
st.header("📊 Resultado Consolidado")

if resultados:
    df_res = pd.DataFrame(resultados)
    fmt_cols = ["Vt (R$)","Vc (R$)","Vi (R$)","IPTU Territ.","IPTU Predial","IPTU Total"]
    df_show = df_res.copy()
    for c in fmt_cols:
        df_show[c] = df_show[c].map(lambda v: f"R$ {v:,.2f}")
    st.dataframe(df_show, use_container_width=True, hide_index=True)

    total_t = sum(r["IPTU Territ."] for r in resultados)
    total_p = sum(r["IPTU Predial"] for r in resultados)
    total   = sum(r["IPTU Total"]   for r in resultados)

    c1r,c2r,c3r = st.columns(3)
    c1r.metric("Total Territorial", fmt(total_t))
    c2r.metric("Total Predial",     fmt(total_p))
    c3r.metric("IPTU TOTAL",        fmt(total))

    if valor_cobrado > 0:
        st.divider()
        dif = valor_cobrado - total
        pct = (dif / total) * 100 if total else 0
        d1,d2,d3 = st.columns(3)
        d1.metric("Calculado",  fmt(total))
        d2.metric("Cobrado",    fmt(valor_cobrado))
        d3.metric("Diferença",  fmt(dif), delta=f"{pct:+.1f}%", delta_color="inverse")
        if dif > 1:
            st.warning(
                f"⚠️ O valor cobrado é **{fmt(dif)} ({pct:.1f}%) acima** do calculado. "
                "Verifique o espelho cadastral na Secretaria de Receita de São José."
            )
        elif dif < -1:
            st.info(f"ℹ️ O valor cobrado é {fmt(abs(dif))} abaixo do calculado.")
        else:
            st.success("✅ Valores coincidem.")

# ─────────────────────────────────────────────────────────────
# REFERÊNCIA LEGAL
# ─────────────────────────────────────────────────────────────
with st.expander("📋 Base Legal e Fórmulas"):
    st.markdown(f"""
**Fórmulas — Art. 234 / LC 21/2005:**

| | Fórmula |
|---|---|
| Valor Venal | `Vi = Vt + Vc` |
| Terreno | `Vt = [(Vu × At) × T1 × T2 × T3 × T4] × 1,10` |
| Construção | `Vc = [Ac × Vb × C1 × C2] × 1,18` |
| Componentes | `C2 = Σpontos / 100` |

**Alíquotas — Art. 238:** terreno edificado **1,0%** · construção **0,5%**

**Índice de correção atual:** `{indicador_nome}` — {ind["desc"]}  
**Período:** Jan/{ano_lei+1} → Dez/{ano_exercicio-1} · **Fator:** `{fator:.6f}`  
**Fonte:** {fonte}
    """)
