from flask import Flask, render_template, request, redirect, url_for
import psycopg2

app = Flask(__name__)

def conectar_banco():
    return psycopg2.connect(
        host="database-pr.cachldhgkeax.us-east-1.rds.amazonaws.com",
        database="postgres",
        user="postgres",
        password="idkpass1?"
    )

@app.route('/')
def index():
    conexao = conectar_banco()
    cursor = conexao.cursor()
    
    cursor.execute("""
        SELECT e.mat_estudante, u.nome, u.cpf, e.ano_ingresso 
        FROM universidade.estudante e 
        JOIN universidade.usuario u ON e.cpf = u.cpf
        ORDER BY u.nome;
    """)
    todos_alunos = cursor.fetchall()
    
    cursor.execute('SELECT idCurso, nome, grau, turno, campus, nivel FROM universidade.curso ORDER BY nome;')
    todos_cursos = cursor.fetchall()
    
    cursor.close()
    conexao.close()
    
    return render_template('index.html', alunos=todos_alunos, cursos=todos_cursos)

@app.route('/cadastrar_aluno', methods=['POST'])
def cadastrar_aluno():
    nome = request.form['nome']
    cpf = int(request.form['cpf'])
    data_nascimento = request.form['data_nascimento']
    email = request.form['email']
    telefone = request.form['telefone']
    matricula = request.form['matricula']
    
    mc_raw = request.form['mc']
    mc = float(mc_raw) if mc_raw else None
    ano_ingresso = int(request.form['ano_ingresso'])
    nome_curso = request.form['nome_curso']
    status = request.form['status']
    
    login = matricula            
    senha = str(cpf)[:6]         

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("SELECT idCurso FROM universidade.curso WHERE nome = %s LIMIT 1;", (nome_curso,))
        resultado_curso = cursor.fetchone()
        
        if not resultado_curso:
            return f"<h1>Erro: O curso '{nome_curso}' não existe!</h1> <br><a href='/'>Voltar</a>"
        
        id_curso = resultado_curso[0]

        cursor.execute("""
            INSERT INTO universidade.usuario (cpf, nome, data_nascimento, email, telefone, login, senha)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """, (cpf, nome, data_nascimento, [email], [telefone], login, senha))

        cursor.execute("""
            INSERT INTO universidade.estudante (mat_estudante, cpf, MC, ano_ingresso)
            VALUES (%s, %s, %s, %s);
        """, (matricula, cpf, mc, ano_ingresso))

        cursor.execute("""
            INSERT INTO universidade.vinculo (mat_estudante, curso, status)
            VALUES (%s, %s, %s);
        """, (matricula, id_curso, status))

        conexao.commit()

    except Exception as e:
        conexao.rollback()
        return f"<h1>Erro de Base de Dados: {e}</h1> <br><a href='/'>Voltar</a>"
    finally:
        cursor.close()
        conexao.close()

    return redirect(url_for('index'))

@app.route('/cadastrar_curso', methods=['POST'])
def cadastrar_curso():
    nome = request.form['nome_curso']
    campus = request.form['campus']
    grau = request.form['grau']
    nivel = request.form['nivel']
    turno = request.form['turno']

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("""
            INSERT INTO universidade.curso (nome, grau, turno, campus, nivel) 
            VALUES (%s, %s, %s, %s, %s);
        """, (nome, grau, turno, campus, nivel))
        conexao.commit()
    except Exception as e:
        conexao.rollback()
        return f"<h1>Erro ao registar curso: {e}</h1> <br><a href='/'>Voltar</a>"
    finally:
        cursor.close()
        conexao.close()

    return redirect(url_for('index'))

@app.route('/deletar_aluno/<cpf>', methods=['POST'])
def deletar_aluno(cpf):
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("SELECT mat_estudante FROM universidade.estudante WHERE cpf = %s;", (int(cpf),))
        resultado = cursor.fetchone()

        if resultado:
            matricula = resultado[0]
            cursor.execute("DELETE FROM universidade.vinculo WHERE mat_estudante = %s;", (matricula,))
            cursor.execute("DELETE FROM universidade.estudante WHERE cpf = %s;", (int(cpf),))

        cursor.execute("DELETE FROM universidade.usuario WHERE cpf = %s;", (int(cpf),))
        conexao.commit()
    except Exception as e:
        conexao.rollback()
        return f"<h1>Erro ao tentar eliminar aluno: {e}</h1> <br><a href='/'>Voltar</a>"
    finally:
        cursor.close()
        conexao.close()

    return redirect(url_for('index'))

@app.route('/deletar_curso/<id_curso>', methods=['POST'])
def deletar_curso(id_curso):
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM universidade.vinculo WHERE curso = %s;", (id_curso,))
        total_alunos = cursor.fetchone()[0]

        if total_alunos > 0:
            return f"""
                <h1>Não é possível eliminar o curso!</h1>
                <p>Existem {total_alunos} aluno(s) inscrito(s) neste curso atualmente.</p>
                <p>Transfira os alunos antes de remover o curso.</p>
                <br><a href='/'>Voltar ao Painel</a>
            """

        cursor.execute("DELETE FROM universidade.curso WHERE idCurso = %s;", (id_curso,))
        conexao.commit()
    except Exception as e:
        conexao.rollback()
        return f"<h1>Erro ao tentar eliminar curso: {e}</h1> <br><a href='/'>Voltar</a>"
    finally:
        cursor.close()
        conexao.close()

    return redirect(url_for('index'))

@app.route('/usuario/<cpf>')
def detalhes_usuario(cpf):
    conexao = conectar_banco()
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT cpf, nome, data_nascimento, email, telefone, login 
        FROM universidade.usuario 
        WHERE cpf = %s;
    """, (int(cpf),))
    usuario = cursor.fetchone()

    cursor.execute("""
        SELECT e.mat_estudante, e.cpf, e.MC, v.status, c.nome
        FROM universidade.estudante e
        LEFT JOIN universidade.vinculo v ON e.mat_estudante = v.mat_estudante
        LEFT JOIN universidade.curso c ON v.curso = c.idCurso
        WHERE e.cpf = %s;
    """, (int(cpf),))
    estudante = cursor.fetchone()

    cursor.close()
    conexao.close()

    if not usuario:
        return "<h1>Utilizador não encontrado!</h1> <br><a href='/'>Voltar</a>"

    return render_template('informacoes.html', usuario=usuario, estudante=estudante)

@app.route('/editar_usuario/<cpf>', methods=['POST'])
def editar_usuario(cpf):
    nome = request.form['nome']
    login = request.form['login']

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("""
            UPDATE universidade.usuario 
            SET nome = %s, login = %s 
            WHERE cpf = %s;
        """, (nome, login, int(cpf)))
        conexao.commit()
    except Exception as e:
        conexao.rollback()
        return f"<h1>Erro ao atualizar perfil: {e}</h1> <br><a href='/usuario/{cpf}'>Voltar</a>"
    finally:
        cursor.close()
        conexao.close()

    return redirect(url_for('detalhes_usuario', cpf=cpf))

@app.route('/atualizar_status_vinculo', methods=['POST'])
def atualizar_status_vinculo():
    matricula = request.form['matricula']
    status_vinculo = request.form['status_vinculo']

    conexao = conectar_banco()
    cursor = conexao.cursor()
    cpf_aluno = None

    try:
        cursor.execute("""
            UPDATE universidade.vinculo 
            SET status = %s 
            WHERE mat_estudante = %s;
        """, (status_vinculo, matricula))
        conexao.commit()

        cursor.execute("SELECT cpf FROM universidade.estudante WHERE mat_estudante = %s;", (matricula,))
        resultado = cursor.fetchone()
        if resultado:
            cpf_aluno = resultado[0]

    except Exception as e:
        conexao.rollback()
        return f"<h1>Erro ao atualizar estado: {e}</h1> <br><a href='/'>Voltar ao Painel</a>"
    finally:
        cursor.close()
        conexao.close()

    if cpf_aluno:
        return redirect(url_for('detalhes_usuario', cpf=cpf_aluno))
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)