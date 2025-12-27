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

# ==============================================
# CONFIGURACIÓN PRINCIPAL
# ==============================================
CONFIG = {
    # API Keys (ACTUALIZADAS - REEMPLAZA EL SECRETO DE INTEGRIDAD)
    "WOMPI_PUBLIC_KEY": "pub_prod_I0KpwGvgPD3xNcLggJZKyD3cNUKrywkx",
    "WOMPI_INTEGRITY_SECRET": "prv_prod_vIazSzxilsFQzdiBt75rakWBzccyBfaC",  # ¡REEMPLAZA ESTO! Obtén el verdadero en tu dashboard
    "RESEND_API_KEY": "re_ZewmUDhy_NoAiD8ss2yZroL8uY56EDZHo",
    
    # Rutas de archivos
    "RUTAS": {
        "EXCEL": r"C:\Users\Giral\OneDrive\Documentos\CATQALOGO MOTOS\catalogo_completo\CATALOGO TEMPLO GARAGE.xlsm",
        "LOGO_TEMPLO": r"C:\Users\Giral\OneDrive\Documentos\CATQALOGO MOTOS\logo\TEMPLO GARAGE STREET.png",
        "LOGO_TIKTOK": r"C:\Users\Giral\OneDrive\Documentos\CATQALOGO MOTOS\logo\LOGO TIKTOK.png",
        "PORTADA": r"C:\Users\Giral\OneDrive\Documentos\CATQALOGO MOTOS\logo\iloveimg-background-removed\portada.png",
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
    
    # Configuración de comisiones (simplificada)
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
        
        # Determinar el tipo MIME
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
    
    # Convertir a minúsculas y eliminar acentos
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    texto = texto.lower()
    
    # Eliminar caracteres especiales excepto espacios
    texto = re.sub(r'[^a-z0-9\s]', '', texto)
    
    # Eliminar espacios múltiples
    texto = re.sub(r'\s+', ' ', texto)
    
    return texto.strip()

def calcular_precio_final(precio_base):
    """Calcula el precio final con comisión e IVA simplificado"""
    if precio_base <= 0:
        return {"total": 0, "precio_base": 0}
    
    try:
        # Calcular comisión (usamos tarjeta como estándar)
        comision = precio_base * (CONFIG["COMISION_TARJETA"] / 100)
        
        # Calcular IVA sobre la comisión (19%)
        iva_comision = comision * (CONFIG["PARAMETROS"]["IVA_PORCENTAJE"] / 100)
        
        # Precio total
        total = precio_base + comision + iva_comision
        
        # Redondear a múltiplos de 100
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
        
        # Eliminar símbolos no numéricos
        precio_limpio = re.sub(r'[^\d.,]', '', precio_str)
        
        # Manejar diferentes formatos decimales
        if '.' in precio_limpio and ',' in precio_limpio:
            # Formato 1.000,00
            precio_limpio = precio_limpio.replace('.', '').replace(',', '.')
        elif ',' in precio_limpio:
            # Formato 1000,00
            precio_limpio = precio_limpio.replace(',', '.')
        
        return float(precio_limpio) if precio_limpio else 0
        
    except Exception as e:
        print(f"⚠️ Error procesando precio '{precio_raw}': {e}")
        return 0

def generar_url_placeholder(texto, ancho=400, alto=300):
    """Genera URL de placeholder con color basado en hash del texto"""
    # Colores profesionales para motos
    colores_motos = [
        ('FF0000', 'FFFFFF'),  # Rojo/Blanco
        ('1a237e', 'FFFFFF'),  # Azul/Blanco
        ('25D366', 'FFFFFF'),  # Verde/Blanco
        ('FFC107', '000000'),  # Amarillo/Negro
        ('9C27B0', 'FFFFFF'),  # Púrpura/Blanco
        ('FF5722', 'FFFFFF'),  # Naranja/Blanco
        ('607D8B', 'FFFFFF'),  # Gris/Blanco
    ]
    
    # Generar índice de color basado en hash del texto
    if texto:
        hash_obj = hashlib.md5(texto.encode())
        hash_int = int(hash_obj.hexdigest(), 16)
        color_idx = hash_int % len(colores_motos)
    else:
        color_idx = 0
    
    color_fondo, color_texto = colores_motos[color_idx]
    
    # Codificar texto para URL
    texto_codificado = texto.replace(' ', '+')[:20] if texto else "Producto"
    
    return f"https://via.placeholder.com/{ancho}x{alto}/{color_fondo}/{color_texto}?text={texto_codificado}"

def limpiar_datos_excel(df):
    """Limpia y valida los datos del DataFrame"""
    print("🧹 Limpiando datos del Excel...")
    
    # Crear copia para no modificar el original
    df_limpio = df.copy()
    
    # Eliminar filas completamente vacías
    df_limpio = df_limpio.dropna(how='all')
    
    # Renombrar columnas a nombres estándar si es necesario
    column_rename = {}
    for col_std, posibles in CONFIG["EXCEL"]["COLUMNAS"].items():
        for col in df_limpio.columns:
            if col in posibles:
                column_rename[col] = col_std
                break
    
    if column_rename:
        df_limpio = df_limpio.rename(columns=column_rename)
        print(f"   ✅ Columnas renombradas: {column_rename}")
    
    # Asegurar que existan las columnas requeridas
    columnas_requeridas = ['marca', 'nombre']
    for col in columnas_requeridas:
        if col not in df_limpio.columns:
            df_limpio[col] = None
            print(f"   ⚠️ Columna '{col}' no encontrada, se crea vacía")
    
    # Limpiar marca
    if 'marca' in df_limpio.columns:
        df_limpio['marca'] = df_limpio['marca'].fillna('Genérica')
        df_limpio['marca'] = df_limpio['marca'].astype(str).str.strip().str[:30]
    
    # Limpiar nombre
    if 'nombre' in df_limpio.columns:
        df_limpio['nombre'] = df_limpio['nombre'].fillna('Sin nombre')
        df_limpio['nombre'] = df_limpio['nombre'].astype(str).str.strip().str[:100]
    
    # Limpiar descripción
    if 'descripcion' in df_limpio.columns:
        df_limpio['descripcion'] = df_limpio['descripcion'].fillna('Sin descripción')
        df_limpio['descripcion'] = df_limpio['descripcion'].astype(str).str.strip().str[:150]
    
    # Limpiar tipo
    if 'tipo' in df_limpio.columns:
        df_limpio['tipo'] = df_limpio['tipo'].fillna('Accesorio')
        df_limpio['tipo'] = df_limpio['tipo'].astype(str).str.strip().str[:20]
    
    # Convertir precio a numérico
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
                    
                    # Actualizar estadísticas
                    if producto['precio'] > 0:
                        self.estadisticas['con_precio'] += 1
                    self.estadisticas['marcas_unicas'].add(producto['marca'])
                    self.estadisticas['tipos_unicos'].add(producto['tipo'])
                    
                    # Mostrar progreso cada 500 productos
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
            # Extraer y limpiar datos
            marca = str(fila.get('marca', '')).strip()[:30] or 'Genérica'
            nombre = str(fila.get('nombre', '')).strip()[:100] or 'Sin nombre'
            descripcion = str(fila.get('descripcion', '')).strip()[:150] or 'Sin descripción'
            tipo = str(fila.get('tipo', '')).strip()[:20] or 'Accesorio'
            precio = float(fila.get('precio', 0)) if pd.notna(fila.get('precio')) else 0
            
            # Procesar imagen
            imagen_raw = fila.get('imagen', '')
            if pd.isna(imagen_raw) or not isinstance(imagen_raw, str) or not imagen_raw.startswith(('http', 'https')):
                imagen = generar_url_placeholder(marca)
            else:
                imagen = str(imagen_raw).strip()
            
            # Calcular precio final (simplificado)
            calculo = calcular_precio_final(precio)
            
            # Crear objeto producto
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
    
    # Preparar datos JSON para JavaScript
    productos_json = json.dumps(productos, ensure_ascii=False, separators=(',', ':'))
    
    # Obtener fecha actual
    fecha_actual = datetime.now().strftime('%d/%m/%Y %H:%M')
    
    # Generar HTML
    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Templo Garage Street & TikTok Moto Parts - Catálogo Profesional</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap">
    <!-- PASO 1 DE WOMPI: Incluir el script del widget -->
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
            
            /* Variables para tema claro/oscuro */
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
            height: 80vh;
            min-height: 600px;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            overflow: hidden;
            padding: 20px;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%);
        }}

        .portada::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: var(--gradient-primary);
            opacity: 0.1;
            z-index: 1;
        }}

        .portada-content {{
            position: relative;
            z-index: 2;
            max-width: 1400px;
            width: 100%;
        }}

        /* ===== LOGOS PROFESIONALES ANIMADOS ===== */
        .logos-container {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 60px;
            margin-bottom: 40px;
            flex-wrap: wrap;
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
            width: 300px;
            text-decoration: none;
            color: inherit;
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
            height: 120px;
            width: auto;
            max-width: 250px;
            object-fit: contain;
            filter: drop-shadow(0 10px 20px rgba(0,0,0,0.7));
            margin-bottom: 20px;
            z-index: 1;
        }}

        .logo-label {{
            font-size: 18px;
            font-weight: 700;
            color: white;
            text-shadow: 2px 2px 8px rgba(0,0,0,0.8);
            padding: 10px 25px;
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
            font-size: 3.5rem;
            font-weight: 800;
            margin-bottom: 20px;
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 10px 30px rgba(0,0,0,0.5);
            line-height: 1.2;
        }}

        .subtitle {{
            font-size: 1.5rem;
            color: var(--text-primary);
            margin-bottom: 30px;
            max-width: 800px;
            margin-left: auto;
            margin-right: auto;
            background: rgba(0, 0, 0, 0.5);
            padding: 15px 30px;
            border-radius: 15px;
            border-left: 4px solid var(--primary);
            border-right: 4px solid var(--secondary);
        }}

        .protect-text {{
            font-size: 3rem;
            font-weight: 900;
            color: white;
            margin: 40px auto 80px auto;
            padding: 20px 40px;
            text-align: center;
            background: var(--gradient-protect);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 20px rgba(255, 152, 0, 0.5);
            border: 3px solid;
            border-image: linear-gradient(135deg, #FF0000, #FF9800, #FF0000) 1;
            position: relative;
            animation: protectPulse 2s ease-in-out infinite;
            max-width: 90%;
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

        /* ===== BUSCADOR MEJORADO ===== */
        .buscador-avanzado {{
            background: linear-gradient(135deg, var(--bg-secondary), var(--card-bg));
            padding: 20px;
            border-radius: 15px;
            margin: 20px auto;
            max-width: 1200px;
            box-shadow: var(--card-shadow);
        }}

        .buscador-container {{
            position: relative;
            max-width: 800px;
            margin: 0 auto 20px;
        }}

        .buscador-container i {{
            position: absolute;
            left: 20px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--primary);
            font-size: 18px;
            z-index: 2;
        }}

        .buscador-container input {{
            width: 100%;
            padding: 15px 20px 15px 50px;
            border: 2px solid var(--primary);
            border-radius: 25px;
            background: rgba(255, 255, 255, 0.1);
            color: var(--text-primary);
            font-size: 16px;
            transition: all 0.3s;
        }}

        .buscador-container input:focus {{
            background: rgba(255, 255, 255, 0.15);
            outline: none;
            box-shadow: 0 0 20px rgba(255, 0, 0, 0.3);
        }}

        .sugerencias {{
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: var(--card-bg);
            border-radius: 10px;
            box-shadow: var(--card-shadow);
            max-height: 300px;
            overflow-y: auto;
            display: none;
            z-index: 1000;
            border: 1px solid var(--border-color);
        }}

        .sugerencia-item {{
            padding: 12px 20px;
            border-bottom: 1px solid var(--border-color);
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 10px;
            transition: background 0.2s;
            color: var(--text-primary);
        }}

        .sugerencia-item:hover {{
            background: rgba(255, 0, 0, 0.1);
        }}

        .sugerencia-item img {{
            width: 40px;
            height: 40px;
            object-fit: cover;
            border-radius: 5px;
        }}

        .filtros-rapidos {{
            display: flex;
            justify-content: center;
            gap: 10px;
            flex-wrap: wrap;
        }}

        .filtro-btn {{
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 0, 0, 0.3);
            color: var(--text-primary);
            padding: 10px 20px;
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .filtro-btn:hover {{
            background: var(--primary);
            transform: translateY(-2px);
        }}

        /* ===== CONTROLES SUPERIORES ===== */
        .controles-superiores {{
            position: fixed;
            top: 20px;
            right: 20px;
            display: flex;
            gap: 10px;
            z-index: 9999;
        }}

        .btn-carrito-flotante {{
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, var(--secondary), #283593);
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            cursor: pointer;
            box-shadow: 0 5px 15px rgba(26, 35, 126, 0.3);
            border: none;
            position: relative;
        }}

        .btn-toggle-modo {{
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, var(--primary), #ff3333);
            color: white;
            border: none;
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            box-shadow: 0 5px 15px rgba(255, 0, 0, 0.3);
            transition: transform 0.3s;
        }}

        .btn-toggle-modo:hover {{
            transform: rotate(30deg);
        }}

        .carrito-contador {{
            position: absolute;
            top: -5px;
            right: -5px;
            background: var(--accent);
            color: white;
            width: 22px;
            height: 22px;
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
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
            padding: 20px;
            max-width: 1400px;
            margin: 0 auto;
        }}

        /* 2 columnas en móvil */
        @media (max-width: 768px) {{
            .productos-grid {{
                grid-template-columns: repeat(2, 1fr);
                gap: 12px;
                padding: 12px;
            }}
            
            .producto-card {{
                margin: 0;
                border-radius: 12px;
                padding: 12px;
                transition: transform 0.2s;
            }}
            
            .producto-card:active {{
                transform: scale(0.98);
            }}
            
            .producto-imagen {{
                height: 140px;
                border-radius: 8px;
            }}
            
            .producto-titulo {{
                font-size: 14px;
                line-height: 1.3;
                height: 36px;
                overflow: hidden;
                margin-bottom: 8px;
            }}
            
            .producto-precio {{
                font-size: 16px;
                font-weight: 700;
                margin-bottom: 10px;
            }}
            
            .btn-comprar {{
                padding: 10px 15px;
                font-size: 13px;
                width: 100%;
            }}
            
            .main-title {{
                font-size: 2rem;
            }}
            
            .subtitle {{
                font-size: 1rem;
                padding: 10px 20px;
            }}
            
            .protect-text {{
                font-size: 1.8rem;
                padding: 15px 25px;
            }}
            
            .logos-container {{
                gap: 20px;
            }}
            
            .logo-wrapper {{
                width: 90%;
                max-width: 280px;
                padding: 20px;
            }}

            .controles-superiores {{
                top: 10px;
                right: 10px;
                gap: 8px;
            }}

            .btn-carrito-flotante,
            .btn-toggle-modo {{
                width: 45px;
                height: 45px;
                font-size: 18px;
            }}
        }}

        /* Tablets - 3 columnas */
        @media (min-width: 769px) and (max-width: 1024px) {{
            .productos-grid {{
                grid-template-columns: repeat(3, 1fr);
                gap: 15px;
            }}
        }}

        /* Escritorio grande - 4 columnas */
        @media (min-width: 1025px) {{
            .productos-grid {{
                grid-template-columns: repeat(4, 1fr);
            }}
        }}

        /* ===== TARJETAS DE PRODUCTO MEJORADAS ===== */
        .producto-card {{
            background: var(--card-bg);
            border-radius: 15px;
            padding: 15px;
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
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(255, 0, 0, 0.2);
            border-color: var(--primary);
        }}

        .producto-badge {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: var(--primary);
            color: white;
            padding: 5px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            z-index: 2;
        }}

        .producto-badge.oferta {{
            background: linear-gradient(135deg, #FF0000, #FF9800);
        }}

        .producto-imagen {{
            width: 100%;
            height: 200px;
            object-fit: contain;
            border-radius: 10px;
            margin-bottom: 15px;
            background: rgba(255, 255, 255, 0.05);
            padding: 10px;
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
            transform: scale(1.05);
        }}

        .producto-info {{
            flex: 1;
            display: flex;
            flex-direction: column;
        }}

        .producto-marca {{
            font-size: 12px;
            color: var(--primary);
            font-weight: 600;
            margin-bottom: 5px;
            text-transform: uppercase;
        }}

        .producto-titulo {{
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 10px;
            color: var(--text-primary);
            line-height: 1.3;
            flex: 1;
        }}

        .producto-descripcion {{
            font-size: 13px;
            color: var(--text-secondary);
            margin-bottom: 15px;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}

        .producto-precio {{
            margin-bottom: 15px;
        }}

        .precio-actual {{
            font-size: 20px;
            font-weight: 700;
            color: var(--primary);
        }}

        .precio-original {{
            font-size: 14px;
            color: var(--text-secondary);
            text-decoration: line-through;
            margin-right: 8px;
        }}

        .precio-consultar {{
            font-size: 16px;
            color: var(--warning);
            font-weight: 600;
        }}

        .btn-comprar {{
            background: linear-gradient(135deg, var(--primary), #ff3333);
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 10px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            width: 100%;
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
            gap: 10px;
            margin: 30px auto;
            flex-wrap: wrap;
        }}

        .paginacion-btn {{
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            width: 40px;
            height: 40px;
            border-radius: 8px;
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
            margin: 0 15px;
        }}

        /* ===== MODAL DE COMPRA MEJORADO ===== */
        .modal-compra {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
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
            width: 90%;
            max-width: 500px;
            border-radius: 20px;
            padding: 30px;
            position: relative;
            color: var(--text-primary);
            max-height: 90vh;
            overflow-y: auto;
            border: 1px solid var(--border-color);
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
        }}

        .modal-close {{
            position: absolute;
            top: 20px;
            right: 20px;
            background: none;
            border: none;
            font-size: 24px;
            color: var(--text-primary);
            cursor: pointer;
            width: 30px;
            height: 30px;
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
            margin-bottom: 30px;
            color: var(--primary);
        }}

        .form-group {{
            margin-bottom: 20px;
        }}

        .form-group label {{
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: var(--text-secondary);
        }}

        .form-group input,
        .form-group select {{
            width: 100%;
            padding: 12px 15px;
            border: 2px solid var(--border-color);
            border-radius: 10px;
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

        /* Selector de país mejorado */
        .phone-input-container {{
            display: flex;
            gap: 10px;
        }}

        .country-select {{
            flex: 0 0 120px;
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 12px 15px;
            border: 2px solid var(--border-color);
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.05);
        }}

        .country-select img {{
            width: 20px;
            height: 15px;
            object-fit: cover;
            border-radius: 2px;
        }}

        .phone-input {{
            flex: 1;
        }}

        .resumen-compra {{
            background: rgba(255, 255, 255, 0.05);
            padding: 20px;
            border-radius: 10px;
            margin: 25px 0;
        }}

        .resumen-total {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 15px;
            border-top: 2px solid var(--border-color);
            font-size: 18px;
        }}

        .btn-pagar {{
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, var(--primary), #ff3333);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            transition: transform 0.3s;
        }}

        .btn-pagar:hover {{
            transform: translateY(-2px);
        }}

        .texto-seguro {{
            text-align: center;
            margin-top: 15px;
            color: var(--text-secondary);
            font-size: 14px;
        }}

        /* ===== CHAT WIDGET ===== */
        .chat-widget {{
            position: fixed;
            bottom: 100px;
            right: 20px;
            width: 350px;
            background: var(--card-bg);
            border-radius: 15px;
            box-shadow: var(--card-shadow);
            z-index: 9999;
            overflow: hidden;
            transform: translateY(0);
            transition: transform 0.3s;
            border: 1px solid var(--border-color);
        }}

        .chat-widget.collapsed {{
            transform: translateY(calc(100% - 70px));
        }}

        .chat-header {{
            background: linear-gradient(135deg, var(--primary), #ff3333);
            color: white;
            padding: 15px;
            display: flex;
            align-items: center;
            gap: 15px;
            cursor: pointer;
        }}

        .chat-body {{
            height: 400px;
            display: flex;
            flex-direction: column;
        }}

        .chat-messages {{
            flex: 1;
            padding: 15px;
            overflow-y: auto;
            background: var(--bg-secondary);
        }}

        .mensaje {{
            margin-bottom: 15px;
            max-width: 80%;
            clear: both;
        }}

        .mensaje.bot {{
            float: left;
        }}

        .mensaje.usuario {{
            float: right;
        }}

        .burbuja {{
            padding: 12px 15px;
            border-radius: 20px;
            font-size: 14px;
            line-height: 1.4;
            max-width: 100%;
            word-wrap: break-word;
        }}

        .mensaje.bot .burbuja {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 20px 20px 20px 5px;
        }}

        .mensaje.usuario .burbuja {{
            background: linear-gradient(135deg, var(--primary), #ff3333);
            color: white;
            border-radius: 20px 20px 5px 20px;
        }}

        .chat-input-container {{
            display: flex;
            padding: 15px;
            background: var(--card-bg);
            border-top: 1px solid var(--border-color);
            gap: 10px;
        }}

        .chat-input-container input {{
            flex: 1;
            padding: 12px 15px;
            border: 2px solid var(--border-color);
            border-radius: 25px;
            font-size: 14px;
            transition: border 0.3s;
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-primary);
        }}

        .chat-input-container input:focus {{
            border-color: var(--primary);
            outline: none;
        }}

        .chat-input-container button {{
            width: 50px;
            background: var(--primary);
            color: white;
            border: none;
            border-radius: 50%;
            cursor: pointer;
            transition: background 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .chat-input-container button:hover {{
            background: #cc0000;
        }}

        /* ===== NOTIFICACIONES TOAST ===== */
        .toast-notification {{
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: var(--card-bg);
            color: var(--text-primary);
            padding: 15px 20px;
            border-radius: 10px;
            box-shadow: var(--card-shadow);
            z-index: 10000;
            display: flex;
            align-items: center;
            gap: 10px;
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
            background: rgba(0, 0, 0, 0.7);
            z-index: 10000;
            align-items: center;
            justify-content: center;
        }}

        .spinner {{
            width: 50px;
            height: 50px;
            border: 5px solid rgba(255, 255, 255, 0.3);
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
            padding: 40px 20px;
            text-align: center;
            margin-top: 50px;
            border-top: 1px solid var(--border-color);
        }}

        .footer-links {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }}

        .footer-links a {{
            color: var(--text-secondary);
            text-decoration: none;
            transition: color 0.3s;
        }}

        .footer-links a:hover {{
            color: var(--primary);
        }}

        .copyright {{
            color: var(--text-secondary);
            font-size: 14px;
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
            padding: 3px 8px;
            border-radius: 10px;
            font-size: 12px;
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
                   placeholder="Busca por marca, producto o referencia..."
                   autocomplete="off">
            <div class="sugerencias" id="sugerenciasBusqueda"></div>
        </div>
        
        <div class="filtros-rapidos">
            <button class="filtro-btn" data-tipo="yamaha">
                <i class="fas fa-motorcycle"></i> Yamaha
            </button>
            <button class="filtro-btn" data-tipo="honda">
                <i class="fas fa-motorcycle"></i> Honda
            </button>
            <button class="filtro-btn" data-tipo="suzuki">
                <i class="fas fa-motorcycle"></i> Suzuki
            </button>
            <button class="filtro-btn" data-tipo="akt">
                <i class="fas fa-motorcycle"></i> AKT
            </button>
            <button class="filtro-btn" data-tipo="ofertas">
                <i class="fas fa-fire"></i> Ofertas
            </button>
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

    <!-- Chat Widget -->
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
        let carrito = [];
        let transacciones = [];
        let paginaActual = 1;
        let totalPaginas = 1;

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
        // FUNCIÓN CRÍTICA: GENERAR FIRMA DE INTEGRIDAD WOMPI
        // ==============================================
        async function generarFirmaIntegridad(referencia, montoEnCentavos) {{
            try {{
                // PASO 3 DE WOMPI: Generar firma de integridad según documentación
                // Cadena concatenada: referencia + monto + moneda + secreto
                const cadenaConcatenada = `${{referencia}}${{montoEnCentavos}}COP${{CONFIG_SISTEMA.WOMPI_INTEGRITY_SECRET}}`;
                
                // Encriptar con SHA256 (como indica la documentación)
                const encoder = new TextEncoder();
                const data = encoder.encode(cadenaConcatenada);
                const hashBuffer = await crypto.subtle.digest('SHA-256', data);
                const hashArray = Array.from(new Uint8Array(hashBuffer));
                const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
                
                console.log('Firma generada para referencia:', referencia);
                return hashHex;
                
            }} catch (error) {{
                console.error('Error generando firma:', error);
                // Fallback: firma de prueba (NO USAR EN PRODUCCIÓN)
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
            
            // Botón anterior
            html += `<button class="paginacion-btn" onclick="cambiarPagina(${{paginaActual - 1}})" ${{paginaActual === 1 ? 'disabled' : ''}}>
                        <i class="fas fa-chevron-left"></i>
                    </button>`;
            
            // Números de página
            const inicio = Math.max(1, paginaActual - 2);
            const fin = Math.min(totalPaginas, inicio + 4);
            
            for (let i = inicio; i <= fin; i++) {{
                html += `<button class="paginacion-btn ${{i === paginaActual ? 'active' : ''}}" onclick="mostrarPagina(${{i}})">${{i}}</button>`;
            }}
            
            // Botón siguiente
            html += `<button class="paginacion-btn" onclick="cambiarPagina(${{paginaActual + 1}})" ${{paginaActual === totalPaginas ? 'disabled' : ''}}>
                        <i class="fas fa-chevron-right"></i>
                    </button>`;
            
            // Información
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
            // Cargar transacciones
            cargarTransacciones();
            
            // Inicializar sistemas
            inicializarTema();
            inicializarCarrito();
            inicializarChat();
            configurarPaginacion();
            inicializarBuscador();
            
            // Mensaje de bienvenida en chat
            setTimeout(() => {{
                agregarMensajeChat('¡Hola! 👋 Soy el asistente virtual de Templo Garage. ¿En qué puedo ayudarte hoy?', 'bot');
            }}, 2000);
            
            // Mostrar estadísticas en consola
            console.log(`📊 Catálogo cargado: ${{todosProductos.length}} productos`);
            console.log(`🔑 Wompi configurado con llave: ${{CONFIG_SISTEMA.WOMPI_PUBLIC_KEY.substring(0, 20)}}...`);
        }});

        // ==============================================
        // SISTEMA DE PRODUCTOS
        // ==============================================
        function renderizarProductos(productosARenderizar) {{
            const grid = document.getElementById('productosGrid');
            grid.innerHTML = '';
            
            productosARenderizar.forEach(producto => {{
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
                        
                        <button class="btn-comprar" onclick="iniciarCompra(${{producto.id}})" ${{producto.precio <= 0 ? 'disabled' : ''}}>
                            <i class="fas fa-shopping-cart"></i> ${{producto.precio > 0 ? 'COMPRAR AHORA' : 'CONSULTAR'}}
                        </button>
                    </div>
                `;
                
                grid.appendChild(card);
            }});
        }}

        // ==============================================
        // SISTEMA DE PAGO WOMPI (IMPLEMENTACIÓN OFICIAL SEGÚN DOCUMENTACIÓN)
        // ==============================================
        async function procesarPagoWompi(producto, cliente) {{
            mostrarLoading();
            
            try {{
                const precioFinal = producto.precio_final;
                const montoEnCentavos = Math.round(precioFinal * 100);
                
                // PASO 2 DE WOMPI: Generar referencia única
                const referencia = `TG_${{producto.id}}_${{Date.now()}}_${{Math.random().toString(36).substr(2, 9).toUpperCase()}}`;
                
                // Generar firma de integridad (PASO 3)
                const firmaIntegridad = await generarFirmaIntegridad(referencia, montoEnCentavos);
                
                console.log('=== CONFIGURACIÓN WOMPI ===');
                console.log('Referencia:', referencia);
                console.log('Monto (centavos):', montoEnCentavos);
                console.log('Firma generada:', firmaIntegridad.substring(0, 20) + '...');
                
                // PASO 2 DE WOMPI: Configurar widget según documentación oficial
                const checkoutConfig = {{
                    currency: 'COP',
                    amountInCents: montoEnCentavos,
                    reference: referencia,
                    publicKey: CONFIG_SISTEMA.WOMPI_PUBLIC_KEY,
                    signature: {{ integrity: firmaIntegridad }},
                    redirectUrl: 'https://templogarage.com/confirmacion', // Cambia esto por tu URL real
                    customerData: {{
                        email: cliente.email,
                        fullName: cliente.nombre,
                        phoneNumber: cliente.telefono.replace(/\\D/g, ''),
                        phoneNumberPrefix: '+57',
                        legalId: '1234567890', // En producción, pedir al cliente
                        legalIdType: 'CC'
                    }},
                    taxInCents: {{
                        vat: Math.round((producto.precio_final - producto.precio) * 100 * 0.19) // IVA estimado
                    }}
                }};
                
                console.log('Configuración completa:', checkoutConfig);
                
                // Crear instancia del widget (como muestra la documentación)
                const checkout = new WidgetCheckout(checkoutConfig);
                
                // PASO 3 DE WOMPI: Abrir widget con callback según documentación
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
                
                // 1. Registrar transacción localmente
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
                
                // 2. Enviar comprobantes por email
                const emailEnviado = await enviarComprobantes(cliente.email, producto, monto, referencia, transaccion);
                
                // 3. Enviar WhatsApp automático
                enviarWhatsAppConfirmacion(cliente.telefono, producto, monto, referencia, transaccion);
                
                // 4. Mostrar confirmación
                mostrarToast('✅ ¡Compra exitosa! Revisa tu email y WhatsApp', 'success');
                
                // 5. Cerrar modal
                cerrarModalCompra();
                
                ocultarLoading();
                
                // 6. Redirigir a página de agradecimiento (opcional)
                setTimeout(() => {{
                    // window.location.href = '/gracias.html?id=' + transaccion.id;
                }}, 2000);
                
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
                
                // Enviar al cliente
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
                // Fallback: permitir al cliente enviar email manualmente
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
            // Mantener solo últimas 50
            transacciones = transacciones.slice(0, 50);
            localStorage.setItem('transacciones_templo', JSON.stringify(transacciones));
        }}

        // ==============================================
        // SISTEMA DE CHAT
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
            
            // Agregar mensaje del usuario
            agregarMensajeChat(texto, 'usuario');
            input.value = '';
            
            // Respuesta automática después de 1 segundo
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
                <div class="hora-mensaje">${{hora}}</div>
            `;
            
            messages.appendChild(mensaje);
            messages.scrollTop = messages.scrollHeight;
            
            // Abrir chat si está colapsado
            if (tipo === 'usuario') {{
                document.getElementById('chatWidget').classList.remove('collapsed');
            }}
        }}

        function responderChat(pregunta) {{
            const preguntaLower = pregunta.toLowerCase();
            let respuesta = '';
            
            if (preguntaLower.includes('precio') || preguntaLower.includes('cuesta')) {{
                respuesta = "Los precios incluyen IVA y comisiones. Selecciona cualquier producto para ver el precio final.";
            }} else if (preguntaLower.includes('envío') || preguntaLower.includes('entrega')) {{
                respuesta = "📦 **Envíos:**\\n• Bogotá: 24-48 horas\\n• Otras ciudades: 3-5 días\\n• Envío gratis en compras mayores a $200,000\\n• Usamos Servientrega e Interrapidisimo";
            }} else if (preguntaLower.includes('garantía') || preguntaLower.includes('devolución')) {{
                respuesta = "✅ **Garantía:**\\n• Todos los productos tienen garantía de 3 meses\\n• Devoluciones en 15 días si el producto está sin usar\\n• Contacta por WhatsApp para gestionar garantías";
            }} else if (preguntaLower.includes('contacto') || preguntaLower.includes('whatsapp')) {{
                respuesta = "📱 **Contacto directo:**\\n• WhatsApp: +57 {CONFIG['CONTACTO']['WHATSAPP']}\\n• TikTok: @brujablanca51\\n• Email: templogarage@gmail.com\\n• Horario: Lunes a Sábado 8AM - 6PM";
            }} else if (preguntaLower.includes('hola') || preguntaLower.includes('buenas')) {{
                respuesta = "¡Hola! 👋 Soy el asistente virtual de Templo Garage. ¿En qué puedo ayudarte hoy?";
            }} else {{
                const respuestas = [
                    "¿Te gustaría que te ayude a encontrar algún repuesto en específico?",
                    "Puedes usar los filtros por marca para encontrar más fácil lo que necesitas.",
                    "Si necesitas asistencia inmediata, escribe directamente al WhatsApp +57 {CONFIG['CONTACTO']['WHATSAPP']}",
                    "¿Ya viste nuestras ofertas especiales? Tenemos descuentos en varias marcas."
                ];
                respuesta = respuestas[Math.floor(Math.random() * respuestas.length)];
            }}
            
            // Reemplazar saltos de línea por <br>
            respuesta = respuesta.replace(/\\n/g, '<br>');
            agregarMensajeChat(respuesta, 'bot');
        }}

        function inicializarChat() {{
            // Agregar mensaje inicial al chat
            const messages = document.getElementById('chatMessages');
            messages.innerHTML = '';
        }}

        // ==============================================
        // SISTEMA DE BÚSQUEDA
        // ==============================================
        function inicializarBuscador() {{
            const buscador = document.getElementById('buscadorPrincipal');
            const sugerencias = document.getElementById('sugerenciasBusqueda');
            
            buscador.addEventListener('input', function() {{
                const query = normalizarTexto(this.value);
                
                if (query.length < 2) {{
                    sugerencias.style.display = 'none';
                    return;
                }}
                
                const resultados = todosProductos.filter(p => 
                    normalizarTexto(p.nombre).includes(query) ||
                    normalizarTexto(p.marca).includes(query) ||
                    normalizarTexto(p.descripcion).includes(query)
                ).slice(0, 10);
                
                if (resultados.length > 0) {{
                    sugerencias.innerHTML = resultados.map(p => `
                        <div class="sugerencia-item" onclick="seleccionarProductoBusqueda(${{p.id}})">
                            <img src="${{p.imagen}}" alt="${{p.nombre}}" style="width: 40px; height: 40px;">
                            <div>
                                <strong>${{p.nombre}}</strong><br>
                                <small>${{p.marca}} - ${{p.precio_str}}</small>
                            </div>
                        </div>
                    `).join('');
                    sugerencias.style.display = 'block';
                }} else {{
                    sugerencias.style.display = 'none';
                }}
            }});
            
            // Cerrar sugerencias al hacer clic fuera
            document.addEventListener('click', function(e) {{
                if (!buscador.contains(e.target) && !sugerencias.contains(e.target)) {{
                    sugerencias.style.display = 'none';
                }}
            }});
            
            // Filtros rápidos
            document.querySelectorAll('.filtro-btn').forEach(btn => {{
                btn.addEventListener('click', function() {{
                    const tipo = this.dataset.tipo;
                    filtrarProductos(tipo);
                }});
            }});
        }}

        function seleccionarProductoBusqueda(productoId) {{
            const producto = todosProductos.find(p => p.id === productoId);
            if (producto) {{
                // Encontrar en qué página está el producto
                const index = todosProductos.findIndex(p => p.id === productoId);
                const pagina = Math.floor(index / CONFIG_SISTEMA.PRODUCTOS_POR_PAGINA) + 1;
                
                // Mostrar la página del producto
                mostrarPagina(pagina);
                
                // Desplazar hacia el producto
                setTimeout(() => {{
                    const elemento = document.querySelector(`[data-id="${{productoId}}"]`);
                    if (elemento) {{
                        elemento.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                        
                        // Destacar temporalmente
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

        function filtrarProductos(tipo) {{
            let filtrados = todosProductos;
            
            if (tipo === 'ofertas') {{
                filtrados = todosProductos.filter(p => p.precio > 0 && Math.random() > 0.5);
            }} else if (['yamaha', 'honda', 'suzuki', 'akt'].includes(tipo)) {{
                filtrados = todosProductos.filter(p => 
                    normalizarTexto(p.marca).includes(tipo)
                );
            }}
            
            productos = filtrados;
            totalPaginas = Math.ceil(productos.length / CONFIG_SISTEMA.PRODUCTOS_POR_PAGINA);
            mostrarPagina(1);
            mostrarToast(`${{filtrados.length}} productos encontrados`, 'info');
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
                // Abrir WhatsApp para consultar
                const mensaje = `Hola, estoy interesado en: ${{productoSeleccionado.nombre}} (${{productoSeleccionado.marca}})`;
                window.open(`https://wa.me/${{CONFIG_SISTEMA.WHATSAPP_NUMERO}}?text=${{encodeURIComponent(mensaje)}}`, '_blank');
                return;
            }}
            
            // Actualizar resumen en el modal
            const resumen = document.getElementById('resumenCompra');
            const precioFinal = productoSeleccionado.precio_final;
            
            resumen.innerHTML = `
                <h4>Resumen del pedido</h4>
                <div class="resumen-item" style="display: flex; align-items: center; gap: 15px; margin: 15px 0;">
                    <img src="${{productoSeleccionado.imagen}}" alt="${{productoSeleccionado.nombre}}" 
                         style="width: 60px; height: 60px; border-radius: 8px; object-fit: cover;">
                    <div style="flex: 1;">
                        <h5 style="margin: 0;">${{productoSeleccionado.nombre}}</h5>
                        <p style="margin: 5px 0; font-size: 14px; color: var(--text-secondary);">${{productoSeleccionado.marca}}</p>
                    </div>
                    <span class="precio-actual">${{formatearPrecio(precioFinal)}}</span>
                </div>
                <div class="resumen-total">
                    <span>Total a pagar:</span>
                    <strong class="precio-actual">${{formatearPrecio(precioFinal)}}</strong>
                </div>
            `;
            
            // Mostrar modal
            document.getElementById('modalCompra').style.display = 'flex';
            
            // Resetear formulario
            document.getElementById('formCompra').reset();
        }}

        function cerrarModalCompra() {{
            document.getElementById('modalCompra').style.display = 'none';
            productoSeleccionado = null;
        }}

        // Manejar envío del formulario de compra
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
            
            // Validaciones
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
            
            // Procesar pago con Wompi
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
        // SISTEMA DE CARRITO
        // ==============================================
        function inicializarCarrito() {{
            const carritoGuardado = localStorage.getItem('carrito_templo');
            carrito = carritoGuardado ? JSON.parse(carritoGuardado) : [];
            actualizarContadorCarrito();
            
            document.getElementById('btnCarritoFlotante').addEventListener('click', mostrarCarrito);
        }}

        function agregarAlCarrito(productoId) {{
            const producto = todosProductos.find(p => p.id === productoId);
            if (!producto) return;
            
            carrito.push({{
                ...producto,
                cantidad: 1,
                fecha: new Date().toISOString()
            }});
            
            localStorage.setItem('carrito_templo', JSON.stringify(carrito));
            actualizarContadorCarrito();
            
            mostrarToast('Producto agregado al carrito', 'success');
        }}

        function actualizarContadorCarrito() {{
            const contador = document.getElementById('carritoContador');
            if (carrito.length > 0) {{
                contador.textContent = carrito.length;
                contador.style.display = 'flex';
            }} else {{
                contador.style.display = 'none';
            }}
        }}

        function mostrarCarrito() {{
            if (carrito.length === 0) {{
                mostrarToast('El carrito está vacío', 'info');
                return;
            }}
            
            let mensaje = '🛒 Tu carrito:\\n\\n';
            let total = 0;
            
            carrito.forEach((item, index) => {{
                const precio = item.precio_final || 0;
                mensaje += `${{index + 1}}. ${{item.nombre}} - $${{precio.toLocaleString()}}\\n`;
                total += precio;
            }});
            
            mensaje += `\\n💰 Total: $${{total.toLocaleString()}}\\n\\n`;
            mensaje += `¿Deseas proceder al pago de estos ${{carrito.length}} productos?`;
            
            if (confirm(mensaje)) {{
                mostrarToast('Función de carrito múltiple en desarrollo', 'info');
            }}
        }}

        // ==============================================
        // FUNCIONES AUXILIARES
        // ==============================================
        function mostrarTerminos() {{
            const terminos = `
                <h3>Términos y Condiciones</h3>
                <p>1. Todos los precios incluyen IVA.</p>
                <p>2. Envíos a todo Colombia.</p>
                <p>3. Garantía de 3 meses en todos los productos.</p>
                <p>4. Devoluciones en 15 días si el producto está sin usar.</p>
                <p>5. Los tiempos de envío varían según la ciudad.</p>
                <p>6. Para reclamos, contactar por WhatsApp.</p>
            `;
            
            alert(terminos);
        }}

        // Prevenir cerrar modal al hacer clic fuera
        document.getElementById('modalCompra').addEventListener('click', function(e) {{
            if (e.target === this) {{
                cerrarModalCompra();
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
        # ==============================================
        # 1. CARGAR RECURSOS GRÁFICOS
        # ==============================================
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
                    # Usar placeholder si falla
                    recursos[nombre] = generar_url_placeholder(nombre.replace('_', ' '), 400, 200)
            else:
                print(f"   ❌ {nombre}: No encontrado en {ruta}")
                recursos[nombre] = generar_url_placeholder(nombre.replace('_', ' '), 400, 200)
        
        # ==============================================
        # 2. CARGAR Y PROCESAR DATOS DEL EXCEL
        # ==============================================
        print("\n📊 CARGANDO DATOS DEL EXCEL...")
        
        try:
            # Verificar si el archivo existe
            if not os.path.exists(CONFIG["RUTAS"]["EXCEL"]):
                print(f"❌ Archivo Excel no encontrado: {CONFIG['RUTAS']['EXCEL']}")
                print("   Creando datos de demostración...")
                
                # Crear datos demo
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
                # Leer Excel real
                print(f"   📄 Archivo: {CONFIG['RUTAS']['EXCEL']}")
                print(f"   📋 Hoja: {CONFIG['EXCEL']['HOJA']}")
                
                # Listar hojas disponibles
                xls = pd.ExcelFile(CONFIG["RUTAS"]["EXCEL"])
                print(f"   📑 Hojas disponibles: {xls.sheet_names}")
                
                # Verificar si la hoja configurada existe
                hoja_a_usar = CONFIG["EXCEL"]["HOJA"]
                if hoja_a_usar not in xls.sheet_names:
                    print(f"   ⚠️ Hoja '{hoja_a_usar}' no encontrada. Usando primera hoja.")
                    hoja_a_usar = xls.sheet_names[0]
                
                # Leer Excel
                df = pd.read_excel(CONFIG["RUTAS"]["EXCEL"], sheet_name=hoja_a_usar)
                print(f"   ✅ Excel cargado: {len(df)} filas, {len(df.columns)} columnas")
                
                # Mostrar columnas encontradas
                print(f"   📊 Columnas encontradas: {list(df.columns)}")
        
        except Exception as e:
            print(f"❌ Error leyendo Excel: {e}")
            print("   Creando datos de demostración...")
            
            # Crear datos demo en caso de error
            df = pd.DataFrame({
                'MARCA': ['Yamaha', 'Honda', 'Suzuki', 'AKT', 'Kawasaki'] * 20,
                'NOMBRE': ['Filtro de Aire', 'Cadena', 'Bujía', 'Aceite', 'Pastillas'] * 20,
                'PRECIO MUNDIMOTOS': [45000, 120000, 15000, 35000, 80000] * 20,
                'imagen_url': [generar_url_placeholder(m) for m in ['Yamaha', 'Honda', 'Suzuki', 'AKT', 'Kawasaki']] * 20,
                'DESCRIPCION': ['Producto de alta calidad', 'Original de fábrica', 
                               'Alto rendimiento', 'Durabilidad garantizada', 'Seguridad'] * 20,
                'TIPO': ['Filtro', 'Transmisión', 'Eléctrico', 'Lubricante', 'Frenos'] * 20
            })
        
        # ==============================================
        # 3. LIMPIAR Y PROCESAR DATOS
        # ==============================================
        print("\n🧹 PROCESANDO DATOS...")
        
        # Limpiar datos
        df_limpio = limpiar_datos_excel(df)
        
        # Limitar cantidad de productos si es necesario
        if len(df_limpio) > CONFIG["PARAMETROS"]["MAX_PRODUCTOS"]:
            print(f"   ⚠️ Limitar a {CONFIG['PARAMETROS']['MAX_PRODUCTOS']} productos")
            df_limpio = df_limpio.head(CONFIG["PARAMETROS"]["MAX_PRODUCTOS"])
        
        # Procesar productos
        procesador = ProcesadorProductos()
        productos = procesador.procesar_dataframe(df_limpio)
        
        estadisticas = procesador.estadisticas
        
        print(f"\n✅ PROCESAMIENTO COMPLETADO")
        print(f"   • Total productos: {estadisticas['total']:,}")
        print(f"   • Con precio: {estadisticas['con_precio']:,}")
        print(f"   • Marcas únicas: {len(estadisticas['marcas_unicas'])}")
        print(f"   • Tipos: {len(estadisticas['tipos_unicos'])}")
        print(f"   • Errores: {estadisticas['errores']}")
        
        # ==============================================
        # 4. GENERAR HTML
        # ==============================================
        print("\n🚀 GENERANDO HTML PROFESIONAL...")
        
        html = generar_html_completo(productos, recursos, estadisticas)
        
        # ==============================================
        # 5. GUARDAR ARCHIVO
        # ==============================================
        output_path = CONFIG["RUTAS"]["SALIDA"]
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        tiempo_total = time.time() - start_time
        
        print(f"\n💾 ARCHIVO GUARDADO: {output_path}")
        print(f"   • Tamaño: {os.path.getsize(output_path)/1024/1024:.2f} MB")
        print(f"   • Tiempo total: {tiempo_total:.2f} segundos")
        print(f"   • Productos/segundo: {estadisticas['total']/tiempo_total:.2f}")
        
        # ==============================================
        # 6. GENERAR REPORTE
        # ==============================================
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
        
        # Guardar reporte en archivo
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
        
        # ==============================================
        # 7. ABRIR EN NAVEGADOR
        # ==============================================
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