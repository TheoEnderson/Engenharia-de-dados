import pymongo
from pymongo.errors import CollectionInvalid, WriteError

URI_CONEXAO = "mongodb+srv://dobaguiop_db_user:7EFjBPiiQhQOJwBF@dadosbd.342z1yl.mongodb.net/?appName=DadosBD"

print("Conectando ao MongoDB...")
client = pymongo.MongoClient(URI_CONEXAO)
db = client['trabalho_pratico']

# VALIDAÇÃO 1: DEPARTAMENTO
validador_departamento = {
    "$jsonSchema": {
        "bsonType": "object",
        "additionalProperties": False,
        "required": ["cod_depto", "nome"],
        "properties": {
            "_id": {"bsonType": "objectId"},
            "cod_depto": {"bsonType": "string"},
            "nome": {"bsonType": "string"},
            "orcamento": {"bsonType": ["double", "int"]},
            "comissal": {"bsonType": ["double", "int"]}
        }
    }
}

# VALIDAÇÃO 2: PROFESSOR 
validador_professor = {
    "$jsonSchema": {
        "bsonType": "object",
        "additionalProperties": False,
        "required": ["mat_professor", "cod_depto", "usuario"],
        "properties": {
            "_id": {"bsonType": "objectId"},
            "mat_professor": {"bsonType": "string"},
            "cod_depto": {"bsonType": "string", "description": "REFERENCING: Aponta para o Departamento"},
            "formacao": {"enum": ["Graduação", "Especialização", "Mestrado", "Doutorado"]},
            "data_admissao": {"bsonType": ["string", "null"]},
            "tipo_jornada_trabalho": {"enum": ["20h", "40h", "DE"]},
            "salario": {"bsonType": ["double", "int"]},
            
            "usuario": {
                "bsonType": "object",
                "additionalProperties": False,
                "required": ["cpf", "nome", "login", "senha"],
                "properties": {
                    "cpf": {"bsonType": "string"},
                    "nome": {"bsonType": "string"},
                    "data_nascimento": {"bsonType": "string"},
                    "email": {"bsonType": "array", "items": {"bsonType": "string"}},
                    "telefone": {"bsonType": "array", "items": {"bsonType": "string"}},
                    "login": {"bsonType": "string"},
                    "senha": {"bsonType": "string"}
                }
            }
        }
    }
}

# VALIDAÇÃO 3: ESTUDANTE
validador_estudante = {
    "$jsonSchema": {
        "bsonType": "object",
        "additionalProperties": False,
        "required": ["mat_estudante", "usuario"],
        "properties": {
            "_id": {"bsonType": "objectId"},
            "mat_estudante": {"bsonType": "string"},
            "MC": {"bsonType": ["double", "int"]},
            "ano_ingresso": {"bsonType": ["int", "null"]},
            
            "usuario": {
                "bsonType": "object",
                "additionalProperties": False,
                "required": ["cpf", "nome"],
                "properties": {
                    "cpf": {"bsonType": "string"},
                    "nome": {"bsonType": "string"},
                    "data_nascimento": {"bsonType": ["string","null"]},
                    "email": {"bsonType": "array", "items": {"bsonType": "string"}},
                    "telefone": {"bsonType": "array", "items": {"bsonType": "string"}},
                    "login": {"bsonType": "string"},
                    "senha": {"bsonType": "string"}
                }
            },
            
            "vinculos": {
                "bsonType": "array",
                "items": {
                    "bsonType": "object",
                    "properties": {
                        "idCurso": {"bsonType": "int", "description": "REFERENCING: Aponta para o Curso"},
                        "status": {"enum": ["Ativo", "Cancelada", "Formando", "Graduado"]},
                        "data_entrada": {"bsonType": ["string", "null"]},
                        "data_saida": {"bsonType": ["string", "null"]}
                    }
                }
            }
        }
    }
}

# APLICANDO AS VALIDAÇÕES NO BANCO

colecoes = {
    "departamento": validador_departamento,
    "professor": validador_professor,
    "estudante": validador_estudante
}

print("\n--- Criando Coleções e Aplicando Regras ---")
for nome, validador in colecoes.items():
    try:
        db.create_collection(nome, validator=validador)
        print(f"[OK] Coleção '{nome}' criada com sucesso!")
    except CollectionInvalid:
        # Se a gente rodar o script duas vezes, ele avisa que já existe
        db.command("collMod", nome, validator=validador)
        print(f"[OK] Coleção '{nome}' atualizada com as regras!")


def remover_duplicatas(colecao, campo_chave):
    """Remove documentos duplicados de 'colecao', mantendo apenas um por valor de 'campo_chave'."""
    pipeline = [
        {"$group": {
            "_id": f"${campo_chave}",
            "ids": {"$push": "$_id"},
            "total": {"$sum": 1}
        }},
        {"$match": {"total": {"$gt": 1}}}
    ]

    grupos_duplicados = list(colecao.aggregate(pipeline))
    if not grupos_duplicados:
        return 0

    total_removidos = 0
    for grupo in grupos_duplicados:
        ids = grupo["ids"]
        manter = ids[-1]       
        remover = ids[:-1]     
        resultado = colecao.delete_many({"_id": {"$in": remover}})
        total_removidos += resultado.deleted_count
        print(f"  - Valor '{grupo['_id']}': mantido 1 documento, removidos {resultado.deleted_count} duplicado(s)")

    return total_removidos

print("\n--- Verificando e Removendo Duplicatas ---")
print("Coleção 'departamento' (chave: cod_depto):")
removidos_depto = remover_duplicatas(db.departamento, "cod_depto")
print(f"  Total removido: {removidos_depto}" if removidos_depto else "  Nenhuma duplicata encontrada.")

print("Coleção 'professor' (chave: mat_professor):")
removidos_prof = remover_duplicatas(db.professor, "mat_professor")
print(f"  Total removido: {removidos_prof}" if removidos_prof else "  Nenhuma duplicata encontrada.")

print("Coleção 'estudante' (chave: mat_estudante):")
removidos_est = remover_duplicatas(db.estudante, "mat_estudante")
print(f"  Total removido: {removidos_est}" if removidos_est else "  Nenhuma duplicata encontrada.")

print("Coleção 'professor' (chave: usuario.cpf):")
removidos_prof_cpf = remover_duplicatas(db.professor, "usuario.cpf")
print(f"  Total removido: {removidos_prof_cpf}" if removidos_prof_cpf else "  Nenhuma duplicata encontrada.")

print("Coleção 'estudante' (chave: usuario.cpf):")
removidos_est_cpf = remover_duplicatas(db.estudante, "usuario.cpf")
print(f"  Total removido: {removidos_est_cpf}" if removidos_est_cpf else "  Nenhuma duplicata encontrada.")


# ÍNDICES ÚNICOS

print("\n--- Criando Índices Únicos ---")
db.departamento.create_index("cod_depto", unique=True)
db.professor.create_index("mat_professor", unique=True)
db.estudante.create_index("mat_estudante", unique=True)
db.professor.create_index("usuario.cpf", unique=True)
db.estudante.create_index("usuario.cpf", unique=True)
print("[OK] Índices únicos criados/confirmados em cod_depto, mat_professor, mat_estudante e usuario.cpf!")

# INSERINDO OS DADOS DO DUMP SQL

print("\n--- Inserindo Dados de Exemplo (Upsert) ---")
print("Observação: esses são dados de exemplo/smoke test. Os dados reais da")
print("universidade são carregados pelo ETL.py a partir do dump.sql.")

try:
    db.departamento.update_one(
        {"cod_depto": "DCOMP"},
        {"$set": {
            "cod_depto": "DCOMP",
            "nome": "Departamento de Computação",
            "orcamento": 10000.0,
            "comissal": 1000.0
        }},
        upsert=True
    )
    print("Departamento DCOMP inserido/atualizado!")

    db.professor.update_one(
        {"mat_professor": "P100"},
        {"$set": {
            "mat_professor": "P100",
            "cod_depto": "DCOMP", 
            "formacao": "Doutorado",
            "tipo_jornada_trabalho": "20h",
            "salario": 2000.0,
            "usuario": { 
                "cpf": "11111111100",
                "nome": "Prof A",
                "data_nascimento": "1980/03/05",
                "email": ["profA@email.com"],
                "telefone": ["99998888", "88889999"],
                "login": "profa",
                "senha": "senha1"
            }
        }},
        upsert=True
    )
    print("Professor P100 (Prof A) inserido/atualizado com sucesso!")

    db.estudante.update_one(
        {"mat_estudante": "E101"},
        {"$set": {
            "mat_estudante": "E101",
            "MC": 7.0,
            "ano_ingresso": 2021,
            "usuario": {         
                "cpf": "22222222201",
                "nome": "Steve Jobs",
                "data_nascimento": "1990/03/05",
                "email": ["steve@email.com", "steve@apple.com"],
                "login": "steve",
                "senha": "s1"
            },
            "vinculos": [        
                {
                    "idCurso": 3, 
                    "status": "Ativo"
                }
            ]
        }},
        upsert=True
    )
    print("Estudante E101 (Steve Jobs) inserido/atualizado com sucesso!")

except WriteError as e:
    print(f"ERRO DE VALIDAÇÃO (O MongoDB bloqueou algo errado): {e}")