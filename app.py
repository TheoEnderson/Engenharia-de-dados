from flask import Flask, render_template, request, redirect
import psycopg2

app = Flask(__name__)

DB_HOST = "seu-banco.rds.amazonaws.com"
DB_NAME = "postgres" 
DB_USER = "postgres"
DB_PASS = "sua_senha_nova"

def conectar_banco():
    return psycopg2.connect(
        host= "database-1.cvwyoa2wy9je.us-east-1.rds.amazonaws.com",
        database= "postgres",
        user= "postgres",
        password= "idkpass1?",
    )


@app.route('/')
def index():
    conexao = conectar_banco()
    cursor = conexao.cursor()
    
    # CORREÇÃO NO ÚLTIMO JOIN: Alterado 'v.curso' para 'v.idCurso'
    cursor.execute("""
        SELECT e.mat_estudante, u.nome, u.cpf, e.MC, e.ano_ingresso, v.status, c.nome
        FROM universidade.estudante e 
        JOIN universidade.usuario u ON e.cpf = u.cpf
        JOIN universidade.vinculo v ON e.mat_estudante = v.mat_estudante
        JOIN universidade.curso c ON c.idCurso = v.curso;
    """)
    todos_alunos = cursor.fetchall()
    
    # Busca os cursos
    cursor.execute('SELECT idCurso, nome, grau, turno, campus, nivel FROM universidade.curso;')
    todos_cursos = cursor.fetchall()
    
    cursor.close()
    conexao.close()
    
    return render_template('index.html', alunos=todos_alunos, cursos=todos_cursos)


# ==========================================
# ROTA PARA CADASTRAR ALUNO
# ==========================================
@app.route('/cadastrar_aluno', methods=['POST'])
def cadastrar_aluno():
    nome = request.form['nome']
    cpf = request.form['cpf']
    matricula = request.form['matricula']
    ano = request.form['ano_ingresso']
    status = request.form['novo_status']
    
    # CORREÇÃO 1: Mudei o nome da variável para 'nome_curso' para bater com o SELECT abaixo
    nome_curso = request.form['nome_curso'] 

    conexao = conectar_banco()
    cursor = conexao.cursor()

    # CORREÇÃO 2: Adicionada a vírgula no final -> (nome_curso,) para virar uma tupla válida
    cursor.execute("SELECT idCurso FROM universidade.curso WHERE nome = %s", (nome_curso,))
   
    resultado_busca = cursor.fetchone() 

    if resultado_busca is None:
        # Se não achou o curso, fecha a conexão e avisa o usuário
        cursor.close()
        conexao.close()
        return f"<h1>Erro: O curso '{nome_curso}' não está cadastrado no sistema!</h1> <br> <a href='/'>Voltar</a>"
    id_do_curso = resultado_busca[0]
    
    # Insere no Usuário e no Estudante
    cursor.execute("INSERT INTO universidade.usuario (cpf, nome) VALUES (%s, %s)", (cpf, nome))
    cursor.execute("INSERT INTO universidade.estudante (mat_estudante, cpf, ano_ingresso) VALUES (%s, %s, %s)", (matricula, cpf, ano))
    
    # CORREÇÃO 3: Alterado o nome da coluna de 'curso' para 'idCurso' para bater com o banco
    cursor.execute("INSERT INTO universidade.vinculo (curso, mat_estudante, status) VALUES (%s, %s, %s)", (id_do_curso, matricula, status))
    
    conexao.commit() 
    cursor.close()
    conexao.close()
    
    return redirect('/')

# ============= =======================================================================
# ROTA PARA CADASTRAR CURSO
# ==========================================
@app.route('/cadastrar_curso', methods=['POST'])
def cadastrar_curso():
    nome = request.form['nome_curso']
    campus = request.form['campus']
    turno = request.form['turno']
    
    
    conexao = conectar_banco()
    cursor = conexao.cursor()

  
    cursor.execute("INSERT INTO universidade.curso (nome, campus, turno) VALUES (%s, %s, %s)", (nome, campus, turno))
    
    conexao.commit()
    cursor.close()
    conexao.close()
    
    return redirect('/')


@app.route('/mudar_status', methods=['POST'])
def mudar_status():
    matricula = request.form['matricula_busca']
    novo_status = request.form['novo_status']
    
    conexao = conectar_banco()
    cursor = conexao.cursor()
    cursor.execute("SELECT cpf FROM universidade.estudante WHERE mat_estudante = %s", (matricula,))
    resultado = cursor.fetchone()

    if novo_status == "Cancelada" :
        cpf_aluno = resultado[0]
        cursor.execute("DELETE FROM universidade.vinculo WHERE mat_estudante = %s", (matricula,))              
        cursor.execute("DELETE FROM universidade.estudante WHERE mat_estudante = %s", (matricula,))
        cursor.execute("DELETE FROM universidade.usuario WHERE cpf = %s", (cpf_aluno,))
        
        print(f"Aluno {matricula} deletado do sistema por cancelamento.")
    else :
        cursor.execute("UPDATE universidade.vinculo SET status = %s WHERE mat_estudante = %s", (novo_status, matricula))
    
    conexao.commit()
    cursor.close()
    conexao.close()
    
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)