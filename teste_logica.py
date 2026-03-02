import pandas as pd
import io

# Dados baseados no seu exemplo real para validação
dados_exemplo = """Relatorio-Dados
CP+CA+Numero;Nome;Data;Valor Consumo;Unidade Consumo;Grupo de classificacao;Oferta e pacote usado
+5554994937504;MARIA APARECIDA;2026-02-27;2.19;MB;WhatsApp;Pacote Mensageria;
+5554994937504;MARIA APARECIDA;2026-02-27;930.37;MB;Web;Claro Total Compartilhado 1TB;
+5555991072016;LUCIR NASCIMENTO;2026-02-27;47.00;KB;WhatsApp;Pacote Mensageria;
+5555991072016;LUCIR NASCIMENTO;2026-02-27;1.18;MB;Web;Claro Total Compartilhado 1TB;
+5555991073681;JOCELI NARDES;2026-02-27;161.51;MB;Web;Claro Total Compartilhado 1TB;
+5555991073819;JOCELI NARDES;2026-02-27;842.94;MB;Web;Claro Total Compartilhado 1TB;"""

def executar_teste():
    print("--- INICIANDO TESTE DE LOGICA ---")
    
    # Simula a leitura do CSV ignorando a primeira linha
    df = pd.read_csv(io.StringIO(dados_exemplo), sep=";", skiprows=1, engine="python")
    
    # Limpa colunas extras e espaços
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    df.columns = [col.strip() for col in df.columns]
    
    # Regra 1: Manter apenas "Web"
    antes = len(df)
    df = df[df["Grupo de classificacao"].str.strip().str.upper() == "WEB"]
    depois = len(df)
    print(f"Registros filtrados (Apenas Web): {depois} de {antes}")

    # Regra 2: Conversão de unidades
    def converter(valor, unidade):
        v = float(str(valor).replace(',', '.'))
        u = str(unidade).upper()
        if "GB" in u: return v * 1024
        if "KB" in u: return v / 1024
        return v

    df["consumo_mb"] = df.apply(lambda r: converter(r["Valor Consumo"], r["Unidade Consumo"]), axis=1)

    # Regra 3: Agrupamento por número e nome
    resumo = df.groupby(["CP+CA+Numero", "Nome"])["consumo_mb"].sum().reset_index()
    
    print("\n--- RESULTADO DO PROCESSAMENTO ---")
    print(resumo)
    
    # Validação do Joceli Nardes (Soma de duas linhas Web)
    joceli = resumo[resumo["Nome"].str.contains("JOCELI")]
    valor_esperado = 161.51 + 842.94
    
    if not joceli.empty and round(joceli.iloc[0]["consumo_mb"], 2) == round(valor_esperado, 2):
        print("\n✅ SUCESSO: Soma do consumo agrupado correta!")
    else:
        print("\n❌ ERRO: Falha na soma ou agrupamento.")

if __name__ == "__main__":
    executar_teste()
