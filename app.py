from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from database import init_db, get_session, Cadastro, ConsumoResumido
from services import processar_cadastro, processar_consumo
import os

app = Flask(__name__)
app.secret_key = "globall_secret"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

init_db()

# ==========================================================
# DASHBOARD
# ==========================================================

@app.route("/")
def dashboard():

    session = get_session()

    total_consumo = sum(c.consumo_mb for c in session.query(ConsumoResumido).all())
    total_franquias = sum(c.franquia_mb for c in session.query(Cadastro).all())

    total_usuarios = session.query(Cadastro).count()
    usuarios_com_consumo = session.query(ConsumoResumido).count()
    total_sem_consumo = total_usuarios - usuarios_com_consumo

    percentual_total = round((total_consumo / total_franquias * 100), 2) if total_franquias else 0

    session.close()

    return render_template(
        "dashboard.html",
        total_consumo=round(total_consumo / 1024, 2),
        total_franquias=round(total_franquias / 1024, 2),
        percentual_total=percentual_total,
        total_usuarios=total_usuarios,
        total_sem_consumo=total_sem_consumo
    )

# ==========================================================
# MAPA DE UTILIZAÇÃO
# ==========================================================

@app.route("/usuarios_risco")
def usuarios_risco():

    minimo = float(request.args.get("minimo", 80))
    ordenar = request.args.get("ordenar", "percentual")
    ordem = request.args.get("ordem", "desc")

    session = get_session()

    cadastros = session.query(Cadastro).all()
    consumos = session.query(ConsumoResumido).all()

    consumo_dict = {c.numero: c for c in consumos}

    resultados = []

    for cadastro in cadastros:

        consumo = consumo_dict.get(cadastro.numero)

        consumo_mb = consumo.consumo_mb if consumo else 0
        nome_usuario = consumo.nome_usuario if consumo else "Sem Consumo"

        percentual = (
            (consumo_mb / cadastro.franquia_mb) * 100
            if cadastro.franquia_mb else 0
        )

        if percentual >= minimo:
            resultados.append({
                "numero": cadastro.numero,
                "nome": nome_usuario,
                "franquia": round(cadastro.franquia_mb / 1024, 2),
                "consumo": round(consumo_mb / 1024, 2),
                "percentual": round(percentual, 2)
            })

    session.close()

    reverse = True if ordem == "desc" else False
    resultados.sort(key=lambda x: x.get(ordenar, 0), reverse=reverse)

    return jsonify(resultados)

# ==========================================================
# BUSCA SELECT2
# ==========================================================

@app.route("/buscar_nomes")
def buscar_nomes():

    termo = request.args.get("q", "").strip()
    session = get_session()

    nomes = session.query(ConsumoResumido.nome_usuario).filter(
        ConsumoResumido.nome_usuario.ilike(f"%{termo}%")
    ).distinct().all()

    resultados = [{"id": n[0], "text": n[0]} for n in nomes]

    session.close()
    return jsonify(resultados)


@app.route("/buscar_numeros")
def buscar_numeros():

    termo = request.args.get("q", "").strip()
    session = get_session()

    numeros = session.query(Cadastro.numero).filter(
        Cadastro.numero.ilike(f"%{termo}%")
    ).all()

    resultados = [{"id": n[0], "text": n[0]} for n in numeros]

    session.close()
    return jsonify(resultados)

# ==========================================================
# CONSULTA DETALHADA (CORRIGIDA DEFINITIVA)
# ==========================================================

@app.route("/consultar_usuario")
def consultar_usuario():

    termo = request.args.get("termo", "").strip()
    session = get_session()

    resultados = []

    # 1️⃣ Tenta buscar como número
    cadastro = session.query(Cadastro).filter_by(numero=termo).first()

    if cadastro:
        consumo = session.query(ConsumoResumido).filter_by(numero=termo).first()

        consumo_mb = consumo.consumo_mb if consumo else 0
        nome_usuario = consumo.nome_usuario if consumo else "Sem Consumo"

        percentual = (
            (consumo_mb / cadastro.franquia_mb) * 100
            if cadastro.franquia_mb else 0
        )

        resultados.append({
            "numero": cadastro.numero,
            "nome": nome_usuario,
            "franquia": round(cadastro.franquia_mb / 1024, 2),
            "consumo": round(consumo_mb / 1024, 2),
            "percentual": round(percentual, 2)
        })

    else:
        # 2️⃣ Se não for número, busca por nome
        consumos = session.query(ConsumoResumido).filter(
            ConsumoResumido.nome_usuario == termo
        ).all()

        for consumo in consumos:

            cadastro = session.query(Cadastro).filter_by(numero=consumo.numero).first()
            if not cadastro:
                continue

            percentual = (
                (consumo.consumo_mb / cadastro.franquia_mb) * 100
                if cadastro.franquia_mb else 0
            )

            resultados.append({
                "numero": cadastro.numero,
                "nome": consumo.nome_usuario,
                "franquia": round(cadastro.franquia_mb / 1024, 2),
                "consumo": round(consumo.consumo_mb / 1024, 2),
                "percentual": round(percentual, 2)
            })

    session.close()
    return jsonify(resultados)

# ==========================================================
# UPLOAD CSV
# ==========================================================

@app.route("/upload_cadastro", methods=["POST"])
def upload_cadastro():

    file = request.files.get("file")
    if not file:
        flash("Arquivo não selecionado")
        return redirect(url_for("dashboard"))

    path = os.path.join(UPLOAD_FOLDER, "cadastro.csv")
    file.save(path)

    try:
        processar_cadastro(path)
        flash("Cadastro importado com sucesso")
    except Exception as e:
        flash(str(e))

    return redirect(url_for("dashboard"))


@app.route("/upload_consumo", methods=["POST"])
def upload_consumo():

    file = request.files.get("file")
    if not file:
        flash("Arquivo não selecionado")
        return redirect(url_for("dashboard"))

    path = os.path.join(UPLOAD_FOLDER, "consumo.csv")
    file.save(path)

    try:
        processar_consumo(path)
        flash("Consumo importado com sucesso")
    except Exception as e:
        flash(str(e))

    return redirect(url_for("dashboard"))

# ==========================================================
# CADASTRO ADMIN
# ==========================================================

@app.route("/cadastro_admin")
def cadastro_admin():
    session = get_session()
    usuarios = session.query(Cadastro).all()
    session.close()
    return render_template("cadastro_admin.html", usuarios=usuarios)


@app.route("/cadastro_adicionar", methods=["POST"])
def cadastro_adicionar():

    numero = request.form.get("numero").strip()
    franquia = float(request.form.get("franquia")) * 1024

    session = get_session()

    if session.query(Cadastro).filter_by(numero=numero).first():
        flash("Número já cadastrado.")
        session.close()
        return redirect(url_for("cadastro_admin"))

    novo = Cadastro(numero=numero, franquia_mb=franquia)

    session.add(novo)
    session.commit()
    session.close()

    flash("Usuário adicionado com sucesso.")
    return redirect(url_for("cadastro_admin"))


@app.route("/cadastro_editar", methods=["POST"])
def cadastro_editar():

    numero_antigo = request.form.get("numero_antigo")
    numero_novo = request.form.get("numero_novo")
    franquia = float(request.form.get("franquia")) * 1024

    session = get_session()

    cadastro = session.query(Cadastro).filter_by(numero=numero_antigo).first()
    if not cadastro:
        session.close()
        return redirect(url_for("cadastro_admin"))

    consumo = session.query(ConsumoResumido).filter_by(numero=numero_antigo).first()
    if consumo:
        consumo.numero = numero_novo

    cadastro.numero = numero_novo
    cadastro.franquia_mb = franquia

    session.commit()
    session.close()

    flash("Usuário atualizado.")
    return redirect(url_for("cadastro_admin"))


@app.route("/cadastro_excluir", methods=["POST"])
def cadastro_excluir():

    numero = request.form.get("numero")
    session = get_session()

    session.query(ConsumoResumido).filter_by(numero=numero).delete()
    session.query(Cadastro).filter_by(numero=numero).delete()

    session.commit()
    session.close()

    flash("Usuário removido.")
    return redirect(url_for("cadastro_admin"))

# ==========================================================
# START SERVER
# ==========================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)