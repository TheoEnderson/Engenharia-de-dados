import os
from datetime import date

from flask import Flask, flash, redirect, render_template, request, url_for
import psycopg2


app = Flask(__name__)
app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "chave-local-de-desenvolvimento-altere-em-producao",
)


def conectar_banco():
    return psycopg2.connect(
        host="database-pr.cachldhgkeax.us-east-1.rds.amazonaws.com",
        database="postgres",
        user="postgres",
        password="idkpass1?"
    )


def pagina_erro(mensagem, destino="/", categoria="error"):
    """Registra uma mensagem e retorna ao Portal sem expor detalhes internos."""
    flash(mensagem, categoria)
    return redirect(destino)


def mensagem_erro_banco(erro, operacao):
    if isinstance(erro, psycopg2.errors.UniqueViolation):
        restricao = (getattr(erro.diag, "constraint_name", "") or "").lower()
        if "login" in restricao:
            return "Este login já está em uso. Escolha outro login."
        return "Já existe um registro com um dos identificadores informados."
    if isinstance(erro, psycopg2.errors.ForeignKeyViolation):
        return "A operação não pode ser concluída porque o registro ainda possui dados relacionados."
    return f"Não foi possível {operacao}."


@app.route('/')
def index():
    conexao = None
    cursor = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()

        cursor.execute("""
            SELECT e.mat_estudante, u.nome, u.cpf, e.ano_ingresso
            FROM universidade.estudante e
            JOIN universidade.usuario u ON e.cpf = u.cpf
            ORDER BY u.nome;
        """)
        todos_alunos = cursor.fetchall()

        cursor.execute("""
            SELECT idCurso, nome, grau, turno, campus, nivel
            FROM universidade.curso
            ORDER BY nome, campus, turno;
        """)
        todos_cursos = cursor.fetchall()
    finally:
        if cursor is not None:
            cursor.close()
        if conexao is not None:
            conexao.close()

    return render_template('index.html', alunos=todos_alunos, cursos=todos_cursos)


@app.route('/cadastrar_aluno', methods=['POST'])
def cadastrar_aluno():
    login = request.form.get('login', '').strip()
    if not login:
        return pagina_erro("O login é obrigatório.")
    if len(login) > 45:
        return pagina_erro("O login deve ter no máximo 45 caracteres.")

    try:
        nome = request.form['nome'].strip()
        cpf = int(request.form['cpf'])
        data_nascimento = request.form['data_nascimento']
        email = request.form['email'].strip()
        telefone = request.form['telefone'].strip()
        matricula = request.form['matricula'].strip()
        mc_raw = request.form.get('mc', '').strip()
        mc = float(mc_raw) if mc_raw else None
        ano_ingresso = int(request.form['ano_ingresso'])
        id_curso = int(request.form['curso_id'])
        status = request.form['status']
    except (KeyError, TypeError, ValueError):
        return pagina_erro("Há campos obrigatórios ausentes ou inválidos.")

    if not all((nome, data_nascimento, email, telefone, matricula, status)):
        return pagina_erro("Preencha todos os campos obrigatórios.")
    if not 1900 <= ano_ingresso <= 2100:
        return pagina_erro("O ano de ingresso deve estar entre 1900 e 2100.")

    # O dump define vinculo.data_entrada como DATE. Como a interface recebe
    # somente o ano, o primeiro dia desse ano representa a data de ingresso.
    data_entrada = date(ano_ingresso, 1, 1)
    senha = str(cpf)[:6]

    conexao = None
    cursor = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()

        cursor.execute(
            "SELECT 1 FROM universidade.usuario WHERE login = %s;",
            (login,),
        )
        if cursor.fetchone():
            conexao.rollback()
            return pagina_erro("Este login já está em uso. Escolha outro login.")

        cursor.execute(
            "SELECT 1 FROM universidade.curso WHERE idCurso = %s;",
            (id_curso,),
        )
        if not cursor.fetchone():
            conexao.rollback()
            return pagina_erro("O curso selecionado não existe.")

        cursor.execute("""
            INSERT INTO universidade.usuario
                (cpf, nome, data_nascimento, email, telefone, login, senha)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """, (cpf, nome, data_nascimento, [email], [telefone], login, senha))

        cursor.execute("""
            INSERT INTO universidade.estudante
                (mat_estudante, cpf, MC, ano_ingresso)
            VALUES (%s, %s, %s, %s);
        """, (matricula, cpf, mc, ano_ingresso))

        cursor.execute("""
            INSERT INTO universidade.vinculo
                (mat_estudante, curso, data_entrada, status)
            SELECT %s, %s, %s, %s
            WHERE NOT EXISTS (
                SELECT 1
                FROM universidade.vinculo
                WHERE mat_estudante = %s AND curso = %s
            );
        """, (matricula, id_curso, data_entrada, status, matricula, id_curso))
        if cursor.rowcount != 1:
            raise psycopg2.IntegrityError("O vínculo entre estudante e curso já existe.")

        # As três inserções pertencem à mesma transação.
        conexao.commit()
    except Exception as erro:
        if conexao is not None:
            conexao.rollback()
        return pagina_erro(mensagem_erro_banco(erro, "cadastrar o aluno"))
    finally:
        if cursor is not None:
            cursor.close()
        if conexao is not None:
            conexao.close()

    flash("Aluno cadastrado com sucesso.", "success")
    return redirect(url_for('index'))


@app.route('/cadastrar_curso', methods=['POST'])
def cadastrar_curso():
    try:
        nome = request.form['nome_curso'].strip()
        campus = request.form['campus'].strip()
        grau = request.form['grau']
        nivel = request.form['nivel']
        turno = request.form['turno']
    except (KeyError, AttributeError):
        return pagina_erro("Há campos obrigatórios do curso ausentes ou inválidos.")

    if not all((nome, campus, grau, nivel, turno)):
        return pagina_erro("Preencha todos os campos obrigatórios do curso.")

    conexao = None
    cursor = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        cursor.execute("""
            INSERT INTO universidade.curso (nome, grau, turno, campus, nivel)
            VALUES (%s, %s, %s, %s, %s);
        """, (nome, grau, turno, campus, nivel))
        conexao.commit()
    except Exception as erro:
        if conexao is not None:
            conexao.rollback()
        return pagina_erro(mensagem_erro_banco(erro, "cadastrar o curso"))
    finally:
        if cursor is not None:
            cursor.close()
        if conexao is not None:
            conexao.close()

    flash("Curso cadastrado com sucesso.", "success")
    return redirect(url_for('index'))


@app.route('/editar_curso/<int:id_curso>', methods=['POST'])
def editar_curso(id_curso):
    try:
        nome = request.form['nome_curso'].strip()
        campus = request.form['campus'].strip()
        grau = request.form['grau']
        nivel = request.form['nivel']
        turno = request.form['turno']
    except (KeyError, AttributeError):
        return pagina_erro("Há campos obrigatórios do curso ausentes ou inválidos.")

    if not all((nome, campus, grau, nivel, turno)):
        return pagina_erro("Preencha todos os campos obrigatórios do curso.")

    conexao = None
    cursor = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        cursor.execute("""
            UPDATE universidade.curso
            SET nome = %s, grau = %s, turno = %s, campus = %s, nivel = %s
            WHERE idCurso = %s;
        """, (nome, grau, turno, campus, nivel, id_curso))
        conexao.commit()
    except Exception as erro:
        if conexao is not None:
            conexao.rollback()
        return pagina_erro(mensagem_erro_banco(erro, "atualizar o curso"))
    finally:
        if cursor is not None:
            cursor.close()
        if conexao is not None:
            conexao.close()

    flash("Curso atualizado com sucesso.", "success")
    return redirect(url_for('index'))


@app.route('/deletar_aluno/<cpf>', methods=['POST'])
def deletar_aluno(cpf):
    conexao = None
    cursor = None
    try:
        cpf_numero = int(cpf)
        conexao = conectar_banco()
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT mat_estudante FROM universidade.estudante WHERE cpf = %s;",
            (cpf_numero,),
        )
        resultado = cursor.fetchone()

        if resultado:
            matricula = resultado[0]
            cursor.execute(
                "DELETE FROM universidade.vinculo WHERE mat_estudante = %s;",
                (matricula,),
            )
            cursor.execute(
                "DELETE FROM universidade.estudante WHERE cpf = %s;",
                (cpf_numero,),
            )

        cursor.execute(
            "DELETE FROM universidade.usuario WHERE cpf = %s;",
            (cpf_numero,),
        )
        conexao.commit()
    except Exception as erro:
        if conexao is not None:
            conexao.rollback()
        return pagina_erro(mensagem_erro_banco(erro, "excluir o aluno"))
    finally:
        if cursor is not None:
            cursor.close()
        if conexao is not None:
            conexao.close()

    flash("Aluno excluído com sucesso.", "success")
    return redirect(url_for('index'))


@app.route('/deletar_curso/<int:id_curso>', methods=['POST'])
def deletar_curso(id_curso):
    conexao = None
    cursor = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM universidade.vinculo WHERE curso = %s;",
            (id_curso,),
        )
        total_alunos = cursor.fetchone()[0]

        if total_alunos > 0:
            conexao.rollback()
            return pagina_erro(
                f"Não é possível excluir o curso: existem {total_alunos} aluno(s) vinculado(s).",
                categoria="warning",
            )

        cursor.execute(
            "DELETE FROM universidade.curso WHERE idCurso = %s;",
            (id_curso,),
        )
        conexao.commit()
    except Exception as erro:
        if conexao is not None:
            conexao.rollback()
        return pagina_erro(mensagem_erro_banco(erro, "excluir o curso"))
    finally:
        if cursor is not None:
            cursor.close()
        if conexao is not None:
            conexao.close()

    flash("Curso excluído com sucesso.", "success")
    return redirect(url_for('index'))


@app.route('/usuario/<cpf>')
def detalhes_usuario(cpf):
    conexao = None
    cursor = None
    try:
        cpf_numero = int(cpf)
        conexao = conectar_banco()
        cursor = conexao.cursor()
        cursor.execute("""
            SELECT cpf, nome, data_nascimento, email, telefone, login
            FROM universidade.usuario
            WHERE cpf = %s;
        """, (cpf_numero,))
        usuario = cursor.fetchone()

        cursor.execute("""
            SELECT e.mat_estudante, e.cpf, e.MC, v.status, c.nome,
                   e.ano_ingresso, v.data_entrada, v.curso, v.idVinculo
            FROM universidade.estudante e
            LEFT JOIN universidade.vinculo v
                ON e.mat_estudante = v.mat_estudante
            LEFT JOIN universidade.curso c ON v.curso = c.idCurso
            WHERE e.cpf = %s;
        """, (cpf_numero,))
        estudante = cursor.fetchone()

        cursor.execute("""
            SELECT idCurso, nome, grau, turno, campus, nivel
            FROM universidade.curso
            ORDER BY nome, campus, turno;
        """)
        cursos = cursor.fetchall()
    finally:
        if cursor is not None:
            cursor.close()
        if conexao is not None:
            conexao.close()

    if not usuario:
        return pagina_erro("Usuário não encontrado.")

    return render_template(
        'informacoes.html', usuario=usuario, estudante=estudante, cursos=cursos
    )


@app.route('/editar_usuario/<cpf>', methods=['POST'])
def editar_usuario(cpf):
    nome = request.form.get('nome', '').strip()
    login = request.form.get('login', '').strip()
    if not nome:
        return pagina_erro("O nome é obrigatório.", f"/usuario/{cpf}")
    if not login:
        return pagina_erro("O login é obrigatório.", f"/usuario/{cpf}")
    if len(login) > 45:
        return pagina_erro(
            "O login deve ter no máximo 45 caracteres.", f"/usuario/{cpf}"
        )

    conexao = None
    cursor = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        cursor.execute("""
            UPDATE universidade.usuario
            SET nome = %s, login = %s
            WHERE cpf = %s;
        """, (nome, login, int(cpf)))
        conexao.commit()
    except Exception as erro:
        if conexao is not None:
            conexao.rollback()
        return pagina_erro(
            mensagem_erro_banco(erro, "atualizar o perfil"), f"/usuario/{cpf}"
        )
    finally:
        if cursor is not None:
            cursor.close()
        if conexao is not None:
            conexao.close()

    flash("Dados do usuário atualizados com sucesso.", "success")
    return redirect(url_for('detalhes_usuario', cpf=cpf))


@app.route('/editar_estudante_vinculo', methods=['POST'])
def editar_estudante_vinculo():
    cpf_formulario = request.form.get('cpf', '').strip()
    destino_formulario = (
        f"/usuario/{cpf_formulario}" if cpf_formulario.isdigit() else "/"
    )
    try:
        matricula = request.form['matricula']
        id_vinculo = int(request.form['id_vinculo'])
        id_curso = int(request.form['curso_id'])
        ano_ingresso = int(request.form['ano_ingresso'])
        status = request.form['status_vinculo']
        mc_raw = request.form.get('mc', '').strip()
        mc = float(mc_raw) if mc_raw else None
    except (KeyError, TypeError, ValueError):
        return pagina_erro(
            "Há campos de estudante ou vínculo inválidos.", destino_formulario
        )

    if not 1900 <= ano_ingresso <= 2100:
        return pagina_erro(
            "O ano de ingresso deve estar entre 1900 e 2100.", destino_formulario
        )

    data_entrada = date(ano_ingresso, 1, 1)
    conexao = None
    cursor = None
    cpf_aluno = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT cpf FROM universidade.estudante WHERE mat_estudante = %s;",
            (matricula,),
        )
        resultado = cursor.fetchone()
        if not resultado:
            conexao.rollback()
            return pagina_erro("Estudante não encontrado.", destino_formulario)
        cpf_aluno = resultado[0]

        cursor.execute(
            "SELECT 1 FROM universidade.curso WHERE idCurso = %s;",
            (id_curso,),
        )
        if not cursor.fetchone():
            conexao.rollback()
            return pagina_erro(
                "O curso selecionado não existe.", destino_formulario
            )

        cursor.execute("""
            UPDATE universidade.estudante
            SET MC = %s, ano_ingresso = %s
            WHERE mat_estudante = %s;
        """, (mc, ano_ingresso, matricula))
        cursor.execute("""
            UPDATE universidade.vinculo
            SET curso = %s, data_entrada = %s, status = %s
            WHERE idVinculo = %s AND mat_estudante = %s;
        """, (id_curso, data_entrada, status, id_vinculo, matricula))
        if cursor.rowcount != 1:
            raise psycopg2.IntegrityError("Vínculo não encontrado.")
        conexao.commit()
    except Exception as erro:
        if conexao is not None:
            conexao.rollback()
        destino = f"/usuario/{cpf_aluno}" if cpf_aluno else "/"
        return pagina_erro(
            mensagem_erro_banco(erro, "atualizar estudante e vínculo"), destino
        )
    finally:
        if cursor is not None:
            cursor.close()
        if conexao is not None:
            conexao.close()

    flash("Dados do aluno e do vínculo atualizados com sucesso.", "success")
    return redirect(url_for('detalhes_usuario', cpf=cpf_aluno))


@app.route('/atualizar_status_vinculo', methods=['POST'])
def atualizar_status_vinculo():
    """Mantida por compatibilidade com formulários antigos."""
    matricula = request.form['matricula']
    status_vinculo = request.form['status_vinculo']
    conexao = None
    cursor = None
    cpf_aluno = None
    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()
        cursor.execute("""
            UPDATE universidade.vinculo
            SET status = %s
            WHERE mat_estudante = %s;
        """, (status_vinculo, matricula))
        cursor.execute(
            "SELECT cpf FROM universidade.estudante WHERE mat_estudante = %s;",
            (matricula,),
        )
        resultado = cursor.fetchone()
        if resultado:
            cpf_aluno = resultado[0]
        conexao.commit()
    except Exception as erro:
        if conexao is not None:
            conexao.rollback()
        return pagina_erro(mensagem_erro_banco(erro, "atualizar o vínculo"))
    finally:
        if cursor is not None:
            cursor.close()
        if conexao is not None:
            conexao.close()

    if cpf_aluno:
        flash("Status do vínculo atualizado com sucesso.", "success")
        return redirect(url_for('detalhes_usuario', cpf=cpf_aluno))
    flash("Status atualizado, mas o aluno associado não foi encontrado.", "info")
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
