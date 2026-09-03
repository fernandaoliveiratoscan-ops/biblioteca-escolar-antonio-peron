
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import date, timedelta

DB = "biblioteca_escolar.db"

class BibliotecaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Biblioteca Escolar")
        self.root.geometry("1100x700")
        self.root.minsize(900, 600)
        self.init_db()
        self.style()
        self.build_layout()
        self.show_dashboard()

    def init_db(self):
        self.conn = sqlite3.connect(DB)
        c = self.conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS livros(
            id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT UNIQUE,
            titulo TEXT NOT NULL, autor TEXT, categoria TEXT,
            quantidade INTEGER DEFAULT 1, disponivel INTEGER DEFAULT 1
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS alunos(
            id INTEGER PRIMARY KEY AUTOINCREMENT, matricula TEXT UNIQUE,
            nome TEXT NOT NULL, turma TEXT, responsavel TEXT, telefone TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS emprestimos(
            id INTEGER PRIMARY KEY AUTOINCREMENT, aluno_id INTEGER,
            livro_id INTEGER, data_emprestimo TEXT, data_prevista TEXT,
            data_devolucao TEXT, status TEXT DEFAULT 'Em andamento'
        )""")
        self.conn.commit()

    def style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", rowheight=30, font=("Arial", 10))
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"))
        style.configure("Title.TLabel", font=("Arial", 20, "bold"))
        style.configure("Card.TLabel", font=("Arial", 11, "bold"))
        style.configure("TButton", padding=8)

    def build_layout(self):
        self.sidebar = tk.Frame(self.root, bg="#14263d", width=210)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        tk.Label(self.sidebar, text="📚 BIBLIOTECA\nESCOLAR", bg="#14263d",
                 fg="white", font=("Arial", 15, "bold"), justify="left").pack(pady=30)

        menu = [
            ("🏠  Início", self.show_dashboard),
            ("📚  Livros", self.show_livros),
            ("👨‍🎓  Alunos", self.show_alunos),
            ("📤  Empréstimos", self.show_emprestimos),
            ("📥  Devoluções", self.show_devolucoes),
            ("📊  Relatórios", self.show_relatorios),
        ]
        for text, command in menu:
            tk.Button(self.sidebar, text=text, command=command, anchor="w",
                      bg="#14263d", fg="white", activebackground="#2563b8",
                      activeforeground="white", bd=0, padx=18, pady=12,
                      font=("Arial", 10)).pack(fill="x")

        tk.Frame(self.sidebar, bg="#2a3d54", height=1).pack(fill="x", padx=15, pady=20)
        tk.Button(self.sidebar, text="💾  Backup", command=self.backup_info,
                  anchor="w", bg="#14263d", fg="white", bd=0, padx=18, pady=12,
                  font=("Arial", 10)).pack(fill="x")

        self.content = tk.Frame(self.root, bg="#f5f7fa")
        self.content.pack(side="left", fill="both", expand=True)

    def clear(self):
        for w in self.content.winfo_children():
            w.destroy()

    def header(self, title, subtitle=""):
        ttk.Label(self.content, text=title, style="Title.TLabel").pack(anchor="w", padx=30, pady=(25, 2))
        if subtitle:
            ttk.Label(self.content, text=subtitle, foreground="#64748b").pack(anchor="w", padx=30, pady=(0, 20))

    def count(self, sql, args=()):
        return self.conn.execute(sql, args).fetchone()[0]

    def card(self, parent, title, value):
        box = tk.Frame(parent, bg="white", bd=1, relief="solid")
        box.pack(side="left", fill="both", expand=True, padx=8)
        tk.Label(box, text=title, bg="white", fg="#64748b", font=("Arial", 10)).pack(anchor="w", padx=15, pady=(15, 5))
        tk.Label(box, text=str(value), bg="white", fg="#1e3a5f", font=("Arial", 22, "bold")).pack(anchor="w", padx=15, pady=(0, 15))

    def show_dashboard(self):
        self.clear()
        self.header("Dashboard", "Visão geral da Biblioteca Escolar")
        cards = tk.Frame(self.content, bg="#f5f7fa")
        cards.pack(fill="x", padx=22)
        total = self.count("SELECT COUNT(*) FROM livros")
        disponiveis = self.count("SELECT COALESCE(SUM(disponivel),0) FROM livros")
        ativos = self.count("SELECT COUNT(*) FROM emprestimos WHERE status='Em andamento'")
        atrasados = self.count("SELECT COUNT(*) FROM emprestimos WHERE status='Em andamento' AND data_prevista < ?", (date.today().isoformat(),))
        self.card(cards, "📚 Total de títulos", total)
        self.card(cards, "✅ Exemplares disponíveis", disponiveis)
        self.card(cards, "📤 Empréstimos ativos", ativos)
        self.card(cards, "⚠️ Empréstimos atrasados", atrasados)

        frame = tk.Frame(self.content, bg="white")
        frame.pack(fill="both", expand=True, padx=30, pady=25)
        tk.Label(frame, text="Empréstimos recentes", bg="white", font=("Arial", 14, "bold")).pack(anchor="w", padx=15, pady=15)
        cols = ("Aluno", "Livro", "Empréstimo", "Devolução prevista", "Status")
        tree = ttk.Treeview(frame, columns=cols, show="headings")
        for col in cols: tree.heading(col, text=col); tree.column(col, width=150)
        rows = self.conn.execute("""SELECT a.nome,l.titulo,e.data_emprestimo,e.data_prevista,e.status
                                  FROM emprestimos e JOIN alunos a ON a.id=e.aluno_id
                                  JOIN livros l ON l.id=e.livro_id ORDER BY e.id DESC LIMIT 10""").fetchall()
        for r in rows: tree.insert("", "end", values=r)
        tree.pack(fill="both", expand=True, padx=15, pady=(0,15))

    def form_entry(self, parent, label, row, col=0):
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky="w", padx=8, pady=(8,2))
        e = ttk.Entry(parent, width=32)
        e.grid(row=row+1, column=col, sticky="ew", padx=8, pady=(0,8))
        return e

    def show_livros(self):
        self.clear()
        self.header("Livros", "Cadastre e gerencie os livros da biblioteca")
        top = tk.Frame(self.content, bg="#f5f7fa")
        top.pack(fill="x", padx=30)
        tk.Button(top, text="+ Adicionar livro", command=self.add_livro_dialog, bg="#2563b8", fg="white", bd=0, padx=15, pady=8).pack(side="right")
        cols=("Código","Título","Autor","Categoria","Quantidade","Disponível")
        tree=self.make_tree(cols)
        rows=self.conn.execute("SELECT codigo,titulo,autor,categoria,quantidade,disponivel FROM livros ORDER BY titulo").fetchall()
        for r in rows: tree.insert("", "end", values=r)

    def make_tree(self, cols):
        frame=tk.Frame(self.content, bg="white")
        frame.pack(fill="both", expand=True, padx=30, pady=20)
        tree=ttk.Treeview(frame, columns=cols, show="headings")
        for c in cols: tree.heading(c,text=c); tree.column(c,width=140)
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        return tree

    def add_livro_dialog(self):
        win=tk.Toplevel(self.root); win.title("Adicionar livro"); win.geometry("480x420")
        f=ttk.Frame(win,padding=20); f.pack(fill="both",expand=True)
        codigo=self.form_entry(f,"Código",0); titulo=self.form_entry(f,"Título",2)
        autor=self.form_entry(f,"Autor",4); categoria=self.form_entry(f,"Categoria",6)
        quantidade=self.form_entry(f,"Quantidade",8); quantidade.insert(0,"1")
        def salvar():
            try:
                q=int(quantidade.get())
                self.conn.execute("INSERT INTO livros(codigo,titulo,autor,categoria,quantidade,disponivel) VALUES(?,?,?,?,?,?)",
                                  (codigo.get(),titulo.get(),autor.get(),categoria.get(),q,q))
                self.conn.commit(); win.destroy(); self.show_livros()
            except Exception as e: messagebox.showerror("Erro",f"Não foi possível salvar: {e}")
        ttk.Button(f,text="Salvar livro",command=salvar).grid(row=10,column=0,padx=8,pady=15,sticky="ew")

    def show_alunos(self):
        self.clear()
        self.header("Alunos", "Cadastre os estudantes da escola")
        top=tk.Frame(self.content,bg="#f5f7fa"); top.pack(fill="x",padx=30)
        tk.Button(top,text="+ Adicionar aluno",command=self.add_aluno_dialog,bg="#2563b8",fg="white",bd=0,padx=15,pady=8).pack(side="right")
        cols=("Matrícula","Nome","Turma","Responsável","Telefone")
        tree=self.make_tree(cols)
        for r in self.conn.execute("SELECT matricula,nome,turma,responsavel,telefone FROM alunos ORDER BY nome").fetchall(): tree.insert("", "end", values=r)

    def add_aluno_dialog(self):
        win=tk.Toplevel(self.root); win.title("Adicionar aluno"); win.geometry("480x460")
        f=ttk.Frame(win,padding=20); f.pack(fill="both",expand=True)
        mat=self.form_entry(f,"Matrícula",0); nome=self.form_entry(f,"Nome completo",2)
        turma=self.form_entry(f,"Turma",4); resp=self.form_entry(f,"Responsável",6); tel=self.form_entry(f,"Telefone",8)
        def salvar():
            try:
                self.conn.execute("INSERT INTO alunos(matricula,nome,turma,responsavel,telefone) VALUES(?,?,?,?,?)",(mat.get(),nome.get(),turma.get(),resp.get(),tel.get()))
                self.conn.commit(); win.destroy(); self.show_alunos()
            except Exception as e: messagebox.showerror("Erro",str(e))
        ttk.Button(f,text="Salvar aluno",command=salvar).grid(row=10,column=0,padx=8,pady=15,sticky="ew")

    def show_emprestimos(self):
        self.clear(); self.header("Empréstimos", "Registre a retirada de livros")
        panel=ttk.Frame(self.content,padding=30); panel.pack(fill="x")
        alunos=self.conn.execute("SELECT id,nome FROM alunos ORDER BY nome").fetchall()
        livros=self.conn.execute("SELECT id,titulo FROM livros WHERE disponivel>0 ORDER BY titulo").fetchall()
        ttk.Label(panel,text="Aluno").grid(row=0,column=0,sticky="w")
        aluno=ttk.Combobox(panel,values=[f"{x[0]} - {x[1]}" for x in alunos],width=45); aluno.grid(row=1,column=0,padx=(0,20),pady=5)
        ttk.Label(panel,text="Livro").grid(row=2,column=0,sticky="w")
        livro=ttk.Combobox(panel,values=[f"{x[0]} - {x[1]}" for x in livros],width=45); livro.grid(row=3,column=0,padx=(0,20),pady=5)
        ttk.Label(panel,text="Data prevista para devolução").grid(row=4,column=0,sticky="w")
        devol=ttk.Entry(panel,width=48); devol.insert(0,(date.today()+timedelta(days=14)).isoformat()); devol.grid(row=5,column=0,pady=5)
        def registrar():
            try:
                aid=int(aluno.get().split(" - ")[0]); lid=int(livro.get().split(" - ")[0])
                self.conn.execute("INSERT INTO emprestimos(aluno_id,livro_id,data_emprestimo,data_prevista,status) VALUES(?,?,?,?,?)",
                                  (aid,lid,date.today().isoformat(),devol.get(),"Em andamento"))
                self.conn.execute("UPDATE livros SET disponivel=disponivel-1 WHERE id=?",(lid,))
                self.conn.commit(); messagebox.showinfo("Sucesso","Empréstimo registrado!"); self.show_dashboard()
            except Exception as e: messagebox.showerror("Erro",str(e))
        ttk.Button(panel,text="Confirmar empréstimo",command=registrar).grid(row=6,column=0,sticky="w",pady=20)

    def show_devolucoes(self):
        self.clear(); self.header("Devoluções", "Registre a entrega dos livros")
        cols=("ID","Aluno","Livro","Data prevista")
        tree=self.make_tree(cols)
        rows=self.conn.execute("""SELECT e.id,a.nome,l.titulo,e.data_prevista FROM emprestimos e
                                JOIN alunos a ON a.id=e.aluno_id JOIN livros l ON l.id=e.livro_id
                                WHERE e.status='Em andamento' ORDER BY e.data_prevista""").fetchall()
        for r in rows: tree.insert("", "end", values=r)
        def devolver():
            sel=tree.selection()
            if not sel: return messagebox.showwarning("Atenção","Selecione um empréstimo.")
            eid=tree.item(sel[0])["values"][0]
            lid=self.conn.execute("SELECT livro_id FROM emprestimos WHERE id=?",(eid,)).fetchone()[0]
            self.conn.execute("UPDATE emprestimos SET status='Devolvido',data_devolucao=? WHERE id=?",(date.today().isoformat(),eid))
            self.conn.execute("UPDATE livros SET disponivel=disponivel+1 WHERE id=?",(lid,))
            self.conn.commit(); messagebox.showinfo("Sucesso","Devolução registrada!"); self.show_devolucoes()
        ttk.Button(self.content,text="Registrar devolução do selecionado",command=devolver).pack(anchor="w",padx=30,pady=(0,20))

    def show_relatorios(self):
        self.clear(); self.header("Relatórios", "Informações importantes da biblioteca")
        f=tk.Frame(self.content,bg="white"); f.pack(fill="both",expand=True,padx=30,pady=20)
        rel=[
            ("Livros mais emprestados", """SELECT l.titulo,COUNT(*) AS total FROM emprestimos e JOIN livros l ON l.id=e.livro_id GROUP BY l.id ORDER BY total DESC LIMIT 10"""),
            ("Alunos com empréstimos ativos", """SELECT a.nome,COUNT(*) FROM emprestimos e JOIN alunos a ON a.id=e.aluno_id WHERE e.status='Em andamento' GROUP BY a.id ORDER BY a.nome"""),
            ("Empréstimos atrasados", """SELECT a.nome,l.titulo,e.data_prevista FROM emprestimos e JOIN alunos a ON a.id=e.aluno_id JOIN livros l ON l.id=e.livro_id WHERE e.status='Em andamento' AND e.data_prevista < date('now')""")
        ]
        for title,sql in rel:
            tk.Label(f,text=title,bg="white",font=("Arial",12,"bold")).pack(anchor="w",padx=20,pady=(18,5))
            rows=self.conn.execute(sql).fetchall()
            if rows:
                for r in rows: tk.Label(f,text=" • "+" — ".join(map(str,r)),bg="white").pack(anchor="w",padx=30)
            else: tk.Label(f,text="Nenhum registro.",bg="white",fg="#64748b").pack(anchor="w",padx=30)

    def backup_info(self):
        messagebox.showinfo("Backup","O banco de dados da biblioteca é o arquivo 'biblioteca_escolar.db'.\n\nCopie esse arquivo para um pen drive para manter uma cópia de segurança.")

if __name__ == "__main__":
    root=tk.Tk()
    app=BibliotecaApp(root)
    root.mainloop()
