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
    
    # Busca os alunos (Fazendo a junção de Estudante e Usuário)
    cursor.execute("""
        SELECT e.mat_estudante, u.nome, u.cpf, e.MC, e.ano_ingresso, v.status
        FROM universidade.estudante e 
        JOIN universidade.usuario u ON e.cpf = u.cpf
            ;
    """)
    todos_alunos = cursor.fetchall()
    
    # Busca os cursos
    cursor.execute('SELECT idCurso, nome, grau, turno, campus, nivel FROM universidade.curso;')
    todos_cursos = cursor.fetchall()
    
    cursor.close()
    conexao.close()
    
    # Manda as variáveis para o HTML desenhar as tabelas
    return render_template('index.html', alunos=todos_alunos, cursos=todos_cursos)

# ==========================================
# ROTA PARA CADASTRAR ALUNO
# ==========================================
@app.route('/cadastrar_aluno', methods=['POST'])
def cadastrar_aluno():
    # Pega o que foi digitado no HTML
    nome = request.form['nome']
    cpf = request.form['cpf']
    matricula = request.form['matricula']
    ano = request.form['ano_ingresso']
    status = request.form['novo_status']
    curso = request.form['nome_curso']

    conexao = conectar_banco()
    cursor = conexao.cursor()
    
    # 1º Insere na tabela usuário (Pois estudante depende de usuário)
    cursor.execute("INSERT INTO universidade.usuario (cpf, nome) VALUES (%s, %s)", (cpf, nome))
    
    # 2º Insere na tabela estudante
    cursor.execute("INSERT INTO universidade.estudante (mat_estudante, cpf, ano_ingresso) VALUES (%s, %s, %s)", (matricula, cpf, ano))
    cursor.execute("INSERT INTO universidade.vinculo (mat_estudante,status,curso) VALUES (%s, %s)", (matricula, status))
    
    conexao.commit() # Salva na AWS
    cursor.close()
    conexao.close()
    
    return redirect('/') # Recarrega a página

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
    
    cursor.execute("UPDATE universidade.vinculo SET status = %s WHERE mat_estudante = %s", (novo_status, matricula))
    
    conexao.commit()
    cursor.close()
    conexao.close()
    
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)