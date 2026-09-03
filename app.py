from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from pathlib import Path
from datetime import date

app = Flask(__name__, template_folder=".", static_folder=".")
app.secret_key = "biblioteca-escolar-antonio-peron"
DB = Path("biblioteca.db")

def conectar():
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout = 30000")
    return con

def iniciar_banco():
    con = conectar()

    try:
        con.execute("PRAGMA journal_mode=WAL")

        con.execute("""CREATE TABLE IF NOT EXISTS livros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            titulo TEXT NOT NULL,
            autor TEXT,
            categoria TEXT,
            quantidade INTEGER NOT NULL,
            disponivel INTEGER NOT NULL
        )""")

        con.execute("""CREATE TABLE IF NOT EXISTS alunos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matricula TEXT UNIQUE NOT NULL,
            nome TEXT NOT NULL,
            turma TEXT
        )""")

        con.execute("""CREATE TABLE IF NOT EXISTS emprestimos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER NOT NULL,
            livro_id INTEGER NOT NULL,
            data_emprestimo TEXT NOT NULL,
            data_prevista TEXT NOT NULL,
            data_devolucao TEXT,
            status TEXT NOT NULL DEFAULT 'Em andamento',
            FOREIGN KEY(aluno_id) REFERENCES alunos(id),
            FOREIGN KEY(livro_id) REFERENCES livros(id)
        )""")

        con.commit()

    finally:
    if con:
        con.close()

@app.route("/")
def inicio():
    con = conectar()
    total = con.execute("SELECT COUNT(*) FROM livros").fetchone()[0]
    disponiveis = con.execute("SELECT COALESCE(SUM(disponivel),0) FROM livros").fetchone()[0]
    emprestados = con.execute("SELECT COUNT(*) FROM emprestimos WHERE status='Em andamento'").fetchone()[0]
    atrasados = con.execute("""SELECT COUNT(*) FROM emprestimos
        WHERE status='Em andamento' AND data_prevista < ?""", (date.today().isoformat(),)).fetchone()[0]
    recentes = con.execute("""SELECT a.nome aluno,l.titulo livro,e.data_emprestimo,e.status
        FROM emprestimos e JOIN alunos a ON a.id=e.aluno_id
        JOIN livros l ON l.id=e.livro_id ORDER BY e.id DESC LIMIT 8""").fetchall()
    con.close()
    return render_template("inicio.html", total=total, disponiveis=disponiveis,
        emprestados=emprestados, atrasados=atrasados, recentes=recentes)

@app.route("/livros")
def livros():
    busca = request.args.get("busca", "").strip()
    con = conectar()
    if busca:
        dados = con.execute("""SELECT * FROM livros WHERE titulo LIKE ? OR autor LIKE ?
            OR codigo LIKE ? ORDER BY titulo""", (f"%{busca}%",)*3).fetchall()
    else:
        dados = con.execute("SELECT * FROM livros ORDER BY titulo").fetchall()
    con.close()
    return render_template("livros.html", livros=dados, busca=busca)

@app.route("/livros/novo", methods=["GET", "POST"])
def novo_livro():

    if request.method == "POST":

        con = None

        try:
            q = int(request.form["quantidade"])

            con = conectar()

            con.execute(
                """INSERT INTO livros(
                    codigo,
                    titulo,
                    autor,
                    categoria,
                    quantidade,
                    disponivel
                ) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    request.form["codigo"],
                    request.form["titulo"],
                    request.form["autor"],
                    request.form["categoria"],
                    q,
                    q
                )
            )

            con.commit()

            flash("Livro cadastrado com sucesso!")

            return redirect(url_for("livros"))

        except sqlite3.IntegrityError:

            flash("Este código de livro já está cadastrado.")

        except Exception as erro:

            flash(f"Erro ao cadastrar o livro: {erro}")

        finally:

            if con:
                con.close()

    return render_template("novo_livro.html")

@app.route("/livros/excluir/<int:id>", methods=["POST"])
def excluir_livro(id):
    con=conectar()
    ativos=con.execute("SELECT COUNT(*) FROM emprestimos WHERE livro_id=? AND status='Em andamento'",(id,)).fetchone()[0]
    if ativos: flash("Não é possível excluir um livro com empréstimo ativo.")
    else:
        con.execute("DELETE FROM livros WHERE id=?",(id,)); con.commit(); flash("Livro excluído.")
    con.close()
    return redirect(url_for("livros"))

@app.route("/alunos")
def alunos():
    busca=request.args.get("busca","").strip()
    con=conectar()
    if busca:
        dados=con.execute("SELECT * FROM alunos WHERE nome LIKE ? OR matricula LIKE ? OR turma LIKE ? ORDER BY nome",
                          (f"%{busca}%",)*3).fetchall()
    else: dados=con.execute("SELECT * FROM alunos ORDER BY nome").fetchall()
    con.close()
    return render_template("alunos.html", alunos=dados, busca=busca)

@app.route("/alunos/novo", methods=["GET", "POST"])
def novo_aluno():

    if request.method == "POST":

        con = None

        try:
            con = conectar()

            con.execute(
                "INSERT INTO alunos(matricula, nome, turma) VALUES (?, ?, ?)",
                (
                    request.form["matricula"],
                    request.form["nome"],
                    request.form["turma"]
                )
            )

            con.commit()

            flash("Aluno cadastrado com sucesso!")

            return redirect(url_for("alunos"))

        except sqlite3.IntegrityError:

            flash("Esta matrícula já está cadastrada.")

        except sqlite3.OperationalError as erro:

            flash(f"Erro no banco de dados: {erro}")

        finally:

            if con:
                con.close()

    return render_template("novo_aluno.html")

@app.route("/alunos/excluir/<int:id>", methods=["POST"])
def excluir_aluno(id):
    con=conectar()
    ativos=con.execute("SELECT COUNT(*) FROM emprestimos WHERE aluno_id=? AND status='Em andamento'",(id,)).fetchone()[0]
    if ativos: flash("Não é possível excluir aluno com empréstimo ativo.")
    else: con.execute("DELETE FROM alunos WHERE id=?",(id,)); con.commit(); flash("Aluno excluído.")
    con.close(); return redirect(url_for("alunos"))

@app.route("/emprestimos", methods=["GET","POST"])
def emprestimos():
    con=conectar()
    if request.method=="POST":
        aluno_id=int(request.form["aluno_id"]); livro_id=int(request.form["livro_id"])
        disponivel=con.execute("SELECT disponivel FROM livros WHERE id=?",(livro_id,)).fetchone()
        if not disponivel or disponivel["disponivel"]<=0:
            flash("Este livro não está disponível.")
        else:
            con.execute("""INSERT INTO emprestimos(aluno_id,livro_id,data_emprestimo,data_prevista,status)
                VALUES(?,?,?,?,?)""",(aluno_id,livro_id,date.today().isoformat(),
                request.form["data_prevista"],"Em andamento"))
            con.execute("UPDATE livros SET disponivel=disponivel-1 WHERE id=?",(livro_id,))
            con.commit(); flash("Empréstimo registrado com sucesso!")
            con.close(); return redirect(url_for("emprestimos"))
    alunos_lista=con.execute("SELECT * FROM alunos ORDER BY nome").fetchall()
    livros_lista=con.execute("SELECT * FROM livros WHERE disponivel>0 ORDER BY titulo").fetchall()
    dados=con.execute("""SELECT e.*,a.nome aluno,l.titulo livro FROM emprestimos e
        JOIN alunos a ON a.id=e.aluno_id JOIN livros l ON l.id=e.livro_id
        WHERE e.status='Em andamento' ORDER BY e.data_prevista""").fetchall()
    con.close()
    return render_template("emprestimos.html",alunos=alunos_lista,livros=livros_lista,emprestimos=dados)

@app.route("/devolucoes")
def devolucoes():
    con=conectar()
    dados=con.execute("""SELECT e.*,a.nome aluno,l.titulo livro FROM emprestimos e
        JOIN alunos a ON a.id=e.aluno_id JOIN livros l ON l.id=e.livro_id
        WHERE e.status='Em andamento' ORDER BY e.data_prevista""").fetchall()
    con.close()
    return render_template("devolucoes.html", emprestimos=dados, hoje=date.today().isoformat())

@app.route("/devolucoes/<int:id>", methods=["POST"])
def registrar_devolucao(id):
    con=conectar()
    emp=con.execute("SELECT livro_id,status FROM emprestimos WHERE id=?",(id,)).fetchone()
    if emp and emp["status"]=="Em andamento":
        con.execute("UPDATE emprestimos SET status='Devolvido',data_devolucao=? WHERE id=?",(date.today().isoformat(),id))
        con.execute("UPDATE livros SET disponivel=disponivel+1 WHERE id=?",(emp["livro_id"],))
        con.commit(); flash("Devolução registrada com sucesso!")
    con.close(); return redirect(url_for("devolucoes"))

@app.route("/relatorios")
def relatorios():
    con=conectar()
    mais=con.execute("""SELECT l.titulo,COUNT(*) total FROM emprestimos e JOIN livros l ON l.id=e.livro_id
        GROUP BY l.id ORDER BY total DESC LIMIT 10""").fetchall()
    atrasados=con.execute("""SELECT a.nome aluno,l.titulo livro,e.data_prevista FROM emprestimos e
        JOIN alunos a ON a.id=e.aluno_id JOIN livros l ON l.id=e.livro_id
        WHERE e.status='Em andamento' AND e.data_prevista < ? ORDER BY e.data_prevista""",(date.today().isoformat(),)).fetchall()
    con.close()
    return render_template("relatorios.html",mais=mais,atrasados=atrasados)
iniciar_banco()

if __name__ == "__main__":
    app.run(debug=True)

