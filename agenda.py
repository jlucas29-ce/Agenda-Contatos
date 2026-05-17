import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3, re, os, shutil
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR  = Path(os.path.dirname(os.path.abspath(__file__)))
DB_PATH   = BASE_DIR / "agenda.db"
FOTOS_DIR = BASE_DIR / "fotos"
FOTOS_DIR.mkdir(exist_ok=True)

# ── Banco ─────────────────────────────────────────────────────────────────────
def init_db():
    c = sqlite3.connect(DB_PATH)
    c.execute("""CREATE TABLE IF NOT EXISTS contatos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL, email TEXT,
        endereco TEXT, cpf TEXT, telefone TEXT, foto TEXT)""")
    c.commit(); c.close()

def db_all(filtro=""):
    c = sqlite3.connect(DB_PATH)
    q = "SELECT id,nome,email,endereco,cpf,telefone,foto FROM contatos"
    if filtro:
        rows = c.execute(q+" WHERE nome LIKE ? OR email LIKE ? OR cpf LIKE ? ORDER BY nome",
                         (f"%{filtro}%",)*3).fetchall()
    else:
        rows = c.execute(q+" ORDER BY nome").fetchall()
    c.close(); return rows

def db_save(nome, email, endereco, cpf, telefone, foto, cid=None):
    c = sqlite3.connect(DB_PATH)
    if cid:
        c.execute("UPDATE contatos SET nome=?,email=?,endereco=?,cpf=?,telefone=?,foto=? WHERE id=?",
                  (nome,email,endereco,cpf,telefone,foto,cid))
    else:
        c.execute("INSERT INTO contatos(nome,email,endereco,cpf,telefone,foto) VALUES(?,?,?,?,?,?)",
                  (nome,email,endereco,cpf,telefone,foto))
    c.commit(); c.close()

def db_del(cid, foto):
    c = sqlite3.connect(DB_PATH)
    c.execute("DELETE FROM contatos WHERE id=?", (cid,))
    c.commit(); c.close()
    if foto and os.path.exists(foto):
        try: os.remove(foto)
        except: pass

def copy_foto(src, nome):
    ext = Path(src).suffix.lower()
    dst = FOTOS_DIR / f"{re.sub(r'[^\\w]','_',nome)}_{abs(hash(src))}{ext}"
    shutil.copy2(src, dst); return str(dst)

# ── Cores ─────────────────────────────────────────────────────────────────────
BG      = "#f1f5f9"
CARD    = "#ffffff"
BORDER  = "#e2e8f0"
PRIMARY = "#3b82f6"
PRIM_D  = "#2563eb"
SUCCESS = "#16a34a"
DANGER  = "#ef4444"
WARN    = "#f59e0b"
HEADER  = "#1e293b"
TEXT    = "#1e293b"
MUTED   = "#94a3b8"
WHITE   = "#ffffff"

FB = ("Segoe UI", 10, "bold")
FN = ("Segoe UI", 10)
FL = ("Segoe UI", 9, "bold")
FT = ("Segoe UI", 20, "bold")
FS = ("Segoe UI", 9)

def Btn(p, t, bg, hv, cmd, **kw):
    b = tk.Button(p, text=t, font=FB, bg=bg, fg=WHITE, relief="flat",
                  cursor="hand2", activebackground=hv, activeforeground=WHITE,
                  command=cmd, **kw)
    b.bind("<Enter>", lambda e: b.config(bg=hv))
    b.bind("<Leave>", lambda e: b.config(bg=bg))
    return b

# ══════════════════════════════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Agenda de Contatos")
        self.geometry("860x580")
        self.minsize(760, 500)
        self.configure(bg=BG)
        init_db()
        self._build()
        self._load()

    # ── Tela principal ────────────────────────────────────────────────────────
    def _build(self):
        # Topbar
        top = tk.Frame(self, bg=HEADER, pady=14)
        top.pack(fill="x")

        tk.Label(top, text="📒  Agenda de Contatos", font=("Segoe UI",16,"bold"),
                 bg=HEADER, fg=WHITE).pack(side="left", padx=20)

        right = tk.Frame(top, bg=HEADER)
        right.pack(side="right", padx=20)

        # Busca
        busca_frame = tk.Frame(right, bg="#334155",
                                highlightbackground="#475569", highlightthickness=1)
        busca_frame.pack(side="left", padx=(0,12))
        tk.Label(busca_frame, text="🔍", bg="#334155", fg=WHITE,
                 font=("Segoe UI",11)).pack(side="left", padx=6)
        self.var_busca = tk.StringVar()
        self.var_busca.trace_add("write", lambda *a: self._load())
        tk.Entry(busca_frame, textvariable=self.var_busca, font=FN,
                 bg="#334155", fg=WHITE, relief="flat", width=20,
                 insertbackground=WHITE).pack(side="left", ipady=6, pady=4, padx=(0,8))

        Btn(right, "＋  Novo Contato", PRIMARY, PRIM_D,
            self._open_form).pack(side="left", padx=4, pady=2, ipady=4)

        # Info bar
        info = tk.Frame(self, bg=BG)
        info.pack(fill="x", padx=20, pady=(14,6))
        self.lbl_total = tk.Label(info, text="", font=FS, bg=BG, fg=MUTED)
        self.lbl_total.pack(side="left")

        # Tabela
        table_frame = tk.Frame(self, bg=CARD,
                                highlightbackground=BORDER, highlightthickness=1)
        table_frame.pack(fill="both", expand=True, padx=20, pady=(0,16))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("A.Treeview", background=CARD, foreground=TEXT,
                         fieldbackground=CARD, font=("Segoe UI",10),
                         rowheight=44, borderwidth=0)
        style.configure("A.Treeview.Heading", background=HEADER,
                         foreground=WHITE, font=("Segoe UI",10,"bold"),
                         relief="flat", padding=10)
        style.map("A.Treeview",
                  background=[("selected","#dbeafe")],
                  foreground=[("selected",TEXT)])

        cols = ("foto","nome","email","telefone","cpf","endereco")
        self.tree = ttk.Treeview(table_frame, columns=cols,
                                  show="headings", style="A.Treeview")

        self.tree.heading("foto",     text="")
        self.tree.heading("nome",     text="Nome")
        self.tree.heading("email",    text="E-mail")
        self.tree.heading("telefone", text="Telefone")
        self.tree.heading("cpf",      text="CPF")
        self.tree.heading("endereco", text="Endereço")

        self.tree.column("foto",     width=44,  anchor="center", stretch=False)
        self.tree.column("nome",     width=160, anchor="w")
        self.tree.column("email",    width=160, anchor="w")
        self.tree.column("telefone", width=110, anchor="w")
        self.tree.column("cpf",      width=120, anchor="w")
        self.tree.column("endereco", width=160, anchor="w")

        sb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.tree.bind("<Double-Button-1>", lambda e: self._open_form(edit=True))

        # Botões ação
        act = tk.Frame(self, bg=BG)
        act.pack(fill="x", padx=20, pady=(0,16))
        Btn(act, "✏️  Editar selecionado", WARN, "#d97706",
            lambda: self._open_form(edit=True), padx=14, pady=7).pack(side="left", padx=(0,8))
        Btn(act, "🗑️  Excluir selecionado", DANGER, "#dc2626",
            self._excluir, padx=14, pady=7).pack(side="left")
        tk.Label(act, text="Duplo clique para editar",
                 font=FS, bg=BG, fg=MUTED).pack(side="right")

    # ── Carregar ──────────────────────────────────────────────────────────────
    def _load(self):
        for r in self.tree.get_children(): self.tree.delete(r)
        filtro = self.var_busca.get()
        data   = db_all(filtro)
        for c in data:
            cid,nome,email,endereco,cpf,telefone,foto = c
            icone = "📷" if foto and os.path.exists(foto) else "👤"
            self.tree.insert("","end", iid=str(cid),
                              values=(icone,nome,email or "",telefone or "",cpf or "",endereco or ""),
                              tags=(foto or "",))
        self.lbl_total.config(text=f"{len(data)} contato(s) salvos")

    # ── Excluir ───────────────────────────────────────────────────────────────
    def _excluir(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Atenção","Selecione um contato para excluir."); return
        nome = self.tree.item(sel[0],"values")[1]
        foto = (self.tree.item(sel[0],"tags") or ("",))[0]
        if messagebox.askyesno("Confirmar",f"Excluir '{nome}'?"):
            db_del(int(sel[0]), foto)
            self._load()

    # ── Abrir formulário (janela modal) ───────────────────────────────────────
    def _open_form(self, edit=False):
        cid = None; row = None
        if edit:
            sel = self.tree.selection()
            if not sel:
                messagebox.showinfo("Atenção","Selecione um contato para editar."); return
            cid = int(sel[0])
            all_ = db_all()
            row  = next((x for x in all_ if x[0]==cid), None)

        FormDialog(self, row, self._load)


# ══════════════════════════════════════════════════════════════════════════════
class FormDialog(tk.Toplevel):
    def __init__(self, master, row, on_save):
        super().__init__(master)
        self.on_save   = on_save
        self._foto_path = None
        self._foto_img  = None
        self._cpf_busy  = False

        is_edit = row is not None
        self.cid = row[0] if is_edit else None
        self._foto_atual = row[6] if is_edit else None

        self.title("Editar Contato" if is_edit else "Novo Contato")
        self.geometry("460x640")
        self.resizable(False, False)
        self.configure(bg=CARD)
        self.grab_set()
        self.focus_force()

        self._build(row)

        # Preencher campos se edição
        if is_edit:
            self.v_nome.set(row[1] or "")
            self.v_email.set(row[2] or "")
            self.v_end.set(row[3] or "")
            self.v_cpf.set(row[4] or "")
            self.v_tel.set(row[5] or "")
            self._foto_path = row[6]
            self._draw_avatar(row[6])

    def _build(self, row):
        # Cabeçalho
        head = tk.Frame(self, bg=HEADER, pady=16)
        head.pack(fill="x")
        titulo = "Editar Contato" if row else "Novo Contato"
        tk.Label(head, text=titulo, font=("Segoe UI",14,"bold"),
                 bg=HEADER, fg=WHITE).pack()

        # Scroll frame
        canvas = tk.Canvas(self, bg=CARD, highlightthickness=0)
        scroll = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scroll_frame = tk.Frame(canvas, bg=CARD)
        self.scroll_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        f = self.scroll_frame

        # Foto
        foto_area = tk.Frame(f, bg=CARD)
        foto_area.pack(pady=20)

        self.foto_cv = tk.Canvas(foto_area, width=110, height=110,
                                  bg="#e2e8f0", relief="flat",
                                  highlightbackground=BORDER, highlightthickness=2,
                                  cursor="hand2")
        self.foto_cv.pack()
        self.foto_cv.bind("<Button-1>", lambda e: self._choose_foto())
        self._draw_avatar()

        tk.Label(foto_area, text="Clique na imagem para adicionar foto",
                 font=FS, bg=CARD, fg=MUTED).pack(pady=(6,0))

        bf = tk.Frame(foto_area, bg=CARD)
        bf.pack(pady=6)
        Btn(bf, "📷  Escolher Foto", "#64748b", "#475569",
            self._choose_foto, padx=10, pady=5).pack(side="left", padx=4)
        Btn(bf, "✕  Remover", DANGER, "#dc2626",
            self._remove_foto, padx=10, pady=5).pack(side="left", padx=4)

        tk.Frame(f, bg=BORDER, height=1).pack(fill="x", padx=20, pady=(0,16))

        # Variáveis
        self.v_nome  = tk.StringVar()
        self.v_email = tk.StringVar()
        self.v_tel   = tk.StringVar()
        self.v_end   = tk.StringVar()
        self.v_cpf   = tk.StringVar()

        # Campos
        self._field(f, "Nome *", self.v_nome)
        self._field(f, "E-mail", self.v_email)
        self._field(f, "Telefone", self.v_tel)
        self._field(f, "Endereço", self.v_end)

        # CPF com máscara
        cpf_f = tk.Frame(f, bg=CARD)
        cpf_f.pack(fill="x", padx=24, pady=(0,12))
        tk.Label(cpf_f, text="CPF", font=FL, bg=CARD, fg=MUTED, anchor="w").pack(fill="x")
        self.e_cpf = tk.Entry(cpf_f, textvariable=self.v_cpf, font=("Segoe UI",11),
                               bg="#f8fafc", fg=TEXT, relief="flat",
                               highlightbackground=BORDER, highlightthickness=1)
        self.e_cpf.pack(fill="x", ipady=9, pady=(3,0))
        self.e_cpf.bind("<KeyRelease>", self._mask_cpf)

        # Botão salvar
        bot = tk.Frame(f, bg=CARD)
        bot.pack(fill="x", padx=24, pady=(8,24))
        Btn(bot, "💾  Salvar Contato", SUCCESS, "#15803d",
            self._save, padx=16, pady=11).pack(fill="x", pady=(0,8))
        Btn(bot, "Cancelar", "#e2e8f0", BORDER,
            self.destroy, padx=16, pady=11).config(fg=TEXT, activeforeground=TEXT)
        tk.Button(bot, text="Cancelar", font=FB, bg="#e2e8f0", fg=TEXT,
                  relief="flat", cursor="hand2", command=self.destroy,
                  padx=16, pady=11).pack(fill="x")

    def _field(self, parent, label, var):
        f = tk.Frame(parent, bg=CARD)
        f.pack(fill="x", padx=24, pady=(0,12))
        tk.Label(f, text=label, font=FL, bg=CARD, fg=MUTED, anchor="w").pack(fill="x")
        e = tk.Entry(f, textvariable=var, font=("Segoe UI",11),
                     bg="#f8fafc", fg=TEXT, relief="flat",
                     highlightbackground=BORDER, highlightthickness=1)
        e.pack(fill="x", ipady=9, pady=(3,0))
        return e

    # ── Foto ──────────────────────────────────────────────────────────────────
    def _draw_avatar(self, path=None):
        self.foto_cv.delete("all")
        if path and os.path.exists(str(path)):
            try:
                from PIL import Image, ImageTk, ImageDraw
                img  = Image.open(path).resize((110,110), Image.LANCZOS)
                mask = Image.new("L",(110,110),0)
                ImageDraw.Draw(mask).ellipse((0,0,110,110),fill=255)
                out  = Image.new("RGBA",(110,110),(0,0,0,0))
                out.paste(img, mask=mask)
                self._foto_img = ImageTk.PhotoImage(out)
                self.foto_cv.create_image(55,55,image=self._foto_img)
                return
            except ImportError:
                self.foto_cv.create_rectangle(0,0,110,110,fill=PRIMARY,outline="")
                self.foto_cv.create_text(55,55,text="📷",font=("Segoe UI",30))
                return
            except: pass
        self.foto_cv.create_oval(6,6,104,104,fill="#cbd5e1",outline="")
        self.foto_cv.create_text(55,48,text="👤",font=("Segoe UI",32))
        self.foto_cv.create_text(55,82,text="Adicionar foto",font=FS,fill=MUTED)

    def _choose_foto(self):
        p = filedialog.askopenfilename(
            title="Escolher foto",
            filetypes=[("Imagens","*.png *.jpg *.jpeg *.bmp *.gif *.webp"),
                       ("Todos","*.*")])
        if p:
            self._foto_path = p
            self._draw_avatar(p)

    def _remove_foto(self):
        self._foto_path = None
        self._foto_atual = None
        self._draw_avatar()

    # ── CPF máscara ───────────────────────────────────────────────────────────
    def _mask_cpf(self, event=None):
        if self._cpf_busy: return
        self._cpf_busy = True
        try:
            pos  = self.e_cpf.index(tk.INSERT)
            raw  = self.v_cpf.get()
            nums = re.sub(r"\D","",raw)[:11]
            if   len(nums)>9: fmt=f"{nums[:3]}.{nums[3:6]}.{nums[6:9]}-{nums[9:]}"
            elif len(nums)>6: fmt=f"{nums[:3]}.{nums[3:6]}.{nums[6:]}"
            elif len(nums)>3: fmt=f"{nums[:3]}.{nums[3:]}"
            else:             fmt=nums
            if fmt != raw:
                self.v_cpf.set(fmt)
                np = min(pos+(len(fmt)-len(raw)), len(fmt))
                self.e_cpf.icursor(np)
        finally:
            self._cpf_busy = False

    # ── Salvar ────────────────────────────────────────────────────────────────
    def _save(self):
        nome     = self.v_nome.get().strip()
        email    = self.v_email.get().strip()
        telefone = self.v_tel.get().strip()
        endereco = self.v_end.get().strip()
        cpf      = self.v_cpf.get().strip()

        if not nome:
            messagebox.showwarning("Campo obrigatório","Nome é obrigatório.",parent=self)
            return
        if email and not re.match(r'^[\w\.-]+@[\w\.-]+\.\w{2,}$', email):
            messagebox.showwarning("E-mail inválido","Informe um e-mail válido.",parent=self)
            return
        nums = re.sub(r"\D","",cpf)
        if cpf and len(nums) != 11:
            messagebox.showwarning("CPF inválido","O CPF deve ter 11 dígitos.",parent=self)
            return

        foto_salva = self._foto_atual
        if self._foto_path and self._foto_path != self._foto_atual:
            foto_salva = copy_foto(self._foto_path, nome)
        elif self._foto_path is None:
            foto_salva = None

        db_save(nome, email, endereco, cpf, telefone, foto_salva, self.cid)
        self.on_save()
        self.destroy()

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    App().mainloop()