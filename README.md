# 🏠 Calculadora IPTU — São José / SC

Uma ferramenta interativa desenvolvida em **Streamlit** para simulação e conferência do cálculo de IPTU no município de São José/SC. O aplicativo realiza a recomposição de valores venais históricos com base nas legislações vigentes e faz a atualização monetária em tempo real.

## 📋 Funcionalidades

* **Legislação Municipal Integrada:** Aplicação direta das fórmulas e tabelas de pontuação da **Lei Complementar nº 21/2005** (Código Tributário Municipal) e da **Lei nº 3.440/1999** (Planta Genérica de Valores).
* **Correção Monetária Real-Time:** Integração direta com a **API do Banco Central do Brasil (SGS)** para obtenção automatizada de índices acumulados (`IPCA`, `INPC`, `IGP-M`, `IGP-DI`, `IPC-FIPE`, `IPCA-15`).
* **Mecanismo de Fallback:** Caso a API do Banco Central esteja indisponível, o sistema conta com uma matriz histórica embutida de taxas anuais do IPCA para garantir a continuidade dos cálculos.
* **Cálculo Multi-Unidade:** Suporte para o cálculo concomitante de até 8 unidades autônomas (ex: Apartamento + Vagas de Garagem) gerando um **Resultado Consolidado**.
* **Auditoria Contábil:** Campo para inserção do valor real do carnê cobrado, gerando análise de divergência absoluta e percentual para identificar possíveis inconsistências tributárias.

---

## 🛠️ Estrutura do Cálculo Realizado

O aplicativo replica fielmente as etapas administrativas de lançamento fiscal de São José:

1.  **Valor do Terreno ($Vt$):** $$Vt = [(Vu \times At) \times T1 \times T2 \times T3 \times T4] \times 1.10$$
    *(Onde T1 a T4 representam os fatores de Situação, Aproveitamento, Topografia e Pedologia).*
2.  **Valor da Construção ($Vc$):** $$Vc = [Ac \times Vb \times C1 \times C2] \times 1.18$$
    *(Onde C1 é a depreciação por idade e C2 é a somatória de pontos das características estruturais divided por 100).*
3.  **Valor Venal Total ($Vi$):** $$Vi = Vt + Vc$$
4.  **Alíquotas Aplicadas (Art. 238):**
    * Imposto Territorial: **1,0%** sobre o $Vt$
    * Imposto Predial: **0,5%** sobre o $Vc$

---

## 🚀 Tecnologias Utilizadas

* [Python 3.x](https://www.python.org/)
* [Streamlit](https://streamlit.io/) — Interface de usuário de alto desempenho
* [Pandas](https://pandas.pydata.org/) — Manipulação e agregação de séries temporais
* [Requests](https://requests.readthedocs.io/) — Consumo da API REST SGS/BCB

---

## ⚙️ Instalação e Execução

### 1. Clonar o Repositório
```bash
git clone [https://github.com/seu-usuario/calculadora-iptu-sao-jose.git](https://github.com/seu-usuario/calculadora-iptu-sao-jose.git)
cd calculadora-iptu-sao-jose
