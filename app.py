from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np

app = Flask(__name__)
CORS(app)

# --- FUNÇÕES ESTATÍSTICAS ORIGINAIS ---
def calcular_teste_z(po, pe, n):
    try:
        if n <= 0 or pe >= 1:
            return 0
        desvio_padrao = np.sqrt((pe * (1 - pe)) / n)
        z_score = abs(po - pe) / desvio_padrao
        return round(z_score, 4)
    except:
        return 0

def calcular_qui_quadrado(po, pe, n):
    try:
        if pe <= 0:
            return 0
        return n * ((po - pe)**2 / pe)
    except:
        return 0

def calcular_distribuicao_benford(df):
    # 1. Limpeza de cabeçalhos e REMOÇÃO DE DUPLICATAS para bater com o LibreOffice
    df.columns = [str(c).strip().replace('\ufeff', '') for c in df.columns]
    df = df.drop_duplicates()

    colunas_valor_alvo = ['Valor Total', 'Valor', 'VALOR', 'valor']
    coluna_valor = next((c for c in colunas_valor_alvo if c in df.columns), None)

    colunas_funcao_alvo = ['Função', 'FUNÇÃO', 'funcao', 'Funcao', 'Classificação Funcional']
    coluna_funcao = next((c for c in colunas_funcao_alvo if c in df.columns), None)

    colunas_data_alvo = ['Data de Movimento', 'Data', 'DATA', 'data']
    coluna_data = next((c for c in colunas_data_alvo if c in df.columns), None)

    if not coluna_valor:
        return None, "Não foi possível encontrar a coluna de valores."

    # 2. LIMPEZA NUMÉRICA CORRIGIDA (Evita o erro dos 250 milhões)
    def converter_valor_br(v):
        try:
            v = str(v).replace('R$', '').strip()
            if '.' in v and ',' in v: # Formato 1.234,56
                v = v.replace('.', '').replace(',', '.')
            elif ',' in v: # Formato 1234,56
                v = v.replace(',', '.')
            return float(v)
        except:
            return np.nan

    df['valor_limpo'] = df[coluna_valor].apply(converter_valor_br).abs()
    df_vivos = df[df['valor_limpo'] > 0].dropna(subset=['valor_limpo']).copy()
    
    if df_vivos.empty:
        return None, "Nenhum valor numérico válido."

    # Prepara strings para dígitos (Remove pontos decimais para análise de Benford)
    v_str = df_vivos['valor_limpo'].astype(str).str.replace('.', '', regex=False).str.lstrip('0')
    total_n = len(v_str)

    # 3. Análise do Primeiro Dígito + Teste Z (Mantendo sua lógica original)
    d1_series = pd.to_numeric(v_str.str[0], errors='coerce').dropna()
    contagem_real = d1_series.value_counts()

    real_d1, valores_z, teorica_d1 = [], [], []
    for d in range(1, 10):
        po = contagem_real.get(d, 0) / total_n
        pe = np.log10(1 + 1/d)
        real_d1.append(po * 100)
        teorica_d1.append(pe * 100)
        valores_z.append(calcular_teste_z(po, pe, total_n))

    # 4. Segundo Dígito (REINSTALADO)
    v_str_2 = v_str[v_str.str.len() >= 2]
    if not v_str_2.empty:
        d2_series = pd.to_numeric(v_str_2.str[1], errors='coerce')
        d2_counts = d2_series.value_counts(normalize=True).sort_index() * 100
        real_d2 = d2_counts.reindex(range(10), fill_value=0).tolist()
    else:
        real_d2 = [0] * 10
    teorica_d2 = [sum(np.log10(1 + 1/(10*d1 + d2)) for d1 in range(1, 10)) * 100 for d2 in range(10)]

    # 5. Tabela Conjunta e Qui-Quadrado (OTIMIZADO para não travar)
    primeiros_dois = v_str.str[:2]
    contagens_conjuntas = primeiros_dois.value_counts()
    qui_quadrado_matriz = 0
    tabela_conjunta = []

    for d1 in range(1, 10):
        linha = []
        for d2 in range(10):
            pe = np.log10(1 + 1 / (10 * d1 + d2))
            chave = f"{d1}{d2}"
            po = contagens_conjuntas.get(chave, 0) / total_n
            qui_quadrado_matriz += calcular_qui_quadrado(po, pe, total_n)
            linha.append({"teorico": round(pe, 4), "real": round(po, 4)})
        tabela_conjunta.append(linha)

    # 6. Gastos por Função
    gastos_por_funcao = None
    if coluna_funcao:
        top_10 = df_vivos.groupby(coluna_funcao)['valor_limpo'].sum().sort_values(ascending=False).head(10)
        gastos_por_funcao = {"labels": top_10.index.tolist(), "valores": top_10.values.tolist()}

    # 7. Sazonalidade (Ajustado para o padrão MM-DD-YY do seu CSV)
    gastos_por_mes = None
    periodo_texto = "N/A"
    if coluna_data:
        try:
            # Removi o dayfirst e adicionei o formato específico do seu arquivo
            df_vivos[coluna_data] = pd.to_datetime(df_vivos[coluna_data], format='%m-%d-%y', errors='coerce')
            
            df_sazon = df_vivos.dropna(subset=[coluna_data])
            if not df_sazon.empty:
                # Agrupamento mensal
                sazonalidade = df_sazon.groupby(df_sazon[coluna_data].dt.to_period('M'))['valor_limpo'].sum().sort_index()
                
                meses_pt = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun', 
                            7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
                
                labels_f = [f"{p.year}-{meses_pt[p.month]}" for p in sazonalidade.index]
                gastos_por_mes = {"labels": labels_f, "valores": sazonalidade.values.tolist()}
                
                # Texto do período
                ano_min, ano_max = df_sazon[coluna_data].dt.year.min(), df_sazon[coluna_data].dt.year.max()
                periodo_texto = str(int(ano_min)) if ano_min == ano_max else f"{int(ano_min)} - {int(ano_max)}"
        except Exception as e:
            print(f"Erro na data: {e}") # Útil para log no Flask
            pass
    
    # 8. Detalhamento de Janeiro (Gráfico de Pizza)
    gastos_janeiro_funcao = None
    if coluna_data and coluna_funcao:
        try:
            # Filtra apenas o mês 1 (Janeiro) de todos os anos presentes
            df_jan = df_vivos[df_vivos[coluna_data].dt.month == 1]
            if not df_jan.empty:
                jan_resumo = df_jan.groupby(coluna_funcao)['valor_limpo'].sum().sort_values(ascending=False)
                gastos_janeiro_funcao = {
                    "labels": jan_resumo.index.tolist(),
                    "valores": jan_resumo.values.tolist()
                }
        except:
            pass

    return {
        "coluna_usada": coluna_valor,
        "total_valor": float(df_vivos['valor_limpo'].sum()),
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
        "gastos_janeiro_funcao": gastos_janeiro_funcao,
        "qui_quadrado_matriz": round(qui_quadrado_matriz, 2),
        
    }, None

@app.route('/analisar', methods=['POST'])
def analisar():
    if 'file' not in request.files:
        return jsonify({"error": "Arquivo não enviado"}), 400
    file = request.files['file']
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file, sep=None, engine='python', encoding='utf-8-sig')
        else:
            df = pd.read_excel(file)
        
        resultado, erro = calcular_distribuicao_benford(df)
        return jsonify(resultado) if not erro else (jsonify({"error": erro}), 400)
    except Exception as e:
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

if __name__ == '__main__':
    print("--- Servidor de Auditoria Ativo na Porta 5000 ---")
    app.run(debug=True, port=5000)