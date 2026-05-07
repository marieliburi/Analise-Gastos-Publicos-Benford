from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np
import io

app = Flask(__name__)
# O CORS é essencial para que seu HTML (Live Server) consiga acessar o Python
CORS(app)

def calcular_distribuicao_benford(df):
    """
    Realiza a limpeza e extração estatística dos dados.
    """
    # 1. Tenta encontrar a coluna especificada ou similares
    colunas_foco = ['Valor Total', 'valor', 'Valor', 'VALOR', 'pago', 'empenhado']
    coluna_valor = next((c for c in colunas_foco if c in df.columns), None)

    # Se não achar pelos nomes, pega a primeira coluna numérica
    if not coluna_valor:
        colunas_numericas = df.select_dtypes(include=[np.number]).columns
        if len(colunas_numericas) > 0:
            coluna_valor = colunas_numericas[0]
        else:
            return None, "Não foi possível encontrar uma coluna de valores numéricos."

    # 2. Filtragem: Apenas valores positivos e maiores que zero
    # (Essencial para a integridade da Lei de Benford)
    valores_limpos = df[coluna_valor][df[coluna_valor] > 0].dropna()

    if valores_limpos.empty:
        return None, "A coluna de valores está vazia ou contém apenas números negativos/zero."

    # 3. Extração do Primeiro Dígito
    # Removemos pontos e vírgulas, limpamos zeros à esquerda e pegamos o 1º caractere
    primeiros_digitos = (
        valores_limpos.astype(str)
        .str.replace(r'[\.,]', '', regex=True)
        .str.lstrip('0')
        .str[0]
    )
    
    # Converte para número e remove erros
    primeiros_digitos = pd.to_numeric(primeiros_digitos, errors='coerce').dropna().astype(int)
    
    # 4. Cálculo das Porcentagens (Frequência Relativa)
    # Contamos as ocorrências e multiplicamos por 100 para ter a porcentagem
    contagem_real = primeiros_digitos.value_counts(normalize=True).sort_index() * 100
    
    # Criamos a lista final de 1 a 9, preenchendo com 0% onde não houver dados
    real_lista = contagem_real.reindex(range(1, 10), fill_value=0).tolist()
    
    # 5. Valores Teóricos de Benford para comparação no gráfico
    teorica_lista = [np.log10(1 + 1/d) * 100 for d in range(1, 10)]
    
    return {
        "coluna_usada": coluna_valor,
        "labels": list(range(1, 10)),
        "real": real_lista,
        "teorica": teorica_lista,
        "total_valor": float(valores_limpos.sum()),
        "qtd_registros": len(valores_limpos)
    }, None

@app.route('/analisar', methods=['POST'])
def analisar():
    if 'file' not in request.files:
        return jsonify({"error": "Arquivo não enviado"}), 400
    
    file = request.files['file']
    
    try:
        if file.filename.endswith('.csv'):
            # O segredo: sep=None faz o pandas descobrir se é vírgula ou ponto e vírgula sozinho
            # on_bad_lines='skip' ignora linhas com erro (como rodapés de sites)
            df = pd.read_csv(file, sep=None, engine='python', on_bad_lines='skip')
        else:
            df = pd.read_excel(file)

        # Log para você ver no terminal se ele leu as colunas certo
        print("Colunas encontradas:", df.columns.tolist())

        resultado, erro = calcular_distribuicao_benford(df)

    except Exception as e:
        return jsonify({"error": f"Erro ao processar: {str(e)}"}), 500

if __name__ == '__main__':
    # Roda o servidor localmente na porta 5000
    print("Servidor de Auditoria de Ourinhos iniciado!")
    app.run(debug=True, port=5000)