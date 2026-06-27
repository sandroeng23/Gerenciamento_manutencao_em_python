#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mini SAP PM - versão web (Flask + SQLite)
"""
import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

APP_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(APP_DIR, "sap_pm.db")

app = Flask(__name__, template_folder=os.path.join(APP_DIR, "templates"))
app.secret_key = "mini-sap-pm-local"
app.config["TEMPLATES_AUTO_RELOAD"] = True


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS equipamento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nome TEXT NOT NULL,
            tipo TEXT,
            local TEXT,
            fabricante TEXT,
            modelo TEXT,
            data_instalacao TEXT,
            observacoes TEXT
        );
        CREATE TABLE IF NOT EXISTS material (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            descricao TEXT NOT NULL,
            unidade TEXT,
            quantidade REAL DEFAULT 0,
            local_estoque TEXT,
            fornecedor TEXT,
            valor_unitario REAL
        );
        CREATE TABLE IF NOT EXISTS material_equipamento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipamento_id INTEGER NOT NULL,
            material_id INTEGER NOT NULL,
            quantidade REAL,
            posicao TEXT,
            observacoes TEXT,
            UNIQUE(equipamento_id, material_id),
            FOREIGN KEY (equipamento_id) REFERENCES equipamento(id),
            FOREIGN KEY (material_id) REFERENCES material(id)
        );
        CREATE TABLE IF NOT EXISTS notificacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipamento_id INTEGER NOT NULL,
            tipo TEXT,
            descricao TEXT,
            data_criacao TEXT,
            prioridade TEXT,
            status TEXT DEFAULT 'Aberta',
            FOREIGN KEY (equipamento_id) REFERENCES equipamento(id)
        );
        CREATE TABLE IF NOT EXISTS ordem_manutencao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipamento_id INTEGER NOT NULL,
            tipo TEXT,
            descricao TEXT,
            data_inicio TEXT,
            data_fim TEXT,
            status TEXT DEFAULT 'Planejada',
            custo REAL DEFAULT 0,
            FOREIGN KEY (equipamento_id) REFERENCES equipamento(id)
        );
        CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipamento_id INTEGER NOT NULL,
            data TEXT,
            tipo TEXT,
            descricao TEXT,
            FOREIGN KEY (equipamento_id) REFERENCES equipamento(id)
        );
        """
    )
    conn.commit()
    conn.close()


# ---------------------- helpers ----------------------
def conn_simple():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# ---------------------- routes ----------------------
@app.route("/")
def index():
    conn = get_conn()
    stats = {
        "equipamentos": conn.execute("SELECT COUNT(*) as n FROM equipamento").fetchone()["n"],
        "materiais": conn.execute("SELECT COUNT(*) as n FROM material").fetchone()["n"],
        "ordens": conn.execute("SELECT COUNT(*) as n FROM ordem_manutencao").fetchone()["n"],
        "notificacoes": conn.execute("SELECT COUNT(*) as n FROM notificacao WHERE status='Aberta'").fetchone()["n"],
    }
    conn.close()
    return render_template("index.html", stats=stats)


# ---------------- EQUIPAMENTOS ----------------
@app.route("/equipamentos")
def equipamentos():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM equipamento ORDER BY codigo").fetchall()
    conn.close()
    return render_template("equipamentos.html", equipamentos=rows)


@app.route("/equipamentos/novo", methods=["POST"])
def equipamento_novo():
    form = request.form
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO equipamento (codigo,nome,tipo,local,fabricante,modelo,data_instalacao,observacoes) VALUES (?,?,?,?,?,?,?,?)",
            (
                form["codigo"].strip(),
                form["nome"].strip(),
                form.get("tipo", "").strip(),
                form.get("local", "").strip(),
                form.get("fabricante", "").strip(),
                form.get("modelo", "").strip(),
                form.get("data_instalacao", "").strip(),
                form.get("observacoes", "").strip(),
            ),
        )
        conn.commit()
        flash("Equipamento cadastrado.", "ok")
    except sqlite3.IntegrityError:
        flash("Código já existe.", "erro")
    conn.close()
    return redirect(url_for("equipamentos"))


@app.route("/equipamentos/editar/<int:eid>", methods=["POST"])
def equipamento_editar(eid):
    form = request.form
    conn = get_conn()
    conn.execute(
        "UPDATE equipamento SET codigo=?,nome=?,tipo=?,local=?,fabricante=?,modelo=?,data_instalacao=?,observacoes=? WHERE id=?",
        (
            form["codigo"].strip(),
            form["nome"].strip(),
            form.get("tipo", "").strip(),
            form.get("local", "").strip(),
            form.get("fabricante", "").strip(),
            form.get("modelo", "").strip(),
            form.get("data_instalacao", "").strip(),
            form.get("observacoes", "").strip(),
            eid,
        ),
    )
    conn.commit()
    conn.close()
    flash("Equipamento atualizado.", "ok")
    return redirect(url_for("equipamentos"))


@app.route("/equipamentos/excluir/<int:eid>", methods=["POST"])
def equipamento_excluir(eid):
    conn = get_conn()
    conn.execute("DELETE FROM material_equipamento WHERE equipamento_id=?", (eid,))
    conn.execute("DELETE FROM historico WHERE equipamento_id=?", (eid,))
    conn.execute("DELETE FROM ordem_manutencao WHERE equipamento_id=?", (eid,))
    conn.execute("DELETE FROM notificacao WHERE equipamento_id=?", (eid,))
    conn.execute("DELETE FROM equipamento WHERE id=?", (eid,))
    conn.commit()
    conn.close()
    flash("Equipamento excluído.", "ok")
    return redirect(url_for("equipamentos"))


# ---------------- MATERIAIS ----------------
@app.route("/materiais")
def materiais():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM material ORDER BY codigo").fetchall()
    conn.close()
    return render_template("materiais.html", materiais=rows)


@app.route("/materiais/novo", methods=["POST"])
def material_novo():
    form = request.form
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO material (codigo,descricao,unidade,quantidade,local_estoque,fornecedor,valor_unitario) VALUES (?,?,?,?,?,?,?)",
            (
                form["codigo"].strip(),
                form["descricao"].strip(),
                form.get("unidade", "").strip(),
                float(form.get("quantidade", 0) or 0),
                form.get("local_estoque", "").strip(),
                form.get("fornecedor", "").strip(),
                float(form.get("valor_unitario", 0) or 0),
            ),
        )
        conn.commit()
        flash("Material cadastrado.", "ok")
    except sqlite3.IntegrityError:
        flash("Código já existe.", "erro")
    conn.close()
    return redirect(url_for("materiais"))


@app.route("/materiais/editar/<int:mid>", methods=["POST"])
def material_editar(mid):
    form = request.form
    conn = get_conn()
    conn.execute(
        "UPDATE material SET codigo=?,descricao=?,unidade=?,quantidade=?,local_estoque=?,fornecedor=?,valor_unitario=? WHERE id=?",
        (
            form["codigo"].strip(),
            form["descricao"].strip(),
            form.get("unidade", "").strip(),
            float(form.get("quantidade", 0) or 0),
            form.get("local_estoque", "").strip(),
            form.get("fornecedor", "").strip(),
            float(form.get("valor_unitario", 0) or 0),
            mid,
        ),
    )
    conn.commit()
    conn.close()
    flash("Material atualizado.", "ok")
    return redirect(url_for("materiais"))


@app.route("/materiais/excluir/<int:mid>", methods=["POST"])
def material_excluir(mid):
    conn = get_conn()
    conn.execute("DELETE FROM material_equipamento WHERE material_id=?", (mid,))
    conn.execute("DELETE FROM material WHERE id=?", (mid,))
    conn.commit()
    conn.close()
    flash("Material excluído.", "ok")
    return redirect(url_for("materiais"))


# ---------------- VÍNCULOS ----------------
@app.route("/vinculos", methods=["GET", "POST"])
def vinculos():
    conn = get_conn()
    eqs = conn.execute("SELECT id, codigo, nome FROM equipamento ORDER BY codigo").fetchall()
    mats = conn.execute("SELECT id, codigo, descricao FROM material ORDER BY codigo").fetchall()
    vinculos = []
    filtro_eq = request.args.get("equipamento")
    if filtro_eq:
        vincs = conn.execute(
            """
            SELECT me.id, e.codigo as eq_cod, e.nome as eq_nome,
                   m.codigo as mat_cod, m.descricao as mat_desc, me.quantidade, me.posicao, me.observacoes
            FROM material_equipamento me
            JOIN equipamento e ON e.id = me.equipamento_id
            JOIN material m ON m.id = me.material_id
            WHERE e.id = ?
            ORDER BY m.codigo
            """,
            (filtro_eq,),
        ).fetchall()
        for v in vincs:
            vinculos.append(
                {
                    "id": v["id"],
                    "equipamento": f"{v['eq_cod']} - {v['eq_nome']}",
                    "material": f"{v['mat_cod']} - {v['mat_desc']}",
                    "quantidade": v["quantidade"],
                    "posicao": v["posicao"],
                    "observacoes": v["observacoes"],
                }
            )
    conn.close()
    return render_template("vinculos.html", equipamentos=eqs, materiais=mats, vinculos=vinculos, filtro_eq=int(filtro_eq) if filtro_eq else None)


@app.route("/vinculos/novo", methods=["POST"])
def vinculo_novo():
    form = request.form
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO material_equipamento (equipamento_id, material_id, quantidade, posicao, observacoes) VALUES (?,?,?,?,?)",
            (
                int(form["equipamento_id"]),
                int(form["material_id"]),
                float(form.get("quantidade", 0) or 0),
                form.get("posicao", "").strip(),
                form.get("observacoes", "").strip(),
            ),
        )
        conn.commit()
        flash("Vínculo criado.", "ok")
    except sqlite3.IntegrityError:
        flash("Vínculo já existe.", "erro")
    conn.close()
    return redirect(url_for("vinculos", equipamento=form.get("equipamento_id")))


@app.route("/vinculos/excluir/<int:meid>", methods=["POST"])
def vinculo_excluir(meid):
    conn = get_conn()
    conn.execute("DELETE FROM material_equipamento WHERE id=?", (meid,))
    conn.commit()
    conn.close()
    flash("Vínculo removido.", "ok")
    # volta para o mesmo equipamento
    eq_id = request.args.get("equipamento") or request.referrer or url_for("vinculos")
    return redirect(eq_id)


# ---------------- ORDENS ----------------
@app.route("/ordens", methods=["GET", "POST"])
def ordens():
    conn = get_conn()
    equipamentos = conn.execute("SELECT id, codigo, nome FROM equipamento ORDER BY codigo").fetchall()
    filtro_eq = request.args.get("equipamento")
    rows = []
    if filtro_eq:
        rows = conn.execute(
            """
            SELECT o.*, e.codigo || ' - ' || e.nome as equipamento_nome
            FROM ordem_manutencao o
            JOIN equipamento e ON e.id = o.equipamento_id
            WHERE o.equipamento_id = ?
            ORDER BY o.data_inicio DESC
            """,
            (filtro_eq,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT o.*, e.codigo || ' - ' || e.nome as equipamento_nome
            FROM ordem_manutencao o
            JOIN equipamento e ON e.id = o.equipamento_id
            ORDER BY o.data_inicio DESC
            """
        ).fetchall()
    conn.close()
    return render_template("ordens.html", equipamentos=equipamentos, ordens=rows, filtro_eq=int(filtro_eq) if filtro_eq else None)


@app.route("/ordens/novo", methods=["POST"])
def ordem_nova():
    form = request.form
    conn = get_conn()
    conn.execute(
        "INSERT INTO ordem_manutencao (equipamento_id,tipo,descricao,data_inicio,data_fim,status,custo) VALUES (?,?,?,?,?,?,?)",
        (
            int(form["equipamento_id"]),
            form.get("tipo", "").strip(),
            form.get("descricao", "").strip(),
            form.get("data_inicio", "").strip(),
            form.get("data_fim", "").strip(),
            form.get("status", "Planejada").strip(),
            float(form.get("custo", 0) or 0),
        ),
    )
    conn.commit()
    conn.close()
    flash("Ordem de manutenção criada.", "ok")
    return redirect(url_for("ordens"))


@app.route("/ordens/editar/<int:oid>", methods=["POST"])
def ordem_editar(oid):
    form = request.form
    conn = get_conn()
    conn.execute(
        "UPDATE ordem_manutencao SET tipo=?,descricao=?,data_inicio=?,data_fim=?,status=?,custo=? WHERE id=?",
        (
            form.get("tipo", "").strip(),
            form.get("descricao", "").strip(),
            form.get("data_inicio", "").strip(),
            form.get("data_fim", "").strip(),
            form.get("status", "Planejada").strip(),
            float(form.get("custo", 0) or 0),
            oid,
        ),
    )
    conn.commit()
    conn.close()
    flash("Ordem atualizada.", "ok")

    eq_id = request.form.get("equipamento_id")
    if eq_id:
        return redirect(url_for("ordens", equipamento=eq_id))
    return redirect(url_for("ordens"))


@app.route("/ordens/excluir/<int:oid>", methods=["POST"])
def ordem_excluir(oid):
    conn = get_conn()
    conn.execute("DELETE FROM ordem_manutencao WHERE id=?", (oid,))
    conn.commit()
    conn.close()
    flash("Ordem excluída.", "ok")
    return redirect(url_for("ordens"))


# ---------------- NOTIFICAÇÕES ----------------
@app.route("/notificacoes", methods=["GET", "POST"])
def notificacoes():
    conn = get_conn()
    equipamentos = conn.execute("SELECT id, codigo, nome FROM equipamento ORDER BY codigo").fetchall()
    if request.method == "POST":
        form = request.form
        conn.execute(
            "INSERT INTO notificacao (equipamento_id,tipo,descricao,data_criacao,prioridade,status) VALUES (?,?,?,?,?,?)",
            (
                int(form["equipamento_id"]),
                form.get("tipo", "").strip(),
                form.get("descricao", "").strip(),
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                form.get("prioridade", "Média").strip(),
                form.get("status", "Aberta").strip(),
            ),
        )
        conn.commit()
        flash("Notificação criada.", "ok")
        conn.close()
        return redirect(url_for("notificacoes"))

    rows = conn.execute(
        """
        SELECT n.*, e.codigo || ' - ' || e.nome as equipamento_nome
        FROM notificacao n
        JOIN equipamento e ON e.id = n.equipamento_id
        ORDER BY n.data_criacao DESC
        """
    ).fetchall()
    conn.close()
    return render_template("notificacoes.html", equipamentos=equipamentos, notificacoes=rows)


@app.route("/notificacoes/fechar/<int:nid>", methods=["POST"])
def notificacao_fechar(nid):
    conn = get_conn()
    conn.execute("UPDATE notificacao SET status='Fechada' WHERE id=?", (nid,))
    conn.commit()
    conn.close()
    flash("Notificação fechada.", "ok")
    return redirect(url_for("notificacoes"))


@app.route("/notificacoes/excluir/<int:nid>", methods=["POST"])
def notificacao_excluir(nid):
    conn = get_conn()
    conn.execute("DELETE FROM notificacao WHERE id=?", (nid,))
    conn.commit()
    conn.close()
    flash("Notificação excluída.", "ok")
    return redirect(url_for("notificacoes"))


# ---------------- HISTÓRICO ----------------
@app.route("/historico", methods=["GET", "POST"])
def historico():
    conn = get_conn()
    equipamentos = conn.execute("SELECT id, codigo, nome FROM equipamento ORDER BY codigo").fetchall()
    filtro_eq = request.args.get("equipamento")
    rows = []
    if filtro_eq:
        rows = conn.execute(
            "SELECT * FROM historico WHERE equipamento_id=? ORDER BY data DESC",
            (filtro_eq,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT h.*, e.codigo || ' - ' || e.nome as equipamento_nome
            FROM historico h
            JOIN equipamento e ON e.id = h.equipamento_id
            ORDER BY h.data DESC
            """
        ).fetchall()
    conn.close()
    return render_template("historico.html", equipamentos=equipamentos, historico=rows, filtro_eq=int(filtro_eq) if filtro_eq else None)


@app.route("/historico/novo", methods=["POST"])
def historico_novo():
    form = request.form
    conn = get_conn()
    conn.execute(
        "INSERT INTO historico (equipamento_id,data,tipo,descricao) VALUES (?,?,?,?)",
        (
            int(form["equipamento_id"]),
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            form.get("tipo", "").strip(),
            form.get("descricao", "").strip(),
        ),
    )
    conn.commit()
    conn.close()
    flash("Entrada adicionada ao histórico.", "ok")
    return redirect(url_for("historico"))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8080, debug=True)
