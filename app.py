from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np

app = Flask(__name__)
CORS(app)


def calcular_distribuicao_benford(df):
    """
    Processa os dados de Ourinhos: limpa colunas, realiza análise de Benford,
    agrupa gastos por Função e calcula a Sazonalidade Mensal.
    """
    # 1. Limpeza de cabeçalhos (remove espaços e o caractere invisível \ufeff)
    df.columns = [str(c).strip().replace('\ufeff', '') for c in df.columns]

    # Identificar colunas alvo baseadas no seu CSV
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
        return None, "Não foi possível encontrar a coluna de valores (ex: 'Valor Total')."

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

        # Usamos valor absoluto e salvamos no DF original para bater com as datas/funções
        df['valor_limpo'] = valores.abs()
        df_vivos = df[df['valor_limpo'] > 0].dropna(
            subset=['valor_limpo']).copy()
        valores_vivos = df_vivos['valor_limpo']
    except Exception as e:
        return None, f"Erro na conversão numérica: {str(e)}"

    if valores_vivos.empty:
        return None, "Nenhum valor numérico válido encontrado para análise."

    # Prepara strings para análise de Benford
    v_str = valores_vivos.astype(str).str.replace(
        r'[^0-9]', '', regex=True).str.lstrip('0')

    # 3. Análise do Primeiro Dígito (Gráfico 1)
    d1_series = v_str.str[0].dropna()
    d1_counts = pd.to_numeric(d1_series, errors='coerce').value_counts(
        normalize=True).sort_index() * 100
    real_d1 = d1_counts.reindex(range(1, 10), fill_value=0).tolist()
    teorica_d1 = [np.log10(1 + 1/d) * 100 for d in range(1, 10)]

    # 4. Análise do Segundo Dígito (Gráfico 2)
    v_str_2 = v_str[v_str.str.len() >= 2]
    if not v_str_2.empty:
        d2_series = v_str_2.str[1]
        d2_counts = pd.to_numeric(d2_series, errors='coerce').value_counts(
            normalize=True).sort_index() * 100
        real_d2 = d2_counts.reindex(range(10), fill_value=0).tolist()
    else:
        real_d2 = [0] * 10

    teorica_d2 = [sum(np.log10(1 + 1/(10*d1 + d2))
                      for d1 in range(1, 10)) * 100 for d2 in range(10)]

    # 5. Tabela de Probabilidades Conjuntas (Matriz 9x10)
    tabela_conjunta = []
    for d1 in range(1, 10):
        linha = []
        for d2 in range(10):
            prob_teorica = np.log10(1 + 1 / (10 * d1 + d2))
            comeca_com = f"{d1}{d2}"
            contagem_real = v_str.str.startswith(comeca_com).sum()
            percentual_real = (contagem_real / len(valores_vivos))
            linha.append({
                "teorico": round(prob_teorica, 4),
                "real": round(percentual_real, 4)
            })
        tabela_conjunta.append(linha)

    # 6. Gastos por Função (Gráfico 3)
    gastos_por_funcao = None
    if coluna_funcao:
        agrupado = df_vivos.groupby(coluna_funcao)[
            'valor_limpo'].sum().sort_values(ascending=False)
        top_10 = agrupado.head(10)
        gastos_por_funcao = {
            "labels": top_10.index.tolist(),
            "valores": top_10.values.tolist()
        }

    # 7. Sazonalidade (Gráfico 4)
    gastos_por_mes = None
    if coluna_data:
        try:
            df_vivos[coluna_data] = pd.to_datetime(
                df_vivos[coluna_data], dayfirst=True, errors='coerce')
            df_sazon = df_vivos.dropna(subset=[coluna_data])

            # Agrupamos primeiro por uma chave que mantém a ordem cronológica (YYYY-MM)
            # Mas exibimos no formato (YYYY-AbbreviatedMonth)
            sazonalidade = df_sazon.groupby(df_sazon[coluna_data].dt.to_period('M'))[
                'valor_limpo'].sum().sort_index()

            if not sazonalidade.empty:
                # Mapeamento para meses em português (opcional, mas recomendado)
                meses_pt = {
                    1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
                    7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
                }

                labels_formatados = [
                    f"{p.year}-{meses_pt[p.month]}" for p in sazonalidade.index]

                gastos_por_mes = {
                    "labels": labels_formatados,
                    "valores": sazonalidade.values.tolist()
                }
        except Exception as e:
            print(f"Erro na sazonalidade: {e}")

    periodo_texto = "N/A"
    # Garantimos que df_sazon existe antes de verificar se está vazia
    if coluna_data and 'df_sazon' in locals() and not df_sazon.empty:
        try:
            ano_min = df_sazon[coluna_data].dt.year.min()
            ano_max = df_sazon[coluna_data].dt.year.max()
            
            if ano_min == ano_max:
                periodo_texto = str(int(ano_min))
            else:
                periodo_texto = f"{int(ano_min)} - {int(ano_max)}"
        except:
            periodo_texto = "Erro na data"

    # Retorno limpo e sem chaves duplicadas
    return {
        "coluna_usada": coluna_valor,
        "total_valor": float(valores_vivos.sum()),
        "qtd_registros": int(len(valores_vivos)),
        "periodo": periodo_texto, # <--- Esta é a chave!
        "labels": list(range(1, 10)),
        "real": real_d1,
        "teorica": teorica_d1,
        "labels_d2": list(range(10)),
        "real_d2": real_d2,
        "teorica_d2": teorica_d2,
        "tabela_conjunta": tabela_conjunta,
        "gastos_por_funcao": gastos_por_funcao,
        "gastos_por_mes": gastos_por_mes
    }, None

@app.route('/analisar', methods=['POST'])
def analisar():
    if 'file' not in request.files:
        return jsonify({"error": "Arquivo não enviado"}), 400

    file = request.files['file']
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file, sep=None, engine='python',
                             encoding='utf-8-sig', on_bad_lines='skip')
        else:
            df = pd.read_excel(file)

        resultado, erro = calcular_distribuicao_benford(df)
        if erro:
            return jsonify({"error": erro}), 400

        return jsonify(resultado)
    except Exception as e:
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500


if __name__ == '__main__':
    print("--- Servidor de Auditoria Ourinhos Ativo ---")
    app.run(debug=True, port=5000)
