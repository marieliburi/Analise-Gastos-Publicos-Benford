from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np

app = Flask(__name__)
CORS(app)

def calcular_distribuicao_benford(df):
    """
    Realiza a limpeza profunda e extração estatística (1º e 2º dígitos) para Ourinhos.
    """
    # 1. Identificar e limpar nomes de colunas
    df.columns = [str(c).strip() for c in df.columns]
    colunas_foco = ['Valor Total', 'valor', 'Valor', 'VALOR', 'pago', 'empenhado', 'Valor_Total']
    coluna_valor = next((c for c in colunas_foco if c in df.columns), None)

    if not coluna_valor:
        cols_num = df.select_dtypes(include=[np.number]).columns
        if len(cols_num) > 0:
            coluna_valor = cols_num[0]
        else:
            return None, "Não foi possível encontrar uma coluna de valores."

    # 2. Limpeza Numérica (Transforma texto em número real)
    try:
        coluna_limpa = (
            df[coluna_valor].astype(str)
            .str.replace('R$', '', regex=False)
            .str.replace('.', '', regex=False)
            .str.replace(',', '.', regex=False)
            .str.strip()
        )
        valores = pd.to_numeric(coluna_limpa, errors='coerce')
        valores_vivos = valores[valores > 0].dropna()
    except Exception as e:
        return None, f"Erro na conversão: {str(e)}"

    if valores_vivos.empty:
        return None, "A coluna não contém números válidos após a limpeza."

    # Prepara os números como strings limpas (sem pontos ou zeros à esquerda)
    v_str = valores_vivos.astype(str).str.replace(r'[^0-9]', '', regex=True).str.lstrip('0')

    # 3. Análise do Primeiro Dígito (Gráfico 1)
    d1_series = v_str.str[0].dropna()
    d1_counts = pd.to_numeric(d1_series, errors='coerce').value_counts(normalize=True).sort_index() * 100
    
    real_d1 = d1_counts.reindex(range(1, 10), fill_value=0).tolist()
    teorica_d1 = [np.log10(1 + 1/d) * 100 for d in range(1, 10)]

    # 4. Análise do Segundo Dígito (Gráfico 2)
    # Pegamos apenas números com pelo menos 2 dígitos
    v_str_2 = v_str[v_str.str.len() >= 2]
    if not v_str_2.empty:
        d2_series = v_str_2.str[1]
        d2_counts = pd.to_numeric(d2_series, errors='coerce').value_counts(normalize=True).sort_index() * 100
        real_d2 = d2_counts.reindex(range(10), fill_value=0).tolist()
    else:
        real_d2 = [0] * 10
        
    teorica_d2 = []
    for d2 in range(10):
        p_d2 = sum(np.log10(1 + 1/(10*d1 + d2)) for d1 in range(1, 10)) * 100
        teorica_d2.append(p_d2)

    # 5. Tabela de Probabilidades Conjuntas (Matriz 9x10)
    tabela_conjunta = []
    for d1 in range(1, 10):
        linha = []
        for d2 in range(10):
            # Teórico
            prob_teorica = np.log10(1 + 1 / (10 * d1 + d2))
            
            # Real nos dados de Ourinhos
            comeca_com = f"{d1}{d2}"
            contagem_real = v_str.str.startswith(comeca_com).sum()
            percentual_real = (contagem_real / len(valores_vivos))
            
            linha.append({
                "teorico": round(prob_teorica, 4),
                "real": round(percentual_real, 4)
            })
        tabela_conjunta.append(linha)

    # UM ÚNICO RETURN com tudo organizado
    return {
        "coluna_usada": coluna_valor,
        "total_valor": float(valores_vivos.sum()),
        "qtd_registros": int(len(valores_vivos)),
        "labels": list(range(1, 10)),
        "real": real_lista if 'real_lista' in locals() else real_d1, # Fallback
        "teorica": teorica_d1,
        "labels_d2": list(range(10)),
        "real_d2": real_d2,
        "teorica_d2": teorica_d2,
        "tabela_conjunta": tabela_conjunta
    }, None

@app.route('/analisar', methods=['POST'])
def analisar():
    if 'file' not in request.files:
        return jsonify({"error": "Arquivo não enviado"}), 400
    
    file = request.files['file']
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file, sep=None, engine='python', on_bad_lines='skip')
        else:
            df = pd.read_excel(file)

        resultado, erro = calcular_distribuicao_benford(df)
        if erro:
            return jsonify({"error": erro}), 400

        return jsonify(resultado)
    except Exception as e:
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

if __name__ == '__main__':
    print("--- Servidor de Auditoria de Ourinhos Iniciado ---")
    app.run(debug=True, port=5000)