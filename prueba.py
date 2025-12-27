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
from fuzzywuzzy import fuzz, process

# ==============================================
# CONFIGURACIÓN PRINCIPAL
# ==============================================
CONFIG = {
    # API Keys
    "WOMPI_PUBLIC_KEY": "pub_prod_I0KpwGvgPD3xNcLggJZKyD3cNUKrywkx",
    "WOMPI_INTEGRITY_SECRET": "prv_prod_vIazSzxilsFQzdiBt75rakWBzccyBfaC",
    "RESEND_API_KEY": "re_ZewmUDhy_NoAiD8ss2yZroL8uY56EDZHo",
    
    # Rutas de archivos
    "RUTAS": {
        "EXCEL": r"C:\Users\Giral\OneDrive\Documentos\CATQALOGO MOTOS\catalogo_completo\CATALOGO TEMPLO GARAGE.xlsm",
        "LOGO_TEMPLO": r"C:\Users\Giral\OneDrive\Documentos\CATQALOGO MOTOS\logo\TEMPLO GARAGE STREET.png",
        "LOGO_TIKTOK": r"C:\Users\Giral\OneDrive\Documentos\CATQALOGO MOTOS\logo\LOGO TIKTOK.png",
        "PORTADA": r"C:\Users\Giral\OneDrive\Documentos\CATQALOGO MOTOS\logo\portada.png",
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
        "TIKTOK_BRUJABLANCA": "https://www.tiktok.com/@brujablanca51",
        "TIKTOK_NATURISTA": "https://www.tiktok.com/@naturista_venuz"
    },
    
    # Parámetros del sistema
    "PARAMETROS": {
        "IVA_PORCENTAJE": 19,
        "REDONDEO": 100,
        "RATING_DEFAULT": 4.9,
        "COMENTARIOS_DEFAULT": 156,
        "MAX_PRODUCTOS": 10000,
        "PRODUCTOS_POR_PAGINA": 20
    }
}

# ==============================================
# FUNCIONES DE UTILIDAD
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
# PROCESAMIENTO DE PRODUCTOS
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
# GENERACIÓN DE HTML COMPLETO
# ==============================================

def generar_html_completo(productos, recursos, estadisticas):
    """Genera el HTML completo con todas las funcionalidades"""
    
    productos_json = json.dumps(productos, ensure_ascii=False, separators=(',', ':'))
    fecha_actual = datetime.now().strftime('%d/%m/%Y %H:%M')
    
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

        /* ===== PORTADA MEJORADA ===== */
        .portada {{
            position: relative;
            height: 85vh;
            min-height: 700px;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            overflow: hidden;
            padding: 20px;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%);
            margin-bottom: 50px;
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
            padding-top: 80px;
        }}

        /* ===== LOGOS PROFESIONALES ANIMADOS ===== */
        .logos-container {{
            display: flex;
            justify-content: center;
            align-items: flex-start;
            gap: 80px;
            margin-bottom: 60px;
            flex-wrap: wrap;
            padding-top: 50px;
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
            margin-bottom: 40px;
            max-width: 900px;
            margin-left: auto;
            margin-right: auto;
            background: rgba(0, 0, 0, 0.6);
            padding: 20px 40px;
            border-radius: 15px;
            border-left: 4px solid var(--primary);
            border-right: 4px solid var(--secondary);
        }}

        .protect-text {{
            font-size: 3.5rem;
            font-weight: 900;
            color: white;
            margin: 60px auto 100px auto;
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
        .btn-whatsapp-flotante {{
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

        .btn-carrito-flotante:hover,
        .btn-toggle-modo:hover,
        .btn-whatsapp-flotante:hover {{
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

        /* ===== CHAT WIDGET MEJORADO ===== */
        .chat-widget {{
            position: fixed;
            bottom: 120px;
            right: 25px;
            width: 380px;
            background: var(--card-bg);
            border-radius: 20px;
            box-shadow: var(--card-shadow);
            z-index: 9997;
            overflow: hidden;
            transform: translateY(0);
            transition: transform 0.3s;
            border: 1px solid var(--border-color);
        }}

        .chat-widget.collapsed {{
            transform: translateY(calc(100% - 80px));
        }}

        .chat-header {{
            background: linear-gradient(135deg, var(--primary), #ff3333);
            color: white;
            padding: 20px;
            display: flex;
            align-items: center;
            gap: 20px;
            cursor: pointer;
        }}

        .chat-indicator {{
            margin-left: auto;
            position: relative;
            width: 10px;
            height: 10px;
        }}

        .pulse {{
            width: 10px;
            height: 10px;
            background: #25D366;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }}

        @keyframes pulse {{
            0% {{ transform: scale(1); opacity: 1; }}
            50% {{ transform: scale(1.5); opacity: 0.5; }}
            100% {{ transform: scale(1); opacity: 1; }}
        }}

        .chat-body {{
            height: 450px;
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
    </style>
</head>
<body data-theme="dark">
    <!-- Loading Spinner -->
    <div class="loading-spinner" id="loadingSpinner">
        <div class="spinner"></div>
    </div>

    <!-- Controles Superiores -->
    <div class="controles-superiores">
        <button class="btn-toggle-modo" id="btnToggleModo" title="Cambiar tema">
            <i class="fas fa-moon"></i>
        </button>
        
        <button class="btn-whatsapp-flotante" id="btnWhatsappFlotante" title="Contactar por WhatsApp">
            <i class="fab fa-whatsapp"></i>
        </button>
        
        <button class="btn-carrito-flotante" id="btnCarritoFlotante" title="Ver carrito">
            <i class="fas fa-shopping-cart"></i>
            <span class="carrito-contador" id="carritoContador" style="display: none;">0</span>
        </button>
    </div>

    <!-- Portada Mejorada -->
    <section class="portada">
        <div class="portada-content">
            <div class="logos-container">
                <a href="https://www.tiktok.com/@naturista_venuz" target="_blank" class="logo-wrapper logo-templo">
                    <img id="logoTemplo" src="{recursos['logo_templo']}" alt="Templo Garage" class="logo-img">
                    <div class="logo-label">Templo Garage Street</div>
                </a>
                <a href="https://www.tiktok.com/@brujablanca51" target="_blank" class="logo-wrapper logo-tiktok">
                    <img id="logoTiktok" src="{recursos['logo_tiktok']}" alt="TikTok Moto Parts" class="logo-img">
                    <div class="logo-label">TikTok Moto Parts</div>
                </a>
            </div>
            
            <h1 class="main-title">CATÁLOGO PROFESIONAL DE REPUESTOS</h1>
            <p class="subtitle">Todo para tu moto en un solo lugar. Envíos a todo Colombia. Pago seguro con Wompi.</p>
            
            <div class="protect-text">
                🛡️ PROTEGEMOS TODAS TUS PARTES 🛡️
            </div>
        </div>
    </section>

    <!-- Buscador Avanzado -->
    <section class="buscador-avanzado">
        <div class="buscador-container">
            <i class="fas fa-search"></i>
            <input type="text" 
                   id="buscadorPrincipal" 
                   placeholder="Busca por marca, producto o referencia... (escribe aunque sea mal escrito)"
                   autocomplete="off">
            <div class="sugerencias" id="sugerenciasBusqueda"></div>
        </div>
        
        <div class="filtros-desplegables">
            <select id="filtroMarca" class="filtro-select">
                <option value="">Todas las marcas</option>
            </select>
            
            <select id="filtroTipo" class="filtro-select">
                <option value="">Todos los tipos</option>
            </select>
        </div>
    </section>

    <!-- Grid de Productos -->
    <div class="productos-grid" id="productosGrid">
        <!-- Los productos se cargan aquí dinámicamente -->
    </div>

    <!-- Paginación -->
    <div class="paginacion" id="paginacion">
        <!-- Se genera dinámicamente -->
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

    <!-- Chat Widget Mejorado -->
    <div class="chat-widget collapsed" id="chatWidget">
        <div class="chat-header" onclick="toggleChat()">
            <div class="chat-avatar">
                <i class="fas fa-headset"></i>
            </div>
            <div class="chat-info">
                <h5>Templo Garage</h5>
                <p>En línea • Responde al instante</p>
            </div>
            <div class="chat-indicator">
                <div class="pulse"></div>
            </div>
        </div>
        
        <div class="chat-body" id="chatBody">
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
        // CONFIGURACIÓN DEL SISTEMA
        // ==============================================
        const CONFIG_SISTEMA = {{
            WOMPI_PUBLIC_KEY: "{CONFIG['WOMPI_PUBLIC_KEY']}",
            WOMPI_INTEGRITY_SECRET: "{CONFIG['WOMPI_INTEGRITY_SECRET']}",
            RESEND_API_KEY: "{CONFIG['RESEND_API_KEY']}",
            WHATSAPP_NUMERO: "{CONFIG['CONTACTO']['WHATSAPP']}",
            EMAIL_VENDEDOR: "{CONFIG['CONTACTO']['EMAIL_VENDEDOR']}",
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
                const cadenaConcatenada = `${{referencia}}${{montoEnCentavos}}COP${{CONFIG_SISTEMA.WOMPI_INTEGRITY_SECRET}}`;
                
                const encoder = new TextEncoder();
                const data = encoder.encode(cadenaConcatenada);
                const hashBuffer = await crypto.subtle.digest('SHA-256', data);
                const hashArray = Array.from(new Uint8Array(hashBuffer));
                const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
                
                console.log('Firma generada para referencia:', referencia);
                return hashHex;
                
            }} catch (error) {{
                console.error('Error generando firma:', error);
                return '3a4bd1f3e3edb5e88284c8e1e9a191fdf091ef0dfca9f057cb8f408667f054d0';
            }}
        }}

        // ==============================================
        // PAGINACIÓN
        // ==============================================
        function configurarPaginacion() {{
            productos = [...todosProductos];
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
                html += `<button class="paginacion-btn ${{i === paginaActual ? 'active' : ''}}" onclick="mostrarPagina(${{i}})">${{i}}</button>`;
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
            cargarTransacciones();
            inicializarTema();
            inicializarCarrito();
            inicializarChat();
            configurarPaginacion();
            inicializarBuscador();
            inicializarFiltros();
            inicializarBotonesWhatsapp();
            
            // Mensaje de bienvenida en chat
            setTimeout(() => {{
                mostrarOpcionesChat();
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
            // Obtener marcas y tipos únicos
            const marcas = [...new Set(todosProductos.map(p => p.marca).filter(m => m))];
            const tipos = [...new Set(todosProductos.map(p => p.tipo).filter(t => t))];
            
            const filtroMarca = document.getElementById('filtroMarca');
            const filtroTipo = document.getElementById('filtroTipo');
            
            // Llenar filtro de marcas
            marcas.sort().forEach(marca => {{
                const option = document.createElement('option');
                option.value = marca;
                option.textContent = marca;
                filtroMarca.appendChild(option);
            }});
            
            // Llenar filtro de tipos
            tipos.sort().forEach(tipo => {{
                const option = document.createElement('option');
                option.value = tipo;
                option.textContent = tipo;
                filtroTipo.appendChild(option);
            }});
            
            // Event listeners para filtros
            filtroMarca.addEventListener('change', aplicarFiltros);
            filtroTipo.addEventListener('change', aplicarFiltros);
        }}

        function aplicarFiltros() {{
            const marcaSeleccionada = document.getElementById('filtroMarca').value;
            const tipoSeleccionado = document.getElementById('filtroTipo').value;
            
            let filtrados = todosProductos;
            
            if (marcaSeleccionada) {{
                filtrados = filtrados.filter(p => p.marca === marcaSeleccionada);
            }}
            
            if (tipoSeleccionado) {{
                filtrados = filtrados.filter(p => p.tipo === tipoSeleccionado);
            }}
            
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
            
            productosARenderizar.forEach(producto => {{
                // Verificar si el producto ya está en el carrito
                const enCarrito = carrito.find(item => item.id === producto.id);
                const cantidadEnCarrito = enCarrito ? enCarrito.cantidad : 0;
                
                const card = document.createElement('div');
                card.className = 'producto-card';
                card.dataset.id = producto.id;
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
                        </div>
                    </div>
                `;
                
                grid.appendChild(card);
            }});
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
                imagen: carrito[0].imagen
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
        // SISTEMA DE PAGO WOMPI
        // ==============================================
        async function procesarPagoWompi(producto, cliente) {{
            mostrarLoading();
            
            try {{
                const precioFinal = producto.precio_final;
                const montoEnCentavos = Math.round(precioFinal * 100);
                const referencia = `TG_${{producto.id === 'carrito' ? 'CARRITO' : producto.id}}_${{Date.now()}}_${{Math.random().toString(36).substr(2, 9).toUpperCase()}}`;
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
                    redirectUrl: 'https://templogarage.com/confirmacion',
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
                
                checkout.open(function(result) {{
                    console.log('Resultado de Wompi:', result);
                    
                    const transaction = result.transaction;
                    if (transaction && transaction.status === 'APPROVED') {{
                        console.log('✅ Transacción exitosa ID:', transaction.id);
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
                
                const emailEnviado = await enviarComprobantes(cliente.email, producto, monto, referencia, transaccion);
                enviarWhatsAppConfirmacion(cliente.telefono, producto, monto, referencia, transaccion);
                
                mostrarToast('✅ ¡Compra exitosa! Revisa tu email y WhatsApp', 'success');
                cerrarModalCompra();
                ocultarLoading();
                
            }} catch (error) {{
                console.error('Error finalizando compra:', error);
                mostrarToast('Compra procesada, pero hubo error enviando comprobantes.', 'warning');
                ocultarLoading();
            }}
        }}

        async function enviarComprobantes(emailCliente, producto, monto, referencia, transaccion) {{
            try {{
                const fecha = new Date().toLocaleDateString('es-CO', {{
                    weekday: 'long',
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                }});
                
                const emailHtml = `
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                        <h2 style="color: #FF0000; text-align: center;">✅ COMPRA CONFIRMADA - TEMPLO GARAGE</h2>
                        <p>Gracias por tu compra. Aquí está tu comprobante:</p>
                        <div style="background: #f5f5f5; padding: 20px; border-radius: 10px; margin: 20px 0;">
                            <p><strong>Referencia:</strong> ${{referencia}}</p>
                            <p><strong>ID Transacción:</strong> ${{transaccion.id}}</p>
                            <p><strong>Fecha:</strong> ${{fecha}}</p>
                            <p><strong>Producto:</strong> ${{producto.nombre}}</p>
                            <p><strong>Marca:</strong> ${{producto.marca}}</p>
                            <p><strong>Total pagado:</strong> $${{monto.toLocaleString('es-CO')}}</p>
                            <p><strong>Estado:</strong> ✅ Aprobado</p>
                        </div>
                        <p>Guarda este comprobante para cualquier reclamo.</p>
                        <hr style="margin: 30px 0;">
                        <p><strong>Contacto:</strong><br>
                        WhatsApp: +57 {CONFIG['CONTACTO']['WHATSAPP']}<br>
                        TikTok: @brujablanca51</p>
                    </div>
                `;
                
                const response = await fetch('https://api.resend.com/emails', {{
                    method: 'POST',
                    headers: {{
                        'Authorization': `Bearer ${{CONFIG_SISTEMA.RESEND_API_KEY}}`,
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{
                        from: 'Templo Garage <ventas@templogarage.com>',
                        to: emailCliente,
                        subject: `✅ Comprobante #${{referencia}} - Templo Garage`,
                        html: emailHtml
                    }})
                }});
                
                if (!response.ok) throw new Error('Error enviando email');
                
                return true;
            }} catch (error) {{
                console.error('Error enviando email:', error);
                const asunto = `Comprobante compra ${{referencia}}`;
                const cuerpo = `Comprobante de compra Templo Garage%0A%0AReferencia: ${{referencia}}%0AProducto: ${{producto.nombre}}%0AMonto: $${{monto.toLocaleString()}}%0AID Transacción: ${{transaccion.id}}%0A%0A¡Gracias por tu compra!`;
                window.open(`mailto:${{emailCliente}}?subject=${{encodeURIComponent(asunto)}}&body=${{encodeURIComponent(cuerpo)}}`, '_blank');
                return false;
            }}
        }}

        function enviarWhatsAppConfirmacion(telefono, producto, monto, referencia, transaccion) {{
            try {{
                const mensaje = `✅ COMPRA CONFIRMADA - TEMPLO GARAGE%0A%0A` +
                               `Producto: ${{producto.nombre}}%0A` +
                               `Referencia: ${{referencia}}%0A` +
                               `ID Transacción: ${{transaccion.id}}%0A` +
                               `Total: $${{monto.toLocaleString()}}%0A%0A` +
                               `¡Gracias por tu compra! Te hemos enviado el comprobante al email registrado.%0A%0A` +
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
        // SISTEMA DE CHAT MEJORADO
        // ==============================================
        function toggleChat() {{
            document.getElementById('chatWidget').classList.toggle('collapsed');
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
            
            if (tipo === 'usuario') {{
                document.getElementById('chatWidget').classList.remove('collapsed');
            }}
        }}

        function mostrarOpcionesChat() {{
            const messages = document.getElementById('chatMessages');
            messages.innerHTML = '';
            
            agregarMensajeChat('¡Hola! 👋 Soy el asistente virtual de Templo Garage. ¿En qué puedo ayudarte hoy?', 'bot');
            
            setTimeout(() => {{
                const opcionesHTML = `
                    <div class="opciones-chat">
                        <button class="opcion-chat" onclick="seleccionarOpcionChat(1)">
                            🔍 Buscar un repuesto específico
                        </button>
                        <button class="opcion-chat" onclick="seleccionarOpcionChat(2)">
                            👨‍🔧 Contactar a un asesor (repuesto no encontrado)
                        </button>
                        <button class="opcion-chat" onclick="seleccionarOpcionChat(3)">
                            📦 Información sobre envíos y garantías
                        </button>
                        <button class="opcion-chat" onclick="seleccionarOpcionChat(4)">
                            💳 Métodos de pago y seguridad
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
            
            switch(opcion) {{
                case 1:
                    agregarMensajeChat('🔍 Buscar un repuesto específico', 'usuario');
                    setTimeout(() => {{
                        agregarMensajeChat('Escribe el nombre, marca o referencia del repuesto que buscas. Puedes escribir aunque no estés seguro de la ortografía.', 'bot');
                    }}, 500);
                    break;
                    
                case 2:
                    agregarMensajeChat('👨‍🔧 Contactar a un asesor (repuesto no encontrado)', 'usuario');
                    setTimeout(() => {{
                        agregarMensajeChat('Perfecto. Por favor, proporciona la siguiente información:<br><br>' +
                                          '1. 🏍️ Marca de la moto<br>' +
                                          '2. 📋 Modelo<br>' +
                                          '3. 📅 Año<br>' +
                                          '4. 🔧 Nombre del repuesto que necesitas<br>' +
                                          '5. 📦 Cantidad requerida<br><br>' +
                                          'Escribe toda la información en un solo mensaje.', 'bot');
                        datosChatAsesor = {{}};
                    }}, 500);
                    break;
                    
                case 3:
                    agregarMensajeChat('📦 Información sobre envíos y garantías', 'usuario');
                    setTimeout(() => {{
                        agregarMensajeChat('📦 **INFORMACIÓN DE ENVÍOS:**<br>' +
                                          '• 🚚 Bogotá: 24-48 horas<br>' +
                                          '• 🌎 Otras ciudades: 3-5 días hábiles<br>' +
                                          '• 🆓 Envío gratis en compras mayores a $200,000<br>' +
                                          '• 📦 Usamos Servientrega e Interrapidisimo<br><br>' +
                                          '✅ **GARANTÍAS:**<br>' +
                                          '• Todos los productos tienen garantía de 3 meses<br>' +
                                          '• 🔄 Devoluciones en 15 días si el producto está sin usar<br>' +
                                          '• 📞 Contacta por WhatsApp para gestionar garantías', 'bot');
                        setTimeout(() => mostrarOpcionesChat(), 2000);
                    }}, 500);
                    break;
                    
                case 4:
                    agregarMensajeChat('💳 Métodos de pago y seguridad', 'usuario');
                    setTimeout(() => {{
                        agregarMensajeChat('💳 **MÉTODOS DE PAGO:**<br>' +
                                          '• ✅ Tarjetas débito/crédito (Wompi)<br>' +
                                          '• 📱 Transferencias bancarias<br>' +
                                          '• 💰 Pago contra entrega (solo Bogotá)<br><br>' +
                                          '🛡️ **SEGURIDAD:**<br>' +
                                          '• 🔒 Pago 100% seguro con encriptación SSL<br>' +
                                          '• 🏦 Transacciones certificadas por Wompi<br>' +
                                          '• 📄 Factura electrónica incluida', 'bot');
                        setTimeout(() => mostrarOpcionesChat(), 2000);
                    }}, 500);
                    break;
            }}
        }}

        function responderChat(pregunta) {{
            const preguntaLower = pregunta.toLowerCase();
            
            if (estadoChat.startsWith('opcion_1')) {{
                // Búsqueda de repuesto
                const resultados = buscarFuzzy(pregunta, todosProductos, ['nombre', 'marca', 'descripcion', 'tipo'], 5);
                
                if (resultados.length > 0) {{
                    let mensaje = '🔍 Encontré estos repuestos:<br><br>';
                    
                    resultados.forEach((p, i) => {{
                        mensaje += `<strong>${{i+1}}. ${{p.nombre}}</strong><br>`;
                        mensaje += `🏷️ Marca: ${{p.marca}}<br>`;
                        mensaje += `📋 Tipo: ${{p.tipo}}<br>`;
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
                
                agregarMensajeChat('📝 Información recibida. ¿Quieres que envíe estos detalles a un asesor por WhatsApp? (responde "sí" o "no")', 'bot');
                estadoChat = 'enviar_asesor';
                
            }} else if (estadoChat === 'enviar_asesor') {{
                if (preguntaLower.includes('si') || preguntaLower.includes('sí')) {{
                    const mensaje = `🚨 SOLICITUD DE ASESOR - TEMPLO GARAGE%0A%0A` +
                                   `🆔 Cliente: Chat Web%0A` +
                                   `📝 Detalles:%0A${{datosChatAsesor.detalles.replace(/\\n/g, '%0A')}}%0A%0A` +
                                   `🕒 Fecha: ${{new Date().toLocaleString()}}`;
                    
                    window.open(`https://wa.me/${{CONFIG_SISTEMA.WHATSAPP_NUMERO}}?text=${{encodeURIComponent(mensaje)}}`, '_blank');
                    agregarMensajeChat('✅ He abierto WhatsApp para que puedas contactar a nuestro asesor con toda la información. ¿En qué más puedo ayudarte?', 'bot');
                }} else {{
                    agregarMensajeChat('De acuerdo, no se ha enviado el mensaje. ¿En qué más puedo ayudarte?', 'bot');
                }}
                estadoChat = '';
                setTimeout(() => mostrarOpcionesChat(), 1000);
                
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
                setTimeout(() => mostrarOpcionesChat(), 1000);
                
            }} else {{
                // Respuesta por defecto
                agregarMensajeChat('No estoy seguro de cómo ayudarte con eso. ¿Prefieres elegir una de las opciones?', 'bot');
                setTimeout(() => mostrarOpcionesChat(), 1000);
            }}
        }}

        function inicializarChat() {{
            const messages = document.getElementById('chatMessages');
            messages.innerHTML = '';
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
    </script>
</body>
</html>'''
    
    return html

# ==============================================
# FUNCIÓN PRINCIPAL
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
        imagenes_a_cargar = [
            ("logo_templo", CONFIG["RUTAS"]["LOGO_TEMPLO"]),
            ("logo_tiktok", CONFIG["RUTAS"]["LOGO_TIKTOK"]),
            ("portada", CONFIG["RUTAS"]["PORTADA"])
        ]
        
        for nombre, ruta in imagenes_a_cargar:
            if os.path.exists(ruta):
                print(f"   📁 {nombre}: Cargando...")
                base64_img = convertir_imagen_a_base64(ruta)
                if base64_img:
                    recursos[nombre] = base64_img
                    print(f"     ✅ Convertido a base64")
                else:
                    print(f"     ⚠️ No se pudo convertir")
                    recursos[nombre] = generar_url_placeholder(nombre.replace('_', ' '), 400, 200)
            else:
                print(f"   ❌ {nombre}: No encontrado en {ruta}")
                recursos[nombre] = generar_url_placeholder(nombre.replace('_', ' '), 400, 200)
        
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
        
        if len(df_limpio) > CONFIG["PARAMETROS"]["MAX_PRODUCTOS"]:
            print(f"   ⚠️ Limitar a {CONFIG['PARAMETROS']['MAX_PRODUCTOS']} productos")
            df_limpio = df_limpio.head(CONFIG["PARAMETROS"]["MAX_PRODUCTOS"])
        
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
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        tiempo_total = time.time() - start_time
        
        print(f"\n💾 ARCHIVO GUARDADO: {output_path}")
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

CONFIGURACIÓN WOMPI:
- Llave Pública: {CONFIG['WOMPI_PUBLIC_KEY'][:20]}...
- Secreto Integridad: {CONFIG['WOMPI_INTEGRITY_SECRET'][:20]}... (¡VERIFICA ESTO!)
- Resend Key: {CONFIG['RESEND_API_KEY'][:20]}...
- WhatsApp: {CONFIG['CONTACTO']['WHATSAPP']}
- Email: {CONFIG['CONTACTO']['EMAIL_VENDEDOR']}

IMPORTANTE: Para que Wompi funcione, necesitas obtener tu SECRETO DE INTEGRIDAD real desde:
Dashboard Wompi > Desarrolladores > Secretos para integración técnica

ARCHIVOS UTILIZADOS:
- Excel: {CONFIG['RUTAS']['EXCEL']}
- Logo Templo: {CONFIG['RUTAS']['LOGO_TEMPLO']}
- Logo TikTok: {CONFIG['RUTAS']['LOGO_TIKTOK']}
- Portada: {CONFIG['RUTAS']['PORTADA']}
"""
        
        with open('reporte_generacion.txt', 'w', encoding='utf-8') as f:
            f.write(reporte)
        
        print(f"\n📝 Reporte guardado en: reporte_generacion.txt")
        print("\n⚠️  ATENCIÓN: Para que Wompi funcione CORRECTAMENTE, necesitas:")
        print("   1. Obtener tu SECRETO DE INTEGRIDAD desde el dashboard de Wompi")
        print("   2. Reemplazar 'WOMPI_INTEGRITY_SECRET' en la línea 18 del código")
        print("   3. El secreto comienza con 'prod_integrity_' o 'test_integrity_'")
        
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