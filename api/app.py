from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np

app = Flask(__name__)
CORS(app)

#Função para realizar os testes de Z e X²
def calcular_teste_z(po, pe, n):
    """
    Calcula o valor Z para um dígito específico.
    Z = |Po - Pe| / sqrt( (Pe * (1 - Pe)) / n )
    """
    try:
        if n <= 0 or pe >= 1:
            return 0

        # Cálculo estatístico do desvio padrão da proporção
        desvio_padrao = np.sqrt((pe * (1 - pe)) / n)
        z_score = abs(po - pe) / desvio_padrao
        return round(z_score, 4)
    except:
        return 0


def calcular_qui_quadrado(po, pe, n):
    """
    Calcula a parcela do Qui-quadrado para um dígito ou par de dígitos.
    Fórmula: n * ((po - pe)**2 / pe)
    """
    try:
        if pe <= 0:
            return 0
        return n * ((po - pe)**2 / pe)
    except:
        return 0


def calcular_distribuicao_benford(df):
    """
    Processa os dados de Ourinhos: análise de Benford, Função, Sazonalidade e Teste Z.
    """
    # 1. Limpeza de cabeçalhos
    df.columns = [str(c).strip().replace('\ufeff', '') for c in df.columns]

    colunas_valor_alvo = ['Valor Total', 'Valor', 'VALOR', 'valor']
    coluna_valor = next(
        (c for c in colunas_valor_alvo if c in df.columns), None)

    colunas_funcao_alvo = ['Função', 'FUNÇÃO',
                           'funcao', 'Funcao', 'Classificação Funcional']
    coluna_funcao = next(
        (c for c in colunas_funcao_alvo if c in df.columns), None)

    colunas_data_alvo = ['Data de Movimento', 'Data', 'DATA', 'data']
    coluna_data = next((c for c in colunas_data_alvo if c in df.columns), None)

    if not coluna_valor:
        return None, "Não foi possível encontrar a coluna de valores."

    # 2. Limpeza Numérica
    try:
        coluna_limpa = (
            df[coluna_valor].astype(str)
            .str.replace('R$', '', regex=False)
            .str.replace('.', '', regex=False)
            .str.replace(',', '.', regex=False)
            .str.replace('"', '', regex=False)
            .str.strip()
        )
        valores = pd.to_numeric(coluna_limpa, errors='coerce')
        df['valor_limpo'] = valores.abs()
        df_vivos = df[df['valor_limpo'] > 0].dropna(
            subset=['valor_limpo']).copy()
        valores_vivos = df_vivos['valor_limpo']
    except Exception as e:
        return None, f"Erro na conversão numérica: {str(e)}"

    if valores_vivos.empty:
        return None, "Nenhum valor numérico válido."

    # Prepara strings para dígitos
    v_str = valores_vivos.astype(str).str.replace(
        r'[^0-9]', '', regex=True).str.lstrip('0')
    total_n = len(v_str)

    # 3. Análise do Primeiro Dígito + Chamada do Teste Z (Gráfico 1)
    d1_series = pd.to_numeric(v_str.str[0], errors='coerce').dropna()
    contagem_real = d1_series.value_counts()

    real_d1 = []
    valores_z = []  # Lista para armazenar os resultados do teste

    for d in range(1, 10):
        po = contagem_real.get(d, 0) / total_n  # Proporção Observada
        pe = np.log10(1 + 1/d)                 # Proporção Esperada (Benford)

        # --- AQUI CHAMAMOS A SUA FUNÇÃO SEPARADA ---
        z_score = calcular_teste_z(po, pe, total_n)

        real_d1.append(po * 100)
        valores_z.append(z_score)

    teorica_d1 = [np.log10(1 + 1/d) * 100 for d in range(1, 10)]

    # 4. Segundo Dígito
    v_str_2 = v_str[v_str.str.len() >= 2]
    if not v_str_2.empty:
        d2_series = pd.to_numeric(v_str_2.str[1], errors='coerce')
        d2_counts = d2_series.value_counts(normalize=True).sort_index() * 100
        real_d2 = d2_counts.reindex(range(10), fill_value=0).tolist()
    else:
        real_d2 = [0] * 10
    teorica_d2 = [sum(np.log10(1 + 1/(10*d1 + d2))
                      for d1 in range(1, 10)) * 100 for d2 in range(10)]

    # 5. Tabela Conjunta
    tabela_conjunta = []
    for d1 in range(1, 10):
        linha = []
        for d2 in range(10):
            prob_teorica = np.log10(1 + 1 / (10 * d1 + d2))
            contagem_real_c = v_str.str.startswith(f"{d1}{d2}").sum()
            linha.append({
                "teorico": round(prob_teorica, 4),
                "real": round(contagem_real_c / total_n, 4)
            })
        tabela_conjunta.append(linha)

    # 6. Gastos por Função
    gastos_por_funcao = None
    if coluna_funcao:
        top_10 = df_vivos.groupby(coluna_funcao)['valor_limpo'].sum(
        ).sort_values(ascending=False).head(10)
        gastos_por_funcao = {
            "labels": top_10.index.tolist(), "valores": top_10.values.tolist()}

    # 7. Sazonalidade + Período
    gastos_por_mes = None
    periodo_texto = "N/A"
    if coluna_data:
        try:
            df_vivos[coluna_data] = pd.to_datetime(
                df_vivos[coluna_data], dayfirst=True, errors='coerce')
            df_sazon = df_vivos.dropna(subset=[coluna_data])
            if not df_sazon.empty:
                # Período para o Card
                ano_min, ano_max = df_sazon[coluna_data].dt.year.min(
                ), df_sazon[coluna_data].dt.year.max()
                periodo_texto = str(
                    int(ano_min)) if ano_min == ano_max else f"{int(ano_min)} - {int(ano_max)}"

                # Gráfico Sazonal
                sazonalidade = df_sazon.groupby(df_sazon[coluna_data].dt.to_period('M'))[
                    'valor_limpo'].sum().sort_index()
                meses_pt = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
                            7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
                labels_f = [
                    f"{p.year}-{meses_pt[p.month]}" for p in sazonalidade.index]
                gastos_por_mes = {"labels": labels_f,
                                  "valores": sazonalidade.values.tolist()}
        except:
            pass

    # --- BLOCO CORRIGIDO DA TABELA CONJUNTA E QUI-QUADRADO ---
    qui_quadrado_matriz = 0
    tabela_conjunta = []

    for d1 in range(1, 10):
        linha = [] # Inicia a linha para o dígito d1
        for d2 in range(10):
            # Probabilidade Teórica (Pe)
            pe = np.log10(1 + 1 / (10 * d1 + d2))

            # Probabilidade Real (Po)
            comeca_com = f"{d1}{d2}"
            contagem_real_c = v_str.str.startswith(comeca_com).sum()
            po = contagem_real_c / total_n

            # Soma para o Qui-Quadrado Global da Matriz
            qui_quadrado_matriz += calcular_qui_quadrado(po, pe, total_n)

            linha.append({
                "teorico": round(pe, 4),
                "real": round(po, 4)
            })
        # ESTA LINHA ABAIXO DEVE ESTAR ALINHADA COM O 'for d2'
        tabela_conjunta.append(linha) 

    # Agora o return enviará a matriz completa (9x10)
    return {
        "coluna_usada": coluna_valor,
        "total_valor": float(valores_vivos.sum()),
        "qtd_registros": int(total_n),
        "periodo": periodo_texto,
        "labels": list(range(1, 10)),
        "real": real_d1,
        "teorica": teorica_d1,
        "valores_z": valores_z,
        "labels_d2": list(range(10)),
        "real_d2": real_d2,
        "teorica_d2": teorica_d2,
        "tabela_conjunta": tabela_conjunta,
        "gastos_por_funcao": gastos_por_funcao,
        "gastos_por_mes": gastos_por_mes,
        "qui_quadrado_matriz": round(qui_quadrado_matriz, 2)
    }, None


@app.route('/analisar', methods=['POST'])
def analisar():
    if 'file' not in request.files:
        return jsonify({"error": "Arquivo não enviado"}), 400
    file = request.files['file']
    try:
        df = pd.read_csv(file, sep=None, engine='python',
                         encoding='utf-8-sig') if file.filename.endswith('.csv') else pd.read_excel(file)
        resultado, erro = calcular_distribuicao_benford(df)
        return jsonify(resultado) if not erro else (jsonify({"error": erro}), 400)
    except Exception as e:
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500


if __name__ == '__main__':
    print("--- Servidor de Auditoria Ourinhos Ativo ---")
    app.run(debug=True, port=5000)
