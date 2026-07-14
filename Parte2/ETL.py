import pymongo
from pymongo import UpdateOne
import re
import csv
from io import StringIO

# 1. CONFIGURAÇÃO DA CONEXÃO
URI_CONEXAO = "mongodb+srv://dobaguiop_db_user:7EFjBPiiQhQOJwBF@dadosbd.342z1yl.mongodb.net/?appName=DadosBD"
client = pymongo.MongoClient(URI_CONEXAO)
db = client['trabalho_pratico']

# FUNÇÕES DE TRANSFORMAÇÃO 

def extrair_valores_sql(linha):
    """Lê uma linha de INSERT do SQL e extrai os valores como uma lista do Python."""
    match = re.search(r"VALUES\s*\((.*)\);", linha, re.IGNORECASE)
    if not match:
        return None
    
    raw_vals = match.group(1)
    reader = csv.reader(StringIO(raw_vals), quotechar="'", skipinitialspace=True)
    for row in reader:
        return [None if v.strip() == 'NULL' else v.strip() for v in row]

def limpar_vetor_pg(array_str):
    """Transforma o texto de array do PostgreSQL '{"email1", "email2"}' em uma lista Python ['email1', 'email2']"""
    if not array_str or array_str == 'None': return []
    limpo = array_str.strip('{}')
    if not limpo: return []
    return [x.strip('"') for x in limpo.split(',')]

# EXTRAÇÃO: LENDO O ARQUIVO SQL
print("Lendo o arquivo dump.sql...")

usuarios_memoria = {}
departamentos_memoria = []
professores_memoria = []
estudantes_memoria = {}
vinculos_memoria = []

try:
    with open('dump.sql', 'r', encoding='utf-8') as file:
        conteudo = file.read()

    statements = conteudo.split(';')

    for statement in statements:
        linha = ' '.join(statement.split()).strip()
        if not linha:
            continue
        linha = linha + ';' 

        if linha.startswith("INSERT INTO universidade.usuario"):
            vals = extrair_valores_sql(linha)
            if vals:
                cpf = vals[0]
                usuarios_memoria[cpf] = {
                    "cpf": cpf,
                    "nome": vals[1],
                    "data_nascimento": vals[2],
                    "email": limpar_vetor_pg(vals[3]),
                    "telefone": limpar_vetor_pg(vals[4]),
                    "login": vals[5],
                    "senha": vals[6]
                }

        elif linha.startswith("INSERT INTO universidade.departamento"):
            vals = extrair_valores_sql(linha)
            if vals:
                departamentos_memoria.append({
                    "cod_depto": vals[0],
                    "nome": vals[1],
                    "orcamento": float(vals[3]) if vals[3] else None,
                    "comissal": float(vals[4]) if vals[4] else None
                })

        elif linha.startswith("INSERT INTO universidade.professor"):
            vals = extrair_valores_sql(linha)
            if vals:
                professores_memoria.append({
                    "mat_professor": vals[0],
                    "cpf_ref": vals[1],
                    "cod_depto": vals[2],
                    "formacao": vals[3],
                    "data_admissao": vals[4],
                    "tipo_jornada_trabalho": vals[5],
                    "salario": float(vals[6]) if vals[6] else None
                })

        elif linha.startswith("INSERT INTO universidade.estudante"):
            vals = extrair_valores_sql(linha)
            if vals:
                mat = vals[0]
                estudantes_memoria[mat] = {
                    "mat_estudante": mat,
                    "cpf_ref": vals[1],
                    "MC": float(vals[2]) if vals[2] else None,
                    "ano_ingresso": int(vals[3]) if vals[3] else None,
                    "vinculos": []
                }

        elif linha.startswith("INSERT INTO universidade.vinculo"):
            vals = extrair_valores_sql(linha)
            if vals:
                vinculos_memoria.append({
                    "mat_estudante": vals[1],
                    "idCurso": int(vals[2]) if vals[2] else None,
                    "data_entrada": vals[3],
                    "status": vals[4],
                    "data_saida": vals[5]
                })
except FileNotFoundError:
    print("ERRO: O arquivo 'dump.sql' não foi encontrado na mesma pasta do script.")
    exit()

print("Montando os documentos NoSQL na memória (Embedding)...")

documentos_professores = []
for prof in professores_memoria:
    cpf = prof.pop("cpf_ref")
    if cpf in usuarios_memoria:
        prof["usuario"] = usuarios_memoria[cpf]
        documentos_professores.append(prof)
    else:
        print(f"AVISO: usuário com CPF '{cpf}' não encontrado para o professor "
              f"'{prof.get('mat_professor')}'. Este professor será IGNORADO nesta carga "
              f"(o schema exige o campo 'usuario').")

for vinc in vinculos_memoria:
    mat = vinc.pop("mat_estudante") 
    if mat in estudantes_memoria:
        estudantes_memoria[mat]["vinculos"].append(vinc) 

documentos_estudantes = []
for mat, est in estudantes_memoria.items():
    cpf = est.pop("cpf_ref")
    if cpf in usuarios_memoria:
        est["usuario"] = usuarios_memoria[cpf]
        documentos_estudantes.append(est)
    else:
        print(f"AVISO: usuário com CPF '{cpf}' não encontrado para o estudante "
              f"'{mat}'. Este estudante será IGNORADO nesta carga "
              f"(o schema exige o campo 'usuario').")

# CARGA: ENVIANDO TUDO PARA O MONGODB

print("Atualizando dados existentes e inserindo novos (Upsert)...")


if departamentos_memoria:
    operacoes_depto = [UpdateOne({"cod_depto": d["cod_depto"]}, {"$set": d}, upsert=True) for d in departamentos_memoria]
    db.departamento.bulk_write(operacoes_depto)
    print(f"[{len(departamentos_memoria)}] Departamentos processados (Upsert)!")

if documentos_professores:
    operacoes_prof = [UpdateOne({"mat_professor": p["mat_professor"]}, {"$set": p}, upsert=True) for p in documentos_professores]
    db.professor.bulk_write(operacoes_prof)
    print(f"[{len(documentos_professores)}] Professores processados (Upsert)!")

if documentos_estudantes:
    operacoes_est = [UpdateOne({"mat_estudante": e["mat_estudante"]}, {"$set": e}, upsert=True) for e in documentos_estudantes]
    db.estudante.bulk_write(operacoes_est)
    print(f"[{len(documentos_estudantes)}] Estudantes processados (Upsert)!")

print("\n--- MIGRAÇÃO CONCLUÍDA COM SUCESSO E SEM DUPLICATAS! ---")