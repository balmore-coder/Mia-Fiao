import sqlite3
import streamlit as st
from datetime import datetime, timedelta

# Configuración de la página estilo móvil
st.set_page_config(page_title="Mia-Fiao", page_icon="🏪", layout="centered")
st.title("🏪 Mia-Fiao")
st.subheader("Gestión de Fiados y Puntos")

# --- BASE DE DATOS ---
def inicializar_bd():
    conn = sqlite3.connect('bodeguita_cashea.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            cedula TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            telefono TEXT,
            foto_ruta TEXT,
            puntos INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS creditos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cedula_cliente TEXT,
            monto_deuda REAL DEFAULT 0.0,
            fecha_inicio TEXT,
            fecha_limite TEXT,
            estado TEXT DEFAULT 'PENDIENTE',
            FOREIGN KEY(cedula_cliente) REFERENCES clientes(cedula)
        )
    ''')
    conn.commit()
    conn.close()

inicializar_bd()

# --- FUNCIONES DE LÓGICA ---
def registrar_cliente_bd(cedula, nombre, telefono):
    if not cedula or not nombre:
        st.error("❌ Cédula y Nombre son obligatorios.")
        return False
    try:
        conn = sqlite3.connect('bodeguita_cashea.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO clientes (cedula, nombre, telefono, foto_ruta) VALUES (?, ?, ?, ?)', 
                       (cedula, nombre, telefono, "cliente_foto.jpg"))
        conn.commit()
        conn.close()
        st.success(f"✅ Cliente {nombre} registrado correctamente.")
        return True
    except sqlite3.IntegrityError:
        st.error("❌ Ya existe un cliente con esta cédula.")
        return False

def registrar_fiado_bd(cedula, monto):
    if not cedula or not monto:
        st.error("❌ Debe ingresar Cédula y Monto.")
        return
    try:
        monto_float = float(monto)
        conn = sqlite3.connect('bodeguita_cashea.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT nombre FROM clientes WHERE cedula = ?', (cedula,))
        if not cursor.fetchone():
            st.error("❌ El cliente no está registrado.")
            conn.close()
            return
            
        fecha_actual = datetime.now()
        fecha_ini = fecha_actual.strftime('%Y-%m-%d')
        fecha_lim = (fecha_actual + timedelta(days=30)).strftime('%Y-%m-%d')
        
        cursor.execute('INSERT INTO creditos (cedula_cliente, monto_deuda, fecha_inicio, fecha_limite) VALUES (?, ?, ?, ?)',
                       (cedula, monto_float, fecha_ini, fecha_lim))
        conn.commit()
        conn.close()
        st.success(f"✅ Crédito por ${monto_float} registrado.\nVence el: {fecha_lim}")
    except ValueError:
        st.error("❌ El monto debe ser un número válido.")

def procesar_pago_bd(cedula, pago):
    if not cedula or not pago:
        st.error("❌ Debe ingresar Cédula y Monto del pago.")
        return
    try:
        monto_pago = float(pago)
        conn = sqlite3.connect('bodeguita_cashea.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, monto_deuda, fecha_limite FROM creditos WHERE cedula_cliente = ? AND estado = "PENDIENTE"', (cedula,))
        credito = cursor.fetchone()
        
        if not credito:
            st.info("ℹ️ Este cliente no tiene deudas pendientes.")
            conn.close()
            return
            
        credito_id, monto_deuda, fecha_limite_str = credito
        fecha_limite = datetime.strptime(fecha_limite_str, '%Y-%m-%d')
        fecha_actual = datetime.now()
        
        if fecha_actual > fecha_limite:
            monto_deuda += 1.0
            st.warning("⚠️ Cliente moroso (+1 mes). Se sumó $1 de multa a la deuda.")
        
        if monto_pago >= monto_deuda:
            cursor.execute('UPDATE creditos SET estado = "PAGADO", monto_deuda = 0 WHERE id = ?', (credito_id,))
            if fecha_actual <= fecha_limite:
                cursor.execute('UPDATE clientes SET puntos = puntos + 10 WHERE cedula = ?', (cedula,))
                st.success("🎉 ¡Deuda pagada a tiempo! Cliente ganó +10 puntos.")
            else:
                st.success("✅ Deuda pagada por completo (con retraso). No suma puntos.")
        else:
            nueva_deuda = monto_deuda - monto_pago
            cursor.execute('UPDATE creditos SET monto_deuda = ? WHERE id = ?', (nueva_deuda, credito_id))
            st.success(f"💰 Se abonaron ${monto_pago}. Restan: ${nueva_deuda}")
            
        conn.commit()
        conn.close()
    except ValueError:
        st.error("❌ El pago debe ser un número válido.")

def obtener_resumen():
    conn = sqlite3.connect('bodeguita_cashea.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.cedula, c.nombre, c.puntos, IFNULL(cr.monto_deuda, 0.0), IFNULL(cr.fecha_limite, 'Sin deuda')
        FROM clientes c
        LEFT JOIN creditos cr ON c.cedula = cr.cedula_cliente AND cr.estado = 'PENDIENTE'
    ''')
    datos = cursor.fetchall()
    conn.close()
    return datos

# --- INTERFAZ EN PESTAÑAS (MÓVIL) ---
tab1, tab2, tab3, tab4 = st.tabs(['📊 Resumen', '📋 Registrar Cliente', '💸 Fiar', '🪙 Cobrar'])

with tab1:
    st.header("Resumen de Cuentas")
    busqueda = st.text_input("🔍 Buscar por Cédula o ID:")
    clientes = obtener_resumen()
    
    if clientes:
        for cl in clientes:
            if busqueda == "" or busqueda in str(cl):
                st.markdown(f"**👤 {cl[1]}** (CI: {cl[0]})")
                st.text(f"⭐ Puntos: {cl[2]} | 🔴 Debe: ${cl[3]:.2f} | 📅 Vence: {cl[4]}")
                st.divider()
    else:
        st.write("No hay clientes registrados aún.")

with tab2:
    st.header("Registrar Cliente")
    cedula = st.text_input("Cédula / ID:")
    nombre = st.text_input("Nombre Completo:")
    telefono = st.text_input("Teléfono:")
    if st.button("Guardar Cliente"):
        registrar_cliente_bd(cedula, nombre, telefono)

with tab3:
    st.header("Registrar Crédito")
    cedula_fiar = st.text_input("Cédula del Cliente (Fiar):")
    monto_fiar = st.text_input("Monto a Fiar ($):")
    if st.button("Registrar Crédito (30 días)"):
        registrar_fiado_bd(cedula_fiar, monto_fiar)

with tab4:
    st.header("Procesar Cobro")
    cedula_cobrar = st.text_input("Cédula del Cliente (Cobrar):")
    monto_pago = st.text_input("Monto que está Pagando ($):")
    if st.button("Procesar Pago"):
        procesar_pago_bd(cedula_cobrar, monto_pago)
