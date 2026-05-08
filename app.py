from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np

app = Flask(__name__)
CORS(app)

def calcular_distribuicao_benford(df):
    """
    Realiza a limpeza profunda e extração estatística dos dados de Ourinhos.
    """
    # 1. Identificar a coluna de valor (limpando espaços extras nos nomes das colunas)
    df.columns = [str(c).strip() for c in df.columns]
    colunas_foco = ['Valor Total', 'valor', 'Valor', 'VALOR', 'pago', 'empenhado', 'Valor_Total']
    coluna_valor = next((c for c in colunas_foco if c in df.columns), None)

    if not coluna_valor:
        cols_num = df.select_dtypes(include=[np.number]).columns
        if len(cols_num) > 0:
            coluna_valor = cols_num[0]
        else:
            return None, "Não foi possível encontrar uma coluna de valores (ex: Valor Total)."

    # 2. Limpeza Blindada (Transforma texto "R$ 1.250,50" em número 1250.50)
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
        return None, f"Erro na conversão numérica: {str(e)}"

    if valores_vivos.empty:
        return None, "A coluna de valores está vazia ou não contém números válidos."

    # 3. Extração do Primeiro Dígito
    # Removemos zeros à esquerda e pegamos o primeiro número
    primeiros_digitos = (
        valores_vivos.astype(str)
        .str.replace(r'[^0-9]', '', regex=True) # Garante apenas números
        .str.lstrip('0')
        .str[0]
    )
    
    primeiros_digitos = pd.to_numeric(primeiros_digitos, errors='coerce').dropna().astype(int)
    
    # 4. Cálculo das Porcentagens (Frequência Real)
    contagem_real = primeiros_digitos.value_counts(normalize=True).sort_index() * 100
    real_lista = contagem_real.reindex(range(1, 10), fill_value=0).tolist()
    
    # 5. Valores Teóricos da Lei de Benford
    teorica_lista = [np.log10(1 + 1/d) * 100 for d in range(1, 10)]
    
    return {
        "coluna_usada": coluna_valor,
        "labels": list(range(1, 10)),
        "real": real_lista,
        "teorica": teorica_lista,
        "total_valor": float(valores_vivos.sum()),
        "qtd_registros": int(len(valores_vivos))
    }, None

@app.route('/analisar', methods=['POST'])
def analisar():
    if 'file' not in request.files:
        return jsonify({"error": "Arquivo não enviado"}), 400
    
    file = request.files['file']
    
    try:
        # Suporte a CSV e Excel
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file, sep=None, engine='python', on_bad_lines='skip')
        else:
            df = pd.read_excel(file)

        print(f"Arquivo recebido. Colunas: {df.columns.tolist()}")

        resultado, erro = calcular_distribuicao_benford(df)

        if erro:
            return jsonify({"error": erro}), 400

        return jsonify(resultado)

    except Exception as e:
        print(f"Erro no processamento: {str(e)}")
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

if __name__ == '__main__':
    print("--- Servidor de Auditoria de Ourinhos Iniciado ---")
    app.run(debug=True, port=5000)