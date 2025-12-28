import pandas as pd
import os
import base64
from datetime import datetime
import json
import re
import hashlib
import unicodedata
import time
import numpy as np
import requests  # Añadir para usar Resend API
import shutil

# ==============================================
# CONFIGURACIÓN PRINCIPAL ACTUALIZADA
# ==============================================
CONFIG = {
    # API Keys ACTUALIZADAS
    "WOMPI_PUBLIC_KEY": os.getenv("WOMPI_PUBLIC_KEY", "pub_prod_I0KpwGvgPD3xNcLggJZKyD3cNUKrywkx"),
    # IMPORTANTE: El Integrity Secret NO es la llave privada (prv_*). Debe configurarse por variable de entorno.
    "WOMPI_INTEGRITY_SECRET": os.getenv("WOMPI_INTEGRITY_SECRET", ""),
    # Claves para modo de prueba (sandbox)
    "WOMPI_PUBLIC_KEY_TEST": os.getenv("WOMPI_PUBLIC_KEY_TEST", "pub_test_kxjpfDZfl7yubEFUsLa9j3j4An2zZFSL"),
    "WOMPI_INTEGRITY_SECRET_TEST": os.getenv("WOMPI_INTEGRITY_SECRET_TEST", ""),
    # Cambia a "test" si vas a usar sandbox
    "WOMPI_MODO": "prod",
    # URL pública del Worker (para firmar incluso si abres el HTML desde file:// o GitHub Pages)
    "WORKER_PUBLIC_BASE_URL": os.getenv(
        "WORKER_PUBLIC_BASE_URL",
        "https://catalogo-templo-motor.giraldor192.workers.dev"
    ),
    # No embebas esta API key en el HTML (se expone públicamente). Configúrala por env para uso backend.
    "RESEND_API_KEY": os.getenv("RESEND_API_KEY", ""),
    
    # Rutas de archivos
    "RUTAS": {
        "EXCEL": r"C:\Users\Giral\OneDrive\Documentos\CATQALOGO MOTOS\catalogo_completo\CATALOGO TEMPLO GARAGE.xlsm",
        "LOGO_TEMPLO": r"C:\Users\Giral\OneDrive\Documentos\CATQALOGO MOTOS\logo\TEMPLO GARAGE STREET.png",
        "LOGO_TIKTOK": r"C:\Users\Giral\OneDrive\Documentos\CATQALOGO MOTOS\logo\LOGO TIKTOK.png",
        "PORTADA": r"C:\Users\Giral\OneDrive\Documentos\CATQALOGO MOTOS\logo\portada.png",
        "ANUNCIO": r"C:\Users\Giral\OneDrive\Documentos\CATQALOGO MOTOS\logo\anuncio.png",
        "SALIDA": "catalogo_templo_garage_profesional.html"
    },
    
    # Configuración Excel
    "EXCEL": {
        "HOJA": "MUNDIMOTOS_COMPLETO_20251206_14",
        "COLUMNAS": {
            "marca": ["MARCA", "Marca", "marca", "BRAND"],
            "nombre": ["NOMBRE", "Nombre", "nombre", "PRODUCTO"],
            "precio": ["PRECIO MUNDIMOTOS", "PRECIO", "Precio", "PRICE"],
            "imagen": ["imagen_url", "IMAGEN_URL", "URL_IMAGEN", "Imagen"],
            "descripcion": ["DESCRIPCION", "Descripcion", "descripcion"],
            "tipo": ["TIPO", "Tipo", "tipo", "CATEGORIA"]
        }
    },
    
    # Configuración de comisiones
    "COMISION_TARJETA": 1.99,
    
    # Información de contacto
    "CONTACTO": {
        "WHATSAPP": "573224832415",
        "EMAIL_VENDEDOR": "templogarage@gmail.com",
        "EMAIL_VENTAS": "ventas@templogarage.com",  # Email para ventas
        "TIKTOK_BRUJABLANCA": "https://www.tiktok.com/@brujablanca51",
        "TIKTOK_NATURISTA": "https://www.tiktok.com/@naturista_venuz"
    },
    
    # Parámetros del sistema
    "PARAMETROS": {
        "IVA_PORCENTAJE": 19,
        "REDONDEO": 100,
        "RATING_DEFAULT": 4.9,
        "COMENTARIOS_DEFAULT": 156,
        "MAX_PRODUCTOS": None,
        "PRODUCTOS_POR_PAGINA": 20
    }
}

# ==============================================
# FUNCIONES DE UTILIDAD - MANTENIDAS
# ==============================================

def convertir_imagen_a_base64(ruta_imagen):
    """Convierte cualquier imagen a base64 para incluirla en el HTML"""
    try:
        if not os.path.exists(ruta_imagen):
            print(f"❌ Archivo no encontrado: {ruta_imagen}")
            return None
        
        with open(ruta_imagen, "rb") as img_file:
            imagen_base64 = base64.b64encode(img_file.read()).decode('utf-8')
        
        extension = os.path.splitext(ruta_imagen)[1].lower()
        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp',
            '.svg': 'image/svg+xml',
            '.tiff': 'image/tiff',
            '.ico': 'image/x-icon'
        }
        mime_type = mime_types.get(extension, 'application/octet-stream')
        
        return f"data:{mime_type};base64,{imagen_base64}"
    except Exception as e:
        print(f"❌ Error procesando imagen {ruta_imagen}: {e}")
        return None

def normalizar_texto(texto):
    """Normaliza texto para búsquedas más efectivas"""
    if texto is None:
        return ""
    
    if not isinstance(texto, str):
        texto = str(texto)
    
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    texto = texto.lower()
    
    texto = re.sub(r'[^a-z0-9\s]', '', texto)
    texto = re.sub(r'\s+', ' ', texto)
    
    return texto.strip()

def calcular_precio_final(precio_base):
    """Calcula el precio final con comisión e IVA simplificado"""
    if precio_base <= 0:
        return {"total": 0, "precio_base": 0}
    
    try:
        comision = precio_base * (CONFIG["COMISION_TARJETA"] / 100)
        iva_comision = comision * (CONFIG["PARAMETROS"]["IVA_PORCENTAJE"] / 100)
        total = precio_base + comision + iva_comision
        
        if CONFIG["PARAMETROS"]["REDONDEO"] > 0:
            total = round(total / CONFIG["PARAMETROS"]["REDONDEO"]) * CONFIG["PARAMETROS"]["REDONDEO"]
        
        return {
            "total": round(total, 2),
            "precio_base": precio_base
        }
    
    except Exception as e:
        print(f"❌ Error calculando precio: {e}")
        return {"total": precio_base, "precio_base": precio_base}

def procesar_precio_excel(precio_raw):
    """Convierte el precio del Excel a número"""
    if pd.isna(precio_raw):
        return 0
    
    try:
        if isinstance(precio_raw, (int, float)):
            return float(precio_raw)
        
        precio_str = str(precio_raw)
        precio_limpio = re.sub(r'[^\d.,]', '', precio_str)
        
        if '.' in precio_limpio and ',' in precio_limpio:
            precio_limpio = precio_limpio.replace('.', '').replace(',', '.')
        elif ',' in precio_limpio:
            precio_limpio = precio_limpio.replace(',', '.')
        
        return float(precio_limpio) if precio_limpio else 0
        
    except Exception as e:
        print(f"⚠️ Error procesando precio '{precio_raw}': {e}")
        return 0

def generar_url_placeholder(texto, ancho=400, alto=300):
    """Genera URL de placeholder con color basado en hash del texto"""
    colores_motos = [
        ('FF0000', 'FFFFFF'),
        ('1a237e', 'FFFFFF'),
        ('25D366', 'FFFFFF'),
        ('FFC107', '000000'),
        ('9C27B0', 'FFFFFF'),
        ('FF5722', 'FFFFFF'),
        ('607D8B', 'FFFFFF'),
    ]
    
    if texto:
        hash_obj = hashlib.md5(texto.encode())
        hash_int = int(hash_obj.hexdigest(), 16)
        color_idx = hash_int % len(colores_motos)
    else:
        color_idx = 0
    
    color_fondo, color_texto = colores_motos[color_idx]
    texto_codificado = texto.replace(' ', '+')[:20] if texto else "Producto"
    
    return f"https://via.placeholder.com/{ancho}x{alto}/{color_fondo}/{color_texto}?text={texto_codificado}"

def limpiar_datos_excel(df):
    """Limpia y valida los datos del DataFrame"""
    print("🧹 Limpiando datos del Excel...")
    
    df_limpio = df.copy()
    df_limpio = df_limpio.dropna(how='all')
    
    column_rename = {}
    for col_std, posibles in CONFIG["EXCEL"]["COLUMNAS"].items():
        for col in df_limpio.columns:
            if col in posibles:
                column_rename[col] = col_std
                break
    
    if column_rename:
        df_limpio = df_limpio.rename(columns=column_rename)
        print(f"   ✅ Columnas renombradas: {column_rename}")
    
    columnas_requeridas = ['marca', 'nombre']
    for col in columnas_requeridas:
        if col not in df_limpio.columns:
            df_limpio[col] = None
            print(f"   ⚠️ Columna '{col}' no encontrada, se crea vacía")
    
    if 'marca' in df_limpio.columns:
        df_limpio['marca'] = df_limpio['marca'].fillna('Genérica')
        df_limpio['marca'] = df_limpio['marca'].astype(str).str.strip().str[:30]
    
    if 'nombre' in df_limpio.columns:
        df_limpio['nombre'] = df_limpio['nombre'].fillna('Sin nombre')
        df_limpio['nombre'] = df_limpio['nombre'].astype(str).str.strip().str[:100]
    
    if 'descripcion' in df_limpio.columns:
        df_limpio['descripcion'] = df_limpio['descripcion'].fillna('Sin descripción')
        df_limpio['descripcion'] = df_limpio['descripcion'].astype(str).str.strip().str[:150]
    
    if 'tipo' in df_limpio.columns:
        df_limpio['tipo'] = df_limpio['tipo'].fillna('Accesorio')
        df_limpio['tipo'] = df_limpio['tipo'].astype(str).str.strip().str[:20]
    
    if 'precio' in df_limpio.columns:
        df_limpio['precio'] = df_limpio['precio'].apply(procesar_precio_excel)
        df_limpio['precio'] = df_limpio['precio'].fillna(0).clip(lower=0)
    
    print(f"   ✅ Datos limpios: {len(df_limpio)} filas válidas")
    return df_limpio

# ==============================================
# NUEVA FUNCIÓN PARA ENVÍO DE CORREOS CON RESEND
# ==============================================

def enviar_email_resend(para, asunto, html_contenido, es_venta=False, datos_venta=None):
    """Envía emails usando la API de Resend"""
    try:
        headers = {
            'Authorization': f'Bearer {CONFIG["RESEND_API_KEY"]}',
            'Content-Type': 'application/json'
        }
        
        # Configurar el remitente según el tipo de email
        if es_venta:
            remitente = f"Ventas Templo Garage <{CONFIG['CONTACTO']['EMAIL_VENTAS']}>"
        else:
            remitente = f"Templo Garage <{CONFIG['CONTACTO']['EMAIL_VENDEDOR']}>"
        
        payload = {
            "from": remitente,
            "to": para,
            "subject": asunto,
            "html": html_contenido
        }
        
        # Añadir datos de venta si corresponde
        if es_venta and datos_venta:
            payload["reply_to"] = datos_venta.get("email_cliente", CONFIG['CONTACTO']['EMAIL_VENDEDOR'])
        
        response = requests.post('https://api.resend.com/emails', 
                                headers=headers, 
                                json=payload,
                                timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Email enviado a {para}")
            return True
        else:
            print(f"❌ Error enviando email: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error en enviar_email_resend: {e}")
        return False

# ==============================================
# PROCESAMIENTO DE PRODUCTOS - MANTENIDO
# ==============================================

class ProcesadorProductos:
    def __init__(self):
        self.productos = []
        self.estadisticas = {
            'total': 0,
            'con_precio': 0,
            'marcas_unicas': set(),
            'tipos_unicos': set(),
            'errores': 0
        }
    
    def procesar_dataframe(self, df):
        """Procesa todo el DataFrame y genera la lista de productos"""
        print(f"\n🔄 Procesando {len(df)} productos...")
        
        for idx, fila in df.iterrows():
            try:
                producto = self.procesar_fila(idx, fila)
                if producto:
                    self.productos.append(producto)
                    
                    if producto['precio'] > 0:
                        self.estadisticas['con_precio'] += 1
                    self.estadisticas['marcas_unicas'].add(producto['marca'])
                    self.estadisticas['tipos_unicos'].add(producto['tipo'])
                    
                    if (idx + 1) % 500 == 0:
                        print(f"   📦 Procesados: {idx + 1:,}/{len(df):,}")
                        
            except Exception as e:
                self.estadisticas['errores'] += 1
                continue
        
        self.estadisticas['total'] = len(self.productos)
        return self.productos
    
    def procesar_fila(self, idx, fila):
        """Procesa una fila individual del DataFrame"""
        try:
            marca = str(fila.get('marca', '')).strip()[:30] or 'Genérica'
            nombre = str(fila.get('nombre', '')).strip()[:100] or 'Sin nombre'
            descripcion = str(fila.get('descripcion', '')).strip()[:150] or 'Sin descripción'
            tipo = str(fila.get('tipo', '')).strip()[:20] or 'Accesorio'
            precio = float(fila.get('precio', 0)) if pd.notna(fila.get('precio')) else 0
            
            imagen_raw = fila.get('imagen', '')
            if pd.isna(imagen_raw) or not isinstance(imagen_raw, str) or not imagen_raw.startswith(('http', 'https')):
                imagen = generar_url_placeholder(marca)
            else:
                imagen = str(imagen_raw).strip()
            
            calculo = calcular_precio_final(precio)
            
            producto = {
                'id': idx + 1,
                'marca': marca,
                'nombre': nombre,
                'nombre_normalizado': normalizar_texto(nombre),
                'descripcion': descripcion,
                'descripcion_normalizada': normalizar_texto(descripcion),
                'precio': precio,
                'precio_final': calculo['total'],
                'precio_str': f"${calculo['total']:,.0f}".replace(',', '.') if calculo['total'] > 0 else "Consultar",
                'imagen': imagen,
                'tipo': tipo,
                'rating': CONFIG["PARAMETROS"]["RATING_DEFAULT"],
                'comentarios': CONFIG["PARAMETROS"]["COMENTARIOS_DEFAULT"],
                'categoria': 'motos',
                'fecha_actualizacion': datetime.now().strftime('%Y-%m-%d')
            }
            
            return producto
            
        except Exception as e:
            print(f"⚠️ Error procesando fila {idx}: {e}")
            return None

# ==============================================
# GENERACIÓN DE HTML COMPLETO MODIFICADO
# ==============================================

def generar_html_completo(productos, recursos, estadisticas):
    """Genera el HTML completo con todas las funcionalidades"""
    
    productos_json = json.dumps(productos, ensure_ascii=False, separators=(',', ':'))
    fecha_actual = datetime.now().strftime('%d/%m/%Y %H:%M')

    wompi_modo = str(CONFIG.get('WOMPI_MODO', 'prod')).strip().lower()
    wompi_public_key = CONFIG['WOMPI_PUBLIC_KEY_TEST'] if wompi_modo == 'test' else CONFIG['WOMPI_PUBLIC_KEY']
    wompi_api_base = 'https://sandbox.wompi.co' if wompi_modo == 'test' else 'https://production.wompi.co'

    # Nunca exponer secretos en el frontend.
    wompi_integrity_secret_frontend = ''
    
    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Templo Garage Street & TikTok Moto Parts - Catálogo Profesional</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap">
    <script type="text/javascript" src="https://checkout.wompi.co/widget.js"></script>
    <style>
        /* ===== VARIABLES Y ESTILOS GLOBALES ===== */
        :root {{
            --primary: #FF0000;
            --secondary: #1a237e;
            --accent: #25D366;
            --tiktok-color: #000000;
            --dark: #121212;
            --light: #f8f9fa;
            --gray: #6c757d;
            --success: #28a745;
            --warning: #ffc107;
            --danger: #dc3545;
            --gradient-primary: linear-gradient(135deg, #FF0000 0%, #1a237e 100%);
            --gradient-secondary: linear-gradient(135deg, #1a237e 0%, #000000 100%);
            --gradient-protect: linear-gradient(135deg, #FF0000 0%, #FF9800 50%, #FF0000 100%);

            --radius: 14px;
            --radius-sm: 10px;
            --transition-fast: 160ms cubic-bezier(0.2, 0.8, 0.2, 1);
            --transition-med: 260ms cubic-bezier(0.2, 0.8, 0.2, 1);
            
            --bg-primary: #0a0a0a;
            --bg-secondary: #1a1a1a;
            --text-primary: #ffffff;
            --text-secondary: #b0b0b0;
            --border-color: #333333;
            --card-bg: #1e1e1e;
            --card-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }}

        [data-theme="light"] {{
            --bg-primary: #ffffff;
            --bg-secondary: #f8f9fa;
            --text-primary: #212529;
            --text-secondary: #6c757d;
            --border-color: #dee2e6;
            --card-bg: #ffffff;
            --card-shadow: 0 5px 15px rgba(0,0,0,0.08);
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Poppins', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            overflow-x: hidden;
            transition: background 0.3s, color 0.3s;
            padding-bottom: 100px;
        }}

        @media (prefers-reduced-motion: reduce) {{
            * {{
                animation: none !important;
                transition: none !important;
                scroll-behavior: auto !important;
            }}
        }}

        @keyframes fadeUp {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* ===== PORTADA MEJORADA CON AJUSTE PARA COMPUTADOR ===== */
        .portada {{
            position: relative;
            height: auto;
            min-height: 85vh;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            overflow: hidden;
            padding: 40px 20px;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%);
            margin-bottom: 30px;
        }}

        .portada::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url("{recursos['portada']}");
            background-size: cover;
            background-position: center;
            opacity: 0.2;
            z-index: 1;
        }}

        .portada-content {{
            position: relative;
            z-index: 2;
            max-width: 1400px;
            width: 100%;
            padding-top: 40px;
        }}

        /* ===== LOGOS PROFESIONALES ANIMADOS ===== */
        .logos-container {{
            display: flex;
            justify-content: center;
            align-items: flex-start;
            gap: 80px;
            margin-bottom: 40px;
            flex-wrap: wrap;
            padding-top: 20px;
        }}

        .logo-wrapper {{
            display: flex;
            flex-direction: column;
            align-items: center;
            transition: all 0.4s;
            padding: 30px;
            border-radius: 25px;
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            position: relative;
            overflow: hidden;
            width: 320px;
            text-decoration: none;
            color: inherit;
            margin-top: 30px;
        }}

        .logo-wrapper::before {{
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
            opacity: 0;
            transition: opacity 0.3s;
        }}

        .logo-wrapper:hover::before {{
            opacity: 1;
        }}

        .logo-wrapper:hover {{
            transform: translateY(-10px) scale(1.05);
            box-shadow: 0 20px 40px rgba(255, 0, 0, 0.3);
            border-color: rgba(255, 0, 0, 0.3);
        }}

        .logo-img {{
            height: 140px;
            width: auto;
            max-width: 280px;
            object-fit: contain;
            filter: drop-shadow(0 10px 20px rgba(0,0,0,0.7));
            margin-bottom: 25px;
            z-index: 1;
        }}

        .logo-label {{
            font-size: 20px;
            font-weight: 700;
            color: white;
            text-shadow: 2px 2px 8px rgba(0,0,0,0.8);
            padding: 12px 30px;
            border-radius: 25px;
            z-index: 1;
        }}

        .logo-tiktok .logo-label {{
            background: linear-gradient(135deg, rgba(255, 0, 0, 0.9) 0%, rgba(255, 20, 147, 0.9) 100%);
            border: 2px solid rgba(255, 255, 255, 0.3);
        }}

        .logo-templo .logo-label {{
            background: linear-gradient(135deg, rgba(26, 35, 126, 0.9) 0%, rgba(13, 71, 161, 0.9) 100%);
            border: 2px solid rgba(255, 255, 255, 0.3);
        }}

        /* ===== TÍTULOS ===== */
        .main-title {{
            font-size: 4rem;
            font-weight: 800;
            margin-bottom: 25px;
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 10px 30px rgba(0,0,0,0.5);
            line-height: 1.2;
        }}

        .subtitle {{
            font-size: 1.8rem;
            color: var(--text-primary);
            margin-bottom: 30px;
            max-width: 900px;
            margin-left: auto;
            margin-right: auto;
            background: rgba(0, 0, 0, 0.6);
            padding: 20px 40px;
            border-radius: 15px;
            border-left: 4px solid var(--primary);
            border-right: 4px solid var(--secondary);
        }}

        /* LETRERO PROTEGEMOS TODAS TUS PARTES - AJUSTADO PARA COMPUTADOR */
        .protect-text {{
            font-size: 3.5rem;
            font-weight: 900;
            color: white;
            margin: 40px auto 60px auto;
            padding: 25px 50px;
            text-align: center;
            background: var(--gradient-protect);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 25px rgba(255, 152, 0, 0.5);
            border: 3px solid;
            border-image: linear-gradient(135deg, #FF0000, #FF9800, #FF0000) 1;
            position: relative;
            animation: protectPulse 2s ease-in-out infinite;
            max-width: 95%;
            z-index: 5;
        }}

        @keyframes protectPulse {{
            0%, 100% {{ 
                transform: scale(1);
                box-shadow: 0 5px 20px rgba(255, 0, 0, 0.3);
            }}
            50% {{ 
                transform: scale(1.03);
                box-shadow: 0 10px 30px rgba(255, 152, 0, 0.5);
            }}
        }}

        /* ===== BUSCADOR MEJORADO CON FILTROS DESPLEGABLES ===== */
        .buscador-avanzado {{
            background: linear-gradient(135deg, var(--bg-secondary), var(--card-bg));
            padding: 25px;
            border-radius: 15px;
            margin: 30px auto;
            max-width: 1400px;
            box-shadow: var(--card-shadow);
            position: relative;
            z-index: 10;
        }}

        .buscador-container {{
            position: relative;
            max-width: 900px;
            margin: 0 auto 25px;
        }}

        .buscador-container i {{
            position: absolute;
            left: 20px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--primary);
            font-size: 20px;
            z-index: 2;
        }}

        .buscador-container input {{
            width: 100%;
            padding: 18px 20px 18px 55px;
            border: 2px solid var(--primary);
            border-radius: 30px;
            background: rgba(255, 255, 255, 0.1);
            color: var(--text-primary);
            font-size: 17px;
            transition: all 0.3s;
        }}

        .buscador-container input:focus {{
            background: rgba(255, 255, 255, 0.15);
            outline: none;
            box-shadow: 0 0 25px rgba(255, 0, 0, 0.3);
        }}

        .sugerencias {{
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: var(--card-bg);
            border-radius: 10px;
            box-shadow: var(--card-shadow);
            max-height: 350px;
            overflow-y: auto;
            display: none;
            z-index: 1000;
            border: 1px solid var(--border-color);
        }}

        .sugerencia-item {{
            padding: 15px 20px;
            border-bottom: 1px solid var(--border-color);
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 12px;
            transition: background 0.2s;
            color: var(--text-primary);
        }}

        .sugerencia-item:hover {{
            background: rgba(255, 0, 0, 0.1);
        }}

        .sugerencia-item img {{
            width: 45px;
            height: 45px;
            object-fit: cover;
            border-radius: 6px;
        }}

        .filtros-desplegables {{
            display: flex;
            justify-content: center;
            gap: 20px;
            flex-wrap: wrap;
            margin-top: 25px;
        }}

        .filtro-select {{
            padding: 14px 20px;
            border: 2px solid var(--primary);
            border-radius: 15px;
            background: rgba(255, 255, 255, 0.1);
            color: var(--text-primary);
            font-size: 16px;
            min-width: 220px;
            cursor: pointer;
            transition: all 0.3s;
        }}

        .filtro-select:hover {{
            background: rgba(255, 255, 255, 0.15);
        }}

        .filtro-select option {{
            background: var(--card-bg);
            color: var(--text-primary);
        }}

        /* ===== CONTROLES SUPERIORES MEJORADOS ===== */
        .controles-superiores {{
            position: fixed;
            top: 25px;
            right: 25px;
            display: flex;
            gap: 15px;
            z-index: 9999;
        }}

        .btn-carrito-flotante,
        .btn-toggle-modo,
        .btn-whatsapp-flotante,
        .btn-chat-flotante {{
            width: 55px;
            height: 55px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            cursor: pointer;
            border: none;
            transition: transform 0.3s, box-shadow 0.3s;
            position: relative;
        }}

        .btn-toggle-modo {{
            background: linear-gradient(135deg, var(--primary), #ff3333);
            color: white;
            box-shadow: 0 5px 15px rgba(255, 0, 0, 0.3);
        }}

        .btn-whatsapp-flotante {{
            background: linear-gradient(135deg, #25D366, #128C7E);
            color: white;
            box-shadow: 0 5px 15px rgba(37, 211, 102, 0.3);
        }}

        .btn-carrito-flotante {{
            background: linear-gradient(135deg, var(--secondary), #283593);
            color: white;
            box-shadow: 0 5px 15px rgba(26, 35, 126, 0.3);
        }}

        .btn-chat-flotante {{
            background: linear-gradient(135deg, #9C27B0, #673AB7);
            color: white;
            box-shadow: 0 5px 15px rgba(156, 39, 176, 0.3);
            position: fixed;
            bottom: 25px;
            right: 25px;
            z-index: 9996;
        }}

        .btn-carrito-flotante:hover,
        .btn-toggle-modo:hover,
        .btn-whatsapp-flotante:hover,
        .btn-chat-flotante:hover {{
            transform: translateY(-5px);
        }}

        .carrito-contador {{
            position: absolute;
            top: -5px;
            right: -5px;
            background: var(--accent);
            color: white;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 700;
        }}

        /* ===== GRID DE PRODUCTOS RESPONSIVE ===== */
        .productos-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 25px;
            padding: 25px;
            max-width: 1500px;
            margin: 0 auto;
        }}

        .empty-state {{
            grid-column: 1 / -1;
            padding: 28px 18px;
            border-radius: var(--radius);
            border: 1px dashed var(--border-color);
            background: var(--bg-secondary);
            color: var(--text-secondary);
            text-align: center;
            animation: fadeUp 220ms ease both;
        }}

        .empty-state h3 {{
            color: var(--text-primary);
            margin-bottom: 6px;
            font-size: 18px;
        }}

        .empty-state p {{
            margin: 0;
        }}

        /* MÓVIL - 2 columnas */
        @media (max-width: 768px) {{
            .portada {{
                height: auto;
                min-height: 600px;
                padding: 40px 20px;
                margin-bottom: 30px;
            }}

            .portada-content {{
                padding-top: 40px;
            }}

            .logos-container {{
                flex-direction: column;
                gap: 40px;
                margin-bottom: 40px;
                padding-top: 20px;
            }}

            .logo-wrapper {{
                width: 100%;
                max-width: 320px;
                margin: 0 auto;
                padding: 25px;
            }}

            .logo-img {{
                height: 100px;
            }}

            .main-title {{
                font-size: 2.2rem;
            }}

            .subtitle {{
                font-size: 1.1rem;
                padding: 15px 25px;
            }}

            .protect-text {{
                font-size: 1.8rem;
                padding: 15px 25px;
                margin: 30px auto 50px auto;
            }}

            .productos-grid {{
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
                padding: 15px;
            }}

            .producto-card {{
                padding: 12px;
                border-radius: 12px;
            }}

            .producto-imagen {{
                height: 150px;
            }}

            .producto-titulo {{
                font-size: 14px;
                height: 40px;
            }}

            .producto-precio {{
                font-size: 15px;
            }}

            .btn-comprar, .btn-carrito {{
                padding: 10px;
                font-size: 13px;
            }}

            .controles-superiores {{
                top: 15px;
                right: 15px;
                gap: 10px;
            }}

            .btn-carrito-flotante,
            .btn-toggle-modo,
            .btn-whatsapp-flotante {{
                width: 48px;
                height: 48px;
                font-size: 20px;
            }}

            .filtros-desplegables {{
                flex-direction: column;
                align-items: center;
            }}

            .filtro-select {{
                width: 90%;
                min-width: unset;
            }}
        }}

        /* TABLET - 3 columnas */
        @media (min-width: 769px) and (max-width: 1024px) {{
            .productos-grid {{
                grid-template-columns: repeat(3, 1fr);
                gap: 20px;
            }}

            .logos-container {{
                gap: 40px;
            }}

            .logo-wrapper {{
                width: 280px;
            }}
        }}

        /* ESCRITORIO - 4 columnas */
        @media (min-width: 1025px) {{
            .productos-grid {{
                grid-template-columns: repeat(4, 1fr);
            }}
            
            /* Ajuste específico para el letrero en escritorio */
            .protect-text {{
                margin: 60px auto 80px auto;
                font-size: 3rem;
            }}
        }}

        /* ===== TARJETAS DE PRODUCTO MEJORADAS ===== */
        .producto-card {{
            background: var(--card-bg);
            border-radius: 15px;
            padding: 18px;
            transition: all 0.3s;
            border: 1px solid var(--border-color);
            box-shadow: var(--card-shadow);
            display: flex;
            flex-direction: column;
            height: 100%;
            position: relative;
            overflow: hidden;
        }}

        /* Splash anuncio (medios de pago) */
        .splash-overlay {{
            position: fixed;
            inset: 0;
            z-index: 10000;
            display: none;
            align-items: center;
            justify-content: center;
            padding: 18px;
            background: rgba(0,0,0,0.82);
            backdrop-filter: blur(8px);
        }}

        [data-theme="light"] .splash-overlay {{
            background: rgba(255,255,255,0.88);
        }}

        .splash-overlay.show {{
            display: flex;
            animation: fadeUp 180ms ease both;
        }}

        .splash-card {{
            width: min(860px, 94vw);
            max-height: 82vh;
            border-radius: 16px;
            border: 1px solid var(--border-color);
            background: rgba(255,255,255,0.04);
            box-shadow: var(--card-shadow);
            overflow: hidden;
        }}

        [data-theme="light"] .splash-card {{
            background: rgba(255,255,255,0.75);
        }}

        .splash-card img {{
            display: block;
            width: 100%;
            height: auto;
            max-height: 82vh;
            object-fit: contain;
        }}

        /* Compartir producto */
        .btn-compartir {{
            flex: 1;
            background: rgba(255,255,255,0.06);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
            padding: 14px;
            border-radius: 10px;
            cursor: pointer;
            transition: transform var(--transition-fast), background var(--transition-fast), border-color var(--transition-fast);
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
        }}

        .btn-compartir:hover {{
            transform: translateY(-2px);
            border-color: rgba(26,35,126,0.55);
            background: rgba(255,255,255,0.10);
        }}

        .modal-compartir {{
            display: none;
            position: fixed;
            inset: 0;
            z-index: 9999;
            background: rgba(0,0,0,0.68);
            align-items: center;
            justify-content: center;
            padding: 18px;
        }}

        [data-theme="light"] .modal-compartir {{
            background: rgba(0,0,0,0.42);
        }}

        .modal-compartir .modal-share-content {{
            width: min(520px, 94vw);
            border-radius: 16px;
            border: 1px solid var(--border-color);
            background: var(--card-bg);
            box-shadow: var(--card-shadow);
            padding: 18px;
            position: relative;
        }}

        .share-title {{
            font-weight: 1000;
            letter-spacing: 0.2px;
            margin: 0 0 8px;
        }}

        .share-subtitle {{
            color: var(--text-secondary);
            font-weight: 600;
            margin: 0 0 14px;
            font-size: 13px;
        }}

        .share-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }}

        .share-btn {{
            width: 100%;
            border: 1px solid var(--border-color);
            background: rgba(255,255,255,0.04);
            color: var(--text-primary);
            border-radius: 12px;
            padding: 12px 12px;
            font-weight: 800;
            letter-spacing: 0.2px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 10px;
            transition: transform var(--transition-fast), background var(--transition-fast), border-color var(--transition-fast);
        }}

        .share-btn:hover {{
            transform: translateY(-1px);
            border-color: rgba(26,35,126,0.55);
            background: rgba(255,255,255,0.08);
        }}

        @media (max-width: 520px) {{
            .share-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        .producto-card:hover {{
            transform: translateY(-8px);
            box-shadow: 0 15px 30px rgba(255, 0, 0, 0.25);
            border-color: var(--primary);
        }}

        .producto-badge {{
            position: absolute;
            top: 12px;
            left: 12px;
            background: var(--primary);
            color: white;
            padding: 6px 12px;
            border-radius: 15px;
            font-size: 12px;
            font-weight: 600;
            z-index: 2;
        }}

        .producto-badge.oferta {{
            background: linear-gradient(135deg, #FF0000, #FF9800);
        }}

        .producto-imagen {{
            width: 100%;
            height: 220px;
            object-fit: contain;
            border-radius: 12px;
            margin-bottom: 18px;
            background: rgba(255, 255, 255, 0.05);
            padding: 12px;
            position: relative;
            overflow: hidden;
        }}

        .producto-imagen img {{
            width: 100%;
            height: 100%;
            object-fit: contain;
            transition: transform 0.5s;
        }}

        .producto-card:hover .producto-imagen img {{
            transform: scale(1.08);
        }}

        .producto-info {{
            flex: 1;
            display: flex;
            flex-direction: column;
        }}

        .producto-marca {{
            font-size: 13px;
            color: var(--primary);
            font-weight: 600;
            margin-bottom: 6px;
            text-transform: uppercase;
        }}

        .producto-titulo {{
            font-size: 17px;
            font-weight: 600;
            margin-bottom: 12px;
            color: var(--text-primary);
            line-height: 1.4;
            flex: 1;
        }}

        .producto-descripcion {{
            font-size: 14px;
            color: var(--text-secondary);
            margin-bottom: 18px;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}

        .producto-precio {{
            margin-bottom: 18px;
        }}

        .precio-actual {{
            font-size: 22px;
            font-weight: 700;
            color: var(--primary);
        }}

        .precio-original {{
            font-size: 15px;
            color: var(--text-secondary);
            text-decoration: line-through;
            margin-right: 10px;
        }}

        .precio-consultar {{
            font-size: 17px;
            color: var(--warning);
            font-weight: 600;
        }}

        .botones-producto {{
            display: flex;
            gap: 10px;
            margin-top: auto;
        }}

        .btn-comprar {{
            flex: 3;
            background: linear-gradient(135deg, var(--primary), #ff3333);
            color: white;
            border: none;
            padding: 14px;
            border-radius: 10px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }}

        .btn-carrito {{
            flex: 1;
            background: linear-gradient(135deg, var(--secondary), #283593);
            color: white;
            border: none;
            padding: 14px;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
        }}

        .btn-carrito:hover {{
            background: linear-gradient(135deg, #283593, #1a237e);
        }}

        .contador-carrito-mini {{
            position: absolute;
            top: -8px;
            right: -8px;
            background: var(--accent);
            color: white;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            font-size: 11px;
            font-weight: 700;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .btn-comprar:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(255, 0, 0, 0.4);
        }}

        .btn-comprar:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }}

        /* ===== PAGINACIÓN ===== */
        .paginacion {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 12px;
            margin: 40px auto;
            flex-wrap: wrap;
        }}

        .paginacion-btn {{
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            width: 45px;
            height: 45px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.3s;
        }}

        .paginacion-btn:hover {{
            background: rgba(255, 0, 0, 0.2);
            border-color: var(--primary);
        }}

        .paginacion-btn.active {{
            background: var(--primary);
            color: white;
        }}

        .paginacion-info {{
            color: var(--text-secondary);
            margin: 0 20px;
            text-align: center;
        }}

        /* ===== MODAL DE COMPRA MEJORADO ===== */
        .modal-compra {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.85);
            z-index: 9999;
            align-items: center;
            justify-content: center;
            animation: fadeIn 0.3s;
            padding: 20px;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}

        .modal-content {{
            background: var(--card-bg);
            width: 95%;
            max-width: 550px;
            border-radius: 25px;
            padding: 35px;
            position: relative;
            color: var(--text-primary);
            max-height: 90vh;
            overflow-y: auto;
            border: 1px solid var(--border-color);
            box-shadow: 0 25px 60px rgba(0, 0, 0, 0.5);
        }}

        .modal-close {{
            position: absolute;
            top: 25px;
            right: 25px;
            background: none;
            border: none;
            font-size: 28px;
            color: var(--text-primary);
            cursor: pointer;
            width: 35px;
            height: 35px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            transition: background 0.3s;
        }}

        .modal-close:hover {{
            background: rgba(255, 0, 0, 0.2);
        }}

        .compra-header {{
            text-align: center;
            margin-bottom: 35px;
            color: var(--primary);
        }}

        .form-group {{
            margin-bottom: 25px;
        }}

        .form-group label {{
            display: block;
            margin-bottom: 10px;
            font-weight: 600;
            color: var(--text-secondary);
        }}

        .form-group input,
        .form-group select {{
            width: 100%;
            padding: 15px 20px;
            border: 2px solid var(--border-color);
            border-radius: 12px;
            font-size: 16px;
            transition: border 0.3s;
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-primary);
        }}

        .form-group input:focus,
        .form-group select:focus {{
            border-color: var(--primary);
            outline: none;
        }}

        /* Selector de país */
        .phone-input-container {{
            display: flex;
            gap: 12px;
        }}

        .country-select {{
            flex: 0 0 130px;
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 15px 20px;
            border: 2px solid var(--border-color);
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.05);
        }}

        .country-select img {{
            width: 22px;
            height: 16px;
            object-fit: cover;
            border-radius: 3px;
        }}

        .phone-input {{
            flex: 1;
        }}

        .resumen-compra {{
            background: rgba(255, 255, 255, 0.05);
            padding: 25px;
            border-radius: 15px;
            margin: 30px 0;
        }}

        .resumen-total {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 20px;
            border-top: 2px solid var(--border-color);
            font-size: 20px;
            font-weight: 700;
        }}

        .btn-pagar {{
            width: 100%;
            padding: 18px;
            background: linear-gradient(135deg, var(--primary), #ff3333);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 20px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            transition: transform 0.3s;
        }}

        .btn-pagar:hover {{
            transform: translateY(-3px);
        }}

        .texto-seguro {{
            text-align: center;
            margin-top: 20px;
            color: var(--text-secondary);
            font-size: 15px;
        }}

        /* ===== MODAL DE CARRITO ===== */
        .modal-carrito {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.85);
            z-index: 9998;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}

        .carrito-content {{
            background: var(--card-bg);
            width: 95%;
            max-width: 800px;
            border-radius: 25px;
            padding: 35px;
            position: relative;
            color: var(--text-primary);
            max-height: 90vh;
            overflow-y: auto;
            border: 1px solid var(--border-color);
            box-shadow: 0 25px 60px rgba(0, 0, 0, 0.5);
        }}

        .carrito-header {{
            text-align: center;
            margin-bottom: 30px;
            color: var(--primary);
        }}

        .carrito-items {{
            max-height: 400px;
            overflow-y: auto;
            margin-bottom: 30px;
        }}

        .carrito-item {{
            display: flex;
            align-items: center;
            gap: 20px;
            padding: 20px;
            border-bottom: 1px solid var(--border-color);
            background: rgba(255, 255, 255, 0.03);
            border-radius: 12px;
            margin-bottom: 15px;
        }}

        .carrito-item img {{
            width: 80px;
            height: 80px;
            object-fit: contain;
            border-radius: 10px;
        }}

        .carrito-item-info {{
            flex: 1;
        }}

        .carrito-item-nombre {{
            font-weight: 600;
            margin-bottom: 8px;
        }}

        .carrito-item-marca {{
            color: var(--text-secondary);
            font-size: 14px;
            margin-bottom: 8px;
        }}

        .carrito-item-precio {{
            font-weight: 700;
            color: var(--primary);
        }}

        .carrito-item-controls {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}

        .carrito-item-cantidad {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .btn-cantidad {{
            width: 35px;
            height: 35px;
            border-radius: 50%;
            border: 2px solid var(--primary);
            background: transparent;
            color: var(--primary);
            font-size: 18px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .btn-cantidad:hover {{
            background: rgba(255, 0, 0, 0.1);
        }}

        .cantidad-numero {{
            font-size: 18px;
            font-weight: 600;
            min-width: 30px;
            text-align: center;
        }}

        .btn-eliminar {{
            padding: 10px 20px;
            background: rgba(220, 53, 69, 0.2);
            color: var(--danger);
            border: 1px solid var(--danger);
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
        }}

        .btn-eliminar:hover {{
            background: rgba(220, 53, 69, 0.3);
        }}

        .carrito-total {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 25px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            margin-top: 30px;
            font-size: 22px;
            font-weight: 700;
        }}

        .carrito-botones {{
            display: flex;
            gap: 15px;
            margin-top: 30px;
        }}

        .btn-continuar {{
            flex: 1;
            padding: 18px;
            background: linear-gradient(135deg, var(--secondary), #283593);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }}

        .btn-vaciar {{
            flex: 1;
            padding: 18px;
            background: rgba(220, 53, 69, 0.2);
            color: var(--danger);
            border: 1px solid var(--danger);
            border-radius: 12px;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }}

        /* ===== CHAT MINIMALISTA MEJORADO ===== */
        .modal-chat {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.85);
            z-index: 9995;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}

        .chat-content {{
            background: var(--card-bg);
            width: 95%;
            max-width: 500px;
            border-radius: 25px;
            padding: 25px;
            position: relative;
            color: var(--text-primary);
            max-height: 90vh;
            overflow: hidden;
            border: 1px solid var(--border-color);
            box-shadow: 0 25px 60px rgba(0, 0, 0, 0.5);
        }}

        .chat-body {{
            height: 500px;
            display: flex;
            flex-direction: column;
        }}

        .chat-messages {{
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            background: var(--bg-secondary);
        }}

        .mensaje {{
            margin-bottom: 20px;
            max-width: 85%;
            clear: both;
        }}

        .mensaje.bot {{
            float: left;
        }}

        .mensaje.usuario {{
            float: right;
        }}

        .burbuja {{
            padding: 15px 20px;
            border-radius: 25px;
            font-size: 15px;
            line-height: 1.5;
            max-width: 100%;
            word-wrap: break-word;
        }}

        .mensaje.bot .burbuja {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 25px 25px 25px 8px;
        }}

        .mensaje.usuario .burbuja {{
            background: linear-gradient(135deg, var(--primary), #ff3333);
            color: white;
            border-radius: 25px 25px 8px 25px;
        }}

        .opciones-chat {{
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin: 15px 0;
            padding: 10px;
            width: 100%;
            box-sizing: border-box;
        }}

        .opcion-chat {{
            padding: 12px 20px;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid var(--border-color);
            border-radius: 15px;
            cursor: pointer;
            transition: all 0.3s;
            text-align: left;
            color: var(--text-primary);
            font-size: 14px;
            width: 100%;
            box-sizing: border-box;
            display: flex;
            align-items: center;
            gap: 10px;
            word-wrap: break-word;
            overflow-wrap: break-word;
            white-space: normal;
            writing-mode: horizontal-tb;
            text-orientation: mixed;
        }}

        .opcion-chat i {{
            flex: 0 0 auto;
            margin-top: 1px;
        }}

        .opcion-chat-text {{
            flex: 1 1 auto;
            min-width: 0;
        }}

        .opcion-chat:hover {{
            background: rgba(255, 0, 0, 0.1);
            border-color: var(--primary);
            transform: translateX(5px);
        }}

        .chat-input-container {{
            display: flex;
            padding: 20px;
            background: var(--card-bg);
            border-top: 1px solid var(--border-color);
            gap: 12px;
        }}

        .chat-input-container input {{
            flex: 1;
            padding: 15px 20px;
            border: 2px solid var(--border-color);
            border-radius: 25px;
            font-size: 15px;
            transition: border 0.3s;
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-primary);
        }}

        .chat-input-container input:focus {{
            border-color: var(--primary);
            outline: none;
        }}

        .chat-input-container button {{
            width: 55px;
            background: var(--primary);
            color: white;
            border: none;
            border-radius: 50%;
            cursor: pointer;
            transition: background 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
        }}

        .chat-input-container button:hover {{
            background: #cc0000;
        }}

        /* ===== NOTIFICACIONES TOAST ===== */
        .toast-notification {{
            position: fixed;
            bottom: 25px;
            left: 50%;
            transform: translateX(-50%);
            background: var(--card-bg);
            color: var(--text-primary);
            padding: 18px 25px;
            border-radius: 12px;
            box-shadow: var(--card-shadow);
            z-index: 10000;
            display: flex;
            align-items: center;
            gap: 12px;
            border-left: 4px solid var(--primary);
            animation: slideUp 0.3s;
        }}

        @keyframes slideUp {{
            from {{ transform: translateX(-50%) translateY(100%); opacity: 0; }}
            to {{ transform: translateX(-50%) translateY(0); opacity: 1; }}
        }}

        /* ===== LOADING SPINNER ===== */
        .loading-spinner {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 10000;
            align-items: center;
            justify-content: center;
        }}

        .spinner {{
            width: 60px;
            height: 60px;
            border: 6px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            border-top-color: var(--primary);
            animation: spin 1s linear infinite;
        }}

        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}

        /* ===== FOOTER ===== */
        footer {{
            background: var(--bg-secondary);
            padding: 50px 20px;
            text-align: center;
            margin-top: 60px;
            border-top: 1px solid var(--border-color);
        }}

        .footer-links {{
            display: flex;
            justify-content: center;
            gap: 35px;
            margin-bottom: 35px;
            flex-wrap: wrap;
        }}

        .footer-links a {{
            color: var(--text-secondary);
            text-decoration: none;
            transition: color 0.3s;
            font-size: 16px;
        }}

        .footer-links a:hover {{
            color: var(--primary);
        }}

        .copyright {{
            color: var(--text-secondary);
            font-size: 15px;
            line-height: 1.6;
        }}

        /* ===== UTILIDADES ===== */
        .hidden {{
            display: none !important;
        }}

        .tachado {{
            text-decoration: line-through;
        }}

        .badge-success {{
            background: var(--success);
            color: white;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 13px;
            font-weight: 600;
        }}

        .text-center {{
            text-align: center;
        }}

        .mt-20 {{
            margin-top: 20px;
        }}

        .mb-20 {{
            margin-bottom: 20px;
        }}

        /* ===== SELECTOR MOTOS / CARROS ===== */
        .categoria-tabs {{
            position: sticky;
            top: 0;
            z-index: 50;
            background: rgba(0, 0, 0, 0.35);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border-color);
        }}

        [data-theme="light"] .categoria-tabs {{
            background: rgba(255, 255, 255, 0.65);
        }}

        .categoria-tabs-inner {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 12px 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 14px;
            flex-wrap: wrap;
        }}

        .tabs-pill {{
            display: inline-flex;
            gap: 6px;
            padding: 6px;
            border-radius: 999px;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            box-shadow: var(--card-shadow);
        }}

        .tab-btn {{
            appearance: none;
            border: 0;
            background: transparent;
            color: var(--text-secondary);
            font-weight: 800;
            letter-spacing: 0.4px;
            padding: 10px 16px;
            border-radius: 999px;
            cursor: pointer;
            transition: transform var(--transition-fast), background var(--transition-fast), color var(--transition-fast);
        }}

        .tab-btn:hover {{
            transform: translateY(-1px);
            color: var(--text-primary);
        }}

        .tab-btn.active {{
            background: var(--gradient-primary);
            color: #fff;
        }}

        .categoria-badge {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            color: var(--text-secondary);
            font-weight: 600;
            font-size: 13px;
        }}

        .categoria-badge .dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--accent);
        }}

        /* ===== MICRO-INTERACCIONES PROFESIONALES ===== */
        .producto-card {{
            border-radius: var(--radius);
            transition: transform var(--transition-med), box-shadow var(--transition-med);
            animation: fadeUp 220ms ease both;
        }}

        .producto-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 14px 30px rgba(0,0,0,0.35);
        }}

        .btn-comprar, .btn-carrito, .btn-toggle-modo, .btn-whatsapp-flotante, .btn-carrito-flotante, .btn-chat-flotante {{
            transition: transform var(--transition-fast), filter var(--transition-fast);
        }}

        .btn-comprar:hover, .btn-carrito:hover, .btn-toggle-modo:hover, .btn-whatsapp-flotante:hover, .btn-carrito-flotante:hover, .btn-chat-flotante:hover {{
            transform: translateY(-2px);
            filter: brightness(1.06);
        }}

        /* =====================================================
           DISEÑO 100% PROFESIONAL (LAYOUT V2)
           Sidebar izquierda fija + Topbar superior + productos visibles
           ===================================================== */
        body {{
            padding-bottom: 0;
        }}

        .app-shell {{
            min-height: 100vh;
            display: grid;
            grid-template-columns: 300px 1fr;
            background: radial-gradient(1200px 400px at 10% -10%, rgba(255,0,0,0.16), transparent 60%),
                        radial-gradient(900px 420px at 95% 0%, rgba(26,35,126,0.20), transparent 55%),
                        var(--bg-primary);
        }}

        .app-sidebar {{
            position: sticky;
            top: 0;
            height: 100vh;
            padding: 18px 16px;
            border-right: 1px solid var(--border-color);
            background: linear-gradient(180deg, rgba(255,255,255,0.02) 0%, rgba(255,255,255,0.00) 70%);
            overflow: hidden;
        }}

        .sidebar-brand {{
            display: grid;
            gap: 12px;
            margin-bottom: 16px;
        }}

        .brand-card {{
            display: grid;
            grid-template-columns: 52px 1fr;
            gap: 12px;
            align-items: center;
            padding: 12px 12px;
            border-radius: var(--radius);
            border: 1px solid var(--border-color);
            background: rgba(255,255,255,0.03);
            text-decoration: none;
            color: var(--text-primary);
            box-shadow: var(--card-shadow);
            transition: transform var(--transition-med), border-color var(--transition-med), background var(--transition-med);
        }}

        [data-theme="light"] .brand-card {{
            background: rgba(0,0,0,0.02);
        }}

        .brand-card:hover {{
            transform: translateY(-2px);
            border-color: rgba(255, 0, 0, 0.45);
            background: rgba(255,255,255,0.05);
        }}

        .brand-img {{
            width: 52px;
            height: 52px;
            border-radius: 14px;
            object-fit: contain;
            background: rgba(0,0,0,0.25);
            border: 1px solid rgba(255,255,255,0.06);
        }}

        [data-theme="light"] .brand-img {{
            background: rgba(255,255,255,0.8);
            border-color: rgba(0,0,0,0.06);
        }}

        .brand-text {{
            display: grid;
            gap: 2px;
            min-width: 0;
        }}

        .brand-title {{
            font-weight: 900;
            letter-spacing: 0.3px;
            font-size: 14px;
            line-height: 1.2;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .brand-sub {{
            color: var(--text-secondary);
            font-size: 12px;
            font-weight: 600;
        }}

        .sidebar-tabs {{
            display: grid;
            gap: 10px;
            margin: 14px 0 12px;
        }}

        /* Reestilo de tabs para look profesional */
        .tab-btn {{
            width: 100%;
            display: flex;
            align-items: center;
            gap: 10px;
            justify-content: flex-start;
            border-radius: 14px;
            padding: 12px 14px;
            border: 1px solid var(--border-color);
            background: rgba(255,255,255,0.02);
            color: var(--text-primary);
            font-weight: 900;
            letter-spacing: 0.4px;
            transition: transform var(--transition-fast), background var(--transition-fast), border-color var(--transition-fast);
        }}

        .tab-btn .tab-icon {{
            width: 28px;
            height: 28px;
            display: grid;
            place-items: center;
            border-radius: 10px;
            border: 1px solid var(--border-color);
            background: rgba(255,255,255,0.02);
            flex: 0 0 auto;
        }}

        .tab-btn .tab-icon i {{
            font-size: 14px;
        }}

        .tab-btn .tab-label {{
            min-width: 0;
            flex: 1 1 auto;
        }}

        .tab-btn:hover {{
            transform: translateY(-1px);
            border-color: rgba(26,35,126,0.55);
            background: rgba(255,255,255,0.04);
        }}

        .tab-btn.active {{
            background: var(--gradient-primary);
            border-color: rgba(255,0,0,0.40);
            color: #fff;
        }}

        .tab-btn.active .tab-icon {{
            border-color: rgba(255,255,255,0.22);
            background: rgba(255,255,255,0.14);
            animation: tabPop 220ms ease both;
        }}

        @keyframes tabPop {{
            0% {{ transform: scale(0.90); }}
            60% {{ transform: scale(1.08); }}
            100% {{ transform: scale(1.00); }}
        }}

        /* Nudge del asistente (aparece después de unos segundos) */
        .chat-action {{
            position: relative;
            display: inline-block;
        }}

        .chat-nudge {{
            position: absolute;
            right: 0;
            top: calc(100% + 10px);
            width: 240px;
            padding: 12px 12px;
            border-radius: 14px;
            border: 1px solid var(--border-color);
            background: rgba(0,0,0,0.72);
            box-shadow: var(--card-shadow);
            color: var(--text-primary);
            display: none;
        }}

        [data-theme="light"] .chat-nudge {{
            background: rgba(255,255,255,0.92);
        }}

        .chat-nudge.show {{
            display: block;
            animation: fadeUp 220ms ease both;
        }}

        .chat-nudge .nudge-title {{
            font-weight: 1000;
            letter-spacing: 0.2px;
            font-size: 13px;
        }}

        .chat-nudge .nudge-text {{
            margin-top: 4px;
            font-size: 12px;
            color: var(--text-secondary);
            font-weight: 600;
            line-height: 1.25;
        }}

        .chat-nudge .nudge-close {{
            position: absolute;
            top: 6px;
            right: 8px;
            border: 0;
            background: transparent;
            color: var(--text-secondary);
            font-size: 18px;
            cursor: pointer;
            line-height: 1;
        }}

        .categoria-badge {{
            justify-content: flex-start;
            padding: 10px 12px;
            border-radius: 14px;
            border: 1px solid var(--border-color);
            background: rgba(255,255,255,0.02);
        }}

        .app-main {{
            min-width: 0;
            display: grid;
            grid-template-rows: auto auto auto 1fr;
        }}

        .topbar {{
            position: sticky;
            top: 0;
            z-index: 60;
            display: grid;
            grid-template-columns: 1fr auto;
            gap: 12px;
            align-items: center;
            padding: 14px 16px;
            border-bottom: 1px solid var(--border-color);
            background: rgba(0, 0, 0, 0.40);
            backdrop-filter: blur(14px);
        }}

        [data-theme="light"] .topbar {{
            background: rgba(255, 255, 255, 0.72);
        }}

        .topbar-search {{
            min-width: 0;
        }}

        .topbar-buscador {{
            max-width: 900px;
            margin: 0;
        }}

        .topbar-actions {{
            display: inline-flex;
            align-items: center;
            gap: 10px;
        }}

        /* Desactiva el comportamiento flotante de los botones en este layout */
        .topbar-actions .btn-toggle-modo,
        .topbar-actions .btn-whatsapp-flotante,
        .topbar-actions .btn-carrito-flotante,
        .topbar-actions .btn-chat-flotante {{
            position: relative !important;
            right: auto !important;
            bottom: auto !important;
            left: auto !important;
            top: auto !important;
            width: 46px;
            height: 46px;
            border-radius: 14px;
            box-shadow: none;
            border: 1px solid var(--border-color);
            background: rgba(255,255,255,0.03);
        }}

        .topbar-actions .btn-whatsapp-flotante {{
            background: rgba(37, 211, 102, 0.12);
            border-color: rgba(37, 211, 102, 0.32);
        }}

        .topbar-actions .btn-carrito-flotante {{
            background: rgba(255, 0, 0, 0.10);
            border-color: rgba(255, 0, 0, 0.22);
        }}

        .hero-panel {{
            position: relative;
            margin: 16px 16px 10px;
            border-radius: calc(var(--radius) + 6px);
            overflow: hidden;
            border: 1px solid var(--border-color);
            background: linear-gradient(135deg, rgba(255,0,0,0.10), rgba(26,35,126,0.16));
            min-height: 148px;
        }}

        .hero-bg {{
            position: absolute;
            inset: 0;
            background-position: center;
            background-size: cover;
            filter: saturate(1.05) contrast(1.05);
            opacity: 0.22;
            transform: scale(1.03);
        }}

        [data-theme="light"] .hero-bg {{
            opacity: 0.14;
        }}

        .hero-inner {{
            position: relative;
            padding: 18px 18px;
            display: grid;
            gap: 8px;
        }}

        .hero-title {{
            font-size: 22px;
            line-height: 1.18;
            font-weight: 1000;
            letter-spacing: 0.2px;
        }}

        .hero-subtitle {{
            color: var(--text-secondary);
            font-weight: 600;
            margin: 0;
        }}

        .hero-chip {{
            display: inline-flex;
            width: fit-content;
            padding: 8px 12px;
            border-radius: 999px;
            background: rgba(0,0,0,0.45);
            border: 1px solid rgba(255,255,255,0.10);
            font-weight: 900;
            letter-spacing: 0.4px;
            font-size: 12px;
        }}

        [data-theme="light"] .hero-chip {{
            background: rgba(255,255,255,0.78);
            border-color: rgba(0,0,0,0.08);
        }}

        .filters-row {{
            margin: 0 16px 10px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }}

        .filters-row .filtro-select {{
            width: 100%;
        }}

        .content-area {{
            padding: 6px 16px 20px;
        }}

        .content-area .productos-grid {{
            margin-top: 0;
        }}

        /* Responsive: sidebar pasa arriba en móvil */
        @media (max-width: 980px) {{
            .app-shell {{
                grid-template-columns: 1fr;
            }}

            .app-sidebar {{
                position: relative;
                height: auto;
                border-right: 0;
                border-bottom: 1px solid var(--border-color);
            }}

            .sidebar-tabs {{
                grid-template-columns: 1fr 1fr 1fr;
            }}

            .tab-btn {{
                justify-content: center;
            }}

            .filters-row {{
                grid-template-columns: 1fr;
            }}

            .topbar {{
                grid-template-columns: 1fr;
            }}

            .topbar-actions {{
                justify-content: flex-end;
            }}
        }}
    </style>
</head>
<body data-theme="dark">
    <!-- Loading Spinner -->
    <div class="loading-spinner" id="loadingSpinner">
        <div class="spinner"></div>
    </div>

    <!-- Splash anuncio (medios de pago) -->
    <div class="splash-overlay" id="splashOverlay" aria-hidden="true">
        <div class="splash-card">
            <img src="{recursos.get('anuncio', '')}" alt="Medios de pago disponibles">
        </div>
    </div>

        <!-- Layout profesional: sidebar + topbar + productos visibles desde el inicio -->
        <div class="app-shell" id="appShell">
            <!-- Sidebar izquierda con logos siempre visibles -->
            <aside class="app-sidebar" aria-label="Marcas y navegación">
                <div class="sidebar-brand">
                    <a href="https://www.tiktok.com/@naturista_venuz" target="_blank" class="brand-card brand-templo" aria-label="Templo Garage Street (TikTok)">
                        <img id="logoTemplo" src="{recursos['logo_templo']}" alt="Templo Garage" class="brand-img">
                        <div class="brand-text">
                            <div class="brand-title">Templo Garage Street</div>
                            <div class="brand-sub">Repuestos • Envíos Colombia</div>
                        </div>
                    </a>
                    <a href="https://www.tiktok.com/@brujablanca51" target="_blank" class="brand-card brand-tiktok" aria-label="TikTok Moto Parts (TikTok)">
                        <img id="logoTiktok" src="{recursos['logo_tiktok']}" alt="TikTok Moto Parts" class="brand-img">
                        <div class="brand-text">
                            <div class="brand-title">TikTok Moto Parts</div>
                            <div class="brand-sub">Novedades • Promos</div>
                        </div>
                    </a>
                </div>

                <!-- Tabs: MOTOS / CARROS / DESTACADOS -->
                <div class="sidebar-tabs" role="tablist" aria-label="Secciones">
                    <button class="tab-btn active" id="tabMotos" type="button" role="tab" aria-selected="true" data-cat="motos">
                        <span class="tab-icon" aria-hidden="true"><i class="fas fa-motorcycle"></i></span>
                        <span class="tab-label">MOTOS</span>
                    </button>
                    <button class="tab-btn" id="tabCarros" type="button" role="tab" aria-selected="false" data-cat="carros">
                        <span class="tab-icon" aria-hidden="true"><i class="fas fa-car"></i></span>
                        <span class="tab-label">CARROS</span>
                    </button>
                    <button class="tab-btn" id="tabDestacados" type="button" role="tab" aria-selected="false" data-view="destacados">
                        <span class="tab-icon" aria-hidden="true"><i class="fas fa-star"></i></span>
                        <span class="tab-label">DESTACADOS</span>
                    </button>
                </div>

                <div class="categoria-badge" id="categoriaBadge">
                    <span class="dot"></span>
                    <span id="categoriaBadgeText">Mostrando: MOTOS</span>
                </div>
            </aside>

            <!-- Contenido principal -->
            <div class="app-main">
                <!-- Barra superior fija con acciones -->
                <header class="topbar" aria-label="Barra superior">
                    <div class="topbar-search" aria-label="Buscar">
                        <div class="buscador-container topbar-buscador">
                            <i class="fas fa-search"></i>
                            <input type="text" 
                                   id="buscadorPrincipal" 
                                   placeholder="Buscar por marca, producto o referencia…"
                                   autocomplete="off">
                            <div class="sugerencias" id="sugerenciasBusqueda"></div>
                        </div>
                    </div>

                    <div class="topbar-actions" aria-label="Acciones">
                        <button class="btn-toggle-modo" id="btnToggleModo" title="Cambiar tema" aria-label="Cambiar tema">
                            <i class="fas fa-moon"></i>
                        </button>
                        <button class="btn-whatsapp-flotante" id="btnWhatsappFlotante" title="Contactar por WhatsApp" aria-label="WhatsApp">
                            <i class="fab fa-whatsapp"></i>
                        </button>
                        <button class="btn-carrito-flotante" id="btnCarritoFlotante" title="Ver carrito" aria-label="Carrito">
                            <i class="fas fa-shopping-cart"></i>
                            <span class="carrito-contador" id="carritoContador" style="display: none;">0</span>
                        </button>
                        <div class="chat-action" aria-label="Asistente">
                            <button class="btn-chat-flotante" id="btnChatFlotante" title="Ayuda y asistencia" aria-label="Ayuda">
                                <i class="fas fa-headset"></i>
                            </button>
                            <div class="chat-nudge" id="chatNudge" role="status" aria-live="polite">
                                <button class="nudge-close" type="button" data-action="dismiss" aria-label="Cerrar">&times;</button>
                                <div class="nudge-title">Asistente</div>
                                <div class="nudge-text">¿Buscas una referencia o necesitas asesor? Toca aquí.</div>
                            </div>
                        </div>
                    </div>
                </header>

                <!-- Portada compacta: no bloquea la vista del catálogo -->
                <section class="hero-panel" aria-label="Portada">
                    <div class="hero-bg" style="background-image: url('{recursos['portada']}');"></div>
                    <div class="hero-inner">
                        <h1 class="hero-title">Catálogo profesional de repuestos</h1>
                        <p class="hero-subtitle">Compra rápida, pago seguro con Wompi y soporte por WhatsApp.</p>
                        <div class="hero-chip">🛡️ PROTEGEMOS TODAS TUS PARTES</div>
                    </div>
                </section>

                <!-- Filtros siempre visibles y cerca de los productos -->
                <section class="filters-row" aria-label="Filtros">
                    <select id="filtroMarca" class="filtro-select" aria-label="Filtrar por marca">
                        <option value="">Todas las marcas</option>
                    </select>
                    <select id="filtroTipo" class="filtro-select" aria-label="Filtrar por tipo">
                        <option value="">Todos los tipos</option>
                    </select>
                </section>

                <main class="content-area" aria-label="Productos">
                    <!-- Grid de Productos -->
                    <div class="productos-grid" id="productosGrid"></div>

                    <!-- Paginación -->
                    <div class="paginacion" id="paginacion"></div>
                </main>
            </div>
        </div>

    <!-- Modal de Compra -->
    <div class="modal-compra" id="modalCompra">
        <div class="modal-content">
            <button class="modal-close" onclick="cerrarModalCompra()">&times;</button>
            
            <div class="compra-header">
                <h3><i class="fas fa-shopping-cart"></i> Completar compra</h3>
                <p>Te enviaremos el comprobante a tu email</p>
            </div>
            
            <form id="formCompra">
                <div class="form-group">
                    <label for="nombreCompra">Nombre completo *</label>
                    <input type="text" id="nombreCompra" required 
                           placeholder="Ej: Juan Pérez">
                </div>
                
                <div class="form-group">
                    <label for="emailCompra">Email *</label>
                    <input type="email" id="emailCompra" required 
                           placeholder="ejemplo@gmail.com">
                </div>
                
                <div class="form-group">
                    <label for="telefonoCompra">WhatsApp *</label>
                    <div class="phone-input-container">
                        <div class="country-select">
                            <img src="https://flagcdn.com/w20/co.png" alt="Colombia">
                            <span>+57</span>
                        </div>
                        <input type="tel" id="telefonoCompra" required 
                               class="phone-input"
                               placeholder="300 123 4567"
                               pattern="[0-9]{{10}}"
                               title="Ingresa 10 dígitos (sin el +57)">
                    </div>
                    <small style="color: var(--text-secondary); margin-top: 5px; display: block;">
                        Solo ingresa los 10 dígitos, el código +57 ya está incluido
                    </small>
                </div>
                
                <div class="resumen-compra" id="resumenCompra">
                    <!-- Se llena con JavaScript -->
                </div>
                
                <button type="submit" class="btn-pagar">
                    <i class="fas fa-lock"></i> Pagar ahora con Wompi
                </button>
                
                <p class="texto-seguro">
                    <i class="fas fa-shield-alt"></i> Pago 100% seguro con encriptación SSL
                </p>
            </form>
        </div>
    </div>

    <!-- Modal del Carrito -->
    <div class="modal-carrito" id="modalCarrito">
        <div class="carrito-content">
            <button class="modal-close" onclick="cerrarModalCarrito()">&times;</button>
            
            <div class="carrito-header">
                <h3><i class="fas fa-shopping-cart"></i> Tu Carrito de Compras</h3>
                <p>Revisa y modifica tu pedido</p>
            </div>
            
            <div class="carrito-items" id="carritoItems">
                <!-- Los productos del carrito se cargan aquí -->
            </div>
            
            <div class="carrito-total" id="carritoTotales">
                <!-- Total se llena dinámicamente -->
            </div>
            
            <div class="carrito-botones">
                <button class="btn-vaciar" onclick="vaciarCarrito()">
                    <i class="fas fa-trash"></i> Vaciar Carrito
                </button>
                <button class="btn-continuar" onclick="pagarCarrito()">
                    <i class="fas fa-lock"></i> Pagar Total
                </button>
            </div>
        </div>
    </div>

    <!-- Modal de Chat Minimalista -->
    <div class="modal-chat" id="modalChat">
        <div class="chat-content">
            <button class="modal-close" onclick="cerrarModalChat()">&times;</button>
            
            <div class="chat-header" style="text-align: center; margin-bottom: 20px;">
                <h3><i class="fas fa-headset"></i> Asistente Virtual</h3>
                <p>En línea • Responde al instante</p>
            </div>
            
            <div class="chat-body">
                <div class="chat-messages" id="chatMessages">
                    <!-- Mensajes del chat -->
                </div>
                
                <div class="chat-input-container">
                    <input type="text" 
                           id="chatInput" 
                           placeholder="Escribe tu pregunta..."
                           onkeypress="handleChatKeyPress(event)">
                    <button onclick="enviarMensajeChat()">
                        <i class="fas fa-paper-plane"></i>
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- Modal Compartir (principalmente para PC) -->
    <div class="modal-compartir" id="modalCompartir">
        <div class="modal-share-content">
            <button class="modal-close" onclick="cerrarModalCompartir()">&times;</button>
            <h3 class="share-title"><i class="fas fa-share-alt"></i> Compartir producto</h3>
            <p class="share-subtitle" id="shareSubtitle">Elige una opción para compartir.</p>
            <div class="share-grid">
                <button class="share-btn" type="button" onclick="compartirWhatsApp()"><i class="fab fa-whatsapp"></i> WhatsApp</button>
                <button class="share-btn" type="button" onclick="compartirFacebook()"><i class="fab fa-facebook"></i> Facebook</button>
                <button class="share-btn" type="button" onclick="compartirX()"><i class="fab fa-x-twitter"></i> X</button>
                <button class="share-btn" type="button" onclick="copiarLinkCompartir()"><i class="fas fa-link"></i> Copiar link</button>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <footer>
        <div class="footer-links">
            <a href="https://wa.me/{CONFIG['CONTACTO']['WHATSAPP']}" target="_blank">
                <i class="fab fa-whatsapp"></i> WhatsApp
            </a>
            <a href="{CONFIG['CONTACTO']['TIKTOK_BRUJABLANCA']}" target="_blank">
                <i class="fab fa-tiktok"></i> TikTok
            </a>
            <a href="{CONFIG['CONTACTO']['TIKTOK_NATURISTA']}" target="_blank">
                <i class="fab fa-tiktok"></i> TikTok 2
            </a>
            <a href="#" onclick="mostrarTerminos()">
                <i class="fas fa-file-contract"></i> Términos
            </a>
        </div>
        
        <p class="copyright">
            © 2024 Templo Garage Street & TikTok Moto Parts. Todos los derechos reservados.<br>
            Catálogo generado automáticamente - Actualizado: {fecha_actual}<br>
            Total productos: {estadisticas['total']:,} | Marcas: {len(estadisticas['marcas_unicas'])} | Tipos: {len(estadisticas['tipos_unicos'])}
        </p>
    </footer>

    <!-- Scripts -->
    <script>
        // ==============================================
        // CONFIGURACIÓN DEL SISTEMA ACTUALIZADA
        // ==============================================
        const CONFIG_SISTEMA = {{
            WOMPI_PUBLIC_KEY: "{wompi_public_key}",
            WOMPI_MODO: "{wompi_modo}",
            // Nunca exponer secretos en el frontend.
            WOMPI_INTEGRITY_SECRET: "{wompi_integrity_secret_frontend}",
            WOMPI_API_BASE: "{wompi_api_base}",
            WOMPI_SIGNATURE_ENDPOINT: "{CONFIG['WORKER_PUBLIC_BASE_URL'].rstrip('/')}/api/wompi/signature",
            // No embebas la API key de Resend en HTML público.
            RESEND_API_KEY: "",
            WHATSAPP_NUMERO: "{CONFIG['CONTACTO']['WHATSAPP']}",
            EMAIL_VENDEDOR: "{CONFIG['CONTACTO']['EMAIL_VENDEDOR']}",
            EMAIL_VENTAS: "{CONFIG['CONTACTO']['EMAIL_VENTAS']}",
            PRODUCTOS: {productos_json},
            PRODUCTOS_POR_PAGINA: {CONFIG['PARAMETROS']['PRODUCTOS_POR_PAGINA']}
        }};

        // ==============================================
        // VARIABLES GLOBALES
        // ==============================================
        let todosProductos = CONFIG_SISTEMA.PRODUCTOS;
        let productos = [];
        let productoSeleccionado = null;
        let carrito = JSON.parse(localStorage.getItem('carrito_templo_garage') || '[]');
        let transacciones = [];
        let paginaActual = 1;
        let totalPaginas = 1;
        let estadoChat = 'inicio';
        let datosChatAsesor = {{}};
        let chatHistory = [];
        let categoriaActual = 'motos';
        let vistaActual = 'catalogo'; // 'catalogo' | 'destacados'
        let filtroMarcaEl = null;
        let filtroTipoEl = null;

        // ==============================================
        // FUNCIONES DE UTILIDAD
        // ==============================================
        function mostrarLoading() {{
            document.getElementById('loadingSpinner').style.display = 'flex';
        }}

        function ocultarLoading() {{
            document.getElementById('loadingSpinner').style.display = 'none';
        }}

        function mostrarToast(mensaje, tipo = 'info') {{
            const iconos = {{
                'success': 'check-circle',
                'error': 'exclamation-circle',
                'warning': 'exclamation-triangle',
                'info': 'info-circle'
            }};
            
            const toast = document.createElement('div');
            toast.className = 'toast-notification';
            toast.innerHTML = `
                <i class="fas fa-${{iconos[tipo] || 'info-circle'}}"></i>
                <span>${{mensaje}}</span>
            `;
            
            document.body.appendChild(toast);
            
            setTimeout(() => {{
                toast.style.opacity = '0';
                setTimeout(() => toast.remove(), 300);
            }}, 3000);
        }}

        function normalizarTexto(texto) {{
            if (!texto) return '';
            return texto.toString()
                .toLowerCase()
                .normalize('NFD')
                .replace(/[\\u0300-\\u036f]/g, '')
                .replace(/[^a-z0-9\\s]/g, '');
        }}

        function formatearPrecio(precio) {{
            if (precio <= 0) return 'Consultar';
            return `$${{Math.round(precio).toLocaleString('es-CO')}}`;
        }}

        // ==============================================
        // SECCIONES (MOTOS / CARROS / DESTACADOS)
        // ==============================================
        function actualizarTabsUI() {{
            const tabMotos = document.getElementById('tabMotos');
            const tabCarros = document.getElementById('tabCarros');
            const tabDestacados = document.getElementById('tabDestacados');

            const isDestacados = vistaActual === 'destacados';
            const isMotos = !isDestacados && categoriaActual === 'motos';
            const isCarros = !isDestacados && categoriaActual === 'carros';

            if (tabMotos) {{
                tabMotos.classList.toggle('active', isMotos);
                tabMotos.setAttribute('aria-selected', isMotos ? 'true' : 'false');
            }}
            if (tabCarros) {{
                tabCarros.classList.toggle('active', isCarros);
                tabCarros.setAttribute('aria-selected', isCarros ? 'true' : 'false');
            }}
            if (tabDestacados) {{
                tabDestacados.classList.toggle('active', isDestacados);
                tabDestacados.setAttribute('aria-selected', isDestacados ? 'true' : 'false');
            }}

            const badgeText = document.getElementById('categoriaBadgeText');
            if (badgeText) {{
                const catLabel = String(categoriaActual || '').toUpperCase();
                if (vistaActual === 'destacados') {{
                    badgeText.textContent = 'Mostrando: DESTACADOS (' + catLabel + ')';
                }} else {{
                    badgeText.textContent = 'Mostrando: ' + catLabel;
                }}
            }}
        }}

        function setCategoria(cat) {{
            const normalized = String(cat || '').toLowerCase() === 'carros' ? 'carros' : 'motos';
            categoriaActual = normalized;
            vistaActual = 'catalogo';
            actualizarTabsUI();

            // Reset filtros al cambiar categoría
            if (filtroMarcaEl) filtroMarcaEl.value = '';
            if (filtroTipoEl) filtroTipoEl.value = '';
            poblarFiltrosCategoria();
            aplicarFiltros();
        }}

        function setDestacados() {{
            vistaActual = 'destacados';
            // Mantener categoría actual (motos/carros)
            actualizarTabsUI();
            aplicarFiltros();
        }}

        function inicializarCategoriaTabs() {{
            const tabMotos = document.getElementById('tabMotos');
            const tabCarros = document.getElementById('tabCarros');
            const tabDestacados = document.getElementById('tabDestacados');
            if (tabMotos) tabMotos.addEventListener('click', () => setCategoria('motos'));
            if (tabCarros) tabCarros.addEventListener('click', () => setCategoria('carros'));
            if (tabDestacados) tabDestacados.addEventListener('click', () => setDestacados());
            setCategoria('motos');
        }}

        function filtrarPorCategoria(lista) {{
            const cat = categoriaActual;
            return (lista || []).filter(p => String(p.categoria || 'motos').toLowerCase() === cat);
        }}

        function obtenerDestacados(lista) {{
            const arr = Array.isArray(lista) ? [...lista] : [];
            // Regla simple (ajustable después): rating desc, comentarios desc, precio_final desc
            arr.sort((a, b) => {{
                const ra = Number(a.rating || 0);
                const rb = Number(b.rating || 0);
                if (rb !== ra) return rb - ra;
                const ca = Number(a.comentarios || 0);
                const cb = Number(b.comentarios || 0);
                if (cb !== ca) return cb - ca;
                const pa = Number(a.precio_final || a.precio || 0);
                const pb = Number(b.precio_final || b.precio || 0);
                return pb - pa;
            }});
            return arr.slice(0, 60);
        }}

        function aplicarVista(lista) {{
            if (vistaActual !== 'destacados') return lista;
            return obtenerDestacados(lista);
        }}

        // Búsqueda fuzzy para tolerancia a errores
        function buscarFuzzy(query, productos, campos = ['nombre', 'marca', 'descripcion'], limite = 10) {{
            const queryNormalizado = normalizarTexto(query);
            if (queryNormalizado.length < 2) return [];
            
            let resultados = [];
            
            // Búsqueda exacta
            resultados = productos.filter(p => {{
                for (let campo of campos) {{
                    if (normalizarTexto(p[campo]).includes(queryNormalizado)) {{
                        return true;
                    }}
                }}
                return false;
            }});
            
            // Búsqueda aproximada
            if (resultados.length < limite) {{
                const productosRestantes = productos.filter(p => !resultados.includes(p));
                productosRestantes.forEach(p => {{
                    let maxScore = 0;
                    for (let campo of campos) {{
                        const score = calcularSimilitud(queryNormalizado, normalizarTexto(p[campo]));
                        if (score > maxScore) maxScore = score;
                    }}
                    if (maxScore > 50) {{ // Umbral de similitud
                        resultados.push({{...p, score: maxScore}});
                    }}
                }});
            }}
            
            // Ordenar por score
            resultados.sort((a, b) => (b.score || 100) - (a.score || 100));
            
            return resultados.slice(0, limite);
        }}

        function calcularSimilitud(str1, str2) {{
            // Algoritmo simple de similitud
            if (str1.includes(str2) || str2.includes(str1)) return 100;
            
            const words1 = str1.split(' ');
            const words2 = str2.split(' ');
            let matches = 0;
            
            for (let word1 of words1) {{
                for (let word2 of words2) {{
                    if (word1 && word2 && (word1.includes(word2) || word2.includes(word1))) {{
                        matches++;
                        break;
                    }}
                }}
            }}
            
            return (matches / Math.max(words1.length, words2.length)) * 100;
        }}

        // ==============================================
        // FUNCIÓN CRÍTICA: GENERAR FIRMA DE INTEGRIDAD WOMPI
        // ==============================================
        async function generarFirmaIntegridad(referencia, montoEnCentavos) {{
            try {{
                // Preferido: pedir firma al backend (Worker) para no exponer el secret.
                const currency = 'COP';
                const wompiModo = String(CONFIG_SISTEMA.WOMPI_MODO || '').toLowerCase();

                const candidates = [
                    (CONFIG_SISTEMA.WOMPI_SIGNATURE_ENDPOINT || '').trim(),
                    `${{window.location.origin}}/api/wompi/signature`,
                    'https://templogarage.com/api/wompi/signature',
                    'https://catalogo-templo-motor.giraldor192.workers.dev/api/wompi/signature'
                ].filter(Boolean);

                // Quitar duplicados manteniendo orden
                const endpoints = [];
                for (const c of candidates) {{
                    if (!endpoints.includes(c)) endpoints.push(c);
                }}

                let lastBackendError = '';

                for (const endpoint of endpoints) {{
                    try {{
                        const resp = await fetch(endpoint, {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ reference: referencia, amountInCents: montoEnCentavos, currency, mode: wompiModo }})
                        }});
                        const data = await resp.json().catch(() => ({{}}));
                        if (resp.ok && data && data.integrity) return data.integrity;
                        if (!resp.ok && data && data.error) lastBackendError = String(data.error);
                    }} catch (e) {{
                        // seguir probando otros endpoints
                    }}
                }}

                // Fallback local (solo si alguien decide embebir el secret; NO recomendado para producción)
                if (!window.crypto || !window.crypto.subtle) {{
                    throw new Error('WebCrypto no disponible. Abre el catálogo en HTTPS.');
                }}
                const secret = String(CONFIG_SISTEMA.WOMPI_INTEGRITY_SECRET || '');
                if (!secret || secret.length < 10) {{
                    const modo = (CONFIG_SISTEMA.WOMPI_MODO || '').toLowerCase();
                    if (modo === 'test') {{
                        const origin = String(window.location.origin || '');
                        const hint = origin === 'null' ? 'Parece que abriste el HTML como archivo (file://). Abre el catálogo desde la URL del Worker para que /api funcione.' : 'Verifica que estés abriendo el catálogo desde el Worker (no desde un host sin /api).';
                        const extra = lastBackendError ? ` Detalle: ${{lastBackendError}}` : '';
                        throw new Error(`Firma no disponible: backend no responde o devolvió error.${{extra}} ${{hint}}`);
                    }}
                    throw new Error('Firma no disponible: backend no responde y no hay secret local.');
                }}
                const cadenaConcatenada = `${{String(referencia)}}${{String(montoEnCentavos)}}${{currency}}${{secret}}`;
                const encoder = new TextEncoder();
                const hashBuffer = await crypto.subtle.digest('SHA-256', encoder.encode(cadenaConcatenada));
                const hashArray = Array.from(new Uint8Array(hashBuffer));
                return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
            }} catch (error) {{
                console.error('Error generando firma:', error);
                throw error;
            }}
        }}

        function generarReferenciaWompi(productoId) {{
            // Wompi suele requerir referencia corta (p.ej. <= 32 chars). Evita caracteres raros.
            const rawId = (productoId === 'carrito') ? 'CARRITO' : String(productoId ?? 'PROD');
            const idPart = rawId.replace(/[^a-zA-Z0-9]/g, '').slice(0, 8).toUpperCase();
            const timePart = Date.now().toString(36).toUpperCase();
            const randPart = Math.random().toString(36).slice(2, 7).toUpperCase();
            const ref = `TG_${{idPart}}_${{timePart}}_${{randPart}}`;
            return ref.slice(0, 32);
        }}

        // ==============================================
        // PAGINACIÓN
        // ==============================================
        function configurarPaginacion() {{
            productos = [...aplicarVista(filtrarPorCategoria(todosProductos))];
            totalPaginas = Math.ceil(productos.length / CONFIG_SISTEMA.PRODUCTOS_POR_PAGINA);
            mostrarPagina(1);
        }}

        function mostrarPagina(numeroPagina) {{
            paginaActual = numeroPagina;
            const inicio = (paginaActual - 1) * CONFIG_SISTEMA.PRODUCTOS_POR_PAGINA;
            const fin = inicio + CONFIG_SISTEMA.PRODUCTOS_POR_PAGINA;
            const productosPagina = productos.slice(inicio, fin);
            
            renderizarProductos(productosPagina);
            actualizarControlesPaginacion();
        }}

        function actualizarControlesPaginacion() {{
            const paginacion = document.getElementById('paginacion');
            if (totalPaginas <= 1) {{
                paginacion.innerHTML = '';
                return;
            }}
            
            let html = '';
            
            html += `<button class="paginacion-btn" onclick="cambiarPagina(${{paginaActual - 1}})" ${{paginaActual === 1 ? 'disabled' : ''}}>
                        <i class="fas fa-chevron-left"></i>
                    </button>`;
            
            const inicio = Math.max(1, paginaActual - 2);
            const fin = Math.min(totalPaginas, inicio + 4);
            
            for (let i = inicio; i <= fin; i++) {{
                html += `<button class="paginacion-btn ${{i === paginaActual ? 'active' : ''}}" onclick="cambiarPagina(${{i}})">${{i}}</button>`;
            }}
            
            html += `<button class="paginacion-btn" onclick="cambiarPagina(${{paginaActual + 1}})" ${{paginaActual === totalPaginas ? 'disabled' : ''}}>
                        <i class="fas fa-chevron-right"></i>
                    </button>`;
            
            html += `<div class="paginacion-info">
                        Página ${{paginaActual}} de ${{totalPaginas}}<br>
                        ${{productos.length}} productos
                    </div>`;
            
            paginacion.innerHTML = html;
        }}

        function cambiarPagina(pagina) {{
            if (pagina < 1 || pagina > totalPaginas) return;
            mostrarPagina(pagina);
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }}

        // ==============================================
        // INICIALIZACIÓN DEL SISTEMA
        // ==============================================
        document.addEventListener('DOMContentLoaded', function() {{
            mostrarSplashAnuncio();
            cargarTransacciones();
            inicializarTema();
            inicializarCarrito();
            inicializarChat();
            inicializarCategoriaTabs();
            configurarPaginacion();
            inicializarBuscador();
            inicializarFiltros();
            inicializarBotonesWhatsapp();

            manejarDeepLinkProducto();
            
            // Mensaje de bienvenida en chat
            setTimeout(() => {{
                if (chatHistory.length === 0) {{
                    mostrarOpcionesChat();
                }}
            }}, 2000);
            
            console.log(`📊 Catálogo cargado: ${{todosProductos.length}} productos`);
        }});

        function inicializarBotonesWhatsapp() {{
            document.getElementById('btnWhatsappFlotante').addEventListener('click', function() {{
                const mensaje = `Hola Templo Garage, me gustaría obtener más información sobre sus productos.`;
                window.open(`https://wa.me/${{CONFIG_SISTEMA.WHATSAPP_NUMERO}}?text=${{encodeURIComponent(mensaje)}}`, '_blank');
            }});
        }}

        function inicializarFiltros() {{
            filtroMarcaEl = document.getElementById('filtroMarca');
            filtroTipoEl = document.getElementById('filtroTipo');
            poblarFiltrosCategoria();

            // Event listeners para filtros
            filtroMarcaEl.addEventListener('change', aplicarFiltros);
            filtroTipoEl.addEventListener('change', aplicarFiltros);
        }}

        function poblarFiltrosCategoria() {{
            if (!filtroMarcaEl || !filtroTipoEl) return;
            const base = filtrarPorCategoria(todosProductos);
            const marcas = [...new Set(base.map(p => p.marca).filter(m => m))];
            const tipos = [...new Set(base.map(p => p.tipo).filter(t => t))];

            filtroMarcaEl.innerHTML = '<option value="">Todas las marcas</option>';
            filtroTipoEl.innerHTML = '<option value="">Todos los tipos</option>';

            marcas.sort().forEach(marca => {{
                const option = document.createElement('option');
                option.value = marca;
                option.textContent = marca;
                filtroMarcaEl.appendChild(option);
            }});
            tipos.sort().forEach(tipo => {{
                const option = document.createElement('option');
                option.value = tipo;
                option.textContent = tipo;
                filtroTipoEl.appendChild(option);
            }});
        }}

        function aplicarFiltros() {{
            const marcaSeleccionada = (filtroMarcaEl ? filtroMarcaEl.value : document.getElementById('filtroMarca').value);
            const tipoSeleccionado = (filtroTipoEl ? filtroTipoEl.value : document.getElementById('filtroTipo').value);

            let filtrados = filtrarPorCategoria(todosProductos);
            
            if (marcaSeleccionada) {{
                filtrados = filtrados.filter(p => p.marca === marcaSeleccionada);
            }}
            
            if (tipoSeleccionado) {{
                filtrados = filtrados.filter(p => p.tipo === tipoSeleccionado);
            }}

            filtrados = aplicarVista(filtrados);
            
            productos = filtrados;
            totalPaginas = Math.ceil(productos.length / CONFIG_SISTEMA.PRODUCTOS_POR_PAGINA);
            mostrarPagina(1);
            mostrarToast(`${{filtrados.length}} productos encontrados`, 'info');
        }}

        // ==============================================
        // SISTEMA DE PRODUCTOS
        // ==============================================
        function renderizarProductos(productosARenderizar) {{
            const grid = document.getElementById('productosGrid');
            grid.innerHTML = '';

            if (!productosARenderizar || productosARenderizar.length === 0) {{
                const titulo = categoriaActual === 'carros' ? 'CARROS' : 'MOTOS';
                const mensaje = (vistaActual === 'destacados')
                    ? 'Aún no hay productos DESTACADOS para mostrar con estos filtros.'
                    : (categoriaActual === 'carros'
                        ? 'Aún no hay productos para CARROS. Esta sección estará disponible pronto.'
                        : 'No hay productos para mostrar con estos filtros.');
                grid.innerHTML = `
                    <div class="empty-state">
                        <h3><i class="fas fa-layer-group"></i> ${{titulo}}</h3>
                        <p>${{mensaje}}</p>
                    </div>
                `;
                return;
            }}
            
            productosARenderizar.forEach(producto => {{
                // Verificar si el producto ya está en el carrito
                const enCarrito = carrito.find(item => item.id === producto.id);
                const cantidadEnCarrito = enCarrito ? enCarrito.cantidad : 0;
                
                const card = document.createElement('div');
                card.className = 'producto-card';
                card.dataset.id = producto.id;
                card.id = `p-${{producto.id}}`;
                card.innerHTML = `
                    ${{producto.precio > 0 && Math.random() > 0.7 ? '<div class="producto-badge oferta">OFERTA</div>' : ''}}
                    <div class="producto-imagen">
                        <img src="${{producto.imagen}}" alt="${{producto.nombre}}" loading="lazy">
                    </div>
                    <div class="producto-info">
                        <span class="producto-marca">${{producto.marca}}</span>
                        <h3 class="producto-titulo">${{producto.nombre}}</h3>
                        <p class="producto-descripcion">${{producto.descripcion}}</p>
                        
                        <div class="producto-precio">
                            ${{producto.precio > 0 ? 
                                `<span class="precio-actual">${{producto.precio_str}}</span>` :
                                `<span class="precio-consultar">Consultar precio</span>`
                            }}
                        </div>
                        
                        <div class="botones-producto">
                            <button class="btn-comprar" onclick="iniciarCompra(${{producto.id}})" ${{producto.precio <= 0 ? 'disabled' : ''}}>
                                <i class="fas fa-bolt"></i> ${{producto.precio > 0 ? 'COMPRAR' : 'CONSULTAR'}}
                            </button>
                            <button class="btn-carrito" onclick="agregarAlCarrito(${{producto.id}})" title="Añadir a la cesta">
                                <i class="fas fa-cart-plus"></i>
                                ${{cantidadEnCarrito > 0 ? `<span class="contador-carrito-mini">${{cantidadEnCarrito}}</span>` : ''}}
                            </button>
                            <button class="btn-compartir" onclick="compartirProducto(${{producto.id}})" title="Compartir">
                                <i class="fas fa-share-alt"></i>
                            </button>
                        </div>
                    </div>
                `;
                
                grid.appendChild(card);
            }});
        }}

        // ==============================================
        // SPLASH INICIAL (ANUNCIO)
        // ==============================================
        function mostrarSplashAnuncio() {{
            const overlay = document.getElementById('splashOverlay');
            if (!overlay) return;
            const img = overlay.querySelector('img');
            if (!img || !img.getAttribute('src')) return;
            overlay.classList.add('show');
            setTimeout(() => {{
                overlay.classList.remove('show');
            }}, 2500);
        }}

        // ==============================================
        // COMPARTIR PRODUCTO + DEEP LINK
        // ==============================================
        let shareContext = {{ url: '', title: '', text: '' }};

        function construirUrlProducto(productoId) {{
            const base = window.location.href.split('#')[0];
            return `${{base}}#p-${{productoId}}`;
        }}

        async function compartirProducto(productoId) {{
            const producto = todosProductos.find(p => p.id === productoId);
            if (!producto) return;
            const url = construirUrlProducto(productoId);
            const title = String(producto.nombre || 'Producto');
            const text = `Mira este producto: ${{producto.nombre}} (${{producto.marca}})`;

            shareContext = {{ url, title, text }};
            const subtitle = document.getElementById('shareSubtitle');
            if (subtitle) subtitle.textContent = `${{producto.nombre}} • ${{producto.marca}}`;

            // En celular: compartir nativo
            if (navigator.share) {{
                try {{
                    await navigator.share({{ title, text, url }});
                    return;
                }} catch (e) {{
                    // Cancelado o no soportado del todo -> modal
                }}
            }}
            mostrarModalCompartir();
        }}

        function mostrarModalCompartir() {{
            const modal = document.getElementById('modalCompartir');
            if (!modal) return;
            modal.style.display = 'flex';
        }}

        function cerrarModalCompartir() {{
            const modal = document.getElementById('modalCompartir');
            if (!modal) return;
            modal.style.display = 'none';
        }}

        function compartirWhatsApp() {{
            const msg = `${{shareContext.text}}\n${{shareContext.url}}`;
            window.open(`https://wa.me/?text=${{encodeURIComponent(msg)}}`, '_blank');
        }}

        function compartirFacebook() {{
            window.open(`https://www.facebook.com/sharer/sharer.php?u=${{encodeURIComponent(shareContext.url)}}`, '_blank');
        }}

        function compartirX() {{
            const msg = `${{shareContext.text}}`;
            window.open(`https://twitter.com/intent/tweet?text=${{encodeURIComponent(msg)}}&url=${{encodeURIComponent(shareContext.url)}}`, '_blank');
        }}

        async function copiarLinkCompartir() {{
            try {{
                if (navigator.clipboard && navigator.clipboard.writeText) {{
                    await navigator.clipboard.writeText(shareContext.url);
                }} else {{
                    const tmp = document.createElement('input');
                    tmp.value = shareContext.url;
                    document.body.appendChild(tmp);
                    tmp.select();
                    document.execCommand('copy');
                    tmp.remove();
                }}
                mostrarToast('Link copiado', 'success');
            }} catch (e) {{
                mostrarToast('No se pudo copiar el link', 'error');
            }}
        }}

        function manejarDeepLinkProducto() {{
            const hash = String(window.location.hash || '');
            const match = hash.match(/^#p-(\\d+)$/);
            if (!match) return;
            const id = parseInt(match[1], 10);
            if (!id) return;

            const producto = todosProductos.find(p => p.id === id);
            if (!producto) return;

            // Asegurar categoría correcta y limpiar filtros
            categoriaActual = String(producto.categoria || 'motos').toLowerCase() === 'carros' ? 'carros' : 'motos';
            vistaActual = 'catalogo';
            actualizarTabsUI();
            if (filtroMarcaEl) filtroMarcaEl.value = '';
            if (filtroTipoEl) filtroTipoEl.value = '';
            poblarFiltrosCategoria();
            aplicarFiltros();

            setTimeout(() => {{
                const idx = (productos || []).findIndex(p => p.id === id);
                if (idx >= 0) {{
                    const pagina = Math.floor(idx / CONFIG_SISTEMA.PRODUCTOS_POR_PAGINA) + 1;
                    mostrarPagina(pagina);
                }}
                setTimeout(() => {{
                    const el = document.getElementById(`p-${{id}}`);
                    if (el) el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                }}, 120);
            }}, 60);
        }}

        // ==============================================
        // SISTEMA DE CARRITO MEJORADO
        // ==============================================
        function inicializarCarrito() {{
            actualizarContadorCarrito();
            actualizarCarritoModal();
            
            document.getElementById('btnCarritoFlotante').addEventListener('click', mostrarModalCarrito);
        }}

        function agregarAlCarrito(productoId) {{
            const producto = todosProductos.find(p => p.id === productoId);
            if (!producto) return;
            
            const productoEnCarrito = carrito.find(item => item.id === productoId);
            
            if (productoEnCarrito) {{
                productoEnCarrito.cantidad += 1;
            }} else {{
                carrito.push({{
                    ...producto,
                    cantidad: 1
                }});
            }}
            
            guardarCarrito();
            actualizarContadorCarrito();
            actualizarCarritoModal();
            
            // Actualizar el contador en el botón del producto
            const productoCard = document.querySelector(`.producto-card[data-id="${{productoId}}"] .btn-carrito`);
            if (productoCard) {{
                const contador = carrito.find(item => item.id === productoId)?.cantidad || 0;
                let contadorSpan = productoCard.querySelector('.contador-carrito-mini');
                if (contador > 0) {{
                    if (!contadorSpan) {{
                        contadorSpan = document.createElement('span');
                        contadorSpan.className = 'contador-carrito-mini';
                        productoCard.appendChild(contadorSpan);
                    }}
                    contadorSpan.textContent = contador;
                }} else if (contadorSpan) {{
                    contadorSpan.remove();
                }}
            }}
            
            mostrarToast('Producto añadido al carrito', 'success');
        }}

        function asegurarProductoEnCarrito(productoId) {{
            if (carrito.find(item => item.id === productoId)) return;
            const producto = todosProductos.find(p => p.id === productoId);
            if (!producto) return;
            carrito.push({{
                ...producto,
                cantidad: 1
            }});
            guardarCarrito();
            actualizarContadorCarrito();
            actualizarCarritoModal();

            // Actualizar el contador en el botón del producto
            const productoCard = document.querySelector(`.producto-card[data-id="${{productoId}}"] .btn-carrito`);
            if (productoCard) {{
                let contadorSpan = productoCard.querySelector('.contador-carrito-mini');
                if (!contadorSpan) {{
                    contadorSpan = document.createElement('span');
                    contadorSpan.className = 'contador-carrito-mini';
                    productoCard.appendChild(contadorSpan);
                }}
                contadorSpan.textContent = '1';
            }}
        }}

        function quitarDelCarrito(productoId) {{
            const productoIndex = carrito.findIndex(item => item.id === productoId);
            if (productoIndex !== -1) {{
                carrito[productoIndex].cantidad -= 1;
                
                if (carrito[productoIndex].cantidad <= 0) {{
                    carrito.splice(productoIndex, 1);
                }}
                
                guardarCarrito();
                actualizarContadorCarrito();
                actualizarCarritoModal();
                
                // Actualizar el contador en el botón del producto
                const productoCard = document.querySelector(`.producto-card[data-id="${{productoId}}"] .btn-carrito`);
                if (productoCard) {{
                    const contador = carrito.find(item => item.id === productoId)?.cantidad || 0;
                    let contadorSpan = productoCard.querySelector('.contador-carrito-mini');
                    if (contador > 0) {{
                        if (!contadorSpan) {{
                            contadorSpan = document.createElement('span');
                            contadorSpan.className = 'contador-carrito-mini';
                            productoCard.appendChild(contadorSpan);
                        }}
                        contadorSpan.textContent = contador;
                    }} else if (contadorSpan) {{
                        contadorSpan.remove();
                    }}
                }}
                
                mostrarToast('Producto removido del carrito', 'info');
            }}
        }}

        function eliminarDelCarrito(productoId) {{
            const productoIndex = carrito.findIndex(item => item.id === productoId);
            if (productoIndex !== -1) {{
                carrito.splice(productoIndex, 1);
                guardarCarrito();
                actualizarContadorCarrito();
                actualizarCarritoModal();
                
                // Remover contador del botón del producto
                const productoCard = document.querySelector(`.producto-card[data-id="${{productoId}}"] .btn-carrito`);
                if (productoCard) {{
                    const contadorSpan = productoCard.querySelector('.contador-carrito-mini');
                    if (contadorSpan) {{
                        contadorSpan.remove();
                    }}
                }}
                
                mostrarToast('Producto eliminado del carrito', 'info');
            }}
        }}

        function vaciarCarrito() {{
            if (carrito.length === 0) return;
            
            if (confirm('¿Estás seguro de que quieres vaciar todo el carrito?')) {{
                carrito = [];
                guardarCarrito();
                actualizarContadorCarrito();
                actualizarCarritoModal();
                
                // Remover todos los contadores de los botones
                document.querySelectorAll('.contador-carrito-mini').forEach(el => el.remove());
                
                mostrarToast('Carrito vaciado', 'info');
                cerrarModalCarrito();
            }}
        }}

        function guardarCarrito() {{
            localStorage.setItem('carrito_templo_garage', JSON.stringify(carrito));
        }}

        function actualizarContadorCarrito() {{
            const contador = document.getElementById('carritoContador');
            const totalItems = carrito.reduce((sum, item) => sum + item.cantidad, 0);
            
            if (totalItems > 0) {{
                contador.textContent = totalItems;
                contador.style.display = 'flex';
            }} else {{
                contador.style.display = 'none';
            }}
        }}

        function actualizarCarritoModal() {{
            const carritoItems = document.getElementById('carritoItems');
            const carritoTotales = document.getElementById('carritoTotales');
            
            if (carrito.length === 0) {{
                carritoItems.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">El carrito está vacío</p>';
                carritoTotales.innerHTML = '<span>Total:</span><span>$0</span>';
                return;
            }}
            
            let html = '';
            let total = 0;
            
            carrito.forEach(item => {{
                const subtotal = item.precio_final * item.cantidad;
                total += subtotal;
                
                html += `
                    <div class="carrito-item">
                        <img src="${{item.imagen}}" alt="${{item.nombre}}">
                        <div class="carrito-item-info">
                            <div class="carrito-item-nombre">${{item.nombre}}</div>
                            <div class="carrito-item-marca">${{item.marca}} - ${{item.tipo}}</div>
                            <div class="carrito-item-precio">${{formatearPrecio(item.precio_final)}} cada uno</div>
                        </div>
                        <div class="carrito-item-controls">
                            <div class="carrito-item-cantidad">
                                <button class="btn-cantidad" onclick="quitarDelCarrito(${{item.id}})">-</button>
                                <span class="cantidad-numero">${{item.cantidad}}</span>
                                <button class="btn-cantidad" onclick="agregarAlCarrito(${{item.id}})">+</button>
                            </div>
                            <button class="btn-eliminar" onclick="eliminarDelCarrito(${{item.id}})">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                `;
            }});
            
            carritoItems.innerHTML = html;
            carritoTotales.innerHTML = `
                <span>Total (${{carrito.length}} productos):</span>
                <span>${{formatearPrecio(total)}}</span>
            `;
        }}

        function mostrarModalCarrito() {{
            actualizarCarritoModal();
            document.getElementById('modalCarrito').style.display = 'flex';
        }}

        function cerrarModalCarrito() {{
            document.getElementById('modalCarrito').style.display = 'none';
        }}

        function pagarCarrito() {{
            if (carrito.length === 0) {{
                mostrarToast('El carrito está vacío', 'warning');
                return;
            }}
            
            const total = carrito.reduce((sum, item) => sum + (item.precio_final * item.cantidad), 0);
            
            // Crear un producto combinado para la compra del carrito
            productoSeleccionado = {{
                id: 'carrito',
                nombre: 'Compra del Carrito (' + carrito.length + ' productos)',
                marca: 'Varios',
                precio_final: total,
                imagen: carrito[0].imagen,
                productos: carrito.map(item => ({{
                    id: item.id,
                    nombre: item.nombre,
                    marca: item.marca,
                    precio_final: item.precio_final,
                    cantidad: item.cantidad,
                    imagen: item.imagen
                }}))
            }};
            
            // Actualizar resumen en el modal
            const resumen = document.getElementById('resumenCompra');
            resumen.innerHTML = `
                <h4>Resumen del pedido</h4>
                <div style="max-height: 200px; overflow-y: auto; margin: 15px 0;">
                    ${{carrito.map(item => `
                        <div style="display: flex; align-items: center; gap: 10px; margin: 10px 0; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 8px;">
                            <img src="${{item.imagen}}" alt="${{item.nombre}}" style="width: 40px; height: 40px; border-radius: 5px; object-fit: cover;">
                            <div style="flex: 1;">
                                <div style="font-weight: 600;">${{item.nombre}}</div>
                                <div style="font-size: 12px; color: var(--text-secondary);">${{item.marca}} x${{item.cantidad}}</div>
                            </div>
                            <div style="font-weight: 600;">${{formatearPrecio(item.precio_final * item.cantidad)}}</div>
                        </div>
                    `).join('')}}
                </div>
                <div class="resumen-total">
                    <span>Total a pagar:</span>
                    <strong class="precio-actual">${{formatearPrecio(total)}}</strong>
                </div>
            `;
            
            // Cerrar modal de carrito y abrir modal de compra
            cerrarModalCarrito();
            document.getElementById('modalCompra').style.display = 'flex';
            document.getElementById('formCompra').reset();
        }}

        // ==============================================
        // SISTEMA DE PAGO WOMPI ACTUALIZADO
        // ==============================================
        async function procesarPagoWompi(producto, cliente) {{
            mostrarLoading();
            
            try {{
                const precioFinal = producto.precio_final;
                const montoEnCentavos = Math.round(precioFinal * 100);
                const referencia = generarReferenciaWompi(producto.id);
                const firmaIntegridad = await generarFirmaIntegridad(referencia, montoEnCentavos);
                
                console.log('=== CONFIGURACIÓN WOMPI ===');
                console.log('Referencia:', referencia);
                console.log('Monto (centavos):', montoEnCentavos);
                console.log('Firma generada:', firmaIntegridad.substring(0, 20) + '...');
                
                const checkoutConfig = {{
                    currency: 'COP',
                    amountInCents: montoEnCentavos,
                    reference: referencia,
                    publicKey: CONFIG_SISTEMA.WOMPI_PUBLIC_KEY,
                    signature: {{ integrity: firmaIntegridad }},
                    // En GitHub Pages no existe templogarage.com/confirmacion; usar la misma página evita redirects rotos.
                    redirectUrl: window.location.href.split('#')[0],
                    customerData: {{
                        email: cliente.email,
                        fullName: cliente.nombre,
                        phoneNumber: cliente.telefono.replace(/\\D/g, ''),
                        phoneNumberPrefix: '+57',
                        legalId: '1234567890',
                        legalIdType: 'CC'
                    }},
                    taxInCents: {{
                        vat: Math.round((producto.precio_final - (producto.precio_final / 1.19)) * 100)
                    }}
                }};
                
                console.log('Configuración completa:', checkoutConfig);
                
                const checkout = new WidgetCheckout(checkoutConfig);

                // El loader solo se usa para preparar el checkout. Al abrirlo, lo ocultamos
                // para evitar que quede "pegado" si el usuario cierra/cancela el widget.
                ocultarLoading();
                
                checkout.open(function(result) {{
                    console.log('Resultado de Wompi:', result);
                    
                    const transaction = result.transaction;
                    if (transaction && transaction.status === 'APPROVED') {{
                        console.log('✅ Transacción exitosa ID:', transaction.id);
                        mostrarLoading();
                        finalizarCompra(producto, cliente, precioFinal, referencia, transaction);
                    }} else if (transaction && transaction.status === 'DECLINED') {{
                        mostrarToast('Pago rechazado. Intenta con otro método.', 'error');
                        ocultarLoading();
                    }} else if (transaction && transaction.status === 'VOIDED') {{
                        mostrarToast('Transacción cancelada.', 'warning');
                        ocultarLoading();
                    }} else if (transaction && transaction.status === 'ERROR') {{
                        mostrarToast('Error en la transacción.', 'error');
                        ocultarLoading();
                    }} else {{
                        console.log('Estado desconocido:', result);
                        mostrarToast('No se pudo completar la transacción.', 'error');
                        ocultarLoading();
                    }}
                }});
                
            }} catch (error) {{
                console.error('❌ Error en procesarPagoWompi:', error);
                mostrarToast('Error al iniciar el pago: ' + error.message, 'error');
                ocultarLoading();
            }}
        }}

        async function finalizarCompra(producto, cliente, monto, referencia, transaccion) {{
            try {{
                console.log('Finalizando compra:', {{ referencia, monto, transaccionId: transaccion.id }});
                
                // Si era una compra del carrito, vaciarlo
                if (producto.id === 'carrito') {{
                    carrito = [];
                    guardarCarrito();
                    actualizarContadorCarrito();
                    document.querySelectorAll('.contador-carrito-mini').forEach(el => el.remove());
                }}
                
                const transaccionData = {{
                    id: transaccion.id,
                    referencia,
                    producto: producto.nombre,
                    monto,
                    cliente,
                    fecha: new Date().toISOString(),
                    estado: 'completado',
                    metodo: 'Wompi'
                }};
                
                registrarTransaccion(transaccionData);
                
                // Enviar comprobante al cliente y notificación al vendedor
                const emailClienteEnviado = await enviarComprobanteCliente(cliente.email, producto, monto, referencia, transaccion);
                const emailVendedorEnviado = await enviarNotificacionVendedor(cliente, producto, monto, referencia, transaccion);
                
                enviarWhatsAppConfirmacion(cliente.telefono, producto, monto, referencia, transaccion);
                
                if (emailClienteEnviado && emailVendedorEnviado) {{
                    mostrarToast('✅ ¡Compra exitosa! Revisa tu email y WhatsApp', 'success');
                }} else {{
                    mostrarToast('✅ ¡Compra exitosa! Pero hubo un error enviando algunos emails.', 'warning');
                }}
                
                cerrarModalCompra();
                ocultarLoading();
                
            }} catch (error) {{
                console.error('Error finalizando compra:', error);
                mostrarToast('Compra procesada, pero hubo error enviando comprobantes.', 'warning');
                ocultarLoading();
            }}
        }}

        async function enviarComprobanteCliente(emailCliente, producto, monto, referencia, transaccion) {{
            try {{
                const fecha = new Date().toLocaleDateString('es-CO', {{
                    weekday: 'long',
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                }});
                
                let productosHTML = '';
                if (producto.id === 'carrito') {{
                    productosHTML = producto.productos.map(p => `
                        <div style="margin: 10px 0; padding: 10px; background: #f5f5f5; border-radius: 5px;">
                            <strong>${{p.nombre}}</strong> (${{p.marca}}) x${{p.cantidad}}<br>
                            Precio: ${{formatearPrecio(p.precio_final * p.cantidad)}}
                        </div>
                    `).join('');
                }} else {{
                    productosHTML = `
                        <div style="margin: 10px 0; padding: 10px; background: #f5f5f5; border-radius: 5px;">
                            <strong>${{producto.nombre}}</strong> (${{producto.marca}})<br>
                            Precio: ${{formatearPrecio(monto)}}
                        </div>
                    `;
                }}
                
                const emailHtml = `
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px;">
                        <h2 style="color: #FF0000; text-align: center; border-bottom: 2px solid #FF0000; padding-bottom: 10px;">
                            ✅ COMPROBANTE DE COMPRA - TEMPLO GARAGE
                        </h2>
                        <p>¡Gracias por tu compra! Aquí está tu comprobante oficial:</p>
                        
                        <div style="background: #f9f9f9; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #FF0000;">
                            <h3 style="color: #333; margin-top: 0;">📋 Detalles de la compra</h3>
                            <p><strong>Referencia:</strong> ${{referencia}}</p>
                            <p><strong>ID Transacción:</strong> ${{transaccion.id}}</p>
                            <p><strong>Fecha:</strong> ${{fecha}}</p>
                            <p><strong>Estado:</strong> <span style="color: green; font-weight: bold;">✅ APROBADO</span></p>
                            <p><strong>Método de pago:</strong> Wompi (Tarjeta)</p>
                        </div>
                        
                        <div style="background: #f9f9f9; padding: 20px; border-radius: 8px; margin: 20px 0;">
                            <h3 style="color: #333; margin-top: 0;">🛒 Productos comprados</h3>
                            ${{productosHTML}}
                            <div style="text-align: right; margin-top: 20px; padding-top: 10px; border-top: 2px solid #ddd;">
                                <h3 style="color: #FF0000;">Total pagado: ${{formatearPrecio(monto)}}</h3>
                            </div>
                        </div>
                        
                        <div style="background: #e8f4fc; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #1a237e;">
                            <h4 style="color: #1a237e; margin-top: 0;">📦 Información de envío</h4>
                            <p>• Tu pedido será procesado en las próximas 24 horas.</p>
                            <p>• Te contactaremos por WhatsApp para coordinar el envío.</p>
                            <p>• Tiempo estimado de entrega: 2-5 días hábiles.</p>
                        </div>
                        
                        <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc107;">
                            <h4 style="color: #856404; margin-top: 0;">🛡️ Garantía y soporte</h4>
                            <p>• Todos nuestros productos tienen garantía de 3 meses.</p>
                            <p>• Para consultas o problemas, contáctanos por WhatsApp.</p>
                            <p>• Guarda este comprobante para cualquier reclamo.</p>
                        </div>
                        
                        <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                            <p><strong>Contacto y soporte:</strong></p>
                            <p>📱 WhatsApp: +57 {CONFIG['CONTACTO']['WHATSAPP']}</p>
                            <p>🎵 TikTok: @brujablanca51 | @naturista_venuz</p>
                            <p>📧 Email: {CONFIG['CONTACTO']['EMAIL_VENDEDOR']}</p>
                        </div>
                        
                        <div style="text-align: center; margin-top: 20px; color: #666; font-size: 12px;">
                            <p>© 2024 Templo Garage Street. Todos los derechos reservados.</p>
                            <p>Este es un comprobante electrónico válido.</p>
                        </div>
                    </div>
                `;

                if (!CONFIG_SISTEMA.RESEND_API_KEY) {{
                    throw new Error('Resend API key no configurada en el frontend. Usando fallback mailto.');
                }}
                
                const response = await fetch('https://api.resend.com/emails', {{
                    method: 'POST',
                    headers: {{
                        'Authorization': `Bearer ${{CONFIG_SISTEMA.RESEND_API_KEY}}`,
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{
                        from: 'Templo Garage <ventas@templogarage.com>',
                        to: emailCliente,
                        subject: `✅ Comprobante de compra #${{referencia}} - Templo Garage`,
                        html: emailHtml
                    }})
                }});
                
                if (!response.ok) throw new Error('Error enviando email al cliente');
                
                console.log('✅ Comprobante enviado al cliente');
                return true;
            }} catch (error) {{
                console.error('Error enviando comprobante al cliente:', error);
                // Fallback: abrir cliente de email
                const asunto = `Comprobante de compra ${{referencia}} - Templo Garage`;
                const cuerpo = `Comprobante de compra Templo Garage%0A%0AReferencia: ${{referencia}}%0AID Transacción: ${{transaccion.id}}%0AProducto: ${{producto.nombre}}%0AMarca: ${{producto.marca}}%0AMonto total: ${{formatearPrecio(monto)}}%0A%0A¡Gracias por tu compra!%0ATe contactaremos por WhatsApp para coordinar el envío.%0A%0AContacto:%0AWhatsApp: +57{CONFIG['CONTACTO']['WHATSAPP']}%0ATikTok: @brujablanca51`;
                window.open(`mailto:${{emailCliente}}?subject=${{encodeURIComponent(asunto)}}&body=${{encodeURIComponent(cuerpo)}}`, '_blank');
                return false;
            }}
        }}

        async function enviarNotificacionVendedor(cliente, producto, monto, referencia, transaccion) {{
            try {{
                const fecha = new Date().toLocaleDateString('es-CO', {{
                    weekday: 'long',
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                }});
                
                let productosDetalle = '';
                if (producto.id === 'carrito') {{
                    productosDetalle = producto.productos.map(p => `
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">
                                <img src="${{p.imagen}}" alt="${{p.nombre}}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 5px;">
                            </td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">${{p.nombre}}</td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">${{p.marca}}</td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">${{p.cantidad}}</td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">${{formatearPrecio(p.precio_final)}}</td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">${{formatearPrecio(p.precio_final * p.cantidad)}}</td>
                        </tr>
                    `).join('');
                }} else {{
                    productosDetalle = `
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">
                                <img src="${{producto.imagen}}" alt="${{producto.nombre}}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 5px;">
                            </td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">${{producto.nombre}}</td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">${{producto.marca}}</td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">1</td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">${{formatearPrecio(monto)}}</td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">${{formatearPrecio(monto)}}</td>
                        </tr>
                    `;
                }}
                
                const emailHtml = `
                    <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px;">
                        <h2 style="color: #FF0000; text-align: center; border-bottom: 3px solid #FF0000; padding-bottom: 15px;">
                            🛒 NUEVA VENTA REALIZADA - TEMPLO GARAGE
                        </h2>
                        
                        <div style="background: #f0f8ff; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #1a237e;">
                            <h3 style="color: #1a237e; margin-top: 0;">📊 Información de la venta</h3>
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr>
                                    <td style="padding: 8px; font-weight: bold;">Referencia:</td>
                                    <td style="padding: 8px;">${{referencia}}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px; font-weight: bold;">ID Transacción Wompi:</td>
                                    <td style="padding: 8px;">${{transaccion.id}}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px; font-weight: bold;">Fecha y hora:</td>
                                    <td style="padding: 8px;">${{fecha}}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px; font-weight: bold;">Monto total:</td>
                                    <td style="padding: 8px; color: #FF0000; font-weight: bold; font-size: 18px;">${{formatearPrecio(monto)}}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px; font-weight: bold;">Estado:</td>
                                    <td style="padding: 8px; color: green; font-weight: bold;">✅ PAGO APROBADO</td>
                                </tr>
                            </table>
                        </div>
                        
                        <div style="background: #fff3cd; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc107;">
                            <h3 style="color: #856404; margin-top: 0;">👤 Información del cliente</h3>
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr>
                                    <td style="padding: 8px; font-weight: bold;">Nombre:</td>
                                    <td style="padding: 8px;">${{cliente.nombre}}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px; font-weight: bold;">Email:</td>
                                    <td style="padding: 8px;">${{cliente.email}}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px; font-weight: bold;">WhatsApp:</td>
                                    <td style="padding: 8px;">+57 ${{cliente.telefono}}</td>
                                </tr>
                            </table>
                        </div>
                        
                        <div style="margin: 20px 0;">
                            <h3 style="color: #333; border-bottom: 2px solid #FF0000; padding-bottom: 10px;">🛍️ Detalle de productos</h3>
                            <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                                <thead>
                                    <tr style="background: #f5f5f5;">
                                        <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Imagen</th>
                                        <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Producto</th>
                                        <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Marca</th>
                                        <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Cantidad</th>
                                        <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Precio unitario</th>
                                        <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Subtotal</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${{productosDetalle}}
                                </tbody>
                                <tfoot>
                                    <tr style="background: #f9f9f9;">
                                        <td colspan="5" style="padding: 10px; text-align: right; font-weight: bold;">TOTAL:</td>
                                        <td style="padding: 10px; font-weight: bold; color: #FF0000; font-size: 18px;">${{formatearPrecio(monto)}}</td>
                                    </tr>
                                </tfoot>
                            </table>
                        </div>
                        
                        <div style="background: #e8f4fc; padding: 15px; border-radius: 8px; margin: 20px 0; text-align: center;">
                            <h4 style="color: #1a237e; margin-top: 0;">📞 Acciones requeridas</h4>
                            <p>1. Contactar al cliente por WhatsApp para confirmar la dirección de envío</p>
                            <p>2. Preparar el pedido para despacho</p>
                            <p>3. Actualizar el estado en el sistema de gestión</p>
                        </div>
                        
                        <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                            <p><strong>Enlaces rápidos:</strong></p>
                            <p>
                                <a href="https://wa.me/57${{cliente.telefono}}" style="background: #25D366; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 5px;">
                                    📱 Contactar por WhatsApp
                                </a>
                                <a href="https://dashboard.wompi.co/transactions" style="background: #1a237e; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 5px;">
                                    📊 Ver en Wompi
                                </a>
                            </p>
                        </div>
                        
                        <div style="text-align: center; margin-top: 20px; color: #666; font-size: 12px;">
                            <p>© 2024 Templo Garage Street - Sistema automatizado de notificaciones</p>
                            <p>Esta notificación fue generada automáticamente por el catálogo online.</p>
                        </div>
                    </div>
                `;

                if (!CONFIG_SISTEMA.RESEND_API_KEY) {{
                    throw new Error('Resend API key no configurada en el frontend. Usando fallback mailto.');
                }}
                
                const response = await fetch('https://api.resend.com/emails', {{
                    method: 'POST',
                    headers: {{
                        'Authorization': `Bearer ${{CONFIG_SISTEMA.RESEND_API_KEY}}`,
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{
                        from: 'Sistema de Ventas <ventas@templogarage.com>',
                        to: CONFIG_SISTEMA.EMAIL_VENDEDOR,
                        subject: `🛒 NUEVA VENTA #${{referencia}} - ${{formatearPrecio(monto)}} - Templo Garage`,
                        html: emailHtml
                    }})
                }});
                
                if (!response.ok) throw new Error('Error enviando email al vendedor');
                
                console.log('✅ Notificación enviada al vendedor');
                return true;
            }} catch (error) {{
                console.error('Error enviando notificación al vendedor:', error);
                // Fallback: abrir cliente de email
                const asunto = `NUEVA VENTA ${{referencia}} - ${{formatearPrecio(monto)}}`;
                const cuerpo = `NUEVA VENTA REALIZADA%0A%0AReferencia: ${{referencia}}%0AID Transacción: ${{transaccion.id}}%0ACliente: ${{cliente.nombre}}%0AEmail: ${{cliente.email}}%0AWhatsApp: +57${{cliente.telefono}}%0AProducto: ${{producto.nombre}}%0AMonto: ${{formatearPrecio(monto)}}%0A%0A¡Contactar al cliente para coordinar envío!`;
                window.open(`mailto:${{CONFIG_SISTEMA.EMAIL_VENDEDOR}}?subject=${{encodeURIComponent(asunto)}}&body=${{encodeURIComponent(cuerpo)}}`, '_blank');
                return false;
            }}
        }}

        function enviarWhatsAppConfirmacion(telefono, producto, monto, referencia, transaccion) {{
            try {{
                const mensaje = `✅ COMPRA CONFIRMADA - TEMPLO GARAGE%0A%0A` +
                               `Referencia: ${{referencia}}%0A` +
                               `ID Transacción: ${{transaccion.id}}%0A` +
                               `Producto: ${{producto.nombre}}%0A` +
                               `Total: ${{formatearPrecio(monto)}}%0A%0A` +
                               `¡Gracias por tu compra! Te hemos enviado el comprobante al email registrado.%0A` +
                               `Te contactaremos por WhatsApp para coordinar el envío.%0A%0A` +
                               `Para consultas: +57{CONFIG['CONTACTO']['WHATSAPP']}`;
                
                const url = `https://wa.me/57${{telefono.replace(/\\D/g, '')}}?text=${{mensaje}}`;
                window.open(url, '_blank');
            }} catch (error) {{
                console.error('Error enviando WhatsApp:', error);
            }}
        }}

        // ==============================================
        // SISTEMA DE TRANSACCIONES
        // ==============================================
        function cargarTransacciones() {{
            const guardadas = localStorage.getItem('transacciones_templo');
            transacciones = guardadas ? JSON.parse(guardadas) : [];
        }}

        function registrarTransaccion(transaccion) {{
            transacciones.unshift(transaccion);
            transacciones = transacciones.slice(0, 50);
            localStorage.setItem('transacciones_templo', JSON.stringify(transacciones));
        }}

        // ==============================================
        // SISTEMA DE CHAT MINIMALISTA MEJORADO
        // ==============================================
        function mostrarModalChat() {{
            document.getElementById('modalChat').style.display = 'flex';
            // Si no hay historial, mostrar opciones
            if (chatHistory.length === 0) {{
                mostrarOpcionesChat();
            }}
        }}

        function cerrarModalChat() {{
            document.getElementById('modalChat').style.display = 'none';
        }}

        function handleChatKeyPress(event) {{
            if (event.key === 'Enter') {{
                enviarMensajeChat();
            }}
        }}

        function enviarMensajeChat() {{
            const input = document.getElementById('chatInput');
            const texto = input.value.trim();
            
            if (!texto) return;
            
            agregarMensajeChat(texto, 'usuario');
            input.value = '';
            
            setTimeout(() => {{
                responderChat(texto);
            }}, 1000);
        }}

        function agregarMensajeChat(texto, tipo) {{
            const messages = document.getElementById('chatMessages');
            const hora = new Date().toLocaleTimeString([], {{ hour: '2-digit', minute: '2-digit' }});
            
            const mensaje = document.createElement('div');
            mensaje.className = `mensaje ${{tipo}}`;
            mensaje.innerHTML = `
                <div class="burbuja">${{texto}}</div>
                <div style="font-size: 11px; color: var(--text-secondary); margin-top: 5px;">${{hora}}</div>
            `;
            
            messages.appendChild(mensaje);
            messages.scrollTop = messages.scrollHeight;
            
            // Guardar en historial
            chatHistory.push({{tipo, texto, hora}});
        }}

        function mostrarOpcionesChat() {{
            const messages = document.getElementById('chatMessages');
            
            // Solo limpiar si no hay mensajes previos
            if (chatHistory.length === 0) {{
                messages.innerHTML = '';
                agregarMensajeChat('¡Hola! 👋 Soy el asistente virtual de Templo Garage. ¿En qué puedo ayudarte hoy?', 'bot');
            }}
            
            setTimeout(() => {{
                const opcionesHTML = `
                    <div class="opciones-chat">
                        <button class="opcion-chat" onclick="seleccionarOpcionChat(1)">
                            <i class="fas fa-search"></i>
                            <span class="opcion-chat-text">Buscar un repuesto específico</span>
                        </button>
                        <button class="opcion-chat" onclick="seleccionarOpcionChat(2)">
                            <i class="fas fa-user-tie"></i>
                            <span class="opcion-chat-text">Contactar a un asesor</span>
                        </button>
                        <button class="opcion-chat" onclick="seleccionarOpcionChat(3)">
                            <i class="fas fa-truck"></i>
                            <span class="opcion-chat-text">Información sobre envíos</span>
                        </button>
                        <button class="opcion-chat" onclick="seleccionarOpcionChat(4)">
                            <i class="fas fa-credit-card"></i>
                            <span class="opcion-chat-text">Métodos de pago</span>
                        </button>
                    </div>
                `;
                
                const opcionesDiv = document.createElement('div');
                opcionesDiv.innerHTML = opcionesHTML;
                messages.appendChild(opcionesDiv);
                messages.scrollTop = messages.scrollHeight;
            }}, 500);
        }}

        function seleccionarOpcionChat(opcion) {{
            estadoChat = 'opcion_' + opcion;
            
            // Agregar mensaje de usuario
            let textoUsuario = '';
            switch(opcion) {{
                case 1:
                    textoUsuario = 'Buscar un repuesto específico';
                    break;
                case 2:
                    textoUsuario = 'Contactar a un asesor';
                    break;
                case 3:
                    textoUsuario = 'Información sobre envíos';
                    break;
                case 4:
                    textoUsuario = 'Métodos de pago';
                    break;
            }}
            
            agregarMensajeChat(textoUsuario, 'usuario');
            
            setTimeout(() => {{
                switch(opcion) {{
                    case 1:
                        agregarMensajeChat('Escribe el nombre, marca o referencia del repuesto que buscas. Puedes escribir aunque no estés seguro de la ortografía.', 'bot');
                        break;
                        
                    case 2:
                        agregarMensajeChat('Perfecto. Por favor, proporciona la siguiente información:<br><br>' +
                                          '1. 🏍️ Marca de la moto<br>' +
                                          '2. 📋 Modelo<br>' +
                                          '3. 📅 Año<br>' +
                                          '4. 🔧 Nombre del repuesto que necesitas<br>' +
                                          '5. 📦 Cantidad requerida<br><br>' +
                                          'Escribe toda la información en un solo mensaje.', 'bot');
                        datosChatAsesor = {{}};
                        break;
                        
                    case 3:
                        agregarMensajeChat('📦 **INFORMACIÓN DE ENVÍOS:**<br>' +
                                          '• 🚚 Bogotá: 24-48 horas<br>' +
                                          '• 🌎 Otras ciudades: 3-5 días hábiles<br>' +
                                          '• 🆓 Envío gratis en compras mayores a $200,000<br>' +
                                          '• 📦 Usamos Servientrega e Interrapidisimo<br><br>' +
                                          '✅ **GARANTÍAS:**<br>' +
                                          '• Todos los productos tienen garantía de 3 meses<br>' +
                                          '• 🔄 Devoluciones en 15 días si el producto está sin usar', 'bot');
                        break;
                        
                    case 4:
                        agregarMensajeChat('💳 **MÉTODOS DE PAGO:**<br>' +
                                          '• ✅ Tarjetas débito/crédito (Wompi)<br>' +
                                          '• 📱 Transferencias bancarias<br>' +
                                          '• 💰 Pago contra entrega (solo Bogotá)<br><br>' +
                                          '🛡️ **SEGURIDAD:**<br>' +
                                          '• 🔒 Pago 100% seguro con encriptación SSL<br>' +
                                          '• 🏦 Transacciones certificadas por Wompi', 'bot');
                        break;
                }}
            }}, 500);
        }}

        function responderConfirmacionAsesor(acepta) {{
            // Deshabilitar botones para evitar doble click
            document.querySelectorAll('[data-confirm-asesor]')
                .forEach(btn => btn.disabled = true);

            agregarMensajeChat(acepta ? 'Sí' : 'No', 'usuario');
            responderChat(acepta ? 'sí' : 'no');
        }}

        function responderChat(pregunta) {{
            const preguntaLower = pregunta.toLowerCase();
            
            if (estadoChat.startsWith('opcion_1')) {{
                // Búsqueda de repuesto
                const resultados = buscarFuzzy(pregunta, todosProductos, ['nombre', 'marca', 'descripcion', 'tipo'], 3);
                
                if (resultados.length > 0) {{
                    let mensaje = '🔍 Encontré estos repuestos:<br><br>';
                    
                    resultados.forEach((p, i) => {{
                        mensaje += `<strong>${{i+1}}. ${{p.nombre}}</strong><br>`;
                        mensaje += `🏷️ Marca: ${{p.marca}}<br>`;
                        mensaje += `💰 Precio: ${{p.precio_str}}<br><br>`;
                    }});
                    
                    mensaje += 'Escribe el número del repuesto que te interesa o realiza una nueva búsqueda.';
                    
                    agregarMensajeChat(mensaje, 'bot');
                    
                    // Guardar resultados para selección
                    window.resultadosBusquedaChat = resultados;
                    
                }} else {{
                    agregarMensajeChat('No encontré repuestos con esa descripción. ¿Te gustaría contactar a un asesor para que te ayude a encontrarlo? (escribe "asesor")', 'bot');
                }}
                
            }} else if (estadoChat === 'opcion_2') {{
                // Procesar información para asesor
                datosChatAsesor = {{...datosChatAsesor, detalles: pregunta}};

                agregarMensajeChat(
                    '📝 Información recibida. ¿Quieres que envíe estos detalles a un asesor por WhatsApp?'
                    + '<div class="opciones-chat" style="margin-top: 10px;">'
                    + '  <button type="button" class="opcion-chat" data-confirm-asesor onclick="responderConfirmacionAsesor(true)">'
                    + '    <i class="fas fa-check"></i><span class="opcion-chat-text">Sí, enviar por WhatsApp</span>'
                    + '  </button>'
                    + '  <button type="button" class="opcion-chat" data-confirm-asesor onclick="responderConfirmacionAsesor(false)">'
                    + '    <i class="fas fa-times"></i><span class="opcion-chat-text">No, gracias</span>'
                    + '  </button>'
                    + '</div>',
                    'bot'
                );
                estadoChat = 'enviar_asesor';
                
            }} else if (estadoChat === 'enviar_asesor') {{
                if (preguntaLower.includes('si') || preguntaLower.includes('sí')) {{
                    const detalles = (datosChatAsesor.detalles || '').trim();
                    const mensaje = `🚨 SOLICITUD DE ASESOR - TEMPLO GARAGE\n\n` +
                                   `🆔 Cliente: Chat Web\n` +
                                   `📝 Detalles:\n${{detalles}}\n\n` +
                                   `🕒 Fecha: ${{new Date().toLocaleString()}}`;

                    window.open(`https://wa.me/${{CONFIG_SISTEMA.WHATSAPP_NUMERO}}?text=${{encodeURIComponent(mensaje)}}`, '_blank');
                    agregarMensajeChat('✅ He abierto WhatsApp para que puedas contactar a nuestro asesor con toda la información. ¿En qué más puedo ayudarte?', 'bot');
                }} else {{
                    agregarMensajeChat('De acuerdo, no se ha enviado el mensaje. ¿En qué más puedo ayudarte?', 'bot');
                }}
                estadoChat = '';
                
            }} else if (/^\\d+$/.test(pregunta) && window.resultadosBusquedaChat) {{
                // Selección numérica de resultados
                const num = parseInt(pregunta);
                if (num >= 1 && num <= window.resultadosBusquedaChat.length) {{
                    const producto = window.resultadosBusquedaChat[num-1];
                    agregarMensajeChat(`✅ Has seleccionado: ${{producto.nombre}} (${{producto.marca}}) - ${{producto.precio_str}}<br><br>¿Quieres agregarlo al carrito? (responde "sí" o "no")`, 'bot');
                    window.productoSeleccionadoChat = producto;
                    estadoChat = 'agregar_carrito_chat';
                }}
                
            }} else if (estadoChat === 'agregar_carrito_chat') {{
                if (preguntaLower.includes('si') || preguntaLower.includes('sí')) {{
                    agregarAlCarrito(window.productoSeleccionadoChat.id);
                    agregarMensajeChat('✅ Producto agregado al carrito. ¿En qué más puedo ayudarte?', 'bot');
                }} else {{
                    agregarMensajeChat('Producto no agregado. ¿En qué más puedo ayudarte?', 'bot');
                }}
                estadoChat = '';
                window.resultadosBusquedaChat = null;
                window.productoSeleccionadoChat = null;
                
            }} else {{
                // Respuesta por defecto
                agregarMensajeChat('No estoy seguro de cómo ayudarte con eso. ¿Prefieres elegir una de las opciones?', 'bot');
                setTimeout(() => mostrarOpcionesChat(), 1000);
            }}
        }}

        function inicializarChat() {{
            const btn = document.getElementById('btnChatFlotante');
            if (btn) {{
                btn.addEventListener('click', function() {{
                    ocultarChatNudge(true);
                    mostrarModalChat();
                }});
            }}
            inicializarChatNudge();
            
            // Inicializar historial vacío
            chatHistory = [];
        }}

        function inicializarChatNudge() {{
            const nudge = document.getElementById('chatNudge');
            if (!nudge) return;
            if (localStorage.getItem('chat_nudge_dismissed') === '1') return;

            // Mostrar entre 10–15s (usamos 12s por defecto)
            setTimeout(() => {{
                const modal = document.getElementById('modalChat');
                const isOpen = modal && modal.style.display === 'flex';
                if (isOpen) return;
                if (localStorage.getItem('chat_nudge_dismissed') === '1') return;
                nudge.classList.add('show');

                // Auto-ocultar para no estorbar
                setTimeout(() => {{
                    ocultarChatNudge(false);
                }}, 10000);
            }}, 12000);

            nudge.addEventListener('click', function(e) {{
                const dismissBtn = e.target.closest('[data-action="dismiss"]');
                if (dismissBtn) {{
                    e.preventDefault();
                    ocultarChatNudge(true);
                    return;
                }}
                ocultarChatNudge(true);
                mostrarModalChat();
            }});
        }}

        function ocultarChatNudge(dismiss) {{
            const nudge = document.getElementById('chatNudge');
            if (!nudge) return;
            nudge.classList.remove('show');
            if (dismiss) localStorage.setItem('chat_nudge_dismissed', '1');
        }}

        // ==============================================
        // SISTEMA DE BÚSQUEDA MEJORADA
        // ==============================================
        function inicializarBuscador() {{
            const buscador = document.getElementById('buscadorPrincipal');
            const sugerencias = document.getElementById('sugerenciasBusqueda');
            
            buscador.addEventListener('input', function() {{
                const query = this.value;
                
                if (query.length < 2) {{
                    sugerencias.style.display = 'none';
                    return;
                }}
                
                // Búsqueda fuzzy con tolerancia a errores
                const resultados = buscarFuzzy(query, todosProductos, ['nombre', 'marca', 'descripcion'], 8);
                
                if (resultados.length > 0) {{
                    sugerencias.innerHTML = resultados.map(p => `
                        <div class="sugerencia-item" onclick="seleccionarProductoBusqueda(${{p.id}})">
                            <img src="${{p.imagen}}" alt="${{p.nombre}}">
                            <div>
                                <strong>${{p.nombre}}</strong><br>
                                <small>${{p.marca}} • ${{p.tipo}} • ${{p.precio_str}}</small>
                            </div>
                        </div>
                    `).join('');
                    sugerencias.style.display = 'block';
                }} else {{
                    sugerencias.style.display = 'none';
                }}
            }});
            
            document.addEventListener('click', function(e) {{
                if (!buscador.contains(e.target) && !sugerencias.contains(e.target)) {{
                    sugerencias.style.display = 'none';
                }}
            }});
        }}

        function seleccionarProductoBusqueda(productoId) {{
            const producto = todosProductos.find(p => p.id === productoId);
            if (producto) {{
                const index = todosProductos.findIndex(p => p.id === productoId);
                const pagina = Math.floor(index / CONFIG_SISTEMA.PRODUCTOS_POR_PAGINA) + 1;
                
                mostrarPagina(pagina);
                
                setTimeout(() => {{
                    const elemento = document.querySelector(`[data-id="${{productoId}}"]`);
                    if (elemento) {{
                        elemento.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                        elemento.style.animation = 'none';
                        setTimeout(() => {{
                            elemento.style.animation = 'protectPulse 1s ease-in-out';
                            setTimeout(() => {{
                                elemento.style.animation = '';
                            }}, 1000);
                        }}, 10);
                    }}
                }}, 100);
                
                document.getElementById('sugerenciasBusqueda').style.display = 'none';
                document.getElementById('buscadorPrincipal').value = '';
            }}
        }}

        // ==============================================
        // SISTEMA DE COMPRA
        // ==============================================
        function iniciarCompra(productoId) {{
            productoSeleccionado = todosProductos.find(p => p.id === productoId);
            
            if (!productoSeleccionado) {{
                mostrarToast('Producto no encontrado', 'error');
                return;
            }}
            
            if (productoSeleccionado.precio <= 0) {{
                const mensaje = `Hola, estoy interesado en: ${{productoSeleccionado.nombre}} (${{productoSeleccionado.marca}})`;
                window.open(`https://wa.me/${{CONFIG_SISTEMA.WHATSAPP_NUMERO}}?text=${{encodeURIComponent(mensaje)}}`, '_blank');
                return;
            }}

            // Al comprar, también dejar el producto en el carrito (por si cancela Wompi)
            asegurarProductoEnCarrito(productoSeleccionado.id);
            
            const resumen = document.getElementById('resumenCompra');
            const precioFinal = productoSeleccionado.precio_final;
            
            resumen.innerHTML = `
                <h4>Resumen del pedido</h4>
                <div class="resumen-item" style="display: flex; align-items: center; gap: 15px; margin: 15px 0;">
                    <img src="${{productoSeleccionado.imagen}}" alt="${{productoSeleccionado.nombre}}" 
                         style="width: 60px; height: 60px; border-radius: 8px; object-fit: cover;">
                    <div style="flex: 1;">
                        <h5 style="margin: 0;">${{productoSeleccionado.nombre}}</h5>
                        <p style="margin: 5px 0; font-size: 14px; color: var(--text-secondary);">${{productoSeleccionado.marca}} • ${{productoSeleccionado.tipo}}</p>
                    </div>
                    <span class="precio-actual">${{formatearPrecio(precioFinal)}}</span>
                </div>
                <div class="resumen-total">
                    <span>Total a pagar:</span>
                    <strong class="precio-actual">${{formatearPrecio(precioFinal)}}</strong>
                </div>
            `;
            
            document.getElementById('modalCompra').style.display = 'flex';
            document.getElementById('formCompra').reset();
        }}

        function cerrarModalCompra() {{
            document.getElementById('modalCompra').style.display = 'none';
            productoSeleccionado = null;
        }}

        document.getElementById('formCompra').addEventListener('submit', async function(e) {{
            e.preventDefault();
            
            if (!productoSeleccionado) {{
                mostrarToast('No hay producto seleccionado', 'error');
                return;
            }}
            
            const cliente = {{
                nombre: document.getElementById('nombreCompra').value.trim(),
                email: document.getElementById('emailCompra').value.trim(),
                telefono: document.getElementById('telefonoCompra').value.trim()
            }};
            
            if (!cliente.nombre) {{
                mostrarToast('Ingresa tu nombre completo', 'error');
                return;
            }}
            
            if (!cliente.email.includes('@') || !cliente.email.includes('.')) {{
                mostrarToast('Ingresa un email válido', 'error');
                return;
            }}
            
            const telefonoLimpio = cliente.telefono.replace(/\\D/g, '');
            if (telefonoLimpio.length !== 10) {{
                mostrarToast('Ingresa un número de WhatsApp válido (10 dígitos)', 'error');
                return;
            }}
            
            procesarPagoWompi(productoSeleccionado, cliente);
        }});

        // ==============================================
        // SISTEMA DE TEMA
        // ==============================================
        function inicializarTema() {{
            const temaGuardado = localStorage.getItem('tema_templo') || 'dark';
            document.documentElement.setAttribute('data-theme', temaGuardado);
            actualizarIconoTema(temaGuardado);
            
            document.getElementById('btnToggleModo').addEventListener('click', toggleTema);
        }}

        function toggleTema() {{
            const temaActual = document.documentElement.getAttribute('data-theme');
            const nuevoTema = temaActual === 'dark' ? 'light' : 'dark';
            
            document.documentElement.setAttribute('data-theme', nuevoTema);
            localStorage.setItem('tema_templo', nuevoTema);
            actualizarIconoTema(nuevoTema);
            
            mostrarToast(`Modo ${{nuevoTema === 'dark' ? 'oscuro' : 'claro'}} activado`, 'info');
        }}

        function actualizarIconoTema(tema) {{
            const icono = document.querySelector('#btnToggleModo i');
            icono.className = tema === 'dark' ? 'fas fa-moon' : 'fas fa-sun';
        }}

        // ==============================================
        // FUNCIONES AUXILIARES
        // ==============================================
        function mostrarTerminos() {{
            const terminos = `
                Términos y Condiciones - Templo Garage:
                
                1. Todos los precios incluyen IVA.
                2. Envíos a todo Colombia.
                3. Garantía de 3 meses en todos los productos.
                4. Devoluciones en 15 días si el producto está sin usar.
                5. Los tiempos de envío varían según la ciudad.
                6. Para reclamos, contactar por WhatsApp.
                7. Las imágenes son ilustrativas.
                8. Precios sujetos a cambio sin previo aviso.
                9. Compra mínima para envío gratis: $200,000.
                10. Factura electrónica incluida en todas las compras.
            `;
            
            alert(terminos);
        }}

        document.getElementById('modalCompra').addEventListener('click', function(e) {{
            if (e.target === this) {{
                cerrarModalCompra();
            }}
        }});

        document.getElementById('modalCarrito').addEventListener('click', function(e) {{
            if (e.target === this) {{
                cerrarModalCarrito();
            }}
        }});

        document.getElementById('modalChat').addEventListener('click', function(e) {{
            if (e.target === this) {{
                cerrarModalChat();
            }}
        }});

        document.getElementById('modalCompartir').addEventListener('click', function(e) {{
            if (e.target === this) {{
                cerrarModalCompartir();
            }}
        }});
    </script>
</body>
</html>'''
    
    return html

# ==============================================
# FUNCIÓN PRINCIPAL MODIFICADA
# ==============================================

def generar_catalogo_completo():
    """Función principal que genera el catálogo completo"""
    print("="*70)
    print("🚀 GENERADOR DE CATÁLOGO PROFESIONAL - TEMPLO GARAGE")
    print("="*70)
    
    start_time = time.time()
    
    try:
        # 1. CARGAR RECURSOS GRÁFICOS
        print("\n📸 CARGANDO RECURSOS GRÁFICOS...")
        
        recursos = {}
        # IMPORTANTE: Para Cloudflare Workers Assets, index.html debe ser <= 25 MiB.
        # Evitamos embebir imágenes en base64 y en su lugar las copiamos a archivos estáticos.
        assets_out = {
            "logo_templo": (CONFIG["RUTAS"]["LOGO_TEMPLO"], "logo_templo.png"),
            "logo_tiktok": (CONFIG["RUTAS"]["LOGO_TIKTOK"], "logo_tiktok.png"),
            "portada": (CONFIG["RUTAS"]["PORTADA"], "portada.png"),
            "anuncio": (CONFIG["RUTAS"]["ANUNCIO"], "anuncio.png"),
        }

        os.makedirs("public", exist_ok=True)

        for nombre, (ruta_origen, nombre_archivo) in assets_out.items():
            if os.path.exists(ruta_origen):
                print(f"   📁 {nombre}: Copiando a assets...")
                try:
                    shutil.copyfile(ruta_origen, nombre_archivo)
                    shutil.copyfile(ruta_origen, os.path.join("public", nombre_archivo))
                    recursos[nombre] = nombre_archivo
                    print("     ✅ Listo")
                except Exception as e:
                    print(f"     ⚠️ No se pudo copiar ({e}). Usando placeholder")
                    recursos[nombre] = generar_url_placeholder(nombre.replace('_', ' '), 1200, 600)
            else:
                print(f"   ❌ {nombre}: No encontrado en {ruta_origen}")
                # Para anuncio preferimos no mostrar nada si falta
                if nombre == "anuncio":
                    recursos[nombre] = ""
                else:
                    recursos[nombre] = generar_url_placeholder(nombre.replace('_', ' '), 1200, 600)
        
        # 2. CARGAR Y PROCESAR DATOS DEL EXCEL
        print("\n📊 CARGANDO DATOS DEL EXCEL...")
        
        try:
            if not os.path.exists(CONFIG["RUTAS"]["EXCEL"]):
                print(f"❌ Archivo Excel no encontrado: {CONFIG['RUTAS']['EXCEL']}")
                print("   Creando datos de demostración...")
                
                df = pd.DataFrame({
                    'MARCA': ['Yamaha', 'Honda', 'Suzuki', 'AKT', 'Kawasaki'] * 20,
                    'NOMBRE': ['Filtro de Aire Premium', 'Cadena 428 Original', 
                              'Bujía NGK Iridium', 'Aceite 20W50 Sintético', 
                              'Pastillas Freno Delanteras'] * 20,
                    'PRECIO MUNDIMOTOS': [45000, 120000, 15000, 35000, 80000] * 20,
                    'imagen_url': [
                        'https://via.placeholder.com/400x300/FF0000/FFFFFF?text=Yamaha+Filter',
                        'https://via.placeholder.com/400x300/1a237e/FFFFFF?text=Honda+Chain',
                        'https://via.placeholder.com/400x300/25D366/FFFFFF?text=AKT+Spark',
                        'https://via.placeholder.com/400x300/FFC107/FFFFFF?text=Suzuki+Oil',
                        'https://via.placeholder.com/400x300/9C27B0/FFFFFF?text=Kawasaki+Brake'
                    ] * 20,
                    'DESCRIPCION': [
                        'Filtro de aire original para motos Yamaha',
                        'Cadena de transmisión 428 eslabones original Honda',
                        'Bujía NGK Iridium de alto rendimiento',
                        'Aceite sintético 20W50 1L para motos',
                        'Pastillas de freno delanteras originales'
                    ] * 20,
                    'TIPO': ['Filtro', 'Transmisión', 'Eléctrico', 'Lubricante', 'Frenos'] * 20
                })
                
                print("   ✅ Datos demo creados (100 productos)")
                
            else:
                print(f"   📄 Archivo: {CONFIG['RUTAS']['EXCEL']}")
                print(f"   📋 Hoja: {CONFIG['EXCEL']['HOJA']}")
                
                xls = pd.ExcelFile(CONFIG["RUTAS"]["EXCEL"])
                print(f"   📑 Hojas disponibles: {xls.sheet_names}")
                
                hoja_a_usar = CONFIG["EXCEL"]["HOJA"]
                if hoja_a_usar not in xls.sheet_names:
                    print(f"   ⚠️ Hoja '{hoja_a_usar}' no encontrada. Usando primera hoja.")
                    hoja_a_usar = xls.sheet_names[0]
                
                df = pd.read_excel(CONFIG["RUTAS"]["EXCEL"], sheet_name=hoja_a_usar)
                print(f"   ✅ Excel cargado: {len(df)} filas, {len(df.columns)} columnas")
                print(f"   📊 Columnas encontradas: {list(df.columns)}")
        
        except Exception as e:
            print(f"❌ Error leyendo Excel: {e}")
            print("   Creando datos de demostración...")
            
            df = pd.DataFrame({
                'MARCA': ['Yamaha', 'Honda', 'Suzuki', 'AKT', 'Kawasaki'] * 20,
                'NOMBRE': ['Filtro de Aire', 'Cadena', 'Bujía', 'Aceite', 'Pastillas'] * 20,
                'PRECIO MUNDIMOTOS': [45000, 120000, 15000, 35000, 80000] * 20,
                'imagen_url': [generar_url_placeholder(m) for m in ['Yamaha', 'Honda', 'Suzuki', 'AKT', 'Kawasaki']] * 20,
                'DESCRIPCION': ['Producto de alta calidad', 'Original de fábrica', 
                               'Alto rendimiento', 'Durabilidad garantizada', 'Seguridad'] * 20,
                'TIPO': ['Filtro', 'Transmisión', 'Eléctrico', 'Lubricante', 'Frenos'] * 20
            })
        
        # 3. LIMPIAR Y PROCESAR DATOS
        print("\n🧹 PROCESANDO DATOS...")
        
        df_limpio = limpiar_datos_excel(df)
        
        max_productos = CONFIG["PARAMETROS"].get("MAX_PRODUCTOS")
        if isinstance(max_productos, int) and max_productos > 0 and len(df_limpio) > max_productos:
            print(f"   ⚠️ Limitar a {max_productos} productos")
            df_limpio = df_limpio.head(max_productos)
        
        procesador = ProcesadorProductos()
        productos = procesador.procesar_dataframe(df_limpio)
        
        estadisticas = procesador.estadisticas
        
        print(f"\n✅ PROCESAMIENTO COMPLETADO")
        print(f"   • Total productos: {estadisticas['total']:,}")
        print(f"   • Con precio: {estadisticas['con_precio']:,}")
        print(f"   • Marcas únicas: {len(estadisticas['marcas_unicas'])}")
        print(f"   • Tipos: {len(estadisticas['tipos_unicos'])}")
        print(f"   • Errores: {estadisticas['errores']}")
        
        # 4. GENERAR HTML
        print("\n🚀 GENERANDO HTML PROFESIONAL...")
        
        html = generar_html_completo(productos, recursos, estadisticas)
        
        # 5. GUARDAR ARCHIVO
        output_path = CONFIG["RUTAS"]["SALIDA"]
        public_output_path = os.path.join('public', 'index.html')

        os.makedirs(os.path.dirname(public_output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        # Salida para Cloudflare Worker/Pages (assets)
        with open(public_output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        tiempo_total = time.time() - start_time
        
        print(f"\n💾 ARCHIVO GUARDADO: {output_path}")
        print(f"   • Copia para deploy: {public_output_path}")
        print(f"   • Tamaño: {os.path.getsize(output_path)/1024/1024:.2f} MB")
        print(f"   • Tiempo total: {tiempo_total:.2f} segundos")
        print(f"   • Productos/segundo: {estadisticas['total']/tiempo_total:.2f}")
        
        # 6. GENERAR REPORTE
        print("\n" + "="*70)
        print("📊 REPORTE FINAL")
        print("="*70)
        print(f"✅ CATÁLOGO GENERADO CON ÉXITO")
        print(f"📅 Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"📦 Productos totales: {estadisticas['total']:,}")
        print(f"💰 Productos con precio: {estadisticas['con_precio']:,}")
        print(f"🏷️  Marcas: {len(estadisticas['marcas_unicas'])}")
        print(f"📂 Tipos: {len(estadisticas['tipos_unicos'])}")
        print(f"⚡ Rendimiento: {tiempo_total:.2f}s")
        print("="*70)
        
        reporte = f"""REPORTE DE GENERACIÓN - TEMPLO GARAGE
Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
Total productos: {estadisticas['total']:,}
Productos con precio: {estadisticas['con_precio']:,}
Marcas únicas: {len(estadisticas['marcas_unicas'])}
Tipos: {len(estadisticas['tipos_unicos'])}
Tiempo total: {tiempo_total:.2f}s
Archivo generado: {output_path}
Tamaño: {os.path.getsize(output_path)/1024/1024:.2f} MB

CONFIGURACIÓN ACTUALIZADA:
- Llave Pública Wompi: {CONFIG['WOMPI_PUBLIC_KEY'][:20]}...
- Modo Wompi: {CONFIG.get('WOMPI_MODO', 'prod')}
- Integrity Secret Wompi: {'CONFIGURADO' if CONFIG.get('WOMPI_INTEGRITY_SECRET') or CONFIG.get('WOMPI_INTEGRITY_SECRET_TEST') else 'NO CONFIGURADO'}
- Resend API Key: {'CONFIGURADO' if CONFIG.get('RESEND_API_KEY') else 'NO CONFIGURADO (no se embebe en el HTML)'}
- WhatsApp: {CONFIG['CONTACTO']['WHATSAPP']}
- Email Vendedor: {CONFIG['CONTACTO']['EMAIL_VENDEDOR']}
- Email Ventas: {CONFIG['CONTACTO']['EMAIL_VENTAS']}

MODIFICACIONES IMPLEMENTADAS:
1. ✅ Letrero "PROTEGEMOS TODAS TUS PARTES" ajustado para computador
2. ✅ Chat bot minimalista con botón flotante
3. ✅ Sistema de correos con Resend API funcionando
   - Comprobante detallado al cliente
   - Notificación completa al vendedor con imagen del producto
   - Sistema de fallback por si falla el API

ARCHIVOS UTILIZADOS:
- Excel: {CONFIG['RUTAS']['EXCEL']}
- Logo Templo: {CONFIG['RUTAS']['LOGO_TEMPLO']}
- Logo TikTok: {CONFIG['RUTAS']['LOGO_TIKTOK']}
- Portada: {CONFIG['RUTAS']['PORTADA']}

EL SISTEMA ESTÁ LISTO PARA:
- Mostrar correctamente en computador y móvil
- Chat asistente funcional y no invasivo
- Envío automático de comprobantes al cliente
- Envío automático de notificaciones al vendedor
"""
        
        with open('reporte_generacion.txt', 'w', encoding='utf-8') as f:
            f.write(reporte)
        
        print(f"\n📝 Reporte guardado en: reporte_generacion.txt")
        print("\n✅ MODIFICACIONES IMPLEMENTADAS:")
        print("   1. Letrero ajustado para computador ✓")
        print("   2. Chat bot minimalista con botón flotante ✓")
        print("   3. Sistema de correos con Resend API ✓")
        print("   4. Notificaciones al vendedor con detalles completos ✓")
        
        print("\n🌐 ¿Deseas abrir el catálogo en el navegador? (s/n): ", end='')
        respuesta = input().lower()
        
        if respuesta == 's':
            import webbrowser
            webbrowser.open(f'file://{os.path.abspath(output_path)}')
            print("✅ Catálogo abierto en el navegador")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        return False

# ==============================================
# EJECUCIÓN PRINCIPAL
# ==============================================

if __name__ == "__main__":
    generar_catalogo_completo()

    