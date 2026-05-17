import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import re
import os
import shutil
import base64
from pathlib import Path

# ── Caminhos ─────────────────────────────────────────────────────────────────
BASE_DIR   = Path(os.path.dirname(os.path.abspath(__file__)))
DB_PATH    = BASE_DIR / "agenda.db"
FOTOS_DIR  = BASE_DIR / "fotos"
FOTOS_DIR.mkdir(exist_ok=True)

# ── Banco de dados ────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS contatos (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            nome     TEXT NOT NULL,
            email    TEXT,
            endereco TEXT,
            cpf      TEXT,
            telefone TEXT,
            foto     TEXT
        )
    """)
    # Migração: adicionar colunas se não existirem
    try:
        conn.execute("ALTER TABLE contatos ADD COLUMN telefone TEXT")
    except: pass
    try:
        conn.execute("ALTER TABLE contatos ADD COLUMN foto TEXT")
    except: pass
    conn.commit()
    conn.close()

def buscar_todos(filtro=""):
    conn = sqlite3.connect(DB_PATH)
    if filtro:
        rows = conn.execute(
            "SELECT id,nome,email,endereco,cpf,telefone,foto FROM contatos "
            "WHERE nome LIKE ? OR email LIKE ? OR cpf LIKE ? ORDER BY nome",
            (f"%{filtro}%", f"%{filtro}%", f"%{filtro}%")
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id,nome,email,endereco,cpf,telefone,foto FROM contatos ORDER BY nome"
        ).fetchall()
    conn.close()
    return rows

def salvar_contato(nome, email, endereco, cpf, telefone, foto, contato_id=None):
    conn = sqlite3.connect(DB_PATH)
    if contato_id:
        conn.execute(
            "UPDATE contatos SET nome=?,email=?,endereco=?,cpf=?,telefone=?,foto=? WHERE id=?",
            (nome, email, endereco, cpf, telefone, foto, contato_id)
        )
    else:
        conn.execute(
            "INSERT INTO contatos (nome,email,endereco,cpf,telefone,foto) VALUES (?,?,?,?,?,?)",
            (nome, email, endereco, cpf, telefone, foto)
        )
    conn.commit()
    conn.close()

def excluir_contato(contato_id, foto_path):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM contatos WHERE id=?", (contato_id,))
    conn.commit()
    conn.close()
    if foto_path and os.path.exists(foto_path):
        try: os.remove(foto_path)
        except: pass

def copiar_foto(src_path, contato_nome):
    ext  = Path(src_path).suffix.lower()
    nome_safe = re.sub(r'[^\w]', '_', contato_nome)
    dst  = FOTOS_DIR / f"{nome_safe}_{id(src_path)}{ext}"
    shutil.copy2(src_path, dst)
    return str(dst)

# ── Validações ────────────────────────────────────────────────────────────────
def validar_email(email):
    return not email or bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w{2,}$', email))

def validar_cpf(cpf):
    return not cpf or len(re.sub(r'\D', '', cpf)) == 11

# ── Tema ──────────────────────────────────────────────────────────────────────
BG          = "#f8fafc"
SIDEBAR     = "#1e293b"
SIDEBAR_SEL = "#334155"
HEADER      = "#0f172a"
PRIMARY     = "#3b82f6"
PRIMARY_D   = "#2563eb"
SUCCESS     = "#22c55e"
DANGER      = "#ef4444"
WARNING     = "#f59e0b"
CARD        = "#ffffff"
BORDER      = "#e2e8f0"
TEXT        = "#1e293b"
MUTED       = "#94a3b8"
WHITE       = "#ffffff"

F_TITLE  = ("Segoe UI", 22, "bold")
F_HEAD   = ("Segoe UI", 13, "bold")
F_LABEL  = ("Segoe UI", 9,  "bold")
F_ENTRY  = ("Segoe UI", 11)
F_BTN    = ("Segoe UI", 10, "bold")
F_SMALL  = ("Segoe UI", 9)
F_MONO   = ("Consolas",  10)

# ── Helpers de UI ─────────────────────────────────────────────────────────────
def btn(parent, text, color, hover, cmd, **kw):
    b = tk.Button(parent, text=text, font=F_BTN, bg=color, fg=WHITE,
                  relief="flat", cursor="hand2", activebackground=hover,
                  activeforeground=WHITE, command=cmd, **kw)
    b.bind("<Enter>", lambda e: b.config(bg=hover))
    b.bind("<Leave>", lambda e: b.config(bg=color))
    return b

def entry_field(parent, label, var, show=None):
    f = tk.Frame(parent, bg=CARD)
    f.pack(fill="x", padx=20, pady=(0, 12))
    tk.Label(f, text=label, font=F_LABEL, bg=CARD, fg=MUTED, anchor="w").pack(fill="x")
    e = tk.Entry(f, textvariable=var, font=F_ENTRY, bg="#f1f5f9", fg=TEXT,
                 relief="flat", highlightbackground=BORDER,
                 highlightthickness=1, show=show or "")
    e.pack(fill="x", ipady=8, pady=(3,0))
    return e

# ══════════════════════════════════════════════════════════════════════════════
class AgendaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Agenda de Contatos")
        self.geometry("1050x680")
        self.minsize(900, 600)
        self.configure(bg=BG)

        self._foto_path    = None   # caminho da foto no formulário
        self._foto_img     = None   # referência PhotoImage do preview
        self._editando_id  = None
        self._editando_foto_atual = None

        init_db()
        self._build()
        self._carregar()

    # ── Layout principal ──────────────────────────────────────────────────────
    def _build(self):
        # Sidebar esquerda
        self.sidebar = tk.Frame(self, bg=SIDEBAR, width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self._build_sidebar()

        # Área principal
        self.main = tk.Frame(self, bg=BG)
        self.main.pack(side="left", fill="both", expand=True)
        self._build_header()
        self._build_content()

    def _build_sidebar(self):
        # Logo
        logo = tk.Frame(self.sidebar, bg=PRIMARY, pady=24)
        logo.pack(fill="x")
        tk.Label(logo, text="📒", font=("Segoe UI", 28), bg=PRIMARY, fg=WHITE).pack()
        tk.Label(logo, text="Agenda", font=("Segoe UI", 14, "bold"),
                 bg=PRIMARY, fg=WHITE).pack()
        tk.Label(logo, text="de Contatos", font=("Segoe UI", 10),
                 bg=PRIMARY, fg="#bfdbfe").pack()

        tk.Frame(self.sidebar, bg=SIDEBAR_SEL, height=1).pack(fill="x", pady=10)

        # Estatísticas
        self.lbl_total_side = tk.Label(self.sidebar, text="0 contatos",
                                        font=("Segoe UI", 10), bg=SIDEBAR, fg=MUTED)
        self.lbl_total_side.pack(pady=(0, 20))

        tk.Frame(self.sidebar, bg=SIDEBAR_SEL, height=1).pack(fill="x")

        # Menu
        menus = [("➕  Novo Contato", self._novo), ("📋  Ver Todos", self._carregar)]
        for label, cmd in menus:
            b = tk.Button(self.sidebar, text=label, font=("Segoe UI", 10),
                          bg=SIDEBAR, fg=WHITE, relief="flat", anchor="w",
                          padx=20, pady=12, cursor="hand2",
                          activebackground=SIDEBAR_SEL, activeforeground=WHITE,
                          command=cmd)
            b.pack(fill="x")
            b.bind("<Enter>", lambda e, b=b: b.config(bg=SIDEBAR_SEL))
            b.bind("<Leave>", lambda e, b=b: b.config(bg=SIDEBAR))

        # Info na base
        tk.Label(self.sidebar, text="v2.0 — Com fotos", font=F_SMALL,
                 bg=SIDEBAR, fg="#475569").place(relx=0.5, rely=0.97, anchor="center")

    def _build_header(self):
        header = tk.Frame(self.main, bg=CARD, pady=16,
                          highlightbackground=BORDER, highlightthickness=1)
        header.pack(fill="x")

        left = tk.Frame(header, bg=CARD)
        left.pack(side="left", padx=24)
        self.lbl_titulo = tk.Label(left, text="Meus Contatos",
                                    font=F_TITLE, bg=CARD, fg=TEXT)
        self.lbl_titulo.pack(anchor="w")
        self.lbl_sub = tk.Label(left, text="Gerencie seus contatos com foto",
                                 font=F_SMALL, bg=CARD, fg=MUTED)
        self.lbl_sub.pack(anchor="w")

        # Busca
        right = tk.Frame(header, bg=CARD)
        right.pack(side="right", padx=24)
        self.var_busca = tk.StringVar()
        self.var_busca.trace_add("write", lambda *a: self._carregar())
        busca = tk.Frame(right, bg="#f1f5f9",
                         highlightbackground=BORDER, highlightthickness=1)
        busca.pack()
        tk.Label(busca, text="🔍", bg="#f1f5f9", font=("Segoe UI",11)).pack(side="left",padx=8)
        tk.Entry(busca, textvariable=self.var_busca, font=F_ENTRY,
                 bg="#f1f5f9", fg=TEXT, relief="flat", width=22).pack(side="left", ipady=7, pady=4, padx=(0,8))

    def _build_content(self):
        content = tk.Frame(self.main, bg=BG)
        content.pack(fill="both", expand=True, padx=20, pady=20)

        # Coluna esquerda — formulário
        self.frame_form = tk.Frame(content, bg=BG, width=320)
        self.frame_form.pack(side="left", fill="y", padx=(0,16))
        self.frame_form.pack_propagate(False)
        self._build_form()

        # Coluna direita — lista
        frame_lista = tk.Frame(content, bg=BG)
        frame_lista.pack(side="left", fill="both", expand=True)
        self._build_lista(frame_lista)

    # ── Formulário ────────────────────────────────────────────────────────────
    def _build_form(self):
        # Cabeçalho do form
        head = tk.Frame(self.frame_form, bg=BG)
        head.pack(fill="x", pady=(0,12))
        self.lbl_form_titulo = tk.Label(head, text="Novo Contato",
                                         font=F_HEAD, bg=BG, fg=TEXT)
        self.lbl_form_titulo.pack(side="left")

        # Card do form
        card = tk.Frame(self.frame_form, bg=CARD,
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x")

        # ── Foto ──────────────────────────────────────────────────────────────
        foto_area = tk.Frame(card, bg=CARD)
        foto_area.pack(pady=20)

        self.foto_canvas = tk.Canvas(foto_area, width=100, height=100,
                                      bg="#e2e8f0", relief="flat",
                                      highlightbackground=BORDER, highlightthickness=2,
                                      cursor="hand2")
        self.foto_canvas.pack()
        self.foto_canvas.bind("<Button-1>", lambda e: self._escolher_foto())
        self._desenhar_avatar()

        tk.Label(foto_area, text="Clique para adicionar foto",
                 font=F_SMALL, bg=CARD, fg=MUTED).pack(pady=(6,0))

        btn_foto = tk.Frame(foto_area, bg=CARD)
        btn_foto.pack(pady=4)
        btn(btn_foto, "📷 Escolher Foto", "#64748b", "#475569",
            self._escolher_foto, padx=10, pady=4).pack(side="left", padx=2)
        btn(btn_foto, "✕", DANGER, "#dc2626",
            self._remover_foto, padx=8, pady=4).pack(side="left", padx=2)

        tk.Frame(card, bg=BORDER, height=1).pack(fill="x", padx=20, pady=(0,12))

        # ── Campos ────────────────────────────────────────────────────────────
        self.var_nome     = tk.StringVar()
        self.var_email    = tk.StringVar()
        self.var_telefone = tk.StringVar()
        self.var_endereco = tk.StringVar()
        self.var_cpf      = tk.StringVar()

        self.var_cpf.trace_add("write", self._formatar_cpf)

        entry_field(card, "Nome *", self.var_nome)
        entry_field(card, "E-mail", self.var_email)
        entry_field(card, "Telefone", self.var_telefone)
        entry_field(card, "Endereço", self.var_endereco)
        entry_field(card, "CPF", self.var_cpf)

        # ── Botões ────────────────────────────────────────────────────────────
        btns = tk.Frame(card, bg=CARD)
        btns.pack(fill="x", padx=20, pady=(4,16))

        self.btn_salvar = btn(btns, "💾  Salvar", PRIMARY, PRIMARY_D,
                               self._salvar, padx=14, pady=9)
        self.btn_salvar.pack(fill="x", pady=(0,6))

        self.btn_cancelar = btn(btns, "✕  Cancelar", "#e2e8f0", BORDER,
                                 self._cancelar, padx=14, pady=9)
        self.btn_cancelar.config(fg=TEXT, activeforeground=TEXT)
        self.btn_cancelar.pack(fill="x")
        self.btn_cancelar.pack_forget()

        # Status
        self.lbl_status = tk.Label(self.frame_form, text="", font=F_SMALL, bg=BG)
        self.lbl_status.pack(anchor="w", pady=(8,0))

    # ── Lista de contatos ─────────────────────────────────────────────────────
    def _build_lista(self, parent):
        # Toolbar
        toolbar = tk.Frame(parent, bg=BG)
        toolbar.pack(fill="x", pady=(0,10))

        self.lbl_total = tk.Label(toolbar, text="", font=F_SMALL, bg=BG, fg=MUTED)
        self.lbl_total.pack(side="right")

        # Tabela
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("A.Treeview", background=CARD, foreground=TEXT,
                         fieldbackground=CARD, font=("Segoe UI",10),
                         rowheight=48, borderwidth=0)
        style.configure("A.Treeview.Heading", background=HEADER, foreground=WHITE,
                         font=("Segoe UI",10,"bold"), relief="flat", padding=10)
        style.map("A.Treeview",
                  background=[("selected","#dbeafe")],
                  foreground=[("selected", TEXT)])

        cols = ("foto","nome","email","telefone","cpf")
        self.tree = ttk.Treeview(parent, columns=cols, show="headings",
                                  style="A.Treeview", selectmode="browse")

        self.tree.heading("foto",     text="")
        self.tree.heading("nome",     text="Nome")
        self.tree.heading("email",    text="E-mail")
        self.tree.heading("telefone", text="Telefone")
        self.tree.heading("cpf",      text="CPF")

        self.tree.column("foto",     width=52,  anchor="center", stretch=False)
        self.tree.column("nome",     width=180, anchor="w")
        self.tree.column("email",    width=170, anchor="w")
        self.tree.column("telefone", width=120, anchor="w")
        self.tree.column("cpf",      width=120, anchor="w")

        scroll = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="left", fill="y")

        self.tree.bind("<Double-Button-1>", lambda e: self._editar())

        # Ações
        acoes = tk.Frame(parent, bg=BG)
        acoes.pack(fill="x", pady=(10,0))

        btn(acoes, "✏️  Editar", WARNING, "#d97706", self._editar,
            padx=14, pady=8).pack(side="left", padx=(0,8))
        btn(acoes, "🗑️  Excluir", DANGER, "#dc2626", self._excluir,
            padx=14, pady=8).pack(side="left")
        tk.Label(acoes, text="Dica: duplo clique para editar",
                 font=F_SMALL, bg=BG, fg=MUTED).pack(side="right")

        # Mapa de imagens (evita garbage collection)
        self._imgs = {}

    # ── Foto helpers ──────────────────────────────────────────────────────────
    def _desenhar_avatar(self, img_path=None):
        self.foto_canvas.delete("all")
        if img_path and os.path.exists(img_path):
            try:
                from PIL import Image, ImageTk, ImageDraw
                img = Image.open(img_path).resize((100,100), Image.LANCZOS)
                # Máscara circular
                mask = Image.new("L", (100,100), 0)
                ImageDraw.Draw(mask).ellipse((0,0,100,100), fill=255)
                img.putalpha(mask)
                self._foto_preview = ImageTk.PhotoImage(img)
                self.foto_canvas.create_image(50,50, image=self._foto_preview)
                return
            except ImportError:
                pass
            except Exception:
                pass
        # Avatar padrão
        self.foto_canvas.create_oval(5,5,95,95, fill="#cbd5e1", outline="")
        self.foto_canvas.create_text(50,42, text="👤", font=("Segoe UI",30))
        self.foto_canvas.create_text(50,75, text="Foto", font=F_SMALL, fill=MUTED)

    def _escolher_foto(self):
        path = filedialog.askopenfilename(
            title="Escolher foto",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.gif *.bmp *.webp")]
        )
        if path:
            self._foto_path = path
            self._desenhar_avatar(path)

    def _remover_foto(self):
        self._foto_path = None
        self._editando_foto_atual = None
        self._desenhar_avatar()

    # ── CPF auto-format ───────────────────────────────────────────────────────
    def _formatar_cpf(self, *args):
        val  = self.var_cpf.get()
        nums = re.sub(r'\D', '', val)[:11]
        fmt  = nums
        if len(nums) > 9:   fmt = f"{nums[:3]}.{nums[3:6]}.{nums[6:9]}-{nums[9:]}"
        elif len(nums) > 6: fmt = f"{nums[:3]}.{nums[3:6]}.{nums[6:]}"
        elif len(nums) > 3: fmt = f"{nums[:3]}.{nums[3:]}"
        if fmt != val:
            tr = self.var_cpf.trace_info()
            if tr: self.var_cpf.trace_remove("write", tr[0][1])
            self.var_cpf.set(fmt)
            self.var_cpf.trace_add("write", self._formatar_cpf)

    # ── Carregar lista ────────────────────────────────────────────────────────
    def _carregar(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        self._imgs.clear()

        filtro   = self.var_busca.get() if hasattr(self,"var_busca") else ""
        contatos = buscar_todos(filtro)

        for c in contatos:
            cid, nome, email, endereco, cpf, telefone, foto = c
            # Ícone de foto
            icone = "📷" if foto and os.path.exists(foto) else "👤"
            self.tree.insert("", "end", iid=str(cid),
                              values=(icone, nome, email or "", telefone or "", cpf or ""),
                              tags=(foto or "",))

        total = len(contatos)
        self.lbl_total.config(text=f"{total} contato(s)")
        if hasattr(self, "lbl_total_side"):
            self.lbl_total_side.config(text=f"{total} contato(s)")

    # ── Limpar form ───────────────────────────────────────────────────────────
    def _limpar(self):
        self.var_nome.set("")
        self.var_email.set("")
        self.var_telefone.set("")
        self.var_endereco.set("")
        self.var_cpf.set("")
        self._foto_path = None
        self._editando_id = None
        self._editando_foto_atual = None
        self._desenhar_avatar()
        self.btn_salvar.config(text="💾  Salvar")
        self.btn_cancelar.pack_forget()
        self.lbl_form_titulo.config(text="Novo Contato")
        self.lbl_status.config(text="")

    def _novo(self):
        self._limpar()

    def _cancelar(self):
        self._limpar()

    # ── Salvar ────────────────────────────────────────────────────────────────
    def _salvar(self):
        nome     = self.var_nome.get().strip()
        email    = self.var_email.get().strip()
        telefone = self.var_telefone.get().strip()
        endereco = self.var_endereco.get().strip()
        cpf      = self.var_cpf.get().strip()

        if not nome:
            messagebox.showwarning("Campo obrigatório", "O campo Nome é obrigatório.")
            return
        if not validar_email(email):
            messagebox.showwarning("E-mail inválido", "Informe um e-mail válido.")
            return
        if not validar_cpf(cpf):
            messagebox.showwarning("CPF inválido", "O CPF deve ter 11 dígitos.")
            return

        # Processar foto
        foto_salva = self._editando_foto_atual
        if self._foto_path and self._foto_path != self._editando_foto_atual:
            foto_salva = copiar_foto(self._foto_path, nome)

        salvar_contato(nome, email, endereco, cpf, telefone, foto_salva, self._editando_id)

        msg = "atualizado" if self._editando_id else "salvo"
        self.lbl_status.config(text=f"✅ Contato {msg} com sucesso!", fg=SUCCESS)
        self._limpar()
        self._carregar()

    # ── Editar ────────────────────────────────────────────────────────────────
    def _editar(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Atenção", "Selecione um contato para editar.")
            return

        cid = int(sel[0])
        contatos = buscar_todos()
        c = next((x for x in contatos if x[0] == cid), None)
        if not c: return

        cid, nome, email, endereco, cpf, telefone, foto = c
        self._editando_id = cid
        self._editando_foto_atual = foto

        self.var_nome.set(nome or "")
        self.var_email.set(email or "")
        self.var_telefone.set(telefone or "")
        self.var_endereco.set(endereco or "")
        self.var_cpf.set(cpf or "")
        self._foto_path = foto
        self._desenhar_avatar(foto)

        self.lbl_form_titulo.config(text="Editar Contato")
        self.btn_salvar.config(text="💾  Atualizar")
        self.btn_cancelar.pack(fill="x")
        self.lbl_status.config(text=f"✏️  Editando: {nome}", fg=WARNING)

    # ── Excluir ───────────────────────────────────────────────────────────────
    def _excluir(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Atenção", "Selecione um contato para excluir.")
            return

        vals = self.tree.item(sel[0], "values")
        nome = vals[1]
        foto = self.tree.item(sel[0], "tags")[0] if self.tree.item(sel[0], "tags") else ""

        if messagebox.askyesno("Confirmar", f"Excluir o contato '{nome}'?"):
            excluir_contato(int(sel[0]), foto)
            self.lbl_status.config(text=f"🗑️  '{nome}' excluído.", fg=DANGER)
            self._carregar()

# ── Iniciar ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        from PIL import Image
        PIL_OK = True
    except ImportError:
        PIL_OK = False

    app = AgendaApp()

    if not PIL_OK:
        def show_pil_tip():
            if messagebox.askyesno(
                "Dica — Fotos em círculo",
                "Para exibir fotos em formato circular instale o Pillow:\n\n"
                "pip install Pillow\n\n"
                "Deseja continuar sem ele? (fotos ainda funcionam)"
            ):
                pass
        app.after(500, show_pil_tip)

    app.mainloop()
